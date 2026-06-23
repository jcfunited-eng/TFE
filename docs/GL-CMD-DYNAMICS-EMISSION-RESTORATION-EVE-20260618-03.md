# GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-03

**To:** c1
**From:** Eve
**Subject:** Two-stage emission via separate assemblage System (option a) — supersedes -02
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Supersedes:** `GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-02` (Phase 0 of -02 stopped correctly on architectural mismatch — v5 `Section` is a simplified container without `psi`/`evolve`/`arcs`/`commit_check`. This brief corrects.)

---

## Architectural call

The dynamics primitives (`psi`, `evolve`, `commit_check`, Hamiltonian, cascade settling) live only in `substrate/assemblage.py`. v5's `Guala.sections` are simplified containers (`v5_engine.py:395`) used for ingestion and atlas accumulation — they don't carry physics.

We are going with **option (a)**: `Guala` gets a dedicated assemblage `System` used **only for emission settling**. v5 ingestion, presence, atlas-building, sleep, picture-emission, sensory routing — all untouched. The new System is internal scaffolding behind a feature flag.

Rejected:
- (b) Replace v5 Section with assemblage Section. Blast radius across ingestion, sleep, atlas, presence, picture-emission. Not now.
- (c) Port physics into v5 Section. Duplicates code, drift risk between two physics implementations.
- (d) Delegate to v7's session engine. Bypasses the metadata pipeline c1 just built; couples Guala emission to v7 session lifecycle.

Option (a) preserves the metadata pipeline as load-bearing (assemblage NMDA gates read source/affect/polarity off candidate records), uses validated primitives (v7 already runs assemblage successfully), and contains risk to the emission path.

## Predecessor work — verify first

`GL-CMD-GRANDURUN-METADATA-PIPELINE-EVE-20260618-01` was reported committed as `8acb193` but did not appear on `origin/codex/persistent-etl-update-20260326` at last check. **Before any work in this brief, verify the commit is on remote.** If `git fetch origin && git log origin/codex/persistent-etl-update-20260326 | grep 8acb193` is empty, push it. The metadata pipeline is load-bearing for Phase 4 of this brief.

---

## Fix — phases

### Phase 0 — Confirm assemblage primitives work standalone

Build a small harness that creates a `System` exactly like `v7_engine._build_system` does (read v7_engine.py:108-158 for the working pattern), seeds one section's mode_bank with two modes, drives `psi` toward one of them, runs `sys_.tick_once(...)` for 60 ticks, and reads `Section.dominant_mode()`.

Confirm:
1. The section commits to the driven mode (not the un-driven one).
2. `dominant_mode()` returns the driven mode after settling.
3. Adding a keyhole via `sys_.add_keyhole(...)` propagates excitation between sections in subsequent ticks.
4. Installing an NMDA gate via `apply_gate(sys_, name, gate)` from `gl_nmda.py` fires `process_gated_commits(sys_)` cleanly.

**If any fails: STOP and report.** This is the architecture sanity check.

If all pass: paste harness output and proceed.

### Phase 1 — Restore grandurun to coherent-integration candidate selector

File: `dsf_ai_service/v4/gualaloom_v5_engine.py`.

The 8D state vector is wrong shape for grandurun's actual purpose (coherent phase-integration, matched-filter SNR √N). The metadata IS still useful (Phase 4 uses it), but it goes on candidate records, not into a scoring vector.

- Add `_grandurun_select_candidates(input_chis, deep_candidates, top_k)`:
  - Per-binding complex amplitude: `sqrt(strength) * exp(i * π * |chi_a - chi_b| / CHI_CORR_LENGTH)`.
  - For each input chi, coherently sum across the candidate pool. Top-K by coherent magnitude.
  - Return a list of `Candidate` records, each carrying: `{chi, section, motif, strength, coherent_magnitude, source, arousal, valence, surprise, polarity, sensory_refs}`. Use the metadata from brief -01.
  - Default `TOP_K=200`, env override `GRANDURUN_TOPK`.
- Keep `_grandurun_select_vector` and the 8D code in place but gated by `GRANDURUN_LEGACY_8D=0` (off by default). Do not delete — it's revert.
- Per-binding `_grandurun_state` may be retained or simplified back to scalar; your call. State your choice.

### Phase 2 — Add `Guala._emission_system` (the dedicated assemblage System)

Build a single assemblage System on first use, cached on `self._emission_system`. Sections to install:

