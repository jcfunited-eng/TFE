"""Immutable publication and verified restoration for one UF snapshot generation."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator


S3_SNAPSHOT_BUCKET = "tfe-codebuild-src-418384447921-us-east-1"
S3_SNAPSHOT_PREFIX = "runtime-refresh-checkpoints"
CURRENT_POINTER_KEY = f"{S3_SNAPSHOT_PREFIX}/current.json"
LOCAL_MANIFEST_PATH = Path("uf_snapshot_generation_manifest.json")
ARTIFACT_PATHS = {
    "snapshot": Path("uf_snapshot.json"),
    "envelope": Path("uf_snapshot.ses.json"),
    "report": Path("uf_snapshot_rebuild_report.json"),
}
PRIVATE_FILE_MODE = 0o600


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: object, *, pretty: bool = False) -> bytes:
    if pretty:
        body = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    else:
        body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return (body + "\n").encode("utf-8")


def _atomic_private_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, PRIVATE_FILE_MODE)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, PRIVATE_FILE_MODE)
    finally:
        if temporary.exists():
            temporary.unlink()


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be one JSON object")
    return value


def _load_json(path: Path, label: str) -> dict[str, Any]:
    return _object(json.loads(path.read_text(encoding="utf-8")), label)


def prepare_local_generation() -> dict[str, Any]:
    for label, path in ARTIFACT_PATHS.items():
        if not path.is_file():
            raise FileNotFoundError(f"{label} artifact is missing: {path}")

    snapshot = _load_json(ARTIFACT_PATHS["snapshot"], "snapshot")
    report = _load_json(ARTIFACT_PATHS["report"], "rebuild report")
    generated_at = str(snapshot.get("generated_at_utc") or "").strip()
    rows = snapshot.get("rows")
    if not generated_at or not isinstance(rows, list) or not rows:
        raise ValueError("snapshot requires generated_at_utc and non-empty rows")
    if str(report.get("generated_at_utc") or "").strip() != generated_at:
        raise ValueError("snapshot and rebuild report generated_at_utc do not match")
    if str(report.get("status") or "").strip() != "ok":
        raise ValueError(f"rebuild report is not publishable: status={report.get('status')}")
    if int(report.get("rows_written") or 0) != len(rows):
        raise ValueError("snapshot row count does not match rebuild report")

    payload_base = {"generated_at_utc": generated_at, "rows": rows}
    payload_digest = _sha256(_json_bytes(payload_base))
    publication_id = f"snapshot_pub_v2_{payload_digest[:24]}"
    generation_id = publication_id
    snapshot.update(
        publication_id=publication_id,
        generation_id=generation_id,
        snapshot_payload_digest_sha256=payload_digest,
    )
    report.update(
        snapshot_publication_id=publication_id,
        snapshot_generation_id=generation_id,
        snapshot_payload_digest_sha256=payload_digest,
        publication_schema="tfe.snapshot-generation.v1",
    )
    _atomic_private_bytes(ARTIFACT_PATHS["snapshot"], _json_bytes(snapshot))
    _atomic_private_bytes(ARTIFACT_PATHS["report"], _json_bytes(report, pretty=True))

    generation_prefix = f"{S3_SNAPSHOT_PREFIX}/generations/{generation_id}"
    artifacts: dict[str, dict[str, object]] = {}
    for name, path in ARTIFACT_PATHS.items():
        data = path.read_bytes()
        artifacts[name] = {
            "filename": path.name,
            "key": f"{generation_prefix}/{path.name}",
            "sha256": _sha256(data),
            "bytes": len(data),
        }
    manifest: dict[str, Any] = {
        "schema": "tfe.snapshot-generation.v1",
        "generation_id": generation_id,
        "publication_id": publication_id,
        "generated_at_utc": generated_at,
        "snapshot_payload_digest_sha256": payload_digest,
        "artifacts": artifacts,
    }
    manifest_bytes = _json_bytes(manifest, pretty=True)
    manifest["manifest_sha256"] = _sha256(manifest_bytes)
    manifest_bytes = _json_bytes(manifest, pretty=True)
    _atomic_private_bytes(LOCAL_MANIFEST_PATH, manifest_bytes)
    return manifest


def _head_matches(client: Any, *, bucket: str, key: str, digest: str, size: int) -> bool:
    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except Exception:
        return False
    metadata = head.get("Metadata") if isinstance(head, dict) else None
    observed_digest = str((metadata or {}).get("sha256") or "")
    observed_size = int(head.get("ContentLength") or -1) if isinstance(head, dict) else -1
    if observed_digest != digest or observed_size != size:
        raise RuntimeError(f"immutable S3 object conflicts with generation receipt: {key}")
    return True


def _put_immutable(client: Any, *, bucket: str, key: str, data: bytes, content_type: str) -> None:
    digest = _sha256(data)
    if _head_matches(client, bucket=bucket, key=key, digest=digest, size=len(data)):
        return
    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata={"sha256": digest},
            IfNoneMatch="*",
        )
    except Exception:
        if not _head_matches(client, bucket=bucket, key=key, digest=digest, size=len(data)):
            raise
    if not _head_matches(client, bucket=bucket, key=key, digest=digest, size=len(data)):
        raise RuntimeError(f"immutable S3 object receipt could not be verified: {key}")


def publish_prepared_generation(manifest: dict[str, Any], client: Any | None = None) -> dict[str, Any]:
    if client is None:
        import boto3  # type: ignore[import]

        client = boto3.client("s3")
    generation_id = str(manifest["generation_id"])
    for name, receipt in manifest["artifacts"].items():
        path = ARTIFACT_PATHS[name]
        data = path.read_bytes()
        if _sha256(data) != receipt["sha256"] or len(data) != receipt["bytes"]:
            raise RuntimeError(f"local artifact changed after generation preparation: {path}")
        _put_immutable(
            client,
            bucket=S3_SNAPSHOT_BUCKET,
            key=str(receipt["key"]),
            data=data,
            content_type="application/json",
        )

    manifest_key = f"{S3_SNAPSHOT_PREFIX}/generations/{generation_id}/manifest.json"
    manifest_bytes = LOCAL_MANIFEST_PATH.read_bytes()
    manifest_digest = _sha256(manifest_bytes)
    _put_immutable(
        client,
        bucket=S3_SNAPSHOT_BUCKET,
        key=manifest_key,
        data=manifest_bytes,
        content_type="application/json",
    )
    pointer = {
        "schema": "tfe.snapshot-current.v1",
        "generation_id": generation_id,
        "publication_id": manifest["publication_id"],
        "generated_at_utc": manifest["generated_at_utc"],
        "manifest_key": manifest_key,
        "manifest_sha256": manifest_digest,
    }
    pointer_bytes = _json_bytes(pointer, pretty=True)
    client.put_object(
        Bucket=S3_SNAPSHOT_BUCKET,
        Key=CURRENT_POINTER_KEY,
        Body=pointer_bytes,
        ContentType="application/json",
        Metadata={"sha256": _sha256(pointer_bytes), "generation-id": generation_id},
    )
    print(
        f"[UF-SNAPSHOT] Published immutable generation {generation_id}; "
        f"pointer=s3://{S3_SNAPSHOT_BUCKET}/{CURRENT_POINTER_KEY}",
        flush=True,
    )
    return pointer


def prepare_and_publish_generation(client: Any | None = None) -> dict[str, Any]:
    manifest = prepare_local_generation()
    pointer = publish_prepared_generation(manifest, client=client)
    return {**pointer, "snapshot_payload_digest_sha256": manifest["snapshot_payload_digest_sha256"]}


@contextmanager
def hide_mutable_snapshot_artifacts() -> Iterator[None]:
    held: list[tuple[Path, Path]] = []
    try:
        for path in ARTIFACT_PATHS.values():
            if not path.exists():
                continue
            hidden = path.with_name(f".{path.name}.{os.getpid()}.generation-hold")
            os.replace(path, hidden)
            held.append((path, hidden))
        yield
    finally:
        for path, hidden in held:
            if hidden.exists():
                os.replace(hidden, path)


def retain_bar_cache_export_without_mutable_snapshot_upload(legacy_upload: Callable[[], None]) -> None:
    print("[UF-SNAPSHOT] Mutable snapshot S3 keys disabled; retaining independent bar-cache export lane.", flush=True)
    with hide_mutable_snapshot_artifacts():
        legacy_upload()


def _get_object_bytes(client: Any, bucket: str, key: str) -> bytes:
    response = client.get_object(Bucket=bucket, Key=key)
    body = response.get("Body") if isinstance(response, dict) else None
    if body is None:
        raise RuntimeError(f"S3 object has no body: {key}")
    data = body.read()
    return data if isinstance(data, bytes) else bytes(data)


def restore_current_generation(destination_root: Path, client: Any | None = None) -> dict[str, Any]:
    if client is None:
        import boto3  # type: ignore[import]

        client = boto3.client("s3")
    pointer_bytes = _get_object_bytes(client, S3_SNAPSHOT_BUCKET, CURRENT_POINTER_KEY)
    pointer = _object(json.loads(pointer_bytes), "snapshot current pointer")
    if pointer.get("schema") != "tfe.snapshot-current.v1":
        raise ValueError("snapshot current pointer schema is unsupported")
    manifest_key = str(pointer.get("manifest_key") or "")
    manifest_digest = str(pointer.get("manifest_sha256") or "")
    if not manifest_key or not manifest_digest:
        raise ValueError("snapshot current pointer is incomplete")
    manifest_bytes = _get_object_bytes(client, S3_SNAPSHOT_BUCKET, manifest_key)
    if _sha256(manifest_bytes) != manifest_digest:
        raise ValueError("snapshot generation manifest failed its pointer receipt")
    manifest = _object(json.loads(manifest_bytes), "snapshot generation manifest")
    if manifest.get("schema") != "tfe.snapshot-generation.v1":
        raise ValueError("snapshot generation manifest schema is unsupported")
    if manifest.get("generation_id") != pointer.get("generation_id"):
        raise ValueError("snapshot generation identity does not match current pointer")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(ARTIFACT_PATHS):
        raise ValueError("snapshot generation manifest artifact set is incomplete")
    received: dict[str, bytes] = {}
    for name, local_relative in ARTIFACT_PATHS.items():
        receipt = _object(artifacts[name], f"{name} receipt")
        data = _get_object_bytes(client, S3_SNAPSHOT_BUCKET, str(receipt.get("key") or ""))
        if len(data) != int(receipt.get("bytes") or -1) or _sha256(data) != receipt.get("sha256"):
            raise ValueError(f"snapshot generation artifact failed its receipt: {name}")
        if str(receipt.get("filename") or "") != local_relative.name:
            raise ValueError(f"snapshot generation artifact filename mismatch: {name}")
        received[name] = data

    for name, relative in ARTIFACT_PATHS.items():
        _atomic_private_bytes(destination_root / relative.name, received[name])
    _atomic_private_bytes(destination_root / LOCAL_MANIFEST_PATH.name, manifest_bytes)
    print(
        f"[RESTORE] Verified snapshot generation {manifest['generation_id']} "
        f"({len(received)} bound artifacts).",
        flush=True,
    )
    return manifest
