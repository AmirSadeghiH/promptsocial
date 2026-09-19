from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render

from interactions.models import Follow, Save
from notifications.models import Notification
from notifications.services import serialize_notification, unread_count
from posts.models import Category
from posts.services import (
    get_explore_data,
    get_following_feed,
    get_latest_feed,
    get_trending_feed,
    post_list_queryset,
    search_posts,
    serialize_post,
)


def _viewer(request):
    return request.user if request.user.is_authenticated else None


def _base_context(request):
    context = {
        "categories": Category.objects.all(),
        "unread_notifications": 0,
    }
    if request.user.is_authenticated:
        context["unread_notifications"] = unread_count(request.user)
    return context


def home(request):
    viewer = _viewer(request)
    page = get_trending_feed(page_size=12, viewer=viewer)
    context = {
        **_base_context(request),
        "posts": page["results"],
        "next_cursor": page["next_cursor"],
        "feed_tab": "foryou",
    }
    return render(request, "web/explore.html", context)


def feed_page(request, feed):
    if feed == "following" and not request.user.is_authenticated:
        return redirect("login")

    viewer = _viewer(request)
    feed_fn = {
        "latest": get_latest_feed,
        "following": get_following_feed,
        "trending": get_trending_feed,
    }[feed]
    if feed == "following":
        page = feed_fn(request.user, page_size=12, viewer=viewer)
    else:
        page = feed_fn(page_size=12, viewer=viewer)

    context = {
        **_base_context(request),
        "posts": page["results"],
        "next_cursor": page["next_cursor"],
        "feed_tab": feed,
    }
    return render(request, "web/feed.html", context)


def explore_page(request):
    context = {**_base_context(request), "explore": get_explore_data(viewer=_viewer(request))}
    return render(request, "web/explore.html", context)


def search_page(request):
    query = request.GET.get("q", "").strip()
    context = {**_base_context(request), "query": query, "results": []}
    if query:
        page = search_posts(query, page_size=24, viewer=_viewer(request))
        context["results"] = page["results"]
        context["next_cursor"] = page["next_cursor"]
    return render(request, "web/search.html", context)


def category_page(request, slug):
    category = get_object_or_404(Category, slug=slug)
    page = search_posts("", category_slug=slug, page_size=24, viewer=_viewer(request))
    context = {
        **_base_context(request),
        "category": category,
        "posts": page["results"],
        "next_cursor": page["next_cursor"],
    }
    return render(request, "web/category.html", context)


def post_detail_page(request, pk):
    post = get_object_or_404(post_list_queryset(), pk=pk)
    context = {**_base_context(request), "post": serialize_post(post, viewer=_viewer(request))}
    return render(request, "web/post_detail.html", context)


def create_post_page(request):
    context = _base_context(request)
    context["category_options"] = Category.objects.all()
    return render(request, "web/create.html", context)


def profile_page(request, username):
    user = get_object_or_404(get_user_model(), username=username)
    viewer = _viewer(request)
    posts = post_list_queryset().filter(author=user)[:24]
    context = {
        **_base_context(request),
        "profile_user": user,
        "posts": [serialize_post(post, viewer=viewer) for post in posts],
        "follower_count": Follow.objects.filter(following=user).count(),
        "following_count": Follow.objects.filter(follower=user).count(),
        "is_following": bool(
            viewer and Follow.objects.filter(follower=viewer, following=user).exists()
        ),
    }
    return render(request, "web/profile.html", context)


def saved_page(request):
    if not request.user.is_authenticated:
        return redirect("login")

    save_rows = (
        Save.objects.filter(user=request.user).select_related("post").order_by("-created_at")
    )
    posts = post_list_queryset().filter(pk__in=[r.post_id for r in save_rows])
    by_id = {p.pk: p for p in posts}
    ordered = [by_id[r.post_id] for r in save_rows if r.post_id in by_id]
    context = {
        **_base_context(request),
        "posts": [serialize_post(p, viewer=request.user) for p in ordered],
    }
    return render(request, "web/saved.html", context)


def notifications_page(request):
    if not request.user.is_authenticated:
        return redirect("login")

    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("actor", "post", "comment")[:50]
    )
    context = {
        **_base_context(request),
        "notifications": [serialize_notification(n) for n in notifications],
    }
    return render(request, "web/notifications.html", context)


def offline_page(request):
    return render(request, "web/offline.html")
