# Part 13: The Nous Tool Gateway (One Subscription, Four Tools, Zero Extra Keys)

*New in Hermes v0.10.0 (2026.4.16). If you have a paid Nous Portal subscription, you already have web search, image generation, text-to-speech, and browser automation — you just haven't turned them on yet.*

---

## What It Is

Historically, if you wanted Hermes to search the web, generate images, speak, or drive a browser, you needed **four separate accounts**:

- Firecrawl / Exa / Tavily / Parallel for web search
- FAL for image generation
- OpenAI / ElevenLabs for TTS
- Browser Use / Browserbase for browser automation

That's four signups, four API keys, four billing pages, and four different free-tier limits.

The **Nous Tool Gateway** collapses all of that into one line in your config. If you're a paid [Nous Portal](https://portal.nousresearch.com) subscriber, tool usage bills against your subscription — no extra keys required.

| Tool | Upstream | Direct key you'd otherwise need |
|------|----------|---------------------------------|
| Web search & extract | Firecrawl | `FIRECRAWL_API_KEY`, `EXA_API_KEY`, `PARALLEL_API_KEY`, `TAVILY_API_KEY` |
| Image generation | FAL (FLUX 2 Pro + upscaling) | `FAL_KEY` |
| Text-to-speech | OpenAI TTS | `VOICE_TOOLS_OPENAI_KEY`, `ELEVENLABS_API_KEY` |
| Browser automation | Browser Use | `BROWSER_USE_API_KEY`, `BROWSERBASE_API_KEY` |

Each tool is opt-in. You can route **any combination** through the gateway and keep direct keys for the rest — for example, gateway for web + images, your own ElevenLabs key for TTS.

---

## Who Gets It

