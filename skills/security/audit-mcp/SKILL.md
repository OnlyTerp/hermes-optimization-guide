---
name: audit-mcp
description: Audit every configured MCP server — tool filtering, credential scope, last-update, risk flags
when_to_use:
  - User asks to audit or review MCP configuration
  - Scheduled weekly security check
  - After installing a new MCP server
  - Before widening a server's tools.include list
toolsets:
  - terminal
  - file
security:
  trust: trusted
  notes: |
    Read-only audit. Reads config.yaml and .env key NAMES (never values),
    runs npm view / git log. Never modifies config without confirmation.
model_hint: google/gemini-3.1-flash
---

# audit-mcp — MCP Server Security Audit

Walk every server declared in `~/.hermes/config.yaml` under `mcp_servers:` and produce a structured report with risk flags.

Hermes has no per-server `trust:` levels or `allow_sampling:` knobs — the real controls are **tool filtering** (`tools.include` / `tools.exclude`), **credential scoping** (what you pass via `env:`), and **operator review before install** ([Part 19, Layer 5](../../../part19-security-playbook.md#layer-5-mcp-and-plugin-trust)). This audit checks exactly those.

## Procedure

1. **Read the config.** Load `~/.hermes/config.yaml` and extract the `mcp_servers:` block. If the block is empty or missing, report "No MCP servers configured" and exit.

2. **For each server, collect:**
   - Server name and transport (`stdio` if `command:` present, `http` if `url:` present)
   - `enabled:` flag and `timeout:`
   - `tools.include` / `tools.exclude` — present? how many tools locked in vs exposed?
   - `env:` entries — which credentials this server receives
   - Source identifier: npm package (parse from `args:`), git URL, or HTTP origin
   - Last-updated timestamp:
     - npm: `npm view <pkg> time.modified`
     - git: `git -C <path> log -1 --format=%cI`
     - http: attempt a `HEAD` and grab `Last-Modified`

3. **Risk-flag each server:**
   - 🔴 **HIGH**: server ingests untrusted content (web scraping, email parsing, public RSS — tool names matching `/scrape|fetch|email|rss|crawl/i`) AND has an empty `tools.include` (= all tools exposed) or write-capable tools included.
   - 🔴 **HIGH**: `env:` passes a broad credential (e.g. an unscoped `GITHUB_PERSONAL_ACCESS_TOKEN`) to a server that reads attacker-influenced text (the Comment-and-Control pattern).
   - 🟡 **MEDIUM**: last updated > 90 days ago.
   - 🟡 **MEDIUM**: empty `tools.include` on a server with > 10 tools exposed.
   - 🟡 **MEDIUM**: referenced `${VAR}` in `env:` is not set in `~/.hermes/.env` (check key names only — never read values).
   - 🟢 **LOW**: `enabled: true` on a server the logs show unused for 30+ days — dead attack surface.

4. **Render a table.** Columns: name, transport, enabled, tools-included / tools-exposed, credentials passed, last-update age, flags.

5. **Summarize next steps.** Group findings by flag color and recommend:
   - HIGH: "Set `tools.include:` to the specific read-only tools you audited; swap the credential for a scoped read-only one."
   - MEDIUM stale: "Run `npm update <pkg>` or rebuild the git source; verify release notes."
   - MEDIUM missing include list: "Add `tools.include:` with the specific tools you actually use."
   - For servers that ingest untrusted content: "Run under whole-process isolation, or launch the server inside a sandbox — see [Part 21](../../../part21-remote-sandboxes.md)."

6. **Offer to apply fixes.** Ask the user if they'd like to:
   - Write a suggested `tools.include:` based on `hermes logs` usage history
   - Disable (`enabled: false`) servers unused for 30+ days
   - Downscope any credential in `env:` flagged as broad

Never auto-apply without confirmation.

## Output format

Report as markdown. Paste into Telegram / Discord / dashboard as-is. Example:

```markdown
## MCP Security Audit — 2026-06-17

### 🔴 HIGH (1)
- **random-scraper** — reads untrusted content with empty tools.include (`scrape_url`, `fetch_rss`, 12 more exposed)

### 🟡 MEDIUM (2)
- **postgres** — last updated 127 days ago (package @modelcontextprotocol/server-postgres)
- **github** — empty tools.include, 34 tools exposed

### 🟢 LOW (1)
- **filesystem** — enabled but no tool calls in 30 days

### Recommendations
1. Lock `random-scraper` to `tools.include: [read_docs]` and run it inside a sandbox.
2. `npm update @modelcontextprotocol/server-postgres`.
3. Scope `github` to the 6 tools actually used in last 30d.
```

## Notes

- Runs entirely locally. No data leaves the host.
- Pair with `cron.yaml` to run weekly (see [Part 19](../../../part19-security-playbook.md#periodic-security-hygiene)) — this skill is read-only, so `approvals.cron_mode: deny` won't block it.
- Uses `terminal` to exec `npm view` / `git log`; uses `file` to read the config.
