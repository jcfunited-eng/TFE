from __future__ import annotations

import hashlib
import inspect

import pytest

import tools.run_guala_candidate_rehearsal_task as runner


BASELINE = "11111111-1111-4111-8111-111111111111"
ACTIVE = "22222222-2222-4222-8222-222222222222"
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
GIT_SHA = "a" * 40
IMAGE = "sha256:" + "b" * 64
STATE_SHA = "c" * 64
THERMAL_PROOF = {
    "a013_thermal_body_rehearsed": True,
    "a013_thermal_body_world_revision_before": 0,
    "a013_thermal_body_world_revision_after": 1,
    "a013_thermal_body_receptor_count": 2,
    "a013_thermal_body_reached_site_counts": [1, 1],
    "a013_thermal_body_episode_port_count": 111,
    "a013_thermal_body_episode_sample_count": 222,
    "a013_thermal_body_dsf_delivery_count": 186,
    "a013_thermal_body_transition_receipt_sha256": "1" * 64,
    "a013_thermal_body_anatomy_receipt_sha256": "2" * 64,
    "a013_thermal_body_world_state_sha256": "3" * 64,
    "a013_thermal_body_cold_restore_exact": True,
    "a013_fresh_complete_roster_cold_restore_exact": True,
    "a013_fresh_complete_roster_state_sha256": "4" * 64,
    "a013_thermal_body_python_callback_count": 0,
}


def _task_definition() -> dict[str, object]:
    return {
        "containerDefinitions": [{
            "name": "dsf-ai",
            "image": "repo/candidate@" + IMAGE,
            "environment": [
                {"name": "DEPLOY_EXPECTED_GIT_SHA", "value": GIT_SHA},
                {"name": "GUALA_OWNER_LOCK_PATH", "value": "/retired"},
                {
                    "name": "GUALA_S3_BACKUP_BUCKET",
                    "value": "candidate-test-bucket",
                },
                {
                    "name": "GUALA_NATIVE_ORGANISM_ROOT",
                    "value": "/app/guala/native-organism",
                },
            ],
            "secrets": [{"name": "GUALALOOM_API_KEY", "valueFrom": "arn"}],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/dsf-ai",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "dsf-ai",
                },
            },
        }],
        "cpu": "1024",
        "memory": "4096",
        "networkMode": "awsvpc",
        "requiresCompatibilities": ["FARGATE"],
        "executionRoleArn": "execution-role",
        "taskRoleArn": "task-role",
        "volumes": [{"name": "gualaloom-state"}],
    }


def _migration_task(mode: str) -> dict[str, object]:
    return runner.probe_task_definition(
        _task_definition(),
        mode=mode,
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_baseline_generation=BASELINE,
        expected_active_generation=ACTIVE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
    )


def test_only_exact_same_digest_registry_absence_is_retryable() -> None:
    failure = {
        "stoppedReason": (
            "CannotPullContainerError: failed to resolve repo/candidate@"
            + IMAGE
            + ": not found"
        ),
        "containers": [{"name": "dsf-ai"}],
    }
    assert runner._retryable_same_digest_pull_absence(failure, IMAGE) is True
    assert (
        runner._retryable_same_digest_pull_absence(failure, "sha256:" + "d" * 64)
        is False
    )
    assert runner._retryable_same_digest_pull_absence(
        {**failure, "stoppedReason": "CannotPullContainerError: access denied"},
        IMAGE,
    ) is False
    assert runner._retryable_same_digest_pull_absence(
        {**failure, "containers": [{"exitCode": 1}]}, IMAGE
    ) is False


def test_registry_race_reuses_one_definition_at_most_once() -> None:
    source = inspect.getsource(runner.main)
    assert source.count("ecs.register_task_definition") == 1
    assert "for launch_attempt in range(2):" in source
    assert "taskDefinition=task_definition_arn" in source


def test_rehearsal_is_read_only_and_publication_is_the_only_writer() -> None:
    rehearsal = _migration_task("rehearse")
    publication = _migration_task("publish")
    rehearsal_container = rehearsal["containerDefinitions"][0]
    publication_container = publication["containerDefinitions"][0]
    assert rehearsal_container["mountPoints"] == [{
        "containerPath": runner.SOURCE_MOUNT,
        "readOnly": True,
        "sourceVolume": "gualaloom-state",
    }]
    assert publication_container["mountPoints"][0]["readOnly"] is False
    assert "--native-store-root" not in rehearsal_container["command"]
    assert "/source/guala/native-organism" in publication_container["command"]
    assert rehearsal["ephemeralStorage"] == {
        "sizeInGiB": runner.EPHEMERAL_GIB
    }
    assert all(
        item["name"] != "GUALA_OWNER_LOCK_PATH"
        for item in rehearsal_container["environment"]
    )


