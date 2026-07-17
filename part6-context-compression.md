# Part 6: Context Compression (Don't Lose Your Context Silently)

*Long sessions degrade. Context compression fixes this — but only if it works correctly.*

---

## The Problem

Hermes injects context every message: memory, skills, tool results, conversation history. In long sessions, this grows until you hit the context window limit and the agent freezes or starts forgetting.

Context compression automatically summarizes older messages to keep the context lean. But there's a bug in the default implementation that can silently drop context.

## The Bug (fixed upstream in v0.18)

> **Running v0.18 or later? You're done — skip to [When Compression Triggers](#when-compression-triggers).** v0.18 fixed this upstream (it was one of the P0/P1 issues closed in that release), and hand-patching a PyPI install just gets overwritten by the next `hermes update`. The patch below is only for installs pinned to **pre-v0.18** that can't update yet.

In `context_compressor.py`, when summarization fails (API timeout, model error, rate limit), the compressor **silently discards the messages it was trying to summarize** instead of preserving them. You lose context with no warning.

**Symptoms:**
- Agent suddenly "forgets" something it knew 20 messages ago
- Long sessions degrade faster than expected
- No error messages — it just quietly loses data

## The Fix (pre-v0.18 only)

Find your `context_compressor.py`:

```bash
find ~/.hermes -name "context_compressor.py" -type f
```

Look for the compression function. The bug is in the error handling around the summarization call. It should look something like:

```python
# BROKEN — silently drops context on failure
try:
    summary = await summarize_messages(messages_to_compress)
    compressed_context = summary
except Exception:
    compressed_context = ""  # THIS IS THE BUG — empty string = data lost
```

Fix it by **aborting compression on failure** instead — return the original messages untouched:

```python
# FIXED — abort compression, keep the original messages
try:
    summary = await summarize_messages(messages_to_compress)
except Exception as e:
    logger.warning(f"Context compression failed: {e}; keeping uncompressed context")
    return messages_to_compress  # abort: caller keeps the original messages
return [make_summary_message(summary)]
```

(Exact names differ by version — the point is the shape: on failure, return the *original message list*, not an empty summary. Adapt to whatever your copy of the function returns.)

**The rule:** If compression can't succeed, keep the uncompressed context. A slower response is better than a wrong one.

## When Compression Triggers

- Default: when context reaches ~80% of the model's window
- Configurable via `hermes config set` (the same `compression:` block Part 1 uses):

```bash
# Turn compression on/off
hermes config set compression.enabled true

# Fraction of the context window that triggers compression (default: 0.8)
hermes config set compression.threshold 0.8

# How aggressively to shrink, and how many recent messages to never touch
hermes config set compression.target_ratio 0.5
hermes config set compression.protect_last_n 20
```

## What Compression Actually Keeps (and the Levers That Matter)

When automatic compression fires (the 🗜️ icon — the configured default is the 0.8 threshold above, though community reports often see it fire around the half-full mark once fixed overhead like tool definitions and rule files is counted), it keeps roughly the **first few turns and the last `protect_last_n` messages**, and summarizes the middle. The middle is where "the agent redid work it already did" comes from. Three levers, all hot-reloaded on a running gateway:

```yaml
compression:
  protect_last_n: 30            # keep more recent turns verbatim (default 20)
auxiliary:
  compression:
    provider: openrouter
    model: google/gemini-3-flash  # summarize on a cheap model, never your primary
model:
  context_length: 200000        # a bigger ceiling = compression fires later
```

And compaction is a **structured brief, not amnesia** — it fills fixed slots (goal / constraints / progress / key decisions / relevant files / next steps / critical context), and the raw turns stay in `state.db` for `session_search`. So *write for the compactor*: state goals and decisions in plain declarative sentences, and put never-drop facts in `MEMORY.md` instead of chat. More context-survival mechanics: [Part 27](./part27-power-secrets.md#1-context-memory--the-prefix-cache).

## The Context You Didn't Order: Third-Party Rule Files

Compression only manages *conversation* growth — a fat project rule file taxes **every prompt before the conversation even starts**. Rule discovery is first-match-wins (`.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`) with a 20k-char cap, and a stray `.hermes.md` silently shadows your `AGENTS.md`. Worst observed case: Camofox ships an `AGENTS.md` that injects **~22k characters into every prompt** if it's in your cwd. After installing any tool into a workspace, check for rule files it dropped.

## Best Practices

- **Let it compress.** Don't set the threshold to 0.99 — compression needs headroom to work.
- **Monitor long sessions.** If the agent starts forgetting things mid-conversation, check if compression silently failed.
- **Restart fresh for critical work.** If you're doing something important, start a new session rather than running on a 100-message compressed context.
- **Use `session_search` to recall.** If you lost context to compression, `session_search` can find it in past transcripts.

---

*This bug affects Hermes versions before v0.18. Update; patch only if you can't.*
