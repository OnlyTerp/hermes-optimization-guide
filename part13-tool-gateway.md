# Part 13: Tool Gateway, Local Proxy, and Live Search

*If you have a paid Nous Portal subscription, Hermes can turn it into tools: managed web/image/TTS/STT/browser calls, an OpenAI-compatible local proxy for OAuth providers, keyless web search, and first-class live X search.*

---

## What It Is

Historically, if you wanted Hermes to search the web, generate images, speak, or drive a browser, you needed **separate accounts**:

- Firecrawl / Exa / Tavily / Parallel / Keenable for web search
- FAL for image generation
- OpenAI / ElevenLabs for TTS
- Browser Use / Browserbase for browser automation

That's multiple signups, API keys, billing pages, and different free-tier limits.

The **Nous Tool Gateway** collapses all of that into one subscription. If you're a paid [Nous Portal](https://portal.nousresearch.com) subscriber, tool usage bills against your subscription — no extra keys required. Some accounts also get a **free tool pool** — a small managed-tool allowance covering gateway calls without a paid subscription (Hermes surfaces it with a setup prompt on first use).

| Tool | Upstream | Direct key you'd otherwise need |
|------|----------|---------------------------------|
| Web search & extract | Firecrawl through the gateway | `FIRECRAWL_API_KEY`, `EXA_API_KEY`, `PARALLEL_API_KEY`, `TAVILY_API_KEY` |
| Image generation | Nine models under one endpoint, default FLUX 2 Klein 9B (FLUX 2 Pro, Nano Banana Pro, GPT Image 1.5/2, Ideogram V3, Recraft V4 Pro, Qwen Image, Z-Image Turbo) | `FAL_KEY` |
| Text-to-speech | OpenAI TTS voices → `text_to_speech` tool | `VOICE_TOOLS_OPENAI_KEY`, `ELEVENLABS_API_KEY` |
| Speech-to-text | Managed STT (voice-note transcription) | — |
| Browser automation | Headless Chromium via Browser Use | `BROWSER_USE_API_KEY`, `BROWSERBASE_API_KEY` |

Each tool is opt-in. You can route **any combination** through the gateway and keep direct keys for the rest — for example, gateway for web + images, your own ElevenLabs key for TTS.

---

## Who Gets It