def test_fresh_native_current_restore_has_no_legacy_generation_arguments() -> None:
    task = runner.probe_task_definition(
        _task_definition(),
        mode="cold-restore",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
        expected_state_sha256=STATE_SHA,
    )
    container = task["containerDefinitions"][0]
    command = container["command"]
    assert container["mountPoints"][0]["readOnly"] is True
    assert "dsf_ai_service.cold_restore_probe" in command
    assert "--expected-state-sha256" in command
    assert "--expected-baseline-generation" not in command
    assert "--expected-active-generation" not in command
    environment = {
        item["name"]: item["value"] for item in container["environment"]
    }
    assert environment["GUALA_NATIVE_ORGANISM_ROOT"] == (
        runner.SOURCE_MOUNT + "/native-organism"
    )


@pytest.mark.parametrize(
    ("mode", "schema", "read_only"),
    [
        (
            "rehearse",
            "guala.production_candidate_native_restore_rehearsal.v5",
            True,
        ),
        (
            "publish",
            "guala.production_native_current_publication.v1",
            False,
        ),
        (
            "cold-restore",
            "guala.production_native_current_cold_restore.v8",
            True,
        ),
    ],
)
def test_every_task_proof_is_exactly_receipted(
    mode: str,
    schema: str,
    read_only: bool,
) -> None:
    record = {
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cold_restore_exact": True,
        "mode": mode,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": 442_430,
        "resident_state_sha256": STATE_SHA,
        "schema": schema,
        "source_identity": IDENTITY,
        "source_mount_read_only": read_only,
        "tick": 23_723_846,
    }
    if mode == "cold-restore":
        record.update({
            "baseline_observed_state_sha256": STATE_SHA,
            "baseline_observed_tick": 23_723_846,
            "complete_neuron_count": 217,
            "current_format_migration_rehearsed": False,
            "developmental_resting_neuron_count": 196_335,
            "migration_predecessor_state_sha256": None,
            "motor_action_rehearsed": False,
            "source_advanced_after_baseline": False,
        })
    proof = {
        **record,
        "receipt_sha256": hashlib.sha256(runner._canonical(record)).hexdigest(),
    }
    assert runner._validate_proof(
        proof,
        mode=mode,
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
        expected_state_sha256=(STATE_SHA if mode == "cold-restore" else None),
    ) == proof


GENESIS_ROOT = runner.GENESIS_STORE_PREFIX + "20260805T000000Z"


def _genesis_record() -> dict[str, object]:
    return {
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cognitive_mosaic_count": 0,
        "cognitive_trace_count": 0,
        "complete_neuron_count": 29,
        "complete_neuron_fractal_count": 27,
        "genesis_state_sha256": "e" * 64,
        "identity": IDENTITY,
        "lesson_pass_count": 2,
        "mode": "genesis-rehearse",
        "physically_transitioned_neuron_count": 27,
        "post_teach_state_sha256": "f" * 64,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "schema": "guala.genesis_rehearsal_proof.v1",
        "state_root": GENESIS_ROOT,
        "taught_card_id": "alphabet-a",
    }


def _receipted(record: dict[str, object]) -> dict[str, object]:
    return {
        **record,
        "receipt_sha256": hashlib.sha256(runner._canonical(record)).hexdigest(),
    }


def _validate_genesis(proof: dict[str, object]) -> dict[str, object]:
    return runner._validate_proof(
        proof,
        mode="genesis-rehearse",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=None,
        expected_state_sha256=None,
        expected_state_root=GENESIS_ROOT,
    )


