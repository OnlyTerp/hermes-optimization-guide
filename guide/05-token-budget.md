# 05 · Cost & Speed: The Token Budget

> Cut what every call costs without making the agent dumber, using numbers you can measure on your own machine.

**TL;DR**
- **Measure first.** `hermes prompt-size` shows the fixed cost of every call, `/context` shows the live session, and `hermes insights` shows where the money went.
- **Send fewer tool schemas.** Disable toolsets you don't use, per platform. Turning off `browser` and `tts` alone saves about 2,300 tokens on every call.
- **Move side tasks to a cheap model.** Compression, titles, approvals and the background review all run on your *main* model unless you say otherwise. Leave vision alone if your main model can see images.
- **Protect the cache.** Don't switch models or reload MCP servers mid-session. Use `/btw`, `/bg`, or a subagent for side work.
- **Know when compression really fires.** On any model with under 512K of context, that's 75%, not the 50% that `hermes config show` prints.
- **Know the guardrails that are already on**, and add hard ceilings only where a runaway would really hurt.

## Measure before you cut

Four tools, from cheapest to most detailed:

| Command | Where | What it tells you |
|---|---|---|
| `hermes prompt-size [--platform telegram]` | shell, offline | The fixed prefix every call carries: system prompt tiers, skills index, memory, and tool schemas by toolset |
| `/context` (`/context all` for per-skill and per-toolset detail) | any session | Live context use by category, the compression threshold, and which context files were loaded, shadowed, or truncated |
| `/usage` · `hermes usage` | session · shell | Token usage and provider rate-limit windows |
| `hermes insights --days 7 [--source telegram]` | shell | Tokens, estimated cost, and tool patterns across past sessions |

The CLI status bar also measures live. On wide terminals it shows `cache_hit` (the prompt-cache hit ratio, which resets on model switch and compression), `latency`, and `tps` by default. Add the session token total with `display.status_bar.fields` (listing fields controls visibility, and an empty list keeps the default set). `display.show_cost: true` adds an estimated dollar figure. For one-shot runs, `--usage-file` writes a JSON cost report even when the run fails:

```bash
hermes -z "summarize ./notes.md" --usage-file /tmp/usage.json
```

Here is `hermes prompt-size` on a fresh v0.21.4 install, run from a directory with no project context file:

```text
Prompt-size breakdown (platform=cli, model=unset)

  System prompt total :   13,449 B  (13.1 KB, 13,383 chars)
    skills index       :    5,364 B  (5.2 KB)
  Tool schemas         :   42,187 B  (41.2 KB, 24 tools)

  Toolsets by size (tool-schema JSON, largest first):
    file                       4     5,673 B  (5.5 KB)
    skills                     3     5,019 B  (4.9 KB)
    delegation                 1     4,650 B  (4.5 KB)
    browser                    5     4,407 B  (4.3 KB)
    terminal                   1     3,654 B  (3.6 KB)
    memory                     1     3,526 B  (3.4 KB)
    browser-use                1     3,498 B  (3.4 KB)
    ...
```

That's about 13,000 tokens per call before any conversation (see [chapter 01](./01-how-hermes-works.md#whats-in-every-request) for the token counts). Every lever below attacks one part of it.

## Where the money goes

A turn is a loop of model calls, and each call re-sends everything: `prefix + conversation so far`. Roughly:

```text
turn cost ≈ Σ over each call ( uncached input × input price
                            + cached input × cached-read price
                            + output (including thinking) × output price )
```

So you have exactly five things to push on:

