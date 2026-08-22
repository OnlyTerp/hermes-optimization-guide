# Part 14: Fast Mode & Background Watchers

*Priority-tier inference, live background-process events, and the newer TUI controls that keep long sessions steerable instead of stuck.*

---

## Fast Mode (`/fast`)

### What It Is

Both OpenAI and Anthropic run **priority processing queues** for latency-sensitive traffic. Higher cost per token, but dramatically lower p50 and p99 latency — especially under load on reasoning models.

`/fast` toggles that priority tier per session. On supported OpenAI/Codex and Anthropic models, flipping it on injects `service_tier: "priority"` into outgoing requests.

### When to Use It

- **Interactive CLI sessions** where you're waiting on each response (coding, debugging).
- **Messaging replies** where a slow answer is a bad UX (Telegram, iMessage, WeChat).
- **Subagent-heavy workflows** where the orchestrator latency stacks (Part 8).
- **Whenever the default tier is rate-limited** — priority tier has its own pool.

Don't use it for:
- Batch cron jobs or overnight research runs where latency doesn't matter.
- Anything where you're trying to minimize cost and the default tier is fine.

### How to Toggle

Fast Mode is a **runtime toggle**, not a YAML key — there is no `agent.service_tier:` (or `fast_mode:`) block in `config.yaml` (see [Part 20](./part20-observability.md)). In any interactive session (CLI or messaging platform — `/fast` works on both):

```text
/fast fast      # opt the current session into Priority Processing / Fast Mode
/fast normal    # back to normal pricing
/fast status    # show the current state
```

It persists for the session until you turn it off. For non-interactive entry points (cron, webhooks), simply never run `/fast fast` from them and they stay on normal pricing.

### Where It Works

