# Reference Architecture: Solo Developer

**VPS + phone bot + cost routing.** The 80% setup — cheap, reliable, reachable anywhere, good enough for one person's real work.

## Who this is for

- Developer / maker who wants a Telegram/Discord driver for their daily work
- No ops team; "set it and forget it" is the design goal
- Willing to spend $5–50/mo to not run your own hardware

## Cost

- **Infra:** $5–7/mo (Hetzner CX22 or Fly machine)
- **LLM:** $20–60/mo for typical personal use with cost routing
- **Domain + DNS:** $0–1/mo

**Total: ~$25–70/mo.**

## Architecture

```
  phone/laptop                Internet             hermes.yourdomain.com
       │                         │                         │
       └── Telegram/Discord ─────┼── Cloudflare/Caddy ────→│
                                 │                         │
                                 │                         ├── hermes.service
                                 │                         ├── hermes-dashboard.service
                                 │                         ├── Langfuse (self-host)
                                 │                         └── LightRAG
                                 │
                                 └── Anthropic / Google / Moonshot / Cerebras
```

## Parts list

- **Hetzner CX22** (Debian 12 or Ubuntu 24.04) — $5/mo, 4GB RAM, 2 vCPU
- **Domain** ($12/yr) — or use a free subdomain from duckdns/nip.io
- **Telegram bot token** (free; [@BotFather](https://t.me/BotFather))
- **API keys:** Anthropic (default), Google (Gemini Flash for triage), optionally Moonshot + Cerebras for coding/classification

## Install

```bash
# As root on a fresh VPS
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | bash
```

Then:

```bash
# As root
sudo -u hermes nano ~/.hermes/.env          # fill in keys
sudo cp /opt/hermes-optimization-guide/templates/config/cost-optimized.yaml \
     /home/hermes/.hermes/config.yaml       # or telegram-bot.yaml
sudo cp /etc/caddy/Caddyfile.hermes.reference /etc/caddy/Caddyfile
# edit /etc/caddy/Caddyfile — replace *.yourdomain.com
sudo systemctl reload caddy
sudo systemctl start hermes hermes-dashboard
```

## Why `cost-optimized.yaml` is the right default

See [`templates/config/cost-optimized.yaml`](../../templates/config/cost-optimized.yaml). Defaults to Gemini Flash (cheapest smart model), uses Cerebras Llama for classification (near-free), and only escalates to Sonnet for high-stakes coding. With prompt caching + Fast Mode disabled by default, typical cost is $0.05–0.30 per active hour.

If you need max quality for a specific task, just say "use sonnet" in chat — the router honors explicit user overrides.

## Routines you'll run

Every one of these is installed by the bootstrap script (symlinks into `~/.hermes/skills/`):

- Morning: `/cost-report window=24h` — yesterday's spend
- On idle threads: `/telegram-triage` (autoreply)
- Weekly: `/weekly-dep-audit severity_floor=high`
- Nightly: `/nightly-backup s3://my-backups/hermes/ 30` (or set `remote=local` if you don't care)

## Scaling ceilings

| Constraint | Hit at | Fix |
|---|---|---|
| CX22 RAM | ~5–10 concurrent tool calls + LightRAG | Upgrade to CX32 ($12/mo) |
| Gemini Flash free tier | 1500 req/day | Route to Cerebras or add paid quota |
| LightRAG on 2 vCPU | Indexing 10MB+ docs | Move indexing to a spot Modal sandbox |
| Cost budget | $50+/mo | Turn on `prefer_cached: true` + 32K compression trigger |

## Security note

Because this box is public-facing, **always** deploy the denylist + require_approval from `cost-optimized.yaml`, and keep your Telegram bot **private** (restrict `allowed_user_ids` to your own ID). Any "public" bot should use a separate token and run in a **quarantine profile** — see [Part 19](../../part19-security-playbook.md) and the [`security-hardened.yaml`](../../templates/config/security-hardened.yaml) template.

## When to graduate

- Adding teammates → [Small Agency](./small-agency.md)
- Going offline-first → [Homelab](./homelab.md)
- Wanting a beefy cloud box on-demand → [Road Warrior](./road-warrior.md)
