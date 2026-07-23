"""Exact causal speech actuator output boundary in substrate_runner."""

import base64
import inspect
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dsf_ai_service.substrate_runner as runner
from dsf_ai_service.v4.gualaloom_v5_engine import TTS_MAX_CHARS


class _ObservedEngine:
    def __init__(self, *, observation_error=None):
        self.observation_error = observation_error
        self.observed_wavs = []
        self.failures = []
        self.events = []

    def observe_causal_speech_output(self, wav_bytes):
        self.observed_wavs.append(wav_bytes)
        if self.observation_error is not None:
            raise self.observation_error
        return {"status": "observed"}

    def report_causal_speech_output_failure(self, stage, error):
        self.failures.append((stage, error))
        return {"status": "retryable"}

    def _log_substrate_event(self, kind, **detail):
        self.events.append((kind, detail))


def test_existing_synthesize_voice_call_contract_is_unchanged():
    assert tuple(inspect.signature(runner._synthesize_voice).parameters) == (
        "text",
    )


def test_concurrent_synthesis_uses_private_paths_without_waveform_crosstalk(
    monkeypatch,
):
    both_syntheses_entered = threading.Barrier(2)
    observed_paths = []
    observed_paths_lock = threading.Lock()

    def synthesize_to_requested_path(command, **_kwargs):
        wav_path = command[command.index("-w") + 1]
        utterance = command[-1]
        with observed_paths_lock:
            observed_paths.append(wav_path)
        both_syntheses_entered.wait(timeout=5)
        with open(wav_path, "wb") as wav_file:
            wav_file.write(f"waveform:{utterance}".encode("utf-8"))

    monkeypatch.setattr(runner.subprocess, "run", synthesize_to_requested_path)
    results = {}
    errors = []

    def run_synthesis(key, utterance):
        try:
            results[key] = runner._synthesize_voice(utterance)
        except Exception as error:  # pragma: no cover - asserted below
            errors.append(error)

    first = threading.Thread(
        target=run_synthesis, args=("first", "first causal action")
    )
    second = threading.Thread(
        target=run_synthesis, args=("second", "second causal action")
    )
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert len(observed_paths) == 2
    assert observed_paths[0] != observed_paths[1]
    assert base64.b64decode(results["first"], validate=True) == (
        b"waveform:first causal action"
    )
    assert base64.b64decode(results["second"], validate=True) == (
        b"waveform:second causal action"
    )
    assert all(not os.path.exists(path) for path in observed_paths)


def test_causal_release_returns_same_base64_and_observes_exact_wav(
    monkeypatch,
):
    exact_wav = b"RIFF\x18\x00\x00\x00WAVEfmt exact-actuator-waveform"
    encoded = base64.b64encode(exact_wav).decode("ascii")
    engine = _ObservedEngine()
    monkeypatch.setattr(runner, "_guala", engine)
    monkeypatch.setattr(runner, "_synthesize_voice", lambda text: encoded)

    released = runner._synthesize_released_voice(
        "hello daddy", "causal_action_cycle_commit"
    )

    assert released == encoded
    assert engine.observed_wavs == [exact_wav]
    assert engine.failures == []
    assert engine.events == []


def test_non_causal_voice_behavior_does_not_enter_actuator_observer(
    monkeypatch,
):
    encoded = base64.b64encode(b"legacy-wave").decode("ascii")
    engine = _ObservedEngine()
    calls = []
    monkeypatch.setattr(runner, "_guala", engine)
    monkeypatch.setattr(
        runner,
        "_synthesize_voice",
        lambda text: calls.append(text) or encoded,
    )

    released = runner._synthesize_released_voice(
        "ordinary release", "assemblage_commit"
    )

    assert released == encoded
    assert calls == ["ordinary release"]
    assert engine.observed_wavs == []
    assert engine.failures == []


def test_overlength_causal_action_fails_before_synthesis_without_truncation(
    monkeypatch,
):
    engine = _ObservedEngine()
    synthesis_calls = []
    monkeypatch.setattr(runner, "_guala", engine)
    monkeypatch.setattr(
        runner,
        "_synthesize_voice",
        lambda text: synthesis_calls.append(text),
    )
    action = "x" * (TTS_MAX_CHARS + 1)

    with pytest.raises(RuntimeError, match="action_length_contract"):
        runner._synthesize_released_voice(
            action, "causal_action_cycle_commit"
        )

    assert synthesis_calls == []
    assert engine.observed_wavs == []
    assert engine.failures[0][0] == "action_length_contract"
    assert engine.events[0][0] == "causal_speech_output_error"
    assert engine.events[0][1]["n_chars"] == len(action)


def test_missing_causal_wav_is_reported_retryable_and_raises(monkeypatch):
    engine = _ObservedEngine()
    monkeypatch.setattr(runner, "_guala", engine)
    monkeypatch.setattr(runner, "_synthesize_voice", lambda text: None)

    with pytest.raises(RuntimeError, match="synthesis"):
        runner._synthesize_released_voice(
            "hello daddy", "causal_action_cycle_commit"
        )

    assert engine.observed_wavs == []
    assert engine.failures[0][0] == "synthesis"
    assert engine.events[0][0] == "causal_speech_output_error"


def test_invalid_causal_wav_transport_is_reported_and_never_observed(
    monkeypatch,
):
    engine = _ObservedEngine()
    monkeypatch.setattr(runner, "_guala", engine)
    monkeypatch.setattr(
        runner, "_synthesize_voice", lambda text: "not valid base64!"
    )

    with pytest.raises(RuntimeError, match="wav_decode"):
        runner._synthesize_released_voice(
            "hello daddy", "causal_action_cycle_commit"
        )

    assert engine.observed_wavs == []
    assert engine.failures[0][0] == "wav_decode"


def test_engine_observation_failure_is_reported_retryable_and_raises(
    monkeypatch,
):
    exact_wav = b"RIFF\x18\x00\x00\x00WAVEfailed-observation"
    engine = _ObservedEngine(
        observation_error=ValueError("auditory outcome rejected")
    )
    monkeypatch.setattr(runner, "_guala", engine)
    monkeypatch.setattr(
        runner,
        "_synthesize_voice",
        lambda text: base64.b64encode(exact_wav).decode("ascii"),
    )

    with pytest.raises(RuntimeError, match="engine_observation"):
        runner._synthesize_released_voice(
            "hello daddy", "causal_action_cycle_commit"
        )

    assert engine.observed_wavs == [exact_wav]
    assert engine.failures[0][0] == "engine_observation"
    assert "auditory outcome rejected" in engine.failures[0][1]
    assert engine.events[0][0] == "causal_speech_output_error"
