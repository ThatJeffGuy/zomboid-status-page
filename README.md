# Zomboid server status page

Live, semi-interactive status page and admin panel for a self-hosted
Project Zomboid server -- deployed for the public, designed for community
server admins.

**Live example:** https://zomboid.wubcord.app/

- Interactive live map: uses the server's own interactivity logs to plot
  approximate player positions. A player who's off the depicted map area
  gets placed in an unused corner of the image rather than dropped.
- Admin panel overrides for the maintenance automation -- save, restart, and
  run a mod-update check manually, on top of whatever's scheduled.
- Map is moderator-interactive: right-click a player to kick, ban,
  whitelist, or teleport.
- Map has a chat relay dock when viewed fullscreen.
- Interactive patch notes / announcements / FAQ, editable live from the
  admin panel -- no rebuild needed.
- Site title, credit line, and community links are all editable/configurable
  -- rename and relink as you need for your own server.

A FastAPI web app (online/offline, player count, mod freshness, connect
info, a live map, live chat, and a world-info blurb) plus a login-gated
admin panel (reboot, force mod check, kick/ban, whitelist, teleport,
broadcast, and a live content editor) for a Project Zomboid dedicated
server running in Docker.

## What works out of the box

- Live status (online/offline, player count, names) via RCON.
- Live chat feed and an approximate live player map, read from the game
  server's own logs.
- Admin actions: reboot (with in-game warnings), force save, kick/ban,
  whitelist add/remove, teleport, broadcast -- all over RCON.
- A "Site Content" editor in the admin panel for the public page's title,
  credit line, and the three world-info blurbs (Server News / The Story So
  Far / Help &amp; FAQ) -- edits are live, no rebuild needed.

## Optional integrations (not included -- bring your own scripts)

Two features are driven by host-side scripts this repo does **not**
include, because they're specific to how each server operator automates
their own box. See [zomboid-scripts](https://github.com/ThatJeffGuy/zomboid-scripts)
and [zomboid-storm-events](https://github.com/ThatJeffGuy/zomboid-storm-events)
for reference implementations you can adapt:

- **Mod-check / auto-restart history** (`CARETAKING_LOG`) -- if you have a
  script that periodically checks for mod updates and restarts the server,
  point `CARETAKING_LOG` at its log file and it'll show up as "mod state" /
  "last restart" on the status page. The expected log format is a tail of
  lines like `YYYY-MM-DD HH:MM:SS  <message>`, where `<message>` is one of:
  `mod state: fresh|stale|unknown`, `=== run start (dry_run=<bool>
  force=<bool>) ===`, `run complete: restarted successfully`, or
  `run complete: recovered from a crashed server process`. See
  `app/status_cache.py`'s `_parse_caretaking_log` for the exact parsing.
- **Random event / "storm" scheduling** (`EVENTS_DIR`) -- if you run a
  rotation of scripted world-modifier events, point `EVENTS_DIR` at a
  directory containing `.active_storm` (`<script-basename> <end-epoch>`),
  `.storm_queue` (space-separated script basenames, next up first),
  `.storm_days` (`<iso-week-id> <Day> <Day> <Day>`), `.last_storm_end`, and
  `.last_storm_start_date`, plus one `storm-<id>.sh` file per event defining
  `STORM_NAME="..."` and `STORM_BLURB="..."`. See `app/events.py` for the
  exact format and scheduling logic it expects.

Without either of these, the corresponding UI (mod state, restart reason,
next/active event) just stays hidden -- the app degrades gracefully, it's
not required to run.

There's also an easter egg (`app/live_map.py`'s player-map dots turn into a
face + sound after 10 rapid clicks) that looks for
`app/static/wubby-face.gif` and a handful of `app/static/*.mp3` files. Those
aren't included in this repo (they're someone's personal likeness/voice
clips) -- drop your own in at those paths if you want it, or ignore it; it
silently no-ops if the files aren't there.

## Layout

- `app/` -- the FastAPI web app (runs in the `zomboid-status` container).
- `helper/pz-helper.py` -- a small privileged daemon that runs **outside
  Docker, directly on the host**, as a low-privilege system user. It's the
  only thing allowed to call `docker inspect`/`docker logs` or invoke the
  optional caretaking/event scripts, and only those exact operations -- the
  web app container never gets a Docker socket or root.
- `install.sh` -- one-time host setup (creates the helper's system user,
  installs its systemd unit and sudoers rule).

