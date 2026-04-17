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
ps aux | grep hermes-gateway

# Check logs
tail -50 ~/.hermes/logs/gateway.log
```

## Common Crash Causes

### 1. Context Window Overflow

**Symptoms:** Gateway dies mid-response, logs show token count errors.

**Fix:** Reduce context injection in `~/.hermes/.env`:

```bash
# Lower the max context (default is usually model max)
MAX_CONTEXT_TOKENS=80000

# Enable compression earlier
CONTEXT_COMPRESSION_THRESHOLD=70
```

### 2. OOM (Out of Memory)

**Symptoms:** Gateway killed by OOM killer, `dmesg` shows `Out of memory: Killed process`.

**Fix:**

```bash
# Check memory usage
free -h

# If using local models via Ollama, they eat VRAM/RAM
# Move Ollama to a separate machine or reduce model size

# Limit gateway memory
# In systemd service or launcher script:
systemctl edit hermes-gateway
# Add: MemoryMax=4G
```

### 3. API Provider Down

**Symptoms:** Gateway running but all responses fail, logs show connection errors.

**Fix:** Configure fallback providers (see Part 9):

```yaml
model_fallback:
  - provider: cerebras
    model: llama-3.3-70b
  - provider: openrouter
    model: anthropic/claude-sonnet-4
  - provider: local
    model: nemotron:latest
```

### 4. Disk Full

**Symptoms:** Gateway can't write session files, logs, or memory database.

**Fix:**

```bash
# Check disk space
df -h

# Clean old session files (safe to delete)
find ~/.hermes/sessions -mtime +30 -delete

# Clean old logs
find ~/.hermes/logs -mtime +7 -delete

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

Set up systemd to auto-restart the gateway:

```ini
# /etc/systemd/system/hermes-gateway.service
[Unit]
Description=Hermes Agent Gateway
After=network.target

[Service]
Type=simple
User=terp
WorkingDirectory=/home/terp/.hermes
ExecStart=/home/terp/.hermes/venv/bin/python -m hermes_gateway
Restart=always
RestartSec=5
MemoryMax=4G

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable hermes-gateway
sudo systemctl start hermes-gateway

# Check status
sudo systemctl status hermes-gateway

# View logs
journalctl -u hermes-gateway -f
```

## Auto-Recovery (Cron Fallback)

If you can't use systemd, use a cron watchdog:

```bash
# Add to crontab -e
* * * * * pgrep -f "hermes.*gateway" > /dev/null || (cd ~/.hermes && nohup ./venv/bin/python -m hermes_gateway >> logs/watchdog.log 2>&1 &)
```

Checks every minute. If gateway isn't running, starts it.

## Health Check

Quick script to verify everything is working:

```bash
#!/bin/bash
# ~/.hermes/scripts/health-check.sh

# Gateway running?
if ! pgrep -f "hermes.*gateway" > /dev/null; then
    echo "CRITICAL: Gateway not running"
    exit 1
fi

# Can we reach the API?
if ! curl -s http://localhost:8642/health > /dev/null 2>&1; then
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
