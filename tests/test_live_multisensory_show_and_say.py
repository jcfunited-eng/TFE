from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import dsf_ai_service.app as app_module


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _script() -> str:
    source = _page()
    start = source.index("<script>") + len("<script>")
    end = source.index("</script>", start)
    return source[start:end]


def test_live_six_sense_projection_keeps_truthful_absence() -> None:
    states = (
        ("sight", "observed"),
        ("sound", "observed"),
        ("touch", "sensor_unavailable"),
        ("smell", "sensor_unavailable"),
        ("taste", "sensor_unavailable"),
        ("body", "sensor_unavailable"),
    )
    settlement = SimpleNamespace(
        interpretations=tuple(
            SimpleNamespace(sense=sense, state=state)
            for sense, state in states
        )
    )

    assert app_module._live_sensory_boundary_projection(settlement) == dict(
        states
    )

    missing = SimpleNamespace(interpretations=settlement.interpretations[:-1])
    with pytest.raises(ValueError, match="six-sense order"):
        app_module._live_sensory_boundary_projection(missing)


def test_visual_provenance_is_bounded_and_carries_no_symbol_label() -> None:
    camera = app_module.GLMessage(text="", visual_source="camera_stream")
    simulated = app_module.GLMessage(
        text="",
        visual_source="simulated_material_display",
    )

    assert camera.visual_source == "camera_stream"
    assert simulated.visual_source == "simulated_material_display"
    assert not hasattr(simulated, "symbol")
    assert not hasattr(simulated, "meaning")
    with pytest.raises(ValidationError):
        app_module.GLMessage(text="", visual_source="named_apple_profile")
