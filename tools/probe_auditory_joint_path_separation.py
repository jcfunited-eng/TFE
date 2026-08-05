"""Isolate cochlear path geometry from the known-broken L4 equality gate.

This is a diagnostic only.  Bypassing L4 is prohibited for recognition; the
result identifies which layer owns rejection and grants no cognitive
authority.
"""

from __future__ import annotations

import json
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
import dsf_ai_service.substrate.auditory_reciprocity as reciprocity
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


def main() -> None:
    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    l5_owner = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None,
    )
    try:
        witnesses = tuple(
            reciprocity._pack_experience(
                _experience(path, index, l5_owner)[0]
            )
            for index, path in enumerate(RECORDINGS)
        )
    finally:
        stop_exact_field_executor()

    original = reciprocity._l4_lambda_interval
    reciprocity._l4_lambda_interval = (
        lambda _query, _left, _right, interval: interval
    )
    try:
        cells = []
        for left, right in ((1, 2), (0, 1), (0, 2), (3, 4)):
            matched, work = reciprocity._joint_cell_contains_python(
                witnesses[0],
                witnesses[left],
                witnesses[right],
                max_work=1_000_000,
            )
            cells.append({
                "left": RECORDINGS[left].name,
                "matched": matched,
                "query": RECORDINGS[0].name,
                "right": RECORDINGS[right].name,
                "work_cells": work,
            })
    finally:
        reciprocity._l4_lambda_interval = original
    print(json.dumps({
        "cells": cells,
        "l4_authority_bypassed": True,
        "recognition_authority": False,
        "schema": "guala.audit.auditory_joint_path_separation.v1",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
