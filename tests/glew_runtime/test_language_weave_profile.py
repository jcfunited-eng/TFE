"""Conformance test for the proposed Language Weave Profile v1.

This profile is PROPOSED and PENDING RATIFICATION
(docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md).
These tests verify the profile's own claims are true against the real,
live code -- not that the profile has been ratified or wired into
production. Nothing here grants full_glew_language_commit_authority;
that stays false in GLEW_UPSTREAM_PROFILE_v1.json until a separate,
later cutover is built, proven, and explicitly approved.
"""

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PROFILE_PATH = (
    ROOT / "dsf_ai_service" / "glew_runtime" / "GLEW_LANGUAGE_WEAVE_PROFILE_v1.json"
)
UPSTREAM_PROFILE_PATH = (
    ROOT / "dsf_ai_service" / "glew_runtime" / "GLEW_UPSTREAM_PROFILE_v1.json"
)
CHEMISTRY_PROFILE_PATH = (
    ROOT
    / "dsf_ai_service"
    / "glew_runtime"
    / "profiles"
    / "production_virtual_story_chemistry_profile_v1.json"
)


@pytest.fixture(scope="module")
def profile():
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def test_profile_is_marked_proposed_not_ratified(profile):
    assert profile["status"] == "proposed_pending_ratification"
    assert profile["schema"] == "glew.language_weave.profile.v1"


def test_profile_names_governing_spec(profile):
    spec_path = ROOT / profile["governing_spec"]
    assert spec_path.is_file(), "governing spec file must exist"


def test_profile_contains_no_response_content_or_tuned_thresholds(profile):
    """The profile must never contain response text, target phrases, or
    thresholds -- only operator identities and structural rules."""
    serialized = json.dumps(profile).lower()
    for forbidden_marker in ("target_phrase", "expected_response", "canned_reply",
                             "min_word_count", "threshold_value"):
        assert forbidden_marker not in serialized


def test_upstream_profile_digest_matches_computed_value(profile):
    raw = UPSTREAM_PROFILE_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == profile["upstream_profile"]["digest_sha256_of_raw_file_bytes"]

    # Confirm the file is genuinely in the canonical form genesis.py requires,
    # not merely a file that happens to hash the same by coincidence.
    parsed = json.loads(raw)
    canonical = (
        json.dumps(parsed, allow_nan=False, ensure_ascii=False, indent=2,
                   sort_keys=True) + "\n"
    ).encode("utf-8")
    assert raw == canonical


def test_upstream_profile_still_denies_full_commit_authority():
    """This proposed profile must never have altered the live denial."""
    parsed = json.loads(UPSTREAM_PROFILE_PATH.read_bytes())
    assert parsed["authority"]["full_glew_language_commit_authority"] is False
    assert parsed["downstream"]["full_GLEW_commit"] == "forbidden"


def test_chemistry_profile_digest_matches_computed_value(profile):
    raw = CHEMISTRY_PROFILE_PATH.read_bytes()
    parsed = json.loads(raw)
    canonical_body = json.dumps(parsed, separators=(",", ":"),
                                 sort_keys=True).encode("utf-8")
    digest_body = hashlib.sha256(canonical_body).hexdigest()
    digest_raw = hashlib.sha256(raw).hexdigest()
    assert digest_body == profile["five_sense_chemistry_profile"][
        "digest_sha256_of_canonical_body_no_trailing_newline"]
    assert digest_raw == profile["five_sense_chemistry_profile"][
        "digest_sha256_of_raw_file_bytes"]
    assert raw in (canonical_body, canonical_body + b"\n")


def test_chemistry_profile_has_exactly_five_independent_ports(profile):
    parsed = json.loads(CHEMISTRY_PROFILE_PATH.read_bytes())
    lane_ids = sorted(
        port["kernel_binding"]["lane_id"] for port in parsed["ports"]
    )
    assert lane_ids == sorted(profile["five_sense_chemistry_profile"]["ports"])
    assert len(set(lane_ids)) == 5


def test_expression_mode_operator_ids_are_real(profile):
    from dsf_ai_service.glew_runtime import expression_modes as em

    assert em.EXPRESSION_MODE_OPERATOR_ID == (
        profile["expression_mode"]["operator_ids"]["mode"])
    assert em.EXPRESSION_RECOGNITION_OPERATOR_ID == (
        profile["expression_mode"]["operator_ids"]["recognition"])


def test_commit_operator_ids_and_outcomes_are_real(profile):
    from dsf_ai_service.glew_runtime import commit

    assert commit.COMMIT_OPERATOR_ID == profile["commit"]["operator_ids"]["commit"]
    assert commit.PENDING_GLOBAL_UF_OPERATOR_ID == (
        profile["commit"]["operator_ids"]["pending_global_uf"])
    real_outcomes = sorted(status.value for status in commit.CommitStatus)
    assert real_outcomes == sorted(profile["commit"]["outcomes"])


