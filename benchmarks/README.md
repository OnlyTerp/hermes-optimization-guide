# Benchmarks

Real, reproducible cost + latency benchmarks across flagship models, run on standardized tasks. This folder contains the **methodology**, the **task set**, and the **raw results**.

> ⚠ Benchmark numbers drift as providers re-price and models update. The committed results are a dated April 2026 snapshot; `matrix.yaml` has been refreshed with May 2026 frontier IDs (now 13 models). Re-run with [`./run.sh`](./run.sh) before quoting numbers externally.

---

## Methodology

1. **Tasks.** Five fixed tasks covering the common Hermes workloads, one prompt file each under [`tasks/`](./tasks/):
   - `T1_triage`: classify inbound Telegram messages (cheap/short; committed prompt uses 20 messages — the 2026-04-17 snapshot ran 100)
   - `T2_summarize`: summarize a 200K-token research doc into 1 page (the committed prompt is a small stand-in — swap in your own long corpus, identical across models)
   - `T3_codefix`: diagnose + patch a deliberate bug (committed prompt is a single-module distillation of the original 5K-line-repo task)
   - `T4_deepreason`: solve a 3-step math-with-explanation problem
   - `T5_bulk_extract`: extract structured JSON from product-page snippets (committed prompt: 5; snapshot run: 50)

2. **Measurements:**
   - **$/task** — total provider cost (in + out + cached) in USD
   - **p50 latency** (seconds)
   - **p95 latency**
   - **Quality** — binary pass/fail on a held-out rubric scored by two independent models + 1 human spot-check per cell. `run.sh` records run health and tokens; quality scoring stays a human+rubric step on the saved outputs.
   - **Stability** — % of runs with deterministic output at `temperature=0`

