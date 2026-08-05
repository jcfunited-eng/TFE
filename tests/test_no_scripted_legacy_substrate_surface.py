"""Prove the serving application cannot expose the retired scripted toy.

The June 2026 ``DeepMultiModalCognition`` surface installed a fixed vocabulary
and a Goodnight Moon corpus on first use.  It was a standalone demonstration,
not Guala's causal sensory substrate.  These checks prevent either the direct
routes or the silent v7 relay from being mounted again.
"""

from __future__ import annotations

import ast
from pathlib import Path

from dsf_ai_service import app as app_module


APP_PATH = Path(__file__).parents[1] / "dsf_ai_service" / "app.py"
RETIRED_ROUTES = {
    "/substrate/feed_senses",
    "/substrate/hear_word",
}
RETIRED_NAMES = {
    "SubstrateFeedRequest",
    "SubstrateHearRequest",
    "_get_bridge",
    "_get_substrate",
    "_init_substrate",
    "substrate_feed_senses",
    "substrate_hear_word",
}
RETIRED_REFERENCES = {
    "DeepMultiModalCognition",
    "GOODNIGHT_MOON",
    "bridge_mm_to_v7",
    "bridge_v7_to_mm",
}


def _route_paths(tree: ast.AST) -> set[str]:
    paths: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "app"
                and decorator.func.attr in {
                    "delete",
                    "get",
                    "patch",
                    "post",
                    "put",
                }
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
                and isinstance(decorator.args[0].value, str)
            ):
                paths.add(decorator.args[0].value)
    return paths


def test_scripted_legacy_routes_and_initializer_are_absent() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(APP_PATH))
    defined_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        )
    }

    assert RETIRED_ROUTES.isdisjoint(_route_paths(tree))
    assert RETIRED_NAMES.isdisjoint(defined_names)
    for reference in RETIRED_REFERENCES:
        assert reference not in source


def test_scripted_legacy_routes_are_not_mounted() -> None:
    mounted_paths = {
        route.path
        for route in app_module.app.routes
    }
    assert RETIRED_ROUTES.isdisjoint(mounted_paths)


def test_retired_v7_conversation_is_absent() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(APP_PATH))
    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "v7_converse" not in function_names
    assert "/api/v7/converse" not in _route_paths(tree)
