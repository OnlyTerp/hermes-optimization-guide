# Part 23: Foundation + Tenacity Stack — Kanban, Goals, Handoff, Proxy, No-Agent Cron

*Hermes v0.13 "Tenacity" and v0.14 "Foundation" built the durable execution layer: a SQLite Kanban board, `/goal` persistent objectives, Checkpoints, and no-agent cron. Through the v0.17–v0.20 wave (current: **v0.20.4**, 2026.8.18, "The Herald") that layer did not get replaced — it got *wired deeper*: the dispatcher now lives inside the gateway, goals compile into completion contracts with quality gates, cron chains context, and worker lanes scale into swarms. The move is still: install lean, put durable work on Kanban, lock long sessions to `/goal`, keep deterministic jobs out of the LLM path, and let the board, not a parent process, be the source of truth.*

---

## 1. Treat Kanban as the Durable Execution Layer

`delegate_task` is still useful for short fork/join reasoning. It is not the right primitive for work that must survive restarts, wait for humans, retry after failures, or pass through multiple roles. Use **Hermes Kanban** for that:

```bash
hermes kanban init        # one-time: create kanban.db
hermes gateway start      # the gateway hosts the dispatcher (default)
hermes dashboard          # open the Kanban tab
```

Then create work from chat, CLI, or the dashboard:

```text
/kanban create "Audit the billing dashboard for stale Hermes v0.12 claims" \
  --assignee researcher \
  --workspace worktree
```

Why this matters:

| Old pattern | Board pattern |
|-------------|---------------|
| Parent subagent blocks until child returns | Board row persists; parent can move on |
| Failed child disappears into logs | Task blocks with comments, retry budget, and run history |
| One anonymous worker | Named assignees with durable identity |
| Context compression can erase the trail | SQLite board keeps the audit trail |
| Human feedback is awkward | Human comments/unblocks are first-class (`/kanban` works mid-run) |

**Two surfaces, one DB (`~/.hermes/kanban.db`, or per-board files under `~/.hermes/kanban/boards/<slug>/`):**

- **Agents** drive the board through the `kanban_*` toolset — `kanban_show`, `kanban_list`, `kanban_complete`, `kanban_request_review`, `kanban_request_changes`, `kanban_block`, `kanban_heartbeat`, `kanban_comment`, `kanban_attach`, `kanban_attach_url`, `kanban_attachments`, `kanban_create`, `kanban_link`, `kanban_unblock`. Dispatcher-spawned workers get these automatically via `HERMES_KANBAN_TASK`; orchestrator profiles enable the `kanban` toolset explicitly in config. Workers never shell out to `hermes kanban` — that keeps them working even when their terminal points at a remote sandbox.
- **You** drive it with `hermes kanban …`, `/kanban …` (from any chat, and *mid-turn* — the board lives outside the running agent), or the dashboard's Kanban plugin. Scripts and cron use the CLI with `--idempotency-key` so re-delivered webhooks never duplicate a card.

**The durable machinery (v0.19/v0.20 state):**

- **Dispatcher in the gateway.** `kanban.dispatch_in_gateway: true` is the default; every ~60s tick it reclaims stale claims, reclaims crashed workers (PID gone), promotes parent-gated tasks, and spawns assigned profiles. The standalone `hermes kanban daemon` is deprecated — run the gateway. Ready tasks with `--scheduled-at` wait until their time.
- **Heartbeats and reclaim.** Workers signal liveness with `kanban_heartbeat(note=...)`. A task running past the stale window (~4 h) with no heartbeat in the last hour gets reclaimed to `ready` for re-dispatch — so always heartbeat long operations. Crashed/spawn-failed tasks retry up to `kanban.failure_limit` (default 2) before auto-blocking with the last error, and repeated same-reason block→unblock loops route to `triage` instead of spinning.
- **Runs are per-attempt.** Every attempt writes a `task_runs` row: outcome, summary, structured `metadata` handoff, error. Downstream children read the parent's completion summary + metadata verbatim (`## Parent task results` in worker context) — the pattern for follow-ups is a **new child card via `--parent <done-card>`**, not reopening a done card.
- **Boards (multi-project).** One board per repo/domain — `hermes kanban boards create <slug>`, per-board DBs, workers pinned to their board via env. Tenants scope work *within* a board; boards are the hard isolation boundary.
- **Per-task model override.** `--model claude-opus-4.6 --provider anthropic` at create, or `hermes kanban set-model t_abcd …` later — the dispatcher spawns that worker with the pinned model. Combined with per-profile model config, run a frontier orchestrator and cheap workers.
- **Goal-mode cards.** `--goal` runs a card's worker in the `/goal` continuation loop inside that worker session — the judge re-checks the card body as acceptance criteria, and a max-turns exhaustion *blocks* the card for human review instead of exiting silently. Use for open-ended cards; skip for one-shot work.
- **Attachments & pinned skills.** Upload PDFs/images to a card (25 MB cap) and the worker's context lists absolute paths; pin specialist skills per task with `--skill <name>` (or `skills=[...]` from the `kanban_create` tool) without editing the assignee profile.

