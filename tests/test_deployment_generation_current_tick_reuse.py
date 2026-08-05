import asyncio
import contextlib
import hashlib
import hmac
import importlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from dsf_ai_service.substrate.deployment_generation import (
    BoundedStageAdmission,
    CAUSAL_GENERATION_RECEIPT,
    DeploymentGenerationError,
    RemoteGenerationVerificationError,
    SealValidationError,
    causal_generation_revision,
    load_and_verify_deployment_seal,
    load_generation_deployment_seal,
    persist_deployment_seal,
    persist_generation_deployment_seal,
    stage_authoritative_commit_upload,
    upload_verified_generation,
    verified_causal_generation_receipt,
    verify_staged_authoritative_checkpoint,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    GENERATIONS_DIRECTORY,
    LOCK_NAME,
    ImmutableGenerationStore,
    LoadedGeneration,
)
from dsf_ai_service.substrate.authoritative_cold_generation_store import (
    AuthoritativeColdGenerationError,
    AuthoritativeColdGenerationStore,
)


IDENTITY = "current-tick-reuse-ae"
HMAC_KEY = b"current-tick-reuse-hmac-key-material"
FIRST_NONCE = b"current-tick-first-nonce"
SECOND_NONCE = b"current-tick-second-nonce"


class _FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.put_calls = 0
        self.get_calls = 0
        self.delete_calls = 0
        self.fail_on_put = False
        self.fail_on_delete = False

    def put_object(self, *, Bucket, Key, Body, ContentLength=None):
        self.put_calls += 1
        if self.fail_on_put:
            raise AssertionError("retained remote generation must not be PUT")
        data = Body.read() if hasattr(Body, "read") else bytes(Body)
        assert ContentLength is None or len(data) == ContentLength
        self.objects[(Bucket, Key)] = data
        return {"ETag": hashlib.md5(data).hexdigest()}

    def list_objects_v2(self, *, Bucket, Prefix, ContinuationToken=None):
        assert ContinuationToken is None
        keys = sorted(
            key
            for bucket, key in self.objects
            if bucket == Bucket and key.startswith(Prefix)
        )
        return {
            "Contents": [{"Key": key} for key in keys],
            "IsTruncated": False,
        }

    def get_object(self, *, Bucket, Key):
        self.get_calls += 1
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def delete_objects(self, *, Bucket, Delete):
        self.delete_calls += 1
        if self.fail_on_delete:
            raise AssertionError(
                "duplicate CURRENT proof must not reconcile remote prefixes"
            )
        for record in Delete["Objects"]:
            self.objects.pop((Bucket, record["Key"]), None)
        return {"Deleted": list(Delete["Objects"])}


def _save(marker: str, tick: int):
    def save(stage: Path, admission) -> int:
        with admission.open_text(stage / "core.json") as handle:
            handle.write(json.dumps({"marker": marker, "tick": tick}))
        with admission.open_binary(stage / "organism.bin") as handle:
            handle.write(b"organism:" + marker.encode("ascii"))
        return tick

    return save


def _engine_envelope(
    *,
    timestamp: str,
    current_activity,
    nested_timestamp: str = "causal-nested",
) -> dict:
    return {
        "schema_version": "physical-runtime-v1",
        "guala_identity": IDENTITY,
        "saved_at_tick": 9,
        "saved_at_timestamp": timestamp,
        "data": {
            "tick": 9,
            "current_activity": current_activity,
            "nested": {
                "saved_at_timestamp": nested_timestamp,
                "sleep_ts": "causal-lookalike",
            },
        },
    }


def _save_engine_state(
    *,
    timestamp: str,
    sleep_ts: float,
    current_activity,
    nested_timestamp: str = "causal-nested",
    binary: bytes = b"exact-organism",
):
    def save(stage: Path, admission) -> int:
        with admission.open_text(stage / "guala_core.json") as handle:
            handle.write(json.dumps(_engine_envelope(
                timestamp=timestamp,
                current_activity=current_activity,
                nested_timestamp=nested_timestamp,
            )))
        with admission.open_text(stage / ".sleeping") as handle:
            handle.write(json.dumps({
                "sleep_tick": 9,
                "sleep_ts": sleep_ts,
            }))
        with admission.open_binary(stage / "organism.bin") as handle:
            handle.write(binary)
        return 9

    return save


def _commit_callback(
    *,
    root: Path,
    s3: _FakeS3,
    save,
    nonce: bytes,
    allow_equal_tick_schema_migration: bool = False,
    equal_tick_causal_transition_validator=None,
):
    return stage_authoritative_commit_upload(
        store_root=root,
        identity=IDENTITY,
        save_callback=save,
        s3_client=s3,
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=nonce,
        max_encoded_generation_bytes=16 * 1024 * 1024,
        max_dynamic_required_files=32,
        max_dynamic_path_bytes=4096,
        cold_restore_validator=lambda generation: True,
        allow_equal_tick_schema_migration=(
            allow_equal_tick_schema_migration
        ),
        equal_tick_causal_transition_validator=(
            equal_tick_causal_transition_validator
        ),
    )


def _commit(
    *,
    root: Path,
    s3: _FakeS3,
    marker: str,
    tick: int,
    nonce: bytes,
    validated: list[str],
    bucket: str = "test-bucket",
    prefix: str = "ae/state",
    allow_equal_tick_schema_migration: bool = False,
    equal_tick_causal_transition_validator=None,
):
    return stage_authoritative_commit_upload(
        store_root=root,
        identity=IDENTITY,
        save_callback=_save(marker, tick),
        s3_client=s3,
        bucket=bucket,
        prefix=prefix,
        hmac_key=HMAC_KEY,
        nonce=nonce,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=16,
        max_dynamic_path_bytes=1024,
        cold_restore_validator=lambda generation: (
            validated.append(generation.generation_uuid) or True
        ),
        allow_equal_tick_schema_migration=(
            allow_equal_tick_schema_migration
        ),
        equal_tick_causal_transition_validator=(
            equal_tick_causal_transition_validator
        ),
    )


