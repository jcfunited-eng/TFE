"""Proof that model-generated language grounding is retired, not hidden."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.loom_model import lookup_grounding, world_feeds


RUNNER_SOURCE = (ROOT / "dsf_ai_service" / "substrate_runner.py").read_text()
DEPLOY_SOURCE = (ROOT / "tools" / "deploy_dsf_ai.sh").read_text()
LOOKUP_SOURCE = (ROOT / "dsf_ai_service" / "loom_model" / "lookup_grounding.py").read_text()


def test_lookup_is_a_loud_unavailable_boundary_with_no_model_or_network_path():
    boundary = lookup_grounding.status()
    assert boundary == {
        "available": False,
        "state": "unavailable",
        "reason": lookup_grounding.UNAVAILABLE_REASON,
        "authority": "language_fact_strand",
    }
    with pytest.raises(lookup_grounding.GroundingLookupUnavailable):
        lookup_grounding.describe("fox")

    forbidden = ("urllib", "OPENAI_API_KEY", "api.openai.com", "gpt-", "chat/completions")
    assert all(token not in LOOKUP_SOURCE for token in forbidden)


def test_runner_has_no_lookup_admission_or_model_generated_experience_path():
    assert "def _lookup_and_ground" not in RUNNER_SOURCE
    assert "def _start_lookup_loop" not in RUNNER_SOURCE
    assert "LOOKUP_AUTONOMOUS" not in RUNNER_SOURCE
    assert "LOOKUP_INTERVAL_SEC" not in RUNNER_SOURCE
    assert 'source="lookup"' not in RUNNER_SOURCE
    assert "lookup_grounded" not in RUNNER_SOURCE
    assert 'command == "/lookup"' in RUNNER_SOURCE
    assert '"grounded": False' in RUNNER_SOURCE


def test_runner_compatibility_entrypoint_only_reports_the_boundary(monkeypatch):
    from dsf_ai_service import substrate_runner

    def forbidden_describe(*_args, **_kwargs):
        raise AssertionError("model-generated descriptions must never be called")

    monkeypatch.setattr(lookup_grounding, "describe", forbidden_describe)
    assert substrate_runner._lookup_once() == lookup_grounding.status()


def test_deployment_has_no_openai_lookup_or_youtube_secret_requirement():
    for token in (
        "OPENAI_API_KEY",
        "OPENAI_SECRET",
        "LOOKUP_AUTONOMOUS",
        "LOOKUP_INTERVAL_SEC",
    ):
        assert token not in DEPLOY_SOURCE
    # Spec v3 (2026-07-16): the YouTube feed key is an OPTIONAL injection —
    # present in Secrets Manager -> injected; absent -> the deploy proceeds
    # and the feed stays honestly disabled. The boundary this tripwire
    # guards is REQUIREMENT: a deploy must never fail on the YouTube key,
    # and no plaintext variant may appear.
    assert 'require_secret_arn "${YOUTUBE_SECRET_ID}"' not in DEPLOY_SOURCE
    assert "this is not an error" in DEPLOY_SOURCE  # absent-key path is loud + non-fatal
    secrets = DEPLOY_SOURCE.split("'secrets': [", 1)[1].split("'mountPoints': [", 1)[0]
    assert "if os.environ.get('YOUTUBE_SECRET_ARN')" in secrets  # conditional, never unconditional
    assert "YOUTUBE_API_KEY_PLAINTEXT" not in DEPLOY_SOURCE


def test_optional_youtube_feed_is_unregistered_and_truthful_without_key(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "configured")
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    feeds = world_feeds.available_feeds()
    status = world_feeds.feed_status()

    assert [feed["name"] for feed in feeds] == ["khan"]
    assert status["youtube"] == {
        "enabled": False,
        "reason": "disabled: YOUTUBE_API_KEY is not configured",
    }


def test_optional_youtube_feed_registers_only_when_its_key_exists(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("YOUTUBE_API_KEY", "configured")

    feeds = world_feeds.available_feeds()
    status = world_feeds.feed_status()

    assert [feed["name"] for feed in feeds] == ["youtube"]
    assert status["youtube"] == {"enabled": True, "reason": "configured"}
