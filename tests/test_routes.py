"""Route smoke tests + CRUD round-trips + auth + backup + wikilink + vault."""
from __future__ import annotations

import json

import pytest

from tests.conftest import ADMIN_PASS, ADMIN_USER


def test_login_requires_correct_password(client):
    resp = client.post(
        "/login", data={"username": ADMIN_USER, "password": "wrong"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert b"Invalid" in resp.data


def test_login_then_logout(client):
    resp = client.post(
        "/login", data={"username": ADMIN_USER, "password": ADMIN_PASS},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    resp = client.get("/")
    assert resp.status_code == 200
    resp = client.post("/logout", follow_redirects=False)
    assert resp.status_code == 302
    resp = client.get("/")
    assert resp.status_code == 302  # redirects to login


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/companies/",
        "/contacts/",
        "/stories/",
        "/learning/",
        "/actions/",
        "/actions/calendar",
        "/salary/",
        "/resume/",
        "/review/",
        "/review/history",
        "/vault/",
        "/search?q=Boeing",
        "/capture",
        "/backups",
    ],
)
def test_routes_200(auth_client, path):
    resp = auth_client.get(path)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"


def test_company_crud(auth_client):
    resp = auth_client.post(
        "/companies/new",
        data={"name": "TestCo", "location": "Test City", "type": "specialty",
              "priority": "1", "status": "watching", "notes": "Some [[wikilink]] text"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # Find inserted id.
    resp = auth_client.get("/companies/?q=TestCo")
    assert b"TestCo" in resp.data

    # FTS hit.
    resp = auth_client.get("/search?q=TestCo")
    assert b"TestCo" in resp.data


def test_contact_crud_and_interaction(auth_client):
    resp = auth_client.post(
        "/contacts/new",
        data={"name": "Jane Q", "role": "Stress Engineer", "warmth": "4"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.db import query_one
    with auth_client.application.app_context():
        row = query_one("SELECT id FROM contacts WHERE name = 'Jane Q'")
        assert row is not None
        cid = row["id"]

    resp = auth_client.post(
        f"/contacts/{cid}/interactions/new",
        data={"date": "2026-05-01", "channel": "email", "summary": "Said hi"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with auth_client.application.app_context():
        from app.db import query
        rows = query("SELECT * FROM interactions WHERE contact_id = ?", (cid,))
        assert len(rows) == 1


def test_story_practice_increments_counter(auth_client):
    resp = auth_client.post(
        "/stories/new",
        data={"title": "Practice test", "situation": "S", "task": "T",
              "action": "A", "result": "R", "technical": "T", "readiness": "usable"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    from app.db import query_one
    with auth_client.application.app_context():
        before = query_one("SELECT times_practiced FROM project_stories WHERE title='Practice test'")
    sid = None
    with auth_client.application.app_context():
        sid = query_one("SELECT id FROM project_stories WHERE title='Practice test'")["id"]
    resp = auth_client.post(f"/stories/{sid}/practice/log")
    assert resp.status_code == 200
    with auth_client.application.app_context():
        after = query_one("SELECT times_practiced FROM project_stories WHERE id = ?", (sid,))
    assert after["times_practiced"] == before["times_practiced"] + 1


def test_action_status_change(auth_client):
    auth_client.post(
        "/actions/new",
        data={"title": "Test action", "category": "admin", "priority": "high", "status": "pending"},
        follow_redirects=True,
    )
    from app.db import query_one
    with auth_client.application.app_context():
        aid = query_one("SELECT id FROM actions WHERE title='Test action'")["id"]
    resp = auth_client.post(f"/actions/{aid}/status", data={"status": "done"})
    assert resp.status_code in (200, 302)
    with auth_client.application.app_context():
        row = query_one("SELECT status, date_completed FROM actions WHERE id = ?", (aid,))
        assert row["status"] == "done"
        assert row["date_completed"] is not None


def test_fts_hits_seeded_content(auth_client):
    resp = auth_client.get("/search?q=Bruhn")
    # Bruhn is in seeded learning items and book notes vault file.
    assert b"Bruhn" in resp.data


def test_vault_renders_with_math_and_code(auth_client, tmp_vault):
    (tmp_vault / "10 - Career" / "WithCode.md").write_text(
        "# With Code\n\nInline $E=mc^2$.\n\n```python\nprint('hi')\n```\n",
        encoding="utf-8",
    )
    # Trigger reindex.
    from app.helpers import vault as _v
    with auth_client.application.app_context():
        _v().reindex()
    resp = auth_client.get("/vault/10 - Career/WithCode")
    assert resp.status_code == 200
    assert b"$E=mc^2$" in resp.data  # Raw $ delimiters preserved for KaTeX
    assert b"<code" in resp.data


def test_wikilink_resolution(auth_client, tmp_vault):
    from app.helpers import vault as _v
    with auth_client.application.app_context():
        _v().reindex()
        # Single match -> link to that note.
        href, status = _v().resolve_wikilink("Networking")
        assert status == "ok"
        assert href.endswith("/vault/10 - Career/Networking")
        # Ambiguous basename — Bruhn exists in two folders.
        href, status = _v().resolve_wikilink("Bruhn")
        assert status == "ambiguous"
        # Broken.
        href, status = _v().resolve_wikilink("DoesNotExist")
        assert href is None and status == "broken"


def test_backup_endpoint_token_auth(auth_client, app):
    # Missing token -> 401.
    resp = auth_client.post("/backup")
    assert resp.status_code == 401

    # Wrong token -> 401.
    resp = auth_client.post("/backup", headers={"X-Backup-Token": "wrong"})
    assert resp.status_code == 401

    # Right token -> 200 + JSON file produced.
    resp = auth_client.post(
        "/backup", headers={"X-Backup-Token": app.config["BACKUP_TOKEN"]}
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert "filename" in payload and "size" in payload

    # Query-string token also works.
    resp = auth_client.post(f"/backup?token={app.config['BACKUP_TOKEN']}")
    assert resp.status_code == 200

    # Verify the dump is valid JSON with seeded data.
    dump_path = app.config["BACKUPS_DIR"] / payload["filename"]
    data = json.loads(dump_path.read_text())
    assert "tables" in data
    assert any(c["name"] == "Boeing Defense" for c in data["tables"]["companies"])


def test_capture_creates_action(auth_client):
    resp = auth_client.post(
        "/capture",
        data={"type": "action", "title": "From capture", "notes": "n/a"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    from app.db import query_one
    with auth_client.application.app_context():
        row = query_one("SELECT * FROM actions WHERE title='From capture'")
        assert row is not None
        assert row["status"] == "pending"
