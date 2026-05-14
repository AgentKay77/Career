"""Monthly review form + history."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query, query_one
from ..helpers import coerce_int


bp = Blueprint("review", __name__)


def _auto_counts(year: int, month: int) -> dict[str, int]:
    next_year = year + (1 if month == 12 else 0)
    next_month = 1 if month == 12 else month + 1
    range_start = f"{year:04d}-{month:02d}-01"
    range_end = f"{next_year:04d}-{next_month:02d}-01"
    return {
        "books_completed_count": (
            query_one(
                "SELECT COUNT(*) AS n FROM learning_items WHERE type='book' AND status='done' "
                "AND date_completed >= ? AND date_completed < ?",
                (range_start, range_end),
            )["n"]
        ),
        "actions_completed_count": (
            query_one(
                "SELECT COUNT(*) AS n FROM actions WHERE status='done' "
                "AND date_completed >= ? AND date_completed < ?",
                (range_start, range_end),
            )["n"]
        ),
        "contacts_added_count": (
            query_one(
                "SELECT COUNT(*) AS n FROM contacts WHERE created_at >= ? AND created_at < ?",
                (range_start, range_end),
            )["n"]
        ),
        "stories_polished_count": (
            query_one(
                "SELECT COUNT(*) AS n FROM project_stories WHERE readiness='polished' "
                "AND updated_at >= ? AND updated_at < ?",
                (range_start, range_end),
            )["n"]
        ),
    }


@bp.route("/")
@login_required
def current():
    today = date.today()
    year = coerce_int(request.args.get("year"), today.year) or today.year
    month = coerce_int(request.args.get("month"), today.month) or today.month
    row = query_one(
        "SELECT * FROM monthly_reviews WHERE year = ? AND month = ?", (year, month)
    )
    counts = _auto_counts(year, month)
    return render_template(
        "review/current.html", row=row, year=year, month=month, counts=counts
    )


@bp.route("/save", methods=["POST"])
@login_required
def save():
    year = coerce_int(request.form.get("year"), date.today().year) or date.today().year
    month = coerce_int(request.form.get("month"), date.today().month) or date.today().month
    counts = _auto_counts(year, month)
    fields = {
        "year": year,
        "month": month,
        "wins": request.form.get("wins") or "",
        "misses": request.form.get("misses") or "",
        "lessons": request.form.get("lessons") or "",
        "next_month_focus": request.form.get("next_month_focus") or "",
        "books_completed_count": counts["books_completed_count"],
        "actions_completed_count": counts["actions_completed_count"],
        "contacts_added_count": counts["contacts_added_count"],
        "stories_polished_count": counts["stories_polished_count"],
        "date_completed": date.today().isoformat(),
    }
    existing = query_one(
        "SELECT id FROM monthly_reviews WHERE year = ? AND month = ?", (year, month)
    )
    if existing:
        fields["id"] = existing["id"]
        execute(
            "UPDATE monthly_reviews SET wins=:wins, misses=:misses, lessons=:lessons, "
            "next_month_focus=:next_month_focus, "
            "books_completed_count=:books_completed_count, "
            "actions_completed_count=:actions_completed_count, "
            "contacts_added_count=:contacts_added_count, "
            "stories_polished_count=:stories_polished_count, "
            "date_completed=:date_completed WHERE id=:id",
            fields,
        )
    else:
        execute(
            "INSERT INTO monthly_reviews(year, month, wins, misses, lessons, "
            "next_month_focus, books_completed_count, actions_completed_count, "
            "contacts_added_count, stories_polished_count, date_completed) "
            "VALUES (:year, :month, :wins, :misses, :lessons, :next_month_focus, "
            ":books_completed_count, :actions_completed_count, :contacts_added_count, "
            ":stories_polished_count, :date_completed)",
            fields,
        )
    flash("Review saved.", "success")
    return redirect(url_for(".current", year=year, month=month))


@bp.route("/history")
@login_required
def history():
    rows = query("SELECT * FROM monthly_reviews ORDER BY year DESC, month DESC")
    return render_template("review/history.html", rows=rows)
