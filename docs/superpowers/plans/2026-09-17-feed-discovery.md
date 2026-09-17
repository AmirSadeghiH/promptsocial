# Feed and Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide public Latest and Trending feeds, an authenticated Following feed, and Explore discovery data through efficient cursor-paginated Django JSON endpoints.

**Architecture:** `posts.services` owns composable post querysets, ranking annotations, opaque cursor encoding, pagination, and presentation-safe serialization. `posts.views` only validates HTTP input and turns service results into JSON. All feed paths share the same select/prefetch plan and aggregated engagement counters, so adding a feed does not create a new query pattern.

**Tech Stack:** Python 3.12, Django 6.1 ORM, SQLite, Django `TestCase`/`Client`; no third-party API framework or cache.

**Spec:** `docs/superpowers/specs/2026-09-17-prompt-social-mvp-backend-design.md`

## Global Constraints

- Public posts are the complete post set for this MVP.
- Use Django ORM and JSON responses only; add no DRF, search package, cache, task queue, or external service.
- Page size defaults to 20, accepts a positive integer, and never exceeds 50.
- Invalid cursors and invalid page sizes return JSON HTTP 400; Following returns JSON HTTP 401 for anonymous users.
- A serialized post contains author, category, tags, timestamps, and all five engagement counts without per-post queries.
- Trending considers the last 30 days and orders the score `likes*3 + saves*5 + comments*4 + copies*6 + views` divided by a deterministic age-factor bucket.
- Run focused red-green tests before each implementation task, then `makemigrations --check`, `check`, and the full suite.

---

## File structure

- `posts/services.py`: query construction, score annotations, cursor handling, pagination, and serialization.
- `posts/views.py`: JSON endpoint functions and input validation.
- `posts/urls.py`: namespaced API route declarations.
- `core/urls.py`: mounts posts endpoints at `/api/`.
- `posts/tests.py`: end-to-end feed contracts, pagination, ranking, authentication, and query-count coverage.

### Task 1: Feed service and chronological cursor pagination

**Files:**
- Create: `posts/services.py`
- Modify: `posts/tests.py`

**Interfaces:**
- Produces: `get_latest_feed(*, cursor: str | None, page_size: int) -> dict` whose result has `results` and `next_cursor`.
- Produces: `serialize_post(post: Post) -> dict` with count fields `like_count`, `save_count`, `comment_count`, `view_count`, and `copy_count`.

- [ ] **Step 1: Write failing service tests**

```python
def test_latest_feed_returns_newest_post_first_with_a_next_cursor(self):
    page = get_latest_feed(page_size=1)
    self.assertEqual([item["id"] for item in page["results"]], [self.newer_post.id])
    self.assertIsNotNone(page["next_cursor"])

def test_latest_cursor_returns_each_post_once(self):
    first_page = get_latest_feed(page_size=1)
    second_page = get_latest_feed(cursor=first_page["next_cursor"], page_size=1)
    self.assertEqual([item["id"] for item in second_page["results"]], [self.older_post.id])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py test posts.tests.FeedServiceTests -v 2`

Expected: FAIL because `posts.services` does not exist.

- [ ] **Step 3: Implement the base queryset, serializer, and latest paginator**

```python
def post_list_queryset():
    return Post.objects.select_related("author", "category").prefetch_related("tags").annotate(
        like_count=Count("likes", distinct=True),
        save_count=Count("saves", distinct=True),
        comment_count=Count("comments", distinct=True),
        view_count=Count("view_events", distinct=True),
        copy_count=Count("copy_events", distinct=True),
    )
```

Encode the timestamp and ID as URL-safe base64 JSON, decode strictly, order `-created_at, -id`, and fetch `page_size + 1` rows to calculate `next_cursor`.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py test posts.tests.FeedServiceTests -v 2`

Expected: PASS.

### Task 2: Following and Trending service behavior

**Files:**
- Modify: `posts/services.py`
- Modify: `posts/tests.py`

**Interfaces:**
- Consumes: `interactions.Follow`, engagement related names, and `user`.
- Produces: `get_following_feed(user, *, cursor, page_size)` and `get_trending_feed(*, cursor, page_size)`.

- [ ] **Step 1: Write failing behavioral tests**

```python
def test_following_feed_excludes_posts_by_unfollowed_authors(self):
    page = get_following_feed(self.viewer, page_size=20)
    self.assertEqual([item["id"] for item in page["results"]], [self.followed_post.id])

