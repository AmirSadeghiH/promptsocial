"""JSON endpoints for the AI image studio.

Thin by design: parse, delegate to ``services``, map each domain failure onto
one machine-readable ``error_code`` (the client owns the wording, so the
message can switch language without a page reload).
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from posts.models import Post

from imagegen.client import GenerationError
from imagegen.services import (
    MAX_PROMPT_LENGTH,
    PromptRejected,
    QuotaExceeded,
    generate_image,
    quota_state,
    serialize_generation,
)


def _parse_json_body(request):
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _source_post(data):
    """The prompt-library post this generation was remixed from, if any."""
    raw_id = data.get("source_post_id")
    if isinstance(raw_id, str) and raw_id.isdigit():
        raw_id = int(raw_id)
    if not isinstance(raw_id, int):
        return None
    return Post.objects.filter(pk=raw_id).first()


@login_required
@csrf_exempt
@require_POST
def api_generate(request):
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error_code": "bad_request", "error": "Invalid JSON body."}, status=400)

    try:
        record = generate_image(
            request.user,
            data.get("prompt"),
            size=str(data.get("size") or "").strip() or None,
            source_post=_source_post(data),
        )
    except PromptRejected as exc:
        return JsonResponse(
            {
                "error_code": "invalid_prompt",
                "error": str(exc),
                "max_length": MAX_PROMPT_LENGTH,
            },
            status=400,
        )
    except QuotaExceeded as exc:
        return JsonResponse(
            {
                "error_code": "quota_exceeded",
                "window": exc.window,
                "limit": exc.limit,
                "retry_after_seconds": exc.retry_after_seconds,
                "error": str(exc),
                "quota": quota_state(request.user),
            },
            status=429,
        )
    except GenerationError as exc:
        return JsonResponse(
            {
                "error_code": "provider_error",
                "error": str(exc),
                "quota": quota_state(request.user),
            },
            status=502,
        )

    return JsonResponse(
        {
            "generation": serialize_generation(record),
            "quota": quota_state(request.user),
        },
        status=201,
    )