def test_genesis_rehearsal_task_writes_only_a_throwaway_root() -> None:
    task = runner.probe_task_definition(
        _task_definition(),
        mode="genesis-rehearse",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        genesis_state_root=GENESIS_ROOT,
    )
    container = task["containerDefinitions"][0]
    command = container["command"]
    assert container["mountPoints"] == [{
        "containerPath": runner.PRODUCTION_MOUNT,
        "readOnly": False,
        "sourceVolume": "gualaloom-state",
    }]
    assert "genesis-rehearse" in command
    assert "--expected-baseline-generation" not in command
    assert "--expected-active-generation" not in command
    assert "--expected-tick" not in command
    environment = {
        item["name"]: item["value"] for item in container["environment"]
    }
    assert environment["GUALA_NATIVE_ORGANISM_ROOT"] == GENESIS_ROOT
    assert "GUALA_S3_BACKUP_BUCKET" not in environment
    assert "GUALA_OWNER_LOCK_PATH" not in environment
    with pytest.raises(ValueError, match="throwaway state root"):
        runner.probe_task_definition(
            _task_definition(),
            mode="genesis-rehearse",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            genesis_state_root="/app/guala/native-organism",
        )


def test_genesis_proof_validation_accepts_an_exact_proof() -> None:
    proof = _receipted(_genesis_record())
    assert _validate_genesis(proof) == proof


def test_genesis_proof_validation_rejects_zero_fractal_delta() -> None:
    record = _genesis_record()
    record["complete_neuron_fractal_count"] = 0
    with pytest.raises(RuntimeError, match="proof changed"):
        _validate_genesis(_receipted(record))


def test_genesis_proof_validation_rejects_identity_mismatch() -> None:
    record = _genesis_record()
    record["identity"] = "99999999-9999-4999-8999-999999999999"
    with pytest.raises(RuntimeError, match="proof changed"):
        _validate_genesis(_receipted(record))


def test_genesis_proof_validation_rejects_unchanged_state_receipt() -> None:
    record = _genesis_record()
    record["post_teach_state_sha256"] = record["genesis_state_sha256"]
    with pytest.raises(RuntimeError, match="proof changed"):
        _validate_genesis(_receipted(record))


def test_proof_rejects_state_or_receipt_drift() -> None:
    record = {
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cold_restore_exact": True,
        "mode": "cold-restore",
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": 442_430,
        "resident_state_sha256": STATE_SHA,
        "schema": "guala.production_native_current_cold_restore.v1",
        "source_identity": IDENTITY,
        "source_mount_read_only": True,
        "tick": 23_723_846,
    }
    proof = {
        **record,
        "receipt_sha256": hashlib.sha256(runner._canonical(record)).hexdigest(),
    }
    proof["resident_state_sha256"] = "d" * 64
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            proof,
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
        )


def test_cold_restore_requires_exact_c021_physical_rest_and_wake() -> None:
    record = {
        "baseline_observed_state_sha256": STATE_SHA,
        "baseline_observed_tick": 23_723_846,
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cold_restore_exact": True,
        "current_format_migration_rehearsed": False,
        "migration_predecessor_state_sha256": None,
        "mode": "cold-restore",
        "native_physical_rest_wake_cold_replay_exact": True,
        "native_physical_rest_wake_rehearsed": True,
        "native_rest_articulatory_recruitment_count": 0,
        "native_rest_dissipated_energy_after_zeptojoules": [3, 1],
        "native_rest_dissipated_energy_before_zeptojoules": [7, 1],
        "native_rest_interval_ordinal": 2,
        "native_rest_motor_recruitment_count": 0,
        "native_rest_reachable_dissipation_headroom_after_zeptojoules": [7, 1],
        "native_rest_reachable_dissipation_headroom_before_zeptojoules": [3, 1],
        "native_rest_recovered_neuron_count": 2,
        "native_rest_successor_state_sha256": "e" * 64,
        "native_wake_dsf_delivery_count": 1,
        "native_wake_physically_transitioned_neuron_count": 4,
        "native_wake_successor_state_sha256": "f" * 64,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": 442_430,
        "resident_state_sha256": STATE_SHA,
        "schema": "guala.production_native_current_cold_restore.v8",
        "source_advanced_after_baseline": False,
        "source_identity": IDENTITY,
        "source_mount_read_only": True,
        "tick": 23_723_846,
    }
    proof = _receipted(record)
    assert runner._validate_proof(
        proof,
        mode="cold-restore",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
        expected_state_sha256=STATE_SHA,
        expected_native_physical_rest_wake_rehearsal=True,
    ) == proof

    changed = dict(record)
    changed["native_rest_motor_recruitment_count"] = 1
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_native_physical_rest_wake_rehearsal=True,
        )


