---
name: audit-mcp
description: Audit every configured MCP server — transport, tool filters, sampling, last-update, risk flags
when_to_use:
  - User asks to audit or review MCP configuration
  - Scheduled weekly security check
  - After installing a new MCP server
  - Before setting `sampling.enabled: true`
toolsets:
  - terminal
  - file
---

# audit-mcp — MCP Server Security Audit

Walk every server declared in `~/.hermes/config.yaml` under `mcp_servers:` and produce a structured report with risk flags.

## Procedure

1. **Read the config.** Load `~/.hermes/config.yaml` and extract the `mcp_servers:` block. If the block is empty or missing, report "No MCP servers configured" and exit.

2. **For each server, collect:**
   - Server name and transport (`stdio` if `command:` present, `http` if `url:` present)
   - `sampling.enabled` flag; treat missing `sampling.enabled` as enabled by current MCP client defaults and recommend making intent explicit
   - `tools.include` / `tools.exclude` presence and length
   - Source identifier: npm package (parse from `args:`), git URL, or HTTP origin
   - Last-updated timestamp:
     - npm: `npm view <pkg> time.modified`
     - git: `git -C <path> log -1 --format=%cI`
     - http: attempt a `HEAD` and grab `Last-Modified`

3. **Risk-flag each server:**
   - 🔴 **HIGH**: `sampling.enabled: true` on a server that reads untrusted content (web scraping, email parsing, public RSS). List any tool names matching `/scrape|fetch|email|rss|crawl/i` as evidence.
   - 🔴 **HIGH**: stdio server from an unpinned package/source plus broad env credentials.
   - 🟡 **MEDIUM**: last updated > 90 days ago.
   - 🟡 **MEDIUM**: no `tools.include` for a server with > 10 tools exposed.
   - 🟡 **MEDIUM**: referenced `${VAR}` in `env:` is not set in `~/.hermes/.env`.
   - 🟢 **LOW**: no explicit `sampling.enabled` setting, making operator intent ambiguous.

4. **Render a table.** Columns: name, transport, sampling, tools-filter / tools-exposed, credential scope, last-update age, flags.

5. **Summarize next steps.** Group findings by flag color and recommend:
   - HIGH: "Set `sampling.enabled: false`, scope credentials, and add `tools.include`."
   - MEDIUM stale: "Run `npm update <pkg>` or rebuild the git source; verify release notes."
   - MEDIUM missing filter: "Add `tools.include:` with the specific tools you actually use."

6. **Offer to apply fixes.** Ask the user if they'd like to:
   - Set `sampling.enabled: false` on flagged servers
   - Add or narrow `tools.include`
   - Scope environment variables to only the credentials each server needs

Never auto-apply without confirmation.

## Output format

Report as markdown. Paste into Telegram / Discord / dashboard as-is. Example:

```markdown
## MCP Security Audit — 2026-04-17

### 🔴 HIGH (1)
- **random-scraper** — trusted + reads untrusted content (`scrape_url`, `fetch_rss`)

### 🟡 MEDIUM (2)
- **postgres** — last updated 127 days ago (package @modelcontextprotocol/server-postgres)
- **github** — no `tools.include`, 34 tools exposed

### 🟢 LOW (1)
- **filesystem** — enabled_for empty, loads in every profile

### Recommendations
1. Disable sampling for `random-scraper` and add `tools.include`.
2. `npm update @modelcontextprotocol/server-postgres`.
3. Scope `github` to the 6 tools actually used in last 30d.
```

## Notes

- Runs entirely locally. No data leaves the host.
- Pair with `cron.yaml` to run weekly (see [Part 19](../../../part19-security-playbook.md#periodic-security-hygiene)).
- Uses `terminal` to exec `npm view` / `git log`; uses `file` to read the config.
