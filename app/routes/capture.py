"""Quick-capture: a single mobile-friendly form that creates an action,
contact, learning item, or story stub.
"""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute

bp = Blueprint("capture", __name__)


@bp.route("/capture", methods=["GET", "POST"])
@login_required
def capture():
    if request.method == "POST":
        kind = request.form.get("type") or "action"
        title = (request.form.get("title") or "").strip()
        notes = request.form.get("notes") or ""
        if not title:
            flash("Title required.", "danger")
            return redirect(url_for(".capture"))

        if kind == "action":
            execute(
                "INSERT INTO actions(title, description, category, priority, status) "
                "VALUES (?, ?, 'admin', 'medium', 'pending')",
                (title, notes),
            )
            flash("Action captured.", "success")
        elif kind == "contact":
            execute(
                "INSERT INTO contacts(name, notes) VALUES (?, ?)",
                (title, notes),
            )
            flash("Contact stub captured.", "success")
        elif kind == "learning":
            execute(
                "INSERT INTO learning_items(type, title, key_takeaways, status, priority) "
                "VALUES ('article', ?, ?, 'queued', 2)",
                (title, notes),
            )
            flash("Learning item captured.", "success")
        elif kind == "story":
            execute(
                "INSERT INTO project_stories(title, situation, readiness) VALUES (?, ?, 'draft')",
                (title, notes),
            )
            flash("Story stub captured.", "success")
        else:
            flash("Unknown capture type.", "danger")
        return redirect(url_for(".capture"))

    return render_template("capture.html")