Paid [Nous Portal](https://portal.nousresearch.com/manage-subscription) subscribers — and accounts granted the **free tool pool**, a small managed-tool allowance that covers gateway calls without a paid subscription (Hermes surfaces a setup prompt on first use). Free-tier accounts without a pool don't get gateway access.

Check your status:

```bash
hermes portal info        # Portal auth + Tool Gateway routing summary
hermes portal tools       # Gateway catalog with current routing per tool
hermes status             # Full system status (Tool Gateway is one section)
```

Look for the **Nous Tool Gateway** section. It shows which tools are active via the gateway, which are using direct keys, and which aren't configured yet.

---

## Enabling the Gateway

### Option A: During Model Setup (Easiest)

Fresh installs can do it in one shot:

```bash
hermes setup --portal   # Nous OAuth + Nous provider + Tool Gateway in one flow
```

Or when you run `hermes model` and pick **Nous Portal** as your provider, Hermes auto-prompts you to enable the Tool Gateway:

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

Pick a category (Web, Browser, Image Generation, TTS — or STT for voice-note transcription), then choose **Nous Subscription** as the provider. You don't have to log into Nous Portal first: selecting the Nous row runs the Portal login inline if needed and enables just that tool — it does **not** switch your inference provider. The picker writes the tool's selection key for you (see below). The Nous-managed backends are always listed, even if you've never signed in.

### Option C: Manual Config

Edit `~/.hermes/config.yaml`. Each tool category has a single provider-selection key; the value `nous` routes it through the managed gateway, a vendor name (`fal`, `openai`, `firecrawl`, `browser-use`, …) goes direct with your own credentials:

```yaml
web:
  backend: nous          # web search/extract via the Tool Gateway

image_gen:
  provider: nous         # image generation via the Gateway

tts:
  provider: nous         # TTS via the Gateway

stt:
  provider: nous         # speech-to-text via the Gateway

browser:
  cloud_provider: nous   # cloud browser via the Gateway
```

---

## How Selection Works

The runtime **always uses the stored selection** — credential presence never selects or reroutes a category. A `FAL_KEY` sitting in `.env` is ignored while `image_gen.provider: nous`; conversely, `image_gen.provider: fal` with no `FAL_KEY` set produces a clear error instead of silently falling back to the gateway.

Categories you have **never configured** (no selection key ever written) autodetect from available credentials, same as before. But once a selection exists, adding a key to `.env` does not change the route — only `hermes tools` (or editing the selection key) does.

### The Old `use_gateway` Flag Is Legacy

Older Hermes versions used a per-tool `use_gateway: true` boolean. That flag is **legacy**: it is never written anymore, and the `hermes tools` picker removes it from a category's config when it rewrites the selection. Old configs that still contain `use_gateway: true` are interpreted at read time as the `nous` selection, so existing setups keep working. Don't set `use_gateway` in new configs — pick the provider in `hermes tools` instead.

And the ancient hidden env flag `HERMES_ENABLE_NOUS_MANAGED_TOOLS` (v0.9) is long gone — replaced by these selection keys.

---

## Verifying It's Working

```bash
hermes portal info     # routing summary, or
hermes status          # full system status
```

Look for:

```text
◆ Nous Tool Gateway
  Nous Portal   ✓ managed tools available
  Web tools     ✓ active via Nous subscription
  Image gen     ✓ active via Nous subscription
  TTS           ✓ active via Nous subscription
  Browser       ○ active via Browser Use key
```

Rows marked "active via Nous subscription" are routed through the gateway. Rows with their own keys show which provider is active.

You can also see gateway usage in the Dashboard's **Analytics** tab (Part 12) — gateway calls count toward your Nous subscription and are aggregated alongside LLM token usage, and the [Nous Portal dashboard](https://portal.nousresearch.com) breaks usage down per tool.

---

## Switching Back to Direct Keys

Interactive:

```bash
hermes tools
# Pick the tool → choose a direct provider (e.g. Firecrawl)
```

Manual:

```yaml
web:
  backend: firecrawl   # Hermes now uses FIRECRAWL_API_KEY from .env
```

Picking a non-gateway provider in `hermes tools` rewrites that category's selection key, so the two can never contradict.

---

## OpenAI-Compatible Local Proxy (`hermes proxy`)

`hermes proxy` is a local HTTP server that forwards OpenAI-compatible chat/completions/embeddings requests to an OAuth-backed upstream — your **Nous Portal** subscription (default) or **xAI/Grok** — attaching the real, auto-refreshing credential on the way out, so the client app never holds an API key. This is the clean way to let Codex CLI, Aider, Cline, Continue, Open WebUI, OpenViking, Karakeep, or any OpenAI-compatible client reuse your subscription.

```bash
hermes portal              # one-time: log into the provider (OAuth)
hermes proxy start         # listens on http://127.0.0.1:8645/v1
```

Then point any OpenAI-compatible app at:

```text
Base URL:   http://127.0.0.1:8645/v1
API key:    anything        # e.g. "sk-unused" — proxy attaches the real one
Model:      Hermes-4-70B    # whatever your subscription serves
```

Management:

```bash
hermes proxy providers     # available upstreams (nous, xai; more via UpstreamAdapter)
hermes proxy status        # credential readiness, bearer expiry
hermes proxy start --provider xai --port 8645
```

The proxy forwards only a fixed allowlist of paths (`/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/models`), ignores the client's `Authorization` header, and streams SSE responses through unchanged. It has no auth of its own — it accepts any bearer — so keep it on `127.0.0.1` unless you're behind a firewall/VPN, and note your subscription's RPM/TPM limits apply across the whole proxy. (Anthropic Messages via OAuth doesn't fit the OpenAI-compatible shape yet and is a documented future adapter.)

---

## `x_search`: First-Class X Search

`x_search` gives the agent server-side X search via xAI's Responses API — Grok searches the X index and returns synthesized results with **citations to the originating posts**. Use it when the source of truth is a live X/Twitter thread, launch post, or maintainer account; use `web_search` for docs/blogs.

**Credentials (either path auto-enables the tool):**

- `XAI_API_KEY` in `~/.hermes/.env` — the recommended path, returning real posts with citations. Subscription OAuth can answer in a degraded explanatory mode with no citations, so the key wins when both exist.
- `hermes auth add xai-oauth` — xAI Grok OAuth (SuperGrok / X Premium+), refreshed automatically.

Disable explicitly via `hermes tools` → Search if you don't want it. Configuration is global in `~/.hermes/config.yaml`:

```yaml
x_search:
  model: grok-4.5            # any Grok model with server-side x_search access
  timeout_seconds: 180       # complex queries can take 60–120s
  retries: 2                 # 5xx / ReadTimeout backoff
  # reasoning_effort: low    # optional effort knob
```

The agent can also pass narrowing parameters per calls — `allowed_x_handles`, `excluded_x_handles`, `from_date`/`to_date`, and image/video understanding. Responses carry a `degraded` flag: when you used filters and Grok synthesized an answer without citations, treat it as unsourced.

The `xurl` skill is the other half of the X surface: exact, authenticated X API work (post, reply, like, DM, timelines). Use `x_search` for read-only discovery, then `xurl` for anything state-changing.

---

## Keyless Web Tier — No Gateway, No Keys, No Accounts

Since v0.20, web search works out of the box even with **zero web credentials**: `web_search` and `web_extract` rotate round-robin across **five vendors' public free tiers** — Exa, Parallel, Tavily, Firecrawl, and Keenable — spreading load and automatically retrying a rate-limited request on the next vendor in the ring (multi-hop, until one serves or all throttle). No signup, no key; requests carry no user identifiers.

