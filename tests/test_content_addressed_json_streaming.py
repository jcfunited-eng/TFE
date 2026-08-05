from __future__ import annotations

import json
from pathlib import Path
import sys
import tracemalloc


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate import immutable_generation_store as module
from dsf_ai_service.substrate.immutable_generation_store import (
    MANIFEST_NAME,
    ImmutableGenerationStore,
)


def test_large_json_file_is_validated_and_chunked_with_bounded_memory(
        tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "guala_deep_atlas.json"
    block = "x" * (1024 * 1024)
    with source.open("w", encoding="utf-8") as handle:
        handle.write('{"columnar_payload_chunks":[')
        for index in range(64):
            if index:
                handle.write(",")
            json.dump(block, handle)
        handle.write('],"schema":"deep_atlas_v3"}')

    def forbid_full_file_read(*_args, **_kwargs):
        raise AssertionError("large JSON crossed the full-object reader")

    monkeypatch.setattr(module, "_read_regular_file", forbid_full_file_read)
    store = ImmutableGenerationStore(
        tmp_path / "cold",
        identity="streaming-json-test",
        required_files=("guala_deep_atlas.json",),
        content_addressed=True,
        max_encoded_generation_bytes=80 * 1024 * 1024,
    )
    tracemalloc.start()
    first = store.commit(
        tick=1,
        files={"guala_deep_atlas.json": source},
    )
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak < 32 * 1024 * 1024
    first_bytes = sum(
        path.stat().st_size
        for path in store.root.rglob("*")
        if path.is_file()
    )
    second = store.commit(
        tick=2,
        files={"guala_deep_atlas.json": source},
    )
    second_bytes = sum(
        path.stat().st_size
        for path in store.root.rglob("*")
        if path.is_file()
    )
    assert second_bytes - first_bytes == (
        second.directory / MANIFEST_NAME
    ).stat().st_size
    assert first.payload("guala_deep_atlas.json")["schema"] == "deep_atlas_v3"
