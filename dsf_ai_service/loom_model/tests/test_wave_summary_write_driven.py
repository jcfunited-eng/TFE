"""Production-path tests for write-driven wave-summary organism proposals.

Decay changes retained strength but is not another sensory experience.  These
tests prove that actual physical-sense writes produce one bounded notification,
reinforcement produces another, language stays on its existing word path, and
background decay produces no organism proposal.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fake_guala():
    from dsf_ai_service.loom_model.embryo import Embryo

    enqueued = []
    guala = SimpleNamespace(
        organism=Embryo(brain_seed=42, seed_size=8, observable="event_count"),
        _enqueue_organism_sensory=(
            lambda hemi_id, signal, tick, input_chi=None:
            enqueued.append((hemi_id, signal, tick, input_chi))),
        _log_substrate_event=lambda *_args, **_kwargs: None,
    )
    return guala, enqueued


def test_actual_sensory_write_pushes_once_and_decay_does_not_replay():
    from dsf_ai_service.v4.wave_atlas import WaveAtlas
    from dsf_ai_service.substrate.wave_summary import (
        push_new_wave_writes_to_organism)

    atlas = WaveAtlas()
    guala, enqueued = _fake_guala()

    atlas.record("sight", 1, 100, tick=1, salience=10.0)
    payload = push_new_wave_writes_to_organism(guala, atlas, tick=1)
    assert payload is not None
    assert [item[0] for item in enqueued] == ["H0"]

    enqueued.clear()
    assert push_new_wave_writes_to_organism(guala, atlas, tick=2) is None
    assert enqueued == []

    atlas.tick_decay()
    assert push_new_wave_writes_to_organism(guala, atlas, tick=3) is None
    assert enqueued == []


def test_reinforcement_is_a_new_write_but_language_is_not_sensory_replay():
    from dsf_ai_service.v4.wave_atlas import WaveAtlas
    from dsf_ai_service.substrate.wave_summary import (
        push_new_wave_writes_to_organism)

    atlas = WaveAtlas()
    guala, enqueued = _fake_guala()

    atlas.record("modal_sound", 1, 200, tick=1, salience=10.0)
    push_new_wave_writes_to_organism(guala, atlas, tick=1)
    assert [item[0] for item in enqueued] == ["H1", "H6"]

    enqueued.clear()
    atlas.record("modal_sound", 1, 200, tick=2, salience=10.0)
    push_new_wave_writes_to_organism(guala, atlas, tick=2)
    assert [item[0] for item in enqueued] == ["H1", "H6"]

    enqueued.clear()
    atlas.record("subject", 2, 300, tick=3, salience=10.0)
    assert push_new_wave_writes_to_organism(guala, atlas, tick=3) is None
    assert enqueued == []


def test_only_the_band_with_a_new_write_is_pushed():
    from dsf_ai_service.v4.wave_atlas import WaveAtlas
    from dsf_ai_service.substrate.wave_summary import (
        push_new_wave_writes_to_organism)

    atlas = WaveAtlas()
    guala, enqueued = _fake_guala()

    atlas.record("sight", 1, 100, tick=1, salience=10.0)
    atlas.record("modal_sound", 2, 200, tick=1, salience=10.0)
    push_new_wave_writes_to_organism(guala, atlas, tick=1)
    assert sorted(item[0] for item in enqueued) == ["H0", "H1", "H6"]

    enqueued.clear()
    atlas.record("sight", 1, 100, tick=2, salience=10.0)
    push_new_wave_writes_to_organism(guala, atlas, tick=2)
    assert [item[0] for item in enqueued] == ["H0"]


if __name__ == "__main__":
    test_actual_sensory_write_pushes_once_and_decay_does_not_replay()
    test_reinforcement_is_a_new_write_but_language_is_not_sensory_replay()
    test_only_the_band_with_a_new_write_is_pushed()
    print("ALL PASS: test_wave_summary_write_driven")