This tier is strictly last-resort: any configured backend selection or present API key always wins, and the keyless ring only serves when nothing else matches. It is never sticky — the very next call tries your configured backend again. Disable it entirely with `web.keyless_fallback: false` (which also disables the one-shot keyless rescue for keyed backends, `web.keyless_rescue`).

---

## Outbound Webhooks (v0.20)

Dynamic webhook subscriptions let an external service (GitHub, Stripe, CI, anything) POST into the gateway adapter and trigger an agent run:

```bash
hermes webhook subscribe github-events --prompt 'New {event} on {repo.full_name}' \
  --events issues,pull_request --deliver telegram --deliver-chat-id 123456
```

Each subscription gets a route URL plus a one-time HMAC secret (subscriptions live in `webhook_subscriptions.json`, hot-reloaded — no gateway restart needed). The agent runs the prompt, and the result is **delivered outbound** to a target: `telegram`, `discord`, `slack`, `github_comment`, or local log. `--deliver-only` skips the agent and renders the prompt as a literal outbound message (zero LLM cost, sub-second). The dashboard's Webhooks page (Part 12) covers the same surface from the browser. Webhook safety: keep approvals on, scope the toolset, and template narrowly.

---

## Egress Proxy — one-time proxy tokens for sandboxes

The **iron-proxy** egress layer is for anyone whose terminal runs in a Docker (or other remote) sandbox and doesn't want real API keys sitting inside it. Sandboxes hold opaque **proxy tokens**; a local TLS-intercepting proxy swaps them for real credentials at the network boundary. Managed entirely by `hermes egress`:

```bash
hermes egress install    # download the pinned iron-proxy binary
hermes egress setup      # CA, mappings, config (optionally --from-bitwarden)
hermes egress start
hermes egress status     # binary + config + pid + listening + mappings
```

Wired into the **Docker** terminal backend (as of writing). `/egress` shows the same status from inside a session, and `~/.hermes/proxy/proxy.yaml` / `~/.hermes/proxy/iron-proxy.log` are where you look when something's wrong. The net effect: a compromised sandbox leaks useless tokens, never real keys.

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
No. While a tool's selection is **Nous Subscription**, direct keys for that tool are simply ignored. Your keys stay in `.env`. Pick the direct provider again in `hermes tools` and they become the source again.

### Can I mix gateway and direct keys?
Yes — it's per-tool. Gateway for web + images, ElevenLabs for TTS, Browserbase for browsing is a perfectly normal setup.

### What happens if my subscription lapses?
Tools routed through the gateway stop working (Hermes shows a clear error pointing at the portal). Either renew at [portal.nousresearch.com](https://portal.nousresearch.com/manage-subscription) or switch those tools to direct keys via `hermes tools`.

### Does it work on Telegram / Discord / Slack / etc.?
Yes. The gateway operates at the tool runtime level, not the entry-point level. It works the same whether you're on the CLI, a messaging platform, a cron job, or the dashboard's REST API.

### Is Modal (serverless terminal) included?
No — Modal is an optional subscription add-on. Configure it separately via `hermes setup terminal` or in `config.yaml`. The Tool Gateway prompt doesn't enable it automatically.

### Will the gateway auto-fall-back if the upstream is down?
The gateway itself is a thin proxy — failures return the upstream's error. If you want resilience, configure a direct provider (`hermes tools` → pick Firecrawl/Browserbase/etc.) and switch when the gateway has an incident. Web search additionally has the keyless ring ([Keyless Web Tier](#keyless-web-tier--no-gateway-no-keys-no-accounts)) as a last-resort fallback behind any configured backend.

---

## Cost Playbook

Rough guidance for picking between gateway vs direct keys:

- **Heavy web search + browsing + images in the same month:** gateway almost always wins — one subscription covers them all.
- **Only heavy TTS (audio generation):** ElevenLabs direct is often cheaper than the gateway's OpenAI TTS pricing. Keep TTS off the gateway.
- **Low volume, experimenting:** gateway is perfect — no signups, no free-tier juggling, no surprise overages.
- **Web search only, no Nous sub:** use the keyless ring (Exa/Parallel/Tavily/Firecrawl/Keenable) — it's free and needs zero setup; pin a provider or add a key when you want higher limits.
- **Enterprise / regulated environment:** self-hosted gateway with the `TOOL_GATEWAY_*` env vars pointing at your own proxy.

---

## What's Next

- **Local UI for everything:** [Part 12 — The Local Web Dashboard](./part12-web-dashboard.md)
- **Faster model responses:** [Part 14 — Fast Mode & Background Watchers](./part14-fast-mode-watchers.md)
- **Expand to iMessage / WeChat / Android:** [Part 15 — New Platforms](./part15-new-platforms.md)
