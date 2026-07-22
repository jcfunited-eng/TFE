import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate import immutable_generation_store as store_module
from dsf_ai_service.substrate.immutable_generation_store import (
    CERTIFICATE_SCHEMA,
    CURRENT_NAME,
    CurrentPointerError,
    GenerationValidationError,
    ImmutableGenerationStore,
    MANIFEST_NAME,
)


IDENTITY = "ae-test-identity"
REQUIRED = ("core.json", "nested/atlas.json", "organism.bin")


def _store(tmp_path, *, identity=IDENTITY):
    return ImmutableGenerationStore(
        tmp_path / "store",
        identity=identity,
        required_files=REQUIRED,
    )


def _files(tmp_path, *, marker="first"):
    binary_path = tmp_path / f"{marker}.bin"
    binary_path.write_bytes((marker.encode("utf-8") + b"\x00") * 9)
    return {
        "core.json": json.dumps({"marker": marker, "count": 3}).encode(),
        "nested/atlas.json": json.dumps(
            {"entries": [{"chi": -7}, {"chi": 12}]},
            separators=(",", ":"),
        ).encode(),
        "organism.bin": binary_path,
    }


def _make_writable(path):
    os.chmod(path, path.stat().st_mode | 0o200)


def _rewrite_json(path, value):
    _make_writable(path)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(path, 0o444)


def test_commit_wraps_json_hashes_binary_and_loads_current(tmp_path):
    store = _store(tmp_path)
    source_files = _files(tmp_path)

    loaded = store.commit(tick=41, files=source_files)
    current = store.load_current()

    assert current.generation_uuid == loaded.generation_uuid
    assert current.identity == IDENTITY
    assert current.tick == 41
    assert current.payload("core.json") == {"marker": "first", "count": 3}
    assert current.payload("nested/atlas.json") == {
        "entries": [{"chi": -7}, {"chi": 12}],
    }
    assert current.payload("organism.bin") == Path(
        source_files["organism.bin"]).read_bytes()

    generation = current.directory
    assert generation.name == current.generation_uuid
    assert not generation.stat().st_mode & 0o222
    assert not (generation / MANIFEST_NAME).stat().st_mode & 0o222
    assert not (store.root / CURRENT_NAME).stat().st_mode & 0o222

    envelope = json.loads((generation / "core.json").read_text())
    assert envelope == {
        "schema": "immutable_generation_envelope_v1",
        "generation_uuid": current.generation_uuid,
        "identity": IDENTITY,
        "tick": 41,
        "relative_path": "core.json",
        "payload": {"marker": "first", "count": 3},
    }

    manifest = json.loads((generation / MANIFEST_NAME).read_text())
    assert manifest["generation_uuid"] == current.generation_uuid
    assert manifest["identity"] == IDENTITY
    assert manifest["tick"] == 41
    assert [record["relative_path"] for record in manifest["required_files"]] == list(
        sorted(REQUIRED))
    assert all(
        record["generation_uuid"] == current.generation_uuid
        and record["identity"] == IDENTITY
        and record["tick"] == 41
        for record in manifest["required_files"]
    )


def test_commit_requires_the_exact_declared_file_mapping(tmp_path):
    store = _store(tmp_path)
    files = _files(tmp_path)

    missing = dict(files)
    missing.pop("organism.bin")
    with pytest.raises(GenerationValidationError, match="missing=.*organism.bin"):
        store.commit(tick=1, files=missing)

    extra = dict(files)
    extra["extra.json"] = b"{}"
    with pytest.raises(GenerationValidationError, match="extra=.*extra.json"):
        store.commit(tick=1, files=extra)

    assert not (store.root / CURRENT_NAME).exists()


@pytest.mark.parametrize("bad_path", [
    "/absolute.json",
    "../escape.json",
    "nested/../escape.json",
    "nested\\windows.json",
    MANIFEST_NAME,
])
def test_required_paths_reject_noncanonical_or_reserved_names(tmp_path, bad_path):
    with pytest.raises(GenerationValidationError):
        ImmutableGenerationStore(
            tmp_path / "store",
            identity=IDENTITY,
            required_files=(bad_path,),
        )


