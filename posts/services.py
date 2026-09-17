import base64
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Case, Count, ExpressionWrapper, F, FloatField, Q, Value, When
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from interactions.models import Follow
from posts.models import Category, Post


class InvalidCursor(ValueError):
    """Raised when a feed cursor cannot be decoded safely."""


def post_list_queryset():
    return (
        Post.objects.select_related("author", "category")
        .prefetch_related("tags")
        .annotate(
            like_count=Count("likes", distinct=True),
            save_count=Count("saves", distinct=True),
            comment_count=Count("comments", distinct=True),
            view_count=Count("view_events", distinct=True),
            copy_count=Count("copy_events", distinct=True),
        )
    )


def serialize_post(post):
    return {
        "id": post.id,
        "post_type": post.post_type,
        "title": post.title,
        "description": post.description,
        "prompt": post.prompt,
        "ai_model": post.ai_model,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat(),
        "author": {
            "id": post.author_id,
            "username": post.author.username,
            "display_name": post.author.display_name,
            "is_verified": post.author.is_verified,
        },
        "category": {
            "id": post.category_id,
            "name": post.category.name,
            "slug": post.category.slug,
        },
        "tags": [
            {"id": tag.id, "name": tag.name, "slug": tag.slug}
            for tag in post.tags.all()
        ],
        "like_count": post.like_count,
        "save_count": post.save_count,
        "comment_count": post.comment_count,
        "view_count": post.view_count,
        "copy_count": post.copy_count,
    }


def _encode_cursor(created_at, post_id):
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "id": post_id},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor):
    try:
        padded_cursor = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_cursor.encode()).decode())
        created_at = parse_datetime(payload["created_at"])
        post_id = payload["id"]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise InvalidCursor from None

    if created_at is None or not created_at.tzinfo or not isinstance(post_id, int):
        raise InvalidCursor
    return created_at, post_id


def _paginate_chronological(queryset, *, cursor, page_size):
    queryset = queryset.order_by("-created_at", "-id")
    if cursor:
        created_at, post_id = _decode_cursor(cursor)
        queryset = queryset.filter(
            Q(created_at__lt=created_at)
            | Q(created_at=created_at, id__lt=post_id),
        )

    posts = list(queryset[: page_size + 1])
    has_next_page = len(posts) > page_size
    page_posts = posts[:page_size]
    next_cursor = None
    if has_next_page:
        last_post = page_posts[-1]
        next_cursor = _encode_cursor(last_post.created_at, last_post.id)

    return {
        "results": [serialize_post(post) for post in page_posts],
        "next_cursor": next_cursor,
    }


def _encode_trending_cursor(score, created_at, post_id):
    payload = json.dumps(
        {
            "score": score,
            "created_at": created_at.isoformat(),
            "id": post_id,
        },
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_trending_cursor(cursor):
    try:
        padded_cursor = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_cursor.encode()).decode())
        score = payload["score"]
        created_at = parse_datetime(payload["created_at"])
        post_id = payload["id"]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise InvalidCursor from None

    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or created_at is None
        or not created_at.tzinfo
        or not isinstance(post_id, int)
    ):
        raise InvalidCursor
    return float(score), created_at, post_id


def _paginate_trending(queryset, *, cursor, page_size):
    queryset = queryset.order_by("-trending_score", "-created_at", "-id")
    if cursor:
        score, created_at, post_id = _decode_trending_cursor(cursor)
        queryset = queryset.filter(
            Q(trending_score__lt=score)
            | Q(trending_score=score, created_at__lt=created_at)
            | Q(trending_score=score, created_at=created_at, id__lt=post_id),
        )

    posts = list(queryset[: page_size + 1])
    has_next_page = len(posts) > page_size
    page_posts = posts[:page_size]
    next_cursor = None
    if has_next_page:
        last_post = page_posts[-1]
        next_cursor = _encode_trending_cursor(
            last_post.trending_score,
            last_post.created_at,
            last_post.id,
        )

    return {
        "results": [serialize_post(post) for post in page_posts],
        "next_cursor": next_cursor,
    }


def get_latest_feed(*, cursor=None, page_size=20):
    return _paginate_chronological(
        post_list_queryset(),
        cursor=cursor,
        page_size=page_size,
    )


def get_following_feed(user, *, cursor=None, page_size=20):
    followed_user_ids = Follow.objects.filter(follower=user).values("following_id")
    return _paginate_chronological(
        post_list_queryset().filter(author_id__in=followed_user_ids),
        cursor=cursor,
        page_size=page_size,
    )


def get_trending_feed(*, cursor=None, page_size=20):
    now = timezone.now()
    age_factor = Case(
        When(created_at__gte=now - timedelta(days=1), then=Value(1.0)),
        When(created_at__gte=now - timedelta(days=7), then=Value(2.0)),
        default=Value(3.0),
        output_field=FloatField(),
    )
    engagement_score = ExpressionWrapper(
        F("like_count") * Value(3.0)
        + F("save_count") * Value(5.0)
        + F("comment_count") * Value(4.0)
        + F("copy_count") * Value(6.0)
        + F("view_count"),
        output_field=FloatField(),
    )
    queryset = (
        post_list_queryset()
        .filter(created_at__gte=now - timedelta(days=30))
        .annotate(
            trending_score=ExpressionWrapper(
                engagement_score / age_factor,
                output_field=FloatField(),
            ),
        )
    )
    return _paginate_trending(queryset, cursor=cursor, page_size=page_size)


def get_explore_data():
    return {
        "latest": get_latest_feed(page_size=6)["results"],
        "trending": get_trending_feed(page_size=6)["results"],
        "popular_categories": list(
            Category.objects.annotate(post_count=Count("posts"))
            .filter(post_count__gt=0)
            .order_by("-post_count", "name")
            .values("id", "name", "slug", "post_count")[:6],
        ),
        "popular_creators": list(
            get_user_model()
            .objects.annotate(post_count=Count("posts"))
            .filter(post_count__gt=0)
            .order_by("-post_count", "username")
            .values("id", "username", "display_name", "is_verified", "post_count")[:6],
        ),
    }
