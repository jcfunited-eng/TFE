import hashlib
import io
import inspect
import json
from pathlib import Path
import sys
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dsf_ai_service.app as appmod
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
    source = inspect.getsource(appmod._production_runtime_proof)
    assert "assert_current_reference" in source
    assert "_authoritative_cold_store.inspect" not in source


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
