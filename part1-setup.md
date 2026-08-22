# Part 1: Setup (Stop Fumbling With Installation)

*From zero to working agent in under 5 minutes. Covers what the docs don't.*

---

## The Install

One command. That's it. Current at the time of writing: **Hermes v0.20.4 (2026.8.18)** — this guide tracks the v0.19/v0.20 release wave. Hermes also ships on PyPI, so use the installer for the full local stack or `pip install hermes-agent` for the leanest CLI path. Prefer a GUI? Install the [desktop app](./part24-desktop-app.md) — same agent, same config, same keys.

### Linux / macOS / WSL2

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Lean path when you already manage Python yourself:
pip install hermes-agent
```

> **Security tip:** Piping scripts directly from the internet to bash executes them sight-unseen. If you prefer to inspect first:
> ```bash
> curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o install.sh
> less install.sh   # Review the script
> bash install.sh
> ```

### Windows (native)

Windows is a **first-class supported surface** — no WSL or Docker required. In PowerShell (no admin needed):

```powershell
iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
```

The installer provisions everything under `%LOCALAPPDATA%\hermes` (Python via uv, PortableGit, Node) and adds `hermes` to your User PATH — open a new terminal after it finishes. [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) remains a solid choice if you prefer a Linux environment for gateway work; native data lives at `%LOCALAPPDATA%\hermes`, WSL data at `~/.hermes`.

> **Android users:** the same installer detects Termux and installs the tested `[termux]` extra bundle automatically — CLI, cron, PTY/background terminal, Telegram gateway, MCP, Honcho, ACP. See [Part 15 — Android / Termux](./part15-new-platforms.md#android--termux-running-hermes-on-your-phone).

### Desktop app

Want a GUI instead of a terminal? Install the [Hermes Desktop app](./part24-desktop-app.md) (macOS/Windows/Linux) — or add it to a CLI install with `--include-desktop`. It runs the same agent, config, and keys. Full tour in [Part 24](./part24-desktop-app.md).

### What the Installer Does

The installer handles everything automatically:

- Installs **uv** (fast Python package manager)
- Installs **Python 3.11** via uv (no sudo needed)
- Installs **Node.js v22** (for browser automation)
- Installs **ripgrep** (fast file search) and **ffmpeg** (audio conversion)
- Pre-installs **cua-driver** so the [Computer Use](./part24-desktop-app.md) toolset (background desktop control) works the moment you enable it
- Installs the PyPI package or clones the Hermes repo when you choose source mode
- Sets up the virtual environment
- Creates the global `hermes` command
- Runs the setup wizard for LLM provider configuration

The only prerequisite is **Git**. Everything else is handled for you.

### After Installation

```bash
source ~/.bashrc   # or: source ~/.zshrc
hermes             # Start chatting!
```

---

## First-Run Configuration

The setup wizard (`hermes setup`) walks you through:

### 1. Choose Your Model (bring any)

```bash
hermes model        # fuzzy-search every provider Hermes knows about
```

**Hermes is model-agnostic** — the picker fuzzy-searches a catalog that refreshes hourly, so you're never stuck on last release's list. You don't have to commit to a single provider:

- **Cloud APIs** — Anthropic, OpenAI, Google / Gemini, xAI / Grok (key or OAuth), Moonshot / Kimi, z.ai / GLM, MiniMax, DeepSeek, Novita, and more. Set the matching `*_API_KEY` or sign in by OAuth. Copilot and Codex OAuth subscriptions work, and **OpenCode Free** is a keyless option (no account needed).
- **One key for everything** — OpenRouter (`OPENROUTER_API_KEY`) reaches hundreds of models with automatic fallback.
- **Local / private** — Ollama, LM Studio, or llama.cpp with no key needed. See [Part 25: NVIDIA & Local Hardware](./part25-nvidia-local.md).
- **Nous Portal** — one OAuth login covers 300+ models plus the Tool Gateway (web search, image gen, TTS, browser). Fastest path: `hermes setup --portal`.

**Flagships move fast — don't trust a printed list.** The picker draws from a live catalog ([model catalog](./part9-custom-models.md)) that refreshes hourly; run `hermes model` to see what's actually available. As of v0.20.4 the OpenRouter default is **GLM-5.x** (`z-ai/glm-5.2`), with **Kimi K3**, the **GPT-5.x family**, and **DeepSeek V4-class** models as the other current flagships.

Configure **multiple providers** with automatic fallback — if one goes down, Hermes switches to the next. Routing, aliases, and fallback chains are covered in [Part 9](./part9-custom-models.md).

### 2. Set Your API Keys

```bash
hermes model
```

Run `hermes model` from your terminal (not inside a chat session) to add providers, enter API keys, and run OAuth flows — it's the full provider setup wizard. (`hermes auth` exists too, but it manages *credential pools* — multiple keys per provider for same-provider key rotation — not first-time key entry.) Keys are stored in `~/.hermes/.env` — never committed to git.

> **Tip:** You can also set keys manually using a text editor:
> ```bash
> nano ~/.hermes/.env    # Add: ANTHROPIC_API_KEY=<your-key-here>
> chmod 600 ~/.hermes/.env   # Restrict access to your user only
> ```
>
> **Avoid using `echo` to append secrets** — the command (including the key) is saved in your shell history (`~/.bash_history`). Use an editor or `hermes model` instead. Always run `chmod 600 ~/.hermes/.env` to prevent other users on the system from reading your API keys.

### 3. Configure Toolsets

```bash
hermes tools
```

This opens an interactive TUI to enable/disable tool categories:

- **file** — File read/write, search, and editing
- **terminal** — Shell execution and background process management
- **web** — Web search and page extraction
- **browser** — Full browser automation (requires Node.js)
- **code_execution** — Run Python scripts that call Hermes tools
- **delegation** — Sub-agent spawning for parallel work
- **skills** — Skill discovery and creation
- **memory** — Memory search and management
- **vision**, **image_gen**, **computer_use** — Image analysis/generation and background desktop control

> **Recommendation:** Enable `file`, `terminal`, `web`, `skills`, and `memory` at minimum. Add `browser`, `code_execution`, and `delegation` when you need automation, scripted tool loops, or parallel sub-agents. (Older toolset names like `core`, `code`, and `delegate` were renamed — the TUI above shows the current catalog.)

---

## Key Config Options

After initial setup, fine-tune with `hermes config set`:

### Model Settings

```bash
# Set primary model (example; run `hermes model` for the live catalog)
hermes config set model anthropic/claude-sonnet-5

