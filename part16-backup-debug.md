# Part 16: Backup, Import, and `/debug` — Your Recovery Kit

*First-class backup/import, debug bundles, update preflights, and the hardening details you need before you let Hermes run unattended.*

---

## `hermes backup` and `hermes import`

### Why This Is a Big Deal

Until v0.9, migrating a Hermes install between machines meant `rsync -a ~/.hermes user@new-host:`. Which mostly worked — except for:

- Absolute paths baked into config (Docker mounts, log paths, skill script paths)
- Machine-specific provider endpoints (local Ollama, LAN-only LLM servers)
- SQLite session DB file locks if the source machine was still running
- Secrets you didn't actually want to copy (old dev keys, disabled provider API keys)

`hermes backup` produces a single portable zip that handles the storage-safety part, and `hermes import` replays it on the new machine.

### Creating a Backup

```bash
hermes backup
```

Produces `~/hermes-backup-<timestamp>.zip`. The archive uses SQLite's `backup()` API for database files, so it is **consistent even while Hermes is running** (WAL-mode safe) — no need to stop the gateway first for the backup itself.

| What's inside | Notes |
|---------------|-------|
| `config.yaml` | Your full configuration |
| `.env`, `auth.json` | Your secrets — the backup is a **literal copy of your home**, so guard the archive like a password-manager vault |
| `state.db` | The session database (sessions, message history, session store) |
| `skills/`, `memories/`, `plugins/` | Skills (incl. executable scripts), memory files, installed plugins |
| pairing data, cron jobs | Keep the access-control and scheduled-job state |
| — | Everything else under `HERMES_HOME` |

**Deliberately excluded from the archive:**

- `*.db-wal`, `*.db-shm`, `*.db-journal` — SQLite's live sidecar files. The `*.db` snapshot is already consistent; shipping sidecars alongside it could let a restore see a half-committed state.
- `checkpoints/` — per-session trajectory snapshots (see Checkpoints below). Hash-keyed and regenerated per session; they wouldn't port cleanly to another install anyway.
- The `hermes-agent` code itself. This is a user-data backup, not a repo snapshot.

### Options

| Flag | Description |
|------|-------------|
| `-o`, `--output <path>` | Write the zip to a specific path instead of the default backups location |
| `-q`, `--quick` | Quick snapshot: only critical state files (`config.yaml`, `state.db`, `.env`, auth, cron jobs). Much faster than a full backup |
| `-l`, `--label <name>` | Label for the snapshot (only used with `--quick`) |

### Common Recipes

**Full backup before a risky upgrade or migration:**

```bash
hermes backup -o ~/hermes-$(hostname).zip
```

Treat that archive like a password manager vault — it contains every key.

**Quick pre-upgrade snapshot with a label:**

```bash
hermes backup --quick --label "pre-upgrade"
```

**Scheduled backups to a mounted drive:**

```bash
hermes cron create \
  --deliver local \
  --schedule "0 3 * * *" \
  "run: hermes backup --output /mnt/backups/hermes-\$(date +%F).zip"
```

---

### Importing a Backup

On the target machine:

```bash
hermes import ~/hermes-backup-2026-08-18-030000.zip
```

All files in the archive overwrite the corresponding files in your Hermes home. `--force` only skips the confirmation prompt that fires when the target already has a Hermes installation:

```bash
hermes import ~/hermes-backup-2026-08-18-030000.zip --force
```

> ⚠️ **Stop the gateway before importing.** The importer does not coordinate with running processes; importing under a live gateway can produce conflicts. The backup itself is safe to take while running — the *import* is what wants a quiet machine.

### Cross-Platform Notes

- **Sessions** live in `state.db`; the SQLite backup is portable across OSes.
- **Skills with shell scripts** — Unix permissions (`+x`) are preserved on Linux/macOS archives. On native Windows, script-based skills may need WSL to run, depending on the script.
- **Machine-specific config** — after import, re-check absolute paths in `config.yaml` on the new host (Docker mounts, provider base URLs, SSH endpoints). The backup does not rewrite those; you adjust them after restore.

