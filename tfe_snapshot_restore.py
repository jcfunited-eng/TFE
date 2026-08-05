"""
tfe_snapshot_restore.py

Downloads the latest UF snapshot from S3 on container startup so
it survives deploys. Run before starting Next.js.
"""
from __future__ import annotations

import os
import sys

S3_SNAPSHOT_BUCKET = "tfe-codebuild-src-418384447921-us-east-1"
S3_SNAPSHOT_PREFIX = "runtime-refresh-checkpoints"

DOWNLOADS = [
    (f"{S3_SNAPSHOT_PREFIX}/uf_snapshot.json", "/app/uf_snapshot.json"),
    (f"{S3_SNAPSHOT_PREFIX}/uf_snapshot.ses.json", "/app/uf_snapshot.ses.json"),
    (f"{S3_SNAPSHOT_PREFIX}/uf_snapshot_rebuild_report.json", "/app/uf_snapshot_rebuild_report.json"),
]


def restore() -> bool:
    try:
        import boto3  # type: ignore[import]
    except ImportError:
        print("[RESTORE] boto3 not available — skipping S3 restore.")
        return False

    s3 = boto3.client("s3")
    any_downloaded = False

    for s3_key, local_path in DOWNLOADS:
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            s3.download_file(S3_SNAPSHOT_BUCKET, s3_key, local_path)
            stat = os.stat(local_path)
            print(f"[RESTORE] {s3_key} → {local_path} ({stat.st_size:,} bytes)")
            any_downloaded = True
        except Exception as exc:
            print(f"[RESTORE] Skipped {s3_key}: {exc}")

    if any_downloaded:
        print("[RESTORE] Snapshot restored from S3. Screener will be available immediately.")
    else:
        print("[RESTORE] No snapshot found in S3. Screener will be unavailable until the first admin refresh completes.")

    return any_downloaded


if __name__ == "__main__":
    ok = restore()
    sys.exit(0 if ok else 1)
