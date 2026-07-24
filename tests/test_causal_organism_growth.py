"""Durability and live-engine proof for causal organism plasticity."""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dsf_ai_service.substrate.causal_organism_growth import (
    CausalOrganismGrowthJournal,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _pcm(frequency: float) -> bytes:
    sample_rate = 16_000
    t = np.arange(4_096, dtype=np.float64) / sample_rate
    values = np.sin(2.0 * np.pi * frequency * t) * 0.35
    return np.asarray(
        np.rint(values * 32_767.0),
        dtype="<i2",
    ).tobytes()


def _prime_organism(guala: Guala) -> None:
    t = np.linspace(0.0, 2.0 * np.pi, 200)
    guala.organism.experience_word(
        "physical",
        {
            "auditory": np.sin(7.0 * t),
            "language": "physical",
            "visual": np.cos(5.0 * t),
        },
    )


def _configured_guala(monkeypatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "causal-organism-growth-test-key",
    )
    return Guala()


def test_journal_roundtrip_rejects_tampering(monkeypatch) -> None:
    guala = _configured_guala(monkeypatch)
    try:
        prepared = (
            guala._w1_companion_vocal_experience.prepare_episode(
                pcm_s16le=_pcm(220.0)
            )
        )
        settlement = prepared.prediction_blocks[0].causal_settlement
        journal = CausalOrganismGrowthJournal(
            authority_key=b"j" * 32,
        )
        admission = journal.admit_episode(
            (settlement,),
            engine_tick=17,
            active_organs=("em", "pr", "ep", "sf"),
        )
        assert len(admission.newly_journaled) == 1
        encoded = journal.encoded_snapshot()

        restored = CausalOrganismGrowthJournal(
            authority_key=b"j" * 32,
        )
        restored.restore_encoded(encoded)
        assert restored.status() == journal.status()

        record = json.loads(encoded.decode("utf-8"))
        record["payload"]["pending"][0]["engine_tick"] = 18
        tampered = json.dumps(
            record,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        with pytest.raises(ValueError, match="authority"):
            restored.restore_encoded(tampered)

        guala._w1_companion_vocal_experience.discard_episode(prepared)
    finally:
        guala.shutdown()


def test_companion_experience_grows_only_participating_organs(
    monkeypatch,
) -> None:
    guala = _configured_guala(monkeypatch)
    try:
        _prime_organism(guala)
        results = [
            guala.experience_companion_vocal_episode(_pcm(frequency))
            for frequency in (220.0, 330.0, 440.0, 550.0)
        ]
        guala._organism_growth_queue.join()

        snapshot = guala.organism.growth_snapshot()
        assert snapshot["total_divisions"] == 4
        assert snapshot["per_hemisphere"] == {
            "aff": 8,
            "em": 9,
            "ep": 9,
            "gp": 8,
            "pr": 9,
            "sc": 8,
            "sf": 9,
            "sv": 8,
        }
        assert all(
            result["causal_growth"]["active_organs"]
            == ["em", "pr", "ep", "sf"]
            for result in results
        )
        assert guala._causal_organism_growth.status()["pending"] == 4
        assert len(
            guala.organism.causal_growth_checkpoint_claim_ids()
        ) == 4
    finally:
        guala.shutdown()


def test_recurrent_companion_field_funds_no_additional_growth(
    monkeypatch,
) -> None:
    guala = _configured_guala(monkeypatch)
    try:
        pcm = _pcm(220.0)
        results = [
            guala.experience_companion_vocal_episode(pcm)
            for _index in range(3)
        ]
        guala._organism_growth_queue.join()

        assert [
            result["causal_growth"]["contributing_claims"]
            for result in results
        ] == [1, 0, 0]
        assert guala._causal_organism_growth.status()["pending"] == 1
        reservoirs = guala.organism.growth_snapshot()[
            "causal_growth_reservoirs"
        ]
        assert reservoirs == {
            "aff": "0/1",
            "em": "1/4",
            "ep": "1/4",
            "gp": "0/1",
            "pr": "1/4",
            "sc": "0/1",
            "sf": "1/4",
            "sv": "0/1",
        }
    finally:
        guala.shutdown()


def test_failed_hot_save_rolls_back_growth_journal(
    monkeypatch,
) -> None:
    guala = _configured_guala(monkeypatch)
    try:
        guala._authoritative_hot_generation_publisher = (
            lambda **_values: None
        )
        guala.save_hot_state = lambda _state_dir: (_ for _ in ()).throw(
            RuntimeError("injected growth durability failure")
        )

        with pytest.raises(
            RuntimeError,
            match="injected growth durability failure",
        ):
            guala.experience_companion_vocal_episode(
                _pcm(220.0),
                state_dir="unused",
            )

        assert guala._causal_organism_growth.status()["pending"] == 0
        assert guala._organism_growth_queue.unfinished_tasks == 0
        assert (
            guala.organism.causal_growth_checkpoint_claim_ids()
            == ()
        )
    finally:
        guala.shutdown()


def test_cold_checkpoint_acknowledges_exact_applied_claims(
    monkeypatch,
    tmp_path,
) -> None:
    state_dir = str(tmp_path / "cold")
    writer = _configured_guala(monkeypatch)
    try:
        _prime_organism(writer)
        for frequency in (220.0, 330.0, 440.0, 550.0):
            writer.experience_companion_vocal_episode(_pcm(frequency))
        writer._organism_growth_queue.join()
        assert writer._causal_organism_growth.status()["pending"] == 4
        assert len(
            writer.organism.causal_growth_checkpoint_claim_ids()
        ) == 4

        writer.save_full_state(state_dir)

        assert writer._causal_organism_growth.status()["pending"] == 0
        assert (
            writer.organism.causal_growth_checkpoint_claim_ids()
            == ()
        )
    finally:
        writer.shutdown()

    reader = _configured_guala(monkeypatch)
    try:
        reader.load_full_state(state_dir, require_exact_binary=True)
        assert reader._load_successful is True
        assert reader.organism.growth_snapshot()["total_divisions"] == 4
        assert reader._causal_organism_growth.status()["pending"] == 0
        assert reader._organism_growth_queue.unfinished_tasks == 0
    finally:
        reader.shutdown()


def test_hot_journal_replays_when_cold_graph_predates_claim(
    monkeypatch,
    tmp_path,
) -> None:
    state_dir = str(tmp_path / "hot-replay")
    writer = _configured_guala(monkeypatch)
    try:
        _prime_organism(writer)
        writer.save_full_state(state_dir)
        writer._authoritative_hot_generation_publisher = (
            lambda **_values: None
        )
        result = writer.experience_companion_vocal_episode(
            _pcm(220.0),
            state_dir=state_dir,
        )
        writer._organism_growth_queue.join()
        assert result["causal_growth"]["contributing_claims"] == 1
        assert writer._causal_organism_growth.status()["pending"] == 1
        assert writer.organism.growth_snapshot()[
            "causal_growth_reservoirs"
        ]["em"] == "1/4"
    finally:
        writer.shutdown()

    reader = _configured_guala(monkeypatch)
    try:
        reader.load_full_state(state_dir, require_exact_binary=True)
        assert reader._load_successful is True
        reader._organism_growth_queue.join()
        snapshot = reader.organism.growth_snapshot()
        assert snapshot["total_divisions"] == 0
        assert snapshot["causal_growth_reservoirs"]["em"] == "1/4"
        assert snapshot["causal_growth_reservoirs"]["pr"] == "1/4"
        assert snapshot["causal_growth_reservoirs"]["ep"] == "1/4"
        assert snapshot["causal_growth_reservoirs"]["sf"] == "1/4"
        assert len(
            reader.organism.causal_growth_checkpoint_claim_ids()
        ) == 1
    finally:
        reader.shutdown()
