# Launch Tweet Thread — Draft

**Tone:** matter-of-fact, receipts-forward, no hype language. Replace `@OnlyTerp` / repo URL as needed.

---

**1/8**
I got tired of Hermes guides that explain the architecture but don't give you anything to run, so I shipped the opposite:

21 parts of documentation **plus** 13 installable skills, 5 production configs, 4 reference architectures, a VPS bootstrap script, hardened systemd units, a reproducible cost benchmark, and an in-browser config wizard.

github.com/OnlyTerp/hermes-optimization-guide

---

**2/8**
The 5 configs: `minimum`, `telegram-bot`, `production`, `cost-optimized`, `security-hardened`.

Each one is a single `cp` into `~/.hermes/config.yaml`. They're opinionated — not generic starters — and every field is commented.

`templates/config/`

---

**3/8**
Every skill the guide promises — audit-mcp, rotate-secrets, nightly-backup, weekly-dep-audit, cost-report, telegram-triage, pr-review, release-notes, audit-approval-bypass — is a real runnable `SKILL.md`.

```bash
hermes skills install github://OnlyTerp/hermes-optimization-guide/skills/ops/nightly-backup
```

---

**4/8**
One command from fresh Hetzner CX22 → working hardened production Hermes:

```bash
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | bash
```

Caddy + UFW + fail2ban + systemd + unattended-upgrades + skill symlinks. ~10 min.

---

**5/8**
MCP (Model Context Protocol) went viral last week. The guide has a full chapter — stdio/HTTP transports, 14 servers worth installing, `sampling/createMessage`, trust model, troubleshooting.

The ecosystem directory (ECOSYSTEM.md) links 40+ MCP servers + coding agents + dashboard plugins.

---

**6/8**
The Apr 15 "Comment and Control" cross-vendor prompt-injection attack hit Claude Code + Gemini CLI + Copilot Agent.

Part 19 is the defensive playbook: 7 layers (provenance, approval, secret isolation, webhook sigs, SSRF, MCP trust, quarantine). If your agent reads your inbox, please read this one.

---

**7/8**
Cost routing playbook (Part 20) drops a typical workload by ~90%:
- Triage → Gemini Flash or Cerebras
- Classification → Cerebras Llama (~free)
- Default coding → Kimi K2.5
- Hard coding → Sonnet (explicit opt-in)
- Long context → Gemini 2.5 Pro

Benchmarks + methodology in `benchmarks/`.

---

**8/8**
Everything's MIT-licensed, `CONTRIBUTING.md` is real, CI lints skill frontmatter + YAML + markdown links, and there's a ROADMAP.

If this saves you an afternoon, a star helps more people find it. Issues + PRs welcome.

github.com/OnlyTerp/hermes-optimization-guide

---

## Replies / follow-ups to prep

- "Why not [other framework]?" → I'm not trying to push Hermes; this guide was a need *because* we run Hermes. The config-wizard + skill pattern is copy-able for any agent framework.
- "Does this work with local models?" → Yes. `homelab` reference architecture covers Ollama routing. See `docs/reference-architectures/homelab.md`.
- "Will you maintain it?" → CHANGELOG + ROADMAP are live. Bus factor = 1 right now, actively looking for co-maintainers.
