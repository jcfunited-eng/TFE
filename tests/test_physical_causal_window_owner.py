import threading

import pytest

import dsf_ai_service.substrate.window_manager as window_module
from dsf_ai_service.loom_model.structural_graph_state import (
    structural_registry_contract,
)
from dsf_ai_service.substrate.window_manager import (
    WindowCapacityRefusal,
    WindowIntegrityError,
    WindowManager,
    physical_topology_fact,
)


def _native(
    sense,
    topology_index,
    *,
    sensor_id,
    substream_id,
    signal=(0.25, -0.5, 0.75),
):
    return {
        "schema": "guala.native_sensory_input.v4",
        "sense": sense,
        "sensor_id": sensor_id,
        "substream_id": substream_id,
        "topology_index": topology_index,
        "coordinates": [["lane", str(topology_index)]],
        "physical_quantity": "normalized-pressure" if sense == "sound"
        else "normalized-light-intensity",
        "physical_unit": "normalized-full-scale",
        "causal_offsets_fraction": [[0, 1], [1, 100], [1, 50]],
        "normalized_signal": list(signal),
        "phase_turns": [0.0, 0.25, 0.5],
    }


def _manager(settle, **limits):
    tick = iter(range(100000))
    return WindowManager(
        log_event_fn=lambda *args, **kwargs: None,
        get_tick_fn=lambda: next(tick),
        settle_window_fn=settle,
        **limits,
    )


def _admit(manager, context_id, record):
    return manager.add_entry(
        modality=record["sense"],
        topology=physical_topology_fact(record),
        full_field=record,
        context_id=context_id,
        source_tag="test:physical",
    )


def test_continuous_mono_transactions_release_every_owned_byte():
    settled = []
    manager = _manager(settled.append)
    for index in range(256):
        context_id = f"mono:{index}"
        manager.begin_context(
            context_id,
            "sound",
            context_detail={
                "source_time_start_ns": index * 20_000_000,
                "source_time_end_ns": (index + 1) * 20_000_000,
            },
        )
        record = _native(
            "sound",
            0,
            sensor_id="mono-mic",
            substream_id="mono-pressure",
        )
        _admit(manager, context_id, record)
        manager.end_context(context_id, "sound_frame_complete")
        assert manager.resource_stats()["total_owned_bytes"] == 0
    assert len(settled) == 256
    assert all(item["entries"][0]["full_field"]["sense"] == "sound"
               for item in settled)


def test_binaural_and_audiovisual_transactions_preserve_order_and_topology():
    settled = []
    manager = _manager(settled.append)
    manager.begin_context("binaural", "sound")
    left = _native(
        "sound", 0, sensor_id="head", substream_id="left-pressure")
    right = _native(
        "sound", 1, sensor_id="head", substream_id="right-pressure",
        signal=(0.1, -0.4, 0.8))
    _admit(manager, "binaural", left)
    _admit(manager, "binaural", right)
    manager.end_context("binaural")

    manager.begin_context("av", "audiovisual")
    sight = _native(
        "sight", 0, sensor_id="retina", substream_id="fovea")
    _admit(manager, "av", sight)
    _admit(manager, "av", left)
    manager.end_context("av")

    assert [
        item["full_field"]["substream_id"]
        for item in settled[0]["entries"]
    ] == ["left-pressure", "right-pressure"]
    assert [
        item["modality"] for item in settled[1]["entries"]
    ] == ["sight", "sound"]
    assert settled[1]["entries"][0]["topology"] == (
        physical_topology_fact(sight)
    )


def test_capacity_refusal_rolls_back_context_and_aggregate_bytes():
    manager = _manager(
        lambda record: None,
        max_total_open_bytes=1300,
        max_context_bytes=900,
    )
    manager.begin_context("one")
    before = manager.resource_stats()
    oversized = _native(
        "sound",
        0,
        sensor_id="mono",
        substream_id="large",
        signal=tuple(index / 10 for index in range(300)),
    )
    with pytest.raises(WindowCapacityRefusal):
        _admit(manager, "one", oversized)
    after = manager.resource_stats()
    assert after["open_context_bytes"] == before["open_context_bytes"]
    assert manager.current is not None
    assert manager.current.entries == []

    manager.begin_context("two")
    aggregate_before = manager.resource_stats()["open_context_bytes"]
    with pytest.raises(WindowCapacityRefusal):
        manager.begin_context(
            "three",
            context_detail={"padding": "x" * 1000},
        )
    assert manager.open_context_ids() == ("one", "two")
    assert manager.resource_stats()["open_context_bytes"] == aggregate_before


