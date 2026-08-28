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

## 9. Edge 502 blips misread as exhaustion killed healthy lanes

**Symptom:** Agents mid-run suddenly report the primary model "out of
quota" and get failed over to a worse lane. Provider dashboards show
 utilization near zero. After a relay restart, everything works again —
until it doesn't.

**Root cause:** The Anthropic-style edge served ~25ms `502` blips between
healthy responses. The relay's error path cooled *both* plans on any 5xx,
then reported a synthetic `429` ("quota") upstream. The orchestrator's
failover logic did exactly what it was told: evict a model whose plans were
actually at ~2% utilization and route to a dead lane.

**Recovery:** Read the real upstream status codes from the relay logs. Restart
the relay with the corrected semantics (see permanent fix). Agents recover
on their next request — no provider action needed, because the provider was
never the problem.

**Permanent fix:**
- 5xx = **same-plan immediate retry**; only *persisted* 5xx earns a short
  cooldown plus a bounded attempt budget.
- When both plans are stuck, return the **real 502** — never synthesize a
  429. A synthetic error poisons every layer above the relay.
- Failover fires only when exhaustion is *proven* (real provider error
  codes), never on a transient.

---

## 10. Subagent fan-out tripped a per-account concurrency ceiling that looked like quota

**Symptom:** A 10-subagent fan-out, all children on one subscription
account, starts failing with errors that read like rate limiting / quota.
Adding a backup provider doesn't help; the failures continue.

**Root cause:** Subscription plans carry a per-account *concurrent request*
ceiling distinct from the usage quota. Ten simultaneous streams trip it, and
the error text suggests exhaustion. The relay's own request count is the
tell — the account is fine; it's just parallel.

**Recovery:** Stop the fan-out; serial or small-batch execution completes
normally.

**Permanent fix:** Per-plan concurrency gate in the relay — a semaphore that
admits N concurrent upstream calls per plan, queues beyond that, and fails
open after a bounded wait. Add the gate *before* adding a twelfth backup
provider.

---

## 11. A hard relay restart killed every live stream (and got blamed on the provider)

**Symptom:** Mid-session, all agents report connection errors at once. The
pattern "restarted the relay, then connection errors, then everything
stopped" repeats across incidents.

**Root cause:** A hard process kill (`taskkill /F` / `Stop-Process -Force`)
on a streaming relay resets every in-flight stream simultaneously. Agents
see a burst of connection resets, burn failover budget, and some evict the
provider entirely. Two overlapping kill windows from different operators (or
agent and human) make it look like an outage.

**Recovery:** Restart the relay gracefully and let agents retry; streams
re-establish on their own.

**Permanent fix:** The relay gains a `/shutdown` endpoint: stop accepting,
drain in-flight streams (bounded), serve clean errors to new requests during
drain, wait for zero established connections, then relaunch. **Hard kills of
a streaming relay are forbidden by policy.**

---

## 12. Vision relay dropped every image — model hallucinated confidently about an image it never saw

**Symptom:** An image-routing model "reads" screenshots but invents labels,
counts, and UI elements that don't exist. Two runs on the same image
produce two different wrong answers. The model sometimes says "I don't see
an image attached" — sometimes not even that.

**Root cause:** In the relay's request-conversion path, a loop guarded on
`if part.get("text")` — silently dropping every `image_url` content part.
The model received a text-only transcript of a conversation about an image
and did what strong models do: it filled the gap with plausible detail.

**Recovery:** None at the agent layer — this is invisible from the model's
side. Diagnose by sending a generated test image with known text/shape/color
and checking the read exactly.

**Permanent fix:**
- Convert every content part; map `data:` URLs to inline image parts and
  `http(s)` URLs to file parts. No part-type filter that can drop silently.
- **Verify vision with a known-target test image, twice.** A plausible
  answer proves nothing.
- Upscale 3–5× before reading small text; digits are the weakest read.

---

## 13. The mirror test: a regression test that shared the bug's default

**Symptom:** A latency fix ships. The suite stays green. Users still see the
slow path. Nothing catches it — ever.

**Root cause:** The test read `section.get(key, [50, ...])` — the *same
default* as the source under test. When the fix landed, the test read the
fixed value; when the fix regressed, the test read the slow default too. It
mirrored the logic instead of observing it, so it could never fail.

**Recovery:** Rewrite the test to drive the real function/class and assert
what reaches the boundary (the wire payload, the emitted frames) — not what
an internal default returns.

**Permanent fix:** For every fix: **negative control** — revert the fix,
confirm the test FAILS, restore byte-identical (hash-checked). Compare
failure *sets* across runs, not counts.

---

## 14. Green suites hid an entirely unwired subsystem

**Symptom:** A directory of modules shows 100% passing unit tests. Months
later, a grep reveals nothing outside `tests/` imports any of it — the
feature never actually runs in the product.

**Root cause:** Unit tests import the module directly, so green suites prove
compilation plus internal logic — not wiring. Dead code with healthy tests
is invisible to every dashboard.

**Recovery:** Find the real entry point (route, task loop, CLI command);
assert content only the real module can produce; delete or wire the dead
code.

**Permanent fix:** Wiring proof = drive the *real* entry point end-to-end,
then a deletion test — replace the call with an empty value; if tests still
pass, the coverage was theater. Extend to data: a lane wired only to
fixtures sees nothing; delivery requires the real entry point on real data
with an assertion that fails when the lane is disconnected.

---

## 15. Handoff summary vs. raw transcript: 4.6% fidelity

**Symptom:** A long autonomous run ends with a tidy summary. The next
session builds on it and immediately cites IDs, decisions, and file states
that don't exist.

**Root cause:** The handoff summary preserved 4.6% of the raw session
record. Summaries compress; compression drops exactly the identifiers and
caveats the next step needs.

**Recovery:** Re-open the raw transcript/rollout files; resolve every cited
ID against the raw source before continuing.

**Permanent fix:** Treat the raw archive as authority, never the handoff.
Any process that produces both must make the raw path *part of* the handoff.
And in conversation: no number (exit code, hash, count, timing) may be
stated without a tool result behind it — "no tool result available" is the
honest answer, an invented number is the unforgivable one.

---

## Add yours

This page grows by incident, not by release. If a failure mode burned you:

1. Open a PR adding an entry in the shape above (Symptom → Root cause →
   Recovery → Permanent fix).
2. Include the exact error text you saw — future readers grep for it.
3. No invented failures: every entry must come from something that actually
   happened. The value of this page is that all of it is real.
