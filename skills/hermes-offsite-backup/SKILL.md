---
name: hermes-offsite-backup
description: Set up encrypted off-machine Hermes backups.
version: 1.0.0
author: Terp AI Labs
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [hermes, backup, operations, encryption]
    related_skills: [hermes-health-check]
---

# Hermes Off-Machine Backup

Nightly `hermes backup`, encrypted with `age` to a public key whose private half lives elsewhere, copied to a destination the user picks. It runs as a zero-token cron job that only messages the user when something fails.

## When to Use

- The user wants Hermes backed up somewhere other than the machine it runs on.
- Before relying on an always-on Hermes host for anything important.

## Procedure

1. **Ask; don't guess.** You need three things from the user:
   - an **age public key** (`age1…`). Its private key must *not* be on this machine.
   - a **destination**: an rclone remote path (for example `b2:my-bucket/hermes`) or an scp target (`user@host:/backups/hermes`).
   - a **local staging directory** (default `~/hermes-backups`).

2. **Check the tools** with the terminal tool:

   ```bash
   age --version
   rclone version || command -v scp
   ```

   If `age` is missing, tell the user how to install it for their OS rather than installing it yourself.

3. **Install the script.** Copy `scripts/offsite-backup.sh` from this skill into `~/.hermes/scripts/offsite-backup.sh`. Fill in the three values at the top, then run `chmod 700` on it.

4. **Test it once by hand** and show the user the result:

   ```bash
   bash ~/.hermes/scripts/offsite-backup.sh && echo "backup ok"
   ```

   The script prints nothing on success and one line on failure.

5. **Schedule it with no model involved.** Output is delivered only when the script prints something, which happens only on failure:

   ```bash
   hermes cron create "0 3 * * *" --no-agent --script offsite-backup.sh \
     --name offsite-backup --deliver telegram
   ```

   Use whatever delivery target the user prefers, or `local`.

6. **Explain the restore path** and have the user try it once, on the machine that holds the private key:

   ```bash
   age -d -i ~/.config/age/key.txt -o hermes-backup.zip hermes-backup-YYYYMMDD-HHMMSS.zip.age
   hermes import hermes-backup.zip
   ```

## Verification

- The encrypted file appears at the destination after the manual run.
- `hermes cron list` shows `offsite-backup` as active, and `hermes cron runs offsite-backup` shows a clean run the next morning.
- A test restore on another machine succeeds. An untested backup is a hope, not a backup.

## Pitfalls

- A full `hermes backup` includes API keys and bot tokens. Never copy the unencrypted zip off the machine. The script deletes the plaintext zip after encrypting it.
- `hermes backup` is safe to run while Hermes is running. Never copy `state.db` by hand instead.
- Keep the age private key off this host. If the host is compromised, the backups should stay unreadable.
- `-k` in the script prunes old local zips. Pruning remote copies is the destination's job (for example a bucket lifecycle rule).
