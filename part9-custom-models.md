# Part 9: Custom Model Providers (Use Any Model You Want)

*Hermes supports any OpenAI-compatible API, plus first-class native adapters for Nous Portal, Anthropic, OpenAI (API key and Codex/ChatGPT OAuth), GitHub Copilot, OpenRouter, AWS Bedrock, Azure AI Foundry, Google Gemini (API key) and Vertex AI, xAI Grok (API key and SuperGrok OAuth), LM Studio, Xiaomi MiMo, Kimi/Moonshot, z.ai/GLM, MiniMax, Arcee, GMI Cloud, Tencent TokenHub, Qwen (DashScope + Portal OAuth), DeepSeek, NVIDIA NIM, StepFun, NovitaAI, Fireworks, Vercel AI Gateway, Ollama Cloud, OpenCode Zen/Go/Free (keyless), MoA virtual models, and provider plugins — plus every plain OpenAI-compatible endpoint (Cerebras, Groq, Together, vLLM, llama.cpp, ...). This is the v0.20.4 ("Herald") cheat sheet, verified against the 2026-08-21 model manifest.*

> **What changed since the v0.18 refresh — v0.20.x is the "Herald" line (v2026.8.18).** Mirrored every **Mixture-of-Agents preset is a selectable model** under a `moa` provider ([Part 26](./part26-moa-verification.md)), **Vertex AI** is a first-class provider (auto-minted, auto-refreshed OAuth2 tokens — no static key, no mid-run expiry), and the old Gemini-CLI OAuth providers (`google-gemini-cli`, `google-antigravity`) are **gone** — migrate to `GOOGLE_API_KEY`/`GEMINI_API_KEY` or Vertex. Since v0.18 the provider surface grew a lot: **credential pools** (`hermes auth add` — several keys per provider, rotation on 429/402/401), the **interactive fallback chain manager** (`hermes fallback`), **GitHub Copilot OAuth**, **Qwen Portal OAuth**, **MiniMax OAuth**, an **OpenCode free keyless tier**, **DeepSeek / NVIDIA NIM / StepFun / NovitaAI** first-class providers, a **subscription proxy** (`hermes proxy`, OpenAI-compatible local endpoint backed by your OAuth — nous/xai upstreams), and **remote model-catalog manifests** so the `/model` picker list updates without a release.
>
> **Model names move fast.** The curated OpenRouter/Nous picker lists are now fetched from a remote manifest (default at time of writing: **z-ai/glm-5.2**; **moonshotai/kimi-k3** carries the "recommended" badge), so treat the picks below as routing *postures*, not a leaderboard — always read the live list with `hermes model`.

---

## Native Adapters vs Generic OpenAI-Compatible

Hermes ships **native adapters** for a large provider set, plus a provider-plugin surface for out-of-tree backends. Native adapters know about provider-specific features that a generic OpenAI-compatible wrapper can't:

| Provider | Native adapter? | Notable feature |
|----------|-----------------|-----------------|
| **Nous Portal** | Yes | OAuth, no bare API key. Unlocks the [Tool Gateway](./part13-tool-gateway.md) and 300+ models. |
| **Anthropic** | Yes | Native prompt caching, extended thinking. OAuth path requires **Claude Max + extra usage credits**; API key works for everyone. |
| **OpenAI (API)** | Yes | Responses API, reasoning effort levels (`openai-api`, `OPENAI_API_KEY`) |
| **OpenAI Codex** | Yes | ChatGPT/Codex device-code OAuth, no API key (provider id `openai-codex`) |
| **GitHub Copilot** | Yes | OAuth device code or a `gho_*`/fine-grained token; GPT-5.x, Claude, Gemini through your Copilot sub (provider id `copilot`) |
| **xAI (Grok)** | Yes | Responses transport; `XAI_API_KEY` or SuperGrok / X Premium+ browser OAuth (`xai-oauth`), same token powers TTS/image/video/transcription |
| **AWS Bedrock** | Yes | Converse API, boto3/IAM credential chain, cross-region inference profiles, Guardrails |
| **Azure AI Foundry** | Yes | Auto-detects OpenAI-style vs Anthropic-style deployments and context length; Microsoft Entra ID option |
| **LM Studio** | Yes | Local `/models` discovery, optional auth, reasoning transport, `hermes doctor` checks |
| **Xiaomi MiMo** | Yes | Native reasoning modes (`low`/`medium`/`high`) exposed as config; MiMo 2.5 Pro era |
| **Kimi / Moonshot** | Yes | 200K+ context; the `kimi-coding` provider (`KIMI_API_KEY`) is great for long reads |
| **z.ai / GLM** | Yes | Open-weight tool-use stars; GLM 5.x is the OpenRouter picker default. Auto-probes global/China/coding endpoints |
| **Google Gemini (direct)** | Yes | API-key only (no consumer-plan OAuth); huge windows (Gemini 3.1 Pro / 3.7 Flash era) |
| **Google Vertex AI** | Yes | Gemini through your GCP project; short-lived OAuth2 auto-minted + refreshed from service-account JSON/ADC |
| **MoA (virtual)** | Yes | Every Mixture-of-Agents preset is a pickable model — see [Part 26](./part26-moa-verification.md) |
| **MiniMax** | Yes | API key (global `minimax` / `minimax-cn`) or browser OAuth (`minimax-oauth`), M2.7-class fast models |
| **Qwen / Alibaba** | Yes | DashScope (`alibaba`, `DASHSCOPE_API_KEY`), Coding Plan (`alibaba-coding-plan`), and consumer Qwen Portal OAuth (`qwen-oauth`) |
| **DeepSeek** | Yes | Direct `deepseek` provider; DeepSeek V4-flash / V4-pro era (also on OpenRouter/Nous) |
| **NVIDIA NIM** | Yes | Nemotron 3-class models via build.nvidia.com (free key) or a local NIM endpoint; `NVIDIA_BASE_URL` flips cloud ↔ local |
| **StepFun** | Yes | Step-3.x flash class, OpenAI-compatible, `STEPFUN_API_KEY` |
| **NovitaAI** | Yes | 200+ models one API key, Agent Sandbox, GPU Cloud |
| **GMI Cloud** | Yes | Hosted open models behind a native provider |
| **Tencent TokenHub** | Yes | Tencent HY3 routing through TokenHub aliases |
| **Arcee AI** | Yes | Trinity-class function-calling specialists, cheap (`ARCEEAI_API_KEY`) |
| **Fireworks** | Yes | Native catalog IDs (e.g. `accounts/fireworks/models/kimi-k2p6`); Qwen3-Embedding-8B for LightRAG |
| **Vercel AI Gateway** | Yes | `ai-gateway` provider, dynamic model discovery |
| **Hugging Face** | Yes | `HF_TOKEN`, routers to 20+ open models, `:fastest`/`:cheapest` suffixes |
| **Ollama Cloud** | Yes | Managed open-weight catalog, no local GPU (`OLLAMA_API_KEY`) |
| **OpenCode Free** | Yes | Keyless — zero-config anonymous tier (`/model free`); also OpenCode Zen/Go keyed tiers |
| **OpenRouter** | Yes | Pass-through to 400+ raw models; curated picker list; respects native quirks downstream |
| **Ollama** (local) | Generic | OpenAI-compatible, zero auth |
| **Cerebras / Groq / Together / vLLM / llama.cpp** | Generic | Any OpenAI-compatible `base_url` via a named `custom` provider |
| **Provider plugin** | Plugin | Drop in a `ProviderProfile` without patching Hermes core |
| **Anything else** | Generic | Any OpenAI-compatible `base_url` |

Pick the native adapter when one exists — you get the provider-specific features for free. Fall back to the generic OpenAI-compatible path only for endpoints that don't have a native adapter yet.

### xAI Grok: SuperGrok OAuth (no API key) or API key

v0.14 made xAI a first-class Hermes provider instead of just another OpenAI-compatible key. Use **SuperGrok / X Premium+ browser OAuth** (`xai-oauth`) when you already pay for either — no key needed, and the same OAuth token is reused by xAI TTS, image generation, video, and transcription. Use `XAI_API_KEY` (`xai`) for service-account automation and CI. Grok is on the Responses transport, so reasoning is automatic and a `reasoning_effort` param is not required. `grok-4.6` is the pinned top pick in the xAI OAuth picker — the IDE-facing "composer-style" fast coding variants rotate, so check the live list before hardcoding one.

```bash
hermes model     # choose xAI — SuperGrok OAuth (browser login) or API key
# or: hermes auth add xai-oauth
```

```yaml
model:
  provider: xai-oauth        # or xai (API key)
  default: grok-4.6
# optional — route web search through xAI's hosted search: web.backend: xai
```

Keep it out of cheap cron loops; route it explicitly for live events, X threads, and million-token synthesis. If OAuth login succeeds but inference 403s, xAI has restricted your tier — fall back to `XAI_API_KEY` (provider xai).

