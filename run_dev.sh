#!/usr/bin/env bash
# Dev runner — Flask debug on port 5001 with autoreload.
# Production uses gunicorn via systemd; see deploy/roundbreak-career.service.
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Wrote .env from .env.example — edit it before logging in."
fi

export FLASK_APP="app:create_app()"
export FLASK_DEBUG=1

exec .venv/bin/flask run --host 0.0.0.0 --port 5001
