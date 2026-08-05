from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "dsf_ai_service" / "static"
GUALA = STATIC / "gualaloom.html"
LOOM = STATIC / "loomscan.html"
LEGAL = STATIC / "legal.html"
OBSERVATION_ROUTE = "/api/v1/guala/native-observation"


class _ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.references.append(value)


def _references(path: Path) -> set[str]:
    parser = _ReferenceParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return set(parser.references)


def _literal_api_routes(source: str) -> set[str]:
    return set(re.findall(r'(?<![A-Za-z0-9_./-])(/api/v1/[A-Za-z0-9_./-]+)', source))


def test_public_pages_have_one_literal_native_api_route() -> None:
    guala_source = GUALA.read_text(encoding="utf-8")
    loom_source = LOOM.read_text(encoding="utf-8")
    assert _literal_api_routes(guala_source) == {OBSERVATION_ROUTE}
    assert _literal_api_routes(loom_source) == {OBSERVATION_ROUTE}
    assert 'method:"GET"' in guala_source
    assert 'method:"GET"' in loom_source
    assert 'method:"POST"' in guala_source
    assert 'method:"POST"' not in loom_source
    assert "postCapability" in guala_source
    assert "safeEndpoint" in guala_source


def test_public_pages_contain_no_retired_authority_or_chat_surface() -> None:
    combined = GUALA.read_text(encoding="utf-8") + LOOM.read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "guala.observation_snapshot.v5",
        "3d6toi0gw0",
        "current_owner_state",
        "owner_state",
        "master_sense",
        "passive_whole_organism",
        "speechSynthesis",
        "SpeechSynthesisUtterance",
        "chi_density",
        "/converse",
        "/api/v1/teach",
        "/api/v1/correction",
        "/api/v1/auditory/reply",
    ):
        assert forbidden not in combined
    assert "No frontend inference creates activity" in combined
    assert "Missing state never becomes activity" in combined


def test_native_contract_sections_are_present_on_both_pages() -> None:
    required = (
        "generation",
        "identity",
        "sensory",
        "neuron_activity",
        "fractals",
        "formations",
        "recall",
        "cognitive_capital",
        "attention",
        "body",
        "autonomy",
        "articulation",
        "curriculum",
        "full_dsf",
        "persistence",
        "resources",
    )
    for path in (GUALA, LOOM):
        source = path.read_text(encoding="utf-8")
        assert "guala.native.public_observation.v1" in source
        for name in required:
            assert name in source


def test_static_pages_reference_only_approved_release_assets() -> None:
    assert _references(GUALA) == {
        "/gualaloom-rich-room-v3.png",
        "/loomscan.html",
    }
    assert _references(LOOM) == {
        "/guala-brain-foundation-v1.png",
        "/gualaloom.html",
    }
    for asset in (
        "gualaloom-rich-room-v3.png",
        "Guala_Talking_Bust_No_Bow_Transparent.png",
        "guala-brain-foundation-v1.png",
    ):
        assert (STATIC / asset).is_file()


def test_legal_notice_remains_truthful() -> None:
    source = LEGAL.read_text(encoding="utf-8").lower()
    assert "do not by themselves establish recognized words" in source
    assert "persistent learned and embodied state" in source
    assert "support@dsf-ai.com" in source
