"""arcloom_demonstrator/tests/conftest.py

Package-local test configuration for standalone ArcLoom demonstrator.
Ensures package root is present in sys.path for deterministic imports.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
