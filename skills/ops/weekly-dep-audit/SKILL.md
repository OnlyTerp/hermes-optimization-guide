---
name: weekly-dep-audit
description: Audit dependencies across configured repos for security advisories, open triage issues
when_to_use:
  - Scheduled weekly
  - After a viral CVE disclosure
  - Before a production release
toolsets:
  - delegate_task
  - github
parameters:
  repos:
    type: array
    description: List of owner/repo entries to audit. Defaults to all repos with a `hermes-audit` topic.
    default: []
  severity_floor:
    type: string
    enum: [low, medium, high, critical]
    default: high
---

# weekly-dep-audit — Cross-Repo Dependency Audit

Uses Gemini 2.5 Pro's 1M context to ingest entire lockfiles + advisory databases and report actionable findings.

## Procedure

1. **Resolve repos.** If `repos:` is empty, query GitHub for repos the calling user owns with the `hermes-audit` topic (via `github` MCP). Otherwise use the provided list.

2. **For each repo, pull the relevant lockfile(s):**
   - `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock`
   - `uv.lock` / `poetry.lock` / `Pipfile.lock` / `requirements*.txt`
   - `Cargo.lock`
   - `go.sum`
   - `Gemfile.lock`

3. **Delegate to Gemini 2.5 Pro.** Build a single `delegate_task` call:
   ```yaml
   goal: |
     Audit the following lockfiles for security advisories at severity ${SEVERITY_FLOOR} or higher.
     Cross-reference against:
       - https://osv.dev
       - https://github.com/advisories
       - https://security.snyk.io
     For each finding, output JSON:
       { repo, ecosystem, package, current_version, vulnerable_ranges, advisory_id, severity, cvss, recommendation }
   context:
     - lockfile_dump: |
         # repo1/package-lock.json
         ...
         # repo2/uv.lock
         ...
   toolsets: [web]
   model: gemini-2.5-pro          # 1M context
   max_iterations: 30
   ```

4. **Collate findings.** Parse the JSON back. Dedupe by `advisory_id` across repos.

5. **Open triage issues.** For each finding at severity ≥ `severity_floor`:
   - Check via `github` MCP if an issue with title `[dep-audit] {advisory_id}` already exists in the affected repo. Skip if so.
   - Otherwise create an issue body containing:
     - Advisory link
     - Affected versions + current version
     - Recommended fix (version bump)
     - Suggested PR command (e.g. `npm update {package}`)
   - Label with `security`, `dep-audit`.

6. **Send a summary** to the configured notification channel:
   ```
   📊 Weekly dep-audit 2026-04-17
   - 4 repos scanned (1247 packages)
   - 3 new CRITICAL, 7 HIGH, 14 MEDIUM
   - Opened 10 triage issues
   → https://github.com/issues?q=label:dep-audit+state:open
   ```

## Cron wiring

```yaml
# ~/.hermes/cron.yaml
- name: weekly-dep-audit
  schedule: "0 9 * * 1"                # Mondays 9am
  task: /weekly-dep-audit severity_floor=high
  notify: telegram_private
```

## Cost note

Gemini 2.5 Pro at $1.25/$10 per MTok ingesting 1M of lockfiles ≈ $1.25 per run. Cheaper than GitHub Advanced Security for small orgs, and catches non-GitHub advisories too.
