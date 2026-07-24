import hashlib
import io
import inspect
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dsf_ai_service.app as appmod
from dsf_ai_service.substrate import deployment_generation
from dsf_ai_service.substrate.deployment_generation import discover_and_load_current
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


class _S3:
    def __init__(self):
        self.objects = {}

    def put_object(self, *, Bucket, Key, Body):
        self.objects[(Bucket, Key)] = bytes(Body)
        return {"ETag": hashlib.md5(bytes(Body)).hexdigest()}

    def list_objects_v2(self, *, Bucket, Prefix, ContinuationToken=None):
        assert ContinuationToken is None
        return {
            "Contents": [
                {"Key": key}
                for bucket, key in sorted(self.objects)
                if bucket == Bucket and key.startswith(Prefix)
            ],
            "IsTruncated": False,
        }

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}


def test_boot_audits_immutable_generations_without_disposable_engine_loads():
    source = inspect.getsource(appmod._prepare_generation_boot)
    assert "cold_store.inspect_sealed_boot" in source
    assert "cold_store.inspect_legacy_retention_transition()" in source
    assert "cold_store.reconcile_verified_retention()" not in source
    assert "_deployment_baseline_generation = authoritative_baseline" in source
    assert "authoritative_baseline = cold_state.current" in source
    assert "_deployment_baseline_generation = materialized_baseline" not in source
    completion = inspect.getsource(
        appmod._complete_legacy_cold_retention_transition
    )
    assert "complete_legacy_retention_transition" in completion
    assert "_validate_runtime_generation_cold_restore" not in completion
    init_source = inspect.getsource(appmod._gl_init)
    exact_restore_guard = init_source.index(
        "generation identity/tick mismatch"
    )
    legacy_completion = init_source.index(
        "_complete_legacy_cold_retention_transition(g)"
    )
    autonomy_start = init_source.index("g.start_autonomy_loop")
    assert exact_restore_guard < legacy_completion < autonomy_start


def test_recurring_readiness_never_reaudits_generation_payloads():
    source = inspect.getsource(
        appmod._production_runtime_proof_under_authority
    )
    assert "assert_current_reference" in source
    assert "_authoritative_cold_store.inspect" not in source


def test_readiness_cannot_observe_a_half_published_hot_generation(
    monkeypatch,
):
    current = {"generation": "old"}
    loaded = {"generation": "old"}
    entered = threading.Event()
    completed = threading.Event()
    outcome = {}

    def coherent_proof(*, nonce=None):
        entered.set()
        assert current["generation"] == loaded["generation"]
        return {"generation": loaded["generation"], "nonce": nonce}

    monkeypatch.setattr(
        appmod,
        "_production_runtime_proof_under_authority",
        coherent_proof,
    )

    appmod._persistence_authority_lock.acquire()
    try:
        current["generation"] = "new"

        def prove():
            try:
                outcome["proof"] = appmod._production_runtime_proof(
                    nonce="deployment-nonce"
                )
            except BaseException as error:
                outcome["error"] = error
            finally:
                completed.set()

        worker = threading.Thread(target=prove)
        worker.start()
        assert not entered.wait(timeout=0.1)
        assert not completed.is_set()
        loaded["generation"] = "new"
    finally:
        appmod._persistence_authority_lock.release()

    worker.join(timeout=2.0)
    assert not worker.is_alive()
    assert "error" not in outcome
    assert outcome["proof"] == {
        "generation": "new",
        "nonce": "deployment-nonce",
    }


def test_async_readiness_does_not_block_the_server_on_checkpoint_authority():
    shallow = inspect.getsource(appmod.ready)
    deep = inspect.getsource(appmod.ready_guala)
    assert "await asyncio.to_thread(_production_runtime_proof)" in shallow
    assert "await asyncio.to_thread(" in deep
    assert "_production_runtime_proof," in deep


