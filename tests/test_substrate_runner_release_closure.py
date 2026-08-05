import base64
import inspect
import io

import pytest
from PIL import Image

from dsf_ai_service import app as app_module
from dsf_ai_service import substrate_runner as runner
from dsf_ai_service.substrate.ring_buffer import InputRing


CURRENT_OPERATIONS = {
    "ring_write",
    "observation_snapshot",
    "embodied_action_experience",
    "ground_latest_sight_contact",
}


def test_runner_operation_closure_contains_only_current_physical_owners():
    assert set(runner.OP_HANDLERS) == CURRENT_OPERATIONS
    assert runner.HANDLERS is runner.OP_HANDLERS

    source = inspect.getsource(runner)
    for forbidden in (
        "gualaloom_post",
        "auditory_l5_teach",
        "force_dream",
        "cascade_monitor",
        "atlas_snapshot",
        "organ_brain",
        "scene_lanes",
        "addpicture",
        "addsound",
        "corpus_status",
        "filename",
        "title",
        "md5",
        "vocab",
        "motifs",
    ):
        assert forbidden not in source


def test_runner_unknown_and_nonphysical_transport_fail_closed(monkeypatch):
    class Owner:
        pass

    monkeypatch.setattr(runner, "_guala", Owner())
    for retired_or_unknown in (
        "status",
        "causal_inquiry_transient_act",
        "causal_inquiry_transient_consequence",
    ):
        with pytest.raises(ValueError, match="unknown op"):
            runner.dispatch(retired_or_unknown, {})

    previous = runner._input_ring
    runner._input_ring = InputRing(size=4)
    try:
        refused = runner.handle_ring_write({
            "kind": "text_input",
            "source": "browser",
            "data": {"text": "hello"},
        })
    finally:
        runner._input_ring = previous
    assert refused == {
        "ok": False,
        "error": "unsupported physical input event",
        "status_code": 422,
    }


def test_runner_observation_and_action_operations_return_owner_receipts(
    monkeypatch,
):
    action_payload = b"physical-command"

    class Owner:
        def observation_snapshot(self):
            return {
                "schema": "guala.observation_snapshot.v5",
                "snapshot_receipt_sha256": "a" * 64,
            }

        def durably_experience_embodied_action(self, **values):
            assert values["command_payload"] == action_payload
            return {
                "authority_receipt_sha256": "b" * 64,
            }

        def durably_ground_latest_retained_sight_to_contact(
            self,
            *,
            state_dir,
        ):
            assert state_dir == "/physical-state"
            return {
                "authority_receipt_sha256": "c" * 64,
            }

    monkeypatch.setattr(runner, "_guala", Owner())
    monkeypatch.setattr(runner, "STATE_DIR", "/physical-state")

    observation = runner.dispatch("observation_snapshot", {})
    assert observation["snapshot_receipt_sha256"] == "a" * 64

    action = runner.dispatch("embodied_action_experience", {
        "tutor_id": "physical-tutor",
        "nonce": "physical-nonce",
        "port_id": "W1-port",
        "command_payload_base64": base64.b64encode(
            action_payload
        ).decode("ascii"),
    })
    assert action == {
        "authority_receipt_sha256": "b" * 64,
    }

    grounding = runner.dispatch("ground_latest_sight_contact", {})
    assert grounding == {
        "authority_receipt_sha256": "c" * 64,
    }


def test_runner_sound_window_preserves_physical_interval(monkeypatch):
    calls = []
    wav_bytes = b"RIFF-physical-wav"

    class Owner:
        def process_sound_frame(self, supplied_wav, **values):
            calls.append((supplied_wav, values))
            return {
                "auditory_continuation_receipt": {
                    "receipt_sha256": "d" * 64,
                },
            }

    monkeypatch.setattr(runner, "_guala", Owner())
    monkeypatch.setattr(
        runner,
        "_decode_sound_window",
        lambda _data: wav_bytes,
    )

    result = runner._process_sound_window(
        {
            "seq": 9,
            "source": "mic:browser",
        },
        {
            "auditory_event_boundary": "ambient",
            "source_time_start_ns": 1_000,
            "source_time_end_ns": 2_000,
        },
    )

    assert result[
        "auditory_continuation_receipt"
    ]["receipt_sha256"] == "d" * 64
    assert calls == [(
        wav_bytes,
        {
            "source": "mic:browser",
            "source_anchor_ns": 1_000,
            "source_time_end_ns": 2_000,
            "auditory_event_boundary": "ambient",
        },
    )]


def test_app_imports_runner_helpers_and_decodes_physical_image():
    assert callable(runner._webm_to_wav_bytes)
    assert callable(runner._start_input_ring_consumer)
    assert callable(runner._start_background_thread)
    assert callable(runner.quiesce_background_loops)
    assert callable(runner.heartbeat_loop)

    image = Image.new("RGB", (4, 3), color=(30, 60, 90))
    encoded = io.BytesIO()
    image.save(encoded, format="PNG")
    decoded, grid, width, height = app_module.decode_image_bytes(
        encoded.getvalue()
    )
    assert decoded is not None
    assert grid.shape == (64, 64)
    assert (width, height) == (4, 3)


def test_runner_compatibility_heartbeat_has_no_external_surface(
    monkeypatch,
):
    opened = []

    def forbid_open(*args, **kwargs):
        opened.append((args, kwargs))
        raise AssertionError("heartbeat attempted external state")

    monkeypatch.setattr("builtins.open", forbid_open)
    assert runner.heartbeat_loop() is None
    assert opened == []
