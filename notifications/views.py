from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from notifications.models import Notification
from notifications.services import serialize_notification, unread_count


def _method_not_allowed():
    return JsonResponse({"error": "Method not allowed."}, status=405)


def _login_required_json(view):
    """login_required that answers 401 JSON instead of redirecting."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


@_login_required_json
def notification_list(request):
    if request.method != "GET":
        return _method_not_allowed()

    try:
        page_size = min(max(int(request.GET.get("page_size", "30")), 1), 50)
    except (TypeError, ValueError):
        page_size = 30

    queryset = Notification.objects.filter(recipient=request.user).select_related(
        "actor", "post", "comment"
    )
    unread_only = request.GET.get("unread") in {"1", "true", "yes"}
    if unread_only:
        queryset = queryset.filter(is_read=False)

    notifications = list(queryset[:page_size])
    return JsonResponse(
        {
            "results": [serialize_notification(n) for n in notifications],
            "unread_count": unread_count(request.user),
        }
    )


@_login_required_json
@require_POST
def mark_all_read(request):
    updated = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({"marked_read": updated, "unread_count": 0})


@_login_required_json
@require_POST
def mark_read(request, notification_id):
    updated = Notification.objects.filter(
        Q(recipient=request.user),
        pk=notification_id,
        is_read=False,
    ).update(is_read=True)
    if not updated:
        exists = Notification.objects.filter(recipient=request.user, pk=notification_id).exists()
        if not exists:
            return JsonResponse({"error": "Notification not found."}, status=404)
    return JsonResponse({"id": notification_id, "is_read": True})
