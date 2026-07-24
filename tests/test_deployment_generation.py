import hashlib
import io
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate import deployment_generation as deployment
from dsf_ai_service.substrate.deployment_generation import (
    EFSOwnerLockUnavailable,
    MaterializationError,
    ProcessLifetimeEFSOwnerLock,
    RemoteGenerationVerificationError,
    SealValidationError,
    StageValidationError,
    discover_and_load_current,
    load_and_verify_deployment_seal,
    load_generation_deployment_seal,
    materialize_current,
    materialize_verified_generation,
    persist_deployment_seal,
    stage_authoritative_commit_upload,
    stage_commit_upload,
    upload_verified_generation,
    verify_deployment_seal,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    CURRENT_NAME,
    ImmutableGenerationStore,
    MANIFEST_NAME,
)
from dsf_ai_service.substrate.authoritative_cold_generation_store import (
    AuthoritativeColdGenerationError,
)


IDENTITY = "deployment-test-ae"
HMAC_KEY = b"deployment-test-key-material-32-bytes-minimum"
NONCE = b"unique-deploy-nonce-0001"


class FakeS3:
    def __init__(self, *, page_size=100, corrupt_every_read=False):
        self.objects = {}
        self.page_size = page_size
        self.extra_listing_keys = set()
        self.hidden_listing_keys = set()
        self.corrupt_get_keys = set()
        self.corrupt_every_read = corrupt_every_read

    def put_object(self, *, Bucket, Key, Body):
        self.objects[(Bucket, Key)] = bytes(Body)
        return {"ETag": hashlib.md5(bytes(Body)).hexdigest()}

    def list_objects_v2(self, *, Bucket, Prefix, ContinuationToken=None):
        keys = sorted(
            key for bucket, key in self.objects
            if bucket == Bucket and key.startswith(Prefix)
            and key not in self.hidden_listing_keys
        )
        keys.extend(sorted(key for key in self.extra_listing_keys if key.startswith(Prefix)))
        keys = sorted(set(keys))
        start = int(ContinuationToken or "0")
        page = keys[start:start + self.page_size]
        next_start = start + len(page)
        truncated = next_start < len(keys)
        response = {
            "Contents": [{"Key": key} for key in page],
            "IsTruncated": truncated,
        }
        if truncated:
            response["NextContinuationToken"] = str(next_start)
        return response

    def get_object(self, *, Bucket, Key):
        data = self.objects[(Bucket, Key)]
        if self.corrupt_every_read or Key in self.corrupt_get_keys:
            data = data + b"corrupt"
        return {"Body": io.BytesIO(data)}

    def delete_objects(self, *, Bucket, Delete):
        for record in Delete["Objects"]:
            self.objects.pop((Bucket, record["Key"]), None)
        return {"Deleted": list(Delete["Objects"])}


def _save_callback(stage, admission=None, *, marker="one"):
    nested = stage / "nested"
    nested.mkdir()
    core = json.dumps({"marker": marker, "tick": 7})
    atlas = json.dumps({"chis": [-2, 0, 9]})
    organism = b"\x00organism\xff" + marker.encode()
    if admission is None:
        (stage / "core.json").write_text(core)
        (nested / "atlas.json").write_text(atlas)
        (stage / "organism.bin").write_bytes(organism)
        return
    with admission.open_text(stage / "core.json") as handle:
        handle.write(core)
    with admission.open_text(nested / "atlas.json") as handle:
        handle.write(atlas)
    with admission.open_binary(stage / "organism.bin") as handle:
        handle.write(organism)


def _committed_generation(tmp_path, *, marker="one"):
    source = tmp_path / "source"
    source.mkdir(parents=True)
    _save_callback(source, marker=marker)
    required = ("core.json", "nested/atlas.json", "organism.bin")
    store = ImmutableGenerationStore(
        tmp_path / "store",
        identity=IDENTITY,
        required_files=required,
    )
    generation = store.commit(
        tick=77,
        files={relative: source / relative for relative in required},
    )
    return store, generation


def _rewrite_read_only_json(path, value):
    os.chmod(path, 0o644)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(path, 0o444)


