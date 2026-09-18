import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from posts.models import Category, Post, Tag
from posts.services import (
    InvalidCursor,
    get_explore_data,
    get_following_feed,
    get_latest_feed,
    get_trending_feed,
    post_list_queryset,
    search_posts,
    serialize_post,
)


def _get_pagination_params(request):
    raw_page_size = request.GET.get("page_size", "20")
    try:
        page_size = int(raw_page_size)
    except (TypeError, ValueError):
        return None, None, JsonResponse(
            {"error": "page_size must be an integer between 1 and 50."},
            status=400,
        )

    if not 1 <= page_size <= 50:
        return None, None, JsonResponse(
            {"error": "page_size must be an integer between 1 and 50."},
            status=400,
        )
    return request.GET.get("cursor") or None, page_size, None


def _method_not_allowed():
    return JsonResponse({"error": "Method not allowed."}, status=405)


def _feed_response(request, feed_function, *, user=None):
    if request.method != "GET":
        return _method_not_allowed()

    cursor, page_size, error_response = _get_pagination_params(request)
    if error_response:
        return error_response

    viewer = request.user if request.user.is_authenticated else None
    try:
        if user is None:
            page = feed_function(cursor=cursor, page_size=page_size, viewer=viewer)
        else:
            page = feed_function(user, cursor=cursor, page_size=page_size, viewer=viewer)
    except InvalidCursor:
        return JsonResponse({"error": "Invalid cursor."}, status=400)
    return JsonResponse(page)


def feed_latest(request):
    return _feed_response(request, get_latest_feed)


def feed_following(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)
    return _feed_response(request, get_following_feed, user=request.user)


def feed_trending(request):
    return _feed_response(request, get_trending_feed)


def explore(request):
    if request.method != "GET":
        return _method_not_allowed()
    viewer = request.user if request.user.is_authenticated else None
    return JsonResponse(get_explore_data(viewer=viewer))


def search(request):
    if request.method != "GET":
        return _method_not_allowed()

    cursor, page_size, error_response = _get_pagination_params(request)
    if error_response:
        return error_response

    viewer = request.user if request.user.is_authenticated else None
    try:
        page = search_posts(
            request.GET.get("q", "").strip(),
            post_type=request.GET.get("type") or None,
            category_slug=request.GET.get("category") or None,
            tag_slug=request.GET.get("tag") or None,
            ai_model=request.GET.get("ai_model") or None,
            cursor=cursor,
            page_size=page_size,
            viewer=viewer,
        )
    except InvalidCursor:
        return JsonResponse({"error": "Invalid cursor."}, status=400)
    return JsonResponse(page)


def category_list(request):
    if request.method != "GET":
        return _method_not_allowed()
    categories = Category.objects.annotate(post_count=Count("posts")).order_by("name")
    return JsonResponse(
        {
            "results": [
                {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "description": category.description,
                    "post_count": category.post_count,
                }
                for category in categories
            ]
        }
    )


def category_posts(request, slug):
    if request.method != "GET":
        return _method_not_allowed()

    cursor, page_size, error_response = _get_pagination_params(request)
    if error_response:
        return error_response

    category = get_object_or_404(Category, slug=slug)
    viewer = request.user if request.user.is_authenticated else None
    try:
        page = search_posts(
            "",
            category_slug=category.slug,
            cursor=cursor,
            page_size=page_size,
            viewer=viewer,
        )
    except InvalidCursor:
        return JsonResponse({"error": "Invalid cursor."}, status=400)
    page["category"] = {"id": category.id, "name": category.name, "slug": category.slug}
    return JsonResponse(page)


def tag_list(request):
    if request.method != "GET":
        return _method_not_allowed()

    query = request.GET.get("q", "").strip()
    tags = Tag.objects.all()
    if query:
        tags = tags.filter(Q(name__icontains=query))
    tags = tags.annotate(post_count=Count("posts", filter=Q(posts__isnull=False)))
    tags = tags.filter(post_count__gt=0).order_by("-post_count", "name")[:50]
    return JsonResponse(
        {
            "results": [
                {"id": tag.id, "name": tag.name, "slug": tag.slug, "post_count": tag.post_count}
                for tag in tags
            ]
        }
    )


