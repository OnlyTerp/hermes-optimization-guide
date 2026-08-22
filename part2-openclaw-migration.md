# Part 2: OpenClaw Migration (Don't Leave Your Knowledge Behind)

*Transfer your skills, memory, config, and personality from OpenClaw to Hermes in one command.*

---

## Why Migrate

Hermes is the successor to OpenClaw. If you've spent weeks or months building up skills, memory files, and configuration in OpenClaw, the migration tool brings all of it over automatically.

**What transfers:**

| What | OpenClaw Location | Hermes Destination |
|------|------------------|-------------------|
| Personality | `workspace/SOUL.md` | `~/.hermes/SOUL.md` |
| Instructions | `workspace/AGENTS.md` | Your `--workspace-target` directory (requires the flag) |
| Memory | `workspace/MEMORY.md` + `workspace/memory/*.md` | `~/.hermes/memories/MEMORY.md` (parsed into entries, merged, deduped) |
| User profile | `workspace/USER.md` | `~/.hermes/memories/USER.md` |
| Skills | `workspace/skills/`, `~/.openclaw/skills/`, `~/.agents/skills/`, `workspace/.agents/skills/` | `~/.hermes/skills/openclaw-imports/` |
| Model config | `agents.defaults.model` | `config.yaml` |
| Provider keys | `models.providers.*.apiKey` | `~/.hermes/.env` (only with `--migrate-secrets`) |
| Custom providers | `models.providers.*` | `config.yaml → custom_providers` (auto-migrates to the canonical `providers:` dict on the next config migration) |
| MCP servers | `mcp.servers.*` | `config.yaml → mcp_servers` (stdio and HTTP/SSE transports) |
| Max turns | `agents.defaults.timeoutSeconds` | `agent.max_turns` (timeoutSeconds / 10) |

> **Note:** Session transcripts, cron job definitions, and plugin-specific data do not transfer. Those are OpenClaw-specific and have different formats in Hermes.

---

## Quick Migration

```bash
# Preview what would happen (no files changed)
hermes claw migrate --dry-run

# Full migration of all compatible settings (API keys NOT included by default)
hermes claw migrate --preset full

# Same, but also bring over allowlisted API keys
hermes claw migrate --preset full --migrate-secrets

# User data only (excludes infrastructure config; still no secrets)
hermes claw migrate --preset user-data
```

The migration reads from `~/.openclaw/` by default. Legacy `~/.clawdbot/` / `~/.moltbot/` directories — and legacy config filenames (`clawdbot.json`, `moltbot.json`) — are detected automatically.

---

## Migration Options

| Option | What It Does | Default |
|--------|-------------|---------|
| `--dry-run` | Preview without writing anything | off |
| `--preset full` | All compatible settings — **no secrets** | yes (default preset) |
| `--preset user-data` | Excludes infrastructure config — still no secrets | off |
| `--migrate-secrets` | Copy allowlisted API keys. **Required even under `--preset full`** — no preset imports secrets silently | off |
| `--overwrite` | Overwrite existing Hermes files on conflicts | refuse to apply when the plan has conflicts |
| `--no-backup` | Skip the pre-migration zip snapshot of `~/.hermes/` (a restore point is written to `~/.hermes/backups/pre-migration-*.zip` by default, restorable with `hermes import`) | off |
| `--source <path>` | Custom OpenClaw directory | `~/.openclaw/` |
| `--workspace-target <path>` | Where to place `AGENTS.md` | none — pass the flag to migrate workspace instructions |
| `--skill-conflict <mode>` | `skip`, `overwrite`, or `rename` | `skip` |
| `--yes` | Skip confirmation prompt | off |

---

## Step-by-Step Walkthrough

### 1. Dry Run First

Always preview before committing:

```bash
hermes claw migrate --dry-run
```

This shows you exactly what files would be created, overwritten, or skipped. Review the output carefully.

### 2. Run the Migration

```bash
hermes claw migrate
```

The tool will:
1. Detect your OpenClaw installation
2. Map config keys to Hermes equivalents
3. Merge memory files (deduplicating entries)
4. Copy skills to `~/.hermes/skills/openclaw-imports/`
5. Migrate allowlisted API keys **only if you passed `--migrate-secrets`** — no preset imports secrets by default
6. Report what was done

