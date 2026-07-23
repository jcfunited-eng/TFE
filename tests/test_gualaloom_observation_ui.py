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
        assert value["schema"] == "guala.observation_snapshot.v4"
        assert value["embodiment"]["status"] == "observed"
        assert value["embodiment"]["location"] == {
            "region_id": "W1-region-A",
            "revision": 0,
        }
        assert value["embodiment"]["room_bounds"] == {
            "minimum": {"x_mm": 0, "y_mm": 0, "z_mm": 0},
            "maximum": {"x_mm": 5000, "y_mm": 5000, "z_mm": 3000},
        }
        assert value["embodiment"]["self_body_id"] == "guala-body-1"
        assert value["embodiment"]["bodies"][0]["pose"] == {
            "heading_millidegrees": 0,
            "position": {"x_mm": 1000, "y_mm": 1000, "z_mm": 0},
        }
        assert value["embodiment"]["bodies"][1]["body_id"] == "w1-body-2"
        assert value["embodiment"]["bodies"][1]["pose"] == {
            "heading_millidegrees": 180000,
            "position": {"x_mm": 4750, "y_mm": 4750, "z_mm": 0},
        }
        assert [
            item["object_id"]
            for item in value["embodiment"]["objects"]
        ] == [f"W1-object-{number}" for number in range(1, 7)]
        assert all(
            len(item["reflectance_ppm"]) == 6
            for item in value["embodiment"]["objects"]
        )
        assert value["embodiment"]["topology"]["current_region_id"] == (
            "W1-region-A"
        )
        assert len(value["embodiment"]["topology"]["regions"]) == 3
        assert len(value["embodiment"]["topology"]["portals"]) == 2
        assert value["embodiment"]["ownership"] == {
            "status": "unlearned",
            "relations": [],
        }
        assert value["embodied_action"] == {
            "status": "idle",
            "world_revision": 0,
        }
        assert value["conversation"]["status"] == "unavailable"
        assert value["conversation_exchange"]["status"] == "unavailable"
        assert value["full_field_authority"]["status"] == "not_observed"
        assert value["full_field_authority"]["senses"] == []
        assert value["full_field_authority"]["view_contract"] == {
            "decision_authority": False,
            "projection": "latest_exact_tuple_per_substream",
            "projection_loss": (
                "earlier temporal tuples are omitted from this bounded "
                "observation view; prediction evaluates the complete field"
            ),
            "required_fields": [
                "D_k", "M_k", "R_rev_k", "U_star_k",
                "C_k", "P_k", "B_k",
            ],
        }
        assert value["live_anonymous_encounter"]["state"] == "unknown"
        assert value["live_anonymous_encounter"]["acoustic_source"] == (
            "unknown"
        )
        assert set(value["causal_action"]) == {
            "cycle", "dispatcher", "speech_output"
        }
        assert len(value["snapshot_receipt_sha256"]) == 64
        organism._log_substrate_event("same_tick_route_first")
        organism._log_substrate_event("same_tick_route_second")
        emitted = organism.get_recent_events(limit=2)
        route = TestClient(app_module.app).get(
            "/api/v1/gualaloom/events",
            params={
                "after_sequence": emitted[0]["sequence"],
                "n": 10,
            },
        )
        assert route.status_code == 200
        routed = route.json()
        assert [item["kind"] for item in routed["events"]] == [
            "same_tick_route_second"
        ]
        assert routed["event_stream"]["epoch"] == (
            organism.event_stream_status()["epoch"]
        )
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
    assert "guala.observation_snapshot.v4" in page
    assert page.count('id="cam-perm"') == 1
    assert "/v7/quiet" not in page
    assert "triggerSleep" not in page
    assert "openBundleModal" not in page
    assert "pollAutonomousThought" not in page
    assert "command:'/thought'" not in page
    assert "after_sequence=${lastEventSequence}" in page
    assert "lastEventEpoch" in page
    assert "reply to: “" in page


