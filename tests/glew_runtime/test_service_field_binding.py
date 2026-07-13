import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.glew_runtime.conformance import (
    DEFAULT_PROFILE_PATH,
    RuntimeConfiguration,
    RuntimeConformanceError,
)
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.service import create_status_application


def _creation_configuration(tmp_path: Path) -> RuntimeConfiguration:
    return RuntimeConfiguration(
        genesis_root=tmp_path / "clean-field-service",
        profile_path=DEFAULT_PROFILE_PATH,
        create_clean_genesis=True,
    )


def test_status_executes_and_binds_current_field_operator_conformance(tmp_path):
    application = create_status_application(
        configuration_provider=lambda: _creation_configuration(tmp_path)
    )

    with TestClient(application) as client:
        status = client.get("/glew/status")
        repeated = client.get("/glew/conformance")

    field = status.json()["field_evolution"]
    assert status.status_code == 200
    assert repeated.status_code == 200
    assert status.json() == repeated.json()
    assert field["status"] == "operator_conformant_no_live_mounted_topology"
    assert field["live_mounted_topology"] is False
    assert field["empty_genesis"]["available"] is False
    assert field["empty_genesis"]["dimension"] == 0
    assert field["one_port_vector"]["dimension"] == 19
    assert field["one_port_vector"]["expected_integrated_charge"] == "3/2"
    assert len(field["one_port_vector"]["physical_profile_receipt_sha256"]) == 64
    assert len(field["report_sha256"]) == 64
    assert status.json()["full_glew_language_commit_authority"] is False


def test_field_operator_failure_stops_startup_before_serving(tmp_path, monkeypatch):
    application = create_status_application(
        configuration_provider=lambda: _creation_configuration(tmp_path)
    )

    def failed_operator():
        raise ReceiptError("field conformance failure fixture")

    monkeypatch.setattr(
        "dsf_ai_service.glew_runtime.service.field_conformance",
        failed_operator,
    )

    with pytest.raises(RuntimeConformanceError, match="field operator conformance"):
        with TestClient(application):
            pass
