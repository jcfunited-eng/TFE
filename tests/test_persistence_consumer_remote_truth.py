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
    assert not prior.exists()
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
