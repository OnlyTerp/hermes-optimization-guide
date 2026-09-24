# 06 · Personality & Context Files

> Give Hermes a voice worth talking to and project instructions it actually follows, without paying for a novel on every call.

**TL;DR**
- **`SOUL.md` is who the agent is.** It's slot #1 of every system prompt, loaded only from `~/.hermes/SOUL.md` (per profile). Keep it to a few hundred words of voice and stance.
- **Project instructions go in `AGENTS.md`** (or `.hermes.md`), not `SOUL.md`. Only **one** kind of project file loads per session, and inside a git repo Hermes loads the whole `AGENTS.md` chain from the repo root down to your working directory.
- **Everything always-on is paid on every call.** A 31.9 KB `AGENTS.md` measured **+8,609 tokens per call**. Push rarely needed detail into subdirectory `AGENTS.md` files, skills, or `@file:` references, which load only when needed.
- `/context` tells you exactly which files loaded, which were shadowed or truncated, and what each costs.
- Use `/personality` for temporary modes, per-channel prompts for rooms with a job, and `platform_hints` for formatting.

## Where each kind of instruction belongs

Most "Hermes ignores my instructions" problems come from putting the instruction in the wrong place. Use this map:

| Instruction | Put it in | Loaded | Scope |
|---|---|---|---|
| Voice, tone, bluntness, what to never say | `~/.hermes/SOUL.md` | Every call | The whole profile |
| Repo layout, conventions, commands, ports, don'ts | `AGENTS.md` / `.hermes.md` in the project | Every call in that project | One project |
| Your personal tweaks to a shared repo's rules | `AGENTS.override.md` (gitignored) | Instead of `AGENTS.md` | You, in that project |
| Facts about you and your environment that it learned | Memory (`MEMORY.md`, `USER.md`) | Every call, as a snapshot | The whole profile ([07](./07-memory.md)) |
| Multi-step procedures ("how we deploy") | A skill | Index line always; body on demand | The whole profile ([08](./08-skills.md)) |
| A temporary mode ("teach me", "be terse") | `/personality <name>` | While selected | This session |
| What a specific chat room is for | `<platform>.channel_prompts` | Every turn in that channel | One channel |
| Formatting for a surface ("no tables on WhatsApp") | `platform_hints.<platform>` | Every call on that platform | One platform |

## SOUL.md: the agent's identity

Hermes seeds a starter `SOUL.md` (667 bytes) on first run and never overwrites yours. Facts worth knowing:

