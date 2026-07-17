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
- Environment details ("GPU box at 192.0.2.10, port 11434")
- Tool quirks ("PowerShell needs -Encoding utf8 for Unicode files")
- Stable conventions ("Use OnlyTerp for GitHub repos")

**What NOT to save:**
- Task progress (use session_search to recall)
- Temporary state (TODO lists, current status)
- Anything that changes frequently

**Format:** Keep entries under 2000 chars total. Be compact. These get injected into every message.

**Batch operations (v0.17):** the `memory` tool applies multiple add/update/delete operations **atomically in one call**. Bulk cleanups are one round-trip instead of ten — and a failed batch doesn't leave memory half-edited.

```python
# Good
memory(action="add", target="memory", content="OpenClaw migrated. LightRAG: 4528 entities, float16 vectors (4096d). Telegram bot 123456789, group -100EXAMPLE.")

# Bad — too verbose, task-specific
memory(action="add", target="memory", content="Today I worked on the lead gen pipeline. First I fixed the API key issue, then I updated the quality gate scoring to use a new algorithm, then I tested with 50 leads...")
```

## Tier 2: session_search (Conversation Recall)

`session_search` searches your entire conversation history across all past sessions.

**Two modes:**

```python
# Browse recent sessions (no cost, instant)
session_search()

# Search for specific topics (local full-text search — free and instant since v0.15)
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

## Auditing What the Agent Learned (v0.18)

The memory system is no longer write-only. Two v0.18 additions close the loop:

- **`/journey`** — a timeline of every memory and skill Hermes has accumulated; edit or delete any entry in place. The desktop app renders it as a playable **memory graph**.
- **`/learn <anything>`** — deliberately distill a skill from a directory, URL, or a workflow you just demonstrated, instead of waiting for the background self-improvement loop.

Do a `/journey` pruning pass monthly — a wrong memory gets injected into every future session and compounds. Full guidance: [Part 26](./part26-moa-verification.md#3-learn-and-journey--self-improvement-you-can-see).

## The Snapshot Rule (Why the Agent "Forgets" Mid-Session)

The most-hit memory gotcha in the wild: memory writes hit disk **immediately**, but the memory block injected into the *system prompt* is **snapshotted at session start** and stays fixed for the whole session — deliberately, to keep the provider prefix cache warm (see [Part 20](./part20-observability.md)). The same applies to `USER.md`.

- Need a just-saved fact live *now*? Start a new session, or `hermes -c`.
- Tool calls that read memory always see live disk — only the injected block is frozen.
- This is not a bug to fix; it's a cost trade you should know you're making.

## Approval Gates for Self-Improvement

For shared or production agents, gate what gets written before it compounds:

```text
/memory approval on
/skills approval on
```

The agent keeps proposing memories and skills, but every write waits for your yes. One wrong "fact" in memory gets injected into every future session — cheap insurance.

## Community Memory Layers (When Native Isn't Enough)

Native memory + `/journey` covers session continuity and user preferences. For other shapes of the problem:

| Need | Prefer |
|------|--------|
| Session continuity + user prefs | **Hermes native memory** (this part) |
| Knowledge graph over a document corpus | **LightRAG** ([Part 3](./part3-lightrag-setup.md)) |
| Cross-app / multi-client memory | **Mem0 MCP** — official packages only ([Part 17](./part17-mcp-servers.md)) |
| Long-horizon procedural knowledge | **Skills via `/learn`** ([Part 26](./part26-moa-verification.md)) |

Community plugins like Sibyl Memory (Hermes Atlas) advertise big LongMemEval numbers and token savings — treat vendor benchmarks as marketing until you've reproduced them on your own workload, and audit anything that reads your whole session history.

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
