"""Studio rules: what may be generated, how often, and where it is stored.

The view layer stays thin — it parses input, calls one of these functions and
turns the outcome into JSON.  Everything a second caller would need to agree
with (the quota windows, the prompt limits, how a download becomes a stored
file) lives here.
"""

from __future__ import annotations

import secrets
from datetime import timedelta
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.utils import timezone

from posts.models import Post
from posts.validation import validate_upload_file

from imagegen.client import GenerationError, ImageProvider, ProviderSettings
from imagegen.models import AIConfig, GeneratedImage

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is a hard dependency
    Image = None

# Generous on purpose: real community prompts run long (over a thousand
# characters is common), and the provider has its own limits.
MAX_PROMPT_LENGTH = 2000

# Account usage limits, as (key, window length, allowed generations).
# Windows are rolling, not calendar-based, so the allowance refills
# continuously instead of resetting at midnight.
QUOTA_WINDOWS = (
    ("day", timedelta(hours=24), 3),
    ("week", timedelta(days=7), 7),
    ("month", timedelta(days=30), 15),
)

_LONGEST_WINDOW = max(window for _, window, _ in QUOTA_WINDOWS)

# Formats the provider may hand back, mapped to a safe file extension.
_EXTENSIONS_BY_FORMAT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}

LIBRARY_LIMIT = 12


class PromptRejected(ValueError):
    """The prompt itself cannot be sent (empty, or too long)."""


class QuotaExceeded(RuntimeError):
    """The account has used up one of its rolling windows."""

    def __init__(self, window, limit, retry_after_seconds):
        self.window = window
        self.limit = limit
        self.retry_after_seconds = max(0, int(retry_after_seconds))
        super().__init__(f"The {window} limit of {limit} images has been reached.")


# ---------------------------------------------------------------------------
# Quota
# ---------------------------------------------------------------------------


def check_prompt(prompt) -> str:
    """Return the cleaned prompt, or raise ``PromptRejected``."""
    cleaned = " ".join(str(prompt or "").split())
    if not cleaned:
        raise PromptRejected("Write a prompt first.")
    if len(cleaned) > MAX_PROMPT_LENGTH:
        raise PromptRejected(f"Prompts are limited to {MAX_PROMPT_LENGTH} characters.")
    return cleaned


def quota_state(user, *, now=None) -> list[dict]:
    """Usage per rolling window, oldest-first, ready for a progress meter."""
    now = now or timezone.now()
    if user is None or not getattr(user, "is_authenticated", False):
        return []

    # One query for every counted attempt in the longest window, then bucket
    # in Python — cheaper and clearer than one COUNT per window.
    timestamps = list(
        GeneratedImage.objects.filter(
            user=user,
            created_at__gte=now - _LONGEST_WINDOW,
            status__in=GeneratedImage.COUNTED_STATUSES,
        ).values_list("created_at", flat=True)
    )

    state = []
    for key, window, limit in QUOTA_WINDOWS:
        cutoff = now - window
        used_in_window = [stamp for stamp in timestamps if stamp >= cutoff]
        used = len(used_in_window)
        resets_in = 0
        if used_in_window:
            oldest = min(used_in_window)
            resets_in = max(0, int(((oldest + window) - now).total_seconds()))
        state.append(
            {
                "key": key,
                "label_key": f"studio_quota_{key}",
                "used": used,
                "limit": limit,
                "remaining": max(0, limit - used),
                "percent": min(100, round(used * 100 / limit)) if limit else 0,
                "reset_in_seconds": resets_in,
            }
        )
    return state


def check_quota(user, *, now=None) -> QuotaExceeded | None:
    """The first exhausted window, or ``None`` when the account may generate."""
    now = now or timezone.now()
    for entry in quota_state(user, now=now):
        if entry["used"] >= entry["limit"]:
            return QuotaExceeded(entry["key"], entry["limit"], entry["reset_in_seconds"])
    return None


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate_image(user, prompt, *, size=None, source_post=None, provider_factory=None):
    """Generate one image for *user* and store it.

    Records the attempt before calling the provider so a crash mid-request
    still leaves a visible, counted row.  Raises ``PromptRejected``,
    ``QuotaExceeded`` or ``GenerationError``.
    """
    cleaned = check_prompt(prompt)

    exceeded = check_quota(user)
    if exceeded:
        raise exceeded

    config = AIConfig.load()
    if not config.is_ready:
        raise GenerationError(
            "Image generation is turned off right now. Try again once an admin enables it."
        )

    record = GeneratedImage.objects.create(
        user=user,
        prompt=cleaned,
        source_post=source_post,
        provider_model=config.model,
        status=GeneratedImage.Status.PENDING,
    )

    # Resolved at call time, not bound as a default, so the provider is
    # swappable (tests inject one; nothing reaches for the network).
    factory = provider_factory or ImageProvider
    provider = factory(ProviderSettings.from_config(config))
    try:
        payload = provider.generate(cleaned, size or config.image_size)
        _store_image(record, payload)
    except GenerationError as exc:
        _mark_failed(record, str(exc))
        raise
    except Exception as exc:  # unexpected provider-adapter bug
        _mark_failed(record, "Something went wrong while generating this image.")
        raise GenerationError("Something went wrong while generating this image.") from exc

    return record