def test_exact_current_tick_reuses_verified_generation_with_fresh_seal(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []

    first = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )
    generation_seal_before = (
        root
        / "deployment-seals"
        / f"{first.generation.generation_uuid}.json"
    ).read_bytes()
    remote_before = dict(s3.objects)
    put_calls_before = s3.put_calls
    s3.fail_on_put = True

    reused = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=SECOND_NONCE,
        validated=validated,
    )

    assert reused.generation.generation_uuid == first.generation.generation_uuid
    assert reused.generation.manifest_sha256 == first.generation.manifest_sha256
    assert reused.generation.tick == 9
    assert reused.version_aware_remote_reconciliation is False
    assert reused.read_only_remote_reuse_verified is True
    assert reused.remote_retained_generation_uuids == (
        first.generation.generation_uuid,
    )
    assert reused.remote_retired_generation_uuids == ()
    assert s3.put_calls == put_calls_before
    assert s3.objects == remote_before
    assert s3.get_calls > 0
    assert validated == [
        first.generation.generation_uuid,
        first.generation.generation_uuid,
    ]
    assert sorted(
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    ) == [first.generation.generation_uuid]
    assert (
        root
        / "deployment-seals"
        / f"{first.generation.generation_uuid}.json"
    ).read_bytes() == generation_seal_before
    immutable_seal = load_generation_deployment_seal(
        root,
        first.generation.generation_uuid,
        hmac_key=HMAC_KEY,
        expected_nonce=FIRST_NONCE,
    )
    fresh_pointer = load_and_verify_deployment_seal(
        root,
        hmac_key=HMAC_KEY,
        expected_nonce=SECOND_NONCE,
    )
    assert immutable_seal["generation_uuid"] == first.generation.generation_uuid
    assert fresh_pointer["generation_uuid"] == first.generation.generation_uuid
    assert {
        key: value
        for key, value in fresh_pointer.items()
        if key not in {"nonce_base64", "seal_hmac_sha256"}
    } == {
        key: value
        for key, value in immutable_seal.items()
        if key not in {"nonce_base64", "seal_hmac_sha256"}
    }


