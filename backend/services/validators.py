from __future__ import annotations

import re
from datetime import datetime
from typing import Any


IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"[0-9\-\+\(\) ]{7,20}")


def validate_ifsc(value: str | None) -> bool:
    if not value:
        return False
    s = str(value).strip().upper().replace(" ", "")
    return bool(IFSC_RE.match(s))


def validate_email(value: str | None) -> bool:
    if not value:
        return False
    return bool(EMAIL_RE.match(str(value).strip()))


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    # Try common formats
    formats = ["%b %d %Y", "%b %d, %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    # fallback: search for YYYY or dd MMM YYYY
    m = re.search(r"(\d{4})", s)
    if m:
        return m.group(1)  # best-effort
    return None


def normalize_currency(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value)
    s = s.replace(",", "").strip()
    m = re.search(r"-?[0-9]+(?:\.[0-9]+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"[^0-9+]", "", value)
    if len(digits) < 7:
        return None
    return digits
