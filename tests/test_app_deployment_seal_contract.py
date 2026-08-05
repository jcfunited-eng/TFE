"""Focused production handoff contracts for the FastAPI organism process.

The tests use isolated in-memory collaborators.  They exercise orchestration
and fail-closed behavior without creating a real Guala, writing EFS, or using
AWS.
"""

import asyncio
from contextlib import nullcontext
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dsf_ai_service.app as appmod
from dsf_ai_service.substrate import deployment_generation
import dsf_ai_service.substrate_runner as substrate_runner


def _run(coroutine):
    return asyncio.run(coroutine)


def _resident_state(*, identity="guala-identity", tick=73):
    record = {
        "available": True,
        "cognitive_mosaic_count": 0,
        "cognitive_ordinal": 0,
        "cognitive_trace_count": 0,
        "fabric_bytes": 1313,
        "fabric_generation": 7,
        "fabric_sha256": "3" * 64,
        "formation_activation_count": 0,
        "identity": identity,
        "joint_field_count": 1,
        "joint_neuron_count": 96,
        "mounted_generation": 7,
        "organism_tick": tick,
        "partial_cue_reassembly_count": 0,
        "persistence": {
            "body_file": "guala_organism.glorun",
            "encoding": "raw_glorun01",
            "schema": "guala.native_resident_organism.v3",
        },
        "python_callback_count": 0,
        "resource_admission": {
            "derivation": "finite_local_resources_divided_by_concurrent_regions",
            "max_envelope_bytes": 4096,
            "max_fabric_bytes": 3072,
            "max_logical_peak_bytes": 12288,
            "memory_boundary_source": "test_fixture",
            "persistence_available_bytes_at_mount": 16384,
            "runtime_available_bytes_at_mount": 16384,
        },
        "schema": "guala.native.resident_readiness.v2",
        "state_bytes": 1345,
        "state_sha256": "1" * 64,
    }
    latest = {
        **record,
        "complete_neuron_fractal_count": 0,
        "dsf_delivery_count": 2,
        "recurrent_complete_neuron_fractal_count": 0,
        "transition": "cold_restore",
    }
    runtime = SimpleNamespace(
        _guala_identity=identity,
        _latest_native_resident_transition=latest,
        native_resident_readiness=lambda: dict(record),
        tick=tick,
    )
    return runtime, record, latest


def test_native_neuron_readiness_separates_dsf_delivery_from_neuronal_output(
        monkeypatch):
    runtime, record, _latest = _resident_state()
    monkeypatch.setattr(appmod, "_guala", runtime)

    assert appmod._native_neuron_readiness() == {
        "available": True,
        "persistence_schema": "guala.native_resident_organism.v3",
        "persistence": record["persistence"],
        "resource_admission": record["resource_admission"],
        "state_sha256": "1" * 64,
        "state_bytes": 1345,
        "fabric_sha256": "3" * 64,
        "fabric_bytes": 1313,
        "fabric_generation": 7,
        "mounted_generation": 7,
        "organism_tick": 73,
        "outcome": "resident_native_organism_active",
        "last_transition": "cold_restore",
        "joint_field_count": 1,
        "joint_neuron_count": 96,
        "dsf_delivery_count": 2,
        "complete_neuron_fractal_count": 0,
        "recurrent_complete_neuron_fractal_count": 0,
        "cognitive_ordinal": 0,
        "cognitive_trace_count": 0,
        "cognitive_mosaic_count": 0,
        "formation_activation_count": 0,
        "partial_cue_reassembly_count": 0,
        "python_callback_count": 0,
        "joint_transition_sha256": None,
        "episode_relation_candidate_sha256": None,
    }


def test_native_neuron_readiness_rejects_observation_drift(
        monkeypatch):
    runtime, _record, latest = _resident_state()
    latest["joint_neuron_count"] = 97
    monkeypatch.setattr(appmod, "_guala", runtime)

    with pytest.raises(
        RuntimeError,
        match="joint_neuron_count differs from active state",
    ):
        appmod._native_neuron_readiness()


def _certificate():
    return {
        "active_recovery_generation": (
            "22222222-2222-4222-8222-222222222222"
        ),
        "active_recovery_is_overlay": True,
        "active_recovery_manifest_sha256": "c" * 64,
        "active_recovery_tick": 73,
        "generation_uuid": "11111111-1111-4111-8111-111111111111",
        "identity": "guala-identity",
        "tick": 73,
        "manifest_sha256": "a" * 64,
        "seal_hmac_sha256": "b" * 64,
    }


