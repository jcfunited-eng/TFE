"""Run selected pytest targets under the production exact-field owner.

The application shutdown contract intentionally retires the process-wide
executor.  A pytest process can exercise shutdown and then continue with
another independent application contract, so the harness proves a healthy
owner before every test boundary.  Production still has exactly one owner for
the lifetime of one application process.
"""

from __future__ import annotations

import sys

import pytest

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)


class _ExactFieldOwnerBoundary:
    """Maintain the production owner across independent pytest lifetimes."""

    @staticmethod
    def pytest_runtest_setup(item) -> None:
        del item
        owner = start_exact_field_executor()
        owner.assert_healthy()


def main() -> None:
    plugin = _ExactFieldOwnerBoundary()
    try:
        result = pytest.main(sys.argv[1:], plugins=[plugin])
    finally:
        stop_exact_field_executor()
    raise SystemExit(result)


if __name__ == "__main__":
    main()
