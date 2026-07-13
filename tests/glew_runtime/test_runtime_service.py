import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.glew_runtime import field, genesis, l6
from dsf_ai_service.glew_runtime.conformance import (
    CREATED_ACTION,
    DEFAULT_PROFILE_PATH,
    RESTORED_ACTION,
    RuntimeConfiguration,
    RuntimeConformanceError,
    main,
    run_conformance,
    run_startup_conformance,
)
from dsf_ai_service.glew_runtime.service import (
    create_status_application,
    create_wrapped_application,
)


def _genesis_configuration(
    tmp_path: Path, *, bind_expected_identity: bool = True
) -> RuntimeConfiguration:
    root = tmp_path / "glew-clean-generation"
    receipt = genesis.create_clean_genesis(
        root,
        profile_path=DEFAULT_PROFILE_PATH,
        fixed42_provider=l6,
        field_provider=field,
    )
    return RuntimeConfiguration(
        genesis_root=root,
        expected_identity=(receipt.identity if bind_expected_identity else None),
        profile_path=DEFAULT_PROFILE_PATH,
    )


def _legacy_application(events: list[str]) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        events.append("startup")
        yield
        events.append("shutdown")

    legacy = FastAPI(lifespan=lifespan)

    @legacy.post("/converse")
    async def legacy_converse():
        return {"owner": "unchanged-legacy-route"}

    return legacy


def test_cold_conformance_is_repeatable_exact_and_truthful(tmp_path):
    configuration = _genesis_configuration(tmp_path, bind_expected_identity=False)

    first = run_conformance(configuration)
    second = run_conformance(configuration)

    assert first == second
    assert first["conformant"] is True
    assert first["full_glew_language_commit_authority"] is False
    assert first["legacy_conversation_routed_through_glew"] is False
    assert first["field_authority"]["dsf_field_reduced"] is False
    assert first["field_authority"]["full_field_preserved"] is True
    assert first["field_authority"]["current_facts"] == {
        "R_UF": {
            "reason": "no_closed_receipted_grid_or_mounted_required_edge_graph",
            "status": "unknown",
            "value": None,
        },
        "S_UF": {
            "reason": "no_closed_receipted_grid_or_mounted_required_port_domain",
            "status": "unknown",
            "value": None,
        },
    }
    assert first["field_evolution"]["status"] == (
        "operator_conformant_no_live_mounted_topology"
    )
    assert first["field_evolution"]["live_mounted_topology"] is False
    assert first["field_evolution"]["empty_genesis"]["dimension"] == 0
    assert first["fixed42"]["current_matrix_shape"] == [0, 42]
    assert first["fixed42"]["current_row_count"] == 0
    assert first["fixed42"]["zero_rows_fabricated"] is False
    assert len(first["genesis"]["identity"]) == 36
    assert len(first["genesis"]["manifest_sha256"]) == 64
    assert len(first["profile"]["sha256"]) == 64
    assert len(first["backend"]["adapter_sha256"]) == 64
    assert len(first["backend"]["python_flint_wheel_sha256"]) == 64
    assert first["backend"]["arb_capture_certificate"]["uniquely_certified"] is True
    assert len(first["conformance_report_sha256"]) == 64


def test_explicit_first_boot_creates_once_then_cold_restores(tmp_path):
    configuration = RuntimeConfiguration(
        genesis_root=tmp_path / "new-clean-root",
        profile_path=DEFAULT_PROFILE_PATH,
        create_clean_genesis=True,
    )

    created = run_startup_conformance(configuration)
    restarted = run_startup_conformance(configuration)

    assert created["startup_action"] == CREATED_ACTION
    assert restarted["startup_action"] == RESTORED_ACTION
    assert created["genesis"] == restarted["genesis"]
    assert created["profile"] == restarted["profile"]
    assert (configuration.genesis_root / "CURRENT").is_file()


def test_concurrent_first_boot_serializes_to_one_genesis(tmp_path):
    configuration = RuntimeConfiguration(
        genesis_root=tmp_path / "race-clean-root",
        profile_path=DEFAULT_PROFILE_PATH,
        create_clean_genesis=True,
    )
    barrier = threading.Barrier(2)

    def boot():
        barrier.wait()
        return run_startup_conformance(configuration)

    with ThreadPoolExecutor(max_workers=2) as executor:
        reports = tuple(executor.map(lambda _index: boot(), range(2)))

    assert sorted(report["startup_action"] for report in reports) == sorted(
        (CREATED_ACTION, RESTORED_ACTION)
    )
    assert reports[0]["genesis"] == reports[1]["genesis"]
    assert len(tuple((configuration.genesis_root / "generations").iterdir())) == 1


def test_creation_refuses_arbitrary_content_without_overwrite(tmp_path):
    root = tmp_path / "occupied"
    root.mkdir()
    inherited = root / "legacy-state.json"
    inherited.write_bytes(b'{"legacy":true}\n')
    configuration = RuntimeConfiguration(
        genesis_root=root,
        profile_path=DEFAULT_PROFILE_PATH,
        create_clean_genesis=True,
    )

    with pytest.raises(RuntimeConformanceError, match="cold restore failed"):
        run_startup_conformance(configuration)

    assert inherited.read_bytes() == b'{"legacy":true}\n'
    assert tuple(root.iterdir()) == (inherited,)


