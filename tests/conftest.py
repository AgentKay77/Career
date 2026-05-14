"""Pytest fixtures: ephemeral app, ephemeral DB, ephemeral vault."""
from __future__ import annotations

import os
import secrets
import tempfile
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.db import create_user

ADMIN_USER = "tester"
ADMIN_PASS = "correct-horse-battery-staple"


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "10 - Career").mkdir()
    (vault / "10 - Career" / "Networking.md").write_text(
        "# Networking\n\nA note that links to [[Bruhn]] and [[Missing Note]].\n"
        "\n## Math\n\nInline $E = mc^2$ and block:\n\n$$\\sigma = F/A$$\n",
        encoding="utf-8",
    )
    (vault / "30 - Book Notes").mkdir()
    (vault / "30 - Book Notes" / "Bruhn.md").write_text(
        "# Bruhn\n\nAirframe stress analysis canon.\n",
        encoding="utf-8",
    )
    # Create an ambiguous basename.
    (vault / "10 - Career" / "Bruhn.md").write_text("Alternate Bruhn note.", encoding="utf-8")
    return vault


@pytest.fixture
def app(tmp_path: Path, tmp_vault: Path, monkeypatch):
    instance = tmp_path / "instance"
    instance.mkdir()
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "False")
    app = create_app(
        {
            "TESTING": True,
            "INSTANCE_DIR": instance,
            "BACKUPS_DIR": tmp_path / "backups",
            "UPLOADS_DIR": instance / "uploads",
            "DB_PATH": instance / "career.sqlite3",
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "SECRET_KEY": "test-secret",
            "BACKUP_TOKEN": "test-backup-token",
            "WTF_CSRF_ENABLED": False,
            "SESSION_COOKIE_SECURE": False,
        }
    )
    with app.app_context():
        create_user(ADMIN_USER, generate_password_hash(ADMIN_PASS))
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    client.post("/login", data={"username": ADMIN_USER, "password": ADMIN_PASS},
                follow_redirects=False)
    return client