def test_stage_commit_upload_reads_every_object_back_and_seals(tmp_path):
    fake = FakeS3(page_size=2)
    result = stage_commit_upload(
        store_root=tmp_path / "store",
        identity=IDENTITY,
        tick=88,
        save_callback=_save_callback,
        s3_client=fake,
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )

    generation = result.generation
    certificate = result.seal_certificate()
    verified = verify_deployment_seal(
        result.seal_certificate_bytes(),
        hmac_key=HMAC_KEY,
        expected_nonce=NONCE,
    )
    assert verified == certificate
    assert certificate["generation_uuid"] == generation.generation_uuid
    assert certificate["identity"] == IDENTITY
    assert certificate["tick"] == 88
    assert certificate["versioned_prefix"] == (
        f"ae/state/{generation.generation_uuid}")
    expected_relative = set(generation.required_files) | {MANIFEST_NAME}
    assert {
        record["key"].split(f"/{generation.generation_uuid}/", 1)[1]
        for record in certificate["objects"]
    } == expected_relative
    assert len(fake.objects) == len(expected_relative)
    assert not list((tmp_path / "store").glob(".deployment-stage-*"))

    with pytest.raises(SealValidationError, match="nonce mismatch"):
        verify_deployment_seal(
            certificate,
            hmac_key=HMAC_KEY,
            expected_nonce=b"different-nonce-value",
        )


def test_authoritative_stage_seals_dynamic_contracts_and_retains_exact_two(
    tmp_path,
) -> None:
    root = tmp_path / "store"
    fake = FakeS3()
    validated = []

    def validate(generation):
        validated.append((
            generation.tick,
            generation.required_files,
        ))
        return True

    first = stage_authoritative_commit_upload(
        store_root=root,
        identity=IDENTITY,
        tick=88,
        save_callback=_save_callback,
        s3_client=fake,
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=128,
        max_dynamic_path_bytes=16 * 1024,
        cold_restore_validator=validate,
    )

    def save_with_learned_media(stage, admission):
        _save_callback(stage, admission, marker="two")
        learned = stage / "assets" / "pictures"
        learned.mkdir(parents=True)
        with admission.open_binary(learned / "learned.bin") as handle:
            handle.write(b"learned-picture")

    second = stage_authoritative_commit_upload(
        store_root=root,
        identity=IDENTITY,
        tick=89,
        save_callback=save_with_learned_media,
        s3_client=fake,
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=128,
        max_dynamic_path_bytes=16 * 1024,
        cold_restore_validator=validate,
    )
    def save_third_contract(stage, admission):
        with admission.open_text(stage / "core.json") as handle:
            handle.write('{"marker":"three"}')
        learned = stage / "sounds"
        learned.mkdir()
        with admission.open_binary(learned / "third.audio") as handle:
            handle.write(b"third-sound")

    third = stage_authoritative_commit_upload(
        store_root=root,
        identity=IDENTITY,
        tick=90,
        save_callback=save_third_contract,
        s3_client=fake,
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=128,
        max_dynamic_path_bytes=16 * 1024,
        cold_restore_validator=validate,
    )
    assert (
        "assets/pictures/learned.bin"
        not in first.generation.required_files
    )
    assert (
        "assets/pictures/learned.bin"
        in second.generation.required_files
    )
    retained_local = {
        path.name
        for path in (root / "generations").iterdir()
    }
    assert retained_local == {
        second.generation.generation_uuid,
        third.generation.generation_uuid,
    }
    assert {
        path.stem
        for path in (root / deployment.DEPLOYMENT_SEALS_DIRECTORY).iterdir()
    } == retained_local
    assert {
        key.split("/")[2]
        for bucket, key in fake.objects
        if bucket == "test-bucket"
    } == retained_local
    dynamic_store = ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=None,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=128,
        max_dynamic_path_bytes=16 * 1024,
    )
    assert dynamic_store.load_current().tick == 90
    assert [tick for tick, _contract in validated] == [
        88,
        88,
        89,
        89,
        88,
        90,
    ]
    loaded_seal = load_generation_deployment_seal(
        root,
        third.generation.generation_uuid,
        hmac_key=HMAC_KEY,
        expected_nonce=NONCE,
    )
    assert loaded_seal["generation_uuid"] == third.generation.generation_uuid


