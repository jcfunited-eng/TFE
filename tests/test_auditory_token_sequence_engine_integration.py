from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import struct
from dataclasses import replace

import pytest

import dsf_ai_service.app as app_module
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
    pcm_s16le_wav,
)
from dsf_ai_service.substrate.auditory_token_sequence import (
    TokenClassificationState,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


LEARNED_SAMPLES = 6_400
TRAILING_SAMPLES = 4_800


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pcm_tone(*, count: int, frequency_hz: int = 440) -> bytes:
    values = tuple(
        int(
            8_000
            * math.sin(
                2 * math.pi * frequency_hz * index / PCM_SAMPLE_RATE_HZ
            )
        )
        for index in range(count)
    )
    return struct.pack(f"<{len(values)}h", *values)


def _two_terminal_pcm() -> bytes:
    learned = _pcm_tone(count=LEARNED_SAMPLES)
    return (
        bytes(3_200 * 2)
        + learned
        + bytes(3_200 * 2)
        + learned
        + bytes(TRAILING_SAMPLES * 2)
    )


def _disable_background(monkeypatch) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY", "auditory-token-engine-test-key"
    )


def _teach_physical_form(engine: Guala) -> None:
    learned = _pcm_tone(count=LEARNED_SAMPLES)
    engine.teach_isolated_auditory_asset(
        pcm_s16le_wav(
            bytes(3_200 * 2) + learned + bytes(TRAILING_SAMPLES * 2)
        ),
        "written tutor label must not become sequence text",
    )


def _advance(
    engine: Guala,
    *,
    stream_id: str,
    epoch_ns: int,
    settle_tokens: bool = True,
):
    registry = AuditoryPCMStreamRegistry()
    opened = registry.open()
    expected_context = stream_id
    stream_id = opened["stream_id"]
    assert expected_context
    pcm = _two_terminal_pcm()
    accepted = registry.accept(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=epoch_ns,
        pcm_s16le=pcm,
    )
    sound = engine.process_sound_frame(
        pcm_s16le_wav(pcm),
        source="browser_microphone",
        source_anchor_ns=epoch_ns,
        source_time_end_ns=(
            epoch_ns + len(pcm) // 2 * 1_000_000_000 // PCM_SAMPLE_RATE_HZ
        ),
        auditory_pcm_continuity=accepted.receipt,
        auditory_pcm_s16le=pcm,
    )
    if settle_tokens:
        result = engine.advance_continuous_auditory_terminal(
            pcm_s16le=pcm,
            transport=accepted.receipt,
            settlement=sound["settlement"],
        )
        engine.close_auditory_pcm_stream(
            stream_id, release_terminal=False
        )
        return result
    original = engine._settle_released_auditory_token_sequence
    engine._settle_released_auditory_token_sequence = lambda _advance: None
    try:
        joint, advance = engine.advance_continuous_auditory_terminal(
            pcm_s16le=pcm,
            transport=accepted.receipt,
            settlement=sound["settlement"],
        )
    finally:
        del engine._settle_released_auditory_token_sequence
    engine.close_auditory_pcm_stream(stream_id, release_terminal=False)
    return joint, advance, original


def _states(engine: Guala) -> tuple[str, ...]:
    latest = engine.auditory_token_sequence_status()["latest"]
    assert latest is not None
    return tuple(
        occurrence["classification_state"]
        for occurrence in latest["occurrences"]
    )


