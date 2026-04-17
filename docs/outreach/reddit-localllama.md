# r/LocalLLaMA — Post Draft

**Title:** I shipped a Hermes guide with runnable skills, 5 production configs, and a one-command VPS bootstrap

**Flair:** `Resources` or `Tutorial | Guide`

---

## Body

r/LocalLLaMA skews toward people who **run their own stuff**, so I'm posting the `homelab` angle specifically.

I built a Hermes (Nous Research's agent framework) optimization guide that goes beyond docs. Everything's installable — not just explained.

**Repo:** https://github.com/OnlyTerp/hermes-optimization-guide

**What's in it that'll matter to this sub:**

- **Homelab reference architecture** — full setup for running Hermes + LightRAG + self-hosted Langfuse on your own box, with Ollama as the default provider and routing only the hard stuff to Sonnet. Tailscale instead of port-forwarding. Scaling ceilings + honest tradeoffs (latency, quality, etc.) included.

- **5 production config templates** — one of them is `cost-optimized.yaml`, which uses Gemini Flash + Cerebras Llama for most traffic and only escalates to Sonnet on explicit opt-in. Typical spend is $0.05–0.30/active-hour.

- **Reproducible benchmarks** — 12 flagship models × 5 tasks (triage / summarize / codefix / deepreason / bulk-extract), methodology + `hermes evals run` command to reproduce.

- **9 installable skills** (`SKILL.md` files with YAML frontmatter — drop into `~/.hermes/skills/`): audit-mcp, rotate-secrets, audit-approval-bypass, nightly-backup, weekly-dep-audit, cost-report, telegram-triage, pr-review, release-notes.

- **Security playbook** (Part 19) — 7-layer defense against prompt injection, written after the Apr 15 "Comment and Control" attack hit Claude Code + Gemini CLI + Copilot Agent.

- **MCP chapter** (Part 17) — stdio/HTTP transports, 14 servers worth installing today, the trust model, writing your own in 30 lines.

- **Remote sandboxes** (Part 21) — phone-drives-cloud pattern, Modal/Daytona/Fly/E2B. The bulk tar-pipe sync from the Apr 17 Hermes PR is documented.

**One command to go from fresh VPS to working Hermes:**

```bash
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | bash
```

MIT license. CI lints skill frontmatter + YAML + markdown links. CHANGELOG + ROADMAP are real.

If this is useful — a star helps more people find it. If something's wrong, open an issue or PR.
