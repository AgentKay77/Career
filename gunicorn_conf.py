"""Gunicorn config for Roundbreak Career.

Binds 0.0.0.0:5001 — verify the port is free before deployment.
Two sync workers are plenty for a single-user PWA.
"""
from __future__ import annotations

bind: str = "0.0.0.0:5001"
workers: int = 2
worker_class: str = "sync"
timeout: int = 60
graceful_timeout: int = 30
keepalive: int = 5
accesslog: str = "-"
errorlog: str = "-"
loglevel: str = "info"
proc_name: str = "roundbreak-career"