---

## Checkpoints and `/rollback` — the per-project safety net

Backups cover *machines*; checkpoints cover *working trees*. Hermes can automatically snapshot a project before destructive operations and restore it with a single command. Powered by a **shared shadow git store** at `~/.hermes/checkpoints/store/` — your real project `.git` is never touched, and git's content-addressable object DB deduplicates across projects and turns.

**Opt-in by default.** Enable per session or globally:

```bash
hermes chat --checkpoints
```

```yaml
# ~/.hermes/config.yaml
checkpoints:
  enabled: true
```

Snapshots are taken automatically before `write_file`/`patch` and before destructive terminal commands (`rm`, `mv`, `sed -i`, `truncate`, `dd`, output redirects, `git reset`/`clean`/`checkout`, ...) — at most one per directory per turn.

In-session commands:

| Command | Definition |
|---------|------------|
| `/rollback` | List all checkpoints with change stats |
| `/rollback <N>` | Restore to checkpoint N, keeping your hand-edits |
| `/rollback <N> --all` | Full restore — overwrites hand-edits too |
| `/rollback diff <N>` | Preview the diff between N and current state |
| `/rollback <N> <file>` | Restore a single file from N |

CLI for the store itself (safe to run any time, agent doesn't need to be running):

```bash
hermes checkpoints                # status: size, project count, per-project breakdown
hermes checkpoints prune          # sweep: drop orphans/stale, GC, enforce size cap
hermes checkpoints clear          # wipe the whole store (asks first)
hermes checkpoints clear-legacy   # drop v1→v2 migration archives
```

Auto-maintenance sweeps `~/.hermes/checkpoints/` at startup (default: `auto_prune: true`, `retention_days: 7`, at most once per 24h); `hermes checkpoints prune` forces a sweep immediately. Full knobs: `enabled`, `max_snapshots` (20), `max_total_size_mb` (500), `max_file_size_mb` (10).

Why checkpoints matter for your backup story: a rollback will not resurrect files you deleted *before* a checkpoint, and backup archives exclude the checkpoint store — filesystem safety per-machine, archive safety cross-machine. Use both.

---

## `hermes sessions export` — Share a Session Without Sharing Your Keys

Backups are for *you*; exports are for *everyone else*. The session store is `~/.hermes/state.db`; `hermes sessions export` turns any slice of it into a file:

```bash
hermes sessions export backup.jsonl                                    # JSONL (default)
hermes sessions export --format md --session-id <id> --redact          # readable per-session markdown
hermes sessions export --format html --newer-than 1w --source telegram # one self-contained HTML file
```

Formats: **`jsonl`** (default — one JSON object per session), **`md`** / **`qmd`** (one file per session into `~/.hermes/session-exports` plus a `manifest.jsonl` with paths, message counts, lineage, SHA-256s), **`html`** (single self-contained transcript with collapsible tool output), and **`trace`** (tool-call traces, secret-redacted by default, built to leave the machine).

Selection knobs work across formats: `--session-id` for one session, or the full `prune` filter set for bulk — `--older-than`/`--newer-than`, `--source telegram`, `--model`, `--min-/--max-messages`, etc. `--redact` scrubs API keys/tokens/credentials from the exported content. `--only user-prompts` exports just your prompts (great for building prompt libraries). Write to `-` for stdout.

- **Always `--redact` before sharing.** A raw session log is a credential-disclosure incident waiting to happen ([Part 19](./part19-security-playbook.md)).
- Great for bug reports, blog write-ups, and "how did the agent do this?" postmortems.

While you're in session-hygiene mode:

```bash
hermes sessions prune              # delete old ended sessions (default: older than 90 days)
hermes sessions optimize           # non-destructive: merge FTS5 segments + VACUUM
hermes sessions repair             # fix a malformed state.db schema
hermes sessions stats              # how big is the store, anyway
```

`hermes sessions import` also exists (`--from codex ...` for Codex exports) — session portability works both ways.

---

## `/debug`, `hermes debug share`, `hermes dump` — the diagnostic flow

When something goes weird, the old flow was: grep through `~/.hermes/logs/`, paste 800 lines into a GitHub issue, hope you got the right ones. The modern flow is three tools with one rule: **the report leaves your machine already redacted.**

### `/debug` (CLI and messaging)

```text
You → /debug
  ✓ System info (OS, Python, Hermes version)
  ✓ Recent agent, gateway, GUI/dashboard, and desktop logs
  ✓ API key status (redacted)
  → Uploading…
  → Shareable link(s):
      https://paste.rs/XXXX
```

Available in both the CLI **and** messaging. It builds the report, uploads it to a public paste service (paste.rs, then dpaste.com), and gives you a short link you can paste into a bug report. Everything lands on the paste service **redacted by default** — secrets are stripped before upload.

### `hermes debug share` — the CLI twin

Same bundler, explicit flags:

```bash
hermes debug share              # upload debug report, print URL
hermes debug share --lines 500  # more log lines per file (default 200)
hermes debug share --expire 30  # paste lifetime in days (default 7)
hermes debug share --nous       # private Nous diagnostics storage instead of public paste
hermes debug share --local      # print the report locally, upload nothing
```

- `--nous` uploads the same bundle to **Nous-internal diagnostics storage** — the returned viewer link is for the Nous team and auto-deletes after 14 days. Use it when Nous support asks for a private diagnostic bundle.
- `--no-redact` exists; do not use it casually.
- The report includes system info (OS, Python, Hermes version), recent agent/gateway/dashboard/desktop logs (512 KB cap per file), and whether API keys are set (values never included).
- To attach a bundle to an issue yourself without uploading, `--local` prints it straight to the terminal.

### `hermes dump` — the paste-ready plain-text summary

```bash
hermes dump              # compact text: version, OS, model, providers, toolsets, MCP count,
                         # gateway status, cron jobs, skills — literally designed to be
                         # copy-pasted into a GitHub issue or Discord
hermes dump --show-keys  # add redacted API-key prefixes (first/last 4 chars)
```

`hermes dump` never leaves your machine — it prints. Paste the whole block into a bug report: it contains ~everything a maintainer needs and is formatted to be read by a human in one glance. `--show-keys` shows only the first and last 4 characters of each key.

### `hermes doctor` — interactive diagnostics

`hermes doctor` is the interactive companion: it checks your install and surface the specific checks you should fix before you open an issue. Dump is for sharing; `doctor` is for inspecting.

---

## Importing From Other Agents

Tired of rebuilding? Current Hermes migrations:

- **Claude Code / Codex CLI** — `hermes import-agent claude-code` (or `codex`) imports `CLAUDE.md`/`AGENTS.md` instructions to memory entries, `Bash(...)` permission rules to `command_allowlist`/`approvals.deny`, `mcpServers` → `mcp_servers` in `config.yaml`, and skill directories into `~/.hermes/skills/`. Always previews before applying; API keys/credentials are never imported.
- **OpenClaw / ClawdBot / Moltbot** — `hermes claw migrate` reads `~/.openclaw` and writes `~/.hermes`, covering 30+ categories (persona, memory, skills, providers, messaging platforms, MCP servers, TTS, ...). Previews with `--dry-run`, refuses conflicts unless `--overwrite`, only touches secrets with an explicit `--migrate-secrets`, and writes a pre-migration restore-point zip to `~/.hermes/backups/pre-migration-*.zip` (restorable with `hermes import`).

Both can be tested safely: `--dry-run` writes nothing.

---

## Pluggable Context Engine + `/compress <topic>`

Covered in more depth in [Part 14](./part14-fast-mode-watchers.md). TL;DR:

### Custom context engine

The context engine controls what happens when a conversation approaches the token limit — the built-in `compressor` engine uses lossy summarization; plugin engines replace that strategy:

```yaml
# ~/.hermes/config.yaml
context:
  engine: "compressor"   # built-in default; set to a plugin's name to swap
```

Plugin engines are never auto-activated — you must set `context.engine` explicitly (browse/select via `hermes plugins` → Provider Plugins → Context Engine). See Part 14 for a minimal implementation.

### `/compress <topic>`

The context compressor (Part 6) accepts an optional focus topic — preserve detail relevant to the topic, aggressively compress everything else. Full walkthrough in [Part 14](./part14-fast-mode-watchers.md#compress-topic--guided-compression).

---

## Security Hardening Notes

Hardening items worth keeping in mind for the v0.20 era:

### The approval layer (`approvals:`)

```yaml
# ~/.hermes/config.yaml
approvals:
  mode: smart        # smart (default) | manual | off
```

- `smart` (default) — an auxiliary LLM assesses whether a flagged command is actually dangerous: low-risk auto-approved for that command only, genuinely risky denied, uncertain escalates to you. `manual` prompts on every flagged command; `off` skips checks entirely (only in trusted, sandboxed environments).
- **`approvals.deny` — your own hardline blocklist.** A list of glob patterns that block matching terminal commands *unconditionally* — even under yolo/off. This is the user-editable counterpart to the built-in hardline patterns:
  ```yaml
  approvals:
    deny:
      - "git push --force*"
  ```
- `approvals.denial_breaker_threshold` (default 3) stops the agent from retrying variants of a command the reviewer keeps denying — after that many denials it's told to stop and report.
- `approvals.smart_policy` appends your own rules to the reviewer's instructions (tighten or relax for your environment).
- `sudo` / `rm -rf` still require explicit approval regardless of service tier, gateway platform, or cron runner — `/fast` does not bypass approvals.

### Update preflight: `hermes update --check`

Before a major upgrade:

```bash
hermes update --check     # am I behind origin/main?
hermes backup --quick --label "pre-upgrade"
```

`hermes update` already takes a pre-update backup itself — `quick` (lightweight state snapshot) by default; `--backup` forces a *full* zip; `updates.pre_update_backup: quick | full | off` sets the permanent mode. After a successful update, Hermes restarts running gateway profiles automatically.

### Redaction is the default everywhere

- `hermes debug share` uploads **redacted** unless you pass `--no-redact`.
- `hermes dump --show-keys` shows only 4-character key prefixes, otherwise just `set`/`not set`.
- Exports get `--redact`.

<a id="approval-bypass-for-trusted-subagents"></a>
### Approval posture flows to subagents

Subagents spawned by the orchestrator inherit the parent session's approval posture by default. If the parent session is in `yolo` mode, so is the subagent. If the parent is in `ask` mode, subagents prompt the user on dangerous calls. Override per delegation:

```python
delegate_task(
    goal="Research X",
    approvals="ask",        # override inherited posture
    toolsets=["file"],
)
```

Adapter-level hardening (webhook signature validation, SSRF filters on outbound media, redaction of env values in logs) is per-adapter — see the messaging-platform sections in [Part 15](./part15-new-platforms.md) and the current official adapter docs for the live state of each.

---

## What's Next

You've now seen the backup/debug slice of the current feature surface:

- [Part 12 — Web Dashboard](./part12-web-dashboard.md)
- [Part 13 — Nous Tool Gateway](./part13-tool-gateway.md)
- [Part 14 — Fast Mode & Background Watchers](./part14-fast-mode-watchers.md)
- [Part 15 — New Platforms (35+ adapters: A2A, Buzz, IRC, Photon, Teams...)](./part15-new-platforms.md)
- [Part 23 — Tenacity Stack](./part23-tenacity-stack.md)

If you installed fresh on v0.20.4 and walked through [Part 1](./part1-setup.md) and this series, you've got the most capable Hermes configuration to date — and the recovery kit to keep it that way.