"""
GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1: unit tests for the
seed_loader.py rich/programmatic loader enhancement (load_seed_layered,
SeedLoadProgress, chunked background programmatic load). Local-only --
Embryo() + WaveAtlas() stand-in substrate, no deployed target (this
dispatch is generation-only, no production deployment).
"""

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _make_substrate():
    from dsf_ai_service.loom_model.embryo import Embryo
    from dsf_ai_service.v4.wave_atlas import WaveAtlas

    class _Substrate:
        def __init__(self):
            self.organism = Embryo(brain_seed=42)
            self.wave_atlas = WaveAtlas()

    return _Substrate()


def _write_seed(path, n_words, prefix="w"):
    entries = [
        {
            "word": f"{prefix}{i}",
            "chi": 1000 + i,
            "grounding": {"visual": 1000 + i},
            "hemisphere_affinity": ["sf", "aff"],
            "initial_strength": 1.0,
        }
        for i in range(n_words)
    ]
    with open(path, "w") as f:
        json.dump({"version": "v1", "vocabulary_entries": entries,
                   "grammatical_patterns": [], "semantic_networks": []}, f)
    return entries


def test_load_seed_layered_rich_only(tmp_path=None):
    from dsf_ai_service.substrate.seed_loader import load_seed_layered

    tmp = tempfile.mkdtemp()
    rich_path = os.path.join(tmp, "rich.seed.json")
    _write_seed(rich_path, 10, prefix="r")

    substrate = _make_substrate()
    progress = load_seed_layered(rich_path, substrate, programmatic_path=None)

    assert progress.rich_done is True
    assert progress.rich_report.ok is True
    assert progress.rich_report.vocabulary_loaded == 10
    assert progress.programmatic_done is True  # no programmatic path -> immediately done
    assert progress.programmatic_total == 0
    print("test_load_seed_layered_rich_only: PASS")


def test_load_seed_layered_with_programmatic():
    from dsf_ai_service.substrate.seed_loader import load_seed_layered, verify_seed_integrity

    tmp = tempfile.mkdtemp()
    rich_path = os.path.join(tmp, "rich.seed.json")
    prog_path = os.path.join(tmp, "programmatic.seed.json")
    _write_seed(rich_path, 10, prefix="r")
    _write_seed(prog_path, 25, prefix="p")

    substrate = _make_substrate()
    progress = load_seed_layered(rich_path, substrate, programmatic_path=prog_path, chunk_size=5)

    assert progress.rich_done is True
    assert progress.rich_report.vocabulary_loaded == 10

    deadline = time.time() + 10
    while not progress.programmatic_done and time.time() < deadline:
        time.sleep(0.05)

    assert progress.programmatic_done is True, "background programmatic load did not finish in time"
    assert progress.programmatic_report.ok is True
    assert progress.programmatic_report.vocabulary_loaded == 25
    assert progress.programmatic_total == 25
    assert progress.programmatic_loaded == 25

    rich_integrity = verify_seed_integrity(substrate, seed_path=rich_path)
    assert rich_integrity.ok is True
    assert rich_integrity.words_verified == 10

    prog_integrity = verify_seed_integrity(substrate, seed_path=prog_path)
    assert prog_integrity.ok is True
    assert prog_integrity.words_verified == 25

    print("test_load_seed_layered_with_programmatic: PASS")


def test_progress_as_dict():
    from dsf_ai_service.substrate.seed_loader import SeedLoadProgress

    p = SeedLoadProgress()
    p.rich_done = True
    p.programmatic_total = 200
    p.programmatic_loaded = 50
    d = p.as_dict()
    assert d["rich_complete"] is True
    assert d["programmatic_percent"] == 25.0
    assert d["programmatic_complete"] is False
    print("test_progress_as_dict: PASS")


if __name__ == "__main__":
    test_load_seed_layered_rich_only()
    test_load_seed_layered_with_programmatic()
    test_progress_as_dict()
    print("ALL PASS")
