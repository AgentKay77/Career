"""Jinja filters: markdown rendering, date formatting, wikilink resolution."""
from __future__ import annotations

from datetime import date, datetime

import markdown as md
from markupsafe import Markup
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.footnotes import FootnoteExtension
from markdown.extensions.tables import TableExtension

from .helpers import vault
from .markdown_ext import WikilinkExtension, make_resolver


def render_markdown(text: str | None) -> Markup:
    """Render markdown -> safe HTML.

    KaTeX runs client-side over $...$ and $$...$$ delimiters; we preserve
    them by configuring fenced code first and leaving raw text untouched
    elsewhere. Code blocks get language hints for highlight.js.
    """
    if not text:
        return Markup("")
    extensions = [
        FencedCodeExtension(),
        TableExtension(),
        FootnoteExtension(),
        CodeHiliteExtension(css_class="hljs", guess_lang=False),
        "sane_lists",
        WikilinkExtension(make_resolver(vault())),
    ]
    html = md.markdown(text, extensions=extensions, output_format="html5")
    return Markup(html)


def format_date(value, fmt: str = "%Y-%m-%d") -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime(fmt)
    try:
        return datetime.fromisoformat(str(value)).strftime(fmt)
    except ValueError:
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").strftime(fmt)
        except ValueError:
            return str(value)


def format_money(value) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def days_until(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        target = datetime.fromisoformat(str(value)).date()
    except ValueError:
        try:
            target = datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError:
            return None
    return (target - date.today()).days


def init_app(app) -> None:
    app.jinja_env.filters["markdown"] = render_markdown
    app.jinja_env.filters["fmt_date"] = format_date
    app.jinja_env.filters["money"] = format_money
    app.jinja_env.filters["days_until"] = days_until
    app.jinja_env.globals["today"] = date.today
