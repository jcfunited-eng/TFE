"""Production custody for code-only deployment at an unchanged lived tick."""

from __future__ import annotations

import contextlib
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import boto3
import pytest

from dsf_ai_service import app as app_module
from dsf_ai_service.substrate import deployment_generation
from dsf_ai_service.substrate.deployment_generation import (
    BoundedStageAdmission,
    CAUSAL_GENERATION_RECEIPT,
)
from dsf_ai_service.substrate.generation_content_delta import (
    DETACHED_CAUSAL_MUTATION_MEMBER_PATH,
    GenerationContentDeltaError,
    exact_current_generation_receipt_paths,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.whole_organism_persistence import (
    WHOLE_ORGANISM_STATE_CONTRACT,
    WholeOrganismPersistenceError,
)


IDENTITY = "equal-tick-production-custody"
TICK = 73
DETACHED = DETACHED_CAUSAL_MUTATION_MEMBER_PATH
OWNER_RECEIPT = "receipts/owner_state/owner.json"
CORE = "guala_core.json"
IDENTITY_FILE = "guala_identity.json"
KEY = b"equal-tick-production-custody-key"


def _core() -> bytes:
    organism_state = {"owners": {"organism": {"phase": "resting"}}}
    organism_bytes = json.dumps(
        organism_state,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return json.dumps(
        {
            "data": {
                "continuity_contract": WHOLE_ORGANISM_STATE_CONTRACT,
                "organism_state": organism_state,
                "organism_state_bytes": len(organism_bytes),
                "organism_state_sha256": hashlib.sha256(
                    organism_bytes
                ).hexdigest(),
                "state_file_ticks": {CORE: TICK},
                "tick": TICK,
            },
            "guala_identity": IDENTITY,
            "saved_at_tick": TICK,
            "saved_at_timestamp": "2026-07-29T20:00:00Z",
            "schema_version": "physical-runtime-v1",
        },
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _baseline(tmp_path: Path):
    store = ImmutableGenerationStore(
        tmp_path / "sealed",
        identity=IDENTITY,
        required_files=(
            CAUSAL_GENERATION_RECEIPT,
            CORE,
            DETACHED,
            IDENTITY_FILE,
            OWNER_RECEIPT,
        ),
        content_addressed=True,
    )
    return store.commit(
        tick=TICK,
        files={
            CAUSAL_GENERATION_RECEIPT: b'{"causal":"sealed"}',
            CORE: _core(),
            DETACHED: b'{"mutation":"sealed"}',
            IDENTITY_FILE: b'{"identity":"equal-tick-production-custody"}',
            OWNER_RECEIPT: b'{"owner":"sealed"}',
        },
    )


def _write_runtime_stage(stage: Path, admission) -> int:
    with admission.open_binary(
        stage / CORE,
        expected_size=len(_core()),
    ) as stream:
        stream.write(_core())
    identity = b'{"identity":"equal-tick-production-custody"}'
    with admission.open_binary(
        stage / IDENTITY_FILE,
        expected_size=len(identity),
    ) as stream:
        stream.write(identity)
    return TICK


def test_equal_tick_receipt_census_restores_only_baseline_authority(
    tmp_path: Path,
) -> None:
    baseline = _baseline(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    admission = BoundedStageAdmission(
        stage,
        max_total_bytes=1024 * 1024,
        max_required_files=16,
        max_path_bytes=4096,
    )
    _write_runtime_stage(stage, admission)

    receipt_paths = exact_current_generation_receipt_paths(
        baseline,
        candidate_stage_root=stage,
        candidate_relative_paths=admission.admitted_relative_paths(),
        candidate_tick=TICK,
        rebuilt_member_paths=(CAUSAL_GENERATION_RECEIPT,),
    )

    assert receipt_paths == (DETACHED, OWNER_RECEIPT)


def test_equal_tick_receipt_census_rejects_added_or_missing_causal_paths(
    tmp_path: Path,
) -> None:
    baseline = _baseline(tmp_path)
    added = tmp_path / "added"
    added.mkdir()
    admission = BoundedStageAdmission(
        added,
        max_total_bytes=1024 * 1024,
        max_required_files=16,
        max_path_bytes=4096,
    )
    _write_runtime_stage(added, admission)
    with admission.open_binary(added / "unexpected.json") as stream:
        stream.write(b"{}")

    with pytest.raises(
        GenerationContentDeltaError,
        match="adds paths outside",
    ):
        exact_current_generation_receipt_paths(
            baseline,
            candidate_stage_root=added,
            candidate_relative_paths=admission.admitted_relative_paths(),
            candidate_tick=TICK,
            rebuilt_member_paths=(CAUSAL_GENERATION_RECEIPT,),
        )

    missing = tmp_path / "missing"
    missing.mkdir()
    missing_admission = BoundedStageAdmission(
        missing,
        max_total_bytes=1024 * 1024,
        max_required_files=16,
        max_path_bytes=4096,
    )
    with missing_admission.open_binary(
        missing / IDENTITY_FILE,
        expected_size=len(
            b'{"identity":"equal-tick-production-custody"}'
        ),
    ) as stream:
        stream.write(
            b'{"identity":"equal-tick-production-custody"}'
        )

    with pytest.raises(
        GenerationContentDeltaError,
        match="omitted causal baseline paths",
    ):
        exact_current_generation_receipt_paths(
            baseline,
            candidate_stage_root=missing,
            candidate_relative_paths=(
                missing_admission.admitted_relative_paths()
            ),
            candidate_tick=TICK,
            rebuilt_member_paths=(CAUSAL_GENERATION_RECEIPT,),
        )


def test_app_seal_stages_and_validates_one_whole_organism(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _baseline(tmp_path)
    staged_paths: set[str] = set()
    finalized: list[tuple[int, dict]] = []

    class Guala:
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
            raise AssertionError(
                "successful equal-tick reuse must finalize"
            )

    overlay = SimpleNamespace(
        generation_uuid="22222222-2222-4222-8222-222222222222",
        identity=IDENTITY,
        manifest_sha256="2" * 64,
        tick=TICK,
    )

    class LiveRecovery:
        def rebase_after_deployment_seal(self, *, baseline, tick, files):
            assert baseline is globals_baseline
            assert tick == TICK
            assert tuple(files) == (CORE,)
            return overlay

    globals_baseline = baseline
    certificate = {
        "generation_uuid": baseline.generation_uuid,
        "identity": baseline.identity,
        "manifest_sha256": baseline.manifest_sha256,
        "tick": baseline.tick,
        "seal_hmac_sha256": "3" * 64,
    }

    def commit_upload(**kwargs):
        stage = tmp_path / "candidate"
        stage.mkdir()
        admission = BoundedStageAdmission(
            stage,
            max_total_bytes=1024 * 1024,
            max_required_files=16,
            max_path_bytes=4096,
        )
        assert kwargs["save_callback"](stage, admission) == TICK
        staged_paths.update(admission.admitted_relative_paths())
        assert staged_paths == {CORE, IDENTITY_FILE}
        assert not (stage / "receipts").exists()
        assert not (stage / DETACHED).exists()
        assert not (stage / CAUSAL_GENERATION_RECEIPT).exists()
        validator = kwargs["cold_restore_validator"]
        assert validator(baseline) is True

        tampered = json.loads(_core())
        tampered["data"]["organism_state"]["owners"]["organism"][
            "phase"
        ] = "changed-after-freeze"
        tampered_bytes = json.dumps(
            tampered,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        tampered_candidate = SimpleNamespace(
            identity=IDENTITY,
            tick=TICK,
            stored_bytes=lambda relative_path: (
                tampered_bytes
                if relative_path == CORE
                else baseline.stored_bytes(relative_path)
            ),
        )
        with pytest.raises(
            WholeOrganismPersistenceError,
            match="whole-organism state integrity changed",
        ):
            validator(tampered_candidate)
        return SimpleNamespace(
            generation=baseline,
            version_aware_remote_reconciliation=False,
            read_only_remote_reuse_verified=True,
            remote_retained_generation_uuids=(
                baseline.generation_uuid,
            ),
            remote_retired_generation_uuids=(),
            seal_certificate_bytes=lambda: b"fresh-attempt-seal",
        )

    monkeypatch.setattr(app_module, "_guala", Guala())
    monkeypatch.setattr(
        app_module,
        "_deployment_baseline_generation",
        baseline,
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
        LiveRecovery(),
    )
    monkeypatch.setattr(
        app_module,
        "_write_runtime_generation_stage",
        _write_runtime_stage,
    )
    monkeypatch.setattr(
        app_module,
        "_validate_runtime_generation_cold_restore",
        lambda generation: generation is baseline,
    )
    monkeypatch.setattr(
        app_module,
        "_authoritative_cold_limits",
        lambda: (1024 * 1024, 16, 4096),
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
        app_module,
        "_deploy_hmac_key",
        lambda: KEY,
    )
    monkeypatch.setattr(
        app_module,
        "GENERATION_STORE_ROOT",
        str(tmp_path / "sealed"),
    )
    monkeypatch.setattr(app_module, "STATE_DIR", str(tmp_path / "active"))
    monkeypatch.setattr(
        app_module.Guala,
        "HOT_SAVE_MANIFEST_FILES",
        (CORE,),
    )
    monkeypatch.setattr(
        deployment_generation,
        "stage_authoritative_commit_upload",
        commit_upload,
    )
    monkeypatch.setattr(
        deployment_generation,
        "verify_deployment_seal",
        lambda *_args, **_kwargs: dict(certificate),
    )
    monkeypatch.setattr(
        boto3,
        "client",
        lambda *_args, **_kwargs: object(),
    )

    receipt = app_module._seal_runtime_generation("equal-tick-nonce")

    assert receipt["generation_uuid"] == baseline.generation_uuid
    assert receipt["tick"] == TICK
    assert finalized == [(TICK, {CORE: TICK})]
    assert staged_paths == {CORE, IDENTITY_FILE}
