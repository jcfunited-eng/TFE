"""Regression pins for the 2026-07-16 boot-fallback hotfixes (9b52514 +
fae2e4b) — none existed when the fixes shipped live.

Incident shape (seal 503 fail-back -> boot purgatory): a full save wrote
core at tick T2 but the organism pickle save failed, leaving the organism
artifact + its binding receipt at older tick T1.  The binding payload check
demanded exact equality with core's tick, so NO generation could load — a
zombie.  Separately, a young life that never wrote wave_atlas.npz could not
satisfy the validator that demanded it, and even after acceptance the
downstream required-proof gate re-rejected it.

Contracts pinned here:
  * (a) an organism binding tick OLDER than core loads: via an explicit
    state-file-ticks manifest row (manifest-consistent), and via the loud
    cold-skew acceptance when no manifest row covers the artifact —
    content integrity still enforced by the receipt's hash;
  * a hash-verified binding whose tick is NEWER than core still halts;
  * (b) absent wave_atlas.npz + absent binding receipt loads with the
    restore proof satisfied; present receipt + absent npz halts.
"""

import gzip
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


def _fresh_engine():
    guala = Guala()
    return guala


def _grow_and_save(state_dir, *, ticks=3):
    """Genesis + a little lived experience + one full (bound) save."""
    guala = _fresh_engine()
    guala.load_full_state(state_dir)
    assert guala._load_successful, guala._load_errors
    guala.read_sentence("the sun is warm", source="joe")
    guala.tick += ticks
    guala.save_full_state(state_dir)
    return guala


def _reload(state_dir):
    guala = _fresh_engine()
    guala.load_full_state(state_dir)
    return guala


def _core_data(state_dir):
    with open(os.path.join(state_dir, "guala_core.json")) as handle:
        return json.load(handle)


def _write_core(state_dir, core):
    with open(os.path.join(state_dir, "guala_core.json"), "w") as handle:
        json.dump(core, handle)


ORGANISM = "guala_organism.pkl.gz"
ORGANISM_BINDING = ORGANISM + ".binding.json"
WAVE_NPZ = "wave_atlas.npz"
WAVE_BINDING = WAVE_NPZ + ".binding.json"


def _make_organism_older_than_core(state_dir, tmp_path):
    """Reproduce the incident: full save at T1, stash the organism artifact
    + receipt, full save at T2, then put the T1 pair back (as if the T2
    organism save had failed).  Returns (t1, t2)."""
    guala = _grow_and_save(state_dir, ticks=3)
    t1 = guala.tick
    stash = str(tmp_path / "stash")
    os.makedirs(stash)
    shutil.copy(os.path.join(state_dir, ORGANISM), stash)
    shutil.copy(os.path.join(state_dir, ORGANISM_BINDING), stash)
    guala.tick += 5
    guala.save_full_state(state_dir)
    t2 = guala.tick
    shutil.copy(os.path.join(stash, ORGANISM), state_dir)
    shutil.copy(os.path.join(stash, ORGANISM_BINDING), state_dir)
    with open(os.path.join(state_dir, ORGANISM_BINDING)) as handle:
        assert json.load(handle)["saved_at_tick"] == t1
    return t1, t2


def test_older_cold_cycle_binding_loads_via_cold_skew(tmp_path, capsys):
    state = str(tmp_path / "state")
    t1, t2 = _make_organism_older_than_core(state, tmp_path)
    assert t1 < t2

    rebooted = _reload(state)
    printed = capsys.readouterr().out
    assert rebooted._load_successful, rebooted._load_errors
    # The loud cold-skew acceptance path fired (no manifest row covers the
    # organism artifact in a real save — only the .json stores are rows).
    assert "[cold-skew]" in printed
    assert ORGANISM in printed
    # Content really came from the older, hash-verified artifact.
    assert rebooted._binary_restore_status["organism"] is True


def test_older_binding_loads_when_manifest_row_confirms_it(tmp_path):
    state = str(tmp_path / "state")
    t1, _t2 = _make_organism_older_than_core(state, tmp_path)

    # Manifest-consistent variant: core's state-file-ticks manifest carries
    # the artifact's own real tick (what a manifest-aware save lane would
    # record).  The binding check must resolve through the manifest row.
    core = _core_data(state)
    core["data"]["state_file_ticks"][ORGANISM] = t1
    _write_core(state, core)

    rebooted = _reload(state)
    assert rebooted._load_successful, rebooted._load_errors
    assert rebooted._binary_restore_status["organism"] is True


