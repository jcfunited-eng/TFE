"""The runner cannot create an independent persistence or backup authority."""

import inspect

import dsf_ai_service.substrate_runner as runner


def test_runner_has_no_backup_operation_or_orchestrator():
    source = inspect.getsource(runner)

    assert "backup" not in runner.OP_HANDLERS
    assert not hasattr(runner, "handle_backup")
    assert not hasattr(runner, "_orchestrated_backup")
    assert "SAVE_COORDINATOR" not in source
    assert "save_full_state" not in source


def test_app_owned_save_lifecycle_facts_remain_available():
    assert runner._backup_in_flight is False
    assert runner._last_successful_backup_wall >= 0.0
    assert runner._backup_lock is not None
