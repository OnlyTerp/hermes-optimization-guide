# Contributing

Corrections are the most valuable thing you can send. Hermes ships several releases a month, and every one of them can make a sentence in this guide wrong.

## The three rules

1. **Verify against the pinned release.** The guide is pinned to one Hermes release (see the badge in the [README](./README.md)). Any `hermes` command or flag, slash command, config key, toolset name, or env var you add must exist in that release. Run the drift guard before opening a PR (commands below). It catches most mistakes.
2. **Measure, don't guess.** Numbers (tokens, bytes, latencies, costs) must be measured on a real install and say how (`hermes prompt-size`, `/context`, `hermes insights`), or come from a cited source. No invented benchmarks, and no prices quoted from memory.
3. **Cite fixes.** Troubleshooting fixes need a source: an official docs page, a merged upstream PR or closed issue, or release notes. Anecdotes go in an issue for discussion, not in the guide. Problems with no confirmed fix belong under "known open problems", labeled as such.

## Style

Match the existing chapters: direct, second person, opinionated. Each chapter opens with a one-line promise and a TL;DR, and ends with "Verify it", "Gotchas" (confirmed traps only), and "Go deeper" (official docs links). Prefer tables for comparisons and short verified snippets for config. Link to the official docs for exhaustive reference instead of copying them. Avoid hype words ("supercharge", "seamless", "robust", "game-changer").

## Run the checks locally

```bash
# once: install the pinned Hermes release into a throwaway venv
git clone --depth 1 --branch v2026.9.21 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-agent
python3 -m venv /tmp/venv && /tmp/venv/bin/pip install -e /tmp/hermes-agent pyyaml

# every change
/tmp/venv/bin/python scripts/drift_guard.py extract --upstream /tmp/hermes-agent --out /tmp/surface.json
/tmp/venv/bin/python scripts/drift_guard.py check --surface /tmp/surface.json
/tmp/venv/bin/python scripts/drift_guard.py lint-skills --upstream /tmp/hermes-agent
python3 .github/scripts/check_anchors.py
```

If the drift guard flags something you're sure is real, show where it lives in the upstream source or docs in your PR, and we'll teach the guard about it. Please don't rephrase just to get past the check. Escape hatches exist for legitimate non-Hermes content:

- `<!-- drift-guard: ignore -->` on the line before a fenced block, for non-Hermes YAML such as compose files;
- `<!-- drift-guard: ignore-line -->` on a line that deliberately shows something invalid (for example the myths table).

## Bumping the pin to a new Hermes release

1. Read the release notes for every tag between the pin and the target.
2. Change `HERMES_TAG` in [`.github/workflows/drift-guard.yml`](./.github/workflows/drift-guard.yml), the "Verified against" badge and line in the README, and the tag in the commands above, all in one commit.
3. Fix everything the drift guard reports, then re-measure any numbers in the chapters the release touched.
4. Add a CHANGELOG entry.

## Skills and templates

- **Skills** go in `skills/<name>/SKILL.md`. The name must match the folder, the description must fit 60 characters, and there must be a `## When to Use` section. `lint-skills` must report zero findings. Skills should read and report first and change nothing without approval. Scripts must pass `shellcheck`.
- **Config templates** go in `templates/config/`. Every key must pass the drift guard, every non-obvious line gets a comment, and the header says what the template is for and which chapter explains it. `hardened.yaml` is the YAML block under "A hardened profile" in chapter 13, so change both together.

## Scope

In scope: corrections, new confirmed fixes, better measurements, clearer explanations, new recipes built from verified features, and translations of the current guide.

Out of scope: promotion of commercial products, anything that relies on undocumented internals, and secrets in any example (use placeholders).