### The two traps everyone hits once

1. **The kanban toolset is opt-in for orchestrators.** Ordinary chats don't carry board tools, so a profile that *drives* the board needs `toolsets: [kanban]` explicitly — workers spawned *by* the board get theirs automatically. If your orchestrator "can't see the board," this is why.
2. **The default worker workspace is scratch — cleared on completion.** Files explicitly declared through `kanban_complete(artifacts=[...])` are copied into durable attachment storage; everything else in scratch dies. If the task produces files you want kept, pin a workspace: `--workspace dir:/absolute/path` (must be absolute — relative paths are rejected at dispatch) or `--workspace worktree` for git repos.

### Two board shapes worth stealing

- **Overnight autonomy:** stack the board in the evening, let workers grind while you sleep, review results with coffee. The real cost is one-time — tuning board conditions and worker prompts until unattended quality holds. Budget an evening of iteration, then it compounds.
- **GPU FIFO:** a capacity-1, strictly-ordered board serializes GPU-hungry jobs so multiple agents never OOM the same card. The board *is* the queue — no extra infrastructure.

Good board shapes: **solo dev** (triage → implement → review → PR), **research desk** (scouts gather, analyst synthesizes, writer drafts), **ops journal** (recurring checks append to the same service card over weeks), **fleet work** (one board per client/tenant; specialists claim their lane), **coding factory** (worker lanes write patches; Hermes reviews before completion — next section).

---

## 2. Add Worker Lanes Instead of Giant Prompt Swarms

Worker lanes are the SOTA orchestration pattern for coding-heavy Hermes setups. A lane is an assignee plus a spawn contract:

- **Hermes-profile lanes (paved path):** dispatcher spawns `hermes -p <profile>` with claim-scoped Kanban tools — the standard, fully supported route.
- **External CLI lanes (not yet paved):** wiring Codex / Claude Code / OpenCode CLIs as *direct* board workers is still a plugin job — the dispatcher's `spawn_fn` is pluggable, so a plugin can register one and wrap the CLI's exit code into `kanban_complete`/`kanban_block`. Until that exists, drive external CLIs from inside a Hermes-profile lane instead of assuming native board integration.
- **Review lanes:** human or agent reviewer gates "done" before dependent work unblocks (`kanban_request_review` → `kanban_request_changes`, or `/kanban request-review`).

Practical routing:

| Assignee | Use for | Completion posture |
|----------|---------|--------------------|
| `specifier` | Convert vague cards into acceptance criteria | Complete when spec is clear |
| `researcher` | Gather docs, issues, release notes | Comment sources, then hand off |
| `codex-worker` | Small isolated code edits | Block for Hermes/human review |
| `claude-code` | Larger multi-file refactors | Block for review + tests |
| `reviewer` | Verify diff, tests, risk | Complete or unblock with fixes |

Keep Hermes Kanban as the source of truth. Do not let a specialist CLI silently mark code as done just because it exited successfully — review lanes exist precisely so "exited 0" and "done" stay different statements.

### Scaling lanes into a swarm

When the work is a *campaign* — N parallel angles, one verifier, one bottom line — `hermes kanban swarm` builds the whole topology in one atomic shot:

```bash
hermes kanban swarm "Design a multi-region failover plan" \
  --workers researcher,architect,sre \
  --verifier reviewer --synthesizer writer
```

That creates a completed root/blackboard card, N parallel worker cards, a verifier card gated on all workers, and a synthesizer card gated on the verifier — the shared context ("blackboard") lives as structured JSON comments on the root card. The graph commits atomically: dispatchers and dashboard readers see either no swarm or the complete topology. Cost strategy to pair with it: per-profile models (frontier on the orchestrator, inexpensive workers — the workers are where the tokens go) with per-task `--model` overrides for quality-sensitive cards.

