# Reference Architecture: Road Warrior

**Phone drives, disposable cloud boxes do the heavy lifting.** Inspired by [Part 21](../../part21-remote-sandboxes.md). You carry a tiny $5 always-on VPS; it orchestrates Modal / Daytona / Fly sandboxes that spin up on demand for real work.

## Who this is for

- Traveling developers / nomads
- People who code from their phone via Telegram
- Anyone who wants "I can fix prod from a train" energy

## Cost

- **Always-on driver box:** $5/mo (Hetzner CX22)
- **On-demand remote compute:** $0–50/mo (only pay when you're actually running things)
- **LLM:** $20–60/mo

## Architecture

```
 Phone (Telegram) ──→ Driver VPS ($5/mo, always-on)
                            │
                            │   hermes.service
                            │   remote_sandbox: modal (default)
                            │
                            ▼
                     On-demand sandbox:
                       Modal (GPU-ish)
                       Daytona (full dev env)
                       Fly Machines (persistent)
                       E2B (Python sandbox)
                       SSH (your own beast)
```

Your phone → Telegram → 5¢/mo VPS → spins up a $0.05/hr Modal sandbox → runs Claude Code, pulls the repo, does the work → syncs files back on teardown → pushes PR.

## Parts list

- **Hetzner CX22** as the driver ($5/mo)
- **Modal account** (free $30/mo credits) OR **Daytona** OR **Fly Machines** — see [Part 21](../../part21-remote-sandboxes.md)
- **Telegram bot** + your user ID
- **API keys:** Anthropic (for Claude Code inside sandbox), optional Google (for Hermes triage on the driver)

## Install

```bash
# On the driver VPS — as root
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | bash
```

Then customize:

```yaml
# /home/hermes/.hermes/config.yaml — schema verified against Part 19 (v0.18)
model: gemini-3.1-flash                     # Cheap + fast for "plan the work" phase
provider: google

providers:
  google:
    api_key: "${GOOGLE_API_KEY}"
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"         # Used by sandboxed Claude Code

# The money section — remote sandbox lanes from PR #8018 (Part 21).
# Backend credentials (MODAL_TOKEN_ID/SECRET, ssh identity) live in
# ~/.hermes/.env; pick the lane per-run with /sandbox modal | ssh.
remote_sandbox:
  default_backend: modal          # Or daytona / fly / e2b / ssh
  backends:
    modal:
      image: "python:3.12-slim"
      timeout_idle: 600           # 10m idle → auto-shutdown
    ssh:                          # your home beast, if any
      host: "beast.tailnet-xxx.ts.net"
      user: "hermes"
```

Telegram wiring goes in `~/.hermes/.env` — Hermes is default-deny (Part 19, Layer 1):

```bash
TELEGRAM_BOT_TOKEN=...              # from @BotFather
TELEGRAM_ALLOWED_USERS=123456789    # your numeric user ID
```

Install the four skills this pattern leans on into `~/.hermes/skills/`: [pr-review](../../skills/dev/pr-review/SKILL.md), [release-notes](../../skills/dev/release-notes/SKILL.md), [cost-report](../../skills/ops/cost-report/SKILL.md), and a `remote-run` trigger skill.

## The workflow

```
you: "@bot fix the null-check in auth.ts"
bot:  [spinning up modal sandbox…]
bot:  cloned acme/app, branch devin-123
bot:  claude code: analyzing…
bot:  [file diff preview, 3 lines]
      Approve? /yes /no /changes
you:  /yes
bot:  [syncing files back, running tests]
bot:  tests green. Pushed PR #342 → https://…
bot:  sandbox torn down (ran 4m 12s, $0.014)
```

## Key wins from Part 21 + PR #8018

- **Bulk tar-pipe sync** — 30s cold start beats 5 minutes of 100× `scp`
- **SIGINT-safe sync-back** — lose signal mid-run, the sandbox still flushes on teardown
- **Hash-only sync** — only changed files come back, not the whole tree
- **Local `git push`** — the driver VPS keeps your authenticated git creds; sandbox never sees them

## Skill setup

```bash
# Symlink all the guide skills
for s in /opt/hermes-optimization-guide/skills/*/*/; do
  ln -sfn "$s" "/home/hermes/.hermes/skills/$(basename $s)"
done

# Write a tiny remote-run skill (paste into ~/.hermes/skills/remote-run/SKILL.md)
# that wraps `hermes sandbox run --repo acme/app -- claude -p "$@"`
hermes /reload
```

## Safety rails

- Sandbox = **quarantine profile** (as if it were untrusted input) — Claude Code in the sandbox cannot touch the driver's MCP servers or secrets
- Driver has read-only GitHub PAT (for triage/search)
- The **write** PAT only exists inside the sandbox, short-lived, piped through stdin so it's never on disk

## Costs in the wild

Typical month for an active user:

| Line | Cost |
|---|---:|
| CX22 driver | $5 |
| Modal compute (3h/day × 30 days × $0.05/h) | $4.50 |
| Anthropic (Claude Code, routed) | $20–40 |
| Google Gemini Flash (triage) | ~$0.50 |
| **Total** | **~$30–50/mo** |

## When to graduate

- You're running 10+ sandbox hours a day → migrate to a persistent Fly Machine + scale up
- You need GPU in the sandbox → Modal A10G is ~$1.10/hr, still cheap for spot usage
- You want *multi-user* → [Small Agency](./small-agency.md)
