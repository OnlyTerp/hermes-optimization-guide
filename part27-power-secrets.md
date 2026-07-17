# Part 27: Power Secrets — The Field Manual the Docs Don't Give You

*Twenty-five non-obvious mechanics that separate people who fight Hermes from people who fly it. Distilled from the official Wingtips series (#1–#22 by @witcheer), Teknium's July guidance, and the highest-signal community field reports from July 2026 — verified against the real v0.18.x schema before inclusion.*

---

## Why this part exists

Every mechanic below is *documented nowhere or buried deep*, yet each one explains a class of "Hermes is broken / dumb / expensive" complaints. Read this part once and you'll stop hitting most of them. It's organized into five clusters:

1. [Context, memory & the prefix cache](#1-context-memory--the-prefix-cache) — why the agent "forgets" and what actually fixes it
2. [Cost mechanics](#2-cost-mechanics) — where tokens really go
3. [Profiles, files & identity](#3-profiles-files--identity) — which file is the brain, and when to split agents
4. [Kanban & operational traps](#4-kanban--operational-traps) — the opt-ins and absolute paths that bite everyone once
5. [The one-page cheat sheet](#5-the-one-page-cheat-sheet) — all of it, compressed

---

## 1. Context, Memory & the Prefix Cache

### Secret #1 — MEMORY.md is a frozen snapshot, not a live file

Writes to `MEMORY.md` hit disk **immediately**, but the memory block in the *system prompt* is **snapshotted at session start** and stays fixed for the whole session. This is deliberate — it keeps the provider's prefix cache warm (see [Part 20](./part20-observability.md)). The same applies to `USER.md`.

**Symptom:** you tell the agent a fact, it saves it, and ten turns later it acts like it never heard it.
**Fix when you need the fact *now*:** start a new session, or `hermes -c` to continue with a fresh prompt build. Tool calls that *read* the file always see live disk — only the injected prompt block is frozen.

### Secret #2 — Compression keeps first 3 + last 20 turns; the middle is where work dies

Automatic compression (the 🗜️ icon) kicks in around **50% of the context window**. It keeps roughly the **first 3 turns and the last 20**, and summarizes the middle. If the agent "redoes work," the details it needed were in the summarized middle. Three real levers in `config.yaml` (hot-reloaded on a running gateway):

```yaml
compression:
  protect_last_n: 30          # keep more recent turns uncompressed
auxiliary:
  compression:
    provider: openrouter
    model: google/gemini-3-flash   # summarize on a cheap model, not your primary
model:
  context_length: 200000      # raise the ceiling so compression fires later
```

Full compression tuning: [Part 6](./part6-context-compression.md).

### Secret #3 — Compaction is a structured brief, not amnesia

When compaction runs, it doesn't just truncate — it fills fixed slots: **goal / constraints / progress / key decisions / relevant files / next steps / critical context**. Raw turns stay in `state.db` and remain findable with `session_search`.

**Practical consequence:** *write for the compactor*. State goals and decisions in plain declarative sentences ("Decision: we're using Postgres, not SQLite, because X") so they map cleanly into slots. Facts that must **never** drop belong in `MEMORY.md`, not in chat.

### Secret #4 — Switching models mid-session resets the prompt cache

The cache key includes the model. Switch models mid-thread and the next turn re-reads your **entire history at full input price**. Same for rotating credentials (see Secret #10). If a long session needs a different model for one step, **delegate to a subagent** (own context, own cache) instead of ping-ponging `/model`.

### Secret #5 — `/steer`, `/queue`, `/busy`: redirect without burning the run

- `/steer focus on the auth module first` — lands **after the current tool call**, inside the same turn. Not a new turn, no restart.
- `/queue` (`/q`) — stages the next prompt without touching the current run.
- `/busy` — configures what a plain Enter does while the agent is working: queue, steer, or interrupt.

Details: [Part 14](./part14-fast-mode-watchers.md#steer-queue-and-background-turns).

### Secret #6 — Third-party context files tax every single prompt

Project rule files inject on **every prompt**, and the discovery order is first-match-wins: `.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`, with a **20k-char cap** (head+tail truncation). Two traps:

- A `.hermes.md` **silently shadows** `AGENTS.md` — no warning, your carefully-written AGENTS.md just stops loading.
- Tools you install can drop their own fat context files. The infamous case: **Camofox's `AGENTS.md` injects ~22k chars into every prompt** if it sits in your cwd. Audit `ls -la` for rule files after installing anything.

`SOUL.md` always loads separately from `~/.hermes/SOUL.md` — identity is never subject to project-rule shadowing.

---

## 2. Cost Mechanics

### Secret #7 — The messaging-gateway token tax (the biggest one)

Talking to Hermes through Telegram/Discord carries **~15–20k tokens of tool definitions per turn**. The same work through the **CLI costs ~6–8k**. Same agent, same result, 2–3× the context overhead.

**The rule: CLI for heavy work, messaging for control.** Kick off long jobs from the terminal (or Kanban), then steer and receive results on your phone. Full cost math: [Part 20](./part20-observability.md#the-gateway-token-tax-cli-for-heavy-work-messaging-for-control).

### Secret #8 — Default cheap, escalate deliberately

The pattern high-volume users converge on: default to a **DeepSeek-Flash-class model** (~$0.14/M input) and reach for frontier models only when actually stuck. Community claim that holds up in practice: ~80% of tasks get the same result at ~30× lower cost. Combine with persistent memory + `/learn` skills and similar tasks get measurably faster and cheaper over weeks — the agent amortizes its own learning.

### Secret #9 — Benchmark the stack, not the model

July's WolfBench numbers: the **same model** (GPT-5.6 Sol, max reasoning) scored 86.7% on Codex at ~$90/run vs 84.5% on Hermes at ~$173/run — Hermes used ~2× the tokens for the same brain. Corollaries:

- On Hermes, **Terra** lands ~3.6 points behind Sol at **~44% lower cost** — usually the right trade.
- High-reasoning models **create busywork** (one user watched Sol hash every test file and review every hash — 347 redundant tests). Cap `/goal` scope, use verification contracts ([Part 26](./part26-moa-verification.md)), and never pair a Sol parent with Sol children — the busywork compounds exponentially.

### Secret #10 — Credential pools ≠ fallbacks, and rotation costs a cache miss

You can register **multiple keys per provider**; Hermes rotates on rate-limit/quota before falling back to another provider:

```bash
hermes auth add openrouter --api-key sk-or-...
hermes auth list
```

Pool exhausts first, then `fallback_providers` kicks in — and **every fallback entry needs both `provider` and `model`** fields. Put a local model last (`provider: custom` → llama.cpp/vLLM) as your outage floor. One warning: each rotation is a **prefix-cache miss** — the full history is re-read at full price. Nous Portal's single OAuth usually needs no pool.

### Secret #11 — MoA is nearly free *at the turn level*

Measured: single Opus turn ~27.9k tokens / ~$0.14 vs a full 4-reference + aggregator MoA turn ~28.6k / ~$0.15. Why: the system prompt and tool schemas dominate the bill, and reference models run on **stripped context**. And it works — Opus+GPT-5.5 MoA benched 0.8202 vs 0.7607/0.7412 alone. Still 5 calls/turn (scales with session length), so save it for genuinely hard problems. See [Part 26](./part26-moa-verification.md).

---

## 3. Profiles, Files & Identity

### Secret #12 — Which file is the brain

| File | Role |
|------|------|
| `SOUL.md` | Who the agent **is** — system prompt slot #1, replaces the default identity |
| `USER.md` | Who **you** are (snapshotted at session start, like MEMORY.md) |
| `MEMORY.md` | Facts about the work; reloads every session |
| Project rules | First-match-wins: `.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules` |

### Secret #13 — A profile is a whole separate agent

`hermes profile create <name>` gives you an agent with its **own memory, sessions, skills, and bot token** — it knows nothing about your main agent. Two architectures, pick deliberately:

- **One agent on many platforms** = **one profile, many gateways** (shared SOUL/memory across Telegram + Discord + Desktop).
- **Profile per domain** ("profiles as rooms": coder / research / private / cron) = strangers by design — no cross-contamination of memory or skills. Clone a starting point with `hermes profile create new --clone-all` (without the flag you get a blank agent).

**Boundary warning:** profiles isolate *Hermes state*, **not the filesystem** — every profile runs as the same OS user. For real isolation use Docker, SSH, or OS ACLs ([Part 19](./part19-security-playbook.md)).

### Secret #14 — The "me layer" pattern (personalization beyond USER.md)

Power users maintain a small directory of markdown files — beliefs, values, strategy, decisions, ideas, preferences, active focus — that `SOUL.md` instructs the agent to explore, promoting stable findings into `USER.md`/`MEMORY.md`. Pair it with a nightly cron that ingests the day's sessions (and optionally your own posts) into the layer, dedupes, and compresses. It's the difference between an agent that knows your name and one that knows your *judgment*.

### Secret #15 — Supervised self-improvement

```text
/memory approval on
/skills approval on
```

The agent keeps learning, but every new memory write and skill creation waits for your yes. This is the right default for shared or production agents — silent memory writes are how one wrong "fact" compounds into every future session.

### Secret #16 — `/learn` output needs a haircut

`/learn <dir|url|workflow>` is the fastest path to procedural memory, but it routinely writes **123–202-char skill descriptions** — and descriptions load **every session**, forever. After every `/learn`: open the generated `SKILL.md`, trim the description to **≤60 chars**, and set the author before sharing. Also: check the **built-in tools first** — memory, web search, browser control, cron, and sub-agents are native; don't install a skill for something the agent already has.

---

## 4. Kanban & Operational Traps

### Secret #17 — `toolsets: all` does NOT include kanban

The Kanban toolset is **opt-in** (so chat isn't cluttered with board tools). Any profile that *drives* a board needs it explicitly:

```yaml
toolsets:
  - kanban
```

Workers spawned *by* the board already get their tools. This one silently breaks every "orchestrator can't see the board" setup.

### Secret #18 — The default Kanban workspace is scratch — your output gets wiped

Worker workspaces are **cleared on completion** by default. To keep the output:

```bash
hermes kanban create "your task" --workspace dir:/absolute/path
```

And it must be **absolute** — a relative path is accepted at create time and **rejected at spawn time**. Two more board patterns worth stealing: overnight autonomous coding runs (the real cost is one-time board-condition + prompt tuning), and using a capacity-1 ordered board as a **GPU FIFO** so multi-agent GPU jobs never race. More in [Part 23](./part23-tenacity-stack.md).

### Secret #19 — Gateway dies at logout on headless boxes

A user-service gateway is killed when your login session ends. On any headless VPS:

```bash
hermes gateway install
sudo loginctl enable-linger $USER
# or go system-wide: sudo hermes gateway install --system
```

### Secret #20 — Disk fills are not logs

The three unbounded growers to watch: **`state-snapshots/`** (750MB+ observed), **per-run cron output** (1500+ files), and **host-piped stdout**. Run the disk-cleanup plugin and watch those three before you get "no space left on device."

### Secret #21 — Prune state.db before it drags

`~/.hermes/state.db` auto-prune is **off by default**. Hundreds of sessions ≈ 10–15MB; you'll feel drag near **~384MB / ~1000 sessions** (heavy 24/7 users have hit 900MB+):

```bash
hermes sessions prune        # ended sessions only, never active ones
# or set-and-forget: sessions.auto_prune: true
```

### Secret #22 — Session export, with redaction

```bash
hermes sessions export --format md    # or qmd | html
# --redact hides keys/tokens; --session-id <id> for one session
```

md/qmd exports land in `~/.hermes/session-exports` with a manifest. Always `--redact` before sharing anywhere.

### Secret #23 — Telegram group silence is a BotFather default

Group Privacy Mode defaults **ON**, so your bot only sees @mentions and `/` commands — plain group messages never arrive. Fix: BotFather → `/setprivacy` → Disable, then **remove and re-add** the bot to each group (the change doesn't apply to groups it already joined). Details: [Part 4](./part4-telegram-setup.md).

### Secret #24 — Background computer use (macOS)

```bash
hermes computer-use install
# grant Screen Recording + Accessibility to CuaDriver
hermes -t computer_use chat
```

The agent clicks and types in the background while **your cursor stays put**; destructive actions wait for approval. See [Part 25](./part25-nvidia-local.md).

### Secret #25 — Keep Hermes in the loop

Official guidance from Teknium: don't demote Hermes to a shell that launches another agent and exits. Routing through a second agent as the "real" brain **breaks the trace** — memory stops accumulating, `/learn` sees nothing, plugins go blind. Run models *inside* Hermes; delegate to coding CLIs as **workers** ([Part 18](./part18-coding-agents.md)), with Hermes as the durable control plane.

---

## 5. The One-Page Cheat Sheet

Print this. Tape it somewhere.

1. **CLI for heavy work; messaging for control** — the gateway tool-definition tax is real (15–20k vs 6–8k tokens).
2. **Default cheap (DeepSeek-Flash-class); frontier only when stuck.**
3. **MEMORY/USER are snapshotted at session start** — need a fact live now → new session or `hermes -c`.
4. **`/steer` mid-run; `/queue` next; `/busy` configures Enter.**
5. **`/memory approval on` + `/skills approval on`** for supervised self-improvement.
6. **After `/learn`, trim the skill description to ≤60 chars.**
7. **Profiles for domain isolation; one profile + many gateways for one brain on many platforms.**
8. **`toolsets: [kanban]`** for any board-driving profile; **`--workspace dir:/abs`** or your output is wiped.
9. **Credential pools ≠ fallbacks; every rotation costs a full-history cache miss.**
10. **Model switch mid-thread = full re-read; use a subagent instead.**
11. **Compression levers: `protect_last_n`, cheap `auxiliary.compression` model, raise `context_length`.**
12. **Compaction writes a brief** — state goals/decisions in plain language so they survive it.
13. **`loginctl enable-linger`** on every headless VPS gateway.
14. **Prune `state.db`** past ~384MB / ~1000 sessions.
15. **Disk watch: `state-snapshots/`, cron outputs, piped stdout — not logs.**
16. **BotFather privacy off + remove/re-add the bot** for Telegram groups.
17. **Docker with internal-only network + an action ontology** for production security ([Part 19](./part19-security-playbook.md)).
18. **External spend kernel** for any agent that touches money ([Part 19](./part19-security-playbook.md#external-spend-kernels-when-the-agent-touches-money)).
19. **High-reasoning models invent busywork** — verification contracts, and never Sol-parent + Sol-child.
20. **Terra over Sol on Hermes when cost matters; Luna for the daily lane.**
21. **Anthropic subscriptions don't work natively** — use API keys, or orchestrate a Claude terminal instead.
22. **Keep Hermes in the loop** — outsourcing the brain kills memory, trace, and plugins.
23. **A remote Desktop backend means code runs on the server** — want local files, run local.
24. **MoA is nearly free per turn** (system prompt dominates) — but save it for genuinely hard calls.
25. **Watch third-party `AGENTS.md` files** — one stray 22k-char rule file taxes every prompt you send.

---

## What's Next

- [Part 20: Observability & Cost](./part20-observability.md) — measure the tax before and after you fix it
- [Part 19: Security Playbook](./part19-security-playbook.md) — the seven layers + spend kernels these secrets reference
- [Part 26: MoA & Verification](./part26-moa-verification.md) — the verification contracts that tame busywork
- [Part 23: Tenacity Stack](./part23-tenacity-stack.md) — Kanban patterns beyond the two traps

---

*Sources: Hermes Wingtips #1–#22 (@witcheer), Teknium's July 2026 posts, and community field reports from 2026-07-09 → 17 — cross-checked against the v0.18.x schema. When a claim couldn't be verified against real behavior, it didn't make this page.*
