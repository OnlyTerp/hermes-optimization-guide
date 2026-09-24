# 02 · Install & First Run

> A clean, supported install on the first try, a first chat that actually works, and updates that don't break anything.

**TL;DR**
- Install with the **official installer**, or the Desktop installer on Apple-Silicon Macs and Windows. PyPI, Homebrew, and AUR installs are officially **unsupported**, and so are Intel Macs.
- Run `hermes setup` and pick a mode: **Quick Setup** (Nous Portal, least friction), **Full Setup** (your own keys), or **Blank Slate** (a minimal agent with the smallest prompt).
- Get **one clean chat** working before adding anything else. That's the official rule of thumb, and it saves hours.
- `hermes doctor` is your first diagnostic and `hermes status` your dashboard.
- Update with `hermes update`. It snapshots state, validates the new code, and drain-restarts gateways. Run `hermes update --check` first on anything important.

## Decide where it runs

Hermes runs happily on a laptop, but an agent that answers your phone at 3 a.m. or runs overnight jobs needs a machine that doesn't sleep.

| You want | Run it on | Install with |
|---|---|---|
| A desktop assistant, mostly in front of you | Your Mac (Apple Silicon) or Windows PC | Desktop installer |
| A terminal-first coding agent | Your dev machine (Linux, macOS, WSL2, Windows) | `install.sh` / `install.ps1` |
| A 24/7 chat bot with scheduled jobs | A small VPS or home server (Linux) | `install.sh`, then [chapter 14](./14-production.md) |
| Isolated, reproducible deployments | Docker | The official image ([Docker guide](https://hermes-agent.nousresearch.com/docs/user-guide/docker)) |
| Hermes in your pocket | Android via Termux | [Termux guide](https://hermes-agent.nousresearch.com/docs/getting-started/termux) |

Upstream's [platform support](https://hermes-agent.nousresearch.com/docs/getting-started/platform-support) policy, in short:

| Tier | Platforms | What it means |
|---|---|---|
| **Tier 1** | macOS (Apple Silicon), Windows 10/11, Linux and WSL2 (x86_64, aarch64), Docker | Regressions are first priority |
| **Tier 2** | Android (Termux), Nix | Best effort. Releases may break them. |
| **Unsupported** | Intel Macs, and installs via PyPI (`pip`/`uv tool install hermes-agent`), Homebrew, or the AUR | May break at any time. PRs to fix them are not accepted. |

> [!WARNING]
> The `hermes-agent` package on PyPI is stale: 0.19.0 as of 2026-09-23, while the GitHub release is 0.21.4. Upstream no longer supports PyPI installs. If an old guide told you `pip install hermes-agent`, switch to the installer.

## Install

### Desktop installer (macOS Apple Silicon, Windows)

Download it from [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/) and run it. You get the desktop app *and* the `hermes` command-line tool. On first launch the app installs the agent runtime into the same `~/.hermes` (or `%LOCALAPPDATA%\hermes`) layout a script install uses, so the two are interchangeable. Onboarding then gets you to a provider and model, or you can pick **Choose provider later** and explore first.

### Linux, macOS, WSL2, Termux

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc      # or ~/.zshrc; puts `hermes` on your PATH
```

Prerequisites: `git`. On Linux also `curl` and `xz-utils`, and `build-essential` if you'll build the desktop app. The installer fetches everything else itself: uv, Python 3.11, Node.js, ripgrep, and ffmpeg.

Useful installer flags (pass them after `bash -s --`):

```bash
# headless server with no browser automation: skip Playwright/Chromium
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --skip-browser
```

`--skip-computer-use` skips the Computer Use driver, and `--dir PATH` installs somewhere other than `~/.hermes/hermes-agent`.

**Prefer to read before you run?** Download, inspect, then execute. It's the same script:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o hermes-install.sh
less hermes-install.sh
bash hermes-install.sh
```

### Windows (native)

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

This installs everything natively, including a private portable Git Bash that Hermes uses for shell commands. It lives under `%LOCALAPPDATA%\hermes`. WSL2 works too: use the Linux command inside WSL, and note that its data lives in the WSL `~/.hermes`, separate from any native install.

If antivirus quarantines `%LOCALAPPDATA%\hermes\bin\uv.exe`, that's a known false positive on Astral's `uv`. The upstream README has [verification steps](https://github.com/NousResearch/hermes-agent/blob/v2026.9.21/README.md#troubleshooting) (an attestation check against Astral's release). Whitelist the **folder**, not the file hash, because `uv` updates change the hash.

### Where things land

| Install | Code | `hermes` command | Your data |
|---|---|---|---|
| Per-user (normal) | `~/.hermes/hermes-agent/` | `~/.local/bin/hermes` | `~/.hermes/` |
| As root (`sudo … \| sudo bash`) | `/usr/local/lib/hermes-agent/` | `/usr/local/bin/hermes` | `/root/.hermes/` or `$HERMES_HOME` |
| Windows native | `%LOCALAPPDATA%\hermes\` | on your PATH | `%LOCALAPPDATA%\hermes\` |

For a server, install as a **dedicated unprivileged user**, not root. [Chapter 14](./14-production.md) walks through it, including the one step that needs an admin (`sudo npx playwright install-deps chromium`, if you want browser tools).

## First run

```bash
hermes setup
```

On a fresh install the wizard offers three modes:

| Mode | What you get | Pick it when |
|---|---|---|
| **Quick Setup (Nous Portal)** | OAuth login, a model, and the Tool Gateway (web search, image generation, TTS, cloud browser) on one account | You want it working in five minutes without collecting API keys |
| **Full Setup** | Walks every provider, tool, and option. Bring your own keys. | You already have OpenRouter, Anthropic, OpenAI, or local-model credentials |
| **Blank Slate** | Only provider and model, the file toolset, and the terminal toolset. Web, browser, memory, skills, delegation, cron, MCP, and compression all start **off**. | You want a minimal, fully controlled agent with the smallest possible prompt, and you'll opt into features one by one |

`hermes setup --portal` jumps straight to the Nous Portal flow. On an existing install, `hermes setup --quick` prompts only for what's missing. You can also skip the wizard entirely: run `hermes model` to pick a provider and model, then `hermes` to chat.

Quick and Full Setup finish by installing and starting the messaging gateway as a background **user** service, even if you skip messaging, because scheduled jobs only run while a gateway does. That's expected, not a stray process: `hermes gateway status` shows it. In a container, or on a host with no service manager, setup prints how to run it yourself instead.

> [!IMPORTANT]
> Hermes refuses models with less than **64K tokens** of context. The system prompt and tool schemas alone are about 13K tokens. Hosted frontier models clear this easily. For local models, see [chapter 04](./04-local-models.md).

### Prove it works before you add anything

```bash
hermes doctor                     # config, keys, dependencies, advisories; add --fix to auto-repair
hermes status                     # model, keys, platforms, gateway, cron at a glance
hermes -z "Reply with exactly: OK" # one real model call; prints only the answer
hermes                            # then a normal conversation
```

If the one-shot prints `OK`, the model, key, and network path are good. Add messaging, cron, MCP, and voice only after this works. Most "it installed but does nothing" reports come from stacking features onto a provider that never worked.

### Coming from another agent

```bash
# OpenClaw: preview first, then migrate. Secrets are NOT copied unless you ask.
hermes claw migrate --dry-run
hermes claw migrate --preset full --migrate-secrets

# Claude Code or Codex CLI setups (~/.claude or ~/.codex)
hermes import-agent --dry-run
hermes import-agent
```

`hermes claw migrate` brings over `SOUL.md`, memories, skills (into `~/.hermes/skills/openclaw-imports/`), command allowlists, messaging settings, and, with `--migrate-secrets`, allowlisted API keys and bot tokens. It writes a restore-point zip to `~/.hermes/backups/` first. `--skill-conflict rename` keeps both copies when names collide.

Moving your own Hermes to a new machine? Use `hermes backup` on the old one and `hermes import <zip>` on the new one. A profile export (`hermes profile export`) deliberately excludes credentials, so it isn't a full backup ([chapter 14](./14-production.md#backups)).

## The first ten minutes of tuning

Once the first chat works, these are the highest-leverage defaults to set. Each links to the chapter that explains it.

1. **Pick your main model on purpose**: `hermes model` ([03](./03-models.md)).
2. **Move side tasks to a cheap model.** They run on your main model by default ([05](./05-token-budget.md#lever-3-put-side-tasks-on-a-cheap-model)).
3. **Set your timezone** so "tomorrow at 9" and cron schedules mean what you think: `hermes config set timezone America/New_York`.
4. **Write a short `SOUL.md`**: `~/.hermes/SOUL.md` ([06](./06-personality-and-context.md)).
5. **Trim toolsets** for each surface you'll use: `hermes tools` ([05](./05-token-budget.md#lever-1-send-fewer-tool-schemas)).
6. **Leave approvals on `smart`**, the default, until you've read [chapter 13](./13-security.md).

## Updating without breaking things

```bash
hermes update --check     # is there anything new? (read-only)
hermes update --plan      # what would restart, across all profiles (read-only)
hermes update             # do it
```

`hermes update` tracks upstream's `main` branch and runs the same careful sequence every time:

1. **Snapshot** `config.yaml`, `.env`, auth, cron jobs, and pairing data, for every profile (`updates.pre_update_backup: quick`, the default). Use `--backup`, or set it to `full`, to also zip the whole Hermes home on machines you'd hate to rebuild.
2. **Pull**, then **compile-check** the critical startup files. A broken pull rolls itself back so your shell stays bootable.
3. **Sync dependencies** and **migrate config**, prompting for new options.
4. **Rebuild the desktop app**, if you built it from this checkout. A failed rebuild leaves the previous app untouched.
5. **Drain-restart gateways.** Running chats and cron jobs finish first, for up to `agent.restart_after_turn_timeout` (30 minutes). Wedged work is interrupted instead.

Every run writes a receipt to `~/.hermes/logs/update_receipts/`. The update exits non-zero if any gateway is left running old code, so automation can trust the exit code.

Rules of thumb:

- **Don't update in the middle of a long job** you care about. The drain waits, but `hermes update --plan` shows you what's running first.
- **Windows:** close the desktop app's backend and other `hermes` terminals first. The updater refuses while another `hermes.exe` holds the venv open.
- **Docker installs don't use `hermes update`.** Pull and run a new image.
- **Updating from a cron job or chat command?** Use `hermes update --no-gateway-restart` and restart the gateway separately. An update launched *by* the gateway can't survive its own restart.
- **After updating:** `hermes --version`, then `hermes config check`.

Pinned machines can silence update notices with `hermes config set updates.check false`. Explicit `hermes update` still works.

## Uninstall

```bash
hermes uninstall --dry-run   # see what would be removed
hermes uninstall             # remove the agent, keep ~/.hermes data
hermes uninstall --full      # remove everything, including config and data
```

## Verify it

```bash
hermes --version    # Hermes Agent v0.21.4 (2026.9.21) or newer
hermes doctor       # no errors; warnings explain themselves
hermes status       # your provider shows as configured
```

## Gotchas

- **`hermes: command not found`** after install: reload your shell (`source ~/.bashrc`) or add `~/.local/bin` to `PATH`. Service accounts often have a minimal `PATH` ([official troubleshooting](https://hermes-agent.nousresearch.com/docs/getting-started/installation#troubleshooting)).
- **`ModuleNotFoundError: No module named 'dotenv'`** means you ran the repo's `hermes` script with system Python. Use the venv launcher, `~/.hermes/hermes-agent/venv/bin/hermes` (from the official install docs).
- **A user-level gateway service stops when you log out** on Linux until you enable lingering: `sudo loginctl enable-linger <user>` ([chapter 14](./14-production.md)).
- **A symlinked `~/.hermes` on an unmounted NAS** fails with a storage error, by design. Hermes won't silently write to the local disk instead. Remount, don't re-run setup.
- **Intel Macs** are unsupported. Use a Linux VPS or Docker if that's your hardware.
- **Free-tier API keys** (for example Google AI Studio's) can run out after a handful of agent turns, because one turn is several model calls. The providers page warns about exactly this.

## Go deeper

- Official: [Installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation) · [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) · [Updating & Uninstalling](https://hermes-agent.nousresearch.com/docs/getting-started/updating) · [Platform Support](https://hermes-agent.nousresearch.com/docs/getting-started/platform-support) · [Migrate from OpenClaw](https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw) · [Import from other agents](https://hermes-agent.nousresearch.com/docs/user-guide/import-from-other-agents)
- Next: [03 · Models & Providers](./03-models.md)

---
[← Previous: 01 · How Hermes Works](./01-how-hermes-works.md) · [Guide index](../README.md#the-guide) · [Next: 03 · Models & Providers →](./03-models.md)
