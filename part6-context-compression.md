# Part 6: Context Compression (Don't Lose Your Context Silently)

*Long sessions degrade. Context compression fixes this — but only if it works correctly.*

---

## The Problem

Hermes injects context every message: memory, skills, tool results, conversation history. In long sessions, this grows until you hit the context window limit and the agent freezes or starts forgetting.

Context compression automatically summarizes older messages to keep the context lean. There **was** a bug in older implementations (pre-v0.18) that could silently drop context on summarizer failure — it is fixed upstream in current versions (v0.20.x). This part covers what's real today: the actual config keys, the levers that matter, and the newer no-LLM "micro-compaction" paths.

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

- Default: `compression.threshold: 0.5` — compression fires when the conversation reaches **50%** of the model's context window (older guides said ~80%; the current default is 0.5).
- Configurable via `hermes config set` (or directly in `config.yaml` under `compression:`):

```bash
# Turn compression on/off (default: on)
hermes config set compression.enabled true

# Fraction of the context window that triggers compression (default: 0.5)
hermes config set compression.threshold 0.6

# How aggressively to shrink, and how many recent messages to never touch
hermes config set compression.target_ratio 0.2    # (default) — keep ~20% of the window as verbatim tail
hermes config set compression.protect_last_n 20   # (default) — min recent messages kept verbatim
```

## What Compression Actually Keeps (and the Levers That Matter)

When automatic compression fires (the 🗜️ icon — default trigger is the 0.5 threshold above, though it often fires around the half- to two-thirds-full mark once fixed overhead like tool definitions and rule files is counted), it keeps the opening exchange, the last `protect_last_n` messages verbatim, and summarizes the middle. The middle is where "the agent re-explains decisions it already made" comes from. Real levers, all hot-reloaded on a running gateway:

```yaml
compression:
  enabled: true                 # toggle compression on/off (default: on)
  threshold: 0.5                # compress at 50% of the model's context window (default)
  target_ratio: 0.20            # fraction of the window preserved verbatim as the tail (default 0.2)
  protect_last_n: 20            # min recent messages kept verbatim (default 20)
  protect_first_n: 3            # opening exchange pinned across every compaction (default 3)
  in_place: true                # compact in place on the same session id — pre-compaction turns
                                # are soft-archived (searchable), never deleted
  threshold_tokens: null        # optional absolute token cap — fires at the lower of ratio vs. absolute
  tail_mode: legacy             # "lean" = clamped ~2.5% tail with digests — about 3x fewer retained tokens
  idle_compact_after_seconds: 0 # opt-in: compact a stale resumed thread up front (0 = off)
  proactive_prune_tokens: 0     # opt-in no-LLM tool-dump prune trigger (0 = off; see below)

# The summarizer is a separate auxiliary LLM call — point it somewhere cheap:
auxiliary:
  compression:
    provider: auto              # "auto" (default) or force "openrouter" / "nous" / ...
    model: ""                   # empty = main chat model; e.g. "google/gemini-3-flash-preview"
```

And compaction is **non-destructive, not amnesia**: with `in_place: true` (the default), the pre-compaction turns are soft-archived under the same session id — no session rotation, no `#2`/`#3` renumbering — and they stay searchable via `session_search`. Three levers that matter: pin the summarizer to a cheap model under `auxiliary.compression` (the summary model's context window **must be ≥ your main model's window**, or the middle turns get dropped without a summary), raise `model.context_length` to delay compaction, and keep never-drop facts in `MEMORY.md` rather than chat. More cache mechanics: [Part 27](./part27-power-secrets.md#1-context-memory--the-prefix-cache).

## Micro-Compaction: The No-LLM Tool-Dump Prune (v0.20)

Full compaction is a summarization LLM call — not something you want firing on every tool iteration. On large-window models the threshold compaction (~50% of the window) rarely fires, so bulky tool results (terminal output, file reads, web extracts) ride along in history and get re-sent every turn. Hermes adds a deterministic, **model-free** prune that runs independently of `threshold`:

```yaml
compression:
  proactive_prune_tokens: 48000     # 0 (default) = off. When re-sent history exceeds this, prune.
  proactive_prune_min_result_chars: 8000     # Only summarize tool results larger than this
  proactive_prune_min_reclaim_tokens: 4096  # Only commit if it reclaims at least this many tokens
```

The prune deduplicates identical results, summarizes old oversized tool outputs, and truncates huge tool-call arguments — and it never calls the model. It leaves `protect_last_n` untouched, and full outputs stay recoverable from the session store. The minimum-reclaim gate is deliberate: a committed prune rewrites already-sent history and invalidates the provider's prompt-cache prefix, so the defaults keep cache breaks episodic (one meaningful break) instead of firing on every tool call. Set `proactive_prune_tokens: 48000` on a big-window model and stale tool dumps stop re-riding along on every turn.

Sibling key: `idle_compact_after_seconds` (default 0) — a long-lived thread that resumes after at least that many idle seconds compacts its stale history up front, before the next reply (`1800` = after 30 minutes). And on the gateway, the count-based safety valve `compression.hygiene_hard_message_limit` (default 5000) forces compression when API calls keep disconnecting before token-usage data arrives — so an oversized session recovers even when the token threshold can't fire.

You can also compress **manually** whenever you want, with a boundary you pick (same summarizer and locks as automatic compaction):

```
/compress                      # full summary now
/compress here [N]             # keep the most recent N exchanges verbatim (default 2), summarize the rest
/compress focus <topic>        # narrow what the full summary preserves
```

## The Context You Didn't Order: Third-Party Rule Files

Compression only manages *conversation* growth — a fat project rule file taxes **every prompt before the conversation even starts**. Rule discovery is first-match-wins (`.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`) with a 20k-char cap, and a stray `.hermes.md` silently shadows your `AGENTS.md`. Worst observed case: Camofox ships an `AGENTS.md` that injects **~22k characters into every prompt** if it's in your cwd. After installing any tool into a workspace, check for rule files it dropped.

## Best Practices

- **Let it compress.** Don't set the threshold to 0.99 — compression needs headroom to work.
- **Monitor long sessions.** If the agent starts forgetting things mid-conversation, check if compression silently failed.
- **Restart fresh for critical work.** If you're doing something important, start a new session rather than running on a 100-message compressed context.
- **Use `session_search` to recall.** If you lost context to compression, `session_search` can find it in past transcripts.

---

*This bug affects Hermes versions before v0.18. Update; patch only if you can't.*
