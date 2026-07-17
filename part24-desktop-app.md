# Part 24: Hermes Desktop App — A Real GUI Over the Same Agent

<p align="center">
  <img src="./assets/desktop-app.png" alt="Hermes Desktop — the native macOS, Windows, and Linux app for the Hermes Agent" width="880">
</p>

*The v0.16.0 "Surface Release" shipped **Hermes Desktop**: a native macOS/Windows/Linux app that runs the exact same agent as the CLI, TUI, and gateway. Same config, same keys, same sessions, same skills, same memory — it's "another surface over one agent, not a fork." Two releases later it has grown into a genuine daily driver: v0.17 "Reach" added subagent watch-windows, native notifications, marketplace themes, and a real terminal pane; v0.18 "Judgment" turned it into a coding cockpit with first-class **Projects**, a **multi-terminal panel**, and the **memory graph**. If you've avoided Hermes because you didn't want to live in a terminal, this is your on-ramp.*

---

## 1. Install and Launch

If Hermes is already installed, the app is one command away:

```bash
hermes desktop
```

The first run downloads or builds the desktop bundle (e.g. `Hermes.app` on macOS) and launches it. To build the desktop app as part of a fresh install, pass the installer flag:

```bash
# macOS / Linux
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --include-desktop
```

On **Windows**, the native installer ships a signed bootstrap that can include the desktop app:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

Once installed it behaves like any other desktop program — pin it to your dock/taskbar and launch it without the terminal.

> **Same brain, new face.** The desktop app talks to the same agent core as everything else. A session you start in the app shows up in `hermes sessions`, and a skill the agent wrote from Telegram is available in the app. Nothing is siloed.

---

## 2. The Chat Surface

The main window is a streaming chat with **live tool activity** — you watch tool calls run inline instead of staring at a spinner. Highlights:

- **Shared history across surfaces** — desktop, CLI, TUI, and messaging all read/write the same sessions.
- **Drag-and-drop files** — drop a file onto the composer to attach it.
- **Clipboard image paste** — paste a screenshot straight in.
- **Right-hand preview rail** — rendered output (files, images, results) opens beside the chat instead of scrolling away.
- **Composer history and queue editing** — press up/down in the composer to recall previous messages and edit a queued message before it sends.
- **Per-thread drafts** (v0.17) — half-written messages persist per conversation; switch threads without losing what you were typing.
- **PR-style diffs in chat** (v0.18) — code changes render as reviewable diffs inline.
- **Conversation timeline rail** (v0.18) — jump around long sessions from a scannable timeline instead of scrolling.
- **Subagent watch-windows** (v0.17) — pop open a live window on any running subagent and watch it work instead of waiting on a summary.
- **Native OS notifications** (v0.17) — get pinged when a long run finishes or the agent needs an approval, even when the app is backgrounded.

---

## 3. Command Palette and Keyboard

- **Command palette:** `Cmd+K` (macOS) / `Ctrl+K` (Windows/Linux) opens a fuzzy command palette for nearly everything — switch sessions, change model, open settings, run commands.
- **Rebindable shortcuts** (v0.17): remap keys to taste.
- **Themes from the VS Code Marketplace** (v0.17): install any VS Code theme and the whole app adopts it. Your terminal aesthetic can follow you.
- **Custom zoom:** scale the whole UI up or down.
- **Language switcher:** the desktop UI is fully internationalized. v0.16 added **Simplified Chinese (简体中文)**; English is the default. Switch via the UI language picker (`display.language`).

---

## 4. The Model Picker

Hermes is model-agnostic, and the desktop makes switching trivial. The **model picker** sits in the composer (left of the mic) and lets you change the **model**, **reasoning effort**, and **fast mode** per message:

- The picker is **sticky per device** and **never writes your profile default** — experiment freely without rewriting config.
- Set your actual default in **Settings → Model**, including per-model reasoning-effort and fast-mode presets.
- It's the same fuzzy, hourly-refreshed catalog you get in the TUI/CLI/web (see [Part 9](./part9-custom-models.md) for routing and aliases).

---

## 5. Status Bar and the YOLO Toggle

The status bar shows live session state and exposes a **per-session YOLO toggle**. Flipping YOLO on bypasses approval prompts for that session so the agent runs tools without stopping to ask.

> **Use YOLO deliberately.** It is genuinely useful for trusted, low-stakes loops on your own machine. Do **not** enable it for any session that reads untrusted input (email, webhooks, public chats) or has destructive tools wired up. Read [Part 19: Security Playbook](./part19-security-playbook.md) first, and keep the approval layer on for anything that touches production.

---

## 6. First-Run Quick Setup via Nous Portal

First launch offers two paths:

