from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dsf_ai_service" / "static" / "loomscan.html"
IMAGE = ROOT / "dsf_ai_service" / "static" / "guala-brain-foundation-v1.png"
SCHEMA = "guala.native.public_observation.v1"
ROUTE = "/api/v1/guala/native-observation"
FIELDS = ("D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k")
SENSES = (
    "visual",
    "auditory",
    "text",
    "touch",
    "temperature",
    "smell",
    "taste",
    "vestibular",
    "proprioception",
    "interoception",
)


def _source() -> str:
    return PAGE.read_text(encoding="utf-8")


def _script() -> str:
    source = _source()
    start = source.index("<script>") + len("<script>")
    end = source.index("</script>", start)
    return source[start:end]


def _script_without_boot() -> str:
    return _script().rsplit("\ncreateUI();", 1)[0]


def _json_array_constant(name: str) -> list[str]:
    matched = re.search(rf"const {name}=(\[[^;]+\]);", _source())
    assert matched is not None
    value = json.loads(matched.group(1))
    assert isinstance(value, list)
    return value


def test_scan_is_data_first_and_art_is_explicitly_non_authoritative() -> None:
    source = _source()
    assert IMAGE.is_file()
    assert IMAGE.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Illustrative foundation only" in source
    assert "claims no human biological localization or live activity" in source
    assert "Exact native records are shown beside and below it" in source
    assert source.index("Illustrative foundation only") < source.index(
        "Whole-organism sensory frontier"
    )


def test_scan_uses_only_the_native_public_observation_contract() -> None:
    source = _source()
    assert f'const OBSERVATION_ROUTE="{ROUTE}"' in source
    assert f'const OBSERVATION_SCHEMA="{SCHEMA}"' in source
    assert 'method:"GET"' in source
    assert 'method:"POST"' not in source
    assert 'headers["If-None-Match"]=etag' in source
    assert "response.status===304" in source
    assert "const POLL_INTERVAL_MS=15000" in source
    assert "if(!document.hidden)" in source


def test_scan_exposes_all_whole_organism_sensory_modalities() -> None:
    source = _source()
    assert "Whole-organism sensory frontier" in source
    for sense in SENSES:
        assert f'["{sense}",' in source
        assert f'`sense-${{id}}-state`' in source
    assert "Current extent" in source
    assert "Reason / loss" in source


def test_scan_keeps_each_causal_frontier_stage_separate() -> None:
    source = _source()
    for title, path in (
        ("Sensory delivery", "sensory"),
        ("Neuron activity", "neuron_activity"),
        ("Retained fractals", "fractals"),
        ("Formations", "formations"),
        ("Recall / reassembly", "recall"),
        ("Autonomous action", "autonomy"),
        ("Sensed consequence", "autonomy.consequence"),
    ):
        assert title in source
        assert f'"{path}"' in source
    assert "No count or receipt is promoted into cognition" in source


def test_growth_hierarchy_uses_direct_native_counts() -> None:
    source = _source()
    for title, path in (
        ("Fractals", "fractals.count"),
        ("Mosaics", "formations.mosaic_count"),
        ("Mosaics of mosaics", "formations.mosaic_of_mosaics_count"),
        ("Tapestries", "formations.tapestry_count"),
        (
            "Tapestries of tapestries",
            "formations.tapestry_of_tapestries_count",
        ),
        ("Weaves", "formations.weave_count"),
    ):
        assert title in source
        assert f'"{path}"' in source
    assert "native retained formation evidence" in source


def test_recall_action_body_articulation_and_curriculum_are_distinct() -> None:
    source = _source()
    for title, path in (
        ("Attention", "attention"),
        ("Hippocampal / distributed recall", "recall"),
        ("Causal action loop", "autonomy"),
        ("Body / world / consequence", "body"),
        ("Articulation / emitted sound", "articulation"),
        ("Curriculum experience", "curriculum"),
    ):
        assert title in source
        assert f'"{path}"' in source
    assert "no frontend-generated labels or meanings" in source


def test_cognitive_capital_is_39_capabilities_by_10_dimensions() -> None:
    dimensions = _json_array_constant("CAPITAL_DIMENSIONS")
    capabilities = _json_array_constant("CAPITAL_CAPABILITIES")
    assert len(dimensions) == 10
    assert len(set(dimensions)) == 10
    assert len(capabilities) == 39
    assert len(set(capabilities)) == 39
    source = _source()
    assert "There is no aggregate score" in source
    assert "normalizedCredits" in source
    assert "credited" in source


def test_full_dsf_is_an_exact_reference_without_flattening() -> None:
    source = _source()
    expected = "required=" + json.dumps(list(FIELDS), separators=(",", ":"))
    assert expected in source
    assert "The scan never averages or flattens" in source
    assert "exact reference" in source
    assert "observation loss" in source
    assert "decision authority" in source
    assert "support minus drag" not in source.lower()
    assert "weighted score" not in source.lower()


def test_persistence_compute_memory_and_storage_are_truthful_records() -> None:
    source = _source()
    assert "Persistence and bounded resources" in source
    assert "Native persistence" in source
    assert "CPU / calls / processes" in source
    assert "RAM / state / storage" in source
    assert "resources?.python_calls" in source
    assert "resources?.process_count" in source
    assert "resources?.ram_bytes" in source
    assert "resources?.storage_bytes" in source


def test_complete_loomscan_script_compiles() -> None:
    completed = subprocess.run(
        ["node", "-e", "new Function(" + json.dumps(_script()) + ");"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_renderer_preserves_real_zero_counts_and_exact_field_order() -> None:
    ids = (
        "fractal-count",
        "mosaic-count",
        "mosaic-relation-count",
        "tapestry-count",
        "tapestry-relation-count",
        "weave-count",
        "field-contract",
    )
    snapshot = {
        "fractals": {"count": 0},
        "formations": {
            "mosaic_count": 0,
            "mosaic_of_mosaics_count": 0,
            "tapestry_count": 0,
            "tapestry_of_tapestries_count": 0,
            "weave_count": 0,
        },
        "full_dsf": {
            "available": True,
            "status": "observed",
            "fields": list(FIELDS),
            "evidence_ref": "f" * 64,
            "decision_authority": False,
            "projection": "exact bounded reference",
            "observation_loss": "field body omitted from public view",
        },
    }
    program = f"""
class Element {{constructor(){{this.textContent='';this.className='';}}}}
const elements=Object.fromEntries({json.dumps(ids)}.map(id=>[id,new Element()]));
globalThis.document={{getElementById:id=>elements[id]||null}};
{_script_without_boot()}
const observation={json.dumps(snapshot, separators=(',', ':'))};
renderGrowth(observation);renderDsf(observation);
process.stdout.write(JSON.stringify({{
  fractals:elements['fractal-count'].textContent,
  mosaics:elements['mosaic-count'].textContent,
  weaves:elements['weave-count'].textContent,
  field:elements['field-contract'].textContent
}}));
"""
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    rendered = json.loads(completed.stdout)
    assert rendered["fractals"] == "0"
    assert rendered["mosaics"] == "0"
    assert rendered["weaves"] == "0"
    assert "field order D_k → M_k → R_rev_k → U_star_k → C_k → P_k → B_k" in rendered["field"]
    assert "decision authority false" in rendered["field"]
    assert "observation loss field body omitted from public view" in rendered["field"]