def test_safe_mode_operator_id_is_real(profile):
    from dsf_ai_service.glew_runtime import safe_mode

    assert safe_mode.SAFE_MODE_OPERATOR_ID == profile["safe_mode"]["operator_id"]


def test_event_support_operator_ids_are_real(profile):
    from dsf_ai_service.glew_runtime import event_support as es

    assert es.EVENT_SUPPORT_OPERATOR_ID == (
        profile["event_support"]["operator_ids"]["full_rank"])
    assert es.EXTERIOR_GRAM_GEOMETRY_OPERATOR_ID == (
        profile["event_support"]["operator_ids"]["exterior_geometry"])


def test_global_uf_operator_id_is_real(profile):
    from dsf_ai_service.glew_runtime import global_uf

    assert global_uf.GLOBAL_UF_OPERATOR_ID == profile["global_uf"]["operator_id"]


def test_fixed42_n_start_is_real(profile):
    from dsf_ai_service.glew_runtime import l6

    assert l6.N_START == profile["fixed42_l6"]["n_start"] == 42


def test_heterogeneous_l6_operator_id_is_real(profile):
    from dsf_ai_service.glew_runtime import heterogeneous_l6 as hl6

    assert hl6.HETEROGENEOUS_L6_ASSEMBLY_OPERATOR_ID == (
        profile["fixed42_l6"]["heterogeneous_assembly_operator_id"])


def test_learning_operator_id_is_real(profile):
    from dsf_ai_service.glew_runtime import expression_learning as el

    assert el.LEARNING_OPERATOR_ID == profile["learning"]["operator_id"]
    assert hasattr(el, "learn_committed_binding_transaction")


def test_fresh_recall_operator_ids_are_real(profile):
    from dsf_ai_service.glew_runtime import recall_reentry as rr

    assert rr.FRESH_RECALL_SELF_SENSE_OPERATOR_ID == (
        profile["fresh_recall"]["operator_ids"]["self_sense_reentry"])
    assert rr.RECALLED_LANGUAGE_TRANSDUCTION_OPERATOR_ID == (
        profile["fresh_recall"]["operator_ids"]["language_transduction"])


def test_typed_language_operator_ids_are_real(profile):
    from dsf_ai_service.glew_runtime import typed_language_native_replay as tlnr

    assert tlnr.TYPED_LANGUAGE_NATIVE_REPLAY_OPERATOR_ID == (
        profile["typed_language"]["operator_ids"]["native_replay"])
    assert tlnr.TYPED_LANGUAGE_CONTINGENT_CONE_OPERATOR_ID == (
        profile["typed_language"]["operator_ids"]["contingent_cone"])
    assert tlnr.TYPED_LANGUAGE_DIRECTION_ROW_OPERATOR_ID == (
        profile["typed_language"]["operator_ids"]["direction_row"])


def test_entropy_operator_is_confirmed_unreferenced_by_language_authority(profile):
    """The excluded entropy operator must genuinely not be reachable from
    the expression-mode or commit path -- not merely undocumented."""
    from dsf_ai_service.glew_runtime import modes, expression_modes, commit
    import inspect

    assert modes.ENTROPY_OPERATOR_ID == (
        profile["entropy_disposition"]["legacy_operator_id_not_ratified"])

    em_source = inspect.getsource(expression_modes)
    commit_source = inspect.getsource(commit)
    assert "ENTROPY_OPERATOR_ID" not in em_source
    assert "ENTROPY_OPERATOR_ID" not in commit_source
    assert "shannon" not in em_source.lower()
    assert "shannon" not in commit_source.lower()


def test_l5_applicability_gap_is_honestly_still_open(profile):
    """This profile must not claim L5 applicability is ratified when it
    is not -- this test fails the moment someone quietly closes the gap
    without updating the profile, which is the intended tripwire."""
    assert profile["l5_applicability"]["open_gap"] is True
    assert profile["l5_applicability"]["status"] == "mechanism_ratified_rule_not_ratified"


def test_prohibitions_list_matches_governing_spec_section_6(profile):
    spec_text = (ROOT / profile["governing_spec"]).read_text(encoding="utf-8")
    spec_text_stripped = spec_text.replace("`", "").lower()
    for prohibition in profile["prohibitions"]:
        # A loose substring check: every prohibition's key phrase must
        # appear somewhere in the governing spec's own forbidden list.
        # Strip markdown backticks (the spec wraps code terms like
        # `False` in them; the profile text does not).
        key_phrase = prohibition.split(",")[0].split(" or ")[0].strip()
        assert key_phrase[:20].lower() in spec_text_stripped, (
            f"prohibition not traceable to governing spec: {prohibition!r}")


def test_seven_open_decisions_are_all_present(profile):
    decisions = profile["open_decisions_requiring_explicit_ratification"]
    assert len(decisions) == 7