def _rebased_overlay():
    return SimpleNamespace(
        generation_uuid="22222222-2222-4222-8222-222222222222",
        identity=_certificate()["identity"],
        manifest_sha256="c" * 64,
        tick=_certificate()["tick"],
    )


def _lineage_generation(generation, manifest):
    return SimpleNamespace(
        generation_uuid=generation,
        identity="guala-identity",
        manifest_sha256=manifest,
        tick=73,
    )


def _lineage_authority(revision, causal, operational):
    return SimpleNamespace(
        state_revision=revision,
        causal_state_sha256=causal,
        operational_metadata_sha256=operational,
    )


def _lineage_seal(generation, authority, seal_hmac):
    return {
        "schema": "deployment_generation_seal_v3",
        "generation_uuid": generation.generation_uuid,
        "identity": generation.identity,
        "manifest_sha256": generation.manifest_sha256,
        "tick": generation.tick,
        "state_revision": authority.state_revision,
        "causal_state_sha256": authority.causal_state_sha256,
        "operational_metadata_sha256": (
            authority.operational_metadata_sha256
        ),
        "attempt_operational_metadata_sha256": (
            authority.operational_metadata_sha256
        ),
        "seal_hmac_sha256": seal_hmac,
    }


class _LineageReadOnlyTransaction:
    def __init__(self, state):
        self._state = state

    def __enter__(self):
        return self._state

    def __exit__(self, *_args):
        return False


def _install_lineage_authority(monkeypatch):
    predecessor = _lineage_generation(
        "11111111-1111-4111-8111-111111111111",
        "a" * 64,
    )
    successor = _lineage_generation(
        "22222222-2222-4222-8222-222222222222",
        "b" * 64,
    )
    predecessor_authority = _lineage_authority(
        8,
        "c" * 64,
        "d" * 64,
    )
    successor_authority = _lineage_authority(
        9,
        "e" * 64,
        "f" * 64,
    )
    predecessor_seal = _lineage_seal(
        predecessor,
        predecessor_authority,
        "1" * 64,
    )
    successor_seal = _lineage_seal(
        successor,
        successor_authority,
        "2" * 64,
    )
    state = SimpleNamespace(
        current=successor,
        predecessor=predecessor,
        current_authority=successor_authority,
        predecessor_authority=predecessor_authority,
    )
    store = SimpleNamespace(
        exclusive_read_only_transaction=lambda **_kwargs: (
            _LineageReadOnlyTransaction(state)
        ),
    )
    seals = {
        predecessor.generation_uuid: predecessor_seal,
        successor.generation_uuid: successor_seal,
    }
    monkeypatch.setattr(appmod, "_authoritative_cold_store", store)
    monkeypatch.setattr(
        appmod,
        "_deployment_baseline_generation",
        successor,
    )
    monkeypatch.setattr(appmod, "_deploy_hmac_key", lambda: b"k" * 32)
    monkeypatch.setattr(
        appmod,
        "_remote_generation_reconciliation",
        {
            "retained_generation_uuids": tuple(seals),
        },
    )

    def load_seal(_root, generation_uuid, *, hmac_key):
        assert hmac_key == b"k" * 32
        return dict(seals[generation_uuid])

    monkeypatch.setattr(
        deployment_generation,
        "load_generation_deployment_seal",
        load_seal,
    )
    return SimpleNamespace(
        predecessor=predecessor,
        successor=successor,
        predecessor_seal=predecessor_seal,
        successor_seal=successor_seal,
    )


def _lineage_storage(proof):
    return {
        "remote_reconciliation": {
            "retained_generation_uuids": [
                proof.predecessor.generation_uuid,
                proof.successor.generation_uuid,
            ],
        },
    }


def test_reviewed_schema_successor_readiness_binds_exact_lineage(
    monkeypatch,
):
    proof = _install_lineage_authority(monkeypatch)
    encoded = appmod._build_authenticated_current_schema_extension_certificate(
        predecessor=proof.predecessor,
        successor_certificate=proof.successor_seal,
        migration_markers=(
            "physical_surface_tutoring_conductor_genesis",
            "whole_organism_neuron_population_profile_v1_to_v2",
        ),
    )
    monkeypatch.setattr(
        appmod,
        "_authenticated_current_schema_extension_certificate",
        encoded,
    )

    readiness = appmod._current_authenticated_schema_extension_readiness(
        current=proof.successor,
        current_certificate=proof.successor_seal,
        storage_cutover=_lineage_storage(proof),
    )

    assert readiness["predecessor"]["generation"] == (
        proof.predecessor.generation_uuid
    )
    assert readiness["successor"]["generation"] == (
        proof.successor.generation_uuid
    )
    assert readiness["successor"]["generation_tick"] == (
        readiness["predecessor"]["generation_tick"]
    )
    assert readiness["successor"]["state_revision"] == (
        readiness["predecessor"]["state_revision"] + 1
    )


