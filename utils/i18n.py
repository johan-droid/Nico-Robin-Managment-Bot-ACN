from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import settings


class _SafeFormatDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


LOCALE_DIR = Path(__file__).resolve().parent.parent / "i18n"


@lru_cache(maxsize=16)
def load_locale(locale: str) -> dict[str, str]:
    path = LOCALE_DIR / f"{locale}.json"
    if not path.exists():
        path = LOCALE_DIR / "en.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def gettext(key: str, locale: str | None = None, **values: Any) -> str:
    active_locale = locale or settings.default_locale
    messages = load_locale(active_locale)
    template = messages.get(key) or load_locale("en").get(key) or key
    return template.format_map(_SafeFormatDict(values))
