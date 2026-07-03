# Part 11: Gateway Recovery (When Things Break at 3am)

*The gateway is the brain stem. When it crashes, everything stops.*

---

## What the Gateway Does

The gateway (`hermes gateway`) is the always-on process that:
- Receives messages from Telegram, Discord, Slack, CLI
- Routes them to the agent
- Manages sessions and context
- Runs cron jobs

If the gateway dies, your agent is unreachable.

## Detecting a Crash

```bash
# Check if gateway is running
hermes status

# Or directly
pgrep -af "[h]ermes gateway"

# Check logs
tail -50 ~/.hermes/logs/gateway.log
```

## Common Crash Causes

### 1. Context Window Overflow

**Symptoms:** Gateway dies mid-response, logs show token count errors.

**Fix:** Compress earlier so context never hits the window limit (see [Part 6](./part6-context-compression.md)):

```bash
# Trigger compression at 70% of the window instead of the 0.8 default
hermes config set compression.threshold 0.7
```

### 2. OOM (Out of Memory)

**Symptoms:** Gateway killed by OOM killer, `dmesg` shows `Out of memory: Killed process`.

**Fix:**

```bash
# Check memory usage
free -h

# If using local models via Ollama, they eat VRAM/RAM
# Move Ollama to a separate machine or reduce model size

# Limit gateway memory (templates/systemd/hermes.service already sets MemoryMax=4G)
sudo systemctl edit hermes
# Add under [Service]: MemoryMax=4G
```

### 3. API Provider Down

**Symptoms:** Gateway running but all responses fail, logs show connection errors.

**Fix:** Configure fallback models (see [Part 9](./part9-custom-models.md#fallback-chain)):

```bash
hermes config set fallback_models '["cerebras/qwen-3-32b", "openrouter/anthropic/claude-sonnet-5", "local/nemotron:latest"]'
```

### 4. Disk Full

**Symptoms:** Gateway can't write session files, logs, or memory database.

**Fix:**

```bash
# Check disk space
df -h

# Clean old session files (safe to delete)
find ~/.hermes/sessions -type f -mtime +30 -delete

# Clean old logs
find ~/.hermes/logs -type f -mtime +7 -delete

# Check LightRAG data size
du -sh ~/.hermes/skills/research/lightrag/data/
```

### 5. Crash Loop

**Symptoms:** Gateway starts, crashes immediately, repeats.

**Fix:**

```bash
# Check the last crash log
tail -100 ~/.hermes/logs/gateway.log

# Common cause: corrupted session file
# Move sessions out temporarily
mv ~/.hermes/sessions ~/.hermes/sessions.bak
mkdir ~/.hermes/sessions

# Restart
hermes gateway

# If it works, the issue was a corrupt session
# Move sessions back one by one to find the bad one
```

## Auto-Recovery (systemd)

Don't hand-roll a unit file. This repo ships a hardened one — [`templates/systemd/hermes.service`](./templates/systemd/hermes.service) — with a dedicated `hermes` user, `ProtectSystem=strict`, syscall filtering, and `MemoryMax=4G` already set:

```bash
sudo cp templates/systemd/hermes.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes

# Check status
sudo systemctl status hermes

# View logs
journalctl -u hermes -f
```

Or let Hermes do it for you — `hermes gateway install` (see [Part 4](./part4-telegram-setup.md)) generates and enables a user-level unit without any manual file copying.

Either way, `Restart=on-failure` + `RestartSec=5` means a crashed gateway is back within seconds.

## Auto-Recovery (Cron Fallback)

If you can't use systemd, use a cron watchdog. **Don't inline the `pgrep` into the crontab line** — `pgrep -f "hermes.*gateway"` would match the cron shell's own command line (it contains the pattern), so the check always "passes" and the gateway never restarts. Put the check in a script and use a bracketed pattern that can't match itself:

```bash
#!/bin/bash
# ~/.hermes/bin/gateway-watchdog.sh
# The [h] bracket trick: the pattern "[h]ermes gateway" matches the
# process "hermes gateway" but never matches this script's own cmdline.
if ! pgrep -f "[h]ermes gateway" > /dev/null; then
    echo "$(date -Is) gateway down, restarting" >> ~/.hermes/logs/watchdog.log
    nohup hermes gateway >> ~/.hermes/logs/watchdog.log 2>&1 &
fi
```

```bash
chmod +x ~/.hermes/bin/gateway-watchdog.sh

# Add to crontab -e
* * * * * $HOME/.hermes/bin/gateway-watchdog.sh
```

Checks every minute. If the gateway isn't running, starts it.

## Health Check

Quick script to verify everything is working:

```bash
#!/bin/bash
# ~/.hermes/scripts/health-check.sh

# Port of the gateway's local HTTP API. There is no fixed default —
# it's whatever you enabled via API_SERVER_ENABLED / the api_server
# settings in ~/.hermes/.env. Adjust to match your setup.
GATEWAY_PORT="${GATEWAY_PORT:-8642}"

# Gateway running? (bracket trick avoids matching this script itself)
if ! pgrep -f "[h]ermes gateway" > /dev/null; then
    echo "CRITICAL: Gateway not running"
    exit 1
fi

# Can we reach the API? (gateway should only listen on localhost)
if ! curl -s "http://localhost:${GATEWAY_PORT}/health" > /dev/null 2>&1; then
    echo "CRITICAL: Gateway not responding"
    exit 1
fi

# Disk space OK?
USAGE=$(df -Ph ~/.hermes | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$USAGE" -gt 90 ]; then
    echo "WARNING: Disk usage at ${USAGE}%"
    exit 1
fi

echo "OK"
```

---

*The gateway should be boring. If it's interesting, something's wrong.*