- It's loaded **only** from the profile's Hermes home (`~/.hermes/SOUL.md`, or `~/.hermes/profiles/<name>/SOUL.md`). A `SOUL.md` in your project directory is ignored. That's deliberate, so your agent's personality doesn't change with the folder you launched from.
- It **replaces** the built-in identity rather than adding to it. An empty file falls back to the built-in default, which is a sensible "be direct, no filler" paragraph.
- It's scanned for prompt-injection patterns. Unlike project files, your own `SOUL.md` is warned about, not blocked, and `/context` flags it.
- Delegated subagents don't load it. They use the built-in identity.
- **The agent *can* rewrite it without asking.** `security.protected_instruction_files` (on by default) makes agent writes to *project* instruction files (`AGENTS.md`, `CLAUDE.md`, a `SOUL.md` in a repo, `.cursorrules`) ask for your approval, even under `--yolo`. Your own Hermes home is exempt by design (`tools/file_tools_write_guards.py` at v0.21.4), so a write to `~/.hermes/SOUL.md` goes through with no prompt, whatever the upstream SOUL guide says. Keep it in version control or back it up, and check it after any session that read untrusted text ([chapter 13](./13-security.md#layer-6-instruction-integrity)).

### What makes a SOUL.md good

Put in things that change how the agent *feels* to work with: tone, directness, brevity, humor, when to push back, how to handle uncertainty. Leave out file paths, project conventions, life stories, security policy, and anything that only matters sometimes.

| Rules that work | Rules that produce mush |
|---|---|
| "Answer first, then explain only if asked." | "Provide comprehensive and thoughtful assistance." |
| "If my plan is bad, say so in the first sentence." | "Maintain professionalism at all times." |
| "Never open with 'Great question'." | "Ensure a positive and supportive experience." |
| "When unsure, say what you'd check and check it." | "Be accurate and helpful." |

**Short beats long.** `SOUL.md` rides on every call of every session. A tight 500–1,000-byte file shapes behavior as much as a 5 KB one, and it costs a fraction as much. A starting point:

```markdown
# Soul

You're a sharp, practical operator. You work for me, not for politeness.

- Lead with the answer. One sentence if one sentence does it.
- Have opinions. Recommend one option; mention alternatives only if they matter.
- Call out bad ideas early and plainly. Charm over cruelty, no sugarcoating.
- No filler: never open with "Great question", "Absolutely", or "I'd be happy to".
- Unsure? Say so, then go find out with your tools instead of guessing.
- Before claiming something worked, show the evidence: the exit code, the output, the file.
- Humor when it lands naturally. Never forced.
```

### The Molty prompt

Want to skip writing it yourself? This prompt is from [OpenClaw's SOUL.md guide](https://docs.openclaw.ai/concepts/soul#the-molty-prompt), credited and reproduced as published. Paste it into a chat and let the agent rewrite its own `SOUL.md`. There's no approval prompt for that file, so save a copy first (`cp ~/.hermes/SOUL.md ~/.hermes/SOUL.md.bak`) and read the result:

```text
Read your `SOUL.md`. Now rewrite it with these changes:

1. You have opinions now. Strong ones. Stop hedging everything with "it depends" - commit to a take.
2. Delete every rule that sounds corporate. If it could appear in an employee handbook, it doesn't belong here.
3. Add a rule: "Never open with Great question, I'd be happy to help, or Absolutely. Just answer."
4. Brevity is mandatory. If the answer fits in one sentence, one sentence is what I get.
5. Humor is allowed. Not forced jokes - just the natural wit that comes from actually being smart.
6. You can call things out. If I'm about to do something dumb, say so. Charm over cruelty, but don't sugarcoat.
7. Swearing is allowed when it lands. A well-placed "that's fucking brilliant" hits different than sterile corporate praise. Don't force it. Don't overdo it. But if a situation calls for a "holy shit" - say holy shit.
8. Add this line verbatim at the end of the vibe section: "Be the assistant you'd actually want to talk to at 2am. Not a corporate drone. Not a sycophant. Just... good."

Save the new `SOUL.md`. Welcome to having a personality.
```

Review the result. Then start a new session (`/new`), because the running session keeps the prompt it started with.

> [!WARNING]
> Personality is not permission to be sloppy. If the agent posts in shared channels or talks to customers, make sure the tone fits the room. Profiles let a public-facing bot have a different `SOUL.md` from your personal one ([chapter 12](./12-multi-agent.md)).

## Personalities: temporary modes

`/personality` swaps in a session-level overlay on top of `SOUL.md` without editing it:

```text
/personality              # list them; the active one is marked
/personality concise      # built-ins: helpful, concise, technical, creative, teacher, pirate, noir, …
/personality none         # back to plain SOUL.md
```

Define your own under `agent.personalities` and switch to them from any surface:

```yaml
agent:
  personalities:
    reviewer: >
      You are a meticulous code reviewer. Lead with bugs and security issues,
      then design concerns. Cite file and line. No praise padding.
    brief: Answer in at most three sentences unless I ask for more.
```

## Project context files

Hermes looks for project instructions in the directory you start it from. **Only one type is loaded, first match wins:**

| Priority | File | Search scope |
|---|---|---|
| 1 | `.hermes.md` or `HERMES.md` | Working directory up to the git root |
| 2 | `AGENTS.override.md` | Your personal, usually gitignored, replacement for `AGENTS.md` |
| 3 | `AGENTS.md` | Inside a git repo: **every** `AGENTS.md` from the repo root down to the working directory, merged (deeper wins). Outside a repo: the working directory only. |
| 4 | `CLAUDE.md` | Working directory, for Claude Code compatibility |
| 5 | `.cursorrules`, `.cursor/rules/*.mdc` | Working directory, for Cursor compatibility |

Consequences people trip over:

- **A `.hermes.md` silently shadows your `AGENTS.md`.** There's no warning, but `/context` lists the shadowed file.
- **Starting deep inside a monorepo loads a stack of files**, from the root down. That's great for correctness, and every file costs tokens.
- **Your home directory matters.** Launching `hermes` from `~` loads a stray `~/AGENTS.md`, and outside a git repo that's the only place it looks.
- **Subdirectory files load lazily.** When the agent reads files under `backend/`, a `backend/AGENTS.md` is injected into that tool result (capped at 32,000 characters), not into the system prompt. That's the cache-friendly way to scope instructions.

Limits and safety:

- Each startup file is capped at `context_file_max_chars`. By default the cap scales with the model's window, from a 20,000-character floor to a 500,000 ceiling, and keeps 70% head and 20% tail with a marker in between. Set an explicit number to hold the line.
- Files that take longer than `context_file_read_timeout` (5 s) to read, as can happen on iCloud, OneDrive, or NFS, are skipped with a warning.
- Project files are scanned for injection patterns ("ignore previous instructions", hidden HTML, invisible Unicode, `cat .env`, credential exfiltration). A hit replaces the file with a `[BLOCKED: …]` marker. Still review `AGENTS.md` in repos you didn't write ([chapter 13](./13-security.md)).

### Write an AGENTS.md that earns its tokens

A good project file is a briefing for a smart new hire, not a wiki:

```markdown
# Project: billing-api

FastAPI + SQLAlchemy 2 + Postgres 16. Python 3.12, uv.

## Commands
- Test: `uv run pytest -q` · Lint: `uv run ruff check .` · Dev: `make dev` (port 8000)

## Conventions
- Endpoints return `{data, error, meta}`. Money is integer cents, never floats.
- New tables need an Alembic migration: `uv run alembic revision --autogenerate`.

## Never
- Edit files under `migrations/versions/` by hand.
- Commit `.env*` or touch `infra/prod/`.
```

That's about 500 bytes, and it prevents the most expensive mistakes. What **not** to put in it:

- Long architecture essays. Put them in `docs/` and let the agent read them when needed.
- Step-by-step procedures. Make them skills, so only one index line is always loaded.
- Per-module detail. Put it in `module/AGENTS.md`, loaded lazily when the agent works there.
- Anything true in every project. That belongs in `SOUL.md` or memory.

Let Hermes draft it: `/init` scans the repo and writes or updates `AGENTS.md`. Pass notes to steer it, like `/init focus on the test and deploy commands`. Then cut it down.

### Check what actually loaded

`/context` ends with a **Context files** list that shows each file's token estimate and whether it was loaded, truncated, shadowed by a higher-priority file, blocked by the injection scan, or unreadable. It's the answer to "why is my CLAUDE.md ignored?" To skip project files for one run, use `hermes --ignore-rules`.

## Context on demand: `@` references

Instead of making something permanent context, attach it to one message:

```text
Review @file:src/billing/invoice.py:40-120 against @file:docs/pricing.md
What changed? @diff
Summarize @url:https://example.com/changelog
```

Also available: `@folder:path`, `@staged`, and `@git:5` (the last N commits with patches, max 10). In the CLI, typing `@` autocompletes paths. This is pay-per-use context: it lands in one message instead of every call.

## Per-channel prompts and platform hints

Give a specific chat room a job without touching the agent's identity. The prompt is injected on every turn in that channel and isn't stored in the transcript:

```yaml
discord:
  channel_prompts:
    "1234567890": |
      This channel is for research. Compare options, cite sources, end with a recommendation.
telegram:
  channel_prompts:
    "-1001234567890": Keep replies under 5 lines. This is the family group.
```

`slack.channel_prompts` and `mattermost.channel_prompts` work the same way. Channel and thread IDs come from the platform ([chapter 10](./10-messaging.md)).

For surface-wide formatting, append to or replace Hermes' built-in platform hint:

```yaml
platform_hints:
  whatsapp:
    append: Never use Markdown tables; use short bullet lists.
  telegram: Prefer short messages; split long answers.   # bare string = append
```

Hints live in the stable part of the prompt and are byte-identical for a fixed config, so they don't hurt caching.

## Verify it

```bash
cat ~/.hermes/SOUL.md               # what the agent is actually told
hermes prompt-size                  # context tier bytes from the current directory
```

In a session, `/context` shows the context files and their token cost. `/personality` shows the active overlay. Start a fresh session after editing `SOUL.md` or `AGENTS.md`, because running sessions keep the prompt they started with.

## Gotchas

- **Edits don't apply mid-session.** Prompts are frozen per session for caching. Use `/new`.
- **`.hermes.md` beats `AGENTS.md`**, and both beat `CLAUDE.md`. Keep one type per project.
- **Monorepos stack `AGENTS.md` files** from root to working directory. Each one costs tokens on every call.
- **Profiles have separate `SOUL.md` files.** Editing `~/.hermes/SOUL.md` doesn't change the `work` profile.
- **A blocked project file shows as `[BLOCKED: …]`.** Remove the flagged phrasing, since even innocent documentation of an attack phrase trips the scanner in project files.

## Go deeper

- Official: [Personality & SOUL.md](https://hermes-agent.nousresearch.com/docs/user-guide/features/personality) · [Use SOUL.md with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes) · [Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files) · [Context References](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-references) · [Prompt Assembly](https://hermes-agent.nousresearch.com/docs/developer-guide/prompt-assembly)
- In this guide: [05 · The Token Budget](./05-token-budget.md) · [07 · Memory](./07-memory.md) · [08 · Skills](./08-skills.md)

---
[← Previous: 05 · Cost & Speed](./05-token-budget.md) · [Guide index](../README.md#the-guide) · [Next: 07 · Memory →](./07-memory.md)