def test_failed_settlement_is_immutable_retryable_and_discardable():
    attempts = []

    def settle(record):
        attempts.append(record)
        if len(attempts) == 1:
            raise RuntimeError("settlement failed")
        return "published"

    manager = _manager(settle)
    manager.begin_context("retry")
    record = _native(
        "sound", 0, sensor_id="mono", substream_id="pressure")
    _admit(manager, "retry", record)
    with pytest.raises(RuntimeError, match="settlement failed"):
        manager.end_context("retry")
    first = attempts[0]
    with pytest.raises(WindowIntegrityError):
        _admit(manager, "retry", record)
    window_id, result = manager.end_context(
        "retry", return_settlement=True)
    assert window_id == first["window_id"]
    assert attempts[1] == first
    assert result == "published"
    assert manager.resource_stats()["total_owned_bytes"] == 0

    manager.begin_context("discard")
    _admit(manager, "discard", record)
    manager.discard_unsettled_context("discard")
    assert manager.resource_stats()["total_owned_bytes"] == 0


def test_settlement_concurrency_fails_closed():
    entered = threading.Event()
    release = threading.Event()

    def settle(record):
        entered.set()
        assert release.wait(2)

    manager = _manager(settle)
    manager.begin_context("concurrent")
    record = _native(
        "sound", 0, sensor_id="mono", substream_id="pressure")
    _admit(manager, "concurrent", record)
    thread = threading.Thread(
        target=lambda: manager.end_context("concurrent"))
    thread.start()
    assert entered.wait(2)
    with pytest.raises(WindowIntegrityError):
        manager.end_context("concurrent")
    with pytest.raises(WindowIntegrityError):
        _admit(manager, "concurrent", record)
    with pytest.raises(WindowIntegrityError):
        manager.discard_unsettled_context("concurrent")
    release.set()
    thread.join(2)
    assert not thread.is_alive()
    assert manager.resource_stats()["total_owned_bytes"] == 0


def test_owner_exposes_no_legacy_or_durable_state_surface():
    manager = _manager(lambda record: None)
    forbidden = {
        "windows",
        "closed_window",
        "window_ids",
        "window_metadata",
        "snapshot",
        "restore",
        "configure_wal",
        "lookup_chi",
        "chi_index",
        "atlas",
        "cache",
        "wal",
    }
    assert forbidden.isdisjoint(vars(manager))
    assert all(not hasattr(manager, name) for name in forbidden)
    assert manager.resource_stats()["total_owned_bytes"] == 0
    graph_contract = structural_registry_contract()
    encoded_contract = repr(graph_contract).lower()
    assert "bindingwindow" not in encoded_contract
    assert "windowentry" not in encoded_contract
    assert "windowmanager" not in encoded_contract


def test_wall_clock_cannot_change_owned_record_capacity_or_settlement(
    monkeypatch,
):
    records = []
    open_events = []

    def run(wall_clock):
        monkeypatch.setattr(
            window_module.time,
            "time",
            lambda: wall_clock,
        )
        ticks = iter((11, 12, 13))
        manager = WindowManager(
            log_event_fn=lambda kind, **event: open_events.append(
                (kind, event)
            ),
            get_tick_fn=lambda: next(ticks),
            settle_window_fn=lambda record: records.append(record),
        )
        manager.begin_context(
            "same-context",
            "sound",
            context_detail={
                "source_time_start_ns": 100,
                "source_time_end_ns": 200,
            },
        )
        record = _native(
            "sound",
            0,
            sensor_id="mono",
            substream_id="pressure",
        )
        _admit(manager, "same-context", record)
        before_close = manager.resource_stats()["open_context_bytes"]
        manager.end_context("same-context", "complete")
        return before_close

    first_bytes = run(1.25)
    second_bytes = run(99_999_999.75)

    assert first_bytes == second_bytes
    assert records[0] == records[1]
    assert "opened_wall_clock" not in records[0]
    assert "closed_wall_clock" not in records[0]
    assert {
        event["operational_wall_clock"]
        for kind, event in open_events
        if kind == "window_opened"
    } == {1.25, 99_999_999.75}
