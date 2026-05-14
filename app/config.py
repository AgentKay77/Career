"""Flask configuration.

Code default is safe: SESSION_COOKIE_SECURE=True. The env var override
exists so LAN-only HTTP installs work — flipping it back to True after
adding HTTPS is one line in .env, no code change.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"false", "0", "no", "off", ""}


class Config:
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    BACKUP_TOKEN: str = os.environ.get("BACKUP_TOKEN", "")
    OBSIDIAN_VAULT_PATH: str = os.environ.get(
        "OBSIDIAN_VAULT_PATH", str(Path.home() / "obsidian-vault")
    )

    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    # Default True (safe). LAN-only installs set SESSION_COOKIE_SECURE=False in .env.
    SESSION_COOKIE_SECURE: bool = _env_bool("SESSION_COOKIE_SECURE", True)

    WTF_CSRF_TIME_LIMIT: int | None = None  # session-lifetime CSRF tokens
    MAX_CONTENT_LENGTH: int = 32 * 1024 * 1024  # 32 MB resume uploads

    INSTANCE_DIR: Path = BASE_DIR / "instance"
    BACKUPS_DIR: Path = BASE_DIR / "backups"
    DB_PATH: Path = INSTANCE_DIR / "career.sqlite3"
    UPLOADS_DIR: Path = INSTANCE_DIR / "uploads"
