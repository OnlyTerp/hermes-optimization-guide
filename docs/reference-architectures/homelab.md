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
                    │                └── Dashboard :9119   │
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
# Schema verified against Part 19 (v0.18).
# Primary model: local via the Ollama OpenAI-compatible endpoint.
model: llama3.1:70b-instruct-q4_K_M
provider: ollama

providers:
  ollama:
    base_url: http://gpu-box.tailnet-xxx.ts.net:11434/v1
    api_key: ollama                            # any non-empty string
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"            # for the hard stuff

# There is no intent-routing DSL (Part 20) — you switch models explicitly.
# Give the escalation a name and use `/model smart` when local isn't enough:
model_aliases:
  smart:
    model: claude-sonnet-5
    provider: anthropic

# Keep auxiliary side-tasks local too:
auxiliary_models:
  compression:
    provider: ollama
    model: qwen2.5-coder:32b
```

Platform wiring lives in `~/.hermes/.env`, not config.yaml (Part 19, Layer 1):

```bash
TELEGRAM_BOT_TOKEN=...          # admin bot from @BotFather
TELEGRAM_ALLOWED_USERS=123456789   # your numeric ID — default-deny otherwise
```

Memory: the native SQLite backend needs zero config (Part 7). For the knowledge-graph layer, LightRAG runs as its own server plus a query skill — it is not a `memory:` block in config.yaml; point its extraction model at Ollama (`qwen2.5-coder:32b`) and embeddings at `text-embedding-3-small` or a local bge-m3. Full setup: Part 3.

### 5. Langfuse self-host (observability inside the LAN)

```bash
cp templates/compose/langfuse-stack.yml /opt/
cp templates/compose/.env.langfuse.example /opt/.env.langfuse
# edit /opt/.env.langfuse → generate secrets
docker compose -f /opt/langfuse-stack.yml --env-file /opt/.env.langfuse up -d
```

Then enable the plugin and point it at your box: `hermes plugins enable observability/langfuse`, and in `~/.hermes/.env` set `HERMES_LANGFUSE_BASE_URL=http://127.0.0.1:3000` plus the pk/sk keys — there is no `telemetry:` block in config.yaml (Part 20).

### 6. Skills

```bash
for skill in /opt/hermes-optimization-guide/skills/*/*/; do
  ln -sfn "$skill" "/home/hermes/.hermes/skills/$(basename $skill)"
done
hermes /reload
```

## Honest tradeoffs

- **Latency.** Local 70B Q4 ≈ 20–40 tok/s on a 3090. Flagship Sonnet ≈ 60–90 tok/s. Most "work" queries you won't notice; coding/deep reasoning you will.
- **Quality.** Current open/local models (Qwen Coder, Llama, Kimi-class local models) are *close* on many tasks, *behind* on long-context + nuanced reasoning. `/model smart` hands the hard stuff to Sonnet.
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
