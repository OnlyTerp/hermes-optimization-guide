# Part 12: The Local Web Dashboard (Stop Editing YAML)

*Introduced in v0.9 and, as of v0.20, a full browser-based admin control panel: config, Chat/TUI, channels, MCP, webhooks, pairing, credentials, memory, skills, cron, Kanban, plugins, profiles, and analytics — not just a YAML editor.*

> **Update (v0.16–v0.20):** This part matches the v0.20 dashboard. v0.16 added a **Channels** page (per-platform gateway management from the browser) and a **System** page with a check-before-update flow and one-click **Debug Share** support dumps (the flow [Part 1's update section](./part1-setup.md#updating) points at). v0.17 added the **profile builder**, a rehauled **Skills Hub**, and **hardened dashboard auth** — the server validates session tokens plus `Origin`/`Host` on state-changing requests. v0.19/v0.20 grew it into a machine-level admin panel: a profile switcher (`?profile=`), an MCP catalog (one-click installs), **Webhooks** and **Pairing** pages, memory provider config, a rotating **credential pool**, a full **Profiles** management page, dashboard auth providers (username/password, Nous Portal OAuth, self-hosted OIDC), and a **System** page that can check for and apply updates plus generate Debug Share support dumps. One rule of thumb for v0.20: binding the dashboard to anything other than `127.0.0.1` now **refuses to start without an auth provider** — no more unauthenticated public binds. If your dashboard shows pages this part doesn't, that's the version wave.

---

## Why This Matters

Before v0.9, managing Hermes meant: edit `config.yaml`, export env vars, grep through logs, and use the CLI to inspect sessions. Great for power users. Terrible for anyone new.

The **web dashboard** (`hermes dashboard`) replaces most of that with a single browser UI:

- Live status of the gateway and all built-in/plugin platform adapters
- Browser Chat backed by the real `hermes --tui`
- Form-based editor for every config field (all 150+ of them, auto-discovered from `DEFAULT_CONFIG`)
- Models tab for main + auxiliary model configuration
- API key manager for providers, tools, and platforms
- **Channels** page — configure every messaging platform from the browser (full parity with `hermes gateway setup`)
- MCP server manager + one-click installs from the Nous-approved catalog
- Webhook subscriptions, DM pairing approvals, memory provider config, and rotational credential pools
- Full-text search across past sessions (FTS5)
- Log tailer with level/component filters
- Usage and cost analytics (daily token + cost breakdown, per-model)
- Cron job management
- Kanban boards, worker/task status, comments, blocks, and handoffs
- Skills, Skills Hub (search/install/update with security-scan verdicts), Curator, plugins, profiles, and toolsets browser with enable/disable toggles
- System page with check-before-update and one-click Debug Share

Everything runs on `127.0.0.1` — no data leaves your machine.

---

## Quick Start

```bash
hermes dashboard
```

That's it. It starts a local server and opens `http://127.0.0.1:9119` in your default browser.

### Install the Dependencies (One Time)

The dashboard uses FastAPI + Uvicorn + a React frontend. The Chat tab also needs PTY support:

```bash
# pip install (PyPI install)
pip install 'hermes-agent[web,pty]'

# or, for a source install under ~/.hermes/hermes-agent:
cd ~/.hermes/hermes-agent && uv pip install -e ".[web,pty]"
```

If you installed with `hermes-agent[all]`, you're already done. The `web` extra brings FastAPI/Uvicorn; `pty` brings `ptyprocess` (POSIX) or `pywinpty`. The frontend auto-builds on first launch if `npm` is available. The embedded Chat tab is part of every `hermes dashboard` launch — no extra flag needed.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `9119` | Port to serve on |
| `--host` | `127.0.0.1` | Bind address |
| `--no-open` | — | Don't auto-open the browser |
| `--insecure` | off | **Deprecated / no-op.** Formerly bypassed auth on a non-loopback bind; a public bind now always requires an auth provider (password or OAuth) |
| `--isolated` | off | When launched from a named profile (`worker dashboard`), run a dedicated per-profile server instead of routing to the machine dashboard |
| `--skip-build` | off | Skip the frontend build step and serve the existing build (useful for CI/non-interactive) |
| `--stop` / `--status` | — | Stop / list running `hermes dashboard` processes and exit |

```bash
# Custom port
hermes dashboard --port 8080

# Bind to all interfaces (use with caution — see security note below)
hermes dashboard --host 0.0.0.0

# Start without opening the browser
hermes dashboard --no-open
```

> **Security:** The dashboard reads and writes your `.env` file (API keys) and can run agent commands — treat it as root on your machine. On a loopback bind (`127.0.0.1`, the default) there's no login; only local processes can reach it, so the classic DNS-rebinding hole is closed by `Origin`/`Host` validation on state-changing requests. Binding to **any non-loopback address engages an auth gate**: since the June 2026 hardening, `hermes dashboard --host 0.0.0.0` **fails closed** unless an auth provider is configured — the legacy `--insecure` flag no longer disables anything. Three providers ship in the box: a **username/password** provider (trusted LAN/VPN use only), **Nous Portal OAuth** (`hermes dashboard register` — the public-internet option), and **self-hosted OIDC** (Keycloak, Authentik, Auth0, Okta, …). For a local-only setup, leave it on `127.0.0.1`; to reach it remotely use SSH port-forwarding (`ssh -L 9119:127.0.0.1:9119 user@your-server`), Tailscale, or a reverse proxy with authentication (see `templates/caddy/Caddyfile`).

---

## Pages at a Glance

### Status

Live overview that auto-refreshes every 5 seconds:

- Agent version + release date
- Gateway state — running/stopped, PID, every connected platform with its own state
- Active sessions — everything alive in the last 5 minutes
- Recent sessions — the last 20, with model, message count, token usage, and a preview

This is the page you leave open on a second monitor.

### Chat

The Chat tab embeds the actual `hermes --tui` process through xterm.js. That matters: slash commands, approval prompts, clarify/sudo/secret prompts, skins, markdown streaming, tool-call cards, `/resume`, `/steer`, `/queue`, and TUI fixes appear here automatically because the dashboard is not maintaining a second chat implementation.

Requirements:

- Node.js for the Ink TUI bundle
- `ptyprocess` (POSIX) via the `pty` extra — `pip install 'hermes-agent[pty]'` or `cd ~/.hermes/hermes-agent && uv pip install -e ".[web,pty]"`
- POSIX PTY support: Linux, macOS, or WSL2 for the embedded `/chat` terminal. On a **native Windows** install the rest of the dashboard (sessions, jobs, analytics, config editor) works fully, but the Chat pane shows a banner telling you to use WSL2 for that one feature — native Windows Python has no PTY equivalent

Tip: launch from the Sessions page with the play icon to resume a past session directly into `/chat?resume=<id>`.

### Config

Form-based editor for `config.yaml`. Fields are auto-discovered from `DEFAULT_CONFIG` and grouped into tabs:

- **model** — default model, provider, base URL, reasoning settings
- **terminal** — backend (local / docker / ssh / modal), timeouts, shell preferences
- **display** — skin, tool progress rendering, spinner settings
- **agent** — max iterations, gateway timeout, `service_tier` (Fast Mode), `/goal` behavior
- **delegation** — subagent limits, reasoning effort
- **memory** — provider, context injection settings
- **approvals** — dangerous command mode (`manual` / `smart` / `off` — see [Part 19](./part19-security-playbook.md))
- **plugins** — enabled/disabled plugin allowlists
- **curator** — schedule, pruning thresholds, pinned/archived behavior
- **kanban** — board location, worker profiles, retry budget, stale heartbeat reclaim policy

Dropdowns for known-value fields (terminal backend, skin, approval mode). Toggles for booleans. Text inputs for everything else.

Actions:
- **Save** — writes to `config.yaml` immediately
- **Reset to defaults** — previews reverting everything (still requires Save)
- **Export** — download current config as JSON
- **Import** — upload a JSON file to replace values

> Config changes take effect on the next agent session or gateway restart. This edits the exact same file as `hermes config set` and the gateway.

### API Keys

The `.env` editor you'll actually use. Keys are grouped by category:

- **LLM providers** — OpenRouter, Anthropic, OpenAI, z.ai/GLM, Kimi, MiniMax, Xiaomi MiMo, Arcee, etc.
- **Tool API keys** — Browserbase, Firecrawl, Tavily, ElevenLabs, FAL, etc.
- **Messaging platforms** — Telegram, Discord, Slack, BlueBubbles, WeChat, etc.
- **Agent settings** — non-secret env vars like `API_SERVER_ENABLED`

Each row shows whether a key is set (redacted preview), a one-line description, and a link to the provider's key page.

Advanced/rarely-used keys are hidden behind a toggle by default to keep the surface clean.

### Sessions

Full browse and search across every session you've ever run, across every platform.

- **Search** — FTS5 full-text search across message content. Hits are highlighted and auto-scrolled on expand.
- **Expand** — load the full message history with Markdown + syntax highlighting, color-coded by role (user / assistant / system / tool).
- **Tool calls** — collapsible blocks showing the function name and JSON arguments for every tool call.
- **Delete** — remove a session and its messages with the trash icon.

Each row shows the title, source platform icon (CLI, Telegram, Discord, Slack, cron, BlueBubbles, WeChat), model, message count, tool call count, and how long since last activity. Live sessions pulse.

### Logs

Agent, gateway, and error log files with filtering and live tail.

- **File** — switch between `agent`, `errors`, `gateway`
- **Level** — ALL / DEBUG / INFO / WARNING / ERROR
- **Component** — all / gateway / agent / tools / cli / cron
- **Lines** — 50 / 100 / 200 / 500
- **Auto-refresh** — live tail polling every 5s
- Color-coded by severity (red errors, yellow warnings, dim debug)

### Analytics

Usage and cost, computed from session history. Pick a time window (7 / 30 / 90 days):

- Summary cards — total input/output tokens, cache hit %, estimated or actual cost, session count with daily average
- Daily token chart — stacked input/output bars, hover for exact breakdowns and cost
- Daily breakdown table — date, sessions, tokens, cache hit rate, cost
- Per-model breakdown — each model used, sessions, tokens, cost

If you're on the Nous Portal Tool Gateway (Part 13), gateway tool usage shows up here too.

### Models

Use this page before you edit routing YAML by hand. It exposes:

- Main model/provider selection
- Auxiliary models for compression, vision, title generation, session search, and curator
- Remote OpenRouter/Nous picker data when available
- Per-model usage analytics so "cheap default, expensive opt-in" stays honest

This is the fastest way to stop wasting your best model on background summaries.

### Cron

Create and manage scheduled agent prompts.

- **Create** — name, prompt, cron expression (e.g. `0 9 * * *`), delivery target (local / Telegram / Discord / Slack / email)
- **Job list** — name, prompt preview, schedule, state badge, delivery target, last run, next run
- **Pause / Resume** — toggle active state
- **Trigger now** — run a job immediately, outside its normal schedule
- **Delete** — remove permanently

This replaces the old `hermes cron create …` CLI flow for most people.

### Profiles

Create and manage profiles — isolated Hermes instances with their own config, skills, memory, and sessions. The dashboard is a **machine-level** management surface: one server manages every profile on the box, and a sidebar **profile switcher** (visible whenever more than one profile exists) decides which profile the Config, API Keys, Skills, MCP, Models, and Chat tabs read and write (the selection lives in the URL as `?profile=<name>`). The dedicated **Profile Builder** (`/profiles/new`) walks the full flow: model, MCPs, skills.

- **Profile cards** — model/provider, skill count, gateway state, description, badges
- **Create** — name + clone options + model; or the full Profile Builder
- **Set as active** — flips the default that future CLI/gateway runs pick up (same as `hermes profile use`)
- **Edit model / description / SOUL**, rename, delete

Launching `worker dashboard` from a profile alias routes to the machine dashboard with that profile preselected (or starts it); pass `--isolated` for a dedicated per-profile server.

### Channels

The messaging-platform setup page — **full parity with `hermes gateway setup`, from the browser**. It lists every supported channel (Telegram, Discord, Slack, Matrix, Mattermost, WhatsApp, Signal, BlueBubbles/Photon iMessage, Email, SMS/Twilio, DingTalk, Feishu/Lark, WeCom, WeChat, QQ Bot, Yuanbao, plus the API server and webhook endpoints) with live connection status.

- **Configure** — per-platform form with exactly the fields that channel needs (bot token, server URL, allowlist…). Secrets render as password inputs and stay redacted.
- **Enable / disable** — flip a channel without deleting its credentials
- **Test** — is the channel configured, enabled, and reporting a live connection?
- **Restart gateway** — credentials land in `.env`, the enabled flag in `config.yaml`, and the gateway connects on restart — which you can trigger right from the page

### MCP

Manage [`mcp_servers` in `config.yaml`](part17-mcp-servers.md) without the CLI:

- **Add** — HTTP/SSE (URL) or stdio (command + args) servers, optional env vars, secret-shaped values redacted
- **Enable / disable** — toggle with no delete; takes effect on the next gateway restart
- **Test** — connect, list tools, disconnect, before the agent ever depends on it
- **Catalog** — browse the Nous-approved catalog (the same one `hermes mcp catalog` uses) and install entries with one click; entries needing keys prompt for them inline

### Webhooks

Create and manage webhook subscriptions for event-driven agent runs — name, description, event filter, delivery target, optional direct-delivery mode, and the agent prompt (the same surface as `hermes webhook subscribe`). On creation the page hands you the route URL and the one-time HMAC secret. Enable/disable hot-reloads (no gateway restart needed).

### Pairing

Approve and revoke messaging users without the CLI (full parity with `hermes pairing`): pending requests show platform, code, user, and age with an Approve button; approved users get a Revoke button; "Clear pending" drops every outstanding code.

### System

A consolidated admin panel for installation-wide operations:

- **Host** — live stats (OS/kernel, arch, CPU, memory, disk of the Hermes home, uptime), the Hermes version with an **update-status badge**, **Check for updates**, and when an update is available an **Update now** button that shows how many commits you'll pull before running `hermes update` in the background (Docker/Nix installs get the correct out-of-band command instead). This is the **check-before-update** flow [Part 1's update section](./part1-setup.md#updating) points at.
- **Nous Portal** — login state, active provider, and the Tool Gateway routing table (read-only mirror of `hermes portal`)
- **Skill curator** — background skill-repair status with pause/resume and run-now
- **Gateway** — start/stop/restart the messaging gateway with live state
- **Memory** — pick the external memory provider or reset the built-in `MEMORY.md` / `USER.md`
- **Credential pool** — add/remove the rotating per-provider keys the agent round-robins through
- **Operations** — run `doctor`, a security audit, create/restore backups, update skills, show system-prompt size, **generate a support dump** (the one-click Debug Share for support requests), or migrate config for retired settings — each streams a live log into the page
- **Checkpoints / Shell hooks** — see the `/rollback` shadow store size and prune it; create consent-gated shell hooks

### Skills

Browse, search, and toggle every skill and toolset — and install new ones from the hub.

- **Search** — filter by name, description, or category
- **Category filter** — click pills to narrow (MLOps, MCP, Red Teaming, AI, etc.)
- **Toggle** — enable/disable individual skills per session
- **Browse hub** — a dedicated view that searches the skill hub across all sources (same as `hermes skills search`), installs any result by identifier with a live install log, and offers an **"Update all"** button to refresh installed skills. Installs run the same pre-execution security scan as `hermes skills install` — a skill flagged `dangerous` can't be force-installed, and `hermes skills audit` re-scans installed hub skills.
- **Toolsets** — separate section showing built-in toolsets (file, web, browser), with active/inactive state, setup requirements, and the list of tools each one provides

### Plugins

Plugins ship disabled. Use the dashboard to review what was discovered from bundled, user, project, pip, and Nix sources before enabling anything with hooks/tools.

Good first enables:

- `observability/langfuse` — trace LLM/tool calls to Langfuse
- `spotify` — native playback/queue/search tools
- `google_meet` — join, transcribe, speak, and follow up on Meet calls
- `hermes-achievements` — dashboard achievements from real session history

Project-local plugins under `.hermes/plugins/` should stay disabled unless you trust the repository.

### Curator

v0.12 adds Curator controls for skill-library hygiene: run dry-runs, inspect proposed archives/merges, pin important skills, and review archived skills before restoring or deleting. See [Part 5](./part5-creating-skills.md#curator-v012-keep-the-skill-library-from-rotting) and [Part 22](./part22-latest-power-moves.md#1-turn-on-curator-before-your-skill-library-becomes-noise).

---

## `/reload` — Pick Up `.env` Changes Live

When you change an API key in the dashboard (or edit `~/.hermes/.env` directly), you don't need to restart an active CLI session anymore.

In any interactive CLI:

```text
You → /reload
  Reloaded .env (3 var(s) updated)
```

That re-reads `~/.hermes/.env` into the running process environment. Perfect when you add a new provider key and want to switch to it without losing your session.

---

## REST API (for Automation)

The dashboard frontend is just a client of a documented REST API. You can script against it directly — handy for homelab dashboards, Raycast/Alfred shortcuts, Grafana exporters, etc.

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Agent version, gateway status, platform states, active session count (public; also reports `auth_required` / `auth_providers`) |
| `GET /api/sessions` | 20 most recent sessions with metadata |
| `GET /api/sessions/search?q=` | FTS5 full-text search across message content |
| `GET /api/sessions/{id}` / `GET /api/sessions/{id}/messages` | Session metadata / paged message history (incl. tool calls) |
| `GET /api/config`, `/api/config/defaults`, `/api/config/schema` | Current config as JSON, defaults, field schema |
| `PUT /api/config` | Save a new configuration. Body: `{"config": {...}}` |
| `GET /api/env`, `PUT /api/env`, `DELETE /api/env` | Read (redacted) / set / delete env vars |
| `GET /api/logs` | Tail log files with filters (`file`, `lines`, `level`, `component`) |
| `GET /api/analytics/usage` | Usage and cost analytics for a time range (`days`) |
| `GET/POST /api/cron/jobs`, `POST …/{id}/trigger`, `DELETE …/{id}` | Cron job CRUD + trigger |
| `GET /api/skills`, `PUT /api/skills/toggle`, `GET /api/tools/toolsets` | Skills/toolsets list + enable/disable |
| `GET/POST /api/mcp/servers`, `…/{name}/test`, `…/{name}/enabled`, `DELETE …/{name}` | MCP server management (env values redacted) |
| `GET/POST /api/mcp/catalog`, `…/install` | Browse and install from the Nous-approved MCP catalog |
| `GET /api/messaging/platforms`, `PUT …/{id}`, `POST …/{id}/test` | Channels page API — configure, enable, test platforms |
| `GET/POST /api/pairing`, `…/approve`, `…/revoke`, `…/clear-pending` | DM pairing approvals |
| `GET/POST/DELETE /api/webhooks`, `PUT …/{name}/enabled` | Webhook subscriptions |
| `GET/POST/DELETE /api/credentials/pool` | Rotating credential pool per provider |
| `GET/PUT /api/memory`, `POST /api/memory/reset` | Memory provider config + built-in resets |
| `POST /api/gateway/start` · `/stop` · `/restart` | Gateway lifecycle (backgrounded) |
| `POST /api/ops/doctor` · `/security-audit` · `/backup` · `/import` · `/dump` · `/prompt-size` | Diagnostics & maintenance (live log streaming) |
| `GET /api/hermes/update/check` | Update availability (commits behind, install method) — drives the System page check-before-update |
| `GET /api/system/stats` | Host stats — OS, CPU, memory, disk, uptime |

The management endpoint families accept an optional `?profile=<name>` query parameter (or `"profile"` in the JSON body for writes) that scopes the read/write to that profile's home — omit it to manage the dashboard's own profile.

Authentication: on a loopback bind requests need no token, but state-changing endpoints validate `Origin`/`Host` (DNS-rebinding protection). On a gated (non-loopback) dashboard every `/api/` endpoint sits behind the same auth gate as the UI — script with a session cookie from a login, or use the bearer-token provider if you've configured one. Don't expose an unauthenticated loopback dashboard to anything that can reach `127.0.0.1`.

---

## Dashboard Plugins (Extend the UI)

The dashboard is pluggable. A plugin can add its own tab, call the existing API, and optionally register new backend endpoints — all without touching the dashboard source.

### Minimum Plugin

```bash
mkdir -p ~/.hermes/plugins/my-plugin/dashboard/dist
```

`~/.hermes/plugins/my-plugin/dashboard/manifest.json`:

```json
{
  "name": "my-plugin",
  "label": "My Plugin",
  "icon": "Sparkles",
  "version": "1.0.0",
  "tab": { "path": "/my-plugin", "position": "after:skills" },
  "entry": "dist/index.js"
}
```

`~/.hermes/plugins/my-plugin/dashboard/dist/index.js`:

```javascript
(function () {
  var SDK = window.__HERMES_PLUGIN_SDK__;
  var React = SDK.React;
  var Card = SDK.components.Card;
  var CardHeader = SDK.components.CardHeader;
  var CardTitle = SDK.components.CardTitle;
  var CardContent = SDK.components.CardContent;

  function MyPage() {
    return React.createElement(Card, null,
      React.createElement(CardHeader, null,
        React.createElement(CardTitle, null, "My Plugin")),
      React.createElement(CardContent, null,
        React.createElement("p", { className: "text-sm text-muted-foreground" },
          "Hello from my custom dashboard tab!")));
  }

  window.__HERMES_PLUGINS__.register("my-plugin", MyPage);
})();
```

Refresh the dashboard — your tab appears in the nav bar.

Plugins live next to existing CLI/gateway plugins under `~/.hermes/plugins/`. You can ship a plugin that provides a CLI tool *and* a dashboard tab from the same directory.

### Plugin Layout

```
~/.hermes/plugins/my-plugin/
├── plugin.yaml              # optional — existing CLI/gateway plugin manifest
├── __init__.py              # optional — existing CLI/gateway hooks
└── dashboard/               # dashboard extension
    ├── manifest.json        # required — tab config, icon, entry point
    ├── dist/
    │   ├── index.js         # required — pre-built JS bundle
    │   └── style.css        # optional — custom CSS
    └── plugin_api.py        # optional — backend API routes
```

---

## Troubleshooting

### "Missing web dependencies"

```bash
# pip install
pip install 'hermes-agent[web]'

# or, source install:
cd ~/.hermes/hermes-agent && uv pip install -e ".[web]"
```

Or reinstall with `[all]` to get every optional extra.

### "Frontend not built"

The dashboard tries to auto-build the frontend on first launch if `npm` is on PATH (it also rebuilds automatically after `hermes update`). If it can't, build manually:

```bash
cd ~/.hermes/hermes-agent
npm install && npm run build   # from the repo root web/ dir
```

For non-interactive contexts (Windows Scheduled Tasks, CI) where npm isn't available, run `hermes dashboard --skip-build` to serve the existing build.

### "Port 9119 already in use"

```bash
hermes dashboard --port 9200

# or find and stop the running dashboard processes
hermes dashboard --status
hermes dashboard --stop
```

### Dashboard shows stale data

Hit the browser refresh button. Status polls every 5s; other pages reload on navigation.

### Changed a config but it didn't take effect

Config is read at session start and gateway start. For an active CLI session, run `/reload` to pick up `.env` changes. For config.yaml changes, start a new session or restart the gateway.

---

## What's Next

- **Save on API keys:** [Part 13 — Nous Tool Gateway](./part13-tool-gateway.md)
- **Speed up responses:** [Part 14 — Fast Mode & Background Watchers](./part14-fast-mode-watchers.md)
- **Expand reach:** [Part 15 — New Platforms (Teams, LINE, SimpleX, iMessage, WeChat, Android)](./part15-new-platforms.md)
