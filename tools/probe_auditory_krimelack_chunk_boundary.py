"""Falsify fixed-unit Krimelack recall when speech crosses a transport edge."""

from __future__ import annotations

import json
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_krimelack_memory import (
    AuditoryKrimelackMemoryOwner,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from tools.probe_auditory_krimelack_continuous_chunk import (
    _continuous_experience,
    _event_pcm,
)
from tools.probe_auditory_surrounded_event_recognition import _experience


TUTOR = Path(
    "/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"
)
QUERY = Path(
    "/workspaces/Tao_Financial_Engine/harness/hello guala 2.mp3"
)


def main() -> None:
    executor = start_exact_field_executor()
    executor.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        tutor = _experience(TUTOR, 0, l5_owner)[0]
        memory = AuditoryKrimelackMemoryOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=AuditoryTutorAuthority.unrequired(),
        )
        memory.teach(tutor, tutor_label="hello guala")
        pcm = _event_pcm(QUERY)
        midpoint = len(pcm) // 4 * 2
        cases = {
            "complete": pcm,
            "first_half": pcm[:midpoint],
            "second_half": pcm[midpoint:],
        }
        results = {}
        for ordinal, (name, value) in enumerate(cases.items(), 1):
            query = _continuous_experience(
                value,
                offset=0,
                ordinal=ordinal,
                owner=l5_owner,
            )
            recognition = memory.recognize(query)
            results[name] = {
                "pcm_samples": len(value) // 2,
                "state": recognition.state.value,
                "tutor_label": recognition.tutor_label,
                "work_cells": recognition.work_cells,
            }
    finally:
        stop_exact_field_executor()
    print(json.dumps({
        "results": results,
        "schema": "guala.audit.auditory_krimelack_chunk_boundary.v1",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
