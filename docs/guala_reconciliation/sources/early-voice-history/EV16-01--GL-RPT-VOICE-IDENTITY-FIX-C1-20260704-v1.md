# GL-RPT-VOICE-IDENTITY-FIX-C1-20260704-v1

doc_id: GL-RPT-VOICE-IDENTITY-FIX-C1-20260704-v1
From: c1a | To: Eve, Joe
Responds to: Joe's direct message, 2026-07-04 ("c1a — two jobs, in
order: 1. VOICE IDENTITY FIX (P1, small)..."). This report covers Job
1 only; Job 2 (Stage-2 install) is its own report.

---

## Failures first

1. **This fix landed across two commits, not one, because of a shared
   working-tree collision — disclosed precisely, not glossed over.**
   While I was mid-edit (Edit-tool writes land on disk immediately,
   before any `git add`/`commit`), a concurrent session on this same
   branch committed `816ce1e` ("GL-CMD-167 Change 4 completion —
   reserve sleep/dream language for executed dream ticks"). Its diff,
   verified line-by-line against what I was building, **also contains
   the entire SOURCE_WEIGHTS/identity-gate/pair-bond-init/normalization
   half of this fix** — variable names, comment text, and all 9 gate
   sites match what I had in progress. I did not write that commit or
   choose its message; the most likely explanation is that a broad
   `git add` on the other session's side swept up my simultaneously
   in-flight, not-yet-committed edits sitting in the shared working
   directory (the exact risk `-162`'s own report flagged and handled
   the opposite way — "left it untouched" — which wasn't possible here
   since my edits were already saved to disk, not staged).
   I verified the swept-in content is byte-correct against this fix's
   spec before treating it as done, then committed **only** the one
   piece it didn't include (`38769a0`, the historical bond-value
   migration) rather than re-committing or reverting the rest. Filing
   this precisely so the history reads honestly, not as if I'd claimed
   a fix I didn't personally commit, or silently duplicated one that
   already existed.
2. **`git` itself was intermittently unusable this session** (`status`,
   `commit` hanging 30s to several minutes; one commit attempt failed
   outright on a stale `index.lock` from a crashed/timed-out earlier
   process, cleared itself before retry). Consistent with heavy
   concurrent multi-session I/O on this shared repo tonight, not a
   defect in this fix.

---

## The fix

**Scope**: give `source="joe_voice"` full identity parity with
`source="joe"` everywhere identity currently matters, while keeping
the two values distinguishable as literal strings for provenance
(atlas entries, emission logs, commit sources all still say
`"joe_voice"` — nothing here collapses the channel tag itself).

**A. Salience** (`_compute_salience`, `SOURCE_WEIGHTS`): added
`"joe_voice": 1.6` alongside `"joe": 1.6`. Before this fix, `"joe_voice"`
fell through to the dict's default (`SOURCE_WEIGHTS.get(source, 0.7)`)
— the same 0.7 weight as any unrecognized source.

**B. Identity/dwell/self-hearing gates — all 9, not 7.** My own
`-164` wiring-audit report cited exactly 7 `if source in ("joe","wc",
"c1")`-shaped gates by line number. Re-deriving them fresh today (the
file had drifted +17 lines from a concurrent edit since that report),
I found **9** current occurrences of this pattern once the two
self-hearing gates are counted (`_self_hear` triggers, one in the
phased converse path, one in the unphased path) — these ARE identity
gates in the same family, and "everywhere identity matters" is the
operative instruction, not "exactly the 7 previously counted." Fixed
all 9: dwell assignment, response-window opening (x2, phased/unphased),
response-binding tagging, self-hearing trigger (x2), and the
`converse_timing` diagnostic event gate (x2). Correcting my own earlier
count here rather than silently underscoping to match a stale number.

**Not touched, and why**: two `for source in ("joe","wc","c1"):` loops
(`presence_pulse_tick`, `timeout_check`) are a different mechanism —
explicit session-presence heartbeat, keyed to `_presence`/`_wake_tick`
dicts that have no `"joe_voice"` entry and are only ever set by
`wake(source)`, itself gated to `{"joe","wc","c1"}`. Adding `"joe_voice"`
to these iteration tuples would be a no-op (nothing ever sets presence
for that key) — not a real fix, so left alone rather than padded for
appearance.

