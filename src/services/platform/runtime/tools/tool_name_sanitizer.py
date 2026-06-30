from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Optional

from setup.translator import trans

_ALLOWED_TOOL_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_.:-]+")

# A small Persian → latin transliteration table. Covers the most common
# letters. For characters not in the table we fall through to a stable
# hash suffix so the result remains unique without leaking codepoint
# numerics like ``1576_1575`` (F-19).
_PERSIAN_TRANSLITERATION: dict[str, str] = {
    "ا": "a", "آ": "a", "أ": "a", "إ": "e", "ء": "",
    "ب": "b", "پ": "p", "ت": "t", "ث": "s",
    "ج": "j", "چ": "ch", "ح": "h", "خ": "kh",
    "د": "d", "ذ": "z", "ر": "r", "ز": "z", "ژ": "zh",
    "س": "s", "ش": "sh", "ص": "s", "ض": "z",
    "ط": "t", "ظ": "z", "ع": "a", "غ": "gh",
    "ف": "f", "ق": "gh", "ک": "k", "ك": "k", "گ": "g",
    "ل": "l", "م": "m", "ن": "n",
    "و": "v", "ه": "h", "ة": "h",
    "ی": "y", "ي": "y", "ى": "y",
    "ئ": "y", "ؤ": "v",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
}


def _transliterate_persian(value: str) -> str:
    parts: list[str] = []
    for ch in value:
        if ch.isspace() or ch in "-_":
            parts.append("_")
            continue
        ascii_ch = _PERSIAN_TRANSLITERATION.get(ch)
        if ascii_ch is not None:
            parts.append(ascii_ch)
    text = "".join(parts)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def sanitize_provider_tool_name(
    *candidates: Optional[object],
    fallback: str = "tool",
    max_length: int = 128,
) -> str:
    for candidate in candidates:
        sanitized = _sanitize_single_name(candidate, max_length=max_length)
        if sanitized:
            return sanitized

    sanitized_fallback = _sanitize_single_name(fallback, max_length=max_length)
    if sanitized_fallback:
        return sanitized_fallback
    return "tool"


def build_tool_description(
    description: Optional[str],
    *,
    display_name: Optional[str] = None,
    provider_name: Optional[str] = None,
) -> str:
    base = str(description or "").strip()
    display = str(display_name or "").strip()
    provider = str(provider_name or "").strip()

    if not display or not provider or display == provider:
        return base

    extra = trans("ui.platform.tools.display_name", display=display)
    if not base:
        return extra
    return f"{base}\n\n{extra}"


def sanitize_tool_name_prefix(
    *candidates: Optional[object],
    fallback: str = "mcp",
    max_length: int = 48,
) -> str:
    return sanitize_provider_tool_name(*candidates, fallback=fallback, max_length=max_length)


def _sanitize_single_name(value: Optional[object], *, max_length: int) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")

    if not normalized.strip():
        transliterated = _transliterate_persian(raw)
        digest = hashlib.blake2b(raw.encode("utf-8"), digest_size=4).hexdigest()
        normalized = f"{transliterated}_{digest}" if transliterated else f"tool_{digest}"

    text = _ALLOWED_TOOL_NAME_PATTERN.sub("_", normalized)
    text = re.sub(r"_+", "_", text).strip("_.:-")
    if not text:
        return ""

    if not re.match(r"[A-Za-z_]", text[0]):
        text = f"tool_{text}"

    return text[:max_length].rstrip("_.:-") or "tool"
