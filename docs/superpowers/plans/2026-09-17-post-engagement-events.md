# Post Engagement Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record anonymous or authenticated post views and authenticated post copies through durable Django models and JSON endpoints.

**Architecture:** The `interactions` app owns append-only `PostView` and `PostCopy` event rows. Small function views record those rows and return a stable JSON payload. `core.urls` exposes the endpoints under `/api/posts/` without adding a REST framework dependency.

**Tech Stack:** Python 3.12, Django 6.1, SQLite, Django `TestCase` and `Client`.

**Spec:** `docs/superpowers/specs/2026-09-17-prompt-social-mvp-backend-design.md`

## Global Constraints

- Content remains public; post visibility and moderation are out of scope.
- `posts` owns content; `interactions` owns engagement records.
- Add no third-party REST, search, task-queue, cache, or background-worker dependency.
- Read endpoint responses are JSON; mutations use POST and Django session authentication/CSRF handling.
- A view has an optional authenticated user and a copy requires one; neither event is unique per user and post.
- Validate using `makemigrations --check`, `migrate`, `check`, and the full Django test suite before reporting the phase complete.

---

## File structure

- `core/settings.py`: activates the existing `interactions` app.
- `interactions/models.py`: defines event data and query indexes.
- `interactions/migrations/0001_initial.py`: creates the existing interaction tables and the event tables in one reproducible migration.
- `interactions/views.py`: records events and formats JSON responses.
- `interactions/urls.py`: gives engagement views named routes.
- `core/urls.py`: mounts interactions routes under `/api/posts/`.
- `interactions/admin.py`: exposes engagement tables to staff users.
- `interactions/tests.py`: exercises observable model and HTTP contracts using real database rows.

### Task 1: Engagement models and migration

**Files:**
- Modify: `core/settings.py:26-29`
- Modify: `interactions/models.py:1-143`
- Create: `interactions/migrations/0001_initial.py`
- Modify: `interactions/tests.py:1-3`

**Interfaces:**
- Consumes: `posts.Post` and `settings.AUTH_USER_MODEL`.
- Produces: `PostView(post: Post, user: CustomUser | None)` and `PostCopy(post: Post, user: CustomUser)` models, both with `created_at`.

- [ ] **Step 1: Write the failing model tests**

```python
class PostEngagementModelTests(TestCase):
    def test_view_can_be_recorded_without_a_user(self):
        event = PostView.objects.create(post=self.post)
        self.assertIsNone(event.user)
        self.assertEqual(event.post, self.post)

    def test_copy_records_each_use_by_the_same_user(self):
        PostCopy.objects.create(post=self.post, user=self.user)
        PostCopy.objects.create(post=self.post, user=self.user)
        self.assertEqual(PostCopy.objects.filter(post=self.post, user=self.user).count(), 2)
```

- [ ] **Step 2: Run the model tests to verify they fail**

Run: `.\\.venv\\Scripts\\python.exe manage.py test interactions.tests.PostEngagementModelTests -v 2`

Expected: FAIL because `PostView` and `PostCopy` cannot yet be imported from `interactions.models`.

- [ ] **Step 3: Implement the smallest event models and activate the app**

```python
class PostView(models.Model):
    post = models.ForeignKey("posts.Post", on_delete=models.CASCADE, related_name="view_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="post_views")
    created_at = models.DateTimeField(auto_now_add=True)

class PostCopy(models.Model):
    post = models.ForeignKey("posts.Post", on_delete=models.CASCADE, related_name="copy_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_copies")
    created_at = models.DateTimeField(auto_now_add=True)
```

Add the `interactions` app to `INSTALLED_APPS`; add `Meta.indexes` for `("post", "-created_at")` to both models and `("user", "-created_at")` to `PostCopy`; then generate `0001_initial.py` with `makemigrations interactions`.

- [ ] **Step 4: Run the model tests to verify they pass**

