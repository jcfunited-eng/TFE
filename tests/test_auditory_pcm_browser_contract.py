from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_external_epoch_abort_reaches_the_exact_fetch_request() -> None:
    page = _page()
    start = page.index("function fetchT(")
    end = page.index("\nlet _inflight=", start)
    function_source = page[start:end]
    program = f"""
      let receivedSignal=null;
      globalThis.fetch=(_url,options)=>{{receivedSignal=options.signal;return Promise.resolve({{ok:true}})}};
      {function_source}
      (async()=>{{
        const external=new AbortController();
        const pending=fetchT('/sound_frame',{{signal:external.signal}},60000);
        external.abort(new Error('epoch closed'));
        await pending;
        if(!receivedSignal||!receivedSignal.aborted)throw new Error('fetch did not receive epoch abort');
        process.stdout.write(JSON.stringify({{aborted:receivedSignal.aborted}}));
      }})().catch(error=>{{console.error(error);process.exit(1)}});
    """
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == {"aborted": True}


def test_browser_epoch_is_fail_closed_and_locally_owned() -> None:
    page = _page()
    assert "if(micTransitionActive)return" in page
    assert "epoch.sendChain=epoch.sendChain" in page
    assert "audio_stream_id:epoch.streamId" in page
    assert "audio_source_epoch_ms:epoch.sourceEpochMs" in page
    assert "if(!epoch.active)return" in page
    assert "micSightHandoff=Promise.resolve(settled).catch(()=>{}).then" in page
    assert "await micSightHandoff;" in page
    assert (
        "if(standaloneSightRequest)"
        "await standaloneSightRequest.catch(()=>{});" in page
    )
    assert "standaloneSightRequest=request;" in page
    assert "release_terminal:releaseTerminal" in page
    assert "type:'discontinuity'" in page
    assert "currentFrame!==this.expectedFrame" in page
    assert "worklet.onprocessorerror" in page
    assert "addEventListener('ended'" in page
    assert "browser audio sample clock is unavailable" in page


def test_post_open_contract_failure_closes_the_known_server_epoch() -> None:
    page = _page()
    contract = page.index("opened.sample_rate_hz!==PCM_SAMPLE_RATE")
    cleanup = page.index(
        "_notifyPCMEpochClose(opened.stream_id,false)", contract
    )
    construction = page.index("const epoch={generation", contract)
    assert contract < cleanup < construction


def test_camera_handoff_waits_for_pcm_settlement_and_close_ack() -> None:
    page = _page()
    start = page.index("function _closePCMEpoch(")
    end = page.index("\nfunction _failPCMStream", start)
    function_source = page[start:end]
    program = f"""
      let micSightHandoff=Promise.resolve(),micEpoch=null,micStream=null;
      let micPCMActive=true,closeCalls=0,resolveSend;
      function _notifyPCMEpochClose(){{
        closeCalls+=1;
        return Promise.resolve();
      }}
      {function_source}
      const sendChain=new Promise(resolve=>{{resolveSend=resolve}});
      const epoch={{
        active:true,streamId:'stream-1',sendChain,
        sightTimers:new Map(),sightBySequence:new Map(),
        worklet:null,source:null,gain:null,context:null,stream:null
      }};
      micEpoch=epoch;
      _closePCMEpoch(epoch,true,false);
      if(closeCalls!==0)throw new Error('close raced the in-flight PCM request');
      resolveSend();
      micSightHandoff.then(()=>{{
        if(closeCalls!==1)throw new Error('server close was not acknowledged');
        process.stdout.write(JSON.stringify({{closeCalls,micPCMActive}}));
      }}).catch(error=>{{console.error(error);process.exit(1)}});
    """
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == {
        "closeCalls": 1,
        "micPCMActive": False,
    }


def test_camera_to_pcm_handoff_awaits_standalone_server_result() -> None:
    page = _page()
    start = page.index("async function startMicSoundStream(")
    end = page.index("\nfunction stopMicSoundStream", start)
    function_source = page[start:end]
    handoff = function_source.index("await micSightHandoff;")
    standalone = function_source.index(
        "if(standaloneSightRequest)"
        "await standaloneSightRequest.catch(()=>{});"
    )
    open_epoch = function_source.index(
        "fetchT(`${API}/api/v1/auditory/pcm/open`"
    )
    assert handoff < standalone < open_epoch
    assert "standaloneSightAbort.abort()" not in function_source


def test_voice_transcript_pairs_each_reply_with_its_heard_experience() -> None:
    page = _page()
    assert "const auditoryHeardByTerminal=new Map()" in page
    assert "replying to: \"'+heard+'\"" in page
    assert "no learned causal action for: \"'+heard+'\"" in page
    assert "_rememberBoundedMap(auditoryHeardByTerminal" in page


def test_authenticated_multi_token_sequence_is_visible_once_without_stt() -> None:
    page = _page()
    start = page.index("function _handleAuditoryTerminal(")
    end = page.index("\nfunction _pcmBase64", start)
    function_source = page[start:end]
    program = f"""
      const auditoryTerminalSeen=new Set(),auditorySequenceSeen=new Set();
      const auditoryHeardByTerminal=new Map();
      const rendered=[];
      function _rememberBounded(set,value){{set.add(value)}}
      function _rememberBoundedMap(map,key,value){{map.set(key,value)}}
      function addMsg(text,kind){{rendered.push({{text,kind}})}}
      function _pollAuditoryReply(){{throw new Error('no reply was admitted')}}
      {function_source}
      const result={{
        pcm_continuity:{{
          auditory_token_sequence:{{
            sequence_id:'sequence-1',
            occurrences:[
              {{classification_state:'unique',token_candidates:[{{token_form:'hello'}}]}},
              {{classification_state:'unique',token_candidates:[{{token_form:'guala'}}]}}
            ]
          }}
        }},
        spoken_word_recognition:{{recognized_form:null}},
        terminal_event_id:null
      }};
      _handleAuditoryTerminal(result);
      _handleAuditoryTerminal(result);
      process.stdout.write(JSON.stringify(rendered));
    """
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == [
        {"text": 'heard: "hello guala"', "kind": "user"}
    ]


def test_paired_sight_temporally_samples_the_physical_pcm_interval() -> None:
    page = _page()
    start = page.index("function _schedulePCMSight(")
    end = page.index("\nfunction _notifyPCMEpochClose", start)
    function_source = page[start:end]

    assert (
        "const chunkDurationMs=PCM_CHUNK_SAMPLES*1000/PCM_SAMPLE_RATE;"
        in function_source
    )
    assert "const frameCount=epoch.visualFrameCount;" in function_source
    assert "(index+1)*chunkDurationMs/(frameCount+1)" in function_source
    assert "Promise.all(captures)" in function_source
    assert "sequence*5000" not in function_source
