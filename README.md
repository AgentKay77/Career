# Roundbreak Career

A self-hosted, single-user career-development PWA for an aerospace
structural engineer planning a 12-18 month transition to industry. Runs
on a Raspberry Pi, reads an Obsidian vault, never phones home.

It's a focused operating system for a specific kind of work:

- **Companies** — target list with priority, status, and notes.
- **Contacts** — relationship CRM with warmth, last-contact, follow-up dates.
- **Stories** — STAR + a separate **Technical** block (the hidden interview gold), with a practice/reveal mode.
- **Learning** — three-column Queued / Reading / Done; references the vault for full notes.
- **Actions** — drag-drop Kanban with high/medium/low priorities and target dates.
- **Salary data** — H1B / Levels / conversation-source library with p25 / median / p75 calc per filter.
- **Resume versions** — upload, mark current, download.
- **Monthly review** — wins/misses/lessons/focus, with auto-counted progress tiles.
- **Vault browser** — read-only renderer for Obsidian notes: KaTeX, code highlighting, `[[wikilinks]]`, backlinks.
- **Unified search** — FTS5 across every entity plus the vault filesystem.

## Architecture

```
┌─ Pi 5 Trixie ───────────────────────────────────────────────┐
│                                                             │
│  systemd: roundbreak-career.service                         │
│    └── gunicorn (User=career, 2 workers, 0.0.0.0:5001)      │
│          └── Flask app factory                              │
│                ├── SQLite (instance/career.sqlite3 + WAL)   │
│                │     + FTS5 + history triggers              │
│                ├── Vault reader (watchdog → in-mem index)   │
│                └── /opt/roundbreak-career/backups/          │
│                                                             │
│  Obsidian vault (/home/hunter/obsidian-vault) — read-only   │
│  cron @ 02:00 → POST /backup with token from .backup_token  │
└─────────────────────────────────────────────────────────────┘
```

**Why this stack?**

- **Flask 3 + Jinja + HTMX + Alpine** keeps everything server-rendered,
  no build step, no npm, no transpilation. Pages stay fast on a Pi over LAN.
- **SQLite + FTS5** because a single user generates kilobytes a year, not
  gigabytes. Everything is in one file you can `scp` somewhere safer if you
  want a second copy.
- **Obsidian vault as source of truth for notes.** Flask reads markdown
  but never writes — Obsidian is where you type. The app surfaces vault
  content alongside the structured records. Two views, one truth.
- **No nginx, no Tailscale assumption.** Pi-hole owns 80/443 on this box;
  Tailscale isn't installed. Plain HTTP on `:5001` is the v1 deployment
  mode. Remote access is documented but not required.

## Prerequisites

- Raspberry Pi 5 (or any Debian 13 / Trixie machine), Python 3.11+, SSD recommended.
- Port `5001` free. Existing services on this Pi (Pi-hole 53/80/443, Starboard 5000, pi-health 5002, Finance Hub 5003) are untouched.
- (Optional) Syncthing on phone/desktop pointed at `/home/hunter/obsidian-vault` so Obsidian-mobile edits propagate to the Pi.

## Install

```bash
git clone https://github.com/agentkay77/career.git
cd career
sudo bash setup.sh
```

The installer:

1. Verifies Python 3.11+ and that port 5001 is free.
2. Creates the unprivileged `career` system user.
3. Syncs the app to `/opt/roundbreak-career/`, creates a venv, installs deps.
4. Prompts for admin username, admin password, vault path, and `SESSION_COOKIE_SECURE`.
5. Generates `SECRET_KEY` and `BACKUP_TOKEN` (urlsafe, 32 chars each).
6. Writes `.env` (mode 600) and `.backup_token` (mode 600, both owned by `career`).
7. Bootstraps the DB (schema + seed in one transaction).
8. Generates PWA icons via Pillow.
9. Creates the starter vault if it didn't exist; otherwise just ensures setgid + group access.
10. Installs the systemd unit, enables it, starts the service, verifies HTTP.
11. Installs a nightly backup cron in the `career` user's crontab.

