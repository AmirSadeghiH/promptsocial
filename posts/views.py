from django.http import JsonResponse

from posts.services import (
    InvalidCursor,
    get_explore_data,
    get_following_feed,
    get_latest_feed,
    get_trending_feed,
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

    try:
        if user is None:
            page = feed_function(cursor=cursor, page_size=page_size)
        else:
            page = feed_function(user, cursor=cursor, page_size=page_size)
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
    return JsonResponse(get_explore_data())
