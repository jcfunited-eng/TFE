#!/usr/bin/env python3
"""Run one bounded migration, publication, or native CURRENT proof task."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import PurePosixPath
import re
import time


PROBE_FAMILY = "dsf-ai-native-candidate"
SOURCE_MOUNT = "/source/guala"
# The genesis rehearsal runs against the real production mount path (its
# throwaway state root lives beside, never inside, the real native-organism
# directory) so the candidate exercises the exact serving filesystem layout.
PRODUCTION_MOUNT = "/app/guala"
GENESIS_STORE_PREFIX = PRODUCTION_MOUNT + "/native-organism-rehearsal-"
EPHEMERAL_GIB = 30
_SHA = re.compile(r"[0-9a-f]{64}")
PROOF_SCHEMAS = {
    "rehearse": "guala.production_candidate_native_restore_rehearsal.v5",
    "publish": "guala.production_native_current_publication.v1",
    "cold-restore": "guala.production_native_current_cold_restore.v4",
    "genesis-rehearse": "guala.genesis_rehearsal_proof.v1",
}


def mounted_native_store(environment: list[dict[str, object]]) -> str:
    """Map the inherited live body root onto the read-only probe mount.

    The body generation is deliberately not named here.  The candidate task
    inherits the exact live ``GUALA_NATIVE_ORGANISM_ROOT`` and the probe sees
    the same EFS volume at ``/source/guala`` instead of ``/app/guala``.
    """

    values = [
        item.get("value")
        for item in environment
        if item.get("name") == "GUALA_NATIVE_ORGANISM_ROOT"
    ]
    if len(values) != 1 or not isinstance(values[0], str):
        raise RuntimeError("candidate declares no single live organism root")
    declared = PurePosixPath(values[0])
    production_mount = PurePosixPath(PRODUCTION_MOUNT)
    if not declared.is_absolute() or ".." in declared.parts:
        raise RuntimeError("candidate organism root escapes the production mount")
    try:
        relative = declared.relative_to(production_mount)
    except ValueError as error:
        raise RuntimeError(
            "candidate organism root is outside the production mount"
        ) from error
    if not relative.parts:
        raise RuntimeError("candidate organism root names the whole production mount")
    return str(PurePosixPath(SOURCE_MOUNT).joinpath(relative))


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("rehearse", "publish", "cold-restore", "genesis-rehearse"),
        required=True,
    )
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--candidate-task-definition", required=True)
    parser.add_argument("--candidate-git-sha", required=True)
    parser.add_argument("--candidate-image-digest", required=True)
    parser.add_argument("--expected-baseline-generation")
    parser.add_argument("--expected-active-generation")
    parser.add_argument("--expected-identity", required=True)
    parser.add_argument("--expected-tick", type=int)
    parser.add_argument("--expected-state-sha256")
    parser.add_argument("--region", default="us-east-1")
    return parser.parse_args()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def probe_task_definition(
    source: dict[str, object],
    *,
    mode: str,
    candidate_git_sha: str,
    candidate_image_digest: str,
    expected_identity: str,
    expected_tick: int | None = None,
    expected_baseline_generation: str | None = None,
    expected_active_generation: str | None = None,
    expected_state_sha256: str | None = None,
    genesis_state_root: str | None = None,
) -> dict[str, object]:
    containers = source.get("containerDefinitions")
    if not isinstance(containers, list) or len(containers) != 1:
        raise RuntimeError("candidate task must contain one container")
    original = containers[0]
    if not isinstance(original, dict) or original.get("name") != "dsf-ai":
        raise RuntimeError("candidate container changed")
    environment = [
        item
        for item in original.get("environment", [])
        if isinstance(item, dict)
        and item.get("name")
        not in {
            "FORCE_S3_RESTORE",
            "GUALA_EXACT_FIELD_EXECUTOR_REQUIRED",
            "GUALA_GENERATION_STORE_ROOT",
            "GUALA_LIVE_RECOVERY_STORE_ROOT",
            "GUALA_OWNER_LOCK_PATH",
            "GUALA_REQUIRE_SEALED_STATE",
            "STATE_DIR",
        }
    ]
    native_store = (
        mounted_native_store(environment)
        if mode in {"publish", "cold-restore"}
        else None
    )
    if mode == "genesis-rehearse":
        if (
            not genesis_state_root
            or not genesis_state_root.startswith(GENESIS_STORE_PREFIX)
        ):
            raise ValueError(
                "genesis rehearsal requires a unique throwaway state root"
            )
        command = [
            "python3",
            "-m",
            "dsf_ai_service.candidate_release_rehearsal",
            "--mode",
            "genesis-rehearse",
            "--expected-identity",
            expected_identity,
            "--candidate-git-sha",
            candidate_git_sha,
            "--candidate-image-digest",
            candidate_image_digest,
        ]
        # The rehearsal's publications must stay inside the throwaway root:
        # without a remote bucket the app uses its local directory mirror, so
        # the shared production backup bucket is never written or retired by
        # a rehearsal (deterministic genesis could otherwise collide with the
        # real organism's content-addressed keys).
        environment = [
            item
            for item in environment
            if item.get("name")
            not in {"GUALA_NATIVE_ORGANISM_ROOT", "GUALA_S3_BACKUP_BUCKET"}
        ]
        environment.append(
            {"name": "GUALA_NATIVE_ORGANISM_ROOT", "value": genesis_state_root}
        )
    elif expected_tick is None:
        raise ValueError("migration task requires the exact source tick")
    elif mode == "cold-restore":
        if expected_state_sha256 is None:
            raise ValueError("cold restore requires expected state SHA-256")
        command = [
            "python3",
            "-m",
            "dsf_ai_service.cold_restore_probe",
            "--native-store-root",
            native_store,
            "--expected-identity",
            expected_identity,
            "--expected-tick",
            str(expected_tick),
            "--expected-state-sha256",
            expected_state_sha256,
            "--candidate-git-sha",
            candidate_git_sha,
            "--candidate-image-digest",
            candidate_image_digest,
        ]
    else:
        if expected_baseline_generation is None or expected_active_generation is None:
            raise ValueError("migration task requires exact generation identities")
        command = [
            "python3",
            "-m",
            "dsf_ai_service.candidate_release_rehearsal",
            "--mode",
            mode,
            "--source-root",
            SOURCE_MOUNT,
            "--expected-baseline-generation",
            expected_baseline_generation,
            "--expected-active-generation",
            expected_active_generation,
            "--expected-identity",
            expected_identity,
            "--expected-tick",
            str(expected_tick),
            "--candidate-git-sha",
            candidate_git_sha,
            "--candidate-image-digest",
            candidate_image_digest,
        ]
        if mode == "publish":
            command.extend(("--native-store-root", native_store))
    log_configuration = original.get("logConfiguration")
    if not isinstance(log_configuration, dict):
        raise RuntimeError("candidate log transport is absent")
    options = dict(log_configuration.get("options") or {})
    options["awslogs-stream-prefix"] = "guala-native-" + mode
    read_only = mode in {"rehearse", "cold-restore"}
    mount_path = PRODUCTION_MOUNT if mode == "genesis-rehearse" else SOURCE_MOUNT
    container = {
        "command": command,
        "environment": environment,
        "essential": True,
        "image": original.get("image"),
        "logConfiguration": {**log_configuration, "options": options},
        "mountPoints": [{
            "containerPath": mount_path,
            "readOnly": read_only,
            "sourceVolume": "gualaloom-state",
        }],
        "name": "dsf-ai",
        "secrets": original.get("secrets", []),
        "stopTimeout": 120,
    }
    keep = (
        "cpu",
        "executionRoleArn",
        "memory",
        "networkMode",
        "requiresCompatibilities",
        "runtimePlatform",
        "taskRoleArn",
        "volumes",
    )
    task = {name: source[name] for name in keep if name in source}
    task.update({
        "containerDefinitions": [container],
        "ephemeralStorage": {"sizeInGiB": EPHEMERAL_GIB},
        "family": PROBE_FAMILY + "-" + mode,
    })
    return task


def _validate_proof(
    proof: object,
    *,
    mode: str,
    candidate_git_sha: str,
    candidate_image_digest: str,
    expected_identity: str,
    expected_tick: int | None,
    expected_state_sha256: str | None,
    expected_state_root: str | None = None,
    expected_motor_action_rehearsal: bool = False,
) -> dict[str, object]:
    if not isinstance(proof, dict):
        raise RuntimeError("native candidate proof is not an object")
    receipt = proof.get("receipt_sha256")
    record = dict(proof)
    record.pop("receipt_sha256", None)
    if mode == "genesis-rehearse":
        counts = (
            proof.get("complete_neuron_fractal_count"),
            proof.get("physically_transitioned_neuron_count"),
        )
        receipts = (
            proof.get("genesis_state_sha256"),
            proof.get("post_teach_state_sha256"),
        )
        if (
            proof.get("schema") != PROOF_SCHEMAS[mode]
            or proof.get("mode") != mode
            or proof.get("candidate_git_sha") != candidate_git_sha
            or proof.get("candidate_image_digest") != candidate_image_digest
            or proof.get("identity") != expected_identity
            or proof.get("python_callback_count") != 0
            or proof.get("python_cognition_workers_started") != 0
            or not isinstance(proof.get("taught_card_id"), str)
            or not proof["taught_card_id"]
            or any(
                not isinstance(count, int)
                or isinstance(count, bool)
                or count <= 0
                for count in counts
            )
            or any(
                not isinstance(value, str) or _SHA.fullmatch(value) is None
                for value in receipts
            )
            or proof["post_teach_state_sha256"] == proof["genesis_state_sha256"]
            or (
                expected_state_root is not None
                and proof.get("state_root") != expected_state_root
            )
            or receipt != hashlib.sha256(_canonical(record)).hexdigest()
        ):
            raise RuntimeError("native candidate proof changed")
        return proof
    actual_tick = proof.get("tick")
    actual_state_sha256 = proof.get("resident_state_sha256")
    source_advanced = (
        isinstance(actual_tick, int)
        and not isinstance(actual_tick, bool)
        and expected_tick is not None
        and actual_tick > expected_tick
    )
    migration_predecessor = proof.get("migration_predecessor_state_sha256")
    current_format_migration = (
        mode == "cold-restore"
        and proof.get("current_format_migration_rehearsed") is True
        and isinstance(migration_predecessor, str)
        and _SHA.fullmatch(migration_predecessor) is not None
        and (
            source_advanced
            or migration_predecessor == expected_state_sha256
        )
    )
    motor_action_rehearsal = (
        proof.get("motor_action_rehearsed") is True
        and isinstance(proof.get("motor_rehearsal_source_hop_count"), int)
        and not isinstance(proof["motor_rehearsal_source_hop_count"], bool)
        and proof["motor_rehearsal_source_hop_count"] > 0
        and isinstance(proof.get("motor_rehearsal_recruitment_count"), int)
        and not isinstance(proof["motor_rehearsal_recruitment_count"], bool)
        and proof["motor_rehearsal_recruitment_count"] > 0
        and isinstance(
            proof.get("motor_rehearsal_outward_elementary_carriers"), int
        )
        and not isinstance(
            proof["motor_rehearsal_outward_elementary_carriers"], bool
        )
        and proof["motor_rehearsal_outward_elementary_carriers"] > 0
        and isinstance(proof.get("motor_rehearsal_signed_yaw_millidegrees"), int)
        and not isinstance(proof["motor_rehearsal_signed_yaw_millidegrees"], bool)
        and proof["motor_rehearsal_signed_yaw_millidegrees"] != 0
        and isinstance(proof.get("motor_rehearsal_source_dsf_delivery_count"), int)
        and proof["motor_rehearsal_source_dsf_delivery_count"] > 0
        and isinstance(
            proof.get("motor_rehearsal_source_physical_transition_count"), int
        )
        and proof["motor_rehearsal_source_physical_transition_count"] > 0
        and isinstance(proof.get("motor_rehearsal_vestibular_tick_count"), int)
        and not isinstance(proof["motor_rehearsal_vestibular_tick_count"], bool)
        and proof["motor_rehearsal_vestibular_tick_count"] > 0
        and proof.get("motor_rehearsal_vestibular_dsf_delivery_count")
        == proof["motor_rehearsal_vestibular_tick_count"] * 2
        and isinstance(
            proof.get("motor_rehearsal_reached_neuron_growth"), int
        )
        and not isinstance(
            proof["motor_rehearsal_reached_neuron_growth"], bool
        )
        and proof["motor_rehearsal_reached_neuron_growth"] >= 0
        and isinstance(proof.get("motor_rehearsal_state_byte_delta"), int)
        and proof.get("motor_rehearsal_world_revision_delta") == 1
        and isinstance(
            proof.get("motor_rehearsal_successor_state_sha256"), str
        )
        and _SHA.fullmatch(
            proof["motor_rehearsal_successor_state_sha256"]
        )
        is not None
    )
    sparse_index_rehearsal = (
        proof.get("hippocampal_sparse_index_rehearsed") is True
        and proof.get("motor_action_rehearsed") is False
        and isinstance(proof.get("hippocampal_route_formation_receipt"), str)
        and _SHA.fullmatch(proof["hippocampal_route_formation_receipt"])
        is not None
        and isinstance(proof.get("hippocampal_route_index_lineage"), str)
        and re.fullmatch(
            r"[0-9a-f]{32}", proof["hippocampal_route_index_lineage"]
        )
        is not None
        and proof.get("hippocampal_route_inbound_bond_count") == 1
        and isinstance(proof.get("hippocampal_route_outbound_member_count"), int)
        and not isinstance(proof["hippocampal_route_outbound_member_count"], bool)
        and proof["hippocampal_route_outbound_member_count"] >= 3
        and isinstance(proof.get("hippocampal_route_layer_nine_count"), int)
        and not isinstance(proof["hippocampal_route_layer_nine_count"], bool)
        and proof["hippocampal_route_layer_nine_count"] > 0
        and isinstance(proof.get("hippocampal_route_inbound_transition_count"), int)
        and proof["hippocampal_route_inbound_transition_count"] > 0
        and isinstance(proof.get("hippocampal_route_outbound_transition_count"), int)
        and proof["hippocampal_route_outbound_transition_count"] > 0
        and isinstance(proof.get("hippocampal_route_state_byte_delta"), int)
        and isinstance(
            proof.get("hippocampal_route_successor_state_sha256"), str
        )
        and _SHA.fullmatch(
            proof["hippocampal_route_successor_state_sha256"]
        )
        is not None
    )
    if (
        proof.get("schema") != PROOF_SCHEMAS[mode]
        or proof.get("mode") != mode
        or proof.get("candidate_git_sha") != candidate_git_sha
        or proof.get("candidate_image_digest") != candidate_image_digest
        or proof.get("source_identity") != expected_identity
        or not isinstance(actual_tick, int)
        or isinstance(actual_tick, bool)
        or expected_tick is None
        or (mode != "cold-restore" and actual_tick != expected_tick)
        or (
            mode == "cold-restore"
            and (
                actual_tick < expected_tick
                or proof.get("baseline_observed_tick") != expected_tick
                or proof.get("baseline_observed_state_sha256")
                != expected_state_sha256
                or proof.get("source_advanced_after_baseline")
                is not source_advanced
            )
        )
        or proof.get("cold_restore_exact") is not True
        or proof.get("raw_glorun_current_only") is not True
        or proof.get("python_callback_count") != 0
        or proof.get("python_cognition_workers_started") != 0
        or (
            expected_motor_action_rehearsal
            and not (motor_action_rehearsal or sparse_index_rehearsal)
        )
        or not isinstance(proof.get("resident_state_bytes"), int)
        or isinstance(proof.get("resident_state_bytes"), bool)
        or proof["resident_state_bytes"] <= 0
        or not isinstance(actual_state_sha256, str)
        or _SHA.fullmatch(actual_state_sha256) is None
        or (
            mode == "cold-restore"
            and
            expected_state_sha256 is not None
            and actual_tick == expected_tick
            and actual_state_sha256 != expected_state_sha256
            and not current_format_migration
        )
        or receipt != hashlib.sha256(_canonical(record)).hexdigest()
    ):
        raise RuntimeError("native candidate proof changed")
    return proof


def _proof_from_logs(logs, *, group: str, stream: str, schema: str) -> object:
    token = None
    messages: list[str] = []
    while True:
        values = {
            "logGroupName": group,
            "logStreamName": stream,
            "startFromHead": True,
        }
        if token is not None:
            values["nextToken"] = token
        page = logs.get_log_events(**values)
        messages.extend(
            event.get("message", "")
            for event in page.get("events", [])
            if isinstance(event, dict)
        )
        next_token = page.get("nextForwardToken")
        if next_token == token:
            break
        token = next_token
    proofs = []
    for message in messages:
        try:
            value = json.loads(message)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema") == schema:
            proofs.append(value)
    if len(proofs) != 1:
        raise RuntimeError("candidate task did not emit one exact proof")
    return proofs[0]


def main() -> int:
    values = _arguments()
    if values.mode in {"rehearse", "publish"} and (
        not values.expected_baseline_generation
        or not values.expected_active_generation
    ):
        raise ValueError("migration task requires exact generation identities")
    if values.mode == "cold-restore" and not values.expected_state_sha256:
        raise ValueError("cold restore requires expected state SHA-256")
    if values.mode != "genesis-rehearse" and values.expected_tick is None:
        raise ValueError("migration task requires the exact source tick")
    genesis_state_root = None
    if values.mode == "genesis-rehearse":
        genesis_state_root = GENESIS_STORE_PREFIX + time.strftime(
            "%Y%m%dT%H%M%SZ", time.gmtime()
        )
    import boto3

    ecs = boto3.client("ecs", region_name=values.region)
    logs = boto3.client("logs", region_name=values.region)
    source = ecs.describe_task_definition(
        taskDefinition=values.candidate_task_definition
    )["taskDefinition"]
    source_containers = source.get("containerDefinitions", [])
    source_environment = {
        item.get("name"): item.get("value")
        for item in (
            source_containers[0].get("environment", [])
            if len(source_containers) == 1
            and isinstance(source_containers[0], dict)
            else []
        )
        if isinstance(item, dict)
    }
    expected_motor_action_rehearsal = (
        values.mode == "cold-restore"
        and source_environment.get("GUALA_VESTIBULAR") == "1"
    )
    task_input = probe_task_definition(
        source,
        mode=values.mode,
        candidate_git_sha=values.candidate_git_sha,
        candidate_image_digest=values.candidate_image_digest,
        expected_baseline_generation=values.expected_baseline_generation,
        expected_active_generation=values.expected_active_generation,
        expected_identity=values.expected_identity,
        expected_tick=values.expected_tick,
        expected_state_sha256=values.expected_state_sha256,
        genesis_state_root=genesis_state_root,
    )
    registered = ecs.register_task_definition(**task_input)["taskDefinition"]
    task_definition_arn = registered["taskDefinitionArn"]
    task_arn = None
    try:
        service = ecs.describe_services(
            cluster=values.cluster,
            services=[values.service],
        )["services"][0]
        response = ecs.run_task(
            cluster=values.cluster,
            taskDefinition=task_definition_arn,
            launchType="FARGATE",
            networkConfiguration=service["networkConfiguration"],
            count=1,
        )
        if response.get("failures") or len(response.get("tasks", [])) != 1:
            raise RuntimeError("native candidate task failed admission")
        task_arn = response["tasks"][0]["taskArn"]
        ecs.get_waiter("tasks_stopped").wait(
            cluster=values.cluster,
            tasks=[task_arn],
            WaiterConfig={"Delay": 5, "MaxAttempts": 180},
        )
        task = ecs.describe_tasks(
            cluster=values.cluster,
            tasks=[task_arn],
        )["tasks"][0]
        containers = task.get("containers", [])
        if len(containers) != 1 or containers[0].get("exitCode") != 0:
            raise RuntimeError(
                "native candidate task failed: "
                + json.dumps(task.get("stoppedReason"), sort_keys=True)
            )
        log_options = task_input["containerDefinitions"][0][
            "logConfiguration"
        ]["options"]
        group = log_options["awslogs-group"]
        # DescribeTasks does not return the awslogs stream name; it is
        # deterministic: <stream-prefix>/<container-name>/<task-id>.
        stream_name = containers[0].get("logStreamName") or "/".join(
            (
                log_options["awslogs-stream-prefix"],
                task_input["containerDefinitions"][0]["name"],
                task_arn.rsplit("/", 1)[-1],
            )
        )
        for _attempt in range(30):
            try:
                proof = _proof_from_logs(
                    logs,
                    group=group,
                    stream=stream_name,
                    schema=PROOF_SCHEMAS[values.mode],
                )
                break
            except RuntimeError:
                time.sleep(2)
        else:
            raise RuntimeError("native candidate proof was not delivered to logs")
        validated = _validate_proof(
            proof,
            mode=values.mode,
            candidate_git_sha=values.candidate_git_sha,
            candidate_image_digest=values.candidate_image_digest,
            expected_identity=values.expected_identity,
            expected_tick=values.expected_tick,
            expected_state_sha256=values.expected_state_sha256,
            expected_state_root=genesis_state_root,
            expected_motor_action_rehearsal=expected_motor_action_rehearsal,
        )
        print(_canonical(validated).decode("ascii"))
        return 0
    finally:
        if task_arn is not None:
            try:
                ecs.stop_task(
                    cluster=values.cluster,
                    task=task_arn,
                    reason="native candidate task complete",
                )
            except Exception:
                pass
        ecs.deregister_task_definition(taskDefinition=task_definition_arn)


if __name__ == "__main__":
    raise SystemExit(main())
