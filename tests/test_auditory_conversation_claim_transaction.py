"""Atomic ownership tests for one heard-language conversation claim."""

import copy
import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from dsf_ai_service.substrate.exact_causal_experience import (
    MAX_CAUSAL_RESERVATION_WAITERS,
)
from tests.test_auditory_causal_conversation_boundary import _issue, _terminal
from tests.test_exact_causal_experience import _boundary


@pytest.fixture
def guala(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    try:
        yield engine
    finally:
        engine.shutdown()


def _assert_restored_and_retry(guala, terminal, prior_remembered):
    registry = guala._auditory_incremental_terminals
    status = registry.status()
    assert status["issued_terminal_authorities"] == 1
    assert status["in_flight_terminal_authorities"] == 0
    assert guala._latest_auditory_causal_event_record == prior_remembered
    assert (
        f"causal-experience:{terminal.event_id}"
        not in guala.window_manager.open_context_ids()
    )

    guala.read_sentence(
        terminal.tutor_label,
        source="auditory:unresolved_source",
        causal_intake=terminal,
    )

    status = registry.status()
    assert status["issued_terminal_authorities"] == 0
    assert status["in_flight_terminal_authorities"] == 0
    assert guala._latest_auditory_causal_event_record == terminal.as_record()


def _prior_record(guala):
    prior = _terminal("prior remembered auditory event").as_record()
    guala._latest_auditory_causal_event_record = copy.deepcopy(prior)
    return prior


def test_pre_context_failure_restores_exact_issued_authority(
        guala, monkeypatch):
    terminal = _issue(guala, _terminal("pre context failure"))
    prior = _prior_record(guala)
    real_begin = guala.window_manager.begin_context
    failed = False

    def fail_once(*args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("injected pre-context failure")
        return real_begin(*args, **kwargs)

    monkeypatch.setattr(guala.window_manager, "begin_context", fail_once)
    with pytest.raises(RuntimeError, match="injected pre-context failure"):
        guala.read_sentence(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )
    _assert_restored_and_retry(guala, terminal, prior)


def test_mid_read_failure_restores_exact_issued_authority(
        guala, monkeypatch):
    terminal = _issue(guala, _terminal("mid read failure"))
    prior = _prior_record(guala)
    real_read_word = guala.read_word
    failed = False

    def fail_once(*args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("injected mid-read failure")
        return real_read_word(*args, **kwargs)

    monkeypatch.setattr(guala, "read_word", fail_once)
    with pytest.raises(RuntimeError, match="injected mid-read failure"):
        guala.read_sentence(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )
    _assert_restored_and_retry(guala, terminal, prior)


def test_settlement_failure_discards_context_and_restores_authority(
        guala, monkeypatch):
    terminal = _issue(guala, _terminal("settlement failure"))
    prior = _prior_record(guala)
    real_settle = guala.window_manager._settle_window
    failed = False

    def fail_once(record):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("injected settlement failure")
        return real_settle(record)

    monkeypatch.setattr(guala.window_manager, "_settle_window", fail_once)
    with pytest.raises(RuntimeError, match="injected settlement failure"):
        guala.read_sentence(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )
    _assert_restored_and_retry(guala, terminal, prior)


def test_post_completion_failure_reopens_exact_authority(
        guala, monkeypatch):
    terminal = _issue(guala, _terminal("completion failure"))
    prior = _prior_record(guala)
    registry = guala._auditory_incremental_terminals
    real_complete = registry.complete_claim
    completed_claims = []

    def fail_during_completion(claim, settlement, **_kwargs):
        completed_claims.append(claim)
        return real_complete(
            claim,
            settlement,
            commit_settlement=lambda: (_ for _ in ()).throw(
                RuntimeError("injected completion failure")
            ),
        )

    monkeypatch.setattr(registry, "complete_claim", fail_during_completion)
    with pytest.raises(RuntimeError, match="injected completion failure"):
        guala.read_sentence(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )
    assert completed_claims[0].lifecycle == "rolled_back"
    monkeypatch.setattr(registry, "complete_claim", real_complete)
    _assert_restored_and_retry(guala, terminal, prior)


def test_claim_reservation_rejects_concurrent_claim_and_double_completion(
        guala, monkeypatch):
    terminal = _issue(guala, _terminal("single reservation"))
    registry = guala._auditory_incremental_terminals
    first = registry.claim(terminal)

    with pytest.raises(ValueError, match="already claimed"):
        registry.claim(terminal)

    registry.rollback_claim(first)
    with pytest.raises(ValueError, match="already rolled back"):
        registry.rollback_claim(first)

    captured = []
    real_claim = registry.claim

    def capture_claim(event):
        claim = real_claim(event)
        captured.append(claim)
        return claim

    monkeypatch.setattr(registry, "claim", capture_claim)
    guala.read_sentence(
        terminal.tutor_label,
        source="auditory:unresolved_source",
        causal_intake=terminal,
    )
    claim = captured[0]
    with pytest.raises(ValueError, match="already settled"):
        registry.complete_claim(claim, claim.causal_settlement)


def test_remember_preparation_failure_restores_uncommitted_authority(
        guala, monkeypatch):
    terminal = _issue(guala, _terminal("remember failure"))
    prior = _prior_record(guala)

    def fail_remember_preparation(_record):
        raise RuntimeError("injected remember preparation failure")

    monkeypatch.setattr(
        guala,
        "_canonical_auditory_causal_event_record",
        fail_remember_preparation,
    )
    with pytest.raises(
        RuntimeError, match="injected remember preparation failure"
    ):
        guala.read_sentence(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )

    status = guala._auditory_incremental_terminals.status()
    assert status["issued_terminal_authorities"] == 1
    assert status["in_flight_terminal_authorities"] == 0
    assert guala._latest_auditory_causal_event_record == prior
    assert guala._causal_experience_owner.status()["settled"] == 0
    assert guala._causal_settlement_accepted == 0


def test_rollback_restores_original_authority_position(guala):
    first_terminal = _issue(guala, _terminal("authority order first"))
    registry = guala._auditory_incremental_terminals
    with registry._lock:
        original_order = tuple(registry._authority_order)

    first_claim = registry.claim(first_terminal)
    registry.rollback_claim(first_claim)

    with registry._lock:
        assert tuple(registry._authority_order) == original_order
        assert tuple(registry._issued) == original_order
    assert original_order == (first_terminal.event_id,)


@pytest.mark.parametrize("phased", ("0", "1"))
def test_emission_failure_restores_utterance_for_exact_retry(
        guala, monkeypatch, phased):
    monkeypatch.setenv("CONVERSE_PHASED", phased)
    terminal = _issue(guala, _terminal(f"emission failure {phased}"))
    prior = _prior_record(guala)
    real_emit = guala._emit_from_invariants

    def fail_emission(*_args, **_kwargs):
        raise RuntimeError("injected emission failure")

    monkeypatch.setattr(guala, "_emit_from_invariants", fail_emission)
    with pytest.raises(RuntimeError, match="injected emission failure"):
        guala.converse(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )

    status = guala._auditory_incremental_terminals.status()
    assert status["issued_terminal_authorities"] == 1
    assert status["in_flight_terminal_authorities"] == 0
    assert guala._latest_auditory_causal_event_record == prior
    assert guala._causal_experience_owner.status()["settled"] == 0
    assert guala._causal_settlement_accepted == 0
    assert guala._causal_action_owner.status()["working_experiences"] == 0

    monkeypatch.setattr(guala, "_emit_from_invariants", real_emit)
    turn = guala.converse(
        terminal.tutor_label,
        source="auditory:unresolved_source",
        causal_intake=terminal,
    )
    assert turn.causal_experience_id == terminal.event_id
    assert guala._auditory_incremental_terminals.status()[
        "issued_terminal_authorities"
    ] == 0
    assert guala._causal_experience_owner.status()["settled"] == 1


@pytest.mark.parametrize("log_boundary", ("owner", "engine"))
def test_final_settlement_log_failure_is_nonfatal_after_atomic_commit(
        guala, monkeypatch, log_boundary):
    terminal = _issue(guala, _terminal(f"final log failure {log_boundary}"))
    if log_boundary == "owner":
        monkeypatch.setattr(
            guala._causal_experience_owner,
            "_log_event",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("injected owner final log failure")
            ),
        )
    else:
        real_log = guala._log_substrate_event

        def fail_accept_log(event_kind, **detail):
            if event_kind == "causal_experience_accepted":
                raise RuntimeError("injected engine final log failure")
            return real_log(event_kind, **detail)

        monkeypatch.setattr(guala, "_log_substrate_event", fail_accept_log)

    turn = guala.converse(
        terminal.tutor_label,
        source="auditory:unresolved_source",
        causal_intake=terminal,
    )

    assert turn.causal_experience_id == terminal.event_id
    status = guala._auditory_incremental_terminals.status()
    assert status["issued_terminal_authorities"] == 0
    assert status["in_flight_terminal_authorities"] == 0
    assert guala._causal_experience_owner.status()["settled"] == 1
    assert guala._causal_settlement_accepted == 1
    assert guala._causal_action_owner.status()["working_experiences"] == 1
    assert guala._latest_auditory_causal_event_record == terminal.as_record()
    with pytest.raises(ValueError, match="not issued or was already consumed"):
        guala._auditory_incremental_terminals.claim(terminal)


def test_concurrent_camera_settlement_waits_for_deferred_conversation(
        guala, monkeypatch):
    monkeypatch.setenv("CONVERSE_PHASED", "1")
    terminal = _issue(guala, _terminal("reserved causal ordering"))
    emit_entered = threading.Event()
    release_emit = threading.Event()
    ambient_started = threading.Event()
    ambient_done = threading.Event()
    errors = []
    turns = []
    real_emit = guala._emit_from_invariants

    def blocked_emit(*args, **kwargs):
        emit_entered.set()
        if not release_emit.wait(5.0):
            raise RuntimeError("test did not release deferred emission")
        return real_emit(*args, **kwargs)

    def converse_worker():
        try:
            turns.append(guala.converse(
                terminal.tutor_label,
                source="auditory:unresolved_source",
                causal_intake=terminal,
            ))
        except BaseException as error:
            errors.append(error)

    def camera_worker():
        ambient_started.set()
        try:
            guala._causal_experience_owner.settle(
                _boundary("concurrent-camera-settlement"),
                routing_chis=(7,),
                source_tags=("camera",),
            )
        except BaseException as error:
            errors.append(error)
        finally:
            ambient_done.set()

    monkeypatch.setattr(guala, "_emit_from_invariants", blocked_emit)
    conversation = threading.Thread(target=converse_worker)
    conversation.start()
    assert emit_entered.wait(5.0)
    assert guala._causal_experience_owner.status()[
        "prepared_reservation"
    ] == 1

    camera = threading.Thread(target=camera_worker)
    camera.start()
    assert ambient_started.wait(1.0)
    deadline = time.monotonic() + 2.0
    while (
        guala._causal_experience_owner.status()["reservation_waiters"] != 1
        and time.monotonic() < deadline
    ):
        time.sleep(0.005)
    assert guala._causal_experience_owner.status()["reservation_waiters"] == 1
    assert not ambient_done.is_set()

    release_emit.set()
    conversation.join(5.0)
    camera.join(5.0)
    assert not conversation.is_alive()
    assert not camera.is_alive()
    assert errors == []
    assert len(turns) == 1
    assert turns[0].causal_experience_id == terminal.event_id
    owner_status = guala._causal_experience_owner.status()
    assert owner_status["settled"] == 2
    assert owner_status["prepared_reservation"] == 0
    assert owner_status["reservation_waiters"] == 0


def test_reservation_waiters_are_bounded_and_release_without_leaks(
        guala, monkeypatch):
    monkeypatch.setenv("CONVERSE_PHASED", "1")
    terminal = _issue(guala, _terminal("bounded reservation waiters"))
    emit_entered = threading.Event()
    release_emit = threading.Event()
    conversation_errors = []
    turns = []
    waiter_results = []
    waiter_errors = []
    real_emit = guala._emit_from_invariants

    def blocked_emit(*args, **kwargs):
        emit_entered.set()
        if not release_emit.wait(10.0):
            raise RuntimeError("test did not release bounded emission")
        return real_emit(*args, **kwargs)

    def converse_worker():
        try:
            turns.append(guala.converse(
                terminal.tutor_label,
                source="auditory:unresolved_source",
                causal_intake=terminal,
            ))
        except BaseException as error:
            conversation_errors.append(error)

    boundaries = tuple(
        _boundary(f"bounded-reservation-waiter-{index}")
        for index in range(MAX_CAUSAL_RESERVATION_WAITERS + 3)
    )

    def settlement_worker(index):
        try:
            with guala._engine_mutation_scope(
                    f"bounded-reservation-waiter-{index}"):
                waiter_results.append(
                    guala._causal_experience_owner.settle(
                        boundaries[index],
                        routing_chis=(index,),
                        source_tags=(f"waiter-{index}",),
                    )
                )
        except BaseException as error:
            waiter_errors.append(error)

    monkeypatch.setattr(guala, "_emit_from_invariants", blocked_emit)
    conversation = threading.Thread(target=converse_worker)
    conversation.start()
    assert emit_entered.wait(10.0)
    assert guala._causal_experience_owner.status()[
        "prepared_reservation"
    ] == 1

    admitted = []
    for index in range(MAX_CAUSAL_RESERVATION_WAITERS):
        thread = threading.Thread(target=settlement_worker, args=(index,))
        admitted.append(thread)
        thread.start()
        deadline = time.monotonic() + 5.0
        while (
            guala._causal_experience_owner.status()["reservation_waiters"]
            != index + 1
            and time.monotonic() < deadline
        ):
            time.sleep(0.005)
        assert guala._causal_experience_owner.status()[
            "reservation_waiters"
        ] == index + 1

    excess = []
    for index in range(
        MAX_CAUSAL_RESERVATION_WAITERS,
        len(boundaries),
    ):
        thread = threading.Thread(target=settlement_worker, args=(index,))
        excess.append(thread)
        thread.start()
    for thread in excess:
        thread.join(5.0)
        assert not thread.is_alive()

    owner_status = guala._causal_experience_owner.status()
    assert owner_status["reservation_waiter_capacity"] == (
        MAX_CAUSAL_RESERVATION_WAITERS
    ) == len(SENSE_ORDER)
    assert owner_status["reservation_waiters"] == (
        MAX_CAUSAL_RESERVATION_WAITERS
    )
    assert len(waiter_errors) == len(excess)
    assert all(
        isinstance(error, RuntimeError)
        and str(error)
        == "causal settlement reservation waiter capacity is full"
        for error in waiter_errors
    )
    with guala._engine_mutation_condition:
        active_while_reserved = guala._engine_active_mutations
    assert active_while_reserved >= MAX_CAUSAL_RESERVATION_WAITERS + 1

    release_emit.set()
    conversation.join(10.0)
    for thread in admitted:
        thread.join(10.0)
    assert not conversation.is_alive()
    assert all(not thread.is_alive() for thread in admitted)
    assert conversation_errors == []
    assert len(turns) == 1
    assert len(waiter_results) == MAX_CAUSAL_RESERVATION_WAITERS

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        with guala._engine_mutation_condition:
            if guala._engine_active_mutations == 0:
                break
        time.sleep(0.005)
    with guala._engine_mutation_condition:
        assert guala._engine_active_mutations == 0
    owner_status = guala._causal_experience_owner.status()
    assert owner_status["prepared_reservation"] == 0
    assert owner_status["reservation_waiters"] == 0
    assert guala._auditory_incremental_terminals.authority_counts() == {
        "issued_terminal_authorities": 0,
        "in_flight_terminal_authorities": 0,
    }


def test_failed_concurrent_read_does_not_clobber_newer_witness(
        guala, monkeypatch):
    terminal = _issue(guala, _terminal("concurrent failed read"))
    prior = _prior_record(guala)
    newer = _terminal("newer committed witness").as_record()
    read_entered = threading.Event()
    release_read = threading.Event()
    errors = []

    def fail_after_newer_commit(*_args, **_kwargs):
        read_entered.set()
        if not release_read.wait(5.0):
            raise RuntimeError("test did not release failed read")
        raise RuntimeError("injected concurrent read failure")

    def read_worker():
        try:
            guala.read_sentence(
                terminal.tutor_label,
                source="auditory:unresolved_source",
                causal_intake=terminal,
            )
        except BaseException as error:
            errors.append(error)

    monkeypatch.setattr(guala, "read_word", fail_after_newer_commit)
    thread = threading.Thread(target=read_worker)
    thread.start()
    assert read_entered.wait(5.0)
    assert guala._latest_auditory_causal_event_record == prior
    guala._remember_auditory_causal_event(newer)
    release_read.set()
    thread.join(5.0)

    assert not thread.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert str(errors[0]) == "injected concurrent read failure"
    assert guala._latest_auditory_causal_event_record == newer
    assert guala._auditory_incremental_terminals.authority_counts() == {
        "issued_terminal_authorities": 1,
        "in_flight_terminal_authorities": 0,
    }
    assert guala.discard_unadmitted_auditory_terminal(terminal)


@pytest.mark.parametrize(
    "failure",
    (
        RuntimeError("injected situation failure"),
        KeyboardInterrupt("injected situation cancellation"),
        SystemExit("injected situation termination"),
    ),
)
def test_every_post_claim_situation_exit_restores_authority(
        guala, monkeypatch, failure):
    terminal = _issue(guala, _terminal(type(failure).__name__))

    def fail_situation():
        raise failure

    monkeypatch.setattr(guala, "_current_situation", fail_situation)
    with pytest.raises(type(failure), match=str(failure)):
        guala.converse(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )
    assert guala._auditory_incremental_terminals.authority_counts() == {
        "issued_terminal_authorities": 1,
        "in_flight_terminal_authorities": 0,
    }
    assert guala.discard_unadmitted_auditory_terminal(terminal)


def test_direct_read_baseexception_releases_prepared_ordering_and_claim(
        guala, monkeypatch):
    terminal = _issue(guala, _terminal("direct cancellation"))
    registry = guala._auditory_incremental_terminals

    def cancel_after_prepare(_claim, _settlement):
        assert guala._causal_experience_owner.status()[
            "prepared_reservation"
        ] == 1
        raise KeyboardInterrupt("injected direct read cancellation")

    monkeypatch.setattr(registry, "prepare_claim", cancel_after_prepare)
    with pytest.raises(KeyboardInterrupt, match="direct read cancellation"):
        guala.read_sentence(
            terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=terminal,
        )
    assert guala._causal_experience_owner.status()[
        "prepared_reservation"
    ] == 0
    assert guala._auditory_incremental_terminals.authority_counts() == {
        "issued_terminal_authorities": 1,
        "in_flight_terminal_authorities": 0,
    }
    assert guala.discard_unadmitted_auditory_terminal(terminal)


@pytest.mark.parametrize("authority_state", ("issued", "in_flight"))
def test_strict_shutdown_rejects_live_terminal_authority(
        guala, authority_state):
    terminal = _issue(guala, _terminal(f"shutdown {authority_state}"))
    claim = None
    if authority_state == "in_flight":
        claim = guala._auditory_incremental_terminals.claim(terminal)

    with pytest.raises(
        RuntimeError,
        match=(
            "quiescence rejected live auditory terminal authority: "
            f"issued={int(authority_state == 'issued')}, "
            f"in_flight={int(authority_state == 'in_flight')}"
        ),
    ):
        guala.strict_shutdown(timeout=5.0)

    if claim is None:
        assert guala.discard_unadmitted_auditory_terminal(terminal)
    else:
        guala._auditory_incremental_terminals.rollback_claim(claim)
        assert guala.discard_unadmitted_auditory_terminal(terminal)
