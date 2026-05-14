#!/usr/bin/env bash
# Roundbreak Career — one-shot installer for Pi 5 Trixie.
#
# Idempotent: re-running on an existing install upgrades code and deps,
# preserves DB and uploaded resumes, regenerates only missing icons.

set -euo pipefail

APP_NAME="roundbreak-career"
APP_DIR="/opt/${APP_NAME}"
APP_USER="career"
APP_GROUP="career"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
PORT=5001
HUNTER_USER="hunter"
DEFAULT_VAULT="/home/${HUNTER_USER}/obsidian-vault"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

color() { printf "\033[1;%sm%s\033[0m\n" "$1" "$2"; }
info()  { color "34" "→ $*"; }
ok()    { color "32" "✓ $*"; }
warn()  { color "33" "! $*"; }
die()   { color "31" "✗ $*"; exit 1; }

ask() {
  local prompt="$1" default="${2:-}" answer
  if [[ -n "$default" ]]; then
    read -rp "$prompt [$default]: " answer
    echo "${answer:-$default}"
  else
    read -rp "$prompt: " answer
    echo "$answer"
  fi
}

ask_secret() {
  local prompt="$1" answer
  read -rsp "$prompt: " answer
  echo
  echo "$answer"
}

ask_yn() {
  local prompt="$1" default="${2:-N}" answer
  if [[ "$default" == "Y" ]]; then
    read -rp "$prompt [Y/n]: " answer
    answer="${answer:-Y}"
  else
    read -rp "$prompt [y/N]: " answer
    answer="${answer:-N}"
  fi
  [[ "$answer" =~ ^[Yy] ]]
}

# 0. Must be root for systemd / user creation.
if [[ $EUID -ne 0 ]]; then
  die "Run as root: sudo bash setup.sh"
fi

info "Roundbreak Career installer"

# 1. Python version check.
if ! command -v python3 >/dev/null; then
  die "python3 is not installed."
fi
PYVER=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  die "Python ${PYVER} found; 3.11+ required."
fi
ok "Python ${PYVER}"

# 2. Verify port is free (skip if our own service already has it).
if ss -tlnp 2>/dev/null | grep -E "[:.]${PORT}\b" >/dev/null; then
  if systemctl is-active --quiet "${APP_NAME}.service" 2>/dev/null; then
    info "Port ${PORT} held by our own service; stopping for reinstall."
    systemctl stop "${APP_NAME}.service" || true
  else
    die "Port ${PORT} is in use by another process. Free it before installing."
  fi
fi
ok "Port ${PORT} is available"

# 3. nginx warning.
if systemctl is-active --quiet nginx 2>/dev/null; then
  warn "nginx is running. This app does not use nginx; Pi-hole owns 80/443. Coexistence should be fine on port ${PORT} but verify your nginx config doesn't conflict."
fi

# 4. Create system user.
if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd -r -s /usr/sbin/nologin -d "$APP_DIR" "$APP_USER"
  ok "Created system user '${APP_USER}'"
else
  ok "System user '${APP_USER}' already exists"
fi

# 5. Copy app into /opt/roundbreak-career.
info "Syncing app to ${APP_DIR}"
mkdir -p "$APP_DIR"
# rsync preserves perms, excludes dev artifacts and the .env so we don't clobber secrets.
rsync -a --delete \
  --exclude='.git/' --exclude='.venv/' --exclude='__pycache__/' \
  --exclude='instance/career.sqlite3*' --exclude='instance/uploads/' \
  --exclude='backups/' --exclude='.env' --exclude='.backup_token' \
  "$SRC_DIR"/ "$APP_DIR"/
mkdir -p "$APP_DIR/instance" "$APP_DIR/instance/uploads" "$APP_DIR/backups"

chown -R "${APP_USER}:${APP_GROUP}" "$APP_DIR"
ok "App synced"

# 6. Virtualenv + deps.
info "Setting up virtualenv"
if [[ ! -d "${APP_DIR}/.venv" ]]; then
  sudo -u "$APP_USER" python3 -m venv "${APP_DIR}/.venv"
fi
sudo -u "$APP_USER" "${APP_DIR}/.venv/bin/pip" install --upgrade pip wheel >/dev/null
sudo -u "$APP_USER" "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
ok "Dependencies installed"

