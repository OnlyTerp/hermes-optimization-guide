# Cheat Sheet

> The commands, slash commands, and settings you'll actually use, with v0.21.4 defaults. Every entry is checked against the release this guide is pinned to.

## Everyday commands

| Command | Does |
|---|---|
| `hermes` · `hermes --tui` | Chat in the classic CLI or the full-screen TUI |
| `hermes -c` · `hermes -r "<title or id>"` | Continue the last session, or resume one by title or ID |
| `hermes -z "prompt"` | One-shot: prints only the answer (add `--usage-file f.json` for a cost report) |
| `hermes chat -q "prompt" --format stream-json` | Scriptable run that emits JSONL events |
| `hermes -w` | Start in an isolated git worktree |
| `hermes -p <profile> …` | Run any command as another profile |
| `hermes setup` · `hermes setup --portal` | Setup wizard · one-shot Nous Portal setup |
| `hermes model` | Pick provider and model, and configure auxiliary models |
| `hermes tools` · `hermes tools disable --platform telegram browser` | Enable/disable toolsets per surface |
| `hermes config set <key> <value>` · `config get` · `config edit` · `config check` | Change, read, edit, and validate config |
| `hermes doctor` · `hermes status` | Diagnose · see everything at once |
| `hermes logs [agent\|errors\|gateway\|desktop] -f` | Tail logs |
| `hermes update --check` · `--plan` · `hermes update` | Preview, plan, update |
| `hermes backup` · `hermes import <zip>` | Full backup and restore |

## Cost and context

| Command | Does |
|---|---|
| `hermes prompt-size [--platform X] [--json]` | Fixed per-call prompt and tool-schema bytes (offline) |
| `hermes insights --days 7` · `/insights 7` | Spend, tokens, and tool patterns over time |
| `hermes usage` · `/usage` | Provider rate-limit windows and session token usage |
| `/context` · `/context all` | Live context breakdown, and which context files loaded |
| `/compress` · `/compress focus <topic>` · `/compress here 10` | Compact now, keeping what matters |
| `/new` | Fresh session. The cheapest compression there is. |
| `/btw <question>` · `/bg <prompt>` | Side question without touching the transcript · a separate background task |
| `/model <name>` · `/model <name> --global` | Switch this session (breaks the cache) · persist the switch |
| `/reasoning low` · `/fast auto` | Less thinking · priority tier for the first 60 s of each turn (costs more) |

## Messaging and gateway

| Command | Does |
|---|---|
| `hermes gateway setup` | Configure platforms (bot tokens, allowlists) |
| `hermes gateway run` · `hermes gateway install` | Foreground · install as a service (`--system --run-as-user <user>` for boot-time Linux) |
| `hermes gateway status --deep` · `hermes gateway restart` | Health check · drain-first restart |
| `hermes pairing list` · `hermes pairing approve telegram <CODE>` | Approve new users by DM pairing |
| `hermes send` | Send a message to a platform from scripts |
| `/sethome` · `/whoami` · `/approve` · `/deny` | Home channel for cron · your access level · answer an approval (chat only) |
| `/handoff telegram` | Move a CLI session to your phone |
| `hermes pause` · `hermes resume` | Emergency stop for cron, Kanban, and new gateway turns |

## Automation

| Command | Does |
|---|---|
| `hermes cron create "0 8 * * *" "<self-contained prompt>" --deliver telegram` | Scheduled agent job |
| `… --no-agent --script check.sh` | Script-only job: zero model calls, stdout delivered, empty = silent |
| `… --monitor-url <url>` | Agent runs only when the fetched content changes |
| `… --continuity` · `--pin` · `--reasoning-effort low` | Remember last output · lock the current model · cheap thinking |
| `hermes cron list` · `cron status` · `cron runs <job>` · `cron doctor` | Inspect jobs, scheduler, history, health |
| `hermes webhook subscribe <name> --prompt "…" --deliver telegram` | Event-driven runs (`--deliver-only` = no LLM) |
| `/goal <text>` · `/goal gate add <cmd>` · `/subgoal <text>` | Standing goal · a shell check that must pass · extra criteria |
| `/loop 30m <prompt>` · `/heartbeat every 1h <prompt>` · `/queue` · `/steer` | In-session repetition and redirection |

## Memory, skills, context files

