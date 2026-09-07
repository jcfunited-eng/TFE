from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
RETIRED_APP = ROOT / "dsf_ai_service" / "native_production_app.py"
LEAN_DOCKERFILE = ROOT / "dsf_ai_service" / "Dockerfile.lean"


def test_retired_shell_is_a_small_fail_closed_marker() -> None:
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


def test_lean_image_excludes_and_cannot_boot_the_retired_shell() -> None:
    source = LEAN_DOCKERFILE.read_text(encoding="utf-8")
    assert "test ! -e /app/dsf_ai_service/native_production_app.py" in source
    assert '"dsf_ai_service.lean_production_app:app"' in source
    assert '"dsf_ai_service.native_production_app:app"' not in source