## Requirements

- A Project Zomboid dedicated server running in Docker, with RCON enabled.
- Docker + Docker Compose on the host.
- Root access on the host, for the one-time privileged helper setup below.

## Setup

### 1. Edit `docker-compose.yml`

The volume paths are placeholders -- point them at your own files:

- `/path/to/rcon.yaml` -- RCON host/port/password. Either a bare password
  file, or an `rcon-cli`-style YAML (`default:\n  password: "..."`).
- `/path/to/caretaking.log` -- optional, see "Optional integrations" above.
- `.../Server/YourServerName.ini` -- your PZ server's own ini file (used to
  read the public connect name/port/password).
- The `storms`, `db`, and `Logs` mounts point at your Zomboid server's own
  `config/storms` (optional, see above), `config/db` (for the whitelist
  count), and `config/Logs` (for live chat/map) directories.
- `content-overrides` -- a writable directory for live admin content edits;
  create it and make it writable by the container's `appuser` before first
  use (its in-container uid won't match a host user, so `chmod 777` is the
  pragmatic fix):
  ```bash
  mkdir -p /opt/app/zomboid-status/content-overrides
  chmod 777 /opt/app/zomboid-status/content-overrides
  ```

### 2. Host prep for the privileged helper (as root, once)

Only needed if you want the optional mod-check/event admin buttons to work
(they call the helper, which is the only thing allowed to run those scripts
as root). Run `bash install.sh`, or do it by hand:

```bash
useradd --system --no-create-home --shell /usr/sbin/nologin pzhelper
usermod -aG docker pzhelper

cp helper/pz-helper.service /etc/systemd/system/pz-helper.service
systemctl daemon-reload
systemctl enable --now pz-helper.service
systemctl status pz-helper.service --no-pager
ls -l /run/pz-helper/helper.sock

visudo -c -f helper/sudoers-pz-helper
install -m 0440 -o root -g root helper/sudoers-pz-helper /etc/sudoers.d/pz-helper
```

Edit `helper/sudoers-pz-helper` first if your caretaking/event script paths
differ from the defaults (`/opt/app/zomboid/config/storms/...`) -- or set
`PZ_CARETAKING_SCRIPT`/`PZ_EVENTS_SCRIPT` env vars on the `pz-helper`
service to match, and update the sudoers rule to match those same paths.

The helper's socket **must** exist before the app container starts --
Docker will otherwise silently create an empty directory at that bind-mount
path, which breaks the helper.

### 3. Generate secrets

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # SESSION_SECRET

docker run --rm -it python:3.12-slim bash -c \
  "pip install -q bcrypt && python3 -c \"
import bcrypt, getpass
print(bcrypt.hashpw(getpass.getpass('admin password: ').encode()[:72], bcrypt.gensalt()).decode())
\""   # ADMIN_PASSWORD_HASH
```

(`helper/gen_secrets.py` does both interactively in one step if you'd
rather run that instead.)

### 4. Deploy

Either via Portainer (Stacks -> Add stack -> Web editor, paste
`docker-compose.yml`, add `ADMIN_PASSWORD_HASH`/`SESSION_SECRET` under
Environment variables, Deploy), or plain CLI:

```bash
cp .env.example .env   # fill in ADMIN_PASSWORD_HASH / SESSION_SECRET
docker compose up -d --build
curl -s localhost:8080/api/status | head
```

Put a reverse proxy in front of it for HTTPS once you have a domain --
`network_mode: host` means it's directly reachable on the host's IP at
`APP_PORT` (default `8080`) in the meantime.

### 5. Customize

Log in with your admin password at `/login`, then use the "Site Content"
card to set your site title, credit line, and the three world-info blurbs.
Edit `app/static/style.css`/`app/templates/base.html` directly for anything
not covered by the admin panel (community links, colors, etc).

## Notes

- The RCON command syntax in `app/main.py` (`banuser`/`adduser`/
  `removeuserfromwhitelist`/etc.) is the standard PZ RCON set, but hasn't
  been verified against every server build -- run `help` from the admin
  console once logged in to confirm, and adjust if yours differs.
- The web app container runs as a non-root user with no Docker socket -- it
  can't touch Docker or other containers directly; that's all proxied
  through `pz-helper`.

## License

CC0 1.0 Universal -- see [LICENSE](LICENSE). Public domain, no attribution
required, though a link back is always appreciated.