def test_engine_sequence_transaction_is_atomic_classified_bounded_and_restartable(
    monkeypatch, tmp_path
) -> None:
    _disable_background(monkeypatch)
    engine = Guala()
    restarted = None
    try:
        engine._generate_genesis_identity(str(tmp_path))
        _teach_physical_form(engine)
        _joint, advance, settle = _advance(
            engine,
            stream_id="token-unknown",
            epoch_ns=1_000_000_000,
            settle_tokens=False,
        )
        assert len(advance.released_terminals) == 2
        assert advance.reply_candidate is None

        batch = engine._auditory_incremental_terminals.materialize_batch(
            advance
        )
        admitted = engine._auditory_token_sequence_authority.admit(
            batch.entries[0].event,
            batch.entries[0].auditory_l5,
        )
        before_token = engine._auditory_token_sequence_authority.snapshot()
        original_materialize = (
            engine._auditory_incremental_terminals.materialize_batch
        )
        mismatched_batch = replace(
            batch,
            entries=(
                replace(
                    batch.entries[0],
                    auditory_l5=batch.entries[1].auditory_l5,
                ),
                batch.entries[1],
            ),
        )
        monkeypatch.setattr(
            engine._auditory_incremental_terminals,
            "materialize_batch",
            lambda _advance: mismatched_batch,
        )
        with pytest.raises(ValueError, match="full field disagree"):
            settle(advance)
        assert engine._auditory_token_sequence_authority.snapshot() == before_token
        assert engine._auditory_incremental_terminals.status()[
            "issued_terminal_authorities"
        ] == 2
        monkeypatch.setattr(
            engine._auditory_incremental_terminals,
            "materialize_batch",
            original_materialize,
        )
        original_admit = engine._auditory_token_sequence_authority.admit
        calls = 0

        def fail_second(event, auditory_l5):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected second admission failure")
            return original_admit(event, auditory_l5)

        monkeypatch.setattr(
            engine._auditory_token_sequence_authority,
            "admit",
            fail_second,
        )
        with pytest.raises(RuntimeError, match="second admission failure"):
            settle(advance)
        assert engine._auditory_token_sequence_authority.snapshot() == before_token
        assert engine._latest_auditory_token_sequence_observation is None
        terminal_status = engine._auditory_incremental_terminals.status()
        assert terminal_status["issued_terminal_authorities"] == 2
        assert terminal_status["in_flight_terminal_authorities"] == 0

        monkeypatch.setattr(
            engine._auditory_token_sequence_authority,
            "admit",
            original_admit,
        )
        before_language = engine._causal_language_authority.snapshot()
        original_episode_admit = (
            engine._causal_language_authority.admit_episode
        )

        def fail_episode_admit(**_kwargs):
            raise RuntimeError("injected causal language admission failure")

        monkeypatch.setattr(
            engine._causal_language_authority,
            "admit_episode",
            fail_episode_admit,
        )
        with pytest.raises(RuntimeError, match="language admission failure"):
            settle(advance)
        assert engine._auditory_token_sequence_authority.snapshot() == before_token
        assert engine._causal_language_authority.snapshot() == before_language
        assert engine._latest_auditory_token_sequence_observation is None
        assert engine._latest_auditory_causal_language_observation is None
        assert engine._auditory_incremental_terminals.status()[
            "issued_terminal_authorities"
        ] == 2
        monkeypatch.setattr(
            engine._causal_language_authority,
            "admit_episode",
            original_episode_admit,
        )
        sequence = settle(advance)
        assert sequence is not None
        assert _states(engine) == (
            TokenClassificationState.UNKNOWN.value,
            TokenClassificationState.UNKNOWN.value,
        )
        causal_language = engine.auditory_causal_language_status()
        assert causal_language["latest"]["causal_intake_state"] == "unique"
        assert causal_language["latest"]["episode_state"] == "unknown"
        assert causal_language["latest"]["episode_reason"] == (
            "token_classification_not_unique"
        )
        assert engine._auditory_incremental_terminals.status()[
            "issued_terminal_authorities"
        ] == 0

        unique = engine._auditory_token_sequence_authority.issue_teacher_designation(
            admitted,
            token_class_id=_sha("spoken-token-one"),
            token_form="hello",
            nonce=_sha("unique-teacher-nonce"),
        )
        engine._auditory_token_sequence_authority.teach(admitted, unique)
        _advance(
            engine,
            stream_id="token-unique",
            epoch_ns=3_000_000_000,
        )
        assert _states(engine) == (
            TokenClassificationState.UNIQUE.value,
            TokenClassificationState.UNIQUE.value,
        )
        causal_language = engine.auditory_causal_language_status()
        assert causal_language["latest"]["episode_state"] == "unique"
        assert causal_language["latest"]["episode_stored"] is True
        assert causal_language["working_episode_count"] == 1

        ambiguous = (
            engine._auditory_token_sequence_authority.issue_teacher_designation(
                admitted,
                token_class_id=_sha("spoken-token-two"),
                token_form="hallo",
                nonce=_sha("ambiguous-teacher-nonce"),
            )
        )
        engine._auditory_token_sequence_authority.teach(admitted, ambiguous)
        binding_bytes = engine._auditory_token_sequence_authority.snapshot_bytes
        for index in range(3):
            _advance(
                engine,
                stream_id=f"token-ambiguous-{index}",
                epoch_ns=(5 + index * 2) * 1_000_000_000,
            )
            assert _states(engine) == (
                TokenClassificationState.AMBIGUOUS.value,
                TokenClassificationState.AMBIGUOUS.value,
            )
            assert engine._auditory_incremental_terminals.status()[
                "issued_terminal_authorities"
            ] == 0
            assert (
                engine._auditory_token_sequence_authority.snapshot_bytes
                == binding_bytes
            )

        payload = engine._teaching_persistence_payload()
        assert "tutor_label" not in json.dumps(
            payload["latest_auditory_token_sequence"]
        )
        assert "chi" not in json.dumps(
            payload["latest_auditory_token_sequence"]
        ).lower()
        tampered_observation = json.loads(json.dumps(
            payload["latest_auditory_token_sequence"]
        ))
        tampered_observation["sequence"]["occurrences"][0][
            "classification_state"
        ] = TokenClassificationState.UNKNOWN.value
        with pytest.raises(ValueError, match="classification .* changed"):
            engine._verify_auditory_token_sequence_observation(
                tampered_observation
            )
        engine.save_full_state(str(tmp_path))
        engine.strict_shutdown(timeout=30.0)
        engine = None

        restarted = Guala()
        restarted.load_full_state(
            str(tmp_path), require_exact_binary=True
        )
        assert restarted._load_successful, restarted._load_errors
        assert restarted.auditory_token_sequence_status() == (
            restarted.auditory_l5_status()["token_sequence"]
        )
        assert _states(restarted) == (
            TokenClassificationState.AMBIGUOUS.value,
            TokenClassificationState.AMBIGUOUS.value,
        )
        assert restarted._auditory_token_sequence_authority.binding_count == 2
        assert restarted.auditory_causal_language_status()[
            "working_episode_count"
        ] == 1
    finally:
        if engine is not None:
            engine.strict_shutdown(timeout=30.0)
        if restarted is not None:
            restarted.strict_shutdown(timeout=30.0)


