"""Current whole-organism persistence and causal-dirty invariants."""

import threading

import pytest

from dsf_ai_service.v4.guala_physical_runtime import Guala


def _bare_guala():
    guala = object.__new__(Guala)
    guala._persistence_lock = threading.RLock()
    guala.lock = threading.RLock()
    guala.tick = 0
    guala._last_save_tick = 0
    guala._last_cold_save_tick = 0
    guala._last_save_timestamp = None
    guala._cold_checkpoint_established = False
    return guala


def test_persistence_transaction_serializes_and_reenters():
    guala = _bare_guala()
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()
    errors = []

    def first():
        try:
            with guala.persistence_transaction():
                first_entered.set()
                assert release_first.wait(2.0)
                with guala.persistence_transaction():
                    pass
        except BaseException as error:
            errors.append(error)

    def second():
        try:
            with guala.persistence_transaction():
                second_entered.set()
        except BaseException as error:
            errors.append(error)

    first_thread = threading.Thread(target=first)
    second_thread = threading.Thread(target=second)
    first_thread.start()
    assert first_entered.wait(1.0)
    second_thread.start()
    assert not second_entered.wait(0.1)

    release_first.set()
    first_thread.join(2.0)
    second_thread.join(2.0)
    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert second_entered.is_set()
    assert not errors


def test_settled_hot_checkpoint_requires_one_new_causal_tick():
    guala = _bare_guala()
    guala._last_save_timestamp = "2026-08-01T00:00:00Z"

    with pytest.raises(
        RuntimeError,
        match="exclusive settled snapshot authority",
    ):
        guala.settled_hot_persistence_checkpoint_required()

    with guala.settled_external_persistence_transaction():
        assert not guala.settled_hot_persistence_checkpoint_required()

    with guala._engine_mutation_scope("test-causal-mutation"):
        pass
    with guala.settled_external_persistence_transaction():
        assert guala.settled_hot_persistence_checkpoint_required()

    guala._last_save_tick = guala.tick
    with guala.settled_external_persistence_transaction():
        assert not guala.settled_hot_persistence_checkpoint_required()


def test_never_persisted_genesis_requires_hot_checkpoint():
    guala = _bare_guala()
    with guala.settled_external_persistence_transaction():
        assert guala.settled_hot_persistence_checkpoint_required()


def test_settled_cold_checkpoint_requires_new_causal_tick():
    guala = _bare_guala()
    guala._cold_checkpoint_established = True

    with pytest.raises(
        RuntimeError,
        match="exclusive settled snapshot authority",
    ):
        guala.settled_cold_persistence_checkpoint_required()

    with guala.settled_external_persistence_transaction():
        assert not guala.settled_cold_persistence_checkpoint_required()

    with guala._engine_mutation_scope("test-cold-causal-mutation"):
        pass
    with guala.settled_external_persistence_transaction():
        assert guala.settled_cold_persistence_checkpoint_required()

    guala._last_cold_save_tick = guala.tick
    with guala.settled_external_persistence_transaction():
        assert not guala.settled_cold_persistence_checkpoint_required()


def test_genesis_without_cold_authority_requires_cold_checkpoint():
    guala = _bare_guala()
    with guala.settled_external_persistence_transaction():
        assert guala.settled_cold_persistence_checkpoint_required()


def test_loaded_hot_overlay_retains_older_cold_authority():
    guala = _bare_guala()
    guala.tick = 9
    guala._last_save_tick = 9
    guala._last_save_timestamp = "2026-08-01T00:00:00Z"
    guala._load_successful = True

    guala.establish_loaded_cold_checkpoint(
        authoritative_tick=4,
    )

    with guala.settled_external_persistence_transaction():
        assert not guala.settled_hot_persistence_checkpoint_required()
        assert guala.settled_cold_persistence_checkpoint_required()


def test_loaded_cold_authority_cannot_be_newer_than_live_state():
    guala = _bare_guala()
    guala.tick = 9
    guala._last_save_tick = 9
    guala._last_save_timestamp = "2026-08-01T00:00:00Z"
    guala._load_successful = True

    with pytest.raises(
        RuntimeError,
        match="newer than the loaded organism",
    ):
        guala.establish_loaded_cold_checkpoint(
            authoritative_tick=10,
        )
