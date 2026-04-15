# Part 7: The Memory System (Three Tiers That Actually Work)

*Hermes has three memory systems. Most people only know about one.*

---

## The Three Tiers

| Tool | What It Does | When It Fires | Cost |
|------|-------------|---------------|------|
| `memory` | Persistent facts across all sessions | User preferences, environment, lessons learned | Free (local) |
| `session_search` | Search past conversation transcripts | "What did we decide about X?" or "Remember when we..." | Free (local) |
| `skill_manage` | Procedural memory — reusable workflows | After fixing a bug, building something complex, or discovering a new approach | Free (local) |

All three are **local-first**. No API calls, no embedding costs. They use SQLite and full-text search.

## Tier 1: memory (Persistent Facts)

The `memory` tool saves durable facts that get injected into every future session.

**What to save:**
- User preferences ("Terp hates manual steps")
- Environment details ("5090 PC at 192.168.1.67, port 11434")
- Tool quirks ("PowerShell needs -Encoding utf8 for Unicode files")
- Stable conventions ("Use OnlyTerp for GitHub repos")

**What NOT to save:**
- Task progress (use session_search to recall)
- Temporary state (TODO lists, current status)
- Anything that changes frequently

**Format:** Keep entries under 2000 chars total. Be compact. These get injected into every message.

```python
# Good
memory(action="add", target="memory", content="OpenClaw migrated. LightRAG: 4528 entities, float16 vectors (4096d). Telegram bot 8624585264, group -5216536760.")

# Bad — too verbose, task-specific
memory(action="add", target="memory", content="Today I worked on the lead gen pipeline. First I fixed the API key issue, then I updated the quality gate scoring to use a new algorithm, then I tested with 50 leads...")
```

## Tier 2: session_search (Conversation Recall)

`session_search` searches your entire conversation history across all past sessions.

**Two modes:**

```python
# Browse recent sessions (no cost, instant)
session_search()

# Search for specific topics (uses LLM to summarize)
session_search(query="hermes optimization guide github")
session_search(query="LightRAG setup OR embedding model")
```

**When to use it:**
- User says "we did this before" or "remember when"
- You suspect relevant cross-session context exists
- You want to check if you've solved a similar problem before

**Key insight:** session_search is your recency backup. memory is for facts that will still matter in 6 months. If a fact is only relevant to the current project phase, session_search is better than bloating memory.

## Tier 3: skill_manage (Procedural Memory)

`skill_manage` saves reusable workflows as skills. This is how Hermes learns.

**When to create a skill:**
- After a complex task (5+ tool calls)
- After fixing a tricky error
- After discovering a non-trivial workflow
- When the user asks you to remember a procedure

```python
# Create a new skill
skill_manage(
    action="create",
    name="supabase-migrate",
    content="---\ndescription: Run Supabase SQL migrations via Management API\n---\n\n# Supabase Migration\n\n1. Read the SQL file from supabase/migrations/\n2. Use Python http.client to POST to Management API...",
    category="devops"
)

# Patch an existing skill when you find issues
skill_manage(
    action="patch",
    name="supabase-migrate",
    old_string="Use requests.post",
    new_string="Use http.client (requests has timeout issues with Supabase)"
)
```

**Key rules:**
- Skills must have trigger conditions — when should this skill load?
- Skills must have numbered steps — what exactly to do?
- Skills must have pitfalls — what can go wrong?
- Patch skills immediately when you find issues — don't wait to be asked

## How They Work Together

```
User asks a question
    ↓
memory injects persistent context (user prefs, environment)
    ↓
session_search recalls relevant past conversations (if needed)
    ↓
skill_manage loads procedural knowledge (if triggered)
    ↓
Agent has full context → better answer
```

**The hierarchy:** memory is always on. session_search is on-demand. skill_manage is triggered by task matching.

## Anti-Patterns

| Don't Do This | Do This Instead |
|--------------|-----------------|
| Save task progress to memory | Use session_search to recall |
| Create a skill for a one-off task | Just do it, skip the skill |
| Dump raw data into memory | Save compact, durable facts |
| Search session_search for everything | Check memory first, it's free and instant |
| Let skills go stale | Patch them immediately when outdated |

---

*Memory is what separates a stateless chatbot from an actual agent. Use all three tiers.*
