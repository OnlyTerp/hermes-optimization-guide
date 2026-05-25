# Part 22: Latest Power Moves — Curator, TUI, Plugins, Context Files

*If you already know Hermes but missed the v0.11/v0.12 wave, read this part first for Curator, TUI, plugins, and context hygiene. For the v0.13/v0.14 durability + foundation layer — Kanban, `/goal`, `/handoff`, Checkpoints v2, no-agent cron, PyPI installs, proxy, and new platforms — go next to [Part 23](./part23-tenacity-stack.md).*

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

## What to Ignore

Some old advice is no longer worth optimizing around:

- Do not install external Gemini CLI just for Gemini auth; Hermes can do OAuth itself.
- Do not fork the dashboard for a custom tab; write a dashboard plugin.
- Do not keep a giant SOUL.md full of procedures; use skills and Curator.
- Do not use one expensive default model for every auxiliary task.
- Do not expose the dashboard publicly without a real reverse proxy and auth layer.
