# Promptly — AI Prompt Community

A social network for AI prompts. Users share prompts, generated images and videos,
discover trending content, follow creators, save and remix.

Dark · Premium · Minimal — the mood of Pinterest, X, Product Hunt, Linear and
Dribbble, distilled into its own design system.

## Stack

- **Backend:** Django 6.1 (Python 3.12), SQLite for dev, session auth, JSON APIs
- **Frontend:** Server-rendered Django templates + vanilla JS/CSS (no build step)
- **PWA:** manifest + service worker (offline shell, cached static/media)
- **Static/media:** WhiteNoise for static, Django media for uploads

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # optional: demo users/posts/likes
python manage.py runserver
```

Open http://127.0.0.1:8000 — demo accounts: `demo_nova` … `demo_orbit`,
password `demo-password-123`. Admin: create one with `python manage.py createsuperuser`.

## Apps

| App | Purpose |
|---|---|
| `account` | Custom user, profile, signup/login/logout, follow counts, saved posts |
| `posts` | Post/Category/Tag models, CRUD API, feeds, trending ranking, search, explore |
| `interactions` | Like, Save, Comment, Follow, View & Copy events + APIs |
| `notifications` | Notification model, signals on like/save/comment/follow, read/unread API |
| `web` | Server-rendered frontend pages (feed, explore, search, detail, create, profile, notifications) |

## API overview (all JSON, under `/api/`)

**Feeds & discovery** — `GET /api/posts/feed/latest|following|trending/`,
`GET /api/posts/explore/`, `GET /api/posts/search/?q=…&type=…&category=…&tag=…&ai_model=…`,
`GET /api/posts/categories/`, `GET /api/posts/categories/<slug>/`, `GET /api/posts/tags/`

**Posts** — `POST /api/posts/create/`, `GET /api/posts/<id>/`,
`PATCH|PUT /api/posts/<id>/update/`, `DELETE /api/posts/<id>/delete/`
(cursor pagination with `page_size` 1–50 and opaque `cursor`)

**Interactions** — `POST /api/posts/<id>/view|copy|like|save/`,
`GET /api/posts/<id>/comments/`, `POST /api/posts/<id>/comments/create/`,
`DELETE /api/posts/comments/<id>/delete/`, `POST /api/posts/users/<username>/follow/`

**Account** — `POST /api/auth/signup|login|logout/`, `GET /api/auth/me/`,
`PATCH /api/me/update/`, `GET /api/me/saved/`, `GET /api/users/<username>/`

**Notifications** — `GET /api/notifications/`, `POST /api/notifications/read-all/`,
`POST /api/notifications/<id>/read/`

## Design system

- Colors: near-black surfaces (`#0a0a0f` → `#14141c`), violet accent `#8b7cf6`,
  semantic like-red / save-gold, 8% white borders.
- Typography: Inter for UI, JetBrains Mono for prompt text.
- Desktop: sticky top bar + left sidebar (nav + categories) + 4-column masonry.
- Mobile/PWA: single-column cards, top bar with search, floating create button,
  bottom tab bar (Home / Explore / ＋ / Saved / Profile), safe-area aware.

## Testing

```bash
python manage.py test
```

Covers feeds & ranking, cursor pagination, query-count (N+1) guards, search,
post CRUD + permissions, like/save/comment/follow toggles, notifications
(signals + API), auth and profiles.

## Production

Set env vars: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`,
`DJANGO_ALLOWED_HOSTS=yourdomain.com`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com`.
Then `python manage.py collectstatic` and serve behind HTTPS (HSTS, secure cookies and
SSL redirect are enabled automatically when `DEBUG=false`). Serve `MEDIA_ROOT`
from a CDN/object store for scale; swap SQLite for Postgres when needed.

## Roadmap status (MVP)

| Area | Status |
|---|---|
| 1. Account | ✅ API, views, admin, tests |
| 2. Posts | ✅ CRUD API, media fields, admin |
| 3. Interactions | ✅ Like/Save/Comment/Follow APIs |
| 4. Feed & Discovery | ✅ (was already done) |
| 5. Search | ✅ title/prompt/description/tags/category/AI model/creator |
| 6. Notifications | ✅ app, signals, read/unread API |
| 7. APIs & Admin | ✅ all models registered, full JSON surface |
| 8. Frontend | ✅ dark premium minimal, desktop + mobile layouts |
| 9. PWA | ✅ manifest, service worker, offline page, installable |
| 10. Testing & Deploy | ✅ test suite + env-based production settings |
