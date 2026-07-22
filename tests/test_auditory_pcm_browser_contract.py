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
    assert "if(!releaseTerminal&&epoch.fetchAbort){epoch.fetchAbort.abort()" in page
    assert "Promise.resolve(settled).catch(()=>{}).then" in page
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