Run: `.\\.venv\\Scripts\\python.exe manage.py test interactions.tests.PostEngagementModelTests -v 2`

Expected: PASS with two tests.

### Task 2: Event-recording HTTP API

**Files:**
- Modify: `interactions/views.py:1-3`
- Create: `interactions/urls.py`
- Modify: `core/urls.py:18-22`
- Modify: `interactions/tests.py`

**Interfaces:**
- Consumes: `PostView`, `PostCopy`, and Django `request.user`.
- Produces: `POST /api/posts/<int:post_id>/view/` and `POST /api/posts/<int:post_id>/copy/`, responding with `{\"post_id\": <id>, \"event\": \"view\"|\"copy\"}` and status 201.

- [ ] **Step 1: Write failing endpoint tests**

```python
def test_anonymous_post_creates_a_view_event(self):
    response = self.client.post(reverse("interactions:record-view", args=[self.post.pk]))
    self.assertEqual(response.status_code, 201)
    self.assertEqual(response.json(), {"post_id": self.post.pk, "event": "view"})
    self.assertTrue(PostView.objects.filter(post=self.post, user__isnull=True).exists())

def test_anonymous_user_cannot_record_a_copy(self):
    response = self.client.post(reverse("interactions:record-copy", args=[self.post.pk]))
    self.assertEqual(response.status_code, 401)
    self.assertEqual(PostCopy.objects.count(), 0)
```

- [ ] **Step 2: Run endpoint tests to verify they fail**

Run: `.\\.venv\\Scripts\\python.exe manage.py test interactions.tests.PostEngagementApiTests -v 2`

Expected: FAIL because the namespaced routes do not exist.

- [ ] **Step 3: Implement minimal JSON views and route wiring**

```python
def record_view(request, post_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)
    post = get_object_or_404(Post, pk=post_id)
    PostView.objects.create(post=post, user=request.user if request.user.is_authenticated else None)
    return JsonResponse({"post_id": post.pk, "event": "view"}, status=201)
```

Implement `record_copy` with the same POST and 404 semantics, but return `{\"error\": \"Authentication required.\"}` with status 401 before creating a row for anonymous requests. Add `app_name = "interactions"` and the two named paths to `interactions/urls.py`; mount it at `api/posts/` in `core.urls`.

- [ ] **Step 4: Run endpoint tests to verify they pass**

Run: `.\\.venv\\Scripts\\python.exe manage.py test interactions.tests.PostEngagementApiTests -v 2`

Expected: PASS, including authenticated copy creation, missing-post 404, and non-POST 405 cases.

### Task 3: Administration and phase verification

**Files:**
- Modify: `interactions/admin.py:1-3`
- Modify: `interactions/tests.py`

**Interfaces:**
- Consumes: event models.
- Produces: staff-visible lists for events with post, user, and creation timestamp columns.

- [ ] **Step 1: Write a failing admin-registration test**

```python
def test_event_models_are_registered_in_the_admin(self):
    self.assertTrue(admin.site.is_registered(PostView))
    self.assertTrue(admin.site.is_registered(PostCopy))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.\\.venv\\Scripts\\python.exe manage.py test interactions.tests.InteractionsAdminTests -v 2`

Expected: FAIL because neither event model is registered.

- [ ] **Step 3: Register concise admin classes**

```python
@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
    list_select_related = ("post", "user")
    ordering = ("-created_at",)
```

Register `PostCopy` with the same list shape and ordering.

- [ ] **Step 4: Run focused tests and system validation**

Run: `.\\.venv\\Scripts\\python.exe manage.py test interactions -v 2`

Expected: PASS.

Run: `.\\.venv\\Scripts\\python.exe manage.py makemigrations --check; .\\.venv\\Scripts\\python.exe manage.py migrate; .\\.venv\\Scripts\\python.exe manage.py check; .\\.venv\\Scripts\\python.exe manage.py test -v 2`

Expected: no uncreated migrations, migrations applied, no check issues, and no test failures.
