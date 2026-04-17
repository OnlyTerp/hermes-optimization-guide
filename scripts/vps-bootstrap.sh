#!/usr/bin/env bash
# ============================================================
# scripts/vps-bootstrap.sh
# ------------------------------------------------------------
# Hetzner CX22 (or any Debian 12 / Ubuntu 24.04 VPS) -> production
# Hermes in ~10 minutes.
#
# What it does:
#   1. Creates a non-root `hermes` user
#   2. Installs prereqs: curl, jq, git, python3-venv, nodejs, age, rclone, ufw, fail2ban
#   3. Installs Hermes via official installer
#   4. Sets up Caddy (reverse proxy + auto TLS)
#   5. Sets up UFW (22, 80, 443 only) + fail2ban
#   6. Installs the guide repo at /opt/hermes-optimization-guide
#   7. Symlinks all skills into ~hermes/.hermes/skills/
#   8. Copies templates/systemd/ unit files + enables them
#   9. Drops templates/caddy/Caddyfile as a reference
#  10. Leaves .env + config.yaml as stubs the operator fills in
#
# USAGE (as root on a fresh box):
#   curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | bash
#
# Or clone first and run from the repo:
#   git clone https://github.com/OnlyTerp/hermes-optimization-guide /opt/hermes-optimization-guide
#   sudo bash /opt/hermes-optimization-guide/scripts/vps-bootstrap.sh
#
# Non-destructive by default. Re-runnable.
# ============================================================

set -euo pipefail

log()  { printf "\033[1;34m[bootstrap]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[err]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "Run as root (or via sudo)."

# ------------------------------------------------------------
# 1. System packages
# ------------------------------------------------------------
log "Updating apt indexes..."
apt-get update -qq
log "Installing prereqs..."
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  curl ca-certificates gnupg jq git python3-venv python3-pip \
  age rclone ufw fail2ban unattended-upgrades \
  debian-keyring debian-archive-keyring apt-transport-https

# ------------------------------------------------------------
# 2. Node.js (required by MCP servers)
# ------------------------------------------------------------
if ! command -v node >/dev/null 2>&1; then
  log "Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

# ------------------------------------------------------------
# 3. Caddy
# ------------------------------------------------------------
if ! command -v caddy >/dev/null 2>&1; then
  log "Installing Caddy..."
  curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key | \
    gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] \
    https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq
  apt-get install -y -qq caddy
fi

# ------------------------------------------------------------
# 4. hermes user
# ------------------------------------------------------------
if ! id -u hermes >/dev/null 2>&1; then
  log "Creating hermes user..."
  adduser --disabled-password --gecos "" hermes
fi

# ------------------------------------------------------------
# 5. Clone the guide
# ------------------------------------------------------------
GUIDE_DIR=/opt/hermes-optimization-guide
if [ ! -d "$GUIDE_DIR/.git" ]; then
  log "Cloning the optimization guide to $GUIDE_DIR..."
  git clone --depth 1 https://github.com/OnlyTerp/hermes-optimization-guide "$GUIDE_DIR"
else
  log "Updating the optimization guide..."
  git -C "$GUIDE_DIR" pull --ff-only || warn "git pull failed; continuing with current checkout"
fi

# ------------------------------------------------------------
# 6. Hermes install (as hermes user)
# ------------------------------------------------------------
if ! sudo -u hermes bash -c 'command -v hermes >/dev/null 2>&1'; then
  log "Installing Hermes..."
  sudo -u hermes bash -c 'curl -sSL https://install.hermes.nous.ai | bash' \
    || warn "Hermes installer not reachable yet — install manually and re-run."
fi

# ------------------------------------------------------------
# 7. Skill symlinks + config scaffolding
# ------------------------------------------------------------
log "Linking skills from the guide into ~hermes/.hermes/skills/..."
sudo -u hermes mkdir -p /home/hermes/.hermes/skills /home/hermes/.hermes/logs /home/hermes/.hermes/lightrag

for skill_dir in "$GUIDE_DIR"/skills/*/*/; do
  name=$(basename "$skill_dir")
  ln -sfn "$skill_dir" "/home/hermes/.hermes/skills/$name"
done
chown -R hermes:hermes /home/hermes/.hermes

# Drop a stub config if none exists
if [ ! -f /home/hermes/.hermes/config.yaml ]; then
  log "Seeding a cost-optimized config stub..."
  cp "$GUIDE_DIR/templates/config/cost-optimized.yaml" /home/hermes/.hermes/config.yaml
  chown hermes:hermes /home/hermes/.hermes/config.yaml
  warn "Edit /home/hermes/.hermes/config.yaml and /home/hermes/.hermes/.env before starting Hermes."
fi

# Stub .env
if [ ! -f /home/hermes/.hermes/.env ]; then
  cat > /home/hermes/.hermes/.env <<'EOF'
# Fill these in — Hermes won't start without at least ANTHROPIC_API_KEY or GOOGLE_API_KEY.
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
TELEGRAM_ADMIN_BOT_TOKEN=
TELEGRAM_OWNER_ID=
EOF
  chmod 600 /home/hermes/.hermes/.env
  chown hermes:hermes /home/hermes/.hermes/.env
fi

# ------------------------------------------------------------
# 8. systemd units
# ------------------------------------------------------------
log "Installing systemd units..."
install -m 0644 "$GUIDE_DIR/templates/systemd/hermes.service"           /etc/systemd/system/hermes.service
install -m 0644 "$GUIDE_DIR/templates/systemd/hermes-dashboard.service" /etc/systemd/system/hermes-dashboard.service
systemctl daemon-reload
systemctl enable hermes.service hermes-dashboard.service

# ------------------------------------------------------------
# 9. Caddy reference config
# ------------------------------------------------------------
if [ ! -f /etc/caddy/Caddyfile.hermes.reference ]; then
  install -m 0644 "$GUIDE_DIR/templates/caddy/Caddyfile" /etc/caddy/Caddyfile.hermes.reference
  warn "Reference Caddyfile at /etc/caddy/Caddyfile.hermes.reference — edit and copy to /etc/caddy/Caddyfile, then 'systemctl reload caddy'."
fi

# ------------------------------------------------------------
# 10. UFW + fail2ban
# ------------------------------------------------------------
log "Hardening: UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp  comment 'ssh'
ufw allow 80/tcp  comment 'http-acme-challenge'
ufw allow 443/tcp comment 'https'
ufw --force enable

log "Hardening: fail2ban (default jail set)..."
systemctl enable --now fail2ban

# ------------------------------------------------------------
# 11. Unattended upgrades
# ------------------------------------------------------------
log "Enabling unattended-upgrades..."
dpkg-reconfigure -f noninteractive unattended-upgrades

# ------------------------------------------------------------
# Done
# ------------------------------------------------------------
cat <<EOF

============================================================
Bootstrap complete.

Next steps:
  1. Edit /home/hermes/.hermes/.env and fill in API keys.
  2. Review /home/hermes/.hermes/config.yaml (cost-optimized default — swap in
     templates/config/production.yaml or security-hardened.yaml as needed).
  3. Edit /etc/caddy/Caddyfile.hermes.reference (replace *.yourdomain.com),
     copy to /etc/caddy/Caddyfile, then: systemctl reload caddy
  4. Start Hermes:
       systemctl start hermes hermes-dashboard
       systemctl status hermes
  5. Watch logs:
       journalctl -fu hermes

Guide: https://github.com/OnlyTerp/hermes-optimization-guide
============================================================
EOF