def test_legacy_retention_completion_uses_the_real_restored_identity_and_tick(
    tmp_path,
    monkeypatch,
):
    from dsf_ai_service.substrate import deployment_generation

    events = []
    current = SimpleNamespace(
        generation_uuid="11111111-1111-4111-8111-111111111111",
        identity="guala-identity",
        tick=73,
        manifest_sha256="a" * 64,
    )
    predecessor = SimpleNamespace(
        generation_uuid="22222222-2222-4222-8222-222222222222",
    )
    transitioned = SimpleNamespace(
        current=current,
        census=(
            SimpleNamespace(generation_uuid=current.generation_uuid),
            SimpleNamespace(
                generation_uuid=predecessor.generation_uuid
            ),
        ),
    )

    class Authority:
        def complete_legacy_retention_transition(self, **proof):
            events.append(("complete", proof))
            return transitioned

    seal_path = tmp_path / deployment_generation.DEPLOYMENT_SEAL_NAME
    seal_path.write_bytes(b"sealed-generation-certificate")
    monkeypatch.setattr(appmod, "GENERATION_STORE_ROOT", str(tmp_path))
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "control-secret")
    monkeypatch.setattr(
        appmod,
        "_legacy_cold_retention_transition",
        current,
    )
    monkeypatch.setattr(appmod, "_authoritative_cold_store", Authority())
    monkeypatch.setattr(appmod, "_deployment_baseline_generation", None)
    monkeypatch.setattr(
        deployment_generation,
        "load_and_verify_deployment_seal",
        lambda *_args, **_kwargs: {
            "generation_uuid": current.generation_uuid,
            "nonce_base64": "MDEyMzQ1Njc4OWFiY2RlZg==",
        },
    )
    monkeypatch.setattr(
        deployment_generation,
        "persist_generation_deployment_seal",
        lambda *_args, **_kwargs: events.append(("persist", _kwargs)),
    )
    monkeypatch.setattr(
        deployment_generation,
        "reconcile_generation_deployment_seals",
        lambda *_args, **_kwargs: events.append(
            ("local", _kwargs["retained_generation_uuids"])
        ),
    )
    monkeypatch.setattr(
        deployment_generation,
        "reconcile_remote_generation_prefixes",
        lambda **kwargs: events.append(
            ("remote", kwargs["retained_generation_uuids"])
        ),
    )
    monkeypatch.setattr("boto3.client", lambda *_args, **_kwargs: object())

    restored = SimpleNamespace(
        _guala_identity=current.identity,
        tick=current.tick,
    )
    appmod._complete_legacy_cold_retention_transition(restored)

    assert events[0] == (
        "complete",
        {
            "audited_current": current,
            "restored_identity": current.identity,
            "restored_tick": current.tick,
        },
    )
    assert events[1][0] == "persist"
    assert events[2] == (
        "local",
        (current.generation_uuid, predecessor.generation_uuid),
    )
    assert events[3] == (
        "remote",
        (current.generation_uuid, predecessor.generation_uuid),
    )
    assert appmod._deployment_baseline_generation is current
    assert appmod._legacy_cold_retention_transition is None


def test_legacy_pickle_migration_requires_both_verified_generation_artifacts():
    assert not appmod._verified_generation_requires_legacy_pickle_migration(None)
    assert not appmod._verified_generation_requires_legacy_pickle_migration(
        SimpleNamespace(required_files=("guala_organism.pkl.gz",))
    )
    assert appmod._verified_generation_requires_legacy_pickle_migration(
        SimpleNamespace(
            required_files=(
                "guala_organism.pkl.gz",
                "guala_tapestry.pkl.gz",
            )
        )
    )


def test_runtime_generation_contains_complete_contract_and_excludes_transients(
        tmp_path, monkeypatch):
    active = tmp_path / "active"
    store = tmp_path / "sealed"
    active.mkdir()
    guala = Guala()
    guala.add_corpus("remembered", "Remembered", ["red fox runs"])
    guala.save_full_state(str(active))
    guala._save_wave_atlas(str(active))

    for name in (
            "dream_gate_cleared.json",
            "guala_runtime_config.json",
            "curriculum_progress.json",
            "curriculum.json",
            "world_state.json"):
        (active / name).write_text(json.dumps({"name": name}))
    sessions = active / "v7_sessions"
    sessions.mkdir()
    (sessions / "one.json").write_text("{}")
    (sessions / "one.events.jsonl").write_text('{"event":1}\n')

    (active / ".sleeping").write_text("{}")
    (active / "events.log").write_text("old replay data")
    (active / "diary").mkdir()
    (active / "diary" / "old.log").write_text("audit only")

    guala.strict_shutdown(timeout=30.0)
    fake_s3 = _S3()
    monkeypatch.setattr("boto3.client", lambda *_args, **_kwargs: fake_s3)
    monkeypatch.setattr(appmod, "_guala", guala)
    monkeypatch.setattr(appmod, "STATE_DIR", str(active))
    monkeypatch.setattr(appmod, "GENERATION_STORE_ROOT", str(store))
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "test-control-secret")
    monkeypatch.setenv("GUALA_MAX_COLD_GENERATION_BYTES", str(64 * 1024 * 1024))
    monkeypatch.setenv("GUALA_MAX_COLD_REQUIRED_FILES", "16384")
    monkeypatch.setenv("GUALA_MAX_COLD_PATH_BYTES", str(2 * 1024 * 1024))

    proof = appmod._seal_runtime_generation("nonce-for-state-contract-0001")
    generation = discover_and_load_current(store).generation
    required = set(generation.required_files)

    expected_auxiliary = {
        "dream_gate_cleared.json",
        "guala_runtime_config.json",
        "curriculum_progress.json",
        "curriculum.json",
        "world_state.json",
        "v7_sessions/one.json",
        "v7_sessions/one.events.jsonl",
    }
    assert expected_auxiliary <= required
    expected_engine = {
        "guala_identity.json",
        "guala_core.json",
        "guala_organism.sgr",
        "guala_tapestry.sgr",
    }
    if guala.wave_atlas is not None:
        expected_engine.add("wave_atlas.npz")
    assert expected_engine <= required
    assert not ({".sleeping", "events.log", "diary/old.log"} & required)
    assert proof["generation_uuid"] == generation.generation_uuid
    assert proof["manifest_sha256"] == generation.manifest_sha256


