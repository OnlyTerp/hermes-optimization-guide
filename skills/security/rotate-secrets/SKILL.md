---
name: rotate-secrets
description: Rotate webhook HMACs, API keys, OAuth tokens, and update gateway configs atomically
when_to_use:
  - User says "rotate secrets" or "rotate keys"
  - Scheduled monthly rotation
  - After a suspected leak or security incident
  - Pattern-matched argument like /rotate-secrets webhook_hmac_*
toolsets:
  - terminal
  - file
parameters:
  pattern:
    type: string
    description: Glob pattern for which secrets to rotate (e.g. "webhook_hmac_*", "TWILIO_*", "all")
    default: "webhook_hmac_*"
security:
  trust: trusted
  notes: |
    Touches ~/.hermes/.env. Never logs or echoes plaintext secret values;
    logs SHA-256 fingerprints only. Interactive kinds (API keys, PATs)
    require an operator in the loop — see the headless/cron note below.
model_hint: google/gemini-3.1-flash
---

# rotate-secrets — Atomic Secret Rotation

Rotate secrets in `~/.hermes/.env`, propagate the new values to every service that consumes them, and restart only the affected gateways.

## Procedure

1. **Parse the pattern.** Match against every key in `~/.hermes/.env`. Support glob syntax (`*`, `?`, `[abc]`) and the literal `all`.

2. **For each matched key:**
   a. Determine the secret kind from the key name:
      - `*_HMAC_*` or `*_WEBHOOK_SECRET` → generate `openssl rand -hex 32`
      - `*_API_KEY` → prompt the user to provide the new value (can't auto-rotate external APIs)
      - `GITHUB_*_TOKEN` → open https://github.com/settings/tokens and prompt for new PAT
      - `TWILIO_AUTH_TOKEN` → direct user to rotate in Twilio console and prompt for new value
      - Unknown pattern → prompt user for the kind

   b. Back up the current `.env` as `~/.hermes/.env.bak.YYYYMMDDHHMMSS` before any write.

   c. Update the `.env` atomically. **Don't build a `sed s///` expression from
      the key or value** — secret values routinely contain `/`, `&`, and `\`,
      which corrupt the substitution (and switching the delimiter to `|` just
      moves the problem). Use exact-match rewrite instead:
      ```bash
      tmp=$(mktemp ~/.hermes/.env.XXXXXX)
      KEY="$KEY" NEW_VALUE="$NEW_VALUE" awk -F= '
        $1 == ENVIRON["KEY"] { print ENVIRON["KEY"] "=" ENVIRON["NEW_VALUE"]; found=1; next }
        { print }
        END { if (!found) print ENVIRON["KEY"] "=" ENVIRON["NEW_VALUE"] }
      ' ~/.hermes/.env > "$tmp" && chmod 600 "$tmp" && mv "$tmp" ~/.hermes/.env
      ```
      This appends the key if it was missing, keeps `0600` perms, and never
      interprets a secret as a regex.

3. **Propagate to external services.** For HMAC / webhook secrets, update the remote side:
   - **GitHub webhooks:** use `github` MCP to `PATCH /repos/{owner}/{repo}/hooks/{hook_id}` with `config.secret`
   - **Twilio:** user-guided — we don't touch Twilio SMS webhook config automatically
   - **Slack:** user-guided — rotate signing secret in App Manifest
   - **Discord:** user-guided — rotate public key in Developer Portal
   - **Generic webhook:** ask the user where the producer-side config lives

4. **Restart only affected gateways.**
   - `TELEGRAM_BOT_TOKEN` → `hermes gateway restart telegram`
   - `DISCORD_*` → `hermes gateway restart discord`
   - Slack signing → `hermes gateway restart slack`
   - GitHub webhook secret → no restart needed (validated per-request)
   - SMS / Twilio → `hermes gateway restart twilio`

5. **Verify.** Run `hermes doctor` and fail loud if any gateway is unhealthy post-rotation. If unhealthy, restore from the `.env.bak.*` backup and report.

6. **Emit a rotation log entry.** Append to `~/.hermes/logs/rotations.log`:
   ```
   2026-04-17T14:22:00Z rotated webhook_hmac_github by=user result=ok prev_sha=abc123 new_sha=def456
   ```
   Store SHA-256 of the secret, never the plaintext.

## Security notes

- Never log the plaintext new or old value.
- Never echo a secret into the Telegram/Discord channel where the rotation was requested. Approval prompts route to the originating channel ([Part 19, Layer 2](../../../part19-security-playbook.md#layer-2-dangerous-command-approval)) — so only ever run rotations from your owner-only admin DM or the local CLI, never from a shared or public channel.
- For critical rotations (Anthropic, OpenAI, etc.), pause all gateways during rotation to prevent mid-flight requests hitting rejected keys.
- Back up `.env` before every run; retain 30 days of backups.

## Example invocation

```
/rotate-secrets webhook_hmac_*
/rotate-secrets TWILIO_AUTH_TOKEN
/rotate-secrets all                  # With interactive confirmation per key
```

## Headless / cron use

Only the HMAC/webhook kinds are fully automatic — API keys and PATs **prompt
the operator**, and a prompt in a headless cron session never gets answered:
the run stalls until `approvals.timeout` (or the session's own timeout) kills
it. So:

- Cron `/rotate-secrets webhook_hmac_*` — fine; nothing prompts.
- Cron `/rotate-secrets all` — **don't.** It will hang on the first
  interactive kind. Run `all` manually from your admin DM/CLI, monthly.
