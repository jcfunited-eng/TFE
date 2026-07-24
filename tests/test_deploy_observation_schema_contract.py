"""Keep the production route gate aligned with the served observation contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = (ROOT / "tools" / "deploy_dsf_ai.sh").read_text()
APP = (ROOT / "dsf_ai_service" / "app.py").read_text()
GUALA_PAGE = (ROOT / "dsf_ai_service" / "static" / "gualaloom.html").read_text()
LOOM_PAGE = (ROOT / "dsf_ai_service" / "static" / "loomscan.html").read_text()


def test_deploy_and_observation_consumers_require_the_served_schema() -> None:
    schema = "guala.observation_snapshot.v4"
    for source in (DEPLOY, APP, GUALA_PAGE, LOOM_PAGE):
        assert schema in source
    assert "guala.observation_snapshot.v1" not in DEPLOY