def test_loom_scan_separates_embodied_state_from_lexical_scene_lanes() -> None:
    page = Path(
        "dsf_ai_service/static/loomscan.html"
    ).read_text(encoding="utf-8")

    assert "/api/v1/gualaloom/observation" in page
    assert "embodied location" in page
    assert "body state" in page
    assert "embodied action" in page
    assert "observed conversation" in page
    assert "live audiovisual encounter" in page
    assert "acoustic source" in page
    assert "inactive after restart" in page
    assert "acquisition epochs" in page
    assert "no object-identity authority" in page
    assert "explicit full D/M/R/U/C/P/B retained per receptor" in page
    assert "lexical place lane" in page
    assert "lexical ambient lane" in page
    assert "cdef9bcf" not in page
    assert "||'v7'" not in page
    assert "guala.observation_snapshot.v4" in page
    assert "mulberry32" not in page
    assert "ANCHOR_CHIS" not in page
    assert "setLaneGlow" not in page
    assert "decayLanes" not in page
    assert "curriculum/worldfeed" not in page
    assert "e.sequence>_lastEventSequence" in page
    assert "after_sequence=${_lastEventSequence}" in page
    assert "_lastEventEpoch" in page
    assert "['sight','sound','touch','smell','taste','body']" in page


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
        markers:room.children.filter(marker=>marker.className.startsWith('w1-marker')).map(marker=>({{
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
        "location": {"region_id": "observed-region-73", "revision": 41},
        "room_bounds": {
            "minimum": {"x_mm": -200, "y_mm": -100, "z_mm": 0},
            "maximum": {"x_mm": 500, "y_mm": 900, "z_mm": 2400},
        },
        "topology": {
            "current_region_id": "observed-region-73",
            "regions": [
                {
                    "region_id": "observed-region-73",
                    "bounds": {
                        "minimum": {
                            "x_mm": -200, "y_mm": -100, "z_mm": 0
                        },
                        "maximum": {
                            "x_mm": 500, "y_mm": 900, "z_mm": 2400
                        },
                    },
                    "ceiling_height_mm": 2400,
                },
                {
                    "region_id": "observed-region-81",
                    "bounds": {
                        "minimum": {
                            "x_mm": 500, "y_mm": -100, "z_mm": 0
                        },
                        "maximum": {
                            "x_mm": 1200, "y_mm": 900, "z_mm": 2400
                        },
                    },
                    "ceiling_height_mm": None,
                },
                {
                    "region_id": "observed-region-96",
                    "bounds": {
                        "minimum": {
                            "x_mm": 1200, "y_mm": -100, "z_mm": 0
                        },
                        "maximum": {
                            "x_mm": 1800, "y_mm": 900, "z_mm": 2400
                        },
                    },
                    "ceiling_height_mm": 2400,
                },
            ],
            "portals": [
                {
                    "portal_id": "observed-portal-11",
                    "region_ids": [
                        "observed-region-73", "observed-region-81"
                    ],
                    "axis": "x",
                    "plane_mm": 500,
                    "aperture_min_mm": 200,
                    "aperture_max_mm": 700,
                    "height_mm": 2000,
                },
                {
                    "portal_id": "observed-portal-12",
                    "region_ids": [
                        "observed-region-81", "observed-region-96"
                    ],
                    "axis": "x",
                    "plane_mm": 1200,
                    "aperture_min_mm": 200,
                    "aperture_max_mm": 700,
                    "height_mm": 2000,
                },
            ],
        },
        "ownership": {"status": "unlearned", "relations": []},
        "self_body_id": "observed-body-19",
        "bodies": [
            {
                "body_id": "observed-body-19",
                "held_object_id": "held-object-47",
                "pose": {
                    "position": {"x_mm": 300, "y_mm": 650, "z_mm": 0},
                    "heading_millidegrees": 123456,
                },
                "radius_mm": 125,
                "reach_mm": 700,
            },
            {
                "body_id": "observed-body-27",
                "held_object_id": None,
                "pose": {
                    "position": {"x_mm": 900, "y_mm": 600, "z_mm": 0},
                    "heading_millidegrees": 270000,
                },
                "radius_mm": 100,
                "reach_mm": 600,
            },
        ],
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
    assert value["region_id"] == "observed-region-73"
    assert value["revision"] == 41
    assert value["xSpan"] == 2000
    assert value["ySpan"] == 1000
    assert value["selfBodyId"] == "observed-body-19"
    assert value["bodies"] == [
        {
            "body_id": "observed-body-19",
            "radius_mm": 125,
            "heading_millidegrees": 123456,
            "held_object_id": "held-object-47",
            "is_self": True,
            "point": {
                "leftPercent": 25,
                "topPercent": 25,
                "x_mm": 300,
                "y_mm": 650,
                "z_mm": 0,
            },
        },
        {
            "body_id": "observed-body-27",
            "radius_mm": 100,
            "heading_millidegrees": 270000,
            "held_object_id": None,
            "is_self": False,
            "point": {
                "leftPercent": 55,
                "topPercent": 30,
                "x_mm": 900,
                "y_mm": 600,
                "z_mm": 0,
            },
        },
    ]
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
        "observed-region-73 in the authoritative top-down physical topology "
        "at revision 41"
    )
    assert rendered["meta"] == (
        "observed-region-73 · 3 regions · 2 portals · ownership unlearned "
        "(0 relations) · revision 41"
    )
    assert rendered["markers"] == [
        {
            "className": "w1-marker body self",
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
            "className": "w1-marker body other",
            "left": "55%",
            "top": "30%",
            "width": "10%",
            "height": "20%",
            "rotate": "270deg",
            "ariaLabel": (
                "observed-body-27 at 900, 600, 0 millimetres"
            ),
            "label": "observed-body-27",
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
def test_spatial_view_accepts_any_authority_valid_world_shape(page: Path) -> None:
    observation = _nondefault_observation()
    observation["topology"]["regions"] = [
        {
            "region_id": "observed-region-73",
            "bounds": {
                "minimum": {"x_mm": -200, "y_mm": -100, "z_mm": 0},
                "maximum": {"x_mm": 500, "y_mm": 900, "z_mm": 2400},
            },
            "ceiling_height_mm": 2400,
        }
    ]
    observation["topology"]["portals"] = []
    observation["bodies"] = observation["bodies"][:1]
    observation["objects"] = observation["objects"][1:]
    observation["ownership"] = {
        "status": "observed",
        "relations": [
            {"body_id": "observed-body-19", "object_id": "held-object-47"}
        ],
    }

    model = _spatial_model_from_page(page, observation)
    rendered = _rendered_spatial_view_from_page(page, observation)

    assert model["available"] is True
    assert len(model["regions"]) == 1
    assert model["portals"] == []
    assert len(model["bodies"]) == 1
    assert model["ownership"]["status"] == "observed"
    assert "ownership observed (1 relations)" in rendered["meta"]


def test_observation_exchange_and_event_cursor_are_immutable_and_ordered(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "observation-contract-key")

    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    organism = Guala()
    try:
        with organism.lock:
            organism._record_conversation_observation(
                text="hello guala",
                source="joe_voice",
                source_turn_index=7,
                causal_experience_id="terminal-event-7",
                causal_intake_receipt_sha256="a" * 64,
                response="hello daddy",
                response_source="causal_action_cycle_commit",
                emission_id="emission-7",
                commit_provenance=(),
            )
        first = organism.observation_snapshot()
        assert first["event_stream"]["schema"] == (
            "guala.substrate_event_stream.v1"
        )
        assert len(first["event_stream"]["epoch"]) == 64
        assert first["conversation_exchange"]["input"] == {
            "causal_experience_id": "terminal-event-7",
            "causal_intake_receipt_sha256": "a" * 64,
            "source": "joe_voice",
            "source_turn_index": 7,
            "terminal_event_id": "terminal-event-7",
            "text": "hello guala",
        }
        assert first["conversation_exchange"]["response"]["text"] == (
            "hello daddy"
        )
        assert len(first["conversation_exchange"]["exchange_id"]) == 64

        with organism.lock:
            organism._record_conversation_observation(
                text="typed second turn",
                source="joe",
                source_turn_index=8,
                causal_experience_id=None,
                causal_intake_receipt_sha256=None,
                response="second response",
                response_source="mathloom",
                emission_id=None,
                commit_provenance=(),
            )
        second = organism.observation_snapshot()
        assert first["conversation_exchange"]["input"]["text"] == (
            "hello guala"
        )
        assert (
            second["conversation_exchange"]["input"]["terminal_event_id"]
            is None
        )

        organism._log_substrate_event("same_tick_first")
        organism._log_substrate_event("same_tick_second")
        events = organism.get_recent_events(limit=2)
        assert [event["kind"] for event in events] == [
            "same_tick_first", "same_tick_second"
        ]
        assert events[0]["tick"] == events[1]["tick"]
        assert events[1]["sequence"] == events[0]["sequence"] + 1
        assert organism.get_recent_events(
            limit=2,
            since_sequence=events[0]["sequence"],
        ) == [events[1]]
    finally:
        organism.shutdown()


@pytest.mark.parametrize("page", OBSERVATION_PAGES)
def test_spatial_view_fails_closed_without_authoritative_geometry(page: Path) -> None:
    observation = _nondefault_observation()
    observation.pop("topology")
    value = _spatial_model_from_page(page, observation)

    assert value == {
        "available": False,
        "reason": "authoritative physical topology unavailable",
    }
    source = page.read_text(encoding="utf-8")
    model_source = source[
        source.index("function buildW1SpatialModel("):
        source.index("\nfunction renderW1SpatialObservation(")
    ]
    assert "Math.random" not in model_source
    assert "W1-object-1" not in model_source
    assert "guala-body-1" not in model_source