def test_real_app_seal_accepts_and_records_exact_read_only_reuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import boto3

    from dsf_ai_service import app as app_module
    from dsf_ai_service.substrate import deployment_generation

    root = tmp_path / "store"
    s3 = _FakeS3()
    first = _commit_callback(
        root=root,
        s3=s3,
        save=_bootable_save,
        nonce=FIRST_NONCE,
    )
    put_calls_before = s3.put_calls
    s3.fail_on_put = True
    reused = _commit_callback(
        root=root,
        s3=s3,
        save=_bootable_save,
        nonce=SECOND_NONCE,
    )
    assert s3.put_calls == put_calls_before
    assert reused.read_only_remote_reuse_verified is True

    finalized: list[tuple[int, dict]] = []

    class _AppGuala:
        _guala_identity = IDENTITY

        @contextlib.contextmanager
        def persistence_transaction(self):
            yield

        def finalize_authoritative_full_checkpoint(
            self,
            *,
            expected_tick,
            state_file_ticks,
        ):
            finalized.append((expected_tick, state_file_ticks))

        def discard_prepared_authoritative_full_checkpoint(self):
            raise AssertionError("successful reuse must finalize checkpoint")

    physical = {
        "ceiling_bytes": (
            app_module.APPROVED_PERSISTENT_STORAGE_CEILING_BYTES
        ),
    }
    store_status = {
        "content_addressed": True,
        "physical_bytes": physical,
    }
    overlay = SimpleNamespace(
        generation_uuid="22222222-2222-4222-8222-222222222222",
        identity=IDENTITY,
        manifest_sha256="2" * 64,
        tick=reused.generation.tick,
    )

    class _AppLiveRecovery:
        def rebase_after_deployment_seal(self, *, baseline, tick, files):
            assert baseline is reused.generation
            assert tick == reused.generation.tick
            assert tuple(files) == ("guala_core.json",)
            return overlay

        def persistence_status(self):
            return dict(store_status)

    live_recovery = _AppLiveRecovery()
    monkeypatch.setattr(app_module, "_guala", _AppGuala())
    monkeypatch.setattr(app_module, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(
        app_module,
        "_deployment_baseline_generation",
        first.generation,
    )
    monkeypatch.setattr(app_module, "_loaded_generation", None)
    monkeypatch.setattr(
        app_module,
        "_remote_generation_reconciliation",
        None,
    )
    monkeypatch.setattr(
        app_module,
        "_live_recovery_store",
        live_recovery,
    )
    monkeypatch.setattr(
        app_module,
        "_authoritative_cold_store",
        SimpleNamespace(
            persistence_status=lambda: dict(store_status),
        ),
    )
    monkeypatch.setattr(
        app_module,
        "_physical_byte_authority",
        SimpleNamespace(configuration=lambda: dict(physical)),
    )
    monkeypatch.setattr(
        app_module,
        "GENERATION_STORE_ROOT",
        str(root),
    )
    monkeypatch.setattr(app_module, "STATE_DIR", str(tmp_path / "active"))
    monkeypatch.setattr(app_module, "_deploy_hmac_key", lambda: HMAC_KEY)
    monkeypatch.setattr(
        app_module,
        "_authoritative_cold_limits",
        lambda: (16 * 1024 * 1024, 32, 4096),
    )
    monkeypatch.setattr(
        app_module,
        "_authoritative_physical_storage_config",
        lambda: (
            app_module.APPROVED_PERSISTENT_STORAGE_CEILING_BYTES,
            str(tmp_path),
            SimpleNamespace(),
        ),
    )
    monkeypatch.setattr(
        app_module.Guala,
        "HOT_SAVE_MANIFEST_FILES",
        ("guala_core.json",),
    )
    monkeypatch.setattr(
        deployment_generation,
        "stage_authoritative_commit_upload",
        lambda **_kwargs: reused,
    )
    monkeypatch.setattr(boto3, "client", lambda *_args, **_kwargs: object())

    receipt = app_module._seal_runtime_generation(
        SECOND_NONCE.decode("ascii")
    )

    assert receipt["generation_uuid"] == reused.generation.generation_uuid
    assert receipt["active_recovery_generation"] == overlay.generation_uuid
    assert finalized == [
        (
            reused.generation.tick,
            {"guala_core.json": reused.generation.tick},
        ),
    ]
    assert app_module._remote_generation_reconciliation == {
        "executed": True,
        "retained_generation_uuids": (
            reused.generation.generation_uuid,
        ),
        "retired_generation_uuids": (),
        "version_aware": False,
        "read_only_remote_reuse_verified": True,
        "proof_mode": "exact_read_only_reuse",
    }
    status = app_module._verified_storage_cutover_status()
    assert status["remote_reconciliation"]["proof_mode"] == (
        "exact_read_only_reuse"
    )


def test_same_tick_different_payload_is_rejected_without_migration_authority(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []
    first = _commit(
        root=root,
        s3=s3,
        marker="first",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )
    with pytest.raises(
        DeploymentGenerationError,
        match="same-tick checkpoint changed causal content",
    ):
        _commit(
            root=root,
            s3=s3,
            marker="different",
            tick=9,
            nonce=SECOND_NONCE,
            validated=validated,
        )

    assert validated == [first.generation.generation_uuid]
    assert sorted(
        path.name
        for path in (root / GENERATIONS_DIRECTORY).iterdir()
    ) == [first.generation.generation_uuid]
    assert load_and_verify_deployment_seal(
        root,
        hmac_key=HMAC_KEY,
        expected_nonce=FIRST_NONCE,
    )["generation_uuid"] == first.generation.generation_uuid


def test_read_only_rehearsal_uses_the_same_same_tick_causal_refusal(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    stage = tmp_path / "stage"
    stage.mkdir()
    first = _commit(
        root=root,
        s3=_FakeS3(),
        marker="first",
        tick=9,
        nonce=FIRST_NONCE,
        validated=[],
    )
    admission = BoundedStageAdmission(
        stage,
        max_total_bytes=16 * 1024 * 1024,
        max_required_files=32,
        max_path_bytes=4096,
    )
    captured_tick = _save("different", 9)(stage, admission)

    with pytest.raises(
        DeploymentGenerationError,
        match="same-tick checkpoint changed causal content",
    ):
        verify_staged_authoritative_checkpoint(
            store_root=root,
            identity=IDENTITY,
            captured_tick=captured_tick,
            stage_root=stage,
            max_encoded_generation_bytes=16 * 1024 * 1024,
            max_dynamic_required_files=32,
            max_dynamic_path_bytes=4096,
        )

    current = ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=first.generation.required_files,
        content_addressed=True,
    ).load_current()
    assert current.generation_uuid == first.generation.generation_uuid


def test_same_tick_causal_transition_requires_validator_to_accept_exact_stage(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []
    first = _commit(
        root=root,
        s3=s3,
        marker="first",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )
    observations = []

    def exact_transition(current, staged_files, captured_tick):
        observations.append(
            (
                current.generation_uuid,
                tuple(sorted(staged_files)),
                captured_tick,
            )
        )
        return (
            current.generation_uuid == first.generation.generation_uuid
            and set(staged_files) == {"core.json", "organism.bin"}
            and captured_tick == 9
            and b"different" in staged_files["organism.bin"].read_bytes()
        )

    promoted = _commit(
        root=root,
        s3=s3,
        marker="different",
        tick=9,
        nonce=SECOND_NONCE,
        validated=validated,
        equal_tick_causal_transition_validator=exact_transition,
    )

    assert promoted.generation.generation_uuid != (
        first.generation.generation_uuid
    )
    assert promoted.generation.tick == first.generation.tick
    assert causal_generation_revision(promoted.generation) == (
        causal_generation_revision(first.generation) + 1
    )
    assert observations == [
        (
            first.generation.generation_uuid,
            ("core.json", "organism.bin"),
            9,
        )
    ]


def test_older_tick_fails_before_cold_validation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []
    first = _commit(
        root=root,
        s3=s3,
        marker="first",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )

    with pytest.raises(
        DeploymentGenerationError,
        match="older than CURRENT",
    ):
        _commit(
            root=root,
            s3=s3,
            marker="first",
            tick=8,
            nonce=SECOND_NONCE,
            validated=validated,
        )

    assert validated == [first.generation.generation_uuid]


def test_reuse_rejects_remote_target_divergence_without_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []
    _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )
    remote_before = dict(s3.objects)
    seal_before = load_and_verify_deployment_seal(
        root,
        hmac_key=HMAC_KEY,
        expected_nonce=FIRST_NONCE,
    )
    s3.fail_on_put = True

    with pytest.raises(
        DeploymentGenerationError,
        match="remote target differs",
    ):
        _commit(
            root=root,
            s3=s3,
            marker="same",
            tick=9,
            nonce=SECOND_NONCE,
            validated=validated,
            bucket="different-bucket",
            prefix="different/prefix",
        )

    assert s3.objects == remote_before
    assert load_and_verify_deployment_seal(
        root,
        hmac_key=HMAC_KEY,
        expected_nonce=FIRST_NONCE,
    ) == seal_before


def test_corrupt_retained_remote_fails_read_only_and_is_not_overwritten(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []
    _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )
    corrupt_key = min(s3.objects)
    s3.objects[corrupt_key] = b"corrupt retained remote bytes"
    corrupted = dict(s3.objects)
    put_calls_before = s3.put_calls
    s3.fail_on_put = True

    with pytest.raises(
        RemoteGenerationVerificationError,
        match="differs from its immutable deployment seal",
    ):
        _commit(
            root=root,
            s3=s3,
            marker="same",
            tick=9,
            nonce=SECOND_NONCE,
            validated=validated,
        )

    assert s3.put_calls == put_calls_before
    assert s3.objects == corrupted
    load_and_verify_deployment_seal(
        root,
        hmac_key=HMAC_KEY,
        expected_nonce=FIRST_NONCE,
    )


@pytest.mark.parametrize("difference", ("missing", "extra"))
def test_remote_key_set_must_exactly_match_immutable_seal(
    tmp_path: Path,
    difference: str,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []
    first = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )
    if difference == "missing":
        s3.objects.pop(min(s3.objects))
    else:
        s3.objects[(
            "test-bucket",
            (
                "ae/state/"
                f"{first.generation.generation_uuid}/unexpected-object"
            ),
        )] = b"unexpected"
    remote_before = dict(s3.objects)
    put_calls_before = s3.put_calls
    s3.fail_on_put = True

    with pytest.raises(
        RemoteGenerationVerificationError,
        match="missing sealed keys|unexpected key",
    ):
        _commit(
            root=root,
            s3=s3,
            marker="same",
            tick=9,
            nonce=SECOND_NONCE,
            validated=validated,
        )

    assert s3.put_calls == put_calls_before
    assert s3.objects == remote_before


def test_signed_object_authority_mismatch_is_rejected_before_remote_access(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []
    first = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )
    generation_seal = (
        root
        / "deployment-seals"
        / f"{first.generation.generation_uuid}.json"
    )
    certificate = json.loads(generation_seal.read_bytes())
    certificate["objects"][0]["sha256"] = "0" * 64
    unsigned = {
        key: value
        for key, value in certificate.items()
        if key != "seal_hmac_sha256"
    }
    canonical_unsigned = json.dumps(
        unsigned,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    certificate["seal_hmac_sha256"] = hmac.new(
        HMAC_KEY,
        canonical_unsigned,
        hashlib.sha256,
    ).hexdigest()
    forged = json.dumps(
        certificate,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    generation_seal.chmod(0o600)
    generation_seal.write_bytes(forged)
    generation_seal.chmod(0o444)
    get_calls_before = s3.get_calls
    remote_before = dict(s3.objects)
    s3.fail_on_put = True

    with pytest.raises(
        SealValidationError,
        match="object authority differs from CURRENT",
    ):
        _commit(
            root=root,
            s3=s3,
            marker="same",
            tick=9,
            nonce=SECOND_NONCE,
            validated=validated,
        )

    assert s3.get_calls == get_calls_before
    assert s3.objects == remote_before


@pytest.mark.parametrize("damage", ("missing", "corrupt"))
def test_missing_or_corrupt_generation_bound_seal_fails_without_remote_mutation(
    tmp_path: Path,
    damage: str,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []
    first = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )
    generation_seal = (
        root
        / "deployment-seals"
        / f"{first.generation.generation_uuid}.json"
    )
    if damage == "missing":
        generation_seal.unlink()
        error = DeploymentGenerationError
        message = "no generation-bound deployment seal"
    else:
        generation_seal.chmod(0o600)
        generation_seal.write_bytes(b"{}")
        generation_seal.chmod(0o444)
        error = SealValidationError
        message = "nonce is missing"
    remote_before = dict(s3.objects)
    put_calls_before = s3.put_calls
    s3.fail_on_put = True

    with pytest.raises(error, match=message):
        _commit(
            root=root,
            s3=s3,
            marker="same",
            tick=9,
            nonce=SECOND_NONCE,
            validated=validated,
        )

    assert s3.put_calls == put_calls_before
    assert s3.objects == remote_before
    load_and_verify_deployment_seal(
        root,
        hmac_key=HMAC_KEY,
        expected_nonce=FIRST_NONCE,
    )


def test_large_json_reuse_uses_deterministic_candidate_not_current_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    large_text = "x" * (8 * 1024 * 1024)

    def save(stage: Path, admission) -> int:
        with admission.open_text(stage / "core.json") as handle:
            handle.write(json.dumps({"large": large_text, "tick": 9}))
        with admission.open_binary(stage / "organism.bin") as handle:
            handle.write(b"same-organism")
        return 9

    def commit(nonce: bytes):
        return stage_authoritative_commit_upload(
            store_root=root,
            identity=IDENTITY,
            save_callback=save,
            s3_client=s3,
            bucket="test-bucket",
            prefix="ae/state",
            hmac_key=HMAC_KEY,
            nonce=nonce,
            max_encoded_generation_bytes=16 * 1024 * 1024,
            max_dynamic_required_files=16,
            max_dynamic_path_bytes=1024,
            cold_restore_validator=lambda generation: True,
        )

    first = commit(FIRST_NONCE)

    def forbidden_payload_materialization(self, relative_path):
        raise AssertionError(
            "duplicate comparison must not materialize CURRENT JSON payload"
        )

    monkeypatch.setattr(
        LoadedGeneration,
        "payload",
        forbidden_payload_materialization,
    )
    put_calls_before = s3.put_calls
    s3.fail_on_put = True
    reused = commit(SECOND_NONCE)

    assert reused.generation.generation_uuid == first.generation.generation_uuid
    assert reused.generation.manifest_sha256 == first.generation.manifest_sha256
    assert s3.put_calls == put_calls_before


def test_duplicate_proof_never_enters_remote_reconciliation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    validated: list[str] = []
    first = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=validated,
    )
    stale_key = (
        "test-bucket",
        "ae/state/00000000-0000-0000-0000-000000000001/MANIFEST.json",
    )
    s3.objects[stale_key] = b"unrelated stale prefix"
    s3.fail_on_put = True
    s3.fail_on_delete = True

    reused = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=SECOND_NONCE,
        validated=validated,
    )

    assert reused.generation.generation_uuid == first.generation.generation_uuid
    assert s3.delete_calls == 0
    assert s3.objects[stale_key] == b"unrelated stale prefix"
    load_and_verify_deployment_seal(
        root,
        hmac_key=HMAC_KEY,
        expected_nonce=SECOND_NONCE,
    )


def test_only_closed_operational_fields_may_change_during_reuse(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    sleeping = {
        "kind": "SLEEPING",
        "target": None,
        "started_tick": 9,
        "expected_end_tick": 109,
        "metadata": {"trigger": "manual"},
    }
    first = _commit_callback(
        root=root,
        s3=s3,
        save=_save_engine_state(
            timestamp="2026-07-28T01:02:03Z",
            sleep_ts=1000.25,
            current_activity=sleeping,
        ),
        nonce=FIRST_NONCE,
    )
    second = _commit_callback(
        root=root,
        s3=s3,
        save=_save_engine_state(
            timestamp="2026-07-28T04:05:06Z",
            sleep_ts=2000.75,
            current_activity=sleeping,
        ),
        nonce=SECOND_NONCE,
    )

    assert second.generation.generation_uuid == first.generation.generation_uuid
    first_seal = first.seal_certificate()
    second_seal = second.seal_certificate()
    receipt_record = next(
        record
        for record in first.generation.recovery_certificate()[
            "required_files"
        ]
        if record["relative_path"] == CAUSAL_GENERATION_RECEIPT
    )
    sealed_receipt = next(
        record
        for record in first_seal["objects"]
        if (
            record["sha256"] == receipt_record["sha256"]
            and record["size_bytes"] == receipt_record["size_bytes"]
        )
    )
    assert sealed_receipt["sha256"] == receipt_record["sha256"]
    assert sealed_receipt["size_bytes"] == receipt_record["size_bytes"]
    assert first.generation.payload(
        CAUSAL_GENERATION_RECEIPT
    )["causal_state_sha256"] == first_seal["causal_state_sha256"]
    assert (
        second_seal["causal_state_sha256"]
        == first_seal["causal_state_sha256"]
    )
    assert (
        second_seal["operational_metadata_sha256"]
        == first_seal["operational_metadata_sha256"]
    )
    assert (
        second_seal["attempt_operational_metadata_sha256"]
        != second_seal["operational_metadata_sha256"]
    )


@pytest.mark.parametrize(
    ("change", "value"),
    (
        ("nested_timestamp", "changed-causal-nested"),
        ("binary", b"changed-organism"),
        ("current_activity", None),
    ),
)
def test_explicit_schema_migration_advances_same_tick_revision(
    tmp_path: Path,
    change: str,
    value,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    sleeping = {
        "kind": "SLEEPING",
        "target": None,
        "started_tick": 9,
        "expected_end_tick": 109,
        "metadata": {"trigger": "manual"},
    }
    baseline = {
        "timestamp": "2026-07-28T01:02:03Z",
        "sleep_ts": 1000.25,
        "current_activity": sleeping,
        "nested_timestamp": "causal-nested",
        "binary": b"exact-organism",
    }
    first = _commit_callback(
        root=root,
        s3=s3,
        save=_save_engine_state(**baseline),
        nonce=FIRST_NONCE,
    )
    changed = dict(baseline)
    changed[change] = value
    second = _commit_callback(
        root=root,
        s3=s3,
        save=_save_engine_state(**changed),
        nonce=SECOND_NONCE,
        allow_equal_tick_schema_migration=True,
    )

    assert second.generation.generation_uuid != first.generation.generation_uuid
    assert second.seal_certificate()["state_revision"] == (
        first.seal_certificate()["state_revision"] + 1
    )
    assert (
        second.seal_certificate()["causal_state_sha256"]
        != first.seal_certificate()["causal_state_sha256"]
    )


def test_raw_top_level_timestamp_lookalike_remains_causal(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()

    def save(value: str):
        def callback(stage: Path, admission) -> int:
            with admission.open_text(
                stage / "unknown" / "dynamic.json"
            ) as handle:
                handle.write(json.dumps(_engine_envelope(
                    timestamp=value,
                    current_activity=None,
                )))
            return 9

        return callback

    first = _commit_callback(
        root=root,
        s3=s3,
        save=save("2026-07-28T01:02:03Z"),
        nonce=FIRST_NONCE,
    )
    second = _commit_callback(
        root=root,
        s3=s3,
        save=save("2026-07-28T04:05:06Z"),
        nonce=SECOND_NONCE,
        allow_equal_tick_schema_migration=True,
    )

    assert second.generation.generation_uuid != first.generation.generation_uuid
    assert second.seal_certificate()["state_revision"] == 2


def test_legacy_same_tick_generation_migrates_through_revision_one(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    source = tmp_path / "legacy-source"
    source.mkdir()
    (source / "core.json").write_text(
        json.dumps({"marker": "same", "tick": 9})
    )
    (source / "organism.bin").write_bytes(b"organism:same")
    legacy_store = ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=("core.json", "organism.bin"),
    )
    legacy = legacy_store.commit(
        tick=9,
        files={
            "core.json": source / "core.json",
            "organism.bin": source / "organism.bin",
        },
    )
    s3 = _FakeS3()
    legacy_seal = upload_verified_generation(
        legacy,
        s3_client=s3,
        bucket="test-bucket",
        prefix="ae/state",
        hmac_key=HMAC_KEY,
        nonce=FIRST_NONCE,
    )
    persist_generation_deployment_seal(
        root,
        legacy_seal,
        hmac_key=HMAC_KEY,
        expected_nonce=FIRST_NONCE,
    )
    persist_deployment_seal(
        root,
        legacy_seal,
        hmac_key=HMAC_KEY,
        expected_nonce=FIRST_NONCE,
    )

    migrated = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=SECOND_NONCE,
        validated=[],
        allow_equal_tick_schema_migration=True,
    )

    assert migrated.generation.generation_uuid != legacy.generation_uuid
    assert migrated.generation.tick == legacy.tick
    assert migrated.seal_certificate()["state_revision"] == 1
    assert CAUSAL_GENERATION_RECEIPT in migrated.generation.required_files


def _cold_tree_snapshot(root: Path) -> dict[str, tuple]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        digest = (
            hashlib.sha256(path.read_bytes()).hexdigest()
            if path.is_file()
            else None
        )
        snapshot[relative] = (
            info.st_mode,
            info.st_size,
            info.st_mtime_ns,
            digest,
        )
    return snapshot


def _logical_generation_files(
    generation: LoadedGeneration,
) -> dict[str, bytes]:
    return {
        relative: (
            json.dumps(
                generation.payload(relative),
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ).encode("utf-8") + b"\n"
            if relative.endswith(".json")
            else generation.payload(relative)
        )
        for relative in generation.required_files
    }


def _bootable_save(stage: Path, admission) -> int:
    tick = 9
    core = _engine_envelope(
        timestamp="2026-07-28T01:02:03Z",
        current_activity={"kind": "LISTENING"},
    )
    core["data"]["state_file_ticks"] = {"guala_core.json": tick}
    with admission.open_text(stage / "guala_core.json") as handle:
        handle.write(json.dumps(core))
    with admission.open_text(stage / ".sleeping") as handle:
        handle.write(json.dumps({
            "sleep_tick": tick,
            "sleep_ts": 1000.0,
        }))
    with admission.open_binary(stage / "organism.bin") as handle:
        handle.write(b"exact-organism")
    return tick


def _resign_certificate(certificate: dict) -> bytes:
    unsigned = {
        key: value
        for key, value in certificate.items()
        if key != "seal_hmac_sha256"
    }
    certificate["seal_hmac_sha256"] = hmac.new(
        HMAC_KEY,
        (
            json.dumps(
                unsigned,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ) + "\n"
        ).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        json.dumps(
            certificate,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"
    ).encode("utf-8")


@pytest.mark.parametrize(
    "residue",
    ("building", "missing-lock", "third", "equal-order", "newer"),
)
def test_duplicate_read_only_audit_never_mutates_cold_residue(
    tmp_path: Path,
    residue: str,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    first = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=[],
    )
    if residue == "missing-lock":
        (root / LOCK_NAME).unlink()
    elif residue == "building":
        building = (
            root
            / GENERATIONS_DIRECTORY
            / ".building-adversarial-residue"
        )
        building.mkdir()
        (building / "untouched").write_bytes(b"do-not-retire")
    else:
        raw_store = ImmutableGenerationStore(
            root,
            identity=IDENTITY,
            required_files=first.generation.required_files,
        )
        raw_store.commit(
            tick=(
                1
                if residue == "third"
                else 9 if residue == "equal-order" else 10
            ),
            files=_logical_generation_files(first.generation),
            publish_current=False,
        )
        if residue == "third":
            raw_store.commit(
                tick=2,
                files=_logical_generation_files(first.generation),
                publish_current=False,
            )
    before = _cold_tree_snapshot(root)
    s3.fail_on_put = True
    s3.fail_on_delete = True

    with pytest.raises(Exception):
        _commit(
            root=root,
            s3=s3,
            marker="same",
            tick=9,
            nonce=SECOND_NONCE,
            validated=[],
        )

    assert _cold_tree_snapshot(root) == before


def test_equal_current_order_sealed_noncurrent_fails_read_only_without_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    first = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=[],
    )
    raw_store = ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=first.generation.required_files,
        content_addressed=True,
    )
    candidate = raw_store.commit(
        tick=first.generation.tick,
        files={
            relative: first.generation.stored_bytes(relative)
            for relative in first.generation.required_files
        },
        publish_current=False,
    )
    current_receipt = verified_causal_generation_receipt(first.generation)
    candidate_receipt = verified_causal_generation_receipt(candidate)
    assert current_receipt is not None
    assert candidate_receipt is not None
    assert (
        candidate.tick,
        candidate_receipt.state_revision,
    ) == (
        first.generation.tick,
        current_receipt.state_revision,
    )
    authority = AuthoritativeColdGenerationStore(
        root,
        identity=IDENTITY,
        required_files=None,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=16,
        max_dynamic_path_bytes=1024,
        pre_publish_validator=lambda generation: True,
        generation_revision=causal_generation_revision,
    )
    before = _cold_tree_snapshot(root)

    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="predecessor is not strictly older than CURRENT",
    ):
        with authority.exclusive_read_only_transaction(
            require_predecessor=False,
        ):
            raise AssertionError("equal-order audit admitted its callback")

    assert _cold_tree_snapshot(root) == before


def test_forged_receipt_fails_read_only_audit_without_tree_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    first = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=[],
    )
    forged_files = _logical_generation_files(first.generation)
    forged_receipt = json.loads(
        forged_files[CAUSAL_GENERATION_RECEIPT]
    )
    forged_receipt["causal_state_sha256"] = "0" * 64
    forged_files[CAUSAL_GENERATION_RECEIPT] = (
        json.dumps(
            forged_receipt,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8") + b"\n"
    )
    raw_store = ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=first.generation.required_files,
    )
    raw_store.commit(
        tick=8,
        files=forged_files,
        publish_current=False,
    )
    authority = AuthoritativeColdGenerationStore(
        root,
        identity=IDENTITY,
        required_files=None,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=16,
        max_dynamic_path_bytes=1024,
        pre_publish_validator=lambda generation: True,
        generation_revision=causal_generation_revision,
    )
    before = _cold_tree_snapshot(root)

    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="causal generation receipt differs from its exact projected state",
    ):
        with authority.exclusive_read_only_transaction(
            require_predecessor=False,
        ):
            raise AssertionError("forged receipt audit admitted its callback")

    assert _cold_tree_snapshot(root) == before


