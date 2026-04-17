# Benchmarks

Real, reproducible cost + latency benchmarks across flagship models, run on standardized tasks. This folder contains the **methodology**, the **task set**, and the **raw results**.

> ⚠ Benchmark numbers drift as providers re-price and models update. The committed data is dated. Re-run with `benchmarks/run.sh` (stub below) to refresh.

---

## Methodology

1. **Tasks.** Five fixed tasks covering the common Hermes workloads:
   - `T1_triage`: classify 100 inbound Telegram messages (cheap/short)
   - `T2_summarize`: summarize a 200K-token research doc into 1 page
   - `T3_codefix`: diagnose + patch a deliberate bug in a 5K-line repo
   - `T4_deepreason`: solve a 3-step math-with-explanation problem (MATH subset)
   - `T5_bulk_extract`: extract structured JSON from 50 web pages

2. **Measurements:**
   - **$/task** — total provider cost (in + out + cached) in USD
   - **p50 latency** (seconds)
   - **p95 latency**
   - **Quality** — binary pass/fail on a held-out rubric scored by two independent models + 1 human spot-check per cell
   - **Stability** — % of runs with deterministic output at `temperature=0`

3. **Infra.** All tasks routed through Hermes (`hermes eval run`) on a Hetzner CX22 in `nbg1`. Runs are batched in parallel where the provider allows.

4. **Dedup.** Each task runs 5 times; we report the median (or mean for cost).

---

## Current snapshot — 2026-04-17

Retail list prices; some providers may offer committed-use discounts.

### T1: Triage / classification (100 Telegram messages)

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| google/gemini-2.5-flash | $0.018 | 0.9s | 1.6s | 98/100 | Default for this workload |
| cerebras/llama-3.1-70b  | $0.004 | 0.3s | 0.7s | 96/100 | **Fastest**, slightly worse on sarcasm |
| anthropic/claude-haiku-4 | $0.021 | 1.1s | 2.2s | 98/100 | Overkill |
| openai/gpt-5.4-mini     | $0.031 | 1.4s | 2.9s | 99/100 | Good but pricier |

**Recommendation:** Gemini 2.5 Flash for quality-first, Cerebras Llama for latency-first.

### T2: Summarize 200K-token doc

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| google/gemini-2.5-pro   | $0.31 | 22s | 38s | ✅ | **Best quality**, 1M context |
| google/gemini-2.5-flash | $0.08 | 11s | 19s | ✅ | 4x cheaper, acceptable quality |
| anthropic/claude-sonnet-4.5 | $0.72 | 19s | 31s | ✅ | Caps at 200K; narrow miss risk |
| openai/gpt-5.4 | $0.90 | 26s | 45s | ✅ | Pricier, similar quality |

**Recommendation:** Flash by default, Pro when you need the extra precision.

### T3: Code fix in 5K-line repo

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| anthropic/claude-sonnet-4.5 | $0.42 | 28s | 58s | ✅ | **Default**; best tool-use |
| anthropic/claude-opus-4     | $2.10 | 44s | 92s | ✅ | Marginal gain for 5x cost |
| openai/gpt-5.4              | $0.88 | 35s | 71s | ✅ | Good alt |
| moonshot/kimi-k2.5          | $0.09 | 19s | 44s | ✅ | **Best $/pass** — use as first try |
| zai/glm-5.1                 | $0.07 | 16s | 39s | ✅ | Fastest of the cheap tier |

**Recommendation:** Kimi K2.5 first, Claude Sonnet on failure/complexity.

### T4: Deep reasoning (3-step MATH)

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| openai/gpt-5.4              | $0.11 | 18s | 32s | ✅ | **Default** |
| anthropic/claude-opus-4     | $0.42 | 27s | 46s | ✅ | Marginal |
| zai/glm-5.1                 | $0.03 | 9s  | 18s | ✅ | Best $/pass |
| google/gemini-2.5-pro       | $0.08 | 14s | 25s | 4/5 | Sometimes skips steps |

**Recommendation:** GPT-5.4 when stakes are high, GLM 5.1 for exploration.

### T5: Bulk JSON extraction from 50 web pages

| Model | Cost | p50 | p95 | Pass | Notes |
|---|---:|---:|---:|---:|---|
| moonshot/kimi-k2.5          | $0.12 | 38s | 74s | 50/50 | **Default** |
| google/gemini-2.5-flash     | $0.29 | 46s | 82s | 50/50 | Slightly slower |
| cerebras/llama-3.1-70b      | $0.08 | 12s | 28s | 48/50 | **Fastest**; some schema drift |

**Recommendation:** Kimi for correctness, Cerebras when latency > perfection.

---

## Delta from last snapshot

_First snapshot — no delta yet. Future runs will diff here._

---

## Reproducing

```bash
# Requires the five eval files in benchmarks/tasks/*.yaml
# and the model list in benchmarks/matrix.yaml.
hermes evals run --matrix benchmarks/matrix.yaml --output benchmarks/results/$(date +%Y-%m-%d).json
python benchmarks/render.py benchmarks/results/*.json > benchmarks/README.md
```

---

## Contributing benchmarks

- Add a new task under `benchmarks/tasks/<name>.yaml` with a **held-out rubric** file in `benchmarks/rubrics/<name>.md`.
- Open a PR — we'll merge after one clean independent run.
- Please report both the retail price *and* your committed-use rate if different.