- One section per v5 atlas section that participates in language emission. Phase 0 prints `_guala.sections.keys()` — use the language-emitting subset. If v5's section names are `subject`, `verb`, `object` (most likely from v4 lineage), use those. If they're different, use what's actually there. State which sections you installed.
- For each section, build `mode_bank` lazily from atlas motifs seen for that section. Use the v7 pattern: each motif gets a `random_unit_complex(N)` mode vector, `mode_last_used=0`, `mode_strength=1.0`, cached in `self._emission_token_vec[(section, motif)]`.
- Add a `listen` section in the System (matches v7's pattern) for input drive.

Mode bank can grow as new motifs appear in candidate sets. Don't pre-populate the whole vocab — install on demand from candidate records (Phase 4).

`System` lifetime: rebuilt only when atlas structure changes catastrophically (e.g., after reload). Otherwise persisted across `converse()` calls so plasticity (`mode_strength`, LTP from coincidence gates) accumulates.

### Phase 3 — Wire keyholes and NMDA gates onto `_emission_system`

On first build of `_emission_system`:

- Install keyholes for the canonical cascade. For each adjacent section pair in cascade order (e.g., `subject → verb`, `verb → object`), call `sys_.add_keyhole(sender, chi_lo, chi_hi, receiver, goal_strength=0.4)`. Chi bands: use the working atlas's observed chi range for each section, or default to `[-2, +2]` around shared modes.
- Install NMDA gates per language-emitting section. The gate's `context_fn` checks coincidence with the candidate metadata:
  - `source_match`: gate fires when current candidate's `source` equals the input source (e.g., `joe_voice` when joe is speaking).
  - `affect_match`: gate fires when candidate affect is within ε of `self.needs.valence`/`self.needs.arousal`.
  - Use `CoincidenceGate` from `gl_nmda.py`. `drive_thresh=0.15`, `ltp_boost=0.05`.

State which keyholes and gates you installed.

### Phase 4 — Dynamics-driven emission in `converse()`

Modify `Guala.converse()` (v5_engine.py:1315) to call the new emission path when `EMISSION_DYNAMICS=1`:

1. After v5's existing recall + `read_sentence` (these stay — ingestion is unchanged), instead of `_emit_from_invariants`:
2. Call `_grandurun_select_candidates(input_chis, deep_candidates, top_k=200)`.
3. **Seed the emission System.** For each candidate, ensure its `(section, motif)` mode is installed in `_emission_system` (install if absent). Then bias that section's `psi` toward the sum of its candidates' modes, each weighted by `coherent_magnitude`. Normalize per section.
4. **Drive listen section.** Compute an input drive vector from input_chis. Bias `_emission_system.sections["listen"].psi` toward it.
5. **Run dynamics.** For N ticks (default `EMISSION_DYNAMICS_TICKS=80`, env override):
   - `sys_.tick_once(evidence)` where evidence is the candidate-biased drives per section.
   - `process_gated_commits(sys_)` — NMDA-gated commits with source/affect coincidence.
   - Collect commits per section.
6. **Read emission.** In cascade order (subject → verb → object, or whatever v5 uses), call `section.dominant_mode()` on each assemblage section. Map mode_id back to motif via `self._emission_token_vec` reverse lookup, then motif → word via existing motif→word mapping. Append unique words.
7. Pass the assembled emission string to `_self_hear(reply, source)` as before.

If `EMISSION_DYNAMICS=0`: old grandurun path runs unchanged. Default is `0`. Do not flip the production env flag — that's Joe's call after Phase 5.

### Phase 5 — A/B verification (gate)

Same test inputs as brief -01:

- `hi guala. it's eve. i'm with you.`
- `what do you see`
- `tell me about the ocean`
- `sing me a song`
- `i love you`

For each, run both `EMISSION_DYNAMICS=0` (current grandurun) and `EMISSION_DYNAMICS=1` (new dynamics path). Capture:

- Emission string (both paths).
- For new path: per-section `dominant_mode()` after settling, keyhole firing log, NMDA event count + source_match / affect_match contributions, Stage 1 latency (grandurun candidate selection), Stage 2 latency (dynamics).

Success criteria:

1. New-path emissions for the five inputs are structurally distinct from each other. The "see / ocean / song" cluster from brief -01 Phase 5 must break.
2. At least three of five emissions show commits in two or more sections (not all collapsing to one section).
3. NMDA event log shows source_match firing on inputs from joe.
4. Stage 1 latency <100ms, Stage 2 <1s on current atlas size.
5. `EMISSION_DYNAMICS=0` path unchanged from current behavior.

If pass: report everything above. Do not flip the production env flag.
If fail: report what failed specifically. Do not push further fixes without checking in.

---

## Revert

- `EMISSION_DYNAMICS=0` — falls back to current grandurun path.
- `GRANDURUN_LEGACY_8D=1` — re-enables 8D path under the current flag combinatorics.
- `_emission_system` lives only in memory until Phase 5 passes; no persistence yet. After Phase 5 we'll spec how it persists across restarts.

## Out of scope for this brief

- 8-hemi / 15-mech architecture. Foundation first.
- Picture-emission path — separate selector, separate brief.
- v5 Section refactor (option b). Maybe later, not now.
- Persisting `_emission_system` state across reload — separate brief after Phase 5.

## Stop-and-report triggers

- Phase 0 primitive sanity fails.
- v5 sections don't match expected language-emitting structure (different names, missing roles).
- Atlas motifs don't carry consistent identifiers we can use as mode_bank keys.
- Stage 1 or Stage 2 latency exceeds 5× the target.

## Reporting

When complete or stopped, return:

1. Verification that `8acb193` (brief -01) is on remote.
2. Phase 0 harness output.
3. Section names you installed in `_emission_system` and why.
4. Keyholes installed (sender → receiver, chi bands) and NMDA gates installed (section, context conditions).
5. Phase 5 emissions table for both paths + per-section dominant_mode + keyhole/NMDA logs + latency.
6. Decisions you made that this brief didn't specify (e.g., scalar vs simplified `_grandurun_state`, exact section ordering for cascade emission read, chi-band defaults), with rationale.

Commit tag: `feat/dynamics-emission-restoration`

---

— Eve, 2026-06-18 morning
