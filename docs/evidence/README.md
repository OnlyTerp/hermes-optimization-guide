# Verification receipts

This directory is the answer to "prove it." Every claim the guide makes about
the Hermes CLI surface is backed by machine-verifiable receipts in this folder,
and a CI job (`.github/workflows/drift-guard.yml`) re-checks the whole thing
against the live upstream repo on every push and every Monday.

**Generated:** see `00-generated-at.txt` (2026-08-22T11:38:46Z for this batch)
**Against:** Hermes Agent v0.20.4 (2026.8.18), upstream `NousResearch/hermes-agent` @ `fc9cbc87` (2026-08-21), 162 commits behind upstream tip at verification time

## What's in here

| File | Contents |
|---|---|
| `01-version.txt` | `hermes --version` transcript on the verification machine |
| `02-cli-help.txt` | Full `hermes --help` output (the real command surface) |
| `03-real-commands.txt` | The 72 subcommands parsed out of that help output |
| `04-upstream-commands.txt` | 74 commands extracted from upstream *source* (builtin + plugin-registered) via `scripts/extract-upstream-commands.py` |
| `05-audit-receipt.txt` | Output of `scripts/audit-cli-surface.py --exit-on-drift` — 51 distinct commands referenced by the guide, **0 missing from the real CLI** |

## How to reproduce (2 commands)

```bash
python scripts/extract-upstream-commands.py /path/to/hermes-agent --output real.txt
python scripts/audit-cli-surface.py --commands-file real.txt --exit-on-drift
```

Or with Hermes installed: `python scripts/audit-cli-surface.py --exit-on-drift`
(runs `hermes --help` live).

## What the audit caught (and what we did about it)

Running this audit against the "Herald refresh" commit found **4 fabricated
commands** that had slipped through AI-assisted editing:

| Fabricated command | Where | Reality |
|---|---|---|
| `hermes bind-thread` | part18 | Never existed — OpenClaw-era carryover. Replaced with the real mechanism (profile pinning + Kanban lanes). |
| `hermes platforms` | part22, part23 | Not a subcommand — the live surface is the `/platforms` slash command. Fixed both. |
| `hermes api-server` | part9 | Not a subcommand — the real backend is `hermes serve` + the `api_server` gateway platform. Fixed. |
| `hermes background` | part3 | Not a CLI subcommand — background processes are started by the agent's terminal tool; guidance rewritten. |

Two of these were introduced by the refresh itself, two were inherited. That is
exactly the residual-AI-drift risk a volume edit carries — this audit exists so
the next pass can't ship them again. **CI now fails on any new one.**

## What this does and does not prove

**Proves:** every `hermes <subcommand>` named anywhere in the guide's code
blocks and inline code exists in the real CLI, and the help output matches.

**Does not prove:** that every YAML key in every template round-trips through
the config loader, or that every flag combination runs cleanly. Config-key
verification is tracked in the [issue tracker](../../issues) — the drift-guard
covers command surface today; schema coverage is the next layer. We say this
plainly because the alternative — claiming "fully verified" with receipts that
don't actually cover it — is the failure mode this directory exists to kill.
