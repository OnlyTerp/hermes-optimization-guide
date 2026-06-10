# Reference Architecture: Road Warrior

**Phone drives, remote execution does the heavy lifting.** Inspired by [Part 21](../../part21-remote-sandboxes.md). You carry a tiny always-on VPS for gateways, memory, approvals, and Kanban; real work runs through terminal backends, worktrees, or external integrations.

## Who this is for

- Traveling developers / nomads
- People who code from their phone via Telegram
- Anyone who wants "I can fix prod from a train" energy

## Cost

- **Always-on driver box:** about $5/mo
- **On-demand remote compute:** $0-50/mo, depending on how often workers run
- **LLM:** $20-60/mo

## Architecture

```text
Phone (Telegram) ---> Driver VPS (always on)
                         |
                         |  hermes gateway
                         |  memory, skills, MCP config
                         |  Kanban board
                         |  terminal.backend: ssh/docker/modal/daytona/local
                         |
                         v
                  Execution targets:
                    SSH dev box or home workstation
                    Docker/Singularity container
                    Modal/Daytona backend, when supported
                    External Vercel/Fly/E2B/CI integration through CLI/MCP/skills
```

Your phone talks to Hermes on the driver VPS. Hermes creates a worktree or Kanban task, sends shell/file work to the configured terminal backend, runs the coding agent or skill, then reports the diff, test result, PR link, or external artifact back to chat.

## Parts list

- **Driver VPS** such as Hetzner CX22, Fly machine, Render, Railway, or a tiny homelab box
- **Execution target:** SSH dev box, Docker/Singularity, or Modal/Daytona if supported by your Hermes build
- **External integrations:** Vercel, Fly Machines, E2B, and CI through vendor CLIs, MCP servers, or custom skills
- **Telegram bot** + your user ID
- **API keys:** model providers for Hermes and any coding agents you choose to run

## Install

```bash
# On the driver VPS - as root
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | bash
```

Then customize:

```yaml
# /home/hermes/.hermes/config.yaml
version: 1

models:
  default: google/gemini-3.1-flash # Cheap + fast for triage
  providers:
    google:
      api_key: "${GOOGLE_API_KEY}"
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}" # Optional: used by Claude Code or routed model calls

gateways:
  cli: { enabled: true }
  telegram:
    enabled: true
    bots:
      admin:
        token: "${TELEGRAM_ADMIN_BOT_TOKEN}"
        allowed_user_ids:
          - ${TELEGRAM_OWNER_ID}

# The execution section. Use one backend at a time.
terminal:
  backend: ssh # local | docker | singularity | modal | daytona | ssh
  ssh_host: "beast.tailnet-xxx.ts.net"
  ssh_user: "hermes"
  ssh_port: 22
  ssh_key: "~/.ssh/id_ed25519"

# Hermes loads skills from here; use them to create Kanban cards or call vendor CLIs/MCP tools.
skills:
  allowlist:
    - pr-review
    - release-notes
    - cost-report
    - remote-run
```

For a fully local-but-contained driver, switch the terminal block to Docker:

```yaml
terminal:
  backend: docker
  docker_image: nikolaik/python-nodejs:python3.11-nodejs20
  cwd: /workspace
  docker_mount_cwd_to_workspace: false
```

For Modal or Daytona, use only the backend keys your installed Hermes build exposes. Verify after config edits:

```bash
hermes config check
hermes doctor
```

## The workflow

```text
you: "@bot fix the null-check in auth.ts"
bot:  created Kanban task #342 on branch wt/auth-null-check
bot:  worker claimed an isolated worktree
bot:  terminal backend: ssh -> beast.tailnet-xxx.ts.net
bot:  codex-worker: running tests...
bot:  diff preview: 3 lines changed
      Approve? /yes /no /changes
you:  /yes
bot:  tests green. Pushed PR #342 -> https://...
```

The important bit: the source of truth is git. Hermes is not starting a native sandbox and syncing files back on teardown; it is coordinating worktrees, terminal execution, worker logs, tests, and PRs.

## Kanban setup

Create durable work from chat, CLI, or the dashboard:

```bash
hermes kanban create "Fix the null-check in auth.ts and open a PR" \
  --assignee codex-worker \
  --workspace worktree \
  --branch wt/auth-null-check

hermes kanban dispatch --max 1
```

A `remote-run` skill should wrap one of these real surfaces:

- create a Kanban card with `--workspace worktree`;
- run a coding agent through a configured terminal backend;
- call a vendor CLI/API such as `vercel`, `flyctl`, or an E2B MCP server;
- return logs, artifact URLs, test status, and PR links.

It should not wrap a sandbox CLI subcommand; that interface is not part of the current CLI.

## Safety rails

- Terminal backend isolation confines shell/file-tool activity, not every in-process Hermes component. Use [Part 19](../../part19-security-playbook.md) for whole-process containment guidance.
- Keep the driver VPS as the owner of gateways, approvals, memory, and durable Kanban state.
- Pass only the minimum credentials to the remote execution target. Prefer vendor secret stores, short-lived tokens, and PR-based review.
- Use `hermes --worktree` or Kanban `--workspace worktree` for parallel coding work so agents do not collide in one checkout.
- Treat "worker ran" as evidence, not completion. Require tests, review, and a clean branch before calling work done.

## Costs in the wild

Typical month for an active solo user:

| Line                             |              Cost |
| -------------------------------- | ----------------: |
| Driver VPS                       |                $5 |
| SSH home box                     | existing hardware |
| Modal/Daytona/Fly/E2B usage      |             $0-50 |
| Premium coding-agent model calls |            $20-60 |
| Cheap triage model calls         |               <$5 |
| **Total**                        |   **~$30-120/mo** |

## When to graduate

- You run remote jobs all day -> move the execution target to a persistent dev box or a larger VPS.
- You need GPU bursts -> use Modal, a GPU SSH host, or a CI/vendor runner skill.
- You need vendor-native previews -> call Vercel/Fly/E2B through skills, MCP, or CI instead of pretending they are Hermes-native backends.
- You want multi-user operations -> [Small Agency](./small-agency.md).
