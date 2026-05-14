"""SQLite connection, bootstrap, and migration runner.

Pattern: one connection per request, stored on `flask.g`. First-run
bootstrap detects an empty DB (no users table) and runs schema.sql +
seed.sql in a single transaction. Subsequent startups apply any
numbered migrations from app/migrations/ that haven't been applied yet.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Iterable

from flask import Flask, current_app, g

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"
SEED_FILE = Path(__file__).resolve().parent / "seed.sql"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
MIGRATION_PATTERN = re.compile(r"^(\d+)_.+\.sql$")


def get_db() -> sqlite3.Connection:
    """Return the request-scoped SQLite connection, opening one if needed."""
    if "db" not in g:
        db_path = current_app.config["DB_PATH"]
        conn = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None,  # autocommit; we explicitly BEGIN where needed
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        g.db = conn
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def _users_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    return row is not None


def _discover_migrations() -> list[tuple[int, Path]]:
    if not MIGRATIONS_DIR.is_dir():
        return []
    found: list[tuple[int, Path]] = []
    for path in MIGRATIONS_DIR.iterdir():
        match = MIGRATION_PATTERN.match(path.name)
        if match:
            found.append((int(match.group(1)), path))
    found.sort(key=lambda item: item[0])
    return found


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if row is None:
        return set()
    return {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}


def bootstrap(app: Flask) -> None:
    """Create the DB on first run; apply any pending migrations after that."""
    db_path: Path = app.config["DB_PATH"]
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        if not _users_table_exists(conn):
            schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
            seed_sql = SEED_FILE.read_text(encoding="utf-8")
            conn.executescript("BEGIN;\n" + schema_sql + "\n" + seed_sql + "\nCOMMIT;")
            app.logger.info("Initialized fresh database at %s", db_path)

        applied = _applied_versions(conn)
        for version, path in _discover_migrations():
            if version in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            conn.executescript(
                "BEGIN;\n"
                + sql
                + f"\nINSERT INTO schema_migrations(version) VALUES ({version});\nCOMMIT;"
            )
            app.logger.info("Applied migration %s", path.name)
    finally:
        conn.close()


def create_user(username: str, password_hash: str) -> None:
    """Insert a user record. Caller hashes the password."""
    db_path = current_app.config["DB_PATH"]
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO users (id, username, password_hash) "
            "VALUES ((SELECT id FROM users WHERE username = ?), ?, ?)",
            (username, username, password_hash),
        )
        conn.commit()
    finally:
        conn.close()


def _params(params):
    """Pass dicts through (for :name style) and coerce everything else to tuple."""
    return params if isinstance(params, dict) else tuple(params)


def query(sql: str, params: Iterable | dict = ()) -> list[sqlite3.Row]:
    return get_db().execute(sql, _params(params)).fetchall()


def query_one(sql: str, params: Iterable | dict = ()) -> sqlite3.Row | None:
    return get_db().execute(sql, _params(params)).fetchone()


def execute(sql: str, params: Iterable | dict = ()) -> sqlite3.Cursor:
    return get_db().execute(sql, _params(params))


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