def test_failed_reaudit_cannot_expose_prior_authority_from_store(
    tmp_path: Path,
) -> None:
    root = tmp_path / "store"
    s3 = _FakeS3()
    first = _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=[],
    )
    authority = AuthoritativeColdGenerationStore(
        root,
        identity=IDENTITY,
        required_files=None,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=16,
        max_dynamic_path_bytes=1024,
        pre_publish_validator=lambda generation: True,
        generation_revision=verified_causal_generation_receipt,
    )
    audited = authority.inspect_sealed_boot(require_predecessor=False)
    assert audited.current_authority == verified_causal_generation_receipt(
        first.generation
    )

    organism_record = next(
        record
        for record in audited.current.recovery_certificate()[
            "required_files"
        ]
        if record["relative_path"] == "organism.bin"
    )
    organism_digest = organism_record["chunks"][0]["sha256"]
    payload = (
        audited.current._content_chunks_root
        / organism_digest[:2]
        / organism_digest
    )
    payload.chmod(0o644)
    payload.write_bytes(b"corrupt-after-successful-audit")
    payload.chmod(0o444)

    with pytest.raises(
        AuthoritativeColdGenerationError,
        match="verification failed|integrity",
    ):
        authority.inspect_sealed_boot(require_predecessor=False)
    with pytest.raises(Exception):
        verified_causal_generation_receipt(audited.current)
    assert not hasattr(authority, "audited_generation_authority")


