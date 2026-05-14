"""Companies CRUD."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query, query_one
from ..helpers import coerce_int

bp = Blueprint("companies", __name__)

STATUSES = (
    "researching",
    "watching",
    "applied",
    "interviewing",
    "offered",
    "accepted",
    "passed",
    "closed",
)
TYPES = ("prime", "contractor", "specialty", "newspace", "other")


@bp.route("/")
@login_required
def list_view():
    q = (request.args.get("q") or "").strip()
    status_filter = request.args.get("status") or ""
    type_filter = request.args.get("type") or ""
    sort = request.args.get("sort") or "priority"
    sort_col = {
        "name": "name",
        "priority": "priority, name",
        "status": "status, name",
        "type": "type, name",
        "updated": "updated_at DESC, name",
    }.get(sort, "priority, name")

    where, params = ["1=1"], []
    if status_filter:
        where.append("status = ?")
        params.append(status_filter)
    if type_filter:
        where.append("type = ?")
        params.append(type_filter)
    if q:
        # FTS5 match
        rows = query(
            f"""
            SELECT c.* FROM companies c
              JOIN companies_fts f ON f.rowid = c.id
             WHERE companies_fts MATCH ? AND {' AND '.join(where)}
             ORDER BY {sort_col}
            """,
            (q + "*", *params),
        )
    else:
        rows = query(
            f"SELECT * FROM companies WHERE {' AND '.join(where)} ORDER BY {sort_col}",
            params,
        )

    return render_template(
        "companies/list.html",
        rows=rows,
        q=q,
        status_filter=status_filter,
        type_filter=type_filter,
        sort=sort,
        statuses=STATUSES,
        types=TYPES,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        _save(None)
        flash("Company added.", "success")
        return redirect(url_for(".list_view"))
    return render_template(
        "companies/form.html", row=None, statuses=STATUSES, types=TYPES
    )


@bp.route("/<int:cid>")
@login_required
def detail(cid: int):
    row = query_one("SELECT * FROM companies WHERE id = ?", (cid,))
    if row is None:
        abort(404)
    contacts = query(
        "SELECT id, name, role, warmth, last_contact_date "
        "FROM contacts WHERE company_id = ? ORDER BY name",
        (cid,),
    )
    openings = query(
        "SELECT * FROM company_openings WHERE company_id = ? ORDER BY found_date DESC",
        (cid,),
    )
    return render_template(
        "companies/detail.html", row=row, contacts=contacts, openings=openings
    )


@bp.route("/<int:cid>/edit", methods=["GET", "POST"])
@login_required
def edit(cid: int):
    row = query_one("SELECT * FROM companies WHERE id = ?", (cid,))
    if row is None:
        abort(404)
    if request.method == "POST":
        _save(cid)
        flash("Company updated.", "success")
        return redirect(url_for(".detail", cid=cid))
    return render_template(
        "companies/form.html", row=row, statuses=STATUSES, types=TYPES
    )


@bp.route("/<int:cid>/delete", methods=["POST"])
@login_required
def delete(cid: int):
    execute("DELETE FROM companies WHERE id = ?", (cid,))
    flash("Company deleted.", "info")
    return redirect(url_for(".list_view"))


@bp.route("/<int:cid>/openings/new", methods=["POST"])
@login_required
def new_opening(cid: int):
    if query_one("SELECT id FROM companies WHERE id = ?", (cid,)) is None:
        abort(404)
    execute(
        "INSERT INTO company_openings(company_id, title, url, posted_date, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            cid,
            (request.form.get("title") or "").strip() or "Untitled opening",
            request.form.get("url") or "",
            request.form.get("posted_date") or None,
            request.form.get("notes") or "",
        ),
    )
    flash("Opening added.", "success")
    return redirect(url_for(".detail", cid=cid))


def _save(cid: int | None) -> None:
    fields = {
        "name": (request.form.get("name") or "").strip(),
        "location": request.form.get("location") or "",
        "type": request.form.get("type") or "other",
        "website": request.form.get("website") or "",
        "priority": coerce_int(request.form.get("priority"), 2) or 2,
        "status": request.form.get("status") or "researching",
        "notes": request.form.get("notes") or "",
    }
    if fields["type"] not in TYPES:
        fields["type"] = "other"
    if fields["status"] not in STATUSES:
        fields["status"] = "researching"
    if not fields["name"]:
        flash("Name is required.", "danger")
        return
    if cid is None:
        execute(
            "INSERT INTO companies(name, location, type, website, priority, status, notes) "
            "VALUES (:name, :location, :type, :website, :priority, :status, :notes)",
            fields,
        )
    else:
        fields["id"] = cid
        execute(
            "UPDATE companies SET name=:name, location=:location, type=:type, "
            "website=:website, priority=:priority, status=:status, notes=:notes "
            "WHERE id=:id",
            fields,
        )
