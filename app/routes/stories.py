"""Project stories (S/T/A/R/Technical) + practice mode."""
from __future__ import annotations

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query, query_one
from ..helpers import coerce_int, today_iso

bp = Blueprint("stories", __name__)

READINESS = ("draft", "usable", "polished")


@bp.route("/")
@login_required
def list_view():
    q = (request.args.get("q") or "").strip()
    readiness = request.args.get("readiness") or ""
    where, params = ["1=1"], []
    if readiness in READINESS:
        where.append("readiness = ?")
        params.append(readiness)

    if q:
        rows = query(
            f"""
            SELECT s.* FROM project_stories s
              JOIN stories_fts f ON f.rowid = s.id
             WHERE stories_fts MATCH ? AND {' AND '.join(where)}
             ORDER BY readiness DESC, s.title
            """,
            (q + "*", *params),
        )
    else:
        rows = query(
            f"SELECT * FROM project_stories WHERE {' AND '.join(where)} "
            f"ORDER BY CASE readiness WHEN 'polished' THEN 1 WHEN 'usable' THEN 2 ELSE 3 END, title",
            params,
        )
    return render_template(
        "stories/list.html", rows=rows, q=q, readiness=readiness, readiness_levels=READINESS
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        sid = _save(None)
        flash("Story created.", "success")
        return redirect(url_for(".detail", sid=sid))
    return render_template("stories/form.html", row=None, readiness_levels=READINESS)


@bp.route("/<int:sid>")
@login_required
def detail(sid: int):
    row = query_one("SELECT * FROM project_stories WHERE id = ?", (sid,))
    if row is None:
        abort(404)
    return render_template("stories/detail.html", row=row)


@bp.route("/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def edit(sid: int):
    row = query_one("SELECT * FROM project_stories WHERE id = ?", (sid,))
    if row is None:
        abort(404)
    if request.method == "POST":
        _save(sid)
        flash("Story updated.", "success")
        return redirect(url_for(".detail", sid=sid))
    return render_template("stories/form.html", row=row, readiness_levels=READINESS)


@bp.route("/<int:sid>/delete", methods=["POST"])
@login_required
def delete(sid: int):
    execute("DELETE FROM project_stories WHERE id = ?", (sid,))
    flash("Story deleted.", "info")
    return redirect(url_for(".list_view"))


@bp.route("/<int:sid>/practice")
@login_required
def practice(sid: int):
    row = query_one("SELECT * FROM project_stories WHERE id = ?", (sid,))
    if row is None:
        abort(404)
    return render_template("stories/practice.html", row=row)


@bp.route("/<int:sid>/practice/log", methods=["POST"])
@login_required
def practice_log(sid: int):
    if query_one("SELECT id FROM project_stories WHERE id = ?", (sid,)) is None:
        abort(404)
    execute(
        "UPDATE project_stories SET times_practiced = times_practiced + 1, "
        "last_practiced = ? WHERE id = ?",
        (today_iso(), sid),
    )
    return jsonify({"ok": True})


@bp.route("/random-practice")
@login_required
def random_practice():
    row = query_one(
        "SELECT id FROM project_stories WHERE readiness IN ('usable','polished') "
        "ORDER BY RANDOM() LIMIT 1"
    )
    if row is None:
        # Fall back to any draft.
        row = query_one("SELECT id FROM project_stories ORDER BY RANDOM() LIMIT 1")
    if row is None:
        flash("No stories to practice yet — add one first.", "warning")
        return redirect(url_for(".list_view"))
    return redirect(url_for(".practice", sid=row["id"]))


def _save(sid: int | None) -> int:
    readiness = request.form.get("readiness") or "draft"
    if readiness not in READINESS:
        readiness = "draft"
    fields = {
        "title": (request.form.get("title") or "").strip() or "(untitled)",
        "problem_domain": request.form.get("problem_domain") or "",
        "situation": request.form.get("situation") or "",
        "task": request.form.get("task") or "",
        "action": request.form.get("action") or "",
        "result": request.form.get("result") or "",
        "technical": request.form.get("technical") or "",
        "keywords": request.form.get("keywords") or "",
        "readiness": readiness,
    }
    if sid is None:
        cur = execute(
            "INSERT INTO project_stories(title, problem_domain, situation, task, action, "
            "result, technical, keywords, readiness) VALUES (:title, :problem_domain, "
            ":situation, :task, :action, :result, :technical, :keywords, :readiness)",
            fields,
        )
        return cur.lastrowid
    fields["id"] = sid
    execute(
        "UPDATE project_stories SET title=:title, problem_domain=:problem_domain, "
        "situation=:situation, task=:task, action=:action, result=:result, "
        "technical=:technical, keywords=:keywords, readiness=:readiness WHERE id=:id",
        fields,
    )
    return sid
