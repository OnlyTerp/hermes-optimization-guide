---
name: audit-approval-bypass
description: Audit which subagents and skills bypass approval; flag any that touch untrusted input
when_to_use:
  - User asks to audit approval / bypass configuration
  - Scheduled monthly security check
  - Before granting a new subagent bypass
toolsets:
  - terminal
  - file
---

# audit-approval-bypass — Verify Approval Posture

Approval bypass is how power users make trusted subagents run unattended. It's also how attackers escalate if misconfigured. This skill catches drift.

## Procedure

1. **Load** `~/.hermes/config.yaml` → `security.approval` block. Capture:
   - `bypass_subagents[]`
   - `auto_approve_read`
   - `require_approval[]` rules
   - `denylist[]`

2. **For each subagent in `bypass_subagents`:**
   a. Locate its skill file: `~/.hermes/skills/<name>/SKILL.md`.
   b. Parse the frontmatter `when_to_use:` and `toolsets:`.
   c. Flag if the skill reads any of:
      - Telegram / Discord / Slack message body (anything with `gateway:` trigger pattern)
      - Email inbox or any SMTP/IMAP tool
      - Webhook body (generic or GitHub PR/issue body)
      - Scraped web content (tool names matching `/scrape|fetch_url|crawl/`)
      - Voice transcription output
   d. Flag if `toolsets:` includes `terminal` or `bash` AND the skill accepts any user-supplied argument.

3. **Check the denylist:**
   - Verify every entry is still syntactically valid regex.
   - Flag if `rm -rf /` or `curl * | sh` style patterns are missing.
   - Suggest additions based on 2026 attack patterns (e.g. `cat ~/.ssh/`, `aws s3 sync`, `curl.*169.254.169.254`).

4. **Check `require_approval` layers:**
   - Confirm every production tool class is covered:
     - `github`: `[create_pr, merge_pr, delete_branch]`
     - `email`: `[send]`
     - `twilio`: `[send_sms]`
     - `terminal`: pattern-based
     - `any_mcp`: `sampling: true` present

5. **Render a report:**
   ```markdown
   ## Approval Bypass Audit — 2026-04-17
   
   ### Bypass subagents
   - ✅ nightly-backup — read-only, no untrusted input
   - ✅ build-and-test — CI-triggered, clean workspace
   - 🔴 telegram-triage — BYPASSED but reads Telegram messages (untrusted input)
   
   ### Denylist coverage
   - ✅ rm -rf patterns
   - ✅ curl | bash patterns
   - 🟡 Missing: AWS metadata IP exfil (169.254.169.254)
   - 🟡 Missing: SSH key reads (cat ~/.ssh/)
   
   ### Require-approval layers
   - ✅ github destructive actions
   - ✅ email send
   - 🔴 Missing: any_mcp with sampling:true
   
   ### Recommendations
   1. Remove telegram-triage from bypass_subagents (it reads untrusted input).
   2. Add denylist entries for 169.254 and ~/.ssh.
   3. Add require_approval for MCP sampling calls.
   ```

6. **Offer to apply fixes.** Never auto-apply.

## Notes

- If `security.approval` is missing entirely, treat that as 🔴 HIGH across the board and suggest the full config from [Part 19](../../../part19-security-playbook.md).
- Cross-check with the `audit-mcp` skill's output — an MCP flagged HIGH there often correlates with a bypass misconfig here.
