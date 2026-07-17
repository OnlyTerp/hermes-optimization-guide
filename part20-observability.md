# Part 20: Observability & Cost Control — Langfuse, Helicone, Kanban, /usage, Routing Playbooks

*You can't optimize what you can't see. Hermes tracks tokens, latency, and errors natively, but once you're running across CLI + Telegram + Discord + Google Chat + LINE + SimpleX + Teams + cron + Kanban worker lanes, you want a real tracing stack. This part sets up Langfuse, Helicone, or OpenTelemetry → Phoenix with one config block, then gives you the cost-routing playbook that dropped our test deployment from $34 to $3 per feature implementation.*

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

Langfuse is the "everything in one place" option: tracing, prompt management, evals, self-hostable. If you're not sure where to start, start here. Since v0.12, Langfuse ships as a bundled Hermes plugin, so prefer enabling that over hand-rolled hooks.

### Setup (Hosted Cloud)

```bash
pip install langfuse
hermes plugins enable observability/langfuse
```

Then put the keys in `~/.hermes/.env` (the plugin reads env vars, not a YAML
block — there is no `observability:` key in `config.yaml`):

```bash
# ~/.hermes/.env  (chmod 600)
HERMES_LANGFUSE_PUBLIC_KEY=pk-lf-...
HERMES_LANGFUSE_SECRET_KEY=sk-lf-...
HERMES_LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted URL

# Optional knobs
HERMES_LANGFUSE_ENV=production            # tags traces with an environment
HERMES_LANGFUSE_RELEASE=v0.14.0           # tags traces with a release
HERMES_LANGFUSE_SAMPLE_RATE=0.5           # 0.0–1.0; lower for very high volume
HERMES_LANGFUSE_MAX_CHARS=12000           # per-field cap before truncation
HERMES_LANGFUSE_DEBUG=true                # verbose plugin logging
```

Get the keys from https://cloud.langfuse.com → Settings → API Keys. Free tier
covers most individual users. Without the SDK or credentials the plugin
fails-open (hooks no-op silently). Verify with `hermes plugins list` — the row
for `observability/langfuse` should show `enabled`.

### Self-Hosted Langfuse

For privacy or compliance, one-liner on a VPS with Docker:

```bash
curl -fsSL https://langfuse.com/docker-compose.yml -o langfuse.yml
docker compose -f langfuse.yml up -d
```

Point `HERMES_LANGFUSE_BASE_URL` at your domain. Hermes sends OTLP over HTTPS, so Caddy with Let's Encrypt just works.

### What You See

Each Hermes turn becomes a trace. Each trace has spans for:

- `agent.turn` (root)
  - `llm.call` (with prompt, completion, tokens, cost, latency)
  - `tool.call` (each tool with args, result, duration)
    - nested `llm.call` for sampling-enabled MCP servers
  - `memory.search` (queries and hits)
  - `skill.load` (which skills got pulled in)
  - `kanban.task` / `kanban.worker` when a durable board lane claims or completes work

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

If you already run OpenTelemetry (Grafana, Datadog, Honeycomb), point an OTLP
collector at Hermes's standard `OTEL_*` environment variables. Hermes does not
have an `observability: otel:` config block — wiring is done via the OpenTelemetry
SDK's standard env vars in `~/.hermes/.env`:

```bash
# ~/.hermes/.env
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.yourdomain.com:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_HEADERS=authorization=Bearer ${OTEL_TOKEN}
OTEL_SERVICE_NAME=hermes-prod
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production
```