def test_trending_ranks_copy_above_equal_recent_view_activity(self):
    page = get_trending_feed(page_size=20)
    self.assertEqual(page["results"][0]["id"], self.copied_post.id)
```

- [ ] **Step 2: Run to verify they fail**

Run: `D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py test posts.tests.FeedServiceTests -v 2`

Expected: FAIL because following and trending service functions are unavailable.

- [ ] **Step 3: Implement filtered feeds and score-aware cursor pagination**

Use the shared queryset. Filter Following authors with `Follow.objects.filter(follower=user).values("following_id")`. For Trending, filter the 30-day window and annotate a float engagement score and an age bucket of 1 for <24h, 2 for <7d, and 3 otherwise before ordering by `-trending_score, -created_at, -id`. Encode score, timestamp, and ID in the Trending cursor so score ties cannot duplicate or skip rows.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py test posts.tests.FeedServiceTests -v 2`

Expected: PASS, including trending cursor and 30-day cut-off cases.

### Task 3: JSON feed and Explore endpoints

**Files:**
- Modify: `posts/views.py`
- Create: `posts/urls.py`
- Modify: `core/urls.py`
- Modify: `posts/tests.py`

**Interfaces:**
- Produces: `GET /api/feed/latest/`, `/api/feed/following/`, `/api/feed/trending/`, and `/api/explore/`.

- [ ] **Step 1: Write failing HTTP contract tests**

```python
def test_latest_endpoint_returns_json_page(self):
    response = self.client.get(reverse("posts:feed-latest"), {"page_size": 1})
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.json()["results"]), 1)

def test_anonymous_following_endpoint_returns_json_401(self):
    response = self.client.get(reverse("posts:feed-following"))
    self.assertEqual(response.status_code, 401)
    self.assertEqual(response.json(), {"error": "Authentication required."})
```

- [ ] **Step 2: Run endpoint tests to verify they fail**

Run: `D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py test posts.tests.FeedApiTests -v 2`

Expected: FAIL with an unregistered `posts` namespace.

- [ ] **Step 3: Implement views, routes, validation, and Explore**

Parse `page_size` and `cursor` in one helper. Return `{\"error\": \"Invalid cursor.\"}` or `{\"error\": \"page_size must be an integer between 1 and 50.\"}` with 400. Explore returns the first six results of latest and trending plus category and creator lists derived from aggregated post counts, without one query per item.

- [ ] **Step 4: Run endpoint tests to verify they pass**

Run: `D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py test posts.tests.FeedApiTests -v 2`

Expected: PASS.

### Task 4: N+1 regression test and full validation

**Files:**
- Modify: `posts/tests.py`

**Interfaces:**
- Consumes: `get_latest_feed`.
- Produces: a query-count regression guard for a five-post page with tags and engagement data.

- [ ] **Step 1: Write a failing query-count test**

```python
with self.assertNumQueries(2):
    page = get_latest_feed(page_size=5)
    self.assertEqual(len(page["results"]), 5)
```

- [ ] **Step 2: Run the test to observe the pre-optimization count**

Run: `D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py test posts.tests.FeedQueryTests -v 2`

Expected: FAIL before the shared `select_related`/`prefetch_related` query path is used for serialization.

- [ ] **Step 3: Refine only the shared queryset or serializer required to reach a constant query count**

Keep author/category joins and the tags prefetch in `post_list_queryset`; do not query a related manager from `serialize_post`.

- [ ] **Step 4: Validate the complete phase**

Run: `D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py makemigrations --check; D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py check; D:\\PromptSocial\\.venv\\Scripts\\python.exe manage.py test -v 2`

Expected: no migration changes, no system-check issues, and all tests passing.
