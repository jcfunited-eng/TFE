from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.recall_story_episode_archive import (
    RecallStoryEpisodeArchive,
    create_recall_story_episode,
    recall_story_archive_checkpoint_payload,
    restore_recall_story_archive_checkpoint,
)
from dsf_ai_service.glew_runtime.story_native_replay import (
    StoryNativeReplayStatus,
    execute_story_native_replay,
)
from tests.glew_runtime.test_story_native_replay import _mounted_five_sense_runtime


AUTHENTICATION_KEY = bytes.fromhex("3a" * 32)
KEY_ID = "test-recall-story-archive-key"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


@pytest.fixture(scope="module")
def admitted_archive():
    profile, boundary, prewindow, runtime, sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    result = execute_story_native_replay(
        target_lane=profile.ports[0].lane,
        target_field_port_id=profile.ports[0].field_port_id,
        profile=profile,
        boundary=boundary,
        pre_window_state=prewindow,
        story_runtime=runtime,
        sensor_states=sensor_states,
        receipt_registry=registry,
    )
    assert result.status is StoryNativeReplayStatus.READY, result.reason
    episode = create_recall_story_episode(
        profile=profile,
        boundary=boundary,
        pre_window_state=prewindow,
        pre_window_story_runtime=runtime,
        pre_window_sensor_states=sensor_states,
        execution=result.executions[0],
    )
    archive = RecallStoryEpisodeArchive().with_episode(episode)
    return profile, boundary, prewindow, runtime, sensor_states, result, episode, archive


def test_archive_admits_only_real_base_experience_and_preserves_exact_five_senses(
    admitted_archive,
):
    profile, _, _, _, _, result, episode, archive = admitted_archive

    assert {value.lane_id for value in episode.sensory_evidence_bindings} == {
        "sight",
        "sound",
        "smell",
        "taste",
        "touch",
    }
    assert len(episode.pre_window_receiver_state_receipt_sha256s) == 5
    assert len(episode.post_window_receiver_state_receipt_sha256s) == 5
    assert len(episode.pre_window_sensor_state_receipt_sha256s) == 5
    assert len(episode.post_window_sensor_state_receipt_sha256s) == 5
    assert archive.resolve(
        profile_binding_sha256=profile.authority_receipt_sha256,
        sensory_evidence_receipt_sha256s=tuple(
            reversed(episode.sensory_evidence_receipt_sha256s)
        ),
    ) is episode

    with pytest.raises(ReceiptError, match="counterfactual replay"):
        create_recall_story_episode(
            profile=profile,
            boundary=admitted_archive[1],
            pre_window_state=admitted_archive[2],
            pre_window_story_runtime=admitted_archive[3],
            pre_window_sensor_states=admitted_archive[4],
            execution=result.executions[1],
        )


def test_archive_rejects_subset_extra_duplicate_and_profile_mismatch(admitted_archive):
    profile, _, _, _, _, _, episode, archive = admitted_archive
    receipts = episode.sensory_evidence_receipt_sha256s

    for query in (
        receipts[:-1],
        (*receipts, "f" * 64),
        (*receipts, receipts[0]),
    ):
        with pytest.raises(ReceiptError):
            archive.resolve(
                profile_binding_sha256=profile.authority_receipt_sha256,
                sensory_evidence_receipt_sha256s=query,
            )
    with pytest.raises(ReceiptError, match="exact profile"):
        archive.resolve(
            profile_binding_sha256="e" * 64,
            sensory_evidence_receipt_sha256s=receipts,
        )


def test_archive_checkpoint_restores_bit_exactly(admitted_archive):
    archive = admitted_archive[-1]
    checkpoint = recall_story_archive_checkpoint_payload(
        archive=archive,
        checkpoint_id="admitted-five-sense-episode-checkpoint",
        authentication_key=AUTHENTICATION_KEY,
        key_id=KEY_ID,
    )
    restored = restore_recall_story_archive_checkpoint(
        checkpoint_payload=checkpoint,
        authentication_key=AUTHENTICATION_KEY,
        expected_key_id=KEY_ID,
    )

    assert restored == archive
    assert restored.receipt_payload == archive.receipt_payload
    assert (
        recall_story_archive_checkpoint_payload(
            archive=restored,
            checkpoint_id="admitted-five-sense-episode-checkpoint",
            authentication_key=AUTHENTICATION_KEY,
            key_id=KEY_ID,
        )
        == checkpoint
    )


def test_archive_checkpoint_rejects_envelope_and_inner_receipt_tamper(
    admitted_archive,
):
    archive = admitted_archive[-1]
    checkpoint = recall_story_archive_checkpoint_payload(
        archive=archive,
        checkpoint_id="admitted-five-sense-episode-checkpoint",
        authentication_key=AUTHENTICATION_KEY,
        key_id=KEY_ID,
    )
    envelope = json.loads(checkpoint)
    envelope["body"]["archive_receipt_sha256"] = "0" * 64
    with pytest.raises(ReceiptError, match="authentication failed"):
        restore_recall_story_archive_checkpoint(
            checkpoint_payload=_canonical(envelope),
            authentication_key=AUTHENTICATION_KEY,
            expected_key_id=KEY_ID,
        )

    envelope = json.loads(checkpoint)
    record = envelope["body"]["episodes"][0]["receipt_records"][0]
    record["payload_hex"] = record["payload_hex"][:-1] + (
        "0" if record["payload_hex"][-1] != "0" else "1"
    )
    body_payload = _canonical(envelope["body"])
    envelope["authentication"]["signature_sha256"] = hmac.new(
        AUTHENTICATION_KEY,
        body_payload,
        hashlib.sha256,
    ).hexdigest()
    with pytest.raises(ReceiptError, match="does not match"):
        restore_recall_story_archive_checkpoint(
            checkpoint_payload=_canonical(envelope),
            authentication_key=AUTHENTICATION_KEY,
            expected_key_id=KEY_ID,
        )
