"""The rejected daemon cannot silently create or overwrite a second organism."""

from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("entry", ["run_64d_continuous_hardening.py", "keep_64d_hardening.sh"])
def test_retired_entry_is_nonzero_and_preserves_all_checkpoint_bytes(tmp_path, entry):
    state = tmp_path / "backups" / "runtime" / "guala_64d_hardened_state.bin"
    state.parent.mkdir(parents=True)
    # Deliberately invalid: no decoder, reset or writer may be reached at all.
    predecessor = b"historical synthetic bytes - never silently replace"
    state.write_bytes(predecessor)
    command = [sys.executable if entry.endswith(".py") else "bash", str(ROOT / "tools" / entry)]
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=5)
    assert result.returncode == 78
    assert "REFUSED: synthetic 64D hardening is retired" in result.stderr
    assert state.read_bytes() == predecessor
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file()) == [
        "backups/runtime/guala_64d_hardened_state.bin"
    ]
