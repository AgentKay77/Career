"""Flask app factory.

Boots SQLite (creating + seeding on first run, applying migrations after),
attaches the Obsidian vault index, registers blueprints, and wires CSRF.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from flask import Flask, redirect, url_for

from . import auth, db, filters, vault
from .config import Config
from .extensions import csrf


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=False,
        static_folder="static",
        template_folder="templates",
    )
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    # Ensure runtime dirs exist (idempotent).
    for key in ("INSTANCE_DIR", "BACKUPS_DIR", "UPLOADS_DIR"):
        Path(app.config[key]).mkdir(parents=True, exist_ok=True)

    app.permanent_session_lifetime = timedelta(days=30)

    csrf.init_app(app)
    db.init_app(app)
    filters.init_app(app)

    # First-run bootstrap + migrations. Safe to call on every boot.
    db.bootstrap(app)

    # Vault index + watchdog observer.
    vault.init_app(app)

    # Blueprints.
    from .routes import (
        actions as actions_routes,
        backup as backup_routes,
        capture as capture_routes,
        companies as companies_routes,
        contacts as contacts_routes,
        dashboard as dashboard_routes,
        learning as learning_routes,
        resume as resume_routes,
        review as review_routes,
        salary as salary_routes,
        search as search_routes,
        stories as stories_routes,
        vault as vault_routes,
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard_routes.bp)
    app.register_blueprint(companies_routes.bp, url_prefix="/companies")
    app.register_blueprint(contacts_routes.bp, url_prefix="/contacts")
    app.register_blueprint(stories_routes.bp, url_prefix="/stories")
    app.register_blueprint(learning_routes.bp, url_prefix="/learning")
    app.register_blueprint(actions_routes.bp, url_prefix="/actions")
    app.register_blueprint(salary_routes.bp, url_prefix="/salary")
    app.register_blueprint(resume_routes.bp, url_prefix="/resume")
    app.register_blueprint(review_routes.bp, url_prefix="/review")
    app.register_blueprint(vault_routes.bp, url_prefix="/vault")
    app.register_blueprint(search_routes.bp)
    app.register_blueprint(capture_routes.bp)
    app.register_blueprint(backup_routes.bp)
    # /backup is token-authed, not CSRF — exempt the blueprint.
    csrf.exempt(backup_routes.bp)

    @app.route("/healthz")
    def healthz():  # pragma: no cover
        return {"status": "ok"}

    @app.errorhandler(404)
    def _not_found(_e):
        from flask import render_template
        return render_template("404.html"), 404

    return app
