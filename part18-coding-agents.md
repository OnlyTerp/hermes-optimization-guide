# Part 18: Delegating to Coding Agents — Claude Code, Codex, Gemini CLI, OpenCode

*Hermes' killer move for developers isn't writing code itself — it's **orchestrating** specialist coding agents from your Telegram chat or Kanban board. Drive Claude Code, Codex, Gemini CLI, OpenCode, and cheap Kimi/GLM lanes from your phone while Hermes keeps state, memory, approvals, and review gates.*

---

## Why Delegate Instead of Doing It Yourself

Hermes is excellent at reasoning, memory, conversation, and workflow. It is *not* the best at sustained multi-file code generation. The coding-specialist agents are:

| Agent | Strengths | Auth model |
|-------|-----------|------------|
| **Claude Code** | Best unattended PR work, large refactors, tests, reviews; Week 20+ agent view, `/goal`, and fast Opus 4.7 mode make it the premium lane | Pro/Max OAuth or `ANTHROPIC_API_KEY` |
| **Codex** (OpenAI) | Fast sandboxed feedback loop, bug hunts, small/medium edits; v0.133+ goals default well and runs cleanly behind `hermes proxy` | OAuth via `openai` CLI, `OPENAI_API_KEY`, or `hermes proxy` |
| **Gemini CLI** | 1M context and multimodal repo/document sweeps; v0.43 improves surgical edits, session import/export, and OAuth behavior on headless Linux | OAuth via `gemini auth`; for normal model-provider use, Hermes uses a `GEMINI_API_KEY` or Vertex AI ([Part 9](./part9-custom-models.md)) |
| **OpenCode** (anomalyco) | Open-source, routes to Kimi K2.6 / GLM / MiMo cheaply | Bring any provider key |
| **Aider** | Surgical git-based edits, smallest token footprint; works well through `hermes proxy` | Bring any provider key or local proxy |

Hermes keeps state, memory, conversation, approvals, Kanban lifecycle, and platform integration; each specialist does what it does best. You get one control plane, many agents.

---

## Prerequisites

```bash
# Claude Code
npm install -g @anthropic-ai/claude-code
claude login                      # Or set ANTHROPIC_API_KEY

# Codex
npm install -g @openai/codex
codex auth login

# Gemini CLI
npm install -g @google/gemini-cli
gemini auth                       # Only needed when delegating to Gemini CLI itself

# OpenCode (Go variant preferred for Hermes)
curl -fsSL https://opencode.ai/install.sh | bash
opencode auth                     # BYOK

# Aider
pipx install aider-chat
```

Verify from inside Hermes:

```
/skill claude-code
/skill codex
/skill gemini-cli
```

Each skill runs `--version` and `auth status` to confirm the agent is reachable.

---

## Mode 1: Print Mode (Preferred for Most Tasks)

Print mode is non-interactive — run once, return the result, exit. No PTY, no approval prompts to manage, clean stdout capture. Ideal for the 80% of tasks that are "here's a change, come back when it's done."

### From a Skill (Recommended)

Hermes ships with a `claude-code` skill that handles env setup, allowed-tool flags, and error recovery:

```
/claude-code refactor src/auth/ to use the new JWT rotation helper
```

This runs:

```bash
claude -p "refactor src/auth/ to use the new JWT rotation helper" \
       --allowedTools "Read,Edit,Bash" \
       --max-turns 20 \
       --output-format json
```

Captures the JSON, parses the file diff, posts a summary back to your Telegram/Discord/Slack thread with a link to the git diff.

### Parallel Delegation

Need three things done? Fire all three at once:

```
In parallel:
1. /claude-code write unit tests for src/payments/
2. /codex optimize the hot path in worker.ts
3. /gemini-cli audit dependencies in package.json for security
```

Hermes runs them in three independent subagent slots, streams progress, and aggregates.

### Cost-Routing by Task Type

Each specialist has a sweet spot. Let Hermes route:

