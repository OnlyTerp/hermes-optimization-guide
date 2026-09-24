# 15 · Troubleshooting

> When something breaks: a diagnostic ladder that finds the cause fast, and fixes that are confirmed to work, each with its source.

**TL;DR**
- **Climb the ladder** before changing anything: `hermes doctor`, then `hermes status`, then `hermes logs`. In a session, `/status`, `/context all`, and `/usage`.
- **On v0.21.0 or v0.21.1, update now.** v0.21.2 was a dedicated `state.db` reliability release.
- Most "Hermes is broken" reports are one of five things: **the gateway isn't running**, **an allowlist or pairing issue**, **wrong model or context settings**, **a defaults-driven cost surprise**, or **a single-writer database rule**. The tables below cover each.
- **Never** delete `state.db-wal`, and never run `hermes doctor --fix` while other Hermes processes are running.
- A config key from a blog post that "does nothing" may simply not exist. `hermes config set` warns when a key isn't recognized.

Every fix below is confirmed by the official docs, a merged upstream fix, or release notes, and each row links its source. Problems with no confirmed fix are listed separately under [known open problems](#known-open-problems-no-confirmed-fix).

## The diagnostic ladder

| Step | Command | What it tells you |
|---|---|---|
| 1 | `hermes doctor` | Config, keys, dependencies, storage, security advisories, auxiliary routes that won't resolve. `--live` adds one real test call per tool backend. |
| 2 | `hermes status` (`--deep`) | Every component at once: model, keys, platforms, gateway, cron |
| 3 | `hermes logs` · `hermes logs gateway -f` · `hermes logs errors --since 1h` | What actually happened. Also `--level WARNING` and `--component cron`. Logs available: `agent`, `errors`, `gateway`, `gui`, `desktop`. |
| 4 | `hermes gateway status --deep` · `hermes cron status` | Whether the gateway runs, and whether cron will fire |
| 5 | `/status`, `/context all`, `/usage` (in a session) | The model and provider really in use, what fills the context, and rate-limit state |
| 6 | `hermes config check` · `hermes config get <key>` | Missing or outdated options, and the value Hermes actually resolves |
| 7 | `hermes --safe-mode` | Runs with **no** customizations: user config, AGENTS/memory injection, plugins, and MCP are all off. If the problem disappears, it's in your setup. |
| 8 | `hermes dump` · `hermes debug share` | A pasteable setup summary. `debug share` uploads logs publicly with only secrets redacted; use `--local` to keep them on your machine. |

Narrower switches for bisecting: `--ignore-user-config` runs on default config (keys in `.env` still load), and `--ignore-rules` skips AGENTS.md, SOUL.md, memory, and preloaded skills.

## Install and updates

| Symptom | Cause | Fix | Source |
|---|---|---|---|
| `hermes: command not found` right after installing | The shell started before the installer added `~/.local/bin` (or `%LOCALAPPDATA%\hermes\bin`) to `PATH` | `source ~/.bashrc` (or `~/.zshrc`), or open a new terminal. On Windows, open a new PowerShell window. | [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |
| `requires a different Python: 3.14.x` | Hermes supports Python 3.11–3.13 | Let the installer use its own 3.11. On Termux: `pkg install tur-repo && pkg install python3.13`. | [Termux guide](https://hermes-agent.nousresearch.com/docs/getting-started/termux) |
| Errors or missing features after `hermes update` | New config options weren't migrated | `hermes config check`, then `hermes config migrate`, then `hermes doctor` | [Updating](https://hermes-agent.nousresearch.com/docs/getting-started/updating) |
| Windows: `✗ Another hermes.exe is running` | Windows can't replace a running executable | Quit the desktop app and other `hermes` terminals, run `hermes gateway stop`, then retry. `hermes update --list-venv-holders` names the culprits. | [Updating](https://hermes-agent.nousresearch.com/docs/getting-started/updating) |
| Desktop app gone after `hermes update` on Windows | The zip-fallback update dropped the app build | `hermes desktop --build-only --force-build` | [Desktop docs](https://hermes-agent.nousresearch.com/docs/user-guide/desktop) |
| `hermes update` inside Docker exits 2 | Image-managed installs update by image | `docker pull nousresearch/hermes-agent:latest` and recreate the container | [Updating](https://hermes-agent.nousresearch.com/docs/getting-started/updating) |
| macOS gateway can't find `node` or `ffmpeg`, though Terminal can | launchd gives services a minimal `PATH` | Re-run `hermes gateway install`, which re-snapshots `PATH`, then `hermes gateway start` | [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |
| Terminal tool can't find `nvm`/`pyenv`/`cargo` binaries under the gateway | The service environment comes from a login bash, which doesn't read `~/.zshrc` | `terminal.shell_init_files: [~/.zshrc]` (`~/.bashrc` is sourced automatically) | [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |

## Models and providers

| Symptom | Cause | Fix | Source |
|---|---|---|---|
| HTTP 400 on the very first message | The model ID isn't available on that provider, the key lacks access, or there are no credits | `hermes model` to re-pick. Test with `hermes chat -q "hello" --model <known-good>`. On OpenRouter a 400 often means a paid-only model or a typo. | [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |
| `/model` only lists one provider | `/model` switches among providers that are already configured | Exit, add the provider with `hermes model`, then use `/model provider:model` | [Providers](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| Claude subscription: "You're out of extra usage", or Pro "doesn't work" | Claude OAuth consumes **Max plan extra-usage credits only**. Pro can't be used this way. | Pro: use `ANTHROPIC_API_KEY`. Max: buy extra-usage credits. Update to ≥ v0.21.1, which aliased tool names that tripped Anthropic's billing classifier ([PR #100173](https://github.com/NousResearch/hermes-agent/pull/100173)). | [Providers](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| 429s, outages, "API call failed after 3 retries" | Provider throttling or downtime | Add a fallback: `hermes fallback add`. With a fallback in place, `agent.api_max_retries: 0` hands off on the first error. After the chain is exhausted, `agent.auto_recovery_cycles` (default 5) waits and retries. | [Fallback providers](https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers) |
| Context-length errors early; "Context limit: 2048" at startup; a local server goes silent | Wrong auto-detected window, or Hermes believes the context is bigger than the server's real setting | Check the `Context limit` startup line or `/usage`. Set `model.context_length` to the server's **real** window. | [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |
| Hermes refuses to start with a local model ("below the minimum 64,000") | Hermes requires 64K context, and Ollama defaults far lower | Ollama: `OLLAMA_CONTEXT_LENGTH=64000 ollama serve` (or a Modelfile `num_ctx`). llama.cpp: `-c 64000`. vLLM: `--max-model-len`. LM Studio: raise the model's context and reload. | Hermes' own error text (`agent/agent_init.py`); [chapter 04](./04-local-models.md) |
| The local model prints `{"name": "web_search", …}` as text instead of calling the tool | Tool calling is off on the server, or the wrong parser is set | llama.cpp: `--jinja`. vLLM: `--enable-auto-tool-choice --tool-call-parser hermes`. Ollama: use a tools-capable model. | [Providers](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| The first turn on a local model sits silent for minutes | Prefilling ~13K tokens of fixed prompt on a slow GPU or CPU, or Ollama unloading the model after 5 idle minutes | `OLLAMA_KEEP_ALIVE=24h`. Trim the prefix ([chapter 05](./05-token-budget.md#lever-1-send-fewer-tool-schemas)). Make sure layers are on the GPU (`ollama ps`). | [Local Ollama guide](https://hermes-agent.nousresearch.com/docs/guides/local-ollama-setup) |

## Cost surprises

| Symptom | Cause | Fix | Source |
|---|---|---|---|
| "Every message costs ~13K tokens before I type anything" | The fixed prefix (system prompt and tool schemas) is sent on every call | Measure with `hermes prompt-size`, then disable unused toolsets per platform | [Chapter 05](./05-token-budget.md#lever-1-send-fewer-tool-schemas), [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |
| The bill is higher than your chat usage explains | Every `auxiliary.*` task (compression, titles, approvals, background review) runs on your **main** model by default | Route them to a cheap model | [Chapter 05](./05-token-budget.md#lever-3-put-side-tasks-on-a-cheap-model), [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration#auxiliary-models) |
| Cost spikes after `/model`, a fallback, or a key rotation | Provider caches are per model and account, so the next call re-reads everything at full price | Start a new session to change models, and keep fallbacks rare | [Tips](https://hermes-agent.nousresearch.com/docs/guides/tips) |
| Delegation dominates spend | Subagents inherit your frontier model | `delegation.model` / `delegation.provider` set to a cheaper model | [Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation) |

## Quality and memory

| Symptom | Cause | Fix | Source |
|---|---|---|---|
| "It got dumber" in a long session | A different model than you think (`/model` is session-scoped), context pressure, or details summarized away | `/status` shows the real model (`/model … --global` persists one). `/context all` shows pressure. `/compress focus <topic>`, or `/new` for a new task. Ask it to `session_search` archived turns. | [Troubleshooting agent quality](https://hermes-agent.nousresearch.com/docs/guides/troubleshooting-agent-quality) |
| "I told it to remember and it forgot" | It never called the memory tool (common with weak tool-callers), the write is waiting for approval, you're in a different profile, or memory is disabled | `cat ~/.hermes/memories/MEMORY.md`. Say "use the memory tool to save…". Check `/memory pending`. `hermes profile list`. | [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) |
| A memory saved mid-session isn't "known" in that same session | By design: the prompt is a snapshot frozen at session start, which keeps the cache warm | `/new`. The fact is also still in the current conversation. | [Tips](https://hermes-agent.nousresearch.com/docs/guides/tips) |
| It can't recall an old conversation | Memory is small curated facts, not a transcript. Ended sessions are auto-pruned after 90 days (`sessions.auto_prune`). | Ask it to use `session_search`. Pin sessions you'll need later with `hermes sessions pin <id>`. | [Sessions](https://hermes-agent.nousresearch.com/docs/user-guide/sessions) |
| Compression runs every turn and barely shrinks anything | The session trigger was lowered to fit a small auxiliary compression model's window | Use a compression model whose window is at least the trigger (`compression.threshold_tokens`, 256K by default) | [Auxiliary feasibility](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#auxiliary-feasibility-and-tail-retention) (symptom: [issue #53008](https://github.com/NousResearch/hermes-agent/issues/53008)) |

## Messaging gateway

| Symptom | Cause | Fix | Source |
|---|---|---|---|
| The bot dies when you close SSH, or doesn't come back after a reboot | User-level systemd units stop at logout unless lingering is enabled | Run `hermes gateway install`, which tries to enable lingering; otherwise `sudo loginctl enable-linger $USER`. Or switch to a boot-time system unit, after removing the user service so the two don't fight over one bot token ([chapter 14](./14-production.md#or-run-it-as-a-system-service)). | [Messaging](https://hermes-agent.nousresearch.com/docs/user-guide/messaging) |
| Restart loop ("Gateway already running", restart spam) | A custom `ExecStopPost=… kill -9` drop-in, or a restart race | Remove the drop-in (`systemctl --user edit hermes-gateway`, delete the line, `daemon-reload`). Restart with `hermes gateway restart`, which drains first. | [Messaging](https://hermes-agent.nousresearch.com/docs/user-guide/messaging) (the "Don't add a custom ExecStopPost kill drop-in" warning) |
| The bot doesn't respond at all | Gateway not running, bad token, or the sender isn't allowlisted (adapters fail closed) | `hermes gateway status`, then `hermes logs gateway -n 100`. Set the platform allowlist, or approve DM pairing with `hermes pairing approve <platform> <CODE>`. | [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |
| Telegram `409 Conflict`, or duplicate/alternating replies | Two processes polling one bot token | One token per profile. Find and stop the extra process. Since v0.21.4, one host gateway serves every profile. | [Telegram](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram), [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |
| Telegram works in DMs, **silent in groups** | BotFather privacy mode is on by default | @BotFather → `/mybots` → Bot Settings → Group Privacy → **Turn off**, then remove and re-add the bot to the group. Authorize the group with `TELEGRAM_GROUP_ALLOWED_CHATS`. | [Telegram](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram) |
| Telegram replies "unauthorized" | The allowlist has a username, not your **numeric** user ID | `TELEGRAM_ALLOWED_USERS=<id>` (get it from @userinfobot) in `~/.hermes/.env`, then restart | [Telegram](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram) |
| Discord bot is online but never answers | The Message Content intent is off, or no access policy is set (Discord fails closed) | Developer Portal → Bot → enable **Message Content** (plus **Server Members** if you allowlist by role). Set `DISCORD_ALLOWED_USERS`. Run `hermes gateway restart`. | [Discord](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord) |
| Slack answers DMs but not channels | Missing scopes or events, the app wasn't reinstalled after changes, or the bot isn't invited | Generate a manifest with `hermes slack manifest --write` and create the app from it, **reinstall** after any change, then `/invite` the bot | [Slack](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack) |
| WhatsApp is paired but silent | Allowlist format (country code, no `+`), or the session was invalidated | `WHATSAPP_ALLOWED_USERS=15551234567`. `WHATSAPP_DEBUG=true` and restart. `hermes update`, then re-pair with `hermes whatsapp`. | [WhatsApp](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/whatsapp) |
| Chat flooded with tool logs | Tool progress display is too verbose | `display.tool_progress: off` (or `new`), set per platform under `display.platforms.<platform>`. Restart the gateway. | [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |
| Telegram's `/` menu is missing skills | Telegram caps the command list, and the menu is built at gateway start | Disable unneeded skills with `hermes skills config`, then `hermes gateway restart`. `/commands` shows everything. | [Telegram](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram) |
| `sudo` commands fail from chat | The gateway has no TTY to prompt for a password | Ask for a non-sudo route, or allow specific commands with passwordless sudoers entries | [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) |

## Cron

| Symptom | Cause | Fix | Source |
|---|---|---|---|
| Jobs never fire | **Only a running gateway ticks cron.** A CLI chat doesn't. | `hermes cron status` says so explicitly. Install the gateway as a service ([chapter 14](./14-production.md)). `hermes cron tick` runs due jobs once. | [Cron troubleshooting](https://hermes-agent.nousresearch.com/docs/guides/cron-troubleshooting) |
| Cron silently stopped after `hermes update` | The gateway kept running old code | `hermes gateway restart`. v0.21.4's `hermes cron status` now warns about stale code, and updates signal stale gateways ([PR #117501](https://github.com/NousResearch/hermes-agent/pull/117501)). | [Issue #117275](https://github.com/NousResearch/hermes-agent/issues/117275) |
| The job runs but nothing arrives | Wrong or case-sensitive delivery target, no home channel, or the bot can't post there | `/sethome` in the target chat, or target `platform:chat_id`. The Telegram bot must be allowed to post. Slack needs `chat:write`. | [Cron troubleshooting](https://hermes-agent.nousresearch.com/docs/guides/cron-troubleshooting) |
| Jobs start failing after you change your main model | Unpinned jobs follow the main model at fire time | `hermes cron edit <id> --pin`, or set a fleet default: `hermes config set cron.model <model>` | [Cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) |
| Long jobs time out | The inactivity timeout (600 s) | `HERMES_CRON_TIMEOUT=<seconds>` (0 = unlimited). Move data collection into a script and have the agent only summarize. | [Cron troubleshooting](https://hermes-agent.nousresearch.com/docs/guides/cron-troubleshooting) |

## MCP, desktop, Docker

| Symptom | Cause | Fix | Source |
|---|---|---|---|
| An MCP server won't connect, or its tools are missing | Missing runtime (`node`/`npx`/`uvx`), a YAML error, tool filters, the wrong transport, or auth | `hermes mcp test <name>`, and read the MCP summary line in `agent.log`. A 400/405 on initialize means you need `transport: sse`. A 401/403 means `hermes mcp reauth <name>`. Then `/reload-mcp`. | [MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp), [Use MCP with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes) |
| MCP or Spotify OAuth fails when Hermes runs on a server | The OAuth redirect goes to your laptop's 127.0.0.1 | Tunnel it: `ssh -N -L <port>:127.0.0.1:<port> user@host`, using the port from the "Waiting for callback" line | [OAuth over SSH](https://hermes-agent.nousresearch.com/docs/guides/oauth-over-ssh) |
| The desktop app hangs at boot ("Timed out connecting to Hermes backend") | The backend fails to start | `hermes logs desktop -f` shows the traceback. After 3 crashes in 2 minutes the app stops respawning on purpose. | [Desktop](https://hermes-agent.nousresearch.com/docs/user-guide/desktop) |
| macOS asks for Files/Screen permissions again after each update | Permission grants were pinned to the old code signature | `hermes desktop --setup-tcc-identity` once | [Desktop](https://hermes-agent.nousresearch.com/docs/user-guide/desktop) |
| The container exits immediately or restart-loops | The default command is interactive | Run setup once interactively, then run with `gateway run` as the command | [Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker) |
| `Permission denied` on `/opt/data` (NAS, UnRAID, Synology) | The container user doesn't own the bind mount | Pass `-e PUID=$(id -u) -e PGID=$(id -g)` matching the mount's owner | [Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker) |
| Browser tools fail in Docker | Chromium needs shared memory | `--shm-size=1g` | [Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker) |
| Sessions corrupt on Docker Desktop (macOS/Windows) bind mounts | SQLite WAL needs a filesystem that virtiofs/9p mounts don't provide | Use a **named volume**. Or stop everything, run `hermes sessions set-journal-mode delete`, and set `database.journal_mode: delete`. | [Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker) |

## The session database (`state.db`)

**"Another Hermes process still holds an old copy of the session database's write-ahead log…"** Nothing is lost. The refusal exists to *prevent* loss. The official three-step fix:

1. **Stop every Hermes process on that profile**: `hermes gateway stop` (add `-p <profile>`), quit the desktop app, and run `hermes dashboard --stop`. Restarting just one of them isn't enough.
2. **Run `hermes doctor` until it no longer lists a `PID N (command)` holder.** Stop whatever it names.
3. **Start one process again**, the gateway or the desktop app, and resend your message.

Never:
- run `hermes doctor --fix` while processes are running, since it can become the second writer that caused the problem;
- delete `state.db-wal` or `state.db-shm`, which hold committed conversations. This is the one action that causes real data loss;
- copy `state.db` alone. The three files are one image. Use `hermes backup` or `hermes sessions recover`.

Other database problems:

| Symptom | Fix | Source |
|---|---|---|
| "file is not a database" or corruption on v0.21.0/v0.21.1 | Update to ≥ v0.21.2. If already damaged: `hermes doctor`, then `hermes sessions recover --source ~/.hermes/state.db --inspect-only`, and follow what it prints | [v0.21.2 release notes](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.9.11), [recovery guide](https://hermes-agent.nousresearch.com/docs/user-guide/session-storage-recovery) |
| `state.db` grows to gigabytes or search slows down | Stop the writers, then `hermes sessions optimize` (or `optimize-storage`). Both refuse while another process holds the database, by design. | [Recovery guide](https://hermes-agent.nousresearch.com/docs/user-guide/session-storage-recovery) |

## Known open problems (no confirmed fix)

These are real, reported, and **unresolved** at v0.21.4. The guide won't pretend otherwise. Check the linked issue for current status before spending an afternoon on one.

| Problem | Issue |
|---|---|
| Ollama with tool definitions and streaming can hang, then return HTTP 500 | [#25629](https://github.com/NousResearch/hermes-agent/issues/25629) |
| Ollama `qwen3.5` tool calls rendered as text in the desktop app | [#104412](https://github.com/NousResearch/hermes-agent/issues/104412) |
| LM Studio loads models at exactly 64K context on just-in-time load, ignoring your setting. Pre-loading the model with your context in LM Studio is a reporter workaround, not a confirmed fix. | [#66572](https://github.com/NousResearch/hermes-agent/issues/66572) |
| On the Weixin gateway, `USER.md`/`MEMORY.md` aren't injected (the CLI works) | [#96134](https://github.com/NousResearch/hermes-agent/issues/96134) |
| An external memory provider in "both" mode suppresses built-in memory injection on new chats | [#85622](https://github.com/NousResearch/hermes-agent/issues/85622) |
| Subagents hang when `telemetry.shared_metrics.enabled: true`. Keep it at the default `false`. | [#118218](https://github.com/NousResearch/hermes-agent/issues/118218) |
| WhatsApp pairing behind an HTTP(S) proxy loops on `408` with no QR code | [#43603](https://github.com/NousResearch/hermes-agent/issues/43603) |
| Desktop on WSL2: gateway exits every ~2 minutes (reported on v0.17, still open) | [#95189](https://github.com/NousResearch/hermes-agent/issues/95189) |
| macOS Full Disk Access revoked after desktop updates (`--setup-tcc-identity` mitigates) | [#52010](https://github.com/NousResearch/hermes-agent/issues/52010) |

## Myths that cost people time

| Myth | Reality |
|---|---|
| Config keys from popular blog posts (`budget.daily_usd`, `tools.gating.*`, `memory.reflection_enabled`, `skills.auto_create`, `model.fallback_chain`, `messaging.telegram.poll_timeout`) | **None of these exist** in v0.21.4. `hermes config set` saves them anyway and warns that the key isn't recognized. The real levers are in [chapter 05](./05-token-budget.md) and `fallback_providers` (`hermes fallback add`). | <!-- drift-guard: ignore-line (deliberately invalid keys) -->
| "Cap `max_turns` low to save money" | It's unlimited on purpose, and unattended runs already hard-stop runaway loops ([chapter 05](./05-token-budget.md#guardrails-against-runaway-spend)) |
| "Side tasks already use a cheap model" | `auxiliary.*: auto` means your main model |
| "Prompt caching uses a 1-hour TTL automatically" | The default is `5m`. Set `prompt_caching.cache_ttl: 1h` yourself if you pause for long stretches ([chapter 05](./05-token-budget.md#lever-2-keep-the-prompt-cache-warm)). |
| "Skills are the main token hog" | On a default install, tool schemas (~42 KB) dwarf the skills index (~5 KB). Trim toolsets first. |
| "Setting `model.context_length` changes Ollama's context" | It only tells Hermes what to expect. Set the context on the **server**. |
| "Cron runs whenever Hermes is open" | Only a running gateway ticks cron |
| "Messaging sessions reset daily" | Not since v0.21.1. They persist until `/new` or `/reset`, and compression manages length. |
| "My Claude Pro subscription covers Hermes" | Pro can't be used. Max works only through purchased extra-usage credits. |
| "Two profiles can share a bot token" / "two agents can share a profile" | No, and no. Each causes conflicts or corrupts memory. |
| "Hermes phones home" | Telemetry is opt-in (`telemetry.shared_metrics.enabled: false` by default) |
| "`hermes doctor --fix` is always safe" | Not while any Hermes process holds `state.db` |
| "hermes-agent.org / .ai / other look-alike sites are the docs" | The official docs are at hermes-agent.nousresearch.com/docs. Third-party sites have published invented config keys. |

## Filing a bug that gets fixed

1. Search [existing issues](https://github.com/NousResearch/hermes-agent/issues) first. Many problems are already fixed on a newer release.
2. Update and retry: `hermes update --check`.
3. Reproduce with `hermes --safe-mode`. If the problem vanishes, bisect your config, plugins, and MCP servers.
4. Attach context. `hermes dump` gives a compact setup summary. `hermes debug share` uploads logs to a **public** paste service. Only secrets (API keys, tokens, passwords) are redacted. Your display name, platform user ID, recent message text and file paths are not. Pastes delete themselves after about 6 hours; the dpaste fallback keeps them for `--expire` days (default 1) and can't be deleted early. `hermes debug share --nous` uploads privately to Nous staff instead, and `--local` prints the report without uploading. Read the report before posting it anywhere.
5. Include your version (`hermes --version`), OS, install method, the exact command or message, and what you expected.

## Go deeper

- Official: [FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq) · [Troubleshooting agent quality](https://hermes-agent.nousresearch.com/docs/guides/troubleshooting-agent-quality) · [Cron troubleshooting](https://hermes-agent.nousresearch.com/docs/guides/cron-troubleshooting) · [Session storage recovery](https://hermes-agent.nousresearch.com/docs/user-guide/session-storage-recovery) · [Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker)
- In this guide: [05 · Cost & Speed](./05-token-budget.md) · [13 · Security](./13-security.md) · [14 · Running 24/7](./14-production.md)

---
[← Previous: 14 · Running 24/7](./14-production.md) · [Guide index](../README.md#the-guide) · [Next: 16 · Recipes →](./16-recipes.md)
