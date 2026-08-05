#!/usr/bin/env python3
"""Fresh-Chromium proof of live continuous hearing and camera articulation.

The proof accepts no typed input and installs no candidate engine. Chromium
loads the exact reviewed public Guala page, receives an authenticated physical
WAV through its fake microphone, and receives Chromium's native fake camera.
The public page must continuously settle microphone intervals while separately
settling camera intervals. At least one camera request must return, play, and
release a digest-verified physical articulation in that same request.

This verifier does not create a learned THING or a vocal binding. A non-null
articulation therefore requires the cold-restored production organism to
already hold the corresponding lived sight-to-THING-to-vocal relation.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.probe_guala_candidate_browser import (
    PRODUCTION_API_ORIGIN,
    PROOF_SECONDS,
    _browser_instrumentation,
    _status_snapshot,
    _stop_admission_and_drain,
    _validate_records,
    _validate_visual_intervals,
    build_cognitive_proof_wav,
)
from tools.verify_guala_loom_live_cutover import (
    VerificationConfig,
    verify_live_cutover,
)


LIVE_ORIGIN = "https://dsf-ai.com"
LIVE_PAGE_URL = f"{LIVE_ORIGIN}/gualaloom.html"
PLAYBACK_SCHEMA = (
    "guala.loom.same_request_sight_articulatory_playback.v1"
)
PLAYBACK_KEYS = frozenset({
    "channel_count",
    "encoding",
    "pcm_s16le_b64",
    "pcm_sha256",
    "sample_count",
    "sample_rate_hz",
    "schema",
    "source_response_authority_receipt_sha256",
})
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_PCM_BYTES = 160_000
MINIMUM_SETTLED_SIGHT_FIELDS = 2


def _playback_instrumentation() -> str:
    """Observe only browser media custody; never alter page decisions."""

    return r"""
      (() => {
        const state={
          activeUrls:new Set(),
          created:[],
          maximumActiveUrls:0,
          plays:[],
          revoked:[]
        };
        window.__liveArticulationMedia=state;
        const nativeCreate=URL.createObjectURL.bind(URL);
        const nativeRevoke=URL.revokeObjectURL.bind(URL);
        URL.createObjectURL=blob=>{
          const url=nativeCreate(blob);
          if(blob instanceof Blob&&blob.type==='audio/wav'){
            const record={
              byteCount:blob.size,
              error:null,
              pcmSha256:null,
              url,
              wavHeaderValid:null
            };
            state.created.push(record);
            state.activeUrls.add(url);
            state.maximumActiveUrls=Math.max(
              state.maximumActiveUrls,state.activeUrls.size
            );
            blob.arrayBuffer().then(async buffer=>{
              const bytes=new Uint8Array(buffer);
              const text=(offset,count)=>String.fromCharCode(
                ...bytes.slice(offset,offset+count)
              );
              const view=new DataView(buffer);
              const headerValid=
                bytes.length>=44&&text(0,4)==='RIFF'&&
                text(8,4)==='WAVE'&&text(36,4)==='data'&&
                view.getUint32(40,true)===bytes.length-44;
              record.wavHeaderValid=headerValid;
              if(!headerValid)throw new Error('created WAV header changed');
              const digest=await crypto.subtle.digest(
                'SHA-256',bytes.slice(44)
              );
              record.pcmSha256=Array.from(
                new Uint8Array(digest),
                value=>value.toString(16).padStart(2,'0')
              ).join('');
            }).catch(error=>{record.error=error.message});
          }
          return url;
        };
        URL.revokeObjectURL=url=>{
          if(state.activeUrls.has(url)){
            state.activeUrls.delete(url);
            state.revoked.push(url);
          }
          return nativeRevoke(url);
        };
        const nativePlay=HTMLMediaElement.prototype.play;
        HTMLMediaElement.prototype.play=function(...args){
          const src=String(this.currentSrc||this.src||'');
          let record=null;
          if(src.startsWith('blob:')){
            record={
              ended:false,
              error:null,
              resolved:false,
              src
            };
            state.plays.push(record);
            this.addEventListener(
              'ended',()=>{record.ended=true},{once:true}
            );
          }
          const result=nativePlay.apply(this,args);
          if(record&&result&&typeof result.then==='function'){
            result.then(
              ()=>{record.resolved=true},
              error=>{record.error=error.message}
            );
          }
          return result;
        };
      })();
    """


def _decode_playback(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError("camera articulation is not an object")
    if frozenset(value) != PLAYBACK_KEYS:
        raise RuntimeError("camera articulation fields changed")
    if (
        value.get("schema") != PLAYBACK_SCHEMA
        or value.get("encoding") != "pcm_s16le"
        or value.get("channel_count") != 1
        or value.get("sample_rate_hz") != 16_000
    ):
        raise RuntimeError("camera articulation physical format changed")
    sample_count = value.get("sample_count")
    pcm_sha256 = value.get("pcm_sha256")
    response_receipt = value.get(
        "source_response_authority_receipt_sha256"
    )
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count <= 0
        or sample_count * 2 > MAX_PCM_BYTES
        or not isinstance(pcm_sha256, str)
        or SHA256_PATTERN.fullmatch(pcm_sha256) is None
        or not isinstance(response_receipt, str)
        or SHA256_PATTERN.fullmatch(response_receipt) is None
    ):
        raise RuntimeError("camera articulation bounds or receipt changed")
    encoded = value.get("pcm_s16le_b64")
    if not isinstance(encoded, str):
        raise RuntimeError("camera articulation PCM is not base64 text")
    try:
        pcm = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise RuntimeError(
            "camera articulation PCM is not canonical base64"
        ) from error
    if (
        len(pcm) != sample_count * 2
        or hashlib.sha256(pcm).hexdigest() != pcm_sha256
    ):
        raise RuntimeError("camera articulation PCM digest changed")
    return {
        "pcm_byte_count": len(pcm),
        "pcm_sha256": pcm_sha256,
        "sample_count": sample_count,
        "source_response_authority_receipt_sha256": response_receipt,
    }


def validate_same_request_articulation(
    sight_records: list[dict[str, object]],
    media: dict[str, object],
) -> dict[str, object]:
    """Prove server custody, browser playback, capacity one, and release."""

    settled = _validate_visual_intervals(sight_records)
    if len(settled) < MINIMUM_SETTLED_SIGHT_FIELDS:
        raise RuntimeError("too few independent live sight settlements")
    deliveries: list[dict[str, object]] = []
    silent_responses = 0
    for record in settled:
        response = record["response"]
        observation = response.get("articulatory_response")
        playback = response.get("articulatory_playback")
        if playback is None:
            silent_responses += 1
            continue
        if (
            not isinstance(observation, dict)
            or observation.get("state") != "executed"
            or not isinstance(observation.get("thing_ids"), list)
            or not observation["thing_ids"]
        ):
            raise RuntimeError(
                "non-null camera playback lacks an executed THING response"
            )
        delivery = _decode_playback(playback)
        if (
            observation.get(
                "response_authority_receipt_sha256"
            )
            != delivery[
                "source_response_authority_receipt_sha256"
            ]
        ):
            raise RuntimeError(
                "camera response and transient playback custody diverged"
            )
        delivery["thing_ids"] = list(observation["thing_ids"])
        deliveries.append(delivery)
    if not deliveries:
        raise RuntimeError(
            "fresh browser observed no learned camera-evoked articulation"
        )

    created = media.get("created")
    plays = media.get("plays")
    revoked = media.get("revoked")
    active = media.get("activeUrls")
    maximum_active = media.get("maximumActiveUrls")
    if (
        not isinstance(created, list)
        or not isinstance(plays, list)
        or not isinstance(revoked, list)
        or not isinstance(active, list)
        or maximum_active != 1
        or active
    ):
        raise RuntimeError(
            "browser articulation did not retain exactly one bounded slot"
        )
    created_by_digest = {
        value.get("pcmSha256"): value
        for value in created
        if isinstance(value, dict)
    }
    played_urls = {
        value.get("src")
        for value in plays
        if (
            isinstance(value, dict)
            and value.get("resolved") is True
            and value.get("error") is None
        )
    }
    revoked_urls = set(revoked)
    for delivery in deliveries:
        creation = created_by_digest.get(delivery["pcm_sha256"])
        if (
            not isinstance(creation, dict)
            or creation.get("wavHeaderValid") is not True
            or creation.get("error") is not None
            or creation.get("url") not in played_urls
            or creation.get("url") not in revoked_urls
            or creation.get("byteCount")
            != delivery["pcm_byte_count"] + 44
        ):
            raise RuntimeError(
                "verified camera PCM was not played and released by Chromium"
            )
    return {
        "delivery_count": len(deliveries),
        "deliveries": deliveries,
        "maximum_browser_playback_slots": maximum_active,
        "settled_sight_fields": len(settled),
        "silent_sight_responses": silent_responses,
    }


def _media_snapshot(page) -> dict[str, object]:
    return page.evaluate(
        """() => {
          const value=window.__liveArticulationMedia;
          return {
            activeUrls:Array.from(value.activeUrls),
            created:value.created.map(item=>({...item})),
            maximumActiveUrls:value.maximumActiveUrls,
            plays:value.plays.map(item=>({...item})),
            revoked:[...value.revoked]
          };
        }"""
    )


def _continuous_microphone_evidence(
    settled: list[dict[str, object]],
) -> dict[str, object]:
    digests: list[str] = []
    nonzero_chunks = 0
    total_samples = 0
    for record in settled:
        request = record["request"]
        encoded = request.get("text")
        if not isinstance(encoded, str):
            raise RuntimeError("browser microphone request lost PCM")
        try:
            pcm = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise RuntimeError(
                "browser microphone PCM is not canonical base64"
            ) from error
        expected_bytes = request["audio_sample_count"] * 2
        if len(pcm) != expected_bytes:
            raise RuntimeError(
                "browser microphone sample count and PCM diverged"
            )
        digests.append(hashlib.sha256(pcm).hexdigest())
        total_samples += len(pcm) // 2
        if any(pcm):
            nonzero_chunks += 1
    if nonzero_chunks == 0 or len(set(digests)) < 2:
        raise RuntimeError(
            "continuous microphone carried no changing physical pressure"
        )
    return {
        "nonzero_chunks": nonzero_chunks,
        "pcm_sha256s": digests,
        "settled_chunks": len(settled),
        "settled_samples": total_samples,
    }


def run_live_probe(
    *,
    wav_path: Path | None,
    proof_seconds: int,
) -> dict[str, object]:
    if proof_seconds < PROOF_SECONDS:
        raise ValueError(
            f"live sensory proof must run for at least {PROOF_SECONDS}s"
        )
    cutover = verify_live_cutover(VerificationConfig())
    schedule = build_cognitive_proof_wav()
    if wav_path is None:
        wav_path = schedule["wav_path"]
    if not isinstance(wav_path, Path) or not wav_path.is_file():
        raise FileNotFoundError(
            f"authenticated microphone WAV is absent: {wav_path}"
        )
    with wave.open(str(wav_path), "rb") as supplied:
        supplied_shape = (
            supplied.getnchannels(),
            supplied.getsampwidth(),
            supplied.getframerate(),
            supplied.getnframes(),
        )
        supplied_pcm = supplied.readframes(supplied.getnframes())
    if (
        supplied_shape
        != (1, 2, 16_000, schedule["sample_count"])
        or hashlib.sha256(supplied_pcm).hexdigest()
        != schedule["pcm_sha256"]
    ):
        raise RuntimeError(
            "live microphone WAV differs from the authenticated schedule"
        )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "live sensory proof requires the Python Playwright package"
        ) from error

    console_errors: list[str] = []
    http_errors: list[dict[str, object]] = []
    status_samples: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
                f"--use-file-for-fake-audio-capture={wav_path}",
            ],
        )
        context = browser.new_context()
        context.grant_permissions(
            ["camera", "microphone"],
            origin=LIVE_ORIGIN,
        )
        page = context.new_page()
        page.add_init_script(
            _browser_instrumentation(PRODUCTION_API_ORIGIN)
        )
        page.add_init_script(_playback_instrumentation())
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "response",
            lambda response: http_errors.append({
                "status": response.status,
                "url": response.url,
            })
            if response.status >= 400
            else None,
        )
        page.goto(LIVE_PAGE_URL, wait_until="domcontentloaded")
        page.locator("#mic-perm").click()
        page.locator("#cam-perm").click()
        page.wait_for_function(
            """() => Boolean(
              micPCMActive&&micEpoch&&micEpoch.active&&
              micEpoch.accepting&&camStream
            )""",
            timeout=30_000,
        )
        page.evaluate(
            "() => { window.__candidateProofStartedAtMs=performance.now(); }"
        )
        deadline = time.monotonic() + proof_seconds
        while time.monotonic() < deadline:
            page.wait_for_timeout(500)
            status_samples.append(_status_snapshot(page))
        final_active_status = _status_snapshot(page)

        page.locator("#cam-perm").click()
        page.wait_for_function(
            """() => (
              !camStream&&standaloneSightRequest===null&&
              standaloneSightAbort===null
            )""",
            timeout=30_000,
        )
        page.wait_for_function(
            """() => window.__liveArticulationMedia.created.every(
              value=>value.pcmSha256!==null||value.error!==null
            )""",
            timeout=30_000,
        )
        drain = _stop_admission_and_drain(page)
        sound_records = drain.pop("soundRecords")
        settled_sound = _validate_records(sound_records)
        microphone = _continuous_microphone_evidence(
            settled_sound
        )
        sight_records = page.evaluate(
            "() => window.__candidateSightFrames"
        )
        media = _media_snapshot(page)
        articulation = validate_same_request_articulation(
            sight_records,
            media,
        )
        fetch_errors = page.evaluate(
            "() => window.__candidateFetchErrors"
        )
        if fetch_errors:
            raise RuntimeError(
                f"browser request instrumentation failed: {fetch_errors}"
            )
        unstarted_v7 = [
            value
            for value in http_errors
            if (
                value["status"] == 404
                and "/v7/state?session_id=" in value["url"]
            )
        ]
        unexpected_http_errors = [
            value for value in http_errors
            if value not in unstarted_v7
        ]
        if (
            unexpected_http_errors
            or len(console_errors) != len(unstarted_v7)
        ):
            raise RuntimeError(
                "fresh browser emitted errors: "
                f"console={console_errors}; "
                f"http={unexpected_http_errors}; "
                f"unstarted_v7={unstarted_v7}"
            )
        if (
            not final_active_status["microphoneActive"]
            or not final_active_status["cameraActive"]
            or final_active_status["microphoneTracks"] != ["live"]
            or final_active_status["cameraTracks"] != ["live"]
            or any(
                not value["microphoneActive"]
                or not value["cameraActive"]
                for value in status_samples
            )
        ):
            raise RuntimeError(
                "camera or continuous microphone stopped during proof"
            )
        maximum_pending = max(
            value["pendingChunks"]
            for value in status_samples
            if isinstance(value.get("pendingChunks"), int)
        )
        page.locator("#mic-perm").click()
        context.close()
        browser.close()
    return {
        "articulation": articulation,
        "capture_drain": drain,
        "continuous_microphone": {
            **microphone,
            "maximum_pending_chunks": maximum_pending,
        },
        "cutover": cutover,
        "schema": "guala.live_sensory_articulation_proof.v1",
        "status": "verified",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", type=Path, default=None)
    parser.add_argument(
        "--seconds",
        type=int,
        default=PROOF_SECONDS,
    )
    args = parser.parse_args()
    result = run_live_probe(
        wav_path=args.wav,
        proof_seconds=args.seconds,
    )
    print(json.dumps(
        result,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
