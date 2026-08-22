# Part 17: MCP Servers — Give Hermes Any Tool With Zero Glue Code

*Model Context Protocol (MCP) is the "USB-C of AI agents" — a standard way for any tool server to plug into any agent. Hermes has supported MCP natively since [v0.7.0](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.4.3), and v0.20 rounds out the story with a full `hermes mcp` CLI suite (catalog, add/remove/test, OAuth, and running Hermes *as* an MCP server). This is the part of the guide nobody reads until they realize they can stop writing tool adapters by hand.*

---

## Why This Matters

Before MCP, every agent framework had its own tool-calling schema. You'd write a GitHub tool for Hermes, then rewrite it for Claude Code, then rewrite it again for Cursor. All three calling the same GitHub API.

MCP (introduced by Anthropic, now a de facto standard across Claude Code, Cursor, GitHub Copilot, Devin, and Hermes) defines:

- **Tool discovery** — a standard JSON format for describing inputs and outputs
- **Transports** — stdio (local subprocess), Streamable HTTP, and SSE (remote server)
- **Bi-directional sampling** — MCP servers can ask the agent to run an LLM call on their behalf
- **Elicitation** — MCP servers can ask *you* for structured input mid-tool-call (v0.20 era)

Hermes plugs into this ecosystem. Point it at any MCP server — community-built or your own — and the tools show up next to Hermes' built-ins with zero code changes. This is the most leveraged hour you'll spend optimizing your agent.

---

## How MCP Fits Into Hermes

```
┌────────────────────────────────────────────────────┐
│  Hermes Agent                                       │
│  ┌──────────────────────────────────────────────┐  │
│  │  Built-in tools (terminal, skills, memory)   │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │  MCP Client                                  │  │
│  │  ├─ github       (stdio, subprocess)         │  │
│  │  ├─ filesystem   (stdio, subprocess)         │  │
│  │  ├─ linear       (http, OAuth 2.1 remote)    │  │
│  │  └─ your-mcp     (stdio or http)             │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

Hermes discovers MCP servers at startup and registers their tools into the normal tool registry — and it **subscribes to dynamic updates**: if a server pushes a `tools/list_changed` notification mid-session, Hermes re-fetches and updates the tool list without a restart.

### The `hermes mcp` CLI (v0.20)

MCP management is now a first-class CLI surface, not just config-file editing:

```bash
hermes mcp                  # interactive picker (also the default)
hermes mcp catalog          # plain-text list of Nous-approved MCPs, scriptable
hermes mcp install n8n      # install a catalog entry by name (walks credentials)
hermes mcp add my-server --command npx --args -y @my/mcp   # add any custom server
hermes mcp list             # (ls) what's configured
hermes mcp test github      # test a server's connection
hermes mcp configure github # toggle which of its tools are exposed
hermes mcp login linear     # force OAuth re-auth
hermes mcp serve            # run Hermes ITSELF as an MCP server (see below)
hermes mcp remove my-server # (rm) drop a server from config
```

**Catalog:** Hermes ships a curated catalog of MCP servers that Nous staff reviewed and merged (stored under `optional-mcps/` in the repo — presence there *is* the approval). Entries are disabled by default; `hermes mcp install <name>` installs one, walking any required API keys or OAuth at install time. Install is the only place something runs — **read the manifest before installing** (`source:` repo, `install.bootstrap:` commands), and re-check the `source:` URL the picker prints. For well-known servers, `hermes mcp add codex --preset codex` fills in transport defaults (`codex mcp-server` over stdio) for you.

---

## Configuration

MCP servers live under the `mcp_servers` key in `~/.hermes/config.yaml`.

### stdio Servers (Local Subprocess)

```yaml
mcp_servers:
  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}

  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/you/projects"]

  postgres:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
```

Hermes spawns the subprocess on startup, pipes JSON-RPC over stdio, and cleans it up on exit. Reload config without a restart with `/reload-mcp` in the CLI or messaging.

### HTTP / SSE Servers (Remote)

```yaml
mcp_servers:
  remote_api:
    url: https://mcp.example.com/mcp
    headers:
      Authorization: Bearer ${API_TOKEN}

  my_sse:
    url: https://mcp.example.com/sse
    transport: sse          # default for url servers is Streamable HTTP; set sse to opt out

  linear:
    url: https://mcp.linear.app/mcp
    auth: oauth             # OAuth 2.1 with PKCE — Hermes handles discovery, login,
                            # token refresh; tokens cached in ~/.hermes/mcp-tokens/
