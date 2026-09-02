# Known baseline test failures — the re-discovery stopper

PURPOSE (Joe, 2026-09-01, after paying twice to baseline the same debt):
any test failure listed here is INHERITED — already failing on the named
clean base commit before the change under review existed. A review diffs
its failures against this file: red-and-listed is old debt (leave it red,
never paint green, never side-quest it mid-incident); red-and-NOT-listed
is new damage and blocks the change. Add entries only with the exact test
id and the clean base commit it reproduces on. Remove entries only when
the failure is actually fixed, with the fixing commit named.

## Entries

- NAMED 2026-09-02 (Claude), reproduced on clean production 44347ee1
  (task 1408), 556 passed / 16 failed. The 16 exact ids:
  organism_runtime::tests::{body_balance_tick_claims_receptor_and_integration_cells_and_cold_restores,
  exact_quarter_turn_reuses_the_specialized_pair_across_every_millisecond,
  native_genesis_has_resting_anatomy_and_no_synthetic_experience,
  one_seal_trajectory_is_byte_exact_with_per_interval_sealing,
  pre_articulated_live_format_migrates_once_without_changing_existing_state,
  resident_growth_dna_genesis_is_structurally_empty_and_carries_only_authored_seeds,
  resident_optical_step_reports_only_the_physical_cells_that_changed,
  v34_hard_stop_body_pose_returns_to_neutral_once_without_changing_cognition,
  v35_preserves_corrected_pose_and_reissues_proprioception_once}
  resident_cognitive_formation::tests::{ambiguous_returned_vocal_consequence_cannot_author_motor_contact,
  coincident_body_regulation_and_ordering_mount_one_reusable_motor_effector,
  non_simultaneous_body_and_sensory_activity_does_not_manufacture_effectors,
  v27_unlearned_affective_and_ordering_growth_is_retired_once,
  v33_body_without_speech_anatomy_gains_only_the_fixed_vocal_bridge,
  v33_migration_removes_reintroduced_effector_pools_one_way,
  v34_replaces_broad_articulatory_pool_with_fixed_vocal_route_once}
  FIXED 2026-09-02 on speech/v22-valve-organ-20260902: pre_articulated_
  live_format_migrates_once (stale length expectation missing the u32
  in-flight field; commit on that branch).
- Historical: "six inherited wider-suite failures" recorded at the task
  1403 review (2026-08-31, Sol) — presumed subset of the above; confirm
  and merge when the 13 are named.

## Rule

This file is evidence bookkeeping, not cognition, not a work queue.
Fixing an entry is ordinary scheduled work, never an incident side quest.