def test_cold_restore_requires_exact_c022_internal_consolidation() -> None:
    record = {
        "baseline_observed_state_sha256": STATE_SHA,
        "baseline_observed_tick": 23_723_846,
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cold_restore_exact": True,
        "current_format_migration_rehearsed": False,
        "migration_predecessor_state_sha256": None,
        "mode": "cold-restore",
        "native_internal_consolidation_rehearsed": True,
        "native_internal_consolidation_cold_restore_exact": True,
        "native_internal_consolidation_cold_replay_exact": True,
        "native_internal_consolidation_source": "local_metabolic_settlement",
        "native_internal_consolidation_origin": "internally_simulated",
        "native_internal_consolidation_interval_ordinal": 3,
        "native_internal_consolidation_member_count": 14,
        "native_internal_consolidation_cue_count": 2,
        "native_internal_consolidation_formation_count": 2,
        "native_internal_consolidation_metabolic_receptor_count": 2,
        "native_internal_consolidation_external_receptor_count": 0,
        "native_internal_consolidation_recovered_neuron_count": 7,
        "native_internal_consolidation_motor_recruitment_count": 4,
        "native_internal_consolidation_articulatory_recruitment_count": 1,
        "native_internal_consolidation_state_bytes_before": 442_430,
        "native_internal_consolidation_state_bytes_after": 442_431,
        "native_internal_consolidation_formation_receipt_before": "a" * 64,
        "native_internal_consolidation_formation_receipt_after": "b" * 64,
        "native_internal_consolidation_state_sha256_before": "c" * 64,
        "native_internal_consolidation_state_sha256_after": "d" * 64,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": 442_430,
        "resident_state_sha256": STATE_SHA,
        "schema": "guala.production_native_current_cold_restore.v8",
        "source_advanced_after_baseline": False,
        "source_identity": IDENTITY,
        "source_mount_read_only": True,
        "tick": 23_723_846,
    }
    proof = _receipted(record)
    assert runner._validate_proof(
        proof,
        mode="cold-restore",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
        expected_state_sha256=STATE_SHA,
        expected_native_internal_consolidation_rehearsal=True,
    ) == proof

    changed = dict(record)
    changed["native_internal_consolidation_origin"] = "externally_observed"
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_native_internal_consolidation_rehearsal=True,
        )


def test_cold_restore_requires_exact_c023_causal_cross_context_use() -> None:
    record = {
        "baseline_observed_state_sha256": STATE_SHA,
        "baseline_observed_tick": 23_723_846,
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cold_restore_exact": True,
        "complete_neuron_count": 217,
        "current_format_migration_rehearsed": False,
        "developmental_resting_neuron_count": 196_335,
        "migration_predecessor_state_sha256": None,
        "mode": "cold-restore",
        "motor_action_rehearsed": True,
        "native_causal_cross_context_use_rehearsed": True,
        "native_causal_cross_context_cold_restore_exact": True,
        "native_causal_cross_context_formation_receipt": "a" * 64,
        "native_causal_cross_context_transfer_count": 3,
        "native_causal_cross_context_recurrence_tick": 23_723_850,
        "native_causal_cross_context_motor_tick": 23_723_852,
        "native_causal_cross_context_hop_count": 12,
        "native_causal_cross_context_signed_yaw_millidegrees": -122_207,
        "native_causal_cross_context_world_revision_before": 4,
        "native_causal_cross_context_world_revision_after": 5,
        "native_causal_cross_context_body_receptor_count": 1,
        "native_causal_cross_context_vestibular_tick_count": 1,
        "native_causal_cross_context_state_sha256_before": "b" * 64,
        "native_causal_cross_context_state_sha256_after": "c" * 64,
        "native_causal_cross_context_state_bytes_before": 442_430,
        "native_causal_cross_context_state_bytes_after": 442_431,
        "native_causal_cross_context_successor_tick": 23_723_857,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": 442_430,
        "resident_state_sha256": STATE_SHA,
        "schema": "guala.production_native_current_cold_restore.v8",
        "source_advanced_after_baseline": False,
        "source_identity": IDENTITY,
        "source_mount_read_only": True,
        "tick": 23_723_846,
    }
    proof = _receipted(record)
    assert runner._validate_proof(
        proof,
        mode="cold-restore",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
        expected_state_sha256=STATE_SHA,
        expected_native_causal_cross_context_rehearsal=True,
    ) == proof

    changed = dict(record)
    changed["native_causal_cross_context_world_revision_after"] = 4
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_native_causal_cross_context_rehearsal=True,
        )


