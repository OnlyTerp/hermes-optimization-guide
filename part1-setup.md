# Part 1: Setup (Stop Fumbling With Installation)

*From zero to working agent in under 5 minutes. Covers what the docs don't.*

---

## The Install

One command. That's it. v0.14 also ships on PyPI, so use the installer for the full local stack or `pip install hermes-agent` for the leanest CLI path.

### Linux / macOS / WSL2

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Lean v0.14+ path when you already manage Python yourself:
pip install hermes-agent
```

> **Security tip:** Piping scripts directly from the internet to bash executes them sight-unseen. If you prefer to inspect first:
> ```bash
> curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh -o install.sh
> less install.sh   # Review the script
> bash install.sh
> ```

> **Windows users:** Native Windows is in beta in v0.14. Use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) for production/stable gateway work; try native Windows only after backing up config and expecting PTY/dashboard quirks.

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

### 1. Choose Your LLM Provider

```bash
hermes model
```

Supported providers:

| Provider | Best For | Env Variable |
|----------|----------|-------------|
| Anthropic (Claude) | Highest quality, best at complex tasks | `ANTHROPIC_API_KEY` |
| OpenAI (GPT-5.5/Codex) | Strong tool use, sandboxed coding, deep reasoning | `OPENAI_API_KEY` |
| OpenRouter | Access 100+ models from one key | `OPENROUTER_API_KEY` |
| Cerebras | Fast inference, good for simple tasks | `CEREBRAS_API_KEY` |
| Groq | Very fast, limited context | `GROQ_API_KEY` |
| xAI (Grok / SuperGrok OAuth) | Live X search, Grok 4.3 1M context, Custom Voices | `XAI_API_KEY` or OAuth |
| Google (Gemini) | Huge context, cheap | `GEMINI_API_KEY` |

You can configure **multiple providers** with automatic fallback. If one goes down, Hermes switches to the next.

### 2. Set Your API Keys

```bash
hermes auth
```

This opens an interactive menu to add API keys for each provider. Keys are stored in `~/.hermes/.env` — never committed to git.

> **Tip:** You can also set keys manually:
> ```bash
> echo "ANTHROPIC_API_KEY=<your-key-here>" >> ~/.hermes/.env
> chmod 600 ~/.hermes/.env   # Restrict access to your user only
> ```
>
> **Important:** Always run `chmod 600 ~/.hermes/.env` to prevent other users on the system from reading your API keys.

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

This pulls the latest code, updates dependencies, migrates config, and restarts the gateway. Run it regularly — Hermes ships frequent improvements.

---

## What's Next

- **Coming from OpenClaw?** → [Part 2: OpenClaw Migration](./part2-openclaw-migration.md)
- **Want smarter memory?** → [Part 3: LightRAG Setup](./part3-lightrag-setup.md)
- **Need mobile access?** → [Part 4: Telegram Setup](./part4-telegram-setup.md)
- **Want the agent to self-improve?** → [Part 5: On-the-Fly Skills](./part5-creating-skills.md)