### 3. Handle Conflicts

If a skill already exists in Hermes with the same name:

- **`--skill-conflict skip`** (default): Leaves the Hermes version, skips the import
- **`--skill-conflict overwrite`**: Replaces the Hermes version with the OpenClaw version
- **`--skill-conflict rename`**: Creates a `-imported` copy alongside the Hermes version

```bash
# Example: rename on conflict so you can compare
hermes claw migrate --skill-conflict rename
```

### 4. Verify After Migration

```bash
# Check your personality loaded
cat ~/.hermes/SOUL.md

# Check memory entries merged
cat ~/.hermes/memories/MEMORY.md | head -50

# Check skills imported
ls ~/.hermes/skills/openclaw-imports/

# Test the agent
hermes chat -q "What do you remember about me?"

# Verify provider auth / overall health
hermes status
```

> Imported skills and memory take effect in **new sessions**, not the one you're in — open a fresh chat to see them. Once everything checks out, run `hermes claw cleanup` to rename the leftover OpenClaw directories to `.pre-migration/` so they aren't re-detected next time.

---

## What Doesn't Transfer

| Item | Why | What to Do |
|------|-----|-----------|
| Session transcripts | Different format | Archive manually if needed |
| Cron job definitions | Not imported — archived for review | Recreate with `hermes cron create` |
| Plugins, hooks, webhooks | Not imported — archived for review | Use the plugins guide / `hermes webhook` |
| OpenClaw-specific files (`IDENTITY.md`, `TOOLS.md`, `HEARTBEAT.md`, `BOOTSTRAP.md`, memory backend, …) | No direct Hermes equivalent | Archived under `~/.hermes/migration/openclaw/<timestamp>/archive/`; merge into `SOUL.md` / context files / skills manually |

Everything is archived to `~/.hermes/migration/openclaw/<timestamp>/archive/` for manual review — nothing is silently dropped.

---

## Config Key Mapping

For reference, here's how OpenClaw config maps to Hermes:

| OpenClaw Config | Hermes Config | Notes |
|----------------|---------------|-------|
| `agents.defaults.model` | `model` | String or `{primary, fallbacks}` |
| `agents.defaults.timeoutSeconds` | `agent.max_turns` | Divided by 10, capped at 200 |
| `agents.defaults.verboseDefault` | `agent.verbose` | off / on / full |
| `agents.defaults.thinkingDefault` | `agent.reasoning_effort` | always/high/xhigh → high, auto/medium/adaptive → medium, off/low/none/minimal → low |
| `agents.defaults.compaction.mode` | `compression.enabled` | "off" → false, anything else → true |
| `models.providers.*.baseUrl` | `custom_providers.*.base_url` | Direct mapping (auto-migrates to the canonical `providers:` dict on next config migration) |
| `models.providers.*.apiType` | `custom_providers.*.api_type` | openai → chat_completions, anthropic → anthropic_messages |

---

## Troubleshooting

### "No OpenClaw installation found"

Make sure your OpenClaw data is at `~/.openclaw/`. If it's elsewhere:

```bash
hermes claw migrate --source /path/to/your/openclaw
```

### Memory entries look duplicated

The migration deduplicates by content similarity, but if your OpenClaw memory had near-duplicates, they might not merge perfectly. Clean up manually:

```bash
# Edit memory directly
nano ~/.hermes/memories/MEMORY.md
```

### Skills have import errors

OpenClaw skills may reference modules or patterns that don't exist in Hermes. Open the skill file and check the imports:

```bash
cat ~/.hermes/skills/openclaw-imports/skill-name/SKILL.md
```

Most skills work as-is since they're markdown-based instructions. Skills with code that imports OpenClaw-specific modules need manual updating.

---

## What's Next

- **Want smarter memory?** → [Part 3: LightRAG Setup](./part3-lightrag-setup.md)
- **Need mobile access?** → [Part 4: Telegram Setup](./part4-telegram-setup.md)
- **Want the agent to self-improve?** → [Part 5: On-the-Fly Skills](./part5-creating-skills.md)