@pytest.mark.parametrize(
    ("member", "field", "changed"),
    [
        ("predecessor", "identity", "changed-identity"),
        ("predecessor", "manifest_sha256", "3" * 64),
        ("predecessor", "generation_tick", 74),
        ("predecessor", "deployment_seal_schema", "deployment_generation_seal_v1"),
        ("predecessor", "state_revision", 7),
        ("predecessor", "causal_state_sha256", "4" * 64),
        ("predecessor", "operational_metadata_sha256", "5" * 64),
        ("predecessor", "seal_hmac_sha256", "6" * 64),
        ("successor", "identity", "changed-identity"),
        ("successor", "manifest_sha256", "7" * 64),
        ("successor", "generation_tick", 74),
        ("successor", "deployment_seal_schema", "deployment_generation_seal_v1"),
        ("successor", "state_revision", 10),
        ("successor", "causal_state_sha256", "8" * 64),
        ("successor", "operational_metadata_sha256", "9" * 64),
        ("successor", "seal_hmac_sha256", "0" * 64),
    ],
)
def test_schema_successor_readiness_rejects_every_changed_seal_field(
    monkeypatch,
    member,
    field,
    changed,
):
    proof = _install_lineage_authority(monkeypatch)
    encoded = appmod._build_authenticated_current_schema_extension_certificate(
        predecessor=proof.predecessor,
        successor_certificate=proof.successor_seal,
        migration_markers=appmod._REVIEWED_CURRENT_SCHEMA_MIGRATIONS,
    )
    value = json.loads(encoded)
    value[member][field] = changed
    monkeypatch.setattr(
        appmod,
        "_authenticated_current_schema_extension_certificate",
        json.dumps(value).encode("ascii"),
    )

    with pytest.raises(RuntimeError, match="authenticated current-schema"):
        appmod._current_authenticated_schema_extension_readiness(
            current=proof.successor,
            current_certificate=proof.successor_seal,
            storage_cutover=_lineage_storage(proof),
        )


@pytest.mark.parametrize(
    "markers",
    [
        [
            "whole_organism_neuron_population_profile_v1_to_v2",
            "physical_surface_tutoring_conductor_genesis",
        ],
        [
            "physical_surface_tutoring_conductor_genesis",
            "whole_organism_neuron_population_profile_v1_to_v2",
            "whole_organism_neuron_population_profile_v1_to_v2",
        ],
        [
            "physical_surface_tutoring_conductor_genesis",
            "unreviewed_schema_change",
        ],
    ],
)
def test_schema_successor_readiness_rejects_changed_migration_markers(
    monkeypatch,
    markers,
):
    proof = _install_lineage_authority(monkeypatch)
    encoded = appmod._build_authenticated_current_schema_extension_certificate(
        predecessor=proof.predecessor,
        successor_certificate=proof.successor_seal,
        migration_markers=appmod._REVIEWED_CURRENT_SCHEMA_MIGRATIONS,
    )
    value = json.loads(encoded)
    value["migration_markers"] = markers
    monkeypatch.setattr(
        appmod,
        "_authenticated_current_schema_extension_certificate",
        json.dumps(value).encode("ascii"),
    )

    with pytest.raises(RuntimeError, match="migration markers changed"):
        appmod._current_authenticated_schema_extension_readiness(
            current=proof.successor,
            current_certificate=proof.successor_seal,
            storage_cutover=_lineage_storage(proof),
        )


