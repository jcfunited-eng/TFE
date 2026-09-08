from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
RETIRED_APP = ROOT / "dsf_ai_service" / "native_production_app.py"
DEFAULT_DOCKERFILE = ROOT / "dsf_ai_service" / "Dockerfile"
BUILD_SPEC = ROOT / "dsf_ai_service" / "buildspec.yml"
RELEASE_MANIFEST = ROOT / "deploy" / "guala_release_manifest.json"


def test_retired_shell_exists_only_as_a_small_fail_closed_marker() -> None:
    source = RETIRED_APP.read_text(encoding="utf-8")
    assert len(source.splitlines()) <= 16
    assert "49d9fdd60c539ef02809a35991686faca92e1720" in source
    assert "f904f89178076e02901740ee3133e254d3e06459e114b7ed631b9968581ba1ea" in source
    assert "FastAPI" not in source
    assert "home_world_authority" not in source
    assert "restore_native_resident_organism" not in source

    result = subprocess.run(
        [sys.executable, "-c", "import dsf_ai_service.native_production_app"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode != 0
    assert "retired Guala shell quarantined" in result.stderr


def test_default_image_can_boot_only_the_lean_shell() -> None:
    source = DEFAULT_DOCKERFILE.read_text(encoding="utf-8")
    for retired in (
        "dsf_ai_service/app.py",
        "dsf_ai_service/native_production_app.py",
        "dsf_ai_service/candidate_release_rehearsal.py",
        "dsf_ai_service/cold_restore_probe.py",
    ):
        assert f"test ! -e /app/{retired}" in source
    assert '"dsf_ai_service.lean_production_app:app"' in source
    assert '"dsf_ai_service.native_production_app:app"' not in source
    assert '"dsf_ai_service.app:app"' not in source

    build = BUILD_SPEC.read_text(encoding="utf-8")
    assert "--file dsf_ai_service/Dockerfile" in build
    assert "Dockerfile.lean" not in build
    assert "Dockerfile.nogil" not in build


def test_reviewed_release_contains_only_the_lean_runtime_closure() -> None:
    manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["runtime_entrypoints"] == [
        "dsf_ai_service/lean_production_app.py"
    ]
    runtime = next(
        set(category["files"])
        for category in manifest["categories"]
        if category["name"] == "runtime_python"
    )
    assert "dsf_ai_service/lean_production_app.py" in runtime
    for retired in (
        "dsf_ai_service/app.py",
        "dsf_ai_service/native_production_app.py",
        "dsf_ai_service/candidate_release_rehearsal.py",
        "dsf_ai_service/cold_restore_probe.py",
    ):
        assert retired not in runtime
