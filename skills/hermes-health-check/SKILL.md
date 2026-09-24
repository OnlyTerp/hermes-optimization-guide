---
name: hermes-health-check
description: Diagnose a Hermes install and report fixes.
version: 1.0.0
author: Terp AI Labs
license: MIT
metadata:
  hermes:
    tags: [hermes, diagnostics, troubleshooting, operations]
    related_skills: [hermes-cost-audit, hermes-security-review]
---

# Hermes Health Check

Run Hermes' own read-only diagnostics, then turn what they print into a short list of problems, each with the exact fix.

## When to Use

- The user says Hermes, the gateway, cron, or a platform "isn't working".
- After `hermes update`, to confirm everything came back.
- As a daily cron job on an always-on host.

## Procedure

Run every command with the terminal tool. This skill only reads. See the pitfalls before suggesting any fix that writes.

1. **Version and pending updates:**

   ```bash
   hermes --version
   hermes update --check
   ```

2. **Hermes' own diagnostics** (read-only; never add `--fix` from inside a session):

   ```bash
   hermes doctor
   hermes status
   hermes config check
   ```

3. **Gateway and cron:**

   ```bash
   hermes gateway status
   hermes cron status
   hermes cron list
   ```

   Cron fires only while a gateway runs. If `hermes cron status` warns that the gateway runs stale code, the fix is a gateway restart.

4. **Recent errors:**

   ```bash
   hermes logs errors --since 24h
   hermes logs gateway --since 24h --level WARNING
   ```

5. **Map each finding to a fix.** The most common ones:

   | Finding | Fix |
   |---|---|
   | No gateway running, so cron won't fire | `hermes gateway start`, or `hermes gateway install` if no service exists. Never add a system unit next to an existing user service: remove one first (`hermes gateway uninstall`). |
   | Both a user and a system gateway service installed | Two services fight over the same bot tokens. Keep one and uninstall the other. |
   | Gateway on stale code after an update | `hermes gateway restart` |
   | Missing or outdated options | `hermes config check`, then `hermes config migrate` |
   | "not a recognized config key" | Check the key name for a typo. v0.21.4 also prints this for some real keys (`agent.reasoning_effort`, `model_aliases.*`, `skills.creation_nudge_interval`), and for those it's harmless. |
   | A platform's bot doesn't answer | Check that platform's allowlist or run `hermes pairing list`. Discord needs the Message Content intent. |
   | "another Hermes process still holds an old copy of the session database's write-ahead log" | Stop every Hermes process, run `hermes doctor` until no holder is listed, then start one process |
   | Version older than 0.21.2 | Update. That release fixed a class of session-database corruption. |

6. **Report**: one line of overall status, then the problems ordered by severity, each with its fix command and whether the user must run it (anything that restarts or rewrites something).

## Verification

- `hermes doctor` shows no errors after the fixes are applied.
- `hermes gateway status` shows the gateway running, and `hermes cron status` shows the scheduler active.

## Pitfalls

- Never run `hermes doctor --fix`, `hermes sessions optimize`, `hermes sessions optimize-storage`, or `hermes sessions prune` from inside an agent session. This session itself holds the session database, and those commands rewrite it. Hand them to the user to run with every Hermes process stopped.
- Never delete `state.db-wal` or `state.db-shm`. They contain committed conversations.
- If this session runs through the gateway (for example in a Telegram chat), `hermes gateway restart` restarts the process answering the user. Warn them first, or let them run it.
- `hermes doctor --live` makes real network calls to tool backends. Only use it when the user asks.
