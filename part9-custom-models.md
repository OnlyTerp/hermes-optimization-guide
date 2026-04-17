# Part 9: Custom Model Providers (Use Any Model You Want)

*Hermes supports any OpenAI-compatible API, plus first-class native adapters for Nous Portal, xAI, Xiaomi MiMo, Kimi/Moonshot, z.ai/GLM, MiniMax, Arcee, Hugging Face, Cerebras, Groq, Fireworks, and Ollama. OAuth providers landing post-v0.10 add Gemini CLI (free tier: 1500 req/day), Qwen, and Claude Code Pro/Max. This is the up-to-date (April 17, 2026) cheat sheet.*

> **What's new since v0.10.0** — [Gemini CLI OAuth inference provider](https://github.com/NousResearch/hermes-agent/pull/11270) (#11270), [Gemini TTS provider](https://github.com/NousResearch/hermes-agent/pull/10922), [multi-model FAL image gen](https://github.com/NousResearch/hermes-agent/pull/11265), [GLM 5.1 in OpenCode Go catalogs](https://github.com/NousResearch/hermes-agent/pull/11269), [Azure OpenAI GPT-5.x on chat/completions](https://github.com/NousResearch/hermes-agent/pull/10086), plus [TCP keepalives](https://github.com/NousResearch/hermes-agent/pull/11277) that detect dead provider connections before you notice the hang. All shipping on `main`, targeted for v0.11.

---

## Native Adapters vs Generic OpenAI-Compatible

As of v0.10.0 (April 2026), Hermes ships **native adapters** for a growing list of providers. Native adapters know about provider-specific features that a generic OpenAI-compatible wrapper can't:

