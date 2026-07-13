"""V7 sessions must live below the process's canonical active state root."""

import os
import subprocess
import sys
from pathlib import Path


def test_v7_state_dir_derives_from_active_state_environment(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    active_root = tmp_path / "canonical-active"
    env = dict(os.environ)
    env["STATE_DIR"] = str(active_root)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from dsf_ai_service.substrate.v7_engine import STATE_DIR; "
                "print(STATE_DIR)"
            ),
        ],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == str(active_root / "v7_sessions")

