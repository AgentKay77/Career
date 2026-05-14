"""Obsidian vault reader.

Builds an in-memory index of every .md file under the configured vault
root, refreshed by a watchdog observer when the user adds/edits files
from Obsidian. The Flask app reads but never writes — Obsidian is the
source of truth for note content.
"""
from __future__ import annotations

import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


@dataclass
class VaultEntry:
    path: Path        # absolute path on disk
    rel: str          # path relative to vault root, POSIX-style
    basename: str     # filename without ".md"

    @property
    def url_path(self) -> str:
        return self.rel.removesuffix(".md")


@dataclass
class VaultIndex:
    by_rel: dict[str, VaultEntry] = field(default_factory=dict)
    by_basename: dict[str, list[VaultEntry]] = field(default_factory=lambda: defaultdict(list))


class Vault:
    """Vault index + filesystem watcher. Singleton-ish per Flask app."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve() if root else Path.cwd()
        self._index = VaultIndex()
        self._lock = threading.RLock()
        self._observer: Observer | None = None
        if self.root.is_dir():
            self.reindex()

    # ---------- index ----------
    def reindex(self) -> None:
        idx = VaultIndex()
        if self.root.is_dir():
            for path in self.root.rglob("*.md"):
                if any(part.startswith(".") for part in path.relative_to(self.root).parts):
                    continue
                rel = path.relative_to(self.root).as_posix()
                base = path.stem
                entry = VaultEntry(path=path, rel=rel, basename=base)
                idx.by_rel[rel] = entry
                idx.by_basename[base.lower()].append(entry)
        for entries in idx.by_basename.values():
            entries.sort(key=lambda e: e.rel)
        with self._lock:
            self._index = idx

    # ---------- watchdog ----------
    def start_watcher(self) -> None:
        if not self.root.is_dir() or self._observer is not None:
            return
        handler = _ReindexHandler(self.reindex)
        obs = Observer()
        obs.schedule(handler, str(self.root), recursive=True)
        obs.daemon = True
        obs.start()
        self._observer = obs

    def stop_watcher(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer = None

    # ---------- queries ----------
    def entries(self) -> list[VaultEntry]:
        with self._lock:
            return list(self._index.by_rel.values())

    def get(self, rel_path: str) -> VaultEntry | None:
        rel = rel_path.replace("\\", "/").lstrip("/")
        if not rel.endswith(".md"):
            rel = rel + ".md"
        with self._lock:
            return self._index.by_rel.get(rel)

    def read(self, rel_path: str) -> str | None:
        entry = self.get(rel_path)
        if entry is None or not entry.path.is_file():
            return None
        try:
            return entry.path.read_text(encoding="utf-8")
        except OSError:
            return None

    def folders(self) -> list[str]:
        with self._lock:
            folders = {os.path.dirname(rel) for rel in self._index.by_rel}
        return sorted(f for f in folders if f)

    def folder_tree(self) -> dict:
        """Nested folder tree: {'name': str, 'folders': [...], 'files': [VaultEntry]}."""
        root: dict = {"name": "", "folders": {}, "files": []}
        for entry in self.entries():
            parts = entry.rel.split("/")
            node = root
            for part in parts[:-1]:
                node = node["folders"].setdefault(
                    part, {"name": part, "folders": {}, "files": []}
                )
            node["files"].append(entry)
        return root

    def resolve_wikilink(self, target: str) -> tuple[str | None, str]:
        """Return (href_or_None, status). Status one of 'ok', 'ambiguous', 'broken'."""
        target = target.strip()
        if not target:
            return None, "broken"

        # Strip optional .md suffix; preserve subpath if author used one.
        candidate = target.removesuffix(".md")
        # Try exact relative path first.
        with self._lock:
            rel_match = self._index.by_rel.get(candidate + ".md")
            if rel_match is not None:
                return f"/vault/{rel_match.url_path}", "ok"

            base = candidate.rsplit("/", 1)[-1].lower()
            matches = self._index.by_basename.get(base, [])
        if not matches:
            return None, "broken"
        if len(matches) == 1:
            return f"/vault/{matches[0].url_path}", "ok"
        return f"/vault/{matches[0].url_path}", "ambiguous"

    def backlinks(self, target_rel: str) -> list[VaultEntry]:
        """Find notes that wikilink to target_rel by basename match."""
        target_entry = self.get(target_rel)
        if target_entry is None:
            return []
        needle = target_entry.basename.lower()
        out: list[VaultEntry] = []
        for entry in self.entries():
            if entry.rel == target_entry.rel:
                continue
            try:
                text = entry.path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if f"[[" not in text:
                continue
            # Cheap match: any wikilink whose target basename equals needle.
            for chunk in text.split("[[")[1:]:
                end = chunk.find("]]")
                if end < 0:
                    continue
                inner = chunk[:end].split("|", 1)[0].strip()
                if inner.rsplit("/", 1)[-1].removesuffix(".md").lower() == needle:
                    out.append(entry)
                    break
        out.sort(key=lambda e: e.rel)
        return out

    def search(self, query: str, limit: int = 50) -> list[tuple[VaultEntry, str]]:
        """Naive case-insensitive substring search; returns (entry, snippet)."""
        if not query.strip():
            return []
        q = query.strip().lower()
        results: list[tuple[VaultEntry, str]] = []
        for entry in self.entries():
            try:
                text = entry.path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            idx = text.lower().find(q)
            if idx == -1 and q not in entry.basename.lower():
                continue
            start = max(0, idx - 60) if idx >= 0 else 0
            end = min(len(text), (idx if idx >= 0 else 0) + 140)
            snippet = text[start:end].replace("\n", " ").strip()
            results.append((entry, snippet or entry.basename))
            if len(results) >= limit:
                break
        return results


class _ReindexHandler(FileSystemEventHandler):
    def __init__(self, reindex: callable):
        self._reindex = reindex

    def on_any_event(self, event: FileSystemEvent) -> None:
        # We don't care which file changed — reindex is cheap for a personal vault.
        if event.is_directory or event.src_path.endswith(".md"):
            self._reindex()


def init_app(app) -> Vault:
    vault = Vault(app.config["OBSIDIAN_VAULT_PATH"])
    app.extensions["vault"] = vault
    # Only start the watcher when a real process is running (skip during tests).
    if not app.config.get("TESTING", False):
        vault.start_watcher()
    return vault