def _mark_failed(record, message):
    record.status = GeneratedImage.Status.FAILED
    record.error = message
    record.finished_at = timezone.now()
    record.save(update_fields=["status", "error", "finished_at"])


def _store_image(record, payload):
    """Validate the provider's bytes and attach them to the record."""
    extension = _sniff_extension(payload)
    name = f"generation-{record.pk}-{secrets.token_hex(4)}.{extension}"
    file = ContentFile(payload, name=name)

    # The same rules as a user upload: extension, size cap, magic bytes and a
    # full Pillow re-decode.  A "trusted" provider is still an HTTP endpoint.
    try:
        validate_upload_file(file, "image")
    except ValidationError as exc:
        raise GenerationError("The provider returned a file that is not a valid image.") from exc

    record.image.save(name, ContentFile(payload), save=False)
    record.status = GeneratedImage.Status.READY
    record.finished_at = timezone.now()
    record.save(update_fields=["image", "status", "finished_at"])


def _sniff_extension(payload) -> str:
    """Pick a safe extension from the real decoded format, never a guess."""
    if Image is None:  # pragma: no cover - Pillow is a hard dependency
        raise GenerationError("The provider returned an unreadable image.")
    try:
        with Image.open(BytesIO(payload)) as image:
            image_format = (image.format or "").upper()
    except Exception as exc:
        raise GenerationError("The provider returned an unreadable image.") from exc

    extension = _EXTENSIONS_BY_FORMAT.get(image_format)
    if not extension:
        raise GenerationError("The provider returned an unsupported image format.")
    return extension


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------


def serialize_generation(record, *, label=None) -> dict:
    """The JSON shape the studio's JS renders after a generate call."""
    return {
        "id": record.pk,
        "prompt": record.prompt,
        "image": record.image.url if record.image else None,
        "status": record.status,
        "error": record.error,
        "provider_model": record.provider_model,
        "created_at": record.created_at.isoformat(),
        "label": label or _format_timestamp(record.created_at),
        "source_post_id": record.source_post_id,
    }


def recent_generations(user, limit=12):
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    records = GeneratedImage.objects.filter(user=user).select_related("source_post")[:limit]
    return [serialize_generation(record) for record in records]


def _format_timestamp(value):
    local = timezone.localtime(value)
    return f"{local:%Y-%m-%d %H:%M}"


def prompt_library(limit=LIBRARY_LIMIT):
    """Public prompts a user can copy from, best-provenanced first.

    Prompt posts are pure text; image posts carry the output that prompt
    produced.  Both are useful, and duplicates are collapsed so the same
    popular prompt does not fill the whole shelf.
    """
    queryset = (
        Post.objects.filter(~Q(prompt=""))
        .filter(
            Q(post_type=Post.PostType.PROMPT)
            | (Q(post_type=Post.PostType.IMAGE) & ~Q(image=""))
        )
        .select_related("author")
        .annotate(copy_count=Count("copy_events", distinct=True))
        .order_by("-copy_count", "-created_at")[: limit * 3]
    )

    library = []
    seen = set()
    for post in queryset:
        key = post.prompt.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        library.append(
            {
                "post_id": post.pk,
                "title": post.title,
                "prompt": post.prompt.strip(),
                "excerpt": _excerpt(post.prompt),
                "image": post.image.url if post.image else None,
                "ai_model": post.ai_model,
                "author": post.author.username,
                "copy_count": post.copy_count,
            }
        )
        if len(library) >= limit:
            break
    return library


def _excerpt(text, length=180):
    collapsed = " ".join(str(text or "").split())
    return collapsed if len(collapsed) <= length else collapsed[: length - 1].rstrip() + "…"