def test_binary_and_json_sources_accept_caller_paths(tmp_path):
    json_path = tmp_path / "input.json"
    json_path.write_text('{"z":2,"a":1}')
    binary_path = tmp_path / "input.bin"
    binary_path.write_bytes(b"binary-source")
    store = ImmutableGenerationStore(
        tmp_path / "store",
        identity=IDENTITY,
        required_files=("state.json", "state.bin"),
    )

    loaded = store.commit(
        tick=5,
        files={"state.json": str(json_path), "state.bin": binary_path},
    )

    assert loaded.payload("state.json") == {"a": 1, "z": 2}
    assert loaded.payload("state.bin") == b"binary-source"


def test_required_file_corruption_is_rejected_by_hash(tmp_path):
    store = _store(tmp_path)
    loaded = store.commit(tick=10, files=_files(tmp_path))
    target = loaded.directory / "organism.bin"
    _make_writable(target)
    target.write_bytes(b"corrupt")
    os.chmod(target, 0o444)

    with pytest.raises(CurrentPointerError, match="hash or size mismatch"):
        store.load_current()


def test_missing_and_extra_generation_files_are_rejected(tmp_path):
    missing_store = _store(tmp_path / "missing")
    missing_generation = missing_store.commit(
        tick=10, files=_files(tmp_path / "missing")).directory
    nested = missing_generation / "nested"
    os.chmod(nested, 0o755)
    (nested / "atlas.json").unlink()
    os.chmod(nested, 0o555)
    with pytest.raises(CurrentPointerError, match="required-file set mismatch"):
        missing_store.load_current()

    extra_store = _store(tmp_path / "extra")
    extra_generation = extra_store.commit(
        tick=11, files=_files(tmp_path / "extra")).directory
    os.chmod(extra_generation, 0o755)
    extra = extra_generation / "unexpected.bin"
    extra.write_bytes(b"unexpected")
    os.chmod(extra, 0o444)
    os.chmod(extra_generation, 0o555)
    with pytest.raises(CurrentPointerError, match="required-file set mismatch"):
        extra_store.load_current()


def test_extra_directory_and_symlink_are_rejected(tmp_path):
    directory_store = _store(tmp_path / "directory")
    directory_generation = directory_store.commit(
        tick=12, files=_files(tmp_path / "directory")).directory
    os.chmod(directory_generation, 0o755)
    empty = directory_generation / "unexpected"
    empty.mkdir()
    os.chmod(empty, 0o555)
    os.chmod(directory_generation, 0o555)
    with pytest.raises(CurrentPointerError, match="directory set mismatch"):
        directory_store.load_current()

    symlink_store = _store(tmp_path / "symlink")
    symlink_generation = symlink_store.commit(
        tick=13, files=_files(tmp_path / "symlink")).directory
    os.chmod(symlink_generation, 0o755)
    (symlink_generation / "linked").symlink_to("organism.bin")
    os.chmod(symlink_generation, 0o555)
    with pytest.raises(CurrentPointerError, match="not a regular file"):
        symlink_store.load_current()


def test_external_hard_link_breaks_the_immutability_certificate(tmp_path):
    store = _store(tmp_path)
    generation = store.commit(tick=14, files=_files(tmp_path)).directory
    os.link(generation / "organism.bin", tmp_path / "external-hard-link.bin")

    with pytest.raises(CurrentPointerError, match="hard-link count must be one"):
        store.load_current()


