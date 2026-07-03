# 5-Minute Quickstart

From zero to working Telegram bot.

## Prereqs

- A Linux, macOS, or WSL machine (anything with bash)
- A Telegram account
- An Anthropic API key for the default model
- A Google API key — [aistudio.google.com](https://aistudio.google.com/apikey) for Gemini Flash classification + LightRAG LLM in the Telegram template
- An OpenAI API key — [platform.openai.com/api-keys](https://platform.openai.com/api-keys) for LightRAG embeddings in the Telegram template

## Step 1 — Install Hermes

```bash
curl -sSL https://hermes-agent.nousresearch.com/install.sh | bash
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

Create `~/.hermes/.env` — lock the permissions down *before* the keys hit disk:

```bash
touch ~/.hermes/.env
chmod 600 ~/.hermes/.env

cat > ~/.hermes/.env <<'EOF'
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...                 # required by telegram-bot.yaml for LightRAG embeddings
GOOGLE_API_KEY=AIza...                # required by telegram-bot.yaml for Gemini Flash classification + LightRAG LLM
TELEGRAM_ADMIN_BOT_TOKEN=1234567890:ABC...
TELEGRAM_OWNER_ID=1234567            # your numeric ID from @userinfobot
EOF
```

## Step 5 — Start it

```bash
hermes gateway
```

DM your bot. It should reply in seconds. Once it does, Ctrl-C and install it as a service so it survives reboots:

```bash
hermes gateway install   # sets up a systemd/launchd service
hermes gateway status    # confirm it's running
```

## Step 6 — Install the skills you'll want

```bash
for skill in ~/hermes-guide/skills/*/*/SKILL.md; do
  name=$(basename $(dirname "$skill"))
  ln -sfn "$(dirname "$skill")" "$HOME/.hermes/skills/$name"
done
```

Then, in a Hermes session (CLI or DM your bot):

```
/reload
```

Now try:

- `/audit-mcp` — no servers yet, so you'll get "nothing to audit" (expected)
- `/cost-report` — shows this session's token usage
- Ask it anything in freeform — chat just works

## Step 7 — Level up

- **More platforms:** [Part 4 (Telegram deep-dive)](../part4-telegram-setup.md), [Part 15 (Teams/LINE/SimpleX/iMessage/WeChat/Android)](../part15-new-platforms.md)
- **Latest features:** [Part 22 (Curator, TUI, plugins)](../part22-latest-power-moves.md), [Part 23 (Kanban, `/goal`, Checkpoints v2)](../part23-tenacity-stack.md)
- **Desktop app:** [Part 24 (Hermes Desktop)](../part24-desktop-app.md)
- **Local inference:** [Part 25 (NVIDIA local stack)](../part25-nvidia-local.md)
- **Answer quality:** [Part 26 (Mixture-of-Agents verification)](../part26-moa-verification.md)
- **Memory that reasons:** [Part 3 (LightRAG)](../part3-lightrag-setup.md)
- **Tools:** [Part 17 (MCP servers)](../part17-mcp-servers.md)
- **Coding agent driver:** [Part 18 (Claude Code, Codex, Gemini CLI)](../part18-coding-agents.md)
- **Production hardening:** [Part 19 (Security)](../part19-security-playbook.md) + [Part 20 (Observability)](../part20-observability.md)
- **One-command VPS install:** [`scripts/vps-bootstrap.sh`](../scripts/vps-bootstrap.sh)

## Common first-hour issues

| Symptom | Fix |
|---|---|
| Bot doesn't respond | Installed as a service? `journalctl --user -u hermes` (or `hermes gateway status`). Running in the foreground? The error is right there in the terminal. 99% of the time it's a missing env var |
| 401 from Anthropic | Check `ANTHROPIC_API_KEY` has no trailing newline: `cat -A ~/.hermes/.env` |
| "skill not found: /cost-report" | Run `/reload` in-session after symlinking skills |
| Replies are slow | You're rate-limited on a low Anthropic usage tier. Raise your tier or route to Gemini Flash via the `cost-optimized` template |