Re-running `setup.sh` is safe — it upgrades code/deps without clobbering
the database, secrets, or uploaded resumes.

## `SESSION_COOKIE_SECURE` (read this before installing)

Flask's default is `True`, which means the login cookie is only set on
HTTPS connections. Over plain LAN HTTP, the cookie silently never sets
and you'll loop on the login page.

| Install mode                         | Set                              |
| ------------------------------------ | -------------------------------- |
| LAN-only HTTP on `http://<pi-ip>:5001` | `SESSION_COOKIE_SECURE=False`    |
| With HTTPS (Tailscale Funnel, Cloudflare Tunnel, reverse proxy) | `SESSION_COOKIE_SECURE=True` |

`setup.sh` defaults the answer to `False` for the LAN install flow. The
code default is the safer `True`, so a forgotten `.env` doesn't downgrade
security. Flip it back to `True` in `.env` after you add HTTPS, then
`sudo systemctl restart roundbreak-career`.

## PWA limitations on plain HTTP

Service workers and "Install app" require HTTPS from a non-localhost
origin. On the LAN install:

- **Chrome / Edge / desktop browsers** — won't register the service
  worker. No "Install" button, no offline caching. The app works fine
  online, just not installable.
- **iOS Safari** — "Add to Home Screen" still works, but the resulting
  icon launches the app without service-worker caching, so it needs the
  network to load.

To get full PWA behavior (install button + offline caching), put HTTPS
in front:

| Option | What you get |
| --- | --- |
| **Tailscale Funnel** | Free TLS over your tailnet. Easiest path. |
| **Cloudflare Tunnel + Access** | Public URL with auth in front; no port-forwarding. |
| **Reverse proxy (Caddy, Traefik) with a cert** | Local LAN HTTPS via mDNS or your DNS. |

PWA assets are built correctly regardless — they activate the moment
HTTPS is in place, no code change needed.

## First 10 minutes (after install)

