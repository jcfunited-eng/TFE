import json
import os
import uuid
from pathlib import Path

import pytest

from dsf_ai_service.substrate.immutable_generation_store import (
    CURRENT_NAME,
    GENERATIONS_DIRECTORY,
    GenerationCapacityError,
    GenerationValidationError,
    ImmutableGenerationStore,
    MANIFEST_NAME,
)


IDENTITY = "capacity-test-identity"
GENERATION_UUID = "11111111-2222-4333-8444-555555555555"
REQUIRED_FILES = ("brain.json", "organism.bin")


def _sources(root: Path) -> dict[str, object]:
    organism = root / "organism-source.bin"
    organism.write_bytes(bytes(range(64)))
    return {
        "brain.json": b'{"field":{"B_k":0.7,"C_k":0.5,"D_k":0.1,'
                      b'"M_k":0.2,"P_k":0.6,"R_rev":0.3,'
                      b'"S_UF":0.8,"U_star":0.4}}',
        "organism.bin": organism,
    }


def _encoded_generation_bytes(directory: Path) -> int:
    return sum(
        path.stat().st_size
        for path in directory.rglob("*")
        if path.is_file()
    )


def _store(
    root: Path,
    *,
    capacity: int | None,
) -> ImmutableGenerationStore:
    return ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=REQUIRED_FILES,
        max_encoded_generation_bytes=capacity,
    )


def test_exact_encoded_capacity_includes_envelopes_and_manifest(
    tmp_path: Path,
) -> None:
    sources = _sources(tmp_path)
    reference = _store(tmp_path / "reference", capacity=None)
    committed = reference.commit(
        tick=17,
        files=sources,
        generation_uuid=GENERATION_UUID,
    )
    exact = _encoded_generation_bytes(committed.directory)
    assert exact > sum(
        len(value) if isinstance(value, bytes) else Path(value).stat().st_size
        for value in sources.values()
    )
    assert (committed.directory / MANIFEST_NAME).stat().st_size > 0

    admitted = _store(tmp_path / "admitted", capacity=exact)
    admitted_generation = admitted.commit(
        tick=17,
        files=sources,
        generation_uuid=GENERATION_UUID,
    )
    assert _encoded_generation_bytes(admitted_generation.directory) == exact
    assert admitted.load_current().generation_uuid == GENERATION_UUID

    rejected_root = tmp_path / "rejected"
    rejected = _store(rejected_root, capacity=exact - 1)
    with pytest.raises(
        GenerationCapacityError,
        match="encoded-byte capacity",
    ):
        rejected.commit(
            tick=17,
            files=sources,
            generation_uuid=GENERATION_UUID,
        )
    assert not (rejected_root / CURRENT_NAME).exists()
    assert list((rejected_root / GENERATIONS_DIRECTORY).iterdir()) == []


def test_manifest_itself_cannot_cross_capacity(
    tmp_path: Path,
) -> None:
    sources = _sources(tmp_path)
    reference = _store(tmp_path / "reference", capacity=None)
    committed = reference.commit(
        tick=18,
        files=sources,
        generation_uuid=GENERATION_UUID,
    )
    payload_bytes = sum(
        (committed.directory / relative).stat().st_size
        for relative in REQUIRED_FILES
    )
    assert payload_bytes < _encoded_generation_bytes(committed.directory)

    rejected_root = tmp_path / "manifest-rejected"
    rejected = _store(rejected_root, capacity=payload_bytes)
    with pytest.raises(
        GenerationCapacityError,
        match=MANIFEST_NAME,
    ):
        rejected.commit(
            tick=18,
            files=sources,
            generation_uuid=GENERATION_UUID,
        )
    assert not (rejected_root / CURRENT_NAME).exists()
    assert list((rejected_root / GENERATIONS_DIRECTORY).iterdir()) == []


def test_rejected_successor_preserves_prior_current_and_tree(
    tmp_path: Path,
) -> None:
    sources = _sources(tmp_path)
    root = tmp_path / "store"
    initial = _store(root, capacity=None)
    current = initial.commit(
        tick=20,
        files=sources,
        generation_uuid=GENERATION_UUID,
    )
    exact = _encoded_generation_bytes(current.directory)
    current_bytes = (root / CURRENT_NAME).read_bytes()
    tree_before = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
    )

    large_source = tmp_path / "large-successor.bin"
    large_source.write_bytes(b"z" * exact)
    bounded = _store(root, capacity=exact)
    with pytest.raises(
        GenerationCapacityError,
        match="encoded-byte capacity",
    ):
        bounded.commit(
            tick=21,
            files={**sources, "organism.bin": large_source},
            generation_uuid="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        )
    assert (root / CURRENT_NAME).read_bytes() == current_bytes
    assert sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
    ) == tree_before
    assert bounded.load_current().generation_uuid == GENERATION_UUID


