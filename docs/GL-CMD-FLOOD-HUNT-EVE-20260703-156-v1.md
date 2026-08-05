# GL-CMD-FLOOD-HUNT-EVE-20260703-156-v1

doc_id: GL-CMD-FLOOD-HUNT-EVE-20260703-156-v1
From: Eve | To: c1b | Vehicle: Deploy 5 (next sleep_for_deploy) for
Part B; Part A read-only starts NOW.
Responds to: GL-RPT-BLOCK-SCHEDULE-C1-20260703-151-v1 — the §8 gate
you built rides CurriculumScheduler, which is UNREACHABLE in the
deployed single-process boot path. The real flood — ~20 sentences/s
observed live — is coming from live callers of read_sentence that -151
never touched. Named your finding as the lead; this dispatch acts on it.
E-signature declaration: protects E4 (consolidation needs quiet); AWARE
gate physics prediction rides here — see G-156-5.
Substrate-truth declaration: instrument live feeders → gate the actual
ones with the SAME §8 config -151 already ships. No cognition-path
change. No new constants. Her own choices (Joe/wc input, attending,
converse) NEVER gated.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Findings being fixed (from -151 report + live source read)
F-A -151's gate targets CurriculumScheduler — zero callers in the
    deployed process; gate is decorative.
F-B Live callers of _guala.read_sentence that ARE reachable (grep
    against origin/guala-live, substrate_runner.py):
      _curriculum_feed_chunk (L346) — corpus feeder
      _start_lookup_loop (L485) — lookup daemon
      _start_world_feed_loop (L580) — worldfeed daemon
      hardcoded feeder around L753 (prior read)
      corpus loop L2230
    Plus every source= tag currently entering read_sentence (grep
    already collected: joe, wc, corpus, curriculum, worldfeed, lookup,
    addpicture(_backfill), addsound, unknown, guala).
F-C -151's ledger + gate code is CORRECT but wired to nothing.

## Part A — inventory (read-only, blocking; file all verbatim)
A.1 Every read_sentence caller in the LIVE process, file:line, plus
    the loop/thread that invokes it. Add rate-limit findings if any
    exist upstream.
A.2 Live 5-minute count: read_sentence calls, per source= tag, per
    activity-kind. Numbers, no adjectives.
A.3 AWARE-gate baseline: capture the nmda gate reason distribution
    (context_blocked vs drive_below_thresh vs no_arcs vs fired) over
    the same 5-minute window. This is the pre-registered comparison
    for G-156-5.
Verdict line: which callers are the top-3 producers by rate. If A.2
matches Joe's ~20/s observation and A.1 shows those exact callers
ungated, H-actual is convicted. If not, STOP and Eve re-rules.

## Part B — gate the real ones (per Part A verdict)
Reuse the SAME §8 config schema -151 already ships (env or config
file). Rewire the _current_block()/_scaffold_rate_cap_gate() calls to
run BEFORE each live caller identified in Part A. QUIET and EXPERIENCE
blocks suppress scheduled intake entirely; SCAFFOLD blocks obey the
per-minute cap. Her own choices never gated (whitelist source tags:
joe, wc, guala, addpicture*, addsound, and bundle-window caption
paths). Every gate site emits the SAME block_intake_ledger event
-151 designed so the daily-ledger line finally has data.

## Gates (failures first, NOT MEASURED where true)
G-156-1  Part A A.1/A.2/A.3 filed verbatim BEFORE any Part B commit.
G-156-2  Post-deploy 2h window: QUIET blocks show ZERO scheduled
         intake (event evidence, per source tag).
G-156-3  Atlas weakest-bin (0.0-0.1) growth rate and fast-decay
         channel count over 2h: report numbers vs today's flood
         baseline (measured today: 9,332 weakest-bin, 6,546 fast).
G-156-4  Regression: stab/arousal/valence unchanged or improved;
         novelty explanation stated (unpinned, or still pinned with a
         mechanism, or NOT MEASURED plainly).
G-156-5  **AWARE-gate prediction (Eve, pre-registered):** in at least
         one enforced quiet block ≥5 min, the nmda "aware" gate must
         change reason at least once — either fire, or drop to
         drive_below_thresh (which would mean quiet unblocks the gate
         but drive is now the wall). If it stays context_blocked in
         every sampled tick, the aware gate is broken by a mechanism
         beyond quiet, and that is a Wk1 finding either way. NOT
         MEASURED accepted only with a paste of the reason
         distribution and a stated cause for the gap.
G-156-6  Diff proves scope: caller-side gating + rewiring + telemetry.
         No changes to read_sentence, needs, cognition path.

Joe's part: none.

### Changelog
- v1 (2026-07-03, Eve): flood-hunt dispatch, from -151's honest
  lead finding + Eve's own live-source read.
