from __future__ import annotations

import hashlib

import pytest

import tools.run_guala_candidate_rehearsal_task as runner


BASELINE = "11111111-1111-4111-8111-111111111111"
ACTIVE = "22222222-2222-4222-8222-222222222222"
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
GIT_SHA = "a" * 40
IMAGE = "sha256:" + "b" * 64
STATE_SHA = "c" * 64


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
    assert runner.NATIVE_STORE in publication_container["command"]
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
            "guala.production_native_current_cold_restore.v1",
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