def test_remote_failure_never_publishes_unsealed_current(tmp_path):
    with pytest.raises(RemoteGenerationVerificationError):
        stage_commit_upload(
            store_root=tmp_path / "store",
            identity=IDENTITY,
            tick=88,
            save_callback=_save_callback,
            s3_client=FakeS3(corrupt_every_read=True),
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
        )
    assert not (tmp_path / "store" / CURRENT_NAME).exists()


def test_authoritative_remote_failure_cleans_candidate_prefix_and_seal(
    tmp_path,
) -> None:
    root = tmp_path / "store"
    fake = FakeS3(corrupt_every_read=True)
    with pytest.raises(AuthoritativeColdGenerationError):
        stage_authoritative_commit_upload(
            store_root=root,
            identity=IDENTITY,
            tick=88,
            save_callback=_save_callback,
            s3_client=fake,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
            max_encoded_generation_bytes=64 * 1024,
            max_dynamic_required_files=128,
            max_dynamic_path_bytes=16 * 1024,
            cold_restore_validator=lambda generation: True,
        )
    assert not (root / CURRENT_NAME).exists()
    assert list((root / "generations").iterdir()) == []
    assert fake.objects == {}
    seals = root / deployment.DEPLOYMENT_SEALS_DIRECTORY
    assert not seals.exists() or list(seals.iterdir()) == []


def test_authoritative_stage_rejects_write_before_crossing_byte_capacity(
    tmp_path,
) -> None:
    observed_size = []

    def oversized_save(stage, admission):
        target = stage / "oversized.bin"
        with pytest.raises(
            StageValidationError,
            match="aggregate byte capacity",
        ):
            with admission.open_binary(target) as handle:
                handle.write(b"x" * 1024)
                handle.write(b"y")
        observed_size.append(target.stat().st_size)
        raise RuntimeError("stop after observing bounded write")

    with pytest.raises(RuntimeError, match="bounded write"):
        stage_authoritative_commit_upload(
            store_root=tmp_path / "store",
            identity=IDENTITY,
            tick=88,
            save_callback=oversized_save,
            s3_client=FakeS3(),
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
            max_encoded_generation_bytes=1024,
            max_dynamic_required_files=128,
            max_dynamic_path_bytes=16 * 1024,
            cold_restore_validator=lambda generation: True,
        )
    assert observed_size == [1024]


def test_authoritative_stage_rejects_unadmitted_writer(
    tmp_path,
) -> None:
    def bypass_admission(stage, admission):
        del admission
        (stage / "unadmitted.json").write_text("{}")

    with pytest.raises(
        StageValidationError,
        match="admission ledger",
    ):
        stage_authoritative_commit_upload(
            store_root=tmp_path / "store",
            identity=IDENTITY,
            tick=88,
            save_callback=bypass_admission,
            s3_client=FakeS3(),
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
            max_encoded_generation_bytes=64 * 1024,
            max_dynamic_required_files=128,
            max_dynamic_path_bytes=16 * 1024,
            cold_restore_validator=lambda generation: True,
        )


def test_authoritative_stage_rejects_unrepresented_empty_directories(
    tmp_path,
) -> None:
    def empty_directory_bypass(stage, admission):
        with admission.open_text(stage / "core.json") as handle:
            handle.write("{}")
        (stage / "unrepresented" / "empty").mkdir(parents=True)

    with pytest.raises(
        StageValidationError,
        match="directory tree",
    ):
        stage_authoritative_commit_upload(
            store_root=tmp_path / "store",
            identity=IDENTITY,
            tick=88,
            save_callback=empty_directory_bypass,
            s3_client=FakeS3(),
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
            max_encoded_generation_bytes=64 * 1024,
            max_dynamic_required_files=128,
            max_dynamic_path_bytes=16 * 1024,
            cold_restore_validator=lambda generation: True,
        )