```

Remote servers support TLS controls (`ssl_verify`, `client_cert`/`client_key` for mTLS), a per-user `identity_header`, OAuth 2.1 (`auth: oauth`, refresh automatic, re-run with `hermes mcp login <name>`), and `protocol` negotiation (`auto` | `stateless` | `legacy`) for the 2026-07-28 spec era.

**Env and context variables.** Any string in a server entry can interpolate `${VAR}` (or Cursor-style `${env:VAR}`), plus the context variables `${userHome}`, `${workspaceFolder}`, `${workspaceFolderBasename}`, `${pathSeparator}`. MCP snippets copied from Claude Code/Cursor configs work unchanged:

```yaml
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "${workspaceFolder}"]
```

### Per-server knobs

| Key | Meaning |
|-----|---------|
| `enabled: false` | Skip the server entirely: no connect, no discovery (config stays for later) |
| `timeout` / `connect_timeout` | Tool-call (default 300) and initial-connection (default 60) timeouts |
| `supports_parallel_tool_calls` | Let this server's tools run concurrently (read-only servers only — mind races) |
| `idle_timeout_seconds` / `max_lifetime_seconds` | Recycle memory-heavy stdio servers (e.g. Playwright keeps a full Chromium resident) — transparent restart on next use |
| `tools.include` / `tools.exclude` | Whitelist/blacklist tools, exact names or globs |
| `tools.resources` / `tools.prompts` | Also register `list_resources`/`read_resource`/`list_prompts`/`get_prompt` wrappers (capability-aware) |
| `sampling` | Server-initiated LLM requests policy (see Sampling) |
| `elicitation` | Server-initiated user-input requests (see Elicitation) |
| `trust` | `full` (default) or `untrusted` — approval policy for write-capable tools (see Trust) |

### Scoped Tool Exposure

Some servers are chatty — you don't want every tool they expose loaded into every conversation. The knob is per-server `tools.include` / `tools.exclude` (there is no per-profile or per-channel `enabled_for:` scoping — see [Part 19, Layer 5](./part19-security-playbook.md#layer-5-mcp-and-plugin-trust)):

```yaml
mcp_servers:
  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}
    enabled: true
    timeout: 120
    tools:
      include: [create_issue, list_issues, search_code]   # empty = all exposed
      exclude: []
      resources: false
      prompts: false