def test_publish_cannot_bypass_encoded_capacity(
    tmp_path: Path,
) -> None:
    sources = _sources(tmp_path)
    root = tmp_path / "store"
    uncapped = _store(root, capacity=None)
    oversized = uncapped.commit(
        tick=22,
        files=sources,
        generation_uuid=GENERATION_UUID,
        publish_current=False,
    )
    exact = _encoded_generation_bytes(oversized.directory)

    bounded = _store(root, capacity=exact - 1)
    with pytest.raises(
        GenerationCapacityError,
        match="published generation exceeds encoded-byte capacity",
    ):
        bounded.publish(oversized)
    assert not (root / CURRENT_NAME).exists()
    assert bounded.verify_generation(GENERATION_UUID).generation_uuid == (
        GENERATION_UUID
    )


def test_rejected_oversized_publish_preserves_prior_current(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    small_source = tmp_path / "small.bin"
    small_source.write_bytes(b"x")
    small_files = {
        "brain.json": b'{"field":{"B_k":0.7,"C_k":0.5,"D_k":0.1,'
                      b'"M_k":0.2,"P_k":0.6,"R_rev":0.3,'
                      b'"S_UF":0.8,"U_star":0.4}}',
        "organism.bin": small_source,
    }
    uncapped = _store(root, capacity=None)
    prior = uncapped.commit(
        tick=23,
        files=small_files,
        generation_uuid=GENERATION_UUID,
    )
    prior_size = _encoded_generation_bytes(prior.directory)
    current_bytes = (root / CURRENT_NAME).read_bytes()

    large_source = tmp_path / "large.bin"
    large_source.write_bytes(b"y" * prior_size)
    oversized = uncapped.commit(
        tick=24,
        files={**small_files, "organism.bin": large_source},
        generation_uuid="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        publish_current=False,
    )
    assert _encoded_generation_bytes(oversized.directory) > prior_size

    bounded = _store(root, capacity=prior_size)
    with pytest.raises(
        GenerationCapacityError,
        match="published generation exceeds encoded-byte capacity",
    ):
        bounded.publish(oversized)
    assert (root / CURRENT_NAME).read_bytes() == current_bytes
    assert bounded.load_current().generation_uuid == GENERATION_UUID


def test_full_field_json_round_trips_without_reduction(
    tmp_path: Path,
) -> None:
    fields = {
        "D_k": 0.1,
        "M_k": 0.2,
        "R_rev": 0.3,
        "U_star": 0.4,
        "C_k": 0.5,
        "P_k": 0.6,
        "B_k": 0.7,
        "S_UF": 0.8,
    }
    source = tmp_path / "organism.bin"
    source.write_bytes(b"organism")
    store = _store(tmp_path / "store", capacity=64 * 1024)
    committed = store.commit(
        tick=25,
        files={
            "brain.json": (
                ("{\"field\":" + json.dumps(fields) + "}")
                .encode("utf-8")
            ),
            "organism.bin": source,
        },
        generation_uuid=GENERATION_UUID,
    )
    assert committed.payload("brain.json")["field"] == fields


@pytest.mark.parametrize("capacity", [True, False, 0, -1, 1.5, "1024"])
def test_capacity_configuration_must_be_a_positive_integer(
    tmp_path: Path,
    capacity: object,
) -> None:
    with pytest.raises(
        GenerationValidationError,
        match="capacity must be a positive integer",
    ):
        ImmutableGenerationStore(
            tmp_path / str(uuid.uuid4()),
            identity=IDENTITY,
            required_files=REQUIRED_FILES,
            max_encoded_generation_bytes=capacity,
        )


def test_binary_growth_beyond_remaining_capacity_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = _sources(tmp_path)
    reference = _store(tmp_path / "reference", capacity=None)
    committed = reference.commit(
        tick=19,
        files=sources,
        generation_uuid=GENERATION_UUID,
    )
    exact = _encoded_generation_bytes(committed.directory)

    source = Path(sources["organism.bin"])
    original_stat = Path.stat
    first = True

    def stale_size(path: Path, *args, **kwargs):
        nonlocal first
        result = original_stat(path, *args, **kwargs)
        if path == source and first:
            first = False
            source.write_bytes(source.read_bytes() + os.urandom(exact))
        return result

    monkeypatch.setattr(Path, "stat", stale_size)
    rejected_root = tmp_path / "growing-source"
    rejected = _store(rejected_root, capacity=exact)
    with pytest.raises(
        GenerationCapacityError,
        match="remaining encoded-byte capacity",
    ):
        rejected.commit(
            tick=19,
            files=sources,
            generation_uuid=GENERATION_UUID,
        )
    assert not (rejected_root / CURRENT_NAME).exists()
    assert list((rejected_root / GENERATIONS_DIRECTORY).iterdir()) == []


def test_oversized_json_path_is_rejected_before_reading_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    json_source = tmp_path / "oversized.json"
    json_source.write_bytes(
        b'{"field":"' + (b"x" * 4096) + b'"}'
    )
    binary_source = tmp_path / "organism.bin"
    binary_source.write_bytes(b"organism")
    root = tmp_path / "store"
    store = _store(root, capacity=1024)
    original_read_bytes = Path.read_bytes
    oversized_source_was_read = False

    def track_read(path: Path):
        nonlocal oversized_source_was_read
        if path == json_source:
            oversized_source_was_read = True
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", track_read)
    with pytest.raises(
        GenerationCapacityError,
        match="remaining encoded-byte capacity",
    ):
        store.commit(
            tick=26,
            files={
                "brain.json": json_source,
                "organism.bin": binary_source,
            },
            generation_uuid=GENERATION_UUID,
        )
    assert oversized_source_was_read is False
    assert not (root / CURRENT_NAME).exists()
    assert list((root / GENERATIONS_DIRECTORY).iterdir()) == []


def test_json_source_growth_after_fstat_is_bounded_and_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    json_source = tmp_path / "growing.json"
    json_source.write_bytes(b'{"field":"small"}')
    binary_source = tmp_path / "organism.bin"
    binary_source.write_bytes(b"organism")
    root = tmp_path / "store"
    store = _store(root, capacity=1024)
    original_fstat = os.fstat
    source_realpath = str(json_source.resolve())
    grew = False

    def grow_after_initial_fstat(fd: int):
        nonlocal grew
        result = original_fstat(fd)
        try:
            fd_realpath = str(Path(f"/proc/self/fd/{fd}").resolve())
        except OSError:
            fd_realpath = ""
        if not grew and fd_realpath == source_realpath:
            grew = True
            with json_source.open("ab") as handle:
                handle.write(b"x" * 4096)
        return result

    monkeypatch.setattr(os, "fstat", grow_after_initial_fstat)
    with pytest.raises(
        GenerationCapacityError,
        match="grew beyond remaining encoded-byte capacity",
    ):
        store.commit(
            tick=27,
            files={
                "brain.json": json_source,
                "organism.bin": binary_source,
            },
            generation_uuid=GENERATION_UUID,
        )
    assert grew is True
    assert not (root / CURRENT_NAME).exists()
    assert list((root / GENERATIONS_DIRECTORY).iterdir()) == []


def test_generation_specific_contract_preserves_dynamic_learned_assets(
    tmp_path: Path,
) -> None:
    root = tmp_path / "dynamic-store"
    store = ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=None,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=128,
        max_dynamic_path_bytes=16 * 1024,
    )
    first = store.commit(
        tick=28,
        files={
            "brain.json": b'{"tick":28}',
            "assets/pictures/first.bin": b"first-picture",
        },
        generation_uuid=GENERATION_UUID,
    )
    second_uuid = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    second = store.commit(
        tick=29,
        files={
            "brain.json": b'{"tick":29}',
            "assets/pictures/second.bin": b"second-picture",
            "sounds/voice.audio": b"learned-voice",
        },
        generation_uuid=second_uuid,
    )
    assert first.required_files == (
        "assets/pictures/first.bin",
        "brain.json",
    )
    assert second.required_files == (
        "assets/pictures/second.bin",
        "brain.json",
        "sounds/voice.audio",
    )
    assert store.verify_generation(
        GENERATION_UUID
    ).stored_bytes("assets/pictures/first.bin") == b"first-picture"
    assert store.load_current().generation_uuid == second_uuid
    store.prune_generations(retain=2, verified_current=second)
    assert {
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    } == {GENERATION_UUID, second_uuid}


