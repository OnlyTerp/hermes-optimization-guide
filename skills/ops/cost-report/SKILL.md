---
name: cost-report
description: Weekly LLM cost breakdown by provider / gateway / skill, posted to private DM
when_to_use:
  - Scheduled weekly
  - User asks "how much am I spending?"
  - After a noticeable cost spike
toolsets:
  - terminal
  - file
parameters:
  window:
    type: string
    default: "7d"
  format:
    type: string
    enum: [markdown, json, csv]
    default: markdown
security:
  trust: trusted
  notes: |
    Read-only over local usage data. No untrusted input, no external writes.
model_hint: google/gemini-3.7-flash
---

# cost-report — LLM Cost Breakdown

Generate a human-readable (or machine-readable) cost report from Hermes' own usage ledgers.

## Procedure

1. **Surface the numbers Hermes already keeps.** There is no `hermes logs
   export` usage stream (that subcommand never existed) — use the built-in
   insights and logs views:

   ```bash
   hermes insights --days ${WINDOW}     # token + cost breakdown from session history
   hermes logs --since ${WINDOW} --component agent   # raw log lines for detail
   ```

2. **Aggregate per-provider / per-skill splits.** `hermes insights` rolls
   usage up globally. For the per-provider / per-skill / per-gateway
   tables below, pull from your tracing layer (self-hosted Langfuse via
   the `observability/langfuse` plugin — Part 20) or from a JSONL usage
   log you collect with the Part-20 log-tail pipeline. With such a JSONL
   file, DuckDB inspects it quickly:

   ```bash
   duckdb -c "
     CREATE TABLE logs AS SELECT * FROM read_json_auto('/tmp/hermes-logs.jsonl');

     -- By provider
     SELECT provider,
            SUM(cost_usd) AS cost,
            SUM(tokens_in) AS tok_in,
            SUM(tokens_out) AS tok_out,
            COUNT(*) AS calls
     FROM logs
     GROUP BY 1
     ORDER BY 2 DESC;
   "
   ```

3. **Produce four tables:**

   **A. By provider**
   ```
   Provider     Cost($)  Tokens-in   Tokens-out   Calls
   anthropic    18.44    2.1M        380K         412
   openai       6.20     1.2M        220K         187
   gemini       0.45     890K        140K         523
   ```

   **B. By gateway**
   ```
   Gateway     Cost($)  % of total
   telegram    14.22    56%
   cli         8.10     32%
   discord     2.77     11%
   cron        0.50     2%
   ```

   **C. By active skill**
   ```
   Skill                 Cost($)  Calls  Avg-cost
   claude-code           9.40     22     $0.43
   lightrag-query        4.11     189    $0.02
   pr-review             3.20     8      $0.40
   weekly-dep-audit      1.25     1      $1.25
   ```

   **D. Daily trend** (simple ASCII sparkline)
   ```
   Mon ▂
   Tue ▃
   Wed ▅█  ← weekly-dep-audit ran
   Thu ▃
   Fri ▄
   Sat ▂
   Sun ▁
   Total: $25.53
   ```

4. **Flag anomalies.** Use a 3x median-absolute-deviation rule on daily spend. Note any days or skills that exceed the threshold:
   > ⚠ Wed spent $9.80, 4.5x typical. Driven by `weekly-dep-audit`.

5. **Recommend savings.** Pattern-match the data:
   - Any single skill > 30% of weekly cost → suggest a cheaper model for that skill (`hermes model` → "Configure auxiliary models")
   - Input tokens > 10x output tokens on any provider → prompt caching is already auto-on for Anthropic/OpenRouter/Portal; check that mid-session `/model` switches aren't resetting the cache prefix (Part 20)
   - Gemini/Flash calls doing work the primary model could absorb → check `auxiliary.<task>` is not pinned to an expensive model
   - Opus/GPT-5/Grok calls in cron or triage lanes → require explicit opt-in routing (`model_aliases` + cron job model pins)

6. **Deliver.** Post to the job's `--deliver` target (a private DM is the
   classic choice). Attach the raw JSON if format is json.

## Cron wiring

Jobs live in `~/.hermes/cron/jobs.json`, created via `hermes cron create`
(the old `cron.yaml` list format was removed):

```bash
hermes cron create "0 9 * * 1" \
  "Run the cost-report skill: window=7d format=markdown" \
  --skill cost-report --name weekly-cost-report --deliver telegram
```

## See also

- [Part 20: Observability & Cost](../../../part20-observability.md)
- [cost-routing playbook](../../../part20-observability.md#cost-routing-playbook-the-one-that-actually-saves-money)