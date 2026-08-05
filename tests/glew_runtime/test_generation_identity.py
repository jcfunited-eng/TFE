"""Unmocked conformance for the unified generation identity binding.

Every fixture below is a real, already-tested checkpoint built through its
owning module's own unmodified construction path -- this file invents no
fixtures of its own for genesis, learning, or the recall archive.  It only
proves that :mod:`dsf_ai_service.glew_runtime.generation_identity` correctly
composes and cross-checks the three real identifiers those checkpoints
already produce.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.expression_learning import (
    LearnedBindingState,
    learned_binding_checkpoint_payload,
    restore_learned_binding_checkpoint,
)
from dsf_ai_service.glew_runtime.generation_identity import (
    GENERATION_IDENTITY_BINDING_SCHEMA,
    GenerationIdentityBinding,
    bind_generation_identity,
    generation_identity_binding_receipt_payload,
    verify_generation_identity_binding,
)
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.recall_story_episode_archive import (
    recall_story_archive_checkpoint_payload,
    restore_recall_story_archive_checkpoint,
)

from tests.glew_runtime.test_expression_learning import (
    LearningWorld,
    _learn_close,
    _learn_content,
    learning_world,  # noqa: F401 -- reused as a real pytest fixture
)
from tests.glew_runtime.test_genesis import _create as _create_genesis
from tests.glew_runtime.test_genesis import _restore as _restore_genesis
from tests.glew_runtime.test_recall_story_episode_archive import (
    admitted_archive,  # noqa: F401 -- reused as a real pytest fixture
)


LEARNING_KEY = bytes(range(32))
ARCHIVE_KEY = bytes.fromhex("5c" * 32)


def _closed_learning_state(world: LearningWorld) -> LearnedBindingState:
    return _learn_close(world, _learn_content(world))


def _real_learning_checkpoint(
    world: LearningWorld, checkpoint_id: str
) -> bytes:
    return learned_binding_checkpoint_payload(
        state=_closed_learning_state(world),
        checkpoint_id=checkpoint_id,
        authentication_key=LEARNING_KEY,
        key_id="generation-identity-learning-key",
    )


def _checkpoint_id_of(checkpoint_payload: bytes) -> str:
    envelope = json.loads(checkpoint_payload)
    return envelope["body"]["checkpoint_id"]


@pytest.fixture()
def real_generations(tmp_path, learning_world: LearningWorld, admitted_archive):
    """Three real, independently produced generations for cross-mismatch tests."""

    genesis_a_root = tmp_path / "genesis-a"
    genesis_b_root = tmp_path / "genesis-b"
    genesis_a = _create_genesis(genesis_a_root)
    genesis_b = _create_genesis(genesis_b_root)
    restored_genesis_a = _restore_genesis(genesis_a_root, genesis_a.identity)

    learning_a_payload = _real_learning_checkpoint(
        learning_world, "generation-identity-learning-checkpoint-a"
    )
    learning_b_payload = _real_learning_checkpoint(
        learning_world, "generation-identity-learning-checkpoint-b"
    )
    restored_learning_a = restore_learned_binding_checkpoint(
        checkpoint_payload=learning_a_payload,
        authentication_key=LEARNING_KEY,
        expected_key_id="generation-identity-learning-key",
    )

    archive = admitted_archive[-1]
    archive_a_payload = recall_story_archive_checkpoint_payload(
        archive=archive,
        checkpoint_id="generation-identity-archive-checkpoint-a",
        authentication_key=ARCHIVE_KEY,
        key_id="generation-identity-archive-key",
    )
    archive_b_payload = recall_story_archive_checkpoint_payload(
        archive=archive,
        checkpoint_id="generation-identity-archive-checkpoint-b",
        authentication_key=ARCHIVE_KEY,
        key_id="generation-identity-archive-key",
    )
    restored_archive_a = restore_recall_story_archive_checkpoint(
        checkpoint_payload=archive_a_payload,
        authentication_key=ARCHIVE_KEY,
        expected_key_id="generation-identity-archive-key",
    )

    return {
        "genesis_a": genesis_a,
        "genesis_b": genesis_b,
        "restored_genesis_a": restored_genesis_a,
        "learning_a_id": _checkpoint_id_of(learning_a_payload),
        "learning_b_id": _checkpoint_id_of(learning_b_payload),
        "restored_learning_a": restored_learning_a,
        "archive_a_id": _checkpoint_id_of(archive_a_payload),
        "archive_b_id": _checkpoint_id_of(archive_b_payload),
        "restored_archive_a": restored_archive_a,
    }


def test_full_round_trip_binds_and_restores_all_three_generations(
    real_generations,
):
    genesis_a = real_generations["genesis_a"]
    restored_genesis_a = real_generations["restored_genesis_a"]
    learning_id = real_generations["learning_a_id"]
    restored_learning = real_generations["restored_learning_a"]
    archive_id = real_generations["archive_a_id"]
    restored_archive = real_generations["restored_archive_a"]

    binding = bind_generation_identity(
        genesis_identity=genesis_a.identity,
        genesis_generation_uuid=genesis_a.generation_uuid,
        genesis_tick=restored_genesis_a.generation.tick,
        learning_checkpoint_id=learning_id,
        archive_checkpoint_id=archive_id,
    )

    assert binding.genesis_identity == genesis_a.identity
    assert binding.genesis_generation_uuid == genesis_a.generation_uuid
    assert binding.genesis_tick == 0
    assert binding.learning_checkpoint_id == learning_id
    assert binding.archive_checkpoint_id == archive_id
    assert json.loads(binding.receipt_payload)["schema"] == (
        GENERATION_IDENTITY_BINDING_SCHEMA
    )
    binding.verify()

    # The restored domain objects are independent evidence that the exact
    # generation genuinely came back: restoring re-derives the genesis state
    # from scratch and re-authenticates each checkpoint's HMAC envelope.
    restored_learning.verify()
    assert restored_archive.receipt_sha256 is not None

    verify_generation_identity_binding(
        binding,
        restored_genesis_identity=restored_genesis_a.receipt.identity,
        restored_genesis_generation_uuid=(
            restored_genesis_a.receipt.generation_uuid
        ),
        restored_genesis_tick=restored_genesis_a.generation.tick,
        restored_learning_checkpoint_id=learning_id,
        restored_archive_checkpoint_id=archive_id,
    )


@pytest.mark.parametrize(
    "field_name",
    (
        "restored_genesis_identity",
        "restored_genesis_generation_uuid",
        "restored_genesis_tick",
        "restored_learning_checkpoint_id",
        "restored_archive_checkpoint_id",
    ),
)
def test_mismatched_real_restoration_is_rejected(real_generations, field_name):
    genesis_a = real_generations["genesis_a"]
    genesis_b = real_generations["genesis_b"]
    restored_genesis_a = real_generations["restored_genesis_a"]
    learning_id = real_generations["learning_a_id"]
    archive_id = real_generations["archive_a_id"]

    binding = bind_generation_identity(
        genesis_identity=genesis_a.identity,
        genesis_generation_uuid=genesis_a.generation_uuid,
        genesis_tick=restored_genesis_a.generation.tick,
        learning_checkpoint_id=learning_id,
        archive_checkpoint_id=archive_id,
    )

    matched = {
        "restored_genesis_identity": genesis_a.identity,
        "restored_genesis_generation_uuid": genesis_a.generation_uuid,
        "restored_genesis_tick": restored_genesis_a.generation.tick,
        "restored_learning_checkpoint_id": learning_id,
        "restored_archive_checkpoint_id": archive_id,
    }
    mismatched_value = {
        "restored_genesis_identity": genesis_b.identity,
        "restored_genesis_generation_uuid": genesis_b.generation_uuid,
        "restored_genesis_tick": restored_genesis_a.generation.tick + 1,
        "restored_learning_checkpoint_id": real_generations["learning_b_id"],
        "restored_archive_checkpoint_id": real_generations["archive_b_id"],
    }[field_name]
    kwargs = {**matched, field_name: mismatched_value}

    with pytest.raises(ReceiptError, match="does not match"):
        verify_generation_identity_binding(binding, **kwargs)


def test_swapped_archive_checkpoint_id_from_a_different_real_checkpoint_rejected(
    real_generations,
):
    """Section 5's specific case: swap one checkpoint_id for a different real one."""

    genesis_a = real_generations["genesis_a"]
    restored_genesis_a = real_generations["restored_genesis_a"]
    learning_id = real_generations["learning_a_id"]

    binding = bind_generation_identity(
        genesis_identity=genesis_a.identity,
        genesis_generation_uuid=genesis_a.generation_uuid,
        genesis_tick=restored_genesis_a.generation.tick,
        learning_checkpoint_id=learning_id,
        archive_checkpoint_id=real_generations["archive_a_id"],
    )

    with pytest.raises(ReceiptError, match="archive checkpoint id"):
        verify_generation_identity_binding(
            binding,
            restored_genesis_identity=genesis_a.identity,
            restored_genesis_generation_uuid=genesis_a.generation_uuid,
            restored_genesis_tick=restored_genesis_a.generation.tick,
            restored_learning_checkpoint_id=learning_id,
            # A real archive_checkpoint_id -- just from a different real
            # checkpoint of the same archive, not an invented string.
            restored_archive_checkpoint_id=real_generations["archive_b_id"],
        )


