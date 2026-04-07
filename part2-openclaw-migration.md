# Part 2: OpenClaw Migration (Don't Leave Your Knowledge Behind)

*Transfer your skills, memory, config, and personality from OpenClaw to Hermes in one command.*

---

## Why Migrate

Hermes is the successor to OpenClaw. If you've spent weeks or months building up skills, memory files, and configuration in OpenClaw, the migration tool brings all of it over automatically.

**What transfers:**

| What | OpenClaw Location | Hermes Destination |
|------|------------------|-------------------|
| Personality | `workspace/SOUL.md` | `~/.hermes/SOUL.md` |
| Instructions | `workspace/AGENTS.md` | Your specified workspace target |
| Memory | `workspace/MEMORY.md` + `workspace/memory/*.md` | `~/.hermes/memories/MEMORY.md` (merged, deduped) |
| User profile | `workspace/USER.md` | `~/.hermes/memories/USER.md` |
| Skills | `workspace/skills/`, `~/.openclaw/skills/` | `~/.hermes/skills/openclaw-imports/` |
| Model config | `agents.defaults.model` | `config.yaml` |
| Provider keys | `models.providers.*.apiKey` | `~/.hermes/.env` (with `--migrate-secrets`) |
| Custom providers | `models.providers.*` | `config.yaml → custom_providers` |
| Max turns | `agents.defaults.timeoutSeconds` | `agent.max_turns` (timeoutSeconds / 10) |

> **Note:** Session transcripts, cron job definitions, and plugin-specific data do not transfer. Those are OpenClaw-specific and have different formats in Hermes.

---

## Quick Migration

```bash
# Preview what would happen (no files changed)
hermes claw migrate --dry-run

# Run the full migration (includes API keys)
hermes claw migrate

# Exclude API keys (safer for shared machines)
hermes claw migrate --preset user-data
```

The migration reads from `~/.openclaw/` by default. If you have legacy `~/.clawdbot/` or `~/.moldbot/` directories, those are detected automatically.

---

## Migration Options

| Option | What It Does | Default |
|--------|-------------|---------|
| `--dry-run` | Preview without writing anything | off |
| `--preset full` | Include API keys and secrets | yes |
| `--preset user-data` | Exclude API keys | no |
| `--overwrite` | Overwrite existing Hermes files on conflicts | skip |
| `--migrate-secrets` | Include API keys explicitly | on with `--preset full` |
| `--source <path>` | Custom OpenClaw directory | `~/.openclaw/` |
| `--workspace-target <path>` | Where to place `AGENTS.md` | current directory |
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
5. Migrate API keys (if `--preset full`)
6. Report what was done

### 3. Handle Conflicts

If a skill already exists in Hermes with the same name:

- **`--skill-conflict skip`** (default): Leaves the Hermes version, skips the import
- **`--skill-conflict overwrite`**: Replaces the Hermes version with the OpenClaw version
- **--skill-conflict rename`**: Creates a `-imported` copy alongside the Hermes version

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
```

---

## What Doesn't Transfer

| Item | Why | What to Do |
|------|-----|-----------|
| Session transcripts | Different format | Archive manually if needed |
| Cron job definitions | Different scheduler | Recreate with `hermes cron` |
| Plugin configs | Plugin system changed | Reconfigure in Hermes |
| OpenClaw-specific features | May not exist yet | Check Hermes docs for equivalents |

---

## Config Key Mapping

For reference, here's how OpenClaw config maps to Hermes:

| OpenClaw Config | Hermes Config | Notes |
|----------------|---------------|-------|
| `agents.defaults.model` | `model` | String or `{primary, fallbacks}` |
| `agents.defaults.timeoutSeconds` | `agent.max_turns` | Divided by 10, capped at 200 |
| `agents.defaults.verboseDefault` | `agent.verbose` | off / on / full |
| `agents.defaults.thinkingDefault` | `reasoning.mode` | off / low / high |
| `models.providers.*.baseUrl` | `custom_providers.*.base_url` | Direct mapping |
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
