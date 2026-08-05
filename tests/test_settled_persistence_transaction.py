import threading
import time
import inspect

import dsf_ai_service.app as app_module
from dsf_ai_service.v4.guala_physical_runtime import Guala


def _bare_engine():
    engine = Guala.__new__(Guala)
    engine._engine_quiesced = False
    engine._engine_quiescence_complete = False
    engine._engine_mutation_condition = threading.Condition()
    engine._engine_mutation_admission_open = True
    engine._engine_active_mutations = 0
    engine._engine_mutation_local = threading.local()
    engine._engine_raw_threads = set()
    engine._engine_raw_threads_started = 0
    engine._engine_raw_threads_completed = 0
    engine._persistence_lock = threading.RLock()
    engine.lock = threading.RLock()
    engine.tick = 0
    return engine


def test_external_persistence_waits_for_settled_neuron_mutation():
    engine = _bare_engine()
    mutation_started = threading.Event()
    release_mutation = threading.Event()
    persistence_entered = threading.Event()
    errors = []

    class ExactNeuronOwner:
        prepared = False

        def snapshot_encoded(self):
            if self.prepared:
                raise RuntimeError(
                    "cannot snapshot an in-flight neuron mutation"
                )
            return b"settled-neuron-state"

    neuron = ExactNeuronOwner()

    def mutation():
        try:
            with engine._engine_mutation_scope("auditory-settlement"):
                neuron.prepared = True
                mutation_started.set()
                assert release_mutation.wait(1.0)
                neuron.prepared = False
        except BaseException as error:
            errors.append(error)

    def persistence():
        try:
            with engine.settled_external_persistence_transaction():
                persistence_entered.set()
                assert neuron.snapshot_encoded() == b"settled-neuron-state"
        except BaseException as error:
            errors.append(error)

    mutation_thread = threading.Thread(target=mutation)
    persistence_thread = threading.Thread(target=persistence)
    mutation_thread.start()
    assert mutation_started.wait(1.0)
    persistence_thread.start()
    assert not persistence_entered.wait(0.1)

    release_mutation.set()
    mutation_thread.join(1.0)
    persistence_thread.join(1.0)

    assert not mutation_thread.is_alive()
    assert not persistence_thread.is_alive()
    assert persistence_entered.is_set()
    assert not errors


def test_new_mutation_waits_until_settled_persistence_finishes():
    engine = _bare_engine()
    persistence_entered = threading.Event()
    release_persistence = threading.Event()
    mutation_entered = threading.Event()
    errors = []

    def persistence():
        try:
            with engine.settled_external_persistence_transaction():
                persistence_entered.set()
                assert release_persistence.wait(1.0)
        except BaseException as error:
            errors.append(error)

    def mutation():
        try:
            with engine._engine_mutation_scope("late-auditory-settlement"):
                mutation_entered.set()
        except BaseException as error:
            errors.append(error)

    persistence_thread = threading.Thread(target=persistence)
    mutation_thread = threading.Thread(target=mutation)
    persistence_thread.start()
    assert persistence_entered.wait(1.0)
    mutation_thread.start()
    assert not mutation_entered.wait(0.1)

    release_persistence.set()
    persistence_thread.join(1.0)
    mutation_thread.join(1.0)

    assert not persistence_thread.is_alive()
    assert not mutation_thread.is_alive()
    assert mutation_entered.is_set()
    assert not errors


def test_settled_persistence_remains_owned_until_quiescence_can_finish():
    engine = _bare_engine()
    persistence_entered = threading.Event()
    release_persistence = threading.Event()
    quiescence_finished = threading.Event()
    errors = []

    def persistence():
        try:
            with engine.settled_external_persistence_transaction():
                persistence_entered.set()
                assert release_persistence.wait(1.0)
        except BaseException as error:
            errors.append(error)

    def quiescence():
        try:
            engine._close_engine_mutation_admission()
            engine._wait_for_engine_mutations(time.monotonic() + 1.0)
            quiescence_finished.set()
        except BaseException as error:
            errors.append(error)

    persistence_thread = threading.Thread(target=persistence)
    quiescence_thread = threading.Thread(target=quiescence)
    persistence_thread.start()
    assert persistence_entered.wait(1.0)
    quiescence_thread.start()
    assert not quiescence_finished.wait(0.1)

    release_persistence.set()
    persistence_thread.join(1.0)
    quiescence_thread.join(1.0)

    assert not persistence_thread.is_alive()
    assert not quiescence_thread.is_alive()
    assert quiescence_finished.is_set()
    assert not errors


