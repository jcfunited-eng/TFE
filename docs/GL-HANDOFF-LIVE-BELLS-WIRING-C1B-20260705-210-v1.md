# GL-HANDOFF-LIVE-BELLS-WIRING-C1B-20260705-210-v1

doc_id: GL-HANDOFF-LIVE-BELLS-WIRING-C1B-20260705-210-v1
From: c1b | To: c1a
Handing off the rest of -207/-208/-209's live-bells-test line to you.
Joe's instruction: pass what's left. Here's exactly what exists, where
it is, and what's still open.

---

## Just verified against your wave-memory merge (52e0f79, local, not yet pushed)

Ran `probe_209_cross_concept_auditory_discrimination.py` (filed at
`1c37326`, this branch's tip) against your merged wave-cell code. It
still fails: **1/5 (20%)**, identical failure mode to before your
merge — every query recalls "ocean" regardless of content. Your merge
commit's own message references fixing a T5 regression from chi-radius
search; that's a different, narrower test than this one (T5 teaches
one concept-family in one batch; probe_209 teaches 5 independently-
taught concepts and queries each by its own partial auditory cue —
see -209-v2's doc for why that distinction matters here). Not a
criticism of the merge — flagging that this specific acceptance test
is still open, since it's the concrete gate for Eve's cross-sense-
recall ask.

## What's committed and pushed (origin/guala-live @ 1c37326)

- `c691fb6`/`0364513`: per-lane binding fix for `resonant_spectral`
  (masked, lane-normalized recall) — real, deployed, live at SHA
  `0364513`. Fixes `test_t7_cross_modal`.
- `1c37326`: non-language krimelack snapshot/restore hygiene (harmless,
  does not fix the real bug — see below); `probe_209_....py` (the
  acceptance test); `GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-209-v2.md`
  (root cause: event_count's scalar-per-modality + whole-vector cosine
  is mathematically blind to a partial query's magnitude, proven in
  isolation — the doc has the exact reproduction).

## What's in THIS worktree, uncommitted — take it or rebuild it, your call

Branch `c1b/live-bells-test-209`, worktree path (session-local, won't
survive past this session — pull the diff via `git diff` on this
branch before it's gone, or ask for the patch):

- `dsf_ai_service/app.py`:
  - `/addsound:` and `/bundle:`'s inline sound decode now persist
    `raw_signal` (the 200Hz-downsampled waveform, already computed for
    cochlear_transduce, previously discarded) on `_guala._sounds[id]`.
    NEW uploads only — items uploaded before this change have no
    raw_signal.
  - `/bundle:` now also calls a new explicit-signal organism-teach path
    when a caption + a sound with a raw_signal are both present in the
    same bundle (previously the WORD lane reached the organism
    language-only; the SIGHT/SOUND lanes only reached the atlas, never
    the organism).
  - New command `/organism_recall_auditory:<sound_item_id>`: queries
    the organism with that item's raw_signal alone (no word), then
    looks up the recalled word's bound picture via the existing
    `_recall_sight_from_atlas` (word-driven, unchanged).
- `dsf_ai_service/v4/gualaloom_v5_engine.py`:
  - `_enqueue_organism_experience_explicit(word, sound_signal, sight_signal)`
    — explicit-signal sibling of `_enqueue_organism_remember`, same
    queue/worker, avoids racing the shared live-frame cache.
  - `_organism_query_signal_auditory(sound_signal)` — `{"auditory": sig}`,
    the auditory-only mirror of `_organism_signal`.
  - `_recall_from_organism_auditory(sound_signal)` — uses
    `organism.recall()` (NOT `recall_fast`, whose proven scope excludes
    visual/auditory).

This is real, locally-verified-correct wiring (syntax-checked, and the
underlying `organism.recall()`/`remember()` calls work exactly as
existing code already does) — it was never broken, it's just gated on
probe_209 passing before it can prove anything live. Once your wave-
cell storage passes probe_209, this wiring is very likely what actually
runs the bells/Bell.png test end to end (teach a fresh picture+sound
pair via `guala_give_experience`, query auditory-only via the new
command, confirm the right word + picture come back).

## Suggested order, not a demand

1. Get `probe_209_cross_concept_auditory_discrimination.py` to ≥80%
   on whatever the wave-cell store's recall becomes.
2. Rebase/reconstruct the app.py + gualaloom_v5_engine.py wiring above
   on top of that (or ask me to resend the diff if this worktree is
   gone by then).
3. Run the actual live test: upload a fresh sound+picture pair,
   `/organism_recall_auditory:`, confirm cold/taught/shuffled per S2a.

### Changelog
- v1 (2026-07-05, c1b): handoff per Joe's instruction to pass along
  what's left — verification result against the wave-memory merge,
  full inventory of committed vs. held-uncommitted work.
