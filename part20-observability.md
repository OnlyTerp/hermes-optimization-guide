# Part 20: Observability & Cost Control — Langfuse, Helicone, /usage, Routing Playbooks

*You can't optimize what you can't see. Hermes tracks tokens, latency, and errors natively, but once you're running across CLI + Telegram + Discord + cron + coding-agent delegations, you want a real tracing stack. This part sets up Langfuse, Helicone, or OpenTelemetry → Phoenix with one config block, then gives you the cost-routing playbook that dropped our test deployment from $34 to $3 per feature implementation.*

---

## The Three-Level Stack

```
┌────────────────────────────────────────────────────────┐
│  Level 3 — Hosted tracing (Langfuse / Helicone / Phoenix)│
│  Replayable traces, prompt versioning, evals            │
└────────────────────────────────────────────────────────┘
                            ↑
┌────────────────────────────────────────────────────────┐
│  Level 2 — Hermes internals (/usage, /status, dashboard)│
│  Token counts, rate-limit headers, per-session cost     │
└────────────────────────────────────────────────────────┘
                            ↑
┌────────────────────────────────────────────────────────┐
│  Level 1 — Logs (~/.hermes/logs/*, `hermes logs tail`)  │
│  Raw events, tool invocations, errors                   │
└────────────────────────────────────────────────────────┘
```

You always have Level 1 and 2. Level 3 is the force multiplier once you're spending more than $50/mo on LLM calls.

---

## Level 1 + 2 — What Ships With Hermes

### `/usage`

```
/usage                              # Current session
/usage 7d                           # Rolling 7-day window
/usage --by-provider                # Breakdown
/usage --by-skill                   # Which skills burn tokens
/usage --by-gateway                 # CLI vs Telegram vs Discord
```

As of v0.9.0 this now includes **rate-limit headers** captured from each provider — you can see "how close am I to the 5M/min ceiling" without digging into logs.

### Dashboard Analytics

The [Web Dashboard](./part12-web-dashboard.md) has an Analytics tab with:

- Cost by day / week / month
- Tokens in vs out (streaming-aware)
- Per-skill utilization (which ones actually earn their token cost)
- Tool call distribution (are you really using all those MCPs?)
- Error rates per provider (for failover tuning)

### `hermes logs`

```bash
hermes logs tail -f                 # Live tail, all gateways
hermes logs search "TokenLimit"     # Grep
hermes logs export --since 7d       # JSONL for offline analysis
```

Combine with `jq` or load into DuckDB for ad-hoc cost analysis:

```bash
hermes logs export --since 30d --format jsonl \
  | duckdb -c "SELECT gateway, SUM(tokens_out) FROM read_json_auto('/dev/stdin') GROUP BY 1 ORDER BY 2 DESC"
```

---

## Level 3 — Langfuse (Recommended Default)

Langfuse is the "everything in one place" option: tracing, prompt management, evals, self-hostable. If you're not sure where to start, start here.

### Setup (Hosted Cloud)

```yaml
# ~/.hermes/config.yaml
observability:
  langfuse:
    enabled: true
    host: https://cloud.langfuse.com
    public_key: ${LANGFUSE_PUBLIC_KEY}
    secret_key: ${LANGFUSE_SECRET_KEY}
    sample_rate: 1.0                # Reduce for very high volume
    traced_tools:                    # Which tool calls to capture
      - terminal
      - github
      - claude-code
      - gemini-cli
    redact_payloads: true            # Redacts before sending (matches your security.secrets.patterns)
```

Get the keys from https://cloud.langfuse.com → Settings → API Keys. Free tier covers most individual users.

### Self-Hosted Langfuse

For privacy or compliance, one-liner on a VPS with Docker:

```bash
curl -fsSL https://langfuse.com/docker-compose.yml -o langfuse.yml
docker compose -f langfuse.yml up -d
```

Point `host:` at your domain. Hermes sends OTLP over HTTPS, so Caddy with Let's Encrypt just works.

### What You See

Each Hermes turn becomes a trace. Each trace has spans for:

- `agent.turn` (root)
  - `llm.call` (with prompt, completion, tokens, cost, latency)
  - `tool.call` (each tool with args, result, duration)
    - nested `llm.call` for sampling-enabled MCP servers
  - `memory.search` (queries and hits)
  - `skill.load` (which skills got pulled in)

Replay any turn, inspect the exact prompt, compare with previous runs, eval completions against datasets. This is how you find the turn that spent $4 on "how should I name this variable".

---

## Level 3 — Helicone (Gateway-First, Zero Code)

Helicone is the "swap the base URL and ship" option. You don't add a tracing SDK — you route your LLM traffic through a proxy that observes it.

```yaml
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    base_url: https://anthropic.helicone.ai
    headers:
      Helicone-Auth: Bearer ${HELICONE_API_KEY}
      Helicone-Property-Session: ${HERMES_SESSION_ID}
      Helicone-Property-Skill: ${HERMES_ACTIVE_SKILL}

  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: https://oai.helicone.ai/v1
    headers:
      Helicone-Auth: Bearer ${HELICONE_API_KEY}
      Helicone-Cache-Enabled: "true"   # Automatic prompt caching
```

Hermes passes session ID and skill name as Helicone custom properties, so you can filter traces by skill/session in the Helicone UI. Cache hits (identical prompts) are free — this alone cuts bills noticeably for repetitive skills.

Pick Helicone over Langfuse when:

- You want zero code-level integration
- You want provider-level prompt caching for free
- You mostly care about cost + latency dashboards, not prompt management