@pytest.mark.parametrize(
    ("has_current", "extra_generations", "capacity"),
    (
        (True, 4, 4),
        (False, 2, 1),
    ),
)
def test_sealed_boot_overcount_stops_before_authority_and_never_mutates(
    tmp_path: Path,
    has_current: bool,
    extra_generations: int,
    capacity: int,
) -> None:
    root = tmp_path / "store"
    if has_current:
        s3 = _FakeS3()
        first = _commit(
            root=root,
            s3=s3,
            marker="same",
            tick=9,
            nonce=FIRST_NONCE,
            validated=[],
        )
        raw_store = ImmutableGenerationStore(
            root,
            identity=IDENTITY,
            required_files=first.generation.required_files,
        )
        files = _logical_generation_files(first.generation)
        for tick in range(10, 10 + extra_generations):
            raw_store.commit(
                tick=tick,
                files=files,
                publish_current=False,
            )
    else:
        raw_store = ImmutableGenerationStore(
            root,
            identity=IDENTITY,
            required_files=("core.json", "organism.bin"),
        )
        for tick in range(extra_generations):
            raw_store.commit(
                tick=tick,
                files={
                    "core.json": json.dumps({"tick": tick}).encode("utf-8"),
                    "organism.bin": f"organism-{tick}".encode("utf-8"),
                },
                publish_current=False,
            )

    authority_calls = 0

    def forbidden_authority(_generation):
        nonlocal authority_calls
        authority_calls += 1
        raise AssertionError(
            "over-count sealed boot reached causal authority evaluation"
        )

    authority = AuthoritativeColdGenerationStore(
        root,
        identity=IDENTITY,
        required_files=None,
        max_encoded_generation_bytes=64 * 1024,
        max_dynamic_required_files=16,
        max_dynamic_path_bytes=1024,
        pre_publish_validator=lambda generation: True,
        generation_revision=forbidden_authority,
    )
    before = _cold_tree_snapshot(root)

    with pytest.raises(
        AuthoritativeColdGenerationError,
        match=(
            "sealed-boot generation path count exceeds bounded recovery "
            f"capacity {capacity}"
        ),
    ):
        authority.inspect_sealed_boot(require_predecessor=False)

    assert authority_calls == 0
    assert _cold_tree_snapshot(root) == before


