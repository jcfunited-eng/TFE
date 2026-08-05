# Hearing-scoped kernel change validation gate v1

Status: validation design only. No L0-L4 change is authorized by this
document. A hearing operator must first be proven at an exact loss boundary.

## Architecture honesty

- Requested architecture: permit the smallest hearing-scoped kernel change
  that is proven necessary for experience-grown word distinction.
- Current code reality: one shared `uf_core` implementation serves financial,
  auditory, thermal, physiological, and other temporal inputs. There is no
  versioned hearing profile in the kernel today.
- Conflict: yes, if a domain label alone changes L0-L4 behavior. A change is
  admissible only when an exact physical input structure selects a versioned
  operator at the proven loss point and the default operator remains bit
  identical.
- Mechanisms that must not be extended: sign/ray/order quotient identity,
  flattened compatibility vectors, weighted scores, tolerance matching,
  lookup tables, ML, transcript authority, and silent persistence migration.
- Field authority: the complete ordered
  `D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k` surface. No reduced
  approximation is accepted.

## Frozen baseline

The machine-readable baseline is
`tests/fixtures/uf_kernel_backward_compatibility_baseline_v1.json`.

- Canonical commit: `6509971e987d4a1f161ffcfcadc3ec68568322c6`
- Seven-file active kernel bundle:
  `c8b95decde72946e2beccc8513f9d64f7bfc6b58e5736edb3fffd54b4749357b`
- Cross-domain behavioral bundle:
  `f270be00b01d0941a2d8eb508965c108061f907f04beb6431d57b7f37cb3272a`
- Current baseline test:
  `tests/test_uf_kernel_backward_compatibility_baseline.py`
- Current Python/native and relevance checks: 15 passed.

The existing native differential suite does not directly compare the
`uf_core` L0-L4 implementation. The new baseline test therefore records exact
L0, L1, L2, L3, and L4 outputs using binary64 hexadecimal text for financial,
thermal, physiological, adapted signed-sensor, and quiescent inputs.

The current full-field hearing census is also frozen:

- report: `/tmp/guala_full_field_hierarchical_census_v1.json`
- report SHA-256:
  `d0840d854f7c5b0da425acbd44198bd3fa4ea9a61ab48ba276b8e6f7c3f0c8dd`
- embedded authority:
  `f6e0479b1467d828ff993e5b6d54ce2fd7823ce5e2e21acf8779c0e9b0e84ac1`
- corpus SHA-256:
  `49650f2341b26d886b46b3f4fb8fed59e30300b17550f1ee4a768b3106cf93a0`
- 64 source-disjoint speakers, eight commands, five reference and three
  held-out speakers per command.
- Each of the three tested full-field quotients produced 0/224 same-command
  locks, 0/1792 cross-command locks, and 0/24 held-out passes.

This is falsification evidence. It prohibits promoting those quotients; it is
not a passing word-recognition baseline.

The isolated physical-stereo seam adds a second frozen audit:

- authority: `tools/isolated_w1_physical_stereo_path.py`
- contract fixture:
  `tests/fixtures/auditory_bilateral_nonflattening_contract_v1.json`
- executable contract:
  `tests/test_auditory_bilateral_nonflattening_contract.py`
- controlled flank paths: `(left delay 10, right delay 14)` and its
  `(14, 10)` mirror, with exact unit attenuation.
- one complete transaction retains left topology 0-31 and right topology
  32-63.
- current nonidentical-ear difference counts are 32 at L0, 32 at L1, 16 at
  L2, 14 at L3, and 14 at L4.

Those counts localize inquiry points; they do not prove that the L2/L3
equalities are wrong. Five strict fail-first tests remain expected failures
until a transaction-level bilateral audit can issue and verify exact symmetry,
collapse, quiescence, and topology receipts. They run as ordinary `xfail`
tests in the suite. `pytest --runxfail` exposes all five as real failures so
the missing authority cannot be mistaken for implemented behavior.

The measured collapses are exact and localized:

- The 16 odd local component indices are carrier-phase-advance ports. Each
  has one L1 gate in this fixture. At L2, per-port centering and normalization
  therefore produce the same zero CV, unit density weight, stability,
  uncertainty, and regime for left and right even though their L1 records
  differ.
- Local component 28 is `erb_14_pressure` (left topology 28, right topology
  60) and local component 30 is `erb_15_pressure` (left 30, right 62). Their
  L2 CV magnitudes differ. At L3, each port normalizes its CV norms by its own
  maximum; their normalized two-gate pattern and all other L3 inputs become
  identical, so `R_k`, `URF_k`, and L4 become identical.

These may be legitimate exact normalization collapses. The present contract
requires the future transaction-level audit to name and receipt that
explanation; it does not silently declare the operators defective.

## Invariants by layer

### L0

