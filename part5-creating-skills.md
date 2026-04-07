# Part 5: On-the-Fly Skills (Let Hermes Build Its Own Playbook)

*Ask Hermes to create a new skill, and it saves the workflow permanently — no manual file editing needed.*

---

## What Are Skills

Skills are procedural knowledge — step-by-step instructions that teach Hermes how to handle specific tasks. Unlike memory (which is factual), skills are **how-to guides** the agent follows automatically.

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

### SKILL.md Format

```markdown
---
name: my-skill
description: Brief description of what this skill does
version: 1.0.0
metadata:
  hermes:
    tags: [deployment, docker, devops]
    category: my-category
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

### Search for a Skill

```bash
/skills search docker
/skills search deployment
```

### View a Skill's Content

```bash
/skills view my-skill
```

### Enable/Disable Per Platform

```bash
hermes skills
```

This opens an interactive TUI where you can enable or disable skills per platform (CLI, Telegram, Discord, etc.). Useful when you want certain skills only available in specific contexts.

### Install from the Hub

Official optional skills (heavier or niche):

```bash
/skills install official/research/arxiv
/skills install official/creative/songwriting-and-ai-music
```

### Update a Skill

If a skill is outdated or missing steps:

```
Update the docker-deploy skill — we learned that the health check
needs a 30-second timeout, not 10.
```

Hermes patches the skill with `skill_manage(action='patch')`.

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