Paid [Nous Portal](https://portal.nousresearch.com/manage-subscription) subscribers. Free-tier accounts don't have gateway access.

Check your status:

```bash
hermes status
```

Look for the **Nous Tool Gateway** section. It shows which tools are active via the gateway, which are using direct keys, and which aren't configured yet.

---

## Enabling the Gateway

### Option A: During Model Setup (Easiest)

When you run `hermes model` and pick **Nous Portal** as your provider, Hermes auto-prompts you to enable the Tool Gateway:

```text
Your Nous subscription includes the Tool Gateway.
The Tool Gateway gives you access to web search, image generation,
text-to-speech, and browser automation through your Nous subscription.
No need to sign up for separate API keys — just pick the tools you want.

  ○ Web search & extract (Firecrawl)   — not configured
  ○ Image generation (FAL)             — not configured
  ○ Text-to-speech (OpenAI TTS)        — not configured
  ○ Browser automation (Browser Use)   — not configured
  ● Enable Tool Gateway
  ○ Skip
```

Select **Enable Tool Gateway**. Done.

If you already have direct keys for some tools, the prompt adapts — you can enable the gateway for everything (existing keys stay in `.env` but aren't used at runtime), enable it only for tools that aren't configured yet, or skip entirely.

### Option B: Per-Tool via `hermes tools`

```bash
hermes tools
```

Pick a category (Web, Browser, Image Generation, or TTS), then choose **Nous Subscription** as the provider. That flips `use_gateway: true` for that tool in `config.yaml`.

### Option C: Manual Config

Edit `~/.hermes/config.yaml`:

```yaml
web:
  backend: firecrawl
  use_gateway: true

image_gen:
  use_gateway: true

tts:
  provider: openai
  use_gateway: true

browser:
  cloud_provider: browser-use
  use_gateway: true
```

---

## How Precedence Works

Per tool, the runtime checks `use_gateway` first:

- `use_gateway: true` → **always** route through the gateway, even if direct API keys exist in `.env`
- `use_gateway: false` (or unset) → use direct keys if available, fall back to the gateway only when no direct keys exist

This means you can have an `FAL_KEY` and a Nous subscription in `.env` at the same time and deterministically pick which one to use. No deleting keys, no commenting lines.

### The Old Env Var Is Gone

`HERMES_ENABLE_NOUS_MANAGED_TOOLS` was a hidden env flag in v0.9. It's gone in v0.10 — replaced by clean subscription-based detection plus the per-tool `use_gateway` config. If you had that set, `hermes upgrade` migrates it for you.

---

## Verifying It's Working

```bash
hermes status
```

Look for:

```text
◆ Nous Tool Gateway
  Nous Portal   ✓ managed tools available
  Web tools     ✓ active via Nous subscription
  Image gen     ✓ active via Nous subscription
  TTS           ✓ active via Nous subscription
  Browser       ○ active via Browser Use key
  Modal         ○ available via subscription (optional)
```

Rows marked "active via Nous subscription" are routed through the gateway. Rows with their own keys show which provider is active.

You can also see gateway usage in the Dashboard's **Analytics** tab (Part 12) — gateway calls count toward your Nous subscription and are aggregated alongside LLM token usage.

---

## Switching Back to Direct Keys

Interactive:

```bash
hermes tools
# Pick the tool → choose a direct provider
```

Manual:

```yaml
web:
  backend: firecrawl
  use_gateway: false   # now uses FIRECRAWL_API_KEY from .env
```

When you pick a non-gateway provider in `hermes tools`, `use_gateway` is automatically set to `false` to prevent contradictory config.

---

## Self-Hosted / Enterprise Gateway

If you're running your own gateway endpoint (enterprise deployments, staging environments), override the defaults in `~/.hermes/.env`:

```bash
TOOL_GATEWAY_DOMAIN=nousresearch.com     # base domain for routing
TOOL_GATEWAY_SCHEME=https                # http or https (default: https)
TOOL_GATEWAY_USER_TOKEN=your-token       # auth token (normally auto-populated)
FIRECRAWL_GATEWAY_URL=https://...        # override a specific endpoint
```

These env vars are visible regardless of subscription status — they're here so custom infrastructure works without code changes.

---

## FAQ

### Do I have to delete my existing API keys?
No. When `use_gateway: true` is set, the runtime skips direct keys and routes through the gateway. Your keys stay in `.env`. Flip back to them any time.

### Can I mix gateway and direct keys?
Yes — it's per-tool. Gateway for web + images, ElevenLabs for TTS, Browserbase for browsing is a perfectly normal setup.

### What happens if my subscription lapses?
Tools routed through the gateway stop working. Either renew at [portal.nousresearch.com](https://portal.nousresearch.com/manage-subscription) or switch those tools to direct keys via `hermes tools`.

### Does it work on Telegram / Discord / Slack / etc.?
Yes. The gateway operates at the tool runtime level, not the entry-point level. It works the same whether you're on the CLI, a messaging platform, a cron job, or the dashboard's REST API.

### Is Modal (serverless terminal) included?
No — Modal is an optional subscription add-on. Configure it separately via `hermes setup terminal` or in `config.yaml`. The Tool Gateway prompt doesn't enable it automatically.

### Will the gateway auto-fall-back if the upstream is down?
The gateway itself is a thin proxy — failures return the upstream's error. If you want resilience, keep a direct key as a fallback (`use_gateway: false` + `FIRECRAWL_API_KEY` set) and flip it on when the gateway has an incident.

---

## Cost Playbook

Rough guidance for picking between gateway vs direct keys:

- **Heavy web search + browsing + images in the same month:** gateway almost always wins — one subscription covers all four.
- **Only heavy TTS (audio generation):** ElevenLabs direct is often cheaper than the gateway's OpenAI TTS pricing. Keep TTS off the gateway.
- **Low volume, experimenting:** gateway is perfect — no signups, no free-tier juggling, no surprise overages.
- **Enterprise / regulated environment:** self-hosted gateway with the `TOOL_GATEWAY_*` env vars pointing at your own proxy.

---

## What's Next

- **Local UI for everything:** [Part 12 — The Local Web Dashboard](./part12-web-dashboard.md)
- **Faster model responses:** [Part 14 — Fast Mode & Background Watchers](./part14-fast-mode-watchers.md)
- **Expand to iMessage / WeChat / Android:** [Part 15 — New Platforms](./part15-new-platforms.md)
