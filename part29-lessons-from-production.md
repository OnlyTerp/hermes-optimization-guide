# Part 29: Lessons from Production

*Everything in this part was learned the hard way — by running Hermes as the
primary work tool every day for weeks: streaming relays, model failover
ladders, subagent swarms, vision pipelines, and test suites that had to
actually catch regressions. Every law here is one that was violated first
and cost real time or real money.*

The rest of this guide tells you what features exist. This part tells you
what they do when you push them past the demo stage.

---

## The laws, one page

If you read nothing else:

1. **Never switch models on a transient.** Exhaustion must be *proven* —
   error codes read, buckets checked — before a failover fires. A 5-second
   edge blip is not "out of quota."
2. **A proxy must return the REAL upstream error.** Synthesizing a 429 when
   the edge served a 502 doesn't soften the blow — it tells your failover
   logic (and you) a lie, and the wrong lane dies.
3. **Same-plan retry before cross-plan failover.** Most 5xx blips clear on
   the next attempt against the *same* account. Bouncing to a second plan
   on the first blip doubles your cache misses and cools a healthy lane.
4. **Fan-outs need a concurrency gate.** Ten parallel subagents sharing one
   subscription account will trip the *provider's* per-account concurrency
   ceiling — and it looks exactly like quota exhaustion. Gate per-plan.
5. **Never hard-kill a streaming relay mid-request.** Graceful drain, always:
   stop accepting, let in-flight streams finish, then restart. A hard kill
   resets every live session touching it.
6. **Native vision beats described vision for *interaction*, not accuracy.**
   A describer on a legible image is pixel-exact — but follow-up questions
   can't reach the pixels, and on illegible input a describer must invent
   prose while a native model can just say "illegible."
7. **A plausible vision answer proves nothing.** Verify with a generated
   image of *known* text, shape, and color — twice. Plausible ≠ correct.
8. **A test that mirrors the logic it checks is decoration.** Assert what
   reaches the wire, the file, or the process — not what an internal helper
   defaults to.
9. **Every fix needs a negative control: revert the fix, confirm the test
   FAILS, restore byte-identical.** Until then you only know the test runs.
10. **Green suites hide dead code.** If nothing outside `tests/` imports a
    module, its passing unit tests prove it compiles — nothing more.
11. **A capability counts as delivered only when its real entry point drives
    real data end-to-end** — and the proving assertion fails when you
    disconnect the lane.
12. **Never state a number you didn't get from a tool result.** Exit codes,
    hashes, counts, timings — if no tool returned it, say "no tool result
    available." A invented number is worse than an admission.
13. **Children's summaries are self-reports.** Verify external side effects
    yourself — fetch the URL, stat the file, read the record back.
14. **Metered plans: static verification only, unless the operator says so
    per session.** Model sweeps and "quick smoke tests" against a capped
    weekly allowance can drain it in one afternoon.
15. **Memory is a budget, not a landfill.** Batch edits atomically; prune
    stale entries in the same operation that adds new ones. Write facts,
    not instructions — imperative notes get re-read as standing orders.

The sections below give each law its scar tissue.

---

## 1. Failover: the most expensive reflex in your setup

### The symptom that lies

Your model lane starts erroring. The reflex: fail over to the backup lane.
The trap: **transient errors and exhaustion look identical from inside your
process.**

We watched an edge network serve ~25ms `502` blips between healthy
responses. The relay treated a blip as "this plan is dead," cooled *both*
plans, reported a synthetic `429` upstream, and the orchestrator evicted the
model from its failover ladder. Result: agents on healthy, mostly-empty
plans got declared exhausted and routed to a dead lane. The buckets were at
2% utilization the whole time.

**The fix, in order:**

- **5xx = same-plan retry, immediately.** Most edge blips are gone one
  request later. Only *persisted* 5xx earns a cooldown — and a short one,
  with a bounded attempt budget.
- **4xx is a request-shape problem until proven otherwise.** An "out of
  usage" 400 can be the provider rejecting a tool signature your harness
  invented, not a drained bucket. Before believing a quota message, send a
  minimal request and see if it also fails.
- **Only when BOTH lanes are proven exhausted does failover fire.** "Proven"
  means: real error codes from the provider, read, not inferred.
- **The relay must pass through the real status code.** A synthetic error
  poisons every layer above it — the failover logic, the logs, and your
  ability to diagnose the next incident.

**Failover ladder hygiene:** order your backup lanes by cost and quality
*deliberately*, write the order down in config, and never put two lanes that
share the same underlying account next to each other — a "backup" that dies
with the primary is not a backup.

### Concurrency ceilings masquerade as exhaustion

Second trap, nastier: a subagent fan-out — 8-10 children hitting one
subscription account in parallel — trips the provider's *per-account
concurrent request* ceiling. The error text suggests quota. It isn't quota.
Queue beyond the limit with a per-plan semaphore, fail open after a bounded
wait, and the "exhaustion" evaporates. Add this gate before you add a
twelfth backup provider.

---

## 2. Streaming relays: how to restart without casualties