@pytest.mark.parametrize(
    ("member", "field", "remove"),
    [
        ("predecessor", "seal_hmac_sha256", True),
        ("predecessor", "unexpected", False),
        ("successor", "state_revision", True),
        ("successor", "unexpected", False),
    ],
)
def test_schema_successor_readiness_rejects_missing_or_extra_member_fields(
    monkeypatch,
    member,
    field,
    remove,
):
    proof = _install_lineage_authority(monkeypatch)
    encoded = appmod._build_authenticated_current_schema_extension_certificate(
        predecessor=proof.predecessor,
        successor_certificate=proof.successor_seal,
        migration_markers=appmod._REVIEWED_CURRENT_SCHEMA_MIGRATIONS,
    )
    value = json.loads(encoded)
    if remove:
        del value[member][field]
    else:
        value[member][field] = "not-authority"
    monkeypatch.setattr(
        appmod,
        "_authenticated_current_schema_extension_certificate",
        json.dumps(value).encode("ascii"),
    )

    with pytest.raises(RuntimeError, match="field set changed"):
        appmod._current_authenticated_schema_extension_readiness(
            current=proof.successor,
            current_certificate=proof.successor_seal,
            storage_cutover=_lineage_storage(proof),
        )


def test_schema_successor_authority_never_follows_later_generation_drift(
    monkeypatch,
):
    proof = _install_lineage_authority(monkeypatch)
    encoded = appmod._build_authenticated_current_schema_extension_certificate(
        predecessor=proof.predecessor,
        successor_certificate=proof.successor_seal,
        migration_markers=appmod._REVIEWED_CURRENT_SCHEMA_MIGRATIONS,
    )
    monkeypatch.setattr(
        appmod,
        "_authenticated_current_schema_extension_certificate",
        encoded,
    )
    later = _lineage_generation(
        "33333333-3333-4333-8333-333333333333",
        "3" * 64,
    )

    assert appmod._current_authenticated_schema_extension_readiness(
        current=later,
        current_certificate=proof.successor_seal,
        storage_cutover=_lineage_storage(proof),
    ) is None


@pytest.mark.parametrize(
    "markers",
    [
        (
            "physical_surface_tutoring_conductor_genesis",
            "whole_organism_neuron_population_profile_v1_to_v2",
            "whole_organism_neuron_population_profile_v1_to_v2",
        ),
        (
            "physical_surface_tutoring_conductor_genesis",
            "unreviewed_schema_change",
        ),
    ],
)
def test_generation_seal_rejects_duplicate_or_unreviewed_schema_markers(markers):
    with pytest.raises(
        RuntimeError,
        match="migration authority changed",
    ):
        appmod._seal_runtime_generation(
            "nonce",
            runtime=object(),
            authenticated_current_schema_migrations=markers,
        )


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("identity", "changed-identity"),
        ("tick", 74),
        ("generation_uuid", "11111111-1111-4111-8111-111111111111"),
        ("manifest_sha256", "a" * 64),
    ],
)
def test_schema_extension_candidate_is_exact_same_tick_distinct_successor(
    monkeypatch,
    field,
    changed,
):
    import boto3
    from dsf_ai_service.substrate import whole_organism_persistence

    predecessor = _lineage_generation(
        "11111111-1111-4111-8111-111111111111",
        "a" * 64,
    )
    candidate_values = {
        "generation_uuid": "22222222-2222-4222-8222-222222222222",
        "identity": predecessor.identity,
        "manifest_sha256": "b" * 64,
        "tick": predecessor.tick,
    }
    candidate_values[field] = changed
    candidate = SimpleNamespace(
        **candidate_values,
        stored_bytes=lambda _name: b"sealed-core",
    )
    target = SimpleNamespace(
        _guala_identity=predecessor.identity,
        persistence_transaction=nullcontext,
        discard_prepared_authoritative_full_checkpoint=lambda: None,
    )
    monkeypatch.setattr(
        appmod,
        "_deployment_baseline_generation",
        predecessor,
    )
    monkeypatch.setattr(appmod, "_deploy_hmac_key", lambda: b"k" * 32)
    monkeypatch.setattr(
        appmod,
        "_authoritative_cold_limits",
        lambda: (1024, 4, 128),
    )
    monkeypatch.setattr(
        appmod,
        "_authoritative_physical_storage_config",
        lambda: (4096, "/tmp", SimpleNamespace()),
    )
    monkeypatch.setattr(
        appmod,
        "_validate_runtime_generation_cold_restore",
        lambda _candidate: True,
    )
    monkeypatch.setattr(
        whole_organism_persistence,
        "whole_organism_mutation_root",
        lambda _encoded: "root",
    )
    monkeypatch.setattr(boto3, "client", lambda *_args, **_kwargs: object())

    def stage(**arguments):
        arguments["cold_restore_validator"](candidate)
        raise AssertionError("invalid extension candidate was accepted")

    monkeypatch.setattr(
        deployment_generation,
        "stage_authoritative_commit_upload",
        stage,
    )

    with pytest.raises(RuntimeError, match="same-identity same-tick"):
        appmod._seal_runtime_generation(
            "nonce",
            runtime=target,
            authenticated_current_schema_migrations=(
                appmod._REVIEWED_CURRENT_SCHEMA_MIGRATIONS
            ),
        )


