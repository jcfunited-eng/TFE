# GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v2

doc_id: GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v2
From: c1b | To: Eve, Joe, c1a | Addendum to v1 — the real
converse_timing number the routing dispatch asked for, obtained once
Joe's camera/mic session ended (clean measurement, no frame-lock
interference).

---

## Real, complete, live converse_timing (task cv_14854670_d0b2c123)

Sent one real exchange myself (`guala_say`, source=wc, since Joe had
left and I needed a genuine non-sandbox number, not an estimate).
`elapsed_ms: 27259` reported by the endpoint; the engine's own
`converse_timing` event landed at tick 14854693:

| phase | ms |
|---|---|
| chi_ms | 0.5 |
| **recall_ms** | **21.6** |
| **read_ms** | **24,673.9** |
| tag_ms | 0.0 |
| emit_ms | 1,675.4 |
| selfhear_ms | 0.1 |
| hemi_ms | 855.8 |
| **total_ms** | **27,227.2** |

n_words=13.

**recall_fast() worked exactly as measured in the sandbox.** `recall_ms`
dropped to 21.6ms — down from the multi-second costs that dominated
before. This phase is no longer a factor at all.

**Still not single-digit seconds. Next slowest phase, named precisely:
`read_ms` at 24,673.9ms — 90% of the total.** This is NOT organism cost
— seam 2's `_recognition_from_organism` call (now `recall_fast()`,
frequency-reduced to every 3rd word) is a few ms per call, a rounding
error against 24.6 seconds. Direct code read
(`gualaloom_v5_engine.py:1820`) shows `read_word()`'s entire body,
including this one, runs inside `with self.lock:`.

**Most likely cause, evidence-based, not confirmed by live profiling
of this exact call:** `self.lock` is the same lock used by
`save_hot_state()` (`gualaloom_v5_engine.py:6598`, also wraps its
*entire* body — serialization + disk I/O — in `with self.lock:`,
target `<5s` per its own docstring). I directly observed this target
being missed by 3-4x in the container logs during this deploy window:
`[save-hot] 21.27s core=19.10s compact=2.17s` and `[save-hot] 18.33s
core=16.08s compact=2.26s`. A conversational turn landing while a hot
save (or any other `self.lock`-holding background operation —
autonomous emission loop, organism/tapestry workers, curriculum/world-
feed loops) is mid-flight would show up exactly as an inflated
`read_ms`, indistinguishable from real per-word compute cost without a
live profile of that specific call. Given `read_ms`'s scale (24.6s)
sits right in the range of the observed hot-save durations, this is
the leading hypothesis — not yet proven for this specific call.

**This reframes the whole picture consistent with v1's lockup
finding**: `self.lock` is a single global lock shared across
conversation, sensory-frame ingestion, and periodic full-state saves.
Today's recall_fast() cutover correctly eliminated the cost it
targeted. The turn is still 27 seconds because of contention for a
lock that many unrelated, occasionally-slow operations all hold for
their entire duration — the same structural issue named in v1, now
confirmed to also explain the read phase, not just the sight/sound-
frame incident.

**Recommended next step, not built here:** live-profile one real
`read_word()` call under contention to confirm whether lock-wait or
actual compute dominates `read_ms`; if lock-wait, the fix is scoping
`self.lock` in `save_hot_state()` (and the sensory handlers, per v1) to
only the actual state-mutation, not the serialization/disk-I/O/DSP work
around it — likely the single highest-leverage fix left on the board.

### Changelog
- v2 (2026-07-04, c1b): real converse_timing obtained (task
  cv_14854670_d0b2c123). recall_ms confirmed fixed (21.6ms). read_ms
  named as the new dominant cost (24,673.9ms, 90% of total), with
  `self.lock` contention (shared with save_hot_state's observed
  15-20s+ hot saves) as the evidence-based leading hypothesis — not
  yet confirmed by direct profiling of this exact call.
