"""Backup commands must distinguish a local save from a queued S3 copy."""

from types import SimpleNamespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dsf_ai_service.save_coordinator as coordinator_module
import dsf_ai_service.substrate_runner as runner


class LocalOnlyCoordinator:
    s3_bucket = None

    def __init__(self):
        self.reasons = []

    def force_save(self, reason):
        self.reasons.append(reason)


class FakeGuala:
    def __init__(self):
        self.tick = 88
        self.atlas = SimpleNamespace(entries={1: [{"strength": 1.0}]})
        self.events = []

    def save_full_state(self, _state_dir):
        raise AssertionError("coordinator owns the local save in this fixture")

    def _log_substrate_event(self, event, **details):
        self.events.append((event, details))


def test_backup_handlers_report_local_only_when_s3_is_disabled(monkeypatch):
    guala = FakeGuala()
    coordinator = LocalOnlyCoordinator()
    monkeypatch.setattr(runner, "_guala", guala)
    monkeypatch.setattr(coordinator_module, "SAVE_COORDINATOR", coordinator)

    command_result = runner.handle_backup({})
    orchestrated_result = runner._orchestrated_backup(
        "truth-check", blocking=True)

    assert command_result["storage"] == "local-only"
    assert command_result["s3"] == "disabled"
    assert orchestrated_result["storage"] == "local-only"
    assert orchestrated_result["s3"] == "disabled"
    assert coordinator.reasons == ["backup", "truth-check"]
    event_name, event_details = guala.events[-1]
    assert event_name == "auto_backup"
    assert event_details["storage"] == "local-only"
    assert event_details["s3_status"] == "disabled"
    assert "s3_prefix" not in event_details


def test_backup_handlers_use_authoritative_generation_when_connected(
        monkeypatch):
    guala = FakeGuala()
    reasons = []
    guala._authoritative_cold_generation_checkpoint = (
        lambda reason: reasons.append(reason) or {
            "generation_uuid": "11111111-1111-4111-8111-111111111111",
            "manifest_sha256": "a" * 64,
        }
    )
    coordinator = LocalOnlyCoordinator()
    monkeypatch.setattr(runner, "_guala", guala)
    monkeypatch.setattr(coordinator_module, "SAVE_COORDINATOR", coordinator)

    command_result = runner.handle_backup({})
    orchestrated_result = runner._orchestrated_backup(
        "truth-check",
        blocking=True,
    )

    assert command_result["storage"] == (
        "bounded-local-and-verified-remote")
    assert command_result["s3"] == "verified"
    assert orchestrated_result["storage"] == (
        "bounded-local-and-verified-remote")
    assert orchestrated_result["s3"] == "verified"
    assert reasons == ["runner-backup", "orchestrated-truth-check"]
    assert coordinator.reasons == []
