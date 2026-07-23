from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_observation_endpoint_exposes_authoritative_embodied_state(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "observation-route-key")

    import dsf_ai_service.app as app_module
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    organism = Guala()
    previous = app_module._guala
    app_module._guala = organism
    try:
        response = TestClient(app_module.app).get(
            "/api/v1/gualaloom/observation"
        )
        assert response.status_code == 200
        value = response.json()
        assert value["schema"] == "guala.observation_snapshot.v1"
        assert value["embodiment"]["status"] == "observed"
        assert value["embodiment"]["location"] == {
            "room_id": "W1",
            "revision": 0,
        }
        assert value["embodiment"]["room_bounds"] == {
            "minimum": {"x_mm": 0, "y_mm": 0, "z_mm": 0},
            "maximum": {"x_mm": 5000, "y_mm": 5000, "z_mm": 3000},
        }
        assert value["embodiment"]["body"]["pose"] == {
            "heading_millidegrees": 0,
            "position": {"x_mm": 1000, "y_mm": 1000, "z_mm": 0},
        }
        assert value["embodiment"]["objects"] == [
            {
                "held_by_body_id": None,
                "mass_grams": 500,
                "object_id": "W1-object-1",
                "position": {"x_mm": 1500, "y_mm": 1000, "z_mm": 0},
                "radius_mm": 100,
            }
        ]
        assert value["embodied_action"] == {
            "status": "idle",
            "world_revision": 0,
        }
        assert value["conversation"]["status"] == "unavailable"
        assert len(value["snapshot_receipt_sha256"]) == 64
    finally:
        app_module._guala = previous
        organism.shutdown()


def test_conversation_ui_uses_one_observed_reply_surface() -> None:
    page = Path(
        "dsf_ai_service/static/gualaloom.html"
    ).read_text(encoding="utf-8")

    assert "/api/v1/gualaloom/observation" in page
    assert "function pollObservation()" in page
    assert "addMsg('she is here','system')" not in page
    assert "setTimeout(pollRoom" not in page
    assert "setTimeout(pollLocation" not in page
    assert "addEmissionMsg(resp,d.emission_id||null,text)" in page
    assert "aria-label','confirm this reply'" in page
    assert "aria-label','correct this reply'" in page
    assert "Embodied State" in page


def test_loom_scan_separates_embodied_state_from_lexical_scene_lanes() -> None:
    page = Path(
        "dsf_ai_service/static/loomscan.html"
    ).read_text(encoding="utf-8")

    assert "/api/v1/gualaloom/observation" in page
    assert "embodied location" in page
    assert "body state" in page
    assert "embodied action" in page
    assert "observed conversation" in page
    assert "lexical place lane" in page
    assert "lexical ambient lane" in page
    assert "cdef9bcf" not in page
    assert "||'v7'" not in page


ROOT = Path(__file__).resolve().parents[1]
OBSERVATION_PAGES = (
    ROOT / "dsf_ai_service" / "static" / "gualaloom.html",
    ROOT / "dsf_ai_service" / "static" / "loomscan.html",
)


