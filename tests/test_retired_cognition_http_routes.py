from __future__ import annotations

import asyncio
import json

import pytest

from dsf_ai_service import app as app_module


EXPECTED_SCHEMA = "guala.retired_cognition.unavailable.v1"


@pytest.mark.parametrize("remote", (False, True))
def test_retired_cognition_routes_are_immediate_and_transport_invariant(
    monkeypatch,
    remote: bool,
) -> None:
    monkeypatch.setattr(app_module, "_is_remote", lambda: remote)
    invocations = (
        (
            "embodied_reading_lesson",
            app_module.embodied_reading_lesson(None),
        ),
        (
            "embodied_reading_lesson",
            app_module.poll_embodied_reading_lesson("retired"),
        ),
        (
            "physical_surface_tutoring",
            app_module.physical_surface_lesson(None),
        ),
        (
            "physical_surface_tutoring",
            app_module.poll_physical_surface_lesson("retired"),
        ),
        (
            "causal_inquiry_transient_act",
            app_module.causal_inquiry_transient_act(None),
        ),
        (
            "causal_inquiry_transient_consequence",
            app_module.causal_inquiry_transient_consequence(None),
        ),
    )

    for capability, invocation in invocations:
        response = asyncio.run(invocation)
        body = json.loads(response.body)
        assert response.status_code == 410
        assert body == {
            "capability": capability,
            "native_exact_field_preserved": True,
            "reason": "legacy_python_cognition_retired",
            "schema": EXPECTED_SCHEMA,
            "status": "unavailable",
        }
