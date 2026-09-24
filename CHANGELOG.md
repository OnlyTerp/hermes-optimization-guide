# Changelog

## 2026-09-23 — v2: the guide, rebuilt (Hermes v0.21.4)

The guide was rewritten from scratch and re-pinned from Hermes v0.20.5 (`v2026.8.19`) to **v0.21.4 (`v2026.9.21`)**.

**Why.** The v1 guide grew one release refresh at a time: 30 "parts" with overlapping scope ("Latest Power Moves", "Tenacity Stack", "Power Secrets"), a README that duplicated part content, and a lot of meta-material. It also fell five releases behind and had accumulated claims that were stale or wrong at the current release.

**What's new**

- **16 topic-organized chapters plus a cheat sheet** in [`guide/`](./guide), grouped as foundations, cost and smarts, capabilities, operations, and recipes. One topic lives in one place.
- **Measured, not quoted.** Token and byte figures come from a real v0.21.4 install (`hermes prompt-size` and the same prompt builder counted with a real tokenizer). The defaults: about 13K tokens of fixed prefix per call, 77% of it tool schemas. Disabling `browser` and `tts` saves 2,311 tokens per call. A 32 KB `AGENTS.md` adds 8,609 per call.
- **Findings from the upstream source** that the docs get wrong or leave out: compression effectively fires at **75%** for models under 512K context (not the 50% `hermes config show` prints); auxiliary tasks default to the **main** model; prompt-cache TTL defaults to `5m` and can be turned off; Hermes rejects models under **64K** context; `image_gen` and `computer_use` are already deferred behind tool search.
- **A troubleshooting chapter built from confirmed fixes only.** Each fix is sourced from the official docs, merged PRs, or release notes. Known-unsolved problems are listed as unsolved.
- **A new drift guard** ([`scripts/drift_guard.py`](./scripts/drift_guard.py)). It installs the pinned release and checks every `hermes` subcommand **and flag**, slash command, config key, Hermes env var, and official-docs link **and anchor** in the guide. It also runs upstream's own skill linter over [`skills/`](./skills). A weekly job opens an issue when upstream releases something newer than the pin.
- **Templates and skills rebuilt against v0.21.4.** Config fragments are validated key by key against the schema. Four new operations skills (cost audit, health check, security review, encrypted off-machine backup) have zero findings under the upstream linter. The backup script is shellchecked and tested end to end.

**Corrected from v1** (non-exhaustive)

- `pip install hermes-agent` recommended as an install path. PyPI installs are **unsupported** upstream, and the package is stale (0.19.0).
- The claim that messaging platforms cost "2–3× the CLI" in tool definitions. On defaults, the CLI and Telegram carry identical tool schemas.
- "Compression keeps the first 3 and last 20 turns at an 80% threshold." The real behavior is a lean tail, a 75% floor under 512K, and a 256K cap above.
- `/background`, gateway session auto-reset, per-profile gateways, `sessions.auto_prune` off, `auxiliary.web_extract`, `delegation.max_concurrent_children: 3`, `/usage 7d`, and `hermes approval-check`. All are stale or never existed at v0.21.4.
- Config templates with invented keys and model IDs, and skills calling nonexistent commands (`hermes secrets get`, `security.approval.bypass_subagents`, `telegram.bots`).

**Removed**, all still in git history:

