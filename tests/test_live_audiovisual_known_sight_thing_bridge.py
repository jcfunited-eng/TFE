"""Source contract for the live audiovisual passive-learning cutover."""

from __future__ import annotations

import ast
from pathlib import Path


def test_sound_frame_uses_passive_learning_and_exact_trace_evocation() -> None:
    source_path = (
        Path(__file__).parents[1] / "dsf_ai_service" / "app.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    sound_frame = next(
        node
        for node in tree.body
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        and node.name == "sound_frame"
    )
    calls = {
        node.func.attr
        for node in ast.walk(sound_frame)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    literal_keys = {
        node.value
        for node in ast.walk(sound_frame)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
    }

    assert "admit_live_audiovisual_thing_sensory_expansion" not in calls
    assert "evoke_passive_causal_thing_from_sound" in calls
    assert "thing_sensory_expansion" not in literal_keys
    assert "passive_thing_learning" in literal_keys
    assert "sound_evoked_causal_thing" in literal_keys