---

## 3. Use `/goal` for "Do Not Stop Until It Is Done"

`/goal` gives a session a persistent objective. After each turn an auxiliary judge checks whether the goal is satisfied; if not, Hermes feeds a continuation prompt back into the same session and keeps working until the goal is achieved, you pause/clear it, or the turn budget (default 20) runs out.

```text
/goal Refresh this guide to current Hermes, remove stale claims, run validation, and open a PR.
```

Use it for:

- Release-note sweeps where the agent might otherwise stop after the first file.
- Bug hunts that require reproduce → inspect → patch → test loops.
- Documentation refreshes with many cross-links.
- Long "make this production-ready" sessions where done means verified, not merely attempted.

Do not use `/goal` for vague aspirations like "improve the project." Give it an observable exit condition — and if the goal is vague, let Hermes draft it for you.

### Completion contracts: what "done" means, demonstrated

`/goal` now compiles your objective into an explicit **completion contract** — five optional fields (`outcome`, `verification`, `constraints`, `boundaries`, `stop_when`) — and the goal only closes when the contract's conditions are *demonstrated* with concrete evidence (a command result, file excerpt, test output), not claimed:

```text
/goal draft Migrate the auth service from session cookies to JWT
```

Hermes expands the one-liner into a full contract on the `goal_judge` auxiliary model, sets it, and shows it for review. Or write it inline:

```text
/goal Migrate auth to JWT
verify: pytest tests/auth passes
constraints: keep the /login response shape unchanged
boundaries: only touch services/auth and its tests
stop when: a DB schema migration is required
```

Mid-loop you can append criteria with `/subgoal <text>` (the judge must then satisfy every subgoal), inspect the contract with `/goal show`, and check your progress with `/goal status`. Contracts and subgoals persist in session state, so they survive `/resume` and compression.

### Quality gates and `pre_verify`: making "done" mechanical

A contract still trusts an LLM judge. A **quality gate** does not: `/goal gate add <command>` registers a deterministic shell command that must exit 0 before the goal can complete at all. Gates run *before* the judge each turn; a failing gate's output becomes the continuation prompt (so the agent iterates against the real failure), and repeated failures auto-pause the goal instead of burning budget.

Two more layers stack on top when you need them:

- **Automatic parking.** If progress is gated on a background process (CI run, long build), the judge returns a `wait` verdict and the loop parks — no judge calls, no turns consumed — until the process exits, then resumes with the result in hand. Manual override: `/goal wait <pid>`, `/goal unwait`.
- **`pre_verify` hooks.** The plugin hook system exposes a `pre_verify` gate that fires once per turn at the bounded verify gate after the agent edits code — a user/plugin policy check can keep the agent going ("run my linter first") instead of letting it stop.