- `part1-*.md` … `part29-*.md` (replaced by [`guide/`](./guide); see the map below)
- `README-zh.md`, `README-ja.md` (they described the v1 structure; translations of v2 are welcome)
- `docs/outreach/` (promotional drafts), `docs/evidence/` (v1 receipts), `docs/wizard/` (config generator for the v0.20 schema), `docs/reference-architectures/` and `docs/quickstart.md` (folded into chapters 02, 14 and 16), `docs/failure-modes.md` (confirmed items folded into chapter 15)
- `benchmarks/` (the harness had one dated run and model IDs from May 2026; no numbers from it are quoted anywhere)
- `scripts/vps-bootstrap.sh` and its release/pin workflows. Upstream now does the risky parts itself (`hermes gateway install --system --run-as-user`). Chapter 14 walks through a VPS with official commands only.
- `scripts/score-your-setup.py` (replaced by the `hermes-cost-audit` and `hermes-security-review` skills, which read the live install through Hermes' own commands)
- `ECOSYSTEM.md`, `ROADMAP.md`, `diagrams/`, and SVG infographics tied to the v1 part structure
- The v1 config templates (`minimum`, `telegram-bot`, `production`, `cost-optimized`, `security-hardened`), replaced by `lean`, `local`, `messaging-bot` and `hardened`. Three of the five set the dead `auxiliary.web_extract`, and several set an explicit `auxiliary.vision`, which silently turns off native vision.
- `templates/systemd/` (the hand-written `hermes.service` matches upstream's legacy-unit detector, and its `kill -HUP` reload stopped the gateway without a drain or restart; use `hermes gateway install`), `templates/caddy/` (a dashboard behind a proxy also needs `dashboard.public_url` and an auth provider; see chapter 14), `templates/compose/` (a third-party Langfuse stack), and `templates/cron/` (folded into chapters 11 and 16)

### Where the v1 parts went

| v1 part | Now in |
|---|---|
| Part 1 Setup · docs/quickstart | [02 Install & First Run](./guide/02-install.md) |
| SOUL.md section · Part 10 SOUL anti-patterns | [06 Personality & Context Files](./guide/06-personality-and-context.md) |
| Part 2 OpenClaw migration | [02 Install](./guide/02-install.md#coming-from-another-agent) |
| Part 7 Memory | [07 Memory](./guide/07-memory.md) |
| Part 3 LightRAG | Dropped: Hermes has no LightRAG integration. [07](./guide/07-memory.md#knowledge-bases) covers the knowledge-base options that do ship. |
| Part 4 Telegram · Part 15 New platforms | [10 Messaging](./guide/10-messaging.md) |
| Part 5 Skills | [08 Skills](./guide/08-skills.md) |
| Part 6 Context compression · Part 20 cost sections · Part 27 cost/cache secrets | [05 Cost & Speed](./guide/05-token-budget.md) |
| Part 8 Subagents · Part 18 Coding agents | [12 Delegation & Multi-Agent](./guide/12-multi-agent.md) |
| Part 9 Custom models · Part 26 MoA | [03 Models & Providers](./guide/03-models.md) |
| Part 25 NVIDIA & local | [04 Local Models](./guide/04-local-models.md) |
| Part 11 Gateway recovery · Part 16 Backup & debug · docs/failure-modes | [14 Running 24/7](./guide/14-production.md), [15 Troubleshooting](./guide/15-troubleshooting.md) |
| Part 12 Dashboard · Part 24 Desktop app | [01 How Hermes Works](./guide/01-how-hermes-works.md), [14 Running 24/7](./guide/14-production.md) |
| Part 13 Tool gateway · Part 17 MCP · Part 21 Remote sandboxes | [09 Tools, MCP & Plugins](./guide/09-tools-mcp-plugins.md) |
| Part 14 Fast mode & watchers · Part 22/23 cron, goals, Kanban | [11 Automation](./guide/11-automation.md), [12 Delegation & Multi-Agent](./guide/12-multi-agent.md) |
| Part 19 Security playbook | [13 Security](./guide/13-security.md) |
| Part 28 Recipe Book · docs/reference-architectures | [16 Recipes](./guide/16-recipes.md) |
| Part 29 Lessons from Production | Confirmed, general lessons folded into [05](./guide/05-token-budget.md), [14](./guide/14-production.md) and [15](./guide/15-troubleshooting.md) |

---

## Before v2 (v1 history, condensed)

- **2026-08-28**: Part 29 "Lessons from Production", seven postmortems, Power Secrets #26–31.
- **2026-08-22**: Refresh to Hermes v0.20.4 "Herald". Receipts, a pinned-tag drift guard, installer hash pinning, three review rounds.
- **2026-07-17**: Part 27 "Power Secrets", Part 28 "Recipe Book", six infographics (v0.18.2 era).
- **2026-07-03**: Accuracy and cross-link pass, anchor checking in CI.
- **2026-07-01**: Hermes v0.17 "Reach" and v0.18 "Judgment" refresh (MoA, `/goal`, `/learn`, iMessage).
- **2026-06-17**: Hermes v0.16 "Surface" refresh (desktop app, NVIDIA/local hardware).
- **2026-06-03 / 05-27**: Security-playbook and routing schema fixes, LightRAG model refresh, ecosystem update.
- **2026-05-25**: Hermes v0.14 refresh (PyPI install, Grok OAuth, `hermes proxy`, Teams, `/handoff`).
- **2026-05-14**: Hermes v0.13 refresh (Kanban, `/goal`, checkpoints v2, no-agent cron).
- **2026-04-30**: Hermes v0.11/v0.12 refresh (Curator, TUI, plugins).
- **2026-04-17**: Config wizard, reference architectures, CI, installable skills and templates, parts 17–21.
- **2026-04-16 and earlier**: The original guide: setup, OpenClaw migration, LightRAG, Telegram, skills (v0.9/v0.10 era).
