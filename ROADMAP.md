# Roadmap

What's landing next. PRs welcome.

## In progress

- [ ] **Interactive config wizard** — a static page that asks 8 questions and emits a `config.yaml` + systemd unit. Hosted via GitHub Pages.
- [ ] **GitHub Pages docs site** — Astro Starlight with full-text search across all parts + skills.
- [ ] **Asciinema cast** — 60-second "zero to working Telegram bot" recording embedded in the README.
- [ ] **Langfuse dashboard JSON** — importable ready-made dashboard for Hermes traces.

## Queued

- [ ] **Skill templates** — `hermes skills new <name>` scaffolding generator
- [ ] **Reference architectures** — homelab / single-user SaaS / small-team / agency, each with every file needed
- [ ] **Integration tests** — GitHub Actions job that lints every SKILL.md frontmatter + validates YAML configs
- [ ] **Cross-link checker** — CI check that fails if any `[...](./...)` link 404s
- [ ] **Translations** — Chinese + Japanese (large Hermes user base in both communities per v0.9 release notes)
- [ ] **"Hermes Weekly"** — markdown-first week-in-review section auto-generated from Hermes-agent merged PRs
- [ ] **Security CVE feed** — `.github/workflows/cve-watch.yml` that monitors OSV for relevant advisories

## Under consideration

- Native Hermes skill pack installable via `hermes skills install onlyterp/hermes-optimization-guide`
- Per-release git tags so users can pin to a known-good state
- Community MCP server incubator — small repo that graduates servers once they hit quality bar

## Done (recent)

- ✅ 2026-04-17 — Installable skill library + templates + bootstrap script
- ✅ 2026-04-17 — MCP / coding-agent / security / observability / sandbox parts (17–21)
- ✅ 2026-04-16 — v0.9 + v0.10 refresh (parts 12–16)

## How to suggest additions

Open an issue with the `roadmap` label. Include:
- What the addition does
- Who it's for
- An estimate of effort (small / medium / large)
- Whether you'd write it yourself
