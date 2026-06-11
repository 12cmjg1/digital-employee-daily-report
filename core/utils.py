from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def today_string(timezone: str = "Asia/Shanghai") -> str:
    return datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d")


def now_string(timezone: str = "Asia/Shanghai") -> str:
    return datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d %H:%M:%S %Z")


def clamp(value: int, low: int = 1, high: int = 5) -> int:
    return max(low, min(high, value))


def source_link(title: str, url: str | None) -> str:
    return f"[{title}]({url})" if url else title
