"""Isolated exact cold-restore proof for one materialized Guala generation."""

from __future__ import annotations

import argparse


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
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    probe = Guala()
    try:
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
        probe.quiesce_background_workers(timeout=120.0)


if __name__ == "__main__":
    raise SystemExit(main())