def test_uninherited_background_start_waits_for_settled_persistence():
    engine = _bare_engine()
    persistence_entered = threading.Event()
    release_persistence = threading.Event()
    background_registered = threading.Event()
    background_entered = threading.Event()
    errors = []
    workers = []

    def persistence():
        try:
            with engine.settled_external_persistence_transaction():
                persistence_entered.set()
                assert release_persistence.wait(1.0)
        except BaseException as error:
            errors.append(error)

    def start_background():
        try:
            worker = engine._start_engine_background_thread(
                background_entered.set,
                name="standalone-background-mutation",
            )
            workers.append(worker)
            background_registered.set()
        except BaseException as error:
            errors.append(error)

    persistence_thread = threading.Thread(target=persistence)
    starter_thread = threading.Thread(target=start_background)
    persistence_thread.start()
    assert persistence_entered.wait(1.0)
    starter_thread.start()
    assert not background_registered.wait(0.1)
    assert not background_entered.is_set()

    release_persistence.set()
    persistence_thread.join(1.0)
    starter_thread.join(1.0)
    assert background_registered.wait(1.0)
    for worker in workers:
        worker.join(1.0)

    assert not persistence_thread.is_alive()
    assert not starter_thread.is_alive()
    assert background_entered.is_set()
    assert not errors


def test_inherited_background_remains_part_of_admitted_mutation():
    engine = _bare_engine()
    parent_entered = threading.Event()
    start_inherited = threading.Event()
    inherited_registered = threading.Event()
    inherited_entered = threading.Event()
    release_inherited = threading.Event()
    persistence_entered = threading.Event()
    errors = []
    workers = []

    def inherited():
        inherited_entered.set()
        assert release_inherited.wait(1.0)

    def mutation():
        try:
            with engine._engine_mutation_scope("auditory-settlement"):
                parent_entered.set()
                assert start_inherited.wait(1.0)
                worker = engine._start_engine_background_thread(
                    inherited,
                    name="inherited-auditory-continuation",
                )
                workers.append(worker)
                inherited_registered.set()
        except BaseException as error:
            errors.append(error)

    def persistence():
        try:
            with engine.settled_external_persistence_transaction():
                persistence_entered.set()
        except BaseException as error:
            errors.append(error)

    mutation_thread = threading.Thread(target=mutation)
    persistence_thread = threading.Thread(target=persistence)
    mutation_thread.start()
    assert parent_entered.wait(1.0)
    persistence_thread.start()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        with engine._engine_mutation_condition:
            if engine._engine_settled_snapshot_requested:
                break
        time.sleep(0.001)
    else:
        raise AssertionError("settled persistence did not request ownership")

    start_inherited.set()
    assert inherited_registered.wait(1.0)
    assert inherited_entered.wait(1.0)
    mutation_thread.join(1.0)
    assert not mutation_thread.is_alive()
    assert not persistence_entered.wait(0.1)

    release_inherited.set()
    for worker in workers:
        worker.join(1.0)
    persistence_thread.join(1.0)

    assert not persistence_thread.is_alive()
    assert persistence_entered.is_set()
    assert not errors


def test_periodic_hot_and_cold_saves_use_settled_external_boundary():
    source = inspect.getsource(app_module.startup)

    assert source.count(
        "with _guala.settled_external_persistence_transaction():"
    ) == 3
    assert "_checkpoint_authoritative_runtime(" in source
    assert "_guala.save_hot_state(STATE_DIR)" in source
