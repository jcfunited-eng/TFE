import hashlib
import io
import json
from pathlib import Path
import sys


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
        "guala_windows.json",
        "guala_organism.pkl.gz",
        "guala_tapestry.pkl.gz",
    }
    if guala.wave_atlas is not None:
        expected_engine.add("wave_atlas.npz")
    assert expected_engine <= required
    assert not ({".sleeping", "events.log", "diary/old.log"} & required)
    assert proof["generation_uuid"] == generation.generation_uuid
    assert proof["manifest_sha256"] == generation.manifest_sha256
