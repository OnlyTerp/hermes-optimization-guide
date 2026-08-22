# Part 21: Remote Sandboxes & Bulk File Sync — SSH, Modal, Daytona, Vercel

*Running Hermes on a $5 VPS is great for chat. Running heavy coding work there is not. This part sets up the "phone drives, beefy remote does the work" pattern: Hermes lives on your small VPS, delegates execution to a sandbox on Docker/SSH/Modal/Daytona/Vercel Sandbox/Singularity, syncs state back on teardown, and tears the sandbox down when idle. Everything here is verified against the v0.20 docs — the backend list, the config keys, and the egress wiring are real.*

---

## The Pattern

```
Your phone (Telegram)
        │
        ▼
Hermes on $5 VPS  ─────────────►  Remote sandbox ($0 when idle)
- Memory                            - Whole workspace on the remote
- Skills                            - Coding agents (Claude/Codex/etc)
- Conversation state                - Build tools, Docker, GPU
        ▲                                │
        │                                │
        └──────── state sync on teardown ┘
```

Hermes pushes your `~/.hermes/` state (skills, credentials, cache) into the sandbox on task start, delegates the execution, then **syncs changed state back** when the sandbox tears down. The sandbox dies; Hermes keeps the state — and your $5 VPS never needed the 32 GB of RAM the sandbox ran in.

---

## The Backend Lineup (v0.20 schema)

In the current schema there is **one key** — `terminal.backend` — and seven real values:

```yaml
terminal:
  backend: local    # local | docker | ssh | modal | daytona | vercel_sandbox | singularity
```

| Backend | Where commands run | Isolation | You need |
|---------|--------------------|-----------|----------|
| **docker** | One persistent container (`docker exec`), hardened (cap-drop, no-priv) | Full (namespaces) | Docker |
| **ssh** | Remote server via SSH (ControlMaster reuse, persistent shell) | Network boundary | `TERMINAL_SSH_HOST` + `TERMINAL_SSH_USER` |
| **modal** | Modal cloud VM, snapshot/restore | Full (cloud VM) | `MODAL_TOKEN_ID`+`MODAL_TOKEN_SECRET` or `~/.modal.toml` |
| **daytona** | Daytona managed workspace, stop/resume | Full (cloud container) | `DAYTONA_API_KEY` |
| **vercel_sandbox** | Vercel Sandbox microVM, snapshot/restore | Full (cloud microVM) | `VERCEL_TOKEN` + `VERCEL_PROJECT_ID` + `VERCEL_TEAM_ID` (+ `pip install 'hermes-agent[vercel]'`) |
| **singularity** | Singularity/Apptainer container (`--containall`) | Namespaces | `apptainer`/`singularity` on PATH |

