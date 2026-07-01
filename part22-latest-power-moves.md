# Part 22: Latest Power Moves — Curator, TUI, Plugins, Context Files

*If you already know Hermes but missed the v0.11/v0.12 wave, read this part first for Curator, TUI, plugins, and context hygiene. For the v0.13/v0.14 durability + foundation layer — Kanban, `/goal`, `/handoff`, Checkpoints v2, no-agent cron, PyPI installs, proxy, and new platforms — go next to [Part 23](./part23-tenacity-stack.md). The everyday moves from v0.15 "Velocity" and v0.16 "Surface" — `/undo`, a default-interface choice, the fuzzy model picker, and leaner default skills — are in [section 8](#8-newer-power-moves-v015--v016), and the newest v0.17 "Reach" / v0.18 "Judgment" quick hits are in [section 9](#9-newer-power-moves-v017--v018). For the native GUI and the run-it-local story, see [Part 24](./part24-desktop-app.md) and [Part 25](./part25-nvidia-local.md). For the big v0.18 ideas — Mixture-of-Agents, verification, `/learn`, `/journey` — see [Part 26](./part26-moa-verification.md).*

---

## 1. Turn On Curator Before Your Skill Library Becomes Noise

Agent-created skills are valuable until the library fills with duplicates, stale CLI flags, and one-off task notes. Curator is the v0.12 maintenance loop for that.

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

> **v0.17 change:** the Curator's LLM-driven consolidation pass is now **opt-in** — routine curation (archiving duplicates, pruning stale skills) costs zero tokens by default. Enable consolidation explicitly when you want it to actually merge and rewrite skills. Pair Curator with `/journey` ([Part 26](./part26-moa-verification.md#3-learn-and-journey--self-improvement-you-can-see)) to audit the memory side too.

---

## 2. Use the TUI as Your Daily Driver

`hermes --tui` is now the primary power-user interface. It is not just prettier output; it changes how you steer long runs.

```bash
hermes --tui
```

Habits that pay off:

- Use `/steer <constraint>` when the agent is mid-run but drifting.
- Use `/queue <next task>` for dependent follow-ups.
- Use `/background <prompt>` for independent research or monitoring.
- Use `/resume`, then delete stale sessions from the picker with `d`.
- Use `/reload` after editing `.env`; avoid restarting the session just to pick up keys.
- Toggle `/mouse` if your terminal/ConPTY injects phantom mouse events.

If the dashboard Chat tab is enabled, it embeds the same TUI through a PTY, so improving your TUI workflow also improves the browser workflow.

---

## 3. Clean Up Context Files

Hermes now reads common agent instruction files, including `.hermes.md`, `AGENTS.md`, `CLAUDE.md`, `SOUL.md`, and `.cursorrules`.

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

v0.12 made plugins the right abstraction for tools, hooks, slash commands, dashboard tabs, and gateway platforms.

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
| `hermes-achievements` | Dashboard achievements from session history |
| image-gen backends | Extra OpenAI/Codex/xAI image routes |

Security posture:

- Plugins are disabled by default; keep it that way.
- Enable only trusted bundled/user plugins.
- Enable project-local plugins only for trusted repos.
- Treat hooks as code execution, not "just configuration."

---

## 5. Split Main and Auxiliary Models

The dashboard and `hermes model` now expose auxiliary model configuration. Use it.

| Job | Good default |
|-----|--------------|
| Main agent | Your preferred coding/reasoning model |
| Compression | Cheap fast model |
| Vision | A model with actual image capability |
| Session search | Cheap summarizer/search-capable model |
| Title generation | Cheapest reliable model |
| Curator | Cheap model with enough context for skill review |

This avoids spending premium tokens on titles, compression, and housekeeping.

---

## 6. Chain Cron Jobs Instead of Repeating Context

Cron is no longer just "run this prompt every morning." Use:

- Per-job `workdir` for project-aware jobs.
- Per-job `enabled_toolsets` to shrink tool/context overhead.
- `context_from` to feed one job's output into the next.
- Webhook direct delivery for zero-LLM notifications.

Example pattern:

```yaml
cron:
  jobs:
    collect-build-status:
      schedule: "*/30 * * * *"
      workdir: ~/projects/app
      enabled_toolsets: [terminal]
      prompt: "Run the build status check and summarize failures only."
    notify-build-status:
      schedule: "*/30 * * * *"
      context_from: collect-build-status
      deliver: telegram_private
      prompt: "Notify only if the upstream job found failures."
```

---

## 7. v0.12 Upgrade Checklist for Existing Installs

Before moving an older v0.9/v0.10 setup to the v0.12 interface/curator stack:

```bash
hermes update --check
hermes backup
hermes --version
hermes doctor
```

Then:

1. Open `hermes dashboard`.
2. Configure main + auxiliary models.
3. Enable only the plugins you actually need.
4. Run `hermes curator run --dry-run`.
5. Test one gateway message, one tool call, one skill, and one cron job.
6. Review [Part 19](./part19-security-playbook.md) before enabling broad platform access.
7. Then run the [v0.14 Foundation checklist](./part23-tenacity-stack.md#8-upgrade-checklist-from-v013-to-v014).

---

## 8. Newer Power Moves (v0.15 → v0.16)

The Velocity and Surface releases added a handful of small things you'll reach for daily:

### `/undo [N]` — take back turns

Made a mess, or sent the wrong prompt? `/undo` rewinds the last turn; `/undo N` rewinds the last `N`. It also **prefills your last message** so you can edit and resend instead of retyping. Works the same in the CLI, TUI, and messaging surfaces.

```text
/undo        # undo the last turn
/undo 3      # undo the last three turns
```

### Pick your default interface

`hermes chat` can default to either the **CLI** or the **TUI** — set it once and override per-invocation with `--cli`:

```bash
hermes config set interface tui   # or: cli
hermes chat --cli                 # one-off override
```

The TUI also unified its model switcher under `/model` and added a Sessions overlay.

### The fuzzy model picker is everywhere

Desktop, web, TUI, and CLI all share the same **fuzzy model picker**. Multi-endpoint providers are grouped, and the catalog **refreshes hourly**, so new models appear without waiting for a Hermes release. Just type part of a name in `hermes model` and pick.

### Leaner default skills

v0.16 trimmed the built-in skill set so the agent isn't carrying dead weight. Several skills became **native plugins** or moved to **MCP** (for example, Spotify is now a native plugin; Linear is `hermes mcp install linear`), others moved to **optional**, and a new `environments:` relevance gate keeps irrelevant skills from loading. Curator can now prune **built-in** skills too, not just agent-created ones.

If you relied on a skill that disappeared, check whether it's now a plugin (`hermes plugins list`) or an MCP server (`hermes mcp ...`) before recreating it.

### Free, instant session search

`session_search` is now ~4,500× faster and runs locally for free — searching your own history no longer burns tokens. Combine it with desktop's search-by-id (see [Part 24](./part24-desktop-app.md)) to jump back into past work fast.

### Scale durable work into a swarm

When one board outgrows a single worker, `hermes kanban swarm` turns Kanban into a multi-agent platform (root, parallel workers, gated verifier/synthesizer, shared blackboard, per-task model overrides). Full details in [Part 23](./part23-tenacity-stack.md).

> **Security note:** v0.15 added **Brainworm/promptware defenses** against malicious instructions hidden in tool output. Keep them on, and read [Part 19](./part19-security-playbook.md) before wiring up untrusted inputs.

---

## 9. Newer Power Moves (v0.17 → v0.18)

The Reach and Judgment releases added another round of daily drivers. The headline features (MoA, verification, `/learn`, `/journey`, background fan-out) get their own part — [Part 26](./part26-moa-verification.md) — but these small ones deserve muscle memory:

### `/prompt` — compose long prompts in a real editor

Opens `$EDITOR` so you can write a multi-line, markdown-formatted prompt and have it queued as your next message. The single best QoL command of v0.18 for anyone writing detailed task briefs.

### `/reasoning full` — uncap thinking for a session

When a session hits something genuinely hard, `/reasoning full` removes the thinking budget cap for that session. Cheaper than switching to a bigger model for one gnarly step.

### `/timestamps` and a timestamped `/history`

Toggle inline timestamps on turns and see when things actually happened in `/history` — essential when auditing long autonomous runs.

### In-place compaction (no more broken `@session` links)

Context compression now rewrites the session **under the same session id** by default, instead of rotating to a new one. Long-running sessions keep their identity, so `@session` references, integrations, and desktop links stop silently breaking.

### `image_generate` learned image-to-image

Pass an input image and a transform prompt — restyle screenshots, apply logos, iterate on drafts — across every image provider, from any surface.

### `memory` batch operations

The `memory` tool applies multiple add/update/delete operations atomically in one call. Bulk cleanups (or a `/journey` pruning session) are one round-trip instead of ten.

### Automation Blueprints instead of raw cron

Parameterized automation templates that render as a dashboard form, a slash command, or a plain conversation ("set up my daily briefing for 8am"). Use them for anything you'd previously hand-rolled cron YAML for; keep raw cron for the deterministic no-agent watchdogs in [Part 23](./part23-tenacity-stack.md#5-use-no_agent-cron-for-watchdogs).

### Blank Slate setup

A minimal-agent onboarding mode: start from nothing and opt in tools one at a time. The right default for compliance-sensitive or locked-down machines.

---

## What to Ignore

Some old advice is no longer worth optimizing around:

- Do not build your Gemini setup on the old Gemini-CLI OAuth providers — they were **removed in v0.18**. Use a Gemini API key, or the Vertex AI provider for GCP shops ([Part 9](./part9-custom-models.md)).
- Do not fork the dashboard for a custom tab; write a dashboard plugin.
- Do not keep a giant SOUL.md full of procedures; use skills and Curator.
- Do not use one expensive default model for every auxiliary task.
- Do not expose the dashboard publicly without a real reverse proxy and auth layer.
