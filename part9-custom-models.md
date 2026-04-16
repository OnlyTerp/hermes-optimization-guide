# Part 9: Custom Model Providers (Use Any Model You Want)

*Hermes supports any OpenAI-compatible API. Here's how to wire up Cerebras, Fireworks, or your own local models.*

---

## config.yaml Structure

Models are configured in `~/.hermes/config.yaml`:

> **Security note:** Never put real API keys directly in `config.yaml`. Use environment variable references so keys stay in `~/.hermes/.env` (which should be `chmod 600` and never committed to git). You can also use `hermes auth` to set them securely.
```yaml
# Default model
model: claude-sonnet-4-20250514
provider: anthropic

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
