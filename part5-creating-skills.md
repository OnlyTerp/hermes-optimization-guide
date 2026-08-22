# Part 5: On-the-Fly Skills (Let Hermes Build Its Own Playbook)

*Ask Hermes to create a new skill, and it saves the workflow permanently — no manual file editing needed.*

---

## What Are Skills

Skills are procedural knowledge — step-by-step instructions that teach Hermes how to handle specific tasks. Unlike memory (which is factual), skills are **how-to guides** the agent follows automatically.

> **See also:** Skills pair naturally with [MCP Servers (Part 17)](./part17-mcp-servers.md) — skills encode *your* workflow, MCP servers add *external tools*. Combine them: a skill that calls a GitHub MCP to open an issue, a Postgres MCP to check data, then a [Claude Code delegation (Part 18)](./part18-coding-agents.md) to implement the fix.

**Skills vs Memory:**

| | Skills | Memory |
|---|---|---|
| **What** | How to do things | What things are |
| **When** | Loaded on demand, only when relevant | Injected every session automatically |
| **Size** | Can be large (hundreds of lines) | Should be compact (key facts only) |
| **Cost** | Zero tokens until loaded | Small but constant token cost |
| **Examples** | "How to deploy to Kubernetes" | "User prefers dark mode, lives in EST" |
| **Who creates** | You, the agent, or installed from Hub | The agent, based on conversations |

**Rule of thumb:** If you'd put it in a reference document, it's a skill. If you'd put it on a sticky note, it's memory.

---

## The Skill Creation Workflow

Hermes can create skills itself. Here's how it works:

### 1. Do a Complex Task

Ask Hermes to do something multi-step. For example:

```
Set up a monitoring script that checks my server health every 5 minutes
and alerts me on Telegram if CPU goes above 90% or memory above 80%.
```

Hermes will:
- Research the best approach
- Write the script
- Test it
- Set up the cron job
- Fix any issues along the way

### 2. Hermes Offers to Save It

After completing a complex task (5+ tool calls), fixing a tricky error, or discovering a non-trivial workflow, Hermes will offer:

```
This was a multi-step process. Want me to save this as a skill
so I can reuse it next time?
```

### 3. Say Yes

The agent uses `skill_manage` to create a new skill file at `~/.hermes/skills/<category>/<skill-name>/SKILL.md`. This file contains:

- **When to use** — the trigger conditions
- **Exact steps** — commands, files, configurations
- **Pitfalls** — problems encountered and how to fix them
- **Verification** — how to confirm it worked

### 4. It's Available Immediately

The skill appears in `skills_list` and becomes available as a slash command. Next time you (or the agent) encounter a similar task, the skill is loaded automatically.

---

## How to Ask Hermes to Create a Skill

### Direct Request

Just ask:

```
Create a skill for deploying Docker containers to my server.
Include the build, push, SSH deploy, and health check steps.
```

Hermes will:
1. Research the best deployment workflow
2. Create the skill directory at `~/.hermes/skills/`
3. Write `SKILL.md` with the full procedure
4. Add reference files, templates, or scripts if needed
5. Test that it works

### After Solving a Problem

If Hermes just solved a tricky problem for you:

```
Save that as a skill so you remember how to do it next time.
```

The agent captures:
- The exact steps taken
- The errors encountered and fixes
- The configuration needed
- Edge cases discovered

### Iterative Improvement

If a skill is outdated or incomplete:

```
That skill doesn't cover the new deployment method. Update it
with what we just learned.
```

Hermes patches the skill with new information using `skill_manage(action='patch')`.

---

## Curator (v0.12): Keep the Skill Library From Rotting

The old skill failure mode was predictable: after a month of "save that as a skill," `~/.hermes/skills/` filled with duplicates, stale commands, and one-off notes that should have been memory. Hermes v0.12 adds **Curator** to clean that up.

Curator is **on by default** — it is not a cron daemon. On CLI session start and on a recurring tick inside the gateway, Hermes checks whether enough time has passed (`curator.interval_hours`, default 168 = weekly) and the agent has been idle long enough (`curator.min_idle_hours`, default 2); if both, it runs a background pass that never touches your active conversation.

