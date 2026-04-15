# Part 6: Context Compression (Don't Lose Your Context Silently)

*Long sessions degrade. Context compression fixes this — but only if it works correctly.*

---

## The Problem

Hermes injects context every message: memory, skills, tool results, conversation history. In long sessions, this grows until you hit the context window limit and the agent freezes or starts forgetting.

Context compression automatically summarizes older messages to keep the context lean. But there's a bug in the default implementation that can silently drop context.

## The Bug

In `context_compressor.py`, when summarization fails (API timeout, model error, rate limit), the compressor **silently discards the messages it was trying to summarize** instead of preserving them. You lose context with no warning.

**Symptoms:**
- Agent suddenly "forgets" something it knew 20 messages ago
- Long sessions degrade faster than expected
- No error messages — it just quietly loses data

## The Fix

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

Fix it by **aborting compression on failure** instead:

```python
# FIXED — preserves original context if compression fails
try:
    summary = await summarize_messages(messages_to_compress)
    compressed_context = summary
except Exception as e:
    logger.warning(f"Context compression failed: {e}, preserving original context")
    return original_context  # Don't compress, don't lose data
```

**The rule:** If compression can't succeed, keep the uncompressed context. A slower response is better than a wrong one.

## When Compression Triggers

- Default: when context reaches ~80% of the model's window
- Configurable in `~/.hermes/.env`:

```bash
# Percentage of context window to trigger compression (default: 80)
CONTEXT_COMPRESSION_THRESHOLD=80

# Minimum messages before compression activates (default: 20)
CONTEXT_COMPRESSION_MIN_MESSAGES=20
```

## Best Practices

- **Let it compress.** Don't set the threshold to 99% — compression needs headroom to work.
- **Monitor long sessions.** If the agent starts forgetting things mid-conversation, check if compression silently failed.
- **Restart fresh for critical work.** If you're doing something important, start a new session rather than running on a 100-message compressed context.
- **Use `session_search` to recall.** If you lost context to compression, `session_search` can find it in past transcripts.

---

*This bug affects all Hermes versions before the fix. Patch it immediately if you run long sessions.*