1. **Prefix size.** Fewer tool schemas and shorter instructions ([lever 1](#lever-1-send-fewer-tool-schemas), [lever 5](#lever-5-keep-the-conversation-lean)).
2. **Cache hit rate.** An identical prefix on every call, so it bills at the cached rate ([lever 2](#lever-2-keep-the-prompt-cache-warm)).
3. **Price per token.** Cheaper models wherever quality doesn't need the expensive one ([lever 3](#lever-3-put-side-tasks-on-a-cheap-model), [lever 6](#lever-6-cheaper-models-for-work-that-doesnt-need-the-best)).
4. **Conversation size.** Compression and fewer giant tool outputs ([lever 4](#lever-4-compression-that-fires-when-you-think-it-does), [lever 5](#lever-5-keep-the-conversation-lean)).
5. **Number of calls.** Batching and guardrails ([guardrails](#guardrails-against-runaway-spend)).

## Lever 1: Send fewer tool schemas

Tool definitions are about three quarters of the default prefix. Every enabled toolset costs tokens on every call, whether or not the agent uses it.

**Disable what a surface doesn't need, per platform.** A Telegram assistant that never drives a browser shouldn't pay for the browser's schemas on every message:

```bash
hermes tools list --platform telegram                 # what's on now
hermes tools disable --platform telegram browser tts  # drop what you don't use
hermes prompt-size --platform telegram                # confirm the saving
```

Measured on v0.21.4: disabling `browser` (which also removes `browser-use`) and `tts` takes tool schemas from 42,187 bytes (24 tools) to 32,299 bytes (17 tools). That's **−2,311 tokens on every call**. Running `hermes tools` with no arguments opens an interactive checklist per platform. For "off everywhere", use one global switch instead of editing 15 platform rows:

```yaml
agent:
  disabled_toolsets:        # removed on every surface, after per-platform config
    - tts
```

**Don't bother disabling `image_gen` or `computer_use` to save tokens.** They are already deferred behind **tool search** (below), so disabling them doesn't shrink the prefix. Disable them for *safety* if you like ([chapter 13](./13-security.md)).

A starting point for which toolsets to keep:

| Surface | Keep | Usually safe to drop |
|---|---|---|
| Coding in the CLI | `terminal`, `file`, `code_execution`, `web`, `skills`, `memory`, `session_search`, `delegation`, `todo`, `clarify` | `tts`, `browser` (unless you test web UIs) |
| Personal chat bot | `web`, `memory`, `session_search`, `skills`, `cronjob`, `clarify`, `vision` | `browser`, `code_execution`, `delegation` (unless you ask for research jobs) |
| Unattended cron profile | exactly what the jobs use | everything else |

### Tool search is already working for you

By default (`tools.tool_search.enabled: auto`), MCP tools, plugin tools, and a curated list of rarely used built-ins (`computer_use`, `session_search`, `image_generate`, and a few desktop helpers) aren't sent as full schemas. The model sees three bridge tools instead (`tool_search`, `tool_describe`, `tool_call`) plus a compact listing capped at `min(5% of context, 4,000 tokens)`, and it loads a real schema only when it needs one. Core tools such as `terminal`, `read_file`, and `web_search` always stay eager.

In practice, adding an MCP server with 40 tools costs a listing line per tool, not 40 full schemas. Leave tool search on. Setting `tools.tool_search.defer: []` makes everything eager again, which is the expensive direction. Details: [Tool Search](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-search).

## Lever 2: Keep the prompt cache warm

Caching is the single biggest discount available, and it only works when the start of the request is byte-identical to a recent call.

**How it works in Hermes.** For Claude models on the native Anthropic API, OpenRouter, or Nous Portal, Hermes places cache breakpoints itself: on the system prompt and on the most recent messages. All markers use one TTL, `prompt_caching.cache_ttl`. Hermes' own docs estimate about 75% lower input cost on multi-turn conversations. For other providers that cache prefixes automatically on their side, Hermes' job is simply to keep the prefix stable, and the design does that. The system prompt is frozen for the whole session, and memory writes go to disk without touching it.

**The one knob:**

```yaml
prompt_caching:
  cache_ttl: 5m     # default. "1h" costs 2x on cache writes (vs 1.25x for 5m) and pays off
                    # when you routinely pause more than 5 minutes between turns.
                    # "off" disables caching (for OAuth plans that bill cache writes,
                    # or proxies that add their own cache_control markers).
```

That behavior comes straight from `agent/agent_init.py` at v0.21.4. The prose in the configuration docs page about an automatic 1-hour TTL does not match the code.

**What breaks the cache.** The next call re-reads the entire conversation at full price after any of these:

| Action | Why | Do this instead |
|---|---|---|
| `/model` mid-session | Caches are scoped to the model and account | Start a new session on the other model, or delegate that step to a subagent with its own model |
| Automatic fallback to another provider | Same as above | A reliable primary. Fallback only for real outages ([chapter 03](./03-models.md)). |
| Credential-pool rotation to another key | Cache is per account | Pools are for rate limits, not routine use |
| `/reload-mcp` or changing tools mid-session | Tool schemas are part of the cached prefix | Change tools between sessions. `approvals.mcp_reload_confirm` (on by default) asks before a reload. |
| Compression | The compressed region is rewritten (the system prompt stays cached) | Compress deliberately, not constantly ([lever 4](#lever-4-compression-that-fires-when-you-think-it-does)) |
| Long idle gaps | Cache entries expire (5 minutes by default) | `cache_ttl: 1h` if your rhythm is "one message every 10 minutes" |

**Side work without touching the main cache:**

- `/btw <question>` asks about the current conversation through a one-shot auxiliary call on a read-only snapshot. The live history and cache are untouched.
- `/bg <prompt>` runs an independent task in a separate background session.
- `delegate_task` subagents run in their own context. Only their summary comes back.

## Lever 3: Put side tasks on a cheap model

This is the most commonly missed setting. By default every `auxiliary.*` task has `provider: auto`, and **`auto` means your main chat model**. The docs say it plainly: on expensive reasoning models, auxiliary tasks "add meaningful cost". If your main model is a top-tier model, your conversation summaries and memory reviews are billed at top-tier prices.

The tasks that matter most for cost:

| Task (`auxiliary.<task>`) | What it does | How often |
|---|---|---|
| `compression` | Writes the summary when context is compacted | Every compaction |
| `background_review` | Decides what to save to memory and skills | Every ~10 turns ([below](#the-background-review)) |
| `title_generation` | Names new sessions | Once per session |
| `approval` | Classifies risky commands in `smart` approval mode | Every flagged command |
| `goal_judge` | Checks whether a `/goal` is done | After every goal turn |
| `curator` | The optional skill-consolidation pass | Weekly, if enabled |
| `mcp`, `skills_hub`, `memory_query_rewrite`, `triage_specifier`, `kanban_decomposer`, `profile_describer`, `monitor`, `tts_audio_tags` | Feature-specific helpers | When you use the feature |

Route the busy ones to a fast, cheap model. The model below is the example the official docs use (as of September 2026). Any inexpensive model with solid instruction-following works:

```yaml
auxiliary:
  compression:
    provider: openrouter
    model: google/gemini-3-flash-preview
    reasoning_effort: low         # summaries don't need deep thinking
  title_generation:
    provider: openrouter
    model: google/gemini-3-flash-preview
  approval:
    provider: openrouter
    model: google/gemini-3-flash-preview
  background_review:
    provider: openrouter
    model: google/gemini-3-flash-preview
```

> [!WARNING]
> **Leave `auxiliary.vision` alone unless your main model is text-only.** Vision isn't a side task the way compression is. When your main model can see, images (attachments, browser screenshots, `vision_analyze`) go to it as real pixels and no auxiliary call happens at all. Setting *any* explicit `auxiliary.vision` provider or model switches every image to the other path: a second model describes it and your main model only gets the text. That's cheaper on the main model but lossy. With a text-only main model, `auto` already finds a vision backend for you. `agent.image_input_mode` (`auto`, `native`, `text`) makes the choice explicit.

Prefer menus? Run `hermes model`, choose **Configure auxiliary models**, and pick per task. Then run `hermes doctor`. It resolves every routed auxiliary block and reports any it can't reach. An unreachable route silently falls back to the main model, which costs money.

> [!TIP]
> Don't want titles at all? `auxiliary.title_generation.enabled: false`. Want the instant title from your first line but no model call to improve it? `auxiliary.title_generation.model_upgrade_enabled: false`.

### The background review

After every few turns (`memory.nudge_interval` and `skills.creation_nudge_interval`, both 10), Hermes forks a reviewer that replays the conversation and decides what to save to memory and skills. It's the engine of the learning loop. It is also, in the docs' words, something that "can burn a meaningful share of total tokens on busy hosts." You have four knobs:

| Knob | Effect |
|---|---|
| Leave it on the main model (default) | Replays the full conversation, but mostly as cheap cache reads |
| `auxiliary.background_review.provider/model` | A different model gets a compact digest instead of the full transcript. The docs benchmark this as roughly 3–5× cheaper, with memory capture unchanged. |
| `auxiliary.background_review.max_input_tokens: 48000` | Caps one review's total replayed input. The default is 75% of the review model's window, capped at 600K. |
| `auxiliary.background_review.enabled: false` | No automatic reviews. `/refine` still runs one on demand. |

Each review writes a line to `agent.log` (`Background review complete: … in=… out=…`), so you can see what it costs you with `hermes logs --component agent`.

## Lever 4: Compression that fires when you think it does

Hermes compresses a conversation by pruning old tool output (no model call) and then having the auxiliary `compression` model summarize the middle. The system prompt, the first exchange, a recent tail, and your own messages survive. Your messages are quoted verbatim, newest first, within a budget. Pre-compaction turns are archived in `state.db` and stay findable through `session_search`.

**When it fires is not what the config suggests.** The default `compression.threshold` is `0.5`, and `hermes config show` prints "Threshold: 50%". But v0.21.4 applies a raise-only floor (`agent/context_compressor.py`, `_effective_threshold_percent`):

| Model context window | Compression actually triggers at |
|---|---|
| Under 512K (almost every model) | **75%** of the window, or your `threshold` if higher |
| 512K and up | `threshold` × window, capped at `compression.threshold_tokens` (256,000 by default). A 1M model compacts at 256K. |
| Messaging gateway safety net | A separate pre-turn check at 85%, for sessions that grew while idle |

What that means for your settings:

- **Lowering `threshold` below 0.75 does nothing on a sub-512K model.** Compressing earlier to save money isn't available through this knob. Use `/compress`, or start `/new` sessions.
- **On 1M-context models, the 256K cap is the real trigger.** Raising `compression.threshold_tokens` (or setting it to `null`) lets sessions grow toward the full window, and every call gets more expensive as they do. Keep the cap unless you truly need the long context.
- **Per-model overrides** exist (`compression.model_thresholds`, substring match, longest wins) and obey the same floor.

**Compress on purpose.** Manual compression is often the best move:

```text
/compress                    # compact now
/compress focus the billing refactor   # keep detail about one topic
/compress here 10            # summarize everything except the last 10 turns
/compress --preview          # see what would happen first
```

Good moments: right after a large tool dump you no longer need, and when you switch sub-tasks inside a long session. If you're switching to an *unrelated* task, `/new` beats compression. It's free and loses nothing, since the old session stays searchable.

Two settings worth knowing:

```yaml
compression:
  min_tail_user_messages: 3        # keep your last 3 real instructions verbatim (default 1)
  idle_compact_after_seconds: 3600 # compact on resume after an hour idle (default 0 = off)
```

`idle_compact_after_seconds` suits chat bots. After an hour of silence the provider cache has expired anyway, so compacting on resume makes the next call smaller without losing a warm cache.

## Lever 5: Keep the conversation lean

**Cap what tools can dump into context:**

```yaml
tool_output:
  max_bytes: 50000     # terminal output kept per call (first 40% + last 60%); ≈12-15K tokens
  max_lines: 2000      # max lines per read_file call
file_read_max_chars: 100000
web:
  extract_char_limit: 15000   # web_extract truncates; the full text stays pageable
```

The defaults are sane for 128K+ models. On small local models, halve them ([chapter 04](./04-local-models.md)). Oversized results are *spilled to disk* instead of cut (above 100,000 chars, or 50,000 for MCP tools, set by `tool_budget.mcp_result_size_chars`). The model gets a preview and a file path it can page through.

**Keep instructions short.** `SOUL.md`, the project context file, and the skills index ride on every call:

- One `AGENTS.md` under a few KB beats a sprawling one. A 31.9 KB `AGENTS.md` measured **+8,609 tokens per call**. `/context` lists each context file with its token estimate and whether it loaded. [Chapter 06](./06-personality-and-context.md) covers writing tight ones.
- Start Hermes from the directory you're working in, not from a repo root with a giant rules file you don't need. `hermes --ignore-rules` skips context files for one run.
- The skills index costs about 90 bytes per installed skill. Pruning unused skills (`hermes skills config`) is a small win. Opting a single-purpose profile out of bundled skills (`hermes skills opt-out`) is a bigger one ([chapter 08](./08-skills.md)).

**Work patterns that save tokens:**

- **One task, one session.** `/new` between unrelated tasks. Give long-running work a `/title` and come back with `/resume`.
- **Batch with code.** "Write a script that renames all 400 files and run it" is one `execute_code` call. Doing it by hand is 400 terminal calls, each re-sending the whole prefix.
- **Delegate exploration.** A subagent that reads 30 files returns a summary. Reading them yourself leaves 30 files in the main context.
- **One-shots for one-off questions.** `hermes -z "…"` starts clean every time.

## Lever 6: Cheaper models for work that doesn't need the best

- **Subagents:** `delegation.model` and `delegation.provider` route `delegate_task` children to a cheaper model. Research and file-reading children rarely need your top model ([chapter 12](./12-multi-agent.md)).
- **Cron jobs:** `cron.model` and `cron.model_provider` set the default for every unpinned job, independent of your chat model: `hermes config set cron.model <model>` ([chapter 11](./11-automation.md)).
- **Reasoning effort:** thinking tokens bill as output. Lower the default (`/reasoning low --global`) and raise it only when a task needs it, or pin effort per model with `agent.reasoning_overrides`. `hermes -z … --reasoning none` suits quick scripted calls.
- **Mixture of Agents** runs several models per turn. Keep it for genuinely hard problems (`/moa <prompt>` for one turn) rather than as a default ([chapter 03](./03-models.md)).

## Speed

| Want | Do |
|---|---|
| Faster first token | Lower reasoning effort, and a faster model for the step at hand |
| Faster long sessions | Keep the cache warm (cached prefixes are also faster), and compress before the context gets huge |
| Priority processing | `/fast auto`. It sends the provider's fast/priority tier only during the first 60 seconds of each turn (`agent.fast_auto_seconds`). It costs a premium, so use `normal` to stay cheapest. It only reaches first-party endpoints (OpenAI/Codex, Anthropic, xAI), never OpenRouter or custom URLs. |
| See progress as it happens | `display.streaming: true` in the CLI. Telegram streams by default (`display.platforms.telegram.streaming`). |
| Fail over faster | With [fallback providers](./03-models.md) configured, `agent.api_max_retries: 0` hands off on the first transient error instead of retrying three times |
| No stalls on side tasks | A fast auxiliary model ([lever 3](#lever-3-put-side-tasks-on-a-cheap-model)). A slow compression model stalls the turn that triggers compaction. |

## Guardrails against runaway spend

Out of the box Hermes has **no iteration cap**, on purpose: `agent.max_turns` is unlimited because caps used to cut real work off mid-task. The safety nets already on by default are narrower and smarter:

- **Loop guardrails** warn when the agent repeats a failing call. They hard-stop in non-interactive runs such as the gateway, cron, and one-shots (`tool_loop_guardrails.non_interactive_hard_stop_enabled: true`).
- **Per-turn caps** hold every turn to 50 web searches and 50 subagents (`tool_loop_guardrails.loop_caps`).
- **Delegation limits** default to 10 concurrent children and depth 1. A `-z`/`-q` one-shot may spawn at most 2 subagents in total.
- **`/goal` auto-continue** stops after 20 turns (`goals.max_turns`).

Add hard ceilings only where a runaway would really hurt, such as a bot other people can drive or a scripted pipeline with a deadline:

```yaml
agent:
  max_turns: 150              # model calls per turn, then one wrap-up call
  run_budget_seconds: 900     # wall-clock per turn; a single wrap-up notice at 80%
tool_loop_guardrails:
  hard_stop_enabled: true     # also hard-stop repeat-failure loops in interactive sessions
delegation:
  max_concurrent_children: 5  # default 10
```

- `hermes chat --max-turns 50 --run-budget 600 -q "…"` sets both for a single run.
- `hermes pause` is the emergency brake. It stops cron and Kanban dispatch and new gateway turns until `hermes resume`.

## A lean config to start from

Copy what applies into `config.yaml`. Every key here exists in v0.21.4. The full version lives in [`templates/config/lean.yaml`](../templates/config/lean.yaml).

```yaml
agent:
  disabled_toolsets: [tts]       # nothing on any surface needs speech? drop it everywhere

auxiliary:
  compression:
    provider: openrouter
    model: google/gemini-3-flash-preview
    reasoning_effort: low
  title_generation:
    model_upgrade_enabled: false # keep the free first-line title, skip the model call
  background_review:
    provider: openrouter
    model: google/gemini-3-flash-preview
    max_input_tokens: 48000

compression:
  min_tail_user_messages: 3

delegation:
  provider: openrouter
  model: google/gemini-3-flash-preview   # cheap research/reading subagents

prompt_caching:
  cache_ttl: 5m
```

Then trim toolsets per platform with `hermes tools disable --platform <name> …`.

## Verify it

```bash
hermes prompt-size --platform telegram   # prefix before/after trimming
hermes doctor                            # auxiliary routes resolve, nothing falls back silently
hermes insights --days 7                 # compare spend week over week
hermes logs --component agent | grep "Background review complete"
```

In a session, `/context` should show the tool-definition category shrinking, and the status bar's `cache_hit` ratio should climb after the first couple of turns. If it stays near zero on a caching provider, something is changing your prefix between calls ([lever 2](#lever-2-keep-the-prompt-cache-warm)).

## Gotchas

- **"Threshold: 50%" is not when compression fires** on sub-512K models. It fires at 75% (`agent/context_compressor.py`). The docs' worked 200K example predates this floor.
- **`auxiliary.*: auto` is not "cheap auto-pick".** It is your main model.
- **Setting `auxiliary.vision` changes how images are handled, not just who pays for them.** An explicit vision backend makes Hermes describe every image in text, even for a main model that could see it ([warning above](#lever-3-put-side-tasks-on-a-cheap-model)).
- **Disabling deferred tools saves nothing** in the prefix. Check `hermes prompt-size` before and after instead of guessing.
- **Fast mode costs more**, and only reaches first-party endpoints.
- **The old "chat platforms cost 2–3× the CLI" rule doesn't hold on defaults.** CLI and Telegram carry identical tool schemas (42,187 bytes) on a fresh install. The difference is whatever *you* enabled per platform, so measure with `--platform`.
- **A big context file in your launch directory is a silent tax.** `/context` will show it.

## Go deeper

- Official: [Context Compression & Caching](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching) · [Tool Search](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-search) · [Auxiliary models](https://hermes-agent.nousresearch.com/docs/user-guide/configuration#auxiliary-models) · [Fast mode](https://hermes-agent.nousresearch.com/docs/user-guide/configuration#fast-mode) · [Memory (background review)](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) · [Tips](https://hermes-agent.nousresearch.com/docs/guides/tips)
- In this guide: [03 · Models](./03-models.md) · [04 · Local Models](./04-local-models.md) · [06 · Personality & Context Files](./06-personality-and-context.md)

---
[← Previous: 04 · Local Models](./04-local-models.md) · [Guide index](../README.md#the-guide) · [Next: 06 · Personality & Context Files →](./06-personality-and-context.md)
