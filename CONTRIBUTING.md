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

```
.
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md                  ← you are here
├── ECOSYSTEM.md
├── ROADMAP.md
├── LICENSE
├── part1-setup.md … part21-remote-sandboxes.md
├── diagrams/architecture.md
├── skills/
│   ├── README.md
│   ├── security/audit-mcp/SKILL.md
│   ├── security/rotate-secrets/SKILL.md
│   ├── security/audit-approval-bypass/SKILL.md
│   ├── ops/nightly-backup/SKILL.md
│   ├── ops/weekly-dep-audit/SKILL.md
│   ├── ops/cost-report/SKILL.md
│   ├── ops/telegram-triage/SKILL.md
│   ├── dev/pr-review/SKILL.md
│   └── dev/release-notes/SKILL.md
├── templates/
│   ├── config/{minimum,telegram-bot,production,cost-optimized,security-hardened}.yaml
│   ├── compose/langfuse-stack.yml (+ .env example)
│   ├── caddy/Caddyfile
│   ├── systemd/hermes.service + hermes-dashboard.service
│   └── cron/production-crons.yaml
├── scripts/vps-bootstrap.sh
├── benchmarks/README.md + matrix.yaml
└── docs/quickstart.md
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
