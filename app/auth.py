"""Single-user auth: session cookie + login_required decorator."""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from .db import query_one

bp = Blueprint("auth", __name__)


def login_required(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@bp.before_app_request
def load_user() -> None:
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        row = query_one("SELECT id, username FROM users WHERE id = ?", (user_id,))
        if row is not None:
            g.user = {"id": row["id"], "username": row["username"]}


@bp.route("/login", methods=["GET", "POST"])
def login():
    error: str | None = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        row = query_one(
            "SELECT id, password_hash FROM users WHERE username = ?", (username,)
        )
        if row is None or not check_password_hash(row["password_hash"], password):
            error = "Invalid username or password."
            current_app.logger.warning("Failed login attempt for %r", username)
        else:
            session.clear()
            session["user_id"] = row["id"]
            session.permanent = True
            next_url = request.args.get("next") or url_for("dashboard.index")
            if not next_url.startswith("/"):
                next_url = url_for("dashboard.index")
            return redirect(next_url)

    return render_template("login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))
