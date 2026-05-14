"""Learning items — three-column Queued/Reading/Done."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query, query_one
from ..helpers import coerce_int, is_htmx, parse_date, today_iso

bp = Blueprint("learning", __name__)

TYPES = ("book", "chapter", "article", "paper", "video", "course", "skill", "reference")
STATUSES = ("queued", "reading", "done", "dropped")


@bp.route("/")
@login_required
def list_view():
    q = (request.args.get("q") or "").strip()
    type_filter = request.args.get("type") or ""

    where, params = ["1=1"], []
    if type_filter in TYPES:
        where.append("type = ?")
        params.append(type_filter)

    if q:
        rows = query(
            f"""
            SELECT l.* FROM learning_items l
              JOIN learning_fts f ON f.rowid = l.id
             WHERE learning_fts MATCH ? AND {' AND '.join(where)}
             ORDER BY priority, title
            """,
            (q + "*", *params),
        )
    else:
        rows = query(
            f"SELECT * FROM learning_items WHERE {' AND '.join(where)} "
            f"ORDER BY priority, title",
            params,
        )

    columns = {"queued": [], "reading": [], "done": [], "dropped": []}
    for r in rows:
        columns[r["status"]].append(r)

    return render_template(
        "learning/list.html",
        columns=columns,
        q=q,
        type_filter=type_filter,
        types=TYPES,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        _save(None)
        flash("Learning item added.", "success")
        return redirect(url_for(".list_view"))
    return render_template("learning/form.html", row=None, types=TYPES, statuses=STATUSES)


@bp.route("/<int:lid>/edit", methods=["GET", "POST"])
@login_required
def edit(lid: int):
    row = query_one("SELECT * FROM learning_items WHERE id = ?", (lid,))
    if row is None:
        abort(404)
    if request.method == "POST":
        _save(lid)
        flash("Updated.", "success")
        return redirect(url_for(".list_view"))
    return render_template("learning/form.html", row=row, types=TYPES, statuses=STATUSES)


@bp.route("/<int:lid>/delete", methods=["POST"])
@login_required
def delete(lid: int):
    execute("DELETE FROM learning_items WHERE id = ?", (lid,))
    flash("Deleted.", "info")
    return redirect(url_for(".list_view"))


@bp.route("/<int:lid>/status", methods=["POST"])
@login_required
def change_status(lid: int):
    new_status = request.form.get("status") or ""
    if new_status not in STATUSES:
        abort(400)
    row = query_one("SELECT status, date_started, date_completed FROM learning_items WHERE id = ?", (lid,))
    if row is None:
        abort(404)
    date_started = row["date_started"]
    date_completed = row["date_completed"]
    if new_status == "reading" and not date_started:
        date_started = today_iso()
    if new_status == "done" and not date_completed:
        date_completed = today_iso()
        if not date_started:
            date_started = today_iso()
    execute(
        "UPDATE learning_items SET status = ?, date_started = ?, date_completed = ? WHERE id = ?",
        (new_status, date_started, date_completed, lid),
    )
    if is_htmx():
        # Return updated row partial.
        row = query_one("SELECT * FROM learning_items WHERE id = ?", (lid,))
        return render_template("partials/learning_row.html", row=row)
    return redirect(url_for(".list_view"))


def _save(lid: int | None) -> None:
    t = request.form.get("type") or "book"
    if t not in TYPES:
        t = "book"
    status = request.form.get("status") or "queued"
    if status not in STATUSES:
        status = "queued"
    fields = {
        "type": t,
        "title": (request.form.get("title") or "").strip() or "(untitled)",
        "author": request.form.get("author") or "",
        "source": request.form.get("source") or "",
        "status": status,
        "priority": coerce_int(request.form.get("priority"), 2) or 2,
        "notes_path": request.form.get("notes_path") or "",
        "date_started": parse_date(request.form.get("date_started")),
        "date_completed": parse_date(request.form.get("date_completed")),
        "rating": coerce_int(request.form.get("rating")),
        "tags": request.form.get("tags") or "",
        "key_takeaways": request.form.get("key_takeaways") or "",
    }
    if lid is None:
        execute(
            "INSERT INTO learning_items(type, title, author, source, status, priority, "
            "notes_path, date_started, date_completed, rating, tags, key_takeaways) "
            "VALUES (:type, :title, :author, :source, :status, :priority, :notes_path, "
            ":date_started, :date_completed, :rating, :tags, :key_takeaways)",
            fields,
        )
    else:
        fields["id"] = lid
        execute(
            "UPDATE learning_items SET type=:type, title=:title, author=:author, "
            "source=:source, status=:status, priority=:priority, notes_path=:notes_path, "
            "date_started=:date_started, date_completed=:date_completed, rating=:rating, "
            "tags=:tags, key_takeaways=:key_takeaways WHERE id=:id",
            fields,
        )
