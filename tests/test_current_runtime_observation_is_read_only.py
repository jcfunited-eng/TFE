from __future__ import annotations

from dsf_ai_service.v4.guala_physical_runtime import Guala


def test_repeated_truthful_observation_cannot_accumulate_learned_state(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "read-only-observation-owner-key-with-adequate-length",
    )

    organism = Guala()
    try:
        owner_state_before = organism._bounded_owner_state_bodies()
        event_sequence_before = organism._substrate_event_sequence
        world_before = organism._embodiment_world.observation_snapshot()
        first = organism.observation_snapshot()
        auditory = first["auditory_physical_experience"]
        assert auditory["available"] is True
        assert auditory["transcript_authority"] is False
        assert auditory["recognition_authority"] is False
        assert auditory["word_authority"] is False
        assert auditory["settled_l5_experience_count"] == 0
        assert auditory["latest_experience_id"] is None
        assert auditory["latest_stream_settlement_receipt_sha256"] is None

        for _ in range(1_000):
            assert organism.observation_snapshot() == first

        assert organism._bounded_owner_state_bodies() == owner_state_before
        assert organism._substrate_event_sequence == event_sequence_before
        assert (
            organism._embodiment_world.observation_snapshot()
            == world_before
        )
        assert organism.tick == first["observed_at_tick"]
    finally:
        organism.strict_shutdown(timeout=30.0)
