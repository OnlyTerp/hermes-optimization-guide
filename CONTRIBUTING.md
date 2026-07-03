# Contributing

This guide is built in public. PRs welcome.

## What's in scope

- ✅ Corrections (docs drift fast — features, prices, PR numbers)
- ✅ New skills under `skills/` (runnable `SKILL.md` files)
- ✅ New config templates under `templates/config/`
- ✅ New MCP / dashboard / tool entries in `ECOSYSTEM.md`
- ✅ Benchmark contributions under `benchmarks/` (with methodology notes)
- ✅ New diagrams in `diagrams/` (Mermaid preferred)
- ✅ Typo fixes, cross-link fixes, formatting

## What's out of scope

- ❌ Marketing content for specific commercial products (ecosystem entries should be *descriptive*, not promotional)
- ❌ Anything relying on private/undocumented Hermes APIs — wait for the public release
- ❌ Code or configs that embed secrets directly

## PR checklist

- [ ] Clear title (`docs:`, `skill:`, `template:`, `bench:`, `fix:` prefixes welcome)
- [ ] For skills: follow the `skills/README.md` structure (frontmatter, procedure, security notes, cron example if applicable)
- [ ] For templates: comment every non-obvious field; include a header explaining what the template is *for*
- [ ] For benchmark entries: include a reproduction command and date of measurement
- [ ] No secrets, even in examples — use `${VAR}` placeholders
- [ ] Cross-links use relative paths (`./partN-foo.md`) so they work in GitHub, VSCode, and future static-site renders

## Repo layout reference

The [README Repo Map](./README.md#repo-map) is the canonical, row-by-row description of every folder. The short version:

```
.
├── README.md (+ README-zh.md, README-ja.md)
├── CHANGELOG.md · ROADMAP.md · ECOSYSTEM.md · CODE_OF_CONDUCT.md · LICENSE
├── CONTRIBUTING.md                  ← you are here
├── part1-setup.md … part26-moa-verification.md   # the 27-part guide (README + 26 part files)
├── skills/                          # 13 installable SKILL.md files under dev/, ops/, security/
├── templates/
│   ├── config/{minimum,telegram-bot,production,cost-optimized,security-hardened}.yaml
│   ├── compose/langfuse-stack.yml (+ .env example)
│   ├── caddy/Caddyfile
│   ├── systemd/hermes.service + hermes-dashboard.service
│   └── cron/production-crons.yaml
├── scripts/vps-bootstrap.sh
├── benchmarks/                      # reproducible 13-model × 5-task matrix
├── diagrams/architecture.md         # 6 Mermaid diagrams
├── assets/ · screenshots/
└── docs/
    ├── quickstart.md
    ├── wizard/                      # interactive config wizard
    ├── reference-architectures/     # 4 blueprints
    └── outreach/
```

## Style notes

- **Plain English over jargon.** Explain *why*, not just *what*.
- **Runnable over explained.** If you can ship a working template or skill alongside a doc section, do.
- **Receipts.** Link PRs, release notes, advisories. Date anything that drifts (prices, benchmarks).
- **Opinionated where it matters.** Saying "Sonnet for coding" beats "here are 7 models, pick one."

## Local preview

Any markdown renderer will do. We test against GitHub's renderer as the source of truth.

```bash
npx -y prettier --check "**/*.md"          # optional, soft style check
npx -y markdown-link-check README.md       # cross-link validation
```

## Code of Conduct

See [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md). TL;DR: be kind, assume good faith, focus on the work.
