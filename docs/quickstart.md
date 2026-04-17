# 5-Minute Quickstart

From zero to working Telegram bot.

## Prereqs

- A Linux, macOS, or WSL machine (anything with bash)
- A Telegram account
- An Anthropic API key — [console.anthropic.com](https://console.anthropic.com/settings/keys)
- (Optional) A Google API key — [aistudio.google.com](https://aistudio.google.com/apikey) for free-tier routing

## Step 1 — Install Hermes

```bash
curl -sSL https://install.hermes.nous.ai | bash
hermes --version          # sanity check
```

## Step 2 — Create your Telegram bot

1. DM [@BotFather](https://t.me/BotFather) → `/newbot` → follow prompts
2. Copy the bot token
3. DM your new bot once (anything) so it can see you
4. Get your Telegram user ID — DM [@userinfobot](https://t.me/userinfobot)

## Step 3 — Drop in a config

```bash
# Pull the guide
git clone https://github.com/OnlyTerp/hermes-optimization-guide ~/hermes-guide

# Copy the Telegram-bot template
mkdir -p ~/.hermes
cp ~/hermes-guide/templates/config/telegram-bot.yaml ~/.hermes/config.yaml
```

## Step 4 — Fill in secrets

Create `~/.hermes/.env`:

```bash
cat > ~/.hermes/.env <<'EOF'
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
TELEGRAM_ADMIN_BOT_TOKEN=1234567890:ABC...
TELEGRAM_OWNER_ID=1234567            # your numeric ID from @userinfobot
EOF

chmod 600 ~/.hermes/.env
```

## Step 5 — Start it

```bash
hermes run &
```

DM your bot. It should reply in seconds.

## Step 6 — Install the skills you'll want

```bash
for skill in ~/hermes-guide/skills/*/*/SKILL.md; do
  name=$(basename $(dirname "$skill"))
  ln -sfn "$(dirname "$skill")" "$HOME/.hermes/skills/$name"
done
hermes /reload
```

Now try:

- `/audit-mcp` — no servers yet, so you'll get "nothing to audit" (expected)
- `/cost-report` — shows this session's token usage
- Ask it anything in freeform — chat just works

## Step 7 — Level up

- **More platforms:** [Part 4 (Telegram deep-dive)](../part4-telegram-setup.md), [Part 15 (iMessage/WeChat/Android)](../part15-new-platforms.md)
- **Memory that reasons:** [Part 3 (LightRAG)](../part3-lightrag-setup.md)
- **Tools:** [Part 17 (MCP servers)](../part17-mcp-servers.md)
- **Coding agent driver:** [Part 18 (Claude Code, Codex, Gemini CLI)](../part18-coding-agents.md)
- **Production hardening:** [Part 19 (Security)](../part19-security-playbook.md) + [Part 20 (Observability)](../part20-observability.md)
- **One-command VPS install:** [`scripts/vps-bootstrap.sh`](../scripts/vps-bootstrap.sh)

## Common first-hour issues

| Symptom | Fix |
|---|---|
| Bot doesn't respond | `journalctl --user -u hermes` — 99% of the time it's a missing env var |
| 401 from Anthropic | Check `ANTHROPIC_API_KEY` has no trailing newline: `cat -A ~/.hermes/.env` |
| "skill not found: /cost-report" | `hermes /reload` after symlinking skills |
| Replies are slow | You're on Anthropic free tier — rate-limited. Upgrade or route to Gemini Flash via the `cost-optimized` template |