Fly Machines and E2B are **not** values of `terminal.backend` as of v0.20 — do not invent `backend: fly_machines` or `backend: e2b` keys (unrecognized values just won't work). If you want a backend outside the seven, it must come from the current docs or a plugin — check `hermes doctor` and the docs before wiring anything exotic.

> **Quick picks:** **Docker** when you want the hardened default with egress protection (below) · **SSH** for a homelab / always-on dev box · **Modal** for bursty heavy/GPU jobs on a $0-when-idle account · **Daytona** for long-lived dev workspaces · **Vercel Sandbox** for web-flavored build/deploy work · **Singularity** for HPC clusters.

One config file, one backend at a time. To *mix* backends (e.g. a local gateway + a Modal executor), run multiple Hermes **profiles**, each with its own `terminal.backend` — the phone-drives-the-VPS pattern above is exactly that: the "conductor" profile stays on `local`, an executor profile points at the sandbox.

---

## Egress first: sandboxes hold proxy tokens, not real keys (iron-proxy)

The single most important security fact in this whole part: **with the egress proxy on, a Docker sandbox never holds your real API keys.** Hermes starts a local `iron-proxy` daemon on the host, the sandbox gets an opaque **proxy token** under the normal provider env names (e.g. `OPENROUTER_API_KEY=hermes…`), and every outbound request is routed through the daemon, which swaps the token for the real credential before it goes upstream. Compromise the sandbox and the attacker walks away with tokens that only work through your proxy boundary.

```bash
hermes egress install   # pinned iron-proxy binary (SHA-256 verified)
hermes egress setup      # CA + minted proxy tokens for each provider key
hermes egress start
hermes egress status
```

- Config lives under `proxy:` in `~/.hermes/config.yaml` (`enabled`, `tunnel_port`, `extra_allowed_hosts`, `credential_source: env | bitwarden`, `enforce_on_docker`, …).
- `/egress` in chat shows the same status from any surface.
- **This is not the inbound `hermes proxy` command** (the OAuth aggregator for Codex/Cline/etc.). Different command, different direction.
- **As of v0.20 the egress swap is wired into the Docker backend only.** Modal, Daytona, SSH, and Singularity do *not* receive proxy env vars or CA mounts yet — on those backends the sandbox still gets real credentials, which is exactly why the sync rules in the next section exist.
- Uncovered auth schemes (AWS SigV4, GCP service-account OAuth) bypass the proxy — `hermes egress status` warns when their env vars are present.

The threat model is the *sandbox*: an agent running inside a Docker container that tries to `printenv | grep -i key` sees opaque tokens and an allowlist of upstream hosts. Denials are logged per-request in `~/.hermes/proxy/iron-proxy.log`; cloud-metadata IPs (`169.254.169.254`) are refused by default at the network boundary.

### What syncs where (i.e., which backends actually see your state)

| Backend | `~/.hermes/` state in sandbox | Keys in sandbox | Verdict |
|---|---|---|---|
| **docker** (+ egress) | bind-mounts / `docker_forward_env` | **proxy tokens only** | best posture — prefer this for anything untrusted |
| **ssh** | pushed for the session, **synced back** on teardown | real keys (creds included) | fine for infra *you* own |
| **modal** | pushed for the session, **synced back** | real keys | fine for throwaway work |
| **daytona** | pushed for the session, **synced back** | real keys | fine |
| **vercel_sandbox** | snapshot-backed | real keys | fine |
| **singularity** | bind-mounted overlay | real keys | fine |

So the old "never push `~/.hermes`" instinct is outdated for the *egress-protected* Docker backend (that's the point of the proxy), but it is still the right instinct for SSH/Modal/Daytona wherever the box is shared. Keep `secrets*`, `.env`, and `sessions.db`-adjacent material out of any profile that points at a shared host.

---

## SSH Backend (Homelab / Always-On Dev Box)

```bash
# real env-var config — there is no sandboxes: block anymore
export TERMINAL_SSH_HOST=dev-box.local
export TERMINAL_SSH_USER=hermes
# optional:
export TERMINAL_SSH_PORT=22
export TERMINAL_SSH_KEY=~/.ssh/hermes_ed25519
export TERMINAL_SSH_PERSISTENT=true
```

```yaml
# ~/.hermes/config.yaml
terminal:
  backend: ssh
  persistent_shell: true        # long-lived bash -l on the remote (default)
```

- Uses **ControlMaster for connection reuse** (5-minute idle keepalive) — this is what makes bulk sync cheap.
- Remotes need `python3` for `execute_code` (remote backends run scripts over a file-based RPC transport).
- Commands needing `stdin_data` or `sudo` auto-fall back to one-shot mode.

Switch back and forth with `hermes config set terminal.backend ssh` (or `docker`, `local`, …).

---

## Docker Backend (the hardened default + egress)

```yaml
terminal:
  backend: docker
  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"
  docker_mount_cwd_to_workspace: false
  docker_env:
    PYTHONUNBUFFERED: "1"
  docker_forward_env:           # host env vars forwarded into the container
    - GITHUB_TOKEN
  docker_volumes:               # host:container[:ro]
    - "/home/user/projects:/workspace/projects:ro"
  docker_extra_args:
    - "--gpus=all"              # GPU work
proxy:
  enabled: true                 # egress on -> sandbox holds proxy tokens
```

- **One persistent container** shared across sessions, `/new`, and subagent; background processes survive; `container_persistent: false` flips to per-session containers (security boundary between conversations).
- Hardened by default: `--cap-drop ALL` (only `DAC_OVERRIDE`, `CHOWN`, `FOWNER` back), `no-new-privileges`, `--pids-limit 256`, size-limited tmpfs.
- `docker_forward_env` resolves from your shell env first, then `~/.hermes/.env`; skills can declare `required_environment_variables` to merge automatically. **With egress on, provider keys are *not* forwarded — the sandbox gets proxy tokens**.
- GPU: `docker_extra_args: ["--gpus=all"]` (or use Modal for bursty GPU).

### One sandbox run, end to end

```bash
hermes config set terminal.backend docker   # point this profile at the sandbox
hermes egress status                        # confirm the proxy is listening
hermes chat -q "build the release artifacts for proj/* and verify them"
                                        # …everything in a proxy-tokened container
hermes config set terminal.backend local    # back home; container persists (or EOFs)
```

There is no `/sandbox start` slash command in current Hermes — the backend is set in config per profile, and delegation (Part 8/26) plus cron decide *when* work runs inside it. The docker container lives on between runs (label-based reuse), so a gateway profile pointing at it is effectively an always-warm sandbox.

---

## Modal Backend (Bursty / Serverless)

```bash
pip install modal
modal token new
```

```yaml
terminal:
  backend: modal
  container_cpu: 4        # CPU cores
  container_memory: 16384 # MB
  container_disk: 51200   # MB
  container_persistent: true
```

- Each command runs in a fresh Modal sandbox; `container_persistent: true` snapshots the filesystem on cleanup and restores it next session (tracked in `~/.hermes/modal_snapshots.json`) — state survives, live processes don't.
- **Billing note:** cost is per-second of runtime; spend is per-command, so don't do per-line `execute_code` churn on Modal. This is the backend for heavy builds, GPU particles, and evals.
- Credential files from `~/.hermes/` (OAuth tokens, etc.) are mounted and **synced before each command** — the sync-back rules below apply.

---

## Daytona Backend (Long-Lived Workspaces)

```yaml
terminal:
  backend: daytona
  container_cpu: 1
  container_memory: 5120
  container_persistent: true   # stop/resume instead of delete
```

- Requires `DAYTONA_API_KEY`. Sandboxes are *stopped*, not deleted, on cleanup and resumed next session; names follow `hermes-{task_id}`.
- **10 GiB disk cap** — `container_disk` above that is clamped with a warning.
- Pair with a cheap long-context model for in-sandbox research reads (see `hermes model` / Part 9).

---

## Vercel Sandbox (Web Builds / Isolated Code Execution)

```bash
pip install 'hermes-agent[vercel]'
export VERCEL_TOKEN=… VERCEL_PROJECT_ID=… VERCEL_TEAM_ID=…
```

```yaml
terminal:
  backend: vercel_sandbox
  vercel_runtime: node24   # node24 | node22 | python3.13
  cwd: /vercel/sandbox
  container_persistent: true   # snapshot/restore filesystem
```

- Not a replacement for Daytona-style long-lived dev workspaces; treat it as a clean, snapshot-backed execution target for builds/tests/short scripts.
- `terminal.vercel_runtime` defaults to `node24`; `container_disk` is **not supported** (leave unset — non-default values fail backend creation).
- One-off local dev can use short-lived OIDC tokens (`VERCEL_OIDC_TOKEN="$(vc project token)" hermes chat`), but the documented deployment path for long-running processes is access-token auth.

---

## Singularity / Apptainer (HPC, shared machines)

```yaml
terminal:
  backend: singularity
  singularity_image: "docker://nikolaik/python-nodejs:python3.11-nodejs20"
  container_persistent: true    # writable overlay persists
```

Runs with `--containall --no-home`; docker URLs auto-convert to SIF. When the job must stay on-prem but hard-isolated (air-gaps, shared HPC) — and you have `apptainer`/`singularity` on `$PATH`.

---

## Bulk Sync on Teardown (what actually happens)

For **ssh, modal, and daytona**, Hermes pushes your `~/.hermes/` state (credential files, skills, cache) into the sandbox at session start, then on teardown **syncs changed files back**:

- Files whose content hash differs from what was pushed are applied back in place; *new* remote files under a synced directory map back to the corresponding host path (e.g. a skill the agent created remotely).
- Upload-only credential files are **never overwritten** on the host.
- The sync-back retries up to 3× with backoff and refuses archives larger than 2 GiB.
- **Docker and Singularity use bind mounts** — a live host view — and don't need this.

The catch, at the docs: sync covers **Hermes state**, not arbitrary workspace files. If the agent wrote deliverables into the sandbox's cwd, have it copy them out explicitly (`scp`, `modal volume` put) before teardown:

```python
# inside the agent's execute_code, on a remote-backend profile:
terminal("rsync -av /sandbox/artifacts/ hermes@host:/data/artifacts/ ")
```

---

## Cross-Sandbox Patterns

### Pattern A: local orchestrator + remote executor (the phone-drives-VPS pattern)

Two profiles:

```yaml
# ~/.hermes/config.yaml            (gateway/profile "conductor")
terminal:
  backend: local

# ~/.hermes/profiles/runner/config.yaml
terminal:
  backend: modal                  # or ssh / daytona
```

```text
hermes -p agent chat --worktree -q "run the eval harness on /vm"
```

Your phone talks to the local gateway; heavy execution happens in the Modal/SSH host. Stateless per-run sandbox, git-backed real work.

### Pattern B: Per-project Daytona/Vercel workspaces

Because a project is a directory, let `hermes project` anchor a board — the board's project directory gives tasks a deterministic worktree + branch convention. The sandbox profile then runs *that* project.

### Pattern C: Sandboxed MCP servers — with the real knobs

The way to isolate an untrusted MCP server is still to run the server *outside the host* (on the cloud box) and point Hermes at it over HTTP — and then pin the server down with real config keys:

```yaml
# ~/.hermes/config.yaml — keys verified against the MCP reference
mcp_servers:
  random-scraper:
    url: https://<sandbox-internal>/sse   # server runs in the sandbox, not on your host
    enabled: true
    trust: untrusted                      # every write-capable tool goes through approval
    tools:
      include: [read_docs]                # expose only the tools you audited
    elicitation:
      enabled: false                      # don't let it ask your user mid-call
```

Even if the scraper is compromised, it executes on disposable infrastructure with a minimal tool surface, its write-capable calls need your approval, and egress (Docker) would cap which upstreams its tokens reach.

---

## Observability & Ops

```bash
hermes doctor                          # backend prereqs (docker/modal tokens/ssh)
hermes egress status                   # proxy up? token mappings? uncovered creds?
hermes logs gateway -f                 # worker/agent logs
hermes status
```

Per-request egress records (allowlist hit, secret swap, denial) land in `~/.hermes/proxy/iron-proxy.log` while `hermes egress status` shows the mapping count and uncovered providers. If anything is snagged, start with `hermes doctor`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "TERMINAL_SSH_HOST must be set" | Both `TERMINAL_SSH_HOST` and `TERMINAL_SSH_USER` are required for the SSH backend — set them and re-run (`hermes config set` won't do it). |
| SSH falls back to one-shot per command | `stdin_data` or `sudo` usage; also make sure key auth has no password prompts — the backend connects with `BatchMode=yes` |
| Docker: "command not found" inside container | `docker version` on the host; check the image has the tool; verify `docker_env` / `docker_forward_env`. |
| Sandbox gets HTTP 403 from the proxy | The upstream host isn't in `proxy.extra_allowed_hosts` — the 403 body names it. Add it, re-run `hermes egress setup`, `hermes egress restart`. |
| "address already in use" / proxy won't bind | `tunnel_port` (9090) collides — change `proxy.tunnel_port` or kill whoever owns it; check the tail of `iron-proxy.log`. |
| Singularity not found | `apptainer`/`singularity` not on PATH; needs the binary, not just an image name. |
| Sync-back fails on big workspaces | The remote archive cap is 2 GiB; sync is content-hash-diff, retries 3×. Copy big artifacts out with `rsync`/`modal` push/`scp` and keep the remote working tree lean. |
| `container_disk` on Vercel | Unsupported. Leave unset — non-default values fail backend creation. |
| Backend keys in `.env` not visible in sandbox | Docker: add to `docker_forward_env` (or the egress path mints proxy tokens — that's *supposed* to look different). |

---

## What's Next

- [Part 18: Coding Agents](./part18-coding-agents.md) — delegate Claude Code / Codex / Gemini CLI *into* these sandboxes
- [Part 19: Security Playbook](./part19-security-playbook.md) — egress, isolation, and the mental model
- [Part 20: Observability & Cost](./part20-observability.md) — track sandbox-hour costs alongside LLM spend
- [Part 1: Setup](./part1-setup.md) — the base VPS install these extend