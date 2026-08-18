"""Restore one complete, receipt-verified UF snapshot generation from S3."""

from __future__ import annotations

import sys
from pathlib import Path

from snapshot_generation import restore_current_generation


DESTINATION_ROOT = Path("/app")


def restore() -> bool:
    try:
        manifest = restore_current_generation(DESTINATION_ROOT)
    except Exception as error:
        print(f"[RESTORE] Snapshot generation restore failed: {type(error).__name__}: {error}")
        return False
    print(
        f"[RESTORE] Active generation {manifest['generation_id']} restored. "
        "Screener may start only after this verified set is present."
    )
    return True


if __name__ == "__main__":
    raise SystemExit(0 if restore() else 1)
