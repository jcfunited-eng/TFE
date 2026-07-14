"""End-to-end conformance for the real, production first-learned-expression
pipeline (``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-
20260713-v1.md`` section 12, Step 4).

Unlike ``tests/glew_runtime/test_expression_learning.py``'s ``learning_world``
fixture -- which hand-synthesizes ``SealedClosedExperience``/
``CommittedCoexperience`` inputs -- this test drives the actual production
functions built by Steps 1-3 of this effort (``six_sense_boundary_owner``,
``story_chemistry``, ``six_lane_runtime_mount``, ``closed_experience``,
``expression_modes``, ``commit``) through two genuinely independent, real
multimodal scenes, and only then calls the real, unmodified
``expression_learning.learn_committed_binding_transaction``.

The literal Step 4 proof: learn one real multimodal expression, checkpoint
it, restore it, and confirm the restored receipts are bit-identical to the
original -- without any legacy import.
"""

from __future__ import annotations

import json

import pytest

from dsf_ai_service.glew_runtime.expression_learning import (
    learned_binding_checkpoint_payload,
    restore_learned_binding_checkpoint,
)
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.real_experience_learning_pipeline import (
    RealMultimodalLearningResult,
    close_real_multimodal_expression,
    learn_one_real_multimodal_expression,
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@pytest.fixture(scope="module")
def real_learning_result() -> RealMultimodalLearningResult:
    return learn_one_real_multimodal_expression(scenario_id="test-real-learning")


def test_two_real_independent_scenes_commit_and_learn(
    real_learning_result: RealMultimodalLearningResult,
) -> None:
    """Both real scenes genuinely committed (real conjunction, not a stub),
    and the content scene's real typed scalar was learned as the first
    successor of the clean genesis state."""

    from dsf_ai_service.glew_runtime.commit import CommitStatus
    from dsf_ai_service.glew_runtime.output import MotifEventKind, OutputBindingKind

    result = real_learning_result
    assert result.root_committed.commit.status is CommitStatus.COMMIT
    assert result.content_committed.commit.status is CommitStatus.COMMIT
    assert (
        result.root_committed.selected_mode.receipt_sha256
        != result.content_committed.selected_mode.receipt_sha256
    )

    learned = result.learned
    learned.verify()
    assert learned.initial_event is not None
    assert learned.initial_event.event_kind is MotifEventKind.CONTENT
    stable = learned.stable_bank.resolve_unique(
        result.root_committed.selected_mode.source_expression.field_evaluation_identity_sha256,
        learned.receipt_registry,
    )
    assert stable.motif_receipt_sha256 == learned.initial_event.motif_receipt_sha256
    bindings = learned.output_bank.for_motif(stable.motif_receipt_sha256)
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.kind is OutputBindingKind.LANGUAGE_SCALAR
    assert binding.trits == result.content_language.event.trits


def test_learned_expression_survives_checkpoint_restart_bit_identical(
    real_learning_result: RealMultimodalLearningResult,
) -> None:
    """The literal Step 4 proof: learn one real multimodal expression,
    checkpoint it, restore it (a fresh process would call only
    ``restore_learned_binding_checkpoint``, never re-deriving or replaying
    the original scenes), and confirm the restored receipts are exactly
    bit-identical -- no legacy import, no re-synthesis."""

    learned = real_learning_result.learned
    key = bytes(range(32))
    checkpoint = learned_binding_checkpoint_payload(
        state=learned,
        checkpoint_id="test-real-learning-checkpoint",
        authentication_key=key,
        key_id="test-real-learning-key",
    )

    restored = restore_learned_binding_checkpoint(
        checkpoint_payload=checkpoint,
        authentication_key=key,
        expected_key_id="test-real-learning-key",
    )

    assert restored == learned
    assert restored.receipt_sha256 == learned.receipt_sha256
    assert restored.receipt_payload == learned.receipt_payload
    assert restored.receipt_registry.records == learned.receipt_registry.records
    restored.verify()

    envelope = json.loads(checkpoint)
    envelope["body"]["checkpoint_id"] = "test-real-learning-tampered"
    tampered = _canonical_bytes(envelope)
    with pytest.raises(ReceiptError, match="authentication failed"):
        restore_learned_binding_checkpoint(
            checkpoint_payload=tampered,
            authentication_key=key,
            expected_key_id="test-real-learning-key",
        )


def test_close_after_learning_and_restart_still_bit_identical(
    real_learning_result: RealMultimodalLearningResult,
) -> None:
    """Bonus: the full learn -> close cycle, checkpointed and restored,
    still round-trips bit-identically (not required by Step 4's own proof,
    which only needs one learned expression, but demonstrates the pipeline
    composes with the existing close mechanism unmodified)."""

    closed = close_real_multimodal_expression(real_learning_result)
    assert closed.terminal
    assert closed.pending_relation is None

    key = b"0123456789abcdef0123456789abcdef"
    checkpoint = learned_binding_checkpoint_payload(
        state=closed,
        checkpoint_id="test-real-learning-close-checkpoint",
        authentication_key=key,
        key_id="test-real-learning-close-key",
    )
    restored = restore_learned_binding_checkpoint(
        checkpoint_payload=checkpoint,
        authentication_key=key,
        expected_key_id="test-real-learning-close-key",
    )
    assert restored == closed
    assert restored.receipt_sha256 == closed.receipt_sha256
    restored.verify()
