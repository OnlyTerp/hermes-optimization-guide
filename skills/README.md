# Installable Skills

These are the skills referenced throughout the guide — each one is a drop-in `SKILL.md` you can point Hermes at.

## Install one

```bash
# Clone or update this repo
git clone https://github.com/OnlyTerp/hermes-optimization-guide ~/repos/hermes-optimization-guide

# Symlink a skill into your Hermes skills directory
ln -s ~/repos/hermes-optimization-guide/skills/security/audit-mcp ~/.hermes/skills/audit-mcp

# Reload Hermes
hermes /reload
```

## Install them all

```bash
for skill in ~/repos/hermes-optimization-guide/skills/*/*/SKILL.md; do
  name=$(basename $(dirname "$skill"))
  ln -sfn "$(dirname "$skill")" "$HOME/.hermes/skills/$name"
done
hermes /reload
```

## Catalog

| Category | Skill | What it does |
|----------|-------|--------------|
| **security** | `audit-mcp` | Audits every configured MCP server — tool filtering, credential scope, last-update — and flags stale/risky ones |
| **security** | `rotate-secrets` | Rotates webhook HMACs, API keys, and OAuth tokens; updates `.env` and restarts gateways |
| **security** | `audit-approval-bypass` | Audits every path that bypasses dangerous-command approval — approvals mode, `command_allowlist` entries, cron mode, container backends |
| **ops** | `nightly-backup` | `hermes backup`, uploads encrypted copy to configured storage, prunes old backups |
| **ops** | `weekly-dep-audit` | Uses Gemini 3.1 Pro + GitHub MCP to audit dependencies across configured repos |
| **ops** | `cost-report` | Generates a weekly LLM-cost breakdown by provider / gateway / skill, posts to your private DM |
| **ops** | `telegram-triage` | Classifies inbound Telegram DMs, autoreplies low-stakes, escalates high-stakes to you |
| **dev** | `pr-review` | Delegates a PR review to Claude Code with a scoped read-only GitHub PAT |
| **dev** | `release-notes` | Builds a human-readable release note from a range of commits or merged PRs |
| **dev** | `meeting-prep` | Pulls context for an upcoming meeting (calendar + notes + recent threads) into a briefing |
| **ops** | `daily-inbox-triage` | Morning pass across Telegram/email/Slack DMs — classifies, autoreplies, escalates |
| **ops** | `hermes-weekly` | Weekly digest of your Hermes activity (skills run, cost, errors, upcoming crons) |
| **security** | `spam-trap` | Sinks confirmed spam into a quarantine profile with no memory write / no MCP access |

13 skills total, across security / ops / dev.

## Contributing

New skills welcome. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the structure and review process.