If you want LLM-shaped `gen_ai.*` spans (OpenInference conventions), enable
Langfuse's plugin and point its OTLP exporter at your collector via the Langfuse
self-hosted route; or run [Arize Phoenix](https://github.com/Arize-ai/phoenix) as your
collector and let it ingest the raw OTLP stream.

---

## Cost Routing Playbook (The One That Actually Saves Money)

> **Heads-up (2026-04):** Hermes used to ship a `smart_model_routing:` config
> block that routed short turns to a cheap model. It was removed upstream in
> commit `424e9f36b` ("refactor: remove smart_model_routing feature", #12732)
> after the heuristic proved too coarse in practice. Current Hermes has **no
> built-in intent/complexity classifier** — there is no `model_routing:` block
> with `intent:`, `complexity:`, or `match:` keys. The advice below uses the
> primitives that actually exist: the primary `model:` / `provider:`, the
> per-task `auxiliary:` block, `provider_routing:` for OpenRouter, and
> `hermes fallback` for failover. If you see a config example elsewhere that
> looks like a routing DSL, treat it as a feature request, not a feature.

### Rule 1: Pick a Smart Primary, Then Push Side-Tasks to Cheaper Models

Most Hermes cost bloat is not the main agent — it's the auxiliary calls
(vision OCR, web extraction, context compression, summarization, image
classification) silently running on whatever your primary model happens to be.
Set the primary once, then point each `auxiliary:` task at a fast/cheap model
that's good enough for that specific job:

```yaml
# ~/.hermes/config.yaml
# Primary — the model that drives your tool-calling loop.
model: claude-sonnet-5
provider: anthropic

# Per-task auxiliary models. Empty model = provider default.
# These are independent of the primary; setting one here does NOT change
# how your interactive turns are routed.
auxiliary:
  vision:
    provider: openrouter
    model: google/gemini-3-flash
  web_extract:
    provider: openrouter
    model: google/gemini-3-flash
  compression:
    provider: openrouter
    model: google/gemini-3-flash
  summarization:
    provider: openrouter
    model: google/gemini-3-flash

# Failover chain — tried in order when the primary fails with rate-limit /
# overload / connection errors. Manage interactively with `hermes fallback`.
# (Edit via the command, not by hand — it lives in a separate state file.)
```

Empirically on this maintainer's setup:

| What dominated the bill before | What fixed it | Approx. savings |
|---|---|---|
| Compression on every long turn running through Claude Sonnet | `auxiliary.compression` → `google/gemini-3-flash` | ~80% on compression-heavy sessions |
| Web-extract tool calling Sonnet for every fetched page | `auxiliary.web_extract` → `google/gemini-3-flash` | ~90% on research-heavy days |
| Vision OCR on screenshots running through the primary | `auxiliary.vision` → `google/gemini-3-flash` | ~85% on dashboard/screenshot workflows |

For the primary itself, the lever Hermes gives you is your choice of
`model:` + `provider:`. If you want OpenRouter to prefer cheaper providers
for that same model, use `provider_routing:` (the only routing DSL Hermes
actually reads):

```yaml
provider_routing:
  sort: price              # or "throughput" / "latency"
  # only: [anthropic, google]
  # ignore: [deepinfra]
  # order: [anthropic, google, together]
  # require_parameters: true
  # data_collection: deny
```

### Rule 2: Use the Caching You Actually Get

Two cache layers exist in current Hermes; neither needs a per-tool allow-list.

**Anthropic prompt caching** (Claude via the native Anthropic API or OpenRouter)
— configured globally with one key:

```yaml
prompt_caching:
  cache_ttl: "5m"          # or "1h" — those are the only two Anthropic tiers
```

Hermes auto-marks stable prefixes (system prompt, skills, SOUL.md, persistent
memory) as cacheable. Cached reads are ~90% off, so for a 5K-token system
prompt re-used 100×/day you save a real $2–5/day on Sonnet-class models.
Per-component toggles like `cache_system_prompt:` / `cache_skills:` /
`min_cache_tokens:` are **not** real config keys — don't paste them.

**OpenRouter response caching** (separate mechanism — keys identical requests
to the same response, billed at zero):

```yaml
openrouter:
  response_cache: true
  response_cache_ttl: 300  # seconds; 1–86400
```

### Rule 2B: Watch Cold Browser Starts in Logs, Not Spans

The browser/CDP-vs-computer-use distinction the previous rev described
(`telemetry: spans: browser_cdp: true`) was not a real config block. To catch
cold browser startups today, grep the logs:

```bash
hermes logs tail -f --level WARNING | grep -iE 'cdp|browser_use|chrome'
```

…or set a Langfuse alert on the `browser_use` / `computer_use` tool spans the
plugin already emits with their duration. The thing to actually watch for is
repeated multi-second `browser_use.launch` spans, which usually mean Chrome
died, the profile changed, or a sandbox reset blew away the persisted
connection.

### Rule 3: Use Fast Mode Surgically

[Fast Mode](./part14-fast-mode-watchers.md) (`/fast`) costs more per token but
reduces queue latency. It's a **runtime toggle**, not a YAML block — there is
no `fast_mode:` key in `config.yaml`. Use the slash command:

```
/fast on        # opt the current session into Priority Processing / Fast Mode
/fast off       # back to normal
/fast status    # show the current state
```

Use it for:

- Interactive CLI / Telegram / Discord sessions where someone is watching
- Real-time voice flows

Don't use it for:

- Cron / scheduled tasks
- Nightly analysis jobs
- Long bulk operations

For non-interactive gateways (cron, webhooks), just don't run `/fast on` from
those entry points and you'll stay on normal pricing.

### Rule 4: Context Is the Real Cost — Use `/compress`

Most sessions' 100th turn costs 10× the 10th turn. Hermes ships automatic
context compression keyed on percentage-of-context, not absolute tokens. The
real keys are:

```yaml
compression:
  enabled: true            # default true; set false to manage context manually
  threshold: 0.50          # trigger when session uses this % of the model's context
  target_ratio: 0.20       # fraction of the threshold kept as recent tail
  protect_last_n: 20       # always preserve the last N messages (≈10 turns) intact
```

For guided compression on demand, use the slash command:
[`/compress <topic>`](./part14-fast-mode-watchers.md#compress-topic--guided-compression).
Keys like `compression.auto.at_tokens` / `preserve.tool_results_matching` /
`topics_from` from earlier revs are not real — don't paste them.

If compression-on-every-long-turn is what's burning your bill, route the
compression call itself off the primary model via `auxiliary.compression`
(see Rule 1).

### Rule 5: Alert on Cost Anomalies

Hermes doesn't have a built-in `alerts:` block — `cost_spike` / `token_anomaly`
config keys don't exist in the loader. There are two real options:

1. **Set the alerts in your tracing layer.** Langfuse, Helicone, and Phoenix
   all support per-project cost / token-rate alerts that fire to webhook,
   email, or Slack. This is the right place for them — your tracing backend
   sees every call, including async ones the CLI doesn't.

2. **Roll your own from logs.** If you'd rather stay local, tail
   `~/.hermes/logs/agent.log` (or `hermes logs tail -f`) into a small script
   that windows over cost / tokens-per-turn and shells out to `hermes send
   telegram …` when a threshold trips. The Telegram gateway from
   [Part 4](./part4-telegram-setup.md) is the most common destination.

Either way, the two patterns worth catching are runaway loops (a skill stuck
in a retry tornado, usually visible as a sudden spike in `tool.call` count per
turn) and prompt-injection attempts that try to burn your tokens by inflating
input length.

---

## The Gateway Token Tax: CLI for Heavy Work, Messaging for Control

<p align="center">
  <img src="./assets/token-tax.svg" alt="The gateway token tax — CLI/TUI ~6–8k vs messaging gateways ~15–20k tokens of tool definitions per turn, and the division of labor that follows" width="920">
</p>

The single biggest hidden cost in a chat-first Hermes setup, measured repeatedly by the community in July 2026: **the messaging gateways carry ~15–20k tokens of tool definitions per turn**, while the CLI carries **~6–8k** for the same work. That's 2–3× the fixed overhead on *every* turn — before you've said anything. (One user burned 121k tokens just *wiring Telegram to the Desktop app*.)

The fix isn't to abandon your phone — it's a division of labor:

| Surface | Use for | Why |
|---------|---------|-----|
| **CLI / TUI** | Long coding runs, research, bulk work | Lowest per-turn overhead, best cache behavior |
| **Kanban** ([Part 23](./part23-tenacity-stack.md)) | Anything that should survive restarts | Board persists; workers run lean |
| **Telegram / Discord / Slack** | Kickoff, steering, receiving results | High overhead is fine for short control turns |

Use `/usage --by-gateway` to see your own split — if a messaging gateway dominates your token spend on work that didn't need to *originate* there, you've found the money.

Two related cache facts (full detail in [Part 27](./part27-power-secrets.md)):

- **Switching models mid-session resets the prompt cache** — the cache key includes the model, so the next turn re-reads the whole history at full input price. Batch model switches, or delegate the odd-model step to a subagent.
- **Credential-pool rotation is also a cache miss** — multiple keys per provider (`hermes auth add <provider> --api-key ...`) keep you alive through rate limits, but each rotation re-reads the full history. Budget for it on long sessions.

---

## Benchmark the Stack, Not the Model

July's WolfBench data made this concrete: the **same model** (GPT-5.6 Sol, max reasoning) scored 86.7% on Codex at ~$90/run vs 84.5% on Hermes at ~$173/run — the harness used ~2× the tokens for the same brain. Takeaways for Hermes specifically:

1. **A model's cost ranking changes per harness.** Never assume a benchmark run on another agent transfers.
2. **On Hermes, the cost-efficient frontier pick beats the absolute-best pick** more often than not (July example: Terra ~3.6 points behind Sol at ~44% lower cost).
3. **High-reasoning models generate busywork** — self-assigned hashing, redundant test-writing, verification loops of their own verification. Cap `/goal` scope with explicit completion contracts ([Part 26](./part26-moa-verification.md)), and never stack the same high-reasoning model as both orchestrator and worker — the busywork compounds.
4. **Free tiers die fast under agent traffic.** A free-tier provider that lasts a month of chat lasts a day of agent loops. Treat free lanes as burst capacity, not a plan.

Run your own numbers: pick 3–5 representative tasks, run them through your actual config on two candidate models, and compare `/usage` + Langfuse traces. An hour of benchmarking regularly saves hundreds of dollars a month.

---

## Langfuse v4 / OpenTelemetry-Native Path

Langfuse v4 is OTEL-native: it accepts spans directly at `/api/public/otel`, so you can also run a standard **OTel Collector in front of Langfuse** — auth separation, plus fan-out to a second backend (Grafana/Datadog) from one stream. Three currency notes for July 2026:

- **Local models cost $0 in dashboards unless you define prices.** Add pricing for your local models in Langfuse and emit `gen_ai.usage.*` token counts, or your cost dashboards will lie by omission.
- **Watch for double-counted agent spans** — a parent `invoke_agent` span plus its child `chat` span can both carry usage. Filter one level or use a current SDK.
- Langfuse's **root-observations default changed on 2026-07-15** — if you built dashboards on the old default, re-check them after upgrading.

---

## Eval-Driven Regression Prevention

Hermes does not ship a built-in `hermes evals` subcommand — that's a Langfuse
workflow, not a Hermes one. Once Langfuse is wired up, do the eval loop on the
Langfuse side:

1. In the Langfuse UI, build a **dataset** from real traces you want to
   protect (e.g. last week's successful Telegram support turns).
2. Define a small **evaluator** (LLM-as-judge or programmatic) for the
   property you care about — "answers the user's question", "doesn't
   hallucinate a price", "calls the right tool".
3. Re-run the dataset against alternate models from Langfuse's Playground or
   via Langfuse's Python SDK and compare scores before flipping a cheap model
   into production.

This is how you confidently swap a $10/Mtok model for a $0.30/Mtok one —
empirically, not by vibes. See
[Langfuse Datasets & Experiments](https://langfuse.com/docs/datasets/overview)
for the current API.

---

## What's Next

- [Part 19: Security Playbook](./part19-security-playbook.md) — set cost alerts as an injection-detection signal
- [Part 17: MCP Servers](./part17-mcp-servers.md) — MCP sampling costs show up in traces too
- [Part 14: Fast Mode](./part14-fast-mode-watchers.md) — the fast-mode toggle referenced above
- [Part 6: Context Compression](./part6-context-compression.md) — the compression system that backs Rule 4
