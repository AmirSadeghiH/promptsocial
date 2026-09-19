"""Context processor exposing language, direction, and UI strings."""

import json

from web.i18n_strings import LANG_COOKIE, STRINGS


def ui_prefs(request):
    lang = request.COOKIES.get(LANG_COOKIE)
    if lang not in STRINGS:
        lang = "en"
    return {
        "lang": lang,
        "dir": "rtl" if lang == "fa" else "ltr",
        "i18n": STRINGS[lang],
        "i18n_json": json.dumps(STRINGS),
    }