### Provider Cheat Sheet (August 21, 2026)

The exact "best model" moves weekly, so treat this as a routing posture rather than a leaderboard. Use `hermes model` for live picker data, then pin only what you need reproducible:

| Need | Start here | Why |
|------|------------|-----|
| Default coding / refactors | Claude Sonnet (via API/OpenRouter/Nous) or Codex/Copilot OAuth | Best reliability for patch-and-loop work; subscription OAuth avoids API-key churn |
| Deep reasoning / high stakes | `openai/gpt-5.6-sol` (via OpenRouter/Nous or `openai-codex`) or Anthropic Opus (4.8/5) | Use explicitly; do not make it the default for cron/bulk |
| Long-context repo/doc reads | `google/gemini-3.1-pro-preview` / `google/gemini-3.7-flash`, or DeepSeek V4-flash class | Huge window, cheap enough for map/reduce, video, summarization |
| Cheap daily driver | `z-ai/glm-5.2` (picker default) + `deepseek/deepseek-v4-flash` class | Strong quality/cost; agentic tool-callers |
| Committee for hard calls | A `moa` preset of 2–3 frontier models | Visible multi-model deliberation (see [Part 26](./part26-moa-verification.md)); ~N× call count, so use sparingly |
| Enterprise / VPC / compliance | AWS Bedrock or Azure AI Foundry | IAM/Entra auth, guardrails, private deployments, audit controls |
| Local/privacy/offline | LM Studio, Ollama, or a local NIM/vLLM endpoint | No cloud egress; great for extraction, embeddings, drafts |
| Ultra-fast interactive turns | Cerebras / Groq / Fireworks via OpenAI-compatible endpoints, or Ollama Cloud | Very high tokens/sec for classification, background labels, short form chat |
| Current events / X search | xAI Grok 4.6 (`xai-oauth` or key) + `x_search`, or tool-backed web search | Grok has native X live search; Tool Gateway covers the broader web |
| Free tier for cron / triage | OpenRouter free lane: `stealth/ox-alpha`, `openrouter/elephant-alpha`, `tencent/hy3:free`, `nvidia/nemotron-3-super-120b-a12b:free` | Great where a miss is cheap |

> Pricing and context windows change too quickly to hardcode. Hermes now pulls OpenRouter and Nous Portal picker lists from a remote manifest, while provider APIs supply pricing/context metadata where available. `hermes model` is the source of truth.

## The August 2026 Model Landscape (manifest-verified)

Snapshot verified against the live `model-catalog.json` (updated 2026-08-21). Treat as a routing posture, not a leaderboard:

| Lane | Pick | Notes |
|------|------|-------|
| Silent default (OpenRouter + Nous) | **`z-ai/glm-5.2`** (rotatable without a release) | Cheap, agentic; what `hermes model` lands on if you never pick |
| "Recommended" badge (OpenRouter) | **`moonshotai/kimi-k3`** | Strong parallel tool-calling; watch pricing, it burns wallets fast |
| Hard coding / judgment | **`openai/gpt-5.6-sol`/`-terra`/`-luna` (incl. `-pro`) or Anthropic Opus 4.8/5-era** | Sol for high-stakes; Terra/Luna for the cost-conscious frontier tier |
| Long context | **`google/gemini-3.1-pro-preview`**, `google/gemini-3.7-flash` | 1M-class window; image/video input |
| Live events / X | **`x-ai/grok-4.6`** | X-native retrieval; OAuth or API key |
| Fast open weights | `openai/gpt-5.4-mini`, `qwen/qwen3.8-max`, `xiaomi/mimo-v2.5-pro`, `minimax/minimax-m3`, `tencent/hy3`, `stepfun/step-3.7-flash` | All on both OpenRouter and Nous manifests |
| Free | `stealth/ox-alpha`, `openrouter/elephant-alpha`, `nvidia/nemotron-3-super-120b-a12b:free` | Great for cron/triage/classification |
| Local / open-weight | DeepSeek V4-flash / V4-pro class, Qwen3.8-Max-class open weights, NVIDIA Nemotron-3 | [Part 25](./part25-nvidia-local.md) for the hardware playbook |

Two hard facts to save you an evening:

