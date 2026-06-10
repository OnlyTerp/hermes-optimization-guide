---
name: audit-mcp
description: Audit every CLI-managed MCP server - registration, health, source, auth exposure, and risk flags
when_to_use:
  - User asks to audit or review MCP configuration
  - Scheduled weekly security check
  - After installing a new MCP server
  - Before keeping a sampling-capable MCP server registered
toolsets:
  - terminal
  - file
---

# audit-mcp - MCP Server Security Audit

Audit the MCP servers registered through the Hermes CLI. Prefer `hermes mcp list/test/configure` over parsing `~/.hermes/config.yaml`; Hermes owns the persisted MCP registry/config shape.

## Procedure

1. **List registered servers.** Run `hermes mcp list`. If it returns no servers, report "No MCP servers configured" and exit.

2. **For each server, collect:**
   - Server name from `hermes mcp list`
   - Health and discovered tools from `hermes mcp test NAME`
   - Transport/source shown by `list` or `test` (`stdio` command/package, HTTP URL/origin, or preset)
   - Auth mode and environment keys shown by the CLI output; never print secret values
   - Any configured roots, profile scope, or tool filters visible through `hermes mcp list` / `hermes mcp test`
   - Last-updated timestamp:
     - npm: `npm view <pkg> time.modified`
     - git: `git -C <path> log -1 --format=%cI`
     - http: attempt a `HEAD` and grab `Last-Modified`
   - If non-secret details are missing from list/test output, note "unknown" and recommend `hermes mcp configure NAME` for operator review.

3. **Risk-flag each server:**
   - **HIGH**: `hermes mcp test NAME` fails for a production-registered server.
   - **HIGH**: server reads untrusted content (web scraping, email parsing, public RSS) and exposes write/send/exec/file tools. List matching tool names such as `/scrape|fetch|email|rss|crawl|send|write|exec/i` as evidence.
   - **HIGH**: sampling-capable server is registered without a reviewed CLI-managed restriction or isolation plan.
   - **MEDIUM**: last updated > 90 days ago.
   - **MEDIUM**: source package or command is not version-pinned.
   - **MEDIUM**: server exposes > 10 tools and no tool filter/scope is visible in CLI output.
   - **MEDIUM**: required env/auth key name is missing from the environment used by Hermes.
   - **LOW**: scope/profile/root details are unknown; recommend `hermes mcp configure NAME` review.

4. **Render a table.** Columns: name, transport/source, test status, tools exposed, auth/env keys present, last-update age, flags.

5. **Summarize next steps.** Group findings by flag color and recommend:
   - HIGH failing test: "Run `hermes mcp configure NAME`, fix command/url/auth/env, then rerun `hermes mcp test NAME`."
   - HIGH broad untrusted server: "Remove it from this Hermes home or restrict it with `hermes mcp configure NAME` before use."
   - MEDIUM stale: "Run `npm update <pkg>` or rebuild the git source; verify release notes."
   - MEDIUM missing filter/scope: "Use `hermes mcp configure NAME` to expose only the tools and roots you actually use."

6. **Offer to apply fixes.** Ask the user if they'd like to:
   - Run `hermes mcp configure NAME` for flagged servers
   - Remove or re-add a broken server with corrected `hermes mcp add ...` arguments
   - Write suggested CLI-managed tool filters based on Hermes usage history

Never auto-apply without confirmation.

## Output format

Report as markdown. Paste into Telegram / Discord / dashboard as-is. Example:

```markdown
## MCP Security Audit - 2026-04-17

### HIGH (1)

- **random-scraper** - untrusted-content server exposes broad tools (`scrape_url`, `fetch_rss`, `write_file`)

### MEDIUM (2)

- **postgres** - last updated 127 days ago (package @modelcontextprotocol/server-postgres)
- **github** - 34 tools exposed and no CLI-visible filter/scope

### LOW (1)

- **filesystem** - root/profile scope unknown from list/test output

### Recommendations

1. Remove `random-scraper` from this Hermes home or restrict it with `hermes mcp configure random-scraper`.
2. `npm update @modelcontextprotocol/server-postgres`, then `hermes mcp test postgres`.
3. Run `hermes mcp configure github` and expose only the tools actually used in the last 30d.
```

## Notes

- Runs entirely locally. No data leaves the host.
- Pair with `cron.yaml` to run weekly (see [Part 19](../../../part19-security-playbook.md#periodic-security-hygiene)).
- Uses `terminal` to run `hermes mcp list`, `hermes mcp test NAME`, `npm view`, `git log`, and HTTP `HEAD` checks.