- ✅ Interactive CLI (`hermes`)
- ✅ Every gateway platform — the full 30+ adapter lineup ([Part 15](./part15-new-platforms.md)): Telegram, Discord, Slack, Google Chat, WhatsApp (personal + Business Cloud API), Signal, SMS, Email, Home Assistant, Mattermost, Matrix, DingTalk, Feishu/Lark, WeCom, WeCom Callback, Weixin/WeChat, BlueBubbles and Photon (iMessage), QQBot, Tencent Yuanbao, Microsoft Teams, LINE, ntfy, IRC, Buzz, SimpleX, Raft, webhooks, the API server (Open WebUI), A2A, and Hermes Relay frontends
- ✅ Cron jobs started from a session where `/fast fast` is active
- ✅ Subagents (`delegate_task` inherits the parent's tier)
- ❌ Local/Ollama models (no priority tier exists)
- ❌ Free OpenRouter variants (the `:free` suffix forces default tier)

### Pricing Heads-Up

Priority tier is more expensive per token. Watch the **Analytics** tab in the dashboard (Part 12) for per-day cost deltas after enabling it. If you're surprised by a bill, the most common cause is leaving `/fast on` in a long-lived session that's driving work which doesn't need it.

---

## `/steer`, `/queue`, and Background Turns

The newer TUI makes long-running work much easier to control:

| Command | Use it when | Pattern |
|---------|-------------|---------|
| `/steer <instruction>` | The agent is mid-run but drifting | "Continue, but don't edit generated files" |
| `/queue <prompt>` | You want the next task to start after the current one | "After tests pass, summarize the risk" |
| `/background <prompt>` | Fire off work without blocking the main chat | "Research alternatives while I keep coding" |
| `/busy` | You want to inspect what Hermes is doing | Check active runs/subagents |
| `/indicator` | The spinner/activity feed is too loud or too quiet | Toggle busy indicator style |

Best practice:

1. Use `/steer` for **constraints**, not brand-new goals.
2. Use `/queue` for dependent follow-ups.
3. Use `/background` for independent research or monitoring.
4. If the run touches files, keep follow-up prompts specific enough that Hermes can avoid clobbering its own edits.

This is the practical replacement for repeatedly interrupting and restating the whole task.

**The timing semantics people miss:** `/steer <instruction>` is delivered **after the current tool call completes**, inside the same turn — it is *not* a new turn and doesn't reset anything. `/queue` (alias `/q`) stages the next prompt without touching the current run at all. And `/busy` configures what a plain **Enter** does while the agent is working — queue, steer, or interrupt — so your muscle memory stops accidentally killing 20-minute runs.

---

## Segmented Tool Batch Dispatch (Safe-Tool Parallelism)

A mid-July quality-of-life change to how tool batches execute: **safe operations (read / search / fetch / list / check) now run in parallel**, and one unsafe call in a batch no longer serializes the whole batch — dependent or risky calls wait, results merge in order. In practice: five independent 2-second lookups complete in ~2 seconds of wall time instead of ~10.

You don't configure anything — but you can *write for it*:

- Research, content, and file-analysis workloads benefit most — phrase multi-source questions so the agent can fan out reads ("check A, B, and C, then compare") instead of forcing sequential steps.
- Anything mutating (writes, sends, deploys) still serializes and still respects the approval layer ([Part 19](./part19-security-playbook.md)) — parallelism never bypasses approvals.

---

## Background Process Monitoring (`watch_patterns`)

### The Problem This Fixes

A huge chunk of agent work is "run a long thing and wait for a signal" — start a dev server and wait for `listening on port`, start a build and wait for a failure, run a test suite and wait for the summary line.

Before v0.9, the agent had two options:

1. Run the process in the foreground, block the agent loop, lose the ability to do anything else.
2. Run it in the background, then **poll** log output every few seconds, which is wasteful and introduces lag.

`watch_patterns` makes option 2 work correctly. You pass a pattern (or several) when you start a background process, and the agent gets a real-time event the moment the output matches — no polling.

### Basic Usage

Inside an agent session:

```
Start the dev server in the background. Watch for "listening on port"
to know it's ready, and for "EADDRINUSE" or "error" so you can surface
failures immediately.
```

Hermes uses the `terminal_run` tool with `watch_patterns`:

```json
{
  "command": "npm run dev",
  "background": true,
  "watch_patterns": [
    { "pattern": "listening on port \\d+", "label": "ready" },
    { "pattern": "EADDRINUSE|\\berror\\b", "label": "failure", "severity": "error" }
  ]
}
```

Each matched line gets delivered to the agent as an **event**, not a polled log snapshot — it's injected into the next turn like a tool result.

### Pattern Fields

| Field | Required | Description |
|-------|----------|-------------|
| `pattern` | yes | Python `re` regex, matched against each line of stdout/stderr |
| `label` | no | Human-friendly tag so the agent knows *which* watcher fired |
| `severity` | no | `info` (default), `warning`, or `error` — affects how the agent reacts |
| `max_matches` | no | Stop watching after N matches. Default: unlimited |
| `stop_process_on_match` | no | Kill the process when the pattern matches |

Want the *end* of the run instead of a matched line? Most long-running work can be declared with a simple completion signal: start the process with `notify_on_complete: true` (alongside any `watch_patterns`) and the agent receives one event when the process exits, carrying the full output. The goal loop [above](#goal--persistent-target-locking) understands both signals when it decides whether to park.

### Useful Recipes

#### Wait for a dev server to be ready, then run E2E tests

```json
{
  "command": "pnpm run dev",
  "background": true,
  "watch_patterns": [
    { "pattern": "Local:\\s+http://", "label": "ready", "max_matches": 1 }
  ]
}
```

Once `ready` fires, the agent knows it can proceed with the tests.

#### Fail fast on compilation errors

```json
{
  "command": "cargo build --release",
  "background": true,
  "watch_patterns": [
    { "pattern": "error\\[E\\d+\\]", "label": "rustc_error", "severity": "error", "stop_process_on_match": true }
  ]
}
```

#### Tail a log file forever, alert on specific lines

```json
{
  "command": "tail -F /var/log/app.log",
  "background": true,
  "watch_patterns": [
    { "pattern": "\\b5\\d\\d\\b", "label": "5xx", "severity": "warning" },
    { "pattern": "OOMKilled",      "label": "oom", "severity": "error" }
  ]
}
```

Pair this with a messaging platform gateway (Part 4 / Part 15) and you have a cheap production alerting pipeline with zero infrastructure.

### Inspecting What's Running

List background processes with active watchers — in-session:

```text
/background list
```

Each row shows the PID, command, uptime, watcher count, and recent match count. Click a row (in the dashboard) to tail live output.

### Killing a Background Process

In-session:

```text
/background kill <pid>
```

Or use the dashboard's Logs page to find the process and click the terminate icon.

---

## Pluggable Context Engine

Related-but-separate feature also shipped in v0.9.0: the context engine — the thing that decides what gets injected into each agent turn — is now a **pluggable slot** via `hermes plugins`.

You can swap in a custom context engine that:

- Filters memory differently (e.g. only inject memory entries tagged `@project:my-project`)
- Summarizes tool output before injection (cheap local model pre-pass)
- Injects domain-specific context (pulling from LightRAG, a private vector DB, your CRM, etc.)

### Minimum Custom Engine

`~/.hermes/plugins/my-context/plugin.yaml`:

```yaml
name: my-context
version: 1.0.0
provides:
  context_engine:
    entrypoint: my_context:build_context
```

`~/.hermes/plugins/my-context/my_context.py`:

```python
from hermes_agent.context import ContextBundle, DefaultContextEngine

default_engine = DefaultContextEngine()

def build_context(session, turn) -> ContextBundle:
    bundle = default_engine.build_context(session, turn)

    # Inject an extra block every turn
    bundle.extras.append({
        "role": "system",
        "content": "## Project context\n" + _load_project_context(session),
    })

    # Filter memory to the active project only
    active_project = session.metadata.get("project")
    if active_project:
        bundle.memory = [m for m in bundle.memory if m.tags.get("project") == active_project]

    return bundle

def _load_project_context(session):
    # Read a file, query an API, hit LightRAG — whatever you want.
    ...
```

Enable it:

```yaml
# ~/.hermes/config.yaml
context_engine: my-context
```

New sessions use the custom engine. Existing sessions keep the default until restart.

---

## `/compress <topic>` — Guided Compression

The existing context compressor (Part 6) now accepts a focus topic:

```text
You → /compress project migration to Fly.io
  Compressing 47 messages with focus: "project migration to Fly.io"
  Kept 6 messages verbatim, summarized 41 into 2 bullet blocks.
```

Without a topic, it runs with its default heuristics. With one, the summarizer preserves detail relevant to that topic and aggressively compresses the rest. Useful when you're 3 hours into a session and want to keep all the migration detail but jettison the 200 tool calls you ran to generate fixtures. `/compress` works in the CLI, the dashboard Chat tab, and the messaging gateway alike; modern sessions also compress automatically at their configured threshold (see [Part 6](./part6-context-compression.md)) before you ever have to do it by hand.

---

## `/goal` — Persistent Target Locking

v0.13 added `/goal` for the long-loop version of this problem: not "compress this context," but "keep working until this observable objective is done" — Hermes' take on the **Ralph loop** from Codex CLI, with an independent implementation. As of v0.19/v0.20 the command family is much richer:

```text
/goal Migrate the gateway to Google Chat, run checks, and leave a PR link.
```

After every turn an auxiliary **judge model** checks whether the goal is satisfied; if not, Hermes feeds a continuation prompt back into the same session automatically — until it's achieved, you pause/clear it, or the turn budget runs out (default **20 turns**, `goals.max_turns`; `/goal resume` resets the counter).

Today's command surface:

- `/goal <text>` (set), `/goal status` (or bare `/goal`), `/goal pause`, `/goal resume`, `/goal clear`
- `/goal draft <text>` — expand a plain-language objective into a structured **completion contract** (`outcome`, `verification`, `constraints`, `boundaries`, `stop_when`) so the judge only declares done with concrete evidence — or write the fields inline (`verify:`, `constraints:`, …)
- `/goal show` — review the active contract; contracts survive `/resume`
- `/subgoal <text>` — append acceptance criteria mid-loop; the goal isn't done until the original aim **and** every subgoal pass
- `/goal gate add <command>` — a deterministic **quality gate**: a shell command that must exit 0 before the judge may even run (3 retries / 5-min timeout per gate, then auto-pause)
- `/goal wait <pid> [reason]` / `/goal unwait` — park the loop on a background process (the judge also parks automatically when progress depends on a running `terminal(background=true)` watcher)

The judge is deliberately conservative (false "done" is rarer than false "continue"), user messages always preempt the loop, goal state persists in `SessionDB.state_meta` so `/resume` picks it up, and the continuation prompt is a plain user-role message — running a 20-turn goal costs the same cache-wise as 20 turns of chat. Wire the judge to a cheap fast model if you want: `auxiliary.goal_judge` in `config.yaml`.

Use `/goal` when the agent should continue across tool calls until an exit condition is satisfied. For multi-agent work, pair it with [Part 23's Kanban board](./part23-tenacity-stack.md); for one focused session, `/goal` is enough.

---

## What's Next

- **Save keys + streamline setup:** [Part 13 — Nous Tool Gateway](./part13-tool-gateway.md)
- **Expand reach:** [Part 15 — New Platforms (Teams, LINE, SimpleX, iMessage, WeChat, Android)](./part15-new-platforms.md)
- **Disaster recovery:** [Part 16 — Backup & Debug](./part16-backup-debug.md)
