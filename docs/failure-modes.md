# Failure modes & incident postmortems

The part of this guide that cost actual money, downtime, and 3 AM. Each entry
follows the same shape: **Symptom → Root cause → Recovery → Permanent fix.**
These are real incidents from production Hermes fleets, not hypotheticals.
If you hit one of these symptoms, jump straight to the entry.

---

## 1. `hermes update` exits 2 for no visible reason

**Symptom:** `hermes update` or `hermes update -y` aborts with exit code 2.
The error text mentions a lock or process check, and retrying changes nothing.

**Root cause:** The updater refuses to touch the venv while *any* process is
still running from it. Long-lived children count: the gateway, background
relays, anything you launched days ago and forgot. A desktop app instance is
enough on its own.

**Recovery:**
```bash
# stop everything that imports from the venv, then update
taskkill //F //IM python.exe    # Windows — scope tighter if you have other python work
# Linux: pkill -f 'hermes gateway'; also check for stray relays
hermes update -y
```

**Permanent fix:** Before any update, enumerate venv processes first. Never
use `--force` — a forced update over a live process leaves a half-installed
venv that fails in confusing ways later. The flag exists for disaster
recovery, not impatience.

---

## 2. Gateway wedges after delegation-heavy sessions

**Symptom:** The gateway stops responding mid-conversation. Restarting the
process doesn't help. Logs show the session resuming into a corrupted state.

**Root cause:** An environment variable from a delegated child session
(`HERMES_DELEGATED_CHILD_CONTEXT`) leaked into the gateway's own environment.
The gateway then treats its own sessions as children of a dead delegation
tree.

**Recovery:**
```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT hermes gateway run
```

**Permanent fix:** When you launch the gateway from a wrapper script or a
systemd unit, scrub inherited delegation variables explicitly. Child-context
variables are session-scoped and must never be exported globally.

---

## 3. Secrets leaked into the session database (and its FTS index)

**Symptom:** A bot token, API key, or password appeared in a prompt or tool
output once — now you need it *gone*, not just rotated.

**Root cause:** Everything the agent processes is persisted: the message store
(`state.db`) **and** its SQLite FTS5 index. Deleting the message row is not
enough — the full-text index keeps a second copy, and any backup you made
keeps a third.

**Recovery (the procedure we actually ran):**
1. Rotate the credential first. Always. Assume it's burned.
2. Scrub every copy of the DB: live file *and* backups.
3. Rebuild the FTS index after row surgery — a deleted row leaves FTS entries
   behind unless you rebuild.
4. Verify with a full-text search for the old credential: zero hits.

**Permanent fix:** Secrets live in `.env` (or `secrets:` with an external
manager — Bitwarden/1Password integration is built in). Never paste a secret
into chat "just this once" — the session store is forever, and it is
searchable.

---

## 4. Agent file-surgery silently zeroes a file

**Symptom:** After an agent edit, a file that existed moments ago is 0 bytes
or truncated. No error was reported.

**Root cause:** The classic one-liner:
```python
open(p, 'wb').write(open(p, 'rb').read())
```
`'wb'` truncates the file **before** the inner read executes. The read gets
an empty file. Zero bytes. No exception.

**Recovery:** If the file was tracked: `git checkout -- <file>`. If not:
restore from backup. There is no in-place recovery.

**Permanent fix:** Read into a variable first, then write. Any skill that does
file surgery should encode this as an explicit rule — ours calls it the
"safe-write law" and it is enforced in review.

---

## 5. Browser automation dies silently after a crash

**Symptom:** Your Playwright/browser flow worked yesterday. Today the browser
launches and immediately exits, or the script hangs on launch with **no error
message at all**.

**Root cause:** A crashed run left a zombie browser process still holding the
user-data-dir lock. The next launch collides with the lock and dies
*silently* — no stderr, no exception, just a dead process. This is the
hardest failure to diagnose because there is nothing to read.

**Recovery:**
```bash
# kill any browser holding YOUR profile dir, then relaunch
# Windows (PowerShell):
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*<your-profile-name>*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

**Permanent fix:** Before any launch in CI or automation, run a purge step
that kills processes matching your specific profile directory name. Give
every test profile a unique name precisely so this kill is safe.

---

## 6. Big tool payloads → API 400 errors that look like quota

**Symptom:** Delegation or heavy tool sessions start failing with HTTP 400.
The error mentions usage or limits. You assume you're out of quota — you're
not.

**Root cause:** Oversized tool payloads trip provider admission checks
*before* quota is consulted. The error message is misleading by design.
Blind retry at the same size fails identically and burns the rate limit.

**Recovery:** Shrink the payload, then retry. We run a ladder:
full size → 1024-token shrunken form → sibling-model failover. The shrink
step resolves the overwhelming majority.

**Permanent fix:** Never retry-loop on a 400 at identical size. If the first
retry fails with the same signature, the payload is the problem, not the
provider. Encode the ladder in the shim/proxy layer so agents get it for free.

---

## 7. Cost explodes after "optimizing" mid-conversation

**Symptom:** Token costs per conversation jump 3–5x after you enabled extra
tools, swapped a toolset, or changed the system prompt on a live session.

**Root cause:** Per-conversation prompt caching. The provider caches your
system prompt + tool definitions as a prefix; every turn reuses it for
near-zero cost. Swap the toolset or rebuild the system prompt mid-session and
**every subsequent turn pays full re-cache price**. One "small improvement"
mid-conversation silently multiplies your bill for the rest of that session.

**Recovery:** Nothing to recover — the tokens are spent. Start fresh sessions
with the improved toolset instead of mutating live ones.

**Permanent fix:** Toolset and system-prompt decisions are made at session
start. If a session needs different capabilities, spawn it — don't mutate.
(This is also why Hermes itself refuses to do this: the core treats the cache
as sacred and only context compression is allowed to touch past context.)

---

## 8. The retry-loop trap on gated resources

**Symptom:** An agent keeps hammering a login-walled site, a rate-limited
API, or a resource that needs credentials it doesn't have. Each attempt
"almost" works. An hour later: nothing done, rate limits tripped, and the
real task untouched.

**Root cause:** Retry looks like progress. For gated resources it is the
opposite — it spends rate-limit budget and time on a lane that cannot
succeed without an input (a login, a key, a human) the agent doesn't have.

**Recovery:** Stop. Give the gated lane exactly **one honest attempt**. If it
needs a credential you don't have, report that and pivot to the parts of the
task that don't need it.

**Permanent fix:** Bake the rule into your agent's operating instructions:
*one attempt, then pivot.* A visibly looping agent on a gated resource is a
bug in the instruction layer, not persistence.

---

## Add yours

This page grows by incident, not by release. If a failure mode burned you:

1. Open a PR adding an entry in the shape above (Symptom → Root cause →
   Recovery → Permanent fix).
2. Include the exact error text you saw — future readers grep for it.
3. No invented failures: every entry must come from something that actually
   happened. The value of this page is that all of it is real.
