# Night shift 2026-08-05 — state, decisions, evidence (Claude)

Working tree: the salvaged Codex worktree. Branch `salvage/codex-d3-work-20260805`;
durable copies: GitHub `salvage/codex-d3-snapshot-20260805` (workflow files relocated
to docs/salvaged-github-workflows/) and S3
`dsf-ai-site-backups/guala-salvage/salvage-codex-d3-20260805.bundle` (exact original).

## Proven tonight
1. **Kernel is bit-true to spec.** The joint UF v1.4 kernel was compared against a
   fully independent implementation written from `UF_Spec_v1_4_0_skeleton` alone
   (agent never saw the Rust). All 159 frozen values (6 SEV frames × 9, 5 gates × 21,
   plus every discrete flag) agreed bit-for-bit under declared bounds [-1,1]^2,
   max gate interval 100. Oracle fixture refrozen accordingly; passes.
2. **Frozen Python kernel did NOT drift.** All 7 pinned `uf_core/*` sources match
   their baseline sha256 exactly. `test_uf_kernel_backward_compatibility_baseline`
   fails only because its bundle digest includes the machine-specific ABSOLUTE path
   (test defect; fix = digest relative paths + refreeze bundle hash).
3. **Native suite** 267/268 after migrating 36 fixtures to the mandatory-admission
   law (no production code or assertions changed). The 1 failure is the genuine
   genesis-contacts defect (below).
4. **Release manifest completed** — 26 missing native modules added (build-breaking
   omission); canonical JSON verified with the packager's own reader.
5. **Live pages fixed at the CDN**: dsf-ai.com had ONE origin (S3 static) and zero
   API routing; added ALB origin + `/api/*` behavior (CachingDisabled/AllViewer).
   Verified live. Config backup in S3 guala-salvage/. The currently-live page (79K)
   matches the currently-deployed app's endpoints; the salvage-tree page (54K,
   polls /api/v1/guala/native-observation) matches only the NEW native surface.

## Genuine defects found (and ownership)
- **Genesis-contacts**: production genesis uses `ResidentCognitiveFormationState::default()`
  → no developmental electrical seeds → grown cohorts get zero contacts → mosaics can
  NEVER form from a production birth. Fix in flight (agent): seeded genesis carrying
  AUTHORED growth-DNA (never inferred, per developmental_electrical_anatomy doctrine),
  new pyfunction `create_native_resident_organism_runtime_with_growth_dna`, honest fix
  of the failing cold-publish test, plus birth→mosaic end-to-end test.
- **D1 (live-path, proven on /sound_frame)**: 13 production call sites never migrated
  to the mandatory `occurrences` argument of build_six_sense_full_field — every live
  audiovisual window settlement dies. Fix in flight (agent) incl. the live seam at
  guala_physical_runtime_core.py:11489.
- **D2**: app.py masks settlement failures (None deref at app.py:2500) — truthful
  guard in flight.
- **D3**: deploy script lost the ratified 5 GiB storage-ceiling taskdef pin — restore
  in flight.
- **Python test estate**: 692 failures triaged → ~104 retired-legacy (delete/retarget
  anti-resurrection guards), ~360 mechanical admission migrations (agent in flight),
  ~272 were the D1 production defect, ~10 environment-only.

## Architecture decisions taken tonight
- **Serving surface for first honest deploy**: the legacy `app.py` surface (it holds
  the ONLY working sensory intake driving the organism via
  `_advance_native_materialized_fabric` prepare/commit with receipts). The Dockerfile
  currently CMDs `native_production_app:app`, which deliberately answers
  "not_mounted" for every sense — honest but dead. Plan: CMD → app.py surface, and
  port native_production_app's `/api/v1/guala/native-observation` (+ readiness proof)
  into app.py reading the LIVE mounted organism, so both UI pages work. Verify
  health-check paths + preflight expectations at packaging time.
- The legacy owner cascade still runs beside the organism in the same transaction
  (`owner.settle` after `_advance_native_materialized_fabric`). NOT a blocker for the
  first deploy; its removal is the next milestone after D3 ships (this is the
  25M-call amplifier).

## Next steps (in order)
1. Land the three in-flight agent repairs; verify full native + Python suites myself.
2. Growth-DNA authorship at the two genesis call sites in guala_physical_runtime.py
   (anatomy episode from the app's declared sensory ports; authored chain contacts).
3. app.py: native-observation + readiness routes; stale transition label
   ("joint_field_delivery_without_neuronal_cognition") corrected to truthful state.
4. Dockerfile CMD decision applied; packaging rehearsal
   (tools/package_guala_release.py), preflight, deploy via existing CodeBuild/ECS
   machinery; live verification incl. teaching evidence per the D3 contract.
5. Fix the baseline test's absolute-path digest (relative + refreeze).
6. After first deploy: legacy owner-cascade retirement plan.

## Post-deploy fix queue (live, non-blocking)
1. native_production_app "recall" section hardcodes partial_cue_reassembly_count=0
   instead of reading the native observation's real value — truth-coupling bug;
   fix in next deploy alongside the partial-cue lesson mode.
2. Per-response lesson counts are last-hop-only; surface cumulative per-lesson
   sums (fractals/transitioned) in the teach-card response.
3. Hippocampal navigation (read) has no Python binding — needed later for
   truthful recall observation; write path already lawful via prepare_admitted.
4. Per-hop whole-body persistence (~7MB x 60 hops = ~400MB written per
   lesson; ~4s overhead is fine but the write volume violates leanness):
   persist once per lesson with the same never-serve-unpersisted guarantee.
5. Cards are two-sense (sight+tutor audio); the card TOUCH surface is not
   mounted — register per Joe 2026-08-05; closes with touch receptor work.
6. STRUCTURAL CAP (Joe's reserved concern, recorded sharply): DNA
   expression is built but uncatalyzed at every call site — neuron count
   is capped at birth anatomy (29) until expression gets a real catalyst
   source. Part of the metabolism/intake design.