def test_rejected_cold_candidate_cannot_advance_live_checkpoint_lineage(
        tmp_path, monkeypatch):
    active = tmp_path / "active-rejected-candidate"
    store = tmp_path / "sealed-rejected-candidate"
    stage = tmp_path / "private-rejected-candidate"
    active.mkdir()
    guala = Guala()
    guala.save_full_state(str(active))
    prior_ticks = dict(guala._state_file_ticks)
    prior_last_save_tick = guala._last_save_tick
    guala.tick += 7
    rejected_tick = guala.tick
    guala.strict_shutdown(timeout=30.0)

    def reject_after_complete_private_write(**kwargs):
        from dsf_ai_service.substrate.deployment_generation import (
            BoundedStageAdmission,
        )

        stage.mkdir()
        admission = BoundedStageAdmission(
            stage,
            max_total_bytes=64 * 1024 * 1024,
            max_required_files=16_384,
            max_path_bytes=2 * 1024 * 1024,
        )
        kwargs["save_callback"](stage, admission)
        staged_core = json.loads(
            (stage / "guala_core.json").read_text(encoding="utf-8")
        )
        assert set(
            staged_core["data"]["state_file_ticks"].values()
        ) == {rejected_tick}
        raise RuntimeError("injected isolated cold-restore rejection")

    monkeypatch.setattr(
        deployment_generation,
        "stage_authoritative_commit_upload",
        reject_after_complete_private_write,
    )
    monkeypatch.setattr("boto3.client", lambda *_args, **_kwargs: _S3())
    monkeypatch.setattr(appmod, "_guala", guala)
    monkeypatch.setattr(appmod, "STATE_DIR", str(active))
    monkeypatch.setattr(appmod, "GENERATION_STORE_ROOT", str(store))
    monkeypatch.setattr(appmod, "_live_recovery_store", None)
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "test-control-secret")
    monkeypatch.setenv("GUALA_MAX_COLD_GENERATION_BYTES", str(64 * 1024 * 1024))
    monkeypatch.setenv("GUALA_MAX_COLD_REQUIRED_FILES", "16384")
    monkeypatch.setenv("GUALA_MAX_COLD_PATH_BYTES", str(2 * 1024 * 1024))

    with pytest.raises(
            RuntimeError,
            match="isolated cold-restore rejection"):
        appmod._seal_runtime_generation(
            "rejected-candidate-lineage-test-0001"
        )

    assert guala._state_file_ticks == prior_ticks
    assert guala._last_save_tick == prior_last_save_tick
    assert guala._prepared_authoritative_full_checkpoint is None

    guala.save_hot_state(str(active))
    hot_core = json.loads(
        (active / "guala_core.json").read_text(encoding="utf-8")
    )
    hot_ticks = hot_core["data"]["state_file_ticks"]
    for relative in Guala.HOT_SAVE_MANIFEST_FILES:
        assert hot_ticks[relative] == rejected_tick
    for relative in (
            set(Guala.FULL_SAVE_MANIFEST_FILES)
            - set(Guala.HOT_SAVE_MANIFEST_FILES)):
        assert hot_ticks[relative] == prior_ticks[relative]
