#!/usr/bin/env python3
"""Live Chromium proof of Guala's bounded physical hearing custody.

This proof does not test word recognition, language, learned meaning, or
cognition.  A deterministic, nonsemantic acoustic pressure schedule enters
Chromium through its real microphone/media/audio-worklet path.  The deployed
page must preserve one native 16 kHz mono clock, exact PCM continuity,
cochlear/receptor/settlement receipts, and the full D/M/R/U/C/P/B observation.

If Chromium exposes two captured source channels, their discrete lineage and
whether their bytes are actually distinct are reported.  Browser channels do
not become physical ears or room-hearing authority.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import sys
import tempfile
import time
import urllib.request
import wave
from array import array
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_CHUNK_SAMPLES,
    PCM_CONTINUITY_SCHEMA,
    PCM_MAX_CHUNK_SAMPLES,
    PCM_RING_BYTES,
    PCM_SAMPLE_RATE_HZ,
    PCM_TRANSPORT_UNITS,
)


SCHEMA = "guala.production.physical_hearing.live_proof.v1"
OBSERVATION_SCHEMA = "guala.observation_snapshot.v5"
PRODUCTION_API_ORIGIN = (
    "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
)
PAGE_URL = "https://dsf-ai.com/gualaloom.html"
OBSERVATION_URL = (
    f"{PRODUCTION_API_ORIGIN}/api/v1/gualaloom/observation"
)
REVIEWED_PAGE = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
FULL_FIELD_NAMES = (
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
)
MINIMUM_PROOF_SECONDS = 12
DEFAULT_PROOF_SECONDS = 14
MAXIMUM_PROOF_SECONDS = 60
MINIMUM_SETTLED_CHUNKS = 5
MAXIMUM_OBSERVATION_BYTES = 1_048_576
SHA256_HEX = frozenset("0123456789abcdef")


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in SHA256_HEX for character in value)
    ):
        raise RuntimeError(f"{name} is not a canonical SHA-256 receipt")
    return value


def _canonical_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()


def build_nonsemantic_pressure_wav(
    output_path: Path,
    *,
    duration_seconds: int,
) -> dict[str, object]:
    """Create a deterministic varying pressure field with no speech content."""

    if (
        isinstance(duration_seconds, bool)
        or not isinstance(duration_seconds, int)
        or duration_seconds < MINIMUM_PROOF_SECONDS + 4
        or duration_seconds > MAXIMUM_PROOF_SECONDS + 4
    ):
        raise ValueError("physical pressure duration is outside its bound")
    total_samples = duration_seconds * PCM_SAMPLE_RATE_HZ
    silence_samples = PCM_SAMPLE_RATE_HZ // 4
    values = array("h")
    lcg = 0x13579BDF
    for index in range(total_samples):
        if index < silence_samples:
            values.append(0)
            continue
        local = index - silence_samples
        segment = (local // (2 * PCM_SAMPLE_RATE_HZ)) % 4
        frequency = (173, 307, 521, 887)[segment]
        phase = 2.0 * math.pi * frequency * local / PCM_SAMPLE_RATE_HZ
        lcg = (1_103_515_245 * lcg + 12_345) & 0x7FFFFFFF
        noise = ((lcg >> 18) & 0x1FFF) - 4096
        envelope = 1 + ((local // 800) % 7)
        sample = int(
            7_500 * math.sin(phase)
            + 2_300 * math.sin(phase * 0.37)
            + noise * envelope // 18
        )
        values.append(max(-32_768, min(32_767, sample)))
    if sys.byteorder != "little":
        values.byteswap()
    pcm = values.tobytes()
    with wave.open(str(output_path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(PCM_SAMPLE_RATE_HZ)
        target.writeframes(pcm)
    return {
        "channels": 1,
        "duration_seconds": duration_seconds,
        "first_pressure_sample": silence_samples,
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "sample_count": total_samples,
        "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
        "sample_width_bytes": 2,
    }


def _instrumentation() -> str:
    return f"""
      (() => {{
        const production={json.dumps(PRODUCTION_API_ORIGIN)};
        const nativeFetch=window.fetch.bind(window);
        window.__physicalHearing={{
          monoOpen:[],monoClose:[],binauralOpen:[],binauralClose:[],
          sound:[],binaural:[],lineage:[],fetchErrors:[]
        }};
        const classify=path=>{{
          if(path.endsWith('/api/v1/auditory/pcm/open'))return 'monoOpen';
          if(path.endsWith('/api/v1/auditory/pcm/close'))return 'monoClose';
          if(path.endsWith('/api/v1/auditory/binaural-pcm/open'))return 'binauralOpen';
          if(path.endsWith('/api/v1/auditory/binaural-pcm/close'))return 'binauralClose';
          if(path.endsWith('/sound_frame'))return 'sound';
          if(path.endsWith('/api/v1/auditory/binaural-pcm/chunk'))return 'binaural';
          if(path.endsWith('/api/v1/auditory/binaural-pcm/lineage'))return 'lineage';
          return null;
        }};
        window.fetch=(input,init={{}})=>{{
          const supplied=typeof input==='string'?input:input.url;
          const kind=classify(supplied);
          let record=null;
          if(kind){{
            let request=null;
            try{{
              request=init.body?JSON.parse(init.body):null;
            }}catch(error){{
              window.__physicalHearing.fetchErrors.push(
                kind+' request capture failed: '+error.message
              );
            }}
            record={{
              request,response:null,responseStatus:null,fetchError:null,
              requestedAtMs:performance.now(),responseAtMs:null
            }};
            window.__physicalHearing[kind].push(record);
          }}
          const rewritten=supplied.startsWith(production)
            ? production+supplied.slice(production.length):supplied;
          return nativeFetch(rewritten,init).then(response=>{{
            if(record){{
              record.responseStatus=response.status;
              record.responseAtMs=performance.now();
              response.clone().json().then(value=>{{
                record.response=value;
              }}).catch(error=>{{
                record.fetchError=error.message;
              }});
            }}
            return response;
          }}).catch(error=>{{
            if(record)record.fetchError=error.message;
            throw error;
          }});
        }};
      }})();
    """


def _browser_status(page: Any) -> dict[str, object]:
    return page.evaluate(
        """() => ({
          microphoneActive:Boolean(
            micPCMActive&&micEpoch&&micEpoch.active&&micEpoch.accepting
          ),
          pendingChunks:micEpoch?micEpoch.pendingChunks:null,
          sequence:micEpoch?micEpoch.sequence:null,
          monoStreamId:micEpoch?micEpoch.monoStreamId:null,
          binauralStreamId:micEpoch?micEpoch.streamId:null,
          inputChannelCount:micEpoch?micEpoch.inputChannelCount:null,
          binauralActive:Boolean(
            micEpoch&&micEpoch.active&&micEpoch.accepting&&
            micEpoch.binauralActive
          ),
          microphoneTracks:micStream
            ? micStream.getTracks().map(track=>track.readyState):[]
        })"""
    )


def _stop_and_drain(page: Any, timeout_ms: int = 70_000) -> dict[str, object]:
    return page.evaluate(
        """async timeoutMs => {
          const epoch=micEpoch;
          if(!epoch||!epoch.active||!epoch.accepting){
            throw new Error('microphone epoch was not accepting at proof stop');
          }
          const acceptedBeforeStop=epoch.sequence;
          const pendingBeforeStop=epoch.pendingChunks;
          const soundRequestsAtStop=window.__physicalHearing.sound.length;
          const binauralRequestsAtStop=window.__physicalHearing.binaural.length;
          const terminal=value=>value&&(
            value.response!==null||value.fetchError!==null
          );
          const binauralWasActive=epoch.binauralActive;
          const inputChannelCount=epoch.inputChannelCount;
          const closePromise=_closePCMEpoch(epoch,true,true);
          if(epoch.accepting)throw new Error('microphone admission remained open');
          const deadline=performance.now()+timeoutMs;
          while(true){
            const sound=window.__physicalHearing.sound;
            const binaural=window.__physicalHearing.binaural;
            const countsComplete=
              sound.length===acceptedBeforeStop&&
              (!binauralWasActive||binaural.length===acceptedBeforeStop);
            if(epoch.pendingChunks===0&&countsComplete&&
               sound.every(terminal)&&binaural.every(terminal))break;
            if(sound.length>acceptedBeforeStop||
               binaural.length>acceptedBeforeStop){
              throw new Error('capture admitted an interval after stop');
            }
            if(performance.now()>=deadline){
              throw new Error('accepted microphone intervals did not drain');
            }
            await new Promise(resolve=>setTimeout(resolve,25));
          }
          await closePromise;
          return {
            acceptedBeforeStop,pendingBeforeStop,soundRequestsAtStop,
            binauralRequestsAtStop,binauralWasActive,inputChannelCount,
            soundRequestsAfterDrain:window.__physicalHearing.sound.length,
            binauralRequestsAfterDrain:window.__physicalHearing.binaural.length,
            newAdmissionsAfterStop:Math.max(
              0,
              window.__physicalHearing.sound.length-acceptedBeforeStop,
              window.__physicalHearing.binaural.length-acceptedBeforeStop
            )
          };
        }""",
        timeout_ms,
    )


def _single_open_record(
    records: list[dict[str, object]],
    *,
    kind: str,
) -> dict[str, object]:
    if len(records) != 1:
        raise RuntimeError(f"{kind} did not have exactly one open response")
    record = records[0]
    response = record.get("response")
    if (
        record.get("responseStatus") != 200
        or record.get("fetchError") is not None
        or not isinstance(response, dict)
        or response.get("ok") is not True
    ):
        raise RuntimeError(f"{kind} open failed: {response}")
    if (
        response.get("sample_rate_hz") != PCM_SAMPLE_RATE_HZ
        or response.get("chunk_samples") != PCM_CHUNK_SAMPLES
        or response.get("max_chunk_samples") != PCM_MAX_CHUNK_SAMPLES
    ):
        raise RuntimeError(f"{kind} open returned different physical bounds")
    return response


def _single_close_record(
    records: list[dict[str, object]],
    *,
    kind: str,
) -> dict[str, object]:
    if len(records) != 1:
        raise RuntimeError(f"{kind} did not have exactly one close response")
    record = records[0]
    response = record.get("response")
    if (
        record.get("responseStatus") != 200
        or record.get("fetchError") is not None
        or not isinstance(response, dict)
        or response.get("ok") is not True
        or response.get("continuity") != "closed"
    ):
        raise RuntimeError(f"{kind} close failed: {response}")
    return response


def validate_mono_settlements(
    records: list[dict[str, object]],
) -> dict[str, object]:
    settled = [
        record
        for record in records
        if isinstance(record.get("response"), dict)
    ]
    if len(settled) < MINIMUM_SETTLED_CHUNKS:
        raise RuntimeError("too few physical mono settlements")
    prior_receipt: str | None = None
    source_epoch_ns: int | None = None
    captured_chunks: list[bytes] = []
    continuity_receipts: list[str] = []
    receptor_receipts: list[str] = []
    settlement_receipts: list[str] = []
    cochlear_receipts: list[str] = []
    maximum_pending_transport = 0
    maximum_pending_experiences = 0
    pending_experience_capacity = 0
    for sequence, record in enumerate(settled):
        request = record.get("request")
        response = record.get("response")
        if (
            record.get("responseStatus") != 200
            or record.get("fetchError") is not None
            or not isinstance(request, dict)
            or not isinstance(response, dict)
            or response.get("ok") is not True
            or response.get("causal_boundary") != "sound"
            or response.get("observed_senses") != ["sound"]
        ):
            raise RuntimeError(f"mono settlement {sequence} was not physical sound")
        try:
            pcm = base64.b64decode(request["text"], validate=True)
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError("mono settlement lost canonical PCM") from error
        epoch_ms = request.get("audio_source_epoch_ms")
        if (
            request.get("audio_encoding") != "pcm_s16le"
            or request.get("audio_sample_rate_hz") != PCM_SAMPLE_RATE_HZ
            or request.get("audio_sequence") != sequence
            or request.get("audio_first_sample_index")
            != sequence * PCM_CHUNK_SAMPLES
            or request.get("audio_sample_count") != PCM_CHUNK_SAMPLES
            or len(pcm) != PCM_CHUNK_SAMPLES * 2
            or isinstance(epoch_ms, bool)
            or not isinstance(epoch_ms, int)
        ):
            raise RuntimeError("mono settlement left native 16 kHz continuity")
        current_epoch_ns = epoch_ms * 1_000_000
        if source_epoch_ns is None:
            source_epoch_ns = current_epoch_ns
        elif current_epoch_ns != source_epoch_ns:
            raise RuntimeError("mono source epoch changed during capture")
        continuity = response.get("pcm_continuity")
        recognition = response.get("spoken_word_recognition")
        motif = response.get("auditory_motif")
        auditory = response.get("auditory_l5")
        if (
            not isinstance(continuity, dict)
            or continuity.get("status") != "contiguous"
            or continuity.get("sequence") != sequence
            or continuity.get("first_sample_index")
            != sequence * PCM_CHUNK_SAMPLES
            or continuity.get("sample_count") != PCM_CHUNK_SAMPLES
            or continuity.get("meaning_authority") is not False
            or continuity.get("transcript_authority") is not False
            or continuity.get("binaural_hardware_authority_proven")
            is not False
            or continuity.get("room_hearing_authority") is not False
        ):
            raise RuntimeError("mono continuity receipt crossed its authority")
        expected_continuity = _canonical_digest({
            "first_sample_index": sequence * PCM_CHUNK_SAMPLES,
            "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            "prior_receipt_sha256": prior_receipt,
            "sample_count": PCM_CHUNK_SAMPLES,
            "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "schema": PCM_CONTINUITY_SCHEMA,
            "sequence": sequence,
            "stream_id": request.get("audio_stream_id"),
            "source_epoch_start_ns": source_epoch_ns,
        })
        if continuity.get("receipt_sha256") != expected_continuity:
            raise RuntimeError("mono PCM is absent from its continuity receipt")
        if (
            not isinstance(recognition, dict)
            or recognition.get("recognized_form") is not None
            or recognition.get("candidate_labels") != []
            or recognition.get("kind_id") is not None
            or recognition.get("meaning_authority") is not False
            or recognition.get("transcript_authority") is not False
        ):
            raise RuntimeError("physical sound gained word or meaning authority")
        if (
            not isinstance(motif, dict)
            or motif.get("authority_receipt_sha256")
            != continuity.get("auditory_motif_result_receipt_sha256")
        ):
            raise RuntimeError("receptor result custody is absent")
        receptor_receipts.append(_sha256(
            motif.get("source_receptor_event_receipt_sha256"),
            "receptor event",
        ))
        continuity_receipts.append(_sha256(
            continuity.get("receipt_sha256"),
            "PCM continuity",
        ))
        cochlear_receipts.append(_sha256(
            continuity.get("cochlear_state_receipt_sha256"),
            "cochlear state",
        ))
        settlement_receipts.append(_sha256(
            continuity.get("causal_settlement_receipt_sha256"),
            "causal settlement",
        ))
        if (
            not isinstance(auditory, dict)
            or auditory.get("recognition_attempted") is not False
        ):
            raise RuntimeError("physical owner reported a recognition attempt")
        streams = auditory.get("continuous_streams")
        presemantic = auditory.get("recurrent_motif")
        if (
            not isinstance(streams, dict)
            or not isinstance(streams.get("active_streams"), int)
            or not isinstance(streams.get("stream_capacity"), int)
            or streams["active_streams"] < 1
            or streams["active_streams"] > streams["stream_capacity"]
            or not isinstance(presemantic, dict)
            or presemantic.get("semantic_authority") is not False
            or presemantic.get("transcript_authority") is not False
        ):
            raise RuntimeError("auditory resource owner crossed its bound")
        pending = presemantic.get("pending_transport_units")
        terminals = presemantic.get("active_terminal_streams")
        per_stream = presemantic.get("max_pending_transport_units_per_stream")
        experiences = presemantic.get("pending_independent_experience_count")
        capacity = presemantic.get("pending_independent_experience_capacity")
        if (
            not all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in (
                    pending,
                    terminals,
                    per_stream,
                    experiences,
                    capacity,
                )
            )
            or pending > terminals * per_stream
            or experiences > capacity
        ):
            raise RuntimeError("auditory retained work exceeded exact capacity")
        maximum_pending_transport = max(maximum_pending_transport, pending)
        maximum_pending_experiences = max(
            maximum_pending_experiences,
            experiences,
        )
        pending_experience_capacity = capacity
        captured_chunks.append(pcm)
        prior_receipt = expected_continuity
    captured = b"".join(captured_chunks)
    if not any(captured):
        raise RuntimeError("captured microphone pressure is identically zero")
    captured_values = array("h")
    captured_values.frombytes(captured)
    if sys.byteorder != "little":
        captured_values.byteswap()
    captured_first_pressure_sample = next(
        index
        for index, value in enumerate(captured_values)
        if value != 0
    )
    return {
        "captured_first_pressure_sample": (
            captured_first_pressure_sample
        ),
        "captured_pcm_sha256": hashlib.sha256(captured).hexdigest(),
        "causal_settlement_receipt_sha256s": settlement_receipts,
        "cochlear_state_receipt_sha256s": cochlear_receipts,
        "continuity_receipt_sha256s": continuity_receipts,
        "maximum_pending_experiences": maximum_pending_experiences,
        "maximum_pending_transport_units": maximum_pending_transport,
        "pending_experience_capacity": pending_experience_capacity,
        "receptor_event_receipt_sha256s": receptor_receipts,
        "settled_chunks": len(settled),
        "settled_samples": len(captured) // 2,
        "source_epoch_start_ns": source_epoch_ns,
        "word_result": None,
    }


def validate_binaural_transport(
    records: list[dict[str, object]],
    lineages: list[dict[str, object]],
    *,
    active: bool,
    input_channel_count: object,
    mono_settlement_count: int,
) -> dict[str, object]:
    settled = [
        record
        for record in records
        if isinstance(record.get("response"), dict)
    ]
    lineage_settled = [
        record
        for record in lineages
        if isinstance(record.get("response"), dict)
    ]
    if not active:
        if settled or lineage_settled:
            raise RuntimeError("inactive channel pair emitted lineage or PCM")
        return {
            "available": False,
            "binaural_hardware_authority_proven": False,
            "distinct_channel_bytes_observed": False,
            "input_channel_count": input_channel_count,
            "reason": "runtime_exposed_one_captured_channel",
            "room_hearing_authority": False,
        }
    if len(lineage_settled) != 1:
        raise RuntimeError("active channel pair has no unique lineage")
    lineage_request = lineage_settled[0].get("request")
    lineage_response = lineage_settled[0].get("response")
    if (
        lineage_settled[0].get("responseStatus") != 200
        or lineage_settled[0].get("fetchError") is not None
        or not isinstance(lineage_request, dict)
        or not isinstance(lineage_response, dict)
        or lineage_response.get("ok") is not True
        or lineage_request.get("media_track_channel_count") != 2
        or lineage_request.get("worklet_input_channel_count") != 2
        or lineage_request.get("channel_order") != ["left", "right"]
        or lineage_response.get("binaural_hardware_authority_proven")
        is not False
        or lineage_response.get("cognition_authority") is not False
    ):
        raise RuntimeError("channel-pair lineage crossed its authority")
    lineage_receipt = _sha256(
        lineage_response.get("lineage_receipt_sha256"),
        "channel lineage",
    )
    if len(settled) != mono_settlement_count:
        raise RuntimeError("channel pair and mono projection lost cadence")
    distinct = False
    receipt_sha256s = []
    for sequence, record in enumerate(settled):
        request = record.get("request")
        response = record.get("response")
        if (
            record.get("responseStatus") != 200
            or record.get("fetchError") is not None
            or not isinstance(request, dict)
            or not isinstance(response, dict)
            or response.get("ok") is not True
            or request.get("sequence") != sequence
            or request.get("first_sample_index")
            != sequence * PCM_CHUNK_SAMPLES
            or request.get("lineage_receipt_sha256") != lineage_receipt
        ):
            raise RuntimeError("channel-pair PCM lost exact continuity")
        distinct = distinct or (
            request.get("left_pcm_b64") != request.get("right_pcm_b64")
        )
        room = response.get("room_hearing")
        continuity = response.get("continuity")
        if (
            response.get("binaural_hardware_authority_proven") is not False
            or response.get("cognition_authority") is not False
            or response.get("meaning_authority") is not False
            or not isinstance(room, dict)
            or room.get("authority") is not False
            or not isinstance(continuity, dict)
            or continuity.get("status") != "contiguous"
        ):
            raise RuntimeError("browser channel pair became false physical ears")
        receipt_sha256s.append(_sha256(
            continuity.get("receipt_sha256"),
            "channel-pair continuity",
        ))
    return {
        "available": True,
        "binaural_hardware_authority_proven": False,
        "channel_order": ["left", "right"],
        "distinct_channel_bytes_observed": distinct,
        "input_channel_count": input_channel_count,
        "lineage_receipt_sha256": lineage_receipt,
        "room_hearing_authority": False,
        "settled_pair_chunks": len(settled),
        "transport_receipt_sha256s": receipt_sha256s,
    }


def validate_full_field_observation(
    value: object,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError("observation response is not an object")
    if value.get("schema") != OBSERVATION_SCHEMA:
        raise RuntimeError("physical observation is not schema v5")
    receipt = _sha256(
        value.get("snapshot_receipt_sha256"),
        "observation snapshot",
    )
    payload = dict(value)
    del payload["snapshot_receipt_sha256"]
    if receipt != _canonical_digest(payload):
        raise RuntimeError("observation snapshot receipt does not match")
    authority = value.get("full_field_authority")
    if (
        not isinstance(authority, dict)
        or authority.get("available") is not True
        or authority.get("status") != "observed"
    ):
        raise RuntimeError("observation has no current full-field authority")
    settlement_receipt = _sha256(
        authority.get("settlement_receipt_sha256"),
        "observation settlement",
    )
    sound_senses = [
        sense
        for sense in authority.get("senses", [])
        if isinstance(sense, dict)
        and sense.get("sense") == "sound"
        and sense.get("state") == "observed"
    ]
    if len(sound_senses) != 1:
        raise RuntimeError("observation has no unique observed sound sense")
    substreams = sound_senses[0].get("substreams")
    if not isinstance(substreams, list) or not substreams:
        raise RuntimeError("observed sound has no receptor substreams")
    for substream in substreams:
        if (
            not isinstance(substream, dict)
            or [item[0] for item in substream.get("fields", [])]
            != list(FULL_FIELD_NAMES)
            or not isinstance(substream.get("total_temporal_tuples"), int)
            or substream["total_temporal_tuples"] <= 0
        ):
            raise RuntimeError("sound receptor lost the explicit full field")
    contract = authority.get("view_contract")
    if (
        not isinstance(contract, dict)
        or contract.get("decision_authority") is not False
        or contract.get("required_fields") != list(FULL_FIELD_NAMES)
    ):
        raise RuntimeError("full-field observation crossed its authority")
    return {
        "receptor_substream_count": len(substreams),
        "settlement_receipt_sha256": settlement_receipt,
        "snapshot_receipt_sha256": receipt,
    }


def _fetch_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"GET {url} returned HTTP {response.status}")
        body = response.read(MAXIMUM_OBSERVATION_BYTES + 1)
    if len(body) > MAXIMUM_OBSERVATION_BYTES:
        raise RuntimeError("observation response exceeds its byte bound")
    return json.loads(body.decode("utf-8", errors="strict"))


def run_live_physical_hearing_probe(
    *,
    proof_seconds: int = DEFAULT_PROOF_SECONDS,
) -> dict[str, object]:
    if (
        isinstance(proof_seconds, bool)
        or not isinstance(proof_seconds, int)
        or proof_seconds < MINIMUM_PROOF_SECONDS
        or proof_seconds > MAXIMUM_PROOF_SECONDS
    ):
        raise ValueError("proof duration is outside its exact bound")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "physical hearing proof requires the Python Playwright package"
        ) from error
    reviewed = REVIEWED_PAGE.read_bytes()
    reviewed_sha256 = hashlib.sha256(reviewed).hexdigest()
    with urllib.request.urlopen(PAGE_URL, timeout=30) as response:
        deployed = response.read()
    deployed_sha256 = hashlib.sha256(deployed).hexdigest()
    if deployed_sha256 != reviewed_sha256:
        raise RuntimeError("deployed Guala page differs from reviewed source")

    with tempfile.TemporaryDirectory(
        prefix="guala-live-physical-hearing-",
    ) as temporary:
        wav_path = Path(temporary) / "nonsemantic-pressure.wav"
        source = build_nonsemantic_pressure_wav(
            wav_path,
            duration_seconds=proof_seconds + 4,
        )
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
            context.grant_permissions(["microphone"], origin="https://dsf-ai.com")
            page = context.new_page()
            page.add_init_script(_instrumentation())
            page.goto(PAGE_URL, wait_until="domcontentloaded")
            page.locator("#mic-perm").click()
            page.wait_for_function(
                "() => Boolean(micPCMActive&&micEpoch&&micEpoch.active)",
                timeout=30_000,
            )
            maximum_pending = 0
            deadline = time.monotonic() + proof_seconds
            while time.monotonic() < deadline:
                page.wait_for_timeout(250)
                status = _browser_status(page)
                pending = status.get("pendingChunks")
                if not isinstance(pending, int) or isinstance(pending, bool):
                    raise RuntimeError("browser did not expose pending PCM work")
                maximum_pending = max(maximum_pending, pending)
                if maximum_pending > PCM_TRANSPORT_UNITS:
                    raise RuntimeError("browser exceeded exact pending PCM capacity")
            drain = _stop_and_drain(page)
            page.wait_for_function(
                """() => (
                  window.__physicalHearing.monoClose.length===1&&
                  window.__physicalHearing.binauralClose.length===1&&
                  window.__physicalHearing.monoClose.every(
                    value=>value.response!==null||value.fetchError!==null
                  )&&
                  window.__physicalHearing.binauralClose.every(
                    value=>value.response!==null||value.fetchError!==null
                  )
                )""",
                timeout=10_000,
            )
            records = page.evaluate("() => window.__physicalHearing")
            stopped = _browser_status(page)
            if (
                stopped.get("microphoneActive") is not False
                or stopped.get("pendingChunks") != 0
                or drain.get("newAdmissionsAfterStop") != 0
                or drain.get("soundRequestsAfterDrain")
                != drain.get("acceptedBeforeStop")
                or records.get("fetchErrors") != []
            ):
                raise RuntimeError("browser microphone did not close and drain")
            mono_open = _single_open_record(
                records["monoOpen"],
                kind="mono",
            )
            pair_open = _single_open_record(
                records["binauralOpen"],
                kind="channel-pair",
            )
            if (
                pair_open.get("channel_count") != 2
                or pair_open.get("channel_order") != ["left", "right"]
                or pair_open.get("binaural_hardware_authority_proven")
                is not False
            ):
                raise RuntimeError(
                    "channel-pair open crossed its transport authority"
                )
            mono = validate_mono_settlements(records["sound"])
            if mono_open.get("stream_id") != (
                records["sound"][0]["request"]["audio_stream_id"]
            ):
                raise RuntimeError("mono open custody changed before settlement")
            binaural = validate_binaural_transport(
                records["binaural"],
                records["lineage"],
                active=drain.get("binauralWasActive") is True,
                input_channel_count=drain.get("inputChannelCount"),
                mono_settlement_count=mono["settled_chunks"],
            )
            mono_close = _single_close_record(
                records["monoClose"],
                kind="mono",
            )
            pair_close = _single_close_record(
                records["binauralClose"],
                kind="channel-pair",
            )
            context.close()
            browser.close()

    observation = validate_full_field_observation(
        _fetch_json(OBSERVATION_URL),
    )
    source_start_offset_samples = (
        source["first_pressure_sample"]
        - mono["captured_first_pressure_sample"]
    )
    if (
        source_start_offset_samples < 0
        or source_start_offset_samples + mono["settled_samples"]
        > source["sample_count"]
    ):
        raise RuntimeError(
            "captured pressure has no bounded offset inside its source"
        )
    return {
        "authorities": {
            "cognition": False,
            "meaning": False,
            "transcript": False,
            "word": False,
        },
        "binaural_transport": binaural,
        "deployed_html_sha256": deployed_sha256,
        "closed_streams": {
            "binaural": pair_close["continuity"],
            "mono": mono_close["continuity"],
        },
        "mono_physical_hearing": mono,
        "observation_full_field": observation,
        "resource_bounds": {
            "browser_maximum_pending_chunks": maximum_pending,
            "browser_pending_chunk_capacity": PCM_TRANSPORT_UNITS,
            "mono_chunk_samples": PCM_CHUNK_SAMPLES,
            "mono_max_chunk_samples": PCM_MAX_CHUNK_SAMPLES,
            "mono_ring_capacity_bytes": PCM_RING_BYTES,
            "proof_duration_seconds": proof_seconds,
        },
        "reviewed_html_sha256": reviewed_sha256,
        "schema": SCHEMA,
        "source_pressure": source,
        "source_start_offset_samples": source_start_offset_samples,
        "status": "physical_hearing_verified",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove deployed Chromium-to-Guala physical hearing custody "
            "without any learned-word or cognition claim."
        ),
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=DEFAULT_PROOF_SECONDS,
    )
    args = parser.parse_args(argv)
    result = run_live_physical_hearing_probe(
        proof_seconds=args.seconds,
    )
    print(json.dumps(
        result,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
