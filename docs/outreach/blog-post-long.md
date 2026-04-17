# Blog Post — "I got tired of AI agent guides that don't ship code"

**Format:** ~1500 words, dev.to / Substack / personal blog
**Tone:** first person, opinionated, receipts-forward

---

## I got tired of AI agent guides that don't ship code

I use [Hermes](https://github.com/NousResearch/hermes-agent) every day. Telegram is my CLI, my code editor, my inbox triager, my PR reviewer. After a year of running it across a homelab, a Hetzner VPS, and a roster of client boxes, I noticed something frustrating about the existing guides.

**They don't ship anything.**

They explain the architecture. They compare model pricing. They link to Anthropic's prompt caching docs. Then they end — and you still have to write your own `config.yaml`, your own cron skills, your own systemd hardening, your own security playbook, your own observability stack, your own routing logic.

If you've ever tried to stand up an agent framework for real, you know the middle 60% — between "quickstart works" and "this is running in production" — is where every guide I've ever read gives up.

So I wrote the opposite.

---

## What "ships code" means

The [Hermes Optimization Guide](https://github.com/OnlyTerp/hermes-optimization-guide) has 21 chapters of documentation. That's the part that looks like every other guide.

But it also has, in the same repo:

- **9 installable `SKILL.md` files.** Not examples. Not snippets. Actual files with YAML frontmatter, procedure sections, and security notes. You drop them into `~/.hermes/skills/` and they work.
- **5 opinionated production configs.** `minimum`, `telegram-bot`, `production`, `cost-optimized`, `security-hardened`. One `cp` to `~/.hermes/config.yaml` and you have a working deployment. Every non-obvious field is commented.
- **A VPS bootstrap script.** Fresh Hetzner CX22 to hardened production Hermes in one `curl | bash`. Caddy + UFW + fail2ban + systemd + skill symlinks + unattended-upgrades.
- **Reproducible benchmarks.** 12 flagship models × 5 canonical tasks, with the methodology, the dates, the exact reproduction command. Not vibes.
- **4 reference architectures.** Homelab, Solo Developer, Small Agency, Road Warrior. Each with a full parts list, cost line-items, install commands, and scaling ceilings.
- **A static config wizard.** 8 questions → a ready-to-drop `config.yaml`. Runs in your browser. Nothing uploaded.

It feels obvious, written out like this. But look around. Nobody's doing it.

---

## Why the guides keep stopping at "documentation"

My theory: writing docs is *cheap*. Writing docs that ship working artifacts is *expensive* and *awkward*.

You have to actually deploy Hermes. Actually test the Caddy config on a real VPS. Actually run the nightly backup and have it fail at 3am and figure out why. Actually get prompt injection'd and write the lesson up.

Most guides stop before that because their authors never did the work, or did it and never wrote it up because "it's just config, nobody cares".

**People care.** The most-starred AI repos aren't the ones with the best prose. They're the ones where you `git clone && npm install && npm start` and something real happens. The guide version of that is: reader forks the repo, copies five files, and has a working agent 10 minutes later.

---

## The routing playbook that drops cost ~90%

This one gets its own section because it's the part readers care most about.

The default advice on cost is "use cheaper models". But you can't just set `default: gpt-5.4-mini` — for certain tasks (nuanced reasoning, long-context analysis, hard coding) it will silently hurt quality and you'll blame the framework.

Here's what actually works, derived from our benchmarks:

1. **Triage** (~60% of traffic for a personal bot): Gemini 2.5 Flash. Cheap, fast, 1M context. Routes to the right skill or punts to the right model.
2. **Classification** (tagging, routing, spam-trap): Cerebras Llama 70B on a free tier. Effectively zero cost.
3. **Default coding:** Kimi K2.5. Cheapest competent coder, good for 80% of changes.
4. **Hard coding / architecture:** Anthropic Sonnet 4.5. Opt-in (say "use sonnet" or mark the skill with `model: anthropic/claude-sonnet-4-5`).
5. **Long-context research:** Gemini 2.5 Pro. 1M context + reasoning.

With prompt caching on (Anthropic, OpenAI), `prefer_cached: true` as a default, and Fast Mode *off* unless you explicitly need it — the typical user month drops from $150 to $20–40.

The full playbook is in Part 20 of the guide, and the benchmarks are in `benchmarks/`.

---

## The security playbook nobody wanted to write

On April 15, 2026, researchers disclosed "Comment and Control" — a prompt-injection attack that hit Claude Code, Gemini CLI, and Copilot Agent simultaneously. If you run a coding agent that reads GitHub PR bodies or issue comments, you were affected until you patched.

The fact that this hit *three vendor agents* on the same day, with the same vector, is the single most important thing to internalize about this era: **your agent is only as safe as the least-trusted input it processes.**

So Part 19 of the guide is the 7-layer defensive playbook:

1. **Provenance labels.** Every input carries a trust level. Nothing from email / public Telegram / PR bodies is ever treated as instruction unless the user confirms.
2. **Approval gates on the write side.** Reads free, writes approved.
3. **Secret isolation.** API keys live in env files with 0600 perms, redacted in logs, never written to memory.
4. **Webhook signatures.** Stripe-style HMAC verification, rejected at the gateway.
5. **SSRF denylist.** 169.254.169.254 and friends.
6. **MCP trust levels.** Sampling disabled by default for every server; explicit opt-in per server.
7. **Quarantine profile.** Public-facing bot runs as a separate Hermes profile with no MCPs, no memory, no approval chain.

If you run agents in production, read Part 19 before reading anything else.

---

## The real answer to "why this exists"

I wrote this because I was the intended reader. I needed it, couldn't find it, built it.

The open secret is that almost everyone writing in AI right now is in the same spot. The field is moving too fast for the field to document itself. Every framework has a 30-page docs site from 6 months ago and a Discord full of people asking the same 20 questions.

A guide that's *actually maintained* (CHANGELOG is live, every release gets a 72h refresh pass) and *actually runnable* (skills install, configs work, scripts execute) is — and this is the strange part — still rare.

The fix isn't to write better prose. It's to commit working code to the repo next to the docs.

---

## If you run Hermes

- Fork [the guide](https://github.com/OnlyTerp/hermes-optimization-guide), steal the parts you need, contribute back what's missing.
- If a skill or config is wrong for your setup, open an issue. I'd genuinely rather hear "this broke" than have 1000 silent forks.
- Star the repo if it saved you time — GitHub's discovery model is still basically popularity-as-recommendation.

## If you run any other agent framework

- The *pattern* transfers directly. Installable skill files, opinionated configs, bootstrap script, 4 reference architectures, reproducible benchmarks, security playbook.
- If you port this to your framework and want me to link it, open a PR to the `ECOSYSTEM.md` file or to Community Guides.

## If you're writing AI documentation

- Stop stopping at "documentation". Ship what readers need to *run*.
- One skill file, one config, one bootstrap script — all easier to write than you think, all more valuable than the next blog post.

---

*Find the guide at https://github.com/OnlyTerp/hermes-optimization-guide. MIT license, contributions welcome.*