class _AdversarialListingS3(_FakeS3):
    def __init__(self, mode: str) -> None:
        super().__init__()
        self.mode = mode
        self.reuse_listing = False
        self.page = 0

    def list_objects_v2(
        self,
        *,
        Bucket,
        Prefix,
        ContinuationToken=None,
    ):
        if not self.reuse_listing:
            return super().list_objects_v2(
                Bucket=Bucket,
                Prefix=Prefix,
                ContinuationToken=ContinuationToken,
            )
        keys = sorted(
            key
            for bucket, key in self.objects
            if bucket == Bucket and key.startswith(Prefix)
        )
        if self.mode == "duplicate":
            return {
                "Contents": [{"Key": keys[0]}, {"Key": keys[0]}],
                "IsTruncated": False,
            }
        if self.mode == "cycle":
            self.page += 1
            return {
                "Contents": [{"Key": keys[min(self.page - 1, len(keys) - 1)]}],
                "IsTruncated": True,
                "NextContinuationToken": "cycle",
            }
        if self.mode == "nonprogress":
            return {
                "Contents": [],
                "IsTruncated": True,
                "NextContinuationToken": "next",
            }
        if self.mode == "flood":
            return {
                "Contents": [{
                    "Key": f"{Prefix}unexpected-{self.page:08d}",
                }],
                "IsTruncated": True,
                "NextContinuationToken": str(self.page + 1),
            }
        raise AssertionError(self.mode)