# 7. Collect first-run config.
info "Configuring app — answers default to sensible values for LAN install"
ENV_FILE="${APP_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
  warn "Existing .env found at ${ENV_FILE}; reusing values, will not overwrite secrets."
  set -a; source "$ENV_FILE"; set +a
  ADMIN_USER="${ADMIN_USER:-$(ask 'Admin username' "${HUNTER_USER}")}"
  read -rp "Reset admin password? [y/N]: " RESET
  if [[ "$RESET" =~ ^[Yy] ]]; then
    ADMIN_PASS="$(ask_secret 'New admin password')"
  else
    ADMIN_PASS=""
  fi
  VAULT_PATH="${OBSIDIAN_VAULT_PATH:-$DEFAULT_VAULT}"
  COOKIE_SECURE="${SESSION_COOKIE_SECURE:-False}"
else
  ADMIN_USER="$(ask 'Admin username' "${HUNTER_USER}")"
  ADMIN_PASS="$(ask_secret 'Admin password (hidden)')"
  [[ -z "$ADMIN_PASS" ]] && die "Password cannot be empty."
  VAULT_PATH="$(ask 'Obsidian vault path' "${DEFAULT_VAULT}")"
  echo
  echo "SESSION_COOKIE_SECURE=True forces the login cookie to HTTPS-only."
  echo "For LAN-only HTTP install set this to False; flip to True after adding HTTPS."
  if ask_yn "Set SESSION_COOKIE_SECURE=True (HTTPS-only cookie)?" "N"; then
    COOKIE_SECURE="True"
  else
    COOKIE_SECURE="False"
  fi
fi

# 8. Generate secrets if missing, write .env.
SECRET_KEY="${SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')}"
BACKUP_TOKEN="${BACKUP_TOKEN:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')}"

cat > "$ENV_FILE" <<EOF
# Generated by setup.sh — edit with care.
SECRET_KEY=${SECRET_KEY}
BACKUP_TOKEN=${BACKUP_TOKEN}
SESSION_COOKIE_SECURE=${COOKIE_SECURE}
OBSIDIAN_VAULT_PATH=${VAULT_PATH}
ADMIN_USER=${ADMIN_USER}
EOF
chown "${APP_USER}:${APP_GROUP}" "$ENV_FILE"
chmod 600 "$ENV_FILE"
ok ".env written"

# 9. Write backup token to its own file (mode 600).
echo -n "$BACKUP_TOKEN" > "${APP_DIR}/.backup_token"
chown "${APP_USER}:${APP_GROUP}" "${APP_DIR}/.backup_token"
chmod 600 "${APP_DIR}/.backup_token"
ok "Backup token written"

# 10. Bootstrap database & create/reset admin.
info "Bootstrapping database"
sudo -u "$APP_USER" "${APP_DIR}/.venv/bin/python" - <<PY
from werkzeug.security import generate_password_hash
from app import create_app
from app.db import create_user
app = create_app()
admin_user = "${ADMIN_USER}"
admin_pass = """${ADMIN_PASS}"""
if admin_pass:
    with app.app_context():
        create_user(admin_user, generate_password_hash(admin_pass))
        print(f"  admin user '{admin_user}' set")
else:
    print("  admin password unchanged")
PY
ok "Database ready"

# 11. Generate PWA icons (if missing).
info "Generating PWA icons"
sudo -u "$APP_USER" "${APP_DIR}/.venv/bin/python" -m app.scripts.make_icons || warn "Icon generation failed; PWA install icons may be missing."

# 12. Vault access.
info "Configuring vault access"
if [[ ! -d "$VAULT_PATH" ]]; then
  info "Creating starter vault at $VAULT_PATH"
  mkdir -p "$VAULT_PATH"/{"00 - Inbox","10 - Career/Project Stories","10 - Career/Network Notes","10 - Career/Interview Prep","20 - Technical Reference/Stress Analysis","20 - Technical Reference/Fatigue and DaDT","20 - Technical Reference/FEA Notes","20 - Technical Reference/Materials","20 - Technical Reference/Standards and Regs","30 - Book Notes","40 - Lessons Learned","99 - Archive","_templates"}

  cat > "$VAULT_PATH/_templates/Project Story.md" <<'TPL'
---
type: project-story
status: draft
keywords: []
---
# {{title}}

## Situation
## Task
## Action
## Result
## Technical deep-dive
TPL
  cat > "$VAULT_PATH/_templates/Contact Note.md" <<'TPL'
---
type: contact
company:
warmth:
---
# {{name}}
## How we met
## Notes
## Follow-ups
TPL
  cat > "$VAULT_PATH/_templates/Book Note.md" <<'TPL'
---
type: book
author:
status: queued
rating:
---
# {{title}}
## Why I'm reading
## Key takeaways
## Quotes
TPL
  cat > "$VAULT_PATH/_templates/Lesson Learned.md" <<'TPL'
