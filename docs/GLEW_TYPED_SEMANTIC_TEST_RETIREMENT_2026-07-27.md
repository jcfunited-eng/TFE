# GLEW typed-semantic test retirement — 2026-07-27

## Scope

This is a test-only retirement record. No production sensory boundary,
L0–L4 kernel, full DSF field, hearing path, or L6 implementation was changed
by this retirement.

The production somatic boundary now correctly fails closed when callers offer
semantic labels such as `warm`, `floral`, or `sweet` without physical material,
transport, contact, and receptor evidence. The files below exclusively test
the retired typed-semantic `CleanConversation` lineage or build their fixtures
through that lineage.

## Whole obsolete test files

1. `tests/glew_runtime/test_clean_conversation_engine.py`
   - Tests `ProductionCleanConversationEngine` and constructs experience from
     typed characters plus semantic somatic descriptors.
2. `tests/glew_runtime/test_deferred_turn_persistence.py`
   - Imports and drives the retired CleanConversation fixture and typed-turn
     persistence transaction.
3. `tests/glew_runtime/test_expression_mode_growth_arbiter.py`
   - Imports the retired CleanConversation fixture and drives expression growth
     from typed scalar turns.
4. `tests/glew_runtime/test_live_boundary_episode_adapter.py`
   - Mints its claimed live episode through the retired six-sense boundary
     using the semantic touch descriptor `warm`.
5. `tests/glew_runtime/test_multi_scalar_turn_scheduler.py`
   - Tests the explicitly typed-language Unicode-scalar scheduler around
     `ProductionCleanConversationEngine`.
6. `tests/glew_runtime/test_production_runtime_bootstrap.py`
   - Bootstraps and restores the retired `ProductionCleanConversationEngine`
     and its typed/semantic experience pipeline.
7. `tests/glew_runtime/test_real_end_to_end_recall_pipeline.py`
   - Builds recall through the retired `real_experience_learning_pipeline`,
     whose six-sense fixture uses semantic somatic descriptors.
8. `tests/glew_runtime/test_real_experience_learning_pipeline.py`
   - Directly tests the retired typed-language and semantic six-sense
     experience-learning pipeline.
9. `tests/glew_runtime/test_recall_basin_reconciliation_end_to_end.py`
   - Imports and drives the retired CleanConversation fixture and typed recall
     emission route.
10. `tests/glew_runtime/test_recall_settlement_cycle_bound.py`
    - Bootstraps `ProductionCleanConversationEngine` to exercise its retired
      typed recall settlement route.
11. `tests/glew_runtime/test_reproducible_experience_identity.py`
    - Imports the retired CleanConversation fixture and verifies identities for
      its typed/semantic scene construction.
12. `tests/glew_runtime/test_seed_first_production_successor.py`
    - Seeds and drives the retired `ProductionCleanConversationEngine`
      successor and typed scalar scheduler.
13. `tests/glew_runtime/test_six_sense_boundary_owner.py`
    - Treats semantic strings such as `warm` and `floral` as somatic evidence,
      directly contradicting the physical sensory evidence boundary.

## Mixed file: one stale case only

`tests/glew_runtime/test_receipt_registry_extend_incremental.py` contains active
receipt-registry correctness and digest-collision proofs that remain valid.
Only
`test_engine_per_turn_cost_plateaus_as_threaded_registry_grows`
is retired because it imports and benchmarks the obsolete
`ProductionCleanConversationEngine` fixture. The complete test file is replaced
to preserve the active proofs and remove that one stale case.

## Reachability confirmation

The serving application, substrate runner, Gualaloom V5 engine, and current
Gualaloom engine do not import `ProductionCleanConversationEngine`,
`bootstrap_production_clean_conversation_engine`,
`real_experience_learning_pipeline`, or
`live_boundary_episode_adapter`.

The authoritative retirement proof remains
`tests/glew_runtime/test_somatic_boundary.py`: semantic and empty requests
cannot mint sensory evidence.
