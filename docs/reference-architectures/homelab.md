# Reference Architecture: Homelab

**Fully private, on your own hardware.** Nothing leaves your LAN except provider-bound LLM traffic (and optionally, none of that either if you run local models).

## Who this is for

- You own a homelab / NAS / dedicated box
- Privacy-first — you don't want recipe data / PRs / messages in a third-party cloud
- Willing to trade off convenience (dynamic DNS, patching) for control

## Cost

- **Infra:** electricity + existing hardware
- **LLM:** $0 if you go all-Ollama; otherwise retail API for a curated subset
- **External:** $0 (no Tailscale Pro required for 1–3 nodes)

## Architecture

```
                    ┌──────────────────────────────────────┐
                    │            Homelab (LAN)             │
                    │                                      │
   phone / laptop → │  Tailscale    hermes.lan (Caddy)     │
   (Tailscale)      │     │              │                 │
                    │     └──────────────┤                 │
                    │                    ↓                 │
                    │         hermes.service (systemd)     │
                    │                ├── Ollama (GPU box)  │
                    │                ├── LightRAG          │
                    │                ├── Langfuse (self)   │
                    │                └── Dashboard :8765   │
                    │                                      │
                    └──────────────────────────────────────┘
                              │
                              ↓ (optional, for hard queries)
                          Anthropic / Google / OpenAI
```

## Parts list

- **1× Linux box** (16GB+ RAM, any x86_64 or Apple Silicon VM) — runs Hermes, LightRAG, Langfuse
- **1× GPU box** (optional; 16GB+ VRAM) — runs Ollama. Can be the same box if you have one GPU.
- **Tailscale** (free tier, up to 3 users / 100 devices) — mesh VPN; no port-forwarding
- **Domain** (optional; `hermes.lan` works fine with Tailscale MagicDNS)

## Install steps

### 1. Base box

```bash
# On the Linux box (as root, Debian 12 or Ubuntu 24.04)
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | bash
```

### 2. Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --accept-routes
tailscale cert hermes.$(tailscale status --json | jq -r '.MagicDNSSuffix')
```

### 3. Ollama (optional — local models)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:70b-instruct-q4_K_M
ollama pull qwen2.5-coder:32b
```

### 4. Config

Start from [`templates/config/production.yaml`](../../templates/config/production.yaml), then:

```yaml
_config_version: 28

model:
  provider: ollama
  default: llama3.1:70b-instruct-q4_K_M
  base_url: http://gpu-box.tailnet-xxx.ts.net:11434

fallback_providers:
  - provider: anthropic
    model: anthropic/claude-sonnet-5

auxiliary:
  compression:
    provider: ollama
    model: qwen2.5-coder:32b
    base_url: http://gpu-box.tailnet-xxx.ts.net:11434

telegram:
  # Token/user allowlists live in ~/.hermes/.env or are written by:
  #   hermes gateway setup
  allowed_chats: "${TELEGRAM_ALLOWED_CHATS}"
  reactions: true

memory:
  memory_enabled: true
  user_profile_enabled: true
  provider: ""  # built-in memory; keep LightRAG as an external MCP/skill integration
```

### 5. Langfuse self-host (observability inside the LAN)

```bash
cp templates/compose/langfuse-stack.yml /opt/
cp templates/compose/.env.langfuse.example /opt/.env.langfuse
# edit /opt/.env.langfuse → generate secrets
docker compose -f /opt/langfuse-stack.yml --env-file /opt/.env.langfuse up -d
```

Point the observability plugin at Langfuse with `HERMES_LANGFUSE_BASE_URL=http://127.0.0.1:3000` plus the matching Langfuse public/secret keys in `~/.hermes/.env`.

### 6. Skills

```bash
for skill in /opt/hermes-optimization-guide/skills/*/*/; do
  ln -sfn "$skill" "/home/hermes/.hermes/skills/$(basename $skill)"
done
# Restart Hermes, start a new session, or run /reload-skills inside an active chat.
```

## Honest tradeoffs

- **Latency.** Local 70B Q4 ≈ 20–40 tok/s on a 3090. Flagship Sonnet ≈ 60–90 tok/s. Most "work" queries you won't notice; coding/deep reasoning you will.
- **Quality.** Current open/local models (Qwen Coder, Llama, Kimi-class local models) are *close* on many tasks, *behind* on long-context + nuanced reasoning. Routing lets you hand the hard stuff to Sonnet.
- **Patching.** You maintain the box. Enable unattended-upgrades (the bootstrap script does) and schedule monthly reboots.
- **Reachability.** Tailscale is solid but means "no Tailscale = no Hermes". Keep a cellphone backup admin bot, or run a tiny cloud relay.
- **Backups.** Set [`nightly-backup`](../../skills/ops/nightly-backup/SKILL.md) to write encrypted archives to a second physical disk — not the same RAID array.

## What to skip

- Cloudflare / public TLS — Tailscale handles that
- UFW rules for 80/443 — no public ports
- Paid Langfuse — self-host is free for any reasonable single-user volume

## When to graduate

You hit this setup's ceiling when:
- You want more than 1–2 humans using it (permissioning local models gets awkward)
- You need world-reachable webhooks (Stripe, GitHub, etc.)
- Your LightRAG graph exceeds ~200K entities (it'll still work, but merges slow down)

Graduate to [Solo Developer](./solo-developer.md) (add a tiny VPS) or [Small Agency](./small-agency.md).