def test_binding_receipt_tamper_via_mismatched_digest_fails_closed(
    real_generations,
):
    genesis_a = real_generations["genesis_a"]
    restored_genesis_a = real_generations["restored_genesis_a"]
    binding = bind_generation_identity(
        genesis_identity=genesis_a.identity,
        genesis_generation_uuid=genesis_a.generation_uuid,
        genesis_tick=restored_genesis_a.generation.tick,
        learning_checkpoint_id=real_generations["learning_a_id"],
        archive_checkpoint_id=real_generations["archive_a_id"],
    )

    tampered_digest = replace(binding, receipt_sha256="0" * 64)
    with pytest.raises(ReceiptError, match="differs from its exact receipt"):
        tampered_digest.verify()
    with pytest.raises(ReceiptError, match="differs from its exact receipt"):
        verify_generation_identity_binding(
            tampered_digest,
            restored_genesis_identity=genesis_a.identity,
            restored_genesis_generation_uuid=genesis_a.generation_uuid,
            restored_genesis_tick=restored_genesis_a.generation.tick,
            restored_learning_checkpoint_id=real_generations["learning_a_id"],
            restored_archive_checkpoint_id=real_generations["archive_a_id"],
        )


def test_binding_receipt_tamper_via_mutated_payload_bytes_fails_closed(
    real_generations,
):
    genesis_a = real_generations["genesis_a"]
    restored_genesis_a = real_generations["restored_genesis_a"]
    binding = bind_generation_identity(
        genesis_identity=genesis_a.identity,
        genesis_generation_uuid=genesis_a.generation_uuid,
        genesis_tick=restored_genesis_a.generation.tick,
        learning_checkpoint_id=real_generations["learning_a_id"],
        archive_checkpoint_id=real_generations["archive_a_id"],
    )

    envelope = json.loads(binding.receipt_payload)
    tampered_envelope = copy.deepcopy(envelope)
    tampered_envelope["genesis_tick"] = binding.genesis_tick + 1
    tampered_payload = (
        json.dumps(tampered_envelope, sort_keys=True, indent=2, ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    assert tampered_payload != binding.receipt_payload

    tampered_binding = replace(binding, receipt_payload=tampered_payload)
    with pytest.raises(ReceiptError, match="differs from its exact receipt"):
        tampered_binding.verify()


def test_binding_receipt_payload_is_genesis_style_canonical_json(
    real_generations,
):
    genesis_a = real_generations["genesis_a"]
    restored_genesis_a = real_generations["restored_genesis_a"]
    payload = generation_identity_binding_receipt_payload(
        genesis_identity=genesis_a.identity,
        genesis_generation_uuid=genesis_a.generation_uuid,
        genesis_tick=restored_genesis_a.generation.tick,
        learning_checkpoint_id=real_generations["learning_a_id"],
        archive_checkpoint_id=real_generations["archive_a_id"],
    )

    # genesis.py's own canonicalization: two-space indent, sorted keys,
    # exactly one trailing newline, non-ASCII preserved.
    assert payload.endswith(b"\n")
    assert not payload.endswith(b"\n\n")
    reencoded = (
        json.dumps(json.loads(payload), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    assert reencoded == payload


def test_bind_generation_identity_rejects_malformed_sub_identities(
    real_generations,
):
    genesis_a = real_generations["genesis_a"]
    restored_genesis_a = real_generations["restored_genesis_a"]
    valid = dict(
        genesis_identity=genesis_a.identity,
        genesis_generation_uuid=genesis_a.generation_uuid,
        genesis_tick=restored_genesis_a.generation.tick,
        learning_checkpoint_id=real_generations["learning_a_id"],
        archive_checkpoint_id=real_generations["archive_a_id"],
    )

    with pytest.raises(ReceiptError, match="not a canonical UUID"):
        bind_generation_identity(**{**valid, "genesis_identity": "not-a-uuid"})
    with pytest.raises(ReceiptError, match="not a canonical UUIDv4"):
        # A well-formed UUID (version 1, not version 4).
        bind_generation_identity(
            **{
                **valid,
                "genesis_identity": "00000000-0000-1000-8000-000000000001",
            }
        )
    with pytest.raises(ReceiptError, match="not a canonical UUID"):
        bind_generation_identity(
            **{**valid, "genesis_generation_uuid": "not-a-uuid"}
        )
    with pytest.raises(ReceiptError, match="tick must be an integer"):
        bind_generation_identity(**{**valid, "genesis_tick": "0"})
    with pytest.raises(ReceiptError, match="tick cannot be negative"):
        bind_generation_identity(**{**valid, "genesis_tick": -1})
    with pytest.raises(ReceiptError, match="canonical identifier"):
        bind_generation_identity(**{**valid, "learning_checkpoint_id": ""})
    with pytest.raises(ReceiptError, match="canonical identifier"):
        bind_generation_identity(**{**valid, "archive_checkpoint_id": " padded "})


def test_verify_generation_identity_binding_requires_a_real_binding():
    with pytest.raises(ReceiptError, match="real generation identity binding"):
        verify_generation_identity_binding(
            object(),
            restored_genesis_identity="x",
            restored_genesis_generation_uuid="x",
            restored_genesis_tick=0,
            restored_learning_checkpoint_id="x",
            restored_archive_checkpoint_id="x",
        )
