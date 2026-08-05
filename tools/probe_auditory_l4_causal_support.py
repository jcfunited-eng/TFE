"""Prove exact L4 causal support on supplied real auditory recordings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    mount_auditory_l4_causal_support,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tools.probe_auditory_surrounded_event_recognition import _experience


def _has_continuous_coverage(support) -> bool:
    for component in support.components:
        if (
            not component.tuples
            or component.tuples[0].causal_interval_start
            != support.source_time_start
            or component.tuples[-1].causal_interval_end
            != support.source_time_end
        ):
            return False
        prior_end = support.source_time_start
        prior_index = -1
        for exact in component.tuples:
            if (
                exact.causal_interval_start != prior_end
                or exact.source_index_start != prior_index + 1
                or tuple(name for name, _value in exact.fields)
                != DSF_FIELD_ORDER
            ):
                return False
            prior_end = exact.causal_interval_end
            prior_index = exact.source_index_end
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("recordings", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.recordings:
        if not path.is_file():
            raise SystemExit(f"recording does not exist: {path}")

    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    reports = []
    try:
        for ordinal, path in enumerate(args.recordings):
            experience, source_report = _experience(
                path,
                ordinal,
                l5_owner,
            )
            support = mount_auditory_l4_causal_support(experience)
            support.verify(experience)
            reports.append({
                **source_report,
                "causal_support_integrity_receipt_sha256": (
                    support.integrity_receipt_sha256
                ),
                "component_count": len(support.components),
                "continuous_interval_coverage": (
                    _has_continuous_coverage(support)
                ),
                "event_boundary": support.event_boundary,
                "full_dsf_field_order": list(DSF_FIELD_ORDER),
                "l4_tuple_count": sum(
                    len(component.tuples)
                    for component in support.components
                ),
                "sample_support_counts": [
                    (
                        component.tuples[-1].source_index_end
                        - component.tuples[0].source_index_start
                        + 1
                    )
                    for component in support.components
                ],
            })
    finally:
        stop_exact_field_executor()

    print(json.dumps({
        "recording_count": len(reports),
        "recordings": reports,
        "schema": "guala.audit.auditory_l4_causal_support.v2",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