Configure the judge to a cheap fast model (`auxiliary.goal_judge` in config) — the call is ~200 output tokens per turn. Details on contracts, subgoals, and gates live in the [Persistent Goals](https://hermes-agent.nousresearch.com/docs/user-guide/features/goals) docs, and the verification philosophy in [Part 26](./part26-moa-verification.md#2-verification--done-means-proven-not-claimed).

---

## 4. Checkpoints v2 Changes Your Risk Model

Hermes already had rollback-style safety. Checkpoints v2 remains the production baseline through v0.20:

- Real pruning prevents checkpoint directories from growing forever — `hermes checkpoints prune --retention-days N --max-size-mb N` enforces a size cap.
- Disk guardrails stop runaway snapshots from filling a VPS.
- Shadow repos are cleaned up instead of orphaned (legacy pre-v2 trees are quarantined under `legacy-<ts>/`).
- Patch/write syntax linting catches broken Python, JSON, YAML, and TOML immediately after file writes.

The management surface grew into first-class commands:

```bash
hermes checkpoints             # status overview
hermes checkpoints prune       # forced sweep: orphans, GC, size cap
hermes checkpoints clear       # nuke the base (asks first)
```

In-session: `/rollback [N] [file]` restores filesystem checkpoints (with a pre-rollback snapshot taken automatically), `/rollback diff <N>` shows what a checkpoint would change, and `/snapshot` (alias `/snap`) captures config/state snapshots you can restore later.

Recommended habit:

```text
Before a risky multi-file edit, confirm checkpointing is enabled.
After the edit, run tests.
If the direction is wrong, /rollback before trying a different strategy.
```

This is especially important when Kanban workers use git worktrees: checkpoints protect the worker workspace, while git protects the reviewable diff.

---

## 5. Use `no_agent` Cron for Watchdogs

Not every scheduled job needs an LLM. v0.13+ cron can run in **no-agent mode**: execute a script on schedule, deliver stdout if there is anything to say, and spend zero tokens — no model, no provider fallback, nothing at the inference layer.

Use no-agent mode for:

- Disk-space alerts.
- Uptime checks.
- Backup presence checks.
- "Did CI fail?" pollers.
- Cost/budget threshold pings.

Pattern (the script lives in `~/.hermes/scripts/`, then the job references it):

```bash
# ~/.hermes/scripts/disk-watchdog.sh  — the script IS the message:
df -h / | awk 'NR==2 && $5+0 > 85 {print "Disk usage high: "$5}'
```

```bash
hermes cron create "*/15 * * * *" \
  --no-agent \
  --script disk-watchdog.sh \
  --deliver telegram \
  --name "disk-watchdog"
```

Semantics that make it a watchdog:

- Script stdout (trimmed) → delivered verbatim as the message.
- **Empty stdout → silent tick, no delivery** — "only say something when something is wrong."
- Timeout/exit≠0 → an error alert is delivered, so a broken watchdog can't fail silently.
- `{"wakeAgent": false}` on the last stdout line → silent tick (same gate LLM jobs use for pre-check scripts).

Tell the agent once in chat ("ping me on Telegram if RAM is over 85% every 5 minutes") and it writes the script, schedules it, and wires the delivery itself via the `cronjob` tool (`no_agent=True`).

Keep LLM-backed cron for jobs that need judgment, synthesis, or chained context (`context_from` / `continuity` — Part 22 section 6). Use no-agent for deterministic checks.

---

## 6. Route Media to Models That Actually Understand It

Do not treat video or images as "just another attachment" on a text model. Hermes routes media to multimodal providers through its auxiliary slots (vision/video) — the exact model names rotate quarterly, so pick them with `hermes model` / the dashboard instead of hardcoding a SOTA name.

Use the `video_analyze` path for:

- Meeting recordings: action items, objections, decisions, timestamps.
- UI bug reports: "watch the repro video and identify the first broken frame."
- Security review: inspect screen recordings without dumping raw private media into memory.
- Support triage: classify customer clips before escalating to a human.

Model guidance: keep a **cheap multimodal** model in the vision/video auxiliary slots for routine media, and escalate specific frames/clips to a stronger model only when the judgment actually needs it. The `image_generate` tool adds image-to-image editing on edit-capable backends (pass a source image plus optional style references) — Part 22 section 9. For voice replies, TTS providers (Edge, OpenAI, Gemini, MiniMax, xAI custom voices) are configured under `tts:` — keep cloned/personal voices private-channel-only unless you have explicit consent and a clear disclosure policy.

---

## 7. Update Your Platform and Provider Mental Model

v0.14 pushed the plugin/provider surfaces further; v0.19/v0.20 widened them again. The current mental model:

- **Platforms.** The gateway ships ~35+ adapters now (a2a, webhooks, teams-meetings, wecom, qqbot, yuanbao, bluebubbles, homeassistant, … on top of the classics). Treat the *live* `/platforms` slash output as the count — "22+"/"25+" from older guide waves is stale.
- **Providers.** Model providers can ship as plugins; `hermes model` is the picker for everything (full live catalog, OAuth flows, keyless options like the OpenCode free tier). `hermes migrate` rewrites config when a provider you used is retired.
- **`hermes proxy`** still exposes OAuth-backed providers through an OpenAI-compatible local endpoint for Codex/Aider/Cline/Continue — keep it loopback-only.
- **Sandbox credentials.** For Docker-based terminal backends, the egress proxy ([Part 21](./part21-remote-sandboxes.md)) hands the sandbox *proxy tokens* instead of real keys; `hermes egress` manages the daemon. For SSH/Modal/Daytona the host's `~/.hermes/` state (including credential files) is synced into the sandbox — keep shared/other-provider secrets out of profiles aimed at those.
- **Secrets management.** `hermes secrets` pulls provider keys from an external vault at startup instead of `.env` — Bitwarden Secrets Manager is one documented source, and with the egress proxy it can source the real credentials at proxy-start time so rotation never touches your `.env`.

Operational rule:

1. Keep bundled/user plugins opt-in.
2. Keep project-local plugins disabled unless the repo is trusted.
3. Prefer native provider plugins over generic OpenAI-compatible shims when they expose provider-specific caching, reasoning, media, or auth.
4. Re-run `hermes plugins list` and `hermes model` after every major release; the live menus move faster than static docs.

---

## 8. Upgrade Checklist from v0.13 to v0.14

The v0.13→v0.14 durability layer is still the substrate everything newer builds on, so the checklist stays anchored here even as you land on v0.20:

```bash
hermes update --check
hermes backup
hermes --version
hermes doctor
```

Then verify the durability paths end to end:

- **Kanban:** `hermes kanban init` → `hermes gateway start` → create a task with `--assignee` → confirm the dispatcher spawns the worker and `kanban_heartbeat`/`kanban_complete` flow (watch with `hermes kanban watch`, review attempt history with `hermes kanban runs <id>`). Test one `hermes kanban swarm` campaign if you run swarms.
- **Goals:** run `/goal draft <something concrete>` in a disposable session, add a quality gate with `/goal gate add <command>`, and let the loop close out — this exercises the judge, the contract, and the turn budget together.
- **Checkpoints:** confirm checkpointing is on and `hermes checkpoints prune --retention-days 3 --max-size-mb 200` behaves; test `/rollback` on a scratch edit.
- **Cron:** create one `--no-agent` watchdog and one LLM job with `--continuity`/`context_from`; verify delivery targets resolve (home channel or explicit chat) and `hermes cron list` shows per-job model pins as intended.
- **Goal bot / Bots:** if you use the desktop app, the Bots tab is on by default — confirm your profiles appear as bots and a Routine schedules correctly.
- **Security posture:** `hermes security audit` (OSV supply-chain check) and `hermes egress status` if Docker sandboxes are in play.
- Re-check the newer paths too: `/learn`, `/journey`, and the v0.19/v0.20 desktop workflow — Part 22 sections 9/10 and Part 26 cover them.

If anything still needs the legacy install path (`pip install hermes-agent`, lazy deps so the box only carries the adapters it uses), that advice is unchanged from v0.14.

---

## 9. The Current Power Stack

For a serious 2026 (v0.20.4-era) Hermes deployment:

1. **Lean install with lazy deps** — `hermes update`/`pip install hermes-agent` resolves without pulling unused heavy adapters; Windows native (`%LOCALAPPDATA%\hermes`) is a first-class surface, not a beta.
2. **Gateway as the service** — it hosts the Kanban dispatcher, the cron scheduler, and bot-mode notifications in one process; multi-profile gateways are a documented pattern (each profile its own service unit).
3. **Kanban as the durable execution layer** — boards, runs, heartbeats, reclaim; swarm topologies for campaigns.
4. **`/goal` with completion contracts + quality gates** for "do not stop until proven done" sessions (and `--goal` cards on the board).
5. **No-agent cron for watchdogs + chained cron** (`context_from`, `continuity`) for anything that needs memory of its last run.
6. **Docker backend with egress (proxy tokens), or SSH/Modal/Daytona for beefy remote work** ([Part 21](./part21-remote-sandboxes.md)) — coding-agent lanes (Part 18) inside.
7. **Desktop app + Bots** for the human-comfort layer — same agent, same state, Bots tab, multi-terminal, memory graph.
8. **`hermes proxy`** for Codex/Aider/Cline/Continue using subscription auth, loopback-only.
9. **MCP with `trust: untrusted` + elicitation policy** for tools; strict boundaries.
10. **Checkpoints + `/rollback` + backups** (`hermes backup`) and **`hermes security audit`** on a schedule.

Models change quarterly — pick the current ones with `hermes model` and the hourly-refreshed catalog rather than hardcoding "the flagship" into this page.

If you only adopt one durability pattern, adopt Kanban. If you only adopt one v0.20-era pattern, adopt the egress-protected Docker sandbox from [Part 21](./part21-remote-sandboxes.md): every other pattern profits when the box that executes untrusted work holds no real credentials.