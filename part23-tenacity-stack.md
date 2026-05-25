# Part 23: Foundation + Tenacity Stack — Kanban, Goals, Handoff, Proxy, No-Agent Cron

*Hermes v0.14.0 (2026.5.16, "The Foundation Release") does not replace the v0.13 Tenacity stack — it makes it easier to install, cheaper to run, and available from more surfaces. The move is now: install lean, put durable work on Kanban, lock sessions to `/goal`, hand off live when the model/profile should change, and keep deterministic jobs out of the LLM path.*

---

## 1. Treat Kanban as the Durable Execution Layer

`delegate_task` is still useful for short fork/join reasoning. It is not the right primitive for work that must survive restarts, wait for humans, retry after failures, or pass through multiple roles.

Use **Hermes Kanban** for that:

```bash
hermes kanban init
hermes dashboard   # open the Kanban page
```

Then create work from chat, CLI, or the dashboard:

```text
/kanban create "Audit the billing dashboard for stale Hermes v0.12 claims" \
  --assignee researcher \
  --workspace worktree
```

Why this matters:

| Old pattern | v0.14 pattern |
|-------------|---------------|
| Parent subagent blocks until child returns | Board row persists; parent can move on |
| Failed child disappears into logs | Task blocks with comments, retry budget, and history |
| One anonymous worker | Named assignees with durable identity |
| Context compression can erase the trail | SQLite board keeps the audit trail |
| Human feedback is awkward | Human comments/unblocks are first-class |

Workers use the `kanban_*` toolset (`kanban_show`, `kanban_list`, `kanban_complete`, `kanban_block`, `kanban_heartbeat`, `kanban_comment`, `kanban_create`, `kanban_link`, `kanban_unblock`). Humans use `hermes kanban ...`, `/kanban ...`, or the dashboard. Both hit the same `~/.hermes/kanban.db`.

Good board shapes:

- **Solo dev:** triage → implement → review → PR.
- **Research desk:** scouts gather links, analyst synthesizes, writer drafts.
- **Ops journal:** recurring checks append comments to the same service task over weeks.
- **Fleet work:** one board per client/account/tenant; specialists claim their lane.
- **Coding factory:** Codex/Claude/OpenCode worker lanes write patches; Hermes reviews before completion.

---

## 2. Add Worker Lanes Instead of Giant Prompt Swarms

Worker lanes are the SOTA orchestration pattern for coding-heavy Hermes setups. A lane is an assignee plus a spawn contract:

- Hermes profile lanes: dispatcher spawns `hermes -p <profile>` with claim-scoped Kanban tools.
- External CLI lanes: Codex, Claude Code, OpenCode, or custom workers pull assigned cards and report back through the Kanban API/tools.
- Review lanes: human or agent reviewer gates "done" before dependent work unblocks.

Practical routing:

| Assignee | Use for | Completion posture |
|----------|---------|--------------------|
| `specifier` | Convert vague cards into acceptance criteria | Complete when spec is clear |
| `researcher` | Gather docs, issues, release notes | Comment sources, then hand off |
| `codex-worker` | Small isolated code edits | Block for Hermes/human review |
| `claude-code` | Larger multi-file refactors | Block for review + tests |
| `reviewer` | Verify diff, tests, risk | Complete or unblock with fixes |

Keep Hermes Kanban as the source of truth. Do not let a specialist CLI silently mark code as done just because it exited successfully.

---

## 3. Use `/goal` for "Do Not Stop Until It Is Done"

`/goal` gives a session a persistent objective. After each turn, Hermes checks whether the goal is satisfied; if not, it continues within the configured turn budget.

```text
/goal Refresh this guide to Hermes v0.14, remove stale v0.13-as-current claims, run validation, and open a PR.
```

Use it for:

- Release-note sweeps where the agent might otherwise stop after the first file.
- Bug hunts that require reproduce → inspect → patch → test loops.
- Documentation refreshes with many cross-links.
- Long "make this production-ready" sessions where done means verified, not merely attempted.

Do not use `/goal` for vague aspirations like "improve the project." Give it an observable exit condition: checks pass, PR opened, benchmark table updated, board card complete, etc.

---

## 4. Checkpoints v2 Changes Your Risk Model

Hermes already had rollback-style safety. v0.13's Checkpoints v2 remains the production baseline:

- Real pruning prevents checkpoint directories from growing forever.
- Disk guardrails stop runaway snapshots from filling a VPS.
- Shadow repos are cleaned up instead of orphaned.
- Patch/write syntax linting catches broken Python, JSON, YAML, and TOML immediately after file writes.

Recommended habit:

```text
Before a risky multi-file edit, confirm checkpointing is enabled.
After the edit, run tests.
If the direction is wrong, /rollback before trying a different strategy.
```