3. **Infra.** Hermes has no `hermes evals` subcommand (see [Part 20](../part20-observability.md#eval-driven-regression-prevention)) — the harness is [`run.sh`](./run.sh): plain `curl` against any OpenAI-compatible `/chat/completions` endpoint (OpenRouter by default), timing each call and reading token counts from the response `usage` field. The 2026-04-17 snapshot ran on a Hetzner CX22 in `nbg1`.

4. **Dedup.** Each task runs 5 times; we report the median (or mean for cost).

---

## Dated results snapshot — 2026-04-17

Retail list prices; some providers may offer committed-use discounts.

### T1: Triage / classification (100 Telegram messages)

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| google/gemini-3.1-flash | $0.018 | 0.9s | 1.6s | 98/100 | Refresh against Gemini 3.1 Flash; was default for this workload |
| cerebras/qwen-3-32b  | $0.004 | 0.3s | 0.7s | 96/100 | Refresh against Qwen 3 32B; was **fastest**, slightly worse on sarcasm |
| anthropic/claude-haiku-4 | $0.021 | 1.1s | 2.2s | 98/100 | Overkill |
| openai/gpt-5.5-mini     | $0.031 | 1.4s | 2.9s | 99/100 | Good but pricier; refresh against GPT-5.5-mini |

**Recommendation:** Gemini Flash for quality-first, Cerebras/Qwen for latency-first. Re-run before publishing because May 2026 model IDs changed.

### T2: Summarize 200K-token doc

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| google/gemini-3.1-pro   | $0.31 | 22s | 38s | ✅ | Refresh against Gemini 3.1 Pro; was best quality, 1M context |
| google/gemini-3.1-flash | $0.08 | 11s | 19s | ✅ | Refresh against Gemini 3.1 Flash; was 4x cheaper, acceptable quality |
| anthropic/claude-sonnet-5 | $0.72 | 19s | 31s | ✅ | Caps at 200K; refresh against Sonnet 5 |
| openai/gpt-5.5 | $0.90 | 26s | 45s | ✅ | Refresh against GPT-5.5 |
| xai/grok-4.3 | re-run | re-run | re-run | re-run | New v0.14 1M-context lane; do not quote until refreshed |

> **Note for re-runs:** `matrix.yaml` sets `skip_if_context_lt: 300000` on T2 — `run.sh` now skips every model with a smaller window (Sonnet 5, Opus 4.7, Haiku 4, Kimi K2.6, GLM-5, DeepSeek V4-Pro, Qwen3.6, Qwen 3 32B). The Sonnet 5 row above is from the 2026-04-17 snapshot, which predates that rule and squeezed the doc into its 200K window; a fresh run won't reproduce it.

**Recommendation:** Flash by default, Pro when you need precision, Grok 4.3 when live X context matters.

### T3: Code fix in 5K-line repo

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| anthropic/claude-sonnet-5 | $0.42 | 28s | 58s | ✅ | Refresh against Sonnet 5 |
| anthropic/claude-opus-4.7     | $2.10 | 44s | 92s | ✅ | Refresh against Opus 4.7 |
| openai/gpt-5.5              | $0.88 | 35s | 71s | ✅ | Refresh against GPT-5.5 |
| moonshot/kimi-k2.6          | $0.09 | 19s | 44s | ✅ | Refresh against Kimi K2.6 |
| zai/glm-5                 | $0.07 | 16s | 39s | ✅ | Refresh against GLM-5 |

**Recommendation:** Kimi K2.6 first, Claude Sonnet 5 on failure/complexity.

### T4: Deep reasoning (3-step MATH)

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| openai/gpt-5.5              | $0.11 | 18s | 32s | ✅ | Refresh against GPT-5.5 |
| anthropic/claude-opus-4.7     | $0.42 | 27s | 46s | ✅ | Refresh against Opus 4.7 |
| zai/glm-5                 | $0.03 | 9s  | 18s | ✅ | Refresh against GLM-5 |
| google/gemini-3.1-pro       | $0.08 | 14s | 25s | 4/5 | Refresh against Gemini 3.1 Pro; sometimes skipped steps |

**Recommendation:** GPT-5.5 when stakes are high, GLM-5 for exploration.

### T5: Bulk JSON extraction from 50 web pages

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| moonshot/kimi-k2.6          | $0.12 | 38s | 74s | 50/50 | Refresh against Kimi K2.6 |
| google/gemini-3.1-flash     | $0.29 | 46s | 82s | 50/50 | Refresh against Gemini 3.1 Flash; was slightly slower |
| cerebras/qwen-3-32b      | $0.08 | 12s | 28s | 48/50 | Refresh against Qwen 3 32B; was **fastest** with some schema drift |

**Recommendation:** Kimi for correctness, Cerebras when latency > perfection.

---

## Delta from last snapshot

- 2026-05-25: `benchmarks/matrix.yaml` updated for the v0.14 refresh with Grok 4.3 1M context plus current frontier IDs (GPT-5.5, Claude Sonnet 5 / Opus 4.7, Gemini 3.1, Kimi K2.6, DeepSeek V4-Pro, Qwen3.6) — 13 models total. Results above remain the dated 2026-04-17 run until `./run.sh` is executed again.

---

## Reproducing

```bash
# Prompts live in benchmarks/tasks/*.md; the model x task grid in matrix.yaml.
# Any OpenAI-compatible endpoint works — OpenRouter is the default because
# it serves every model in the matrix behind one key.
export HERMES_BENCH_API_KEY=sk-or-...
./benchmarks/run.sh                            # full 13-model x 5-task grid
./benchmarks/run.sh --model zai/glm-5          # one model
./benchmarks/run.sh --task T1_triage           # one task

# Render the tables (cost from matrix.yaml prices + the usage field):
python3 benchmarks/render.py benchmarks/results/results.csv > snapshot.md
```

Quality (the Pass column) is scored separately against the rubric notes at the bottom of each task file — the harness measures cost, latency, and run health, and deliberately doesn't pretend to auto-grade quality.

---

## Contributing benchmarks

- Add a new task under `benchmarks/tasks/<name>.md` (prompt + a scoring note), and give it an id + `repeats:` entry in `matrix.yaml`.
- Open a PR — we'll merge after one clean independent run.
- Please report both the retail price *and* your committed-use rate if different.
