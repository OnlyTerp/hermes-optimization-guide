# Part 15: Messaging Platforms (Teams, LINE, SimpleX, Google Chat, iMessage, WeChat, Android)

*Hermes' gateway is now a plugin host. v0.9 made Hermes "everywhere"; v0.11/v0.12 added QQBot, Tencent Yuanbao, and Microsoft Teams; v0.13 added Google Chat; v0.14 wires Teams end-to-end and adds LINE + SimpleX Chat.*

---

## The 22+ Platform Lineup

As of v0.14, the gateway ships built-in adapters plus plugin-shipped platforms:

| Platform | Mode | Notes |
|----------|------|-------|
| Telegram | Polling + Webhook | Flagship adapter — see [Part 4](./part4-telegram-setup.md) |
| Discord | WebSocket (bot) | Slash commands, voice/media, DMs + servers |
| Slack | Socket / Events API | Threads, file uploads, blocks |
| **Google Chat** | App / webhook | **New in v0.13**, Workspace-native chat surface |
| **LINE** | Messaging API | **New in v0.14**, Japan/Korea/Taiwan mobile-first surface |
| **SimpleX Chat** | Decentralized chat | **New in v0.14**, privacy-first chat with no user IDs |
| WhatsApp | Web API | QR-code login, requires always-on node |
| **iMessage (BlueBubbles)** | Webhook | **New in v0.9** |
| **Weixin (WeChat personal)** | Long-poll | **New in v0.9** |
| **WeCom (Enterprise WeChat)** | Webhook | **New in v0.9** |
| **QQBot** | WebSocket/Webhook | Added after the original v0.9 platform sweep |
| **Tencent Yuanbao** | Native gateway | **New in v0.12**, text + media delivery |
| **Microsoft Teams** | Graph + webhook + runtime + delivery | End-to-end in v0.14 |
| Signal | REST via signal-cli | Self-hosted bridge |
| DingTalk | Webhook | Corporate IM, China/APAC |
| Feishu / Lark | Webhook | Corporate IM, ByteDance |
| SMS (Twilio) | Webhook | Plain SMS |
| Mattermost | WebSocket | Self-hosted Slack alternative |
| Matrix | Client-server | Federated chat |
| Email (IMAP+SMTP) | Polling | Plain email |
| Home Assistant | WebSocket | Voice + automation triggers |
| Webhook (generic) | HTTP POST | Wire up anything |

All of them respect:
- Allowlist / allow-all / pairing access controls
- `/fast` Fast Mode (Part 14)
- Tool Gateway routing (Part 13)
- Cron delivery targets
- The shared session database (Part 7)
- Pre-dispatch plugin hooks

This part covers the v0.9 adapters, the newer v0.12–v0.14 surfaces, and **Android / Termux** — running the agent itself on a phone.

## 2026 Update: Teams, LINE, SimpleX, Google Chat, QQBot, and Yuanbao

### Microsoft Teams

Teams is no longer just a proof of the v0.12 plugin architecture. In v0.14 the Graph auth, webhook listener, pipeline runtime, and outbound delivery are wired together, so Teams can be a real enterprise chat surface.

```yaml
gateways:
  teams:
    enabled: true
    tenant_id: ${MICROSOFT_TENANT_ID}
    client_id: ${MICROSOFT_TEAMS_CLIENT_ID}
    client_secret: ${MICROSOFT_TEAMS_CLIENT_SECRET}
    allowed_teams:
      - ${MICROSOFT_TEAMS_ADMIN_TEAM}
    trust_label: medium
```

Keep approvals in a private admin channel, not in the same team/channel where untrusted requests arrive.

### LINE

Use LINE when your users are in Japan, Korea, Taiwan, or a consumer/mobile-first workflow. Treat it like Telegram operationally: one admin bot/channel for approvals, strict allowed user IDs, and no write tools in public rooms.

```yaml
gateways:
  line:
    enabled: true
    channel_access_token: ${LINE_CHANNEL_ACCESS_TOKEN}
    channel_secret: ${LINE_CHANNEL_SECRET}
    allowed_user_ids:
      - ${LINE_ADMIN_USER_ID}
```

### SimpleX Chat

SimpleX is the privacy-first choice: no global user IDs, no central identity graph. That is good for privacy and harder for ops. Require pairing, persist local contact labels, and do not use it as the only approval channel until restore/backup is tested.

```yaml
gateways:
  simplex:
    enabled: true
    profile: simplex-admin
    require_pairing: true
    trust_label: medium
```

### Google Chat

Google Chat is the cleanest Workspace choice for Google Workspace teams that do not want a separate Slack/Discord surface. Treat spaces as group chats: use allowlists, never approve sensitive actions in the same room that requested them, and route production approvals to a private admin DM/channel.

Typical posture:

```yaml
gateways:
  google_chat:
    enabled: true
    project_id: ${GOOGLE_CLOUD_PROJECT}
    credentials_json: ${GOOGLE_CHAT_CREDENTIALS_JSON}
    allowed_spaces:
      - ${GOOGLE_CHAT_ADMIN_SPACE}
    trust_label: medium
```

Keep public/customer-facing spaces in quarantine profile until identity mapping and approval routing are proven.

### QQBot

Use QQBot when your community already lives in QQ and you want the same approval/session model as Telegram or Discord. Treat QQ groups as untrusted input by default: keep allowlists tight, require approval for filesystem/network tools, and use [Part 19](./part19-security-playbook.md) for prompt-injection hardening.

### Tencent Yuanbao

Yuanbao is now a native gateway adapter with text and media delivery. It belongs in the same bucket as Weixin/WeCom: powerful in China/APAC workflows, but operationally different from Western SaaS bots. Verify media size limits and identity mapping before using it for production approvals.


## iMessage via BlueBubbles

### Why This Matters

Apple doesn't have a public iMessage API. The only supported path is [BlueBubbles](https://bluebubbles.app/), a free open-source macOS server that exposes a REST API + webhook feed on top of the native Messages.app database.

If you have a Mac that stays on, you now have an iMessage bot with full media, reactions, typing indicators, and read receipts.

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

> **Windows users:** native Windows is not supported for the WeChat adapter. Use WSL2.

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