@pytest.mark.parametrize(
    ("mode", "message"),
    (
        ("duplicate", "duplicate key"),
        ("cycle", "cyclic"),
        ("nonprogress", "no key progress"),
        ("flood", "unexpected key"),
    ),
)
def test_duplicate_remote_listing_is_bounded_and_fail_closed(
    tmp_path: Path,
    mode: str,
    message: str,
) -> None:
    root = tmp_path / "store"
    s3 = _AdversarialListingS3(mode)
    _commit(
        root=root,
        s3=s3,
        marker="same",
        tick=9,
        nonce=FIRST_NONCE,
        validated=[],
    )
    remote_before = dict(s3.objects)
    s3.reuse_listing = True
    s3.fail_on_put = True
    s3.fail_on_delete = True

    with pytest.raises(
        RemoteGenerationVerificationError,
        match=message,
    ):
        _commit(
            root=root,
            s3=s3,
            marker="same",
            tick=9,
            nonce=SECOND_NONCE,
            validated=[],
        )

    assert s3.objects == remote_before
    assert s3.delete_calls == 0


@pytest.mark.parametrize(
    ("tamper", "message"),
    (
        (
            "receipt",
            "causal generation receipt differs from its exact projected state",
        ),
        (
            "state_revision",
            "signed deployment seal state_revision differs from verified "
            "CURRENT causal receipt",
        ),
        (
            "causal_state_sha256",
            "signed deployment seal causal_state_sha256 differs from verified "
            "CURRENT causal receipt",
        ),
        (
            "operational_metadata_sha256",
            "signed deployment seal operational_metadata_sha256 differs from "
            "verified CURRENT causal receipt",
        ),
        (
            "attempt_operational_metadata_sha256",
            "signed deployment seal attempt_operational_metadata_sha256 "
            "differs from verified CURRENT causal receipt",
        ),
    ),
)
def test_real_boot_rejects_forged_receipt_and_signed_receipt_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
    message: str,
) -> None:
    from dsf_ai_service import app as app_module

    root = tmp_path / "store"
    s3 = _FakeS3()
    first = _commit_callback(
        root=root,
        s3=s3,
        save=_bootable_save,
        nonce=FIRST_NONCE,
    )
    sealed_generation = first.generation
    immutable_seal_path = (
        root
        / "deployment-seals"
        / f"{sealed_generation.generation_uuid}.json"
    )
    certificate = json.loads(immutable_seal_path.read_bytes())

    if tamper == "receipt":
        forged_files = {
            relative: first.generation.stored_bytes(relative)
            for relative in first.generation.required_files
        }
        forged_receipt = json.loads(
            forged_files[CAUSAL_GENERATION_RECEIPT]
        )
        forged_receipt["causal_state_sha256"] = "0" * 64
        forged_files[CAUSAL_GENERATION_RECEIPT] = (
            json.dumps(
                forged_receipt,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ).encode("utf-8") + b"\n"
        )
        raw_store = ImmutableGenerationStore(
            root,
            identity=IDENTITY,
            required_files=first.generation.required_files,
            content_addressed=True,
        )
        sealed_generation = raw_store.commit(
            tick=first.generation.tick,
            files=forged_files,
            publish_current=True,
        )
        old_prefix = certificate["versioned_prefix"]
        new_prefix = (
            old_prefix.rsplit("/", 1)[0]
            + "/"
            + sealed_generation.generation_uuid
        )
        certificate["generation_uuid"] = sealed_generation.generation_uuid
        certificate["manifest_sha256"] = sealed_generation.manifest_sha256
        certificate["recovery_certificate_sha256"] = hashlib.sha256(
            sealed_generation.recovery_certificate_bytes()
        ).hexdigest()
        certificate["versioned_prefix"] = new_prefix
        for record in certificate["objects"]:
            if record["key"].startswith(old_prefix + "/"):
                record["key"] = (
                    new_prefix + record["key"][len(old_prefix):]
                )
        certificate["objects"].sort(
            key=lambda record: record["key"]
        )
        certificate["state_revision"] = forged_receipt["state_revision"]
        certificate["causal_state_sha256"] = (
            forged_receipt["causal_state_sha256"]
        )
        certificate["operational_metadata_sha256"] = (
            forged_receipt["operational_metadata_sha256"]
        )
        certificate["attempt_operational_metadata_sha256"] = (
            forged_receipt["operational_metadata_sha256"]
        )
        immutable_seal_path = (
            root
            / "deployment-seals"
            / f"{sealed_generation.generation_uuid}.json"
        )
    elif tamper == "state_revision":
        certificate[tamper] += 1
    else:
        certificate[tamper] = (
            "f" * 64
            if certificate[tamper] != "f" * 64
            else "e" * 64
        )

    immutable_seal_path.write_bytes(_resign_certificate(certificate))
    immutable_seal_path.chmod(0o444)
    before = _cold_tree_snapshot(root)
    monkeypatch.setattr(app_module, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(app_module, "_loaded_generation", None)
    monkeypatch.setattr(app_module, "_deployment_baseline_generation", None)
    monkeypatch.setattr(app_module, "_live_recovery_store", None)
    monkeypatch.setattr(app_module, "_authoritative_cold_store", None)
    monkeypatch.setattr(app_module, "GENERATION_STORE_ROOT", str(root))
    monkeypatch.setattr(app_module, "STATE_DIR", str(tmp_path / "active"))
    monkeypatch.setattr(
        app_module,
        "LIVE_RECOVERY_STORE_ROOT",
        str(tmp_path / "live-recovery"),
    )
    monkeypatch.setattr(app_module, "_deploy_hmac_key", lambda: HMAC_KEY)
    monkeypatch.setattr(
        app_module,
        "_authoritative_cold_limits",
        lambda: (64 * 1024, 16, 1024),
    )
    monkeypatch.setattr(
        app_module,
        "_authoritative_physical_storage_config",
        lambda: (
            16 * 1024 * 1024,
            str(tmp_path),
            SimpleNamespace(
                knowledge_gap_ledger_bytes=64 * 1024,
                max_live_recovery_generation_bytes=64 * 1024,
                owner_record_bytes=4096,
            ),
        ),
    )
    monkeypatch.setattr(
        app_module,
        "_validate_runtime_generation_cold_restore",
        lambda generation: True,
    )

    with pytest.raises(RuntimeError, match=message):
        app_module._prepare_generation_boot()

    assert not (tmp_path / "active").exists()
    assert _cold_tree_snapshot(root) == before


def test_reused_current_readiness_accepts_authenticated_nonempty_probe_nonce(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import boto3

    from dsf_ai_service import app as app_module
    from dsf_ai_service.substrate import deployment_generation

    root = tmp_path / "store"
    active = tmp_path / "active"
    live_recovery = tmp_path / "live-recovery"
    s3 = _FakeS3()
    first = _commit_callback(
        root=root,
        s3=s3,
        save=_bootable_save,
        nonce=FIRST_NONCE,
    )
    reused = _commit_callback(
        root=root,
        s3=s3,
        save=_bootable_save,
        nonce=SECOND_NONCE,
    )
    assert reused.generation.generation_uuid == first.generation.generation_uuid
    ring_events = active / "ring_events"
    ring_events.mkdir(parents=True)
    (ring_events / "events.log").write_bytes(b"retired-operational-ring")

    exact_executor_module = importlib.import_module(
        "dsf_ai_service.glew_runtime.exact_field_executor"
    )
    exact_owner = SimpleNamespace(assert_healthy=lambda: None)
    lifecycle = app_module._DeploymentLifecycle()
    actual_git = "1" * 40
    actual_task = "dsf-ai:41"
    actual_image = "sha256:" + "3" * 64

    monkeypatch.setattr(app_module, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(app_module, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", "control-secret")
    monkeypatch.setattr(app_module, "_init_complete", True)
    monkeypatch.setattr(app_module, "_init_error", None)
    monkeypatch.setattr(app_module, "_boot_halted", None)
    monkeypatch.setattr(app_module, "_loaded_generation", None)
    monkeypatch.setattr(app_module, "_deployment_baseline_generation", None)
    monkeypatch.setattr(app_module, "_live_recovery_store", None)
    monkeypatch.setattr(app_module, "_authoritative_cold_store", None)
    monkeypatch.setattr(
        app_module,
        "GENERATION_STORE_ROOT",
        str(root),
    )
    monkeypatch.setattr(app_module, "STATE_DIR", str(active))
    monkeypatch.setattr(
        app_module,
        "LIVE_RECOVERY_STORE_ROOT",
        str(live_recovery),
    )
    monkeypatch.setattr(app_module, "_deploy_hmac_key", lambda: HMAC_KEY)
    monkeypatch.setattr(
        app_module,
        "_authoritative_cold_limits",
        lambda: (64 * 1024, 16, 1024),
    )
    monkeypatch.setattr(
        app_module,
        "_validate_runtime_generation_cold_restore",
        lambda generation: True,
    )
    monkeypatch.setattr(
        app_module,
        "_authoritative_physical_storage_config",
        lambda: (
            16 * 1024 * 1024,
            str(tmp_path),
            SimpleNamespace(
                knowledge_gap_ledger_bytes=64 * 1024,
                max_live_recovery_generation_bytes=64 * 1024,
                owner_record_bytes=4096,
            ),
        ),
    )
    monkeypatch.setattr(
        app_module.Guala,
        "HOT_SAVE_MANIFEST_FILES",
        ("guala_core.json",),
    )
    monkeypatch.setattr(
        deployment_generation,
        "reconcile_remote_generation_prefixes",
        lambda **_kwargs: (),
    )
    verified_receipt_calls: dict[str, int] = {}
    real_verified_receipt = (
        deployment_generation.verified_causal_generation_receipt
    )

    def count_verified_receipt(generation):
        verified_receipt_calls[generation.generation_uuid] = (
            verified_receipt_calls.get(generation.generation_uuid, 0) + 1
        )
        return real_verified_receipt(generation)

    monkeypatch.setattr(
        deployment_generation,
        "verified_causal_generation_receipt",
        count_verified_receipt,
    )
    monkeypatch.setattr(boto3, "client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(app_module, "_read_build_git_sha", lambda: actual_git)
    monkeypatch.setattr(
        app_module,
        "_ecs_task_runtime_identity",
        lambda: {
            "task_definition": actual_task,
            "image_digest": actual_image,
        },
    )
    monkeypatch.setattr(
        exact_executor_module,
        "exact_field_executor",
        lambda: exact_owner,
    )
    monkeypatch.setattr(
        app_module,
        "_verified_storage_cutover_status",
        lambda: {
            "schema": "guala.production.storage_cutover.v1",
            "retired_flat_full_copy_producer": True,
        },
    )
    monkeypatch.setenv("DEPLOY_EXPECTED_GIT_SHA", actual_git)
    monkeypatch.setenv("DEPLOY_EXPECTED_TASK_DEFINITION", actual_task)
    monkeypatch.setenv("DEPLOY_EXPECTED_IMAGE_DIGEST", actual_image)

    booted = app_module._prepare_generation_boot()
    assert booted is app_module._loaded_generation
    assert booted.generation_uuid == reused.generation.generation_uuid
    assert booted.manifest_sha256 == reused.generation.manifest_sha256
    assert verified_receipt_calls == {
        reused.generation.generation_uuid: 1,
    }
    assert not ring_events.exists()
    monkeypatch.setattr(
        app_module,
        "_guala",
        SimpleNamespace(
            _guala_identity=IDENTITY,
            tick=booted.tick,
            _native_materialized_fabric_state=b"native",
            _native_materialized_fabric_reference=object(),
        ),
    )
    monkeypatch.setattr(
        app_module,
        "_native_joint_fractal_readiness",
        lambda: {"available": True},
    )

    async def readiness(nonce: str):
        transport = httpx.ASGITransport(
            app=app_module.app,
            raise_app_exceptions=False,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get(
                "/internal/deployment/readiness",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": nonce,
                },
            )

    accepted = asyncio.run(readiness(SECOND_NONCE.decode("ascii")))
    old = asyncio.run(readiness(FIRST_NONCE.decode("ascii")))
    wrong = asyncio.run(readiness("wrong-retry-nonce-0001"))

    assert accepted.status_code == 200
    assert accepted.json()["generation"] == reused.generation.generation_uuid
    assert old.status_code == 200
    assert wrong.status_code == 200