def test_seal_receipt_exposes_exact_post_seal_recovery_overlay():
    overlay = _rebased_overlay()

    receipt = appmod._seal_receipt_with_rebased_live_recovery(
        _certificate(),
        overlay,
    )

    assert receipt["generation_uuid"] == _certificate()["generation_uuid"]
    assert receipt["active_recovery_generation"] == overlay.generation_uuid
    assert (
        receipt["active_recovery_manifest_sha256"]
        == overlay.manifest_sha256
    )
    assert receipt["active_recovery_tick"] == overlay.tick
    assert receipt["active_recovery_is_overlay"] is True


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        (
            "generation_uuid",
            _certificate()["generation_uuid"],
            "distinct overlay",
        ),
        (
            "identity",
            "different-identity",
            "identity differs",
        ),
        (
            "manifest_sha256",
            _certificate()["manifest_sha256"],
            "manifest reused",
        ),
        (
            "tick",
            _certificate()["tick"] + 1,
            "tick differs",
        ),
    ],
)
def test_seal_receipt_rejects_non_redundant_rebased_overlay(
    field,
    value,
    error,
):
    overlay = _rebased_overlay()
    values = {
        "generation_uuid": overlay.generation_uuid,
        "identity": overlay.identity,
        "manifest_sha256": overlay.manifest_sha256,
        "tick": overlay.tick,
    }
    values[field] = value

    with pytest.raises(RuntimeError, match=error):
        appmod._seal_receipt_with_rebased_live_recovery(
            _certificate(),
            SimpleNamespace(**values),
        )


def _install_verified_storage_cutover(monkeypatch):
    """Keep identity tests focused beyond the independently proved cutover."""
    monkeypatch.setattr(
        appmod,
        "_verified_storage_cutover_status",
        lambda: {
            "schema": "guala.production.storage_cutover.v1",
            "retired_flat_full_copy_producer": True,
        },
    )


class _OrderedGuala:
    IDENTITY_FILE = "guala_identity.json"

    def __init__(self, events):
        self.events = events
        self.tick = 73
        self.vocab = {"known"}
        self._guala_identity = "guala-identity"

    def enter_manual_sleep(self):
        self.events.append("manual_sleep")

    def settle_queues(self, budget_s=420.0, threshold=8):
        raise AssertionError("production sealing must not use threshold settle")

    def quiesce_background_workers(self, timeout):
        assert timeout == 540.0
        self.events.append("engine_strict_stop")
        return {"engine_quiesced": True, "queues": {
            "organism": {"unfinished": 0, "queued": 0},
            "tapestry": {"unfinished": 0, "queued": 0},
        }}


@pytest.fixture
def ordered_handoff(monkeypatch, tmp_path):
    events = []
    lifecycle = appmod._DeploymentLifecycle()
    guala = _OrderedGuala(events)

    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "control-secret")
    monkeypatch.setattr(appmod, "_guala", guala)
    monkeypatch.setattr(appmod, "STATE_DIR", str(tmp_path))
    monkeypatch.setenv("SEAL_SETTLE_BUDGET_S", "420")

    real_auth = appmod._require_deploy_control

    async def ordered_auth(request):
        events.append("auth")
        return await real_auth(request)

    monkeypatch.setattr(appmod, "_require_deploy_control", ordered_auth)

    drain_count = 0

    def drain(_timeout):
        nonlocal drain_count
        drain_count += 1
        events.append(f"admission_drain_{drain_count}")

    monkeypatch.setattr(lifecycle, "wait_for_mutations", drain)

    async def stop_app_tasks(timeout):
        assert timeout == 120.0
        events.append("app_task_stop")
        return {"app_tasks_stopped": 0}

    monkeypatch.setattr(appmod, "_stop_app_lifecycle_tasks", stop_app_tasks)
    monkeypatch.setattr(
        appmod,
        "_stop_embedded_persistence_components",
        lambda timeout: events.append("persistence_stops")
        or {"persistence_components_stopped": ["save_coordinator"]},
    )
    monkeypatch.setattr(
        substrate_runner,
        "quiesce_background_loops",
        lambda timeout: events.append("runner_strict_stop")
        or {"runner_quiesced": True},
    )

    real_seal = lifecycle.seal

    def ordered_seal(proof):
        events.append("sealed")
        real_seal(proof)

    monkeypatch.setattr(lifecycle, "seal", ordered_seal)
    return SimpleNamespace(
        events=events,
        lifecycle=lifecycle,
        guala=guala,
    )


