from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUALA = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
LOOM = ROOT / "dsf_ai_service" / "static" / "loomscan.html"
SCHEMA = "guala.native.public_observation.v1"
ROUTE = "/api/v1/guala/native-observation"


def _script(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    start = source.index("<script>") + len("<script>")
    end = source.index("</script>", start)
    return source[start:end]


def test_both_complete_scripts_compile() -> None:
    for path in (GUALA, LOOM):
        program = "new Function(" + json.dumps(_script(path)) + ");"
        completed = subprocess.run(
            ["node", "-e", program],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr


def test_pages_use_only_the_native_public_observation_contract() -> None:
    combined = GUALA.read_text(encoding="utf-8") + LOOM.read_text(
        encoding="utf-8"
    )
    assert combined.count(f'const OBSERVATION_ROUTE="{ROUTE}"') == 2
    assert combined.count(f'const OBSERVATION_SCHEMA="{SCHEMA}"') == 2
    for forbidden in (
        "3d6toi0gw0.execute-api",
        "guala.observation_snapshot.v5",
        "/sight_frame",
        "/sound_frame",
        "/api/v1/auditory/",
        "current_owner_state",
        "owner_state",
        "passive_whole_organism_thing_learning",
        "auditory_recurrent_motif",
    ):
        assert forbidden not in combined


def test_observation_is_conditional_bounded_and_suspended_when_hidden() -> None:
    for path in (GUALA, LOOM):
        source = path.read_text(encoding="utf-8")
        assert "const POLL_INTERVAL_MS=15000" in source
        assert 'headers["If-None-Match"]=etag' in source
        assert "response.status===304" in source
        assert "pollRefreshQueued=true;pollAbort.abort()" in source
        assert "if(pollAbort===controller)" in source
        assert 'response.headers.get("ETag")' in source
        assert "visibilitychange" in source
        assert "if(document.hidden)" in source
        assert "if(!document.hidden)refreshObservation(true)" in source
        assert 'id="manual-refresh"' in source
        assert "setTimeout(()=>refreshObservation(false),POLL_INTERVAL_MS)" in source
        assert "setInterval(poll" not in source
        assert "2000)}" not in source


def test_controls_fail_closed_and_distinguish_local_from_accepted() -> None:
    source = GUALA.read_text(encoding="utf-8")
    for control in ("camera-toggle", "microphone-toggle", "curriculum-toggle"):
        assert f'id="{control}"' in source
        assert f'id="{control}" class="toggle"' in source
        assert 'aria-pressed="false" disabled' in source
    assert "A local device and an organism-accepted sensory transition are different states" in source
    assert "Local active · awaiting acceptance" in source
    assert "Local active · organism accepted" in source
    assert "result.accepted!==true" in source
    assert "value?.available===true&&endpoint!==null" in source
    assert "safeEndpoint(value)" in source
    assert 'value.startsWith("//")' in source


def test_controls_have_monotonic_epoch_and_abort_boundaries() -> None:
    source = GUALA.read_text(encoding="utf-8")
    assert "function cameraOwns(epoch,stream)" in source
    assert "epoch===cameraEpoch&&cameraStream===stream" in source
    assert "cameraInFlightEpoch===epoch" in source
    assert "if(cameraAbort)cameraAbort.abort()" in source
    assert "cameraEpoch+=1" in source
    assert "function microphoneOwns(epoch,stream)" in source
    assert "epoch===microphoneEpoch&&microphoneStream===stream" in source
    assert "microphoneInFlightEpoch===epoch" in source
    assert "if(microphoneAbort)microphoneAbort.abort()" in source
    assert "microphoneEpoch+=1" in source
    assert "function surfaceOwns(epoch,kind=surfaceKind)" in source
    assert "surfaceEpoch+=1" in source
    assert "if(surfaceAbort)surfaceAbort.abort()" in source
    assert 'if(!camera.available&&(cameraStream!==null||cameraStarting)){stopCamera("Camera stopped · native capability withdrawn");return}' in source
    assert "if(epoch!==cameraEpoch){acquired.getTracks().forEach(track=>track.stop());return}" in source
    assert 'if(!capability("camera").available){acquired.getTracks().forEach(track=>track.stop());stopCamera("Camera stopped · native capability withdrawn");return}' in source
    assert 'stopCamera("Camera stopped · native acceptance failed:' in source
    assert "if(acquired)acquired.getTracks().forEach(track=>track.stop())" in source
    assert "if(stream)stream.getTracks().forEach(track=>track.stop())" in source
    assert 'stopMicrophone("Microphone stopped · native acceptance failed:' in source
    assert "stopCamera(\"Camera stopped while page is hidden\")" in source
    assert "stopMicrophone(\"Microphone stopped while page is hidden\")" in source


def test_typed_text_is_rendered_as_pixels_not_submitted_as_semantics() -> None:
    source = GUALA.read_text(encoding="utf-8")
    assert "The browser renders glyph pixels" in source
    assert "never submitted as meaning" in source
    assert 'schema:"guala.native.browser_visual_material.v1"' in source
    assert "frame_b64:pixels" in source
    call = source[source.index("async function renderGlyphs()") :]
    call = call[: call.index("async function offerFile")]
    assert "text," not in call
    assert "body:JSON.stringify" not in call
    assert "setText(\"human-transcript\",text)" in call
    assert 'document.getElementById("glyph-text").addEventListener("input"' in source


def test_material_and_curriculum_controls_are_capability_gated() -> None:
    source = GUALA.read_text(encoding="utf-8")
    for kind in ("picture", "pdf", "book", "audio", "song"):
        assert f'id="{kind}-file"' in source
        assert f'capability("{kind}")' in source or f'["{kind}","{kind}"]' in source
    for shelf in (
        "Project Gutenberg",
        "YouTube",
        "Khan Academy",
        "PBS Kids",
        "Spotify",
    ):
        assert shelf in source
    assert 'capability("curriculum")' in source
    assert "Invite her to look" in source
    assert "presentation_endpoint" in source
    assert "invitation_receipt_sha256" in source
    assert "no word understanding is inferred" in source
    assert "she recognised" not in source
    assert source.count("async function requestShelf(id,mode)") == 1
    assert "input.disabled=!cap.available" in source


def test_approved_art_is_preserved_and_explicitly_non_authoritative() -> None:
    source = GUALA.read_text(encoding="utf-8")
    for name in (
        "gualaloom-rich-room-v3.png",
        "Guala_Talking_Bust_No_Bow_Transparent.png",
    ):
        asset = ROOT / "dsf_ai_service" / "static" / name
        assert asset.is_file()
        assert name in source
    assert "Approved room artwork · illustrative only" in source
    assert "illustration, not actuator evidence" in source
    assert "Static artwork does not move in place of body evidence" in source


def test_gualaloom_exposes_every_required_truthful_observation() -> None:
    source = GUALA.read_text(encoding="utf-8")
    for phrase in (
        "What reached visual receptors",
        "What Guala sees",
        "What Guala hears",
        "Attention",
        "Formations and recall",
        "Action and autonomy",
        "Body and world",
        "Reached auditory structure",
        "cognitive_capital",
        "full_dsf",
        "persistence",
        "resources",
    ):
        assert phrase in source
    assert "external_sensor_transcript" in source
    assert "transcript_is_cognition:false" in source
    assert "meaning_authority:false" in source


def test_loomscan_exposes_the_reached_frontier_without_flattening() -> None:
    source = LOOM.read_text(encoding="utf-8")
    for record in (
        "Sensory delivery",
        "Neuron activity",
        "Retained fractals",
        "Formations",
        "Recall / reassembly",
        "Autonomous action",
        "Sensed consequence",
        "Hippocampal / distributed recall",
        "Cognitive capital",
        "Complete DSF reference",
    ):
        assert record in source
    for field in ("D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"):
        assert field in source
    assert "never averages or flattens" in source
    assert "observation loss" in source


def test_loomscan_cognitive_capital_is_39_by_10_and_never_a_score() -> None:
    source = LOOM.read_text(encoding="utf-8")
    assert "There is no aggregate score" in source
    assert source.count('"Vision"') == 1
    assert '"Integrated practiced capability"' in source
    dimensions = (
        "availability",
        "participation",
        "retention",
        "recognition",
        "recall",
        "causal_use",
        "transfer",
        "autonomous_use",
        "durability",
        "integration_depth",
    )
    for dimension in dimensions:
        assert f'"{dimension}"' in source
    catalog = source[source.index("const CAPITAL_CAPABILITIES=") :]
    catalog = catalog[: catalog.index("];", catalog.index("=")) + 2]
    assert catalog.count('","') + 1 == 39
