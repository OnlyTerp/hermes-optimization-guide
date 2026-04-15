# Part 9: Custom Model Providers (Use Any Model You Want)

*Hermes supports any OpenAI-compatible API. Here's how to wire up Cerebras, Fireworks, or your own local models.*

---

## config.yaml Structure

Models are configured in `~/.hermes/config.yaml`:

```yaml
# Default model
model: claude-sonnet-4-20250514
provider: anthropic

# Provider configurations
providers:
  anthropic:
    api_key: sk-ant-...
    
  openai:
    api_key: sk-...
    
  cerebras:
    api_key: csk-...
    base_url: https://api.cerebras.ai/v1
    
  fireworks:
    api_key: fw_...
    base_url: https://api.fireworks.ai/inference/v1
    
  local:
    base_url: http://localhost:11434/v1
    api_key: ollama
```

## Adding a Custom Provider

Any provider that implements the OpenAI chat completions API works:

```yaml
providers:
  my-custom:
    api_key: your-key-here
    base_url: https://api.your-provider.com/v1
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
providers:
  cerebras:
    api_key: csk-your-key
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
