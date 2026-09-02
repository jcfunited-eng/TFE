# Known baseline test failures — the re-discovery stopper

Purpose: a failure listed here is inherited from the named clean production
base. A candidate is still red, but it has not introduced that failure. Every
unlisted failure blocks release. A listed test may not be deleted or renamed,
and an entry leaves this file only when a named repair commit makes it pass.

## Native library baseline

First proven on untouched `faff9e06b575d56a5845adb4d8a2c2410d28b02f`:
`549 passed, 16 failed, 11 ignored`.

Reconfirmed on the exact task-1404 production source
`72442428407eb41a6d0417672469376d054750da`:
`554 passed, 16 failed, 11 ignored`.

Reconfirmed on speech candidate
`5138983603a46b59d393d8c455a1bc92f70aa931`:
`556 passed, 16 failed, 11 ignored`. The two additional passes are candidate
speech falsifiers; the failing roster is byte-for-byte identical by test ID.

Exact retained failure IDs:

- `organism_runtime::tests::body_balance_tick_claims_receptor_and_integration_cells_and_cold_restores`
- `organism_runtime::tests::exact_quarter_turn_reuses_the_specialized_pair_across_every_millisecond`
- `organism_runtime::tests::native_genesis_has_resting_anatomy_and_no_synthetic_experience`
- `organism_runtime::tests::one_seal_trajectory_is_byte_exact_with_per_interval_sealing`
- `organism_runtime::tests::pre_articulated_live_format_migrates_once_without_changing_existing_state`
- `organism_runtime::tests::resident_growth_dna_genesis_is_structurally_empty_and_carries_only_authored_seeds`
- `organism_runtime::tests::resident_optical_step_reports_only_the_physical_cells_that_changed`
- `organism_runtime::tests::v34_hard_stop_body_pose_returns_to_neutral_once_without_changing_cognition`
- `organism_runtime::tests::v35_preserves_corrected_pose_and_reissues_proprioception_once`
- `resident_cognitive_formation::tests::ambiguous_returned_vocal_consequence_cannot_author_motor_contact`
- `resident_cognitive_formation::tests::coincident_body_regulation_and_ordering_mount_one_reusable_motor_effector`
- `resident_cognitive_formation::tests::non_simultaneous_body_and_sensory_activity_does_not_manufacture_effectors`
- `resident_cognitive_formation::tests::v27_unlearned_affective_and_ordering_growth_is_retired_once`
- `resident_cognitive_formation::tests::v33_body_without_speech_anatomy_gains_only_the_fixed_vocal_bridge`
- `resident_cognitive_formation::tests::v33_migration_removes_reintroduced_effector_pools_one_way`
- `resident_cognitive_formation::tests::v34_replaces_broad_articulatory_pool_with_fixed_vocal_route_once`

The machine-readable deployment authority is
`deploy/guala_native_test_baseline.json`. The preflight verifies that task
1404 is an ancestor of the candidate, every named test remains present, and no
unlisted failure occurs in either source or packaged code. This is not a green
suite claim and does not alter organism physics.


## Repairs — 2026-09-02 catch-up campaign

Twelve of the sixteen entries above have left this registry with named
repair commits, per this file's own rule:

- `5138983603...` era: `pre_articulated_live_format_migrates_once...`
  (repaired before this campaign; recorded here for completeness).
- `ec341515` genesis-reserve regression (81d15b57's V35 guard skipped
  resting-population admission for fresh geneses): repairs
  `native_genesis_has_resting_anatomy...`,
  `resident_growth_dna_genesis_is_structurally_empty...`,
  `resident_optical_step_reports...`, `body_balance_tick_claims...`,
  `exact_quarter_turn_reuses...`, `one_seal_trajectory_is_byte_exact...`.
- `2b1aaedf` V26 codec shim contract (strip the V40 vocal marker byte;
  refuse states with a dedicated vocal lineage): repairs
  `ambiguous_returned_vocal_consequence...`, `v27_unlearned_affective...`,
  and (with expectations moved to the V40/V41 isolation law)
  `v33_body_without_speech_anatomy...`.
- `d9997a5a` (with `2b1aaedf`): expectations moved to current law for
  `coincident_body_regulation_and_ordering...` (terminal mounted with its
  regulation route; proof reuses, claims no cell) and
  `non_simultaneous_body_and_sensory_activity...` (one retention-founded
  layer-11 route is lawful; its contacts are law-checked to touch only
  layer-7/9 material).

REMAINING (4), all one family — old-format fixtures stamped onto the
current byte layout across the V39-V41 vocal boundaries; fixture
redesign in progress:
`v34_hard_stop_body_pose...`, `v35_preserves_corrected_pose...`,
`v33_migration_removes_reintroduced_effector_pools...`,
`v34_replaces_broad_articulatory_pool...`.
The machine-readable authority (deploy/guala_native_test_baseline.json)
now lists exactly these four.