def _spatial_model_from_page(page: Path, embodiment: dict) -> dict:
    source = page.read_text(encoding="utf-8")
    start = source.index("function buildW1SpatialModel(")
    end = source.index("\nfunction renderW1SpatialObservation(", start)
    model_source = source[start:end]
    program = f"""
      {model_source}
      const result=buildW1SpatialModel({json.dumps(embodiment)});
      process.stdout.write(JSON.stringify(result));
    """
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _rendered_spatial_view_from_page(page: Path, embodiment: dict) -> dict:
    source = page.read_text(encoding="utf-8")
    start = source.index("function buildW1SpatialModel(")
    end = source.index(
        "// --- End authoritative W1 spatial observation ---", start
    )
    function_source = source[start:end]
    program = f"""
      class Element {{
        constructor(id=''){{
          this.id=id;this.className='';this.style={{}};this.hidden=true;
          this.attributes={{}};this.children=[];this._textContent='';
        }}
        set textContent(value){{this._textContent=String(value);this.children=[];}}
        get textContent(){{return this._textContent;}}
        setAttribute(name,value){{this.attributes[name]=String(value);}}
        appendChild(value){{this.children.push(value);}}
      }}
      const elements={{
        'w1-spatial-meta':new Element('w1-spatial-meta'),
        'w1-spatial-room':new Element('w1-spatial-room'),
        'w1-spatial-inventory':new Element('w1-spatial-inventory'),
      }};
      globalThis.document={{
        getElementById:id=>elements[id],
        createElement:()=>new Element(),
      }};
      {function_source}
      renderW1SpatialObservation({json.dumps(embodiment)});
      const room=elements['w1-spatial-room'];
      process.stdout.write(JSON.stringify({{
        meta:elements['w1-spatial-meta'].textContent,
        inventory:elements['w1-spatial-inventory'].textContent,
        hidden:room.hidden,
        aspectRatio:room.style.aspectRatio,
        ariaLabel:room.attributes['aria-label'],
        markers:room.children.map(marker=>({{
          className:marker.className,
          left:marker.style.left,
          top:marker.style.top,
          width:marker.style.width,
          height:marker.style.height,
          rotate:marker.style.rotate||null,
          ariaLabel:marker.attributes['aria-label'],
          label:marker.children[0].textContent,
        }})),
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _nondefault_observation() -> dict:
    return {
        "status": "observed",
        "location": {"room_id": "observed-room-73", "revision": 41},
        "room_bounds": {
            "minimum": {"x_mm": -200, "y_mm": -100, "z_mm": 0},
            "maximum": {"x_mm": 1800, "y_mm": 900, "z_mm": 2400},
        },
        "body": {
            "body_id": "observed-body-19",
            "held_object_id": "held-object-47",
            "pose": {
                "position": {"x_mm": 300, "y_mm": 650, "z_mm": 0},
                "heading_millidegrees": 123456,
            },
            "radius_mm": 125,
            "reach_mm": 700,
        },
        "objects": [
            {
                "object_id": "placed-object-31",
                "position": {"x_mm": 1300, "y_mm": 100, "z_mm": 0},
                "held_by_body_id": None,
                "radius_mm": 80,
                "mass_grams": 430,
            },
            {
                "object_id": "held-object-47",
                "position": None,
                "held_by_body_id": "observed-body-19",
                "radius_mm": 40,
                "mass_grams": 90,
            },
        ],
    }


@pytest.mark.parametrize("page", OBSERVATION_PAGES)
def test_spatial_view_projects_only_live_observation_coordinates(page: Path) -> None:
    value = _spatial_model_from_page(page, _nondefault_observation())

    assert value["available"] is True
    assert value["room_id"] == "observed-room-73"
    assert value["revision"] == 41
    assert value["xSpan"] == 2000
    assert value["ySpan"] == 1000
    assert value["body"] == {
        "body_id": "observed-body-19",
        "radius_mm": 125,
        "heading_millidegrees": 123456,
        "point": {
            "leftPercent": 25,
            "topPercent": 25,
            "x_mm": 300,
            "y_mm": 650,
            "z_mm": 0,
        },
    }
    assert value["objects"][0]["point"] == {
        "leftPercent": 75,
        "topPercent": 80,
        "x_mm": 1300,
        "y_mm": 100,
        "z_mm": 0,
    }
    assert value["objects"][1]["point"] is None
    assert value["objects"][1]["held_by_body_id"] == "observed-body-19"


@pytest.mark.parametrize("page", OBSERVATION_PAGES)
def test_browser_renders_observed_room_body_and_placed_object(page: Path) -> None:
    rendered = _rendered_spatial_view_from_page(
        page, _nondefault_observation()
    )

    assert rendered["hidden"] is False
    assert rendered["aspectRatio"] == "2000 / 1000"
    assert rendered["ariaLabel"] == (
        "observed-room-73 top-down spatial observation at revision 41"
    )
    assert rendered["meta"] == (
        "observed-room-73 · 2000 × 1000 mm · revision 41"
    )
    assert rendered["markers"] == [
        {
            "className": "w1-marker body",
            "left": "25%",
            "top": "25%",
            "width": "12.5%",
            "height": "25%",
            "rotate": "123.456deg",
            "ariaLabel": (
                "observed-body-19 at 300, 650, 0 millimetres"
            ),
            "label": "observed-body-19",
        },
        {
            "className": "w1-marker object",
            "left": "75%",
            "top": "80%",
            "width": "8%",
            "height": "16%",
            "rotate": None,
            "ariaLabel": (
                "placed-object-31 at 1300, 100, 0 millimetres"
            ),
            "label": "placed-object-31",
        },
    ]
    assert "held-object-47: held by observed-body-19" in rendered["inventory"]


@pytest.mark.parametrize("page", OBSERVATION_PAGES)
def test_spatial_view_fails_closed_without_authoritative_geometry(page: Path) -> None:
    observation = _nondefault_observation()
    observation.pop("room_bounds")
    value = _spatial_model_from_page(page, observation)

    assert value == {
        "available": False,
        "reason": "authoritative room bounds unavailable",
    }
    source = page.read_text(encoding="utf-8")
    model_source = source[
        source.index("function buildW1SpatialModel("):
        source.index("\nfunction renderW1SpatialObservation(")
    ]
    assert "Math.random" not in model_source
    assert "W1-object-1" not in model_source
    assert "guala-body-1" not in model_source
