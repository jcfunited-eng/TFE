"""Keep observation consumers aligned without making deployment a cognition authority."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = (ROOT / "tools" / "deploy_dsf_ai.sh").read_text(encoding="utf-8")
APP = (ROOT / "dsf_ai_service" / "app.py").read_text(encoding="utf-8")
GUALA_PAGE = (
    ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
).read_text(encoding="utf-8")
LOOM_PAGE = (
    ROOT / "dsf_ai_service" / "static" / "loomscan.html"
).read_text(encoding="utf-8")


def test_deployment_has_no_observation_schema_authority() -> None:
    assert "guala.observation_snapshot" not in DEPLOY
