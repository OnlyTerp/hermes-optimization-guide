# Part 21: Remote Execution & Workspace Isolation

_Hermes can still do the "phone drives, beefy machine does the work" pattern, but the current runtime does not expose a native sandbox subsystem. There is no sandbox-profile config block, no sandbox CLI subcommand, and no sandbox slash command. Use terminal backends, git worktrees, Kanban worker lanes, MCP servers, and skills instead._

---

## The Current Pattern

```text
Your phone / chat client
        |
        v
Hermes driver on a small VPS
- gateways and approvals
- conversation state
- memory, skills, MCP config
- Kanban board
        |
        v
Execution target
- local shell
- Docker or Singularity container
- SSH host
- Modal or Daytona terminal backend, when supported by your installed build
- external runtime reached through a CLI, MCP server, or custom skill
```

Hermes stays the coordinator. The execution target is where LLM-emitted shell and file-tool operations run. For coding work, use git branches or worktrees as the state boundary, then push a reviewable diff. Do not rely on a Hermes-managed remote sandbox lifecycle or automatic diff-back sync; those are not current CLI/config surfaces.

---

## Pick The Right Execution Boundary

| Pattern           | Hermes surface                                                              | Best for                                                             | Caveat                                                                                         |
| ----------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Local shell       | `terminal.backend: local` or default config                                 | Trusted personal projects on the driver host                         | No OS isolation from the host                                                                  |
| Local container   | `terminal.backend: docker` or `singularity`                                 | Risky shell commands, dependency-heavy builds, repeatable toolchains | Only shell/file-tool paths are isolated; in-process plugins/MCP still run with the agent       |
| Remote host       | `terminal.backend: ssh`                                                     | Homelab boxes, beefy workstations, GPU hosts, existing dev servers   | You own lifecycle, updates, and source checkout                                                |
| Modal / Daytona   | `terminal.backend: modal` or `daytona`, where your Hermes build supports it | Bursty remote compute or persistent cloud workspaces                 | Configure only keys your installed build exposes; do not create a legacy sandbox-profile block |
| Git worktree      | `hermes --worktree` or Kanban `--workspace worktree`                        | Parallel local coding sessions and worker lanes                      | Isolation is source-tree isolation, not a remote runtime                                       |
| External runtimes | Vendor CLI/API through MCP or a skill                                       | Vercel builds, Fly Machines, E2B notebooks, CI runners               | Hermes orchestrates them; they are not native Hermes-managed execution backends                |

For untrusted input, remember the security model from [Part 19](./part19-security-playbook.md): a terminal backend confines shell/file-tool activity, not every in-process code path. Use whole-process wrapping when the whole agent must be isolated.

---

## Configure A Terminal Backend

Hermes terminal backends live under the top-level `terminal:` config key.

### Local

```yaml
# ~/.hermes/config.yaml
terminal:
  backend: local
  cwd: /home/hermes/projects/myapp
```

Use this for the simplest driver-box workflow. Pair it with `hermes --worktree` for isolated coding sessions.

### Docker Or Singularity

```yaml
# ~/.hermes/config.yaml
terminal:
  backend: docker # local | docker | singularity | modal | daytona | ssh
  docker_image: nikolaik/python-nodejs:python3.11-nodejs20
  cwd: /workspace
  docker_mount_cwd_to_workspace: false # opt in only when you want the host cwd mounted
  container_persistent: false # false resets the container filesystem per session
```

Switch `backend` to `singularity` in environments where Singularity is the supported container runtime. Keep host secrets in `~/.hermes/.env`; do not bake them into the image.

### SSH Host

```yaml
# ~/.hermes/config.yaml
terminal:
  backend: ssh
  ssh_host: devbox.example.com
  ssh_user: hermes
  ssh_port: 22
  ssh_key: ~/.ssh/id_ed25519
```

This is the most practical "small VPS drives a bigger machine" setup. Put the repo on the SSH host, run the worker there, and use git to move reviewed changes back through branches and PRs.

### Modal Or Daytona

Current docs list Modal and Daytona as terminal backend choices, but provider-specific fields can vary by Hermes build. Treat them as terminal backends, not named sandbox profiles:

```yaml
# ~/.hermes/config.yaml
terminal:
  backend: modal # or daytona, when supported by your installed build
```

After changing backend config, run:

```bash
hermes config check
hermes doctor
```

If your installed Hermes build does not expose that backend, fall back to Docker or SSH, or wrap the vendor API with a skill/MCP integration.

---

## Isolated Local Sessions With `--worktree`

For a one-off coding pass from a git repo:

```bash
cd ~/projects/myapp
hermes --worktree --tui
```

For a scripted prompt:

```bash
cd ~/projects/myapp
hermes --worktree -z "Run the test suite, fix the auth null-check failure, and summarize the diff."
```

`--worktree` gives the session a separate git worktree so parallel agents do not edit the same checkout. It is ideal when the driver host has enough CPU/RAM and you mainly need source isolation.

---

## Durable Worker Lanes With Kanban

