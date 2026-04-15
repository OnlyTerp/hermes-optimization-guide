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

# Parallel batch (up to 3)
delegate_task(
    tasks=[
        {
            "goal": "Research LightRAG alternatives for graph RAG",
            "toolsets": ["web"]
        },
        {
            "goal": "Benchmark current LightRAG search latency",
            "context="Path: ~/.hermes/skills/research/lightrag/",
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
    context="Repo at /home/terp/my-app. Use existing component library in src/components/",
    acp_command="claude",
    acp_args=["--acp", "--stdio", "--model", "claude-sonnet-4-20250514"]
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

## SWE-1.6 via Windsurf Cascade

For complex coding tasks, use Windsurf's SWE-1.6:

```python
# Send a coding task to Windsurf Cascade
# Requires Windsurf running with --remote-debugging-port=9222
subprocess.run([
    "python", 
    "~/.hermes/skills/autonomous-ai-agents/windsurf-cascade/scripts/cascade_send.py",
    "Build a React dashboard with real-time WebSocket updates"
])
```

**Orchestrator pattern:** Hermes handles APIs, data, decisions. SWE-1.6 handles UI, components, bug fixes. Each does what it's best at.

## Parallelization Rules

| Scenario | Approach |
|----------|----------|
| 3 independent research tasks | Batch `delegate_task` with `tasks` array |
| 1 complex coding task | ACP subagent (Claude Code or Codex) |
| Multiple code changes in different files | SWE-1.6 via Cascade |
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

*The orchestrator pattern is how you scale. One brain, many hands.*
