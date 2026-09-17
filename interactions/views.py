from django.http import JsonResponse

from interactions.models import PostCopy, PostView
from posts.models import Post


def _get_post_or_error(post_id):
    try:
        return Post.objects.get(pk=post_id), None
    except Post.DoesNotExist:
        return None, JsonResponse({"error": "Post not found."}, status=404)


def _method_not_allowed():
    return JsonResponse({"error": "Method not allowed."}, status=405)


def record_view(request, post_id):
    if request.method != "POST":
        return _method_not_allowed()

    post, error_response = _get_post_or_error(post_id)
    if error_response:
        return error_response

    user = request.user if request.user.is_authenticated else None
    PostView.objects.create(post=post, user=user)
    return JsonResponse({"post_id": post.pk, "event": "view"}, status=201)


def record_copy(request, post_id):
    if request.method != "POST":
        return _method_not_allowed()
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    post, error_response = _get_post_or_error(post_id)
    if error_response:
        return error_response

    PostCopy.objects.create(post=post, user=request.user)
    return JsonResponse({"post_id": post.pk, "event": "copy"}, status=201)
