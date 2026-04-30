# Part 9: Custom Model Providers (Use Any Model You Want)

*Hermes supports any OpenAI-compatible API, plus first-class native adapters for Nous Portal, Anthropic, OpenAI/Codex, OpenRouter, AWS Bedrock, Azure AI Foundry, Google Gemini, Gemini OAuth, LM Studio, xAI, Xiaomi MiMo, Kimi/Moonshot, z.ai/GLM, MiniMax, Arcee, GMI Cloud, Tencent TokenHub, Hugging Face, Cerebras, Groq, Fireworks, and Ollama. This is the April 30, 2026 cheat sheet.*

> **What's new since the v0.10 guide refresh** — Gemini OAuth is now built into `hermes model` (no separate CLI install), AWS Bedrock uses the native Converse API, Azure AI Foundry auto-detects OpenAI vs Anthropic transports, LM Studio has `hermes doctor` checks and live `/models`, MiniMax OAuth uses PKCE, and OpenRouter/Nous model pickers update from a remote manifest instead of a hardcoded release snapshot.

---

## Native Adapters vs Generic OpenAI-Compatible

As of v0.12.0 (April 2026), Hermes ships **native adapters** for a large provider set. Native adapters know about provider-specific features that a generic OpenAI-compatible wrapper can't:

| Provider | Native adapter? | Notable feature |
|----------|-----------------|-----------------|
| **Nous Portal** | Yes | Auth via `hermes model` (no bare API key). Unlocks the [Tool Gateway](./part13-tool-gateway.md). |
| **Anthropic** | Yes | Native prompt caching, extended thinking, `/fast` priority tier |
| **OpenAI** | Yes | Native responses API, reasoning effort levels, `/fast` priority tier |
| **OpenAI Codex OAuth** | Yes | ChatGPT/Codex login through `hermes model`, no API key |
| **AWS Bedrock** | Yes | Converse API, IAM credentials, cross-region inference profiles, Bedrock Guardrails |
| **Azure AI Foundry** | Yes | Auto-detects OpenAI-style vs Anthropic-style deployments and context length |
| **LM Studio** | Yes | Local `/models` discovery, optional auth, reasoning transport, `hermes doctor` checks |
| **xAI (Grok)** | Yes | Native live X search and xAI image/STT/TTS integrations |
| **Xiaomi MiMo** | Yes | Native reasoning modes (`low`/`medium`/`high`) exposed as config |
| **Kimi / Moonshot** | Yes | 200K+ context, great for LightRAG entity extraction (see [Part 3](./README.md#part-3-lightrag--graph-rag-that-actually-works)) |
| **z.ai / GLM** | Yes | Strong open-weight tool-use models; good cheap fallback for planning/exploration |
| **Google Gemini (direct)** | Yes | 1M context; native prompt caching on Gemini 2.5 Pro |
| **Google Gemini (OAuth)** | Yes | Browser PKCE login via `hermes model`; free tier supported; no external `gemini` install |
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
| **Anything else** | Generic | Any OpenAI-compatible `base_url` |

Pick the native adapter when one exists — you get the provider-specific features for free. Fall back to the generic OpenAI-compatible path only for endpoints that don't have a native adapter yet.

### Provider Cheat Sheet (April 30, 2026)

The exact "best model" moves weekly, so treat this as a routing posture rather than a leaderboard. Use `hermes model` for live picker data, then pin only what you need reproducible.

| Need | Start here | Why |
|------|------------|-----|
| Default coding / refactors | Anthropic Sonnet or Codex OAuth | Best reliability for patch-heavy work; Codex OAuth avoids API-key churn |
| Deep reasoning / high stakes | OpenAI reasoning or Anthropic Opus-class | Use explicitly; do not make it the default for cron/bulk tasks |
| Long-context repo or document reads | Gemini Pro/Flash or OpenRouter equivalent | Huge window, cheap enough for map/reduce and summarization |
| Cheap daily driver | Gemini OAuth + Kimi/Moonshot + z.ai/GLM | Good quality/cost mix, especially with auxiliary routing |
| Enterprise / VPC / compliance | AWS Bedrock or Azure AI Foundry | IAM/Azure auth, guardrails, private deployments, audit controls |
| Local/privacy/offline | LM Studio or Ollama | No cloud egress; great for extraction, embeddings, and drafts |
| Ultra-fast interactive turns | Cerebras or Groq | Very high tokens/sec; useful for classification and short-form chat |
| Current-events search | xAI Grok or tool-backed web search | Grok has native live-X search; Tool Gateway can cover broader web |

> Pricing and context windows change too quickly to hardcode. Hermes now pulls OpenRouter and Nous Portal picker lists from a remote manifest, while provider APIs supply pricing/context metadata where available.

---

### Nous Portal — OAuth, Not an API Key

Nous Portal uses an OAuth flow via `hermes model` instead of a bare API key. After auth, credentials live in `~/.hermes/auth.json` (never in `.env`). Re-auth when it expires:

```bash
hermes model
# Pick "Nous Portal" → complete the browser OAuth flow
```

If you're on a paid subscription, the setup also offers to enable the [Tool Gateway](./part13-tool-gateway.md) — web search, image gen, TTS, and browser automation through your subscription, no extra keys needed.

### Gemini OAuth — Free-Tier Friendly

If you have a Google account, skip the API key entirely and sign in from Hermes:

```bash
hermes model
# Pick "Google Gemini (OAuth)" → complete the browser PKCE flow
```

Tokens are stored under `~/.hermes/auth/google_oauth.json` with 0600 permissions and automatic refresh. On headless SSH boxes, Hermes falls back to paste-mode auth.

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

> **Security note:** Never put real API keys directly in `config.yaml`. Use environment variable references so keys stay in `~/.hermes/.env` (which should be `chmod 600` and never committed to git).

```yaml
# Default model
model: claude-sonnet
provider: anthropic

# Provider configurations
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
    model: cerebras/llama-3.3-70b
    provider: cerebras
  smart:
    model: claude-opus-4-20250514
    provider: anthropic
  local:
    model: nemotron:latest
    provider: local
```

Use in chat:

```
/model fast      # Switch to Cerebras Llama 70B
/model smart     # Switch to Claude Opus
/model local     # Switch to local Ollama model
```

## Provider Comparison (What We Actually Use)

| Provider | Speed | Cost | Best For |
|----------|-------|------|----------|
| Cerebras | 3000+ tok/s | Cheap | Fast inference, bulk tasks, coding |
| Anthropic | ~100 tok/s | Premium | Complex reasoning, long context |
| OpenRouter | Varies | Varies | Model variety, fallback provider |
| Fireworks | Fast | Cheap | Embeddings, specialized models |
| Ollama (local) | Varies | Free | Privacy, offline, experimenting |

**Our setup:** Cerebras for speed, Anthropic for quality, Ollama for local models and embeddings.

## Routing Cheat Sheet by Task Type

Use these as opinionated defaults, then tune with [Part 20's cost-routing playbook](./part20-observability.md#cost-routing-playbook-the-one-that-actually-saves-money):

| Task | First choice | Fallback (cheaper) | Fallback (fastest) |
|------|--------------|--------------------|--------------------|
| Daily conversation | Anthropic Sonnet | Gemini OAuth or z.ai/GLM | Cerebras Llama/Qwen |
| Coding delegation | Claude Code / Codex OAuth | OpenCode + Kimi/Moonshot | OpenCode + Cerebras |
| Long-context reads (>200K) | Gemini 2.5 Pro | Gemini 2.5 Flash | — |
| Classification / triage | Gemini 2.5 Flash | Cerebras Qwen3 32B | Arcee AFM-4.5 |
| Reasoning (math, planning) | OpenAI reasoning model | Anthropic Opus-class | z.ai/GLM |
| Current events / live search | xAI Grok | Gemini with grounding | Tool Gateway web search |
| Embeddings (LightRAG) | Qwen3-Embedding-8B (Fireworks) | nomic-embed-text (Ollama) | OpenAI `text-embedding-3-small` |
| TTS (Telegram voice) | OpenAI TTS via Tool Gateway | Gemini 2.5 Flash TTS | Edge TTS (free) |
| Vision | Gemini 2.5 Flash | GPT-4o | Claude Sonnet 4.5 |

---

## Cerebras Gotchas

Cerebras is fast but has quirks:

1. **No system prompt caching.** Every request re-sends the full system prompt. Keep it short.
2. **Rate limits are per-minute, not per-request.** Batch carefully.
3. **Some models don't support tool calling.** Check before using as the main agent model.
4. **Streaming is fast but chunky.** Large responses come in big bursts, not smooth streams.

Config:

```yaml
providers:
  cerebras:
    api_key: ${CEREBRAS_API_KEY}
    base_url: https://api.cerebras.ai/v1
    # Models: llama-3.3-70b, llama-4-scout-17b-16e-instruct, qwen-3-32b
```

## Local Models (Ollama)

Run models locally for free inference:

```yaml
providers:
  local:
    base_url: http://localhost:11434/v1
    api_key: ollama
```

**Best local models for Hermes:**
- **Nemotron 30B** — good all-around, fits in 24GB VRAM
- **Qwen 2.5 32B** — strong reasoning, needs 24GB+
- **Llama 3.3 70B Q4** — best quality, needs 40GB+ VRAM

**For embeddings (free):**

```yaml
embedding:
  provider: local
  model: nomic-embed-text
  base_url: http://localhost:11434
```

## Switching at Runtime

```
/model cerebras/llama-3.3-70b    # Full model path
/model fast                       # Alias
/model                            # Show current model
```

## Auxiliary Models (Task-Specific Models)

Hermes supports dedicated models for eight task types. Each can have its own provider, model, base_url, api_key, and timeout.

| Task Type | What It Does | Default |
|-----------|-------------|---------|
| `vision` | Image analysis, screenshot understanding | auto |
| `web_extract` | Summarizing scraped web pages | auto |
| `compression` | Context compression (summarizing old messages) | auto |
| `session_search` | Searching past conversation transcripts | auto |
| `approval` | Deciding whether to auto-approve tool calls | auto |
| `skills_hub` | Skill discovery and matching | auto |
| `mcp` | MCP tool routing | auto |
| `flush_memories` | Memory consolidation and cleanup | auto |

When set to `"auto"` (default), Hermes walks a provider resolution chain: OpenRouter → Nous Portal → Custom endpoint → etc.

**Configure in `~/.hermes/config.yaml`:**

```yaml
auxiliary_models:
  # Use a fast cheap model for compression — it's just summarizing
  compression:
    provider: cerebras
    model: llama-3.3-70b
    timeout: 30

  # Use a vision-capable model for image analysis
  vision:
    provider: openrouter
    model: google/gemini-2.5-flash
    timeout: 60

  # Use local model for session search (free, frequent calls)
  session_search:
    provider: local
    model: nemotron:latest
    base_url: http://localhost:11434/v1
    api_key: ollama

  # Everything else stays on auto
  web_extract: auto
  approval: auto
  skills_hub: auto
  mcp: auto
  flush_memories: auto
```

**Why bother:**
- **Compression** runs on every long session. Using a cheap/fast model saves money without affecting quality (summarization doesn't need Opus).
- **Vision** needs a multimodal model. If your main model doesn't do images, set this to one that does.
- **Session search** is called frequently. A local model makes it free.
- **Approval** controls auto-execution. A fast model here means less latency on every tool call.

## Fallback Chain

Configure automatic fallback if the primary model fails:

```yaml
model_fallback:
  - provider: cerebras
    model: llama-3.3-70b
  - provider: openrouter
    model: anthropic/claude-sonnet-4
  - provider: local
    model: nemotron:latest
```

Hermes tries each in order. If Cerebras is down, it falls back to OpenRouter, then local.

---

*Don't lock yourself into one provider. The best model is the one that's fast enough and cheap enough for the task at hand.*
