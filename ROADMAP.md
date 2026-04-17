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
