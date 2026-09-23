---
name: hermes-cost-audit
description: Audit Hermes token spend and propose cuts.
version: 1.0.0
author: Terp AI Labs
license: MIT
metadata:
  hermes:
    tags: [hermes, cost, tokens, optimization]
    related_skills: [hermes-health-check]
---

# Hermes Cost Audit

Find where this Hermes install spends tokens and propose the cuts with the best payoff, backed by measurements taken on this machine.

## When to Use

- The user asks why Hermes is expensive, where tokens go, or how to spend less.
- As a weekly cron job that reports spend and new savings opportunities.

## Procedure

Run every command with the terminal tool. Read, measure, and report. **Do not change any setting until the user approves the specific change.**

1. **Measure the fixed prefix** that every model call carries, per surface actually in use:

   ```bash
   hermes tools --summary                      # which platforms have which toolsets
   hermes prompt-size --json                   # CLI
   hermes prompt-size --platform telegram --json   # repeat for each platform in use
   ```

   Record system prompt bytes, skills index bytes, tool schema bytes, and the three largest toolsets per platform.

2. **Measure real spend** over time:

   ```bash
   hermes insights --days 7
   hermes insights --days 30
   ```

3. **Read the settings that drive cost.** `auto` on an auxiliary task means *the main model*:

   ```bash
   hermes config get model
   hermes config get auxiliary.compression.model
   hermes config get auxiliary.vision.model
   hermes config get auxiliary.title_generation.model
   hermes config get auxiliary.approval.model
   hermes config get auxiliary.background_review.model
   hermes config get delegation.model
   hermes config get cron.model
   hermes config get agent.disabled_toolsets
   hermes config get prompt_caching.cache_ttl
   ```

4. **Check for these patterns** and estimate the saving of each from the step 1 numbers (roughly 4.2–4.5 bytes per token):

   | Pattern | Proposal |
   |---|---|
   | Auxiliary tasks on `auto` while the main model is expensive | Route compression, vision, titles, approvals, and background review to a cheap model |
   | A toolset enabled on a platform that never uses it (for example `browser` or `tts` on a chat bot) | `hermes tools disable --platform <platform> <toolset>` |
   | Heavy delegation with `delegation.model` unset | A cheaper model for subagents |
   | Several cron jobs with `cron.model` unset | A cheap default for unpinned cron jobs |
   | A large project context file where the user usually works | Shorten it. Move detail into subdirectory files or skills. |
   | Long pauses between turns on a Claude model with `cache_ttl: 5m` | Consider `1h` (cache writes cost 2x, but pauses stop re-reading at full price) |

5. **Report** a table ordered by estimated impact: finding, current value, proposed value, estimated tokens saved per call (or per day), and the exact command. Ask which changes to apply.

6. **After approval,** apply each change with `hermes config set` or `hermes tools disable`, then re-run step 1 and show the before and after.

## Verification

- `hermes prompt-size` shows fewer bytes after toolset changes.
- `hermes doctor` reports no unresolvable auxiliary routes. An unresolvable route silently falls back to the main model and saves nothing.

## Pitfalls

- `image_gen` and `computer_use` are already deferred behind tool search by default. Disabling them does not shrink the prompt.
- Model switches and tool changes break the prompt cache for the running session. Apply changes, then start a new session.
- Don't propose capping `agent.max_turns` as a cost fix. It is unlimited by design, and loop guardrails already stop runaway loops in unattended runs.
- Don't quote model prices from memory. Point the user at the provider's current pricing page.
