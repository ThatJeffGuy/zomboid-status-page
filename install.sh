#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "run this as root" >&2
  exit 1
fi

echo "== creating pzhelper system user =="
if ! id pzhelper >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin pzhelper
else
  echo "pzhelper already exists, skipping"
fi
usermod -aG docker pzhelper

echo "== installing pz-helper systemd unit =="
cp "$HERE/helper/pz-helper.service" /etc/systemd/system/pz-helper.service
systemctl daemon-reload
systemctl enable --now pz-helper.service
sleep 1
systemctl --no-pager status pz-helper.service || true

echo "== installing sudoers rule =="
visudo -c -f "$HERE/helper/sudoers-pz-helper"
install -m 0440 -o root -g root "$HERE/helper/sudoers-pz-helper" /etc/sudoers.d/pz-helper
echo "sudoers rule installed"

echo
echo "== next steps (manual) =="
echo "1. Generate the two secrets (see README.md section 2) -- SESSION_SECRET via"
echo "   'python3 -c \"import secrets; print(secrets.token_urlsafe(48))\"',"
echo "   ADMIN_PASSWORD_HASH via the throwaway-container one-liner in the README."
echo "2. Deploy -- either:"
echo "     Portainer: Stacks -> Add stack -> Web editor, paste docker-compose.yml,"
echo "     add ADMIN_PASSWORD_HASH and SESSION_SECRET under Environment variables,"
echo "     pick the right environment, Deploy."
echo "   or CLI:"
echo "     cd $HERE && cp .env.example .env   # paste the two secrets in"
echo "     docker compose up -d --build"
echo "3. Confirm it's listening:"
echo "     curl -s localhost:8080/api/status | head"
echo "4. Once you have a domain, put a reverse proxy in front of it on port 8080."