def test_cold_restore_requires_exact_a013_articulated_body() -> None:
    record = {
        "baseline_observed_state_sha256": STATE_SHA,
        "baseline_observed_tick": 23_723_846,
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "a013_articulated_body_rehearsed": True,
        "a013_articulated_body_predecessor_state_sha256": STATE_SHA,
        "a013_articulated_body_successor_state_sha256": "e" * 64,
        "a013_articulated_body_predecessor_tick": 23_723_846,
        "a013_articulated_body_successor_tick": 23_723_847,
        "a013_articulated_body_axis_count": 37,
        "a013_articulated_body_terminal_count": 74,
        "a013_articulated_body_state_bytes": 195,
        "a013_articulated_body_state_sha256": "d" * 64,
        "a013_articulated_body_proprioception_initialized": True,
        "a013_articulated_body_neutral_observation": True,
        "a013_articulated_body_live_transition_discarded": True,
        "a013_articulated_body_python_callback_count": 0,
        **THERMAL_PROOF,
        "cold_restore_exact": True,
        "complete_neuron_count": 217,
        "current_format_migration_rehearsed": False,
        "developmental_resting_neuron_count": 196_335,
        "migration_predecessor_state_sha256": None,
        "mode": "cold-restore",
        "motor_action_rehearsed": False,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": 442_430,
        "resident_state_sha256": STATE_SHA,
        "schema": "guala.production_native_current_cold_restore.v8",
        "source_advanced_after_baseline": False,
        "source_identity": IDENTITY,
        "source_mount_read_only": True,
        "tick": 23_723_846,
    }
    proof = _receipted(record)
    assert runner._validate_proof(
        proof,
        mode="cold-restore",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
        expected_state_sha256=STATE_SHA,
        expected_a013_articulated_body_rehearsal=True,
    ) == proof

    changed = dict(record)
    changed["a013_articulated_body_live_transition_discarded"] = False
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_a013_articulated_body_rehearsal=True,
        )


def test_cold_restore_requires_active_l005_word_apple_causal_use() -> None:
    record = {
        "baseline_observed_state_sha256": STATE_SHA,
        "baseline_observed_tick": 23_723_846,
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cold_restore_exact": True,
        "complete_neuron_count": 217,
        "current_format_migration_rehearsed": False,
        "developmental_resting_neuron_count": 196_335,
        "l005_word_apple_rehearsed": True,
        "l005_word_apple_predecessor_tick": 23_723_846,
        "l005_word_apple_successor_tick": 23_723_864,
        "l005_word_apple_predecessor_state_sha256": STATE_SHA,
        "l005_word_apple_successor_state_sha256": "e" * 64,
        "l005_word_apple_full_dsf_delivery_count": 381,
        "l005_word_apple_partial_dsf_delivery_count": 381,
        "l005_word_apple_external_reassembly_count": 1,
        "l005_word_apple_causal_use_kind": "articulation",
        "l005_word_apple_formation_receipt_sha256": "f" * 64,
        "l005_word_apple_causal_transfer_count": 2,
        "l005_word_apple_body_return_count": 1,
        "l005_word_apple_cold_restore_exact": True,
        "l005_word_apple_python_callback_count": 0,
        "migration_predecessor_state_sha256": None,
        "mode": "cold-restore",
        "motor_action_rehearsed": False,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": 442_430,
        "resident_state_sha256": STATE_SHA,
        "schema": "guala.production_native_current_cold_restore.v8",
        "source_advanced_after_baseline": False,
        "source_identity": IDENTITY,
        "source_mount_read_only": True,
        "tick": 23_723_846,
    }
    proof = _receipted(record)
    assert runner._validate_proof(
        proof,
        mode="cold-restore",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
        expected_state_sha256=STATE_SHA,
        expected_l005_word_apple_rehearsal=True,
    ) == proof

    changed = dict(record)
    changed["l005_word_apple_causal_transfer_count"] = 0
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_l005_word_apple_rehearsal=True,
        )


