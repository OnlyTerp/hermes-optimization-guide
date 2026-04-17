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
---

# cost-report — LLM Cost Breakdown

Generate a human-readable (or machine-readable) cost report from Hermes' usage logs.

## Procedure

1. **Export logs.** Run:
   ```bash
   hermes logs export --since ${WINDOW} --format jsonl --output /tmp/hermes-logs.jsonl
   ```

2. **Parse and aggregate.** Using DuckDB (preferred) or `jq` + `awk`:
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
   cerebras     0.45     890K        140K         523
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
   - Any single skill > 30% of weekly cost → suggest a cheaper model for that skill
   - Input tokens > 10x output tokens on any provider → suggest prompt caching
   - Gemini calls without `google/gemini-2.5-flash` on classification-ish intents → suggest routing

6. **Deliver.** Post to private notification channel. Attach the raw JSON if format is json.

## Cron wiring

```yaml
- name: weekly-cost-report
  schedule: "0 9 * * 1"
  task: /cost-report window=7d format=markdown
  notify: telegram_private
```

## See also

- [Part 20: Observability & Cost](../../../part20-observability.md)
- [cost-routing playbook](../../../part20-observability.md#cost-routing-playbook-the-one-that-actually-saves-money)
