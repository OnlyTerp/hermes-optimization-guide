# Reference Architecture: Small Agency

**2–6 devs, multiple clients, per-client isolation.** One Hermes install is hard to scale across a team; this architecture runs a dedicated profile per developer/client and shares only the observability + audit layer.

## Who this is for

- Dev shops / consulting agencies handling multiple client codebases
- Small product teams with strict separation-of-concerns requirements
- Anyone who needs audit trails that hold up to a client security review

## Cost

- **Infra:** ~$25–50/mo (one CX32 or 2× CX22)
- **LLM:** $200–800/mo (routed)
- **Langfuse/observability:** $0 self-host or $100+/mo managed

## Architecture

```
          Devs (Telegram/Discord DMs, CLI)
             │                          │
             ▼                          ▼
     ┌───────────────────┐    ┌───────────────────┐
     │ Hermes per dev/   │    │ Shared services   │
     │ per client        │    │                   │
     │ (systemd units)   │    │  Langfuse         │
     │                   │    │  Audit log sink   │
     │ hermes@alice.s    │    │  LightRAG (each)  │
     │ hermes@bob.s      │    │  backup target    │
     │ hermes@clientA.s  │    │                   │
     └───────────────────┘    └───────────────────┘
```

- **Systemd templated units** — `hermes@<name>.service`, one per dev/client, each with its own `${HOME}/.hermes/` and own approval channel (DM of that dev)
- **LightRAG per instance** — never mix client knowledge
- **Centralized Langfuse + audit log** — every call traced, PII-redacted at the secrets layer

## Parts list

- **1× CX32** (4 vCPU, 8GB RAM) — $12/mo, hosts 3–6 Hermes instances + Langfuse
- **S3/R2 backup bucket** — encrypted nightly backups (age/gpg)
- **Cloudflare** — DNS + TLS-terminated reverse proxy (or Caddy if you prefer not touching CF)
- **Linear/Notion/Slack/Google Workspace** — MCP-wired read-only for context

## Install

1. **Bootstrap the host** as in [Solo Developer](./solo-developer.md).
2. **Replace `hermes.service`** with a templated unit (`hermes@.service`):

```ini
[Unit]
Description=Hermes Agent for %i
After=network-online.target

[Service]
Type=simple
User=%i
WorkingDirectory=/home/%i
ExecStart=/usr/local/bin/hermes run
EnvironmentFile=-/home/%i/.hermes/.env
# ... all the hardening bits from templates/systemd/hermes.service

[Install]
WantedBy=multi-user.target
```

Then:

```bash
# For each dev or client:
adduser --disabled-password --gecos "" alice
sudo -u alice curl -sSL https://install.hermes.nous.ai | bash
cp templates/config/production.yaml /home/alice/.hermes/config.yaml
chown alice:alice /home/alice/.hermes/config.yaml
systemctl enable --now hermes@alice.service
```

3. **Centralize Langfuse** per [Solo Developer](./solo-developer.md#install), then every `config.yaml` points `telemetry.langfuse.host` at the same internal URL. Each profile ships under its own Langfuse project for isolation.

## Per-client separation

- **`profile:`** in the Hermes config — `quarantine` (untrusted input for a public bot) vs `trusted` (the dev's admin DM)
- **Approval channels** — the dev's DM is the only trusted approval source; client support channels are *never* trusted
- **LightRAG dirs** — `~/.hermes/lightrag-<client>/` per client; never mix
- **MCP** — per-client read-only PATs (`GITHUB_PAT_CLIENT_A`, `GITHUB_PAT_CLIENT_B`)
- **Audit log** — append-only JSONL per session, centralized to a single append-only bucket the dev can *read* but not *delete* (makes client reviews easy)

## Cost routing at agency scale

Use [`templates/config/production.yaml`](../../templates/config/production.yaml) as the base. Key rules:

- **Triage** (most traffic): Cerebras Llama 70B — free-ish tier
- **Default coding:** Kimi K2.5 (cheapest competent coder)
- **"Hard" coding / architecture:** Anthropic Sonnet — explicit opt-in
- **Long-context research:** Gemini 2.5 Pro
- **Deep reasoning:** GPT-5.4 (opt-in)

With weekly `cost-report` → Discord ops channel, cost anomalies surface before the invoice.

## Compliance-friendly defaults

- `memory_write_redaction: true` (skip writing secrets to LightRAG)
- `log_redaction: true`
- `security.webhook.max_body_bytes: 524288`
- `security.approval.approval_timeout: 120` — no action sits in pending queue forever
- Nightly backup encrypted with per-client age keys

## When to graduate

- Past ~20 devs → move to a proper Kubernetes setup with per-profile pods, separate Langfuse instances per client
- Regulated industries → self-host the LLM too (vLLM or Ollama on a GPU box)
