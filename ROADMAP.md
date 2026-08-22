# Roadmap

What's landing next. PRs welcome.

## In progress

- [ ] **GitHub Pages docs site** — Astro Starlight with full-text search across all parts + skills.
- [ ] **Asciinema cast** — 60-second "zero to working Telegram bot" recording embedded in the README.
- [ ] **Langfuse dashboard JSON** — importable ready-made dashboard for Hermes traces (retargeted for the Langfuse v4 / OpenTelemetry traces documented in [Part 20](./part20-observability.md)).
- [ ] **Upstream PR** to `NousResearch/hermes-agent` README — add Community Guides section (draft in `docs/outreach/nous-upstream-pr-body.md`), refreshed for the v0.20.4 "Herald" line.

## Queued

- [ ] **Benchmark re-run on the current frontier** — `benchmarks/matrix.yaml` still targets May 2026 IDs and prices (GPT-5.5, Sonnet 5 / Opus 4.7, Kimi K2.6, GLM-5, Grok 4.3). Refresh IDs + prices to the v0.20.4-era plane (GPT-5.6 Sol/Terra/Luna, Claude Opus 5 / 4.8 / Sonnet 5 / Haiku 4.5, Kimi K3, GLM-5.2, MiniMax M3, DeepSeek V4 dated snapshots, Qwen 3.8 Max) and execute `./run.sh` before quoting numbers anywhere.
- [ ] **Translations sync** — `README-zh.md` / `README-ja.md` are pinned to the 2026-07-03 / v0.18.0 state; bring them to the v0.20.4 "Herald" baseline and add a "last synced" stamp.
- [ ] **Skill templates** — `hermes skills new <name>` scaffolding generator
- [ ] **Security CVE feed** — `.github/workflows/cve-watch.yml` that monitors OSV for relevant advisories
- [ ] **Dashboard screenshots pass** — embed actual screens in parts 12 / 17 / 20, including the v0.20 voice (barge-in / wake word) and Bots surfaces

## Under consideration

- Native Hermes skill pack installable via `hermes skills install onlyterp/hermes-optimization-guide`
- Per-release git tags so users can pin to a known-good state
- Community MCP server incubator — small repo that graduates servers once they hit quality bar
- A2A interop build — a worked example of Hermes ↔ Hermes (or Hermes ↔ ADK) agent-to-agent handoff for the Recipe Book
- Voice demo assets — short barge-in / wake-word clips for the desktop voice section of [Part 24](./part24-desktop-app.md)

## Done (recent)

- ✅ 2026-08-22 — **Herald-era refresh (v0.18 → v0.20.4)**: guide baseline moved from v0.18.2 to **v0.20.4 "Herald" (v2026.8.18)**. The July–August wave (v0.19.0 → v0.20.4) is now the guide's current era: streaming TTS with barge-in + wake words, **A2A v1.0** (outbound toolset + inbound platform), **outbound webhooks** with payload filters, **grounded citations**, the desktop platform wave (Bots, multi-connection, memory graph, per-thread drafts), background **computer use** on any model, **egress / iron-proxy** proxy tokens, **external secrets** (Bitwarden / 1Password), and the keyless web tier + **OpenCode Free**. ECOSYSTEM, benchmarks, CONTRIBUTING, and this roadmap realigned to the era.
- ✅ 2026-07-17 — Power Secrets modernization: new Part 27 (Wingtips #1–#22 field manual + cheat sheet), new Part 28 Recipe Book (12 production builds), six new house-style infographics, v0.18.2 / `v2026.7.7.2` currency (Baileys fix, patch-rollup notes), MCP CVE table + checklist, seven-layer security model + spend kernels + action ontology, gateway token tax + stack benchmarking + Langfuse v4/OTEL, seven-rung agent ladder, Kimi K3 / Sol-Terra-Luna routing, Kanban traps, Hermes Cloud (preview), computer use, ecosystem radar
- ✅ 2026-07-03 — Cross-link checker: anchor checking added (CI now fails on dead relative `./partN-foo.md` links *and* dead heading anchors; markdown-link-check shipped 2026-04-17)
- ✅ 2026-07-01 — v0.17 "Reach" + v0.18 "Judgment" refresh: Part 26 MoA / verification / `/learn` + `/journey`, iMessage via Photon Spectrum, WhatsApp Business Cloud, Vertex AI provider, background subagent fan-out, desktop Projects + multi-terminal, gateway scale-to-zero, 25+ platform count, 27-part TOC
- ✅ 2026-06-17 — v0.16 "Surface" refresh: Part 24 Hermes Desktop App, Part 25 NVIDIA & local hardware (DGX Spark / OpenShell / NemoClaw), new banner graphics, `/undo` + default-interface + fuzzy-picker power moves, native Windows installer, `hermes portal` Quick Setup, and a trim of stale per-version model tables to a model-agnostic section
- ✅ 2026-05-25 — v0.14 refresh: PyPI install, Grok OAuth, `hermes proxy`, `x_search`, Teams end-to-end, LINE/SimpleX, `/handoff`, Windows beta, and May 25 model SOTA
- ✅ 2026-05-14 — v0.13 refresh: Kanban, `/goal`, Checkpoints v2, Google Chat, no-agent cron, provider plugins, and May 2026 model SOTA
- ✅ 2026-04-30 — v0.11/v0.12 refresh: Curator, TUI, plugins, Bedrock/Azure/LM Studio, Teams/Yuanbao/QQBot, Vercel Sandbox, Part 22
- ✅ 2026-04-17 — Interactive config wizard (`docs/wizard/`)
- ✅ 2026-04-17 — 4 reference architectures (homelab / solo-dev / small-agency / road-warrior)
- ✅ 2026-04-17 — CI (markdown-link-check + yamllint + skill frontmatter validator)
- ✅ 2026-04-17 — Chinese + Japanese README entry pages
- ✅ 2026-04-17 — Outreach drafts (tweet, HN, Reddit, upstream PR, blog post)
- ✅ 2026-04-17 — Installable skill library + templates + bootstrap script
- ✅ 2026-04-17 — MCP / coding-agent / security / observability / sandbox parts (17–21)
- ✅ 2026-04-16 — v0.9 + v0.10 refresh (parts 12–16)

## How to suggest additions

Open an issue with the `roadmap` label. Include:
- What the addition does
- Who it's for
- An estimate of effort (small / medium / large)
- Whether you'd write it yourself