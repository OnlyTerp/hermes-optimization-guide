# Part 18: Delegating to Coding Agents — Claude Code, Codex, Gemini CLI, OpenCode

*Hermes' killer move for developers isn't writing code itself — it's **orchestrating** the specialist coding agents from your Telegram chat. Drive Claude Code, Codex, Gemini CLI, and OpenCode from your phone while you're on the subway. This is the OpenClaw-style pattern people are calling "clawdbots" and "moltbots" in the 2026 agent scene.*

---

## Why Delegate Instead of Doing It Yourself

Hermes is excellent at reasoning, memory, conversation, and workflow. It is *not* the best at sustained multi-file code generation. The coding-specialist agents are:

| Agent | Strengths | Auth model |
|-------|-----------|------------|
| **Claude Code** | Strongest at large refactors, test writing, PR reviews | Pro/Max OAuth or `ANTHROPIC_API_KEY` |
| **Codex** (OpenAI) | Fast feedback loop, great at bug hunts, small edits | OAuth via `openai` CLI or `OPENAI_API_KEY` |
| **Gemini CLI** | 1M context — unbeatable for "read the whole repo" tasks | OAuth via `gemini auth` (free tier generous) |
| **OpenCode** (anomalyco) | Open-source, routes to GLM/Kimi/MiMo cheaply | Bring any provider key |
| **Aider** | Surgical git-based edits, smallest token footprint | Bring any provider key |

Hermes keeps state, memory, conversation, and platform integration; each specialist does what it does best. You get one chat interface, many agents.

---

## Prerequisites

```bash
# Claude Code
npm install -g @anthropic-ai/claude-code
claude auth login                 # Or set ANTHROPIC_API_KEY

# Codex
npm install -g @openai/codex-cli
codex auth login

# Gemini CLI
npm install -g @google/gemini-cli
gemini auth                       # Free tier: 1500 req/day

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
| Large refactor across 10+ files | Claude Code | Best at sustained multi-file edits |
| Bug reproduction + fix in a single file | Codex | Fast turnaround, cheaper per task |
| "Explain this codebase" | Gemini CLI | 1M context eats any repo whole |
| Bulk surgical edits with deterministic diffs | Aider | Smallest token footprint, git-native |
| Anything on a budget | OpenCode + GLM 4.6 / Kimi K2 | One-tenth the cost of Claude for ~80% quality |

A sensible `~/.hermes/config.yaml`:

```yaml
delegation:
  default: claude-code
  routing:
    - match: { type: refactor, files_changed_gte: 5 }
      agent: claude-code
    - match: { type: bugfix, single_file: true }
      agent: codex
    - match: { type: explore, repo_tokens_gte: 200000 }
      agent: gemini-cli
    - match: { type: dependency_audit }
      agent: gemini-cli
    - match: { budget: low }
      agent: opencode
      model: glm-5.1
```

---

## Mode 2: Thread-Bound Interactive Sessions (OpenClaw Pattern)

What you actually want on your phone: a Telegram topic named "Claude Code" where every message lands in a persistent Claude Code session. No re-explaining context. No re-spawning. Just chat with the coding agent directly, with Hermes handling the transport, memory, and voice-to-text.

This is the feature request tracked in [#5394](https://github.com/NousResearch/hermes-agent/issues/5394) and already landing in bits across v0.9/v0.10. As of v0.10.0 the workflow is:

```bash
# In Telegram, create a topic, then from the CLI or dashboard:
hermes bind-thread <thread-id> --runtime claude-code --cwd ~/projects/myapp
```

From that point:
- Every message in the topic goes to a persistent Claude Code session
- File edits happen in `~/projects/myapp` on the Hermes host
- `/unbind` in the topic detaches and reverts to normal Hermes chat
- `/runtime gemini-cli` swaps the runtime without losing the thread

The same binding works for Codex, Gemini CLI, OpenCode, and any ACP-compatible coding agent.

**Remote execution bonus:** combine with the [remote sandbox feature](./part21-remote-sandboxes.md) and the coding agent runs on a Modal/Daytona/SSH host — your phone drives, a beefy remote does the work.

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

The `/delegate_task` tool then picks an ACP client based on `delegation.routing` rules and streams progress back over a single WebSocket.

---

## Git Hygiene When Agents Share a Workspace

The #1 footgun with coding-agent orchestration is two agents touching the same files. Guardrails:

```yaml
delegation:
  git:
    isolate_branches: true            # Each delegation gets its own branch
    branch_prefix: devin/             # Use your convention
    auto_commit: true                 # Commit before handing back
    require_clean_tree: true          # Refuse if the working tree is dirty
  locks:
    strategy: file-level              # Or "workspace" if you want full serialization
```

Hermes creates `devin/claude-code-1723487-refactor-auth`, runs the specialist there, commits, returns the branch name, and leaves the merge decision to you. The same pattern works for parallel delegation — each agent gets its own branch.

---

## Approval Posture

Coding agents run shell commands and write files. You need an approval policy or you'll lose a weekend debugging an accidental `rm -rf node_modules` in the wrong dir.

```yaml
delegation:
  approval:
    default: prompt                   # Prompt on every write
    trusted_agents:
      - claude-code                   # These inherit parent approval posture
    auto_approve_read: true           # Read-only tools never prompt
    denylist:
      - "rm -rf"
      - "git push --force"
      - "curl * | bash"
```

See [Part 19](./part19-security-playbook.md#approval-and-denylist-layers) for the full story. Approval bypass inheritance landed in v0.10 ([Part 16](./part16-backup-debug.md#approval-bypass-for-trusted-subagents)) — use it for trusted specialists, not for every agent.

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
# ~/.hermes/cron.yaml
- name: weekly-dep-audit
  schedule: "0 3 * * 1"                # Mondays 3am
  task: |
    /gemini-cli audit package.json for security advisories
    If any CRITICAL, open a GitHub issue in this repo with the list
  notify: telegram:#engineering
```

Hermes runs the delegation unattended, Gemini's 1M context reads the whole lockfile, a GitHub MCP opens the issue. You wake up to a triage ticket, not a surprise CVE.

---

## What's Next

- [Part 17: MCP Servers](./part17-mcp-servers.md) — the *tools* layer that these coding agents use
- [Part 19: Security Playbook](./part19-security-playbook.md) — locking down agents that execute shell commands
- [Part 21: Remote Sandboxes](./part21-remote-sandboxes.md) — run coding agents on a Modal/Daytona/SSH host from your phone
- [Part 8: Subagent Patterns](./part8-subagent-patterns.md) — the underlying delegation primitives
