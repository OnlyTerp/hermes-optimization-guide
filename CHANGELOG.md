# Changelog

Dated list of meaningful guide updates. Roughly [Keep a Changelog](https://keepachangelog.com) flavored.

## 2026-04-17 — Wizard + Reference Architectures + CI

### Added
- **`docs/wizard/index.html`** — interactive static config wizard; 8 questions → ready-to-drop `config.yaml`, runs entirely in the browser (GitHub Pages friendly)
- **`docs/reference-architectures/`** — 4 full blueprints: Homelab, Solo Developer, Small Agency, Road Warrior
- **`docs/outreach/`** — launch-ready drafts: launch tweet thread, Hacker News post, r/LocalLLaMA post, upstream PR body to `NousResearch/hermes-agent`, long-form blog post
- **4 new skills**: `ops/daily-inbox-triage`, `ops/hermes-weekly`, `security/spam-trap`, `dev/meeting-prep` (total skills: 13)
- **CI** — `.github/workflows/ci.yml`: markdown-link-check, yamllint, skill-frontmatter validator (`validate_skills.py`), prettier advisory
- **Localized READMEs** — [`README-zh.md`](./README-zh.md), [`README-ja.md`](./README-ja.md) (entry-level summaries)

### Changed
- README: skills badge 9→13, language links, repo map rows for wizard + reference architectures + outreach, CI badge
- `templates/config/*.yaml` — quoted `${VAR}` env-var substitutions inside flow mappings so every template is valid YAML

## 2026-04-17 — Installable Artifacts

### Added
- **`skills/`** — 9 runnable `SKILL.md` files (audit-mcp, rotate-secrets, audit-approval-bypass, nightly-backup, weekly-dep-audit, cost-report, telegram-triage, pr-review, release-notes)
- **`templates/config/`** — 5 opinionated configs (minimum, telegram-bot, production, cost-optimized, security-hardened)
- **`templates/compose/langfuse-stack.yml`** — self-hosted Langfuse v3 with ClickHouse + MinIO + Redis
- **`templates/caddy/Caddyfile`** — reverse-proxy + auto TLS reference
- **`templates/systemd/`** — hardened `hermes.service` + `hermes-dashboard.service`
- **`templates/cron/production-crons.yaml`** — all recommended scheduled tasks
- **`scripts/vps-bootstrap.sh`** — fresh Hetzner CX22 → production Hermes in ~10 minutes
- **`diagrams/architecture.md`** — 6 Mermaid diagrams (top-level, MCP, delegation, sandbox sync, observability, security)
- **`benchmarks/README.md` + `matrix.yaml`** — reproducible cost/latency table across 12 models × 5 tasks
- **`ECOSYSTEM.md`** — canonical directory of MCP servers, coding agents, dashboard plugins, observability tools
- **`ROADMAP.md`** — what's coming next; invites contribution
- **`CONTRIBUTING.md`**, **`CHANGELOG.md`**, **`CODE_OF_CONDUCT.md`** — standard repo hygiene
- **GitHub issue + PR templates**
- **`docs/quickstart.md`** — 5-minute copy-paste from zero to working Telegram bot

### Changed
- README gained badges, "Install everything" section, architecture diagram embed, ecosystem/benchmarks cross-links

## 2026-04-17 — 72h Research Sweep (PR #6, merged)

### Added
- Part 17 — MCP Servers
- Part 18 — Delegating to Coding Agents (Claude Code, Codex, Gemini CLI, OpenCode, Aider)
- Part 19 — Security Playbook (defenses against the April 15 "Comment and Control" prompt injection)
- Part 20 — Observability & Cost Control (Langfuse, Helicone, Phoenix)
- Part 21 — Remote Sandboxes & Bulk File Sync (#8018)
- README "Pick Your Path" decision tree
- README "Cooking on `main`" section (post-v0.10 PRs)

### Changed
- Part 9 — Flagship Model Cheat Sheet, Task Routing cheat sheet, Gemini CLI OAuth, Gemini TTS
- Cross-links added in parts 3, 5, 8

## 2026-04-16 — Hermes v0.9 + v0.10 refresh (PR #5, merged)

### Added
- Part 12 — Web Dashboard (`hermes dashboard`)
- Part 13 — Nous Tool Gateway
- Part 14 — Fast Mode + Background Watchers + pluggable context engine
- Part 15 — New platforms (iMessage, WeChat, Android/Termux) — 16-platform total
- Part 16 — Backup / Import / `/debug` bundler

### Changed
- README TOC bumped from 11 → 17
- Part 4 Telegram reframed as "flagship of 16 gateways"
- Part 9 native-adapter matrix added

## Earlier

- Initial 11-part guide covering setup, OpenClaw migration, LightRAG, Telegram, skills, context compression, memory, subagents, custom models, SOUL anti-patterns, gateway recovery.
