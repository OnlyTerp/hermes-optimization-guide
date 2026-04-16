# Part 4: Telegram Setup (Chat From Anywhere)

*Connect Hermes to Telegram for mobile access, voice memos, group chats, and scheduled task delivery.*

---

## Why Telegram

Your agent is only useful if you can access it. Sitting at a terminal works until you need to:

- Check something from your phone while away from your desk
- Get notified when a long-running task finishes
- Use Hermes in a group chat with your team
- Send voice memos that get auto-transcribed and processed
- Receive scheduled task results (cron jobs) on mobile

Telegram is the best messaging platform for Hermes bots — it supports text, voice, images, files, inline buttons, and group chats with minimal setup.

---

## Step 1: Create a Bot via BotFather

Every Telegram bot requires an API token from [@BotFather](https://t.me/BotFather), Telegram's official bot management tool.

1. Open Telegram and search for **@BotFather**, or visit [t.me/BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Choose a **display name** (e.g., "Hermes Agent") — this can be anything
4. Choose a **username** — this must be unique and end in `bot` (e.g., `my_hermes_bot`)
5. BotFather replies with your **API token**. It looks like this:

```
123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
```

> **Keep your bot token secret.** Anyone with this token can control your bot. If it leaks, revoke it immediately via `/revoke` in BotFather.

---

## Step 2: Customize Your Bot (Optional)

These BotFather commands improve the user experience:

| Command | Purpose |
|---------|---------|
| `/setdescription` | The "What can this bot do?" text shown before chatting |
| `/setabouttext` | Short text on the bot's profile page |
| `/setuserpic` | Upload an avatar for your bot |
| `/setcommands` | Define the command menu (the `/` button in chat) |

For `/setcommands`, a useful starting set:

```
help - Show help information
new - Start a new conversation
sethome - Set this chat as the home channel
status - Show agent status
```

---

## Step 3: Privacy Mode (Critical for Groups)

Telegram bots have **privacy mode** enabled by default. This is the single most common source of confusion.

**With privacy mode ON**, your bot can only see:
- Messages that start with a `/` command
- Replies directly to the bot's own messages
- Service messages (member joins/leaves, pinned messages)

**With privacy mode OFF**, the bot receives every message in the group.

### How to Disable Privacy Mode

1. Message **@BotFather**
2. Send `/mybots`
3. Select your bot
4. Go to **Bot Settings → Group Privacy → Turn off**

> **You must remove and re-add the bot to any group** after changing the privacy setting. Telegram caches the privacy state when a bot joins a group — it won't update until removed and re-added.

> **Alternative:** Promote the bot to **group admin**. Admin bots always receive all messages regardless of privacy settings.

---

## Step 4: Find Your User ID

Hermes uses numeric Telegram user IDs to control access. Your user ID is **not** your username — it's a number like `123456789`.

**Method 1 (recommended):** Message [@userinfobot](https://t.me/userinfobot) — it instantly replies with your user ID.

**Method 2:** Message [@get_id_bot](https://t.me/get_id_bot) — another reliable option.

Save this number; you'll need it for the next step.

---

## Step 5: Configure Hermes

### Option A: Interactive Setup (Recommended)

```bash
hermes gateway setup
```

Select **Telegram** when prompted. The wizard asks for your bot token and allowed user IDs, then writes the configuration for you.

### Option B: Manual Configuration

Add the following to `~/.hermes/.env`:

```bash
TELEGRAM_BOT_TOKEN=<your-bot-token-from-botfather>
TELEGRAM_ALLOWED_USERS=<your-numeric-user-id>    # Comma-separated for multiple users
```

> **Security tip:** After editing, run `chmod 600 ~/.hermes/.env` to restrict file access to your user only.

For groups, also add the group chat ID (negative number, like `-1001234567890`):

```bash
TELEGRAM_ALLOWED_CHATS=-1001234567890
```

---

## Step 6: Start the Gateway

```bash
hermes gateway
```

The bot should come online within seconds. Send it a message on Telegram to verify.

---

## Gateway Management

```bash
# Check gateway status
hermes gateway status

# Stop the gateway
hermes gateway stop

# Restart after config changes
hermes gateway restart

# Run as a system service (auto-start on boot)
hermes gateway install   # Sets up systemd/launchd service
```

---

## Features Available on Telegram

### Text Chat
Full conversation support — the bot processes your messages the same as the CLI.

### Voice Messages
Send a voice memo and Hermes:
1. Auto-transcribes it using Whisper
2. Processes the transcription as a text message
3. Responds with text (or voice via TTS)

### Image Analysis
Send a photo and Hermes analyzes it using vision models. Describe what you want to know about the image in the caption.

### File Attachments
Send documents, code files, or data files — Hermes can read and process them.

### Inline Buttons
For dangerous commands, Hermes shows confirmation buttons instead of executing immediately.

### Slash Commands
The bot supports Telegram's native command menu (the `/` button in chat).

### Scheduled Messages
Cron job results are delivered directly to your Telegram chat:

```bash
# Deliver cron results to Telegram
hermes cron create --deliver telegram "Check server status every hour" --schedule "every 1h"
```

---

## Webhook Mode (For Cloud Deployments)

By default, Hermes uses **long polling** — the gateway makes outbound requests to Telegram. This works for local and always-on servers.

For **cloud deployments** (Fly.io, Railway, Render), **webhook mode** is better. These platforms auto-wake on inbound HTTP traffic but not on outbound connections.

### Configuration

Add to `~/.hermes/.env`:

```bash
TELEGRAM_WEBHOOK_URL=https://your-app.fly.dev
TELEGRAM_WEBHOOK_SECRET=<generate-with-command-below>
```

Generate a strong secret — never use a guessable value:

```bash
openssl rand -hex 32
```

Copy the output and paste it as your `TELEGRAM_WEBHOOK_SECRET` value.

> **Warning:** A weak or default webhook secret lets attackers forge Telegram webhook requests and inject messages into your agent. Always use a cryptographically random value.

| | Polling (default) | Webhook |
|---|---|---|
| Direction | Gateway → Telegram | Telegram → Gateway |
| Best for | Local, always-on servers | Cloud platforms |
| Extra config | None | `TELEGRAM_WEBHOOK_URL` |
| Idle cost | Machine must stay on | Machine can sleep |

---

## Multi-User Setup

To allow multiple users to interact with the bot:

```bash
TELEGRAM_ALLOWED_USERS=123456789,987654321,555555555
```

Each user gets their own conversation session. The bot tracks sessions per user ID.

---

## Troubleshooting

### Bot not responding

1. Check the token is correct: `echo $TELEGRAM_BOT_TOKEN`
2. Verify the gateway is running: `hermes gateway status`
3. Check logs: `hermes gateway logs`

### Bot in group but not seeing messages

Privacy mode is still on. You must:
1. Disable privacy in BotFather (`/mybots` → Bot Settings → Group Privacy → Turn off)
2. **Remove the bot from the group**
3. **Re-add the bot to the group**

### Voice messages not transcribed

Hermes needs `ffmpeg` for audio conversion. The installer includes it, but if you installed manually:

```bash
sudo apt install ffmpeg   # Ubuntu/Debian
brew install ffmpeg        # macOS
```

### Rate limiting

Telegram limits bots to 30 messages/second to different chats and 20 messages/minute to the same group. If you're hitting limits, add a delay:

```bash
hermes config set telegram.rate_limit_delay 1
```

---

## What's Next

- **Want the agent to self-improve?** → [Part 5: On-the-Fly Skills](./part5-creating-skills.md)