def test_manifest_metadata_and_manifest_record_tampering_are_rejected(tmp_path):
    metadata_store = _store(tmp_path / "metadata")
    metadata_generation = metadata_store.commit(
        tick=21, files=_files(tmp_path / "metadata")).directory
    manifest_path = metadata_generation / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text())
    manifest["identity"] = "another-entity"
    _rewrite_json(manifest_path, manifest)
    with pytest.raises(CurrentPointerError, match="manifest identity mismatch"):
        metadata_store.load_current()

    record_store = _store(tmp_path / "record")
    record_generation = record_store.commit(
        tick=22, files=_files(tmp_path / "record")).directory
    record_manifest_path = record_generation / MANIFEST_NAME
    record_manifest = json.loads(record_manifest_path.read_text())
    record_manifest["required_files"][0]["tick"] = 999
    _rewrite_json(record_manifest_path, record_manifest)
    with pytest.raises(CurrentPointerError, match="metadata mismatch"):
        record_store.load_current()


def test_corrupt_torn_and_mismatched_current_are_rejected(tmp_path):
    missing = _store(tmp_path / "missing")
    with pytest.raises(CurrentPointerError, match="missing"):
        missing.load_current()

    corrupt = _store(tmp_path / "corrupt")
    corrupt.commit(tick=30, files=_files(tmp_path / "corrupt"))
    current_path = corrupt.root / CURRENT_NAME
    _make_writable(current_path)
    current_path.write_bytes(b'{"generation_uuid":')
    os.chmod(current_path, 0o444)
    with pytest.raises(CurrentPointerError, match="strict UTF-8 JSON"):
        corrupt.load_current()

    mismatch = _store(tmp_path / "mismatch")
    mismatch.commit(tick=31, files=_files(tmp_path / "mismatch"))
    mismatch_path = mismatch.root / CURRENT_NAME
    pointer = json.loads(mismatch_path.read_text())
    pointer["manifest_sha256"] = "0" * 64
    _rewrite_json(mismatch_path, pointer)
    with pytest.raises(CurrentPointerError, match="manifest hash mismatch"):
        mismatch.load_current()


def test_identity_mismatch_is_rejected_without_loading_payloads(tmp_path):
    writer = _store(tmp_path)
    writer.commit(tick=40, files=_files(tmp_path))
    reader = _store(tmp_path, identity="different-ae")

    with pytest.raises(CurrentPointerError, match="identity mismatch"):
        reader.load_current()


def test_current_update_keeps_old_generation_immutable_and_selects_new(tmp_path):
    store = _store(tmp_path)
    first = store.commit(tick=50, files=_files(tmp_path, marker="first"))
    first_pointer = (store.root / CURRENT_NAME).read_bytes()
    second = store.commit(tick=51, files=_files(tmp_path, marker="second"))

    assert first.generation_uuid != second.generation_uuid
    assert store.load_current().generation_uuid == second.generation_uuid
    assert store.load_current().payload("core.json")["marker"] == "second"
    assert store.verify_generation(first.generation_uuid).payload("core.json")[
        "marker"] == "first"
    assert first.directory.exists()
    assert second.directory.exists()
    assert (store.root / CURRENT_NAME).read_bytes() != first_pointer
    assert not list(store.root.glob(".CURRENT.*.tmp"))
    assert not list(store.generations_directory.glob(".building-*"))


def test_retention_preserves_current_and_two_newest_predecessors(tmp_path):
    store = _store(tmp_path)
    committed = [
        store.commit(tick=tick, files=_files(tmp_path, marker=str(tick)))
        for tick in range(70, 75)
    ]

    removed = store.prune_generations(
        retain=3,
        verified_current=committed[-1],
    )

    assert set(removed) == {
        committed[0].generation_uuid,
        committed[1].generation_uuid,
    }
    assert store.load_current().generation_uuid == committed[-1].generation_uuid
    assert {
        path.name for path in store.generations_directory.iterdir()
    } == {
        committed[2].generation_uuid,
        committed[3].generation_uuid,
        committed[4].generation_uuid,
    }


def test_retention_refuses_to_run_without_a_recovery_predecessor(tmp_path):
    store = _store(tmp_path)
    store.commit(tick=80, files=_files(tmp_path))

    with pytest.raises(
        GenerationValidationError,
        match="CURRENT and a predecessor",
    ):
        store.prune_generations(retain=1)