# Set a fallback chain (used when primary is rate-limited or errors) —
# canonical format is a top-level `fallback_providers` list in config.yaml:
```

```yaml
model:
  default: anthropic/claude-sonnet-5
fallback_providers:
  - provider: openrouter
    model: z-ai/glm-5.2
  - provider: deepseek
    model: deepseek/deepseek-v4-pro
```

### Agent Behavior

```bash
# Max tool-calling iterations per conversation turn (default: none = unlimited;
# the underlying iteration budget defaults to 500 steps)
hermes config set agent.max_turns 90

# Verbose mode: off, on, or full
hermes config set agent.verbose off

# Quiet mode (less terminal output; also toggled in-session via /verbose)
hermes config set display.tool_progress off
```

### Context Management

```bash
# Prompt caching is on by default; the explicit knob is the requested cache
# TTL tier on Anthropic-style breakpoints ("5m" or "1h")
hermes config set prompt_caching.cache_ttl "5m"

# Context compression (auto-summarize old messages)
hermes config set compression.enabled true
```

---

## File Locations

Everything lives under `~/.hermes/`:

```
~/.hermes/
├── config.yaml          # Main configuration
├── .env                 # API keys (never commit this)
├── auth.json            # OAuth credentials (Nous Portal, Copilot, Codex, etc.)
├── SOUL.md             # Agent personality (injected every message)
├── memories/           # Long-term memory entries
├── skills/             # Skills (auto-discovered)
├── skins/              # CLI themes
├── audio_cache/        # TTS audio files
├── logs/               # Session logs
└── hermes-agent/       # Source code (git repo)
```

> **Windows native:** the data directory is `%LOCALAPPDATA%\hermes` instead of `~/.hermes` (inside WSL it's `~/.hermes`).

> **Important:** `SOUL.md` is injected into every message. Keep it under 1 KB. Every byte costs latency and tokens.

> **Security:** The `.env` file contains your API keys. Restrict its permissions so only you can read it:
> ```bash
> chmod 600 ~/.hermes/.env
> ```

---

## Verify Your Setup

```bash
# Check everything is working
hermes status

# Quick test
hermes chat -q "Say hello and confirm you're working"
```

Expected output: Hermes responds with a greeting, confirming the model connection, tool availability, and session initialization.

---

## Updating

```bash
hermes update
```

This pulls the latest code, updates dependencies, migrates config, and restarts the gateway. Run it regularly — Hermes ships frequent improvements. The web admin panel's **System page** adds a **check-before-update** step and a one-click **Debug Share** for support, and the [desktop app](./part24-desktop-app.md) checks in the background and updates in one click.

---

## What's Next

- **Coming from OpenClaw?** → [Part 2: OpenClaw Migration](./part2-openclaw-migration.md)
- **Want smarter memory?** → [Part 3: LightRAG Setup](./part3-lightrag-setup.md)
- **Need mobile access?** → [Part 4: Telegram Setup](./part4-telegram-setup.md)
- **Want the agent to self-improve?** → [Part 5: On-the-Fly Skills](./part5-creating-skills.md)
- **Prefer a GUI?** → [Part 24: Hermes Desktop App](./part24-desktop-app.md)
- **Run it on your own GPU?** → [Part 25: NVIDIA & Local Hardware](./part25-nvidia-local.md)
