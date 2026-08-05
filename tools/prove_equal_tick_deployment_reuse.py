"""Issue a fresh deployment attempt from one frozen Guala state.

This management-plane program never starts the application, acquires the
process-lifetime organism owner lease, advances the lived tick, or writes an
organism state.  It is admitted only after the old serving owner has quiesced.
For a code-only handoff it proves that the hot overlay is exactly redundant
with the sealed baseline and refreshes only the nonce-bound attempt pointer.
For an explicitly requested physical-state migration it seals the exact
HMAC-authenticated hot overlay over its exact immutable baseline.  That
promotion advances only the causal state revision, never the lived tick, and
produces the distinct full composite required by the migration handoff.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any, Callable
import uuid

import boto3

from dsf_ai_service.substrate.deployment_generation import (
    CAUSAL_GENERATION_RECEIPT,
    discover_and_load_current,
    materialize_verified_generation,
    stage_authoritative_commit_upload,
    verify_deployment_seal,
)
from dsf_ai_service.substrate.live_recovery_generation import (
    LIVE_RECOVERY_LINEAGE_FILE,
    LiveRecoveryGenerationStore,
    verify_predecessor_current,
    verify_redundant_predecessor_current,
)


SUCCESS_SCHEMA = "guala.equal_tick_deployment_reuse.v1"
COMPOSITE_SUCCESS_SCHEMA = "guala.equal_tick_composite_seal.v2"
FAILURE_SCHEMA = "guala.equal_tick_deployment_reuse.failure.v1"
MAX_COLD_RESTORE_SECONDS = 540


class EqualTickDeploymentReuseError(RuntimeError):
    """The exact unchanged-generation reuse proof failed."""


def _rebase_promoted_active_recovery(
    *,
    live_recovery_root: Path,
    baseline,
    composite,
    active,
    hot_files: tuple[str, ...],
    hmac_key: bytes,
    max_generation_bytes: int,
    physical_byte_ceiling: int,
    physical_byte_scope: Path,
):
    manager = LiveRecoveryGenerationStore(
        live_recovery_root,
        baseline=baseline,
        hot_files=hot_files,
        hmac_key=hmac_key,
        state_file_tick_manifest="guala_core.json",
        max_encoded_generation_bytes=max_generation_bytes,
        physical_byte_ceiling=physical_byte_ceiling,
        physical_byte_scope=physical_byte_scope,
    )
    with tempfile.TemporaryDirectory(
        prefix="guala-equal-tick-overlay-rebase-"
    ) as root:
        source_root = Path(root)
        sources = {}
        for relative_path in hot_files:
            target = source_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                for block in active.iter_stored_chunks(relative_path):
                    stream.write(block)
                stream.flush()
                os.fsync(stream.fileno())
            sources[relative_path] = target
        rebased = manager.rebase_after_deployment_seal(
            baseline=composite,
            tick=composite.tick,
            files=sources,
        )
    for relative_path in hot_files:
        if (
            rebased.stored_bytes(relative_path)
            != composite.stored_bytes(relative_path)
        ):
            raise EqualTickDeploymentReuseError(
                "rebased active recovery differs from composite at "
                + relative_path
            )
    return rebased


def _deployment_hmac_key() -> bytes:
    secret = os.environ.get("GUALALOOM_API_KEY")
    if not isinstance(secret, str) or len(secret) < 16:
        raise EqualTickDeploymentReuseError(
            "GUALALOOM_API_KEY is required for deployment custody"
        )
    return hashlib.sha256(
        ("guala-deployment-seal-v1\0" + secret).encode("utf-8")
    ).digest()


def _expected_generation(
    generation,
    *,
    generation_uuid: str,
    manifest_sha256: str,
    identity: str,
    tick: int,
) -> None:
    expected = {
        "generation_uuid": generation_uuid,
        "manifest_sha256": manifest_sha256,
        "identity": identity,
        "tick": tick,
    }
    for field, value in expected.items():
        if getattr(generation, field) != value:
            raise EqualTickDeploymentReuseError(
                "sealed CURRENT differs from expected " + field
            )


def _isolated_cold_restore_validator(generation) -> bool:
    with tempfile.TemporaryDirectory(
        prefix="guala-equal-tick-cold-restore-"
    ) as root:
        active = Path(root) / "active"
        materialized = materialize_verified_generation(
            generation=generation,
            active_directory=active,
        )
        if materialized.generation_uuid != generation.generation_uuid:
            raise EqualTickDeploymentReuseError(
                "cold-restore materialization changed generation identity"
            )
        environment = os.environ.copy()
        repository_root = Path(__file__).resolve().parents[1]
        inherited = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = os.pathsep.join(
            value
            for value in (str(repository_root), inherited)
            if value
        )
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "dsf_ai_service.cold_restore_probe",
                    "--active-directory",
                    str(active),
                    "--expected-identity",
                    generation.identity,
                    "--expected-tick",
                    str(generation.tick),
                    "--allow-authenticated-current-schema-migration",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=MAX_COLD_RESTORE_SECONDS,
                env=environment,
            )
        except subprocess.TimeoutExpired as error:
            raise EqualTickDeploymentReuseError(
                "isolated cold restore exceeded 540 seconds"
            ) from error
        if completed.returncode != 0:
            diagnostic = (
                (completed.stdout or "") + (completed.stderr or "")
            )[-4096:]
            raise EqualTickDeploymentReuseError(
                "isolated cold restore failed: "
                + (diagnostic or "no diagnostic output")
            )
    return True


def _isolated_frozen_source_custody_validator(generation) -> bool:
    """Materialize and byte-verify a historical source without booting it.

    A migration source belongs to the prior runtime schema.  Its destination
    is cold-booted by the migration authority after the one-way transform.
    This boundary proves the source's immutable generation custody without
    falsely requiring the new runtime to interpret pre-migration state.
    """

    with tempfile.TemporaryDirectory(
        prefix="guala-equal-tick-frozen-source-"
    ) as root:
        active = Path(root) / "active"
        materialized = materialize_verified_generation(
            generation=generation,
            active_directory=active,
        )
        if materialized.generation_uuid != generation.generation_uuid:
            raise EqualTickDeploymentReuseError(
                "frozen source materialization changed generation identity"
            )
        measured = {
            path.relative_to(active).as_posix()
            for path in active.rglob("*")
            if path.is_file()
        }
        if measured != set(generation.required_files):
            raise EqualTickDeploymentReuseError(
                "frozen source materialization changed required files"
            )
    return True


def prove_equal_tick_deployment_reuse(
    *,
    store_root: Path,
    live_recovery_root: Path,
    expected_generation_uuid: str,
    expected_manifest_sha256: str,
    expected_identity: str,
    expected_tick: int,
    expected_active_recovery_generation: str,
    expected_active_recovery_manifest_sha256: str,
    expected_active_recovery_tick: int,
    bucket: str,
    prefix: str,
    nonce: str,
    max_generation_bytes: int,
    max_required_files: int,
    max_path_bytes: int,
    physical_byte_ceiling: int,
    physical_byte_scope: Path,
    s3_client: Any,
    hmac_key: bytes,
    cold_restore_validator: Callable[[Any], bool] | None = None,
    promote_active_recovery: bool = False,
) -> dict[str, Any]:
    if cold_restore_validator is None:
        cold_restore_validator = (
            _isolated_frozen_source_custody_validator
            if promote_active_recovery
            else _isolated_cold_restore_validator
        )
    discovered = discover_and_load_current(store_root)
    baseline = discovered.generation
    _expected_generation(
        baseline,
        generation_uuid=expected_generation_uuid,
        manifest_sha256=expected_manifest_sha256,
        identity=expected_identity,
        tick=expected_tick,
    )
    verifier = (
        verify_predecessor_current
        if promote_active_recovery
        else verify_redundant_predecessor_current
    )
    owner_observed_active = None
    if promote_active_recovery:
        discovered_active = discover_and_load_current(
            live_recovery_root
        ).generation
        try:
            discovered_lineage = discovered_active.payload(
                LIVE_RECOVERY_LINEAGE_FILE
            )
            discovered_hot_files = tuple(
                discovered_lineage["hot_files"]
            )
        except (KeyError, TypeError) as error:
            raise EqualTickDeploymentReuseError(
                "post-quiescence active recovery lineage is incomplete"
            ) from error
        manager = LiveRecoveryGenerationStore(
            live_recovery_root,
            baseline=baseline,
            hot_files=discovered_hot_files,
            hmac_key=hmac_key,
            state_file_tick_manifest="guala_core.json",
            max_encoded_generation_bytes=max_generation_bytes,
            physical_byte_ceiling=physical_byte_ceiling,
            physical_byte_scope=physical_byte_scope,
        )
        active_before = manager.load_current()
        if active_before is None:
            raise EqualTickDeploymentReuseError(
                "post-quiescence active recovery is absent"
            )
        try:
            canonical_owner_generation = str(uuid.UUID(
                expected_active_recovery_generation
            ))
        except (ValueError, AttributeError) as error:
            raise EqualTickDeploymentReuseError(
                "owner-observed active recovery is not a canonical UUID"
            ) from error
        if (
            canonical_owner_generation
            != expected_active_recovery_generation
            or not isinstance(
                expected_active_recovery_manifest_sha256,
                str,
            )
            or len(expected_active_recovery_manifest_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in (
                    expected_active_recovery_manifest_sha256
                )
            )
            or isinstance(expected_active_recovery_tick, bool)
            or not isinstance(expected_active_recovery_tick, int)
            or expected_active_recovery_tick < 0
            or active_before.tick != expected_active_recovery_tick
        ):
            raise EqualTickDeploymentReuseError(
                "owner-observed or post-quiescence active recovery "
                "differs from the frozen tick"
            )
        owner_observed_active = SimpleNamespace(
            generation_uuid=expected_active_recovery_generation,
            manifest_sha256=(
                expected_active_recovery_manifest_sha256
            ),
            tick=expected_active_recovery_tick,
        )
    else:
        post_quiescence_active = discover_and_load_current(
            live_recovery_root
        ).generation
        if post_quiescence_active.tick != expected_active_recovery_tick:
            raise EqualTickDeploymentReuseError(
                "post-quiescence redundant recovery changed the lived tick"
            )
        active_before = verifier(
            live_recovery_root,
            baseline=baseline,
            hmac_key=hmac_key,
            expected_generation_uuid=(post_quiescence_active.generation_uuid),
            expected_manifest_sha256=(post_quiescence_active.manifest_sha256),
            expected_tick=expected_active_recovery_tick,
            state_file_tick_manifest="guala_core.json",
        )
        owner_observed_active = SimpleNamespace(
            generation_uuid=expected_active_recovery_generation,
            manifest_sha256=expected_active_recovery_manifest_sha256,
            tick=expected_active_recovery_tick,
        )
    active_certificate = active_before.recovery_certificate_bytes()
    lineage = active_before.payload(LIVE_RECOVERY_LINEAGE_FILE)
    hot_files = tuple(lineage["hot_files"])
    if CAUSAL_GENERATION_RECEIPT in hot_files:
        raise EqualTickDeploymentReuseError(
            "active recovery cannot own the causal generation receipt"
        )
    records = {
        generation.generation_uuid: {
            record["relative_path"]: record
            for record in generation.recovery_certificate()[
                "required_files"
            ]
        }
        for generation in (baseline, active_before)
    }
    changed_hot_files = tuple(
        relative_path
        for relative_path in hot_files
        if active_before.stored_bytes(relative_path)
        != baseline.stored_bytes(relative_path)
    )
    if (
        promote_active_recovery
        and not changed_hot_files
        and active_before.tick == baseline.tick
    ):
        raise EqualTickDeploymentReuseError(
            "migration composite requested for a redundant active recovery"
        )

    def expected_source(relative_path):
        if promote_active_recovery and relative_path in hot_files:
            return active_before
        return baseline

    def stage_frozen_state(stage, admission):
        for relative_path in baseline.required_files:
            if relative_path == CAUSAL_GENERATION_RECEIPT:
                continue
            source = expected_source(relative_path)
            expected_size = int(
                records[source.generation_uuid][relative_path][
                    "size_bytes"
                ]
            )
            copied = 0
            with admission.open_binary(
                stage / relative_path,
                expected_size=expected_size,
            ) as destination:
                for block in source.iter_stored_chunks(relative_path):
                    destination.write(block)
                    copied += len(block)
            if copied != expected_size:
                raise EqualTickDeploymentReuseError(
                    "sealed baseline member changed while staged: "
                    + relative_path
                )
        return (
            active_before.tick
            if promote_active_recovery
            else baseline.tick
        )

    def verify_exact_live_recovery_promotion(
        current,
        staged_files,
        captured_tick,
    ) -> bool:
        if (
            current.recovery_certificate_bytes()
            != baseline.recovery_certificate_bytes()
            or captured_tick != (
                active_before.tick
                if promote_active_recovery
                else baseline.tick
            )
            or set(staged_files)
            != set(baseline.required_files).difference(
                {CAUSAL_GENERATION_RECEIPT}
            )
        ):
            return False
        for relative_path, staged_path in staged_files.items():
            source = expected_source(relative_path)
            record = records[source.generation_uuid][relative_path]
            digest = hashlib.sha256()
            measured = 0
            with staged_path.open("rb") as stream:
                while True:
                    block = stream.read(1024 * 1024)
                    if not block:
                        break
                    digest.update(block)
                    measured += len(block)
            if (
                measured != int(record["size_bytes"])
                or digest.hexdigest() != record["sha256"]
            ):
                return False
        return True

    result = stage_authoritative_commit_upload(
        store_root=store_root,
        identity=baseline.identity,
        save_callback=stage_frozen_state,
        s3_client=s3_client,
        bucket=bucket,
        prefix=prefix,
        hmac_key=hmac_key,
        nonce=nonce,
        max_encoded_generation_bytes=max_generation_bytes,
        max_dynamic_required_files=max_required_files,
        max_dynamic_path_bytes=max_path_bytes,
        cold_restore_validator=cold_restore_validator,
        physical_byte_ceiling=physical_byte_ceiling,
        physical_byte_scope=physical_byte_scope,
        purge_migration_escrow_prefix=None,
        allow_equal_tick_schema_migration=False,
        equal_tick_causal_transition_validator=(
            verify_exact_live_recovery_promotion
            if promote_active_recovery
            else None
        ),
    )
    if promote_active_recovery:
        if (
            result.read_only_remote_reuse_verified is not False
            or result.version_aware_remote_reconciliation is not True
            or result.generation.generation_uuid
            in {
                baseline.generation_uuid,
                active_before.generation_uuid,
            }
            or result.generation.manifest_sha256
            in {
                baseline.manifest_sha256,
                active_before.manifest_sha256,
            }
            or result.generation.identity != baseline.identity
            or result.generation.tick != active_before.tick
        ):
            raise EqualTickDeploymentReuseError(
                "generation authority did not publish the exact composite"
            )
    else:
        if (
            result.read_only_remote_reuse_verified is not True
            or result.version_aware_remote_reconciliation is not False
        ):
            raise EqualTickDeploymentReuseError(
                "generation authority did not return exact read-only reuse"
            )
        _expected_generation(
            result.generation,
            generation_uuid=expected_generation_uuid,
            manifest_sha256=expected_manifest_sha256,
            identity=expected_identity,
            tick=expected_tick,
        )
    unchanged_active = verifier(
        live_recovery_root,
        baseline=baseline,
        hmac_key=hmac_key,
        expected_generation_uuid=active_before.generation_uuid,
        expected_manifest_sha256=(
            active_before.manifest_sha256
        ),
        expected_tick=active_before.tick,
        state_file_tick_manifest="guala_core.json",
    )
    if unchanged_active.recovery_certificate_bytes() != active_certificate:
        raise EqualTickDeploymentReuseError(
            "active recovery changed during frozen-state seal"
        )
    if promote_active_recovery:
        active_after = _rebase_promoted_active_recovery(
            live_recovery_root=live_recovery_root,
            baseline=baseline,
            composite=result.generation,
            active=unchanged_active,
            hot_files=hot_files,
            hmac_key=hmac_key,
            max_generation_bytes=max_generation_bytes,
            physical_byte_ceiling=physical_byte_ceiling,
            physical_byte_scope=physical_byte_scope,
        )
        active_after = verify_predecessor_current(
            live_recovery_root,
            baseline=result.generation,
            hmac_key=hmac_key,
            expected_generation_uuid=active_after.generation_uuid,
            expected_manifest_sha256=active_after.manifest_sha256,
            expected_tick=active_after.tick,
            state_file_tick_manifest="guala_core.json",
        )
        if (
            active_after.generation_uuid
            in {
                baseline.generation_uuid,
                unchanged_active.generation_uuid,
                result.generation.generation_uuid,
            }
            or active_after.manifest_sha256
            in {
                baseline.manifest_sha256,
                unchanged_active.manifest_sha256,
                result.generation.manifest_sha256,
            }
            or active_after.tick != result.generation.tick
        ):
            raise EqualTickDeploymentReuseError(
                "rebased active recovery has invalid composite custody"
            )
    else:
        active_after = unchanged_active
    seal = verify_deployment_seal(
        result.seal_certificate_bytes(),
        hmac_key=hmac_key,
        expected_nonce=nonce,
    )
    receipt = {
        "active_recovery_generation": active_after.generation_uuid,
        "active_recovery_manifest_sha256": (
            active_after.manifest_sha256
        ),
        "active_recovery_tick": active_after.tick,
        "attempt_seal_hmac_sha256": seal["seal_hmac_sha256"],
        "causal_state_sha256": seal["causal_state_sha256"],
        "deploy_nonce_sha256": hashlib.sha256(
            nonce.encode("utf-8")
        ).hexdigest(),
        "deployment_baseline_generation": baseline.generation_uuid,
        "deployment_baseline_manifest_sha256": baseline.manifest_sha256,
        "deployment_baseline_tick": baseline.tick,
        "generation_uuid": result.generation.generation_uuid,
        "identity": result.generation.identity,
        "manifest_sha256": result.generation.manifest_sha256,
        "proof_mode": (
            "authenticated_live_recovery_promotion"
            if promote_active_recovery
            else "exact_read_only_reuse"
        ),
        "read_only_remote_reuse_verified": (
            not promote_active_recovery
        ),
        "pre_seal_active_recovery_generation": (
            active_before.generation_uuid
        ),
        "pre_seal_active_recovery_manifest_sha256": (
            active_before.manifest_sha256
        ),
        "pre_seal_active_recovery_tick": active_before.tick,
        "remote_retained_generation_uuids": list(
            result.remote_retained_generation_uuids
        ),
        "schema": (
            COMPOSITE_SUCCESS_SCHEMA
            if promote_active_recovery
            else SUCCESS_SCHEMA
        ),
        "state_revision": seal["state_revision"],
        "status": "sealed" if promote_active_recovery else "reused",
        "tick": result.generation.tick,
        "version_aware_remote_reconciliation": (
            promote_active_recovery
        ),
    }
    if promote_active_recovery:
        receipt.update({
            "owner_pre_quiescence_active_recovery_generation": (
                owner_observed_active.generation_uuid
            ),
            "owner_pre_quiescence_active_recovery_manifest_sha256": (
                owner_observed_active.manifest_sha256
            ),
            "owner_pre_quiescence_active_recovery_tick": (
                owner_observed_active.tick
            ),
        })
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--live-recovery-root", type=Path, required=True)
    parser.add_argument("--expected-generation", required=True)
    parser.add_argument("--expected-manifest", required=True)
    parser.add_argument("--expected-identity", required=True)
    parser.add_argument("--expected-tick", type=int, required=True)
    parser.add_argument(
        "--expected-active-recovery-generation",
        required=True,
    )
    parser.add_argument(
        "--expected-active-recovery-manifest",
        required=True,
    )
    parser.add_argument(
        "--expected-active-recovery-tick",
        type=int,
        required=True,
    )
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--max-generation-bytes", type=int, required=True)
    parser.add_argument("--max-required-files", type=int, required=True)
    parser.add_argument("--max-path-bytes", type=int, required=True)
    parser.add_argument("--physical-byte-ceiling", type=int, required=True)
    parser.add_argument("--physical-byte-scope", type=Path, required=True)
    parser.add_argument(
        "--promote-active-recovery",
        action="store_true",
    )
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    try:
        receipt = prove_equal_tick_deployment_reuse(
            store_root=arguments.store_root,
            live_recovery_root=arguments.live_recovery_root,
            expected_generation_uuid=arguments.expected_generation,
            expected_manifest_sha256=arguments.expected_manifest,
            expected_identity=arguments.expected_identity,
            expected_tick=arguments.expected_tick,
            expected_active_recovery_generation=(
                arguments.expected_active_recovery_generation
            ),
            expected_active_recovery_manifest_sha256=(
                arguments.expected_active_recovery_manifest
            ),
            expected_active_recovery_tick=(
                arguments.expected_active_recovery_tick
            ),
            bucket=arguments.bucket,
            prefix=arguments.prefix,
            nonce=arguments.nonce,
            max_generation_bytes=arguments.max_generation_bytes,
            max_required_files=arguments.max_required_files,
            max_path_bytes=arguments.max_path_bytes,
            physical_byte_ceiling=arguments.physical_byte_ceiling,
            physical_byte_scope=arguments.physical_byte_scope,
            s3_client=boto3.client("s3", region_name="us-east-1"),
            hmac_key=_deployment_hmac_key(),
            promote_active_recovery=arguments.promote_active_recovery,
        )
    except Exception as error:
        print(json.dumps(
            {
                "error": str(error),
                "schema": FAILURE_SCHEMA,
                "status": "failed",
            },
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ))
        return 1
    print(json.dumps(
        receipt,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
