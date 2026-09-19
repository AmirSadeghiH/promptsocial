"""Template filters for i18n string formatting."""

from django import template

register = template.Library()


@register.filter
def fmt(value, args):
    """Replace {query}/{n}-style placeholders in a UI string with a value."""
    text = str(value or "")
    return text.replace("{query}", str(args)).replace("{n}", str(args))