- **Quick Setup** — `hermes portal` signs you in through the [Nous Portal](https://portal.nousresearch.com) and picks a model for you. The fastest way from zero to a working agent without touching YAML or hunting for API keys.
- **Full Setup** — the complete onboarding UI: providers and keys, models, tools, MCP servers, gateway, and sessions. xAI Grok OAuth is first-class here.

You can re-open onboarding any time from Settings.

---

## 7. Connect to a Remote Hermes

The desktop app doesn't have to run the agent locally. It can connect to a **remote Hermes gateway** over a secure WebSocket (`/api/ws`):

- **Auth:** OAuth or username/password.
- **Per-profile remote host:** point each profile at a different Hermes box.
- **Concurrent multi-profile sessions:** run several profiles at once, and link across them with cross-profile `@session` references.

The model is "**thin GUI local, heavy agent remote**" — keep a lightweight app on your laptop while the agent, tools, and memory live on a workstation, a DGX Spark, or a VPS. (Pair this with [Part 21: Remote Sandboxes](./part21-remote-sandboxes.md) and [Part 25: NVIDIA & Local Hardware](./part25-nvidia-local.md).)

> **The gotcha nobody warns you about:** with a remote backend, *code runs on the remote server* — file writes, terminal commands, everything. If you asked for a local script and can't find it, it's on the VPS. Want the agent working on your laptop's files? Run the backend locally (or mount/sync deliberately, e.g. via Tailscale + a shared directory).

### 7b. Hermes Cloud — the third connection mode (preview)

Alongside *local* and *remote gateway*, current builds are growing a third mode: **Hermes Cloud** — sign in with Nous Portal and the app auto-discovers cloud-hosted agents, no VPS to babysit. The pitch: one-click deploy, scale-to-zero pricing, natural-language scheduling, multi-channel attach, persistent memory, isolated sandboxes, and parallel subagents — managed.

Treat it as **preview until GA**: features on `main` move fast, and self-hosting (this guide's default posture) remains the way to keep full control of memory, secrets, and egress. When it ships stable, expect it to be the right answer for "I want the [Part 23](./part23-tenacity-stack.md) stack without owning a server."

---

## 8. Projects — the v0.18 Coding Cockpit

v0.18 made **Projects** first-class. A project is a per-profile workspace with:

- A **project sidebar** and dedicated project pages.
- A **coding rail** — the agent's plan, running checks, and file activity beside the chat.
- A **review pane** — read the diff like a PR before you accept it.
- **Worktree management** — each project's changes live in an isolated git worktree, so parallel projects don't stomp each other.
- **Session–project association** — sessions attach to a project, so the history of a codebase stays in one place.

Combined with the **multi-terminal panel** (multiple named terminals per project) this is the closest thing to an IDE the Hermes desktop has — except the agent drives. Pair it with verification and completion contracts from [Part 26](./part26-moa-verification.md#2-verification--done-means-proven-not-claimed) so "accept" means "checks passed," not "looks plausible."

---

## 9. The Memory Graph

Settings → Memory opens the v0.18 **memory graph**: a radial, playable timeline of every memory and skill the agent has accumulated — scrub through time and watch the graph grow. It's the GUI counterpart of `/journey` ([Part 26](./part26-moa-verification.md#3-learn-and-journey--self-improvement-you-can-see)): click any node to edit or delete it. Do a pruning pass monthly; wrong memories compound.

---

## 10. Sessions, Files, and Voice

- **Sessions:** archive, search, and **search-by-id**; run concurrent multi-profile sessions with cross-profile `@session` links.
- **File browser:** set the initial working directory with `hermes desktop --cwd PATH` or the `HERMES_DESKTOP_CWD` environment variable.
- **Voice:** click the mic to talk; macOS prompts for microphone permission once.
- **Remote media relay** (v0.17): when connected to a remote gateway, images and files generated on the remote box stream back to the app instead of being stranded on the server.

### Management Panes

Beyond chat, the app has dedicated panes for **Skills**, **Cron**, **Profiles**, **Messaging**, and **Agents**, plus a **Command Center** — the same surfaces you'd otherwise drive from the [web admin panel](./part12-web-dashboard.md), now native.

---

## 11. Updating

The app checks for updates in the background and offers **one-click update**; manual updates work too. This mirrors the gateway's **check-before-update** flow (verify before pulling) introduced alongside the System page in the web admin panel — see [Part 12](./part12-web-dashboard.md).

---

## 12. Uninstalling

Remove the app from **Settings → About → Danger zone**, or from the CLI:

```bash
hermes uninstall --gui    # remove the desktop GUI only
hermes uninstall          # remove GUI + agent, keep your data
hermes uninstall --full   # remove everything, including data
```

---

## 13. `hermes desktop` Flags

For development and troubleshooting, `hermes desktop` accepts:

| Flag | What it does |
|------|--------------|
| `--skip-build` | Launch without rebuilding the bundle |
| `--force-build` | Force a rebuild before launch |
| `--build-only` | Build the bundle and exit (no launch) |
| `--source` | Run from source instead of a packaged build |
| `--cwd PATH` | Set the initial working directory |
| `--hermes-root PATH` | Point at a specific Hermes install root |
| `--ignore-existing` | Ignore an already-running instance |
| `--fake-boot` | Boot the UI without starting the agent (UI dev) |

---

## When to Use Desktop vs CLI/TUI

- **Desktop** — you want a real GUI: drag-and-drop, image paste, a preview rail, Projects with reviewable diffs, the memory graph, point-and-click model switching, and one-click updates. Great for non-terminal users and for connecting to a remote agent.
- **TUI** (`hermes --tui`) — you live in the terminal but want live tool cards, `/steer`, queueing, and a sticky composer. See [Part 22](./part22-latest-power-moves.md).
- **CLI** (`hermes`) — scripting, cron, CI, and quick one-shots.

It's the same agent underneath — pick the surface that fits the moment and switch whenever you want.