| Command | Does |
|---|---|
| `/memory pending` · `/memory approve <id>` | Review staged memory writes (with `memory.write_approval: true`) |
| `/refine` · `/learn <what>` | Save lessons now · turn anything into a skill |
| `hermes skills browse` · `search` · `install` · `audit` | Find and vet skills |
| `hermes skills config` · `hermes skills opt-out` | Disable skills per platform · stop seeding bundled skills |
| `hermes curator run --dry-run` | Preview skill cleanup |
| `hermes memory setup` · `hermes memory status` | External memory provider (one at a time) |
| `hermes sessions pin <id>` | Exempt a session from 90-day auto-pruning |
| `/init` · `/personality <name>` · `@file:path` · `@diff` | Draft AGENTS.md · temporary mode · attach context to one message |

## Settings worth knowing (defaults at v0.21.4)

| Key | Default | Why you'd touch it |
|---|---|---|
| `auxiliary.<task>.provider` / `.model` | `auto` = **your main model** | Route compression, vision, titles, and approvals to a cheap model ([05](./05-token-budget.md#lever-3-put-side-tasks-on-a-cheap-model)) |
| `auxiliary.background_review.enabled` | `true` | The memory/skill review fork. Route it cheap, cap it, or disable it. |
| `compression.threshold` | `0.5` (effective **0.75** under 512K windows) | Rarely. See [05](./05-token-budget.md#lever-4-compression-that-fires-when-you-think-it-does). |
| `compression.threshold_tokens` | `256000` | The cap that decides when 1M-window models compact |
| `compression.min_tail_user_messages` | `1` | Raise to 3 to keep your recent instructions verbatim |
| `prompt_caching.cache_ttl` | `5m` | `1h` if you pause for long stretches. `off` disables caching. |
| `tools.tool_search.enabled` | `auto` (on) | Leave on. It defers MCP/plugin tool schemas. |
| `agent.disabled_toolsets` | `[]` | Toolsets to drop on every surface |
| `agent.max_turns` | unlimited | Cap only for shared or public agents |
| `agent.reasoning_effort` | unset = `medium` | Global thinking level (`/reasoning`). Lower it for cheap, fast turns. |
| `delegation.model` / `.provider` | inherit | Cheap subagents |
| `delegation.max_concurrent_children` | `10` | Lower on rate-limited plans |
| `cron.model` | main model | Cheap default for unpinned jobs |
| `memory.memory_char_limit` / `user_char_limit` | `2200` / `1375` | Bounded on purpose |
| `memory.write_approval` | `false` | `true` to review every memory write |
| `sessions.auto_prune` / `retention_days` | `true` / `90` | Ended sessions older than this are deleted |
| `approvals.mode` | `smart` | `manual` for shared agents. `off` only in disposable sandboxes. |
| `approvals.cron_mode` · `unattended_mode` | `deny` · `deny` | Dangerous commands in unattended runs are refused |
| `security.redact_secrets` | `true` | Keep it on |
| `security.protected_instruction_files` | `true` | Agent edits to SOUL/AGENTS need your approval |
| `gateway.allow_all_users` | `false` | Never `true` on a bot with a shell |
| `terminal.backend` | `local` | `docker` for untrusted work |
| `checkpoints.enabled` | `false` | `true` for coding: `/rollback` safety net |
| `timezone` | server-local | Set it, so schedules and "today" mean what you think |

## Where things live

| Path | Contents |
|---|---|
| `~/.hermes/config.yaml` | Settings (`hermes config path`) |
| `~/.hermes/.env` | Secrets and API keys (`hermes config env-path`) |
| `~/.hermes/SOUL.md` | Identity and voice |
| `~/.hermes/memories/MEMORY.md`, `USER.md` | Built-in memory |
| `~/.hermes/skills/` | Installed skills (`.archive/` = curator-archived) |
| `~/.hermes/state.db` (+ `-wal`, `-shm`) | Sessions and search index. Never delete the `-wal`. |
| `~/.hermes/scripts/` | Scripts for cron `--script` / `--no-agent` jobs |
| `~/.hermes/logs/` | `agent.log`, `errors.log`, `gateway.log`, `update_receipts/` |
| `~/.hermes/profiles/<name>/` | A complete separate agent |
| `~/.hermes/hermes-agent/` | The code (per-user installs) |
| `%LOCALAPPDATA%\hermes\` | All of the above on native Windows |

---
[← Previous: 16 · Recipes](./16-recipes.md) · [Guide index](../README.md#the-guide)
