import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from interactions.models import Follow, Save
from posts.services import post_list_queryset, serialize_post


def _method_not_allowed():
    return JsonResponse({"error": "Method not allowed."}, status=405)


def _parse_body(request):
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def serialize_user(user, *, viewer=None, detailed=False):
    data = {
        "id": user.pk,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "is_verified": user.is_verified,
        "profile_picture": user.profile_picture.url if user.profile_picture else None,
    }
    if detailed:
        follower_count = Follow.objects.filter(following=user).count()
        following_count = Follow.objects.filter(follower=user).count()
        data.update(
            {
                "biography": user.biography,
                "level": user.level,
                "experience": user.experience,
                "post_count": user.posts.count(),
                "follower_count": follower_count,
                "following_count": following_count,
            }
        )
        if viewer is not None and viewer.is_authenticated and viewer.pk != user.pk:
            data["is_following"] = Follow.objects.filter(
                follower=viewer, following=user
            ).exists()
    return data


@csrf_exempt
@require_POST
def signup(request):
    data = _parse_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    display_name = str(data.get("display_name", "")).strip()

    errors = {}
    if not username:
        errors["username"] = "Username is required."
    if "@" not in email:
        errors["email"] = "A valid email is required."
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters."

    User = get_user_model()
    if not errors and User.objects.filter(username__iexact=username).exists():
        errors["username"] = "This username is already taken."
    if not errors and User.objects.filter(email__iexact=email).exists():
        errors["email"] = "This email is already registered."
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        display_name=display_name or username,
    )
    login(request, user)
    return JsonResponse({"user": serialize_user(user, detailed=True)}, status=201)


@csrf_exempt
@require_POST
def api_login(request):
    data = _parse_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    identifier = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    User = get_user_model()
    user = None
    lookup = Q(username__iexact=identifier) | Q(email__iexact=identifier)
    found = User.objects.filter(lookup).first()
    if found:
        user = authenticate(request, username=found.username, password=password)

    if user is None:
        return JsonResponse({"error": "Invalid credentials."}, status=400)

    login(request, user)
    return JsonResponse({"user": serialize_user(user, detailed=True)})


@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({"logged_out": True})


def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)
    return JsonResponse(
        {"user": serialize_user(request.user, viewer=request.user, detailed=True)}
    )


def profile_detail(request, username):
    if request.method != "GET":
        return _method_not_allowed()

    user = get_object_or_404(
        get_user_model().objects.annotate(post_count=Count("posts")),
        username=username,
    )
    viewer = request.user if request.user.is_authenticated else None
    data = serialize_user(user, viewer=viewer, detailed=True)
    data["posts"] = [
        serialize_post(post, viewer=viewer)
        for post in post_list_queryset().filter(author=user)[:12]
    ]
    return JsonResponse({"user": data})


@login_required
def profile_update(request):
    if request.method not in ("PUT", "PATCH"):
        return _method_not_allowed()

    data = _parse_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    user = request.user
    if "display_name" in data:
        user.display_name = str(data["display_name"]).strip()[:100]
    if "biography" in data:
        user.biography = str(data["biography"]).strip()
    user.save()
    return JsonResponse({"user": serialize_user(user, detailed=True)})


@login_required
def saved_posts(request):
    if request.method != "GET":
        return _method_not_allowed()

    save_rows = list(
        Save.objects.filter(user=request.user)
        .select_related("post")
        .order_by("-created_at", "-pk")
    )
    if not save_rows:
        return JsonResponse({"results": []})

    posts = {
        post.pk: post
        for post in post_list_queryset().filter(pk__in=[row.post_id for row in save_rows])
    }
    ordered = [posts[row.post_id] for row in save_rows if row.post_id in posts]
    return JsonResponse(
        {"results": [serialize_post(post, viewer=request.user) for post in ordered]}
    )
