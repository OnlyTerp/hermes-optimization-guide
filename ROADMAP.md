# Roadmap

What's landing next. PRs welcome.

## In progress

- [ ] **GitHub Pages docs site** — Astro Starlight with full-text search across all parts + skills.
- [ ] **Asciinema cast** — 60-second "zero to working Telegram bot" recording embedded in the README.
- [ ] **Langfuse dashboard JSON** — importable ready-made dashboard for Hermes traces.
- [ ] **Upstream PR** to `NousResearch/hermes-agent` README — add Community Guides section (draft in `docs/outreach/nous-upstream-pr-body.md`).

## Queued

- [ ] **Skill templates** — `hermes skills new <name>` scaffolding generator
- [ ] **Cross-link checker** — CI check that fails if any `[...](./...)` link 404s (partial: markdown-link-check on modified files is live)
- [ ] **Security CVE feed** — `.github/workflows/cve-watch.yml` that monitors OSV for relevant advisories
- [ ] **Dashboard screenshots pass** — embed actual screens in parts 12 / 17 / 20

## Under consideration

- Native Hermes skill pack installable via `hermes skills install onlyterp/hermes-optimization-guide`
- Per-release git tags so users can pin to a known-good state
- Community MCP server incubator — small repo that graduates servers once they hit quality bar

## Done (recent)

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