1. Input health remains fail-closed for missing columns, non-monotonic
   indices, NaN, and non-finite values.
2. The default transform remains `log(F + 1e-8)`.
3. Sample cardinality and order remain unchanged.
4. `dF`, rolling variance, curvature, and negative-space `N` remain exact
   under the existing 20-sample variance window and named thresholds.
5. Default relevance remains `legacy_unit`; physical sensory relevance may
   only enter through the already explicit adapter authority.
6. No hearing operator may rewrite or discard raw source support.

### L1

1. Gates remain contiguous, ordered, exhaustive, and non-overlapping.
2. The default boundary remains strict `D(t) > 0.20`.
3. TVR, lattice projections, mosaic divergence, drift, and negative-space
   flags retain their formulas, cardinalities, and values for default inputs.
4. Gate identity is identical across L1-L4.

### L2

1. Every `GateInterpretation` field remains present.
2. Density, normalized weight, centered TVR, stability, uncertainty, IAS,
   regime, mosaic divergence, drift, and negative-space values remain exact.
3. Existing clamps and threshold inequalities remain unchanged.

### L3

1. Resonance remains the normalized five-term field relation.
2. Hysteresis, uncertainty/IAS gating, `R_k`, `URF_k`, `g_k`, and `raw_k`
   remain exact for the default operator.
3. A proposed operator must identify the exact L3 information absent before
   it may add a new state or relation.

### L4

1. One ordered DSF tuple remains attached to every gate.
2. Direction, momentum, reversal, uncertainty, cohesion, pressure, and
   breathing remain explicit and unflattened.
3. Existing directional epsilon, uncertainty amplification, breathing
   dynamics, clamps, and initial conditions remain unchanged by default.
4. Optional hardening remains outside the authoritative DSF path.

### Cross-layer and receipt invariants

1. Determinism means identical typed input, profile, and prior state produce
   identical gates, values, canonical bytes, and receipts.
2. Complete trace schemas v3 and v4 remain readable and retain their original
   meaning.
3. Every field tuple remains linked to source indices and its L0-L4 trace.
4. All 64 auditory components remain present: 32 cochlear pressure and 32
   carrier-phase components, each with complete tuple support.
5. Missing, corrupted, discontinuous, or unauthenticated evidence fails
   closed; it never selects a nearest class.

## Auditory bilateral non-flattening inquiry contract

This contract is an inquiry trigger, not a rule that left and right must
always differ. Flat or identical output is legitimate when physics and the
declared operator prove it. Equality becomes a failure only when authenticated
physical asymmetry entered a layer, its output became equal, and no exact
legitimate receipt explains that collapse.

### Law 1 — symmetry conservation

Byte-identical physical inputs under identical authenticated calibration,
topology, source interval, and prior state must remain identical. The kernel
may not invent an ear difference. The audit records an exact
`identical_physical_input` receipt and verifies zero difference at every
applicable layer.

### Law 2 — physical asymmetry preservation

Authenticated nonidentical left/right pressure caused by propagation delay,
attenuation, head, pinna, room, or source geometry must produce a traceable
nonidentical receptor/full-field witness. A later layer may become equal only
when an exact declared operator proves that the two inputs occupy the same
legitimate equivalence class.

### Law 3 — per-layer loss accounting

For L0, L1, L2, L3, and L4 the audit records:

- ordered left and right input witness receipts;
- an exact difference witness receipt;
- ordered left and right output witness receipts;
- an output difference witness receipt;
- the operator/profile receipt;
- one disposition:
  `difference_preserved`, `symmetry_conserved`,
  `static_quiescent_equal`, or `declared_exact_collapse`.

Whenever a nonzero input difference becomes zero, the disposition must be
`static_quiescent_equal` or `declared_exact_collapse` and must carry the exact
support and operator receipt that proves why. Silent flattening is invalid.
Whenever a zero input difference becomes nonzero, symmetry conservation has
failed.

### Law 4 — topology preservation

Left, right, and explicitly bilateral ports remain distinct, ordered, and
receipt-bound through every layer. No layer may merge, reorder, duplicate, or
substitute them. Mirrored hemisphere assemblies may change view order only
through an explicit topology receipt that retains both source orders.

### Law 5 — legitimate static or quiescent equality

Static or quiescent signals may lawfully settle to equal outputs. The equality
must be explicit: the receipt binds both source supports, calibration,
topology, the exact quiescence/static operator, and the layer at which
equality was established.

### Mandatory equality investigation

Any flat or identical bilateral output opens the same traced investigation,
even when it ultimately passes:

1. Were the authenticated input bytes already identical?
2. Were both calibrations and transfer paths identical?
3. Were left/right topology and ordering preserved?
4. Did a declared exact operator legitimately collapse the difference?
5. Was the state static or quiescent under an exact operator?
6. Did an adapter discard pressure, phase, order, timing, or support?
7. Did the test measure the full field, or only a reduced projection?

