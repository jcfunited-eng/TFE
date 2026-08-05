"""One-shot task-853 migration rehearsal and native CURRENT publication.

The rehearsal reads the authenticated legacy predecessor from a read-only
mount, admits only its hard-bound GLMFAB03 bytes to the separately named native
migration, and proves raw binary publication/cold restore in ephemeral space.
Publication repeats that proof against a writable native-organism directory.
Ordinary production boot never imports or invokes this module.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from dsf_ai_service.glew_runtime.authenticated_task853_organism_migration import (
    REHEARSAL_MAX_ENVELOPE_BYTES,
    REHEARSAL_MAX_FABRIC_BYTES,
    REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
    TASK853_AUTHENTICATED_PREDECESSOR_TICK,
    TASK853_GLMFAB03_SHA256,
    TASK853_IDENTITY,
    migrate_authenticated_task853_predecessor,
)
from dsf_ai_service.glew_runtime.native_resident_organism import (
    restore_native_resident_organism,
)
from dsf_ai_service.substrate.native_organism_binary_store import (
    NativeOrganismBinaryStoreError,
    publish_staged_native_organism,
    restore_current_native_organism,
    stage_active_native_organism,
)


PROOF_SCHEMA = "guala.production_candidate_native_restore_rehearsal.v5"
PUBLICATION_SCHEMA = "guala.production_native_current_publication.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT = re.compile(r"[0-9a-f]{40}")
_CONTENT_MANIFEST_SCHEMA = "immutable_generation_content_manifest_v2"
_CONTENT_RECORD_SCHEMA = "immutable_generation_content_record_v2"
_CONTENT_CHUNK_SCHEMA = "immutable_generation_content_chunk_v1"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _generation_canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _uuid(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} is not a UUID")
    canonical = str(uuid.UUID(value))
    if value != canonical:
        raise ValueError(f"{label} is not canonical")
    return value


def _identity(value: object) -> str:
    if not isinstance(value, str) or value != TASK853_IDENTITY:
        raise ValueError("candidate source is not the authenticated organism")
    return value


def _tick(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value != TASK853_AUTHENTICATED_PREDECESSOR_TICK
    ):
        raise ValueError("candidate source tick is not authenticated")
    return value


def _regular_bytes(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label} is not a regular file")
    return path.read_bytes()


def _manifest(
    store_root: Path,
    generation: str,
    *,
    expected_identity: str,
    expected_tick: int | None,
) -> tuple[dict[str, object], Path]:
    directory = store_root / "generations" / generation
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("candidate source generation is absent")
    body = _regular_bytes(directory / "MANIFEST.json", "generation manifest")
    try:
        manifest = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("generation manifest is not strict JSON") from error
    if (
        not isinstance(manifest, dict)
        or body != _generation_canonical(manifest)
        or manifest.get("generation_uuid") != generation
        or manifest.get("identity") != expected_identity
        or (
            expected_tick is not None
            and manifest.get("tick") != expected_tick
        )
        or manifest.get("schema") != _CONTENT_MANIFEST_SCHEMA
        or not isinstance(manifest.get("required_files"), list)
    ):
        raise RuntimeError("candidate source generation manifest changed")
    return manifest, directory


def _record(manifest: dict[str, object], relative_path: str) -> dict[str, object]:
    matches = [
        item
        for item in manifest["required_files"]
        if isinstance(item, dict) and item.get("relative_path") == relative_path
    ]
    if len(matches) != 1:
        raise RuntimeError(f"candidate source lacks one {relative_path} record")
    return matches[0]


def _stored_payload(
    store_root: Path,
    generation: str,
    *,
    expected_identity: str,
    expected_tick: int,
    relative_path: str,
) -> bytes:
    manifest, _directory = _manifest(
        store_root,
        generation,
        expected_identity=expected_identity,
        expected_tick=expected_tick,
    )
    record = _record(manifest, relative_path)
    if (
        record.get("schema") != _CONTENT_RECORD_SCHEMA
        or record.get("json_payload") is not relative_path.endswith(".json")
        or not isinstance(record.get("chunks"), list)
        or not record["chunks"]
    ):
        raise RuntimeError("candidate content record changed")
    output = bytearray()
    for chunk in record["chunks"]:
        if (
            not isinstance(chunk, dict)
            or chunk.get("schema") != _CONTENT_CHUNK_SCHEMA
            or not isinstance(chunk.get("sha256"), str)
            or _SHA256.fullmatch(chunk["sha256"]) is None
            or not isinstance(chunk.get("size_bytes"), int)
            or isinstance(chunk.get("size_bytes"), bool)
            or chunk["size_bytes"] <= 0
        ):
            raise RuntimeError("candidate content chunk record changed")
        path = (
            store_root
            / "content-chunks"
            / chunk["sha256"][:2]
            / chunk["sha256"]
        )
        body = _regular_bytes(path, "generation content chunk")
        if len(body) != chunk["size_bytes"] or _sha256(body) != chunk["sha256"]:
            raise RuntimeError("candidate content chunk changed")
        output.extend(body)
    body = bytes(output)
    if (
        not isinstance(record.get("size_bytes"), int)
        or record["size_bytes"] != len(body)
        or not isinstance(record.get("sha256"), str)
        or _SHA256.fullmatch(record["sha256"]) is None
        or _sha256(body) != record["sha256"]
    ):
        raise RuntimeError("candidate generation payload changed")
    return body


def _predecessor(
    source_root: Path,
    *,
    expected_baseline_generation: str,
    expected_active_generation: str,
    expected_identity: str,
    expected_tick: int,
) -> bytes:
    _manifest(
        source_root / "sealed",
        expected_baseline_generation,
        expected_identity=expected_identity,
        expected_tick=None,
    )
    core = _stored_payload(
        source_root / "sealed-live-recovery",
        expected_active_generation,
        expected_identity=expected_identity,
        expected_tick=expected_tick,
        relative_path="guala_core.json",
    )
    try:
        parsed = json.loads(core)
        encoded = parsed["data"]["organism_state"]["native_materialized_fabric"][
            "state_base64"
        ]
        predecessor = base64.b64decode(encoded, validate=True)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("candidate source lacks the authenticated predecessor") from error
    if hashlib.sha256(predecessor).digest() != TASK853_GLMFAB03_SHA256:
        raise RuntimeError("candidate source predecessor digest changed")
    return predecessor


class _MemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_if_absent(self, key, chunks, *, byte_count, sha256):
        body = b"".join(chunks)
        if len(body) != byte_count or _sha256(body) != sha256:
            raise RuntimeError("rehearsal remote stage changed")
        prior = self.objects.get(key)
        if prior is not None:
            if prior != body:
                raise RuntimeError("rehearsal remote key collision")
            return False
        self.objects[key] = body
        return True

    def iter_bytes(self, key):
        body = self.objects[key]
        for offset in range(0, len(body), 1024 * 1024):
            yield body[offset : offset + 1024 * 1024]

    def delete_if_exact(self, key, *, byte_count, sha256):
        body = self.objects[key]
        if len(body) != byte_count or _sha256(body) != sha256:
            raise RuntimeError("rehearsal remote retirement changed")
        del self.objects[key]


class _S3ObjectStore:
    def __init__(self, *, bucket: str, client) -> None:
        self.bucket = bucket
        self.client = client

    def put_if_absent(self, key, chunks, *, byte_count, sha256):
        from botocore.exceptions import ClientError

        try:
            existing = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if error.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 404:
                raise
        else:
            metadata = existing.get("Metadata", {})
            if (
                existing.get("ContentLength") != byte_count
                or metadata.get("sha256") != sha256
            ):
                raise RuntimeError("native remote object collision")
            return False
        body = b"".join(chunks)
        if len(body) != byte_count or _sha256(body) != sha256:
            raise RuntimeError("native remote upload body changed")
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            Metadata={"sha256": sha256},
        )
        return True

    def iter_bytes(self, key):
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        yield from response["Body"].iter_chunks(chunk_size=1024 * 1024)

    def delete_if_exact(self, key, *, byte_count, sha256):
        existing = self.client.head_object(Bucket=self.bucket, Key=key)
        if (
            existing.get("ContentLength") != byte_count
            or existing.get("Metadata", {}).get("sha256") != sha256
        ):
            raise RuntimeError("native remote predecessor changed")
        self.client.delete_object(Bucket=self.bucket, Key=key)


def _round_trip(store_root: Path, predecessor: bytes, object_store) -> dict[str, object]:
    migration = migrate_authenticated_task853_predecessor(
        legacy_glmfab03=predecessor
    )
    organism = restore_native_resident_organism(
        current_envelope=migration.envelope,
        max_envelope_bytes=REHEARSAL_MAX_ENVELOPE_BYTES,
        max_fabric_bytes=REHEARSAL_MAX_FABRIC_BYTES,
        max_logical_peak_bytes=REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
    )
    reused = False
    try:
        current = restore_current_native_organism(
            store_root,
            max_envelope_bytes=REHEARSAL_MAX_ENVELOPE_BYTES,
            max_fabric_bytes=REHEARSAL_MAX_FABRIC_BYTES,
            max_logical_peak_bytes=REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
        )
    except NativeOrganismBinaryStoreError as error:
        if "CURRENT is absent" not in str(error):
            raise
        staged = stage_active_native_organism(
            store_root,
            organism,
            max_envelope_bytes=REHEARSAL_MAX_ENVELOPE_BYTES,
        )
        published = publish_staged_native_organism(
            staged,
            expected_predecessor_sha256=None,
            object_store=object_store,
            max_envelope_bytes=REHEARSAL_MAX_ENVELOPE_BYTES,
            max_fabric_bytes=REHEARSAL_MAX_FABRIC_BYTES,
            max_logical_peak_bytes=REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
        )
        pointer = published.pointer
    else:
        pointer = current.pointer
        reused = True
    restored = restore_current_native_organism(
        store_root,
        max_envelope_bytes=REHEARSAL_MAX_ENVELOPE_BYTES,
        max_fabric_bytes=REHEARSAL_MAX_FABRIC_BYTES,
        max_logical_peak_bytes=REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
    )
    observed = restored.organism.readiness()
    if (
        restored.organism.save() != migration.envelope
        or pointer.state_sha256 != migration.state_sha256
        or observed.identity != TASK853_IDENTITY
        or observed.organism_tick != TASK853_AUTHENTICATED_PREDECESSOR_TICK
        or observed.python_callback_count != 0
    ):
        raise RuntimeError("native candidate cold restore changed")
    return {
        "cognitive_mosaic_count": observed.cognitive_mosaic_count,
        "cognitive_trace_count": observed.cognitive_trace_count,
        "formation_activation_count": observed.formation_activation_count,
        "joint_field_count": observed.joint_field_count,
        "joint_neuron_count": observed.joint_neuron_count,
        "publication_reused": reused,
        "python_callback_count": 0,
        "resident_state_bytes": observed.state_bytes,
        "resident_state_sha256": observed.state_sha256,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("rehearse", "publish"), required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--native-store-root")
    parser.add_argument("--expected-baseline-generation", required=True)
    parser.add_argument("--expected-active-generation", required=True)
    parser.add_argument("--expected-identity", required=True)
    parser.add_argument("--expected-tick", required=True, type=int)
    parser.add_argument("--candidate-git-sha", required=True)
    parser.add_argument("--candidate-image-digest", required=True)
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    baseline = _uuid(values.expected_baseline_generation, "baseline generation")
    active = _uuid(values.expected_active_generation, "active generation")
    identity = _identity(values.expected_identity)
    tick = _tick(values.expected_tick)
    if _GIT.fullmatch(values.candidate_git_sha) is None:
        raise ValueError("candidate commit is not canonical")
    if (
        not values.candidate_image_digest.startswith("sha256:")
        or _SHA256.fullmatch(values.candidate_image_digest[7:]) is None
    ):
        raise ValueError("candidate image digest is not canonical")
    predecessor = _predecessor(
        Path(values.source_root),
        expected_baseline_generation=baseline,
        expected_active_generation=active,
        expected_identity=identity,
        expected_tick=tick,
    )
    if values.mode == "rehearse":
        with tempfile.TemporaryDirectory(prefix="guala-native-rehearsal-") as name:
            result = _round_trip(Path(name), predecessor, _MemoryObjectStore())
        schema = PROOF_SCHEMA
    else:
        if not values.native_store_root:
            raise ValueError("publication requires --native-store-root")
        import boto3

        bucket = os.environ.get("GUALA_S3_BACKUP_BUCKET")
        if not bucket:
            raise RuntimeError("publication has no native remote bucket")
        result = _round_trip(
            Path(values.native_store_root),
            predecessor,
            _S3ObjectStore(
                bucket=bucket,
                client=boto3.client("s3", region_name="us-east-1"),
            ),
        )
        schema = PUBLICATION_SCHEMA
    record = {
        "active_generation": active,
        "baseline_generation": baseline,
        "candidate_git_sha": values.candidate_git_sha,
        "candidate_image_digest": values.candidate_image_digest,
        "cold_restore_exact": True,
        "mode": values.mode,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "schema": schema,
        "source_identity": identity,
        "source_mount_read_only": values.mode == "rehearse",
        "tick": tick,
        **result,
    }
    proof = {**record, "receipt_sha256": _sha256(_canonical(record))}
    print(_canonical(proof).decode("ascii"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
