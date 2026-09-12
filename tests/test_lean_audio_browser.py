"""Real Chromium/WebAudio transport checks; fixtures are NOT speech evidence."""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright


PAGE = Path(__file__).resolve().parents[1] / "dsf_ai_service/static/gualaloom.html"
STREAM = "a" * 32
PCM = b"\x00\x01" * 4000


def test_real_browser_order_duplicates_gap_and_stop() -> None:
    # Explicit installed executable, never an implicit browser download.
    executable = os.environ["GUALA_TEST_CHROMIUM"]
    assert Path(executable).is_file()
    state = {"hold": False, "gap": False, "requests": 0, "mode": "normal"}
    pending = []

    def feed(cursor, events=(), gap=None):
        return {
            "schema": "guala.pressure_feed.v1", "stream": STREAM,
            "cursor": cursor, "latest": cursor, "gap": gap,
            "sample_rate_hz": 16000, "events": list(events),
        }

    def event(tick, pcm=PCM):
        return {
            "tick": tick, "sha256": hashlib.sha256(pcm).hexdigest(),
            "pcm_s16le_base64": base64.b64encode(pcm).decode(),
        }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("""
            window.audioStarts=[];window.audioStops=0;
            const start=AudioBufferSourceNode.prototype.start;
            AudioBufferSourceNode.prototype.start=function(when){
              audioStarts.push({when,duration:this.buffer.duration,
                rate:this.buffer.sampleRate,sample:this.buffer.getChannelData(0)[0]});
              return start.call(this,when);
            };
            const stop=AudioBufferSourceNode.prototype.stop;
            AudioBufferSourceNode.prototype.stop=function(){audioStops++;return stop.call(this)};
        """)

        def route(request):
            url = urlparse(request.request.url)
            if url.path == "/gualaloom.html":
                request.fulfill(status=200, content_type="text/html", body=PAGE.read_text())
            elif url.path == "/api/v1/guala/pressure":
                state["requests"] += 1
                if state["mode"] == "bytes":
                    request.fulfill(status=200, body="x" * 90001)
                    return
                if state["hold"]:
                    pending.append(request)
                    return
                query = parse_qs(url.query)
                if "after" not in query:
                    request.fulfill(json=feed(12 if state["gap"] else 10))
                elif state["mode"] in ("batch", "queue"):
                    after = int(query["after"][0])
                    count = 9 if state["mode"] == "batch" else 8
                    request.fulfill(json=feed(after + count, (
                        event(tick, PCM[:2] if state["mode"] == "batch" else PCM)
                        for tick in range(after + 1, after + count + 1)
                    )))
                elif state["gap"]:
                    request.fulfill(json=feed(20, gap="audio-evicted"))
                elif int(query["after"][0]) == 10:
                    request.fulfill(json=feed(12, (event(11), event(12))))
                else:
                    request.fulfill(json=feed(12))
            elif url.path == "/api/v1/guala/observation":
                request.fulfill(json={"schema": "guala.lean_actor_observation.v1",
                                      "identity": "fixture-not-Guala", "live_tick": 12,
                                      "available": True})
            else:
                request.fulfill(status=404, body="fixture asset unavailable")

        page.route("**/*", route)
        page.goto("http://localhost/gualaloom.html")
        page.locator("#hear").click()
        page.wait_for_function("audioStarts.length === 2")
        starts = page.evaluate("audioStarts")
        assert starts[0]["rate"] == starts[1]["rate"] == 16000
        assert starts[0]["sample"] == starts[1]["sample"] == 256 / 32768
        assert abs(starts[1]["when"] - starts[0]["when"] - .25) < 1e-9
        assert page.evaluate("listenSession.gain.gain.value") == 64
        page.wait_for_timeout(750)  # Three declared transport polls, not organism clocks.
        assert state["requests"] >= 3
        assert page.evaluate("audioStarts.length") == 2
        page.locator("#hear").click()
        assert page.evaluate("listenSession === null && !listening")

        state["mode"] = "queue"
        page.locator("#hear").click()
        page.evaluate("listenSession.context.suspend()")
        page.wait_for_function("listenSession.sources.size === 16")
        queued_requests = state["requests"]
        page.wait_for_timeout(750)
        assert state["requests"] == queued_requests
        assert page.evaluate("listenSession.sources.size") == 16
        page.evaluate("window.stoppingContext=listenSession.context")
        stops = page.evaluate("audioStops")
        page.locator("#hear").click()
        page.wait_for_function("stoppingContext.state === 'closed'")
        assert page.evaluate("audioStops") - stops == 16
        assert page.evaluate("listenSession === null && !listening")
        played = page.evaluate("audioStarts.length")
        assert played == 18

        for mode, message in (("bytes", "byte bound"), ("batch", "feed contract")):
            state["mode"] = mode
            page.locator("#hear").click()
            page.wait_for_function(
                "(message) => document.getElementById('listen-status').textContent.includes(message)",
                arg=message,
            )
            assert page.evaluate("listenSession === null && !listening")
            assert page.evaluate("audioStarts.length") == played

        state["mode"] = "normal"
        state["hold"] = True
        page.locator("#hear").click()
        page.wait_for_timeout(300)
        assert len(pending) == 1
        page.locator("#hear").click()
        # Fulfilment races a cancelled fetch; either outcome must stay stopped.
        pending.pop().fulfill(json=feed(12, (event(11), event(12))))
        page.wait_for_timeout(300)
        assert page.evaluate("audioStarts.length") == played
        assert page.evaluate("listenSession === null && !listening")

        state.update(hold=False, gap=True)
        page.locator("#hear").click()
        page.wait_for_function("document.getElementById('listen-status').textContent.includes('audio-evicted')")
        assert page.evaluate("audioStarts.length") == played
        page.locator("#hear").click()
        assert not errors
        browser.close()
