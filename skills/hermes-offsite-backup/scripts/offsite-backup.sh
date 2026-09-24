#!/usr/bin/env bash
# Encrypted off-machine backup of Hermes (installed by the hermes-offsite-backup skill).
#
# Prints NOTHING on success and one line on failure, so a
#   hermes cron create "0 3 * * *" --no-agent --script offsite-backup.sh --deliver telegram
# job only messages you when something is wrong. No model is ever called.
set -euo pipefail

# --- fill these in -----------------------------------------------------------
AGE_RECIPIENT="age1replace-with-your-public-key"   # public key; the private key lives elsewhere
METHOD="rclone"                                     # "rclone" or "scp"
DEST="remote:bucket/hermes"                         # rclone: remote:path   scp: user@host:/path
STAGING="${HOME}/hermes-backups"                    # local working directory
KEEP_LOCAL=3                                        # encrypted copies to keep locally
# -----------------------------------------------------------------------------

fail() { echo "offsite-backup FAILED on $(hostname): $*"; exit 1; }
trap 'fail "line ${LINENO}: ${BASH_COMMAND}"' ERR

HERMES_BIN="$(command -v hermes || true)"
[ -n "$HERMES_BIN" ] || HERMES_BIN="${HOME}/.local/bin/hermes"
[ -x "$HERMES_BIN" ] || fail "hermes command not found"
command -v age >/dev/null 2>&1 || fail "age is not installed"
case "$AGE_RECIPIENT" in age1replace*) fail "AGE_RECIPIENT is not configured" ;; esac

mkdir -p "$STAGING"
chmod 700 "$STAGING"
stamp="$(date +%Y%m%d-%H%M%S)"
zip="${STAGING}/hermes-backup-${stamp}.zip"

# A full backup includes API keys: encrypt immediately, never ship the plain zip.
"$HERMES_BIN" backup -o "$zip" >/dev/null 2>&1 || fail "hermes backup failed"
age -r "$AGE_RECIPIENT" -o "${zip}.age" "$zip"
rm -f -- "$zip"

case "$METHOD" in
  rclone) rclone copy --quiet "${zip}.age" "$DEST" ;;
  scp)    scp -q "${zip}.age" "${DEST%/}/" ;;
  *)      fail "METHOD must be rclone or scp" ;;
esac

# Keep only the newest KEEP_LOCAL encrypted copies in the staging directory.
find "$STAGING" -maxdepth 1 -name 'hermes-backup-*.zip.age' -type f -print \
  | sort -r | tail -n +"$((KEEP_LOCAL + 1))" \
  | while IFS= read -r old; do rm -f -- "$old"; done
