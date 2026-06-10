# Part 17: MCP Servers — Give Hermes Any Tool With Zero Glue Code

_Model Context Protocol (MCP) is the "USB-C of AI agents" — a standard way for any tool server to plug into any agent. Hermes has supported MCP natively since [v0.7.0](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.4.3). This is the part of the guide nobody reads until they realize they can stop writing tool adapters by hand._

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

MCP servers are managed by the Hermes CLI. Hermes may persist MCP entries in its own config/registry, but operators should treat `hermes mcp add/list/test/configure` as the source of truth instead of hand-authoring an `mcp_servers:` block from old examples.

Use this loop for every server:

```bash
hermes mcp add NAME [--url URL] [--command MCP_COMMAND] [--args ...] [--auth oauth|header] [--preset PRESET] [--env KEY=VALUE]
hermes mcp test NAME
hermes mcp list
```

Use `hermes mcp configure NAME` when a server needs auth, tool filtering, or other CLI-managed settings.

### stdio Servers (Local Subprocess)

```bash
hermes mcp add github --command npx --env GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_TOKEN} --args -y @modelcontextprotocol/server-github
hermes mcp add filesystem --command npx --args -y @modelcontextprotocol/server-filesystem /home/you/projects
hermes mcp add postgres --command npx --args -y @modelcontextprotocol/server-postgres "$DATABASE_URL"

hermes mcp test github
hermes mcp list
```

Hermes spawns stdio servers as CLI-managed subprocesses, pipes JSON-RPC over stdio, and unspawns them on exit. Use `hermes mcp test NAME` immediately after adding a server so command, args, env, and tool discovery fail fast.

### HTTP / SSE Servers (Remote)

```bash
hermes mcp add mem0 --url https://mcp.mem0.ai/sse --auth header
hermes mcp configure mem0
hermes mcp test mem0

hermes mcp add linear --url https://mcp.linear.app/mcp --auth oauth
hermes mcp configure linear
hermes mcp test linear
```

HTTP servers can add/remove tools live. Hermes handles reconnection with exponential backoff. For header or OAuth auth, register the transport first, then use `hermes mcp configure NAME` so secrets stay in Hermes-managed state instead of pasted into guide YAML.

### Scoped Enablement

Some servers are chatty — you don't want every tool they expose loaded into every conversation. Scope them:

```bash
hermes mcp configure postgres
hermes mcp test postgres
hermes mcp list
```

Use the configure flow to restrict auth, profiles, roots, or exposed tools when your Hermes build exposes those controls. If the CLI does not show a restriction you need, leave the server unregistered or keep it in a lower-trust Hermes home instead of inventing YAML keys.

---

## The MCP Servers Worth Installing Today

These are the ones that pay for themselves within a day:

> **2026 reality check:** MCP is also a supply-chain boundary. Prefer official servers, pin package versions, restrict filesystem roots, and review sampling-capable servers before enabling or keeping them registered.

| Server                                      | What it adds                           | Why you want it                                                        |
| ------------------------------------------- | -------------------------------------- | ---------------------------------------------------------------------- |
| **@modelcontextprotocol/server-github**     | Issues, PRs, repo search, branch diffs | Hermes becomes a code-aware teammate                                   |
| **@modelcontextprotocol/server-filesystem** | Scoped file reads/writes/search        | Safer than giving terminal access                                      |
| **@modelcontextprotocol/server-postgres**   | Read-only SQL                          | Answer "what's in the db?" without exposing DSN                        |
| **@modelcontextprotocol/server-sqlite**     | Local SQLite analysis                  | Great for log files, analytics snapshots                               |
| **@modelcontextprotocol/server-puppeteer**  | Browser automation                     | Complement to the Tool Gateway's Browser Use; sandbox it tightly       |
| **@modelcontextprotocol/server-memory**     | Knowledge-graph memory                 | Pairs with [Part 3 LightRAG](./part3-lightrag-setup.md) for redundancy |
| **mcp.mem0.ai**                             | Hosted long-term memory                | Cross-device memory across Hermes + Claude Code                        |
| **Cloudflare Observability MCP**            | Query your Worker logs/analytics       | If you run anything on Cloudflare                                      |
| **@supabase/mcp-server-supabase**           | Supabase RPC + Postgres + storage      | One config for a whole backend                                         |
| **linear-mcp**                              | Linear issue CRUD                      | Turn Hermes into an issue assignee                                     |
| **stripe-mcp**                              | Stripe reads (customers, subs)         | Support triage from Telegram                                           |
| **@notionhq/notion-mcp-server**             | Notion pages + databases               | Company wiki as grounded context                                       |
| **@browserbase/mcp**                        | Headless browser-as-a-service          | Scraping sites Firecrawl can't handle                                  |
| **@chroma-core/chroma-mcp**                 | ChromaDB vectors                       | Works alongside LightRAG                                               |

