"""Measure bounded receipt material for real event-local auditory fields."""

from __future__ import annotations

import json
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    mount_auditory_l4_causal_support,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tools.probe_auditory_surrounded_event_recognition import _experience


RECORDINGS = (
    Path("/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 1.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 2.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Daddy says Hello.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Your Name is Guala.mp3"),
)


def _registry_bytes(registry) -> int:
    return sum(len(value.payload) for value in registry.records)


def main() -> None:
    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    reports = []
    try:
        for index, path in enumerate(RECORDINGS):
            experience, source = _experience(path, index, l5_owner)
            support = mount_auditory_l4_causal_support(experience)
            tuple_count = sum(
                len(component.l4_field_tuples)
                for channel in experience.channels
                for component in (
                    channel.pressure,
                    channel.carrier_phase_advance,
                )
            )
            support_bytes = len(support.payload()) + sum(
                len(component.payload())
                + sum(len(value.payload()) for value in component.tuples)
                for component in support.components
            )
            reports.append({
                **source,
                "l4_tuple_count": tuple_count,
                "upstream_record_count": len(
                    experience.upstream_receipt_registry.records
                ),
                "upstream_payload_bytes": _registry_bytes(
                    experience.upstream_receipt_registry
                ),
                "l5_record_count": len(experience.receipt_registry.records),
                "l5_payload_bytes": _registry_bytes(
                    experience.receipt_registry
                ),
                "causal_support_payload_bytes": support_bytes,
            })
    finally:
        stop_exact_field_executor()
    print(json.dumps({
        "schema": "guala.audit.auditory_receipt_bytes.v1",
        "recordings": reports,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
