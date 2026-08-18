from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import snapshot_generation


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, dict[str, str]] = {}
        self.put_order: list[str] = []

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        del Bucket
        if Key not in self.objects:
            raise KeyError(Key)
        return {"ContentLength": len(self.objects[Key]), "Metadata": self.metadata.get(Key, {})}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, Metadata: dict[str, str], **kwargs: object) -> None:
        del Bucket
        if Key in self.objects and kwargs.get("IfNoneMatch") == "*":
            raise RuntimeError("precondition failed")
        self.objects[Key] = bytes(Body)
        self.metadata[Key] = dict(Metadata)
        self.put_order.append(Key)

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        del Bucket
        return {"Body": io.BytesIO(self.objects[Key])}


def write_source_artifacts(root: Path) -> None:
    snapshot = {"rows": [{"ticker": "A", "D_k": 1}], "generated_at_utc": "2026-08-18T00:00:00Z"}
    report = {"status": "ok", "rows_written": 1, "generated_at_utc": "2026-08-18T00:00:00Z"}
    (root / "uf_snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    (root / "uf_snapshot.ses.json").write_text('{"encrypted":"receipt-bound"}', encoding="utf-8")
    (root / "uf_snapshot_rebuild_report.json").write_text(json.dumps(report), encoding="utf-8")


def test_publication_writes_immutable_generation_before_current_pointer(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    write_source_artifacts(tmp_path)
    client = FakeS3()

    receipt = snapshot_generation.prepare_and_publish_generation(client)

    assert receipt["generation_id"].startswith("snapshot_pub_v2_")
    assert client.put_order[-1] == snapshot_generation.CURRENT_POINTER_KEY
    assert all("/generations/" in key for key in client.put_order[:-1])
    assert f"{snapshot_generation.S3_SNAPSHOT_PREFIX}/uf_snapshot.json" not in client.objects
    snapshot = json.loads((tmp_path / "uf_snapshot.json").read_text(encoding="utf-8"))
    report = json.loads((tmp_path / "uf_snapshot_rebuild_report.json").read_text(encoding="utf-8"))
    assert snapshot["publication_id"] == receipt["publication_id"]
    assert report["snapshot_generation_id"] == receipt["generation_id"]


def test_restore_verifies_every_artifact_before_writing(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.chdir(source)
    write_source_artifacts(source)
    client = FakeS3()
    snapshot_generation.prepare_and_publish_generation(client)
    pointer = json.loads(client.objects[snapshot_generation.CURRENT_POINTER_KEY])
    manifest = json.loads(client.objects[pointer["manifest_key"]])
    corrupted_key = manifest["artifacts"]["envelope"]["key"]
    client.objects[corrupted_key] += b"corrupt"
    destination = tmp_path / "destination"
    destination.mkdir()

    with pytest.raises(ValueError, match="failed its receipt"):
        snapshot_generation.restore_current_generation(destination, client)

    assert list(destination.iterdir()) == []


def test_restore_activates_exact_received_generation(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.chdir(source)
    write_source_artifacts(source)
    client = FakeS3()
    receipt = snapshot_generation.prepare_and_publish_generation(client)
    destination = tmp_path / "destination"
    destination.mkdir()

    manifest = snapshot_generation.restore_current_generation(destination, client)

    assert manifest["generation_id"] == receipt["generation_id"]
    assert {path.name for path in destination.iterdir()} == {
        "uf_snapshot.json",
        "uf_snapshot.ses.json",
        "uf_snapshot_rebuild_report.json",
        "uf_snapshot_generation_manifest.json",
    }
    restored_snapshot = json.loads((destination / "uf_snapshot.json").read_text(encoding="utf-8"))
    assert restored_snapshot["generation_id"] == receipt["generation_id"]


def test_startup_has_one_external_schedule_authority() -> None:
    startup = Path("tfe_startup.sh").read_text(encoding="utf-8")
    assert "EventBridge is the only scheduled trigger authority" in startup
    assert "tfe_refresh_daemon" not in startup
    assert "/api/admin/refresh" not in startup
    assert "/api/health" not in startup
