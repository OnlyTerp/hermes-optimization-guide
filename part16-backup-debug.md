# Part 16: Backup, Import, and `/debug` — Your Recovery Kit

*New in Hermes v0.9.0 and v0.10.0. Two long-missing features finally shipped: first-class backup/import of your whole Hermes install, and a built-in diagnostic bundler you can share in bug reports.*

---

## `hermes backup` and `hermes import`

### Why This Is a Big Deal

Until v0.9, migrating a Hermes install between machines meant `rsync -a ~/.hermes user@new-host:`. Which mostly worked — except for:

- Absolute paths baked into config (Docker mounts, log paths, skill script paths)
- Machine-specific provider endpoints (local Ollama, LAN-only LightRAG)
- SQLite session DB file locks if the source machine was still running
- Secrets you didn't actually want to copy (old dev keys, disabled provider API keys)

`hermes backup` produces a portable archive that handles all of that. `hermes import` replays it on the new machine with interactive conflict resolution.

### Creating a Backup

```bash
hermes backup
```

Produces `~/.hermes/backups/hermes-YYYY-MM-DD-HHMMSS.tar.zst` containing:

| Path | Included | Notes |
|------|----------|-------|
| `config.yaml` | yes | Machine-specific paths (Docker mounts, local provider URLs) are rewritten to portable placeholders |
| `.env` | yes (redacted by default) | Secret values are zeroed; key names kept. Pass `--include-secrets` to include values in plaintext (use with care) |
| `memories/` | yes | All memory files |
| `skills/` | yes | All skills including executable scripts and references |
| `sessions.db` | yes | SQLite DB is dumped via `VACUUM INTO` so it's consistent even with a running gateway |
| `plugins/` | yes | Both CLI and dashboard plugins |
| `logs/` | no by default | Use `--include-logs` if you need them for debugging |
| `auth.json` | no | Never backed up — re-authenticate on the new machine |

### Options

| Flag | Description |
|------|-------------|
| `--output <path>` | Write to a specific path instead of the default backups directory |
| `--include-secrets` | Include `.env` values in plaintext (default: redacted) |
| `--include-logs` | Include `logs/` in the archive |
| `--exclude <path>` | Exclude a specific subpath (repeatable) |
| `--no-sessions` | Skip `sessions.db` (useful for sharing skill/memory libraries) |

### Common Recipes

**Full portable backup for migrating to a new machine:**

```bash
hermes backup --include-secrets --output ~/hermes-$(hostname).tar.zst
```

Treat that archive like a password manager vault — it contains every key.

**Share skills + memory with a teammate (no secrets, no sessions):**

```bash
hermes backup --no-sessions --output ~/hermes-share.tar.zst
```

Safe to email. Contains your prompting knowledge and procedural skills, nothing private.

**Scheduled backups to a mounted drive:**

```bash
hermes cron create \
  --deliver local \
  --schedule "0 3 * * *" \
  "run: hermes backup --output /mnt/backups/hermes-\$(date +%F).tar.zst"
```

---

### Importing a Backup

On the target machine:

```bash
hermes import ~/hermes-2026-04-17-030000.tar.zst
```

The importer walks through each section interactively:

```text
config.yaml
  ✓ No existing config. Importing.

.env
  ⚠ 12 existing keys, 18 in backup.
    [m] Merge (keep existing for duplicates)
    [r] Replace (backup overrides everything)
    [s] Skip
    [d] Diff before deciding
  Choice [m]:

memories/
  ⚠ 47 existing files, 52 in backup, 14 differ.
    [m] Merge (newer file wins)
    [r] Replace
    [s] Skip
    [d] Diff each conflicting file
  Choice [m]:

skills/
  ✓ Non-conflicting, importing 23 skills.

sessions.db
  ⚠ Existing sessions.db has 1,247 sessions. Backup has 892.
    [m] Merge (session IDs already deduped — safe)
    [r] Replace
    [s] Skip
  Choice [m]:
```

### Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Print what would happen without touching disk |
| `--strategy <merge\|replace\|skip>` | Non-interactive default for all conflicts |
| `--only <path>` | Import only a subpath (e.g. `--only skills/`) |
| `--rewrite-paths` | Re-scan config for paths that don't exist on this machine and prompt to fix them |

### Cross-Platform Notes

