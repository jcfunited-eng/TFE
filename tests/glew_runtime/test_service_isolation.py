import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_module_level_service_does_not_import_or_mount_legacy_application():
    script = """
import json
import sys
from dsf_ai_service.glew_runtime.service import app
print(json.dumps({
    "legacy_imported": "dsf_ai_service.app" in sys.modules,
    "paths": sorted(route.path for route in app.routes),
}))
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT)

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result == {
        "legacy_imported": False,
        "paths": ["/glew/conformance", "/glew/status"],
    }