def test_http_multi_release_exposes_order_without_joining_or_replying(
    monkeypatch,
) -> None:
    _disable_background(monkeypatch)
    engine = Guala()
    monkeypatch.setattr(app_module, "_guala", engine)
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    monkeypatch.setattr(app_module, "_converse_inflight", 0)
    monkeypatch.setattr(app_module, "_converse_window_started_at", 0.0)
    monkeypatch.setattr(
        app_module, "_auditory_pcm_streams", AuditoryPCMStreamRegistry()
    )
    monkeypatch.setattr(
        app_module,
        "_maybe_trigger_voice_reply",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("multi-terminal release entered conversation")
        ),
    )
    try:
        _teach_physical_form(engine)
        opened = asyncio.run(app_module.auditory_pcm_stream_open())
        pcm = _two_terminal_pcm()
        result = asyncio.run(app_module.sound_frame(app_module.GLMessage(
            text=base64.b64encode(pcm).decode("ascii"),
            source="browser_microphone",
            audio_encoding="pcm_s16le",
            audio_stream_id=opened["stream_id"],
            audio_sequence=0,
            audio_first_sample_index=0,
            audio_sample_count=len(pcm) // 2,
            audio_sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            audio_source_epoch_ms=1_000,
        )))

        assert result["ok"] is True
        continuity = result["pcm_continuity"]
        assert continuity["incremental_terminal_status"] == "released_unique"
        assert continuity["auditory_token_sequence_status"] == "settled"
        observation = continuity["auditory_token_sequence"]
        assert observation["occurrence_count"] == 2
        assert [item["ordinal"] for item in observation["occurrences"]] == [0, 1]
        assert "transcript" not in result
        assert result["spoken_word_recognition"]["recognized_form"] is None
        assert result["spoken_word_recognition"]["candidate_labels"] == []
        snapshot = engine.observation_snapshot()
        assert snapshot["auditory_token_sequence"]["status"] == "settled"
        assert snapshot["auditory_token_sequence"]["latest"] == observation
    finally:
        engine.strict_shutdown(timeout=30.0)
