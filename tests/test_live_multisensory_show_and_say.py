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


def test_live_surface_exposes_truthful_camera_and_human_show_and_say() -> None:
    source = _page()

    assert '<button id="camera-perm"' in source
    assert '<button id="camera-stop"' in source
    assert '<video id="camera-preview"' in source
    assert '<canvas id="lesson-card"' in source
    assert "A human tutor must say the displayed symbol aloud" in source
    assert "it generates no speech" in source
    assert "speechSynthesis" not in source
    assert "SpeechSynthesisUtterance" not in source
    assert "/sight_frame" in source
    assert "/sound_frame" in source


def test_show_and_say_card_extent_is_exactly_a_to_z_then_one_to_ten() -> None:
    source = _script()
    start = source.index("const SHOW_AND_SAY_CARDS=")
    end = source.index("\nlet visualCaptureContract", start)
    program = (
        source[start:end]
        + "\nprocess.stdout.write(JSON.stringify(SHOW_AND_SAY_CARDS));"
    )
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == [
        "/cards/alphabet-a-apple-v1.png",
        "/cards/alphabet-b-bee-v1.png",
        *[
            f"/cards/{letter}-is-for-{name}.png"
            for letter, name in zip(
                "CDEFGHIJKLMNOPQRSTUVWXYZ",
                (
                    "Cat", "Dolphin", "Elephant", "Fox", "Giraffe", "House",
                    "Ice-Cream", "Jellyfish", "Kite", "Lion", "Mushroom",
                    "Nest", "Owl", "Penguin", "Queen", "Rabbit", "Snail",
                    "Turtle", "Umbrella", "Violin", "Whale", "Xylophone",
                    "Yak", "Zebra",
                ),
                strict=True,
            )
        ],
        *[
            f"/cards/number-{number:02d}-{name}-v1.png"
            for number, name in enumerate(
                (
                    "one", "two", "three", "four", "five", "six", "seven",
                    "eight", "nine", "ten",
                ),
                start=1,
            )
        ],
    ]


def test_pcm_chunk_carries_bounded_sight_in_the_same_request() -> None:
    source = _script()
    pcm_start = source.index("function _pcmBase64(")
    pcm_end = source.index("\nasync function _sha256", pcm_start)
    send_start = source.index("async function _sendPCMChunk(")
    send_end = source.index("\nfunction _admitPCMChunk", send_start)
    program = f"""
      const API='https://example.invalid',PCM_SAMPLE_RATE=16000;
      {source[pcm_start:pcm_end]}
      let admitted=null,terminalHandled=false,statusText=null;
      function _selectVisualFrames(startMs,endMs){{
        if(startMs!==1000||endMs!==3000)throw new Error('visual interval left PCM');
        return {{
          provenance:'simulated_material_display',
          frames:[1,2,3,4].map(offset=>({{
            captured_ms:1000+offset*300,
            frame_b64:'frame-'+offset
          }}))
        }};
      }}
      function fetchT(_url,options){{
        admitted=JSON.parse(options.body);
        return Promise.resolve({{
          ok:true,
          json:()=>Promise.resolve({{
            ok:true,
            pcm_continuity:{{status:'contiguous'}},
            sensory_boundary:{{
              sight:'observed',sound:'observed',
              touch:'sensor_unavailable',smell:'sensor_unavailable',
              taste:'sensor_unavailable',body:'sensor_unavailable'
            }}
          }})
        }});
      }}
      function _handleAuditoryTerminal(){{terminalHandled=true}}
      function _setHearingStatus(value){{statusText=value}}
      {source[send_start:send_end]}
      const epoch={{
        active:true,binauralActive:false,sourceEpochMs:1000,
        monoStreamId:'mono',lineageReceipt:null
      }};
      const leftBuffer=new ArrayBuffer(32000*2);
      _sendPCMChunk(epoch,{{
        leftBuffer,rightBuffer:null,sequence:0,
        firstSampleIndex:0,renderFrameStart:0
      }}).then(()=>{{
        process.stdout.write(JSON.stringify({{
          admitted,terminalHandled,statusText
        }}));
      }}).catch(error=>{{console.error(error);process.exit(1)}});
    """
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    admitted = result["admitted"]

    assert admitted["visual_source"] == "simulated_material_display"
    assert [item["captured_ms"] for item in admitted["sight_frames"]] == [
        1300,
        1600,
        1900,
        2200,
    ]
    assert admitted["audio_first_sample_index"] == 0
    assert admitted["audio_sample_count"] == 32_000
    assert result["terminalHandled"] is True
    assert "one sight-and-sound experience settled" in result["statusText"]


def test_visual_selection_is_bounded_ordered_and_single_source() -> None:
    source = _script()
    start = source.index("function _selectVisualFrames(")
    end = source.index("\nasync function _sendStandaloneSightWindow", start)
    program = f"""
      const visualCaptureContract={{
        minimum_frames:4,maximum_frames:8
      }};
      let visualFrameRing=[
        ...Array.from({{length:4}},(_,index)=>({{
          captured_ms:1000+index*100,
          frame_b64:'camera-'+index,
          visual_source:'camera_stream'
        }})),
        ...Array.from({{length:10}},(_,index)=>({{
          captured_ms:1500+index*100,
          frame_b64:'card-'+index,
          visual_source:'simulated_material_display'
        }}))
      ];
      {source[start:end]}
      process.stdout.write(JSON.stringify(
        _selectVisualFrames(1000,2600)
      ));
    """
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    selected = json.loads(completed.stdout)

    assert selected["provenance"] == "simulated_material_display"
    assert len(selected["frames"]) == 8
    assert [frame["frame_b64"] for frame in selected["frames"]] == [
        f"card-{index}" for index in range(2, 10)
    ]
    assert [frame["captured_ms"] for frame in selected["frames"]] == sorted(
        frame["captured_ms"] for frame in selected["frames"]
    )


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
