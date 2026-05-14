"""Backup endpoints.

POST /backup       — token-authed (header or query string), CSRF exempt
GET  /backups      — login-authed UI to download/restore
POST /backups/<f>/restore — login-authed restore
GET  /backups/<f>  — login-authed download
"""
from __future__ import annotations

import hmac
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from ..auth import login_required
from ..db import bootstrap

bp = Blueprint("backup", __name__)


def _valid_token() -> bool:
    expected = current_app.config.get("BACKUP_TOKEN") or ""
    if not expected:
        return False
    provided = request.headers.get("X-Backup-Token") or request.args.get("token") or ""
    return hmac.compare_digest(expected, provided)


def _dump_db_to_json(db_path: Path) -> dict:
    """Read each user table and emit a JSON dump. FTS tables skipped — rebuilt from triggers."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%' "
                "AND name NOT IN ('schema_migrations')"
            )
        ]
        dump: dict = {"version": 1, "exported_at": datetime.utcnow().isoformat() + "Z", "tables": {}}
        for table in tables:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
            dump["tables"][table] = rows
        return dump
    finally:
        conn.close()


@bp.route("/backup", methods=["POST"])
def create_backup():
    if not _valid_token():
        return jsonify({"error": "unauthorized"}), 401
    db_path: Path = current_app.config["DB_PATH"]
    backups_dir: Path = current_app.config["BACKUPS_DIR"]
    backups_dir.mkdir(parents=True, exist_ok=True)
    dump = _dump_db_to_json(db_path)
    fname = "career_" + datetime.now().strftime("%Y-%m-%d_%H%M") + ".json"
    fpath = backups_dir / fname
    counter = 1
    while fpath.exists():
        fpath = backups_dir / f"career_{datetime.now().strftime('%Y-%m-%d_%H%M')}_{counter}.json"
        counter += 1
    fpath.write_text(json.dumps(dump, indent=2, default=str), encoding="utf-8")
    return jsonify({"filename": fpath.name, "size": fpath.stat().st_size})


@bp.route("/backups", methods=["GET"])
@login_required
def list_view():
    backups_dir: Path = current_app.config["BACKUPS_DIR"]
    backups_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(
        (p for p in backups_dir.iterdir() if p.is_file() and p.suffix == ".json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    entries = [
        {"name": p.name, "size": p.stat().st_size, "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="minutes")}
        for p in files
    ]
    return render_template("backups.html", entries=entries)


@bp.route("/backups/<path:fname>", methods=["GET"])
@login_required
def download(fname: str):
    safe = secure_filename(fname)
    if not safe.endswith(".json"):
        abort(404)
    return send_from_directory(current_app.config["BACKUPS_DIR"], safe, as_attachment=True)


@bp.route("/backups/<path:fname>/restore", methods=["POST"])
@login_required
def restore(fname: str):
    safe = secure_filename(fname)
    backups_dir: Path = current_app.config["BACKUPS_DIR"]
    src = backups_dir / safe
    if not src.is_file():
        abort(404)
    try:
        payload = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        flash(f"Could not read backup: {exc}", "danger")
        return redirect(url_for(".list_view"))

    db_path: Path = current_app.config["DB_PATH"]
    # Snapshot current DB before clobbering.
    snap = backups_dir / f"pre_restore_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.sqlite3"
    try:
        snap.write_bytes(db_path.read_bytes())
    except OSError:
        pass

    # Wipe & re-bootstrap, then load rows.
    try:
        db_path.unlink(missing_ok=True)
    except OSError:
        pass
    bootstrap(current_app)
    conn = sqlite3.connect(db_path)
    try:
        # Clear seed data so we don't double-insert.
        for table in payload.get("tables", {}):
            try:
                conn.execute(f"DELETE FROM {table}")
            except sqlite3.Error:
                pass
        for table, rows in payload.get("tables", {}).items():
            if not rows:
                continue
            columns = list(rows[0].keys())
            placeholders = ",".join(["?"] * len(columns))
            collist = ",".join(columns)
            for row in rows:
                values = [row.get(c) for c in columns]
                try:
                    conn.execute(
                        f"INSERT OR REPLACE INTO {table}({collist}) VALUES ({placeholders})",
                        values,
                    )
                except sqlite3.Error as exc:
                    current_app.logger.warning("Restore skip on %s: %s", table, exc)
        conn.commit()
    finally:
        conn.close()
    flash(f"Restored from {safe}. Pre-restore snapshot at {snap.name}.", "success")
    return redirect(url_for(".list_view"))
