"""Exact management-only custody for an unchanged deployment generation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from dsf_ai_service.substrate.deployment_generation import (
    BoundedStageAdmission,
    CAUSAL_GENERATION_RECEIPT,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.live_recovery_generation import (
    LiveRecoveryError,
    LiveRecoveryGenerationStore,
    verify_predecessor_current,
    verify_redundant_predecessor_current,
)
from tools import prove_equal_tick_deployment_reuse as control


IDENTITY = "equal-tick-management-custody"
TICK = 41
KEY = b"equal-tick-management-custody-key-material"
NONCE = "equal-tick-management-custody-nonce"
CORE = "guala_core.json"
RECEIPT = CAUSAL_GENERATION_RECEIPT


def _write(path: Path, body: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def _baseline(tmp_path: Path):
    source = tmp_path / "baseline-source"
    files = {
        CORE: _write(
            source / CORE,
            json.dumps(
                {
                    "data": {"state_file_ticks": {CORE: TICK}},
                    "guala_identity": IDENTITY,
                    "saved_at_tick": TICK,
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8"),
        ),
        RECEIPT: _write(
            source / RECEIPT,
            b'{"causal":"unchanged"}',
        ),
    }
    return ImmutableGenerationStore(
        tmp_path / "sealed",
        identity=IDENTITY,
        required_files=tuple(files),
        content_addressed=True,
    ).commit(tick=TICK, files=files)


def _redundant_overlay(tmp_path: Path, baseline):
    source = tmp_path / "hot-source"
    core = _write(source / CORE, baseline.stored_bytes(CORE))
    manager = LiveRecoveryGenerationStore(
        tmp_path / "sealed-live-recovery",
        baseline=baseline,
        hot_files=(CORE,),
        hmac_key=KEY,
    )
    return manager.commit_hot_state(
        tick=baseline.tick,
        files={CORE: core},
    )


def _distinct_overlay(tmp_path: Path, baseline):
    source = tmp_path / "distinct-hot-source"
    core = _write(
        source / CORE,
        json.dumps(
            {
                "data": {
                    "felt_change": "already-lived",
                    "state_file_ticks": {CORE: TICK},
                },
                "guala_identity": IDENTITY,
                "saved_at_tick": TICK,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
    )
    manager = LiveRecoveryGenerationStore(
        tmp_path / "sealed-live-recovery",
        baseline=baseline,
        hot_files=(CORE,),
        hmac_key=KEY,
    )
    return manager.commit_hot_state(
        tick=baseline.tick,
        files={CORE: core},
    )


def test_read_only_overlay_proof_uses_exact_lineage_and_payload(
    tmp_path: Path,
) -> None:
    baseline = _baseline(tmp_path)
    overlay = _redundant_overlay(tmp_path, baseline)

    verified = verify_redundant_predecessor_current(
        tmp_path / "sealed-live-recovery",
        baseline=baseline,
        hmac_key=KEY,
        expected_generation_uuid=overlay.generation_uuid,
        expected_manifest_sha256=overlay.manifest_sha256,
        expected_tick=overlay.tick,
    )

    assert verified.recovery_certificate_bytes() == (
        overlay.recovery_certificate_bytes()
    )
    with pytest.raises(
        LiveRecoveryError,
        match="differs from expected manifest_sha256",
    ):
        verify_redundant_predecessor_current(
            tmp_path / "sealed-live-recovery",
            baseline=baseline,
            hmac_key=KEY,
            expected_generation_uuid=overlay.generation_uuid,
            expected_manifest_sha256="0" * 64,
            expected_tick=overlay.tick,
        )


def test_historical_migration_source_is_materialized_without_new_runtime_boot(
    tmp_path: Path,
) -> None:
    baseline = _baseline(tmp_path)

    assert control._isolated_frozen_source_custody_validator(
        baseline
    ) is True


def test_management_control_reuses_current_without_app_or_owner_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _baseline(tmp_path)
    overlay = _redundant_overlay(tmp_path, baseline)
    staged: dict[str, bytes] = {}
    retained_predecessor = "11111111-1111-4111-8111-111111111111"
    seal = {
        "causal_state_sha256": "2" * 64,
        "seal_hmac_sha256": "3" * 64,
        "state_revision": 9,
    }

    def exact_reuse(**kwargs):
        stage = tmp_path / "control-stage"
        stage.mkdir()
        admission = BoundedStageAdmission(
            stage,
            max_total_bytes=1024 * 1024,
            max_required_files=16,
            max_path_bytes=4096,
        )
        assert kwargs["save_callback"](stage, admission) == TICK
        assert admission.admitted_relative_paths() == (CORE,)
        staged[CORE] = (stage / CORE).read_bytes()
        assert not (stage / RECEIPT).exists()
        assert kwargs["cold_restore_validator"](baseline) is True
        return SimpleNamespace(
            generation=baseline,
            version_aware_remote_reconciliation=False,
            read_only_remote_reuse_verified=True,
            remote_retained_generation_uuids=(
                retained_predecessor,
                baseline.generation_uuid,
            ),
            seal_certificate_bytes=lambda: b"nonce-bound-attempt-seal",
        )

    monkeypatch.setattr(
        control,
        "stage_authoritative_commit_upload",
        exact_reuse,
    )
    monkeypatch.setattr(
        control,
        "verify_deployment_seal",
        lambda certificate, **kwargs: (
            seal
            if (
                certificate == b"nonce-bound-attempt-seal"
                and kwargs["expected_nonce"] == NONCE
            )
            else (_ for _ in ()).throw(AssertionError("wrong seal"))
        ),
    )

    receipt = control.prove_equal_tick_deployment_reuse(
        store_root=tmp_path / "sealed",
        live_recovery_root=tmp_path / "sealed-live-recovery",
        expected_generation_uuid=baseline.generation_uuid,
        expected_manifest_sha256=baseline.manifest_sha256,
        expected_identity=baseline.identity,
        expected_tick=baseline.tick,
        expected_active_recovery_generation=overlay.generation_uuid,
        expected_active_recovery_manifest_sha256=(
            overlay.manifest_sha256
        ),
        expected_active_recovery_tick=overlay.tick,
        bucket="test-bucket",
        prefix="guala/generations",
        nonce=NONCE,
        max_generation_bytes=1024 * 1024,
        max_required_files=16,
        max_path_bytes=4096,
        physical_byte_ceiling=10 * 1024 * 1024,
        physical_byte_scope=tmp_path,
        s3_client=object(),
        hmac_key=KEY,
        cold_restore_validator=lambda generation: generation is baseline,
    )

    assert staged == {CORE: baseline.stored_bytes(CORE)}
    assert receipt == {
        "active_recovery_generation": overlay.generation_uuid,
        "active_recovery_manifest_sha256": overlay.manifest_sha256,
        "active_recovery_tick": TICK,
        "attempt_seal_hmac_sha256": "3" * 64,
        "causal_state_sha256": "2" * 64,
        "deploy_nonce_sha256": hashlib.sha256(
            NONCE.encode("utf-8")
        ).hexdigest(),
        "deployment_baseline_generation": baseline.generation_uuid,
        "deployment_baseline_manifest_sha256": baseline.manifest_sha256,
        "deployment_baseline_tick": TICK,
        "generation_uuid": baseline.generation_uuid,
        "identity": IDENTITY,
        "manifest_sha256": baseline.manifest_sha256,
        "pre_seal_active_recovery_generation": overlay.generation_uuid,
        "pre_seal_active_recovery_manifest_sha256": (
            overlay.manifest_sha256
        ),
        "pre_seal_active_recovery_tick": TICK,
        "proof_mode": "exact_read_only_reuse",
        "read_only_remote_reuse_verified": True,
        "remote_retained_generation_uuids": [
            retained_predecessor,
            baseline.generation_uuid,
        ],
        "schema": "guala.equal_tick_deployment_reuse.v1",
        "state_revision": 9,
        "status": "reused",
        "tick": TICK,
        "version_aware_remote_reconciliation": False,
    }


def test_management_control_seals_exact_distinct_overlay_for_migration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _baseline(tmp_path)
    active_tick = TICK + 8
    owner_overlay = _distinct_overlay(tmp_path, baseline)
    overlay = None
    for index in range(8):
        felt_change = f"quiescence-{index}"
        successor_core = _write(
            tmp_path / f"quiescent-hot-source-{index}" / CORE,
            json.dumps(
                {
                    "data": {
                        "felt_change": felt_change,
                        "state_file_ticks": {CORE: active_tick},
                    },
                    "guala_identity": IDENTITY,
                    "saved_at_tick": active_tick,
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8"),
        )
        overlay = LiveRecoveryGenerationStore(
            tmp_path / "sealed-live-recovery",
            baseline=baseline,
            hot_files=(CORE,),
            hmac_key=KEY,
            state_file_tick_manifest=CORE,
        ).commit_hot_state(
            tick=active_tick,
            files={CORE: successor_core},
        )
    assert overlay is not None
    assert not (
        tmp_path
        / "sealed-live-recovery"
        / "generations"
        / owner_overlay.generation_uuid
    ).exists()
    candidate = SimpleNamespace(
        generation_uuid="33333333-3333-4333-8333-333333333333",
        identity=IDENTITY,
        manifest_sha256="4" * 64,
        tick=active_tick,
    )
    rebased = SimpleNamespace(
        generation_uuid="77777777-7777-4777-8777-777777777777",
        identity=IDENTITY,
        manifest_sha256="8" * 64,
        tick=active_tick,
    )
    seal = {
        "causal_state_sha256": "5" * 64,
        "seal_hmac_sha256": "6" * 64,
        "state_revision": 10,
    }

    def exact_composite(**kwargs):
        stage = tmp_path / "composite-stage"
        stage.mkdir()
        admission = BoundedStageAdmission(
            stage,
            max_total_bytes=1024 * 1024,
            max_required_files=16,
            max_path_bytes=4096,
        )
        assert kwargs["save_callback"](stage, admission) == active_tick
        assert (stage / CORE).read_bytes() == overlay.stored_bytes(CORE)
        validator = kwargs["equal_tick_causal_transition_validator"]
        staged = {CORE: stage / CORE}
        assert validator(baseline, staged, active_tick) is True
        (stage / CORE).write_bytes(b"tampered")
        assert validator(baseline, staged, active_tick) is False
        assert kwargs["allow_equal_tick_schema_migration"] is False
        return SimpleNamespace(
            generation=candidate,
            version_aware_remote_reconciliation=True,
            read_only_remote_reuse_verified=False,
            remote_retained_generation_uuids=(
                baseline.generation_uuid,
                candidate.generation_uuid,
            ),
            seal_certificate_bytes=lambda: b"composite-attempt-seal",
        )

    monkeypatch.setattr(
        control,
        "stage_authoritative_commit_upload",
        exact_composite,
    )
    monkeypatch.setattr(
        control,
        "verify_deployment_seal",
        lambda certificate, **_kwargs: (
            seal
            if certificate == b"composite-attempt-seal"
            else (_ for _ in ()).throw(AssertionError("wrong seal"))
        ),
    )
    original_predecessor_verifier = control.verify_predecessor_current

    def verify_predecessor(root, *, baseline, **kwargs):
        if baseline is candidate:
            assert kwargs["expected_generation_uuid"] == (
                rebased.generation_uuid
            )
            assert kwargs["expected_manifest_sha256"] == (
                rebased.manifest_sha256
            )
            return rebased
        return original_predecessor_verifier(
            root,
            baseline=baseline,
            **kwargs,
        )

    monkeypatch.setattr(
        control,
        "verify_predecessor_current",
        verify_predecessor,
    )
    monkeypatch.setattr(
        control,
        "_rebase_promoted_active_recovery",
        lambda **kwargs: (
            rebased
            if (
                kwargs["baseline"].generation_uuid
                == baseline.generation_uuid
                and kwargs["composite"] is candidate
                and kwargs["active"].generation_uuid
                == overlay.generation_uuid
            )
            else (_ for _ in ()).throw(AssertionError("wrong rebase"))
        ),
    )

    receipt = control.prove_equal_tick_deployment_reuse(
        store_root=tmp_path / "sealed",
        live_recovery_root=tmp_path / "sealed-live-recovery",
        expected_generation_uuid=baseline.generation_uuid,
        expected_manifest_sha256=baseline.manifest_sha256,
        expected_identity=baseline.identity,
        expected_tick=baseline.tick,
        expected_active_recovery_generation=(
            owner_overlay.generation_uuid
        ),
        expected_active_recovery_manifest_sha256=(
            owner_overlay.manifest_sha256
        ),
        expected_active_recovery_tick=overlay.tick,
        bucket="test-bucket",
        prefix="guala/generations",
        nonce=NONCE,
        max_generation_bytes=1024 * 1024,
        max_required_files=16,
        max_path_bytes=4096,
        physical_byte_ceiling=10 * 1024 * 1024,
        physical_byte_scope=tmp_path,
        s3_client=object(),
        hmac_key=KEY,
        cold_restore_validator=lambda generation: generation is candidate,
        promote_active_recovery=True,
    )

    assert receipt["schema"] == "guala.equal_tick_composite_seal.v2"
    assert receipt["status"] == "sealed"
    assert receipt["proof_mode"] == (
        "authenticated_live_recovery_promotion"
    )
    assert receipt["generation_uuid"] == candidate.generation_uuid
    assert receipt["deployment_baseline_generation"] == (
        baseline.generation_uuid
    )
    assert receipt["active_recovery_generation"] == (
        rebased.generation_uuid
    )
    assert receipt["pre_seal_active_recovery_generation"] == (
        overlay.generation_uuid
    )
    assert receipt[
        "owner_pre_quiescence_active_recovery_generation"
    ] == owner_overlay.generation_uuid
    assert receipt["tick"] == active_tick
    assert receipt["state_revision"] == 10
    assert receipt["read_only_remote_reuse_verified"] is False
    assert receipt["version_aware_remote_reconciliation"] is True


def test_migration_repairs_lagging_outer_tick_without_inventing_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_tick = TICK + 8
    source = tmp_path / "lagging-baseline-source"
    core = _write(
        source / CORE,
        json.dumps(
            {
                "data": {"state_file_ticks": {CORE: active_tick}},
                "guala_identity": IDENTITY,
                "saved_at_tick": active_tick,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
    )
    receipt = _write(source / RECEIPT, b'{"causal":"unchanged"}')
    baseline = ImmutableGenerationStore(
        tmp_path / "sealed",
        identity=IDENTITY,
        required_files=(CORE, RECEIPT),
        content_addressed=True,
    ).commit(
        tick=TICK,
        files={CORE: core, RECEIPT: receipt},
    )
    overlay = LiveRecoveryGenerationStore(
        tmp_path / "sealed-live-recovery",
        baseline=baseline,
        hot_files=(CORE,),
        hmac_key=KEY,
        state_file_tick_manifest=CORE,
    ).commit_hot_state(
        tick=active_tick,
        files={CORE: core},
    )

    class ReachedAuthoritativeCommit(RuntimeError):
        pass

    def observe_lineage_repair(**kwargs):
        stage = tmp_path / "lineage-repair-stage"
        stage.mkdir()
        admission = BoundedStageAdmission(
            stage,
            max_total_bytes=1024 * 1024,
            max_required_files=16,
            max_path_bytes=4096,
        )
        assert kwargs["save_callback"](stage, admission) == active_tick
        assert (stage / CORE).read_bytes() == baseline.stored_bytes(CORE)
        assert kwargs["equal_tick_causal_transition_validator"](
            baseline,
            {CORE: stage / CORE},
            active_tick,
        ) is True
        raise ReachedAuthoritativeCommit

    monkeypatch.setattr(
        control,
        "stage_authoritative_commit_upload",
        observe_lineage_repair,
    )

    with pytest.raises(ReachedAuthoritativeCommit):
        control.prove_equal_tick_deployment_reuse(
            store_root=tmp_path / "sealed",
            live_recovery_root=tmp_path / "sealed-live-recovery",
            expected_generation_uuid=baseline.generation_uuid,
            expected_manifest_sha256=baseline.manifest_sha256,
            expected_identity=baseline.identity,
            expected_tick=baseline.tick,
            expected_active_recovery_generation=overlay.generation_uuid,
            expected_active_recovery_manifest_sha256=(
                overlay.manifest_sha256
            ),
            expected_active_recovery_tick=overlay.tick,
            bucket="test-bucket",
            prefix="guala/generations",
            nonce=NONCE,
            max_generation_bytes=1024 * 1024,
            max_required_files=16,
            max_path_bytes=4096,
            physical_byte_ceiling=10 * 1024 * 1024,
            physical_byte_scope=tmp_path,
            s3_client=object(),
            hmac_key=KEY,
            promote_active_recovery=True,
        )


def test_promoted_composite_rebases_overlay_lineage_without_changing_payload(
    tmp_path: Path,
) -> None:
    baseline = _baseline(tmp_path)
    overlay = _distinct_overlay(tmp_path, baseline)
    source = tmp_path / "composite-source"
    composite = ImmutableGenerationStore(
        tmp_path / "composite-store",
        identity=IDENTITY,
        required_files=(CORE, RECEIPT),
        content_addressed=True,
    ).commit(
        tick=TICK,
        files={
            CORE: _write(
                source / CORE,
                overlay.stored_bytes(CORE),
            ),
            RECEIPT: _write(
                source / RECEIPT,
                b'{"causal":"promoted"}',
            ),
        },
    )

    rebased = control._rebase_promoted_active_recovery(
        live_recovery_root=tmp_path / "sealed-live-recovery",
        baseline=baseline,
        composite=composite,
        active=overlay,
        hot_files=(CORE,),
        hmac_key=KEY,
        max_generation_bytes=1024 * 1024,
        physical_byte_ceiling=10 * 1024 * 1024,
        physical_byte_scope=tmp_path,
    )

    assert rebased.generation_uuid != overlay.generation_uuid
    assert rebased.tick == composite.tick
    assert rebased.stored_bytes(CORE) == composite.stored_bytes(CORE)
    verified = verify_predecessor_current(
        tmp_path / "sealed-live-recovery",
        baseline=composite,
        hmac_key=KEY,
        expected_generation_uuid=rebased.generation_uuid,
        expected_manifest_sha256=rebased.manifest_sha256,
        expected_tick=rebased.tick,
        state_file_tick_manifest=CORE,
    )
    assert verified.recovery_certificate_bytes() == (
        rebased.recovery_certificate_bytes()
    )


def test_management_verifier_is_packaged_inside_the_runtime_image() -> None:
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "deploy"
            / "guala_release_manifest.json"
        ).read_text()
    )
    runtime = next(
        category
        for category in manifest["categories"]
        if category["name"] == "runtime_python"
    )
    build_control = next(
        category
        for category in manifest["categories"]
        if category["name"] == "build_control"
    )
    relative = "tools/prove_equal_tick_deployment_reuse.py"

    assert relative in manifest["runtime_entrypoints"]
    assert runtime["archive_prefix"] == "runtime"
    assert relative in runtime["files"]
    assert relative not in build_control["files"]
