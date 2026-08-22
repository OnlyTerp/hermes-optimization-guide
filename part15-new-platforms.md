# Part 15: Messaging Platforms — 30+ Adapters (iMessage via Photon, WhatsApp Cloud, Teams, LINE, SimpleX, Google Chat, A2A, Buzz, IRC, WeChat, Android)

*Hermes' gateway is now a plugin host. v0.9 made Hermes "everywhere"; v0.11/v0.12 added QQBot, Tencent Yuanbao, and Microsoft Teams; v0.13 added Google Chat; v0.14 wired Teams end-to-end and added LINE + SimpleX Chat; v0.15 added ntfy; and v0.17 "Reach" added the three biggest asks at once — **iMessage with no Mac required (Photon)**, an **official WhatsApp Business Cloud API** adapter, and the **Raft** agent-to-agent network. The v0.18–v0.20 wave kept widening the roster: **IRC** (stdlib-only, no deps), **Buzz** (Block's Nostr-based human+agent community platform), **A2A** (the Linux Foundation's Agent2Agent protocol v1.0 — agents calling agents), a **Microsoft Graph webhook** connector powering the Teams Meeting Pipeline, and the experimental **Hermes Relay** connector system that fronts platforms without holding their credentials. As of **v0.20.4 (2026.8.18)**, the official docs catalog **34 adapter pages** — this part is the curated tour.*

---

<a id="the-25-platform-lineup"></a>
## The 30+ Platform Lineup

As of v0.20.4, the gateway ships **34 adapter pages** in the official docs — built-in adapters plus plugin-shipped platforms. The full capability matrix (voice, images, files, threads, reactions, typing, streaming per platform) lives in the [official Messaging Gateway docs](https://nousresearch.github.io/hermes-agent/docs/user-guide/messaging/) and changes with every release; the roster below is the current shape:

| Platform | Mode | Notes |
|----------|------|-------|
| Telegram | Polling + Webhook | Flagship adapter — see [Part 4](./part4-telegram-setup.md) |
| Discord | WebSocket (bot) | Slash commands, voice/media, DMs + servers |
| Slack | Socket / Events API | Threads, file uploads, blocks |
| **Google Chat** | App / webhook | Workspace-native chat surface |
| **LINE** | Messaging API | Japan/Korea/Taiwan mobile-first; has a built-in "slow LLM" postback trick |
| **SimpleX Chat** | Queue-based DMs | Privacy-first chat with no user IDs |
| WhatsApp (personal) | Web API (Baileys bridge) | QR-code login, requires always-on node |
| **iMessage (Photon)** | Photon Spectrum relay | **No Mac required** — managed line pool |
| **iMessage (BlueBubbles)** | Webhook | Self-hosted alternative (needs an always-on Mac) |
| **WhatsApp Business Cloud API** | Official Meta webhook | Production-grade — no QR node, no ban risk |
| **Weixin (WeChat personal)** | Long-poll (iLink) | QR login, media, encrypted CDN |
| **WeCom (Enterprise WeChat)** | Webhook (+ callback variant) | Corporate WeChat, signature-validated callbacks |
| **QQBot** | WebSocket/Webhook | Tencent QQ via Official API v2 |
| **Tencent Yuanbao** | Native gateway | Text + media delivery, China/APAC |
| **Raft** | Agent network | Talk to other agents, not humans |
| **A2A** | Agent protocol (HTTP) | **v0.20** — Linux Foundation A2A v1.0, both directions |
| **Buzz** | Nostr WebSocket + CLI | Block's open human+agent community platform |
| IRC | Raw IRC over asyncio | Zero dependencies; plain text only |
| Signal | REST via signal-cli | Self-hosted bridge |
| DingTalk | Webhook | Corporate IM, China/APAC |
| Feishu / Lark | Webhook | Corporate IM, ByteDance roster |
| SMS (Twilio) | Webhook | Plain SMS |
| Mattermost | WebSocket | Self-hosted Slack alternative |
| Matrix | Client-server | Federated chat |
| Email (IMAP+SMTP) | Polling | Plain email |
| **ntfy** | HTTP pub/sub | Push notifications to any device |
| Home Assistant | WebSocket | Voice + automation triggers |
| Webhook (generic) | HTTP POST | Wire up anything |
| Teams Meeting Pipeline | Microsoft Graph webhook | Transcripts → meeting summaries |
| open-webui | Chat UI | Serve Hermes through an Open WebUI frontend |
| Hermes Relay | Connector (experimental) | Front any platform without holding its credentials |

All of them respect:
- Allowlist / allow-all / pairing access controls
- `/fast` Fast Mode (Part 14)
- Tool Gateway routing (Part 13)
- Cron delivery targets
- The shared session database (Part 7)
- Pre-dispatch plugin hooks

This part covers the v0.9 adapters, the newer v0.12–v0.20 surfaces (A2A, Buzz, IRC, Raft, Photon, WhatsApp Cloud, Teams, LINE, SimpleX, Google Chat, QQBot, Yuanbao), the WeChat family, and **Android / Termux** — running the agent itself on a phone.

> **Telegram got richer in v0.17:** the Telegram adapter upgraded to Bot API 10.1 rich messages — formatted output with media, on by default. If your bot's replies suddenly look nicer, that's why; if a client chokes on them, they can be disabled per-gateway.

## 2026 Update (v0.17): iMessage Without a Mac, Official WhatsApp, and Raft

### iMessage via Photon Spectrum — the new default

The #1 ask since v0.9 — iMessage without dedicating a Mac — shipped in v0.17 as a platform plugin built on **Photon Spectrum's** managed line pool:

```bash
hermes photon setup --phone +15551234567   # device-code OAuth, one command: login + project + sidecar deps
hermes photon status                        # verify token, sidecar, and connected line
```

The free tier draws from Photon's **shared line pool** — different recipients may see different sending numbers, but each conversation stays stable. The paid Business tier gives you a dedicated number. Either way, no macOS server, no Full Disk Access, and no always-on hardware. Restrict senders with `PHOTON_ALLOWED_USERS` or DM pairing (`hermes pairing approve photon <CODE>`), and everything else — allowlists, `/fast`, cron delivery — works like every other gateway.

Operationally:

- **Use Photon** if you just want Hermes on iMessage. It's the supported, zero-hardware path and is positioned as the successor to the BlueBubbles bridge.
- **Keep BlueBubbles** (below) if you require fully self-hosted message flow — Photon is a relay service, so your iMessage traffic transits their infrastructure. For the privacy-maximalist posture, the Mac-based bridge is still the answer.

### WhatsApp Business Cloud API — the official path

The old WhatsApp adapter drives WhatsApp Web with a QR login and an always-on Node.js bridge — fine for personal use, fragile for production (the July 2026 Baileys breakage above is exhibit A). v0.17 added an adapter for **Meta's official Business Cloud API**: webhook-based, no browser session or Node bridge to babysit, no account-ban risk, and legitimate for business use. It runs on a **dedicated business phone number** — not your personal number. If you're building anything customer-facing on WhatsApp, use this one; keep the Web adapter for personal accounts. `hermes gateway setup` walks you through the credentials and catches the #1 setup trap (pasting your phone number into the Phone Number ID field).

> **If the personal (Web) adapter suddenly broke for you in July 2026:** an upstream Baileys dependency change broke QR-login connections. Fixed in **v0.18.2 (`v2026.7.7.2`)** — update Hermes (and rebuild if you pin a Docker tag older than `v2026.7.7.2`), re-scan the QR, done.

### Raft — your agent gets peers

Raft is a channel where the counterparty is **another agent**, not a human. A bundled adapter connects Hermes to [Raft](https://raft.build) as an external agent through a wake-channel bridge: set `RAFT_PROFILE`, run the bridge, and Raft can wake Hermes to handle messages. The design is privacy-by-contract — wake payloads carry only metadata (event IDs, timestamps), never message bodies. Still: treat every inbound Raft message as **untrusted input** — same posture as a public group chat: quarantine profile, no write tools, approvals for anything that touches your machine. [Part 19](./part19-security-playbook.md) applies double here.

## 2026 Update (v0.20): A2A, Buzz, IRC, and the Relay Connector

The v0.18–v0.20 wave wasn't just desktop polish — it added four new gateway surfaces worth knowing about.

### A2A — agents calling agents (protocol v1.0)

[A2A](https://a2a-protocol.org) is the Linux Foundation's Agent2Agent protocol v1.0, and the Hermes plugin works **both directions**: your agent can call other A2A agents as tools, and other agents can send tasks to your Hermes over HTTP. Interop is with anything on the `a2a-sdk` — another Hermes, LangChain, CrewAI, Google ADK. This is the protocol-level sibling of Raft: Raft is a wake-channel to one external service; A2A is a general agent network.

```yaml
gateway:
  platforms:
    a2a:
      enabled: true
      extra:
        port: 9900
```

The outbound client tools ship as an `a2a` toolset, **off by default** — enable per platform with `hermes tools enable a2a --platform cli` (or `--platform telegram`, etc.). Same trust posture as Raft: A2A peers are untrusted input; quarantine profile + approvals until identity is proven.

### Buzz — Block's Nostr-based team chat

The [Buzz](https://github.com/block/buzz) adapter connects Hermes to a Buzz community — Block's open-source human+agent collaboration platform built on the **Nostr protocol**. Inbound rides a persistent NIP-42-authenticated WebSocket subscription (CLI polling as fallback); outbound shells to the `buzz` CLI. Needs the `buzz` binary on PATH and a Nostr key that's already a community member. Buzz renders markdown, delivers images (local files or URLs), and can thread replies onto existing messages. Run `hermes gateway setup`, pick **Buzz**, and set `BUZZ_TRANSPORT=auto|websocket|poll` in `.env`.

### IRC — the zero-dependency classic

The IRC adapter is pure Python stdlib `asyncio` — no SDK, no daemon, no extra packages. It speaks the IRC protocol directly, so it works on public networks (Libera.Chat) or any self-hosted ircd. Plain text means **no voice/images/files/threads/reactions** — replies are `PRIVMSG` lines, long messages split to fit the line limit. Configure with `platforms.irc.extra` (`server`, `port`, `nickname`, `channel`/`channels`, optional NickServ password) in `config.yaml` — the gateway merges the top-level `platforms.` map into its platform config. Ideal for tireless on-call bots in a channel everyone already lives in.

### Hermes Relay — front platforms without holding their credentials (experimental)

Relay is not a platform itself — it's a **connector system**. A separate service (the *connector*) owns the platform bot tokens and sockets; your gateway dials **out** to it over one authenticated WebSocket and gets a capability descriptor at handshake. Because the gateway never opens an inbound port and never touches platform secrets, relay works behind NAT and is the answer when a platform's credentials must not live on the agent host. Marked experimental — the wire contract may change without a deprecation cycle.

### Teams Meeting Pipeline

Separate from the Teams bot, the [Microsoft Graph webhook](https://nousresearch.github.io/hermes-agent/docs/user-guide/messaging/msgraph-webhook) surface delivers meeting transcripts → AI summaries into your chosen Teams target, using the same `teams` platform entry for outbound delivery. With the meeting-pipeline plugin enabled, one Teams integration gives you both the bot and the meeting-summary writer.

## 2026 Update: Teams, LINE, SimpleX, Google Chat, QQBot, and Yuanbao

### Microsoft Teams

Teams is no longer just a proof of the v0.12 plugin architecture. In v0.14 the Graph auth, webhook listener, pipeline runtime, and outbound delivery are wired together, so Teams can be a real enterprise chat surface.

```yaml
gateway:
  platforms:
    teams:
      enabled: true
      extra:
        tenant_id: ${MICROSOFT_TENANT_ID}
        client_id: ${MICROSOFT_TEAMS_CLIENT_ID}
        client_secret: ${MICROSOFT_TEAMS_CLIENT_SECRET}
        port: 3978
```

Keep approvals in a private admin channel, not in the same team/channel where untrusted requests arrive. Who can reach the bot at all is controlled by `TEAMS_ALLOWED_USERS` (AAD object IDs). One Teams nicety: approvals render as interactive **Adaptive Cards** — Allow Once / Allow Session / Always Allow / Deny — instead of text-only prompts.

### LINE

Use LINE when your users are in Japan, Korea, Taiwan, or a consumer/mobile-first workflow. Treat it like Telegram operationally: one admin bot/channel for approvals, strict allowed user IDs, and no write tools in public rooms.

```bash
# ~/.hermes/.env — LINE configures via env vars
LINE_CHANNEL_ACCESS_TOKEN=...      # long-lived channel token (required)
LINE_CHANNEL_SECRET=...            # HMAC-SHA256 webhook verification (required)
LINE_ALLOWED_USERS=U1234567890...  # comma-separated U-prefixed user IDs
LINE_ALLOWED_GROUPS=C1234567890... # optional group IDs
LINE_HOME_CHANNEL=U1234567890...   # default cron / notification target
LINE_SLOW_RESPONSE_THRESHOLD=45    # optional: sticky "Get answer" postback for slow LLMs
```

### SimpleX Chat

SimpleX is the privacy-first choice: no global user IDs, no central identity graph. That is good for privacy and harder for ops. Require pairing, persist local contact labels, and do not use it as the only approval channel until restore/backup is tested.

```bash
# No `require_pairing` config key — SimpleX pairs by DM:
#   send any message to the bot -> it replies with a pairing code
hermes pairing approve simplex <CODE>
SIMPLEX_ALLOWED_USERS=...   # optional explicit allowlist; DM pairing covers the rest
```

### Google Chat

Google Chat is the cleanest Workspace choice for Google Workspace teams that do not want a separate Slack/Discord surface. Treat spaces as group chats: use allowlists, never approve sensitive actions in the same room that requested them, and route production approvals to a private admin DM/channel.

Typical posture:

```bash
# ~/.hermes/.env — Google Chat bridges via Pub/Sub with a service account
GOOGLE_CHAT_PROJECT_ID=my-chat-bot-123
GOOGLE_CHAT_SUBSCRIPTION_NAME=projects/my-chat-bot-123/subscriptions/hermes-chat-events-sub
GOOGLE_CHAT_SERVICE_ACCOUNT_JSON=/home/you/.hermes/google-chat-sa.json
GOOGLE_CHAT_ALLOWED_USERS=you@yourdomain.com,coworker@yourdomain.com
GOOGLE_CHAT_HOME_CHANNEL=spaces/AAAA...   # default cron delivery target
```

Keep public/customer-facing spaces in quarantine profile until identity mapping and approval routing are proven.

### QQBot

Use QQBot when your community already lives in QQ and you want the same approval/session model as Telegram or Discord. Treat QQ groups as untrusted input by default: keep allowlists tight, require approval for filesystem/network tools, and use [Part 19](./part19-security-playbook.md) for prompt-injection hardening.

### Tencent Yuanbao

Yuanbao is now a native gateway adapter with text and media delivery. It belongs in the same bucket as Weixin/WeCom: powerful in China/APAC workflows, but operationally different from Western SaaS bots. Verify media size limits and identity mapping before using it for production approvals.


## iMessage via BlueBubbles (Self-Hosted Alternative)

### Why You'd Still Do This

> **Most people should use Photon now** — `hermes photon setup --phone <your-number>`, above — it needs no Mac at all. BlueBubbles remains the right choice when you want message flow that never leaves hardware you own.

[BlueBubbles](https://bluebubbles.app/) is a free open-source macOS server that exposes a REST API + webhook feed on top of the native Messages.app database. If you have a Mac that stays on, you get a fully self-hosted iMessage bot with full media, reactions, typing indicators, and read receipts.

### Prerequisites

- A **macOS 10.15+** machine that stays on (a Mac mini or spare MacBook works great)
- Apple ID signed into Messages.app on that Mac, actually sending + receiving iMessages
- Homebrew

### Step 1: Install BlueBubbles Server

```bash
brew install --cask bluebubbles
open /Applications/BlueBubbles.app
```

> The app is unsigned (Apple disabled the dev account). If macOS blocks it, right-click in Finder → **Open** → confirm.

### Step 2: Grant Permissions

System Settings → Privacy & Security, grant BlueBubbles:

- **Full Disk Access** — required (it reads `~/Library/Messages/chat.db`)
- **Accessibility** — optional, enables the Private API helper for reactions, typing indicators, and read receipts

### Step 3: Capture Server URL and Password

BlueBubbles Server → **Settings → API**, note:

- **Server URL** (e.g. `http://192.168.1.10:1234`)
- **Server Password**

### Step 4: Configure Hermes

```bash
hermes gateway setup
```

Select **BlueBubbles (iMessage)**, paste the URL + password.

Or manually in `~/.hermes/.env`:

```bash
BLUEBUBBLES_SERVER_URL=http://192.168.1.10:1234
BLUEBUBBLES_PASSWORD=your-server-password
```

### Step 5: Authorize Users (Pick One)

**DM Pairing (recommended):**

When someone iMessages your Apple ID, Hermes auto-replies with a pairing code. Approve it:

```bash
hermes pairing approve bluebubbles <CODE>
hermes pairing list    # see pending + approved pairings
```

**Pre-authorize specific users** in `.env`:

```bash
BLUEBUBBLES_ALLOWED_USERS=user@icloud.com,+15551234567
```

**Open access** (not recommended — your iMessage is probably spammed):

```bash
BLUEBUBBLES_ALLOW_ALL_USERS=true
```

### Step 6: Start the Gateway

```bash
hermes gateway run
```

Hermes will register a webhook with BlueBubbles Server and listen. First message should round-trip within seconds.

### Environment Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `BLUEBUBBLES_SERVER_URL` | — | Server URL (required) |
| `BLUEBUBBLES_PASSWORD` | — | Server password (required) |
| `BLUEBUBBLES_WEBHOOK_HOST` | `127.0.0.1` | Webhook listener bind address |
| `BLUEBUBBLES_WEBHOOK_PORT` | `8645` | Webhook listener port |
| `BLUEBUBBLES_WEBHOOK_PATH` | `/bluebubbles-webhook` | Webhook URL path |
| `BLUEBUBBLES_HOME_CHANNEL` | — | Phone/email for cron delivery |
| `BLUEBUBBLES_ALLOWED_USERS` | — | Comma-separated authorized users |
| `BLUEBUBBLES_ALLOW_ALL_USERS` | `false` | Allow all users |
| `BLUEBUBBLES_SEND_READ_RECEIPTS` | `true` | Auto-mark messages as read |

### Features

- **Text, images, voice messages, videos, documents** in both directions
- **Tapback reactions** (love / like / dislike / laugh / emphasize / question) — requires Private API
- **Typing indicators** — requires Private API
- **Read receipts** — requires Private API
- **Address chats by email or phone number** — Hermes resolves to BlueBubbles GUIDs automatically
- **Cron delivery** — `hermes cron create --deliver bluebubbles …`

### Private API (Optional but Nice)

Install the helper bundle: [docs.bluebubbles.app/helper-bundle/installation](https://docs.bluebubbles.app/helper-bundle/installation). Without it, basic text + media still work — only reactions, typing, and read receipts require it.

### Security Note

BlueBubbles gives API access to your **entire iMessage history**. Treat the server password like a root password. Keep BlueBubbles on your LAN (or behind Tailscale / WireGuard) instead of exposing it publicly. If you must expose it, use Ngrok / Cloudflare Tunnel with authentication.

### Common Issues

- **"Cannot reach server"** — Mac asleep, BlueBubbles not running, firewall blocking the port
- **Messages not arriving** — webhook not registered. Check BlueBubbles Server → Settings → API → Webhooks. Make sure the webhook URL points back at the machine running Hermes.
- **"Private API helper not connected"** — only required for reactions/typing/receipts. Install the helper bundle or ignore if you don't need those.

---

## WeChat (Weixin, 微信)

### Why This Matters

WeChat is the dominant personal messaging platform across China and much of Asia-Pacific. The new Weixin adapter uses Tencent's public iLink Bot API, requires no public endpoint, and logs in via QR code — the exact UX people already use for Web WeChat.

> For corporate/enterprise WeChat, see the WeCom section below. The two are separate platforms.

### Prerequisites

- A personal WeChat account
- `aiohttp` and `cryptography` Python packages
- Optional: `qrcode` for terminal QR rendering during setup

```bash
pip install aiohttp cryptography
pip install qrcode   # optional — for terminal QR display
```

### Step 1: Run the Setup Wizard

```bash
hermes gateway setup
```

Pick **Weixin**. The wizard:

1. Requests a QR code from the iLink Bot API
2. Renders it in the terminal (or prints a URL to an image)
3. Scan with the WeChat mobile app → tap **Confirm Login**
4. Saves credentials to `~/.hermes/weixin/accounts/`

On success:

```text
微信连接成功，account_id=your-account-id
```

The wizard persists `account_id`, `token`, and `base_url`. You don't touch them again.

### Step 2: Set Access Controls (Optional)

In `~/.hermes/.env`:

```bash
WEIXIN_ACCOUNT_ID=your-account-id

# DM access policy: open, allowlist, disabled, or pairing
WEIXIN_DM_POLICY=open

# Or restrict to specific users
WEIXIN_ALLOWED_USERS=user_id_1,user_id_2

# Cron/notifications target
WEIXIN_HOME_CHANNEL=chat_id
WEIXIN_HOME_CHANNEL_NAME=Home
```

### Step 3: Start

```bash
hermes gateway
```

The adapter restores saved credentials, connects to iLink, and begins long-polling.

### Features

- **Long-poll transport** — no public endpoint, webhook, or WebSocket required
- **QR code login** — scan once, persist across restarts
- **DM and group messaging**
- **Media** — images, video, files, voice messages
- **AES-128-ECB encrypted CDN** — automatic encrypt/decrypt for every media transfer
- **Markdown reformatting** — headers, tables, code blocks rewritten for WeChat readability
- **Smart chunking** — single bubble when under the limit; split at logical boundaries only when oversized
- **Typing indicators**
- **SSRF protection** — outbound media URLs validated before download
- **Message deduplication** — 5-minute sliding window
- **Automatic retry with backoff** — survives transient API errors
- **Context token persistence** — disk-backed reply continuity across restarts

### Full Config Reference

In `config.yaml` under `platforms.weixin.extra`:

| Key | Default | Description |
|-----|---------|-------------|
| `account_id` | — | iLink Bot account ID (required) |
| `token` | — | iLink Bot token (required, auto-saved from QR login) |
| `base_url` | `https://ilinkai.weixin.qq.com` | iLink API base URL |
| `cdn_base_url` | `https://novac2c.cdn.weixin.qq.com/c2c` | CDN base for media |
| `dm_policy` | `open` | `open`, `allowlist`, `disabled`, or `pairing` |

### Common Issues

- **QR expires before you scan** — re-run `hermes gateway setup` and keep the phone ready
- **"Login confirmed but no messages"** — check `dm_policy`. `disabled` silently drops all DMs
- **Media downloads fail** — SSRF protection is blocking an internal/private URL. Set `WEIXIN_ALLOW_PRIVATE_MEDIA_URLS=true` only on trusted networks.

---

## WeCom (Enterprise WeChat, 企业微信)

Separate adapter for enterprise deployments. Setup is webhook-based rather than QR-based because WeCom bots run as first-class corporate apps.

### Quick Setup

1. In the WeCom admin console, create a new bot under **Apps & Mini Programs → Bots**.
2. Note the `corp_id`, `agent_id`, and `secret`.
3. Set a callback URL pointing at your Hermes instance (must be HTTPS, public, and respond to WeCom's verification handshake).
4. Add to `~/.hermes/.env`:

```bash
WECOM_CORP_ID=your-corp-id
WECOM_AGENT_ID=1000001
WECOM_SECRET=your-secret
WECOM_TOKEN=your-callback-token
WECOM_ENCODING_AES_KEY=your-43-char-aes-key
WECOM_ALLOWED_USERS=user_id_1,user_id_2
```

5. Run `hermes gateway` — the webhook handler exposes `/wecom/callback` and validates the WeCom signature on every inbound event.

Feature surface is a subset of Weixin — DM and @mention in group chats, text + media, and bot-to-user replies.

---

## Android / Termux (Running Hermes *on* Your Phone)

### What This Is

v0.9 adds a tested path for running the Hermes CLI itself directly on Android via [Termux](https://termux.dev/). Not "connect to Hermes from your phone" — that's what messaging adapters are for. **This is running the whole agent locally on the phone itself.**

Great for:
- Offline fieldwork where you don't want a round-trip to a server
- A self-contained assistant that never leaves your pocket
- Homelab admins who want `hermes` in their SSH kit on any device

### Tested Bundle (What You Get)

The Termux install path deliberately narrows the feature set to what's known-good on Android:

- ✅ Hermes CLI
- ✅ Cron support
- ✅ PTY / background terminal support
- ✅ Telegram gateway (best-effort background runs)
- ✅ MCP support
- ✅ Honcho memory provider
- ✅ ACP support

- ❌ `.[all]` extras (many fail to compile on Android)
- ❌ `voice` (blocked by `faster-whisper → ctranslate2` which has no Android wheels)
- ❌ Automatic browser / Playwright bootstrap
- ❌ Docker-based terminal isolation (Docker doesn't run on stock Android)
- ⚠️  Background persistence — Android may suspend Termux jobs; gateway runs are best-effort, not a managed service

### One-Line Installer

Inside Termux:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

On Termux, the installer:

- Uses `pkg` for system packages
- Creates the venv with `python -m venv`
- Installs `.[termux]` with `pip` (under a Termux-specific constraints file)
- Links `hermes` into `$PREFIX/bin` so it stays on PATH across sessions
- Skips the untested browser / WhatsApp bootstrap

### Manual Install (If the One-Liner Fails)

```bash
pkg update && pkg upgrade
pkg install python git libjpeg-turbo libandroid-support rust build-essential
python -m venv ~/hermes-venv
source ~/hermes-venv/bin/activate
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
python -m pip install -e '.[termux]' -c constraints-termux.txt
```

Add the venv to your Termux PATH so `hermes` stays available:

```bash
echo 'export PATH="$HOME/hermes-venv/bin:$PATH"' >> ~/.bashrc
```

### First Run

```bash
hermes
```

Set a model with `hermes model` — OpenRouter, Nous Portal, or any OpenAI-compatible endpoint works. For offline use, point at a local model server on your LAN (LM Studio, Ollama, vLLM running on a desktop) — the phone is your UI, the heavy lifting stays on the GPU.

### Keeping It Alive in the Background

Android aggressively suspends background apps. Two tactics:

**Termux:Boot + Termux:Wake-Lock** — install from F-Droid, add a wake-lock command to your gateway startup so Android doesn't freeze it:

```bash
termux-wake-lock
hermes gateway
```

**Don't use Android as a server.** For always-on gateway duty, put Hermes on a $5 VPS or a home Linux box and talk to it from your phone via Telegram / iMessage. Termux is great as an interactive agent on your phone, not as a production gateway.

### Tested vs. Untested on Android

If you want a feature outside the tested bundle, you can often get it working with extra effort — but it's on you. File issues with `[termux]` in the title if you hit something reproducible.

---

## What's Next

- **Telegram deep dive:** [Part 4 — Telegram Setup](./part4-telegram-setup.md)
- **UI for everything:** [Part 12 — Web Dashboard](./part12-web-dashboard.md)
- **Reliability on mobile links:** [Part 11 — Gateway Recovery](./part11-gateway-recovery.md)
