"""Salary data — filterable table with stats panel."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query, query_one
from ..helpers import coerce_bool, coerce_float, coerce_int, parse_date, percentile_stats

bp = Blueprint("salary", __name__)

SOURCES = ("h1b", "levels", "glassdoor", "conversation", "recruiter", "offer", "other")


@bp.route("/")
@login_required
def list_view():
    company = request.args.get("company") or ""
    role = request.args.get("role") or ""
    location = request.args.get("location") or ""
    source = request.args.get("source") or ""
    cleared = request.args.get("cleared") or ""

    where, params = ["1=1"], []
    if company:
        where.append("company LIKE ?")
        params.append(f"%{company}%")
    if role:
        where.append("role LIKE ?")
        params.append(f"%{role}%")
    if location:
        where.append("location LIKE ?")
        params.append(f"%{location}%")
    if source in SOURCES:
        where.append("source = ?")
        params.append(source)
    if cleared == "1":
        where.append("cleared = 1")
    elif cleared == "0":
        where.append("cleared = 0")

    rows = query(
        f"SELECT * FROM salary_data WHERE {' AND '.join(where)} "
        f"ORDER BY year DESC, total_comp DESC, id DESC",
        params,
    )
    stats = {
        "base": percentile_stats([r["base_salary"] for r in rows]),
        "total": percentile_stats([r["total_comp"] for r in rows]),
    }
    return render_template(
        "salary/list.html",
        rows=rows,
        stats=stats,
        sources=SOURCES,
        company=company,
        role=role,
        location=location,
        source=source,
        cleared=cleared,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        _save(None)
        flash("Salary data point added.", "success")
        return redirect(url_for(".list_view"))
    return render_template("salary/form.html", row=None, sources=SOURCES)


@bp.route("/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def edit(sid: int):
    row = query_one("SELECT * FROM salary_data WHERE id = ?", (sid,))
    if row is None:
        abort(404)
    if request.method == "POST":
        _save(sid)
        flash("Updated.", "success")
        return redirect(url_for(".list_view"))
    return render_template("salary/form.html", row=row, sources=SOURCES)


@bp.route("/<int:sid>/delete", methods=["POST"])
@login_required
def delete(sid: int):
    execute("DELETE FROM salary_data WHERE id = ?", (sid,))
    flash("Deleted.", "info")
    return redirect(url_for(".list_view"))


def _save(sid: int | None) -> None:
    src = request.form.get("source") or "other"
    if src not in SOURCES:
        src = "other"
    fields = {
        "source": src,
        "company": request.form.get("company") or "",
        "role": request.form.get("role") or "",
        "level": request.form.get("level") or "",
        "base_salary": coerce_float(request.form.get("base_salary")),
        "bonus_target_pct": coerce_float(request.form.get("bonus_target_pct")),
        "bonus_amount": coerce_float(request.form.get("bonus_amount")),
        "equity_value": coerce_float(request.form.get("equity_value")),
        "total_comp": coerce_float(request.form.get("total_comp")),
        "location": request.form.get("location") or "",
        "year": coerce_int(request.form.get("year")),
        "cleared": coerce_bool(request.form.get("cleared")),
        "notes": request.form.get("notes") or "",
        "date_recorded": parse_date(request.form.get("date_recorded")) or None,
    }
    if sid is None:
        execute(
            "INSERT INTO salary_data(source, company, role, level, base_salary, "
            "bonus_target_pct, bonus_amount, equity_value, total_comp, location, year, "
            "cleared, notes, date_recorded) "
            "VALUES (:source, :company, :role, :level, :base_salary, :bonus_target_pct, "
            ":bonus_amount, :equity_value, :total_comp, :location, :year, :cleared, "
            ":notes, COALESCE(:date_recorded, date('now')))",
            fields,
        )
    else:
        fields["id"] = sid
        execute(
            "UPDATE salary_data SET source=:source, company=:company, role=:role, level=:level, "
            "base_salary=:base_salary, bonus_target_pct=:bonus_target_pct, "
            "bonus_amount=:bonus_amount, equity_value=:equity_value, total_comp=:total_comp, "
            "location=:location, year=:year, cleared=:cleared, notes=:notes, "
            "date_recorded=COALESCE(:date_recorded, date_recorded) WHERE id=:id",
            fields,
        )
