# Skills

Four operations skills that turn this guide's advice into things Hermes does for you. Each one:

- follows the current `SKILL.md` format and passes Hermes' own skill linter (`tools/skill_linter.py` at v0.21.4) with zero findings, which CI re-checks;
- uses only commands that exist in the pinned release (checked by the [drift guard](../scripts/drift_guard.py));
- reads and reports first, and changes nothing without your approval.

| Skill | What it does | Good as a cron job? |
|---|---|---|
| [`hermes-cost-audit`](./hermes-cost-audit/SKILL.md) | Measures the fixed prompt per platform, reads real spend, finds the settings that cost the most, and proposes cuts with estimated savings | Weekly |
| [`hermes-health-check`](./hermes-health-check/SKILL.md) | Runs Hermes' read-only diagnostics (doctor, status, gateway, cron, logs) and maps each finding to its confirmed fix | Daily, on always-on hosts |
| [`hermes-security-review`](./hermes-security-review/SKILL.md) | Checks approvals, allowlists, secret-file permissions, redaction, and supply chain (`hermes security audit`), rated by severity | Monthly |
| [`hermes-offsite-backup`](./hermes-offsite-backup/SKILL.md) | Sets up nightly `hermes backup` → `age` encryption → off-machine copy, as a **zero-token** cron job that only messages you on failure | It installs its own |

## Install

Install one straight from GitHub. It goes through the same security scan as any community skill and is recorded in the hub lock file, so `hermes skills check` and `hermes skills update` track it:

```bash
hermes skills inspect OnlyTerp/hermes-optimization-guide/skills/hermes-cost-audit   # read it first
hermes skills install OnlyTerp/hermes-optimization-guide/skills/hermes-cost-audit
```

Or copy the folder into your Hermes skills directory (the profile's `skills/` folder):

```bash
git clone https://github.com/OnlyTerp/hermes-optimization-guide.git
cp -r hermes-optimization-guide/skills/hermes-cost-audit ~/.hermes/skills/
```

Then start a new session, or run `/reload-skills` in a running one, and use it:

```text
/hermes-cost-audit
```

For another profile, copy into `~/.hermes/profiles/<name>/skills/` instead.

## Use one on a schedule

```bash
hermes cron create "0 9 * * 1" "Run a cost audit and report the top three savings." \
  --skill hermes-cost-audit --name weekly-cost-audit --deliver telegram
```

A cron job starts with no memory of past chats, so the prompt says what to do and the skill says how. [Chapter 11](../guide/11-automation.md) covers scheduling in depth.

## Writing your own

[Chapter 08](../guide/08-skills.md) covers the `SKILL.md` format, the 60-character description budget for the always-on skill index, and how to keep skills lean.
