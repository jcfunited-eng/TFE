"""Native CURRENT persistence and fail-closed production cutover contract."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = (ROOT / "tools" / "deploy_dsf_ai.sh").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "dsf_ai_service" / "Dockerfile").read_text(
    encoding="utf-8"
)
MANIFEST = json.loads(
    (ROOT / "deploy" / "guala_release_manifest.json").read_text(
        encoding="utf-8"
    )
)


def _manifest_files() -> frozenset[str]:
    files: set[str] = set()
    for category in MANIFEST["categories"]:
        files.update(category.get("paths", []))
        files.update(category.get("files", []))
    return frozenset(files)


def test_production_boot_is_only_the_native_http_boundary() -> None:
    assert (
        'CMD ["uvicorn", "dsf_ai_service.native_production_app:app", '
        '"--host", "0.0.0.0", "--port", "8080"]'
    ) in DOCKERFILE
    assert "dsf_ai_service.app:app" not in DOCKERFILE
    assert "substrate_runner" not in DOCKERFILE


def test_release_contains_native_current_transport_not_owner_generation_stores() -> None:
    files = _manifest_files()
    for required in (
        "dsf_ai_service/native_production_app.py",
        "dsf_ai_service/candidate_release_rehearsal.py",
        "dsf_ai_service/cold_restore_probe.py",
        "dsf_ai_service/substrate/native_organism_binary_store.py",
        "dsf_ai_service/substrate/native_resident_resource_admission.py",
    ):
        assert required in files
    for forbidden in (
        "dsf_ai_service/app.py",
        "dsf_ai_service/substrate/authoritative_cold_generation_store.py",
        "dsf_ai_service/substrate/immutable_generation_store.py",
        "dsf_ai_service/substrate/live_recovery_generation.py",
        "dsf_ai_service/substrate/owner_lock.py",
    ):
        assert forbidden not in files


def test_candidate_task_removes_every_retired_runtime_authority() -> None:
    for retired in (
        '"FORCE_S3_RESTORE"',
        '"GUALA_EXACT_FIELD_EXECUTOR_REQUIRED"',
        '"GUALA_" + "GENERATION_STORE_ROOT"',
        '"GUALA_LIVE_RECOVERY_STORE_ROOT"',
        '"GUALA_" + "OWNER_LOCK_PATH"',
        '"GUALA_" + "REQUIRE_SEALED_STATE"',
        '"STATE_DIR"',
    ):
        assert retired in DEPLOY
    assert "candidate retains legacy authority environment" in DEPLOY
    assert "candidate contains database environment" in DEPLOY
    assert "registered candidate has more than one runtime container" in DEPLOY
    assert "candidate has more than one persistent state volume" in DEPLOY


def test_preflight_and_current_rehearsal_complete_before_the_single_cutover() -> None:
    registration = DEPLOY.index("CANDIDATE_JSON=")
    preflight = DEPLOY.index("python3 tools/preflight_guala_production.py")
    rehearsal = DEPLOY.index(
        "[5/7] Rehearsing the digest-pinned candidate before fail-closed cutover."
    )
    rehearsal_task = DEPLOY.index("--mode cold-restore")
    turnover = DEPLOY.index("aws ecs update-service", rehearsal_task)
    live = DEPLOY.index("CURRENT_RUNNING_TASK=$(verify_live_organism", turnover)
    production_tag = DEPLOY.index(
        "[6/7] Pinning only the live-verified artifact as production-current."
    )
    assert registration < preflight < rehearsal
    assert rehearsal < rehearsal_task < turnover < live < production_tag
    # The continuity cutover reads and rehearses the exact current predecessor;
    # it neither publishes a substitute nor invokes a genesis path.
    assert "PUBLICATION_PROOF=" not in DEPLOY
    assert "COLD_RESTORE_PROOF=" not in DEPLOY
    assert '--expected-identity "${REHEARSAL_IDENTITY}"' in DEPLOY
    assert '--expected-state-sha256 "${REHEARSAL_STATE_SHA}"' in DEPLOY
    assert "REPEAT_CUTOVER=1" in DEPLOY
    assert "rollback=false" in DEPLOY


def test_live_proof_requires_exact_artifact_and_truthful_native_scope() -> None:
    for evidence in (
        'value.get("ready_scope") != "http_native_current_and_admitted_sensory_transitions"',
        'native.get("available") is not True',
        'native.get("python_callback_count") != 0',
        'native.get("complete_neuron_available") is not True',
        'native.get("cognition_available") is not True',
        'containers[0].get("imageDigest") != os.environ["EXPECTED_DIGEST"]',
    ):
        assert evidence in DEPLOY
    assert "automatic_legacy_rollback" in DEPLOY
    assert '"status": "deployed"' in DEPLOY
