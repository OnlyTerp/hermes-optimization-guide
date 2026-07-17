# Part 9: Custom Model Providers (Use Any Model You Want)

*Hermes supports any OpenAI-compatible API, plus first-class native adapters for Nous Portal, Anthropic, OpenAI/Codex, OpenRouter, AWS Bedrock, Azure AI Foundry, Google Gemini, Google Vertex AI, LM Studio, xAI, Xiaomi MiMo, Kimi/Moonshot, z.ai/GLM, MiniMax, Arcee, GMI Cloud, Tencent TokenHub, Hugging Face, Cerebras, Groq, Fireworks, Vercel AI Gateway, Ollama, MoA virtual models, and provider plugins. This is the July 1, 2026 cheat sheet.*

> **What's new since the v0.14 guide refresh** — v0.17 puts Cursor's **Composer** (`grok-composer-2.5-fast`, 200K context) in the xAI OAuth picker; v0.18 adds a first-class **Google Vertex AI** provider (auto-minted, auto-refreshed OAuth2 tokens from a service account — no static key, no mid-session expiry) and makes every **Mixture-of-Agents preset a selectable model** under a `moa` provider ([Part 26](./part26-moa-verification.md)). **Breaking:** the Gemini-CLI OAuth providers (`google-gemini-cli`, `google-antigravity`) were **removed in v0.18** — migrate to a `GEMINI_API_KEY` or Vertex AI.
>
> **Mid-July 2026:** **Kimi K3** landed day-one in Hermes (Nous Portal, Kimi Direct, OpenRouter — **update Hermes before using Kimi Direct**), and OpenAI's **GPT Sol / Terra / Luna** family is reachable via Nous Portal, a Codex/ChatGPT subscription, or OpenRouter. See [The Mid-July Model Landscape](#the-mid-july-2026-model-landscape) below.

---

## Native Adapters vs Generic OpenAI-Compatible

As of v0.14.0 (May 2026), Hermes ships **native adapters** for a large provider set, plus a provider-plugin surface for out-of-tree backends. Native adapters know about provider-specific features that a generic OpenAI-compatible wrapper can't:

| Provider | Native adapter? | Notable feature |
|----------|-----------------|-----------------|
| **Nous Portal** | Yes | Auth via `hermes model` (no bare API key). Unlocks the [Tool Gateway](./part13-tool-gateway.md). |
| **Anthropic** | Yes | Native prompt caching, extended thinking, `/fast` priority tier |
| **OpenAI** | Yes | Native responses API, reasoning effort levels, `/fast` priority tier |
| **OpenAI Codex OAuth** | Yes | ChatGPT/Codex login through `hermes model`, no API key |
| **AWS Bedrock** | Yes | Converse API, IAM credentials, cross-region inference profiles, Bedrock Guardrails |
| **Azure AI Foundry** | Yes | Auto-detects OpenAI-style vs Anthropic-style deployments and context length |
| **LM Studio** | Yes | Local `/models` discovery, optional auth, reasoning transport, `hermes doctor` checks |
| **xAI / SuperGrok** | Yes | SuperGrok OAuth, Grok 4.3 1M context, `x_search`, and xAI image/STT/TTS integrations including Custom Voices |
| **Xiaomi MiMo** | Yes | Native reasoning modes (`low`/`medium`/`high`) exposed as config |
| **Kimi / Moonshot** | Yes | 200K+ context, great for LightRAG entity extraction (see [Part 3](./part3-lightrag-setup.md)) |
| **z.ai / GLM** | Yes | Strong open-weight tool-use models; good cheap fallback for planning/exploration |
| **Google Gemini (direct)** | Yes | 1M context; native prompt caching on Pro; image/video-capable model routing |
| **Google Vertex AI** | Yes | Gemini via your GCP service account / ADC; short-lived OAuth2 tokens auto-minted and refreshed |
| **MoA (virtual)** | Yes | Every Mixture-of-Agents preset is a pickable model — see [Part 26](./part26-moa-verification.md) |
| **MiniMax** | Yes | API key or OAuth; native streaming and TTS |
| **GMI Cloud** | Yes | Hosted open models behind a native provider |
| **Tencent TokenHub** | Yes | Tencent model routing through TokenHub aliases |
| **Arcee** | Yes | AFM-4.5 function-calling specialist, cheap |
| **Cerebras** | Yes | 2000+ tok/s inference |
| **Groq** | Yes | Fast hosted Llama / Qwen |
| **Fireworks** | Yes | Qwen3-Embedding-8B (recommended for LightRAG) |
| **Vercel AI Gateway** | Yes | Dynamic model discovery, pricing metadata, attribution |
| **Hugging Face** | Yes | Any TGI / TEI endpoint (self-hosted or Inference Endpoints) |
| **OpenRouter** | Yes | Pass-through to 200+ models; respects native adapter quirks when downstream is one |
| **Ollama** (local) | Generic | OpenAI-compatible, zero auth |
| **Provider plugin** | Plugin | Drop in a `ProviderProfile` without patching Hermes core |
| **Anything else** | Generic | Any OpenAI-compatible `base_url` |