def test_cold_restore_requires_exact_native_articulation_when_active() -> None:
    articulation = {
        "applied_motor_quanta": 8,
        "articulatory_body_port_count": 4,
        "articulatory_body_receptor_ingress_count": 16,
        "articulatory_body_perturbed_neuron_count": 4,
        "glottal_open_samples_at_apex": 144,
        "layer_13_recruitment_count": 78,
        "mouth_area_square_millimetres_at_apex": 305,
        "peak_breath_flow_pcm": 12_000,
        "perioral_area_displacement_square_millimetres": -40,
        "pressure_sample_count": 16_000,
        "pressure_sha256": "e" * 64,
        "relaxation_sample_count": 0,
        "sample_rate_hz": 16_000,
        "self_hearing_fractal_count": 49,
        "self_hearing_hop_count": 4,
        "self_hearing_transitioned_neuron_count": 889,
        "stalled_motor_quanta": 42,
    }
    record = {
        "baseline_observed_state_sha256": STATE_SHA,
        "baseline_observed_tick": 23_723_846,
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cold_restore_exact": True,
        "complete_neuron_count": 217,
        "current_format_migration_rehearsed": False,
        "developmental_resting_neuron_count": 196_335,
        "migration_predecessor_state_sha256": None,
        "mode": "cold-restore",
        "motor_action_rehearsed": False,
        "native_articulation": articulation,
        "native_articulation_cold_replay_exact": True,
        "native_articulation_rehearsal_successor_state_sha256": "f" * 64,
        "native_articulation_source_available_interval_count": 250,
        "native_articulation_source_dsf_delivery_count": 2,
        "native_articulation_source_interval_count": 3,
        "native_articulation_source_layer_13_recruitment_count": 78,
        "native_articulation_source_physically_transitioned_neuron_count": 208,
        "native_articulation_source_state_byte_delta": 64,
        "native_articulation_source_successor_state_sha256": "c" * 64,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": 43_384_308,
        "resident_state_sha256": STATE_SHA,
        "schema": "guala.production_native_current_cold_restore.v8",
        "source_advanced_after_baseline": False,
        "source_identity": IDENTITY,
        "source_mount_read_only": True,
        "tick": 23_723_846,
    }
    proof = _receipted(record)
    assert runner._validate_proof(
        proof,
        mode="cold-restore",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
        expected_state_sha256=STATE_SHA,
        expected_native_articulation_rehearsal=True,
    ) == proof

    changed = dict(record)
    changed["native_articulation"] = None
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_native_articulation_rehearsal=True,
        )

    changed = dict(record)
    changed["native_articulation"] = {
        **articulation,
        "relaxation_sample_count": 1,
    }
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_native_articulation_rehearsal=True,
        )

    changed = dict(record)
    changed["native_articulation"] = {
        **articulation,
        "perioral_area_displacement_square_millimetres": 0,
    }
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_native_articulation_rehearsal=True,
        )

    changed = dict(record)
    changed["native_articulation_source_interval_count"] = 251
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_native_articulation_rehearsal=True,
        )


