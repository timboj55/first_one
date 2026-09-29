"""Time rules: business hours, quiet hours, call window, busy mode, deferral of touches.

All decisions are made in a specific IANA timezone. Leads are contacted in *their* timezone
when GHL knows it (contact.timezone), otherwise in the practice timezone.
"""

from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def tz(name: str | None, fallback: str) -> ZoneInfo:
    for candidate in (name, fallback, "UTC"):
        if candidate:
            try:
                return ZoneInfo(candidate)
            except Exception:  # unknown tz name from GHL
                continue
    return ZoneInfo("UTC")


def _parse_hhmm(s: str) -> dtime:
    h, m = s.split(":")
    return dtime(int(h), int(m))


def in_window(now: datetime, start: str, end: str) -> bool:
    """True if now's wall-clock time is inside [start, end). Handles windows that cross midnight."""
    t = now.time().replace(second=0, microsecond=0)
    a, b = _parse_hhmm(start), _parse_hhmm(end)
    if a <= b:
        return a <= t < b
    return t >= a or t < b  # crosses midnight


def is_business_hours(now: datetime, business: dict, holidays: list[str]) -> bool:
    if now.strftime("%Y-%m-%d") in holidays:
        return False
    window = business.get(DAYS[now.weekday()])
    if not window:
        return False
    return in_window(now, window[0], window[1])


def is_quiet(now: datetime, quiet: list[str]) -> bool:
    return in_window(now, quiet[0], quiet[1])


def next_allowed(now: datetime, quiet: list[str], window: list[str] | None = None) -> datetime:
    """Earliest time >= now that is outside quiet hours and (if given) inside the call window."""
    cur = now.replace(second=0, microsecond=0)
    for _ in range(0, 60 * 48):  # scan up to 48h in 1-minute steps (cheap, exact)
        ok = not is_quiet(cur, quiet)
        if ok and window:
            ok = in_window(cur, window[0], window[1])
        if ok:
            return cur if cur > now else now
        cur += timedelta(minutes=1)
    return cur


def defer_to_allowed(when: datetime, quiet: list[str], window: list[str] | None = None) -> datetime:
    return next_allowed(when, quiet, window)


class Clock:
    """Injectable clock so tests can freeze time."""

    def __init__(self, fixed: Optional[datetime] = None):
        self.fixed = fixed

    def now(self, zone: ZoneInfo) -> datetime:
        if self.fixed is not None:
            return self.fixed.astimezone(zone)
        return datetime.now(zone)


def describe_hours(business: dict) -> str:
    parts = []
    for d in DAYS:
        w = business.get(d)
        parts.append(f"{d.title()} {w[0]}-{w[1]}" if w else f"{d.title()} closed")
    return ", ".join(parts)