If you pool subscriptions or custom providers behind a local relay (see
[Part 9](./part9-custom-models.md)), you will eventually need to restart it
while agents are live. The wrong way is `kill -9`:

- every in-flight stream dies mid-token,
- every session touching the relay sees connection errors,
- agents conclude "the provider is down" and burn failover budget.

**The right way — graceful drain:**

1. Add a `/shutdown` endpoint that stops accepting new requests and lets
   in-flight streams finish (with a time cap).
2. New requests during drain get an immediate clean error so *their* retry
   logic engages instantly — that's failover working, not a failure.
3. Wait for the port to free and in-flight counts to hit zero. Only then
   relaunch.
4. If you must force-kill (old build without `/shutdown`), do it only when
   zero connections are established — check first.

**Corollary:** anything that kills processes mid-stream (watchdogs, update
scripts, "fix it with taskkill") must be forbidden by policy. The
"restarted it and now everything errors" pattern is almost always a hard
kill followed by blame-the-provider.

---

## 3. Vision: the interaction difference, and the hallucination trap

### Native vs auxiliary vision

When your model reports vision support, images stay in the model's context
(`native`): the model can re-examine pixels on follow-up questions. When it
doesn't, a fallback describes the image once, prose enters context, and the
pixels are *discarded*. On a legible image the description is often
pixel-exact — quality is not the difference. **Interaction is:**

- follow-up questions can't reach discarded pixels,
- the describer can't know what you'll ask next,
- on illegible input a describer **must** emit prose (a native model can
  decline), so it invents labels, counts, and icons with total confidence.

The failure is silent: a confident wrong digit in a screenshot read.

### How to actually verify vision

Do not test with a screenshot of a real dashboard and accept a plausible
reading. Generate a test image with **known** text, shape, and color; send
it; check the read exactly. Run it twice — a single plausible answer proves
nothing, two exact reads across trials is evidence. And when small text
matters, upscale 3-5× before the read; digits are where describers are
weakest.

### Wire it right

If you route vision through a relay, walk **every content part**. We found a
conversion path whose loop checked `if part.get("text")` — and silently
dropped every image part, so the model confidently hallucinated about an
image it never received. After the fix, exact glyph reads went from random
to 2/2. A model "not seeing" an attached image is a wire bug until proven
otherwise.

---

## 4. Tests that can't lie

### The mirror test

The subtlest failure: a test that reads the *same defaults* as the code it
tests. We shipped a latency fix whose test read `section.get(key,
[same_default_as_source])` — so shipping the slow default still passed. The
test passed forever because it *mirrored* the logic instead of *observing*
it.

**The law: drive the real function/class and assert what crosses the
boundary** — the bytes on the wire, the file on disk, the process spawn —
not what an internal helper returns when called with the same constants.
Every time you write `get(key, default)` in a test, ask what fails when the
source changes that default. If the answer is "nothing," the test is a
mirror.

### The negative control

A passing test tells you the test *runs*. A negative control tells you it
can *fail*:

