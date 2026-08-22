# Verification receipts

This directory is the answer to "prove it." Every claim the guide makes about
the Hermes surface — CLI subcommands, in-session slash commands, and config
keys — is backed by machine-verifiable receipts in this folder, and a CI job
(`.github/workflows/drift-guard.yml`) re-checks the whole thing against the
PINNED upstream tag on every push and every Monday.

**Generated:** see `00-generated-at.txt`
**Against:** Hermes Agent **v0.20.5**, upstream `NousResearch/hermes-agent` @ tag **v2026.8.19** (see `06-tag.txt`)

## What's in here

| File | Contents |
|---|---|
| `01-version.txt` | `hermes --version` transcript on the verification machine |
| `02-cli-help.txt` | Full `hermes --help` output (the real command surface) |
| `03-real-commands.txt` | The 72 subcommands parsed out of that help output |
| `04-upstream-commands.txt` | 74 CLI commands extracted from upstream *source* at the pinned tag (builtin + plugin-registered) via `scripts/extract-upstream-surface.py` |
| `05-audit-receipt.txt` | Output of the full audit — CLI subcommands, slash commands, and config keys all clean |
| `06-tag.txt` | The upstream tag this batch was generated against |

## How to reproduce (2 commands)

```bash
python scripts/extract-upstream-surface.py /path/to/hermes-agent --out-dir surface/
python scripts/audit-cli-surface.py --commands-file surface/commands.txt \
  --slash-file surface/slash-commands.txt --config-file surface/config-keys.txt \
  --exit-on-drift
```

Or with Hermes installed: `python scripts/audit-cli-surface.py --exit-on-drift`
(runs `hermes --help` live for the CLI surface).

## What the audit caught (and what we did about it)

**Round 1** (against the "Herald refresh" commit) found **4 fabricated CLI
commands**:

| Fabricated command | Where | Reality |
|---|---|---|
| `hermes bind-thread` | part18 | Never existed — OpenClaw-era carryover. Replaced with the real mechanism (profile pinning + Kanban lanes). |
| `hermes platforms` | part22, part23 | Not a subcommand — the live surface is the `/platforms` slash command. Fixed both. |
| `hermes api-server` | part9 | Not a subcommand — the real backend is `hermes serve` + the `api_server` gateway platform. Fixed. |
| `hermes background` | part3 | Not a CLI subcommand — background processes are started by the agent's terminal tool; guidance rewritten. |

**Round 2** (after extending the audit to slash commands and config keys)
found **4 fabricated slash commands** and **2 bad config references**:

| Fabricated reference | Where | Reality |
|---|---|---|
| `/unbind`, `/runtime` | part18 | Never existed. The ACP story is real but runs the other direction (`hermes acp` — editors drive Hermes). Rewritten. |
| `/switch` | part7 | Real command is `/sessions`. Fixed. |
| `/mouse` | part22 | Real knob is the env var `HERMES_TUI_DISABLE_MOUSE=1`. Fixed. |
| `/billing` | part26 | Real commands are `/topup` + `/subscription`. Fixed. |
| `gateway.platforms.irc.extra` | part15 | Real path is `platforms.irc.extra` (top-level map). Fixed. |
| `prompt_caching.enabled` | README | Real key is `prompt_caching.cache_ttl`. Fixed. |

Two rounds, ten fabrications, zero remaining. That is the residual-AI-drift
risk volume editing carries — this audit exists so the next pass can't ship
them again. **CI now fails on any new one, across all three surfaces.**

## What this does and does not prove

**Proves:** every `hermes <subcommand>`, every `/slash-command`, and every
dotted config key named in the guide's prose, code blocks, and YAML templates
exists in the upstream surface at the pinned tag.

**Does not prove:** that every flag combination runs cleanly, or that prose
descriptions of what a command *does* match its behavior (surface exists ≠
semantics verified). We say this plainly because the alternative — claiming
"fully verified" with receipts that don't actually cover it — is the failure
mode this directory exists to kill.

