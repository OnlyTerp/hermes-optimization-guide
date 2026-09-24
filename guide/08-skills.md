# 08 · Skills

> Turn the work you repeat into procedures Hermes loads only when it needs them, keep the library small and trustworthy, and know what every skill costs you.

**TL;DR**
- **A skill is cheap until it's used.** Each installed skill adds one index line, about 19 tokens, to every call. Its `SKILL.md` is read only when a task matches, and the agent judges that from the first 57 characters of the description.
- **Prune what you don't use.** `hermes skills config` disables skills globally or per platform, and `hermes skills opt-out` keeps bundled skills out of single-purpose profiles.
- **Don't auto-load big skills.** Pinning the bundled `claude-code` skill with `skills.auto_load` adds about 9,300 tokens to every call.
- **Install from the most trusted source that has what you need.** Inspect before you install, and re-scan with `hermes skills audit`.
- **Let Hermes write skills, then tighten them.** `/learn` or "save that as a skill" gets you a draft. Keep each skill to one job, with numbered steps, pitfalls, and a verification step.
- **Protect what matters.** Use `skills.write_approval` on shared agents, `hermes curator pin` for skills you rely on, and `hermes curator run --dry-run` before trusting any cleanup.

## How skills work

A skill is a folder holding a `SKILL.md` (YAML frontmatter plus markdown instructions) and, optionally, `references/`, `templates/`, `scripts/`, and `assets/`. The format follows the [agentskills.io](https://agentskills.io/specification) open standard. Hermes loads a skill in up to three steps, and you pay for each step separately:

| Level | What the model gets | When | Cost, measured on v0.21.4 |
|---|---|---|---|
| 1. Index | One line per skill: its name and description | Every call | 5,364 bytes (≈ 1,270 tokens) for the 58 bundled skills. Each added skill is one 60–95 byte line (≈ 15–20 tokens). |
| 2. `SKILL.md` | The whole file | When the agent calls `skill_view`, or you type `/<skill-name>` | Bundled median ≈ 10 KB. `obsidian`: 3 KB, 724 tokens. `llm-wiki`: 20 KB, 4,846 tokens. `claude-code`: 35 KB, 9,164 tokens. |
| 3. Supporting file | One file from `references/`, `templates/`, … | Only when the skill says to load it | Whatever that file weighs |

The skills toolset itself (`skills_list`, `skill_view`, `skill_manage`) adds about 5 KB of tool schemas. Tokens were counted with `o200k_base`.

Four details decide how well this works:

- **The index tells the model to load anything "even partially relevant."** That's the actual wording of the instruction Hermes puts above the index. A vague description triggers loads you pay for on unrelated tasks, and a buried trigger causes misses. The description is the most important line you'll write.
- **Only 57 characters survive.** Descriptions longer than 60 characters are cut to 57 plus "..." in the index.
- **Only visible skills cost anything.** Skills restricted to another OS, or whose conditions aren't met, stay out of the index. On Linux, 53 of the 58 bundled skills showed up: four Apple skills are macOS-only, and `sdlc-review` appears only where Kanban is enabled.
- **The index is frozen for the session.** A skill you install or write mid-session isn't in the running prompt. `/reload-skills` rescans and tells the agent what changed on your next message, without clearing the prompt cache. Or start a `/new` session.

Every visible skill is also a slash command, on the CLI and every chat platform. You can stack up to five in front of your instruction:

```text
/test-driven-development /github fix issue #123 and open a PR
```

A skill whose name matches a built-in command (for example, a skill called `plan`) doesn't get a `/<name>` shortcut. Load it with `hermes -s <name>`, or just ask for it by name.

**Where skills live, highest precedence first:** a trusted project's `.hermes/skills/` or `.agents/skills/`, then `~/.hermes/skills/` (per profile), then any `skills.external_dirs`. The first skill with a given name wins.

## Find and install skills

Sources, from most to least trusted:

| Source | Identifier example | Trust level | What that means |
|---|---|---|---|
| Bundled | already installed | `builtin` | 58 skills seeded into every profile, refreshed by `hermes update` |
| Official optional | `official/security/1password` | `official` | Ships in the Hermes repo but isn't installed by default |
| Trusted repos | `openai/skills/k8s` | `trusted` | openai/skills, anthropics/skills, huggingface/skills, NVIDIA/skills |
| Everything else | `skills-sh/…`, `well-known:…`, a direct URL, other GitHub repos, ClawHub, LobeHub, browse.sh | `community` | A warning panel on first install, and stricter scan policy |

```bash
hermes skills browse --source official     # just the official optional skills
hermes skills search kubernetes            # every source (add --source skills-sh etc.)
hermes skills inspect openai/skills/k8s    # read it before you install it
hermes skills install openai/skills/k8s    # scanned, then recorded in skills/.hub/lock.json
hermes skills audit                        # re-scan installed hub skills (--deep adds Python AST checks)
hermes skills check                        # which hub skills changed upstream
hermes skills update                       # reinstall those; skills you edited are skipped
hermes skills uninstall k8s
```

Every hub install goes through a security scanner that looks for data exfiltration, prompt injection, destructive commands, and supply-chain signals. `--force` overrides caution-level findings on a community skill. Nothing overrides a `dangerous` verdict. Hermes copies only `SKILL.md` plus the files it references, and the lock file records the source, content hash, and scan results. For a second, advisory opinion, install NVIDIA's SkillEvaluator binaries: Hermes then runs its Tier 1 checks before each hub install ([details](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills#advisory-skillevaluator-scan)).

> [!WARNING]
> The scanner is a review aid, not a boundary. A skill is a set of instructions the agent follows with your tools and permissions, and a malicious one doesn't even need code, only a sentence. Upstream's [security policy](https://github.com/NousResearch/hermes-agent/blob/v2026.9.21/SECURITY.md) puts the boundary at your review before install, and says that reviewing a skill "means reading its Python code and scripts, not just its SKILL.md description."

Worth knowing:

- **Hub searches hit GitHub's anonymous rate limit** of 60 requests an hour. Put `GITHUB_TOKEN` in `.env` to raise it to 5,000.
- **Installs take effect in the next session.** In a CLI session, `/skills install <id> --now` applies it immediately, but that invalidates the prompt cache.
- **A skill can be an automation.** If an installed skill carries a blueprint, Hermes adds it to `/suggestions` as a proposed cron job. Nothing is scheduled until you accept it.
- **Editing a bundled skill freezes it.** `hermes update` skips skills you've changed so it never overwrites your edits. `hermes skills list-modified` shows them, `hermes skills diff <name>` shows what changed, and `hermes skills reset <name> --restore` returns to the stock version.

### Trim the library

Each skill you don't use still costs an index line on every call. At about 19 tokens a line, 500 skills would add close to 10,000 tokens to every request.

```bash
hermes curator usage                     # use counts for every skill, bundled and hub ones included
hermes skills config                     # interactive: enable/disable, globally or per platform
hermes skills list --enabled-only        # what will actually load (add -p <profile> for another profile)
hermes skills opt-out --remove           # stop seeding bundled skills; delete the unmodified ones
hermes profile create research --no-skills   # a new profile with no bundled skills at all
```

Skills at the bottom of `hermes curator usage`, with no uses after a few weeks, are the ones to disable. `hermes skills config` writes `skills.disabled` and `skills.platform_disabled.<platform>`. The `hermes-agent` skill can't be disabled. `hermes skills opt-in --sync` undoes an opt-out.

For a narrow bot that never needs skills, drop the whole toolset on that platform: `hermes tools disable --platform telegram skills`. Measured on v0.21.4, that removed 12.3 KB from every call (the index, its guidance, and three tool schemas). The trade-off is real: on that platform the agent can no longer load or learn skills.

## Create skills

### Let Hermes write them

- **Ask at the end of a task:** "save what you just did as a skill called deploy-staging."
- **`/learn <what>`** turns anything you can describe into a skill: a local directory, a URL, the workflow you just walked through, or pasted notes. Large sources, like a book or a docs folder, become knowledge-base skills: a lean `SKILL.md` with an index, plus one distilled file per topic under `references/`. Running `/learn` again with new material on the same topic updates that skill instead of creating a duplicate. It works in the CLI, on chat platforms, in the TUI, and from the dashboard's **Learn a skill** button.
- **The background review** can create or patch skills on its own. It considers skills after every 10 tool-calling iterations (`skills.creation_nudge_interval`), alongside its memory pass ([chapter 05](./05-token-budget.md#the-background-review)). `hermes config set` warns that `skills.creation_nudge_interval` isn't a recognized key, but the agent does read it from `config.yaml` (`agent/agent_init.py` at v0.21.4).

New skills land in `~/.hermes/skills/`, or wherever `skills.create_dir` points, for example a git-tracked folder you share across machines. The agent works under its own rules: a new skill's description must fit 60 characters, and pitfalls are written as "a rule plus why", never as an incident diary.

### Review what it writes

On a shared or production agent, stage skill changes for approval:

```yaml
skills:
  write_approval: true    # stage every skill write: create, patch, delete, supporting files
```

```text
/skills pending          # staged writes, with a one-line gist each
/skills diff <id>        # the full unified diff (easiest to read on the CLI or dashboard)
/skills approve <id>     # or 'all'
/skills reject <id>
```

Staged writes survive restarts under `~/.hermes/pending/skills/`. On chat platforms, `/skills` only exists while the gate is on. Separately, `skills.guard_agent_created: true` adds a content scanner for credential harvesting and injection patterns in agent-written skills. It's off by default because it flagged too much legitimate work.

### Write one by hand

Create the folder and a `SKILL.md`. This complete example passes Hermes' own create-time validation and its skill linter with zero findings, and shows up in the index as a 70-byte line:

```text
~/.hermes/skills/software-development/release-notes/
└── SKILL.md
```

```markdown
---
name: release-notes
description: Draft user-facing release notes from git history.
version: 1.0.0
author: Your Name
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, release, writing]
    related_skills: []
---

# Release Notes

Turns the commits since the last tag into short, user-facing release notes.

## When to Use
- The user asks for release notes, a changelog entry, or "what changed since vX".
- Don't use for: commit messages or PR descriptions.

## Procedure
1. Find the previous tag with `terminal`: `git describe --tags --abbrev=0`. Done when you have a tag name.
2. List the range: `git log <tag>..HEAD --no-merges --format='%h %s'`. Done when every commit is listed.
3. Sort each user-visible change into Added, Changed, or Fixed. Drop CI, formatting, and dependency-bump noise.
4. Write one imperative line per change ("Add…", "Fix…"), newest first. Save to a file only if asked.

## Pitfalls
- Commit subjects describe code, not impact. When a subject is vague, read `git show --stat <sha>`, because readers need the effect, not the refactor.
- Squash-merged repos hide sub-commits. Use the squash subject; don't expand the branch.

## Verification
Every line maps to at least one commit in the range, and nothing outside the range appears.
```

Then check it:

```bash
hermes skills list --source local      # shows release-notes as local and enabled
hermes prompt-size --json              # skills_breakdown lists its index line and file size
```

Frontmatter reference, checked against the v0.21.4 loader and validator:

| Field | Required | Rules |
|---|---|---|
| `name` | Yes | Lowercase letters, digits, `-`, `_`, `.`; starts with a letter or digit; up to 64 characters. Stick to hyphens and match the folder name, because the linter flags a mismatch. |
| `description` | Yes | Up to 1,024 characters are accepted, but the index keeps 57, and skills the agent creates must fit in 60. One sentence, trigger or capability first, ending with a period. Quote it if it contains a colon. |
| `version`, `author`, `license` | No | The linter warns when they're missing. |
| `platforms` | No | Any of `macos`, `linux`, `windows`. The skill is hidden on other systems. Omit it for all. |
| `metadata.hermes.tags`, plus `related_skills` under `metadata.hermes` | No | Search keywords and cross-links |
| `metadata.hermes.requires_toolsets`, `requires_tools`, `fallback_for_toolsets`, `fallback_for_tools` | No | Show the skill only when those tools are (or aren't) available. The official optional `duckduckgo-search` skill appears only when the `web` toolset is missing. |
| `required_environment_variables` | No | A list of `name`, `prompt`, `help`, `required_for`. The CLI asks for missing values securely when the skill loads, and the values pass through to `terminal` and `execute_code`. |
| `metadata.hermes.config` | No | Non-secret settings (`key`, `description`, `default`, `prompt`), stored under `skills.config.*` |
| `metadata.hermes.blueprint` | No | Makes the skill an installable automation (a suggested cron job) |

The hard limits, enforced when the agent writes a skill: the file must start with `---` on its very first line, the frontmatter must be a YAML mapping closed by a `---` line, the body can't be empty, `SKILL.md` can't exceed 100,000 characters, and each supporting file must stay under 1 MiB inside `references/`, `templates/`, `scripts/`, or `assets/`. Skill discovery parses the frontmatter from the first 4,000 characters, so keep it short.

## Make skills lean and reliable

These rules mirror the advisory linter Hermes runs whenever the agent creates a skill, plus upstream's own authoring standard:

1. **One job per skill.** "Deploy the blog to Cloudflare Pages", not "DevOps".
2. **Trigger first, within 60 characters.** The index is how the agent decides, and it sees 57 characters.
3. **A `## When to Use` section near the top**, including a "Don't use for" line.
4. **Numbered steps that end in something checkable.** "Done when every commit is listed" beats "summarize the changes".
5. **Pitfalls as rule plus reason.** No incident stories, dates, or issue numbers. The rule has to stand on its own.
6. **A `## Verification` section** that proves the result, not just claims it.
7. **Name Hermes tools, not shell utilities:** `search_files` rather than grep, `read_file` rather than cat, `patch` rather than sed.
8. **Aim for about 100 lines** for a simple skill and 200 for a complex one, which is upstream's own authoring target.
9. **No scaffolding** in the skill folder: no README, changelog, install script, or `.env` file.
10. **No secrets in the file.** Declare them in `required_environment_variables`.
11. **Set `platforms`** if a bundled script depends on POSIX-only features.

Move bulk out of `SKILL.md`. Reference material goes in `references/`, named by topic and extended in place rather than one file per session. Deterministic logic goes in `scripts/`, so the model runs a tested script instead of rewriting a parser every time:

```text
~/.hermes/skills/devops/deploy-blog/
├── SKILL.md                     # when, steps, pitfalls, verification
├── references/
│   └── cache-purge.md           # loaded only when step 4 fails
└── scripts/
    └── check_live.sh            # run by path, returns OK or FAIL
```

```markdown
4. Purge the CDN cache. If the purge API errors, load `references/cache-purge.md`.
5. Run `bash ${HERMES_SKILL_DIR}/scripts/check_live.sh https://blog.example.com`. Done when it prints OK.
```

When a skill loads, Hermes replaces `${HERMES_SKILL_DIR}` with the skill's absolute path (`skills.template_vars: false` turns that off). Inline shell snippets written as `` !`cmd` `` run on the host without approval, which is why `skills.inline_shell` is off by default. Leave it off unless you wrote every skill on the machine.

## Always-loaded skills and bundles

| Mechanism | What loads | What it costs | Use it for |
|---|---|---|---|
| A normal skill | The file, when a task matches | An index line per call, plus the file when used | Almost everything |
| `/<skill-name>`, stacked or not | The file, into this message | The file, once | You know what you need |
| `hermes -s a,b` | The files, for one CLI session | The files, for that session | A focused session |
| `/<bundle-name>` | Several files, into this message | The files, once | Combinations you use repeatedly |
| `skills.auto_load` | The file, in the system prompt of every new session | The whole file on every call (cached) | A small skill that must always apply |

`skills.auto_load` is resolved once per session, so the prompt stays cache-stable and edits apply to the next session. Missing or disabled skills are skipped with a warning, `--ignore-rules` suppresses the list, and subagents and background reviews don't get it. The cost is the catch. Measured on v0.21.4, auto-loading the 1.3 KB `release-notes` skill added 1.8 KB to every call, while auto-loading `claude-code` took the system prompt from 14.9 KB to 50.6 KB, about 9,300 more tokens per call.

```yaml
skills:
  auto_load:
    - house-style        # keep this list to small skills that apply to every task
```

A bundle is a named group of skills behind one slash command:

```bash
hermes bundles create ship-it --skill release-notes --skill github -d "Release notes, then the GitHub release"
hermes bundles list
```

Then type `/ship-it v1.5` on any surface. Bundles live as YAML in `~/.hermes/skill-bundles/` and `/bundles` lists them in chat. A bundle wins over a skill with the same name, and missing skills are skipped with a note. Because the skills arrive in your message, not the system prompt, a bundle never invalidates the cache.

## The curator

The curator keeps agent-made skills from piling up. Know its scope before you rely on it.

**It only manages skills the background review created.** Everything else is left alone: bundled skills (unless you set `curator.prune_builtins: true`), hub installs, anything created at your request (including `/learn`), hand-written skills, and project or external-directory skills. `hermes curator status` shows managed versus unmanaged counts, and `hermes curator adopt <name>` hands an unmanaged skill over.

**When it runs:** at most every 7 days, and only after 2 idle hours. On a new install, its first real pass waits one full interval.

**What it does:**

1. **A deterministic pass**, free and always on. Skills unused for 14 days become stale, and after 30 days they move to `~/.hermes/skills/.archive/`. Skills that were never used get a grace period. Pinned skills and skills any cron job references are skipped. It never deletes anything.
2. **An LLM consolidation pass**, off by default. It merges overlapping skills into broader ones and patches drift. The docs put a full sweep at 50–100 API calls, so route `auxiliary.curator` to a cheap model before you turn it on. Hermes snapshots the skills tree before each consolidation run.

```yaml
curator:
  enabled: true
  interval_hours: 168       # at most weekly, and only when idle
  min_idle_hours: 2
  stale_after_days: 14
  archive_after_days: 30
  consolidate: false        # the LLM merge pass; costs auxiliary tokens
  prune_builtins: false     # true = also archive unused bundled skills
  backup:
    keep: 2                 # snapshots kept (taken before consolidation runs)
```

```bash
hermes curator status               # managed vs unmanaged, five least recently used
hermes curator run --dry-run        # preview; changes nothing
hermes curator pin deploy-blog      # never auto-archive it (also blocks the agent from deleting it)
hermes curator list-archived
hermes curator restore deploy-blog  # bring an archived skill back
hermes curator run --consolidate    # one LLM merge pass, this time only
hermes curator ledger               # every skill change, by curator, agent, or you
hermes curator rollback <entry-id>  # undo exactly one change
```

`hermes curator pin` refuses bundled and hub skills. On your own skills it works whether or not the curator manages them, and it stops the agent from deleting them. The same subcommands are available as `/curator` in any session. Archived skills are kept forever by default. To bound `.archive/`, set `curator.archive_ttl_days` (for example `180`) and run `hermes curator purge --dry-run`, then `hermes curator purge`. Purging never happens automatically, and each purged skill is captured in the ledger first.

> [!NOTE]
> Two upstream texts lag the code. The lifecycle list on the official curator page still says 30 days to stale and 90 to archive (the defaults have been 14 and 30 since v0.21.3). And `hermes curator --help` says a snapshot is taken before every real run, while v0.21.4 snapshots only before consolidation runs. A plain prune just moves folders into `.archive/`, and every move is in the ledger.

## Project skills and shared libraries

**Project skills.** A repo can carry skills in `.hermes/skills/` or `.agents/skills/`. Hermes finds them but won't load them until you trust the repo, because they're instructions from whoever committed them:

```bash
hermes skills trust            # from inside the repo (or pass its path)
hermes skills untrust
```

Trusted roots are stored in `skills.trusted_project_dirs`, and `skills.project_discovery: false` turns the feature off. Inside that repo, project skills take precedence over your own and are tagged `[project]` in the index. Each one is re-scanned whenever it changes, and one judged dangerous is quarantined and won't load. The curator never touches them, and cron jobs inherit your trust decision based on the job's working directory.

**Sharing across machines and people:**

| Method | How |
|---|---|
| A shared folder | Point `skills.external_dirs` at it. Your local skills win name clashes. It isn't read-only: if Hermes can write there, the agent can edit those skills. |
| A symlink | Link one skill folder from a git checkout into `~/.hermes/skills/<category>/`. Discovery follows symlinks, and the agent's patches show up in `git diff`. |
| New skills to a shared folder | `skills.create_dir`, for example a git-tracked directory |
| A tap | A GitHub repo with a `skills/` folder. Others run `hermes skills tap add owner/repo` (and `tap list`, `tap remove`), then install from it. `hermes skills publish` pushes one skill. |
| Skill Sync | `hermes sync` moves the skills you opt in (`hermes sync enable <skill>`) between devices through your Nous account, and in an organisation pulls shared skills and lets you propose yours. At v0.21.4 it's limited access: without it, the commands report that sync isn't enabled for your account. `hermes sync status` shows where you stand. |

This repo's [`skills/`](../skills/) folder holds installable example skills. Copy one into `~/.hermes/skills/`, or install it straight from GitHub with `hermes skills install OnlyTerp/hermes-optimization-guide/skills/<name>`, which runs the same scan as any community skill.

## Verify it

```bash
hermes skills list --enabled-only    # what will load in this profile
hermes prompt-size                   # skills index size (--json adds per-skill bytes)
hermes curator status                # what the curator manages and what's going stale
hermes skills audit                  # re-scan hub installs
```

In a session, `/context all` lists every skill's index cost next to its `SKILL.md` load cost. Good looks like a short list of enabled skills you actually use, descriptions that each start with the trigger, and no surprise entries under `skills.auto_load`.

## Gotchas

- **Skills missing from Telegram's `/` menu.** Telegram caps the command list, and Hermes builds the menu at gateway start. Disable skills you don't need there with `hermes skills config`, then `hermes gateway restart`. `/commands` pages through everything. ([FAQ](https://hermes-agent.nousresearch.com/docs/reference/faq#managing-skills-on-telegram-slash-command-limit))
- **"Skill not found" in a cron job.** The skill must be installed in the profile that runs the job, and the job must use the exact folder name from `hermes skills list`. Cron also disables the `clarify` toolset, so skills that ask questions stall. ([cron troubleshooting](https://hermes-agent.nousresearch.com/docs/guides/cron-troubleshooting#skill-loading-failures))
- **Your hand-written and `/learn` skills never age out.** That's by design. The curator only manages what the background review created. ([docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/curator#what-agent-created-means))
- **`--force` doesn't override a `dangerous` scan verdict**, and it shouldn't. ([docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills#trust-levels))
- **Rate-limit errors during search or install** mean anonymous GitHub API access. Add `GITHUB_TOKEN` to `.env`. ([docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills#update-lifecycle))
- **Some official examples name skills that no longer ship.** `github-pr-workflow` and `github-code-review` appear in the upstream docs but aren't bundled in v0.21.4, and `/plan` became a built-in command. Check `hermes skills list` before building a bundle around a name.

## Go deeper

- Official: [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) · [Creating Skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills) · [Working with Skills](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills) · [Curator](https://hermes-agent.nousresearch.com/docs/user-guide/features/curator) · [Bundled catalog](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) · [Optional catalog](https://hermes-agent.nousresearch.com/docs/reference/optional-skills-catalog)
- In this guide: [05 · The background review](./05-token-budget.md#the-background-review) · [06 · Personality & Context Files](./06-personality-and-context.md) · [07 · Memory](./07-memory.md) · [11 · Automation](./11-automation.md) · [13 · Security](./13-security.md)

---
[← Previous: 07 · Memory](./07-memory.md) · [Guide index](../README.md#the-guide) · [Next: 09 · Tools, MCP & Plugins →](./09-tools-mcp-plugins.md)
