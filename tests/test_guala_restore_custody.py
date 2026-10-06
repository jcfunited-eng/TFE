"""Checkpoint custody guards only; these do not establish learned cognition."""

import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from dsf_ai_service.guala_functional_organism import FunctionalOrganism, VOICE_VERSION
from dsf_ai_service.paired_current_store import PairedCurrentStore

IDENTITY = "7a635ab2-225c-4222-98b4-975ce41b6a1a"
TICK = 23
WORLD_BYTES = b"declared-world-custody-fixture"


def retained_body():
    value = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=TICK)
    value._state.update(
        voice=[{"tick": 18, "retained": [1, 2, 3]}],
        heard=[{"tick": 19, "retained": [4, 5, 6]}],
        pending_voice=base64.b64encode(b"\x01\x00" * 4000).decode("ascii"),
        pending_drive=[1, 2, 3],
        speech={"historical-key": {"retained": 7}},
        syllable_totals={"historical-key": 8},
        prior_syllable="historical-key",
        visited={"historical-place": [2, 17]},
        unknown_historical_record={"source": [0, False, "unchanged"]},
    )
    value._state["streams"]["historical_stream"] = [1.0, -0.0, -1.0]
    value._state["acts"]["historical-key"] = {
        "regimes": "retired-regime", "acts": {"rest": [2, 1.0]}, "tick": 17,
    }
    return value


def test_current_body_codec_roundtrip_retains_every_record_and_pending_pressure():
    warm = retained_body()
    before = warm.encoded()
    for _ in range(3):
        restored = FunctionalOrganism.restore(before)
        assert restored.encoded() == before
        assert restored.migrate() is False
        assert restored.encoded() == before
        assert restored.identity == IDENTITY and restored.live_organism_tick == TICK
        assert restored.pending_voice == warm.pending_voice
        assert restored._state == warm._state


