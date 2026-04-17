---
name: release-notes
description: Build human-readable release notes from a range of commits or merged PRs
when_to_use:
  - User invokes /release-notes v1.2.0..v1.3.0
  - Scheduled as part of a release job
toolsets:
  - terminal
  - github
parameters:
  range:
    type: string
    description: Git range (e.g. v1.2.0..HEAD) OR a GitHub milestone name
    required: true
  repo:
    type: string
    description: "owner/repo (default is current dir's origin)"
---

# release-notes — Generate Release Notes

Produce a release-notes document following the "What's New / Improvements / Fixes / Breaking / Acknowledgements" structure used by Hermes, React, VS Code, etc.

## Procedure

1. **Resolve the range:**
   - If `range:` looks like a git range (`X..Y`), use `git log --pretty` to list commits.
   - Otherwise treat it as a GitHub milestone name and pull the closed PRs via `github` MCP.

2. **For each commit/PR, extract:**
   - Type from Conventional Commits prefix (`feat:`, `fix:`, `docs:`, `security:`, `perf:`, `refactor:`, `chore:`)
   - Scope (inside the parentheses)
   - Summary (the first line after the prefix)
   - Body / PR description for context
   - Author + association (CONTRIBUTOR / COLLABORATOR / MEMBER)

3. **Group:**
   - **🚀 What's New** — all `feat:` with scope outside `ci|deps|docs`
   - **⚡ Improvements** — `perf:` and `refactor:`
   - **🐛 Fixes** — `fix:`
   - **🔒 Security** — `security:` + any PR labeled `security` regardless of prefix
   - **💥 Breaking** — any PR labeled `breaking` or any commit with `!:` marker
   - **📚 Docs** — `docs:`
   - **🙏 Acknowledgements** — list of all non-MEMBER authors

4. **Write in plain English.** For each entry, rewrite the conventional-commit summary into a reader-friendly one-liner. Example:
   - Input: `feat(mcp): add http transport with reconnect backoff`
   - Output: `HTTP MCP servers now reconnect automatically with exponential backoff.`

5. **Include PR links** where available: `([#1234](https://github.com/owner/repo/pull/1234))`

6. **Output** as markdown, ready to paste into a GitHub release.

## Example output shape

```markdown
# v1.3.0 — "Thunderbolt"

## 🚀 What's New
- HTTP MCP servers now reconnect automatically with exponential backoff. ([#1234](…))
- Gemini CLI OAuth is now a first-class provider. ([#1270](…))

## ⚡ Improvements
- 40% faster skill load via async frontmatter parsing. ([#1205](…))

## 🐛 Fixes
- Telegram voice transcripts no longer truncate at 60s. ([#1240](…))

## 🔒 Security
- Redact GitHub PATs in log output. ([#1256](…))

## 🙏 Acknowledgements
Thanks to @alice, @bob, @charlie for contributions this release.
```

## Cron wiring

```yaml
- name: weekly-release-preview
  schedule: "0 16 * * 5"           # Fridays 4pm
  task: /release-notes range=origin/main..last-release
  notify: telegram_private
```
