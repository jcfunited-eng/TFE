"""Falsify whole-unit Krimelack recall with sequential competing sound."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

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
    TRANSPORT_SAMPLES,
    _continuous_experience,
    _event_pcm,
)
from tools.probe_auditory_surrounded_event_recognition import _experience


HELLO = Path(
    "/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"
)
HELLO_SECOND = Path(
    "/workspaces/Tao_Financial_Engine/harness/hello guala 1.mp3"
)
UNRELATED = Path(
    "/workspaces/Tao_Financial_Engine/docs/Daddy says Hello.mp3"
)


def main() -> None:
    executor = start_exact_field_executor()
    executor.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        tutor = _experience(HELLO, 0, l5_owner)[0]
        memory = AuditoryKrimelackMemoryOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=AuditoryTutorAuthority.unrequired(),
        )
        memory.teach(tutor, tutor_label="hello guala")
        hello = np.frombuffer(_event_pcm(HELLO_SECOND), dtype="<i2")
        unrelated = np.frombuffer(_event_pcm(UNRELATED), dtype="<i2")
        cases = {
            "hello_only": hello,
            "hello_then_unrelated": np.concatenate((hello, unrelated)),
            "unrelated_then_hello": np.concatenate((unrelated, hello)),
            "unrelated_only": unrelated,
        }
        results = {}
        for ordinal, (name, values) in enumerate(cases.items(), 1):
            if len(values) > TRANSPORT_SAMPLES:
                raise RuntimeError(
                    f"{name} exceeds the two-second transport proof"
                )
            query = _continuous_experience(
                values.astype("<i2", copy=False).tobytes(),
                offset=0,
                ordinal=ordinal,
                owner=l5_owner,
            )
            recognition = memory.recognize(query)
            results[name] = {
                "event_samples": len(values),
                "state": recognition.state.value,
                "tutor_label": recognition.tutor_label,
                "work_cells": recognition.work_cells,
            }
    finally:
        stop_exact_field_executor()
    print(json.dumps({
        "results": results,
        "schema": (
            "guala.audit.auditory_krimelack_competing_sequence.v1"
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