| Task | Sweet-spot specialist | Why |
|------|-----------------------|-----|
| Large refactor across 10+ files | Claude Code + Sonnet 5/Opus 4.7 | Best at sustained multi-file edits |
| Bug reproduction + fix in a single file | Codex + GPT-5.5/Codex | Fast sandboxed turnaround |
| "Explain this codebase" | Gemini CLI + Gemini 3.1 Pro | 1M context eats any repo whole |
| Bulk surgical edits with deterministic diffs | Aider | Smallest token footprint, git-native |
| Anything on a budget | OpenCode + Kimi K2.6 / GLM | Much cheaper than frontier models for routine edits |

How do you encode that routing? Not in YAML. There is no `delegation.routing:` match-rule DSL in Hermes — [Part 20's warning](./part20-observability.md) applies: if you see a routing DSL in a config example, treat it as a feature request, not a feature. The primitives that actually exist are the primary `model:`/`provider:`, the per-task `auxiliary:` block, `provider_routing:` for OpenRouter, and `hermes fallback`. For delegation, routing is behavioral: tell Hermes the table above (put it in a memory or a skill's instructions) and let the orchestrator pick the specialist per task — or just name the specialist explicitly (`/codex ...`, `/claude-code ...`).

## Mode 1B: Kanban Worker Lanes (Preferred for Long Work)

