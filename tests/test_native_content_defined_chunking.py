from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from dsf_ai_service.substrate import immutable_generation_store as module
from dsf_ai_service.substrate.immutable_generation_store import (
    CONTENT_CHUNK_MAX_BYTES,
    CONTENT_CHUNK_MIN_BYTES,
    GenerationValidationError,
    ImmutableGenerationStore,
)


def _reference_chunks(blocks: list[bytes]) -> list[bytes]:
    pending = bytearray()
    gear = 0
    chunks: list[bytes] = []
    for block in blocks:
        for byte in block:
            pending.append(byte)
            gear = (
                ((gear << 1) + module._CONTENT_GEAR_TABLE[byte])
                & module.UINT64_MAX
            )
            length = len(pending)
            if length >= module.CONTENT_CHUNK_MIN_BYTES and (
                (gear & module._CONTENT_CHUNK_MASK) == 0
                or length >= module.CONTENT_CHUNK_MAX_BYTES
            ):
                chunks.append(bytes(pending))
                pending.clear()
                gear = 0
    if pending:
        chunks.append(bytes(pending))
    return chunks


def _deterministic_bytes(size: int) -> bytes:
    body = bytearray()
    counter = 0
    while len(body) < size:
        body.extend(hashlib.sha256(counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(body[:size])


@pytest.mark.skipif(
    module._NativeContentDefinedChunker is None,
    reason="native wheel is not built",
)
def test_native_stream_is_exact_for_every_source_block_partition() -> None:
    data = _deterministic_bytes(13 * 1024 * 1024 + 37)
    expected = _reference_chunks([data])
    for block_bytes in (4093, 64 * 1024, 1024 * 1024):
        chunker = module._NativeContentDefinedChunker()
        actual: list[bytes] = []
        for offset in range(0, len(data), block_bytes):
            actual.extend(
                bytes(value)
                for value in chunker.feed(data[offset:offset + block_bytes])
            )
        final = chunker.finish()
        if final is not None:
            actual.append(bytes(final))
        assert actual == expected
        assert [len(value) for value in actual] == [
            len(value) for value in expected
        ]

    bytewise = data[:4099]
    chunker = module._NativeContentDefinedChunker()
    for value in bytewise:
        assert chunker.feed(bytes((value,))) == []
    assert bytes(chunker.finish()) == bytewise


@pytest.mark.skipif(
    module._NativeContentDefinedChunker is None,
    reason="native wheel is not built",
)
def test_native_boundaries_and_capacity_are_fixed_and_bounded() -> None:
    chunker = module._NativeContentDefinedChunker()
    assert chunker.maximum_source_block_bytes == 1024 * 1024
    assert chunker.maximum_pending_bytes == CONTENT_CHUNK_MAX_BYTES
    assert chunker.finish() is None
    with pytest.raises(RuntimeError, match="already finished"):
        chunker.feed(b"x")

    chunker = module._NativeContentDefinedChunker()
    with pytest.raises(ValueError, match="source block exceeds"):
        chunker.feed(b"x" * (1024 * 1024 + 1))

    data = _deterministic_bytes(24 * 1024 * 1024 + 19)
    chunks: list[bytes] = []
    for offset in range(0, len(data), 1024 * 1024):
        chunks.extend(
            bytes(value)
            for value in chunker.feed(data[offset:offset + 1024 * 1024])
        )
        assert 0 <= chunker.pending_bytes < CONTENT_CHUNK_MAX_BYTES
    final = chunker.finish()
    if final is not None:
        chunks.append(bytes(final))
    assert b"".join(chunks) == data
    assert all(len(value) <= CONTENT_CHUNK_MAX_BYTES for value in chunks)
    assert all(
        len(value) >= CONTENT_CHUNK_MIN_BYTES
        for value in chunks[:-1]
    )


@pytest.mark.skipif(
    module._NativeContentDefinedChunker is None,
    reason="native wheel is not built",
)
def test_store_native_path_never_enters_the_python_byte_loop(
        monkeypatch: pytest.MonkeyPatch) -> None:
    data = _deterministic_bytes(3 * 1024 * 1024 + 7)
    expected = _reference_chunks([data])

    class ForbiddenPythonGearTable:
        def __getitem__(self, _index: int) -> int:
            raise AssertionError("Python gear-hash byte loop ran")

    monkeypatch.setattr(module, "_CONTENT_GEAR_TABLE", ForbiddenPythonGearTable())
    actual = list(ImmutableGenerationStore._iter_content_defined_chunks(
        data,
        "native no-Python-byte-loop proof",
        max_bytes=len(data),
    ))
    assert actual == expected


def test_unsealed_fallback_remains_exact(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = _deterministic_bytes(9 * 1024 * 1024 + 11)
    monkeypatch.setattr(module, "_NativeContentDefinedChunker", None)
    monkeypatch.setenv("GUALA_REQUIRE_SEALED_STATE", "0")
    monkeypatch.delenv(
        module.REQUIRE_NATIVE_CONTENT_CHUNKING_ENV, raising=False
    )
    actual = list(ImmutableGenerationStore._iter_content_defined_chunks(
        data,
        "fallback equivalence",
        max_bytes=len(data),
    ))
    assert actual == _reference_chunks([data])


def test_sealed_production_never_silently_uses_python_fallback(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "_NativeContentDefinedChunker", None)
    monkeypatch.setenv("GUALA_REQUIRE_SEALED_STATE", "1")
    monkeypatch.delenv(
        module.REQUIRE_NATIVE_CONTENT_CHUNKING_ENV, raising=False
    )
    with pytest.raises(
        GenerationValidationError,
        match="requires the native immutable-generation content chunker",
    ):
        list(ImmutableGenerationStore._iter_content_defined_chunks(
            b"{}",
            "sealed production source",
            max_bytes=2,
        ))

    monkeypatch.setenv(module.REQUIRE_NATIVE_CONTENT_CHUNKING_ENV, "0")
    with pytest.raises(
        GenerationValidationError,
        match="requires the native immutable-generation content chunker",
    ):
        list(ImmutableGenerationStore._iter_content_defined_chunks(
            b"{}",
            "sealed production cannot weaken native requirement",
            max_bytes=2,
        ))


def test_explicit_native_requirement_and_invalid_configuration_are_loud(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "_NativeContentDefinedChunker", None)
    monkeypatch.setenv("GUALA_REQUIRE_SEALED_STATE", "0")
    monkeypatch.setenv(module.REQUIRE_NATIVE_CONTENT_CHUNKING_ENV, "1")
    with pytest.raises(GenerationValidationError, match="requires the native"):
        list(ImmutableGenerationStore._iter_content_defined_chunks(
            b"{}", "explicit native source", max_bytes=2
        ))

    monkeypatch.setenv(module.REQUIRE_NATIVE_CONTENT_CHUNKING_ENV, "maybe")
    with pytest.raises(GenerationValidationError, match="must be 0 or 1"):
        list(ImmutableGenerationStore._iter_content_defined_chunks(
            b"{}", "invalid native setting", max_bytes=2
        ))
