"""Isolated exact cold-restore proof for one materialized Guala generation."""

from __future__ import annotations

import argparse
import os


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-directory", required=True)
    parser.add_argument("--expected-identity", required=True)
    parser.add_argument("--expected-tick", required=True, type=int)
    parser.add_argument(
        "--allow-authenticated-legacy-pickle",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    from dsf_ai_service.app import SEED_CORPORA
    from dsf_ai_service.glew_runtime.exact_field_executor import (
        start_exact_field_executor,
        stop_exact_field_executor,
    )
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    # The serving owner requires the fixed exact-field executor before Guala
    # can construct or restore any native full-field state.  The isolated
    # validator must reproduce that same boot boundary; otherwise it rejects
    # a valid generation merely because its own execution organ is absent.
    os.environ["GUALA_EXACT_FIELD_EXECUTOR_REQUIRED"] = "1"
    exact_field_owner = start_exact_field_executor()
    exact_field_owner.assert_healthy()

    probe = None
    try:
        probe = Guala()
        for corpus_id, corpus in SEED_CORPORA.items():
            probe.add_corpus(
                corpus_id,
                corpus["title"],
                corpus["lines"],
            )
        probe.load_full_state(
            values.active_directory,
            require_exact_binary=True,
            allow_authenticated_legacy_pickle=(
                values.allow_authenticated_legacy_pickle
            ),
        )
        if not bool(getattr(probe, "_load_successful", False)):
            raise RuntimeError(
                "cold-restore probe did not complete an exact engine load"
            )
        if (
            getattr(probe, "_guala_identity", None)
            != values.expected_identity
        ):
            raise RuntimeError(
                "cold-restore probe identity differs from generation"
            )
        if int(probe.tick) != values.expected_tick:
            raise RuntimeError(
                "cold-restore probe tick differs from generation"
            )
        return 0
    finally:
        try:
            if probe is not None:
                probe.quiesce_background_workers(timeout=120.0)
        finally:
            stop_exact_field_executor()


if __name__ == "__main__":
    raise SystemExit(main())
