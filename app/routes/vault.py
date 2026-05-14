"""Read-only Obsidian vault browser/renderer.

Hunter edits notes in Obsidian; this app reads them. The watchdog
observer keeps the index fresh; the rendered HTML is generated on
each request (with HTTP caching headers handled by the service worker
when present).
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import frontmatter
from flask import Blueprint, abort, current_app, render_template, request, url_for

from ..auth import login_required
from ..filters import render_markdown
from ..helpers import vault as vault_handle

bp = Blueprint("vault", __name__)


@bp.route("/")
@login_required
def browse():
    tree = vault_handle().folder_tree()
    return render_template(
        "vault/browse.html",
        tree=tree,
        vault_root=current_app.config["OBSIDIAN_VAULT_PATH"],
    )


@bp.route("/<path:filepath>")
@login_required
def render(filepath: str):
    v = vault_handle()
    entry = v.get(filepath)
    if entry is None:
        # Allow folder browse if path corresponds to a folder.
        if any(
            other.rel.startswith(filepath.rstrip("/") + "/") for other in v.entries()
        ):
            tree = v.folder_tree()
            return render_template(
                "vault/browse.html",
                tree=_subtree(tree, filepath.strip("/")),
                vault_root=current_app.config["OBSIDIAN_VAULT_PATH"],
                folder_path=filepath.strip("/"),
            )
        abort(404)

    raw = v.read(filepath) or ""
    try:
        post = frontmatter.loads(raw)
        meta = dict(post.metadata)
        body = post.content
    except Exception:
        meta, body = {}, raw

    html = render_markdown(body)
    backlinks = v.backlinks(filepath)

    # Obsidian deep link uses obsidian://open?vault=...&file=...
    vault_name = Path(current_app.config["OBSIDIAN_VAULT_PATH"]).name
    obsidian_uri = (
        f"obsidian://open?vault={quote(vault_name)}&file={quote(entry.url_path)}"
    )

    return render_template(
        "vault/render.html",
        entry=entry,
        html=html,
        meta=meta,
        backlinks=backlinks,
        obsidian_uri=obsidian_uri,
    )


def _subtree(tree: dict, folder_path: str) -> dict:
    if not folder_path:
        return tree
    node = tree
    for part in folder_path.split("/"):
        if part not in node["folders"]:
            return {"name": folder_path, "folders": {}, "files": []}
        node = node["folders"][part]
    return node