def test_current_replace_failure_preserves_prior_pointer_and_removes_temp(
        tmp_path, monkeypatch):
    store = _store(tmp_path)
    first = store.commit(tick=55, files=_files(tmp_path, marker="first"))
    prior_pointer = (store.root / CURRENT_NAME).read_bytes()
    real_replace = store_module.os.replace

    def fail_current_replace(source, destination):
        if Path(destination) == store.root / CURRENT_NAME:
            raise OSError("injected CURRENT publication failure")
        return real_replace(source, destination)

    monkeypatch.setattr(store_module.os, "replace", fail_current_replace)
    with pytest.raises(OSError, match="publication failure"):
        store.commit(tick=56, files=_files(tmp_path, marker="second"))

    assert (store.root / CURRENT_NAME).read_bytes() == prior_pointer
    assert store.load_current().generation_uuid == first.generation_uuid
    assert not list(store.root.glob(".CURRENT.*.tmp"))
    complete_generations = [
        path for path in store.generations_directory.iterdir()
        if path.is_dir() and not path.name.startswith(".building-")
    ]
    assert len(complete_generations) == 2


def test_manifest_is_created_after_every_required_generation_file(
        tmp_path, monkeypatch):
    store = _store(tmp_path)
    write_order = []
    real_write = store_module._write_new_bytes
    real_copy = store_module._copy_new_file

    def record_write(path, data):
        write_order.append(Path(path))
        return real_write(path, data)

    def record_copy(source, destination):
        write_order.append(Path(destination))
        return real_copy(source, destination)

    monkeypatch.setattr(store_module, "_write_new_bytes", record_write)
    monkeypatch.setattr(store_module, "_copy_new_file", record_copy)
    loaded = store.commit(tick=57, files=_files(tmp_path))

    generation_writes = [
        path.relative_to(loaded.directory).as_posix()
        for path in write_order
        if loaded.directory in path.parents
    ]
    # Paths were recorded under the pre-publication directory.  Match by
    # filename order instead of the renamed parent directory.
    if not generation_writes:
        generation_writes = [path.name for path in write_order[:-1]]
        assert generation_writes[-1] == MANIFEST_NAME
        assert set(generation_writes[:-1]) == {
            "core.json", "atlas.json", "organism.bin",
        }
    else:
        assert generation_writes[-1] == MANIFEST_NAME


def test_recovery_certificate_is_deterministic_and_manifest_bound(tmp_path):
    store = _store(tmp_path)
    committed = store.commit(tick=61, files=_files(tmp_path))
    loaded_once = store.load_current()
    loaded_twice = store.verify_generation(committed.generation_uuid)

    assert loaded_once.recovery_certificate_bytes() == (
        loaded_twice.recovery_certificate_bytes())
    assert loaded_once.recovery_certificate() == loaded_twice.recovery_certificate()
    certificate = loaded_once.recovery_certificate()
    assert certificate["schema"] == CERTIFICATE_SCHEMA
    assert certificate["status"] == "verified"
    assert certificate["generation_uuid"] == committed.generation_uuid
    assert certificate["identity"] == IDENTITY
    assert certificate["tick"] == 61
    manifest_bytes = (committed.directory / MANIFEST_NAME).read_bytes()
    assert certificate["manifest_sha256"] == hashlib.sha256(
        manifest_bytes).hexdigest()
    assert all(
        record["generation_uuid"] == committed.generation_uuid
        and record["identity"] == IDENTITY
        and record["tick"] == 61
        for record in certificate["required_files"]
    )


def test_json_payload_rejects_nonfinite_or_corrupt_input_before_current(tmp_path):
    store = ImmutableGenerationStore(
        tmp_path / "store",
        identity=IDENTITY,
        required_files=("state.json",),
    )
    with pytest.raises(GenerationValidationError, match="strict UTF-8 JSON"):
        store.commit(tick=1, files={"state.json": b'{"x":NaN}'})
    with pytest.raises(GenerationValidationError, match="strict UTF-8 JSON"):
        store.commit(tick=1, files={"state.json": b'{"x":'})
    assert not (store.root / CURRENT_NAME).exists()
