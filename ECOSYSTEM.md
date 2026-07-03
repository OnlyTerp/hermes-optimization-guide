# Hermes Ecosystem

The canonical "where do I find X for Hermes" directory. Maintained alongside the guide — if you ship something useful, open a PR to add it.

---

## MCP Servers Worth Installing

### Official / reference
- [`github/github-mcp-server`](https://github.com/github/github-mcp-server) — GitHub's official server: PRs, issues, code search, Actions (replaces the archived `@modelcontextprotocol/server-github`)
- [`@modelcontextprotocol/server-filesystem`](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) — read/write to scoped directories
- [`@modelcontextprotocol/server-postgres`](https://www.npmjs.com/package/@modelcontextprotocol/server-postgres) — read-only SQL *(archived/legacy — reference only; prefer a vendor Postgres MCP such as Supabase's)*
- [`@modelcontextprotocol/server-sqlite`](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/sqlite) — local SQLite
- [`@modelcontextprotocol/server-puppeteer`](https://www.npmjs.com/package/@modelcontextprotocol/server-puppeteer) — headless browser automation *(archived/legacy — prefer Browserbase or Playwright MCP)*
- [`@modelcontextprotocol/server-memory`](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) — lightweight KV memory
- [`@modelcontextprotocol/server-google-drive`](https://www.npmjs.com/package/@modelcontextprotocol/server-gdrive) — Drive read

### First-party vendor MCPs
- [`AWS Labs MCP servers`](https://github.com/awslabs/mcp) — AWS docs, CDK, cost, diagrams, and service-specific helpers
- [`@cloudflare/mcp-server-cloudflare`](https://github.com/cloudflare/mcp-server-cloudflare) — Workers, KV, D1, R2
- [`@supabase/mcp-server-supabase`](https://github.com/supabase-community/supabase-mcp/tree/main/packages/mcp-server-supabase) — Postgres + storage + auth
- [`@stripe/mcp-server-stripe`](https://github.com/stripe/ai/tree/main/tools/modelcontextprotocol) — payments read + restricted writes
- [`Linear remote MCP`](https://linear.app/docs/mcp) — issue tracking
- [`@notionhq/notion-mcp-server`](https://github.com/makenotion/notion-mcp-server) — page read/write
- [`@browserbase/mcp-server`](https://github.com/browserbase/mcp-server-browserbase) — managed headless browser
- [`@chromadb/mcp-server-chroma`](https://github.com/chroma-core/chroma-mcp) — vector search

### Community
- [`Mem0 remote MCP`](https://docs.mem0.ai/platform/mem0-mcp) — persistent cross-device memory
- [`arxiv-mcp-server`](https://github.com/blazickjp/arxiv-mcp-server) — arxiv search + PDF extraction
- [`mcp-server-atlassian`](https://github.com/sooperset/mcp-atlassian) — Jira + Confluence
- [`@modelcontextprotocol/server-slack`](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/slack) — message, search, profile
- [`dbt-mcp`](https://github.com/dbt-labs/dbt-mcp) — dbt Cloud
- [`e2b-dev/mcp-server`](https://github.com/e2b-dev/mcp-server) — disposable Python sandboxes
- [`mcp-obsidian`](https://github.com/MarkusPfundstein/mcp-obsidian) — your Obsidian vault

See [Part 17](./part17-mcp-servers.md) for install patterns and trust model guidance.

---

## Native Hermes plugins

- [`hermes-tweet`](https://github.com/Xquik-dev/hermes-tweet) — X/Twitter search, reads, and gated account actions for Hermes Agent through Xquik

See [Part 22](./part22-latest-power-moves.md#4-use-plugins-for-integrations-not-one-off-scripts) for plugin-first integration guidance.

---

## Coding-agent integrations

- [Claude Code](https://docs.claude.com/en/docs/claude-code) — `claude -p` + ACP; best unattended PR lane with Sonnet 5 / Opus 4.7
- [OpenAI Codex CLI](https://github.com/openai/codex) — `codex -p`; strong sandboxed bug-fix lane with GPT-5.5/Codex models
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) — `gemini -p` (free tier via OAuth); best repo-scale read/research lane
- [OpenCode](https://github.com/sst/opencode) — multi-model orchestrator; useful with Kimi K2.6 / GLM budget lanes
- [Aider](https://aider.chat) — pair-programming REPL

See [Part 18](./part18-coding-agents.md) and [Part 23](./part23-tenacity-stack.md#2-add-worker-lanes-instead-of-giant-prompt-swarms).

---

## Dashboard plugins

- `hermes-dashboard-lightrag` — graph explorer tab
- `hermes-dashboard-langfuse` — inline Langfuse traces for the current session
- `hermes-dashboard-costs` — per-provider / per-skill cost chart

(Community-maintained; see [Part 12](./part12-web-dashboard.md#dashboard-plugins-extend-the-ui).)

---

## Observability + cost

- [Langfuse](https://github.com/langfuse/langfuse) — self-hostable tracing + prompts + evals
- [Helicone](https://github.com/Helicone/helicone) — gateway-first proxy, auto caching
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) — OpenTelemetry-native, offline
- [OpenRouter](https://openrouter.ai) — provider aggregator with cost routing
- [Helicone pricing comparison](https://www.helicone.ai/llm-cost) — current retail prices
- [Artificial Analysis](https://artificialanalysis.ai) — third-party benchmarks

See [Part 20](./part20-observability.md).

---

## Security research / CVEs of note (2026)

- **Comment and Control (2026-04-15)** — cross-vendor prompt-injection via GitHub PR titles hitting Claude Code, Gemini CLI, GitHub Copilot Agent. See the defensive write-up referenced in [Part 19](./part19-security-playbook.md).
- **MCP stdio poisoning** — untrusted npm packages that proxy stdio MCP traffic. Mitigated by pinning versions + Socket.dev/Semgrep audits.
- **Webhook replay attacks** — a reminder that HMAC + TTL together, not HMAC alone, prevents replay.

See [Part 19](./part19-security-playbook.md).

---

## Templates in this repo

- [`templates/config/*`](./templates/config/) — five opinionated config baselines
- [`templates/compose/langfuse-stack.yml`](./templates/compose/langfuse-stack.yml) — Langfuse v3 self-host
- [`templates/caddy/Caddyfile`](./templates/caddy/Caddyfile) — reverse proxy + auto TLS
- [`templates/systemd/hermes.service`](./templates/systemd/hermes.service) — hardened unit file
- [`scripts/vps-bootstrap.sh`](./scripts/vps-bootstrap.sh) — fresh VPS → production in one run

---

## Elsewhere on the web

- [Hermes Agent (Nous Research)](https://github.com/NousResearch/hermes-agent) — upstream
- [Model Context Protocol](https://modelcontextprotocol.io) — spec + servers catalog
- [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)
- [Nous Research Discord](https://discord.gg/nousresearch) — community support

---

## Submit an entry

Open a PR adding to the relevant section. Requirements:
1. Link to a real, public repo
2. One-line description of what it does
3. (MCP servers) license + trust-tier recommendation

See [CONTRIBUTING.md](./CONTRIBUTING.md).