def test_fresh_process_restores_exact_history_and_pending_pressure():
    import guala_core

    warm = retained_body()
    before = warm.encoded()
    native_path = str(Path(guala_core.__file__).resolve(strict=True))
    script = """
import importlib.util, json, os, sys
from pathlib import Path
native_path = os.environ['GUALA_TEST_CUSTODY_NATIVE_PATH']
spec = importlib.util.spec_from_file_location('guala_core', native_path)
core = importlib.util.module_from_spec(spec)
sys.modules['guala_core'] = core
spec.loader.exec_module(core)
assert str(Path(core.__file__).resolve(strict=True)) == native_path
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
request = json.load(sys.stdin)
before = bytes.fromhex(request['body'])
restored = FunctionalOrganism.restore(before)
assert restored.migrate() is False
json.dump({
    'body': restored.encoded().hex(),
    'pending_pressure': restored.pending_voice.hex(),
    'identity': restored.identity,
    'tick': restored.live_organism_tick,
    'native_path': str(Path(core.__file__).resolve(strict=True)),
}, sys.stdout)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps({"body": before.hex()}), text=True, capture_output=True,
        env=dict(os.environ, GUALA_TEST_CUSTODY_NATIVE_PATH=native_path),
        timeout=30, check=True,
    )
    cold = json.loads(result.stdout)
    assert bytes.fromhex(cold["body"]) == before
    assert bytes.fromhex(cold["pending_pressure"]) == warm.pending_voice
    assert cold["identity"] == IDENTITY and cold["tick"] == TICK
    assert cold["native_path"] == native_path
    assert warm.encoded() == before


def test_current_law_does_not_fill_or_remove_historical_fields():
    body = retained_body()
    for key in ("acts", "pending_act", "last_chosen", "act_totals", "ambient_sound"):
        del body._state[key]
    before = body.encoded()
    assert body.migrate() is False
    assert body.encoded() == before
    assert FunctionalOrganism.restore(before).encoded() == before


@pytest.mark.parametrize("version", [1, None, float(VOICE_VERSION), True])
def test_unsupported_voice_law_refuses_without_resetting_direct_migration(version):
    body = retained_body()
    if version is None:
        del body._state["voice_version"]
    else:
        body._state["voice_version"] = version
    before = body.encoded()
    state_before = copy.deepcopy(body._state)
    with pytest.raises(ValueError, match="voice law is unsupported"):
        body.migrate()
    assert body.encoded() == before and body._state == state_before
    with pytest.raises(ValueError, match="voice law is unsupported"):
        FunctionalOrganism.restore(before)
    assert body.encoded() == before


def file_bytes(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def startup_fixture(monkeypatch, tmp_path, body, *, world_successor=WORLD_BYTES):
    import dsf_ai_service.guala_home_world as home
    import dsf_ai_service.lean_production_app as production
    import dsf_ai_service.substrate.native_resident_resource_admission as admission

    store = PairedCurrentStore(tmp_path, max_body_bytes=len(body), max_world_bytes=len(WORLD_BYTES))
    pointer = store.publish(identity=IDENTITY, organism_tick=TICK, body=body,
                            world=WORLD_BYTES, expected_current_body_sha256=None)
    before = file_bytes(tmp_path)
    monkeypatch.setenv("GUALA_PAIRED_ROOT", str(tmp_path))
    monkeypatch.setenv("GUALA_MAX_WORLD_BYTES", str(len(WORLD_BYTES)))
    monkeypatch.setenv("NATIVE_CORE_ENABLED", "0")
    monkeypatch.setattr(admission, "derive_native_resident_resource_admission",
                        lambda root: SimpleNamespace(max_envelope_bytes=len(body)))

    def forbidden(*args, **kwargs):
        pytest.fail("startup tried to replace retained state")

    monkeypatch.setattr(FunctionalOrganism, "genesis", forbidden)
    monkeypatch.setattr(PairedCurrentStore, "publish", forbidden)
    world_calls = []

    def restore_world(**kwargs):
        world_calls.append(kwargs)
        return SimpleNamespace(encoded_snapshot=lambda: world_successor)

    monkeypatch.setattr(home, "home_world_authority", restore_world)
    monkeypatch.setattr(production, "LeanOrganismActor", lambda **kwargs: SimpleNamespace(**kwargs))
    return production, pointer, before, world_calls


@pytest.mark.parametrize("kind", ["foreign_format", "old_voice_law", "missing_voice_law", "wrong_identity", "wrong_tick"])
def test_incompatible_startup_preserves_current_and_never_geneses_or_publishes(monkeypatch, tmp_path, kind):
    body = retained_body()
    if kind == "old_voice_law":
        body._state["voice_version"] = 1
    elif kind == "missing_voice_law":
        del body._state["voice_version"]
    elif kind == "wrong_identity":
        body._state["identity"] = "c58a5b51-3d68-4ea4-85f0-fb63aa1c1f90"
    elif kind == "wrong_tick":
        body._state["tick"] += 1
    encoded = b"GLBODY01historical-body" if kind == "foreign_format" else body.encoded()
    production, pointer, before, world_calls = startup_fixture(monkeypatch, tmp_path, encoded)

    def no_reconciliation(*args, **kwargs):
        pytest.fail("refused startup must leave stored generations untouched")

    monkeypatch.setattr(PairedCurrentStore, "reconcile", no_reconciliation)
    with pytest.raises((RuntimeError, ValueError), match="unsupported|identity/tick"):
        production._restore_production_actor()
    assert not world_calls
    assert file_bytes(tmp_path) == before


def test_current_startup_restores_the_exact_pair_without_publication(monkeypatch, tmp_path):
    encoded = retained_body().encoded()
    production, pointer, before, world_calls = startup_fixture(monkeypatch, tmp_path, encoded)
    actor = production._restore_production_actor()
    assert actor.pointer == pointer
    assert actor.runtime.encoded() == encoded
    assert actor.world.encoded_snapshot() == WORLD_BYTES
    assert world_calls == [{"identity": IDENTITY, "encoded_world": WORLD_BYTES,
                            "migrate_physical_return": False}]
    assert file_bytes(tmp_path) == before


def test_changed_world_restore_cannot_publish_at_the_retained_tick(monkeypatch, tmp_path):
    encoded = retained_body().encoded()
    production, pointer, before, world_calls = startup_fixture(
        monkeypatch, tmp_path, encoded, world_successor=WORLD_BYTES + b"changed",
    )

    def no_reconciliation(*args, **kwargs):
        pytest.fail("refused startup must leave stored generations untouched")

    monkeypatch.setattr(PairedCurrentStore, "reconcile", no_reconciliation)
    with pytest.raises(RuntimeError, match="home-world restore changed canonical bytes"):
        production._restore_production_actor()
    assert len(world_calls) == 1
    assert file_bytes(tmp_path) == before