- **Sessions DB** — merges are deduplicated by session UUID; no risk of collisions.
- **Skills with shell scripts** — Unix permissions (`+x`) are preserved inside the archive. On Windows, you'll need WSL to run script-based skills anyway.
- **Config path rewriting** — on import, Hermes detects stale paths (e.g. `/home/alice/...` on a machine where `alice` doesn't exist) and prompts you to fix them before writing.
- **LightRAG data** — lives outside `~/.hermes`, so it's not in the backup. Back up `~/.hermes/lightrag` separately with `tar` or re-ingest on the new machine.

---

## `/debug` and `hermes debug share`

### The New Diagnostic Flow

When something goes weird, the old flow was: grep through `~/.hermes/logs/`, paste 800 lines into a GitHub issue, hope you got the right ones. The v0.10 flow is:

```text
You → /debug
  Collecting diagnostics…
  ✓ Agent version: v0.10.0 (v2026.4.16)
  ✓ Platform: Linux 6.8.0 / Python 3.12.3
  ✓ Gateway: running (3 adapters connected)
  ✓ Last 200 lines of agent.log
  ✓ Last 200 lines of errors.log
  ✓ Config snapshot (secrets redacted)
  ✓ Active session metadata (no message content)

  Bundle: ~/.hermes/debug/debug-2026-04-17-030000.tar.gz

  Upload with: hermes debug share ~/.hermes/debug/debug-2026-04-17-030000.tar.gz
```

Then:

```bash
hermes debug share ~/.hermes/debug/debug-2026-04-17-030000.tar.gz
```

That uploads the bundle to the Hermes public debug endpoint and returns a short URL you can paste into a bug report. The upload:

- Redacts all `.env` secrets before leaving your machine
- Strips message content by default — only metadata (session ID, model, message count, tool calls)
- Expires after 14 days
- Is only readable by Nous support staff with the link

### What Gets Included

| Section | Content |
|---------|---------|
| `system.json` | OS, Python, Hermes version, installed extras |
| `config.yaml` | Your config, with `.env` values redacted |
| `logs/agent.log` | Last N lines (default 200, `--lines` to change) |
| `logs/errors.log` | Last N lines |
| `logs/gateway.log` | Last N lines |
| `gateway-state.json` | Connected platforms, PIDs, last event times |
| `session-metadata.json` | Session IDs, models, message counts (no content) |
| `pip-freeze.txt` | Exact dependency versions |

### Opt-In for More

```bash
/debug --full
```

Includes message content for the active session, recent session tool call arguments, and LLM request/response pairs (with auth headers stripped). Only use this when a bug genuinely requires reproducing your exact prompt chain — it's more revealing than the default bundle.

### Without the Share Step

`/debug` always creates the local bundle. `hermes debug share` is a separate step. If you don't want to upload, just attach the tarball directly to a GitHub issue yourself.

---

## Pluggable Context Engine + `/compress <topic>`

Covered in more depth in [Part 14](./part14-fast-mode-watchers.md). TL;DR:

### Custom context engine

Plug-and-play replacement for what gets injected into each agent turn:

```yaml
# ~/.hermes/config.yaml
context_engine: my-custom-engine
```

Use it to filter memory by project, pre-summarize tool output, pull from LightRAG or a private vector DB, etc. See Part 14 for a minimal implementation.

### `/compress <topic>`

The context compressor (Part 6) now takes an optional focus topic:

```text
You → /compress migration to Fly.io
  Compressing 47 messages with focus: "migration to Fly.io".
  Kept 6 messages verbatim, summarized 41 into 2 bullet blocks.
```

Preserves detail relevant to the topic and aggressively compresses everything else. Perfect for salvaging a long debugging session after you've solved the problem and want to keep the decision trail but ditch 200 exploratory tool calls.

---

## Security Hardening (v0.9 + v0.10 Notes)

A handful of hardening changes landed in the "everywhere" + "gateway" releases worth calling out explicitly:

### Webhook secrets validated on startup

Every webhook-based adapter (Telegram, BlueBubbles, WeCom, Feishu, WeChat, generic Webhook) now validates its signing secret at gateway startup. A missing/empty/weak secret produces a startup error instead of silently accepting forged requests.

Generate strong ones:

```bash
openssl rand -hex 32
```

### SSRF protection on outbound media

WeChat, Telegram, and BlueBubbles download inbound media through a validator that blocks:
- Private/loopback IPs (`10.0.0.0/8`, `192.168.0.0/16`, `127.0.0.0/8`, etc.)
- Link-local addresses (`169.254.0.0/16`)
- Metadata endpoints (`169.254.169.254` — AWS/GCP IMDS)
- `file://`, `data://`, and other non-HTTP schemes

Set `HERMES_ALLOW_PRIVATE_MEDIA_URLS=true` only on trusted networks where your agent legitimately needs to fetch from an internal host.

### Env values redacted in all logs

Every log line now runs through a redactor that replaces values of known secret env vars with `<redacted:VAR_NAME>` before printing. Prevents accidental secret leakage to log aggregators or shared debug bundles.

### `sudo` and `rm -rf` still require explicit approval

Nothing new, but worth restating: dangerous commands still trigger the approval UI (`ask` / `yolo` / `deny`) regardless of service tier, gateway platform, or cron runner. `/fast` does not bypass approvals.

### Approval bypass for trusted subagents

Subagents spawned by the orchestrator now inherit the parent session's approval posture by default. If the parent session is in `yolo` mode (every tool call auto-approved), so is the subagent. If the parent is in `ask` mode, subagents prompt the user on dangerous calls. Override per delegation:

```python
delegate_task(
    goal="Research X",
    approvals="ask",        # override inherited posture
    toolsets=["file"],
)
```

---

## What's Next

You've now seen the full April 2026 feature surface:

- [Part 12 — Web Dashboard](./part12-web-dashboard.md)
- [Part 13 — Nous Tool Gateway](./part13-tool-gateway.md)
- [Part 14 — Fast Mode & Background Watchers](./part14-fast-mode-watchers.md)
- [Part 15 — New Platforms (iMessage, WeChat, Android)](./part15-new-platforms.md)

If you installed fresh on v0.10.0 and walked through [Part 1](./part1-setup.md) and this series, you're running the most capable Hermes configuration to date.
