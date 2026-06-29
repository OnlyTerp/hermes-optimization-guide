# Part 19: Security Playbook — Locking Down an Agent That Reads Untrusted Text

_April 15, 2026 published [Comment and Control](https://oddguan.com/blog/comment-and-control-prompt-injection-credential-theft-claude-code-gemini-cli-github-copilot/) — cross-vendor prompt injection that steals GitHub Actions secrets from Claude Code, Gemini CLI, and Copilot Agent via PR titles. Your Hermes bot reads messages from Telegram, Discord, email, webhooks, and SMS — every one of them an injection vector. This part is the defensive posture that stops your agent from becoming someone else's command-and-control channel._

> **Schema note (updated 2026-06-29):** Earlier revisions of this part documented a `security:` config block with `provenance`, `approval.require_approval` regex, `secrets.scope`, and `network.egress_allowlist` keys. **None of those exist in Hermes Agent.** This rev tracks the real schema: top-level [`approvals:`](https://hermes-agent.nousresearch.com/docs/user-guide/security), native dangerous-command detection, `command_allowlist:`, `.env` user allowlists and DM pairing, `security.redact_secrets`, `security.tirith_*`, `security.website_blocklist`, `security.allow_private_urls`, supply-chain advisory acks, lazy-install controls, env/credential passthrough, and OS-level isolation. See the [official Security guide](https://hermes-agent.nousresearch.com/docs/user-guide/security) and [SECURITY.md trust model](https://github.com/NousResearch/hermes-agent/blob/main/SECURITY.md).

---

## Threat Model

Hermes is uniquely exposed because it takes input from **many** surfaces and has **many** capabilities:

| Surface             | Attacker controls                       | Risk                                       |
| ------------------- | --------------------------------------- | ------------------------------------------ |
| Telegram DM         | Message body, filename, image caption   | Injection → tool calls                     |
| Discord channel     | Embed text, webhook payloads, usernames | Injection → tool calls                     |
| Email inbox         | Headers, body, attachment filenames     | Multi-stage (HTML + links)                 |
| SMS / Twilio        | Message body + webhook payloads         | Injection → tool calls                     |
| GitHub MCP          | PR titles, issue bodies, comments       | Comment-and-Control pattern                |
| Web-scraped content | Page HTML the agent reads               | "Read then act" injections                 |
| Voice transcript    | STT transcription                       | "Say the magic phrase" attacks             |
| MCP/plugin package  | Tool schema, stdout, hook behavior      | Supply-chain prompt injection / token burn |
| Dashboard plugin    | Browser UI + backend endpoints          | Local secret/config exposure               |

The goal isn't to eliminate these channels — Hermes is _for_ reading them. The goal is to make sure untrusted text can't cross a trust boundary into secrets, writes, or shell.

---

## The Only Real Boundary: OS-Level Isolation

Before the config knobs, internalize the single most important sentence in Hermes' [security policy](https://github.com/NousResearch/hermes-agent/blob/main/SECURITY.md):

> **The only security boundary against an adversarial LLM is the operating system.** Nothing inside the agent process constitutes containment — not the approval gate, not output redaction, not any pattern scanner, not any tool allowlist.

Every in-process control below (approval prompts, secret redaction, skill scanning) is a **heuristic operating on an attacker-influenced string**. They catch cooperative-mode mistakes and casual exfiltration. They do **not** contain a model that has been successfully turned hostile by an injection.

Hermes supports two OS-level isolation postures — choose deliberately:

- **Terminal-backend isolation.** A non-default `terminal.backend` (Docker, Singularity, Modal, Daytona, SSH) runs LLM-emitted shell _and_ file-tool operations inside a container/remote host. Confines anything the agent does _through the shell_. Does **not** confine the agent's own Python process (code-execution tool, MCP subprocesses, plugins, hooks, skills).
- **Whole-process wrapping.** Runs the entire agent process tree in a sandbox so _every_ path — shell, code-exec, MCP, file tools, plugins, hooks — is subject to one filesystem/network/process policy. Hermes supports this via its own Docker/Compose setup, or via [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell) for declarative filesystem + **L7 network egress** + syscall + inference-routing policy.

If your agent ingests content from surfaces you don't control (the open web, inbound email, multi-user channels, untrusted MCP servers), **whole-process wrapping is the supported posture.** Running the default local backend against untrusted input is operating outside Hermes' supported security model. The layers below harden a real deployment; they are not a substitute for the boundary.

---

## Layer 1: User Authorization — Who Can Talk to the Agent

The first gate is _who is even allowed to reach the agent_. On every messaging gateway, Hermes is **default-deny**: if no allowlist is configured and `GATEWAY_ALLOW_ALL_USERS` is unset, all users are rejected.

Set per-platform allowlists in `~/.hermes/.env` (comma-separated IDs):

```bash
# ~/.hermes/.env
TELEGRAM_ALLOWED_USERS=123456789,987654321
DISCORD_ALLOWED_USERS=111222333444555666
WHATSAPP_ALLOWED_USERS=15551234567
SLACK_ALLOWED_USERS=U01ABC123
EMAIL_ALLOWED_USERS=you@example.com

# Cross-platform allowlist (checked for every platform)
GATEWAY_ALLOWED_USERS=123456789
```

Authorization is checked in order: per-platform allow-all flag → DM-pairing approved list → platform allowlist → global allowlist → global allow-all → **default deny**. Avoid `GATEWAY_ALLOW_ALL_USERS=true` on anything public — it exposes the agent (and every tool it has) to anyone who finds the bot.

For people whose platform IDs you don't know in advance, use **DM pairing**: users send a one-time code generated out-of-band before they can interact. Pairing state persists across gateway restarts.

Per-platform hardening worth setting:

```yaml
# ~/.hermes/config.yaml
discord:
  require_mention: true # Bot only responds when @mentioned in channels (default)
  free_response_channels: "" # Channel IDs exempt from the mention requirement
group_sessions_per_user: true # Each group participant gets an isolated session
```

---

## Layer 2: Dangerous-Command Approval

Before executing any shell command, Hermes checks it against a **curated, built-in list of dangerous patterns** (`tools/approval.py`). On a match, execution pauses for human approval. The patterns are part of the source — you do **not** define approval regex in your config.

Configure the policy with the top-level `approvals:` block:

```yaml
# ~/.hermes/config.yaml
approvals:
  mode: manual # manual | smart | off
  timeout: 60 # seconds to wait before fail-closed deny
  cron_mode: deny # deny | approve — behavior when a cron job hits a dangerous command
  mcp_reload_confirm: true # /reload-mcp confirms before invalidating the MCP tool cache
  destructive_slash_confirm: true # /clear, /new, /reset, /undo confirm before discarding state
```

| Mode                 | Behavior                                                                                                                                                             |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **manual** (default) | Always prompt on a dangerous command                                                                                                                                 |
| **smart**            | An auxiliary LLM assesses risk first — auto-approves clearly low-risk matches, auto-denies clearly dangerous ones, escalates the uncertain middle to a manual prompt |
| **off**              | Skip all approval prompts (equivalent to `--yolo`)                                                                                                                   |

When a prompt fires in the CLI you get four choices — **once / session / always / deny** (deny is the default if you time out). On messaging platforms the prompt is delivered as a message (inline buttons on Telegram/Discord/Slack); reply _yes/approve_ or _no/deny_.

### `command_allowlist` — the "always approve" list

Choosing **always** writes the detector pattern that fired to the top-level `command_allowlist:`:

```yaml
# Permanently allowed dangerous command patterns
command_allowlist:
  - rm
  - systemctl
```

These entries are pattern strings consumed by the built-in detector — not your own regex language, and not a path-scoped policy. Be conservative: allowing a broad pattern can silently approve future commands you did not intend. Periodically run `hermes config edit` and remove stale allowlist entries.

### YOLO mode — what it does and doesn't bypass

`hermes --yolo`, the `/yolo` toggle, or `HERMES_YOLO_MODE=1` bypass **all** approval prompts for the session. Use only for vetted automation in disposable environments.

### The hardline blocklist (always-on floor)

A small set of catastrophic, irreversible commands is refused **regardless** of `--yolo`, `approvals.mode: off`, cron `approve` mode, or "always" — there is no override flag (`tools/approval.py::UNRECOVERABLE_BLOCKLIST`):

- `rm -rf /` and obvious variants (incl. `--no-preserve-root /`)
- The bash fork bomb `:(){ :|:& };:`
- `mkfs.*` on a mounted root device
- `dd if=/dev/zero of=/dev/sd*`
- Piping untrusted URLs to `sh` at the rootfs top level

The blocklist trips _before_ the approval layer sees the command. It's the seatbelt, not the whole car.

### Two caveats that matter

- **Container backends skip approval entirely.** When `terminal.backend` is `docker`, `singularity`, `modal`, or `daytona`, dangerous-command checks are bypassed because the container _is_ the boundary (Layer "OS isolation" above). That's the intended trade — unrestricted execution inside a disposable box.
- **Approvals route to the channel the message came from.** There is no separate "approval channel" config. The defense against "trick the bot into approving itself" is your **allowlist** (Layer 1): keep the public-facing bot's allowlist tight, and drive privileged actions from a separate, owner-only bot or DM that untrusted users can't reach.

### Tirith pre-exec scanning

Hermes layers [tirith](https://github.com/sheeki03/tirith) on top of the native detector to catch homograph URLs, pipe-to-interpreter patterns (`curl | bash`, `wget | sh`), and terminal-injection tricks. It is enabled by default and auto-installs a prebuilt binary on first use with SHA-256 checksum verification (plus cosign provenance verification when `cosign` is available):

```yaml
security:
  tirith_enabled: true # default: true
  tirith_path: "tirith" # PATH lookup by default
  tirith_timeout: 5
  tirith_fail_open: true # default: allow execution if tirith is unavailable
```

Set `tirith_fail_open: false` in high-security environments. Tirith's verdict joins the same approval flow: safe commands pass; suspicious or blocked commands prompt with findings, safer alternatives, and a default-deny choice. On platforms without a prebuilt tirith binary, use WSL/Linux or rely on the built-in pattern detector.

---

## Layer 3: Secrets, Credential Scoping, and Explicit Passthrough

The Comment-and-Control attack class succeeds by exfiltrating credentials. Hermes' defenses here reduce _casual_ leakage — pair them with isolation for real containment.

**On-disk hygiene:**

- API keys belong in `~/.hermes/.env`, not `config.yaml` or the repo. Keep the file `0600` and the profile directory private.
- Redaction is pattern-based, not magic. Never assume every credential-like value is scrubbed; review logs and bundles before sharing.

**Output / log redaction:**

```yaml
# ~/.hermes/config.yaml
security:
  redact_secrets: true # default on — redacts secret-like patterns from tool output, logs, and chat responses
```

Leave it on. The toggle is bridged into `HERMES_REDACT_SECRETS` at startup, so changing it mid-session does not necessarily affect already-imported code. If you disable it to debug auth, restart afterward and treat the resulting logs as secret-bearing.

**Default child-process filtering:** Hermes filters the environment it hands to lower-trust children.

| Child surface         | Default behavior                                                                                                          | How to pass a needed credential                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `execute_code`        | Blocks env vars whose names look secret-bearing (`KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `AUTH`, etc.) except safe prefixes | Load a skill whose frontmatter declares `required_environment_variables`, or add `terminal.env_passthrough` |
| Local `terminal`      | Blocks explicit Hermes infrastructure/provider/gateway/tool secrets                                                       | `terminal.env_passthrough` or skill-declared required env vars                                              |
| Docker/Modal terminal | No host env by default                                                                                                    | Skill-declared passthrough, `terminal.env_passthrough`, or `terminal.docker_forward_env` for Docker         |
| Credential files      | Not mounted by default                                                                                                    | Skill `required_credential_files` or `terminal.credential_files`; Docker mounts read-only                   |
| MCP stdio             | Only safe system vars (`PATH`, `HOME`, `USER`, locale/shell/tmp, `XDG_*`) plus the server's own `env:`                    | Put exactly what the server needs in `mcp_servers.<name>.env`                                               |

Example:

```yaml
terminal:
  env_passthrough:
    - TENOR_API_KEY # task-specific key, not Hermes provider keys
  credential_files:
    - google_token.json # relative to ~/.hermes/; mounted read-only in Docker
```

> **The honest caveat (from SECURITY.md §2.3):** filtering reduces accidental exfiltration; it is _not_ containment. Anything running _inside_ the agent process — skills, plugins, hook handlers — can read what the agent can. The mitigation for a hostile in-process component is operator review before install (Layer 5) and whole-process isolation, not env scrubbing.

---

## Layer 4: Isolation Backends — Where Egress Control Actually Lives

There is no `security.network.egress_allowlist` in Hermes. Filesystem confinement and broad network control come from the **terminal backend** or a **whole-process sandbox** — not a single config key in a `security:` block. Hermes does, however, now ship URL-fetching guardrails (website blocklist + SSRF protection), covered below.

Pick a non-default terminal backend so LLM-emitted shell and file-tool operations run off your host:

```yaml
# ~/.hermes/config.yaml
terminal:
  backend: docker
  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"
  cwd: /workspace
  docker_forward_env: [] # explicit env allowlist only; empty keeps host secrets out
  container_cpu: 1
  container_memory: 5120 # MB
  container_disk: 51200 # MB
  container_persistent: true # persist /workspace and /root under ~/.hermes/sandboxes/docker/<task_id>/
```

What a container backend buys you:

- The agent's terminal/file operations cannot read the host `~/.hermes/.env` unless you explicitly forward env or mount credential files.
- Destructive commands are contained to the container/sandbox filesystem.
- Docker containers run with hardened defaults: Linux capabilities dropped except the minimum needed for package/user setup, `no-new-privileges`, PID limits, and size-limited tmpfs mounts.

SSH and serverless (Modal/Daytona) backends give the same shape — agent code and keys stay local/host-side, only commands are forwarded. Current docs put SSH connection details in `.env` rather than `config.yaml` so they do not travel with profile exports:

```yaml
# ~/.hermes/config.yaml
terminal:
  backend: ssh
```

```bash
# ~/.hermes/.env
TERMINAL_SSH_HOST=agent-worker.local
TERMINAL_SSH_USER=hermes
TERMINAL_SSH_KEY=~/.ssh/hermes_agent_key
```

For **true egress allowlisting** (block private ranges, block the metadata IP `169.254.169.254`, restrict outbound domains across every code path), wrap the _whole process_ with a VM/container policy or [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell). Terminal-only backends do not confine in-process plugins, skills, MCP management code, or gateway/media fetches. For a home-lab / [Home Assistant](./part15-new-platforms.md#home-assistant) setup, an explicit outer egress policy beats hoping a nonexistent Hermes config key blocks every SSRF path.

### URL-fetching guardrails: website blocklist and SSRF protection

Hermes now has built-in URL policy for web/browser/vision/media fetches:

```yaml
security:
  website_blocklist:
    enabled: true
    domains:
      - "*.internal.company.com"
      - "admin.example.com"
    shared_files:
      - "/etc/hermes/blocked-sites.txt"

  allow_private_urls: false # default; leave false for public-facing gateways
```

With the default `allow_private_urls: false`, URL-capable tools reject private, loopback, link-local, CGNAT/Tailscale, reserved/multicast, and cloud-metadata targets; redirects are revalidated. Set it to `true` only for trusted local-network workflows where prompt-injected URLs probing your LAN are an acceptable risk. These URL guards are valuable, but they are not a replacement for OS/network isolation because they only cover Hermes URL-fetching paths, not arbitrary code running in a shell/container/plugin.

---

## Layer 5: MCP and Plugin Trust

MCP servers and plugins are third-party code you give tool access to. Hermes does **not** have per-server `trust:` levels, `allow_sampling`, or `max_concurrent_calls` config knobs. The real controls are credential filtering, tool filtering, TLS/header configuration for HTTP servers, and **operator review before install**.

Configure servers with the documented [MCP schema](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference) and use `tools.include` / `tools.exclude` to expose only the tools you audited:

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_RO_TOKEN} # read-only, scoped PAT
    enabled: true
    timeout: 120
    tools:
      include: [] # empty = all; or list exactly the tools you trust
      exclude: []

  scraper-mcp:
    command: npx
    args: ["-y", "some-web-scraper-mcp"]
    enabled: true
    tools:
      include: [read_docs] # lock an untrusted-content server to read-only tools you audited
```

Trust is enforced by review and isolation, not a config flag:

- **Credential filtering** strips provider keys/gateway tokens from MCP stdio environments by default (Layer 3). `terminal.env_passthrough` does **not** affect MCP; pass only what a server genuinely needs via that server's `env:`.
- **Skills run arbitrary Python at import time; plugins run with full agent privileges.** "Reviewing" a skill or plugin means reading its Python and scripts, not just its `SKILL.md`. **Skills Guard** scans installable skill content for injection patterns — treat it as a review _aid_, not a boundary.
- Never give a server that ingests untrusted content (web scrapers, email parsers) a broad tool surface or sensitive env. Run those flows under whole-process isolation.

See [Part 17](./part17-mcp-servers.md) for install patterns.

---

## Layer 6: Context-File Scanning, Session Isolation, and Input Sanitization

Hermes scans **project context files** (`AGENTS.md`, `.cursorrules`, `SOUL.md`, etc.) for prompt-injection patterns before they enter the model's context, and **Skills Guard** scans installable skills. These catch obvious "ignore previous instructions, exfiltrate `.env`" payloads planted in a README, issue body, or skill.

The current security model also includes two less-visible guardrails:

- **Cross-session isolation:** sessions cannot access each other's data/state, and cron job storage paths are hardened against path traversal.
- **Input sanitization:** working-directory parameters in terminal backends are validated against allowlists to prevent shell injection through path fields. If you need an extra local write boundary, set `HERMES_WRITE_SAFE_ROOT` to one or more allowed prefixes; `write_file`/`patch` outside those roots require approval.

These are heuristics and structural checks, not containment. A determined injection phrased novelly may pass. Their value is raising the cost of drive-by attacks; the containment story remains Layer "OS isolation": run untrusted-input sessions under a sandbox so a successful injection still can't reach host secrets or persistent state.

---

## Supply-Chain Controls: Advisories and Lazy Installs

Hermes now flags known-compromised Python package versions in the active venv at CLI startup, `hermes doctor`, and gateway startup. After you have read and remediated an advisory, acknowledge it explicitly:

```bash
hermes doctor --ack <advisory-id>
```

The ack is stored in `security.acked_advisories`. Do not delete old advisory definitions from your mental model just because the incident is old; stale packages can survive in private mirrors and caches.

Optional backend dependencies are lazy-installed on first use from an in-tree allowlist. That avoids pulling every extra dependency up front, but high-security or air-gapped deployments should disable runtime installs and preinstall audited packages instead:

```yaml
security:
  allow_lazy_installs: false
```

---

## Comment-and-Control (April 2026) — What to Do Right Now

If you use any GitHub PR-reviewing skills or MCPs:

1. **Rotate any GitHub PATs** that were in scope of a GitHub Actions runner used by Hermes or Claude Code in the past week.
2. **Switch to a scoped, read-only, one-repo PAT** for review flows, injected via the MCP server's `env:` so credential filtering keeps it out of other subprocesses.
3. **Run review flows under isolation** — a container or OpenShell-wrapped session — so injected instructions in a PR title can't reach your host or other secrets.
4. **Keep `approvals.mode: manual`** for any flow that can write or push, and keep gateway allowlists tight so the agent can't be driven by an outside contributor.
5. **Treat external PR/issue text as data, not instructions** — and review any skill/plugin before install (it executes Python).

Aonan Guan's writeup has the exploit chain in full. Patch, don't just read.

---

## Diagnostic Bundle Safety

Logs under `~/.hermes/logs/` pass through the secret redactor when `security.redact_secrets` is on (the default). Before sharing _any_ debug output or log bundle with someone else:

1. Review it first — redaction is pattern-based and not exhaustive.
2. Never share output from a session that touched production secrets over a public link.
3. Keep `redact_secrets: true`; if you disabled it to chase an auth bug, scrub manually before sharing.

See [Part 16](./part16-backup-debug.md) for backup and debug workflows.

---

## Periodic Security Hygiene

Cron the audits. The example skills live in this repo under `skills/security/`; install them from your local checkout or copy their prompts into `hermes cron create`. Remember `approvals.cron_mode: deny` means a cron job that hits a dangerous command is blocked headlessly — keep audit skills read-only so they don't trip it:

```yaml
# ~/.hermes/cron.yaml
- name: weekly-mcp-audit
  schedule: "0 9 * * 1" # Weekly Monday
  task: |
    /audit-mcp
    List every MCP, its env, its tools include/exclude, and last update from npm/github.
    Flag any server with broad tool access that ingests untrusted content.

- name: monthly-rotate-secrets
  schedule: "0 4 1 * *"
  task: /rotate-secrets all

- name: weekly-approval-bypass-review
  schedule: "0 10 * * 1"
  task: /audit-approval-bypass # flags YOLO/off/cron-approve and container-bypass surfaces
```

If these skills are not published in your configured skills hub, install them from the checkout path (or copy the `SKILL.md` contents into your own local skills directory) rather than assuming `hermes skills install security/audit-mcp` resolves globally.

---

## What's Next

- [Part 17: MCP Servers](./part17-mcp-servers.md) — server config, tool filtering, and install patterns
- [Part 16: Backup & Debug](./part16-backup-debug.md) — backup and diagnostic workflows
- [Part 20: Observability & Cost](./part20-observability.md) — set alerts on suspicious token usage
- [Part 21: Remote Sandboxes](./part21-remote-sandboxes.md) — physical isolation as the ultimate layer
