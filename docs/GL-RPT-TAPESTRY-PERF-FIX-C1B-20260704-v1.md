# GL-RPT-TAPESTRY-PERF-FIX-C1B-20260704-v1

doc_id: GL-RPT-TAPESTRY-PERF-FIX-C1B-20260704-v1
From: c1b | To: Eve, Joe, c1a | Found via c1a's own P2-campaign handoff
("found and fixed a second problem — the tapestry was making read_word
catastrophically slow — using the same backgrounding pattern from
-172"), root cause confirmed against live production, fix extracted
and deployed same session, isolated from c1a's still-unratified P2
seam work. Failures first.

**Branch note:** the actual fix commit is NOT on `guala-live` —
`guala-live`'s tip already contains this same backgrounding code, but
bundled inside c1a's `b7c1df2` together with the separate, unratified
P2 signal-richness change. To ship the performance fix alone (without
also shipping unratified P2 cognitive substitution), it's built on
`aabb52f` (the last-deployed mainline SHA before c1a's P2 commits) on
a new branch: `guala-live-perf-hotfix-20260704`, commit `9cf2540`.
Filed there (pushed, durable) rather than force-merged/rebased into
`guala-live`'s linear history, to avoid rewriting or duplicating
c1a's already-filed work. Reconciling the two branches (once the P2
signal question is ratified one way or the other) is a follow-up, not
blocking this deploy.

---

## The problem, confirmed against production, not just c1a's sandbox

`LoomMosaic.expose()` (450 real neurons' imaginary-time settle
physics) was running **synchronously inside `read_word`**, already
live since the P1 cutover (task:462), for every word she reads or
hears — c1a's sandbox profiling put it at ~180ms/call, 86% of
`read_word`'s ~450ms total. This is not hypothetical: the live
`converse_timing` events I pulled directly during the post-cutover
watch showed `read_ms` in the 14,600-28,900ms range and `total_ms`
up to 117,748ms (117.7 seconds) for a single conversational turn —
consistent with this exact cost compounding across every word of an
utterance, while holding `self.lock` for the whole `converse()` call.
Joe's actual live replies have been taking tens of seconds to over a
minute apiece since P1 shipped.

## What c1a built, and why I didn't just deploy their commit whole

c1a's fix (`b7c1df2`) is real and correct, but it's bundled with a
**separate, not-yet-ratified P2 change**: a richer multi-modal signal
(`_organism_signal`: language + touch/smell/taste procedural
waveforms) feeding `organism.remember()`/`.recall()`, which is the fix
for P2 seams 1-2's own near-zero discrimination — a genuine, honest,
but *cognitive* change that P2's own framing (like every other seam)
marks "Not deployed... Eve/Joe's call."

The performance problem is independent of that: it's the tapestry
`expose()` call in the **already-live P1 tap**, unrelated to what
signal shape feeds the organism. So I extracted just the backgrounding
mechanism — new `_tapestry_queue`/`_tapestry_worker_thread`/
`_tapestry_lock`, the worker loop, `_enqueue_tapestry_expose()`, and
the two correctness-required lock additions (around `tapestry.compose()`
and `tapestry.save_full_state()`) — onto the currently-deployed
baseline (`aabb52f`), **without** adopting `_organism_signal()` or
touching `organism.remember()`'s signal shape at all. `read_word`
still calls `self.organism.remember(word, {"language": word})`
exactly as P1 shipped it — untouched.

## Verified directly, not just copied

Ran the extracted code standalone before shipping: constructed
`Guala()` (0.08s), called `read_word()` on a 9-word sentence.
**6.0ms/word** (down from the reported 272-457ms/word) — the queue
filled to 7 items immediately, correctly drained to 0 within 2s, the
background worker thread confirmed alive, `tapestry._tick` advanced
by the expected amount (16, matching 8 exposed pairs × 2). This is a
~98% reduction in the dominant cost, confirmed empirically, not
assumed from reading c1a's report alone.

## Deploy

Fresh verified backup (11/11 core state files confirmed present and
complete — pictures still trailing in the background, static assets
already captured in earlier backups, not blocking), then
`tools/deploy_dsf_ai.sh` from an isolated worktree pinned at
`guala-live-perf-hotfix-20260704` (commit `9cf2540`). Single attempt.

## What this does NOT change

No P2 cognitive substitution shipped. `organism.remember()`'s signal
shape is untouched (still P1's single-channel `{"language": word}`).
Does not collide with c1a's P2 work, which remains on `guala-live`,
undeployed, exactly as they left it.

### Changelog
- v1 (2026-07-04, c1b): root cause confirmed against live production
  data, fix extracted (performance-only, isolated from P2's signal
  change), smoke-tested standalone (6.0ms/word, verified queue drain),
  deployed from a separate branch to avoid rewriting guala-live's
  history.