Run (or preview) it manually — `--dry-run` shows the full report with zero mutations:

```bash
hermes curator status            # last run, counts, pinned list, next stale candidates
hermes curator run --dry-run     # preview only — report without mutations
hermes curator run               # trigger a pass now (prune-only unless consolidation is on)
hermes curator run --consolidate # force the LLM consolidation pass for this one run
hermes curator pause             # stop runs until resumed
hermes curator resume
```

What Curator does:

- **Lifecycle: `active → stale → archived`.** Skills unused for `curator.stale_after_days` (30) are marked stale; unused for `archive_after_days` (90) move to `~/.hermes/skills/.archive/`. It **never auto-deletes** — the worst outcome is archival, which is fully recoverable.
- **Pins.** `hermes curator pin <skill>` protects a skill from both the curator's auto-transitions and the agent's `skill_manage(delete)`. Skills referenced by any cron job (even paused) are protected from auto-transitions too.
- **LLM consolidation is opt-in.** `curator.consolidate: true` (or `--consolidate`) enables the opinionated pass that merges near-duplicates and builds umbrella skills, and it costs aux-model tokens. The default deterministic pruning is free — zero API calls.
- **Prunes bundled (built-in) skills by default** after `archive_after_days` of non-use (`curator.prune_builtins: true`); hub-installed skills are always off-limits. Set `curator.prune_builtins: false` to go back to agent-created-only.
- **Backups before every pass.** A `tar.gz` snapshot lands under `~/.hermes/skills/.curator_backups/`, so a whole pass is undoable with `hermes curator rollback` (`--list`, `--id <ts>`). A per-mutation audit ledger adds single-edit rollback: `hermes curator ledger` / `hermes curator rollback <entry-id>`.
- **Only agent-created skills are managed.** The background self-improvement loop marks its own skills as agent-created; hand-written skills and skills you asked for are left alone unless you hand them over with `hermes curator adopt <skill>` (see `hermes curator list-unmanaged`).

Good operating pattern:

1. **Pin** your production runbooks and irreplaceable workflows (`hermes curator pin <skill>`).
2. Run `hermes curator run --dry-run` after major upgrades to see what's aging.
3. Let it archive one-off skills, not memory facts or project instructions.
4. Ask Hermes to update a skill immediately after a failed run; don't wait for Curator to infer the fix later.
5. Review `hermes curator status` monthly — it lists the five least-recently-used skills, i.e. what's likely to go stale next.

Curator is a librarian, not a teammate. It keeps the shelves useful; you still decide what knowledge is important.

---

## Skill Structure

Every skill is a directory with a `SKILL.md` file:

```
~/.hermes/skills/
├── my-category/
│   ├── my-skill/
│   │   ├── SKILL.md              # Main instructions (required)
│   │   ├── references/           # Supporting docs (optional)
│   │   │   ├── api-docs.md
│   │   │   └── examples.md
│   │   ├── templates/            # Template files (optional)
│   │   │   └── config.yaml
│   │   └── scripts/              # Executable scripts (optional)
│   │       └── setup.sh
│   └── another-skill/
│       └── SKILL.md
└── openclaw-imports/             # Migrated from OpenClaw
    └── old-skill/
        └── SKILL.md
```

`~/.hermes/skills/` is the single source of truth; bundled, hub-installed, and agent-created skills all land here (each profile keeps its own under its `HERMES_HOME`). Two sidecar areas matter for maintenance: `~/.hermes/skills/.hub/` holds Skills Hub state (lock + audit log), and the Curator moves long-unused skills to `~/.hermes/skills/.archive/` and snapshots the tree to `.curator_backups/`. You can also point Hermes at **external skill directories** (`skills.external_dirs` in `config.yaml`) and repos can ship **project-local skills** under `<repo>/.hermes/skills/` — those load only after you trust the repo with `hermes skills trust`.

**Required frontmatter:** every `SKILL.md` needs `name` and a short `description` (the description rides in the prompt index every session — keep it ≤60 characters and self-contained, because skills_list truncates at 57). `version` and `metadata.hermes.*` are optional but encouraged.

