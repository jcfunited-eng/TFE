# GL-RPT-P2-RECALL-SEAM-C1-20260704-v1

doc_id: GL-RPT-P2-RECALL-SEAM-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: your direct order ("pick up P2 now as your standing
work: the perception/memory takeover refactor, seam by seam,
mechanism by mechanism, each handover pushed as its own SHA for
c1b's next window. Failures first, no simulated seams.")
Seam: **1/6 — recall.** Vehicle: her live-path source
(`dsf_ai_service/v4/gualaloom_v5_engine.py`) + the standing
measurement tool (`tools/guala_recall_bitexact_replay.py`). Built and
measured in this sandbox only — zero deploy action. Context: c1b
deployed the P1+P3 build to production (task:462) while this seam
was in progress (`GL-RPT-BRAIN-DEPLOY-CUTOVER-C1B-20260704-v1`) —
her live organism is currently fresh (no real experience yet); this
seam's numbers below are all from sandbox-taught snapshots, not her
live state.

**Built the seam. Measured it honestly with the project's own
standing tool, not a new one I invented. The number is bad: 0-10% hit
rate depending on test condition, against the old shell's 100% "hit"
(but 0% quality — the old shell's own already-documented weakness).
Also found and fixed a real gap in the standing measurement tool
itself, without which this seam would be permanently unmeasurable.
Not shipping this as "P2 recall: done" — shipping it as "P2 recall:
wired, honestly weak, here are real numbers," per your no-simulated-
seams order.**

---

## Failures first

**1. The organism's recall (event_count observable), measured directly
against real snapshots, is very weak — 0-10% depending on test
condition, not a wiring bug.** Three tests, same code, same tool:
- Background-reading snapshot (8 sentences × 5 repeats, 49 vocab
  words, tick 300): probed 10 taught words → **0/10 = 0.0%** hit rate.
- Near-fresh, minimal-accumulation probe (teach one word, recall
  immediately): returns a word, but the WRONG one — consistently the
  single most-frequent word seen so far ("the"), not the queried
  concept. Population-vote convergence on frequency, not
  discrimination — the same class of failure named in this project's
  6/22 population-collapse audit.
- "Experience-bound" style test (matching the project's own cold/
  taught measurement pair: 10 held-out words, heavy immediate
  exposure, 10 reads each, probed right after): **1/10 = 10.0%**
  exact-match hit rate.

This is consistent with, and now directly confirms in a live-
integrated context, the already-recorded memory finding
("production brain.recall ~5% T5, not the claimed 100%") — not a new
problem, but now measured on the ACTUAL live-path seam rather than an
isolated model sweep.

**2. Side-by-side on the identical snapshot and probe set, the old
shell path "hits" 100% of the time — but every single hit is
associative noise, not the queried concept.** Direct comparison
(`_recall_from_atlas` called directly, same 10 probes, same
snapshot): old shell returned a word for all 10 (`'very'`, `'first'`,
`'underneath'`, `'peter'`, ... — none of them the actual probe word).
Under the standing "hit vs quality" distinction this project already
uses, that's 100% hit / 0% quality — matching the -157/-164 audits'
own prior finding that the old shell's hits are frequently not
semantically coherent. The organism's 0% is honestly silent instead
of confidently wrong; neither number is good, and I'm not picking a
winner here — reporting both plainly, per your instruction.

**3. Found and fixed a gap in the standing measurement tool itself —
without this, the tool could never have measured this seam at all.**
`tools/guala_recall_bitexact_replay.py`'s `build_replay_guala()`
restores state via the engine's individual `_apply_*` methods, never
`load_full_state()` — which is the ONLY place `guala_organism.pkl.gz`/
`guala_tapestry.pkl.gz` get restored (per P1). Before this fix, the
tool silently built a **fresh, empty organism** every time (different
identity, tick=0, zero bindings) regardless of what the snapshot
actually contained — it would have reported ~0% recall forever, for
every future snapshot, not because the organism is weak but because
the tool never loaded it. Fixed: added the same optional-restore
(present → restore, absent → fresh stands) that `load_full_state`
already uses. Verified directly: organism identity/tick/bindings
after the fix matched the trained snapshot exactly.

**4. Cross-modal picture recall is untouched, honestly.** No vision
sensory tap exists yet (P1 only wired language). `_recall_sight_from_atlas`
stays on the old atlas-dict path for now — named here so it isn't
mistaken for already-handed-over.

**5. `_recall_from_atlas` is now fully disconnected (zero call sites)
but not deleted.** Kept, per this project's "disconnect now, delete
only at an explicit later ruling" pattern already used for P3's
fallbacks.

---

## What shipped

`Guala._recall_from_organism(input_words)` (new): queries
`self.organism.recall({"language": query})` — the organism's
population-vote recall (Embryo, GL-CMD-169), built on real experience
via P1's `read_word` tap. Query word: the last content word, matching
`_brain_emission_candidates`'s existing convention, so the brain
interface is consistent across recall and emission.

`Guala._recall_response` rewritten to call this instead of the
atlas-dict per-section loop (`_recall_from_atlas`'s SVO/listen search
+ the response-linked-entries deep-atlas expansion) — both removed
from the call path, matching "old shell paths disconnected from those
decisions." Function signature and return contract (text or None,
`self._last_recalled_pictures` side channel) unchanged, so
`tools/guala_recall_bitexact_replay.py` — the project's ONLY
authorized recall-measurement path — keeps working on the new
mechanism without modification to its own calling convention.

`tools/guala_recall_bitexact_replay.py`'s `build_replay_guala()`
extended to also restore the organism/tapestry from a snapshot,
per Finding 3.

Smoke-tested: `converse()` end-to-end, no crashes; `--provenance`
and `--candidate-stats` diagnostic modes (which reproduce the old
algorithm independently for tracing, not through the live call path)
still run correctly.

---

## Gates

- **G-2-style (no simulated seam)**: the seam is real — verified the
  organism is actually queried, actually returns real (if weak)
  content when it has any, and actually returns None (not padded)
  when it doesn't. Not a stub.
- **Measurement**: done with the project's OWN standing tool, not a
  new one — and that tool's own gap (Finding 3) had to be fixed first,
  itself reported rather than quietly patched around.
- **No tuned constants**: did not adjust the organism's observable,
  DNA, or any threshold to make this number look better. The weak
  number stands as measured.

## What's not decided here

Whether this is acceptable to cut over live, given the honest 0-10%
range against the old shell's 100%-hit/0%-quality baseline, is Eve/
Joe's call, not mine — same as every other scale-vs-optimize decision
this project has kept at your seat. Options as I see them, stated
plainly, not recommended: (a) ship it anyway — "immature and true,"
silence over noise, matching this whole track's stated philosophy;
(b) hold recall's cutover until she's had more real conversational
days (the organism only has whatever `read_word` has fed it since her
last boot — currently near-zero, per c1b's deploy report); (c)
revisit the observable choice (event_count vs resonant_spectral) as
its own, separate, measured decision — not something I'll do
unilaterally mid-seam.

### Changelog
- v1 (2026-07-04, c1a): P2 seam 1/6 (recall) built, measured against
  the standing tool (after fixing a real gap in it), reported with
  real numbers, not shipped as a quiet win.