```

With an empty `tools.include`, every tool the server exposes is available. Both lists accept fnmatch globs — essential for huge flat surfaces like Cloudflare's API MCP (3,300+ tools): `exclude: ["*_radar_*", "*_accounts_dlp_*"]`. If both are set, `include` wins. If filtering strips everything and no utility tools remain, Hermes doesn't create an empty runtime toolset for that server.

MCP tools register with the prefix convention `mcp__<server>__<tool>`, e.g. `mcp__github__create_issue` — the same convention Claude Code, Codex, and OpenCode use. For filters, use the **original** server tool names (hyphens/dots intact), not the sanitized registered names.

---

## The MCP Servers Worth Installing Today

These are the ones that pay for themselves within a day:

> **2026 reality check:** MCP is also a supply-chain boundary. Prefer catalog entries or official servers, pin package versions, restrict filesystem roots, and use `tools.include` to expose only the tools you audited — trust is enforced by review and isolation, not a config flag ([Part 19, Layer 5](./part19-security-playbook.md#layer-5-mcp-and-plugin-trust)).

**One-click catalog entries** (Nous-reviewed; `hermes mcp install <name>`):

| Server | What it adds | Why you want it |
|--------|--------------|-----------------|
| **linear** | Find/create/update issues, projects, comments | Turn Hermes into an issue assignee (remote OAuth) |
| **stripe** | Payments, customers, invoices | Support triage from Telegram without touching the dashboard |
| **supabase** | Database, auth, storage from your projects | One config for a whole backend |
| **notion** | Pages + databases | Company wiki as grounded context |
| **atlassian** | Jira issues + Confluence pages (hosted remote MCP) | Enterprise ticket surface |
| **github — not cataloged** | Issues, PRs, repos | Hosted GitHub MCP requires your own OAuth app, so it isn't in the catalog — use the bundled `github/*` skills driving `gh`, or add the server manually (register via config) |
| **figma** | Design context, write-to-canvas | Live design context for frontend work |
| **n8n** | Inspect/manage n8n workflows (stdio bridge) | Automations, meet the agent |
| **datadog / sentry** | Logs, monitors, incidents / error context | Ops triage in-chat |
| **vercel / netlify / webflow / square / paypal / asana / intercom / comfy-cloud / unreal-engine** | Hosted integrations | Check `hermes mcp catalog` for the live list |

**Community servers worth wiring up** (via `hermes mcp add` or config — verify the current package name in the [MCP Registry](https://registry.modelcontextprotocol.io/)):

| Server | What it adds | Why you want it |
|--------|--------------|-----------------|
| **@modelcontextprotocol/server-github** | Issues, PRs, repo search, branch diffs | Hermes becomes a code-aware teammate |
| **@modelcontextprotocol/server-filesystem** | Scoped file reads/writes/search | Safer than giving terminal access |
| **@modelcontextprotocol/server-postgres** | Read-only SQL | Answer "what's in the db?" without exposing the DSN |
| **@modelcontextprotocol/server-sqlite** | Local SQLite analysis | Great for log files, analytics snapshots |
| **@brave/brave-search-mcp** | Live web search | Add it if you want a second search backend |
| **@playwright/mcp** | Browser automation | Complement to the Tool Gateway's Browser Use; sandbox it and set `max_lifetime_seconds` so Chromium memory gets recycled |
| **@upstash/context7-mcp** | Docs for any library (up-to-date) | Grounds "how do I use this SDK" answers |
| **@modelcontextprotocol/server-memory** | Knowledge-graph memory | Pairs with [Part 3 LightRAG](./part3-lightrag-setup.md) for redundancy |

For the full catalog, see `hermes mcp catalog` locally and the [MCP Registry](https://registry.modelcontextprotocol.io/) + `awesome-mcp-servers` on GitHub.

---

## MCP Security: July 2026 State of Play

MCP is no longer a theoretical attack surface — the 2025–2026 CVE trail is all one theme: **MCP configs and manifests are executable trust**.

| CVE | What | Lesson for Hermes users |
|-----|------|------------------------|
| CVE-2026-30623 | LiteLLM authenticated RCE via malicious MCP JSON (patched ≥ 1.83.7) | If you proxy Hermes through LiteLLM, patch it — an MCP *config* was the payload |
| CVE-2026-30615 | Windsurf: writable `mcp.json` → prompt injection → code execution | Anything that can *write* your MCP config owns your agent |
| CVE-2025-54136 | Cursor "MCPoison": approve once, config silently swapped later (fixed 1.3) | Re-approval must trigger on *change*, not just first add |
| CVE-2025-49596 | MCP Inspector RCE (browser → localhost, fixed 0.14.1) | Dev tools listening on localhost are reachable from any web page you visit |
| CVE-2026-22252 | LibreChat MCP `require()` injection via server config | Same class, different host — the pattern is universal |

The checklist that follows from it:

1. **Pin every MCP package to an exact version** — no `latest`, no floating ranges. Catalog installs are revision-controlled in `optional-mcps/`; community npx servers aren't — pin.
2. **Treat MCP blocks in cloned repos as untrusted input.** Never launch with MCP servers from a repo you haven't reviewed — that's the MCPoison delivery vehicle (and `hermes import-agent` previews exactly what it would import for a reason).
3. **Watch for registry impersonators.** Fake `mem0-mcp`-style packages ship info-stealers under trusted names; install from the vendor's documented source and check publish dates.
4. **Never expose MCP dev tools (Inspector etc.) beyond localhost.**
5. **Separate tokens per server, minimal scopes** — a compromised MCP config should burn one narrow credential, not your account.
6. **Strip environment leakage** — stdio servers get only the `env` you configure plus a safe baseline, never your full shell environment.
7. **Add OSV/CVE monitoring** for the MCP packages you run (a weekly cron works — see [Part 19](./part19-security-playbook.md#periodic-security-hygiene)).

`tools.include` scoping, isolation backends, and the broader trust model live in [Part 19, Layer 5](./part19-security-playbook.md#layer-5-mcp-and-plugin-trust).

### Trust tiers: `trust: full | untrusted`

Since the v0.20 era, every server has a trust tier. On a server marked `untrusted`, **every write-capable tool call** (any tool without a `readOnlyHint: true` annotation) requires your approval through the standard approval surface before it runs. `readOnlyHint` is only a *hint* from the server — a lying server can at most skip approval for tools it claims are read-only, never gain extra access — so mark any server you don't fully control as `untrusted`:

```yaml
mcp_servers:
  sketchy_helper:
    url: https://mcp.example.com
    trust: untrusted     # every write tool call prompts for approval
```

Unknown values fail closed (`untrusted`). Combined with `tools.include` allowlisting, this is the "review before, enforce at runtime" posture.

---

## Writing Your Own MCP Server (Fast)

A minimal Node MCP server is ~30 lines. Python is similar. Point Hermes at it like any other stdio server.

```javascript
// my-mcp/index.js
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server(
  { name: "my-mcp", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler("tools/list", async () => ({
  tools: [{
    name: "deploy_staging",
    description: "Deploys current git HEAD to the staging environment",
    inputSchema: {
      type: "object",
      properties: { service: { type: "string" } },
      required: ["service"]
    }
  }]
}));

server.setRequestHandler("tools/call", async (req) => {
  if (req.params.name === "deploy_staging") {
    const result = await deployStaging(req.params.arguments.service);
    return { content: [{ type: "text", text: result }] };
  }
});

await server.connect(new StdioServerTransport());
```

Register it — directly in config...

```yaml
mcp_servers:
  ops:
    command: node
    args: ["/home/you/mcp/my-mcp/index.js"]
```

...or from the CLI:

```bash
hermes mcp add ops --command node --args /home/you/mcp/my-mcp/index.js
```

Now `deploy_staging` is a tool Hermes can call from any surface — CLI, Telegram, iMessage, Teams — without touching Hermes' code. (Prefer packages: the `@modelcontextprotocol/sdk` and the Python `mcp` SDK both cover stdio, Streamable HTTP, and SSE.)

---

## Sampling: Letting an MCP Server Call the LLM

MCP servers can request LLM inference from Hermes via `sampling/createMessage` — useful for servers that need model capability without their own model access:

- A scraper MCP fetches a messy page → asks Hermes' LLM to extract the structured data → returns the structured data to the agent.
- A security-review MCP reads a diff → asks the LLM to classify severity → returns a triage label.
- A translation MCP reads a file → asks the LLM to localize it → writes the output.

Sampling is **on by default** and **configurable per server** since v0.20 — the previous "no knobs" state is gone:

```yaml
mcp_servers:
  my_server:
    command: "my-mcp-server"
    sampling:
      enabled: true            # default: true
      model: "openai/gpt-4o"   # override the sampling model (optional)
      max_tokens_cap: 4096     # default 4096
      timeout: 30              # default 30s per request
      max_rpm: 10              # rate limit — default 10 req/min
      max_tool_rounds: 5       # cap tool-use loops inside sampling
      allowed_models: []       # allowlist; empty = any model
```

The handler includes a sliding-window rate limiter, per-request timeouts, and loop-depth caps, with per-server metrics. Disable for servers you don't fully trust: `sampling: { enabled: false }`. Only run sampling-capable servers you've actually read.

---

## Elicitation: When a Server Needs *You* Mid-Tool-Call

MCP servers can also ask the user for **structured input mid-tool-call** (`elicitation/create`, mcp Python SDK ≥ 1.11.0). Hermes routes **form-mode** elicitations through its existing approval surface — an interactive prompt in the CLI/TUI, or approval buttons on gateway platforms like Telegram and Slack — so you approve a form wherever the session lives. **URL-mode** elicitations (a server pointing you at an external web page) are declined by design.

```yaml
mcp_servers:
  my_server:
    command: "my-mcp-server"
    elicitation:
      enabled: true    # default: true
      timeout: 300     # how long to wait for your answer (default: 300s)
```

Security posture is the same as sampling: only run elicitation-capable servers you've read, and expect a mid-call prompt — that's the feature working.

---

## Observing MCP Traffic

```bash
hermes mcp list        # what's configured + server status
hermes mcp test github # one-off connection + tool-discovery probe
hermes mcp configure github  # re-run the tool checklist
```

Inside a session: `/reload-mcp` re-reads config and refreshes the tool list (also fires on config auto-reload when you edit config.yaml). If a specific server misbehaves, ask Hermes to run `hermes mcp test <name>` and paste the output — it's the fastest repro for connection vs permission vs discovery failures.

The [Web Dashboard](./part12-web-dashboard.md) has an **MCP** page that shows connection status, tool lists, recent invocations, and error logs per server (and per catalog entry: transport, auth, the git source/ref and bootstrap commands — rendered as clickable links, so you can inspect exactly what an entry installs before clicking Install). That's the fastest way to eyeball a misbehaving server.

---

## When MCP Is Overkill

MCP adds a process (or a network hop) per tool. For things that live inside Hermes already, don't bother:

- **Terminal commands** — just use the built-in `terminal` tool.
- **File edits** — built-in file tools are faster than filesystem MCP if the files are local.
- **Skills** — if the workflow is deterministic, a [skill](./part5-creating-skills.md) is cheaper to maintain.

Use MCP when you want:

- A tool that already has a community-maintained server (GitHub, Slack, Postgres, etc.)
- A tool you'd want to share with other agents (Claude Code, Cursor, Copilot)
- A tool that needs its own runtime (Node/Go/Rust) you'd rather not embed into Hermes
- To expose Hermes' own messaging to other agents (`hermes mcp serve` — next)

---

## Running Hermes as an MCP Server: `hermes mcp serve`

The other side of the protocol: **Hermes itself becomes an MCP server**, so Claude Code, Cursor, Codex, or any MCP client can use Hermes' messaging capabilities — list conversations, read history, send messages across every connected platform — from inside that agent.

```bash
hermes mcp serve          # stdio MCP server; the client manages the process
hermes mcp serve --verbose
```

Add to a client's config (e.g. Claude Code):

```json
{
  "mcpServers": {
    "hermes": { "command": "hermes", "args": ["mcp", "serve"] }
  }
}
```

Available tools (matching the channel-bridge surface): `conversations_list`, `conversation_get`, `messages_read`, `attachments_fetch`, `events_poll`, `events_wait`, `messages_send` (e.g. `telegram:123456`, `discord:#general`), `channels_list`, `permissions_list_open`, and `permissions_respond` (approve/deny pending approval requests straight from the coding agent). The gateway doesn't need to run for reads; it must run for sends. Current limits: stdio-only server today (the *client* side of Hermes speaks stdio + HTTP), text-only sends, event polling at ~200ms.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `MCP server 'X' failed to start` | `npx` not on PATH in the gateway's environment | Use an absolute path in `command:` or set `PATH` in `env:` |
| Server connects but 0 tools | Discovery failed — server's env vars are missing its auth token | Check `env:` entries and that referenced `${VARS}` exist in `.env`; run `hermes mcp test <name>` |
| Tools show up in CLI but not messaging | Gateway process has its own env — reload or restart it after config change | `/reload-mcp` in the chat, or `hermes gateway restart` |
| Constant reconnects on an HTTP server | SSE timeout behind the reverse proxy | Set `proxy_read_timeout 300s` in nginx/Caddy, or `keepalive_interval` lower than the server's session TTL |
| Runaway token spend from one server | A sampling-capable server looping on `sampling/createMessage` | `sampling: { enabled: false }` (or cap `max_rpm`), review the server's code, and re-check it as `trust: untrusted` |
| Server asks for input via a web page | URL-mode elicitation | Declined by design — use/request a form-mode elicitation instead |

---

## What's Next

- [Part 18: Delegating to Coding Agents](./part18-coding-agents.md) — use Claude Code, Codex, and Gemini CLI as sub-agents invoked through Hermes (some ship MCP servers too)
- [Part 19: Security Playbook](./part19-security-playbook.md) — the MCP trust model ((Layer 5)) and why review-before-install, tool allowlists, and `trust: untrusted` are the real controls
- [Part 12: Web Dashboard](./part12-web-dashboard.md) — the MCP panel
- [Part 16: Backup & Debug](./part16-backup-debug.md) — `hermes import-agent` migrates MCP servers from Claude Code / Codex