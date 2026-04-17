# Part 12: The Local Web Dashboard (Stop Editing YAML)

*New in Hermes v0.9.0 (2026.4.13). The easiest way to run Hermes — a full browser-based control panel for everything you used to do in the terminal.*

---

## Why This Matters

Before v0.9, managing Hermes meant: edit `config.yaml`, export env vars, grep through logs, and use the CLI to inspect sessions. Great for power users. Terrible for anyone new.

The new **web dashboard** (`hermes dashboard`) replaces all of that with a single browser UI:

- Live status of the gateway and all 16 platform adapters
- Form-based editor for every config field (all 150+ of them, auto-discovered from `DEFAULT_CONFIG`)
- API key manager for providers, tools, and platforms
- Full-text search across past sessions (FTS5)
- Log tailer with level/component filters
- Usage and cost analytics (daily token + cost breakdown, per-model)
- Cron job management
- Skills and toolsets browser with enable/disable toggles

Everything runs on `127.0.0.1` — no data leaves your machine.

---

## Quick Start

```bash
hermes dashboard
```

That's it. It starts a local server and opens `http://127.0.0.1:9119` in your default browser.

### Install the Dependencies (One Time)

The dashboard uses FastAPI + Uvicorn + a React frontend:

```bash
pip install hermes-agent[web]
```

If you installed with `hermes-agent[all]`, you're already done. The frontend auto-builds on first launch if `npm` is available.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `9119` | Port to serve on |
| `--host` | `127.0.0.1` | Bind address |
| `--no-open` | — | Don't auto-open the browser |

```bash
# Custom port
hermes dashboard --port 8080

# Bind to all interfaces (use with caution — see security note below)
hermes dashboard --host 0.0.0.0

# Start without opening the browser
hermes dashboard --no-open
```

> **Security:** The dashboard reads and writes your `.env` file. It has **no authentication of its own**. Keep it on `127.0.0.1`. If you must expose it (e.g., a homelab), put it behind a reverse proxy with authentication or use SSH port-forwarding: `ssh -L 9119:127.0.0.1:9119 user@your-server`.

---

## Pages at a Glance

### Status

Live overview that auto-refreshes every 5 seconds:

- Agent version + release date
- Gateway state — running/stopped, PID, every connected platform with its own state
- Active sessions — everything alive in the last 5 minutes
- Recent sessions — the last 20, with model, message count, token usage, and a preview

This is the page you leave open on a second monitor.

### Config

Form-based editor for `config.yaml`. Fields are auto-discovered from `DEFAULT_CONFIG` and grouped into tabs:

- **model** — default model, provider, base URL, reasoning settings
- **terminal** — backend (local / docker / ssh / modal), timeouts, shell preferences
- **display** — skin, tool progress rendering, spinner settings
- **agent** — max iterations, gateway timeout, `service_tier` (Fast Mode)
- **delegation** — subagent limits, reasoning effort
- **memory** — provider, context injection settings
- **approvals** — dangerous command mode (`ask` / `yolo` / `deny`)

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

### Cron

Create and manage scheduled agent prompts.

- **Create** — name, prompt, cron expression (e.g. `0 9 * * *`), delivery target (local / Telegram / Discord / Slack / email)
- **Job list** — name, prompt preview, schedule, state badge, delivery target, last run, next run
- **Pause / Resume** — toggle active state
- **Trigger now** — run a job immediately, outside its normal schedule
- **Delete** — remove permanently

This replaces the old `hermes cron create …` CLI flow for most people.

### Skills

Browse, search, and toggle every skill and toolset.

- **Search** — filter by name, description, or category
- **Category filter** — click pills to narrow (MLOps, MCP, Red Teaming, AI, etc.)
- **Toggle** — enable/disable individual skills per session
- **Toolsets** — separate section showing built-in toolsets (file, web, browser), with active/inactive state, setup requirements, and the list of tools each one provides

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
| `GET /api/status` | Agent version, gateway status, platform states, active session count |
| `GET /api/sessions` | 20 most recent sessions with metadata |
| `GET /api/sessions/{id}` | Full message history for a session |
| `GET /api/config` | Current `config.yaml` as JSON |
| `GET /api/config/defaults` | Default configuration values |
| `GET /api/config/schema` | Schema for every config field (type, description, category, options) |
| `PUT /api/config` | Save a new configuration. Body: `{"config": {...}}` |
| `GET /api/env` | All known env vars with set/unset status, redacted values, descriptions |
| `PUT /api/env` | Set a variable. Body: `{"key": "VAR_NAME", "value": "secret"}` |
| `DELETE /api/env` | Delete a variable |
| `GET /api/logs` | Tail log files with filters |
| `GET /api/analytics` | Usage and cost analytics for a time range |
| `GET /api/cron/jobs` | List cron jobs |
| `POST /api/cron/jobs` | Create a cron job |
| `POST /api/cron/jobs/{id}/trigger` | Trigger a job immediately |
| `GET /api/skills` | List skills and toolsets |

Requests are unauthenticated and only listen on `127.0.0.1` — trust the local-machine boundary.

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
pip install hermes-agent[web]
```

Or reinstall with `[all]` to get every optional extra.

### "Frontend not built"

The dashboard tries to auto-build the frontend on first launch if `npm` is on PATH. If it can't, build manually:

```bash
cd ~/.hermes/hermes-agent/hermes_agent/web_dashboard/frontend
npm install && npm run build
```

### "Port 9119 already in use"

```bash
hermes dashboard --port 9200
```

### Dashboard shows stale data

Hit the browser refresh button. Status polls every 5s; other pages reload on navigation.

### Changed a config but it didn't take effect

Config is read at session start and gateway start. For an active CLI session, run `/reload` to pick up `.env` changes. For config.yaml changes, start a new session or restart the gateway.

---

## What's Next

- **Save on API keys:** [Part 13 — Nous Tool Gateway](./part13-tool-gateway.md)
- **Speed up responses:** [Part 14 — Fast Mode & Background Watchers](./part14-fast-mode-watchers.md)
- **Expand reach:** [Part 15 — New Platforms (iMessage, WeChat, Android)](./part15-new-platforms.md)