For the full catalog, see the [MCP Registry](https://registry.modelcontextprotocol.io/) and the `awesome-mcp-servers` list on GitHub.

---

## Writing Your Own MCP Server (Fast)

A minimal Node MCP server is ~30 lines. Python is similar. Point Hermes at it like any other stdio server.

```javascript
// my-mcp/index.js
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server(
  { name: "my-mcp", version: "0.1.0" },
  { capabilities: { tools: {} } },
);

server.setRequestHandler("tools/list", async () => ({
  tools: [
    {
      name: "deploy_staging",
      description: "Deploys current git HEAD to the staging environment",
      inputSchema: {
        type: "object",
        properties: { service: { type: "string" } },
        required: ["service"],
      },
    },
  ],
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

```bash
hermes mcp add ops --command node --args /home/you/mcp/my-mcp/index.js
hermes mcp test ops
```

Now `deploy_staging` is a tool Hermes can call from any surface — CLI, Telegram, iMessage, Discord — without touching Hermes' code.

---

## Sampling: Letting an MCP Server Call the LLM

This is MCP's killer feature and the reason it matters for agents specifically. MCP servers can request LLM inference from Hermes via `sampling/createMessage`:

- A scraper MCP fetches a messy page → asks Hermes' LLM to extract the structured data → returns the structured data to the agent.
- A security-review MCP reads a diff → asks the LLM to classify severity → returns a triage label.
- A translation MCP reads a file → asks the LLM to localize it → writes the output.

Hermes handles the inference request with the active provider and meters the tokens against the current session. Do not add a YAML `allow_sampling:` block; current MCP setup is CLI-managed. If a server needs sampling or any other privileged behavior, review it first, then use the CLI-managed settings:

```bash
hermes mcp add scraper --command node --args ./scraper-mcp.js
hermes mcp configure scraper
hermes mcp test scraper
```

**Security note:** Sampling means an MCP server can burn your tokens. Only keep sampling-capable servers registered when you trust their code and have verified the CLI-managed restrictions. See [Part 19](./part19-security-playbook.md#layer-5-mcp-and-plugin-trust).

---

## Observing MCP Traffic

```bash
hermes mcp list                      # Show registered servers and tool counts
hermes mcp test github               # Start the server and verify discovery
hermes mcp configure github          # Change auth/env/tool settings
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

| Symptom                                 | Likely cause                                                          | Fix                                                                                |
| --------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `MCP server 'github' failed to start`   | `npx` not on PATH in the Hermes environment                           | Run `hermes mcp configure github` and set an absolute command or PATH/env override |
| Server shows connected but 0 tools      | Permissions or auth values are missing                                | Run `hermes mcp test NAME`, then `hermes mcp configure NAME` to review auth/env    |
| Tools show up in CLI but not Telegram   | Gateway process has its own env — restart it after config change      | `hermes gateway restart`                                                           |
| Constant reconnects on HTTP server      | SSE timeout behind a reverse proxy                                    | Set `proxy_read_timeout 300s` in nginx/Caddy                                       |
| `sampling not permitted` in server logs | Server is requesting sampling without an approved CLI-managed setting | Review the server, then use `hermes mcp configure NAME` or unregister it           |

---

## What's Next

- [Part 18: Delegating to Coding Agents](./part18-coding-agents.md) — use Claude Code, Codex, and Gemini CLI as sub-agents invoked through Hermes (some ship MCP servers too)
- [Part 19: Security Playbook](./part19-security-playbook.md) — MCP trust model, sampling limits, and how untrusted MCPs get quarantined
- [Part 12: Web Dashboard](./part12-web-dashboard.md) — the MCP Servers panel
