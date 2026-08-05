"""Publish one authenticated unified Guala generation without owner files.

This management-plane program is run only while the serving owner count is
zero.  It cold-restores the exact sealed source, permits only the runtime's
explicit authenticated current-schema migrations, writes the resulting raw
resident organism and its core receipt, cold-restores that candidate, and publishes it through the
authoritative generation transaction.  It never starts the web application,
acquires the process-lifetime organism lease, advances lived time, invents
meaning, or imports retired graph/database state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import boto3

from dsf_ai_service.substrate.deployment_generation import (
    discover_and_load_current,
    materialize_verified_generation,
    stage_authoritative_commit_upload,
)
from dsf_ai_service.substrate.live_recovery_generation import (
    retire_redundant_predecessor_current,
    verify_redundant_predecessor_current,
)
from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from tools.prove_equal_tick_deployment_reuse import (
    _isolated_cold_restore_validator,
)


SUCCESS_SCHEMA = "guala.unified_generation_publication.v1"


class UnifiedGenerationPublicationError(RuntimeError):
    """The exact unified-generation publication failed."""


def _deployment_hmac_key() -> bytes:
    secret = os.environ.get("GUALALOOM_API_KEY")
    if not isinstance(secret, str) or len(secret) < 16:
        raise UnifiedGenerationPublicationError(
            "GUALALOOM_API_KEY is required for generation custody"
        )
    return hashlib.sha256(
        ("guala-deployment-seal-v1\0" + secret).encode("utf-8")
    ).digest()


def _exact_source(
    *,
    store_root: Path,
    generation_uuid: str,
    manifest_sha256: str,
    identity: str,
    tick: int,
):
    discovered = discover_and_load_current(store_root)
    source = discovered.generation
    expected = {
        "generation_uuid": generation_uuid,
        "manifest_sha256": manifest_sha256,
        "identity": identity,
        "tick": tick,
    }
    for field, value in expected.items():
        if getattr(source, field) != value:
            raise UnifiedGenerationPublicationError(
                "CURRENT differs from expected source " + field
            )
    return source


def _retire_redundant_overlay(
    *,
    live_recovery_root: Path,
    source,
    hmac_key: bytes,
    physical_byte_authority: PhysicalByteCeilingAuthority,
) -> tuple[str, ...]:
    if not live_recovery_root.exists():
        return ()
    active = discover_and_load_current(live_recovery_root).generation
    verified = verify_redundant_predecessor_current(
        live_recovery_root,
        baseline=source,
        hmac_key=hmac_key,
        expected_generation_uuid=active.generation_uuid,
        expected_manifest_sha256=active.manifest_sha256,
        expected_tick=active.tick,
        state_file_tick_manifest="guala_core.json",
    )
    if verified.tick != source.tick:
        raise UnifiedGenerationPublicationError(
            "live recovery advanced beyond the frozen source"
        )
    retired = retire_redundant_predecessor_current(
        live_recovery_root,
        baseline=source,
        hmac_key=hmac_key,
        physical_byte_authority=physical_byte_authority,
    )
    if live_recovery_root.exists():
        raise UnifiedGenerationPublicationError(
            "redundant live recovery was not retired exactly"
        )
    return retired


def publish_unified_generation(
    *,
    store_root: Path,
    live_recovery_root: Path,
    expected_generation: str,
    expected_manifest: str,
    expected_identity: str,
    expected_tick: int,
    bucket: str,
    prefix: str,
    nonce: str,
    max_generation_bytes: int,
    max_required_files: int,
    max_path_bytes: int,
    physical_byte_ceiling: int,
    physical_byte_scope: Path,
) -> dict[str, object]:
    source = _exact_source(
        store_root=store_root,
        generation_uuid=expected_generation,
        manifest_sha256=expected_manifest,
        identity=expected_identity,
        tick=expected_tick,
    )
    hmac_key = _deployment_hmac_key()
    physical_byte_authority = PhysicalByteCeilingAuthority(
        physical_byte_scope,
        physical_byte_ceiling,
    )
    retired_overlay = _retire_redundant_overlay(
        live_recovery_root=live_recovery_root,
        source=source,
        hmac_key=hmac_key,
        physical_byte_authority=physical_byte_authority,
    )

    with tempfile.TemporaryDirectory(
        prefix="guala-unified-source-"
    ) as source_root_text, tempfile.TemporaryDirectory(
        prefix="guala-unified-destination-"
    ) as destination_root_text:
        source_root = Path(source_root_text)
        destination_root = Path(destination_root_text)
        materialized = materialize_verified_generation(
            generation=source,
            active_directory=source_root,
        )
        if materialized.generation_uuid != source.generation_uuid:
            raise UnifiedGenerationPublicationError(
                "source materialization changed generation identity"
            )

        runtime = None
        try:
            runtime = Guala()
            runtime.load_full_state(
                source_root,
                require_exact_binary=True,
                allow_authenticated_current_schema_migration=True,
            )
            if (
                not bool(getattr(runtime, "_load_successful", False))
                or runtime._guala_identity != source.identity
                or runtime.tick != source.tick
            ):
                raise UnifiedGenerationPublicationError(
                    "unified cold restore changed identity or lived tick"
                )
            runtime.save_full_state(
                destination_root,
                publish_generation=False,
            )
        finally:
            if runtime is not None:
                runtime.quiesce_background_workers(timeout=120.0)

        expected_files = {
            "guala_core.json",
            "guala_identity.json",
            "guala_organism.glorun",
        }
        actual_files = {
            path.relative_to(destination_root).as_posix()
            for path in destination_root.rglob("*")
            if path.is_file()
        }
        if actual_files != expected_files:
            raise UnifiedGenerationPublicationError(
                "unified save emitted non-organism files: "
                + ", ".join(sorted(actual_files))
            )

        def save_candidate(stage: Path, admission) -> int:
            for relative_path in sorted(expected_files):
                admission.copy_regular_file(
                    destination_root / relative_path,
                    stage / relative_path,
                    logical_path=relative_path,
                )
            return source.tick

        publication = stage_authoritative_commit_upload(
            store_root=store_root,
            identity=source.identity,
            save_callback=save_candidate,
            s3_client=boto3.client("s3", region_name="us-east-1"),
            bucket=bucket,
            prefix=prefix,
            hmac_key=hmac_key,
            nonce=nonce,
            max_encoded_generation_bytes=max_generation_bytes,
            max_dynamic_required_files=max_required_files,
            max_dynamic_path_bytes=max_path_bytes,
            cold_restore_validator=_isolated_cold_restore_validator,
            physical_byte_ceiling=physical_byte_ceiling,
            physical_byte_scope=physical_byte_scope,
            allow_equal_tick_schema_migration=True,
        )

    destination = publication.generation
    if (
        destination.generation_uuid == source.generation_uuid
        or destination.identity != source.identity
        or destination.tick != source.tick
        or set(destination.required_files)
        != {"CAUSAL_GENERATION.json", "guala_core.json", "guala_identity.json"}
    ):
        raise UnifiedGenerationPublicationError(
            "published destination is not the exact unified organism"
        )
    return {
        "destination_generation": destination.generation_uuid,
        "destination_manifest_sha256": destination.manifest_sha256,
        "identity": destination.identity,
        "retired_live_recovery_generations": list(retired_overlay),
        "schema": SUCCESS_SCHEMA,
        "source_generation": source.generation_uuid,
        "source_manifest_sha256": source.manifest_sha256,
        "status": "published",
        "tick": destination.tick,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--live-recovery-root", type=Path, required=True)
    parser.add_argument("--expected-generation", required=True)
    parser.add_argument("--expected-manifest", required=True)
    parser.add_argument("--expected-identity", required=True)
    parser.add_argument("--expected-tick", type=int, required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--max-generation-bytes", type=int, required=True)
    parser.add_argument("--max-required-files", type=int, required=True)
    parser.add_argument("--max-path-bytes", type=int, required=True)
    parser.add_argument("--physical-byte-ceiling", type=int, required=True)
    parser.add_argument("--physical-byte-scope", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    try:
        receipt = publish_unified_generation(
            store_root=values.store_root,
            live_recovery_root=values.live_recovery_root,
            expected_generation=values.expected_generation,
            expected_manifest=values.expected_manifest,
            expected_identity=values.expected_identity,
            expected_tick=values.expected_tick,
            bucket=values.bucket,
            prefix=values.prefix,
            nonce=values.nonce,
            max_generation_bytes=values.max_generation_bytes,
            max_required_files=values.max_required_files,
            max_path_bytes=values.max_path_bytes,
            physical_byte_ceiling=values.physical_byte_ceiling,
            physical_byte_scope=values.physical_byte_scope,
        )
    except Exception as error:
        print(json.dumps({
            "error": str(error),
            "schema": "guala.unified_generation_publication.failure.v1",
            "status": "failed",
        }, separators=(",", ":"), sort_keys=True))
        return 1
    print(json.dumps(receipt, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
