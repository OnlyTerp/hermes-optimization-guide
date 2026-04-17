# Upstream PR to `NousResearch/hermes-agent` — Draft PR Body

**This is the single highest-leverage move for stars + team respect.** Rob should open this PR themselves — it comes better from a user than from an AI assistant.

---

## Suggested title
`docs: add "Community Guides" section linking external optimization resources`

## Suggested branch name
`docs/community-guides`

## Suggested change

Add a new section to `README.md` (just below "Documentation" or "Quick Start"):

````markdown
## Community Guides

Independent guides written by Hermes users. These are not official, but have been vetted by maintainers for accuracy.

- [Hermes Optimization Guide](https://github.com/OnlyTerp/hermes-optimization-guide) — 21-part guide covering LightRAG, Telegram deployment, MCP, security hardening, cost routing, observability, and remote sandboxes. Ships installable skills, 5 production configs, a VPS bootstrap script, and reproducible cost benchmarks.

_Maintain your own? Open a PR adding it here._
````

## PR body

> Hi Nous team — first, thanks for Hermes, it's been my daily driver for a year.
>
> I've been writing a community optimization guide since v0.9.0 shipped, and have gotten enough "where should I link this so people can find it?" messages that I wanted to propose an upstream spot: a small **Community Guides** section in the README.
>
> The guide itself is at https://github.com/OnlyTerp/hermes-optimization-guide — 21 parts of documentation, 9 installable `SKILL.md` files, 5 production configs, a VPS bootstrap script, and a reproducible cost benchmark. MIT license. CHANGELOG + ROADMAP are real. I cross-check every release note on `main` and update within 72h.
>
> Totally understand if you'd rather maintain a separate page, or curate more carefully before pointing at third-party content. Happy to iterate on the section copy, add more guides as they show up, or even move the list to `docs/community.md` if that fits better.
>
> If there's a better channel for this kind of ask (Discord, an `awesome-hermes` repo, etc.) — just let me know and I'll move there.

## Why this specific shape

- **"Community Guides" (plural)** — signals the section is for anyone, not just this guide. Easier to accept because it's a pattern, not a promo.
- **One-line link with a quality descriptor** — follows the style Nous already uses for integrations. Doesn't read like marketing.
- **Explicit "vetted by maintainers for accuracy"** — puts the burden on the team to do a light review. Removes their fear of linking something that'll get out of date.
- **"Maintain your own? Open a PR adding it here."** — invites contribution. Doesn't feel self-serving.
- **PR body is a user speaking user-to-user** — the Nous team respects builders; show that you've been building.

## What to do if rejected

1. **Ask where the right spot is.** If they say "not in README", ask about `docs/community.md` or a GH topic/tag.
2. **Offer to run an `awesome-hermes` repo** — totally different framing, same destination: people find this guide.
3. **Don't push.** Take the rejection, thank them, keep writing.

## What to do if accepted

1. **Thank them publicly** — quote-tweet / reply in the PR. The Hermes community watches these merges.
2. **Update [this guide's README](../../README.md)** with the upstream link ("Listed in the official Hermes README").
3. **Don't abuse the channel.** Never add other projects to that section in a later PR unless they're comparable-quality and the author opens it themselves.
