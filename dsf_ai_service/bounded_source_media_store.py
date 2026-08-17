"""Bounded immutable source media for Guala's sensory experiences.

This is a transport provenance boundary, not cognition.  It preserves the
exact bytes that a local person offered or that a named public source
returned, and it refuses growth beyond fixed count and byte ceilings.  Media
labels, locators, and receipts never enter neuronal settlement.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path


SOURCE_MEDIA_SCHEMA = "guala.bounded_source_media.v1"
SOURCE_MEDIA_KINDS = frozenset(
    {"audio", "book", "gutenberg_text", "pdf", "picture", "song", "video"}
)
SOURCE_ORIGIN_KINDS = frozenset({"local_offer", "project_gutenberg"})
MAX_SOURCE_MEDIA_BYTES = 24 * 1024 * 1024
MAX_SOURCE_MEDIA_COUNT = 32
MAX_SOURCE_MEDIA_TOTAL_BYTES = 256 * 1024 * 1024
MAX_ORIGIN_LOCATOR_BYTES = 2_048

_RECEIPT = re.compile(r"[0-9a-f]{64}")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@dataclass(frozen=True, slots=True)
class SourceMediaRecord:
    material_kind: str
    origin_kind: str
    origin_locator: str
    source_bytes_sha256: str
    source_byte_count: int
    receipt_sha256: str

    def receipt_payload(self) -> dict[str, object]:
        return {
            "material_kind": self.material_kind,
            "origin_kind": self.origin_kind,
            "origin_locator": self.origin_locator,
            "schema": SOURCE_MEDIA_SCHEMA,
            "source_byte_count": self.source_byte_count,
            "source_bytes_sha256": self.source_bytes_sha256,
        }

    def public_projection(self) -> dict[str, object]:
        return {
            **self.receipt_payload(),
            "cognition_authority": False,
            "receipt_sha256": self.receipt_sha256,
            "retained_source_bytes": self.source_byte_count,
            "semantic_authority": False,
        }


class BoundedSourceMediaStoreError(RuntimeError):
    """The immutable source-media boundary refused or failed validation."""


class BoundedSourceMediaStore:
    """A fixed-capacity set of immutable, content-verified media records."""

    def __init__(
        self,
        root: Path,
        *,
        max_source_bytes: int = MAX_SOURCE_MEDIA_BYTES,
        max_source_count: int = MAX_SOURCE_MEDIA_COUNT,
        max_total_bytes: int = MAX_SOURCE_MEDIA_TOTAL_BYTES,
    ) -> None:
        if min(max_source_bytes, max_source_count, max_total_bytes) <= 0:
            raise ValueError("source-media bounds must be positive")
        if max_source_bytes > max_total_bytes:
            raise ValueError("one source cannot exceed the total media boundary")
        self.root = root
        self.entries = root / "entries"
        self.stage = root / ".stage"
        self.max_source_bytes = max_source_bytes
        self.max_source_count = max_source_count
        self.max_total_bytes = max_total_bytes
        self._lock = threading.Lock()

    def _decode_entry(self, directory: Path) -> SourceMediaRecord:
        if not directory.is_dir() or not _RECEIPT.fullmatch(directory.name):
            raise BoundedSourceMediaStoreError("source-media entry identity changed")
        children = {item.name for item in directory.iterdir()}
        if children != {"record.json", "source.bin"}:
            raise BoundedSourceMediaStoreError("source-media entry shape changed")
        source_path = directory / "source.bin"
        size = source_path.stat().st_size
        if not 0 < size <= self.max_source_bytes:
            raise BoundedSourceMediaStoreError("source-media entry exceeds its bound")
        source = source_path.read_bytes()
        if len(source) != size:
            raise BoundedSourceMediaStoreError("source-media byte extent changed")
        try:
            value = json.loads((directory / "record.json").read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BoundedSourceMediaStoreError(
                "source-media record cannot be decoded"
            ) from error
        expected = {
            "material_kind",
            "origin_kind",
            "origin_locator",
            "receipt_sha256",
            "schema",
            "source_byte_count",
            "source_bytes_sha256",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise BoundedSourceMediaStoreError("source-media record shape changed")
        if value.get("schema") != SOURCE_MEDIA_SCHEMA:
            raise BoundedSourceMediaStoreError("source-media schema changed")
        record = SourceMediaRecord(
            material_kind=value.get("material_kind"),
            origin_kind=value.get("origin_kind"),
            origin_locator=value.get("origin_locator"),
            source_bytes_sha256=value.get("source_bytes_sha256"),
            source_byte_count=value.get("source_byte_count"),
            receipt_sha256=value.get("receipt_sha256"),
        )
        if (
            not isinstance(record.material_kind, str)
            or record.material_kind not in SOURCE_MEDIA_KINDS
        ):
            raise BoundedSourceMediaStoreError("source-media kind changed")
        if (
            not isinstance(record.origin_kind, str)
            or record.origin_kind not in SOURCE_ORIGIN_KINDS
        ):
            raise BoundedSourceMediaStoreError("source-media origin changed")
        if (
            not isinstance(record.origin_locator, str)
            or not record.origin_locator
            or record.origin_locator != record.origin_locator.strip()
            or len(record.origin_locator.encode("utf-8")) > MAX_ORIGIN_LOCATOR_BYTES
        ):
            raise BoundedSourceMediaStoreError("source-media locator changed")
        digest = hashlib.sha256(source).hexdigest()
        if (
            isinstance(record.source_byte_count, bool)
            or not isinstance(record.source_byte_count, int)
            or record.source_byte_count != size
            or not isinstance(record.source_bytes_sha256, str)
            or not isinstance(record.receipt_sha256, str)
            or record.source_bytes_sha256 != digest
            or record.receipt_sha256 != directory.name
            or hashlib.sha256(_canonical(record.receipt_payload())).hexdigest()
            != record.receipt_sha256
        ):
            raise BoundedSourceMediaStoreError("source-media receipt mismatch")
        return record

    def inventory(self) -> tuple[SourceMediaRecord, ...]:
        if self.stage.exists():
            raise BoundedSourceMediaStoreError(
                "an interrupted source-media admission requires recovery"
            )
        if not self.root.exists():
            return ()
        if not self.entries.is_dir():
            raise BoundedSourceMediaStoreError("source-media entries are absent")
        unexpected = {
            item.name for item in self.root.iterdir() if item.name != "entries"
        }
        if unexpected:
            raise BoundedSourceMediaStoreError("source-media root shape changed")
        records = tuple(
            self._decode_entry(path)
            for path in sorted(self.entries.iterdir(), key=lambda item: item.name)
        )
        if len(records) > self.max_source_count:
            raise BoundedSourceMediaStoreError("source-media count exceeds its bound")
        if sum(item.source_byte_count for item in records) > self.max_total_bytes:
            raise BoundedSourceMediaStoreError("source-media bytes exceed their bound")
        return records

    def admit(
        self,
        *,
        material_kind: str,
        origin_kind: str,
        origin_locator: str,
        source_bytes: bytes,
    ) -> SourceMediaRecord:
        if material_kind not in SOURCE_MEDIA_KINDS:
            raise ValueError("source-media kind is not admitted")
        if origin_kind not in SOURCE_ORIGIN_KINDS:
            raise ValueError("source-media origin is not admitted")
        if (
            not isinstance(origin_locator, str)
            or not origin_locator
            or origin_locator != origin_locator.strip()
            or len(origin_locator.encode("utf-8")) > MAX_ORIGIN_LOCATOR_BYTES
        ):
            raise ValueError("source-media locator changed")
        if (
            not isinstance(source_bytes, bytes)
            or not source_bytes
            or len(source_bytes) > self.max_source_bytes
        ):
            raise ValueError("source-media bytes exceed their bound")
        source_digest = hashlib.sha256(source_bytes).hexdigest()
        payload = {
            "material_kind": material_kind,
            "origin_kind": origin_kind,
            "origin_locator": origin_locator,
            "schema": SOURCE_MEDIA_SCHEMA,
            "source_byte_count": len(source_bytes),
            "source_bytes_sha256": source_digest,
        }
        receipt = hashlib.sha256(_canonical(payload)).hexdigest()
        record = SourceMediaRecord(
            material_kind=material_kind,
            origin_kind=origin_kind,
            origin_locator=origin_locator,
            source_bytes_sha256=source_digest,
            source_byte_count=len(source_bytes),
            receipt_sha256=receipt,
        )
        encoded_record = _canonical({**payload, "receipt_sha256": receipt})
        with self._lock:
            current = self.inventory()
            prior = next(
                (item for item in current if item.receipt_sha256 == receipt),
                None,
            )
            if prior is not None:
                return prior
            if len(current) >= self.max_source_count:
                raise BoundedSourceMediaStoreError(
                    "source-media count boundary reached"
                )
            if (
                sum(item.source_byte_count for item in current) + len(source_bytes)
                > self.max_total_bytes
            ):
                raise BoundedSourceMediaStoreError(
                    "source-media byte boundary reached"
                )
            self.entries.mkdir(parents=True, exist_ok=True)
            self.stage.mkdir()
            try:
                with (self.stage / "source.bin").open("xb") as stream:
                    stream.write(source_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
                with (self.stage / "record.json").open("xb") as stream:
                    stream.write(encoded_record)
                    stream.flush()
                    os.fsync(stream.fileno())
                _fsync_directory(self.stage)
                os.replace(self.stage, self.entries / receipt)
                _fsync_directory(self.entries)
                _fsync_directory(self.root)
            except BaseException:
                if self.stage.exists():
                    shutil.rmtree(self.stage)
                raise
            return self._decode_entry(self.entries / receipt)

    def source_bytes(self, receipt_sha256: str) -> bytes:
        if not isinstance(receipt_sha256, str) or not _RECEIPT.fullmatch(
            receipt_sha256
        ):
            raise ValueError("source-media receipt changed")
        with self._lock:
            records = self.inventory()
            if not any(item.receipt_sha256 == receipt_sha256 for item in records):
                raise KeyError(receipt_sha256)
            path = self.entries / receipt_sha256 / "source.bin"
            source = path.read_bytes()
            if hashlib.sha256(source).hexdigest() != next(
                item.source_bytes_sha256
                for item in records
                if item.receipt_sha256 == receipt_sha256
            ):
                raise BoundedSourceMediaStoreError("source-media bytes changed")
            return source
