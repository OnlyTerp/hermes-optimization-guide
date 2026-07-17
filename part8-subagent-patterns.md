# Part 8: Subagent & Orchestrator Patterns (Stop Doing Everything Yourself)

*One agent can't do everything well. Delegate.*

---

## The Core Idea

Hermes is the orchestrator. It decides what to do, then delegates execution to specialized subagents. Each subagent runs in isolation — own context, own tools, own session.

**When to delegate:**
- Reasoning-heavy tasks (debugging, code review, research)
- Tasks that would flood your context with intermediate data
- Parallel independent workstreams (research A and B simultaneously)

**When NOT to delegate:**
- Single tool calls (just call the tool directly)
- Simple tasks that need 1-2 steps
- Tasks needing user interaction (subagents can't use clarify)

## delegate_task — The Main Tool

```python
# Single task
delegate_task(
    goal="Debug why the API returns 403 on POST requests",
    context="File: src/api/client.py. Error started after adding auth headers. Token is valid.",
    toolsets=["terminal", "file"]
)

# Parallel batch
delegate_task(
    tasks=[
        {
            "goal": "Research LightRAG alternatives for graph RAG",
            "toolsets": ["web"]
        },
        {
            "goal": "Benchmark current LightRAG search latency",
            "context": "Path: ~/.hermes/skills/research/lightrag/",
            "toolsets": ["terminal"]
        },
        {
            "goal": "Check if our embedding model has a newer version",
            "toolsets": ["web"]
        }
    ]
)
```

**Key details:**
- Subagents have NO memory of your conversation. Pass everything via `context`.
- Results come back as a summary. Intermediate tool calls never enter your context.
- Each subagent gets its own terminal session.
- Default max iterations: 50. Lower it for simple tasks (`max_iterations=10`).

## Background Delegation (v0.17) and Fan-Out (v0.18)

By default `delegate_task` blocks your session until the subagent returns. Add `background=True` and it returns a **handle immediately** — you keep chatting, and the result re-enters the conversation as a new turn when it's done:

```python
delegate_task(goal="Deep-dive the competitor's pricing page", background=True)
```

v0.18 extends this to batches — **background fan-out**. Dispatch parallel subagents and get **one consolidated turn when all of them finish**:

```python
delegate_task(
    tasks=[
        {"goal": "Audit src/auth for the token-refresh bug"},
        {"goal": "Audit src/billing for the same pattern"},
        {"goal": "Check upstream issues for known reports"},
    ],
    background=True,
)
```

The CLI/TUI status bar tracks running background subagents, and the desktop app can open a live **watch-window** on any of them ([Part 24](./part24-desktop-app.md)). Rules of thumb:

- **Foreground** when the next step depends on the result.
- **Background** for research, audits, and monitoring legs you'd otherwise wait on.
- **Kanban** ([Part 23](./part23-tenacity-stack.md)) when the work must survive restarts or involve humans — background subagents die with the process.

## The Seven-Rung Agent Ladder

The community pedagogy that stuck this July: seven agent architectures, each mapping to a concrete Hermes mechanism. Don't build rung 7 on day one — the taught progression is **1+6 first**, then climb as the work demands it.

| # | Type | Hermes mechanism | When |
|---|------|------------------|------|
| 1 | Basic + tools | Enable tools in Desktop/Dashboard | Single tasks |
| 2 | MCP-backed | MCP → Add Server ([Part 17](./part17-mcp-servers.md)) | Multi-platform work |
| 3 | Sequential pipeline | Cron + wake gates + file handoffs; one profile per step | Dependent multi-step |
| 4 | Parallel | `delegate_task` batch (default 3 subagents, clean contexts, summaries only) | Research / analysis |
| 5 | Routed specialists | Kanban decompose ([Part 23](./part23-tenacity-stack.md)) or a Chief-of-Staff profile | Inbox triage / multi-role |
| 6 | Human-in-the-loop | `approvals.mode: manual` (default) or `smart`; 60s fail-closed | Send / deploy / spend / post |
| 7 | Dynamic spawn | Orchestrator + `max_spawn_depth: 2` → up to 9 workers | Complex discovery |

**Progression:** 1+6 → 2 → 4 → 3 → 5 → 7. Most workloads never need past rung 5.

## One Agent vs Many Profiles

Two legitimate architectures — the community is genuinely split, so pick on the shape of your work:

- **One agent + skills + subagents** (subagents only for parallelism): best when your domains overlap and shared memory is the point. For the same brain on many chat platforms, use **one profile with many gateways** — shared SOUL and memory everywhere.
- **Profiles as rooms** (coder / research / private / cron): each profile is a *whole separate agent* — own memory, sessions, skills, and bot token. Best for long-running multi-domain setups where a coding session polluting your research memory is a real cost. Clone a starting point with `hermes profile create <name> --clone-all`.

**The boundary that surprises people:** profiles isolate Hermes state, **not the filesystem** — every profile is the same OS user. Real isolation needs Docker/SSH/ACLs ([Part 19](./part19-security-playbook.md)). More in [Part 27](./part27-power-secrets.md#3-profiles-files--identity).

## The CEO/COO/Worker Pattern

```
CEO (you + Hermes main agent)
  │
  ├── COO (delegate_task for planning/review)
  │     └── Returns: strategy, plan, review notes
  │
  └── Workers (delegate_task for execution)
        ├── Worker 1: Build feature A
        ├── Worker 2: Build feature B
        └── Worker 3: Write tests
```

**CEO:** Makes decisions, assigns tasks, reviews results.
**COO:** Researches, plans, reviews code. One subagent, reasoning-heavy.
**Workers:** Execute specific tasks in parallel. Multiple subagents, action-heavy.

## ACP Subagents (Claude Code, Codex)

For coding tasks, delegate to dedicated coding agents via ACP:

```python
# Claude Code
delegate_task(
    goal="Implement the user settings page with React",
    context="Repo at ~/projects/my-app. Use existing component library in src/components/",
    acp_command="claude",
    acp_args=["--acp", "--stdio", "--model", "claude-sonnet-5"]
)

# Codex
delegate_task(
    goal="Refactor database layer to use connection pooling",
    context="File: src/db/connection.py. Currently opens new connection per query.",
    acp_command="codex"
)
```

**When to use ACP vs regular delegate_task:**
- ACP agents (Claude Code, Codex) are better at coding — tool calling, file editing, running tests
- Regular delegate_task is better for research, analysis, and multi-tool workflows
- ACP agents are faster for single-file edits

## Other Coding Agents (Windsurf, Gemini CLI, …)

Anything with a CLI or ACP endpoint can be a worker — see [Part 18: Delegating to Coding Agents](./part18-coding-agents.md) for the full routing pattern (Claude Code, Codex, Gemini CLI, and friends, each bound to a persistent thread).

## Parallelization Rules

| Scenario | Approach |
|----------|----------|
| 3 independent research tasks | Batch `delegate_task` with `tasks` array (`background=True` if you want to keep working) |
| 1 complex coding task | ACP subagent (Claude Code or Codex) |
| Single API call | Just call the tool, don't delegate |
| Task needs user input | Do it yourself, can't delegate interactive work |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Delegating a single tool call | Just call the tool directly |
| Not passing enough context to subagent | Subagents know nothing — pass file paths, error messages, constraints |
| Delegating sequential tasks in parallel | If task B depends on task A's output, run them sequentially |
| Setting max_iterations too high | Simple tasks don't need 50 iterations — use 10-15 |
| Forgetting subagents can't use clarify | If a task might need clarification, do it yourself |

---

## What's Next

The subagent system has grown rapidly. Continue with:

- **[Part 18: Delegating to Coding Agents](./part18-coding-agents.md)** — the OpenClaw pattern (thread-bound Telegram topics → persistent Claude Code / Codex / Gemini CLI runtimes). Print-mode vs interactive, ACP-as-server, git branch isolation, routing rules.
- **[Part 17: MCP Servers](./part17-mcp-servers.md)** — give subagents tools that stay in sync across Hermes, Claude Code, and Cursor.
- **[Part 21: Remote Sandboxes](./part21-remote-sandboxes.md)** — run your subagents on Modal/Daytona/SSH so a $5 VPS can drive a beefy workspace.
- **[Part 20: Observability](./part20-observability.md)** — trace every subagent call in Langfuse, with per-skill cost breakdown.

---

*The orchestrator pattern is how you scale. One brain, many hands.*
