# Prompt Social MVP Backend Design

## Goal

Complete the Django backend MVP after the existing account, post, and interaction models: measurable post engagement, discoverable feeds, search, in-app notifications, JSON endpoints, administration, migrations, and regression tests.

## Scope and constraints

- Content remains public; there is no post-visibility or moderation workflow in this MVP.
- `posts` owns `Post`, `Category`, and `Tag`; interaction records remain in `interactions`; notification delivery state lives in a new `notifications` app.
- The existing project uses Django's built-in test runner and SQLite. The MVP adds no third-party REST, search, task-queue, or cache dependency.
- Endpoints return JSON and use session authentication. Mutating endpoints require an authenticated user and POST; read endpoints are public unless noted.
- The duplicate `account.Follow` is removed in favour of `interactions.Follow`, the existing interaction namespace. No application code will reference two follow tables.

## Data model

### Engagement events

`PostView` and `PostCopy` belong to `interactions` and contain `post`, an optional authenticated `user`, and `created_at`. They intentionally do not have a unique constraint: repeated usage is a useful signal. Indexes start with `(post, -created_at)` for recent aggregation and `(user, -created_at)` for user activity where the user is present.

`Like`, `Save`, `Comment`, and `Follow` retain their existing semantics. Like, Save, and Follow are unique per actor/target. The `Follow.clean()` self-follow validation is preserved and will also be enforced in the endpoint before persistence.

### Notifications

`Notification` records a recipient, actor, one of `follow`, `like`, `save`, or `comment`, an optional target post, an optional target comment, `created_at`, and `read_at`. A uniqueness constraint prevents duplicate follow/like/save notifications for the same actor/recipient/post/action; comments remain independently notifiable. Notifications are not created when actor equals recipient.

Creating a notification is encapsulated in `notifications.services.create_notification()` so interaction code need not know its schema. Initial MVP delivery is in-app only; no email, background worker, or push channel is introduced.

## Query and ranking design

### Shared post query

All feed/search/explore endpoints use one `posts.services.post_list_queryset()` base query. It uses `select_related("author", "category")`, prefetches tags, and annotates counts for likes, saves, comments, views, and copies. This keeps serialization constant-query with respect to the number of posts shown and avoids N+1 fetching.

### Cursor pagination

The cursor is a URL-safe encoded `created_at` timestamp plus post ID. It provides stable, descending ordering by `-created_at, -id`; the next page filters records older than that tuple. Inputs with an invalid cursor return HTTP 400 rather than silently producing arbitrary results. Page size defaults to 20 and is capped at 50.

### Feeds

- **Latest:** all public posts by newest creation time.
- **Following:** posts whose authors are followed by the authenticated requester; anonymous requests return HTTP 401.
- **Trending:** posts from the last 30 days, ordered by an annotated score: `likes*3 + saves*5 + comments*4 + copies*6 + views`, divided by an age factor that increases per 24 hours. Ties are deterministic by creation time and ID.
- **Explore:** a small composition of the latest and trending lists plus popular categories and creators calculated from existing post activity.

## API contract

All routes sit below `/api/` and return an object with explicit fields instead of Django model dumps.

- `GET /api/feed/latest/`, `GET /api/feed/following/`, and `GET /api/feed/trending/` accept `cursor` and `page_size`, return `results` and `next_cursor`.
- `GET /api/explore/` returns `latest`, `trending`, `popular_categories`, and `popular_creators`.
- `GET /api/search/?q=` searches post title, description, prompt, AI model, category, tags, and creator username/display name using case-insensitive matching. Blank/whitespace-only queries return HTTP 400.
- `POST /api/posts/<post_id>/view/` creates a view event. It accepts anonymous and authenticated requests.
- `POST /api/posts/<post_id>/copy/` creates a copy event and requires authentication.
- `GET /api/notifications/` requires authentication and is cursor-paginated.
- `POST /api/notifications/<notification_id>/read/` requires the recipient and sets `read_at` idempotently.

Existing interaction models receive matching POST endpoints for follow, like, save, and comment only if their tests establish the required surface; the MVP will not add broad CRUD that has no user flow.

## Error handling and security

JSON errors contain an `error` string. Missing objects return 404. Unsupported methods return 405. Authentication failures return 401. Mutating views use Django's CSRF protection under session auth. Ownership checks prevent reading or marking another user's notification.

## Administration

All account, post, interaction, and notification models are registered with useful `list_display`, `list_filter`, `search_fields`, ordering, and relationship autocomplete fields where valid.

## Testing and validation

Tests use Django `TestCase` and `Client` with factory helpers local to each test module. Coverage includes model constraints, event recording, notification creation/idempotence, anonymous versus authenticated access, JSON errors, cursor boundary behavior, ranking order, search matches, and a query-count assertion on representative feed serialization. Each feature follows a red-green test cycle.

Before reporting completion, run `makemigrations --check`, `migrate`, `check`, and the full test suite. The resulting work leaves frontend UI, API client integration, PWA assets/offline caching, production settings, media storage, rate limits, full-text search infrastructure, and async notification delivery for later phases.