- **Anthropic subscriptions do NOT work natively in Hermes — with one narrow exception.** The Anthropic OAuth path requires a **Claude Max plan with purchased extra usage credits** (Hermes routes as Claude Code and consumes only the overage). **Claude Pro has no OAuth path at all.** For Claude with API keys or OpenRouter — or orchestrate a Claude Code terminal as a worker lane ([Part 18](./part18-coding-agents.md)) if you only have the subscription. Working subscription auths in Hermes right now: OpenAI Codex/ChatGPT OAuth, GitHub Copilot OAuth, xAI SuperGrok/X Premium+ OAuth, Qwen Portal OAuth, MiniMax OAuth, Nous Portal, and the keyless OpenCode free tier.
- **High-reasoning models overwork.** Sol and friends invent self-assigned busywork on agent harnesses. Cap goals with completion contracts ([Part 26](./part26-moa-verification.md)) and never run the same high-reasoning model as both orchestrator and delegated worker.

### Credential Pools (Multiple Keys per Provider)

Credential pools are the same-provider cousin of the fallback chain: register **several keys (or OAuth tokens) for one provider**, and Hermes rotates within the pool on rate-limit/quota/auth errors *before* falling over to another provider:

```bash
hermes auth add openrouter --api-key sk-or-v1-...
hermes auth add openrouter --api-key sk-or-v1-...    # second key, same provider
hermes auth list                                     # shows pools + active credential
hermes auth                                          # interactive wizard (add/remove/reset/strategy)
```

Rotation strategies (`fill_first` default, `round_robin`, `least_used`, `random`) are per-provider in `config.yaml` under `credential_pool_strategies:` — or set them from the wizard. OAuth-capable providers (Anthropic, Nous, Codex) can mix OAuth and API-key credentials in one pool (`hermes auth add anthropic --type oauth`).

