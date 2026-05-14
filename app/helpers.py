"""Cross-cutting helpers used by multiple routes."""
from __future__ import annotations

import statistics
from datetime import date, datetime
from typing import Iterable

from flask import current_app, request


def vault():
    """Shorthand for the singleton Vault attached to the current app."""
    return current_app.extensions["vault"]


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    # Accept ISO date or datetime.
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None


def today_iso() -> str:
    return date.today().isoformat()


def is_htmx() -> bool:
    return request.headers.get("HX-Request") == "true"


def percentile_stats(values: Iterable[float]) -> dict[str, float | None]:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return {"count": 0, "median": None, "p25": None, "p75": None, "min": None, "max": None}
    vals_sorted = sorted(vals)
    if len(vals_sorted) >= 4:
        quantiles = statistics.quantiles(vals_sorted, n=4)
        p25, p75 = quantiles[0], quantiles[2]
    else:
        p25, p75 = vals_sorted[0], vals_sorted[-1]
    return {
        "count": len(vals_sorted),
        "median": statistics.median(vals_sorted),
        "p25": p25,
        "p75": p75,
        "min": vals_sorted[0],
        "max": vals_sorted[-1],
    }


def coerce_int(value: str | None, default: int | None = None) -> int | None:
    try:
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def coerce_float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def coerce_bool(value) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if value in (1, "1", "true", "True", "on", "yes"):
        return 1
    return 0
