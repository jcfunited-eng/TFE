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
OCCURRENCE_ROUTE = "/api/v1/guala/occurrence"
PRESSURE_PREFIX = "/api/v1/guala/pressure/"
SCHEMA = "guala.lean_actor_observation.v1"


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


def test_pages_are_bounded_valid_and_share_the_lean_contract() -> None:
    assert GUALA.stat().st_size < 30_000
    assert LOOM.stat().st_size < 15_000
    for path in (GUALA, LOOM):
        source = _source(path)
        assert SCHEMA in source
        assert OBSERVATION_ROUTE in source
        parser = _Parser(convert_charrefs=True)
        parser.feed(source)
        parser.close()


def test_route_graph_uses_only_three_of_the_existing_five_routes() -> None:
    guala = _source(GUALA)
    loom = _source(LOOM)
    assert _literal_api_routes(guala) == {
        OBSERVATION_ROUTE,
        OCCURRENCE_ROUTE,
        PRESSURE_PREFIX,
    }
    assert _literal_api_routes(loom) == {OBSERVATION_ROUTE}
    assert 'method:"POST"' in guala
    assert 'method:"POST"' not in loom
    for retired in (
        "/api/v1/guala/native-observation",
        "/api/v1/gualaloom",
        "/converse",
        "guala.native.public_observation.v1",
        "guala.observation_snapshot.v5",
        "WebSocket",
        "EventSource",
        "speechSynthesis",
        "innerHTML",
        "localStorage",
        "sessionStorage",
    ):
        assert retired not in guala + loom


def test_world_page_has_the_authorized_embodied_access_only() -> None:
    source = _source(GUALA)
    for required in (
        "Guala_Talking_Bust_No_Bow_Transparent.png",
        "Guala's home and backyard",
        "135 achromatic receptor samples",
        "Enable camera",
        "Enable microphone",
        "Hear Guala",
        "Show image",
        "Words to show as light",
        "ABC / 123 lesson card",
        "Present with my voice",
        "Center on Guala",
        "no recognition, meaning, gait, or learning is claimed",
        "not live facial movement",
        "discarded, not queued",
        'href="/loomscan.html"',
    ):
        assert required in source
    for source_kind in (
        '"camera"',
        '"camera-microphone"',
        '"card-microphone"',
        '"media"',
        '"microphone"',
        '"text-light"',
        '"text-microphone"',
    ):
        assert source_kind in source


def test_browser_senses_keep_exact_bounds_and_no_backlog() -> None:
    source = _source(GUALA)
    for exact_boundary in (
        "audioContext.sampleRate!==16000",
        "new Uint8Array(8000)",
        "i<4000",
        "values.length!==135",
        "if(inFlight)",
        "if(inFlight||document.hidden)return",
        "setInterval(sensoryPulse,1000)",
        "retina_u8",
        "pcm_s16le_base64",
    ):
        assert exact_boundary in source


def test_loom_lights_only_direct_evidence_and_links_back() -> None:
    source = _source(LOOM)
    for required in (
        "guala-brain-foundation-v1.png",
        "not a claim of human anatomical localization",
        "Thought and memory contents cannot presently be observed",
        "external_retinal_site_count",
        "external_heard_sample_count",
        "self_heard_sample_count",
        "actual_root_motion",
        "pressure_sha256",
        'href="/gualaloom.html"',
    ):
        assert required in source


def test_pages_poll_one_cached_observation_only_while_visible() -> None:
    for path in (GUALA, LOOM):
        source = _source(path)
        assert "POLL_MS=3000" in source
        assert 'cache:"no-store"' in source
        assert "document.hidden" in source
        assert 'document.addEventListener("visibilitychange"' in source
        assert 'window.addEventListener("pagehide"' in source
        assert ".abort()" in source
    assert _script(LOOM).count("fetch(") == 1
    assert _script(GUALA).count("fetch(") == 3


def test_rendered_external_values_use_text_content_only() -> None:
    combined = _source(GUALA) + _source(LOOM)
    assert "textContent=value" in combined
    assert "JSON.stringify(value,null,2)" in combined
    assert "eval(" not in combined
    assert "Function(" not in combined


@pytest.mark.skipif(shutil.which("node") is None, reason="node is unavailable")
def test_inline_scripts_parse_as_javascript() -> None:
    for path in (GUALA, LOOM):
        completed = subprocess.run(
            ["node", "-e", "const vm=require('vm');new vm.Script(process.argv[1]);", _script(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
