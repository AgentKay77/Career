"""Resume version manager."""
from __future__ import annotations

import os
import re
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from ..auth import login_required
from ..db import execute, query, query_one

bp = Blueprint("resume", __name__)

ALLOWED_EXT = {".pdf", ".docx", ".doc", ".odt", ".txt", ".md"}


@bp.route("/")
@login_required
def list_view():
    rows = query("SELECT * FROM resume_versions ORDER BY date_created DESC, id DESC")
    return render_template("resume/list.html", rows=rows)


@bp.route("/upload", methods=["POST"])
@login_required
def upload():
    name = (request.form.get("name") or "").strip() or "Untitled"
    focus = request.form.get("focus_area") or ""
    notes = request.form.get("notes") or ""
    file = request.files.get("file")
    if file is None or not file.filename:
        flash("Choose a file to upload.", "danger")
        return redirect(url_for(".list_view"))

    safe = secure_filename(file.filename)
    ext = os.path.splitext(safe)[1].lower()
    if ext not in ALLOWED_EXT:
        flash(f"File extension {ext!r} not allowed.", "danger")
        return redirect(url_for(".list_view"))

    uploads: Path = current_app.config["UPLOADS_DIR"]
    uploads.mkdir(parents=True, exist_ok=True)
    # Avoid collisions.
    final = uploads / safe
    counter = 1
    while final.exists():
        stem, ext2 = os.path.splitext(safe)
        final = uploads / f"{stem}-{counter}{ext2}"
        counter += 1
    file.save(final)

    execute(
        "INSERT INTO resume_versions(name, focus_area, file_path, notes, is_current) "
        "VALUES (?, ?, ?, ?, 0)",
        (name, focus, final.name, notes),
    )
    flash("Resume uploaded.", "success")
    return redirect(url_for(".list_view"))


@bp.route("/<int:rid>/mark-current", methods=["POST"])
@login_required
def mark_current(rid: int):
    execute("UPDATE resume_versions SET is_current = 0")
    execute("UPDATE resume_versions SET is_current = 1 WHERE id = ?", (rid,))
    flash("Marked current.", "success")
    return redirect(url_for(".list_view"))


@bp.route("/<int:rid>/download")
@login_required
def download(rid: int):
    row = query_one("SELECT file_path, name FROM resume_versions WHERE id = ?", (rid,))
    if row is None:
        abort(404)
    uploads: Path = current_app.config["UPLOADS_DIR"]
    safe = secure_filename(row["file_path"])
    return send_from_directory(uploads, safe, as_attachment=True)


@bp.route("/<int:rid>/delete", methods=["POST"])
@login_required
def delete(rid: int):
    row = query_one("SELECT file_path FROM resume_versions WHERE id = ?", (rid,))
    if row is None:
        abort(404)
    uploads: Path = current_app.config["UPLOADS_DIR"]
    target = uploads / secure_filename(row["file_path"])
    try:
        target.unlink(missing_ok=True)
    except OSError:
        pass
    execute("DELETE FROM resume_versions WHERE id = ?", (rid,))
    flash("Deleted.", "info")
    return redirect(url_for(".list_view"))
