---
name: nightly-backup
description: Run `hermes backup`, encrypt, upload to remote storage, prune old backups
when_to_use:
  - Scheduled nightly via cron
  - User requests an explicit backup
  - Before a risky config change
toolsets:
  - terminal
  - file
parameters:
  remote:
    type: string
    description: Remote target. Supports s3://bucket/prefix, b2://bucket/prefix, ssh://user@host:/path, or "local"
    default: "local"
  retain_days:
    type: integer
    default: 30
---

# nightly-backup — Hermes Backup Automation

Thin wrapper around `hermes backup` + encryption + optional remote upload + retention.

## Procedure

1. **Snapshot.** Run:
   ```bash
   hermes backup --output /tmp/hermes-backup-$(date +%Y%m%d-%H%M%S).tar
   ```
   This bundles config, sessions, skills, memory, and cron entries per [Part 16](../../../part16-backup-debug.md).

2. **Encrypt.** Use age (if available) or gpg symmetric:
   ```bash
   BACKUP_PASSPHRASE=$(hermes secrets get BACKUP_PASSPHRASE)
   age -p -o /tmp/hermes-backup-*.tar.age /tmp/hermes-backup-*.tar
   # or
   gpg --batch --yes --symmetric --cipher-algo AES256 \
       --passphrase "$BACKUP_PASSPHRASE" \
       /tmp/hermes-backup-*.tar
   shred -u /tmp/hermes-backup-*.tar
   ```

3. **Upload.** Based on `remote:` parameter:
   - `s3://…` → `aws s3 cp <file> s3://bucket/prefix/`
   - `b2://…` → `rclone copy <file> b2:bucket/prefix/`
   - `ssh://…` → `rsync -av <file> user@host:/path/`
   - `local` → move to `~/.hermes/backups/`

4. **Prune.** Delete anything older than `retain_days`:
   - `s3`: use S3 lifecycle policy if possible; otherwise `aws s3 ls` + age filter
   - `b2`: `rclone delete --min-age ${retain_days}d b2:bucket/prefix/`
   - `ssh`: `ssh host "find /path -mtime +${retain_days} -delete"`
   - `local`: `find ~/.hermes/backups -mtime +${retain_days} -delete`

5. **Verify.** Download a random recent backup and test-decrypt:
   ```bash
   age -d -i ~/.age-backup-key backup.tar.age > /tmp/verify.tar && tar tf /tmp/verify.tar | head -5
   ```
   Fail loud if the verification fails — a backup you can't restore is not a backup.

6. **Report.** Send a line to your configured `notify:` channel:
   ```
   ✔ hermes backup 2026-04-17 — 284 MB, uploaded to s3://backups/hermes/, pruned 3 old
   ```
   On failure, send 🔴 with the specific error and skip pruning (keep old backups until the new one succeeds).

## Cron wiring

```yaml
# ~/.hermes/cron.yaml
- name: nightly-backup
  schedule: "0 3 * * *"
  task: /nightly-backup s3://my-backups/hermes/ 30
  notify: telegram_private
```

## Security notes

- **Never** back up `.env` plaintext — `hermes backup` already excludes it. If you're using a fork, verify with `tar tf backup.tar | grep .env` and bail if it appears.
- The encryption passphrase must live in a separate secret store (not in `.env`), otherwise a stolen Hermes host gets both.
- Rotate the backup passphrase yearly with `skills/security/rotate-secrets`.
