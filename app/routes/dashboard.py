"""Dashboard: This Week / Follow-ups / Quick Stats."""
from __future__ import annotations

from flask import Blueprint, render_template

from ..auth import login_required
from ..db import query, query_one

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    this_week = query(
        """
        SELECT id, title, category, priority, target_date, status
          FROM actions
         WHERE status IN ('pending','in_progress')
           AND (target_date IS NULL OR date(target_date) <= date('now','+7 days'))
         ORDER BY
            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            target_date IS NULL,
            target_date,
            id
         LIMIT 12
        """
    )
    followups = query(
        """
        SELECT c.id, c.name, c.role, c.next_followup_date, c.last_contact_date,
               co.name AS company_name
          FROM contacts c
          LEFT JOIN companies co ON co.id = c.company_id
         WHERE c.next_followup_date IS NOT NULL
           AND date(c.next_followup_date) <= date('now','+14 days')
         ORDER BY date(c.next_followup_date) ASC
         LIMIT 12
        """
    )
    stale = query(
        """
        SELECT c.id, c.name, c.last_contact_date, co.name AS company_name
          FROM contacts c
          LEFT JOIN companies co ON co.id = c.company_id
         WHERE c.last_contact_date IS NOT NULL
           AND date(c.last_contact_date) <= date('now','-60 days')
         ORDER BY date(c.last_contact_date) ASC
         LIMIT 8
        """
    )
    stats = {
        "companies": (query_one("SELECT COUNT(*) AS n FROM companies") or {"n": 0})["n"],
        "contacts": (query_one("SELECT COUNT(*) AS n FROM contacts") or {"n": 0})["n"],
        "stories_polished": (
            query_one("SELECT COUNT(*) AS n FROM project_stories WHERE readiness='polished'")
            or {"n": 0}
        )["n"],
        "stories_total": (query_one("SELECT COUNT(*) AS n FROM project_stories") or {"n": 0})["n"],
        "actions_open": (
            query_one(
                "SELECT COUNT(*) AS n FROM actions WHERE status IN ('pending','in_progress')"
            )
            or {"n": 0}
        )["n"],
        "books_done": (
            query_one(
                "SELECT COUNT(*) AS n FROM learning_items WHERE type='book' AND status='done'"
            )
            or {"n": 0}
        )["n"],
        "books_queued": (
            query_one(
                "SELECT COUNT(*) AS n FROM learning_items WHERE type='book' AND status IN ('queued','reading')"
            )
            or {"n": 0}
        )["n"],
    }
    return render_template(
        "dashboard.html",
        this_week=this_week,
        followups=followups,
        stale=stale,
        stats=stats,
    )