For work that should survive restarts, handoffs, review, or retries, put it on the Kanban board and assign a worker profile:

```bash
hermes kanban create "Fix the auth null-check and open a PR" \
  --assignee codex-worker \
  --workspace worktree \
  --branch wt/auth-null-check

hermes kanban dispatch --max 1
```

Useful commands while it runs:

```bash
hermes kanban list
hermes kanban show <task-id>
hermes kanban runs <task-id>
hermes kanban log <task-id>
```

The worker uses the configured terminal backend for shell/file operations and the Kanban workspace setting for source isolation. Keep "worker exited" and "work is done" separate: require tests, review, and a clean git diff before closing the card.

---

## Coding Agents On Remote Targets

The coding-agent layer from [Part 18](./part18-coding-agents.md) still applies: Claude Code, Codex, Gemini CLI, OpenCode, and ACP-compatible runtimes can sit behind Hermes as worker lanes or interactive sessions. For this chapter, the important rule is that shell/file operations land wherever `terminal.backend` points.

A common road-warrior setup is:

1. Hermes gateway and memory run on the small VPS.
2. `terminal.backend: ssh` points shell/file work at a stronger dev box.
3. Coding-agent work is assigned through Kanban with `--workspace worktree`.
4. The worker pushes a branch or opens a PR instead of syncing opaque files back to the driver.

---

## External Runtimes: Vercel, Fly, E2B, CI

Vercel, Fly Machines, E2B, and CI runners can be very useful execution targets, but in the current Hermes surface they should be modeled as external integrations.

| Runtime       | Recommended integration shape                                                                                                                               |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Vercel builds | Use the Vercel CLI/API from a Docker or SSH terminal backend, or expose a Vercel MCP/tool skill that runs build/deploy commands and returns logs/artifacts  |
| Fly Machines  | Use `flyctl` from a skill or MCP server to start/stop a machine; if you want Hermes shell execution there, expose SSH and configure `terminal.backend: ssh` |
| E2B           | Use an E2B MCP server or custom tool for notebook-style execution; pass source through git/artifacts, not a native Hermes execution profile                 |
| CI runners    | Have Hermes open a PR, trigger CI, then read status/logs through GitHub/GitLab MCP or CLI tools                                                             |

A good custom skill for an external runtime should:

1. State the target runtime and repo/branch it will use.
2. Create or reuse an isolated checkout.
3. Run the vendor CLI/API with explicit timeouts.
4. Return logs, artifact URLs, and exit status.
5. Avoid writing provider secrets to `config.yaml`, logs, or the repo.

---

## File Movement And Source Of Truth

Use git as the primary sync mechanism:

- Work in a branch or worktree.
- Push changes to the remote repository.
- Review and merge through the normal PR path.
- Pull artifacts explicitly from the external runtime when needed.

If you need raw file copy for an SSH host, use explicit `rsync`, `scp`, or a skill that names source, destination, ignore patterns, and conflict behavior. Do not describe it as Hermes automatic sandbox teardown sync.

---

## Observability

There is no sandbox-status subcommand. Use the surfaces that actually exist:

```bash
hermes status
hermes doctor
hermes config check
hermes logs -f
hermes kanban list
hermes kanban show <task-id>
hermes kanban runs <task-id>
```

The [Web Dashboard](./part12-web-dashboard.md) is useful for config editing, chat/TUI access, sessions, and Kanban state. Vendor runtimes keep their own logs and billing dashboards; surface those back through MCP/skills when you need them in Hermes.

---

## Troubleshooting

| Symptom                                                  | Fix                                                                                                                               |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `hermes: invalid choice: sandbox`                        | Expected on current Hermes. Use `terminal.backend`, `hermes --worktree`, or `hermes kanban ... --workspace worktree`.             |
| Config with a legacy sandbox-profile block has no effect | Remove it. Configure `terminal:` or external runtime skills/MCP servers instead.                                                  |
| Modal/Daytona backend is unavailable                     | Check `hermes config check` and `hermes doctor`; use Docker/SSH or a custom integration if your build does not ship that backend. |
| Remote worker edited the wrong checkout                  | Use Kanban `--workspace worktree`, name branches with `--branch`, and review `git status` before completion.                      |
| External runtime needs secrets                           | Put secrets in the vendor's secret store or a protected local env path; do not write them into the repo or `config.yaml`.         |
| Need full-agent containment                              | Terminal backend isolation is not enough; use the whole-process isolation guidance in Part 19.                                    |

---

## What's Next

- [Part 18: Coding Agents](./part18-coding-agents.md) - delegate Claude Code / Codex / Gemini CLI through Hermes.
- [Part 19: Security Playbook](./part19-security-playbook.md) - understand terminal-backend isolation versus whole-process containment.
- [Part 23: Tenacity Stack](./part23-tenacity-stack.md) - use Kanban, worktrees, checkpoints, and durable worker lanes.
- [Part 17: MCP Servers](./part17-mcp-servers.md) - connect external runtimes and vendor APIs as tool integrations.
