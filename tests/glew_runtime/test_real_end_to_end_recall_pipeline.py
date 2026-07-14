"""Real tests for the Step-5 end-to-end recall attempt (spec section 12).

See ``dsf_ai_service/glew_runtime/real_end_to_end_recall_pipeline.py``'s
module docstring for the full, precise account. Short version: real Step-4
learning and real Step-5 recall-stack construction both succeed genuinely
(``test_real_learning_and_staging_succeed_end_to_end``,
``test_real_step5_recall_stack_is_self_consistent``); bridging the two fails
closed, deterministically, at one exact, confirmed line
(``test_bridging_learned_content_into_fresh_recall_hits_the_confirmed_gap``),
because Step 4's real sensory intake (``six_sense_boundary_owner.py``) and
Step 5's only real recall-archive admission path (``story_native_replay.py``)
are two independent, non-interoperable five-sense subsystems with no shared
code and therefore no shared content-addressed receipts.
"""

from __future__ import annotations

import pytest

from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.output import OutputReason, OutputStatus, StageDisposition
from dsf_ai_service.glew_runtime.real_end_to_end_recall_pipeline import (
    build_real_end_to_end_recall_attempt,
    drive_fresh_recall_attempt,
)
from dsf_ai_service.glew_runtime.recall_reentry import RecallTransitionSettlement


@pytest.fixture(scope="module")
def real_attempt():
    return build_real_end_to_end_recall_attempt()


def test_real_learning_and_staging_succeed_end_to_end(real_attempt):
    learned = real_attempt.learning_result.learned
    learned.verify()  # independent re-verification, not just construction

    # Genuine Step-4 learning: one real learned output binding for the
    # content scene's typed scalar, tied to a real committed coexperience.
    assert len(learned.output_bank.bindings) == 1
    assert learned.output_bank.bindings[0] is real_attempt.source_binding
    assert learned.pending_relation is not None
    assert learned.terminal is False

    # Genuine staging via the real production actuator -- not a hand-built
    # settlement. Exercises this task's own Part A fix
    # (fresh_recall_executor._verify_staged_source) for the first time
    # against a real production learning pipeline's output.
    receipt = real_attempt.staged_output.receipt
    assert real_attempt.staged_output.text == ""
    assert receipt.status is OutputStatus.STAGED_PRIVATE
    assert receipt.reason is OutputReason.UNIQUE_COEXPERIENCED_LANGUAGE_BINDING
    assert receipt.stage_disposition is StageDisposition.RETAINED_PRIVATE
    assert receipt.binding_receipt_sha256s == ()
    assert receipt.event_receipt_sha256 == real_attempt.source_event.event_receipt_sha256

    # The corrected _verify_staged_source check (Part A) genuinely accepts
    # this real settlement -- prove it directly, independent of the
    # cross-universe attempt below.
    from dsf_ai_service.glew_runtime.fresh_recall_executor import (
        FreshRecallClosedExperienceExecutor,
    )

    executor_stub = object.__new__(FreshRecallClosedExperienceExecutor)
    executor_stub._verify_staged_source(
        source_event=real_attempt.source_event,
        staged_output=real_attempt.staged_output,
        source_binding=real_attempt.source_binding,
        receipt_registry=real_attempt.learning_registry,
    )


def test_real_step5_recall_stack_is_self_consistent(real_attempt):
    stack = real_attempt.recall_stack
    context = real_attempt.recall_context

    # Every real Step-5 authority independently re-verifies -- not "no
    # exception was raised" but genuine byte-for-byte re-derivation.
    stack.episode.verify()
    stack.checkpoint.verify()
    stack.language_interface.verify(stack.checkpoint_registry)

    runtime = stack.resolver.resolve_runtime(
        episode=stack.episode,
        receipt_registry=stack.checkpoint.receipt_registry,
    )
    assert runtime.episode_receipt_sha256 == stack.episode.episode_receipt_sha256
    assert runtime.topology.authority_receipt_sha256 == context.topology.authority_receipt_sha256

    # The integrity provider itself is a stateless, real, independently-typed
    # object (ProductionRecallReplayIntegrityProvider) -- its own dedicated
    # test module (test_recall_replay_integrity_provider.py) already proves
    # mount_integrity's tri-state contract in full against a prepared
    # StoryGlobalUFBasinPreparation replay context, which only the executor
    # constructs internally; this test asserts the pieces that stand on
    # their own without needing that internal preparation.
    assert stack.integrity_provider is not None

    assert stack.archive.receipt_sha256  # real, computed, non-empty digest
    assert stack.episode.profile_binding_sha256 == context.profile.authority_receipt_sha256


def test_bridging_learned_content_into_fresh_recall_hits_the_confirmed_gap(real_attempt):
    """The precise, reproducible Step-4/Step-5 architecture gap.

    Step 4's real learned binding and Step 5's real recall archive are
    genuinely, structurally incompatible: different profile bindings, and
    completely disjoint sensory-evidence receipt sets (content-addressed
    from two independent sensing code paths). Assert the disjointness
    directly, then assert the real production call fails exactly there.
    """

    learned_profile = real_attempt.source_binding.profile_binding_sha256
    archived_profile = real_attempt.recall_stack.episode.profile_binding_sha256
    assert learned_profile != archived_profile

    learned_sensory = set(real_attempt.source_binding.sensory_evidence_receipt_sha256s)
    archived_sensory = set(
        real_attempt.recall_stack.episode.sensory_evidence_receipt_sha256s
    )
    assert learned_sensory
    assert archived_sensory
    assert learned_sensory.isdisjoint(archived_sensory)

    with pytest.raises(
        ReceiptError,
        match="no episode has this exact profile and complete sensory receipt set",
    ):
        drive_fresh_recall_attempt(real_attempt)


def test_recall_transition_settlement_type_is_importable():
    # RecallTransitionSettlement is the real success type drive_fresh_recall_attempt
    # would return if the gap above were ever closed -- imported here so any
    # future fix to this exact test module has the type already in scope.
    assert RecallTransitionSettlement is not None
