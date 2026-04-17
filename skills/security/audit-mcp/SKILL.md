---
name: audit-mcp
description: Audit every configured MCP server — trust level, allowlist, last-update, risk flags
when_to_use:
  - User asks to audit or review MCP configuration
  - Scheduled weekly security check
  - After installing a new MCP server
  - Before granting `allow_sampling: true`
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
   - Declared `trust:` level (`trusted` / `community` / `untrusted`; default `community` if unset)
   - `allow_sampling:` flag (default `false`)
   - `tools_allowlist:` presence and length
   - Source identifier: npm package (parse from `args:`), git URL, or HTTP origin
   - Last-updated timestamp:
     - npm: `npm view <pkg> time.modified`
     - git: `git -C <path> log -1 --format=%cI`
     - http: attempt a `HEAD` and grab `Last-Modified`

3. **Risk-flag each server:**
   - 🔴 **HIGH**: `trust: trusted` AND reads untrusted content (web scraping, email parsing, public RSS). List any tool names matching `/scrape|fetch|email|rss|crawl/i` as evidence.
   - 🔴 **HIGH**: `allow_sampling: true` AND `trust` is not `trusted`.
   - 🟡 **MEDIUM**: last updated > 90 days ago.
   - 🟡 **MEDIUM**: no `tools_allowlist` for a server with > 10 tools exposed.
   - 🟡 **MEDIUM**: referenced `${VAR}` in `env:` is not set in `~/.hermes/.env`.
   - 🟢 **LOW**: unscoped `enabled_for`, making the server available in every profile.

4. **Render a table.** Columns: name, transport, trust, sampling, tools-allowed / tools-exposed, last-update age, flags.

5. **Summarize next steps.** Group findings by flag color and recommend:
   - HIGH: "Change `trust:` to `community` or `untrusted`, disable sampling, add tools_allowlist."
   - MEDIUM stale: "Run `npm update <pkg>` or rebuild the git source; verify release notes."
   - MEDIUM missing allowlist: "Add `tools_allowlist:` with the specific tools you actually use."

6. **Offer to apply fixes.** Ask the user if they'd like to:
   - Downgrade any `trusted` → `community`
   - Disable `allow_sampling` on flagged servers
   - Write a suggested `tools_allowlist` based on `hermes logs` usage history

Never auto-apply without confirmation.

## Output format

Report as markdown. Paste into Telegram / Discord / dashboard as-is. Example:

```markdown
## MCP Security Audit — 2026-04-17

### 🔴 HIGH (1)
- **random-scraper** — trusted + reads untrusted content (`scrape_url`, `fetch_rss`)

### 🟡 MEDIUM (2)
- **postgres** — last updated 127 days ago (package @modelcontextprotocol/server-postgres)
- **github** — no tools_allowlist, 34 tools exposed

### 🟢 LOW (1)
- **filesystem** — enabled_for empty, loads in every profile

### Recommendations
1. Change `random-scraper` to `trust: untrusted` and add tools_allowlist.
2. `npm update @modelcontextprotocol/server-postgres`.
3. Scope `github` to the 6 tools actually used in last 30d.
```

## Notes

- Runs entirely locally. No data leaves the host.
- Pair with `cron.yaml` to run weekly (see [Part 19](../../../part19-security-playbook.md#periodic-security-hygiene)).
- Uses `terminal` to exec `npm view` / `git log`; uses `file` to read the config.