---

## Level 3 — OpenTelemetry → Phoenix (Standards-First)

If you already run OpenTelemetry (Grafana, Datadog, Honeycomb), wire Hermes into your existing pipeline:

```yaml
observability:
  otel:
    enabled: true
    endpoint: https://otel.yourdomain.com:4318
    protocol: http/protobuf
    headers:
      authorization: Bearer ${OTEL_TOKEN}
    attributes:
      service.name: hermes-prod
      deployment.environment: production
```

Hermes emits `gen_ai.*` spans following the [OpenInference](https://github.com/Arize-ai/openinference) conventions. Point them at [Arize Phoenix](https://phoenix.arize.com) (self-hosted or cloud) for an LLM-specific view; or at your existing Grafana/Tempo for a "one pane of glass" view.

---

## Cost Routing Playbook (The One That Actually Saves Money)

### Rule 1: Route by Task Complexity, Not Default

Most Hermes cost bloat comes from using Claude Opus / GPT-5 for tasks Kimi / GLM / MiniMax would handle identically. Set up a **task-aware default**:

```yaml
model_routing:
  default:
    model: claude-sonnet-4-20250514
    provider: anthropic
  routes:
    - match: { intent: [classification, extraction, triage, sum_under_500_tokens] }
      model: gemini-2.5-flash
      provider: openrouter
    - match: { intent: long_context, tokens_gte: 150000 }
      model: gemini-2.5-pro
      provider: openrouter
    - match: { intent: [write_code, refactor, debug], complexity: medium }
      model: glm-5.1
      provider: zai
    - match: { intent: [write_code, refactor, debug], complexity: high }
      model: claude-sonnet-4-20250514
      provider: anthropic
    - match: { intent: [reasoning, math], complexity: high }
      model: gpt-5.4
      provider: openai
```

Hermes classifies intent via a tiny prompt (~100 tokens) and routes accordingly. Empirically:

| Scenario | Naive default (Sonnet 4.5) | Routed | Savings |
|----------|----------------------------|--------|---------|
| Feature implementation (100 calls) | ~$34 | ~$3 (mostly Kimi) | 91% |
| Long-doc summarization (10 calls, 200K each) | ~$42 | ~$4 (Gemini 2.5 Pro) | 90% |
| Daily classification triage | ~$18/day | ~$1/day (Flash) | 94% |

### Rule 2: Prompt Caching Is Free Money

Every stable chunk (system prompt, skill, SOUL.md, memory digest) should be cached:

```yaml
prompt_caching:
  enabled: true
  providers: [anthropic, openai, helicone]
  cache_system_prompt: true          # Biggest win
  cache_skills: true
  cache_memory_digest: true
  min_cache_tokens: 1024             # Anthropic's minimum
```

Anthropic's prompt caching discount is ~90% on cached reads. For a 5K-token system prompt used 100 times a day, that's a real $2–5 a day saved.

### Rule 3: Use Fast Mode Surgically

[Fast Mode](./part14-fast-mode-watchers.md) (`/fast`) costs more per token but reduces queue latency. Use it for:

- Interactive CLI sessions where you're watching the output
- Telegram conversations where the user is waiting
- Real-time voice flows

Don't use it for:

- Cron / scheduled tasks
- Nightly analysis jobs
- Long bulk operations

```yaml
fast_mode:
  defaults:
    cli: on
    telegram: on
    discord: on
    cron: off
    webhooks: off
  user_override: true                # User can toggle with /fast
```

### Rule 4: Context Is the Real Cost — Use `/compress`

Most sessions' 100th turn costs 10x the 10th turn. [`/compress <topic>`](./part14-fast-mode-watchers.md#compress-topic--guided-compression) plus the pluggable context engine can cap per-turn cost:

```yaml
compression:
  auto:
    enabled: true
    at_tokens: 48000                 # Compress when session exceeds this
    preserve:
      - last_n_turns: 10
      - tool_results_matching: "error|ERROR|failed"
    topics_from: active_skill         # Use active skill name as compression topic
```

### Rule 5: Alert on Cost Anomalies

```yaml
alerts:
  cost_spike:
    window: 1h
    threshold_usd: 5                 # Alert if > $5 in an hour
    channel: telegram_private
  token_anomaly:
    window: 10m
    threshold_tokens_per_turn: 30000
    channel: telegram_private
```

Catches runaway loops (a skill stuck in a retry tornado) and prompt injection attempts (attacker trying to burn your tokens).

---

## Eval-Driven Regression Prevention

Once you have Langfuse, add a dataset + evals for your critical paths:

```bash
# One-time setup
hermes evals init
hermes evals dataset create telegram-support-flows
hermes evals dataset add telegram-support-flows ~/.hermes/traces/support/*.json

# Run on every release
hermes evals run telegram-support-flows --model claude-sonnet-4-20250514
hermes evals run telegram-support-flows --model glm-5.1     # Check if cheaper model still passes
hermes evals compare
```

This is how you confidently swap a $10/Mtok model for a $0.30/Mtok one — empirically, not by vibes.

---

## What's Next

- [Part 19: Security Playbook](./part19-security-playbook.md) — set cost alerts as an injection-detection signal
- [Part 17: MCP Servers](./part17-mcp-servers.md) — MCP sampling costs show up in traces too
- [Part 14: Fast Mode](./part14-fast-mode-watchers.md) — the fast-mode toggle referenced above
- [Part 6: Context Compression](./part6-context-compression.md) — the compression system that backs Rule 4