1. Open `http://<pi-ip>:5001/` and log in.
2. **Capture**: jot 3 things that have been nagging at you.
3. **Companies**: skim the seeded list, drop priorities you don't want.
4. **Contacts**: add 2 people you actually know in industry (warmth 3-5).
5. **Stories**: open the E-6 cowl panel stub, write the Situation block.
6. **Stories**: now write the **Technical deep-dive** — this is the hidden interview gold most candidates skip.
7. **Learning**: confirm the P1 books (Bruhn / Flabel / Roark's / Voss).
8. **Actions**: mark the AIAA membership action `in_progress`.
9. **Vault**: open the starter folder tree, drop a project-story note.
10. **Review**: scroll to current month; auto-counts are zero — that's the baseline.

## Daily / weekly / monthly workflow

- **Daily (2 min)**: Dashboard → This Week. Knock one item, log one
  interaction, move one Kanban card. Done. Capture anything fresh via
  `/capture`.
- **Weekly (15 min)**: Sweep "Quiet 60+ days". Practice one story via
  Random Practice. Add or refine a salary data point.
- **Monthly (30 min)**: `/review`. Pre-filled auto-counts. Write wins,
  misses, lessons, next-month focus. Save. Future you will read these.

## Backups

- Token-authed nightly POST `/backup` writes a JSON dump to
  `/opt/roundbreak-career/backups/career_YYYY-MM-DD_HHMM.json`.
- Token at `/opt/roundbreak-career/.backup_token` (mode 600, owned by `career`).
- Cron in the `career` user's crontab (not root):
  ```cron
  0 2 * * * curl -s -X POST -H "X-Backup-Token: $(cat /opt/roundbreak-career/.backup_token)" http://localhost:5001/backup > /dev/null 2>&1
  ```
- `/backups` web UI (login-authed) lets you download or restore. Restore
  takes a pre-restore snapshot first, then replays the JSON.
- Token comparison is constant-time (`hmac.compare_digest`).
- Off-Pi copies: `rsync /opt/roundbreak-career/backups/ user@elsewhere:`,
  Syncthing the backups dir to a desktop, or just `scp` periodically.

## Adding fields or tables later

Drop a numbered SQL file in `app/migrations/`:

```
app/migrations/001_add_pipeline_field.sql
app/migrations/002_create_followup_template.sql
```

On next service restart, `db.py` finds any unapplied numbered files,
runs each inside its own transaction, and inserts a row into
`schema_migrations`. Re-running is idempotent.

## Remote access (post-install, optional)

- **Tailscale**: `curl -fsSL https://tailscale.com/install.sh | sh`,
  `sudo tailscale up`. Reach the app at
  `http://<pi-machine-name>:5001/`. For HTTPS:
  `sudo tailscale serve --https=443 http://localhost:5001` or use Funnel
  for public access.
- **Cloudflare Tunnel**: `cloudflared tunnel` pointing at
  `http://localhost:5001`, behind Cloudflare Access for auth on top.

## Troubleshooting

| Symptom | Diagnose |
| --- | --- |
| **Port 5001 in use** | `sudo ss -tlnp \| grep :5001` — kill the squatter or change `gunicorn_conf.py` and the service file. |
| **Login loops endlessly on plain HTTP** | `SESSION_COOKIE_SECURE=True` in `.env`. Set to `False`, restart. |
| **No install-app button on Chrome** | Plain-HTTP non-localhost origin. Add HTTPS — see PWA section. |
| **Vault notes missing** | `sudo -u career ls -la /home/hunter/obsidian-vault` — check the `career` user has read access. `chmod g+rs` the vault root, `usermod -aG hunter career`. |
| **Service won't start** | `sudo journalctl -u roundbreak-career -n 50 --no-pager`. |
| **Vault shows stale list** | Watchdog should pick it up live; if not, restart the service. |
| **Backup endpoint 401** | Cron uses `$(cat .backup_token)` — verify file exists, mode 600, owned `career`. |

## Coexistence on this Pi

This app uses port **5001 only**. It does not touch:

- Pi-hole (53 / 80 / 443)
- Starboard (5000)
- pi-health (5002)
- Finance Hub (5003)

systemd manages all per-app users (`starboard`, `pihealth`, `finance`,
`career`) the same way: unprivileged, no shell, own data dir under
`/opt/<app>/`.

## Decisions (resolved during build)

- **No nginx**: Pi-hole owns 80/443; gunicorn binds 5001 directly.
- **Wikilinks**: custom InlineProcessor in `app/markdown_ext.py`. The
  PyPI `markdown-wikilinks` package matches different syntax. Basename
  collisions resolve to the lexicographically-first match and the link
  is flagged with a CSS class for visual cue.
- **History triggers** fire on markdown-bearing columns only; non-text
  edits don't pollute `field_history`.
- **Backup format**: JSON dump (not raw `.sqlite3`) — survives FTS
  triggers being rebuilt on restore. Restore keeps a `.sqlite3`
  snapshot before clobbering, named `pre_restore_<ts>.sqlite3`.

## Known limitations (v1)

- PWA install button / offline caching require HTTPS — see PWA section.
- Wikilink basename collisions resolve to the first match in
  lexicographic order (with an "ambiguous" CSS class on the link).
- Single user. No public registration, no sharing, no multi-tenant
  features. Adding a second user would mean adding role checks and a
  registration flow this codebase deliberately doesn't have.

## Tests

```bash
.venv/bin/pytest
```

Covers: app factory, schema/seed bootstrap, migration runner with
idempotency, login (good/bad password, logout), every route returns
200/302, CRUD persists for each entity, FTS5 hits on seeded content,
vault renders math + code blocks, wikilink resolution (ok / ambiguous /
broken), backup endpoint token auth (reject without, accept via header
or query, JSON validates), and `SESSION_COOKIE_SECURE` env override
honored.

## License

Personal use. No license granted to third parties.
