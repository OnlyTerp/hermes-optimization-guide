# Changelog

Dated list of meaningful guide updates. Roughly [Keep a Changelog](https://keepachangelog.com) flavored.

## 2026-06-03 — Part 19 security schema fixes

### Fixed
- **Part 19 — Security Playbook**: rewrote the configuration examples to match
  the real Hermes Agent schema. The previous rev documented a top-level
  `security:` block with `provenance` trust-labeling, `approval.require_approval`
  regex + `denylist`, `approval_channels`, `bypass_subagents`, `secrets.scope` /
  `secrets.env_access`, and a `security.network.egress_allowlist` — **none of
  which exist in Hermes**. Replaced with the actual primitives: top-level
  `approvals:` (`mode: manual|smart|off`, `timeout`, `cron_mode`,
  `mcp_reload_confirm`, `destructive_slash_confirm`), the native
  `tools/approval.py` dangerous-command detector, the always-on
  `UNRECOVERABLE_BLOCKLIST`, `command_allowlist:` (human-readable pattern
  descriptions), `.env` user allowlists (`TELEGRAM_ALLOWED_USERS`,
  `GATEWAY_ALLOWED_USERS`, …) + DM pairing, `security.redact_secrets`, optional
  `security.tirith_*` scanning, automatic credential scoping for subprocesses,
  `terminal.backend` isolation, and `mcp_servers.<name>.tools.include/exclude`.
  Added the SECURITY.md framing that OS-level isolation (terminal-backend or
  whole-process wrapping via Docker/Compose or NVIDIA OpenShell — where real
  network egress control lives) is the only boundary; in-process controls are
  heuristics. Resolves [#19](https://github.com/OnlyTerp/hermes-optimization-guide/issues/19).

## 2026-05-27 — LightRAG model setup refresh

### Changed
- Updated the LightRAG setup examples in `part3-lightrag-setup.md` and the
  combined `README.md` to use current model endpoints: Kimi K2.6 via the
  international Moonshot API (`https://api.moonshot.ai/v1`) for quality,
  Cerebras `gpt-oss-120b` for speed, Fireworks Qwen3-Embedding-8B for
  embeddings, and local Ollama as the free/private option. This replaces the
  stale PR #1 examples that referenced `kimi-2.5`, the China-only
  `api.moonshot.cn` endpoint, and deprecated Cerebras `qwen-3-32b`.

## 2026-05-27 — Ecosystem Directory Update

### Added
- Hermes Tweet native plugin entry in `ECOSYSTEM.md`, applied onto current
  `main` without reverting newer MCP / coding-agent ecosystem entries.

## 2026-05-27 — Part 20 routing schema fixes

### Fixed
- **Part 20 — Cost Routing Playbook**: rewrote Rules 1, 2, 2B, 3, 4, 5 and the
  Langfuse / OTel / eval sections to match real Hermes config keys. The
  previous rev described an `intent`/`complexity`/`match`-based
  `model_routing:` DSL, a `prompt_caching:` allow-list, a `telemetry: spans:`
  block, a `fast_mode:` config block, `compression.auto.*` keys, an `alerts:`
  block, an `observability: langfuse:` block, an `observability: otel:`
  block, and a `hermes evals` subcommand — none of which exist in Hermes.
  Replaced with the actual primitives: `auxiliary:` per-task models,
  `provider_routing:` for OpenRouter, `hermes fallback` for failover, real
  `prompt_caching: cache_ttl:`, real `compression:` keys
  (`enabled`/`threshold`/`target_ratio`/`protect_last_n`), the `/fast` slash
  command, `HERMES_LANGFUSE_*` env vars, and standard `OTEL_*` env vars.
  Resolves [#13](https://github.com/OnlyTerp/hermes-optimization-guide/issues/13).
  Also notes that `smart_model_routing` was removed upstream in commit
  `424e9f36b` (#12732) so readers don't try to bring it back.

## 2026-05-25 — Hermes v0.14.0 Foundation Refresh

### Added
- v0.14 Foundation coverage: PyPI install path, lighter lazy-dependency installs, `hermes proxy`, `x_search`, `/handoff`, SuperGrok OAuth, Grok 4.3 1M context, and native Windows beta
- Part 13 sections for the OpenAI-compatible local proxy and first-class X search
- Part 15 coverage for Teams end-to-end, LINE, and SimpleX Chat, bringing gateway guidance to 22+ platforms
- Part 18 May 25 coding-agent update notes for Claude Code Week 20+, Codex v0.133+, Gemini CLI v0.43, Zed ACP Registry, and proxy-backed Aider/Cline/Continue

### Changed
- README badges, “What's New,” quickstart/setup copy, platform counts, localized README summaries, roadmap, and outreach drafts now target Hermes v0.14.0 (v2026.5.16)
- Part 9 model/provider guidance refreshed for May 25 SOTA: Grok 4.3, SuperGrok OAuth, OpenRouter/Nous live catalogs, Claude Sonnet 5 / Opus 4.7, GPT-5.5, Gemini 3.1, Kimi K2.6, GLM-5, DeepSeek V4, Qwen3.6, and current routing defaults
- Config templates, wizard defaults, benchmark matrix, and reference architectures use current model identifiers and Cerebras Qwen 3 instead of older Llama/GPT-4.1/Gemini 2.5 framing
- Part 23 reframed from v0.13-only Tenacity guidance to the current Foundation + Tenacity operating stack

### Removed
- v0.13-as-current framing from top-level guidance
- Stale “Native Windows unsupported,” “20+ platforms,” Cerebras Llama 70B, GPT-4.1, and Gemini 2.5 recommendations where v0.14/May 25 defaults supersede them

## 2026-05-14 — Hermes v0.13.0 Tenacity Refresh

### Added
- **Part 23 — Tenacity Stack** covering durable Kanban boards, worker lanes, `/goal`, Checkpoints v2, no-agent cron, provider plugins, and the v0.13 upgrade checklist
- Google Chat coverage in Part 15 as the 20th messaging platform
- Kanban worker-lane guidance in Part 18 for Codex/Claude/Gemini/OpenCode orchestration
- v0.13 security-default guidance in Part 19: redaction on by default, guild-scoped Discord role allowlists, WhatsApp stranger rejection, and OAuth/auth.json TOCTOU fixes

### Changed
- README badges, "What's New", table of contents, architecture copy, and model tables now target Hermes v0.13.0 (v2026.5.7)
- Part 9 model/provider guidance updated for May 2026 SOTA: Claude Sonnet 5 / Opus 4.7, GPT-5.5, Gemini 3.1, Kimi K2.6, DeepSeek V4, Qwen3.6, provider plugins, and media routing
- Part 12 updated for dashboard Kanban/profile coverage
- Part 14 updated for `/goal`
- Part 16 updated for v0.13 debug/redaction language
- Part 20 updated for Kanban-aware observability
- Config templates, cron templates, benchmarks, localized READMEs, roadmap, outreach copy, and wizard defaults refreshed for the 24-part guide

### Removed
- v0.12-as-current framing from top-level guidance
- Stale April 2026 model recommendations where May 2026 replacements are now the better default

## 2026-04-30 — Hermes v0.11/v0.12 Refresh

### Added
- **Part 22 — Latest Power Moves** covering Curator, TUI steering habits, context-file hygiene, plugins, auxiliary models, cron chaining, and the v0.12 upgrade checklist
- Curator guidance in Part 5, including dry-run, scheduling, pin/archive behavior, and how it differs from skills/memory/context files
- v0.12 platform coverage for QQBot, Tencent Yuanbao, and Microsoft Teams as a plugin-shipped gateway
- AWS Bedrock, Azure AI Foundry, LM Studio, GMI Cloud, Tencent TokenHub, MiniMax OAuth, Gemini OAuth, and remote model catalog notes in Part 9
- Vercel Sandbox coverage in Part 21

### Changed
- README "What's New" now reflects landed v0.11.0 and v0.12.0 releases instead of speculative post-v0.10 PR tracking
- Part 12 updated for dashboard Chat, Models tab, plugins, Curator controls, and `web,pty` install requirements
- Part 14 updated for `/steer`, `/queue`, `/background`, `/busy`, and current Fast Mode language
- Part 18 updated for orchestrator-role subagents and file coordination
- Part 19 updated with MCP/plugin/dashboard threat surfaces and v0.12 hardline block guidance
- Part 20 updated to prefer the bundled Langfuse observability plugin and auxiliary routing

### Removed
- Stale "Cooking on main" framing and example.com disclosure placeholder
- Old Gemini CLI install requirement for Gemini OAuth

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
