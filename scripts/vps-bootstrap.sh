#!/usr/bin/env bash
# ============================================================
# scripts/vps-bootstrap.sh
# ------------------------------------------------------------
# Any Debian 12 / Ubuntu 24.04 VPS (tested on Hetzner CX22-class
# hardware) -> production Hermes in ~10 minutes.
#
# What it does:
#   1. Creates a non-root `hermes` user
#   2. Installs prereqs: curl, jq, git, python3-venv, nodejs, age, rclone, ufw, fail2ban
#   3. Installs Hermes via official installer (sha256-pinned, override available)
#   4. Sets up Caddy (reverse proxy + auto TLS)
#   5. Sets up UFW (your ACTUAL sshd port, 80, 443) + fail2ban with a
#      working jail.local — refuses to enable UFW if it cannot determine
#      the SSH port
#   6. Installs the guide repo at /opt/hermes-optimization-guide
#   7. Symlinks all skills into ~hermes/.hermes/skills/
#   8. Copies templates/systemd/ unit files; enables them ONLY if the
#      Hermes install actually succeeded
#   9. Drops templates/caddy/Caddyfile as a reference
#  10. Leaves .env + config.yaml as stubs the operator fills in
#
# HOW TO RUN THIS SCRIPT SAFELY (do not pipe it from `main`):
#   The README publishes this file's sha256 at a tagged release. Fetch the
#   tagged copy, verify it, then run:
#
#     curl -fsSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/<TAG>/scripts/vps-bootstrap.sh \
#       -o vps-bootstrap.sh
#     echo "<README-PUBLISHED-SHA256>  vps-bootstrap.sh" | sha256sum -c -
#     sudo bash vps-bootstrap.sh
#
#   Or clone the repo at the tag and run from the checkout:
#     git clone --depth 1 --branch <TAG> https://github.com/OnlyTerp/hermes-optimization-guide /opt/hermes-optimization-guide
#     sudo bash /opt/hermes-optimization-guide/scripts/vps-bootstrap.sh
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
# 2. Node.js (required by MCP servers) — sha256-pinned setup script
# ------------------------------------------------------------
if ! command -v node >/dev/null 2>&1; then
  log "Installing Node.js 22 (LTS) via pinned NodeSource setup script..."
  NODESOURCE_URL="https://deb.nodesource.com/setup_22.x"
  PINNED_NODESOURCE_SHA256="575583bbac2fccc0b5edd0dbc03e222d9f9dc8d724da996d22754d6411104fd1"
  if [ "${HERMES_ALLOW_UNPINNED:-0}" = "1" ]; then
    warn "HERMES_ALLOW_UNPINNED=1 — running NodeSource setup script WITHOUT hash verification."
    curl -fsSL "$NODESOURCE_URL" | bash -
  else
    curl -fsSL "$NODESOURCE_URL" -o /tmp/nodesource-setup.sh
    echo "${PINNED_NODESOURCE_SHA256}  /tmp/nodesource-setup.sh" | sha256sum -c - \
      || die "NodeSource setup script hash mismatch — NodeSource rotated it. Review the new script, re-pin PINNED_NODESOURCE_SHA256, or re-run with HERMES_ALLOW_UNPINNED=1 after inspection."
    bash /tmp/nodesource-setup.sh
  fi
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
# 6. Hermes install (as hermes user) — PINNED, not curl|bash
# ------------------------------------------------------------
# We download the official installer, verify its sha256 against a pinned
# value, and only then execute it. If upstream rotates the script, the hash
# check fails LOUDLY and nothing runs — update PINNED_INSTALL_SHA256 below
# after reviewing the new installer (the daily pin-watch CI job opens an
# issue when the live installer hash drifts from this pin).
#
# Operator escape hatch: if you have inspected the new installer yourself,
# HERMES_ALLOW_UNPINNED=1 skips verification for this run.
HERMES_BIN=/home/hermes/.local/bin/hermes
INSTALL_URL="https://hermes-agent.nousresearch.com/install.sh"
PINNED_INSTALL_SHA256="0582d9b1562efcb6e0ac62f4451021667830b830a72ce7d91eaea9fee8b6c09b"
HERMES_INSTALL_OK=0
if [ ! -x "$HERMES_BIN" ]; then
  log "Installing Hermes (pinned installer)..."
  if [ "${HERMES_ALLOW_UNPINNED:-0}" = "1" ]; then
    warn "HERMES_ALLOW_UNPINNED=1 — running Hermes installer WITHOUT hash verification."
    if sudo -u hermes bash -c 'curl -fsSL "'"${INSTALL_URL}"'" | bash'; then
      HERMES_INSTALL_OK=1
    fi
  else
    if sudo -u hermes bash -c '
      set -e
      curl -fsSL "'"${INSTALL_URL}"'" -o /tmp/hermes-install.sh
      echo "'"${PINNED_INSTALL_SHA256}"'  /tmp/hermes-install.sh" | sha256sum -c - \
        || { echo "FATAL: installer hash mismatch — upstream rotated install.sh. Review it, re-pin PINNED_INSTALL_SHA256, or re-run with HERMES_ALLOW_UNPINNED=1 after inspection." >&2; exit 1; }
      bash /tmp/hermes-install.sh
    '; then
      HERMES_INSTALL_OK=1
    fi
  fi
  [ "$HERMES_INSTALL_OK" = "1" ] || warn "Hermes installer failed or hash mismatch — install manually and re-run."
else
  HERMES_INSTALL_OK=1
fi

# Expose the CLI system-wide so the systemd units (ExecStart=/usr/local/bin/hermes)
# and root shells can find it without a login shell for the hermes user.
if [ -x "$HERMES_BIN" ]; then
  ln -sf "$HERMES_BIN" /usr/local/bin/hermes
