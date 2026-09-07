from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
GUALA = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
LOOM = ROOT / "dsf_ai_service" / "static" / "loomscan.html"
OBSERVATION_ROUTE = "/api/v1/guala/observation"
PRESSURE_PREFIX = "/api/v1/guala/pressure/"
SCHEMA = "guala.lean_actor_observation.v1"
FULL_FIELDS = (
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
)


class _Parser(HTMLParser):
    pass


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _script(path: Path) -> str:
    matched = re.search(r"<script>([\s\S]+)</script>", _source(path))
    assert matched is not None
    return matched.group(1)


def _literal_api_routes(source: str) -> set[str]:
    return set(re.findall(r'"(/api/[^"?]*)"', source))


def test_two_pages_are_small_valid_and_use_the_lean_contract() -> None:
    for path in (GUALA, LOOM):
        source = _source(path)
        assert path.stat().st_size < 20_000
        assert SCHEMA in source
        assert OBSERVATION_ROUTE in source
        parser = _Parser(convert_charrefs=True)
        parser.feed(source)
        parser.close()


def test_route_graph_is_read_only_and_contains_no_retired_surface() -> None:
    guala = _source(GUALA)
    loom = _source(LOOM)
    combined = guala + loom
    assert _literal_api_routes(guala) == {
        OBSERVATION_ROUTE,
        PRESSURE_PREFIX,
    }
    assert _literal_api_routes(loom) == {OBSERVATION_ROUTE}
    assert "method:\"POST\"" not in combined
    assert "/occurrence" not in combined
    for retired in (
        "/api/v1/guala/native-observation",
        "/api/v1/gualaloom",
        "/converse",
        "guala.native.public_observation.v1",
        "guala.observation_snapshot.v5",
        "speechSynthesis",
        "WebSocket",
        "EventSource",
        "innerHTML",
    ):
        assert retired not in combined


def test_missing_capabilities_are_explicit_and_not_simulated() -> None:
    combined = _source(GUALA) + _source(LOOM)
    for truth in (
        "Speech remains failed",
        "conversation, camera, microphone, and visual ingress are not mounted",
        "No missing capability is simulated",
        "individual values are not projected here",
        "not scanned or reconstructed by Python",
        "meaningful self-selected action is not yet proved",
    ):
        assert truth in combined
    for field in FULL_FIELDS:
        assert field in combined


def test_pages_poll_one_cached_observation_only_while_visible() -> None:
    for path in (GUALA, LOOM):
        source = _source(path)
        assert "POLL_MS=5000" in source
        assert 'cache:"no-store"' in source
        assert "document.hidden" in source
        assert 'document.addEventListener("visibilitychange"' in source
        assert 'window.addEventListener("pagehide"' in source
        assert "controller.abort()" in source
    assert _script(LOOM).count("fetch(") == 1
    assert _script(GUALA).count("fetch(") == 2


def test_rendered_values_use_text_content_only() -> None:
    combined = _source(GUALA) + _source(LOOM)
    assert "textContent=value" in combined
    assert "JSON.stringify(value,null,2)" in combined
    assert "eval(" not in combined
    assert "Function(" not in combined


@pytest.mark.skipif(shutil.which("node") is None, reason="node is unavailable")
def test_inline_scripts_parse_as_javascript() -> None:
    for path in (GUALA, LOOM):
        completed = subprocess.run(
            [
                "node",
                "-e",
                "const vm=require('vm');new vm.Script(process.argv[1]);",
                _script(path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