def test_manifest_row_mismatch_still_halts(tmp_path):
    state = str(tmp_path / "state")
    t1, _t2 = _make_organism_older_than_core(state, tmp_path)

    core = _core_data(state)
    core["data"]["state_file_ticks"][ORGANISM] = t1 + 1  # lies about the tick
    _write_core(state, core)

    rebooted = _reload(state)
    assert not rebooted._load_successful
    assert any("binding tick mismatch" in err for err in rebooted._load_errors)


def test_newer_binding_than_core_still_halts(tmp_path):
    """Cold-skew accepts strictly OLDER only — a future artifact is a tear."""
    state = str(tmp_path / "state")
    guala = _grow_and_save(state, ticks=3)
    binding_path = os.path.join(state, ORGANISM_BINDING)
    with open(binding_path) as handle:
        binding = json.load(handle)
    # The receipt PAYLOAD claims a future tick (the envelope stays valid —
    # the payload check is the one under test).
    binding["data"]["saved_at_tick"] = guala.tick + 100
    with open(binding_path, "w") as handle:
        json.dump(binding, handle)

    rebooted = _reload(state)
    assert not rebooted._load_successful
    assert any("binding tick mismatch" in err for err in rebooted._load_errors)


# ── (b) wave-atlas: receipt is the truth for the npz requirement ────────────

def test_fresh_life_without_wave_atlas_loads_with_proof(tmp_path, monkeypatch,
                                                        capsys):
    state = str(tmp_path / "state")
    # Save WITHOUT a wave atlas (a young life that never wrote one) ...
    monkeypatch.delenv("WAVE_ATLAS_ENABLED", raising=False)
    _grow_and_save(state, ticks=2)
    assert not os.path.exists(os.path.join(state, WAVE_NPZ))
    assert not os.path.exists(os.path.join(state, WAVE_BINDING))

    # ... then boot WITH the wave atlas enabled: no npz + no receipt is
    # legitimately fresh — accepted loudly, restore proof satisfied.
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "1")
    rebooted = _reload(state)
    printed = capsys.readouterr().out
    assert rebooted._load_successful, rebooted._load_errors
    assert "no npz and no binding" in printed
    assert rebooted._binary_restore_status["wave_atlas"] is True


def test_receipt_without_npz_still_halts(tmp_path, monkeypatch):
    state = str(tmp_path / "state")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "1")
    guala = _grow_and_save(state, ticks=2)
    # The wave npz rides its own save lane (sleep/snapshot/periodic), not
    # save_full_state — run it explicitly to mint the npz + receipt.
    guala._save_wave_atlas(state)
    assert os.path.exists(os.path.join(state, WAVE_NPZ))
    assert os.path.exists(os.path.join(state, WAVE_BINDING))

    os.remove(os.path.join(state, WAVE_NPZ))  # receipt says it was written

    rebooted = _reload(state)
    assert not rebooted._load_successful
    assert any("wave_atlas.npz is missing" in err
               for err in rebooted._load_errors)


def test_manifest_row_one_tick_forward_skew_is_accepted_loudly(tmp_path, capsys):
    """2026-07-16 :662 supersede halt: a graceful mid-life stop saves
    guala_teaching.json one tick after its manifest row was recorded --
    same-cycle real data, not a tear. Bounded forward skew on the
    manifest branch must load; large gaps must still halt."""
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    g = Guala()
    g.add_corpus("seed", "Seed", ["the sun rises in the morning"])
    g.load_full_state(str(tmp_path))
    g.save_full_state(str(tmp_path))

    import json as _json
    core_path = tmp_path / "guala_core.json"
    teaching_path = tmp_path / "guala_teaching.json"
    core = _json.loads(core_path.read_text())
    teaching = _json.loads(teaching_path.read_text())
    row = core["data"]["state_file_ticks"]["guala_teaching.json"]
    teaching["saved_at_tick"] = row + 1
    teaching_path.write_text(_json.dumps(teaching))

    g2 = Guala()
    g2.add_corpus("seed", "Seed", ["the sun rises in the morning"])
    g2.load_full_state(str(tmp_path))
    assert getattr(g2, "_load_successful", False), getattr(g2, "_load_errors", [])
    assert "[manifest-skew] guala_teaching.json" in capsys.readouterr().out

    # A large forward gap is a genuinely mixed save set and must halt.
    teaching["saved_at_tick"] = row + 100000
    teaching_path.write_text(_json.dumps(teaching))
    g3 = Guala()
    g3.add_corpus("seed", "Seed", ["the sun rises in the morning"])
    g3.load_full_state(str(tmp_path))
    assert not getattr(g3, "_load_successful", True)
