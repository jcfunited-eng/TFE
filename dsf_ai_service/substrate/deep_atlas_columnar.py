"""Exact columnar persistence for DeepAtlas association fields.

This module changes representation only.  It preserves every entry, section
reference, unsigned 64-bit motif identifier, and IEEE-754 binary64 weight.
No association is ranked, averaged, thresholded, or discarded here.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
import tempfile
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np


SCHEMA = "deep_atlas_v3"
CONTAINER_SCHEMA = "guala.deep_atlas.columnar.v1"

_ARCHIVE_FIELDS = frozenset({
    "metadata",
    "entries",
    "table_offsets",
    "motifs",
    "weights",
    "entry_offsets",
    "entry_sections",
    "entry_tables",
})
_NPY_ARCHIVE_NAMES = frozenset(f"{name}.npy" for name in _ARCHIVE_FIELDS)
_RAW_CHUNK_BYTES = 3 * 1024 * 1024
_ENCODED_CHUNK_BYTES = (_RAW_CHUNK_BYTES // 3) * 4
_DEFAULT_MAX_ENCODED_BYTES = 512 * 1024 * 1024
_DEFAULT_MAX_DECODED_BYTES = 1024 * 1024 * 1024


class DeepAtlasColumnarError(ValueError):
    """The exact columnar persistence contract was violated."""


def _positive_capacity(name: str, fallback: int) -> int:
    raw = os.environ.get(name, str(fallback))
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise DeepAtlasColumnarError(
            f"{name} must be a positive integer") from error
    if value <= 0:
        raise DeepAtlasColumnarError(
            f"{name} must be a positive integer")
    return value


def _encoded_capacity() -> int:
    return _positive_capacity(
        "GUALA_MAX_DEEP_ATLAS_COLUMNAR_BYTES",
        _DEFAULT_MAX_ENCODED_BYTES,
    )


def _decoded_capacity() -> int:
    return _positive_capacity(
        "GUALA_MAX_DEEP_ATLAS_DECODED_BYTES",
        _DEFAULT_MAX_DECODED_BYTES,
    )


def _canonical_json(value) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise DeepAtlasColumnarError(
            "deep-atlas columnar metadata is not canonical JSON") from error


def section_fingerprint(values: Mapping) -> str:
    """Content-address one exact motif-weight mapping."""
    plain = {str(key): float(weight) for key, weight in values.items()}
    return hashlib.sha256(_canonical_json(plain)).hexdigest()


def mappings_equal(left: Mapping, right: Mapping) -> bool:
    if left is right:
        return True
    if len(left) != len(right):
        return False
    sentinel = object()
    for key, value in left.items():
        other = right.get(key, sentinel)
        if other is sentinel or other != value:
            return False
    return True


@dataclass(frozen=True)
class ColumnarTableStore:
    """Immutable shared table arrays retained by live FrozenSection views."""

    references: tuple[str, ...]
    offsets: np.ndarray
    motifs: np.ndarray
    weights: np.ndarray

    def section(self, table_index: int) -> "FrozenSection":
        return FrozenSection(self, table_index)


class FrozenSection(Mapping):
    """Read-only dictionary-compatible view over one exact array slice."""

    __slots__ = ("_store", "_table_index")

    def __init__(self, store: ColumnarTableStore, table_index: int):
        if (
            isinstance(table_index, bool)
            or not isinstance(table_index, int)
            or table_index < 0
            or table_index >= len(store.references)
        ):
            raise DeepAtlasColumnarError(
                "deep-atlas table index is outside the store")
        self._store = store
        self._table_index = table_index

    @property
    def reference(self) -> str:
        return self._store.references[self._table_index]

    def _bounds(self) -> tuple[int, int]:
        start = int(self._store.offsets[self._table_index])
        stop = int(self._store.offsets[self._table_index + 1])
        return start, stop

    def __len__(self) -> int:
        start, stop = self._bounds()
        return stop - start

    def __iter__(self):
        start, stop = self._bounds()
        for motif in self._store.motifs[start:stop]:
            yield str(int(motif))

    def __getitem__(self, key):
        try:
            wanted = int(key)
        except (TypeError, ValueError) as error:
            raise KeyError(key) from error
        if wanted < 0 or wanted > np.iinfo(np.uint64).max:
            raise KeyError(key)
        start, stop = self._bounds()
        motifs = self._store.motifs
        weights = self._store.weights
        for offset in range(start, stop):
            if int(motifs[offset]) == wanted:
                return float(weights[offset])
        raise KeyError(key)

    def __contains__(self, key) -> bool:
        try:
            self[key]
        except KeyError:
            return False
        return True

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def items(self):
        start, stop = self._bounds()
        motifs = self._store.motifs
        weights = self._store.weights
        for offset in range(start, stop):
            yield str(int(motifs[offset])), float(weights[offset])

    def keys(self):
        return iter(self)

    def values(self):
        start, stop = self._bounds()
        for weight in self._store.weights[start:stop]:
            yield float(weight)

    def plain(self) -> dict[str, float]:
        return dict(self.items())


@dataclass(frozen=True)
class DecodedColumnar:
    metadata: dict
    entries: dict
    sections: tuple[str, ...]
    store: ColumnarTableStore
    entry_offsets: np.ndarray
    entry_sections: np.ndarray
    entry_tables: np.ndarray


def _exact_nonnegative_int(value, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise DeepAtlasColumnarError(
            f"{label} must be a non-negative integer")
    return value


def _validate_reference(reference: object) -> str:
    if (
        not isinstance(reference, str)
        or len(reference) != 64
        or any(character not in "0123456789abcdef"
               for character in reference)
    ):
        raise DeepAtlasColumnarError(
            "deep-atlas table reference is not a SHA-256 digest")
    return reference


def _validate_top_level(data: dict) -> tuple[list[str], str, int]:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise DeepAtlasColumnarError(
            f"deep-atlas schema must be {SCHEMA}")
    for field in (
        "tick",
        "saved_n_entries",
        "promotions_survival",
        "promotions_episodic",
        "reinstatements",
    ):
        _exact_nonnegative_int(data.get(field), f"deep_atlas.{field}")
    chunks = data.get("columnar_payload_chunks")
    if (
        not isinstance(chunks, list)
        or not chunks
        or any(
            not isinstance(chunk, str)
            or not chunk
            or len(chunk) > _ENCODED_CHUNK_BYTES
            for chunk in chunks
        )
    ):
        raise DeepAtlasColumnarError(
            "deep-atlas columnar chunks are invalid")
    encoded_size = sum(len(chunk) for chunk in chunks)
    maximum_encoded = ((_encoded_capacity() + 2) // 3) * 4
    if encoded_size > maximum_encoded:
        raise DeepAtlasColumnarError(
            "deep-atlas columnar payload exceeds its encoded capacity")
    digest = _validate_reference(data.get("columnar_sha256"))
    declared_bytes = _exact_nonnegative_int(
        data.get("columnar_bytes"), "deep_atlas.columnar_bytes")
    if declared_bytes > _encoded_capacity():
        raise DeepAtlasColumnarError(
            "deep-atlas columnar payload exceeds its byte capacity")
    return chunks, digest, declared_bytes


def _finite_number(value, label: str, *, minimum=None) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise DeepAtlasColumnarError(
            f"{label} must be a finite number")
    number = float(value)
    if minimum is not None and number < minimum:
        raise DeepAtlasColumnarError(
            f"{label} is below its structural range")
    return number


def _validate_entry_metadata(
    entry: dict,
    *,
    chi: int,
    tick: int,
    label: str,
) -> None:
    required = (
        "section",
        "motif",
        "chi",
        "strength",
        "last_tick",
        "born_tick",
        "encoded_strength_at_write",
        "dwell_at_write",
        "source_path",
        "promoted_at_tick",
        "clarity",
        "initial_clarity",
        "arousal",
        "valence",
        "surprise",
        "source",
        "polarity",
        "sensory_refs",
        "episode_refs",
    )
    missing = [field for field in required if field not in entry]
    if missing:
        raise DeepAtlasColumnarError(
            f"{label} is missing {missing}")
    if not isinstance(entry["section"], str):
        raise DeepAtlasColumnarError(
            f"{label}.section must be a string")
    motif = _exact_nonnegative_int(
        entry["motif"], f"{label}.motif")
    if motif > np.iinfo(np.uint64).max:
        raise DeepAtlasColumnarError(
            f"{label}.motif exceeds its unsigned 64-bit field")
    if (
        isinstance(entry["chi"], bool)
        or not isinstance(entry["chi"], int)
        or entry["chi"] != chi
    ):
        raise DeepAtlasColumnarError(
            f"{label}.chi does not match its bucket")
    _finite_number(
        entry["strength"], f"{label}.strength", minimum=0.0)
    for field in ("last_tick", "born_tick", "promoted_at_tick"):
        value = _exact_nonnegative_int(
            entry[field], f"{label}.{field}")
        if value > tick:
            raise DeepAtlasColumnarError(
                f"{label}.{field} exceeds the atlas tick")
    _exact_nonnegative_int(
        entry["dwell_at_write"], f"{label}.dwell_at_write")
    for field in (
        "encoded_strength_at_write",
        "clarity",
        "initial_clarity",
        "arousal",
        "valence",
        "surprise",
        "polarity",
    ):
        _finite_number(entry[field], f"{label}.{field}")
    for field in ("source_path", "source"):
        if not isinstance(entry[field], str):
            raise DeepAtlasColumnarError(
                f"{label}.{field} must be a string")
    for field in ("sensory_refs", "episode_refs"):
        if (
            not isinstance(entry[field], list)
            or any(not isinstance(item, str) for item in entry[field])
        ):
            raise DeepAtlasColumnarError(
                f"{label}.{field} must be a string list")


def _decode_chunks(
    chunks: list[str],
    expected_digest: str,
    expected_bytes: int,
    output,
) -> None:
    digest = hashlib.sha256()
    decoded_size = 0
    for chunk in chunks:
        try:
            decoded = base64.b64decode(
                chunk.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error) as error:
            raise DeepAtlasColumnarError(
                "deep-atlas columnar chunk is not canonical base64") from error
        decoded_size += len(decoded)
        if decoded_size > _encoded_capacity():
            raise DeepAtlasColumnarError(
                "deep-atlas columnar payload exceeds its byte capacity")
        digest.update(decoded)
        output.write(decoded)
    if decoded_size != expected_bytes:
        raise DeepAtlasColumnarError(
            "deep-atlas columnar byte count does not match")
    if digest.hexdigest() != expected_digest:
        raise DeepAtlasColumnarError(
            "deep-atlas columnar digest does not match")
    output.flush()
    output.seek(0)


def _archive_arrays(payload) -> dict[str, np.ndarray]:
    try:
        payload.seek(0)
        with zipfile.ZipFile(payload, "r") as archive:
            infos = archive.infolist()
            names = {info.filename for info in infos}
            if names != _NPY_ARCHIVE_NAMES or len(infos) != len(names):
                raise DeepAtlasColumnarError(
                    "deep-atlas columnar archive members are invalid")
            total_decoded = 0
            for info in infos:
                if (
                    info.is_dir()
                    or info.file_size < 0
                    or info.compress_size < 0
                    or info.compress_type not in {
                        zipfile.ZIP_STORED,
                        zipfile.ZIP_DEFLATED,
                    }
                ):
                    raise DeepAtlasColumnarError(
                        "deep-atlas columnar archive metadata is invalid")
                total_decoded += info.file_size
                if total_decoded > _decoded_capacity():
                    raise DeepAtlasColumnarError(
                        "deep-atlas decoded arrays exceed their capacity")
    except (OSError, zipfile.BadZipFile) as error:
        raise DeepAtlasColumnarError(
            "deep-atlas columnar archive is unreadable") from error

    try:
        payload.seek(0)
        with np.load(payload, allow_pickle=False) as archive:
            if set(archive.files) != _ARCHIVE_FIELDS:
                raise DeepAtlasColumnarError(
                    "deep-atlas columnar array set is invalid")
            return {name: archive[name] for name in archive.files}
    except DeepAtlasColumnarError:
        raise
    except Exception as error:
        raise DeepAtlasColumnarError(
            "deep-atlas columnar arrays are unreadable") from error


def _one_dimensional(
    arrays: dict[str, np.ndarray],
    name: str,
    dtype,
) -> np.ndarray:
    array = arrays[name]
    if array.ndim != 1 or array.dtype != np.dtype(dtype):
        raise DeepAtlasColumnarError(
            f"deep-atlas columnar array {name} has an invalid shape or dtype")
    return array


def _decode_json_array(array: np.ndarray, label: str):
    if array.ndim != 1 or array.dtype != np.dtype(np.uint8):
        raise DeepAtlasColumnarError(
            f"deep-atlas {label} bytes have an invalid shape or dtype")
    try:
        return json.loads(array.tobytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DeepAtlasColumnarError(
            f"deep-atlas {label} is not valid JSON") from error


def _validate_offsets(
    offsets: np.ndarray,
    expected_last: int,
    expected_length: int,
    label: str,
) -> None:
    if len(offsets) != expected_length:
        raise DeepAtlasColumnarError(
            f"deep-atlas {label} offset count does not match")
    if not len(offsets) or int(offsets[0]) != 0:
        raise DeepAtlasColumnarError(
            f"deep-atlas {label} offsets must start at zero")
    if int(offsets[-1]) != expected_last:
        raise DeepAtlasColumnarError(
            f"deep-atlas {label} offsets do not cover their values")
    if len(offsets) > 1 and np.any(offsets[1:] < offsets[:-1]):
        raise DeepAtlasColumnarError(
            f"deep-atlas {label} offsets are not monotonic")


def _decode_payload(data: dict, *, verify_fingerprints: bool) -> DecodedColumnar:
    chunks, digest, declared_bytes = _validate_top_level(data)
    with tempfile.TemporaryFile(mode="w+b") as payload:
        _decode_chunks(
            chunks,
            digest,
            declared_bytes,
            payload,
        )
        arrays = _archive_arrays(payload)

    metadata = _decode_json_array(arrays["metadata"], "metadata")
    entries = _decode_json_array(arrays["entries"], "entries")
    if (
        not isinstance(metadata, dict)
        or metadata.get("container_schema") != CONTAINER_SCHEMA
        or not isinstance(entries, dict)
    ):
        raise DeepAtlasColumnarError(
            "deep-atlas columnar logical metadata is invalid")
    raw_sections = metadata.get("sections")
    raw_references = metadata.get("table_references")
    if (
        not isinstance(raw_sections, list)
        or any(not isinstance(section, str) or not section
               for section in raw_sections)
        or len(set(raw_sections)) != len(raw_sections)
        or not isinstance(raw_references, list)
        or len(set(raw_references)) != len(raw_references)
    ):
        raise DeepAtlasColumnarError(
            "deep-atlas columnar dictionaries are invalid")
    sections = tuple(raw_sections)
    references = tuple(_validate_reference(ref) for ref in raw_references)

    table_offsets = _one_dimensional(
        arrays, "table_offsets", np.uint64)
    motifs = _one_dimensional(arrays, "motifs", np.uint64)
    weights = _one_dimensional(arrays, "weights", np.float64)
    entry_offsets = _one_dimensional(
        arrays, "entry_offsets", np.uint64)
    entry_sections = _one_dimensional(
        arrays, "entry_sections", np.uint16)
    entry_tables = _one_dimensional(
        arrays, "entry_tables", np.uint32)

    if len(motifs) != len(weights):
        raise DeepAtlasColumnarError(
            "deep-atlas motif and weight counts differ")
    if np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
        raise DeepAtlasColumnarError(
            "deep-atlas weights must be finite and non-negative")
    _validate_offsets(
        table_offsets, len(weights), len(references) + 1, "table")
    atlas_tick = data["tick"]
    entry_count = 0
    if (
        any(
            not isinstance(chi, str)
            or not chi.lstrip("-").isdigit()
            or not isinstance(bucket, list)
            or any(not isinstance(entry, dict) for entry in bucket)
            for chi, bucket in entries.items()
        )
    ):
        raise DeepAtlasColumnarError(
            "deep-atlas columnar entries are invalid")
    for chi_text, bucket in entries.items():
        chi = int(chi_text)
        for index, entry in enumerate(bucket):
            _validate_entry_metadata(
                entry,
                chi=chi,
                tick=atlas_tick,
                label=f"deep_atlas.entries[{chi_text}][{index}]",
            )
            entry_count += 1
    if data["saved_n_entries"] > entry_count:
        raise DeepAtlasColumnarError(
            "deep-atlas saved entry count exceeds its entries")
    if len(entry_sections) != len(entry_tables):
        raise DeepAtlasColumnarError(
            "deep-atlas entry-reference arrays differ")
    _validate_offsets(
        entry_offsets, len(entry_tables), entry_count + 1, "entry")
    if (
        len(entry_sections)
        and (
            int(entry_sections.max()) >= len(sections)
            or int(entry_tables.max()) >= len(references)
        )
    ):
        raise DeepAtlasColumnarError(
            "deep-atlas entry reference is outside its dictionary")

    store = ColumnarTableStore(
        references=references,
        offsets=table_offsets,
        motifs=motifs,
        weights=weights,
    )
    if verify_fingerprints:
        for table_index, reference in enumerate(references):
            if section_fingerprint(store.section(table_index)) != reference:
                raise DeepAtlasColumnarError(
                    "deep-atlas table fingerprint does not match")
    return DecodedColumnar(
        metadata=metadata,
        entries=entries,
        sections=sections,
        store=store,
        entry_offsets=entry_offsets,
        entry_sections=entry_sections,
        entry_tables=entry_tables,
    )


def validate_columnar_v3(data: dict) -> None:
    """Validate the bounded container before the live atlas is mutated."""
    _decode_payload(data, verify_fingerprints=False)


def decode_columnar_v3(data: dict) -> DecodedColumnar:
    """Decode one container already protected by its whole-payload digest.

    The writer verifies each newly-owned table when it receives its content
    address.  A restored FrozenSection carries that address immutably, and the
    v3 envelope verifies every archive byte with one SHA-256 digest before any
    array is admitted.  Re-serializing all 20M weights merely to recompute the
    same 123,790 hashes would add minutes to every boot without detecting a
    corruption the container digest did not already reject.
    """
    return _decode_payload(data, verify_fingerprints=False)


def _table_arrays(tables: Mapping) -> ColumnarTableStore:
    references = tuple(str(reference) for reference in tables)
    for reference in references:
        _validate_reference(reference)
    if references:
        first = tables[references[0]]
        if isinstance(first, FrozenSection):
            shared_store = first._store
            if (
                references == shared_store.references
                and all(
                    isinstance(tables[reference], FrozenSection)
                    and tables[reference]._store is shared_store
                    and tables[reference]._table_index == table_index
                    for table_index, reference in enumerate(references)
                )
            ):
                return shared_store
    counts = [len(tables[reference]) for reference in references]
    total = sum(counts)
    offsets = np.empty(len(references) + 1, dtype=np.uint64)
    motifs = np.empty(total, dtype=np.uint64)
    weights = np.empty(total, dtype=np.float64)
    cursor = 0
    for table_index, reference in enumerate(references):
        offsets[table_index] = cursor
        values = tables[reference]
        if isinstance(values, FrozenSection):
            if values.reference != reference:
                raise DeepAtlasColumnarError(
                    "deep-atlas frozen table address does not match")
            start, stop = values._bounds()
            length = stop - start
            motifs[cursor:cursor + length] = (
                values._store.motifs[start:stop])
            weights[cursor:cursor + length] = (
                values._store.weights[start:stop])
            cursor += length
            continue
        if section_fingerprint(values) != reference:
            raise DeepAtlasColumnarError(
                "deep-atlas table content address does not match")
        for motif, weight in values.items():
            try:
                motif_value = int(motif)
            except (TypeError, ValueError) as error:
                raise DeepAtlasColumnarError(
                    "deep-atlas motif is not an integer") from error
            if motif_value < 0 or motif_value > np.iinfo(np.uint64).max:
                raise DeepAtlasColumnarError(
                    "deep-atlas motif exceeds its unsigned 64-bit field")
            if (
                isinstance(weight, bool)
                or not isinstance(weight, (int, float))
                or not math.isfinite(float(weight))
                or float(weight) < 0.0
            ):
                raise DeepAtlasColumnarError(
                    "deep-atlas weight is not finite and non-negative")
            motifs[cursor] = motif_value
            weights[cursor] = float(weight)
            cursor += 1
    offsets[-1] = cursor
    return ColumnarTableStore(
        references=references,
        offsets=offsets,
        motifs=motifs,
        weights=weights,
    )


def compact_v2_tables(raw_tables: dict) -> dict[str, FrozenSection]:
    """Freeze validated v2 tables into their exact live columnar form."""
    if not isinstance(raw_tables, dict):
        raise DeepAtlasColumnarError(
            "deep-atlas v2 tables must be an object")
    store = _table_arrays(raw_tables)
    return {
        reference: store.section(table_index)
        for table_index, reference in enumerate(store.references)
    }


def _encoded_archive(arrays: dict[str, np.ndarray]) -> tuple[int, str, list[str]]:
    chunks = []
    digest = hashlib.sha256()
    payload_size = 0
    with tempfile.TemporaryFile(mode="w+b") as payload:
        with zipfile.ZipFile(
            payload,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=True,
            compresslevel=1,
        ) as archive:
            for name in sorted(arrays):
                info = zipfile.ZipInfo(
                    filename=f"{name}.npy",
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info._compresslevel = 1
                info.external_attr = 0o600 << 16
                with archive.open(
                    info,
                    mode="w",
                    force_zip64=True,
                ) as member:
                    np.lib.format.write_array(
                        member,
                        arrays[name],
                        allow_pickle=False,
                    )
        payload_size = payload.tell()
        if payload_size > _encoded_capacity():
            raise DeepAtlasColumnarError(
                "deep-atlas columnar payload exceeds its byte capacity")
        payload.seek(0)
        while True:
            raw = payload.read(_RAW_CHUNK_BYTES)
            if not raw:
                break
            digest.update(raw)
            chunks.append(base64.b64encode(raw).decode("ascii"))
    return payload_size, digest.hexdigest(), chunks


def encode_columnar_v3(snapshot: dict) -> dict:
    """Encode one immutable v2-shaped snapshot without semantic reduction."""
    if not isinstance(snapshot, dict):
        raise DeepAtlasColumnarError(
            "deep-atlas persistence snapshot must be an object")
    entries = snapshot.get("entries")
    tables = snapshot.get("co_occurrence_tables")
    if not isinstance(entries, dict) or not isinstance(tables, Mapping):
        raise DeepAtlasColumnarError(
            "deep-atlas persistence snapshot is incomplete")
    store = _table_arrays(tables)
    reference_index = {
        reference: index
        for index, reference in enumerate(store.references)
    }

    sections = []
    section_index = {}
    entry_count = 0
    entry_reference_count = 0
    entries_without_refs = {}
    for chi, bucket in entries.items():
        if (
            not isinstance(chi, str)
            or not chi.lstrip("-").isdigit()
            or not isinstance(bucket, list)
        ):
            raise DeepAtlasColumnarError(
                "deep-atlas persistence entries are invalid")
        compact_bucket = []
        for entry in bucket:
            if not isinstance(entry, dict):
                raise DeepAtlasColumnarError(
                    "deep-atlas persistence entry is invalid")
            references = entry.get("co_occurrence_refs")
            if not isinstance(references, dict):
                raise DeepAtlasColumnarError(
                    "deep-atlas entry references are invalid")
            for section, reference in references.items():
                if not isinstance(section, str) or not section:
                    raise DeepAtlasColumnarError(
                        "deep-atlas entry section is invalid")
                if reference not in reference_index:
                    raise DeepAtlasColumnarError(
                        "deep-atlas entry references an absent table")
                if section not in section_index:
                    section_index[section] = len(sections)
                    sections.append(section)
            entry_reference_count += len(references)
            compact_bucket.append({
                key: value
                for key, value in entry.items()
                if key != "co_occurrence_refs"
            })
            entry_count += 1
        entries_without_refs[chi] = compact_bucket

    entry_offsets = np.empty(entry_count + 1, dtype=np.uint64)
    entry_sections = np.empty(
        entry_reference_count, dtype=np.uint16)
    entry_tables = np.empty(
        entry_reference_count, dtype=np.uint32)
    if len(sections) > np.iinfo(np.uint16).max:
        raise DeepAtlasColumnarError(
            "deep-atlas section dictionary exceeds uint16 capacity")
    if len(store.references) > np.iinfo(np.uint32).max:
        raise DeepAtlasColumnarError(
            "deep-atlas table dictionary exceeds uint32 capacity")
    entry_cursor = 0
    reference_cursor = 0
    for bucket in entries.values():
        for entry in bucket:
            entry_offsets[entry_cursor] = reference_cursor
            for section, reference in entry[
                    "co_occurrence_refs"].items():
                entry_sections[reference_cursor] = (
                    section_index[section])
                entry_tables[reference_cursor] = (
                    reference_index[reference])
                reference_cursor += 1
            entry_cursor += 1
    entry_offsets[-1] = reference_cursor

    metadata = {
        "container_schema": CONTAINER_SCHEMA,
        "sections": sections,
        "table_references": list(store.references),
    }
    payload_size, payload_digest, chunks = _encoded_archive({
        "metadata": np.frombuffer(
            _canonical_json(metadata), dtype=np.uint8),
        "entries": np.frombuffer(
            _canonical_json(entries_without_refs), dtype=np.uint8),
        "table_offsets": store.offsets,
        "motifs": store.motifs,
        "weights": store.weights,
        "entry_offsets": entry_offsets,
        "entry_sections": entry_sections,
        "entry_tables": entry_tables,
    })
    common = {
        key: value
        for key, value in snapshot.items()
        if key not in {"entries", "co_occurrence_tables", "schema"}
    }
    common.update({
        "schema": SCHEMA,
        "columnar_bytes": payload_size,
        "columnar_sha256": payload_digest,
        "columnar_payload_chunks": chunks,
    })
    return common


__all__ = [
    "CONTAINER_SCHEMA",
    "DecodedColumnar",
    "DeepAtlasColumnarError",
    "FrozenSection",
    "SCHEMA",
    "compact_v2_tables",
    "decode_columnar_v3",
    "encode_columnar_v3",
    "mappings_equal",
    "section_fingerprint",
    "validate_columnar_v3",
]
