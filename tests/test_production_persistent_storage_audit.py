import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from dsf_ai_service.substrate.production_storage_profile import (  # noqa: E402
    ProductionStorageProfile,
)

AUDIT_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "PRODUCTION_PERSISTENT_STORAGE_AUDIT_2026-07-27.json"
)
PROFILE_STATUS_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "PRODUCTION_STORAGE_PROFILE_STATUS_2026-07-27.json"
)


def _load_audit():
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def _load_status():
    return json.loads(PROFILE_STATUS_PATH.read_text(encoding="utf-8"))


def test_storage_audit_records_approved_ceiling_without_rewriting_history():
    audit = _load_audit()
    ceiling = audit["authoritative_ceiling"]

    assert ceiling["source"] == "operator_decision_2026-07-28"
    assert ceiling["status"] == (
        "candidate_configured_live_deployment_pending"
    )
    assert (
        ceiling["approved_hard_global_refusal_ceiling_bytes"]
        == 5 * 1024**3
    )
    assert ceiling["classification"] == (
        "hard_global_write_refusal_ceiling_not_storage_target"
    )
    assert ceiling["aws_efs_storage_byte_quota"] is None
    assert ceiling["current_efs_size_is_a_ceiling"] is False
    assert ceiling["ecs_ephemeral_storage_is_a_ceiling_for_efs"] is False
    assert (
        ceiling["live_task_definition_has_"
                "GUALA_PERSISTENT_STORAGE_CEILING_BYTES"]
        is False
    )
    assert (
        ceiling["candidate_deployment_definition_has_"
                "GUALA_PERSISTENT_STORAGE_CEILING_BYTES"]
        is True
    )
    assert ceiling["required_infrastructure_fact"] is None


def test_every_inventory_evidence_anchor_exists_in_the_named_source():
    audit = _load_audit()
    writers = audit["active_production_writers_outside_authority"]
    assert len(writers) == 6
    assert len({writer["id"] for writer in writers}) == len(writers)

    evidence_groups = [audit["authoritative_ceiling"]["evidence"]]
    evidence_groups.extend(writer["evidence"] for writer in writers)
    for evidence_group in evidence_groups:
        assert evidence_group
        for evidence in evidence_group:
            source = REPOSITORY_ROOT / evidence["file"]
            assert source.is_file(), evidence
            assert evidence["contains"] in source.read_text(
                encoding="utf-8"
            ), evidence


def test_deployment_definition_contains_the_exact_approved_ceiling():
    deploy = (
        REPOSITORY_ROOT / "tools" / "deploy_dsf_ai.sh"
    ).read_text(encoding="utf-8")
    approved = '"GUALA_PERSISTENT_STORAGE_CEILING_BYTES": "5368709120"'
    assert deploy.count(approved) == 1
    status = _load_status()
    assert status["missing_infrastructure_fact"] is None
    assert status["hard_global_refusal_ceiling"]["approved_bytes"] == (
        5 * 1024**3
    )
    assert status["hard_global_refusal_ceiling"][
        "candidate_deployment_definition"
    ] == "configured"
    assert (
        '"GUALA_MAX_COLD_GENERATION_BYTES": "2147483648"'
        in deploy
    )


def test_examined_dormant_surfaces_are_not_misreported_as_active():
    audit = _load_audit()
    active = {
        writer["id"]
        for writer in audit["active_production_writers_outside_authority"]
    }
    dormant = {
        writer["id"]
        for writer in audit["examined_but_not_active_production_writers"]
    }
    assert not active.intersection(dormant)
    assert "binding_window_wal" in dormant
    assert "reusable_substrate_event_log" in dormant


def test_profile_status_separates_readiness_from_emergency_refusal():
    status = _load_status()
    envelope = status["emergency_infrastructure_refusal_envelope"]
    profile = ProductionStorageProfile.from_environment({
        "GUALA_MAX_COLD_GENERATION_BYTES": str(
            envelope["configured_generation_protocol_limit_bytes"]
        ),
    })

    assert status["accounting_authority"] == (
        "verified_reachable_unique_content_plus_manifest_and_"
        "authenticated_receipt_deltas"
    )
    assert status["production_readiness"][
        "static_capacity_multiplication_is_authoritative"
    ] is False
    assert envelope["production_readiness_authority"] is False
    assert envelope["peak_bytes"] == (
        profile.emergency_namespace_refusal_bytes
    )
    assert envelope["retained_bytes"] == (
        profile.emergency_retained_refusal_bytes
    )
    assert status["missing_infrastructure_fact"] is None
    approved = status["hard_global_refusal_ceiling"]
    assert approved["approved_bytes"] == 5 * 1024**3
    assert approved["classification"] == (
        "operator_approved_hard_global_write_refusal_not_storage_target"
    )
    assert approved["live_cutover_status"] == "pending"


def test_status_contains_only_completed_current_purge_counts():
    current = _load_status()[
        "current_observed_storage_after_completed_purge"
    ]
    s3 = current["s3_generation_namespace"]
    efs = current["efs_namespace"]

    assert s3 == {
        "logical_bytes": 1260250898,
        "objects": 185,
        "noncurrent_versions": 0,
        "delete_markers": 0,
        "nongeneration_objects": 0,
        "status": "exact_generation_only_namespace",
    }
    assert efs["logical_bytes"] == 1917332185
    assert efs["recovery_v2_present"] is False
    assert efs["interrupted_unpublished_candidate_present"] is False
    assert current["superseded_recovery_history_pending_bytes"] == 0
    assert current["interrupted_cold_candidate_pending_bytes"] == 0


def test_every_active_writer_has_an_explicit_authority_owner():
    audit = _load_audit()
    status = _load_status()
    covered = set(status["active_writer_authority_coverage"])
    inventory = {
        record["id"]
        for record in audit["active_production_writers_outside_authority"]
    }

    assert covered == inventory
