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

### Scoped Tool Exposure

Some servers are chatty — you don't want every tool they expose loaded into every conversation. The real schema knob is per-server `tools.include` / `tools.exclude` (there is no per-profile or per-channel `enabled_for:` scoping — see [Part 19, Layer 5](./part19-security-playbook.md#layer-5-mcp-and-plugin-trust)):

```yaml
# Schema verified against Part 19 (v0.18)
mcp_servers:
  postgres:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
    enabled: true
    timeout: 120
    tools:
      include: [query, describe_table]   # empty = all tools exposed
      exclude: []
```

With an empty `tools.include`, every tool the server exposes is available. If you need a server only in specific contexts, toggle it at runtime with `/mcp disable <name>` / `/mcp enable <name>` (below) rather than reaching for a config key that doesn't exist.

---

## The MCP Servers Worth Installing Today

These are the ones that pay for themselves within a day:

> **2026 reality check:** MCP is also a supply-chain boundary. Prefer official servers, pin package versions, restrict filesystem roots, and use `tools.include` to expose only the tools you audited — trust is enforced by review and isolation, not a config flag ([Part 19, Layer 5](./part19-security-playbook.md#layer-5-mcp-and-plugin-trust)).

| Server | What it adds | Why you want it |
|--------|--------------|-----------------|
| **@modelcontextprotocol/server-github** | Issues, PRs, repo search, branch diffs | Hermes becomes a code-aware teammate |
| **@modelcontextprotocol/server-filesystem** | Scoped file reads/writes/search | Safer than giving terminal access |
| **@modelcontextprotocol/server-postgres** | Read-only SQL | Answer "what's in the db?" without exposing DSN |
| **@modelcontextprotocol/server-sqlite** | Local SQLite analysis | Great for log files, analytics snapshots |
| **@modelcontextprotocol/server-puppeteer** | Browser automation | Complement to the Tool Gateway's Browser Use; sandbox it tightly |
| **@modelcontextprotocol/server-memory** | Knowledge-graph memory | Pairs with [Part 3 LightRAG](./part3-lightrag-setup.md) for redundancy |
| **mcp.mem0.ai** | Hosted long-term memory | Cross-device memory across Hermes + Claude Code |
| **Cloudflare Observability MCP** | Query your Worker logs/analytics | If you run anything on Cloudflare |
| **@supabase/mcp-server-supabase** | Supabase RPC + Postgres + storage | One config for a whole backend |
| **linear-mcp** | Linear issue CRUD | Turn Hermes into an issue assignee |
| **stripe-mcp** | Stripe reads (customers, subs) | Support triage from Telegram |
| **@notionhq/notion-mcp-server** | Notion pages + databases | Company wiki as grounded context |
| **@browserbase/mcp** | Headless browser-as-a-service | Scraping sites Firecrawl can't handle |
| **@chroma-core/chroma-mcp** | ChromaDB vectors | Works alongside LightRAG |

For the full catalog, see the [MCP Registry](https://registry.modelcontextprotocol.io/) and the `awesome-mcp-servers` list on GitHub.

---

## MCP Security: July 2026 State of Play

MCP is no longer a theoretical attack surface — the first half of 2026 produced a real CVE trail, all variations on one theme: **MCP configs and manifests are executable trust**.

| CVE | What | Lesson for Hermes users |
|-----|------|------------------------|
| CVE-2026-30623 | LiteLLM authenticated RCE via malicious MCP JSON (patched ≥ 1.83.7) | If you proxy Hermes through LiteLLM, patch it — an MCP *config* was the payload |
| CVE-2026-30615 | Windsurf: writable `mcp.json` → prompt injection → code execution | Anything that can *write* your MCP config owns your agent |
| CVE-2025-54136 | Cursor "MCPoison": approve once, config silently swapped later (fixed 1.3) | Re-approval must trigger on *change*, not just first add |
| CVE-2025-49596 | MCP Inspector RCE (browser → localhost, fixed 0.14.1) | Dev tools listening on localhost are reachable from any web page you visit |
| CVE-2026-22252 | LibreChat MCP `require()` injection via server config | Same class, different host — the pattern is universal |

The checklist that follows from it:

1. **Pin every MCP package to an exact version** — no `latest`, no floating ranges. Re-audit and re-approve when a server's version or hash changes.
2. **Treat `mcp.json` / MCP blocks in cloned repos as untrusted input.** Never launch Hermes with MCP servers from a repo you haven't reviewed — that's the MCPoison delivery vehicle.
3. **Watch for npm impersonators.** Fake `mem0-mcp-server`-style packages ship info-stealers under trusted names; install only from the vendor's documented source, and check publish dates + download counts.
4. **Never expose MCP Inspector (or any MCP dev tool) beyond localhost**, and keep it patched — browser-to-localhost is a real attack path.
5. **Separate tokens per server, minimal scopes** — an MCP server compromise should burn one narrow credential, not your account.
6. **Strip environment leakage**: pass only the env vars each stdio server needs, never your full shell environment.
7. **Add OSV/CVE monitoring** for the MCP packages you run (a weekly cron works — see the security-hygiene cron in [Part 19](./part19-security-playbook.md#periodic-security-hygiene)).

`tools.include` scoping, isolation backends, and the broader trust model live in [Part 19, Layer 5](./part19-security-playbook.md#layer-5-mcp-and-plugin-trust).

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

Hermes handles the inference request with the active provider and meters the tokens against the current session.

**Security note:** Sampling means an MCP server can burn your tokens. There is no per-server `allow_sampling:` or `sampling_model:` config knob in Hermes — sampling exposure is controlled the same way all MCP trust is: operator review before install, `tools.include` filtering, and isolation. Only run sampling-capable servers you've actually read. See [Part 19, Layer 5](./part19-security-playbook.md#layer-5-mcp-and-plugin-trust).

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
| Runaway token spend from one server | A sampling-capable server looping on `sampling/createMessage` | `/mcp disable <name>`, then review the server's code before re-enabling |

---

## What's Next

- [Part 18: Delegating to Coding Agents](./part18-coding-agents.md) — use Claude Code, Codex, and Gemini CLI as sub-agents invoked through Hermes (some ship MCP servers too)
- [Part 19: Security Playbook](./part19-security-playbook.md) — the MCP trust model and why review-before-install is the real control
- [Part 12: Web Dashboard](./part12-web-dashboard.md) — the MCP Servers panel