The investigation passes only with one exact supported answer. It fails when
physical asymmetry existed and equality remains unexplained. A sign, ray,
rank, score, tolerance, or label cannot serve as the explanation.

## Downstream consumer inventory

### Direct production consumers

- `dsf_ai_service/glew_runtime/closed_experience.py` calls every L0-L4 layer
  and emits the complete signed v3 or physical v4 trace.
- `dsf_ai_service/glew_runtime/native_sensory_full_field.py` and
  `exact_field_executor.py` execute that trace for all physical senses.
- `dsf_ai_service/kernel_runner.py` directly executes L0-L2.
- `uf_kernel_engine.py`, `uf_mdg_snapshot.py`,
  `real_world_cleaned_universe_l5_row_trace_export.py`, and
  `real_world_cleaned_universe_l5_primitive_only_row_trace_export.py` consume
  the structural-engine API used by financial production and replay.
- `dsf_ai_service/v4/gualaloom_v5_engine.py` consumes the receipt-bearing
  sensory path and its downstream field authorities.

### Direct financial and research consumers

- Full layer chain:
  `tfe_5year_backtest.py`, `tfe_epoch_structural_history.py`,
  `tfe_structural_register.py`, `uf_energy_entropy_phase_map.py`,
  `uf_structural_episodes_log.py`, `tools/derive_sppu_weights.py`,
  `tools/ybco_kernel_analysis.py`, and the L1-L4 phase sync tools.
- Structural-engine API:
  `tools/backfill_history.py`, `tools/backtest_ch3_v2_1.py`,
  `tools/build_dsf_historical_full_surface_snapshot_archive.py`,
  `tools/run_dsf_clean_walkforward_replay_with_symbol_memory_v1.py`,
  `tools/tp_backtest.py`, and `tools/validation_env_refresh.py`.
- Diagnostic direct callers:
  `tools/probe_auditory_pressure_adapter_scale.py`,
  `tools/probe_auditory_relevance_diagnostic_comparison.py`,
  `tools/probe_auditory_chemical_receiver_diagnostic.py`,
  `tools/phase_transition_survey.py`, and the UF anomaly documents.
- Archived/recovered callers still constrain API compatibility:
  `Archieve_2/uf_structural_engine.py` and both recovered L5 policy pipelines.

### Indirect full-field consumers

The complete trace and `DSF_FIELD_ORDER` feed Global-UF, exact causal
experience, prediction, deliberation, expression, compact auditory
persistence, receptor events, recurrent motifs, auditory L5, binaural
grounding/separation, audiovisual continuity, and the Guala engine. The
critical files are:

- `dsf_ai_service/glew_runtime/global_uf.py`
- `dsf_ai_service/substrate/exact_causal_experience.py`
- `dsf_ai_service/substrate/compact_auditory_field_authority.py`
- `dsf_ai_service/substrate/auditory_receptor_event_boundary.py`
- `dsf_ai_service/substrate/auditory_recurrent_motif.py`
- `dsf_ai_service/substrate/auditory_l4_causal_support.py`
- `dsf_ai_service/substrate/auditory_l5.py`
- `dsf_ai_service/substrate/auditory_reciprocity.py`
- `dsf_ai_service/substrate/auditory_incremental_terminal.py`
- `dsf_ai_service/substrate/auditory_motif_causal_grounding.py`
- `dsf_ai_service/substrate/w1_binaural_auditory_l5.py`
- `dsf_ai_service/substrate/w1_binaural_grounding_evidence.py`
- `dsf_ai_service/substrate/w1_exact_binaural_source_separation.py`
- `dsf_ai_service/substrate/w1_audiovisual_physical_evidence.py`

Sight, body, touch, taste, and smell share the same native full-field
executor. They are therefore non-auditory differential authorities even when
they do not import `uf_core` directly.

Packaging and identity also depend on these files:
`dsf_ai_service/Dockerfile`, `Dockerfile.nogil`, and
`dsf_ai_service/integrity.py`.

## Required version boundary

No version name is assigned until the operator is proven. Once proven:

1. The existing default profile remains the v1 authority and must reproduce
   the frozen behavioral bundle bit for bit.
2. The new operator receives a distinct immutable operator/profile ID.
3. Selection must be explicit at the authenticated physical adapter seam. A
   transcript, word label, source identity, chi, or guessed domain may not
   select it.
4. The output must carry both the operator profile and the complete source
   support. An unlabeled mixed-profile tuple is invalid.
5. Cross-profile equality is forbidden unless a separate exact relation
   proves it.

## Validation gate

Every section below is mandatory. One failure blocks promotion.

### Gate A — proven necessity and localization