### SuperGrok OAuth + Grok 4.3

v0.14 makes xAI a first-class Hermes provider instead of just another OpenAI-compatible key. Use SuperGrok OAuth when you already pay for it; use `XAI_API_KEY` for service-account automation. Grok 4.3 is the live-search/default-current-events lane now because it combines 1M context, X-native retrieval, and voice/image integrations.

```bash
hermes model     # choose xAI / SuperGrok OAuth
```

```yaml
models:
  research_live:
    provider: xai
    model: grok-4.3
    context_tokens: 1048576
tools:
  x_search:
    enabled: true
    auth: oauth
```

Keep it out of cheap cron loops; route it explicitly for live events, X threads, and million-token synthesis.

Pick the native adapter when one exists — you get the provider-specific features for free. Fall back to the generic OpenAI-compatible path only for endpoints that don't have a native adapter yet.

### Provider Cheat Sheet (July 1, 2026)

The exact "best model" moves weekly, so treat this as a routing posture rather than a leaderboard. Use `hermes model` for live picker data, then pin only what you need reproducible.

| Need | Start here | Why |
|------|------------|-----|
| Default coding / refactors | Anthropic Sonnet 5, Claude Code, or Codex OAuth | Best reliability for patch-heavy work; Codex OAuth avoids API-key churn |
| Deep reasoning / high stakes | GPT-5.5 reasoning or Anthropic Opus 4.7 | Use explicitly; do not make it the default for cron/bulk tasks |
| Long-context repo or document reads | Gemini 3.1 Pro/Flash, Grok 4.3, or OpenRouter equivalent | Huge window, cheap enough for map/reduce, video, and summarization |
| Cheap daily driver | Gemini Flash (API key) + Kimi K2.6 + z.ai/GLM | Good quality/cost mix, especially with auxiliary routing |
| Committee for hard calls | A `moa` preset of 2–3 frontier models | Visible multi-model deliberation; ~N× cost, use sparingly ([Part 26](./part26-moa-verification.md)) |
| Enterprise / VPC / compliance | AWS Bedrock or Azure AI Foundry | IAM/Azure auth, guardrails, private deployments, audit controls |
| Local/privacy/offline | LM Studio or Ollama | No cloud egress; great for extraction, embeddings, and drafts |
| Ultra-fast interactive turns | Cerebras or Groq | Very high tokens/sec; useful for classification and short-form chat |
| Current-events / X search | xAI Grok 4.3, `x_search`, or tool-backed web search | Grok has native live-X search; Tool Gateway can cover broader web |

> Pricing and context windows change too quickly to hardcode. Hermes now pulls OpenRouter and Nous Portal picker lists from a remote manifest, while provider APIs supply pricing/context metadata where available.

### The Mid-July 2026 Model Landscape

A snapshot of what moved this month — treat as a routing posture, verify against the live picker:

| Lane | Pick | Notes |
|------|------|-------|
| Daily driver | **GPT Luna** or a DeepSeek-Flash-class model | Cheap enough for cron and chat |
| Hard coding / judgment | **GPT-5.6 Sol** or **Kimi K3** | K3 has notably strong parallel tool-calling; watch OpenRouter K3 pricing, it burns wallets fast |
| Cost-conscious frontier on Hermes | **GPT Terra** | ~3.6 points behind Sol on the July WolfBench at ~44% lower cost *on this harness* ([Part 20](./part20-observability.md#benchmark-the-stack-not-the-model)) |
| Fast cheap coding | Composer 2.5 Fast (xAI OAuth) | Still available through the Grok subscription path |
| Local | Qwen3.6 35B-A3B, Bonsai-27B (~36 t/s on 16GB), Gemma4 A4B | [Part 25](./part25-nvidia-local.md) |

Two hard facts to save you an evening:

- **Anthropic subscriptions do NOT work natively in Hermes.** Working subscription auths: OpenAI Codex/ChatGPT, Kimi, Qwen, Z.ai, OpenCode. For Claude models use an API key (direct or OpenRouter) — or orchestrate a Claude Code terminal as a worker lane ([Part 18](./part18-coding-agents.md)) if you only have the subscription.
- **High-reasoning models overwork.** Sol in particular generates self-assigned busywork on agent harnesses. Cap goals with completion contracts ([Part 26](./part26-moa-verification.md)) and never run the same high-reasoning model as both orchestrator and delegated worker.

### Credential Pools (Multiple Keys per Provider)

Distinct from the fallback chain: you can register **several keys for the same provider**, and Hermes rotates within the pool on rate-limit/quota errors *before* falling over to another provider:

```bash
hermes auth add openrouter --api-key sk-or-...
hermes auth add openrouter --api-key sk-or-...   # second key, same provider
hermes auth list
```

Pool first, fallback second. Caveat: every rotation is a **prefix-cache miss** — the next turn re-reads the whole session history at full input price ([Part 20](./part20-observability.md#the-gateway-token-tax-cli-for-heavy-work-messaging-for-control)). Nous Portal's single OAuth usually doesn't need a pool.

---

### Nous Portal — OAuth, Not an API Key

Nous Portal uses an OAuth flow via `hermes model` instead of a bare API key. After auth, credentials live in `~/.hermes/auth.json` (never in `.env`). Re-auth when it expires:

```bash
hermes model
# Pick "Nous Portal" → complete the browser OAuth flow
```

If you're on a paid subscription, the setup also offers to enable the [Tool Gateway](./part13-tool-gateway.md) — web search, image gen, TTS, and browser automation through your subscription, no extra keys needed.

### Google: API Key or Vertex AI (Gemini OAuth Is Gone)

> **Migration note (v0.18):** the Gemini-CLI OAuth providers (`google-gemini-cli`, `google-antigravity`) were **removed**. If your config still points at them, model selection will fail after upgrading. Pick one of the two supported paths below.

**Path 1 — API key (simplest).** Set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and use the native Google Gemini provider. Free-tier keys work.

**Path 2 — Vertex AI (GCP shops).** New in v0.18: a first-class Vertex provider over Vertex's OpenAI-compatible endpoint. Vertex has no static API key — every request needs a short-lived (~1h) OAuth2 token minted from a service-account JSON or Application Default Credentials. Hermes mints and auto-refreshes these for you, so sessions no longer die mid-run on token expiry:

```yaml
providers:
  vertex:
    project_id: ${GOOGLE_CLOUD_PROJECT}
    location: us-central1
    credentials_json: ${GOOGLE_APPLICATION_CREDENTIALS}   # or rely on ADC
```

Use Vertex when your org already routes Gemini through Google Cloud (IAM, quotas, audit); use the plain API key everywhere else.

### Cursor's Composer via xAI OAuth

v0.17 put `grok-composer-2.5-fast` — the fast coding model behind Cursor — in the xAI OAuth model picker with its full 200K context. If you have an xAI Grok subscription, you can point Hermes at Composer directly over OAuth, no separate API key: your Grok plan, Hermes' agent loop, Composer's coding speed. It's a strong pick for the fast-coding lane in your routing table.

### AWS Bedrock and Azure AI Foundry — Enterprise Routing Without Proxy Glue

Bedrock uses the native Converse API and the normal boto3 credential chain:

```bash
pip install 'hermes-agent[bedrock]'
hermes model
# Choose "AWS Bedrock" → region → model/profile
```

Use this when you want IAM roles, Bedrock Guardrails, and cross-region inference profiles instead of direct vendor API keys.

Azure AI Foundry handles both endpoint styles:

```bash
hermes model
# Choose "Azure Foundry" → paste endpoint + key
```

Hermes probes the endpoint, detects OpenAI-style `/chat/completions` vs Anthropic-style `/messages`, discovers deployments when possible, and stores the right `api_mode` in `config.yaml`.

### Remote Model Catalog: Stop Hardcoding This Week's Winner

OpenRouter and Nous Portal model pickers now fetch:

```text
https://hermes-agent.nousresearch.com/docs/api/model-catalog.json
```

The cache lives at `~/.hermes/cache/model_catalog.json`. If the manifest is down, Hermes falls back to the disk cache or the bundled snapshot, so model selection still works offline.

### Gemini TTS

Gemini is now one of the practical voice backends alongside Edge, ElevenLabs, OpenAI, MiniMax, Mistral, NeuTTS, and xAI:

```yaml
tts:
  gemini:
    model: gemini-2.5-flash-preview-tts
    voice: Kore
```

`GEMINI_API_KEY` or `GOOGLE_API_KEY` is enough. Output comes back as PCM, wrapped in WAV natively (no extra deps), optionally converted to mp3/ogg via `ffmpeg`. Works for Telegram voice bubbles out of the box.

---

## config.yaml Structure

Models are configured in `~/.hermes/config.yaml`:

> **Security note:** Never put real API keys directly in `config.yaml`. Use environment variable references so keys stay in `~/.hermes/.env` (which should be `chmod 600` and never committed to git). You can also use `hermes auth` to set them securely.
```yaml
# Default model (combined provider/model form, same as `hermes config set model`)
model: anthropic/claude-sonnet-5

# Provider configurations
# API keys are loaded from ~/.hermes/.env automatically.
# Set them with: hermes auth
# Or add to ~/.hermes/.env:
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...
#   CEREBRAS_API_KEY=csk-...
#   FIREWORKS_API_KEY=fw_...
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}

  openai:
    api_key: ${OPENAI_API_KEY}

  bedrock:
    region: us-east-2                  # Auth via AWS_PROFILE, env vars, or instance role

  azure-foundry:
    api_key: ${AZURE_FOUNDRY_API_KEY}
    base_url: ${AZURE_FOUNDRY_ENDPOINT}
    api_mode: chat_completions         # Or anthropic_messages; wizard auto-detects

  lmstudio:
    base_url: http://127.0.0.1:1234/v1
    api_key: ${LM_API_KEY}             # Optional if your LM Studio server requires auth

  xai:
    api_key: ${XAI_API_KEY}
    oauth_enabled: true               # SuperGrok OAuth when available
    live_search: true                 # Grok's live X/Twitter search

  xiaomi:
    api_key: ${XIAOMI_API_KEY}
    reasoning_mode: high              # low / medium / high

  moonshot:                           # Kimi
    api_key: ${MOONSHOT_API_KEY}

  zai:                                # z.ai / GLM
    api_key: ${ZAI_API_KEY}

  minimax:
    api_key: ${MINIMAX_API_KEY}

  gmi:
    api_key: ${GMI_API_KEY}

  tencent-tokenhub:
    api_key: ${TOKENHUB_API_KEY}

  arcee:
    api_key: ${ARCEE_API_KEY}

  cerebras:
    api_key: ${CEREBRAS_API_KEY}
    base_url: https://api.cerebras.ai/v1

  fireworks:
    api_key: ${FIREWORKS_API_KEY}
    base_url: https://api.fireworks.ai/inference/v1

  local:
    base_url: http://localhost:11434/v1
    api_key: ollama  # Ollama doesn't require a real key
```

## Adding a Custom Provider

Any provider that implements the OpenAI chat completions API works:

```yaml
# Add your API key to ~/.hermes/.env:
#   MY_CUSTOM_API_KEY=your-key-here
providers:
  my-custom:
    api_key: ${MY_CUSTOM_API_KEY}
    base_url: https://api.your-provider.com/v1
```

Add the actual key to your `.env` file:

```bash
echo "MY_CUSTOM_API_KEY=<your-key-here>" >> ~/.hermes/.env
chmod 600 ~/.hermes/.env
```

Then use it:

```bash
hermes --provider my-custom --model their-model-name
```

## Model Aliases (Quick Switching)

Add aliases to switch models without typing full names:

```yaml
model_aliases:
  fast:
    model: cerebras/qwen-3-32b
    provider: cerebras
  smart:
    model: claude-opus-4.7
    provider: anthropic
  local:
    model: nemotron:latest
    provider: local
```

Use in chat:

```
/model fast      # Switch to Cerebras Qwen 3 32B
/model smart     # Switch to Claude Opus
/model local     # Switch to local Ollama model
```

## Provider Comparison (What We Actually Use)

| Provider | Speed | Cost | Best For |
|----------|-------|------|----------|
| Cerebras | 2000+ tok/s | Cheap | Fast inference, bulk tasks, coding |
| Anthropic | ~100 tok/s | Premium | Complex reasoning, long context |
| OpenRouter | Varies | Varies | Model variety, fallback provider |
| Fireworks | Fast | Cheap | Embeddings, specialized models |
| Ollama (local) | Varies | Free | Privacy, offline, experimenting |

**Our setup:** Cerebras for speed, Anthropic for quality, Ollama for local models and embeddings.

## Routing Cheat Sheet by Task Type

Use these as opinionated defaults, then tune with [Part 20's cost-routing playbook](./part20-observability.md#cost-routing-playbook-the-one-that-actually-saves-money):

| Task | First choice | Fallback (cheaper) | Fallback (fastest) |
|------|--------------|--------------------|--------------------|
| Daily conversation | Anthropic Sonnet 5 | Gemini Flash or z.ai/GLM | Cerebras Qwen 3 |
| Coding delegation | Claude Code / Codex OAuth | OpenCode + Kimi K2.6 | xAI Composer 2.5 (OAuth) |
| High-stakes judgment calls | `moa` council preset ([Part 26](./part26-moa-verification.md)) | GPT-5.5 reasoning | — |
| Long-context reads (>200K) | Gemini 3.1 Pro | Gemini Flash | — |
| Classification / triage | Gemini Flash | Cerebras Qwen3 32B | Arcee AFM-4.5 |
| Reasoning (math, planning) | GPT-5.5 reasoning | Anthropic Opus 4.7 | z.ai/GLM |
| Current events / live search | xAI Grok 4.3 + `x_search` | Gemini with grounding | Tool Gateway web search |
| Embeddings (LightRAG) | Qwen3-Embedding-8B (Fireworks) | nomic-embed-text (Ollama) | OpenAI `text-embedding-3-small` |
| TTS (Telegram voice) | xAI Custom Voices or Tool Gateway TTS | Gemini Flash TTS | Edge TTS (free) |
| Vision / video | Gemini 3.1 Pro/Flash | GPT-5.5 multimodal | Claude Sonnet 5 |

---

## Cerebras Gotchas

Cerebras is fast but has quirks:

1. **No system prompt caching.** Every request re-sends the full system prompt. Keep it short.
2. **Rate limits are per-minute, not per-request.** Batch carefully.
3. **Some models don't support tool calling.** Check before using as the main agent model.
4. **Streaming is fast but chunky.** Large responses come in big bursts, not smooth streams.

Config:

```yaml
# Set CEREBRAS_API_KEY in ~/.hermes/.env
providers:
  cerebras:
    api_key: ${CEREBRAS_API_KEY}
    base_url: https://api.cerebras.ai/v1
    # Models: qwen-3-32b, llama-4-scout-17b-16e-instruct
```

## Local Models (Ollama)

Run models locally for free inference:

```yaml
providers:
  local:
    base_url: http://localhost:11434/v1
    api_key: ollama
```

**Best local/open models for Hermes:**
- **Qwen3-Coder-Next** — strongest local coding lane if you have 24GB+ VRAM
- **DeepSeek V4-Flash / V4-Pro** — strong open-weight reasoning/coding if you can host MoE comfortably
- **Qwen3.6-27B / 32B** — practical single-workstation reasoning/coding balance
- **Nemotron 30B** — good all-around fallback, fits in 24GB VRAM

**For embeddings (free):**

```yaml
embedding:
  provider: local
  model: nomic-embed-text
  base_url: http://localhost:11434
```

## Switching at Runtime

```
/model cerebras/qwen-3-32b      # Full model path
/model fast                       # Alias
/model                            # Show current model
```

## Auxiliary Models (Task-Specific Models)

Hermes supports dedicated models for auxiliary task types — the dashboard's Models page ([Part 12](./part12-web-dashboard.md#models)) exposes the everyday ones (compression, vision, title generation, session search, curator), and `config.yaml` covers the full set. Each can have its own provider, model, base_url, api_key, and timeout.

| Task Type | What It Does | Default |
|-----------|-------------|---------|
| `vision` | Image/video analysis, screenshot understanding | auto |
| `web_extract` | Summarizing scraped web pages | auto |
| `compression` | Context compression (summarizing old messages) | auto |
| `title_generation` | Naming sessions | auto |
| `session_search` | Synthesizing answers over past-session search hits | auto |
| `approval` | Deciding whether to auto-approve tool calls | auto |
| `skills_hub` | Skill discovery and matching | auto |
| `mcp` | MCP tool routing | auto |
| `flush_memories` | Memory consolidation and cleanup | auto |
| `curator` | Skill-library hygiene runs ([Part 5](./part5-creating-skills.md)) | auto |

When set to `"auto"` (default), Hermes walks a provider resolution chain: OpenRouter → Nous Portal → Custom endpoint → etc.

**Configure in `~/.hermes/config.yaml`:**

```yaml
auxiliary_models:
  # Use a fast cheap model for compression — it's just summarizing
  compression:
    provider: cerebras
    model: qwen-3-32b
    timeout: 30

  # Use a multimodal model for image/video analysis
  vision:
    provider: openrouter
    model: google/gemini-3.1-flash
    timeout: 60

  # Everything else stays on auto
  session_search: auto
  web_extract: auto
  approval: auto
  skills_hub: auto
  mcp: auto
  flush_memories: auto
```

**Why bother:**
- **Compression** runs on every long session. Using a cheap/fast model saves money without affecting quality (summarization doesn't need Opus).
- **Vision/video** needs a multimodal model. If your main model doesn't do media, set this to one that does.
- **Session search** itself is free — since v0.15 the search is local FTS over the session DB (see Part 7), so there's no per-query model cost to optimize away. The `session_search` aux slot only affects the answer-synthesis step over the hits.
- **Approval** controls auto-execution. A fast model here means less latency on every tool call.

## Fallback Chain

Configure automatic fallback if the primary model fails (same combined `provider/model` strings as [Part 1](./part1-setup.md#model-settings)):

```bash
hermes config set fallback_models '["cerebras/qwen-3-32b", "openrouter/anthropic/claude-sonnet-5", "local/nemotron:latest"]'
```

Hermes tries each in order. If Cerebras is down, it falls back to OpenRouter, then local.

Two rules that save 3am debugging:

- **Every fallback entry needs both a provider and a model** — a bare model name in a `fallback_providers`-style entry fails at the moment you need it most.
- **Put a local model last** (`local/...` via Ollama, or a `custom` provider pointed at llama.cpp/vLLM) as the outage floor. Degraded beats down.

And remember the cache economics of switching: the prompt-cache key includes the model, so **any mid-session model change re-reads the full history at full input price**. Batch your switches, or hand the odd-model step to a subagent with its own context ([Part 8](./part8-subagent-patterns.md)).

---

*Don't lock yourself into one provider. The best model is the one that's fast enough and cheap enough for the task at hand.*