def test_cold_restore_requires_exact_distributed_recall_evidence() -> None:
    receipt = "e" * 64
    formation_receipts = [receipt]
    episodic_receipts = ["1" * 64, "2" * 64]
    record = {
        "baseline_observed_state_sha256": STATE_SHA,
        "baseline_observed_tick": 23_723_846,
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cold_restore_exact": True,
        "complete_neuron_count": 217,
        "current_format_migration_rehearsed": False,
        "developmental_resting_neuron_count": 196_335,
        "distributed_recall_cue_lineage": "f" * 32,
        "distributed_recall_formation_member_count": 27,
        "distributed_recall_interval_ordinal": 4,
        "distributed_recall_rehearsed": True,
        "distributed_recall_source_dsf_delivery_count": 6,
        "distributed_recall_source_physical_transition_count": 223,
        "distributed_recall_state_byte_delta": 1_644,
        "distributed_recall_successor_state_sha256": "a" * 64,
        "distributed_recognition_active_bond_count": 486,
        "distributed_recognition_active_bond_sha256": "b" * 64,
        "distributed_recognition_active_neuron_count": 152,
        "distributed_recognition_affective_neuron_count": 3,
        "distributed_recognition_association_neuron_count": 2,
        "distributed_recognition_body_neuron_count": 2,
        "distributed_recognition_episode_ordinal": 2,
        "distributed_recognition_formation_count": 1,
        "distributed_recognition_formation_receipts": formation_receipts,
        "distributed_recognition_formation_receipts_sha256": hashlib.sha256(
            runner._canonical(formation_receipts)
        ).hexdigest(),
        "distributed_recognition_ordering_neuron_count": 4,
        "distributed_recognition_rehearsed": True,
        "distributed_recognition_retention_neuron_count": 2,
        "distributed_recognition_sensory_neuron_count": 43,
        "distributed_recognition_source_dsf_delivery_count": 6,
        "distributed_recognition_source_hop_count": 4,
        "distributed_recognition_source_physical_transition_count": 223,
        "distributed_recognition_state_byte_delta": 1_644,
        "distributed_recognition_successor_state_sha256": "a" * 64,
        "episodic_archive_lookup_count": 0,
        "episodic_cold_reassembly_exact": True,
        "episodic_complete_source_replayed": False,
        "episodic_memory_rehearsed": True,
        "ordered_physical_cold_reassembly": True,
        "ordered_physical_path_count": 1,
        "ordered_physical_paths_sha256": "6" * 64,
        "ordered_path_relation_count": 1,
        "ordered_path_relations_sha256": "9" * 64,
        "ordered_trajectory_projection_rehearsed": True,
        "ordered_trajectory_path_count": 1,
        "ordered_trajectory_path_relation_count": 1,
        "ordered_trajectory_path_relations_sha256": "b" * 64,
        "ordered_trajectory_paths_sha256": "7" * 64,
        "ordered_trajectory_successor_state_sha256": "8" * 64,
        "episodic_recalled_formation_receipt": episodic_receipts[0],
        "episodic_related_formation_count": 2,
        "episodic_related_formation_receipts": episodic_receipts,
        "episodic_related_formation_receipts_sha256": hashlib.sha256(
            runner._canonical(episodic_receipts)
        ).hexdigest(),
        "episodic_related_member_sets_sha256": "3" * 64,
        "episodic_relation_active_bond_count": 1,
        "episodic_relation_active_bonds_sha256": "4" * 64,
        "structural_relation_sha256": "5" * 64,
        "episodic_relation_interval_ordinal": 4,
        "episodic_relation_shared_lineage_count": 0,
        "migration_predecessor_state_sha256": None,
        "mode": "cold-restore",
        "motor_action_rehearsed": False,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": 43_384_308,
        "resident_state_sha256": STATE_SHA,
        "schema": "guala.production_native_current_cold_restore.v8",
        "sparse_attention_cold_replay_exact": True,
        "sparse_attention_current_route_count": 0,
        "sparse_attention_current_routes_sha256": "c" * 64,
        "sparse_attention_dsf_delivery_count": 500,
        "sparse_attention_downstream_neuron_count": 1,
        "sparse_attention_foregone_route_count": 1,
        "sparse_attention_interval_count": 250,
        "sparse_attention_physically_transitioned_neuron_count": 217,
        "sparse_attention_preceding_route_count": 2,
        "sparse_attention_preceding_routes_sha256": "d" * 64,
        "sparse_attention_qualifying_route_count": 2,
        "sparse_attention_qualifying_routes_sha256": "f" * 64,
        "sparse_attention_reached_route_count": 1,
        "sparse_attention_rehearsed": True,
        "sparse_attention_state_byte_delta": 64,
        "sparse_attention_successor_state_sha256": "e" * 64,
        "source_advanced_after_baseline": False,
        "source_identity": IDENTITY,
        "source_mount_read_only": True,
        "tick": 23_723_846,
    }
    proof = _receipted(record)
    assert runner._validate_proof(
        proof,
        mode="cold-restore",
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
        expected_identity=IDENTITY,
        expected_tick=23_723_846,
        expected_state_sha256=STATE_SHA,
        expected_distributed_recall_rehearsal=True,
        expected_sparse_attention_rehearsal=True,
    ) == proof

    changed = dict(record)
    changed["distributed_recognition_ordering_neuron_count"] = 0
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_distributed_recall_rehearsal=True,
            expected_sparse_attention_rehearsal=True,
        )

    changed = dict(record)
    changed["sparse_attention_current_routes_sha256"] = changed[
        "sparse_attention_preceding_routes_sha256"
    ]
    with pytest.raises(RuntimeError, match="proof changed"):
        runner._validate_proof(
            _receipted(changed),
            mode="cold-restore",
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
            expected_identity=IDENTITY,
            expected_tick=23_723_846,
            expected_state_sha256=STATE_SHA,
            expected_distributed_recall_rehearsal=True,
            expected_sparse_attention_rehearsal=True,
        )