def test_authenticated_handoff_orders_every_writer_before_seal(
        ordered_handoff, monkeypatch):
    """SEALED is published only after every admitted writer and remote proof."""

    def stage_and_prove(nonce):
        assert nonce == "nonce-a"
        ordered_handoff.events.append("stage_and_remote_proof")
        return _certificate()

    monkeypatch.setattr(appmod, "_seal_runtime_generation", stage_and_prove)

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.post(
                "/internal/deployment/quiesce",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": "nonce-a",
                },
                json={"deploy_nonce": "nonce-a"},
            )

    response = _run(scenario())

    assert response.status_code == 200
    response_body = response.json()
    assert response_body["state"] == "SEALED"
    assert (
        response_body["active_recovery_generation"]
        == _certificate()["active_recovery_generation"]
    )
    assert (
        response_body["active_recovery_manifest_sha256"]
        == _certificate()["active_recovery_manifest_sha256"]
    )
    assert (
        response_body["active_recovery_tick"]
        == _certificate()["active_recovery_tick"]
    )
    assert response_body["active_recovery_is_overlay"] is True
    assert ordered_handoff.events == [
        "auth",
        "admission_drain_1",
        "app_task_stop",
        "admission_drain_2",
        "persistence_stops",
        "runner_strict_stop",
        "engine_strict_stop",
        "stage_and_remote_proof",
        "sealed",
    ]
    snapshot = ordered_handoff.lifecycle.snapshot()
    assert snapshot["state"] == "SEALED"
    assert snapshot["certificate"]["generation_uuid"] == _certificate()[
        "generation_uuid"]


def test_late_generation_proof_failure_stays_quiescing_without_certificate(
        ordered_handoff, monkeypatch):
    """A failure after strict stops must never reopen or claim a false seal."""

    def fail_late(_nonce):
        ordered_handoff.events.append("stage_and_remote_proof_failed")
        raise RuntimeError("remote read-back differs from staged generation")

    monkeypatch.setattr(appmod, "_seal_runtime_generation", fail_late)

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.post(
                "/internal/deployment/quiesce",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": "nonce-late-failure",
                },
                json={"deploy_nonce": "nonce-late-failure"},
            )

    response = _run(scenario())

    assert response.status_code == 503
    assert response.json()["ok"] is False
    assert "seal_hmac_sha256" not in response.json()
    snapshot = ordered_handoff.lifecycle.snapshot()
    assert snapshot["state"] == "QUIESCING"
    assert snapshot["certificate"] is None
    assert snapshot["failure"] == (
        "remote read-back differs from staged generation")
    assert ordered_handoff.events[-1] == "stage_and_remote_proof_failed"
    assert "sealed" not in ordered_handoff.events


def test_engine_drain_failure_stays_quiescing_and_never_stages(
        ordered_handoff, monkeypatch):
    """A non-zero engine boundary cannot create or publish a generation."""

    def fail_engine_drain(timeout):
        assert timeout == 540.0
        ordered_handoff.events.append("engine_strict_stop_failed")
        raise RuntimeError("quiescence timed out draining tapestry queue")

    def forbidden_stage(_nonce):
        raise AssertionError("generation staged after failed exact-zero drain")

    monkeypatch.setattr(
        ordered_handoff.guala,
        "quiesce_background_workers",
        fail_engine_drain,
    )
    monkeypatch.setattr(appmod, "_seal_runtime_generation", forbidden_stage)

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.post(
                "/internal/deployment/quiesce",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": "nonce-drain-failure",
                },
                json={"deploy_nonce": "nonce-drain-failure"},
            )

    response = _run(scenario())

    assert response.status_code == 503
    assert response.json()["ok"] is False
    assert "tapestry" in response.json()["error"]
    snapshot = ordered_handoff.lifecycle.snapshot()
    assert snapshot["state"] == "QUIESCING"
    assert snapshot["certificate"] is None
    assert "sealed" not in ordered_handoff.events


