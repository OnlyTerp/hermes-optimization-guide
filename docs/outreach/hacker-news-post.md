# Hacker News — Show HN Draft

**Title:** Show HN: Hermes Optimization Guide – runnable skills, configs, and VPS bootstrap

**URL:** `https://github.com/OnlyTerp/hermes-optimization-guide`

**Text:** (leave empty — HN prefers URL-only "Show HN" posts when the linked page speaks for itself; first self-comment below carries the context)

---

## First self-comment (post immediately after)

Author here. Context on what this is and why:

Hermes (Nous Research, ~94K GH stars) is the agent framework I've been using for a year. Most of the existing community guides explain the architecture but don't give you anything to run — you read 15 parts, still have to write your own `config.yaml`, your own cron skills, your own systemd hardening.

This guide is the other direction: 21 parts of actual documentation *plus*

- **9 installable `SKILL.md` files** (audit-mcp, rotate-secrets, nightly-backup, weekly-dep-audit, cost-report, telegram-triage, pr-review, release-notes, audit-approval-bypass) — drop them into `~/.hermes/skills/` or symlink them in
- **5 opinionated configs** for the 5 real personas (minimum / telegram-bot / production / cost-optimized / security-hardened) — every non-obvious field commented
- **A VPS bootstrap script** — fresh Debian/Ubuntu to production Hermes with Caddy + UFW + fail2ban + systemd hardening in ~10 min, one `curl | bash`
- **Docker compose for self-hosted Langfuse** — the single most-asked-for observability setup
- **4 reference architectures** — Homelab, Solo Dev, Small Agency, Road Warrior (phone-drives-cloud-sandbox pattern from the new remote-sandbox PR)
- **Reproducible cost benchmarks** — 12 flagship models × 5 canonical tasks (triage / summarize / codefix / deepreason / bulk-extract), methodology included, rerun-able with `hermes evals run`
- **ECOSYSTEM.md** — 40+ curated MCP servers / coding agents / dashboard plugins

The part I wanted to share specifically for HN: the **cost routing playbook** (Part 20) — five rules that drop typical agent spend ~90% (Gemini Flash for triage, Cerebras Llama for classification, Kimi K2.5 as default coder, Sonnet only when you explicitly opt in, Gemini 2.5 Pro for long-context). The benchmarks folder lets you verify yourself on your own workload.

And the **defensive security playbook** (Part 19) — written after the Apr 15 "Comment and Control" cross-vendor prompt-injection disclosure that hit Claude Code + Gemini CLI + Copilot Agent. Seven layers: provenance labels, approval, secret isolation, webhook signatures, SSRF, MCP trust levels, quarantine profiles. If your coding agent reads arbitrary PR bodies or emails, this is the hardening posture I wish I'd had 6 months ago.

MIT licensed. Issues + PRs welcome. Happy to answer anything.