### SKILL.md Format

```markdown
---
name: my-skill                 # Required
description: Brief description of what this skill does   # Required — keep ≤60 chars
version: 1.0.0
platforms: [macos, linux]      # Optional — restricts the skill to specific OSes
metadata:
  hermes:
    tags: [deployment, docker, devops]
    category: my-category
    # Optional — conditional activation (fallback skills):
    # fallback_for_toolsets: [web]   show only when a toolset is unavailable
    # requires_toolsets: [terminal]  show only when a toolset is available
---

# My Skill

## When to Use
Use this skill when the user asks to deploy containers or manage Docker services.

## Procedure
1. Check Docker is running: `docker ps`
2. Build the image: `docker build -t app:latest .`
3. Push to registry: `docker push registry/app:latest`
4. SSH to server and pull: `ssh server 'docker pull registry/app:latest && docker-compose up -d'`
5. Health check: `curl -f http://server:8080/health`

## Pitfalls
- Docker build fails if Dockerfile has COPY paths wrong — fix by checking working directory
- SSH needs key-based auth — set up with `ssh-keygen` and `ssh-copy-id`
- Health check may take 10s to respond — add retry logic

## Verification
Run `docker ps` on the server and confirm the container is `Up` and healthy.
```

---

## Using Skills

### Via Slash Command

Every skill becomes a slash command automatically:

```bash
/my-skill deploy the latest version to production
```

### Via Natural Conversation

Just ask Hermes to use a skill:

```
Use the docker-deploy skill to push the new build.
```

Hermes loads the skill via `skill_view` and follows its instructions.

### Automatic Loading

Hermes scans available skills at session start. When your request matches a skill's "When to Use" conditions, it loads automatically — you don't need to explicitly invoke it.

---

## Managing Skills

### List All Skills

```bash
/skills
# Or
hermes skills list
```

### Search and Discover

```bash
hermes skills search docker                # search all hub sources
hermes skills search react --source skills-sh
hermes skills browse --source official    # browse official optional skills
hermes skills inspect openai/skills/k8s    # preview before installing
```

### Configure Skills (`hermes skills config`)

```bash
hermes skills config
```

Opens an interactive picker to enable/disable individual skills (the slash-command surface and `skills_list` index follow your choices).

### Install from the Skills Hub

Every install runs a **security scan** (data exfiltration, prompt injection, destructive commands, supply-chain signals). Trust levels: `builtin`/`official` (always trusted), `trusted` (OpenAI/Anthropic/HF/NVIDIA repos), `community` (everything else — non-dangerous findings can be overridden with `--force`, `dangerous` verdicts never can):

```bash
hermes skills install official/security/1password   # official optional skill
hermes skills install openai/skills/k8s             # direct from a GitHub repo
hermes skills install skills-sh/vercel-labs/json-render/json-render-react
hermes skills install https://example.com/SKILL.md  # direct URL (+ referenced files)
```

`GITHUB_TOKEN` in `.env` raises the GitHub API rate limit from 60 to 5,000 req/hour if hub searches start erroring.

### Update a Skill

If a skill is outdated or missing steps:

```
Update the docker-deploy skill — we learned that the health check
needs a 30-second timeout, not 10.
```

Hermes patches the skill with `skill_manage(action='patch')`. For hub-installed skills, track upstream drift and refresh:

```bash
hermes skills check              # which installed hub skills changed upstream
hermes skills update            # re-install only those (skips your local edits)
hermes skills reset my-skill    # un-stick a bundled skill marked "user-modified"
```

### Skill Bundles: One Command, Many Skills

Skill bundles are tiny YAML files that group several skills under a single slash command — `/<bundle-name>` loads them all at once. Great for recurring task profiles ("every backend change: review + TDD + PR").

```bash
hermes bundles create backend-dev \
  --skill github-code-review \
  --skill test-driven-development \
  --skill github-pr-workflow \
  -d "Backend feature work — review, test, PR workflow"
