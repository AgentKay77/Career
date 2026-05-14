"""App factory, schema bootstrap, migration runner."""
from __future__ import annotations

import sqlite3

from app.db import bootstrap


def test_app_factory(app):
    assert app.config["TESTING"] is True
    assert app.config["DB_PATH"].exists()


def test_schema_seeded(app):
    conn = sqlite3.connect(app.config["DB_PATH"])
    try:
        # Seeded companies should include Boeing Defense.
        row = conn.execute("SELECT COUNT(*) FROM companies WHERE name='Boeing Defense'").fetchone()
        assert row[0] == 1
        # Seeded actions exist.
        count = conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
        assert count > 10
        # FTS triggers populated.
        fts_hits = conn.execute(
            "SELECT COUNT(*) FROM companies_fts WHERE companies_fts MATCH 'Boeing*'"
        ).fetchone()[0]
        assert fts_hits >= 1
    finally:
        conn.close()


def test_migration_runner_applies_and_tracks(app, tmp_path):
    """Drop a migration file, re-bootstrap, verify it ran and was tracked."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    # Use the app's existing migration directory by writing into it.
    from app import db as db_module
    test_migration = db_module.MIGRATIONS_DIR / "999_test_migration.sql"
    try:
        test_migration.write_text(
            "CREATE TABLE _test_table_999 (id INTEGER PRIMARY KEY, v TEXT);\n"
            "INSERT INTO _test_table_999(v) VALUES ('marker');\n",
            encoding="utf-8",
        )
        bootstrap(app)
        conn = sqlite3.connect(app.config["DB_PATH"])
        try:
            row = conn.execute("SELECT v FROM _test_table_999").fetchone()
            assert row[0] == "marker"
            applied = conn.execute(
                "SELECT version FROM schema_migrations WHERE version = 999"
            ).fetchone()
            assert applied is not None

            # Re-run is idempotent — no duplicate inserts.
            bootstrap(app)
            count = conn.execute("SELECT COUNT(*) FROM _test_table_999").fetchone()[0]
            assert count == 1
        finally:
            conn.close()
    finally:
        test_migration.unlink(missing_ok=True)


def test_session_cookie_secure_env_override(monkeypatch):
    """SESSION_COOKIE_SECURE env var overrides the safe default."""
    from app.config import _env_bool

    # Default True (safe) when env unset.
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    assert _env_bool("SESSION_COOKIE_SECURE", True) is True

    # LAN install string False => False.
    for value in ("False", "false", "0", "no", "off"):
        monkeypatch.setenv("SESSION_COOKIE_SECURE", value)
        assert _env_bool("SESSION_COOKIE_SECURE", True) is False, value

    # Any truthy value stays True.
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "True")
    assert _env_bool("SESSION_COOKIE_SECURE", True) is True