**C. Pair-bond — merge, not duplicate.** `Coordinator._pair_bond`
(the boolean "is this a bonded identity" gate, ~9 raw dict-lookup call
sites) gained `"joe_voice": True`, mirroring `"joe"`. Separately, and
more substantively: `_record_interaction`/`pair_bond_strength` — the
**continuous** density+salience relationship gradient that actually
computed the 0.74→0.79 number Joe observed — now normalize
`"joe_voice"` to `"joe"` via a small alias map (`_BOND_IDENTITY_ALIASES`)
before touching `_source_interaction_log`. Going forward, a spoken and
a typed sentence both accumulate into the SAME interaction history;
there is no path left that can grow a second "person" under a channel
tag.

**D. What happens to the already-accumulated bond value**: the
dispatch asked this explicitly, and it's the one piece not covered by
the commit that swept up B/C above. `_apply_coordinator` (state
restore) now does a **one-time merge**: any `"joe_voice"` entries in a
loaded state's `source_interaction_log` get concatenated into `"joe"`'s
list (tick-sorted), and the `"joe_voice"` key is dropped. So the
evening's separately-grown 0.74→0.79 history isn't discarded and isn't
left orphaned — it becomes part of `"joe"`'s own combined density/
salience computation the moment this code boots and loads tonight's
saved state. After that one load, the key can never reappear (C's
normalization prevents new writes to it), so this migration step fires
exactly once, ever, per state file.

---

## Before/after proof

**Salience** (`_compute_salience`, same needs-state, `input_novelty=0.5`,
current code):
```
source='joe'        -> 2.8493
source='joe_voice'   -> 2.8493   (identical to 'joe', now)
source='wc'          -> 2.8493   (same weight tier)
source='unknown'     -> 1.2466   (what 'joe_voice' WAS computing, pre-fix,
                                   via the same fallback path)
```
2.8493 / 1.2466 = 2.29× — the actual size of the gap this closes.

**Dwell + decay channel** (taught snapshot, one novel word each,
`read_sentence(word, source=...)`):
```
'zorbaline' via source='joe'        -> dwell_ticks=8, listen entry strength=0.9858
'quithrax'  via source='joe_voice'  -> dwell_ticks=8, listen entry strength=0.9449
```
Both land on `dwell_ticks=8` → both qualify for the **slow** meta-decay
channel (`dwell >= DWELL_GATE_META=4`, not released) — the same
12×-slower fade `-163`'s retention baseline discussed as the protection
one-shot teaching currently lacks. Before this fix, `"joe_voice"` would
have gotten `dwell_ticks=1` → the **fast** channel, decaying roughly
12× quicker than a typed word taught the same way. The two entries'
raw strength values differ slightly (0.9858 vs 0.9449) — that's ordinary
run-to-run atlas/needs-state variation between two different novel
words in the same snapshot, not a residual identity gap; the field that
actually encodes decay-channel membership (`dwell_ticks`) matches
exactly.

**Pair-bond merge** (synthetic pre-fix state: `"joe"` had 2 interaction
entries, `"joe_voice"` had 2, `"wc"` had 1 — modeling exactly the shape
Joe described): after `_apply_coordinator` loads it, `"joe"` carries
all 4 entries tick-sorted, the `"joe_voice"` key is gone, `"wc"` is
untouched, and `pair_bond_strength("joe_voice")` now returns byte-
identical to `pair_bond_strength("joe")` (both alias to the same
lookup). Ran against the actual current code, not asserted from
reading it.

20/20 existing substrate tests pass unchanged
(`test_cognition_bundle`, `test_dynamics_emission`,
`test_hemisphere_roundtrip`, `test_metadata_pipeline`,
`test_plasticity_on_commit`, `test_rich_sensory_wiring`,
`test_structured_noise`, `test_teacher_correction`).

---

## Status

Code complete and pushed (`816ce1e` carries the salience/gate/init half
via the shared-tree collision described above; `38769a0` carries the
historical-bond migration, mine). Not yet deployed — this rides
whatever vehicle Job 2's Stage-2 install uses; see that report for the
carry list. No live gate to prove here beyond the code-level before/
after above; the next live `guala_status`/`pair_bond` read after
deploy should show a single `"joe"` value with no separate
`"joe_voice"` row, which I'll confirm as part of Job 2's post-deploy
checks.