1. Revert the fix (or break the feature deliberately).
2. Confirm the test FAILS.
3. Restore, byte-identical (hash-check, don't trust the editor).

If step 2 doesn't fail, your test passes unconditionally and was never
evidence. Compare failure *sets* across runs, not counts — 192 failures
inherited from base and 192 "new" failures are different universes.

### The dead-module trap

Every module under a directory of ours was fully unit-tested. Nothing outside
`tests/` imported any of it. The suites were green because unit tests import
the module directly — proving compilation, not wiring.

**Wiring proof:** exercise the *real* entry point (the route handler, the
live task loop, the CLI command) and assert content only the real module can
produce. Then replace the call with an empty dict — if tests still pass,
they were testing nothing.

### The real-data law

A lane wired only to fixtures fabricates nothing and sees *nothing*. "No
fabrication" and "actually observes" are different claims. A capability
counts as delivered when:

1. its real entry point drives **real data** end-to-end, and
2. the proving assertion **fails when the lane is disconnected**.

And when a suite test fails after a behavior change — treat it as a
*question*, not a chore. Twice this saved us: two tests were right to fail,
and one had to be inverted because silence stopped meaning "dead socket."

---

## 5. Windows as a first-class Hermes host

Most guides assume Linux. If you run Hermes natively on Windows, these are
the traps:

- **The shell is git-bash, not PowerShell.** POSIX syntax works; PowerShell
  built-ins don't. And MSYS path conversion may be *disabled*: `/c/Users/...`
  paths pass fine to bash built-ins but fail as arguments to native tools —
  use `C:/Users/...` forward-slash native paths for native programs.
- **Flag syntax:** some hosts pass double-slash flags (`//F`) through raw,
  so `taskkill //F` opens cmd interactively, does nothing, and exits 0 — a
  *false success*. Single-slash (`/F`) is correct where conversion is
  disabled. **Always verify the effect** (port up? file changed?) after any
  native-tool call; don't trust exit code 0.
- **`/tmp` split-brain:** git-bash tools write `/tmp` to the MSYS temp dir;
  native Windows Python resolves `/tmp` to `C:\tmp`. A file written by one
  is invisible to the other. Pick `$LOCALAPPDATA/Temp` for scratch files
  that cross that boundary.
- **Line endings:** some files are CRLF, some LF. Before any scripted edit,
  detect the newline style — a replacement built with the wrong one corrupts
  silently.
- **Scripted edits need guardrails:** a blanket find-replace matches in
  unrelated functions and SyntaxErrors a file you never touched. Copy the
  file first, locate exact bounds, parse-check the AST after *every* edit.
- **Safe-write law:** never
  `open(p,'wb').write(open(p,'rb').read())` — `wb` truncates *before* the
  inner read runs. Read into a variable first. (Also in
  [the kill list](./README.md#never-do-this-the-kill-list).)
- **Truncate-then-read recovers:** `git checkout -- <path>` restores tracked
  files — know it before you need it.

---

## 6. Evidence discipline: the anti-fabrication stack

This is the meta-law everything else depends on.

- **No tool result, no number.** The question "what was the exit code?" has
  exactly two honest answers: the number from the tool output, or "no tool
  result available — I won't invent one." A fabricated exit code, hash, PID,
  or benchmark number is worse than any failure, because it's *trusted*.
- **Raw archives beat handoffs.** If a process produces a transcript and a
  summary, the transcript is authority. We measured a handoff summary that
  preserved 4.6% of the raw record — every ID cited in a summary gets
  resolved against the raw source before anything builds on it.
- **Verify external state by reading it back.** "Upload succeeded" from a
  child agent is a self-report. Fetch the URL. Stat the file. Query the
  record. A successful tool call is not a successful task.
- **Measuring is not fixing.** Never declare a fix without re-measuring the
  *user-visible* symptom — not the internal metric that moved.

### Delegation, honestly

Subagents are excellent for parallel reasoning-heavy work. Their final
summaries are *self-reports*, not verified facts. Rules that keep delegation
honest:

- Require a verifiable handle (URL, absolute path, record ID) for any
  external side effect, then verify it yourself.
- Never give children a shared mutable workspace without file-ownership
  boundaries — parallel writers on one tree collide in ways merge tools
  don't catch.
- A child that "completed" without producing its named artifact is a failed
  child. Count artifacts, not completions.
- Don't delegate the work that defines your product's judgment to a cheaper
  model. Cost-tier the *periphery* (exploration, triage, drafts), never the
  core decisions.

---

## 7. Metered plans and the burning reflex

Every subscription plan has a ceiling, and agents discover it
enthusiastically. Rules that keep allowances alive:

- **Classify every provider as metered or unmetered before the first call.**
  Metered = weekly-capped, per-seat, or rate-billed. Unmetered = flat
  subscription or free tier.
- **Static verification only for metered lanes by default:** list models,
  check health-style endpoints, inspect config — never fire a live
  completion "just to check."
- **Live smoke tests need explicit per-session permission**, and even then,
  one call, not a sweep. A 200-model picker sweep against a capped weekly
  allowance can drain it in an afternoon.
- **Failover ladders must never include a "test the ladder" step against
  real providers.** Test against local fake upstreams; verify routing logic
  with unit tests, not tokens.

---

## 8. Memory hygiene at scale

Run the same agent daily for a month and its memory store fills. Ours sits
near its cap constantly. What works:

- **Batch memory edits atomically.** When memory is nearly full, a lone
  `add` fails; a single batched operation that removes stale entries *and*
  adds the new one succeeds, because the budget is checked only on the
  final result. Make consolidation and addition one operation, not two.
- **Write facts, not instructions.** "User prefers concise responses" is a
  fact that informs. "Always respond concisely" is an imperative that
  future sessions re-read as a standing order — and standing orders
  override the user's current request. Declarative phrasing is safer.
- **Don't store anything stale-in-7-days.** Issue numbers, commit SHAs,
  "phase N done," live PIDs — all session state, not memory. Facts about
  preferences, environment, and conventions are memory. The rest belongs in
  session search, not memory.
- **Procedures are skills, not memories.** A workflow you'll repeat belongs
  in a `SKILL.md` where it can be loaded on demand (see
  [Part 5](./part5-creating-skills.md)), not in a memory block taxed on
  every prompt.

---

## What's Next

- [docs/failure-modes.md](./docs/failure-modes.md) — the postmortems behind these laws, symptom-first
- [Part 27: Power Secrets](./part27-power-secrets.md) — the upstream mechanics these laws operate on
- [Part 19: Security Playbook](./part19-security-playbook.md) — approval layers for everything that touches the outside world
- [Part 26: MoA & Verification](./part26-moa-verification.md) — completion contracts that pair with the evidence law

---

*Every law in this part was extracted from real production incidents on a
daily-driver Hermes install (Windows host, multi-provider relay pool,
subagent swarms, local + remote GPUs). Names, accounts, keys, ports, and
identifying details are stripped; the laws and their failure shapes are
intact. If a claim here can't be reproduced from the described mechanics, it
didn't make the page.*
