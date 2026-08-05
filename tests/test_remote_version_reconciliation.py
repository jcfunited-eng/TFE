from __future__ import annotations

import io
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate.deployment_generation import (
    reconcile_remote_generation_prefixes,
    upload_verified_generation,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)


class VersionedMemoryS3:
    def __init__(self) -> None:
        self._counter = 0
        self.versions: dict[tuple[str, str], list[dict]] = {}

    def _next(self) -> str:
        self._counter += 1
        return f"v{self._counter:08d}"

    def put_object(self, *, Bucket, Key, Body):
        version = self._next()
        self.versions.setdefault((Bucket, Key), []).insert(0, {
            "VersionId": version,
            "Body": bytes(Body),
            "DeleteMarker": False,
        })
        return {"VersionId": version}

    def get_object(self, *, Bucket, Key):
        latest = self.versions[(Bucket, Key)][0]
        if latest["DeleteMarker"]:
            raise KeyError(Key)
        return {
            "Body": io.BytesIO(latest["Body"]),
            "VersionId": latest["VersionId"],
        }

    def list_objects_v2(self, *, Bucket, Prefix, ContinuationToken=None):
        assert ContinuationToken is None
        keys = []
        for (bucket, key), records in sorted(self.versions.items()):
            if (
                bucket == Bucket
                and key.startswith(Prefix)
                and records
                and not records[0]["DeleteMarker"]
            ):
                keys.append({"Key": key})
        return {"Contents": keys, "IsTruncated": False}

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
            for index, record in enumerate(records):
                target = markers if record["DeleteMarker"] else versions
                target.append({
                    "Key": key,
                    "VersionId": record["VersionId"],
                    "IsLatest": index == 0,
                })
        return {
            "Versions": versions,
            "DeleteMarkers": markers,
            "IsTruncated": False,
        }

    def delete_objects(self, *, Bucket, Delete):
        for item in Delete["Objects"]:
            key = item["Key"]
            version_id = item.get("VersionId")
            records = self.versions.setdefault((Bucket, key), [])
            if version_id is None:
                records.insert(0, {
                    "VersionId": self._next(),
                    "Body": b"",
                    "DeleteMarker": True,
                })
            else:
                records[:] = [
                    record
                    for record in records
                    if record["VersionId"] != version_id
                ]
                if not records:
                    del self.versions[(Bucket, key)]
        return {}


def test_reconciliation_permanently_removes_versions_and_delete_markers(
        tmp_path: Path) -> None:
    store = ImmutableGenerationStore(
        tmp_path / "cold",
        identity="version-aware-remote-test",
        required_files=("payload.bin",),
        content_addressed=True,
        max_encoded_generation_bytes=1024 * 1024,
    )
    client = VersionedMemoryS3()
    first = store.commit(
        tick=1, files={"payload.bin": b"unchanged-body"})
    second = store.commit(
        tick=2, files={"payload.bin": b"unchanged-body"})
    for generation in (first, second):
        upload_verified_generation(
            generation,
            s3_client=client,
            bucket="bucket",
            prefix="guala/generations",
            hmac_key=b"version-aware-test-hmac-key-32-bytes",
            nonce=b"version-aware-nonce",
        )

    content_key = next(
        key
        for bucket, key in client.versions
        if bucket == "bucket" and "/content-chunks/" in key
    )
    content_body = client.get_object(
        Bucket="bucket", Key=content_key)["Body"].read()
    client.put_object(
        Bucket="bucket", Key=content_key, Body=content_body)
    retired_manifest = (
        f"guala/generations/{first.generation_uuid}/MANIFEST.json")
    retired_body = client.get_object(
        Bucket="bucket", Key=retired_manifest)["Body"].read()
    client.put_object(
        Bucket="bucket", Key=retired_manifest, Body=retired_body)
    orphan_key = "guala/generations/content-chunks/aa/" + "a" * 64
    client.put_object(Bucket="bucket", Key=orphan_key, Body=b"orphan-one")
    client.put_object(Bucket="bucket", Key=orphan_key, Body=b"orphan-two")
    client.delete_objects(
        Bucket="bucket",
        Delete={"Objects": [{"Key": orphan_key}]},
    )

    reconcile_remote_generation_prefixes(
        s3_client=client,
        bucket="bucket",
        prefix="guala/generations",
        retained_generation_uuids=(second.generation_uuid,),
        maximum_objects_per_generation=2,
    )

    assert retired_manifest not in {
        key for _bucket, key in client.versions
    }
    assert orphan_key not in {
        key for _bucket, key in client.versions
    }
    assert len(client.versions[("bucket", content_key)]) == 1
    for records in client.versions.values():
        assert len(records) == 1
        assert not records[0]["DeleteMarker"]