fi

# ------------------------------------------------------------
# 7. Skill symlinks + config scaffolding
# ------------------------------------------------------------
log "Linking skills from the guide into ~hermes/.hermes/skills/..."
# Current ~/.hermes layout (per the v0.20 docs): config.yaml, .env, SOUL.md,
# memories/, skills/, sessions/, cron/, logs/, checkpoints/, cache/.
sudo -u hermes mkdir -p \
  /home/hermes/.hermes/skills \
  /home/hermes/.hermes/logs \
  /home/hermes/.hermes/memories \
  /home/hermes/.hermes/sessions \
  /home/hermes/.hermes/cron \
  /home/hermes/.hermes/checkpoints

shopt -s nullglob
for skill_dir in "$GUIDE_DIR"/skills/*/*/; do
  name=$(basename "$skill_dir")
  ln -sfn "$skill_dir" "/home/hermes/.hermes/skills/$name"
done
shopt -u nullglob
# Prune symlinks whose target vanished (skill removed/renamed upstream)
find /home/hermes/.hermes/skills -maxdepth 1 -xtype l -delete
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
# Fill these in — Hermes won't start without at least one provider key
# (ANTHROPIC_API_KEY or GOOGLE_API_KEY / GEMINI_API_KEY are the common picks).
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
# Optional providers referenced by the seeded cost-optimized.yaml aliases —
# uncomment and fill in the ones you route to.
#KIMI_API_KEY=            # kimi-coding provider (Moonshot/Kimi K3)
#GLM_API_KEY=             # zai provider (GLM-5.x)
#XAI_API_KEY=             # xai provider (Grok)
#DEEPSEEK_API_KEY=        # deepseek provider (V4 class)
EOF
  chmod 600 /home/hermes/.hermes/.env
  chown hermes:hermes /home/hermes/.hermes/.env
fi

# ------------------------------------------------------------
# 8. systemd units — enabled ONLY if the Hermes install succeeded
# ------------------------------------------------------------
install -m 0644 "$GUIDE_DIR/templates/systemd/hermes.service"           /etc/systemd/system/hermes.service
install -m 0644 "$GUIDE_DIR/templates/systemd/hermes-dashboard.service" /etc/systemd/system/hermes-dashboard.service
systemctl daemon-reload
if [ "$HERMES_INSTALL_OK" = "1" ]; then
  log "Enabling hermes systemd units..."
  systemctl enable hermes.service hermes-dashboard.service
else
  warn "Hermes binary missing/failed — units installed but NOT enabled. Install Hermes, then: systemctl enable hermes hermes-dashboard"
fi

# ------------------------------------------------------------
# 9. Caddy reference config
# ------------------------------------------------------------
if [ ! -f /etc/caddy/Caddyfile.hermes.reference ]; then
  install -m 0644 "$GUIDE_DIR/templates/caddy/Caddyfile" /etc/caddy/Caddyfile.hermes.reference
  warn "Reference Caddyfile at /etc/caddy/Caddyfile.hermes.reference — edit and copy to /etc/caddy/Caddyfile, then 'systemctl reload caddy'."
fi

# ------------------------------------------------------------
# 10. UFW + fail2ban — sshd-port-aware (no lockouts)
# ------------------------------------------------------------
# THE LOCKOUT GUARD: we never assume sshd listens on 22. We parse every
# `Port` directive from /etc/ssh/sshd_config and /etc/ssh/sshd_config.d/*,
# allow EACH of them, and REFUSE to enable UFW if we cannot determine at
# least one port. An operator on a non-default port who runs the old
# `ufw allow 22` version gets locked out; this block exists because of that.
log "Hardening: determining sshd port(s) before touching UFW..."
SSH_PORTS=$(grep -hE '^\s*Port\s+[0-9]+' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null \
  | awk '{print $2}' | sort -un)
if [ -z "$SSH_PORTS" ]; then
  if [ -f /etc/ssh/sshd_config ]; then
    # No explicit Port directive: sshd default is 22, but only trust that
    # when the config file genuinely exists (default install).
    SSH_PORTS="22"
    log "No explicit 'Port' directive in sshd_config — assuming default 22."
  else
    die "Cannot determine sshd port (no /etc/ssh/sshd_config and no Port directives). UFW NOT enabled — refusing to risk locking you out. Open your SSH port manually: ufw allow <port>/tcp && ufw --force enable"
  fi
fi

log "Hardening: UFW (allowing ssh on: $(echo "$SSH_PORTS" | tr '\n' ' '))..."
# Additive + idempotent on purpose: never `ufw reset` here — a reset wipes any
# operator-added rules and transiently drops the firewall on re-runs.
if ! ufw status | grep -q "Status: active"; then
  ufw default deny incoming
  ufw default allow outgoing
fi
for p in $SSH_PORTS; do
  ufw allow "${p}/tcp" comment "ssh"
done
ufw allow 80/tcp  comment 'http-acme-challenge'
ufw allow 443/tcp comment 'https'
ufw --force enable

log "Hardening: fail2ban with a working sshd jail..."
# Minimal Debian 12 images commonly fail the stock sshd jail without
# `backend = systemd`; write an explicit jail.local and point it at the
# port(s) we just parsed.
cat > /etc/fail2ban/jail.local <<EOF
[sshd]
enabled  = true
port     = $(echo "$SSH_PORTS" | paste -sd, -)
backend  = systemd
maxretry = 5
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban
if systemctl is-active --quiet fail2ban; then
  log "fail2ban active (sshd jail on port(s): $(echo "$SSH_PORTS" | tr '\n' ' '))."
else
  warn "fail2ban did not come up clean — check: journalctl -u fail2ban -n 50"
fi

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