- Supply two authenticated inputs that should remain distinguishable.
- Show the last layer where their complete structures differ and the first
  layer where the needed relation becomes impossible.
- Prove the proposed operator uses information available at that boundary.
- Re-run the falsified sign/ray/order/coupled-ear alternatives to establish
  that the new law is not one of them under another name.

### Gate B — backward compatibility

- The v1 source and behavioral baselines pass.
- All financial fixtures, historical row-trace fixtures, thermal,
  physiological, adapted signed-sensor, quiescent, sight, body, touch, taste,
  and smell traces remain byte/receipt identical.
- Gate counts, gate indices, every L0-L3 field, every L4 field, regimes,
  stability, and structural-engine output remain identical.
- Python/native differential tests remain unchanged.

### Gate C — full auditory structure

- Exactly 64 ordered components remain.
- Every component retains every field tuple, source interval, tuple receipt,
  causal trace, pressure/phase role, and topology index.
- The proposed operator is tested against the complete field and cannot
  accept a reduced substitute.
- Tampering with any one component, field, interval, profile, or receipt
  fails closed.
- Run the bilateral inquiry contract at L0, L1, L2, L3, and L4. Equality by
  itself is neither a pass nor a failure; the authenticated investigation
  disposition is authoritative.

### Gate D — persistence and migration

Current schemas that require explicit coverage include complete trace v3/v4,
exact causal settlement v5, compact auditory authority v2, W1 binaural L5
state v2, receptor event v1, and recurrent motif state v3.

- Existing v1-profile state cold-restores exactly under its old semantics.
- New-profile state cold-restores exactly and retains its operator ID.
- Old state is never silently relabeled as new.
- Migration to the new profile is allowed only by re-executing retained exact
  source evidence. If exact source is absent, legacy state remains legacy.
- Mixed, unknown, removed, or tampered profile IDs fail closed.
- Round trips preserve canonical bytes and authority receipts.

### Gate E — resources and cadence

- Preserve 64 components, 2 MiB compact authority, 4 MiB W1 state boundary,
  2,048 samples per substream, 32,768 samples per settlement, and all existing
  bounded capacities unless Joseph separately approves a derived replacement.
- Eight consecutive five-second authorities must each prepare in less than
  five seconds; averages do not count.
- Raw PCM is zero after commit, final restore is exact, transition capacity
  remains bounded, and repeated collection shows no monotonic RAM or storage
  growth.
- No asynchronous backlog, sample dropping, deferred verification, or
  deadline relaxation may create a pass.

### Gate F — 64-speaker held-out matrices

The present 64-speaker census is not sufficient because 40 speakers form its
reference set. The promotion matrix requires a second cohort of at least 64
speakers who were excluded from operator derivation, corpus selection, and
all tuning.

- Rows are held-out speakers; columns are authenticated utterance and room
  conditions.
- Each cell has one predeclared exact expected state: recognized causal kind,
  unknown, ambiguous, or indeterminate resource.
- Conditions include repeated exposure, gain/distance, tempo, dialect,
  arbitrary non-speech room sounds, silence, reverberation, and physically
  resolvable overlapping speakers.
- Recognition must use learned physical experience only. Labels are exposed
  after structural decisions solely to score the matrix.
- Every cell must match its declared state. No percentage threshold,
  similarity tolerance, or majority score can hide a failure.
- The full confusion and refusal matrices, corpus hash, split authority, and
  operator receipt are persisted.

### Gate G — unknown and ambiguous truth

- Unheard words and unrelated sounds remain unknown.
- Incomplete or discontinuous events remain unknown.
- Structurally conflicting learned outcomes are ambiguous.
- Spatially symmetric or physically underdetermined mixtures are ambiguous.
- Resource exhaustion is indeterminate, never unknown-as-recognized.
- A resolvable overlap may release separate source lineages only when each
  lineage has independent physical support.

### Gate H — real browser and production-shaped path

- Use a real Chromium microphone path through
  `/api/v1/auditory/binaural-pcm/open`, `/lineage`, `/chunk`, and `/close`.
- Prove the browser sends physical PCM and does not inject transcript,
  tutor text, word IDs, or observational STT into cognition.
- Verify the exact operator/profile and full-field receipts returned by the
  live engine path.
- Exercise two simultaneous voices plus arbitrary room sounds.
- Cold-restart the production-shaped process and repeat recognition,
  unknown, and ambiguous cases from restored state.
- Verify truthful Loom Scan display separately from causal hearing.

Deployment is outside this gate document and remains prohibited until every
local gate passes and a reviewed saved commit exists.

## Exact next item

Wait for the loss-localization lane to provide one proven operator with its
exact layer, equation, typed inputs, typed outputs, and falsification record.
Then bind that operator—not a provisional substitute—to Gates A through H.