def test_creation_flag_never_repairs_damaged_existing_store(tmp_path):
    configuration = _genesis_configuration(tmp_path, bind_expected_identity=False)
    current = configuration.genesis_root / "CURRENT"
    generation_directories = tuple(
        (configuration.genesis_root / "generations").iterdir()
    )
    current.unlink()
    enabled = RuntimeConfiguration(
        genesis_root=configuration.genesis_root,
        profile_path=configuration.profile_path,
        create_clean_genesis=True,
    )

    with pytest.raises(RuntimeConformanceError, match="cold restore failed"):
        run_startup_conformance(enabled)

    assert not current.exists()
    assert tuple((configuration.genesis_root / "generations").iterdir()) == (
        generation_directories
    )


def test_creation_flag_rejects_promised_identity_before_mutation(tmp_path):
    configuration = RuntimeConfiguration(
        genesis_root=tmp_path / "new-clean-root",
        expected_identity="00000000-0000-4000-8000-000000000099",
        profile_path=DEFAULT_PROFILE_PATH,
        create_clean_genesis=True,
    )

    with pytest.raises(RuntimeConformanceError, match="pre-existing identity"):
        run_startup_conformance(configuration)

    assert not configuration.genesis_root.exists()


def test_environment_creation_authority_is_exact_not_truthy(tmp_path):
    base = {"GLEW_GENESIS_ROOT": str(tmp_path / "clean")}

    assert RuntimeConfiguration.from_environment(base).create_clean_genesis is False
    assert RuntimeConfiguration.from_environment(
        {**base, "GLEW_CREATE_CLEAN_GENESIS": "1"}
    ).create_clean_genesis is True
    with pytest.raises(RuntimeConformanceError, match="exactly 0 or 1"):
        RuntimeConfiguration.from_environment(
            {**base, "GLEW_CREATE_CLEAN_GENESIS": "true"}
        )


def test_conformance_cli_returns_canonical_success_and_failure(tmp_path, capsys):
    configuration = _genesis_configuration(tmp_path)

    success = main(
        [
            "--root",
            str(configuration.genesis_root),
            "--profile",
            str(configuration.profile_path),
        ]
    )
    success_payload = json.loads(capsys.readouterr().out)
    failure = main(
        [
            "--root",
            str(configuration.genesis_root),
            "--identity",
            "00000000-0000-4000-8000-000000000099",
            "--profile",
            str(configuration.profile_path),
        ]
    )
    failure_payload = json.loads(capsys.readouterr().out)

    assert success == 0
    assert success_payload["conformant"] is True
    assert failure == 1
    assert failure_payload["conformant"] is False
    assert failure_payload["full_glew_language_commit_authority"] is False


def test_standalone_app_creates_then_cold_restarts_without_converse(tmp_path):
    configuration = RuntimeConfiguration(
        genesis_root=tmp_path / "service-clean-root",
        profile_path=DEFAULT_PROFILE_PATH,
        create_clean_genesis=True,
    )
    standalone = create_status_application(
        configuration_provider=lambda: configuration
    )

    with TestClient(standalone) as first_client:
        status = first_client.get("/glew/status")
        live_check = first_client.get("/glew/conformance")
        absent_converse = first_client.post("/converse")
    with TestClient(standalone) as restarted_client:
        restarted = restarted_client.get("/glew/status")

    assert status.status_code == 200
    assert live_check.status_code == 200
    assert status.json() == live_check.json()
    assert status.json()["startup_action"] == CREATED_ACTION
    assert restarted.status_code == 200
    assert restarted.json()["startup_action"] == RESTORED_ACTION
    assert status.json()["genesis"] == restarted.json()["genesis"]
    assert absent_converse.status_code == 404


def test_explicit_wrapper_delegates_converse_without_glew_routing(tmp_path):
    configuration = _genesis_configuration(tmp_path)
    lifecycle_events: list[str] = []
    wrapper = create_wrapped_application(
        legacy_application=_legacy_application(lifecycle_events),
        configuration_provider=lambda: configuration,
    )

    with TestClient(wrapper) as client:
        status = client.get("/glew/status")
        converse = client.post("/converse")

    assert status.status_code == 200
    assert converse.status_code == 200
    assert converse.json() == {"owner": "unchanged-legacy-route"}
    assert status.json()["legacy_conversation_routed_through_glew"] is False
    assert lifecycle_events == ["startup", "shutdown"]


def test_startup_fails_closed_before_delegated_lifespan_on_bad_identity(tmp_path):
    configuration = _genesis_configuration(tmp_path)
    wrong = RuntimeConfiguration(
        genesis_root=configuration.genesis_root,
        expected_identity="00000000-0000-4000-8000-000000000099",
        profile_path=configuration.profile_path,
    )
    lifecycle_events: list[str] = []
    wrapper = create_wrapped_application(
        legacy_application=_legacy_application(lifecycle_events),
        configuration_provider=lambda: wrong,
    )

    with pytest.raises(RuntimeConformanceError, match="cold restore failed"):
        with TestClient(wrapper):
            pass

    assert lifecycle_events == []


def test_live_conformance_detects_store_loss_without_repair(tmp_path):
    configuration = _genesis_configuration(tmp_path)
    standalone = create_status_application(
        configuration_provider=lambda: configuration
    )

    with TestClient(standalone) as client:
        (configuration.genesis_root / "CURRENT").unlink()
        response = client.get("/glew/conformance")

    assert response.status_code == 503
    assert response.json()["conformant"] is False
    assert response.json()["full_glew_language_commit_authority"] is False
    assert not (configuration.genesis_root / "CURRENT").exists()
