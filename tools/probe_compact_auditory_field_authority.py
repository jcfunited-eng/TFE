"""Measure lossless compact auditory authority on supplied recordings."""

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
from dsf_ai_service.substrate.compact_auditory_field_authority import (
    MAX_COMPACT_AUDITORY_FIELD_BYTES,
    compact_auditory_field_from_l5,
    decode_compact_auditory_field,
)
from tools.probe_auditory_surrounded_event_recognition import (
    _experience,
)


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
            authority = compact_auditory_field_from_l5(
                experience,
                support,
            )
            encoded = authority.encoded()
            restored = decode_compact_auditory_field(encoded)
            if restored != authority or restored.encoded() != encoded:
                raise RuntimeError(
                    "compact auditory authority did not round-trip"
                )
            reports.append({
                **source,
                "authority_receipt_sha256": (
                    authority.authority_receipt_sha256
                ),
                "compact_authority_bytes": len(encoded),
                "full_field_tuple_count": sum(
                    len(value.tuples)
                    for value in authority.components
                ),
                "l5_receipt_payload_bytes": _registry_bytes(
                    experience.receipt_registry
                ),
                "source_receipt_payload_bytes": _registry_bytes(
                    experience.upstream_receipt_registry
                ),
                "within_two_megabyte_boundary": (
                    len(encoded) <= MAX_COMPACT_AUDITORY_FIELD_BYTES
                ),
            })
    finally:
        stop_exact_field_executor()
    print(json.dumps({
        "maximum_authority_bytes": MAX_COMPACT_AUDITORY_FIELD_BYTES,
        "recordings": reports,
        "schema": "guala.audit.compact_auditory_field_authority.v1",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