This is especially important when Kanban workers use git worktrees: checkpoints protect the worker workspace, while git protects the reviewable diff.

---

## 5. Use `no_agent` Cron for Watchdogs

Not every scheduled job needs an LLM. v0.13+ cron can run in **no-agent mode**: execute a script on schedule, deliver stdout if there is anything to say, and spend zero tokens.

Use no-agent mode for:

- Disk-space alerts.
- Uptime checks.
- Backup presence checks.
- "Did CI fail?" pollers.
- Cost/budget threshold pings.

Pattern:

```yaml
cron:
  - name: disk-watchdog
    schedule: "*/15 * * * *"
    mode: no_agent
    command: "df -h / | awk 'NR==2 && $5+0 > 85 {print \"Disk usage high: \"$5}'"
    notify: telegram_private
```

Keep LLM-backed cron for jobs that need judgment, synthesis, or tool use. Use no-agent for deterministic checks.

---

## 6. Route Media to Models That Actually Understand It

v0.13+ adds a `video_analyze` tool path for Gemini and compatible multimodal providers. Do not treat video as "just another attachment" on a text model.

Use it for:

- Meeting recordings: action items, objections, decisions, timestamps.
- UI bug reports: "watch the repro video and identify the first broken frame."
- Security review: inspect screen recordings without dumping raw private media into memory.
- Support triage: classify customer clips before escalating to a human.

Pattern:

```yaml
auxiliary_models:
  vision:
    provider: google
    model: gemini-3.1-pro
  video:
    provider: google
    model: gemini-3.1-pro
```

For voice replies, xAI Custom Voices can now sit beside Edge/OpenAI/Gemini/MiniMax TTS:

```yaml
tts:
  provider: xai
  voice: ${XAI_CUSTOM_VOICE_ID}
  require_private_channel: true
```

Keep cloned voices private-channel only unless you have explicit consent and a clear disclosure policy.

---

## 7. Update Your Platform and Provider Mental Model

v0.14 pushes the plugin/provider surfaces further:

- **Platforms:** Google Chat is joined by Teams end-to-end, LINE, and SimpleX Chat, bringing the gateway to 22+ platforms.
- **Providers:** model providers can ship as plugins, SuperGrok OAuth is first-class, and `hermes proxy` can expose OAuth-backed providers through an OpenAI-compatible local endpoint.

Operational rule:

1. Keep bundled/user plugins opt-in.
2. Keep project-local plugins disabled unless the repo is trusted.
3. Prefer native provider plugins over generic OpenAI-compatible shims when they expose provider-specific caching, reasoning, media, or auth.
4. Re-run `hermes plugins list` and `hermes model` after every major release; the live menus move faster than static docs.

---

## 8. Upgrade Checklist from v0.13 to v0.14

```bash
hermes update --check
hermes backup
hermes --version
pip install -U hermes-agent
hermes plugins list
hermes model
hermes proxy --help
```

Then verify the v0.14-specific paths:

- Confirm `pip install hermes-agent` or your source install resolves without pulling unused heavy adapters.
- Sign in to SuperGrok/Claude/OpenAI OAuth only if you use those subscriptions, then test `hermes proxy` on loopback.
- Run an `x_search` query from a disposable session if you rely on X/Twitter signals.
- If you use Teams, verify Graph auth, webhook receipt, and outbound delivery end-to-end.
- If you expose LINE or SimpleX, keep them in a quarantine profile until identity and approval routing are proven.
- Use `/handoff` in a disposable session to move from a cheap model to a deep-reasoning profile without losing context.
- Re-check the v0.13 durability paths too: Kanban, `/goal`, Checkpoints v2, no-agent cron, and redaction defaults.

---

## 9. The Current Power Stack

For a serious May 2026 Hermes deployment:

1. **PyPI/source install with lazy deps** so the box only carries adapters it actually uses.
2. **Dashboard** for config, plugins, Kanban, analytics, profiles, and Chat.
3. **Kanban** for durable multi-agent work.
4. **`/goal` + `/handoff`** for persistent objectives and live model/profile escalation.
5. **`hermes proxy`** for Codex/Aider/Cline/Continue using OAuth-backed subscriptions.
6. **Grok 4.3 / Gemini 3.1** for million-token research and media lanes.
7. **MCP** for tools, with strict trust and sampling boundaries.
8. **Coding-agent lanes** for code work, not one giant Hermes prompt.
9. **Remote sandboxes/worktrees** for isolation.
10. **Langfuse/Helicone/Phoenix + no-agent cron** for traces, budgets, and deterministic watchdogs.

If you only adopt one durability pattern, adopt Kanban. If you only adopt one v0.14 pattern, adopt `hermes proxy` for OAuth-backed coding tools and keep it loopback-only.
