"""Contacts CRUD + interactions."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query, query_one
from ..helpers import coerce_int, parse_date, today_iso

bp = Blueprint("contacts", __name__)

CHANNELS = ("email", "linkedin", "call", "text", "in-person", "event", "other")


@bp.route("/")
@login_required
def list_view():
    q = (request.args.get("q") or "").strip()
    stale = request.args.get("stale") == "1"

    where, params = ["1=1"], []
    if stale:
        where.append("c.last_contact_date IS NOT NULL "
                     "AND date(c.last_contact_date) <= date('now','-60 days')")

    if q:
        rows = query(
            f"""
            SELECT c.*, co.name AS company_name
              FROM contacts c
              JOIN contacts_fts f ON f.rowid = c.id
              LEFT JOIN companies co ON co.id = c.company_id
             WHERE contacts_fts MATCH ? AND {' AND '.join(where)}
             ORDER BY c.name
            """,
            (q + "*", *params),
        )
    else:
        rows = query(
            f"""
            SELECT c.*, co.name AS company_name
              FROM contacts c
              LEFT JOIN companies co ON co.id = c.company_id
             WHERE {' AND '.join(where)}
             ORDER BY c.name
            """,
            params,
        )

    return render_template("contacts/list.html", rows=rows, q=q, stale=stale)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        _save(None)
        flash("Contact added.", "success")
        return redirect(url_for(".list_view"))
    companies = query("SELECT id, name FROM companies ORDER BY name")
    return render_template("contacts/form.html", row=None, companies=companies)


@bp.route("/<int:cid>")
@login_required
def detail(cid: int):
    row = query_one(
        "SELECT c.*, co.name AS company_name FROM contacts c "
        "LEFT JOIN companies co ON co.id = c.company_id WHERE c.id = ?",
        (cid,),
    )
    if row is None:
        abort(404)
    history = query(
        "SELECT * FROM interactions WHERE contact_id = ? ORDER BY date DESC, id DESC",
        (cid,),
    )
    return render_template(
        "contacts/detail.html", row=row, history=history, channels=CHANNELS
    )


@bp.route("/<int:cid>/edit", methods=["GET", "POST"])
@login_required
def edit(cid: int):
    row = query_one("SELECT * FROM contacts WHERE id = ?", (cid,))
    if row is None:
        abort(404)
    if request.method == "POST":
        _save(cid)
        flash("Contact updated.", "success")
        return redirect(url_for(".detail", cid=cid))
    companies = query("SELECT id, name FROM companies ORDER BY name")
    return render_template("contacts/form.html", row=row, companies=companies)


@bp.route("/<int:cid>/delete", methods=["POST"])
@login_required
def delete(cid: int):
    execute("DELETE FROM contacts WHERE id = ?", (cid,))
    flash("Contact deleted.", "info")
    return redirect(url_for(".list_view"))


@bp.route("/<int:cid>/interactions/new", methods=["POST"])
@login_required
def add_interaction(cid: int):
    if query_one("SELECT id FROM contacts WHERE id = ?", (cid,)) is None:
        abort(404)
    when = parse_date(request.form.get("date")) or today_iso()
    channel = request.form.get("channel") or "other"
    if channel not in CHANNELS:
        channel = "other"
    summary = request.form.get("summary") or ""
    followup_required = 1 if request.form.get("follow_up_required") else 0
    follow_up_by = parse_date(request.form.get("follow_up_by"))

    execute(
        "INSERT INTO interactions(contact_id, date, channel, summary, "
        "follow_up_required, follow_up_by) VALUES (?, ?, ?, ?, ?, ?)",
        (cid, when, channel, summary, followup_required, follow_up_by),
    )
    # Update last_contact_date and next_followup_date.
    execute(
        "UPDATE contacts SET last_contact_date = ?, "
        "next_followup_date = COALESCE(?, next_followup_date) WHERE id = ?",
        (when, follow_up_by, cid),
    )
    flash("Interaction logged.", "success")
    return redirect(url_for(".detail", cid=cid))


def _save(cid: int | None) -> None:
    fields = {
        "name": (request.form.get("name") or "").strip(),
        "company_id": coerce_int(request.form.get("company_id")),
        "role": request.form.get("role") or "",
        "linkedin_url": request.form.get("linkedin_url") or "",
        "email": request.form.get("email") or "",
        "phone": request.form.get("phone") or "",
        "location": request.form.get("location") or "",
        "notes": request.form.get("notes") or "",
        "tags": request.form.get("tags") or "",
        "how_we_met": request.form.get("how_we_met") or "",
        "warmth": coerce_int(request.form.get("warmth")),
        "last_contact_date": parse_date(request.form.get("last_contact_date")),
        "next_followup_date": parse_date(request.form.get("next_followup_date")),
    }
    if not fields["name"]:
        flash("Name is required.", "danger")
        return
    if cid is None:
        execute(
            "INSERT INTO contacts(name, company_id, role, linkedin_url, email, phone, "
            "location, notes, tags, how_we_met, warmth, last_contact_date, next_followup_date) "
            "VALUES (:name, :company_id, :role, :linkedin_url, :email, :phone, :location, "
            ":notes, :tags, :how_we_met, :warmth, :last_contact_date, :next_followup_date)",
            fields,
        )
    else:
        fields["id"] = cid
        execute(
            "UPDATE contacts SET name=:name, company_id=:company_id, role=:role, "
            "linkedin_url=:linkedin_url, email=:email, phone=:phone, location=:location, "
            "notes=:notes, tags=:tags, how_we_met=:how_we_met, warmth=:warmth, "
            "last_contact_date=:last_contact_date, next_followup_date=:next_followup_date "
            "WHERE id=:id",
            fields,
        )