def test_authoritative_seal_failure_removes_remote_and_candidate(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "store"
    fake = FakeS3()

    def reject_seal(*args, **kwargs):
        raise SealValidationError("injected immutable-seal failure")

    monkeypatch.setattr(
        deployment,
        "persist_generation_deployment_seal",
        reject_seal,
    )
    with pytest.raises(AuthoritativeColdGenerationError):
        stage_authoritative_commit_upload(
            store_root=root,
            identity=IDENTITY,
            tick=88,
            save_callback=_save_callback,
            s3_client=fake,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
            max_encoded_generation_bytes=64 * 1024,
            max_dynamic_required_files=128,
            max_dynamic_path_bytes=16 * 1024,
            cold_restore_validator=lambda generation: True,
        )

    assert not (root / CURRENT_NAME).exists()
    assert list((root / "generations").iterdir()) == []
    assert fake.objects == {}


def test_authoritative_current_failure_before_swap_removes_prepared_state(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "store"
    fake = FakeS3()

    def reject_current(self, generation):
        raise OSError("injected CURRENT pre-swap failure")

    monkeypatch.setattr(
        ImmutableGenerationStore,
        "_write_current",
        reject_current,
    )
    with pytest.raises(AuthoritativeColdGenerationError):
        stage_authoritative_commit_upload(
            store_root=root,
            identity=IDENTITY,
            tick=88,
            save_callback=_save_callback,
            s3_client=fake,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
            max_encoded_generation_bytes=64 * 1024,
            max_dynamic_required_files=128,
            max_dynamic_path_bytes=16 * 1024,
            cold_restore_validator=lambda generation: True,
        )

    assert not (root / CURRENT_NAME).exists()
    assert list((root / "generations").iterdir()) == []
    assert fake.objects == {}
    seals = root / deployment.DEPLOYMENT_SEALS_DIRECTORY
    assert not seals.exists() or list(seals.iterdir()) == []


def test_authoritative_current_post_swap_failure_preserves_recoverable_state(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "store"
    fake = FakeS3()
    original = ImmutableGenerationStore._write_current

    def publish_then_fail(self, generation):
        original(self, generation)
        raise OSError("injected CURRENT post-swap acknowledgement failure")

    monkeypatch.setattr(
        ImmutableGenerationStore,
        "_write_current",
        publish_then_fail,
    )
    with pytest.raises(AuthoritativeColdGenerationError):
        stage_authoritative_commit_upload(
            store_root=root,
            identity=IDENTITY,
            tick=88,
            save_callback=_save_callback,
            s3_client=fake,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
            max_encoded_generation_bytes=64 * 1024,
            max_dynamic_required_files=128,
            max_dynamic_path_bytes=16 * 1024,
            cold_restore_validator=lambda generation: True,
        )

    monkeypatch.setattr(
        ImmutableGenerationStore,
        "_write_current",
        original,
    )
    store = ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=None,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=128,
        max_dynamic_path_bytes=16 * 1024,
    )
    current = store.load_current()
    seal = load_generation_deployment_seal(
        root,
        current.generation_uuid,
        hmac_key=HMAC_KEY,
        expected_nonce=NONCE,
    )
    assert current.tick == 88
    assert seal["generation_uuid"] == current.generation_uuid
    assert {
        key.split("/")[2]
        for _, key in fake.objects
    } == {current.generation_uuid}


def test_authoritative_restart_retires_first_boot_prepublication_crash(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "store"
    fake = FakeS3()
    original = deployment.persist_generation_deployment_seal

    def persist_then_crash(*args, **kwargs):
        original(*args, **kwargs)
        raise KeyboardInterrupt(
            "injected process death after seal and before CURRENT")

    monkeypatch.setattr(
        deployment,
        "persist_generation_deployment_seal",
        persist_then_crash,
    )
    with pytest.raises(KeyboardInterrupt):
        stage_authoritative_commit_upload(
            store_root=root,
            identity=IDENTITY,
            tick=88,
            save_callback=_save_callback,
            s3_client=fake,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
            max_encoded_generation_bytes=64 * 1024,
            max_dynamic_required_files=128,
            max_dynamic_path_bytes=16 * 1024,
            cold_restore_validator=lambda generation: True,
        )
    stale_uuid = next(
        (root / deployment.DEPLOYMENT_SEALS_DIRECTORY).iterdir()
    ).stem
    assert not (root / CURRENT_NAME).exists()

    monkeypatch.setattr(
        deployment,
        "persist_generation_deployment_seal",
        original,
    )
    result = stage_authoritative_commit_upload(
        store_root=root,
        identity=IDENTITY,
        tick=89,
        save_callback=_save_callback,
        s3_client=fake,
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=128,
        max_dynamic_path_bytes=16 * 1024,
        cold_restore_validator=lambda generation: True,
    )

    assert result.generation.tick == 89
    assert stale_uuid != result.generation.generation_uuid
    assert {
        path.stem
        for path in (
            root / deployment.DEPLOYMENT_SEALS_DIRECTORY
        ).iterdir()
    } == {result.generation.generation_uuid}
    assert {
        key.split("/")[2]
        for _, key in fake.objects
    } == {result.generation.generation_uuid}


def test_failed_pre_publish_cold_validation_writes_no_remote_or_current(tmp_path):
    fake = FakeS3()

    def reject_cold_restore(generation):
        active = tmp_path / "cold-active"
        result = materialize_verified_generation(
            generation=generation, active_directory=active)
        assert result.tick == 88
        raise RuntimeError("injected cold restore mismatch")

    with pytest.raises(RuntimeError, match="cold restore mismatch"):
        stage_commit_upload(
            store_root=tmp_path / "store",
            identity=IDENTITY,
            tick=88,
            save_callback=_save_callback,
            s3_client=fake,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
            pre_publish_validator=reject_cold_restore,
        )

    assert not fake.objects
    assert not (tmp_path / "store" / CURRENT_NAME).exists()
    assert not (tmp_path / "store" / deployment.DEPLOYMENT_SEAL_NAME).exists()


def test_remote_failure_preserves_prior_sealed_current(tmp_path):
    root = tmp_path / "store"
    first = stage_commit_upload(
        store_root=root,
        identity=IDENTITY,
        tick=88,
        save_callback=_save_callback,
        s3_client=FakeS3(),
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )
    prior_pointer = (root / CURRENT_NAME).read_bytes()

    with pytest.raises(RemoteGenerationVerificationError):
        stage_commit_upload(
            store_root=root,
            identity=IDENTITY,
            tick=89,
            save_callback=lambda stage: _save_callback(stage, marker="two"),
            s3_client=FakeS3(corrupt_every_read=True),
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=b"unique-deploy-nonce-0002",
        )
    assert (root / CURRENT_NAME).read_bytes() == prior_pointer
    assert discover_and_load_current(root).generation.generation_uuid == (
        first.generation.generation_uuid)


def test_persisted_seal_is_immutable_and_nonce_verified(tmp_path):
    root = tmp_path / "store"
    result = stage_commit_upload(
        store_root=root,
        identity=IDENTITY,
        tick=88,
        save_callback=_save_callback,
        s3_client=FakeS3(),
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )
    seal_path = persist_deployment_seal(
        root,
        result.seal_certificate_bytes(),
        hmac_key=HMAC_KEY,
        expected_nonce=NONCE,
    )
    assert oct(seal_path.stat().st_mode & 0o777) == "0o444"
    verified = load_and_verify_deployment_seal(
        root, hmac_key=HMAC_KEY, expected_nonce=NONCE)
    assert verified["generation_uuid"] == result.generation.generation_uuid
    assert load_and_verify_deployment_seal(
        root, hmac_key=HMAC_KEY)["generation_uuid"] == (
            result.generation.generation_uuid)
    with pytest.raises(SealValidationError, match="nonce mismatch"):
        load_and_verify_deployment_seal(
            root,
            hmac_key=HMAC_KEY,
            expected_nonce=b"different-deploy-nonce",
        )


def test_seal_rejects_tampering_and_wrong_key(tmp_path):
    fake = FakeS3()
    _store, generation = _committed_generation(tmp_path)
    certificate_bytes = upload_verified_generation(
        generation,
        s3_client=fake,
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )
    certificate = json.loads(certificate_bytes)
    certificate["objects"][0]["size_bytes"] += 1
    with pytest.raises(SealValidationError, match="HMAC mismatch"):
        verify_deployment_seal(
            certificate, hmac_key=HMAC_KEY, expected_nonce=NONCE)
    with pytest.raises(SealValidationError, match="HMAC mismatch"):
        verify_deployment_seal(
            certificate_bytes,
            hmac_key=b"a-different-key-material-that-is-long-enough",
            expected_nonce=NONCE,
        )


@pytest.mark.parametrize("unsafe_kind", ["symlink", "hardlink", "temp", "fifo"])
def test_stage_rejects_every_unsafe_node_and_publishes_nothing(
        tmp_path, unsafe_kind):
    fake = FakeS3()

    def unsafe_save(stage):
        (stage / "state.json").write_text("{}")
        if unsafe_kind == "symlink":
            (stage / "linked").symlink_to("state.json")
        elif unsafe_kind == "hardlink":
            os.link(stage / "state.json", stage / "hard-linked.json")
        elif unsafe_kind == "temp":
            (stage / "unfinished.tmp").write_bytes(b"partial")
        elif unsafe_kind == "fifo":
            os.mkfifo(stage / "special-fifo")

    with pytest.raises(StageValidationError):
        stage_commit_upload(
            store_root=tmp_path / "store",
            identity=IDENTITY,
            tick=1,
            save_callback=unsafe_save,
            s3_client=fake,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
        )
    assert not (tmp_path / "store" / CURRENT_NAME).exists()
    assert not fake.objects
    assert not list((tmp_path / "store").glob(".deployment-stage-*"))


def test_save_callback_failure_cleans_private_stage(tmp_path):
    def failed_save(stage):
        (stage / "partial.json").write_text("{}")
        raise RuntimeError("injected save failure")

    with pytest.raises(RuntimeError, match="injected save failure"):
        stage_commit_upload(
            store_root=tmp_path / "store",
            identity=IDENTITY,
            tick=1,
            save_callback=failed_save,
            s3_client=FakeS3(),
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
        )
    assert not list((tmp_path / "store").glob(".deployment-stage-*"))


def test_next_transaction_retires_abandoned_private_stage(tmp_path):
    root = tmp_path / "store"
    abandoned = root / ".deployment-stage-interrupted"
    abandoned.mkdir(parents=True)
    (abandoned / "partial.bin").write_bytes(b"unpublished")

    result = stage_commit_upload(
        store_root=root,
        identity=IDENTITY,
        tick=2,
        save_callback=_save_callback,
        s3_client=FakeS3(),
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )

    assert result.generation.tick == 2
    assert not abandoned.exists()
    assert not list(root.glob(".deployment-stage-*"))


def test_named_hidden_state_marker_is_required_but_not_misclassified_as_temp(
        tmp_path):
    def save_with_marker(stage):
        (stage / "core.json").write_text("{}")
        (stage / ".sleeping").write_bytes(b"sleep-boundary")

    result = stage_commit_upload(
        store_root=tmp_path / "store",
        identity=IDENTITY,
        tick=2,
        save_callback=save_with_marker,
        s3_client=FakeS3(),
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )

    assert set(result.generation.required_files) == {".sleeping", "core.json"}


@pytest.mark.parametrize("remote_fault", ["extra", "missing", "corrupt"])
def test_remote_readback_rejects_nonexact_generation(tmp_path, remote_fault):
    fake = FakeS3()
    _store, generation = _committed_generation(tmp_path)
    prefix = f"ae/state/{generation.generation_uuid}/"
    if remote_fault == "extra":
        fake.extra_listing_keys.add(prefix + "unexpected.bin")
    elif remote_fault == "missing":
        fake.hidden_listing_keys.add(prefix + "core.json")
    elif remote_fault == "corrupt":
        fake.corrupt_get_keys.add(prefix + "organism.bin")

    with pytest.raises(RemoteGenerationVerificationError):
        upload_verified_generation(
            generation,
            s3_client=fake,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
        )


def test_upload_revalidates_local_generation_tree_immediately_before_network(
        tmp_path):
    fake = FakeS3()
    _store, generation = _committed_generation(tmp_path)
    os.chmod(generation.directory, 0o755)
    extra = generation.directory / "late-extra.bin"
    extra.write_bytes(b"not certified")
    os.chmod(extra, 0o444)
    os.chmod(generation.directory, 0o555)

    with pytest.raises(
            RemoteGenerationVerificationError, match="exact verified file set"):
        upload_verified_generation(
            generation,
            s3_client=fake,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=NONCE,
        )
    assert not fake.objects


def test_discovery_reads_contract_then_runs_full_verification(tmp_path):
    store, generation = _committed_generation(tmp_path)

    discovered = discover_and_load_current(store.root)

    assert discovered.generation.generation_uuid == generation.generation_uuid
    assert discovered.store.identity == IDENTITY
    assert discovered.store.required_files == tuple(sorted(generation.required_files))

    immutable_file = generation.directory / "organism.bin"
    os.chmod(immutable_file, 0o644)
    immutable_file.write_bytes(b"tampered")
    os.chmod(immutable_file, 0o444)
    with pytest.raises(Exception, match="full immutable-store verification"):
        discover_and_load_current(store.root)


def test_discovery_never_trusts_pointer_generation_path(tmp_path):
    store, _generation = _committed_generation(tmp_path)
    pointer_path = store.root / CURRENT_NAME
    pointer = json.loads(pointer_path.read_text())
    pointer["generation_path"] = "../../outside"
    _rewrite_read_only_json(pointer_path, pointer)

    with pytest.raises(Exception, match="not UUID-derived"):
        discover_and_load_current(store.root)


def test_materialize_current_unwraps_json_and_preserves_binary(tmp_path):
    store, generation = _committed_generation(tmp_path)
    immutable_before = {
        relative: (generation.directory / relative).read_bytes()
        for relative in generation.required_files
    }
    active = tmp_path / "active"
    active.mkdir()
    (active / "old-only.txt").write_text("old generation")

    result = materialize_current(
        store_root=store.root,
        active_directory=active,
    )

    assert result.generation_uuid == generation.generation_uuid
    assert result.identity == IDENTITY
    assert result.tick == 77
    assert set(result.materialized_files) == set(generation.required_files)
    assert json.loads((active / "core.json").read_text()) == {
        "marker": "one", "tick": 7,
    }
    assert "generation_uuid" not in json.loads((active / "core.json").read_text())
    assert (active / "organism.bin").read_bytes() == b"\x00organism\xffone"
    assert not (active / "old-only.txt").exists()
    assert {
        relative: (generation.directory / relative).read_bytes()
        for relative in generation.required_files
    } == immutable_before
    assert not list(active.parent.glob(f".{active.name}.materializing-*"))


def test_matching_active_generation_is_adopted_without_rewrite(
        tmp_path, monkeypatch):
    _store, generation = _committed_generation(tmp_path)
    active = tmp_path / "active"
    first = materialize_verified_generation(
        generation=generation,
        active_directory=active,
    )
    runtime = active / "backups"
    runtime.mkdir()
    (runtime / "audit-only.txt").write_text("not generation authority")

    def reject_rewrite(*_args, **_kwargs):
        raise AssertionError("matching active generation was rewritten")

    monkeypatch.setattr(
        deployment,
        "_write_materialization",
        reject_rewrite,
    )
    adopted = materialize_verified_generation(
        generation=generation,
        active_directory=active,
    )

    assert adopted == first
    assert (runtime / "audit-only.txt").read_text() == "not generation authority"
    assert not list(active.parent.glob(f".{active.name}.materializing-*"))
    assert not list(active.parent.glob(f".{active.name}.retired-*"))


def test_mismatched_active_generation_still_uses_atomic_materialization(
        tmp_path, monkeypatch):
    _store, generation = _committed_generation(tmp_path)
    active = tmp_path / "active"
    materialize_verified_generation(
        generation=generation,
        active_directory=active,
    )
    (active / "core.json").write_text('{"marker":"wrong","tick":7}\n')
    real_write = deployment._write_materialization
    writes = []

    def record_write(candidate, expected):
        writes.append(candidate)
        return real_write(candidate, expected)

    monkeypatch.setattr(
        deployment,
        "_write_materialization",
        record_write,
    )
    restored = materialize_verified_generation(
        generation=generation,
        active_directory=active,
    )

    assert len(writes) == 1
    assert restored.generation_uuid == generation.generation_uuid
    assert json.loads((active / "core.json").read_text()) == {
        "marker": "one",
        "tick": 7,
    }


def test_materialize_current_applies_the_generation_retention_boundary(tmp_path):
    store, first = _committed_generation(tmp_path)
    source = tmp_path / "source"
    generations = [first]
    for tick in range(78, 82):
        generations.append(store.commit(
            tick=tick,
            files={
                relative: source / relative
                for relative in store.required_files
            },
        ))

    result = materialize_current(
        store_root=store.root,
        active_directory=tmp_path / "active",
        retained_generations=3,
    )

    assert result.generation_uuid == generations[-1].generation_uuid
    assert {
        path.name for path in store.generations_directory.iterdir()
    } == {
        generations[-1].generation_uuid,
        generations[-2].generation_uuid,
        generations[-3].generation_uuid,
    }


def test_materialization_rolls_back_existing_active_directory_on_post_swap_failure(
        tmp_path, monkeypatch):
    store, _generation = _committed_generation(tmp_path)
    active = tmp_path / "active"
    active.mkdir()
    (active / "old.json").write_text('{"old":true}')
    real_verify = deployment._verify_materialization
    calls = 0

    def fail_after_swap(directory, expected):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise MaterializationError("injected post-swap verification failure")
        return real_verify(directory, expected)

    monkeypatch.setattr(deployment, "_verify_materialization", fail_after_swap)
    with pytest.raises(MaterializationError, match="post-swap"):
        materialize_current(store_root=store.root, active_directory=active)

    assert json.loads((active / "old.json").read_text()) == {"old": True}
    assert set(path.name for path in active.iterdir()) == {"old.json"}
    assert not list(active.parent.glob(f".{active.name}.materializing-*"))


def test_materialization_uses_restart_recoverable_rename_when_exchange_unsupported(
        tmp_path, monkeypatch):
    store, generation = _committed_generation(tmp_path)
    active = tmp_path / "active"
    active.mkdir()
    (active / "old-only.txt").write_text("old generation")

    def exchange_unsupported(_first, _second):
        raise deployment.AtomicDirectorySwapUnsupported(
            "filesystem does not support atomic directory exchange")

    monkeypatch.setattr(deployment, "_rename_exchange", exchange_unsupported)
    result = materialize_current(
        store_root=store.root,
        active_directory=active,
    )

    assert result.generation_uuid == generation.generation_uuid
    assert json.loads((active / "core.json").read_text()) == {
        "marker": "one", "tick": 7,
    }
    assert not (active / "old-only.txt").exists()
    assert not list(active.parent.glob(f".{active.name}.retired-*"))
    assert not list(active.parent.glob(f".{active.name}.materializing-*"))


def test_efs_rename_fallback_restores_prior_active_on_verification_failure(
        tmp_path, monkeypatch):
    store, _generation = _committed_generation(tmp_path)
    active = tmp_path / "active"
    active.mkdir()
    (active / "old.json").write_text('{"old":true}')
    real_verify = deployment._verify_materialization
    calls = 0

    def exchange_unsupported(_first, _second):
        raise deployment.AtomicDirectorySwapUnsupported(
            "filesystem does not support atomic directory exchange")

    def fail_after_activation(directory, expected):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise MaterializationError("injected EFS verification failure")
        return real_verify(directory, expected)

    monkeypatch.setattr(deployment, "_rename_exchange", exchange_unsupported)
    monkeypatch.setattr(
        deployment, "_verify_materialization", fail_after_activation)
    with pytest.raises(MaterializationError, match="EFS verification"):
        materialize_current(store_root=store.root, active_directory=active)

    assert json.loads((active / "old.json").read_text()) == {"old": True}
    assert not list(active.parent.glob(f".{active.name}.retired-*"))
    assert not list(active.parent.glob(f".{active.name}.materializing-*"))


def test_materialization_rejects_active_path_inside_immutable_store(tmp_path):
    store, _generation = _committed_generation(tmp_path)
    with pytest.raises(MaterializationError, match="inside"):
        materialize_current(
            store_root=store.root,
            active_directory=store.root / "active",
        )


def test_process_lifetime_efs_owner_lock_is_nonblocking_and_never_unlinked(tmp_path):
    lock_path = tmp_path / "efs" / "owner.lock"
    first = ProcessLifetimeEFSOwnerLock(lock_path).acquire()
    assert first.acquired
    assert lock_path.exists()
    owner = json.loads(lock_path.read_text())
    assert owner["schema"] == "deployment_generation_efs_owner_v1"
    assert owner["pid"] == os.getpid()

    second = ProcessLifetimeEFSOwnerLock(lock_path)
    with pytest.raises(EFSOwnerLockUnavailable):
        second.acquire()

    first.release()
    assert not first.acquired
    assert lock_path.exists()
    second.acquire()
    assert second.acquired
    second.release()
    assert lock_path.exists()
