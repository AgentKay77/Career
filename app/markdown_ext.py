"""Custom markdown extensions.

WikilinkExtension renders Obsidian-style ``[[target]]`` and
``[[target|display text]]``. Resolution rules:

* exactly one .md basename match in the vault index -> link to /vault/<path>
* zero matches  -> render as plain span with class "wikilink broken"
* >1 matches    -> link to lexicographically first, class "wikilink ambiguous"

We deliberately do NOT use the PyPI markdown-wikilinks package; its
syntax differs from Obsidian's and would render incorrectly.
"""
from __future__ import annotations

import re
from typing import Callable
from xml.etree import ElementTree as ET

from markdown import Extension
from markdown.inlinepatterns import InlineProcessor

WIKILINK_RE = r"\[\[([^\[\]|\n]+?)(?:\|([^\[\]\n]+?))?\]\]"


class WikilinkProcessor(InlineProcessor):
    """Resolve [[wikilinks]] using a lookup callable injected by the app."""

    def __init__(self, pattern: str, resolver: Callable[[str], tuple[str | None, str]]):
        super().__init__(pattern)
        self._resolver = resolver

    def handleMatch(self, m, data):  # type: ignore[override]
        target = m.group(1).strip()
        display = (m.group(2) or "").strip() or target.rsplit("/", 1)[-1].removesuffix(".md")

        href, status = self._resolver(target)

        if href is None:
            el = ET.Element("span")
            el.set("class", "wikilink broken")
            el.set("title", f"No vault note matches '{target}'")
            el.text = display
        else:
            el = ET.Element("a")
            el.set("href", href)
            css = "wikilink"
            if status == "ambiguous":
                css += " ambiguous"
                el.set("title", f"Multiple matches for '{target}'; linked to first")
            el.set("class", css)
            el.text = display

        return el, m.start(0), m.end(0)


class WikilinkExtension(Extension):
    def __init__(self, resolver: Callable[[str], tuple[str | None, str]]):
        super().__init__()
        self._resolver = resolver

    def extendMarkdown(self, md) -> None:  # type: ignore[override]
        md.inlinePatterns.register(
            WikilinkProcessor(WIKILINK_RE, self._resolver),
            "obsidian_wikilink",
            175,
        )


def make_resolver(vault) -> Callable[[str], tuple[str | None, str]]:
    """Return a resolver bound to a Vault instance's index."""

    def resolve(target: str) -> tuple[str | None, str]:
        return vault.resolve_wikilink(target)

    return resolve


# Tasklist support — checkbox-style list items render as <input> checkboxes.
TASK_RE = re.compile(r"^(\s*[-*+]\s+)\[( |x|X)\]\s+(.*)$")


def render_tasklists(html: str) -> str:
    """Cheap post-pass for GitHub-style task list items inside <li>."""
    def _sub(match: re.Match) -> str:
        checked = "checked" if match.group(1).lower() == "x" else ""
        return f'<input type="checkbox" disabled {checked}> {match.group(2)}'

    return re.sub(r"^\[( |x|X)\]\s+(.*)$", _sub, html, flags=re.MULTILINE)