Pool first, fallback second — pools are tried before the fallback chain. Caveat: every rotation is a **prefix-cache miss** — the next turn re-reads the whole session history at full input price ([Part 20](./part20-observability.md#the-gateway-token-tax-cli-for-heavy-work-messaging-for-control)). A single Nous Portal or OpenRouter OAuth usually doesn't need a pool.

---

### Nous Portal — OAuth, Not an API Key

Nous Portal is OAuth-first via `hermes model` (or `hermes setup --portal` on a fresh install — OAuth + provider + Tool Gateway in one command). Credentials land in `~/.hermes/auth.json` (never `.env`). Inspect routing with `hermes portal info`; re-auth when it expires:

```bash
hermes model
# Pick "Nous Portal" → complete the browser OAuth flow
```

Paid subscriptions also unlock the [Tool Gateway](./part13-tool-gateway.md) — web search, image gen, TTS, browser automation via your Portal subscription, no extra keys.

### Google: API Key or Vertex AI (Gemini OAuth Is Gone)

> **Migration note (v0.18):** the Gemini-CLI OAuth providers (`google-gemini-cli`, `google-antigravity`) were **removed**. If your config still points at them, model selection fails after upgrading. Pick one of the two supported paths below.

**Path 1 — API key (simplest).** Set `GOOGLE_API_KEY` (alias `GEMINI_API_KEY`) and use the native `gemini` provider. Free-tier keys work, but a billing-enabled project is recommended for agent use (several model calls per turn can exhaust free quota fast).

**Path 2 — Vertex AI (GCP shops).** First-class `vertex` provider over Vertex's OpenAI-compatible endpoint. Vertex has no static API key — every request needs a short-lived (~1h) OAuth2 token minted from a service-account JSON or Application Default Credentials. Hermes mints and auto-refreshes (including a re-mint on a mid-session 401), so sessions no longer die mid-run on token expiry:

```yaml
model:
  provider: vertex
  default: google/gemini-3-flash-preview   # Vertex requires the google/ prefix
vertex:
  project_id: ${GOOGLE_CLOUD_PROJECT}     # or the project embedded in credentials
  region: "us-central1"                    # "global" required for some Gemini previews
```

```bash
# credential path stays in .env (never in config.yaml):
echo "VERTEX_CREDENTIALS_PATH=/path/to/service-account.json" >> ~/.hermes/.env
# or: gcloud auth application-default login
hermes model   # → "Google Vertex AI" → project → region → model
```

Use Vertex when your org already routes Gemini through Google Cloud (IAM, quotas, audit); use the plain API key everywhere else.

### The fast-coding lane that most people miss

The coding-model fast lanes (Cursor's Composer-style tiers, Codex models, GitHub Copilot's live catalog) are subscription-gated models that **rotate without warning**. In this guide we deliberately don't hardcode the current name: open `hermes model`, pick your OAuth-able provider (xAI Grok, Codex/ChatGPT, Copilot), and read the fast-coding tier from the live picker. What persists across versions: OAuth beats API-key churn, and the fast tier pairs best as a *worker* lane — not the orchestrator.

### AWS Bedrock and Azure AI Foundry — Enterprise Routing Without Proxy Glue

Bedrock uses the native Converse API and the normal boto3 credential chain:

```bash
pip install 'hermes-agent[bedrock]'
hermes model
# Choose "AWS Bedrock" → region → model/profile
```

Use this when you want IAM roles, Bedrock Guardrails, and cross-region inference profiles instead of direct vendor API keys.

Azure AI Foundry handles both endpoint styles — `hermes model` → "Azure AI Foundry" → paste endpoint + key:

- It probes the endpoint, detects OpenAI-style `/chat/completions` vs Anthropic-style `/messages`, discovers deployments where possible, and stores the right `api_mode` in `config.yaml`.
- Organizations on Microsoft Entra ID can use `model.auth_mode: entra_id` on the provider instead of a shared key.

### Custom Model Catalog: Stop Hardcoding This Week's Winner

OpenRouter and Nous Portal model pickers fetch a JSON manifest:

```text
https://hermes-agent.nousresearch.com/docs/api/model-catalog.json
```

The cache lives at `~/.hermes/cache/model_catalog.json` (1h TTL). If the manifest is down or fails validation, Hermes falls back to the disk cache or the bundled in-repo snapshot, so model selection still works offline. You can also point a provider at your own curated manifest (`model_catalog.providers.<id>.url`) and hide providers you never want in the picker (`model_catalog.excluded_providers`).

### Gemini TTS

Gemini is one of the practical voice backends alongside Edge, ElevenLabs, OpenAI, MiniMax, Mistral, and xAI:

```yaml
tts:
  provider: gemini
  gemini:
    model: gemini-2.5-flash-preview-tts   # or gemini-3.1-flash-tts-preview
    voice: Kore
```

`GOOGLE_API_KEY` / `GEMINI_API_KEY` is enough. Output comes back as PCM wrapped in WAV natively (no extra deps), optionally converted to mp3/ogg via `ffmpeg`. Works for Telegram voice bubbles out of the box. Gemini TTS also supports natural-language `persona_prompt_file` and, on 3.1 Flash, `audio_tags` for expressive delivery.

### `hermes proxy` — an OpenAI-compatible endpoint backed by your OAuth

`hermes proxy` runs a local HTTP server (`http://127.0.0.1:8645/v1`) that external OpenAI-compatible apps point at — the proxy attaches your real OAuth credential (currently `nous` and `xai` upstreams) and never exposes a key. Useful for giving Codex CLI, Aider, Open WebUI, OpenViking, or Karakeep your Nous Portal or Grok subscription instead of a separate API key:

```bash
hermes proxy start          # --provider nous (default) | xai --port 8645
hermes proxy status         # all ready + bearer expiry
hermes proxy providers      # list upstreams
```

This is *not* the same thing as the backend/API server (`hermes serve` — headless JSON-RPC/WebSocket backend for the desktop app and remote clients; or the `api_server` gateway platform for OpenAI-compatible serving), which serves the full agent — the proxy forwards pure model inference only. It also is not the egress/iron-proxy direction; those are different commands.

---

## config.yaml Structure

Models are configured in `~/.hermes/config.yaml`:

> **Security note:** Never put real API keys directly in `config.yaml`. Use environment-variable references so keys stay in `~/.hermes/.env` (which should be `chmod 600` and never committed to git). Or set them with `hermes auth`/`hermes model`, which store them out-of-band in `~/.hermes/auth.json`.

```yaml
# Default model. `hermes model` writes dict form; a combined string also works:
model:
  provider: openrouter
  default: z-ai/glm-5.2
  base_url: ''
  api_mode: chat_completions

# Provider configurations
# API keys are loaded from ~/.hermes/.env automatically, or set with: hermes auth
#   ANTHROPIC_API_KEY=sk-ant-...      OPENAI_API_KEY=sk-...
#   KIMI_API_KEY=sk-...               GLM_API_KEY=...
#   ARCEEAI_API_KEY=arc-...           NVIDIA_API_KEY=nv-...
#   STEPFUN_API_KEY=...               DEEPSEEK_API_KEY=...
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}

  openai-api:
    api_key: ${OPENAI_API_KEY}

  bedrock:
    region: us-east-2                  # Auth via AWS_PROFILE, env vars, or instance role

  azure-foundry:
    api_key: ${AZURE_FOUNDRY_API_KEY}
    base_url: ${AZURE_FOUNDRY_ENDPOINT}
    api_mode: chat_completions         # Or anthropic_messages; wizard auto-detects

  lmstudio:
    base_url: http://127.0.0.1:1234/v1
    api_key: ${LM_API_KEY}             # optional if LM Studio auth is enabled

  xai:
    api_key: ${XAI_API_KEY}
  # xai-oauth is set up via `hermes auth add xai-oauth` (no key needed)

  xiaomi:
    api_key: ${XIAOMI_API_KEY}
    reasoning_mode: high              # low / medium / high

  kimi-coding:                         # Kimi / Moonshot (KIMI_API_KEY)
    api_key: ${KIMI_API_KEY}

  zai:                                 # z.ai / GLM
    api_key: ${GLM_API_KEY}           # ZAI_API_KEY accepted as an alias

  minimax:
    api_key: ${MINIMAX_API_KEY}

  gmi:
    api_key: ${GMI_API_KEY}

  tencent-tokenhub:
    api_key: ${TOKENHUB_API_KEY}

  arcee:
    api_key: ${ARCEEAI_API_KEY}

  deepseek:
    api_key: ${DEEPSEEK_API_KEY}

  nvidia:
    api_key: ${NVIDIA_API_KEY}        # Nemotron on build.nvidia.com; local NIM via NVIDIA_BASE_URL

  stepfun:
    api_key: ${STEPFUN_API_KEY}

  fireworks:
    api_key: ${FIREWORKS_API_KEY}
    base_url: https://api.fireworks.ai/inference/v1

  opencode-free:
    api_key: ''                        # keyless tier — no credential needed

  # OpenAI-compatible endpoints you use as named providers:
  cerebras:
    api: https://api.cerebras.ai/v1
    key_env: CEREBRAS_API_KEY
  groq:
    api: https://api.groq.com/openai/v1
    key_env: GROQ_API_KEY
  local:                               # Ollama (or any local server)
    api: http://localhost:11434/v1
    api_key: ollama                    # Ollama doesn't require a real key
```

## Adding a Custom Provider

Any provider that implements the OpenAI chat-completions API works — add a named entry under `providers:` (or use the `hermes model` → "Custom endpoint" wizard):

```yaml
# Add your API key to ~/.hermes/.env:
#   MY_CUSTOM_API_KEY=your-key-here
providers:
  my-custom:
    api: https://api.your-provider.com/v1   # api, base_url, url all accepted
    key_env: MY_CUSTOM_API_KEY
```

Or the old-style `api_key`: `base_url` fields. Then use it:

```bash
hermes --provider my-custom --model their-model-name
```

`hermes model` auto-generates a friendly name (e.g. "Together.ai") for custom endpoints you set up interactively; that name can also key a credential pool (`hermes auth add "Together.ai" --api-key ...`).

## Model Aliases (Quick Switching)

Add aliases to switch models without typing full names — two equivalent forms:

```yaml
model_aliases:              # canonical: full control (provider + optional base_url)
  fast:
    model: z-ai/glm-5.2
    provider: openrouter
  smart:
    model: claude-sonnet-5
    provider: anthropic
  local:
    model: nemotron:latest
    provider: local
```

```bash
# or the short string form (provider/model), settable from the shell:
hermes config set model.aliases.fast openrouter/z-ai/glm-5.2
hermes config set model.aliases.smart anthropic/claude-sonnet-5
```

Use in chat:

```
/model fast        # Switch to GLM 5.2
/model smart       # Switch to Claude Sonnet
/model local       # Switch to local Ollama model
```

`model_aliases:` entries take precedence over `model.aliases:` entries of the same name, and both are shadowed by built-in shorts (`sonnet`, `kimi`, `opus`, ...) only if you don't redefine them.

## Provider Comparison (What We Actually Use)

| Provider | Speed | Cost | Best For |
|----------|-------|------|----------|
| Cerebras (custom endpoint) | Very fast | Cheap | Bulk classification, embeddings-style short calls |
| Groq (custom endpoint) | Very fast | Cheap | Latency-sensitive short-form chat |
| Fireworks | Fast | Cheap | Embeddings (`accounts/fireworks/models/...`), specialized models |
| z.ai / GLM | Fast | Cheap | Agentic daily driver, fallback |
| Anthropic | ~100 tok/s | Premium | Complex reasoning, long context |
| Kimi (Moonshot) | Varies | Cheap–mid | Long-context synthesis |
| Google Gemini | Fast | Cheap | Vision, TTS, auxiliaries, long reads |
| xAI Grok | Varies | Subscription/mid | Current events, X-native search (OAuth or key) |
| OpenRouter | Varies | Varies | Model variety, one key for all of the above |
| Nous Portal | Varies | Subscription | 300+ models + Tool Gateway under one login |
| Ollama (local) | Varies | Free | Privacy, offline, experiments |

**Our setup:** Cerebras/Groq for raw speed, Anthropic or GLM for quality, Ollama for local models and embeddings, Nous Portal (or OpenRouter) as the one-subscription umbrella — and one pool + fallback chain so nothing hard-fails at 3am.

## Routing Cheat Sheet by Task Type

Opinionated defaults — then tune with [Part 20's cost-routing playbook](./part20-observability.md#cost-routing-playbook-the-one-that-actually-saves-money):

| Task | First choice | Fallback (cheaper) | Fallback (fastest) |
|------|--------------|--------------------|--------------------|
| Daily conversation | Anthropic Sonnet / `z-ai/glm-5.2` | `deepseek/deepseek-v4-flash` | Groq/Cerebras custom endpoint |
| Coding delegation | Claude Code / Codex OAuth / Copilot OAuth | OpenCode free keyless | xAI fast coding tier (live picker) |
| High-stakes judgment calls | `moa` council preset ([Part 26](./part26-moa-verification.md)) | `gpt-5.6-sol` | — |
| Long-context reads (>200K) | `google/gemini-3.1-pro-preview` | Gemini 3.7 Flash | DeepSeek V4-flash class |
| Classification / triage | `z-ai/glm-5.2` or Gemini Flash | free OpenRouter lane (`ring-2.6-1t:free`, `hy3:free`) | Groq / Cerebras |
| Reasoning (math, planning) | `gpt-5.6-sol` | Anthropic Opus 4.8/5 | GLM 5.x |
| Current events / live search | Grok 4.6 + `x_search` | Gemini with grounding | Tool Gateway web search |
| Embeddings (LightRAG) | Qwen3-Embedding-8B (Fireworks) | nomic-embed-text (Ollama) | OpenAI `text-embedding-3-small` |
| TTS (Telegram voice) | Gemini / xAI voices or Tool Gateway TTS | Gemini Flash TTS | Edge TTS (free) |
| Vision / video | Gemini 3.1 Pro / 3.7 Flash | `gpt-5.6` multimodal | Claude Sonnet 5 |

---

## Cerebras Gotchas

Cerebras is fast but has quirks, and in Hermes it now mounts as a plain OpenAI-compatible endpoint (`providers.cerebras.base_url: https://api.cerebras.ai/v1`) rather than a native adapter:

1. **No system prompt caching.** Every request re-sends the full system prompt. Keep it short.
2. **Rate limits are per-minute, not per-request.** Batch carefully.
3. **Some models don't support tool calling.** Check before using as the main agent model.
4. **Streaming is fast but chunky.** Large responses come in bursts, not smooth streams.

Config:

```yaml
# Set CEREBRAS_API_KEY in ~/.hermes/.env
providers:
  cerebras:
    api: https://api.cerebras.ai/v1
    key_env: CEREBRAS_API_KEY
```

## Local Models (Ollama)

Run models locally for free inference:

```yaml
providers:
  local:
    api: http://localhost:11434/v1
    api_key: ollama
```

**Best local/open models for Hermes (2026 era):**
- **DeepSeek V4-flash / V4-pro** — strong open-weight reasoning/coding, and now priced for hosted use too (OpenRouter)
- **Qwen3.8-Max class** (open weights) — practical single-workstation balance
- **NVIDIA Nemotron-3-Super-120B-class MoE** — big-MoE on DGX Spark / 48GB-class boxes ([Part 25](./part25-nvidia-local.md))
- **Qwen3.6-35B-A3B / Bonsai-class small MoEs** — resident mid-size models respond instantly; often beat paged giants ([Part 9](./part9-custom-models.md#cerebras-gotchas) → [Part 25](./part25-nvidia-local.md))

Always set a real context length (`OLLAMA_CONTEXT_LENGTH=64000` or a `num_ctx` Modelfile) — Ollama defaults can be as low as 4K and Hermes needs ~64K for the agent loop with tools.

**For embeddings (free):**

```yaml
embedding:
  provider: local
  model: nomic-embed-text
  base_url: http://localhost:11434
```

## Switching at Runtime

```
/model openrouter/z-ai/glm-5.2   # Full model path
/model fast                       # Alias
/model my-council --provider moa  # MoA preset as a model (persistent switch)
/model                            # Show current model
/model z-ai/glm-5.2 --global     # Also persist to config.yaml
/model claude-opus-4.8 --once    # One turn only, then auto-restore
```

Every mid-session switch resets the provider prompt-cache prefix (the cache is keyed to model+account) — the next turn re-reads at full input price. Switch early in a conversation, or hand the odd model to a subagent with its own context ([Part 8](./part8-subagent-patterns.md)).

## Auxiliary Models (Task-Specific)

Hermes supports dedicated models for auxiliary task slots — the dashboard's Models page ([Part 12](./part12-web-dashboard.md#models)) exposes all of them, and `hermes model` → "Configure auxiliary models" is the interactive way (each side-task can have its own provider, model, base_url, api_key, and timeout):

| Task slot | What it does | Default |
|-----------|-------------|---------|
| `vision` | Image/video analysis, screenshot understanding | auto |
| `web_extract` | Summarizing scraped web pages | auto |
| `compression` | Context-compression summaries | auto |
| `title_generation` | Session titles | auto |
| `approval` | Deciding whether to auto-approve tool calls | auto |
| `skills_hub` | Skill discovery & matching | auto |
| `mcp` | MCP tool dispatch | auto |
| `triage_specifier` | Kanban one-liner → concrete spec expansion | auto |
| `kanban_decomposer` | Splits a task into a child-task graph | auto |
| `profile_describer` | Profile description generation | auto |
| `curator` | Skill-library hygiene runs ([Part 5](./part5-creating-skills.md)) | auto |
| `tts_audio_tags` | Gemini-3.1-style hidden audio-tag insertion | auto |
| (`delegation`) | Subagent model override (a full `delegation:` block, not an aux slot) | inherits main |

`auto` means "use the main model for that job, honoring fallback policy if it can't serve." Override a slot when the side-job is obviously cheaper elsewhere.

**Configure in `~/.hermes/config.yaml`:**

```yaml
auxiliary:
  # Summaries don't need deep thinking:
  compression:
    provider: openrouter
    model: z-ai/glm-5.2
    reasoning_effort: low
    timeout: 120
  # Multimodal model for image/video analysis:
  vision:
    provider: openrouter
    model: google/gemini-3.7-flash
    timeout: 60
  # Everything else stays auto
  skills_hub: auto
  mcp: auto
```

**Why bother:**
- **Compression** runs on every long session; a cheap model saves real money with no quality loss.
- **Vision/video** must be multimodal — if your main model can't, set this.
- **Approval** answers on every pre-tool check; a fast small model here cuts latency.
- **Session search is free** — since v0.15 it's local FTS over the session DB (see Part 7), so there's no model cost to chase there.

## Fallback Chain

Configure automatic cross-provider failover when the primary fails. The current shape is a top-level `fallback_providers:` list of provider+model pairs — and the interactive manager writes it for you:

```bash
hermes fallback            # show the chain (also the default)
hermes fallback add        # provider+model picker, same picker as `hermes model`
hermes fallback list
hermes fallback remove
hermes fallback clear
```

Direct YAML:

```yaml
fallback_providers:
  - provider: openrouter
    model: z-ai/glm-5.2
  - provider: openai-codex       # Codex OAuth as a fallback (no key to babysit)
    model: gpt-5.6-sol
  - provider: custom             # local model as the last-ditch floor
    model: nemotron:latest
    base_url: http://localhost:11434/v1
```

Hermes tries the chain in order (per turn — the primary is restored at the start of each new message; failed primaries that report a reset time are skipped until it passes). Two rules that save 3am debugging:

- **Every fallback entry needs both a `provider` and a `model`.** A bare model in a legacy `fallback_models`-style entry fails at the moment you need it most.
- **Put the local model last.** The bottom floor is degraded-but-alive, and it's the one thing nobody can rate-limit.

And remember cache economics: a fallback event is a cache reset too — each bounce to a new provider/model re-reads the full history at full price ([Part 20](./part20-observability.md#cost-routing-playbook-the-one-that-actually-saves-money)).

---

*Don't lock yourself into one provider. The best model is the one that's fast enough and cheap enough for the task at hand — and the picker manifest will keep moving under you, so build a posture, not a pin.*