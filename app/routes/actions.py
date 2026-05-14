"""Actions — Kanban board + calendar view + quick add."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query, query_one
from ..helpers import is_htmx, parse_date, today_iso

bp = Blueprint("actions", __name__)

CATEGORIES = (
    "clearance",
    "membership",
    "network",
    "learning",
    "resume",
    "interview",
    "salary_research",
    "admin",
    "technical",
)
PRIORITIES = ("high", "medium", "low")
STATUSES = ("pending", "in_progress", "done", "skipped")


@bp.route("/")
@login_required
def board():
    category = request.args.get("category") or ""
    where, params = ["1=1"], []
    if category in CATEGORIES:
        where.append("category = ?")
        params.append(category)
    rows = query(
        f"SELECT * FROM actions WHERE {' AND '.join(where)} "
        f"ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
        f"target_date IS NULL, target_date, id",
        params,
    )
    columns = {s: [] for s in STATUSES}
    for r in rows:
        columns[r["status"]].append(r)
    return render_template(
        "actions/board.html",
        columns=columns,
        category=category,
        categories=CATEGORIES,
        priorities=PRIORITIES,
        statuses=STATUSES,
    )


@bp.route("/calendar")
@login_required
def calendar():
    start = date.today()
    days = [start + timedelta(days=i) for i in range(28)]
    rows = query(
        "SELECT * FROM actions WHERE status IN ('pending','in_progress') "
        "AND target_date IS NOT NULL AND date(target_date) BETWEEN date('now') AND date('now','+27 days') "
        "ORDER BY target_date, priority"
    )
    by_day = defaultdict(list)
    for r in rows:
        by_day[r["target_date"]].append(r)
    return render_template("actions/board.html", calendar_days=days, by_day=by_day,
                           calendar_mode=True,
                           columns={s: [] for s in STATUSES},
                           categories=CATEGORIES, priorities=PRIORITIES,
                           statuses=STATUSES, category="")


@bp.route("/quick-add", methods=["POST"])
@login_required
def quick_add():
    title = (request.form.get("title") or "").strip()
    if not title:
        return ("", 400) if is_htmx() else redirect(url_for(".board"))
    category = request.form.get("category") or "admin"
    if category not in CATEGORIES:
        category = "admin"
    priority = request.form.get("priority") or "medium"
    if priority not in PRIORITIES:
        priority = "medium"
    cur = execute(
        "INSERT INTO actions(title, category, priority, status) VALUES (?, ?, ?, 'pending')",
        (title, category, priority),
    )
    if is_htmx():
        row = query_one("SELECT * FROM actions WHERE id = ?", (cur.lastrowid,))
        return render_template("partials/action_card.html", row=row)
    return redirect(url_for(".board"))


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        _save(None)
        flash("Action added.", "success")
        return redirect(url_for(".board"))
    return render_template(
        "actions/form.html", row=None, categories=CATEGORIES, priorities=PRIORITIES,
        statuses=STATUSES,
    )


@bp.route("/<int:aid>/edit", methods=["GET", "POST"])
@login_required
def edit(aid: int):
    row = query_one("SELECT * FROM actions WHERE id = ?", (aid,))
    if row is None:
        abort(404)
    if request.method == "POST":
        _save(aid)
        flash("Updated.", "success")
        return redirect(url_for(".board"))
    return render_template(
        "actions/form.html", row=row, categories=CATEGORIES, priorities=PRIORITIES,
        statuses=STATUSES,
    )


@bp.route("/<int:aid>/delete", methods=["POST"])
@login_required
def delete(aid: int):
    execute("DELETE FROM actions WHERE id = ?", (aid,))
    flash("Deleted.", "info")
    return redirect(url_for(".board"))


@bp.route("/<int:aid>/status", methods=["POST"])
@login_required
def change_status(aid: int):
    new_status = request.form.get("status") or ""
    if new_status not in STATUSES:
        abort(400)
    completed = today_iso() if new_status == "done" else None
    execute(
        "UPDATE actions SET status = ?, date_completed = COALESCE(?, "
        "  CASE WHEN ? = 'done' THEN date_completed ELSE NULL END) "
        "WHERE id = ?",
        (new_status, completed, new_status, aid),
    )
    if is_htmx():
        row = query_one("SELECT * FROM actions WHERE id = ?", (aid,))
        return render_template("partials/action_card.html", row=row)
    return redirect(url_for(".board"))


def _save(aid: int | None) -> None:
    cat = request.form.get("category") or "admin"
    if cat not in CATEGORIES:
        cat = "admin"
    pri = request.form.get("priority") or "medium"
    if pri not in PRIORITIES:
        pri = "medium"
    status = request.form.get("status") or "pending"
    if status not in STATUSES:
        status = "pending"
    fields = {
        "title": (request.form.get("title") or "").strip() or "(untitled)",
        "description": request.form.get("description") or "",
        "category": cat,
        "priority": pri,
        "target_date": parse_date(request.form.get("target_date")),
        "status": status,
        "date_completed": parse_date(request.form.get("date_completed")) or (
            today_iso() if status == "done" else None
        ),
        "completion_notes": request.form.get("completion_notes") or "",
    }
    if aid is None:
        execute(
            "INSERT INTO actions(title, description, category, priority, target_date, "
            "status, date_completed, completion_notes) VALUES (:title, :description, "
            ":category, :priority, :target_date, :status, :date_completed, :completion_notes)",
            fields,
        )
    else:
        fields["id"] = aid
        execute(
            "UPDATE actions SET title=:title, description=:description, category=:category, "
            "priority=:priority, target_date=:target_date, status=:status, "
            "date_completed=:date_completed, completion_notes=:completion_notes WHERE id=:id",
            fields,
        )
