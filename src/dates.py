"""Normalize Facebook's human date strings to an approximate ISO date.

FB shows recent posts relatively ("3h", "2d", "5 weeks ago") and older posts
absolutely ("7 May", "December 3, 2024"). For a cutoff boundary an approximate
date is plenty — older posts (near any sensible cutoff) carry absolute dates and
normalize precisely.
"""
from __future__ import annotations

import datetime as _dt
import re

_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}
_MONTHS.update({m[:3].lower(): i for m, i in list(_MONTHS.items())})

_UNIT_DAYS = {"h": 0, "hr": 0, "hour": 0, "m": 0, "min": 0, "minute": 0,
              "d": 1, "day": 1, "w": 7, "wk": 7, "week": 7,
              "mo": 30, "month": 30, "y": 365, "yr": 365, "year": 365}


def to_iso(date_str: str | None, now: _dt.date | None = None) -> str | None:
    """Return YYYY-MM-DD (approx) for a FB date label, or None if unparseable."""
    if not date_str:
        return None
    s = date_str.strip().lower()
    today = now or _dt.date.today()

    if s in ("just now", "yesterday"):
        return (today - _dt.timedelta(days=1 if s == "yesterday" else 0)).isoformat()

    # relative: "3h", "2 d", "5 weeks ago", "1 month ago"
    m = re.match(r"^(\d+)\s*([a-z]+)", s)
    if m and "ago" in s or (m and re.fullmatch(r"\d+\s*[a-z]+", s)):
        n = int(m.group(1))
        unit = m.group(2).rstrip("s")
        if unit in _UNIT_DAYS:
            return (today - _dt.timedelta(days=n * _UNIT_DAYS[unit])).isoformat()

    # absolute with year: "december 3, 2024" / "3 december 2024" / "7 may 2024"
    m = re.search(r"([a-z]+)\s+(\d{1,2}),?\s+(\d{4})", s)
    if m and m.group(1) in _MONTHS:
        return _dt.date(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2))).isoformat()
    m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", s)
    if m and m.group(2) in _MONTHS:
        return _dt.date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1))).isoformat()

    # absolute, no year: "7 may" / "may 7"  -> assume most recent past occurrence
    m = re.search(r"([a-z]+)\s+(\d{1,2})", s)
    if m and m.group(1) in _MONTHS:
        mo, day = _MONTHS[m.group(1)], int(m.group(2))
    else:
        m = re.search(r"(\d{1,2})\s+([a-z]+)", s)
        if m and m.group(2) in _MONTHS:
            mo, day = _MONTHS[m.group(2)], int(m.group(1))
        else:
            return None
    year = today.year
    try:
        d = _dt.date(year, mo, day)
    except ValueError:
        return None
    if d > today:                       # "7 May" but May is in the future -> last year
        d = _dt.date(year - 1, mo, day)
    return d.isoformat()