---
type: lesson
date: {{date:YYYY-MM-DD}}
project:
---
# Lesson — {{title}}
## Context
## What happened
## What I'd do differently
TPL

  if id "$HUNTER_USER" >/dev/null 2>&1; then
    chown -R "${HUNTER_USER}:${HUNTER_USER}" "$VAULT_PATH"
  fi
  ok "Starter vault created"
fi

# 12a. Add career to hunter group + setgid on vault root.
if id "$HUNTER_USER" >/dev/null 2>&1; then
  usermod -aG "$HUNTER_USER" "$APP_USER"
  # Setgid ensures Obsidian-created files inherit the hunter group, so 'career' keeps read access.
  chmod g+rs "$VAULT_PATH"
  find "$VAULT_PATH" -type d -exec chmod g+s {} \; 2>/dev/null || true
  ok "Vault permissions configured (career added to ${HUNTER_USER} group; setgid set)"
else
  warn "User '${HUNTER_USER}' not found; skipping group/setgid setup. Ensure '${APP_USER}' can read ${VAULT_PATH}."
fi

# 13. Install systemd unit.
info "Installing systemd unit"
install -m 0644 "${APP_DIR}/deploy/${APP_NAME}.service" "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable "${APP_NAME}.service" >/dev/null

# 14. Start service and verify.
info "Starting ${APP_NAME}.service"
systemctl restart "${APP_NAME}.service"
sleep 2
if systemctl is-active --quiet "${APP_NAME}.service"; then
  ok "Service active"
else
  systemctl status "${APP_NAME}.service" --no-pager || true
  die "Service failed to start. Check journalctl -u ${APP_NAME}.service"
fi

# Health check.
if curl -sf "http://localhost:${PORT}/login" >/dev/null; then
  ok "HTTP healthcheck passed"
else
  warn "HTTP healthcheck failed — service may need a moment, retry: curl http://localhost:${PORT}/login"
fi

# 15. Install career-user crontab for nightly backup.
info "Installing nightly backup cron in '${APP_USER}' crontab"
CRON_LINE="0 2 * * * curl -s -X POST -H \"X-Backup-Token: \$(cat ${APP_DIR}/.backup_token)\" http://localhost:${PORT}/backup > /dev/null 2>&1"
if crontab -u "$APP_USER" -l 2>/dev/null | grep -F "${APP_DIR}/.backup_token" >/dev/null; then
  ok "Cron entry already present"
else
  (crontab -u "$APP_USER" -l 2>/dev/null || true; echo "$CRON_LINE") | crontab -u "$APP_USER" -
  ok "Cron installed"
fi

LAN_IP="$(hostname -I | awk '{print $1}')"
cat <<EOF

$(color 32 "════════════════════════════════════════════════════════════")
$(color 32 "  Roundbreak Career is up.")
$(color 32 "════════════════════════════════════════════════════════════")

  LAN URL:    http://${LAN_IP}:${PORT}/
  Admin:      ${ADMIN_USER}
  Service:    sudo systemctl status ${APP_NAME}
  Logs:       sudo journalctl -u ${APP_NAME} -f
  Backups:    ${APP_DIR}/backups/
  Vault:      ${VAULT_PATH}

  First 10 minutes:
    1.  Open the URL above on a laptop/phone and log in.
    2.  Sidebar → Capture: jot 3 things that have nagged at you.
    3.  Companies: skim the seeded list, drop priorities you don't want.
    4.  Contacts: add 2 people you actually know in industry (warmth 3-5).
    5.  Stories: open the E-6 cowl panel stub, write the Situation block.
    6.  Stories: write the Technical deep-dive — the hidden interview gold.
    7.  Learning: confirm Bruhn/Flabel/Roark's/Voss priorities.
    8.  Actions: mark the AIAA membership action 'in progress'.
    9.  Vault: open the starter folder tree, drop a project-story note.
   10.  Review: scroll to current month; the auto-counts are zero — that's the baseline.

  PWA note:
    Service workers will NOT register over plain HTTP from a non-localhost
    origin (Chrome/Edge). Add an iOS home-screen shortcut on the phone
    for the LAN URL; full offline + install button arrive when you put
    HTTPS in front (Tailscale Funnel, Cloudflare Tunnel + Access, or a
    reverse proxy with a cert). After adding HTTPS, set
    SESSION_COOKIE_SECURE=True in ${APP_DIR}/.env and restart the service.

EOF
