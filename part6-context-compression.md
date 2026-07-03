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

## Best Practices

- **Let it compress.** Don't set the threshold to 0.99 — compression needs headroom to work.
- **Monitor long sessions.** If the agent starts forgetting things mid-conversation, check if compression silently failed.
- **Restart fresh for critical work.** If you're doing something important, start a new session rather than running on a 100-message compressed context.
- **Use `session_search` to recall.** If you lost context to compression, `session_search` can find it in past transcripts.

---

*This bug affects Hermes versions before v0.18. Update; patch only if you can't.*