@pytest.mark.parametrize(
    ("files", "file_limit", "path_limit", "message"),
    [
        (
            {
                "a.bin": b"",
                "b.bin": b"",
                "c.bin": b"",
            },
            2,
            1024,
            "required-file count capacity",
        ),
        (
            {
                "long/path/alpha.bin": b"",
                "long/path/beta.bin": b"",
            },
            10,
            16,
            "required-path byte capacity",
        ),
    ],
)
def test_dynamic_contract_metadata_is_bounded_before_tree_creation(
    tmp_path: Path,
    files: dict[str, bytes],
    file_limit: int,
    path_limit: int,
    message: str,
) -> None:
    root = tmp_path / str(file_limit)
    store = ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=None,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=file_limit,
        max_dynamic_path_bytes=path_limit,
    )
    with pytest.raises(GenerationCapacityError, match=message):
        store.commit(
            tick=30,
            files=files,
            generation_uuid=GENERATION_UUID,
        )
    assert not (root / CURRENT_NAME).exists()
    assert list((root / GENERATIONS_DIRECTORY).iterdir()) == []


@pytest.mark.parametrize(
    ("file_limit", "path_limit"),
    [
        (None, 1024),
        (10, None),
        (0, 1024),
        (10, 0),
        (True, 1024),
        (10, False),
    ],
)
def test_dynamic_contract_requires_explicit_metadata_capacities(
    tmp_path: Path,
    file_limit: object,
    path_limit: object,
) -> None:
    with pytest.raises(
        GenerationValidationError,
        match="capacity must be a positive integer",
    ):
        ImmutableGenerationStore(
            tmp_path / f"{file_limit}-{path_limit}",
            identity=IDENTITY,
            required_files=None,
            max_encoded_generation_bytes=64 * 1024,
            max_dynamic_required_files=file_limit,
            max_dynamic_path_bytes=path_limit,
        )
