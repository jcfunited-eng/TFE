"""Failure-propagation tests for the ring consumer's S3 replacement boundary."""

from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.persistence_consumer import S3Consumer


class InjectedS3Client:
    def __init__(self):
        self.uploaded = []
        self.deleted = []
        self.fail_upload_key = None
        self.fail_delete_key = None
        self.upload_attempted = threading.Event()

    def upload_file(self, local_path, bucket, key):
        self.uploaded.append((Path(local_path).name, bucket, key))
        self.upload_attempted.set()
        if key == self.fail_upload_key:
            raise OSError(f"upload rejected for {key}")

    def delete_object(self, *, Bucket, Key):
        self.deleted.append((Bucket, Key))
        if Key == self.fail_delete_key:
            raise OSError(f"delete rejected for {Key}")


class VersionedS3Client:
    def __init__(self):
        self.counter = 0
        self.versions = {}

    def _version(self):
        self.counter += 1
        return f"v{self.counter}"

    def upload_file(self, local_path, bucket, key):
        body = Path(local_path).read_bytes()
        self.versions.setdefault((bucket, key), []).insert(0, {
            "Body": body,
            "DeleteMarker": False,
            "VersionId": self._version(),
        })

    def list_object_versions(
            self, *, Bucket, Prefix, KeyMarker=None,
            VersionIdMarker=None):
        assert KeyMarker is None
        assert VersionIdMarker is None
        versions = []
        markers = []
        for (bucket, key), records in sorted(self.versions.items()):
            if bucket != Bucket or not key.startswith(Prefix):
                continue
            for record in records:
                target = (
                    markers
                    if record["DeleteMarker"]
                    else versions
                )
                target.append({
                    "Key": key,
                    "VersionId": record["VersionId"],
                })
        return {
            "DeleteMarkers": markers,
            "IsTruncated": False,
            "Versions": versions,
        }

    def delete_objects(self, *, Bucket, Delete):
        for requested in Delete["Objects"]:
            target = (Bucket, requested["Key"])
            retained = [
                record
                for record in self.versions.get(target, ())
                if record["VersionId"] != requested["VersionId"]
            ]
            if retained:
                self.versions[target] = retained
            else:
                self.versions.pop(target, None)
        return {"Errors": []}


def _write_recovery_point(state_dir, seq):
    checkpoint = state_dir / f"checkpoint-{seq}.json"
    checkpoint.write_text(f'{{"seq": {seq}}}')
    (state_dir / "events.log").write_text(f'{{"seq": {seq + 1}}}\n')
    return checkpoint


def test_failed_replacement_upload_preserves_prior_state_and_cursor(tmp_path):
    client = InjectedS3Client()
    consumer = S3Consumer(
        ring=None, state_dir=str(tmp_path), bucket="truth-bucket",
        s3_client=client)

    prior = _write_recovery_point(tmp_path, 10)
    consumer._check_and_upload()
    assert consumer._last_uploaded_seq == 10

    replacement = _write_recovery_point(tmp_path, 20)
    client.fail_upload_key = "guala/events/events-upto-20.log"

    with pytest.raises(OSError, match="upload rejected"):
        consumer._check_and_upload()

    assert consumer._last_uploaded_seq == 10
    assert prior.exists()
    assert replacement.exists()
    assert client.deleted == []


def test_successful_replacement_advances_only_after_prior_retirement(tmp_path):
    client = InjectedS3Client()
    consumer = S3Consumer(
        ring=None, state_dir=str(tmp_path), bucket="truth-bucket",
        s3_client=client)

    prior = _write_recovery_point(tmp_path, 10)
    consumer._check_and_upload()
    replacement = _write_recovery_point(tmp_path, 20)
    consumer._check_and_upload()

    assert consumer._last_uploaded_seq == 20
    assert prior.exists()
    assert replacement.exists()
    assert client.deleted == [
        ("truth-bucket", "guala/checkpoints/checkpoint-10.json"),
        ("truth-bucket", "guala/events/events-upto-10.log"),
    ]


def test_delete_failure_propagates_and_does_not_claim_advance(tmp_path):
    client = InjectedS3Client()
    consumer = S3Consumer(
        ring=None, state_dir=str(tmp_path), bucket="truth-bucket",
        s3_client=client)

    prior = _write_recovery_point(tmp_path, 10)
    consumer._check_and_upload()
    replacement = _write_recovery_point(tmp_path, 20)
    client.fail_delete_key = "guala/checkpoints/checkpoint-10.json"

    with pytest.raises(OSError, match="delete rejected"):
        consumer._check_and_upload()

    assert consumer._last_uploaded_seq == 10
    assert prior.exists()
    assert replacement.exists()


def test_restart_uses_local_predecessor_for_remote_retirement(tmp_path):
    client = InjectedS3Client()
    predecessor = _write_recovery_point(tmp_path, 10)
    current = _write_recovery_point(tmp_path, 20)
    consumer = S3Consumer(
        ring=None,
        state_dir=str(tmp_path),
        bucket="truth-bucket",
        s3_client=client,
    )

    consumer._check_and_upload()

    assert consumer._last_uploaded_seq == 20
    assert predecessor.exists()
    assert current.exists()
    assert client.deleted == [
        ("truth-bucket", "guala/checkpoints/checkpoint-10.json"),
        ("truth-bucket", "guala/events/events-upto-10.log"),
    ]


def test_production_retirement_removes_every_version_and_delete_marker(
    tmp_path,
):
    client = VersionedS3Client()
    consumer = S3Consumer(
        ring=None,
        state_dir=str(tmp_path),
        bucket="truth-bucket",
        s3_client=client,
        version_aware_retirement=True,
    )
    _write_recovery_point(tmp_path, 10)
    consumer._check_and_upload()
    for records in client.versions.values():
        records.append({
            "Body": b"",
            "DeleteMarker": True,
            "VersionId": client._version(),
        })
        records.append({
            "Body": b"old-copy",
            "DeleteMarker": False,
            "VersionId": client._version(),
        })

    _write_recovery_point(tmp_path, 20)
    consumer._check_and_upload()

    assert all(
        "10" not in key
        for _bucket, key in client.versions
    )
    assert {
        key for _bucket, key in client.versions
    } == {
        "guala/checkpoints/checkpoint-20.json",
        "guala/events/events-upto-20.log",
    }


def test_background_failure_is_re_raised_by_stop(tmp_path):
    client = InjectedS3Client()
    _write_recovery_point(tmp_path, 10)
    client.fail_upload_key = "guala/checkpoints/checkpoint-10.json"
    consumer = S3Consumer(
        ring=None, state_dir=str(tmp_path), bucket="truth-bucket",
        s3_client=client)

    consumer.start()
    assert client.upload_attempted.wait(1.0)
    with pytest.raises(RuntimeError, match="S3 consumer failed") as exc_info:
        consumer.stop(timeout=2.0)

    assert isinstance(exc_info.value.__cause__, OSError)
