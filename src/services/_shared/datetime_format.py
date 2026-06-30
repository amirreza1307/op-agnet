"""Shared date/time formatting for public v1 API responses.

v1 endpoints surface dates as ``"YYYY-MM-DD HH:MM:SS"`` strings in Tehran
local time (matching the Basalam passthrough fields like ``paid_at``), rather
than raw unix timestamps. Stored values are UTC unix epoch seconds.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Union
from zoneinfo import ZoneInfo

_TEHRAN = ZoneInfo("Asia/Tehran")
_FMT = "%Y-%m-%d %H:%M:%S"


def format_api_datetime(value: Union[int, float, datetime, None]) -> Optional[str]:
    """Format a unix timestamp or datetime as Tehran-local ``YYYY-MM-DD HH:MM:SS``.

    Returns ``None`` for ``None``/unparseable input. Naive datetimes are
    assumed UTC.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    else:
        try:
            dt = datetime.fromtimestamp(float(value), timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError):
            return None
    return dt.astimezone(_TEHRAN).strftime(_FMT)
