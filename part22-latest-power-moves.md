# Part 22: Latest Power Moves — Curator, TUI, Plugins, Context Files

*If you already know Hermes but missed the earlier waves, this part is the "what's daily-driver-worthy right now" pass, current through **v0.20.4 (2026.8.18, "The Herald")**. For the durable execution layer — Kanban, `/goal` completion contracts, Checkpoints, no-agent cron, worker lanes and the Kanban swarm — go next to [Part 23](./part23-tenacity-stack.md). The everyday moves from v0.15 "Velocity" and v0.16 "Surface" — `/undo [N]`, the default-interface choice, the fuzzy model picker, and leaner default skills — are in [section 8](#8-newer-power-moves-v015--v016); the v0.17 "Reach" / v0.18 "Judgment" quick hits are in [section 9](#9-newer-power-moves-v017--v018). The newest v0.19/v0.20 "Herald" wave — desktop-app workflow, live subagents, MCP elicitation, automation blueprints and the cron wizard — is in [section 10](#10-newest-power-moves-v019--v020-the-herald). For the native desktop story and the run-it-local stack, see [Part 24](./part24-desktop-app.md) and [Part 25](./part25-nvidia-local.md). The big v0.18 ideas — Mixture-of-Agents, verification, `/learn`, `/journey` — get their own deep dive in [Part 26](./part26-moa-verification.md).*

---

## 1. Turn On Curator Before Your Skill Library Becomes Noise

Agent-created skills are valuable until the library fills with duplicates, stale CLI flags, and one-off task notes. Curator is the maintenance loop that keeps the library honest — and it has been stable through the v0.17–v0.20 releases.

```bash
hermes curator run --dry-run
hermes curator run
hermes curator enable
```

Use it like this:

- Pin production runbooks and skills you personally rely on.
- Let Curator archive weak/duplicate agent-created skills.
- Run a dry-run after upgrades or big workflow changes.
- Restore archived skills instead of recreating them from memory.

Curator should prune skills, not decide project policy. Put durable project rules in context files.

> **Still true through v0.20:** the Curator's LLM-driven consolidation pass is **opt-in** — routine curation (archiving duplicates, pruning stale skills) costs zero tokens by default. Turn consolidation on with `curator.consolidate: true` in config, or run it once on demand with **`hermes curator run --consolidate`**. The Curator never auto-deletes, respects pinned skills, and skips skills referenced by any cron job. Pair with `/journey` ([Part 26](./part26-moa-verification.md#3-learn-and-journey--self-improvement-you-can-see)) to audit the memory side too.

---

## 2. Use the TUI as a Daily Driver (or the Desktop)

`hermes --tui` is the terminal power surface — and the desktop app's Chat is the same agent with a GUI. Choose the surface that fits the moment; they share state.

```bash
hermes --tui
```

Habits that pay off:

- `/steer <constraint>` when the agent is mid-run but drifting.
- `/queue <next task>` for dependent follow-ups.
- `/background <prompt>` (`/bg`) for independent research or monitoring.
- `/resume`, and delete stale sessions from the picker with `d`.
- `/reload` after editing `.env`; avoid restarting the session just to pick up keys.
- Toggle `/mouse` if your terminal/ConPTY injects phantom mouse events.
- `/model` opens the fuzzy filterable picker (section 8) — type part of a model name to narrow.

If the dashboard Chat tab is enabled, it embeds the same TUI through a PTY, so improving your TUI workflow also improves the browser workflow.

---

## 3. Clean Up Context Files

Hermes reads common agent instruction files, including `.hermes.md`, `AGENTS.md`, `CLAUDE.md`, `SOUL.md`, and `.cursorrules`.

Use them for different jobs:

| File | Put this there | Avoid |
|------|----------------|-------|
| `.hermes.md` | Hermes-specific repo workflow, commands, approval expectations | Generic company policy |
| `AGENTS.md` | Cross-agent coding instructions | Personal style/personality |
| `SOUL.md` | Tone, boundaries, durable preferences | Build commands and API docs |
| `.cursorrules` | Editor/Cursor compatibility | Secrets or credentials |

Best pattern:

1. Keep root instructions short.
2. Add subdirectory-specific files only where behavior changes.
3. Store secrets in `.env` or provider auth stores, never context files.
4. Use skills for procedures, memory for facts, and context files for policy.

---

## 4. Use Plugins for Integrations, Not One-Off Scripts

Plugins are the right abstraction for tools, hooks, slash commands, dashboard tabs, gateway platforms — and, since the desktop wave, desktop-app panes and commands too.

```bash
hermes plugins list
hermes plugins enable observability/langfuse
hermes plugins enable spotify
```

Bundled plugins worth reviewing:

| Plugin | Why enable it |
|--------|---------------|
| `observability/langfuse` | Trace LLM/tool calls without writing custom hooks |
| `spotify` | Native playback, queue, search, playlists, devices |
| `google_meet` | Join calls, transcribe, speak, and generate follow-ups |
| hermes-achievements | Dashboard achievements from session history |
| image-gen backends | Extra OpenAI/Codex/xAI image routes |

Two plugin ecosystems now exist:

- **Agent plugins** (`hermes plugins list`) — backend hooks, platforms, toolsets.
- **Desktop plugins** — single ESM files in `$HERMES_HOME/desktop-plugins/<id>/plugin.js` that register panes, command-palette commands, key bindings, status-bar items, and themes in the desktop app (see [Part 24](./part24-desktop-app.md)).

Security posture:

- Plugins are disabled by default; keep it that way.
- Enable only trusted bundled/user plugins.
- Enable project-local plugins only for trusted repos.
- Treat hooks as code execution, not "just configuration."
- For untrusted MCP servers, use the per-server `trust: untrusted` tier instead of a plugin — every write-capable tool then routes through the approval surface (full detail in Part 19, and section 10 below for MCP elicitation).

---

## 5. Split Main and Auxiliary Models

The dashboard, desktop Settings, and `hermes model` all expose auxiliary model configuration. Use it.

| Job | Good default |
|-----|--------------|
| Main agent | Your preferred coding/reasoning model |
| Compression | Cheap fast model |
| Vision | A model with actual image capability |
| Session search | Cheap summarizer/search-capable model |
| Title generation | Cheapest reliable model |
| Curator | Cheap model with enough context for skill review |

This avoids spending premium tokens on titles, compression, and housekeeping. Verify the current auxiliary slot names against `hermes config` — the live menus move faster than static docs.

---

## 6. Chain Cron Jobs Instead of Repeating Context

Cron is no longer just "run this prompt every morning." The current toolset:

- **Per-job model pins** — a job can pin its own model and reasoning effort, independent of your chat model (`hermes cron create … --model <name> --reasoning-effort high`, or the dashboard/desktop cron editor). `cron.model` in config sets a fleet default for every unpinned job; when *neither* is set and your global default later changes, the job **fails closed** and skips rather than silently spending on a different provider. Pin explicitly for anything recurring.
- **Per-job `workdir`** for project-aware jobs (loads that repo's `AGENTS.md`/`CLAUDE.md`/`.cursorrules`).
- **Per-job `enabled_toolsets`** to shrink tool/context overhead.
- **`context_from`** to feed one job's output into the next (chained pipelines).
- **`continuity`** so a recurring job sees its *own* previous output each run and dedupes instead of re-reporting the same news.
- **Webhook direct delivery** for zero-LLM notifications, and `[SILENT]` for quiet monitors.

Example chain (via the `cronjob` tool — jobs live in `~/.hermes/cron/jobs.json`, not in config.yaml):

```python
# Job A: collect
cronjob(action="create", name="collect-build-status",
        schedule="*/30 * * * *", workdir="~/projects/app",
        enabled_toolsets=["terminal"],
        prompt="Run the build status check and summarize failures only.")

# Job B: notify — receives A's latest output as context
cronjob(action="create", name="notify-build-status",
        schedule="*/30 * * * *", context_from=["collect-build-status"],
        deliver="telegram",
        prompt="Notify only if the upstream job found failures.")

# Job C: continuity — same job remembers what it already reported
cronjob(action="create", name="agent-tooling-scout",
        schedule="every 6h", continuity=True,
        prompt="Scan HN + arXiv for new agent-tooling papers; report only items NOT in your previous output.")
```

The dashboard / desktop cron editors are effectively the **cron wizard** now: fill the form (schedule, prompt, per-job model, delivery), and the same underlying scheduler does the rest. For full templates, `/blueprint` is the shortcut — see section 10.

---

## 7. Upgrade Checklist for Existing Installs

If you are moving an older setup forward, or just did `hermes update`:

```bash
hermes update --check
hermes backup
hermes --version
hermes doctor
```

Then:

1. Open the dashboard or desktop Settings; check main + auxiliary models.
2. Enable only the plugins you actually need (`hermes plugins list`).
3. Run `hermes curator run --dry-run`.
4. Test one gateway message, one tool call, one skill, and one cron job — ideally one chained with `context_from` / `continuity`.
5. Verify `hermes egress status` if you use Docker sandboxes (Part 21).
6. Review [Part 19](./part19-security-playbook.md) before enabling broad platform access.
7. Then run the [v0.13 → v0.14 Foundation checklist](./part23-tenacity-stack.md#8-upgrade-checklist-from-v013-to-v014) — the durability layer still applies verbatim; Part 23 builds on it.

---

## 8. Newer Power Moves (v0.15 → v0.16)

The Velocity and Surface releases added a handful of small things you'll reach for daily — all still current in v0.20:

### `/undo [N]` — take back turns

Made a mess, or sent the wrong prompt? `/undo` removes the last user/assistant exchange; `/undo N` backs up N user turns (default 1) and re-prompts — the session is rolled back so you can edit and resend instead of retyping.

```text
/undo        # undo the last turn
/undo 3      # undo the last three turns
```

Works the same in the CLI, TUI, and messaging surfaces.

### Pick your default interface

`hermes chat` can default to either the **CLI** or the **TUI** — set it once and override per-invocation with `--cli`:

```bash
hermes config set interface tui   # or: cli
hermes chat --cli                 # one-off override
```

The TUI also unified its model switcher under `/model` and added a live Sessions overlay and session switcher.

### The fuzzy model picker is everywhere

Desktop, web, TUI, and CLI share the same **fuzzy model picker**. Multi-endpoint providers are grouped, and the catalog **refreshes hourly** (`model_catalog.ttl_hours: 1`), so new models appear without waiting for a Hermes release. Just type part of a name in `hermes model` (or `/model`) and pick.

### Leaner default skills

v0.16 trimmed the built-in skill set so the agent isn't carrying dead weight. Several skills became **native plugins** or moved to **MCP** (for example, Spotify is now a native plugin; Linear is `hermes mcp install linear`), others moved to **optional**, and an `environments:` relevance gate keeps irrelevant skills from loading. Curator can now prune **built-in** skills too, not just agent-created ones.

If you relied on a skill that disappeared, check whether it's now a plugin (`hermes plugins list`) or an MCP server (`hermes mcp ...`) before recreating it.

### Free, instant session search

`session_search` runs locally for free — searching your own history no longer burns tokens. Combine it with desktop's search-by-id (see [Part 24](./part24-desktop-app.md)) to jump back into past work fast.

### Scale durable work into a swarm

When one board outgrows a single worker, `hermes kanban swarm` turns Kanban into a durable multi-agent topology (root/blackboard card, parallel workers, gated verifier, synthesizer). Full details in [Part 23](./part23-tenacity-stack.md#2-add-worker-lanes-instead-of-giant-prompt-swarms).

> **Security note:** v0.15 added **Brainworm/promptware defenses** against malicious instructions hidden in tool output. Keep them on, and read [Part 19](./part19-security-playbook.md) before wiring up untrusted inputs.

---

## 9. Newer Power Moves (v0.17 → v0.18)

The Reach and Judgment releases added another round of daily drivers. The headline features (MoA, verification, `/learn`, `/journey`, background fan-out) get their own part — [Part 26](./part26-moa-verification.md) — but these small ones deserve muscle memory:

### `/prompt` — compose long prompts in a real editor

Opens `$EDITOR` so you can write a multi-line, markdown-formatted prompt and have it queued as your next message. The single best QoL command for anyone writing detailed task briefs (`/compose` is an alias).

### `/reasoning full` — uncap thinking for a session

When a session hits something genuinely hard, `/reasoning full` removes the thinking budget cap for that session. Cheaper than switching to a bigger model for one gnarly step.

### `/timestamps` and a timestamped `/history`

Toggle inline timestamps on turns and see when things actually happened in `/history` — essential when auditing long autonomous runs.

### In-place compaction (no more broken `@session` links)

Context compression now rewrites the session **under the same session id** by default, instead of rotating to a new one. Long-running sessions keep their identity, so `@session` references, integrations, and desktop links stop silently breaking.

### `image_generate` learned image-to-image editing

Pass an input image (`image_url`) plus optional style references (`reference_image_urls`) and a transform prompt — restyle screenshots, blend product shots, iterate on drafts — across every edit-capable backend (FAL, OpenAI `gpt-image-2`, xAI Grok Imagine, Krea, OpenRouter Image API), from any surface. Omit the image and it's plain text-to-image.

### `memory` batch operations

The `memory` tool applies multiple add/update/delete operations atomically in one call. Bulk cleanups (or a `/journey` pruning session) are one round-trip instead of ten.

### Automation Blueprints instead of raw cron

Parameterized automation templates that render as a dashboard form, a slash command, or a plain conversation (`/blueprint morning-brief`, or "set up my daily briefing for 8am"). A blueprint is just a skill with a `metadata.hermes.blueprint` block — slice the catalog with bare `/blueprint`, fill slots inline with `/blueprint <name> slot=value`. Use them for anything you'd previously hand-rolled; keep raw deterministic no-agent cron for the watchdogs in [Part 23](./part23-tenacity-stack.md#5-use-no_agent-cron-for-watchdogs).

### Blank Slate setup

A minimal-agent onboarding mode: start from nothing and opt in tools one at a time. The right default for compliance-sensitive or locked-down machines.

---

## 10. Newest Power Moves (v0.19 → v0.20, "The Herald")

v0.19 and the v0.20 "Herald" release (current: **v0.20.4**, 2026.8.18) are the wave this guide's older parts were written before. The headline banner — streaming voice, A2A v1.0, outbound webhooks, grounded citations — isn't the interesting part for daily driving; these are:

### The desktop app is a first-class surface

Windows, macOS, and Linux are all fully supported now — the old "native Windows beta" framing is stale. The app shares the same config, sessions, skills, and memory as the CLI; it drives a headless `hermes serve` backend. The workflow wins:

- **Bots tab** — every [profile](./part24-desktop-app.md) shows up as a named bot with an avatar, its own canonical chat, and **Routines** (recurring tasks backed by cron). Bots @-mention each other in any chat and deliberate in group chats; "a Bot IS a profile," so a Bot roster is just your profiles wearing faces.
- **Projects** — the sidebar discovers local repos, and the Git worktree/review pane (branch, diff scopes, stage/commit/PR) turns the app into a real coding surface.
- **Multi-terminal** — Ctrl+` toggles the terminal, Ctrl+Shift+` spawns another; the shells persist (scrollback and running processes intact) while hidden, and you can send terminal output *into the composer*.
- **Cmd+K / Cmd+P** — one command palette for every app action: jump to a session, switch model/theme, spawn a terminal, export a profile (`.tar.gz`, keys stripped).
- **Memory Graph / Star Map** — `/journey` in-chat (aliases `/learning`, `/memory-graph`) opens an interactive, filterable constellation of what the agent learned, with edit/delete right in the panel.

Command palette habits aside: pick a model in the composer (sticky per device, never touches your default), watch the context-meter popover, flip per-session YOLO from the status bar.

### Live-viewable subagents

`delegate_task` children are no longer a black box: the TUI's `/agents` (alias `/tasks`) overlay shows a **live subagent tree** with kill/pause controls, per-branch cost/token/file rollups, and turn-by-turn history — so you can watch a fan-out work, catch a child burning tokens, and stop it mid-flight. Background fan-out details stay in [Part 26](./part26-moa-verification.md#4-background-fan-out--delegate-a-fleet-and-keep-working).

### MCP elicitation

MCP servers can now ask *you* for structured input mid-tool-call (the `elicitation/create` protocol). Hermes routes **form-mode** elicitations through the existing approval surface — a prompt in the CLI/TUI, approval buttons on Telegram/Slack — so the request reaches you wherever the session lives. **URL-mode** elicitations are declined as unsupported. Enabled by default per server; configure under `mcp_servers.<name>.elicitation` (`enabled`, `timeout`), and pair with `trust: untrusted` for servers you don't fully control.

### Automation blueprints + the cron wizard

Schedules got two highways: the dashboard/desktop **cron editors** now let you pin a per-job **model and reasoning effort** (the "cron wizard" — fill the form, Hermes writes the job), and **`/blueprint <name>`** spins up full parameterized automations from a skill-based template catalog (`/blueprint` bare lists it; `/blueprint morning-brief time=08:00` fills slots inline). `/suggestions` reviews automations Hermes proposes from your patterns. Raw YAML hand-rolling is obsolete — jobs are JSON managed through the `cronjob` tool, `hermes cron edit`, or `/cron`.

### `/learn` on demand, `/journey` as memory hygiene

`/learn <what>` distills a reusable skill from a directory, a URL, or the workflow you just walked through — on the CLI, messenger, TUI, or dashboard. `/journey` shows the growth: timeline of learned skills + memories (Star Map on desktop). Both are Part 26's deep topic; the power move here is simply *habit* — `/learn` after a novel procedure, `/journey` + Curator monthly.

### Checkpoints and snapshots in chat

`/rollback` restores filesystem checkpoints and `/snapshot` (alias `/snap`) captures state snapshots; `hermes checkpoints` manages the shadow store (prune, size caps) from the CLI. For the durable-work layer at large — goal contracts, Kanban cards, no-agent cron — that is Part 23's job.

### Voice, wake words, and A2A (the Herald headliners)

Streaming TTS with barge-in, wake words ("Hey Hermes"), and A2A v1.0 (agent-to-agent protocol, both directions) are the release's public faces — see the voice-mode and A2A guides in the docs. The practical hook for most setups: Agent-to-Agent lets other agents reach your Hermes, and reach out from it, as a first-class messaging surface.

> **Platform count check:** the gateway now ships ~35+ adapters (A2A, webhooks, teams-meetings, wecom, qqbot, yuanbao, … on top of the classics). Wording like "22+" is stale — count names change every release, so treat the *live*
`/platforms` (slash-command) output as truth.

---

## What to Ignore

Some old advice is no longer worth optimizing around:

- Do not build your Gemini setup on the old Gemini-CLI OAuth providers — they were **removed in v0.18**. Use a Gemini API key, or the Vertex AI provider for GCP shops ([Part 9](./part9-custom-models.md)).
- Do not fork the dashboard for a custom tab; write a dashboard plugin — and for the desktop app, write a desktop plugin.
- Do not keep a giant SOUL.md full of procedures; use skills and Curator.
- Do not use one expensive default model for every auxiliary task — and don't hardcode "the current SOTA model" into your configs; check `hermes model` / the live catalog instead. Model names rotate quarterly.
- Do not hand-edit `~/.hermes/cron/jobs.json` or invent `sandboxes:` / `cron: jobs:` blocks in `config.yaml` — the real keys are `terminal.backend` (Part 21), the `cronjob` tool, and `hermes cron edit`.
- Do not expose the dashboard publicly without a real reverse proxy and auth layer.