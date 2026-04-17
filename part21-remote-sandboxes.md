# Part 21: Remote Sandboxes & Bulk File Sync — SSH, Modal, Daytona

*Running Hermes on a $5 VPS is great for chat. Running heavy coding work there is not. This part sets up the "phone drives, beefy remote does the work" pattern: Hermes lives on your small VPS, delegates execution to a disposable sandbox on SSH/Modal/Daytona, syncs files both ways, and tears it down when idle. Ships in v0.9+ with the [bulk file sync](https://github.com/NousResearch/hermes-agent/pull/8018) hardening that landed April 17, 2026.*

---

## The Pattern

```
Your phone (Telegram)
        │
        ▼
Hermes on $5 VPS  ─────────────►  Remote sandbox ($0 when idle)
- Memory                            - Whole workspace in /home/runner/
- Skills                            - Coding agents (Claude/Codex/etc)
- Conversation state                - Build tools, Docker, GPU
        ▲                                │
        │                                │
        └─── bulk file sync on teardown ─┘
```

Hermes uploads your workspace on task start, delegates work, then downloads only the diff back on teardown. The sandbox dies, Hermes keeps the state — and your $5 VPS never needed the 32GB of RAM the sandbox ran in.

---

## Pick Your Backend

| Backend | Billing | Idle cost | Best for |
|---------|---------|-----------|----------|
| **SSH** | Your infra | Whatever your host costs | Homelab / always-on dev box |
| **Modal** | Per-second compute | $0 (hibernate) | Bursty coding tasks, GPU work |
| **Daytona** | Per-second workspace | $0 (hibernate) | Long-lived dev workspaces |
| **Fly Machines** | Per-second | $0 (stop) | Regional sandboxes near your users |
| **E2B** | Per-second | $0 | Quick throwaway Python sandboxes |
| **Local Docker** | Your hardware | N/A | Testing / development |

Hermes ships native support for SSH, Modal, and Daytona as of v0.9+. Fly Machines and E2B work via a thin `remote_exec` plugin.

---

## SSH Backend (Homelab / Always-On Dev Box)

### Prereqs

- SSH access to the remote host with key auth (no password prompts)
- Remote has `python3`, `rsync`, `tar`, `git`
- Your SSH config uses `ControlMaster` + `ControlPath` for connection reuse (shown below)

### Config

```yaml
# ~/.hermes/config.yaml
sandboxes:
  dev-box:
    backend: ssh
    host: dev.local
    user: hermes
    identity_file: ~/.ssh/hermes_ed25519
    workdir: /home/hermes/sandboxes
    control_master: auto              # Reuses connection for bulk sync
    control_persist: 600
    sync:
      push: ~/.hermes                 # Uploaded at sandbox create
      pull_on_teardown: true
      pull_paths:
        - .hermes
        - projects                    # Grabs any code changes made in-sandbox
      ignore:
        - .git
        - node_modules
        - __pycache__
        - "*.log"
```

### Use It

```
/sandbox start dev-box
/claude-code refactor src/auth/ to use JWT rotation
/sandbox stop dev-box                # Syncs changes back, then stops
```

Under the hood on teardown:

1. Hermes runs `tar cf - -C ~/.hermes .` on the remote
2. Pipes it over the SSH ControlMaster to the local box
3. Unpacks into a staging dir
4. Diffs against SHA-256 hashes of what was originally pushed
5. Applies only changed files back to `~/.hermes`, with `fcntl.flock` serialization if another sandbox runs concurrently
6. SIGINT-safe — pressing Ctrl-C during sync rolls back cleanly

This is what PR [#8018](https://github.com/NousResearch/hermes-agent/pull/8018) (merged April 17) formalized. Before it, you either rsynced everything every time (slow) or lost remote-made edits on teardown.

---

## Modal Backend (Bursty / Serverless)

Modal hibernates sandboxes to zero between runs and spins up in ~2 seconds. Ideal for bursty coding-agent use.

```bash
pip install modal
modal token new
```

```yaml
sandboxes:
  modal-big:
    backend: modal
    image:
      from: python:3.12
      apt_install: [git, ripgrep, build-essential]
      pip_install: [claude-code-cli, aider-chat]
    cpu: 4
    memory: 16384
    gpu: null                        # Set to "T4" / "A10G" / "H100" if you need one
    timeout: 3600
    sync:
      push: ~/.hermes
      pull_on_teardown: true
      pull_paths: [.hermes, projects]
```

Sync uses Modal's `exec tar cf -` → `proc.stdout.read()` → local file pattern — same diff/apply logic as SSH.

Cost tip: set `timeout: 300` and a short `idle_shutdown:` for chat-driven sandboxes; Modal bills per second of actual runtime.

### GPU Sandboxes for Voice / Image Tasks

If you've disabled the [Tool Gateway](./part13-tool-gateway.md) and run your own image-gen or voice pipeline, a GPU sandbox is cheaper than keeping a GPU VPS live:

```yaml
sandboxes:
  gpu-a10g:
    backend: modal
    image:
      from: nvcr.io/nvidia/pytorch:24.10-py3
      pip_install: [diffusers, transformers]
    gpu: "A10G"
    timeout: 600
    commands:
      - /generate_image    # Route image gen to this sandbox
      - /speech_synth
```

Hermes routes the tool calls transparently — the user has no idea the sandbox span is happening.

---

## Daytona Backend (Long-Lived Workspaces)

Daytona is the "it's like GitHub Codespaces for your own code" option. Pair with Hermes when you want the workspace to persist across sessions:

```yaml
sandboxes:
  workspace:
    backend: daytona
    workspace_id: hermes-dev
    auto_create: true                # Create if it doesn't exist
    image: daytonaio/workspace-project:latest
    hibernate_after: 900
    sync:
      push: ~/.hermes
      pull_on_teardown: false        # Work persists, no need to sync every time
      pull_on_command: "/sync-home"  # Manual sync when you want it
```

Pair with the [Gemini CLI OAuth provider](./part9-custom-models.md) (merged PR [#11270](https://github.com/NousResearch/hermes-agent/pull/11270), April 16) for free-tier Gemini use inside the sandbox — the 1500 req/day free tier covers most exploratory work.

---

## Fly Machines (Regional / Low-Latency)

For users in specific regions, Fly Machines deliver sub-100ms latency from a nearby PoP:

```yaml
sandboxes:
  fly-sin:
    backend: fly_machines             # Plugin, not core
    app: hermes-sandbox
    region: sin                       # Singapore
    size: performance-2x
    auto_stop: true
    stopped_shutdown_at: 120
```

Useful when you want the sandbox physically near your iOS / Telegram users for lower round-trip.

---

## E2B (Disposable Python Sandboxes)

E2B gives you a clean Linux sandbox in ~500ms. Best for data analysis / running unknown code:

```yaml
sandboxes:
  e2b-scratch:
    backend: e2b
    template: python                  # E2B template
    metadata:
      purpose: data-analysis
    timeout: 300
```

Hermes routes any tool call marked `/sandbox e2b` into this template. Teardown is automatic.

---

## Cross-Sandbox Patterns

### Pattern A: Primary-Replica Dev Box + Ephemeral Sandboxes

- **Primary:** SSH dev box with your long-lived workspace
- **Replica:** Modal sandbox spun up per delegation

```
/sandbox start dev-box
/delegate (runs in modal-big, reads from dev-box via git)
/sandbox stop dev-box
```

Works great when each coding-agent delegation runs a git-backed feature branch. Sandboxes are stateless; dev-box is the source of truth.

### Pattern B: Per-Project Daytona Workspaces

```
/project open myapp       → daytona workspace "myapp"
/project open sideproject → daytona workspace "sideproject"
```

Each project has its own workspace with its own deps, env, and git state. Hermes remembers which is active per Telegram topic.

### Pattern C: Sandboxed MCP Servers

Route untrusted MCP servers (see [Part 19](./part19-security-playbook.md#mcp-server-trust-model)) into a sandbox:

```yaml
mcp_servers:
  random-scraper:
    trust: untrusted
    run_in_sandbox: e2b-scratch       # Isolate execution
```

Sandbox catches any malicious behavior — even if the scraper is compromised, it can't touch your host.

---

## Observability: `hermes sandbox status`

```
$ hermes sandbox status
NAME         BACKEND   STATE      AGE      CPU   MEM      COST
dev-box      ssh       connected  3h 12m   0.4   2.1 GB   $0 (your infra)
modal-big    modal     running    0m 42s   3.8   14.2 GB  $0.09
workspace    daytona   hibernated 0m 0s    -     -        $0
```

The [Web Dashboard](./part12-web-dashboard.md) has a Sandboxes panel with the same info plus: streaming logs, per-sandbox cost totals for the month, sync history, and a one-click "sync back and stop" button.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "sandbox teardown timed out during sync" | Increase `sync.timeout: 600` — big workspaces over slow SSH |
| "sync conflict: host file also changed" | Last-write-wins by default; set `sync.conflict: prompt` to interactively resolve |
| "SSH ControlMaster socket in use" | Another Hermes process on the box is running; `hermes sandbox ps` to find it |
| "Modal sandbox cold-start keeps timing out" | Pre-warm with `hermes sandbox warm modal-big` before interactive work |
| "Daytona hibernate → resume corrupts git state" | Put `.git` in `pull_paths` so Hermes holds the canonical copy |
| "File-sync uploads .venv every time" | Add it to `ignore:` — missed by default in some templates |

Enable `HERMES_SANDBOX_LOG=debug` to get full tar/ssh command traces.

---

## What's Next

- [Part 18: Coding Agents](./part18-coding-agents.md) — delegate Claude Code / Codex / Gemini CLI *into* these sandboxes
- [Part 19: Security Playbook](./part19-security-playbook.md) — isolate untrusted MCPs in sandboxes
- [Part 20: Observability & Cost](./part20-observability.md) — track sandbox-hour costs alongside LLM spend
- [Part 1: Setup](./README.md#part-1-setup-stop-fumbling-with-installation) — the base VPS install these extend
