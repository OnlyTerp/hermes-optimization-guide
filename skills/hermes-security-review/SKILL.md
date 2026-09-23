---
name: hermes-security-review
description: Review Hermes settings for security risks.
version: 1.0.0
author: Terp AI Labs
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [hermes, security, audit, hardening]
    related_skills: [hermes-health-check]
---

# Hermes Security Review

Check the settings that decide who can drive this agent, what it may run, and what it can leak. Then report risks by severity, each with a concrete fix.

## When to Use

- Before exposing Hermes on a messaging platform, to other people, or on a server.
- After adding MCP servers, plugins, or skills from outside sources.
- As a monthly cron job.

## Procedure

Run commands with the terminal tool. **Never print secret values.** Read key *names* only. Change nothing without the user's approval.

1. **Approval and safety settings:**

   ```bash
   hermes config get approvals.mode
   hermes config get approvals.cron_mode
   hermes config get approvals.unattended_mode
   hermes config get security.redact_secrets
   hermes config get security.protected_instruction_files
   hermes config get security.allow_private_urls
   hermes config get gateway.allow_all_users
   hermes config get terminal.backend
   hermes config get auth.adopt_external_logins
   ```

2. **Secrets file permissions.** Expect `600`:

   ```bash
   ENV_FILE="$(hermes config env-path)"
   stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE"
   ```

3. **Who can talk to it.** List allowlist-related key *names* in the secrets file, without values, plus pending pairings:

   ```bash
   grep -oE '^[A-Z_]*(ALLOWED_USERS|ALLOWED_CHATS|ALLOW_ALL_USERS)=' "$(hermes config env-path)"
   hermes pairing list
   hermes gateway status
   ```

   For each platform the gateway runs, confirm that an allowlist or DM pairing is in place.

4. **Supply chain:**

   ```bash
   hermes security audit      # OSV.dev scan of the venv, plugin deps, pinned MCP servers
   hermes skills audit        # re-scan hub-installed skills
   hermes plugins list --user
   hermes mcp list
   ```

5. **Rate what you found:**

   | Severity | Condition |
   |---|---|
   | Critical | `gateway.allow_all_users: true` or any `*_ALLOW_ALL_USERS=true` on a profile with terminal access. `approvals.mode: off` on a profile reachable from messaging. |
   | High | Secrets file readable by other users (not `600`). A platform running with no allowlist and no pairing. `security.redact_secrets: false`. Known vulnerabilities from `hermes security audit`. |
   | Medium | `approvals.cron_mode` or `approvals.unattended_mode` not `deny`. `security.protected_instruction_files: false`. MCP servers from unknown publishers with broad tool access and no include filter. |
   | Low | `security.allow_private_urls: true` on a machine with sensitive internal services. `auth.adopt_external_logins: true` where Codex CLI or Claude Code logins should stay separate. |

6. **Report** findings by severity with the exact fix for each: `hermes config set …`, `chmod 600 …`, an allowlist line, or `hermes pairing revoke …`. Ask which to apply.

## Verification

- After fixes, re-run steps 1–3. Critical and High findings should be gone.
- `hermes security audit` reports no known-vulnerable packages, or only ones the user accepted.

## Pitfalls

- Container terminal backends (for example Docker) skip dangerous-command approval checks by design, because the container is the boundary. That is only safe if the container really is locked down.
- Never paste the contents of `.env`, `auth.json`, or any key into the chat or a report.
- `hermes security audit` queries OSV.dev over the network. Tell the user before running it on an air-gapped host.