def _parse_json_body(request):
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _validate_post_payload(data, *, partial=False):
    errors = {}
    post_type = data.get("post_type")
    title = data.get("title")
    category_id = data.get("category_id")

    if not partial or "post_type" in data:
        if post_type not in Post.PostType.values:
            errors["post_type"] = "Must be one of: prompt, image, video, audio."
    if not partial or "title" in data:
        if not isinstance(title, str) or not title.strip():
            errors["title"] = "Title is required."
        elif len(title.strip()) > 200:
            errors["title"] = "Title must be at most 200 characters."
    if not partial or "category_id" in data:
        if not isinstance(category_id, int):
            errors["category_id"] = "Category id is required."

    if errors:
        return None, JsonResponse({"errors": errors}, status=400)

    if partial:
        payload = {}
        if "post_type" in data:
            payload["post_type"] = post_type
        if "title" in data:
            payload["title"] = title.strip()
        if "description" in data:
            payload["description"] = str(data["description"]).strip()
        if "prompt" in data:
            payload["prompt"] = str(data["prompt"]).strip()
        if "ai_model" in data:
            payload["ai_model"] = str(data["ai_model"]).strip()
    else:
        payload = {
            "post_type": post_type,
            "title": title.strip(),
            "description": str(data.get("description") or "").strip(),
            "prompt": str(data.get("prompt") or "").strip(),
            "ai_model": str(data.get("ai_model") or "").strip(),
        }
    return payload, None


@login_required
@csrf_exempt
@require_POST
def post_create(request):
    content_type = request.content_type or ""
    if content_type.startswith("multipart/form-data"):
        data = request.POST.dict()
        data["category_id"] = int(data.get("category_id", 0)) if data.get("category_id") else 0
        payload, error_response = _validate_post_payload(data)
        if error_response:
            return error_response

        try:
            category = Category.objects.get(pk=data["category_id"])
        except (Category.DoesNotExist, ValueError):
            return JsonResponse({"errors": {"category_id": "Unknown category."}}, status=400)

        post = Post.objects.create(
            author=request.user,
            category=category,
            **payload,
            image=request.FILES.get("image"),
            video=request.FILES.get("video"),
            audio=request.FILES.get("audio"),
        )
        tag_ids = data.get("tag_ids")
        if isinstance(tag_ids, list):
            tags = Tag.objects.filter(pk__in=[t for t in tag_ids if isinstance(t, int)])
            post.tags.set(tags)
    else:
        data = _parse_json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        payload, error_response = _validate_post_payload(data)
        if error_response:
            return error_response

        try:
            category = Category.objects.get(pk=data["category_id"])
        except (Category.DoesNotExist, ValueError):
            return JsonResponse({"errors": {"category_id": "Unknown category."}}, status=400)

        post = Post.objects.create(author=request.user, category=category, **payload)
        tag_ids = data.get("tag_ids")
        if isinstance(tag_ids, list):
            tags = Tag.objects.filter(pk__in=[t for t in tag_ids if isinstance(t, int)])
            post.tags.set(tags)

    return JsonResponse(
        {"post": serialize_post(post_list_queryset().get(pk=post.pk), viewer=request.user)},
        status=201,
    )


def post_detail(request, pk):
    if request.method != "GET":
        return _method_not_allowed()
    viewer = request.user if request.user.is_authenticated else None
    post = get_object_or_404(post_list_queryset(), pk=pk)
    return JsonResponse({"post": serialize_post(post, viewer=viewer)})


@login_required
def post_update(request, pk):
    if request.method not in ("PUT", "PATCH"):
        return _method_not_allowed()

    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.id:
        raise PermissionDenied("You can only edit your own posts.")

    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    payload, error_response = _validate_post_payload(data, partial=True)
    if error_response:
        return error_response

    for field, value in payload.items():
        setattr(post, field, value)
    if "category_id" in data:
        try:
            post.category = Category.objects.get(pk=data["category_id"])
        except (Category.DoesNotExist, ValueError):
            return JsonResponse({"errors": {"category_id": "Unknown category."}}, status=400)
    post.save()

    if isinstance(data.get("tag_ids"), list):
        tags = Tag.objects.filter(pk__in=[t for t in data["tag_ids"] if isinstance(t, int)])
        post.tags.set(tags)

    post = post_list_queryset().get(pk=post.pk)
    return JsonResponse({"post": serialize_post(post, viewer=request.user)})


@login_required
def post_delete(request, pk):
    if request.method != "DELETE":
        return _method_not_allowed()

    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.id:
        raise PermissionDenied("You can only delete your own posts.")
    post.delete()
    return JsonResponse({"deleted": True})
