"""Shared Flask extension instances.

Kept separate so blueprints can import without circulars.
"""
from __future__ import annotations

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