| Provider | Native adapter? | Notable feature |
|----------|-----------------|-----------------|
| **Nous Portal** | Yes | Auth via `hermes model` (no bare API key). Unlocks the [Tool Gateway](./part13-tool-gateway.md). |
| **Anthropic** | Yes | Native prompt caching, extended thinking, `/fast` priority tier |
| **OpenAI** | Yes | Native responses API, reasoning effort levels, `/fast` priority tier |
| **xAI (Grok)** | **Yes, new in v0.10** | Native **live X/Twitter search** as a built-in tool |
| **Xiaomi MiMo** | **Yes, new in v0.10** | Native reasoning modes (`low`/`medium`/`high`) exposed as config |
| **Kimi / Moonshot** | Yes | 200K+ context, great for LightRAG entity extraction (see [Part 3](#part-3-lightrag--graph-rag-that-actually-works)) |
| **z.ai / GLM** | Yes | **GLM 5.1** (added to OpenCode Go catalogs [#11269](https://github.com/NousResearch/hermes-agent/pull/11269)) — currently strongest open-weights model for tool use |
| **Google Gemini (direct)** | Yes | 1M context; native prompt caching on Gemini 2.5 Pro |
| **Google Gemini CLI (OAuth)** | **Yes, new post-v0.10** | OAuth via `gemini auth` — **1500 requests/day free tier**. [#11270](https://github.com/NousResearch/hermes-agent/pull/11270) |
| **MiniMax** | Yes | M2.7 — balanced speed/quality; native streaming |
| **Arcee** | Yes | AFM-4.5 function-calling specialist, cheap |
| **Cerebras** | Yes | 2000+ tok/s inference |
| **Groq** | Yes | Fast hosted Llama / Qwen |
| **Qwen (OAuth)** | Yes | OAuth via portal-request flow, free-tier available |
| **Fireworks** | Yes | Qwen3-Embedding-8B (recommended for LightRAG) |
| **Azure OpenAI** | Yes | GPT-5.x now via `/chat/completions` (was `/responses` only) [#10086](https://github.com/NousResearch/hermes-agent/pull/10086) |
| **Hugging Face** | Yes | Any TGI / TEI endpoint (self-hosted or Inference Endpoints) |
| **OpenRouter** | Yes | Pass-through to 200+ models; respects native adapter quirks when downstream is one |
| **Ollama** (local) | Generic | OpenAI-compatible, zero auth |
| **Anything else** | Generic | Any OpenAI-compatible `base_url` |

Pick the native adapter when one exists — you get the provider-specific features for free. Fall back to the generic OpenAI-compatible path only for endpoints that don't have a native adapter yet.

### Flagship Model Cheat Sheet (April 17, 2026)

For the "which model should I pick right now?" question, this is the current state of the world:

| Model | Provider | Input / Output ($/MTok) | Context | Best for |
|-------|----------|------------------------|---------|----------|
| **Claude Sonnet 4.5** | Anthropic | $3 / $15 | 200K | Default for coding, refactor, multi-step reasoning |
| **Claude Opus 4** | Anthropic | $15 / $75 | 200K | The hardest reasoning only; $15/MTok stings fast |
| **Claude Mythos** (Cyber) | Anthropic | Invite-only | 200K | Security research — vulnerability discovery, malware triage |
| **GPT-5.4** | OpenAI | $5 / $20 | 256K | Reasoning heavy-lift, agentic long chains |
| **GPT-5.4-Cyber** | OpenAI | Trusted Access only | 256K | Defensive cybersec workflows, reverse engineering |
| **GPT-5.4 Mini** | OpenAI | $0.60 / $4.80 | 256K | Cheap reasoning fallback |
| **Gemini 2.5 Pro** | Google / OpenRouter | $1.25 / $10 | 1M | Long-context, whole-repo reads, research synthesis |
| **Gemini 3 Flash Preview** | Google / OpenRouter | $0.50 / $3 | 1M | Fast agentic reasoning with 1M window |
| **Gemini 2.5 Flash** | Google / OpenRouter | $0.30 / $2.50 | 1M | Classification, triage, bulk extraction |
| **Kimi K2.5** | Moonshot | ~$0.15 / $2.50 | 200K | Best price/quality for coding in 2026 |
| **GLM 5.1** | z.ai | ~$0.20 / $2 | 128K | Strongest open-weights tool use |
| **xAI Grok 4** | xAI | $3 / $15 | 256K | Native live-X search; current-events questions |
| **Xiaomi MiMo** | Xiaomi | $0.50 / $3 | 200K | Three-mode reasoning toggle (low/med/high) |
| **MiniMax M2.7** | MiniMax | $10/mo flat | 256K | Flat-rate users doing bulk work |
| **Cerebras Llama 3.3 70B** | Cerebras | $0.60 / $0.60 | 128K | 3000+ tok/s — interactive chat, fast classification |
| **Local Nemotron 30B** | Ollama | Free | 128K | Privacy, offline, embedding, session search |

> Prices are current per-provider retail as of April 17, 2026. Batch and prompt-caching discounts are not included — stack them via [Part 20](./part20-observability.md#rule-2-prompt-caching-is-free-money).

---

### Nous Portal — OAuth, Not an API Key

Nous Portal uses an OAuth flow via `hermes model` instead of a bare API key. After auth, credentials live in `~/.hermes/auth.json` (never in `.env`). Re-auth when it expires:

```bash
hermes model
# Pick "Nous Portal" → complete the browser OAuth flow
```

If you're on a paid subscription, the setup also offers to enable the [Tool Gateway](./part13-tool-gateway.md) — web search, image gen, TTS, and browser automation through your subscription, no extra keys needed.

### Gemini CLI OAuth — Free 1500 req/day

If you have a Google account, skip the API key entirely and sign in with OAuth:

```bash
npm install -g @google/gemini-cli
gemini auth
hermes model
# Pick "Gemini CLI (OAuth)" — Hermes detects the logged-in session
```

Hermes drives Gemini via the local CLI. You get 1500 requests/day on the free tier — plenty for exploration, classification, and Gemini's killer long-context reads. Merged in [#11270](https://github.com/NousResearch/hermes-agent/pull/11270) (April 16, 2026).

### Gemini TTS — 7th Voice Provider

As of [#10922](https://github.com/NousResearch/hermes-agent/issues/10922) (merged April 16), Gemini joins Edge, ElevenLabs, OpenAI, MiniMax, Mistral, and NeuTTS as a TTS backend:

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
model: claude-sonnet-4-20250514
provider: anthropic

# Provider configurations
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}

  openai:
    api_key: ${OPENAI_API_KEY}

  xai:                                # Native adapter (v0.10+)
    api_key: ${XAI_API_KEY}
    live_search: true                 # Grok's live X/Twitter search

  xiaomi:                             # Native adapter (v0.10+)
    api_key: ${XIAOMI_API_KEY}
    reasoning_mode: high              # low / medium / high

  moonshot:                           # Kimi
    api_key: ${MOONSHOT_API_KEY}

  zai:                                # z.ai / GLM
    api_key: ${ZAI_API_KEY}

  minimax:
    api_key: ${MINIMAX_API_KEY}

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
| Daily conversation | Claude Sonnet 4.5 | GLM 5.1 | Cerebras Llama 70B |
| Coding delegation | Claude Code via Sonnet 4.5 | OpenCode + Kimi K2.5 | OpenCode + Cerebras |
| Long-context reads (>200K) | Gemini 2.5 Pro | Gemini 2.5 Flash | — |
| Classification / triage | Gemini 2.5 Flash | Cerebras Qwen3 32B | Arcee AFM-4.5 |
| Reasoning (math, planning) | GPT-5.4 | Claude Opus 4 | GLM 5.1 |
| Current events / live search | xAI Grok 4 | Gemini with grounding | — |
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