```

Then in any surface:

```
/backend-dev refactor the auth middleware
```

Bundles live in `~/.hermes/skill-bundles/<slug>.yaml` (`name`, `description`, `skills:` list, optional `instruction:`), are managed with `hermes bundles list|show|create|delete|reload`, listed in chat via `/bundles`, and resolve every listed skill on invocation — missing skills are skipped, not fatal. If a bundle slug collides with a skill name, the bundle wins.

---

## Real-World Skill Examples

### Example 1: Server Monitoring

```
Create a skill that monitors my server: check CPU, memory, and disk
usage via SSH, log results to a CSV, and alert on Telegram if anything
exceeds thresholds.
```

Hermes creates a skill with:
- SSH connection commands
- Resource check scripts
- CSV logging format
- Telegram alert integration
- Threshold configuration

### Example 2: Code Review

```
Create a skill for reviewing Python pull requests. It should check
for security issues, performance problems, and style violations.
```

Hermes creates a skill with:
- `git diff` analysis steps
- Security pattern checks
- Performance anti-pattern detection
- Style guide references

### Example 3: Lead Research

```
Create a skill that researches companies: find their website, check
LinkedIn for key contacts, look at recent news, and compile a one-page summary.
```

Hermes creates a skill with:
- Web search queries to use
- LinkedIn search patterns
- News aggregation approach
- Summary template

---

## Tips for Better Skills

**Be specific about the task.** "Deploy Docker containers" is too vague. "Deploy a Python Flask app to a VPS using Docker Compose with health checks" gives the agent enough detail to write a precise skill.

**Include examples.** When asking for a skill, show an example of the desired output. This helps the agent write better templates.

**Let the agent discover pitfalls.** Don't prescribe the exact steps. Let Hermes figure out the workflow and capture what goes wrong — those pitfall notes are the most valuable part of the skill.

**Update skills when they go stale.** If you use a skill and hit issues not covered by it, tell Hermes to update it with what you learned. Skills that aren't maintained become liabilities.

**Use categories.** Organize skills into subdirectories (`~/.hermes/skills/devops/`, `~/.hermes/skills/research/`, etc.). This keeps the list manageable and helps the agent find relevant skills faster.

**Keep skills focused.** A skill that tries to cover "all of DevOps" will be too long and too vague. A skill that covers "deploy a Python app to Fly.io" is specific enough to be genuinely useful.

**Give every skill a ≤60-character description.** The description of *every* skill rides along in the prompt so the agent can pick between them — long descriptions tax every turn. This especially applies to `/learn`-generated skills ([Part 26](./part26-moa-verification.md)), whose auto-written descriptions tend to be paragraphs: trim them after creation. And before writing a skill at all, check whether a built-in tool already does the job.

**Gate self-written skills in production.** `/skills approval on` (config: `skills.write_approval`) makes the agent propose skill creations/updates instead of applying them silently — writes are staged and reviewed with `/skills pending`, `/skills diff <id>`, `/skills approve <id>`, `/skills reject <id>`. Pair it with `/memory approval on` on any shared or long-running agent ([Part 7](./part7-memory-system.md)).

---

## How Hermes Decides to Save Skills

The agent saves skills automatically after:

1. **Complex tasks (5+ tool calls)** — multi-step workflows worth preserving
2. **Tricky error fixes** — debugging steps that took iteration to solve
3. **Non-trivial discoveries** — new approaches or configurations found during work
4. **User request** — when you explicitly say "save this as a skill"

The agent uses `skill_manage(action='create')` to write the skill, including:
- Trigger conditions
- Numbered steps with exact commands
- Pitfalls section (from actual errors encountered)
- Verification steps

---

## What's Next

You've now got the full picture:
- **[Part 1: Setup](./part1-setup.md)** — Install and configure
- **[Part 2: OpenClaw Migration](./part2-openclaw-migration.md)** — Bring your old data
- **[Part 3: LightRAG](./part3-lightrag-setup.md)** — Graph-based knowledge
- **[Part 4: Telegram](./part4-telegram-setup.md)** — Mobile access
- **[Part 5: On-the-Fly Skills](./part5-creating-skills.md)** — Self-improving workflows

Start with setup, add what you need, and let Hermes build the rest.
