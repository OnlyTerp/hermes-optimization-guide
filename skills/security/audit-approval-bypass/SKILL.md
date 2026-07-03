---
name: audit-approval-bypass
description: Audit every path that bypasses dangerous-command approval — YOLO, approvals off, command_allowlist entries, cron approve mode, container backends
when_to_use:
  - User asks to audit approval / bypass configuration
  - Scheduled monthly security check
  - After choosing "always" on an approval prompt
security:
  trust: trusted
  notes: |
    Read-only audit of config.yaml and cron.yaml. Never modifies the
    approval posture without explicit confirmation.
model_hint: google/gemini-3.1-flash
toolsets:
  - terminal
  - file
---

# audit-approval-bypass — Verify Approval Posture

Approval bypass is how power users make trusted automation run unattended. It's also how attackers escalate if misconfigured. This skill catches drift.

Hermes' approval layer is the built-in dangerous-command detector plus the top-level `approvals:` and `command_allowlist:` blocks — there is no `security.approval.bypass_subagents` / `require_approval` regex config ([Part 19, Layer 2](../../../part19-security-playbook.md#layer-2-dangerous-command-approval)). The bypass surfaces that actually exist are the ones below.

## Procedure

1. **Load** `~/.hermes/config.yaml` and capture:
   - `approvals.mode` (`manual` / `smart` / `off`)
   - `approvals.timeout` and `approvals.cron_mode` (`deny` / `approve`)
   - The full `command_allowlist:` (every entry is a standing "always approve")
   - `terminal.backend` (container backends skip approval entirely — by design)
   - `security.redact_secrets`

2. **Flag config-level bypasses:**
   - 🔴 `approvals.mode: off` — equivalent to permanent `--yolo`.
   - 🔴 `approvals.cron_mode: approve` — headless cron jobs auto-approve dangerous commands.
   - 🟡 `approvals.mode: smart` on a deployment that reads untrusted input — the auxiliary risk-assessor is itself operating on attacker-influenced strings.
   - 🟡 Any broad `command_allowlist` entry (e.g. `recursive delete`, `shell command via -c/-lc flag`) — these approve *every* future match, including paths you didn't intend.
   - 🟡 `security.redact_secrets: false`.

3. **Check environment bypasses:**
   - `HERMES_YOLO_MODE` set in `~/.hermes/.env` or the service unit (check the systemd unit's `Environment=` lines).
   - Any wrapper script / alias invoking `hermes --yolo`.

4. **Check the container caveat:**
   - If `terminal.backend` is `docker` / `singularity` / `modal` / `daytona`, dangerous-command checks are **skipped** — the container is the boundary. Verify that's intentional: flag if `docker_mount_cwd_to_workspace: true` or a broad host mount undermines it.

5. **Cross-check cron.** For each entry in `~/.hermes/cron.yaml`, flag any task that can hit shell writes while `cron_mode: approve` is set, or that reads untrusted content (inbox sweeps, web scrapes) headlessly.

6. **Render a report:**

   ```markdown
   ## Approval Bypass Audit — 2026-06-17

   ### Config
   - ✅ approvals.mode: manual
   - ✅ approvals.cron_mode: deny
   - 🟡 command_allowlist has 2 entries — review below

   ### command_allowlist
   - 🟡 "recursive delete" — approves EVERY rm -r; added 2026-04-02
   - ✅ "shell command via -c/-lc flag" — used by nightly-backup only

   ### Environment
   - ✅ no HERMES_YOLO_MODE in .env or unit file

   ### Backend
   - 🟡 terminal.backend: docker — approval skipped by design; verify no host mounts

   ### Recommendations
   1. Remove "recursive delete" from command_allowlist (edit config.yaml or `hermes config edit`).
   2. Keep cron skills read-only so cron_mode: deny never fires.
   ```

7. **Offer to apply fixes.** Never auto-apply.

## Notes

- The hardline `UNRECOVERABLE_BLOCKLIST` (rm -rf /, fork bomb, mkfs on root, …) cannot be bypassed by any of the above — it's the floor, not the posture. Don't report it as configurable.
- If `approvals:` is missing entirely, that's fine — defaults are `manual` / `deny`. Flag only explicit weakening.
- Cross-check with the `audit-mcp` skill's output — an MCP with a broad tool surface plus `approvals.mode: off` is the worst-case combination.
