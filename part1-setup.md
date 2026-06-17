# Part 1: Setup (Stop Fumbling With Installation)

*From zero to working agent in under 5 minutes. Covers what the docs don't.*

---

## The Install

One command. That's it. Hermes also ships on PyPI, so use the installer for the full local stack or `pip install hermes-agent` for the leanest CLI path. Prefer a GUI? Install the [desktop app](./part24-desktop-app.md) — same agent, same config, same keys.

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

Hermes now has a first-class native Windows installer. In PowerShell:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

[WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) is still a solid choice if you prefer a Linux environment for gateway work.

### Desktop app

Want a GUI instead of a terminal? Install the [Hermes Desktop app](./part24-desktop-app.md) (macOS/Windows/Linux) — or add it to a CLI install with `--include-desktop`. It runs the same agent, config, and keys. Full tour in [Part 24](./part24-desktop-app.md).

### What the Installer Does

The installer handles everything automatically:

- Installs **uv** (fast Python package manager)
- Installs **Python 3.11** via uv (no sudo needed)
- Installs **Node.js v22** (for browser automation)
- Installs **ripgrep** (fast file search) and **ffmpeg** (audio conversion)
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

- **Cloud APIs** — Anthropic, OpenAI, Google, xAI / Grok (OAuth), Moonshot / Kimi, z.ai / GLM, MiniMax, Cerebras, Groq, and more. Set the matching `*_API_KEY` or sign in by OAuth.
- **One key for everything** — OpenRouter (`OPENROUTER_API_KEY`) reaches hundreds of models with automatic fallback.
- **Local / private** — Ollama, LM Studio, or llama.cpp with no key needed. See [Part 25: NVIDIA & Local Hardware](./part25-nvidia-local.md).
- **Nous Portal** — `hermes portal` runs a guided **Quick Setup** that signs you in and picks a model for you.

Configure **multiple providers** with automatic fallback — if one goes down, Hermes switches to the next. Routing, aliases, and fallback chains are covered in [Part 9](./part9-custom-models.md).

### 2. Set Your API Keys

```bash
hermes auth
```

This opens an interactive menu to add API keys for each provider. Keys are stored in `~/.hermes/.env` — never committed to git.

> **Tip:** You can also set keys manually using a text editor:
> ```bash
> nano ~/.hermes/.env    # Add: ANTHROPIC_API_KEY=<your-key-here>
> chmod 600 ~/.hermes/.env   # Restrict access to your user only
> ```
>
> **Avoid using `echo` to append secrets** — the command (including the key) is saved in your shell history (`~/.bash_history`). Use an editor or `hermes auth` instead. Always run `chmod 600 ~/.hermes/.env` to prevent other users on the system from reading your API keys.

### 3. Configure Toolsets

```bash
hermes tools
```

This opens an interactive TUI to enable/disable tool categories:

- **core** — File read/write, terminal, web search
- **web** — Browser automation, web extraction
- **browser** — Full browser control (requires Node.js)
- **code** — Code execution sandbox
- **delegate** — Sub-agent spawning for parallel work
- **skills** — Skill discovery and creation
- **memory** — Memory search and management

> **Recommendation:** Enable `core`, `web`, `skills`, and `memory` at minimum. Add `browser` and `code` if you need automation or sandboxed execution.

---

## Key Config Options

After initial setup, fine-tune with `hermes config set`:

### Model Settings

```bash
# Set primary model
hermes config set model anthropic/claude-sonnet-5

# Set fallback model (used when primary is rate-limited)
hermes config set fallback_models '["openrouter/anthropic/claude-sonnet-5"]'
```

### Agent Behavior

```bash
# Max turns per conversation (default: 90)
hermes config set agent.max_turns 90

# Verbose mode: off, on, or full
hermes config set agent.verbose off

# Quiet mode (less terminal output)
hermes config set agent.quiet_mode true
```

### Context Management

```bash
# Enable prompt caching (reduces cost on repeated context)
hermes config set prompt_caching.enabled true

# Context compression (auto-summarize old messages)
hermes config set context_compression.enabled true
```

---

## File Locations

Everything lives under `~/.hermes/`:

```
~/.hermes/
├── config.yaml          # Main configuration
├── .env                 # API keys (never commit this)
├── SOUL.md             # Agent personality (injected every message)
├── memories/           # Long-term memory entries
├── skills/             # Skills (auto-discovered)
├── skins/              # CLI themes
├── audio_cache/        # TTS audio files
├── logs/               # Session logs
└── hermes-agent/       # Source code (git repo)
```

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
