"""Template filters for i18n string formatting."""

from django import template

register = template.Library()


@register.filter
def fmt(value, args):
    """Replace {query}/{n}-style placeholders in a UI string with a value."""
    text = str(value or "")
    return text.replace("{query}", str(args)).replace("{n}", str(args))


@register.filter
def file_url(value):
    """URL for a FileField/FieldFile, or a URL string passed straight through.

    Reads on an empty FileField raise ValueError. Plain ``{{ x }}`` output
    swallows that, but extra context inside an include tag does not — so
    touching ``field.url`` on a user with no avatar returned a 500 instead of
    falling back to the initial-letter avatar. Returning "" for "no file"
    fixes the whole class of bug at one place, and accepting a string keeps
    the API serializers (which already emit URLs) working unchanged.
    """
    if not value:
        return ""
    url = getattr(value, "url", None)
    if url is None:
        return str(value)
    try:
        return str(url)
    except (ValueError, AttributeError):
        return ""
