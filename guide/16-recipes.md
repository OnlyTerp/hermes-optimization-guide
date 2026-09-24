# 16 · Recipes

> Seven complete builds that put the rest of the guide to work. Each one uses only features verified at v0.21.4, and each notes what it costs and how to check it's working.

**TL;DR**
- Start with **[the morning briefing](#1-a-morning-briefing-that-doesnt-repeat-itself)**. It exercises cron, web search, delivery, and cheap models in ten minutes.
- The two biggest cost patterns here are **[zero-token watchdogs](#2-zero-token-watchdogs)** (a script with no LLM) and **[pay-only-on-change monitors](#3-a-monitor-that-only-pays-when-something-changes)**.
- Anything triggered by outside content (webhooks, email, web pages) is a **prompt-injection surface**. The recipes that touch it say how to contain it.
- Every recipe assumes a working chat ([chapter 02](./02-install.md#prove-it-works-before-you-add-anything)) and, for anything scheduled, a running gateway service ([chapter 14](./14-production.md)).

| # | Recipe | Features | Typical cost |
|---|---|---|---|
| 1 | [Morning briefing that doesn't repeat itself](#1-a-morning-briefing-that-doesnt-repeat-itself) | cron, web, `--continuity`, delivery | One short agent run per day on a cheap model |
| 2 | [Zero-token watchdogs](#2-zero-token-watchdogs) | cron `--no-agent` script | $0 in model spend |
| 3 | [A monitor that only pays when something changes](#3-a-monitor-that-only-pays-when-something-changes) | cron `--monitor-url` | Agent runs only on change |
| 4 | [PR reviews on autopilot](#4-pr-reviews-on-autopilot) | webhook route, per-route toolsets, `gh` | One agent run per PR event |
| 5 | [A team Telegram assistant](#5-a-team-telegram-assistant) | profile, pairing, toolsets, approvals | Depends on usage. Capped by design. |
| 6 | [Coding sessions that can't wreck your repo](#6-coding-sessions-that-cant-wreck-your-repo) | worktree, checkpoints, `/goal` gates, `/review` | Your normal coding spend |
| 7 | [A research deep-dive without drowning the context](#7-a-research-deep-dive-without-drowning-the-context) | `/goal`, cheap subagents, `/compress focus`, `/learn` | Most tokens go to cheap children |

## 1. A morning briefing that doesn't repeat itself

**Goal:** a short daily digest on your phone at 8:00, without yesterday's stories.

1. **Get the prompt right interactively first.** Run `hermes`, then:

   ```text
   Search the web for news from the past 24 hours about open-source LLMs and AI agents.
   Pick the 3 most important stories. For each: a one-line headline, two sentences, the source URL.
   ```

   Iterate until you like the output. Cron jobs start with **no** memory of this chat, so the final prompt must be self-contained.

2. **Schedule it** (requires a running gateway and a home channel; send `/sethome` in the Telegram chat first):

   ```bash
   hermes cron create "0 8 * * *" \
     "Search the web for news from the past 24 hours about open-source LLMs and AI agents. \
   Pick the 3 most important stories that were NOT in your previous briefing. For each: a one-line \
   headline, two sentences, the source URL. If nothing new matters, reply with only [SILENT]." \
     --name morning-brief --deliver telegram --continuity --reasoning-effort low
   ```

   - `--continuity` feeds the job its own previous output each run, so it can skip stories it already reported.
   - `[SILENT]` on its own suppresses delivery on quiet days.
   - `--reasoning-effort low` keeps a summarization job from paying for deep thinking.

3. **Make every unpinned job cheap:** `hermes config set cron.model <cheap-model>` (plus `cron.model_provider` if needed). Your chat model stays untouched ([chapter 05](./05-token-budget.md#lever-6-cheaper-models-for-work-that-doesnt-need-the-best)).

**Verify:** `hermes cron list` shows the job as active along with its ID, `hermes cron run morning-brief` fires it on the next scheduler tick, and `hermes cron runs <job-id>` shows the attempt (`runs` takes the ID, not the name). If nothing arrives, see the [cron table in chapter 15](./15-troubleshooting.md#cron).

## 2. Zero-token watchdogs

**Goal:** alerts for "disk almost full", "backup didn't run", or "site is down" that cost nothing in model spend.

A `--no-agent` job runs a script on schedule and delivers its stdout verbatim. **Empty output means no message.** No model is ever called. Scripts live in `~/.hermes/scripts/`:

```bash
mkdir -p ~/.hermes/scripts
cat > ~/.hermes/scripts/disk-check.sh <<'EOF'
#!/usr/bin/env bash
# Print a message only when the root filesystem is over 85% full.
use=$(df --output=pcent / | tail -1 | tr -dc '0-9')
if [ "$use" -gt 85 ]; then echo "Disk / is at ${use}% on $(hostname)"; fi
EOF

hermes cron create "every 1h" --no-agent --script disk-check.sh \
  --name disk-watch --deliver telegram
```

The same shape works for backup freshness (check a file's age), certificate expiry, or an HTTP health check with `curl -fsS … || echo "down"`. Want the agent to *interpret* the output instead of just forwarding it? Drop `--no-agent`. The script's stdout is then injected into the agent's prompt on every run.

**Verify:** make the check fail on purpose (temporarily lower the threshold), then `hermes cron run disk-watch`.

## 3. A monitor that only pays when something changes

**Goal:** "tell me when the pricing page changes, and what changed", without paying for an agent run every hour.

Monitor mode fetches a URL (or runs a cheap script) on every tick and hashes the result. **If nothing changed, the agent doesn't run at all.** When it does change, the agent gets a `MONITOR CHANGE DETECTED` diff in its prompt:

```bash
hermes cron create "every 2h" \
  "A monitored page changed. Summarize what changed in 3 bullets and say whether it affects us." \
  --monitor-url https://example.com/pricing \
  --name pricing-watch --deliver telegram
```

For pages with timestamps or rotating tokens, use `--monitor-script` with a script that extracts only the stable part you care about. Monitor output must be deterministic, or every tick counts as a change.

> [!WARNING]
> The changed page content goes into the agent's prompt, so it's untrusted input. Keep this job on a profile or toolset without terminal access if the page isn't yours ([chapter 13](./13-security.md)).

## 4. PR reviews on autopilot

**Goal:** a review comment on every new pull request, posted by Hermes.

This is the official [webhook PR review guide](https://hermes-agent.nousresearch.com/docs/guides/webhook-github-pr-review) plus the guardrails that matter. You need `gh` installed and authenticated on the gateway host, and a public URL for the gateway (or a tunnel).

1. **Add a webhook route** to `config.yaml`. The webhook platform listens on port 8644 by default:

   ```yaml
   platforms:
     webhook:
       enabled: true
       extra:
         port: 8644
         routes:
           github-pr-review:
             secret: "<long random string, same as in GitHub>"
             events: [pull_request]
             toolsets: [terminal]          # webhook default has NO terminal; grant only what gh needs
             prompt: |
               PR #{number} in {repository.full_name}: {pull_request.title} (action: {action}).
               If the action is not "opened" or "synchronize", stop without commenting.
               Otherwise run: gh pr diff {number} --repo {repository.full_name}
               Review for correctness, security and clarity. Be concise and specific.
             deliver: github_comment
             deliver_extra:
               repo: "{repository.full_name}"
               pr_number: "{number}"
   ```

2. **Restart the gateway**, then in GitHub go to **Settings → Webhooks → Add webhook**: payload URL `https://<your-host>/webhooks/github-pr-review`, content type JSON, the same secret, and **Pull requests** events only.

3. **Contain it.** PR titles, descriptions, and diffs are attacker-controlled text that now reaches an agent with a shell. Run this gateway with a container terminal backend ([chapter 09](./09-tools-mcp-plugins.md)), give `gh` a token scoped to commenting on this repo only, and keep `approvals.unattended_mode: deny` (the default). That denies dangerous commands instead of waiting for an approval nobody will give.

**Verify:** `curl http://localhost:8644/health` returns `{"status": "ok", …}`, and `hermes logs gateway -f` shows the event when you open a test PR. No public endpoint? The official [cron-polling PR review agent](https://hermes-agent.nousresearch.com/docs/guides/github-pr-review-agent) works behind NAT.

Two cheaper variants: `hermes webhook subscribe <name> --deliver-only …` forwards the rendered message without running the agent (zero LLM cost), and `--script <filter>` can drop events before any model call. Empty output or `[SILENT]` ignores the event.

## 5. A team Telegram assistant

**Goal:** a shared bot your team can DM, with its own personality, a cheap model, and no access to your personal memory or your shell.

1. **Give it its own profile** so it never mixes with your personal agent:

   ```bash
   hermes profile create team --description "Team assistant: answers questions, drafts updates" --no-skills
   hermes -p team setup            # pick a cheap, reliable model for this profile
   hermes -p team gateway setup    # Telegram bot token from @BotFather
   ```

2. **Control who can talk to it.** Prefer DM pairing for teams: a new user DMs the bot, gets a one-time code, and you approve it:

   ```bash
   hermes pairing list
   hermes pairing approve telegram XKGH5N7P
   hermes pairing revoke telegram 987654321    # when someone leaves
   ```

3. **Take away what a shared bot shouldn't have**, and make risky actions ask:

   ```bash
   hermes -p team tools disable --platform telegram terminal code_execution browser computer_use
   hermes -p team config set approvals.mode manual
   ```

4. **Give it a voice and a job.** Write a short `~/.hermes/profiles/team/SOUL.md` ([chapter 06](./06-personality-and-context.md)). For a team group chat, put the group's purpose in `telegram.channel_prompts`.

5. **Restart the host gateway**: `hermes gateway restart`. One gateway serves every profile ([chapter 10](./10-messaging.md)).

Or merge [`templates/config/messaging-bot.yaml`](../templates/config/messaging-bot.yaml) into the profile's `config.yaml`. It also removes file access and delegation, stages memory writes for review, and caps turns.

**Verify:** `hermes -p team prompt-size --platform telegram` shows the trimmed tool list. With the template it's 11 tools and 17 KB of schemas, down from 24 tools and 42 KB, measured on v0.21.4. A non-paired account gets a pairing code, not an answer. `/whoami` in the chat shows each user's access level.

## 6. Coding sessions that can't wreck your repo

**Goal:** let the agent make big changes, with a guaranteed way back and "done" meaning *the tests pass*.

```bash
hermes config set checkpoints.enabled true   # filesystem snapshots before edits
hermes -w                                    # start in an isolated git worktree
```

Then, in the session:

```text
/goal Migrate the settings module from dataclasses to pydantic v2 without changing behavior
/goal gate add uv run pytest -q tests/settings
/goal gate add uv run ruff check .
```

- **The worktree** (`-w`) keeps the agent's edits on their own branch under `.worktrees/`. It's kept on exit only if it has unpushed commits.
- **Gates** are shell commands that must exit 0 before the goal's judge is even asked whether you're done. A red suite feeds its output back to the agent as the next instruction. Each gate retries 3 times by default, then the goal pauses for you.
- **`/rollback`** lists checkpoints and restores one. `/diff session` shows everything Hermes changed.
- **`/review`** before you merge spawns an independent reviewer subagent. Pin it to a different model with `auxiliary.review.*` for a genuine second opinion.

Optionally, `agent.verify_on_stop: true` refuses a final answer on any turn that edited code without fresh evidence (a test, build, or lint run). It works better once Hermes knows how your project runs. `hermes verify --detect-only` prints the build, test and start recipe it detects, and `hermes verify --save` pins it in `.hermes/environment.json`. From then on, the stop check steers the agent to prove its work with `hermes verify --json`, a full build → test → start → readiness pass.

**Verify:** `/goal gate list` shows the gates, and `/goal status` shows progress. Break a test on purpose and watch the goal refuse to finish.

## 7. A research deep-dive without drowning the context

**Goal:** a thorough multi-source answer, where the main session stays small and the expensive model does only the thinking.

1. **Make subagents cheap** (once): `hermes config set delegation.model <cheap-model>`, plus `delegation.provider` if it's on another provider.
2. **Set a standing goal** and let it fan out:

   ```text
   /title vector-db-eval
   /goal Compare Qdrant, pgvector and LanceDB for 50M embeddings on one 64 GB box: ingest speed, filtered-query latency, ops burden. Use parallel subagents for the reading; end with a recommendation and a sources list.
   ```

   Each subagent reads its sources in its own context, and only its summary comes back. That's the whole point ([chapter 12](./12-multi-agent.md)).
3. **Keep the main thread lean** as it goes: `/compress focus the latency results` after big tool dumps, and `/btw` for side questions that shouldn't enter the transcript.
4. **Keep the method.** When the result is good: `/learn the research workflow we just used, as a reusable skill`. Next time it's one command ([chapter 08](./08-skills.md)).

**Verify:** `/context` should show the conversation staying small while subagents do the reading, and `hermes insights --days 1` shows where the tokens went.

## Go deeper

- Official tutorials: [Daily briefing bot](https://hermes-agent.nousresearch.com/docs/guides/daily-briefing-bot) · [Team Telegram assistant](https://hermes-agent.nousresearch.com/docs/guides/team-telegram-assistant) · [Webhook PR reviews](https://hermes-agent.nousresearch.com/docs/guides/webhook-github-pr-review) · [Script-only cron](https://hermes-agent.nousresearch.com/docs/guides/cron-script-only) · [Automation blueprints](https://hermes-agent.nousresearch.com/docs/guides/automation-blueprints) · [Persistent goals](https://hermes-agent.nousresearch.com/docs/user-guide/features/goals)
- In this guide: [11 · Automation](./11-automation.md) · [12 · Delegation & Multi-Agent](./12-multi-agent.md) · [13 · Security](./13-security.md)

---
[← Previous: 15 · Troubleshooting](./15-troubleshooting.md) · [Guide index](../README.md#the-guide) · [Next: Cheat Sheet →](./cheatsheet.md)