For work that should survive restarts, human review, retries, or multiple handoffs, put the coding agent behind [Part 23's Kanban flow](./part23-tenacity-stack.md#2-add-worker-lanes-instead-of-giant-prompt-swarms):

```text
/kanban create "Fix flaky checkout tests and open a PR" \
  --assignee codex-worker \
  --workspace worktree
```

Good defaults:

- `codex-worker` for small isolated fixes; successful exit blocks for Hermes/human review instead of auto-completing.
- `claude-code` for multi-file refactors; require tests and review before marking done.
- `gemini-cli` for repo-scale audit cards that should produce comments/specs, not commits.
- `reviewer` as a separate lane so "agent wrote code" and "work is done" stay different states.

Use print mode for quick one-shot answers. Use Kanban lanes for anything you would be embarrassed to lose halfway through.

---

## Mode 2: Thread-Bound Interactive Sessions (OpenClaw Pattern)

What you actually want on your phone: a Telegram topic named "Claude Code" where every message lands in a persistent Claude Code session. No re-explaining context. No re-spawning. Just chat with the coding agent directly, with Hermes handling the transport, memory, and voice-to-text.

This pattern is useful for pair-programming from chat. For unattended work, prefer Kanban worker lanes so task state and review gates survive restarts. The interactive workflow:

```bash
# In Telegram, create a topic, then from the CLI or dashboard:
hermes bind-thread <thread-id> --runtime claude-code --cwd ~/projects/myapp
```

From that point:
- Every message in the topic goes to a persistent Claude Code session
- File edits happen in `~/projects/myapp` on the Hermes host
- Orchestrator subagents can spawn their own workers if `max_spawn_depth` allows it
- Concurrent workers coordinate file state instead of blindly overwriting siblings
- `/unbind` in the topic detaches and reverts to normal Hermes chat
- `/runtime gemini-cli` swaps the runtime without losing the thread

The same binding works for Codex, Gemini CLI, OpenCode, and any ACP-compatible coding agent.

**Remote execution bonus:** combine with the [remote sandbox feature](./part21-remote-sandboxes.md) and the coding agent runs on a Modal/Daytona/SSH host — your phone drives, a beefy remote does the work.

---

## Agent Tooling Updates (May 25, 2026)

- **Claude Code Week 20+**: agent view, `/goal`, and faster Opus 4.7 make it the best premium worker lane for high-stakes PRs.
- **Codex v0.133+**: goals are enabled by default; point it at `hermes proxy` when you want ChatGPT/Codex OAuth without another API key.
- **Gemini CLI v0.43**: better surgical edit steering, session export/import, and headless OAuth fixes make it safer as a repo-scale reader.
- **Zed ACP Registry**: v0.14 exposes Hermes through `uvx`/ACP so Zed and other ACP-aware editors can drive Hermes directly.
- **Aider/Cline/Continue**: all benefit from `hermes proxy` because they only need an OpenAI-compatible base URL.

---

## ACP: The Protocol That Makes This Possible

Agent Client Protocol (ACP) is to coding agents what MCP is to tools — a standard transport for one agent to delegate to another. Hermes supports ACP as both client and server:

- **As ACP client:** Hermes invokes Claude Code / Codex / Gemini as subagents via their ACP endpoints.
- **As ACP server:** you can drive Hermes from another ACP-aware agent (Cursor, Zed, or another Hermes instance).

```yaml
# ~/.hermes/config.yaml
acp:
  enabled: true
  server:
    listen: 127.0.0.1:41212          # Accept inbound ACP from editors
  clients:
    claude-code:
      command: claude
      args: ["--acp"]
    codex:
      command: codex
      args: ["--acp"]
    gemini-cli:
      command: gemini
      args: ["--acp"]
```

The `delegate_task` tool then invokes the chosen ACP client and streams progress back over a single WebSocket.

---

## Git Hygiene When Agents Share a Workspace

The #1 footgun with coding-agent orchestration is two agents touching the same files. There is no `delegation.git:`/`locks:` config block that enforces this for you (again: feature request, not a feature — see [Part 20](./part20-observability.md)). The guardrails are git-native and worth stating in your delegation prompts or skills:

- **One branch per delegation.** Have each specialist work on its own branch (e.g. `devin/claude-code-refactor-auth`) and commit before handing back — every major coding agent will do this when told to.
- **Kanban `--workspace worktree`** (Mode 1B above) gives each card its own git worktree, which is real, supported isolation.
- **Require a clean tree** before starting a delegation; refuse to dispatch onto uncommitted local changes.
- **Leave merges to a human** (or a dedicated reviewer lane) — agents return branch names, not merged main.

The same pattern works for parallel delegation — each agent gets its own branch or worktree.

---

## Approval Posture

Coding agents run shell commands and write files. You need an approval policy or you'll lose a weekend debugging an accidental `rm -rf node_modules` in the wrong dir.

```yaml
# ~/.hermes/config.yaml — schema verified against Part 19 (v0.18)
approvals:
  mode: manual        # prompt on every dangerous command a specialist emits
  timeout: 60         # fail-closed deny
  cron_mode: deny     # unattended delegations never auto-approve
```

The dangerous-command patterns (`rm -rf`, `git push --force`, pipe-to-shell, ...) are built into Hermes (`tools/approval.py`) — there is no `delegation.approval.denylist:` where you write your own, and a small hardline blocklist can't be overridden at all. Subagents inherit the parent session's approval posture by default and you can override it per delegation (`delegate_task(..., approvals="ask")`). See [Part 19](./part19-security-playbook.md#layer-2-dangerous-command-approval) for the full story, and [Part 16](./part16-backup-debug.md#approval-bypass-for-trusted-subagents) for inheritance — use relaxed postures for trusted specialists, not for every agent.

---

## Recipe: Review My PR From Telegram

```
You (Telegram): /review_pr myorg/myapp#342
Hermes: *runs the `github-pr-review` skill*
  1. Pulls the PR diff via GitHub MCP
  2. Sends to Claude Code with --allowedTools "Read" --max-turns 5
  3. Claude Code returns a structured review
  4. Hermes posts a GitHub PR comment with the review
  5. Replies in Telegram with a summary + link
```

Skill source: `~/.hermes/skills/github-pr-review/SKILL.md` (bundled, plus the agent-created variants that appear after you use it a few times).

---

## Recipe: Nightly Cron Maintenance

```yaml
# ~/.hermes/config.yaml
cron:
  jobs:
    weekly-dep-audit:
      schedule: "0 3 * * 1"            # Mondays 3am
      prompt: |
        /gemini-cli audit package.json for security advisories
        If any CRITICAL, open a GitHub issue in this repo with the list
      deliver: telegram_engineering
```

Hermes runs the delegation unattended, Gemini's 1M context reads the whole lockfile, a GitHub MCP opens the issue. You wake up to a triage ticket, not a surprise CVE.

---

## What's Next

- [Part 17: MCP Servers](./part17-mcp-servers.md) — the *tools* layer that these coding agents use
- [Part 19: Security Playbook](./part19-security-playbook.md) — locking down agents that execute shell commands
- [Part 21: Remote Sandboxes](./part21-remote-sandboxes.md) — run coding agents on a Modal/Daytona/SSH host from your phone
- [Part 8: Subagent Patterns](./part8-subagent-patterns.md) — the underlying delegation primitives