@pytest.mark.parametrize("state", ["QUIESCING", "SEALED"])
def test_shallow_ready_keeps_controlled_drain_alive_for_alb(
        monkeypatch, state):
    lifecycle = appmod._DeploymentLifecycle()
    lifecycle.begin_quiescence("nonce-ready")
    if state == "SEALED":
        lifecycle.seal(_certificate())
    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(appmod, "_boot_halted", None)

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.get("/ready")

    response = _run(scenario())

    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["draining"] is True
    assert response.json()["lifecycle"] == state


@pytest.mark.parametrize("value", ["not-a-number", "-1", "nan", "inf"])
def test_invalid_settle_budget_fails_closed_before_engine_drain(
        ordered_handoff, monkeypatch, value):
    monkeypatch.setenv("SEAL_SETTLE_BUDGET_S", value)

    def forbidden_stage(_nonce):
        raise AssertionError("invalid timeout reached generation staging")

    monkeypatch.setattr(appmod, "_seal_runtime_generation", forbidden_stage)

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.post(
                "/internal/deployment/quiesce",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": f"nonce-{value}",
                },
                json={"deploy_nonce": f"nonce-{value}"},
            )

    response = _run(scenario())

    assert response.status_code == 503
    assert "finite non-negative" in response.json()["error"]
    assert ordered_handoff.lifecycle.snapshot()["state"] == "QUIESCING"
    assert "engine_strict_stop" not in ordered_handoff.events


def test_sealed_shutdown_writes_nothing_and_retires_process(monkeypatch):
    lifecycle = appmod._DeploymentLifecycle()
    lifecycle.begin_quiescence("shutdown-nonce")
    lifecycle.seal(_certificate())

    class NoWriteGuala:
        def __getattr__(self, name):
            if name in {
                    "manual_sleep", "save_full_state", "_save_wave_atlas",
                    "quiesce_background_workers", "strict_shutdown",
                    "settle_queues"}:
                def forbidden(*_args, **_kwargs):
                    raise AssertionError(f"sealed shutdown called {name}")
                return forbidden
            raise AttributeError(name)

    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(appmod, "_guala", NoWriteGuala())

    _run(appmod.shutdown())

    assert lifecycle.snapshot()["state"] == "RETIRED"


@pytest.mark.parametrize(
    ("mismatch", "error_fragment"),
    [
        ("build", "git SHA"),
        ("task", "task definition"),
        ("image", "image digest"),
        ("generation", "generation_uuid mismatch"),
        ("manifest", "manifest_sha256 mismatch"),
        ("identity", "live Guala identity"),
    ],
)
def test_deep_readiness_rejects_every_runtime_identity_mismatch(
        monkeypatch, mismatch, error_fragment):
    """No build, task, image, generation, or identity mismatch returns 200."""
    _install_verified_storage_cutover(monkeypatch)
    lifecycle = appmod._DeploymentLifecycle()
    generation = SimpleNamespace(
        generation_uuid=_certificate()["generation_uuid"],
        identity=_certificate()["identity"],
        manifest_sha256=_certificate()["manifest_sha256"],
        tick=_certificate()["tick"],
    )
    guala_identity = (
        "different-live-identity"
        if mismatch == "identity"
        else generation.identity)

    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "control-secret")
    monkeypatch.setattr(appmod, "_init_complete", True)
    monkeypatch.setattr(appmod, "_init_error", None)
    runtime, _record, _latest = _resident_state(
        identity=guala_identity,
        tick=generation.tick,
    )
    monkeypatch.setattr(appmod, "_guala", runtime)
    monkeypatch.setattr(appmod, "_loaded_generation", generation)
    monkeypatch.setattr(
        appmod, "_deployment_baseline_generation", generation)
    monkeypatch.setattr(
        appmod,
        "_live_recovery_store",
        SimpleNamespace(load_current=lambda: None),
    )
    monkeypatch.setattr(
        appmod,
        "_authoritative_cold_store",
        SimpleNamespace(
            assert_current_reference=lambda expected: expected,
        ),
    )
    actual_git = "1" * 40
    expected_git = "2" * 40 if mismatch == "build" else actual_git
    actual_task = "dsf-ai:41"
    expected_task = "dsf-ai:42" if mismatch == "task" else actual_task
    actual_image = "sha256:" + "3" * 64
    expected_image = (
        "sha256:" + "4" * 64 if mismatch == "image" else actual_image)
    monkeypatch.setenv("DEPLOY_EXPECTED_GIT_SHA", expected_git)
    monkeypatch.setenv("DEPLOY_EXPECTED_TASK_DEFINITION", expected_task)
    monkeypatch.setenv("DEPLOY_EXPECTED_IMAGE_DIGEST", expected_image)
    monkeypatch.setattr(appmod, "_read_build_git_sha", lambda: actual_git)
    monkeypatch.setattr(
        appmod,
        "_ecs_task_runtime_identity",
        lambda: {
            "task_definition": actual_task,
            "image_digest": actual_image,
        },
    )

    generation_certificate = _certificate()
    if mismatch == "generation":
        generation_certificate["generation_uuid"] = (
            "22222222-2222-4222-8222-222222222222")
    elif mismatch == "manifest":
        generation_certificate["manifest_sha256"] = "9" * 64
    def load_generation_seal(_root, generation_uuid, *, hmac_key):
        assert hmac_key == appmod._deploy_hmac_key()
        assert generation_uuid == generation.generation_uuid
        return generation_certificate

    monkeypatch.setattr(
        deployment_generation,
        "load_generation_deployment_seal",
        load_generation_seal,
    )

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.get(
                "/internal/deployment/readiness",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": "readiness-nonce",
                },
            )

    response = _run(scenario())
    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert error_fragment in response.json()["error"]


