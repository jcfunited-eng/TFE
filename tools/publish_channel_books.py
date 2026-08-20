#!/usr/bin/env python3
"""Publish exact CH3/CH4/CH6 book bytes to the private TFE snapshot store."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_S3_URI = (
    "s3://tfe-codebuild-src-418384447921-us-east-1/"
    "runtime-refresh-checkpoints/channel-books"
)


@dataclass(frozen=True)
class ChannelSource:
    channel: str
    path: Path
    object_name: str | None = None  # defaults to <channel>.json


SOURCES = {
    "ch3": ChannelSource(
        channel="CH3",
        path=ROOT / "artifacts" / "vtvr_observer" / "ch3_shadow_log.json",
    ),
    "ch4": ChannelSource(
        channel="CH4",
        path=ROOT / "artifacts" / "vtvr_observer" / "ch4_spring_book.json",
    ),
    "ch6-perception": ChannelSource(
        channel="CH6",
        path=ROOT / "artifacts" / "ch6_harvest" / "ch6_perception.json",
        object_name="ch6-perception.json",
    ),
    "ch6": ChannelSource(
        channel="CH6",
        path=ROOT / "artifacts" / "vtvr_observer" / "ch6_book.json",
    ),
}


def utc_iso(timestamp: float | None = None) -> str:
    moment = datetime.now(timezone.utc) if timestamp is None else datetime.fromtimestamp(timestamp, timezone.utc)
    return moment.isoformat().replace("+00:00", "Z")


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError("TFE_CHANNEL_BOOK_S3_URI must be an s3://bucket/prefix URI")
    return parsed.netloc, parsed.path.strip("/")


def build_envelope(source: ChannelSource) -> tuple[bytes, str]:
    raw = source.path.read_bytes()
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{source.path} must contain one JSON object")

    digest = hashlib.sha256(raw).hexdigest()
    stat = source.path.stat()
    envelope = {
        "schema": "tfe.channel-book.snapshot.v1",
        "channel": source.channel,
        "source_name": source.path.name,
        "source_sha256": digest,
        "source_updated_at": utc_iso(stat.st_mtime),
        "published_at": utc_iso(),
        "source_bytes_base64": base64.b64encode(raw).decode("ascii"),
    }
    body = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return body, digest


def object_key(prefix: str, source: ChannelSource) -> str:
    filename = source.object_name or f"{source.channel.lower()}.json"
    return f"{prefix}/{filename}" if prefix else filename


def publish(channels: Iterable[str], dry_run: bool) -> int:
    uri = os.environ.get("TFE_CHANNEL_BOOK_S3_URI", DEFAULT_S3_URI).strip()
    bucket, prefix = parse_s3_uri(uri)
    s3 = None
    if not dry_run:
        import boto3  # type: ignore

        s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))

    published = 0
    for channel_key in channels:
        source = SOURCES[channel_key]
        optional = source.object_name is not None
        if not source.path.is_file():
            if optional:  # optional companion snapshot
                print(f"SKIP {channel_key}: {source.path.name} not present yet")
                continue
            raise FileNotFoundError(f"authoritative {source.channel} book is missing: {source.path}")

        try:
            body, digest = build_envelope(source)
        except Exception as exc:  # noqa: BLE001 — an optional companion
            # must NEVER block a required book behind it in the loop
            if optional:
                print(f"SKIP {channel_key}: unreadable ({type(exc).__name__}: {exc})")
                continue
            raise
        key = object_key(prefix, source)
        if dry_run:
            print(f"DRY {source.channel} sha256={digest} bytes={len(body)} s3://{bucket}/{key}")
            continue

        assert s3 is not None
        unchanged = False
        try:
            head = s3.head_object(Bucket=bucket, Key=key)
            unchanged = head.get("Metadata", {}).get("source-sha256") == digest
        except s3.exceptions.ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status != 404:
                raise

        if unchanged:
            print(f"UNCHANGED {source.channel} sha256={digest}")
            continue

        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
            CacheControl="no-store",
            Metadata={
                "schema": "tfe-channel-book-snapshot-v1",
                "channel": source.channel,
                "source-sha256": digest,
            },
        )
        published += 1
        print(f"PUBLISHED {source.channel} sha256={digest} s3://{bucket}/{key}")
    return published


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("channels", nargs="*", metavar="{ch3,ch4,ch6}")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    channels = args.channels if args.channels else sorted(SOURCES)
    invalid = sorted(set(channels) - set(SOURCES))
    if invalid:
        parser.error(f"unknown channel(s): {', '.join(invalid)}")
    publish(channels, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
