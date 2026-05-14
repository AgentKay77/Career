"""Unified search across SQLite FTS5 tables and the vault filesystem."""
from __future__ import annotations

import re

from flask import Blueprint, render_template, request

from ..auth import login_required
from ..db import query
from ..helpers import vault as vault_handle

bp = Blueprint("search", __name__)


def _fts_term(q: str) -> str:
    # FTS5 prefix-search: split on whitespace, append * to each term, escape quotes.
    parts = [p.replace('"', '""') for p in q.split() if p]
    if not parts:
        return ""
    return " ".join(f'"{p}"*' for p in parts)


@bp.route("/search")
@login_required
def search():
    q = (request.args.get("q") or "").strip()
    results: dict[str, list] = {
        "companies": [],
        "contacts": [],
        "stories": [],
        "actions": [],
        "learning": [],
        "vault": [],
    }
    if q:
        term = _fts_term(q)
        if term:
            results["companies"] = query(
                "SELECT c.id, c.name, snippet(companies_fts, -1, '<mark>', '</mark>', '...', 16) AS snip "
                "FROM companies_fts JOIN companies c ON c.id = companies_fts.rowid "
                "WHERE companies_fts MATCH ? LIMIT 20",
                (term,),
            )
            results["contacts"] = query(
                "SELECT c.id, c.name, c.role, snippet(contacts_fts, -1, '<mark>', '</mark>', '...', 16) AS snip "
                "FROM contacts_fts JOIN contacts c ON c.id = contacts_fts.rowid "
                "WHERE contacts_fts MATCH ? LIMIT 20",
                (term,),
            )
            results["stories"] = query(
                "SELECT s.id, s.title, s.readiness, snippet(stories_fts, -1, '<mark>', '</mark>', '...', 16) AS snip "
                "FROM stories_fts JOIN project_stories s ON s.id = stories_fts.rowid "
                "WHERE stories_fts MATCH ? LIMIT 20",
                (term,),
            )
            results["actions"] = query(
                "SELECT a.id, a.title, a.status, snippet(actions_fts, -1, '<mark>', '</mark>', '...', 16) AS snip "
                "FROM actions_fts JOIN actions a ON a.id = actions_fts.rowid "
                "WHERE actions_fts MATCH ? LIMIT 20",
                (term,),
            )
            results["learning"] = query(
                "SELECT l.id, l.title, l.author, l.status, snippet(learning_fts, -1, '<mark>', '</mark>', '...', 16) AS snip "
                "FROM learning_fts JOIN learning_items l ON l.id = learning_fts.rowid "
                "WHERE learning_fts MATCH ? LIMIT 20",
                (term,),
            )
        # Vault filesystem search uses the watchdog-maintained index.
        for entry, snippet in vault_handle().search(q, limit=20):
            results["vault"].append({"rel": entry.rel, "url_path": entry.url_path, "snippet": snippet})

    return render_template("search.html", q=q, results=results)