def test_deep_readiness_keeps_sealed_baseline_and_active_overlay_distinct(
        monkeypatch):
    """A valid hot overlay cannot replace the deployment seal's identity."""
    _install_verified_storage_cutover(monkeypatch)
    lifecycle = appmod._DeploymentLifecycle()
    baseline = SimpleNamespace(
        generation_uuid=_certificate()["generation_uuid"],
        identity=_certificate()["identity"],
        manifest_sha256=_certificate()["manifest_sha256"],
        tick=_certificate()["tick"],
    )
    overlay = SimpleNamespace(
        generation_uuid="22222222-2222-4222-8222-222222222222",
        identity=baseline.identity,
        manifest_sha256="c" * 64,
        tick=baseline.tick + 11,
    )

    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "control-secret")
    monkeypatch.setattr(appmod, "_init_complete", True)
    monkeypatch.setattr(appmod, "_init_error", None)
    runtime, _record, _latest = _resident_state(
        identity=baseline.identity,
        tick=overlay.tick,
    )
    monkeypatch.setattr(appmod, "_guala", runtime)
    monkeypatch.setattr(appmod, "_loaded_generation", overlay)
    monkeypatch.setattr(
        appmod, "_deployment_baseline_generation", baseline)
    monkeypatch.setattr(
        appmod,
        "_live_recovery_store",
        SimpleNamespace(load_current=lambda: overlay),
    )
    monkeypatch.setattr(
        appmod,
        "_authoritative_cold_store",
        SimpleNamespace(
            assert_current_reference=lambda expected: expected,
        ),
    )
    actual_git = "1" * 40
    actual_task = "dsf-ai:41"
    actual_image = "sha256:" + "3" * 64
    monkeypatch.setenv("DEPLOY_EXPECTED_GIT_SHA", actual_git)
    monkeypatch.setenv("DEPLOY_EXPECTED_TASK_DEFINITION", actual_task)
    monkeypatch.setenv("DEPLOY_EXPECTED_IMAGE_DIGEST", actual_image)
    monkeypatch.setattr(appmod, "_read_build_git_sha", lambda: actual_git)
    monkeypatch.setattr(
        appmod,
        "_ecs_task_runtime_identity",
        lambda: {
            "task_definition": actual_task,
            "image_digest": actual_image,
        },
    )

    def load_generation_seal(_root, generation_uuid, *, hmac_key):
        assert hmac_key == appmod._deploy_hmac_key()
        assert generation_uuid == baseline.generation_uuid
        return _certificate()

    monkeypatch.setattr(
        deployment_generation,
        "load_generation_deployment_seal",
        load_generation_seal,
    )

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.get(
                "/internal/deployment/readiness",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": "readiness-nonce",
                },
            )

    response = _run(scenario())
    assert response.status_code == 200
    proof = response.json()
    assert proof["ready"] is True
    assert proof["generation"] == baseline.generation_uuid
    assert proof["manifest_sha256"] == baseline.manifest_sha256
    assert proof["generation_tick"] == baseline.tick
    assert proof["active_recovery_generation"] == overlay.generation_uuid
    assert proof["active_recovery_manifest_sha256"] == overlay.manifest_sha256
    assert proof["active_recovery_tick"] == overlay.tick
    assert proof["active_recovery_is_overlay"] is True
    assert proof["periodic_cold_checkpoint"] == (
        appmod._periodic_cold_checkpoint_status
    )
