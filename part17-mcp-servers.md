# Part 17: MCP Servers — Give Hermes Any Tool With Zero Glue Code

*Model Context Protocol (MCP) is the "USB-C of AI agents" — a standard way for any tool server to plug into any agent. Hermes has supported MCP natively since [v0.7.0](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.4.3). This is the part of the guide nobody reads until they realize they can stop writing tool adapters by hand.*

---

## Why This Matters

Before MCP, every agent framework had its own tool-calling schema. You'd write a GitHub tool for Hermes, then rewrite it for Claude Code, then rewrite it again for Cursor. All three calling the same GitHub API.

MCP (introduced by Anthropic, now a de facto standard across Claude Code, Cursor, GitHub Copilot, Devin, and Hermes) defines:

- **Tool discovery** — a standard JSON format for describing inputs and outputs
- **Transports** — stdio (local subprocess) and HTTP (remote server)
- **Bi-directional sampling** — MCP servers can ask the agent to run an LLM call on their behalf

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
│  │  ├─ github-mcp     (stdio, subprocess)      │  │
│  │  ├─ postgres-mcp   (stdio, subprocess)      │  │
│  │  ├─ mem0-mcp       (http, remote)           │  │
│  │  └─ your-mcp       (stdio or http)          │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

Hermes auto-discovers tools at startup and subscribes to dynamic updates — if an MCP server adds a new tool mid-session, Hermes picks it up without a restart.

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

Hermes spawns the subprocess on startup, pipes JSON-RPC over stdio, and unspawns it on exit. Restart Hermes after adding a new stdio server.

### HTTP / SSE Servers (Remote)

```yaml
mcp_servers:
  mem0:
    url: https://mcp.mem0.ai/sse
    headers:
      Authorization: Bearer ${MEM0_API_KEY}

  cloudflare:
    url: https://observability.mcp.cloudflare.com/sse
    headers:
      Authorization: Bearer ${CLOUDFLARE_API_TOKEN}
```

HTTP servers can add/remove tools live. Hermes handles reconnection with exponential backoff.

### Scoped Enablement

Some servers are chatty — you don't want every tool they expose loaded into every conversation. Scope them:

```yaml
mcp_servers:
  postgres:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
    enabled_for:                     # Only load in these sessions
      - profile: engineering
      - channel: "#data-questions"
    tools_allowlist:                 # Only expose these tools
      - query
      - describe_table
```

Without a `tools_allowlist`, every tool the server exposes is available.

---

## The MCP Servers Worth Installing Today

These are the ones that pay for themselves within a day:

| Server | What it adds | Why you want it |
|--------|--------------|-----------------|
| **@modelcontextprotocol/server-github** | Issues, PRs, repo search, branch diffs | Hermes becomes a code-aware teammate |
| **@modelcontextprotocol/server-filesystem** | Scoped file reads/writes/search | Safer than giving terminal access |
| **@modelcontextprotocol/server-postgres** | Read-only SQL | Answer "what's in the db?" without exposing DSN |
| **@modelcontextprotocol/server-sqlite** | Local SQLite analysis | Great for log files, analytics snapshots |
| **@modelcontextprotocol/server-puppeteer** | Browser automation | Complement to the Tool Gateway's Browser Use |
| **@modelcontextprotocol/server-memory** | Knowledge-graph memory | Pairs with [Part 3 LightRAG](./part3-lightrag-setup.md) for redundancy |
| **mcp.mem0.ai** | Hosted long-term memory | Cross-device memory across Hermes + Claude Code |
| **Cloudflare Observability MCP** | Query your Worker logs/analytics | If you run anything on Cloudflare |
| **@supabase/mcp-server-supabase** | Supabase RPC + Postgres + storage | One config for a whole backend |
| **linear-mcp** | Linear issue CRUD | Turn Hermes into an issue assignee |
| **stripe-mcp** | Stripe reads (customers, subs) | Support triage from Telegram |
| **@notionhq/notion-mcp-server** | Notion pages + databases | Company wiki as grounded context |
| **@browserbase/mcp** | Headless browser-as-a-service | Scraping sites Firecrawl can't handle |
| **@chroma-core/chroma-mcp** | ChromaDB vectors | Works alongside LightRAG |

For the full catalog, see [modelcontextprotocol.io/servers](https://modelcontextprotocol.io/servers) and the `awesome-mcp-servers` list on GitHub.

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

Register it:

```yaml
mcp_servers:
  ops:
    command: node
    args: ["/home/you/mcp/my-mcp/index.js"]
```

Now `deploy_staging` is a tool Hermes can call from any surface — CLI, Telegram, iMessage, Discord — without touching Hermes' code.

---

## Sampling: Letting an MCP Server Call the LLM

This is MCP's killer feature and the reason it matters for agents specifically. MCP servers can request LLM inference from Hermes via `sampling/createMessage`:

- A scraper MCP fetches a messy page → asks Hermes' LLM to extract the structured data → returns the structured data to the agent.
- A security-review MCP reads a diff → asks the LLM to classify severity → returns a triage label.
- A translation MCP reads a file → asks the LLM to localize it → writes the output.

Hermes handles the inference request with the active provider and meters the tokens against the current session. Enable sampling for a server:

```yaml
mcp_servers:
  scraper:
    command: node
    args: ["./scraper-mcp.js"]
    allow_sampling: true              # Off by default
    sampling_model: gpt-5-mini        # Optional: pin a cheaper model for sampling
```

**Security note:** Sampling means an MCP server can burn your tokens. Only enable it for servers you trust. See [Part 19](./part19-security-playbook.md#mcp-server-trust-model).

---

## Observing MCP Traffic

```bash
/mcp list                            # Show registered servers + tool counts
/mcp reload                          # Reload servers without restarting Hermes
/mcp disable github                  # Temporarily unregister
/mcp enable github                   # Bring it back
```

The [Web Dashboard](./part12-web-dashboard.md) has an **MCP Servers** tab that shows connection status, tool list, recent invocations, and error logs for each server. This is the fastest way to debug a misbehaving MCP.

Set `HERMES_MCP_LOG=debug` in your `.env` to get full JSON-RPC traces in `~/.hermes/logs/mcp.log`. Turn this off in production — traces include tool arguments and results.

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

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `MCP server 'github' failed to start` | `npx` not on PATH in the gateway's environment | Use an absolute path in `command:` or set `PATH` in `env:` |
| Server shows connected but 0 tools | Permissions — server's env vars are missing its auth token | Check `env:` entries and that referenced `${VARS}` exist in `.env` |
| Tools show up in CLI but not Telegram | Gateway process has its own env — restart it after config change | `hermes gateway restart` |
| Constant reconnects on HTTP server | SSE timeout behind a reverse proxy | Set `proxy_read_timeout 300s` in nginx/Caddy |
| `sampling not permitted` in server logs | `allow_sampling: false` (default) | Set `allow_sampling: true` in the server's block |

---

## What's Next

- [Part 18: Delegating to Coding Agents](./part18-coding-agents.md) — use Claude Code, Codex, and Gemini CLI as sub-agents invoked through Hermes (some ship MCP servers too)
- [Part 19: Security Playbook](./part19-security-playbook.md) — MCP trust model, sampling limits, and how untrusted MCPs get quarantined
- [Part 12: Web Dashboard](./part12-web-dashboard.md) — the MCP Servers panel
