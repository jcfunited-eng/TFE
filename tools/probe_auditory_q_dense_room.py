"""Prove exact presemantic word-sized q structure under dense room sound.

Two file-disjoint examples of each acoustic kind are experienced repeatedly,
then retained with their complete authenticated D/M/R/U/C/P/B occurrence
witnesses.  Exact acoustic contrast learns only ordered local-q relations
present in both positive experiences and absent from every explicit contrast.

The held-out stress stream contains unseen speakers for both learned acoustic
kinds plus continuous, non-clipping broadband room sound.  A successful run
requires every complete physical q window to contain both complete learned
relation assemblies.  A room-only window and an unseen unrelated spoken word
under different room sound must contain neither.

This proves exact presemantic structural co-detection and live cadence.  It
does not claim waveform source recovery, speaker identity, semantic word
meaning, or L6 certainty.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import statistics
import time

import numpy as np

import dsf_ai_service.app as app_module
from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_CHUNK_SAMPLES,
    PCM_SAMPLE_RATE_HZ,
    AuditoryPCMStreamRegistry,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifObservationState,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from tools.probe_guala_candidate_browser import (
    COGNITIVE_SOURCE_RECORDINGS,
    _checked_cognitive_source,
)
from tools.probe_guala_pcm_cadence import _post


COMPONENT_A_SOURCES = (
    COGNITIVE_SOURCE_RECORDINGS[0],
    COGNITIVE_SOURCE_RECORDINGS[1],
)
COMPONENT_B_SOURCES = (
    (
        "dsf_ai_service/curriculum/assets/speech_commands/down/"
        "00b01445_nohash_1.wav",
        "bda9ed511cd09723a888b8551de49794d77da02727ad5fa01a399abe32e6ebf8",
    ),
    (
        "dsf_ai_service/curriculum/assets/speech_commands/down/"
        "014f9f65_nohash_0.wav",
        "fdc4dcef1cb506b4e80e009ee997bc7140f7a0d91dde7c9ce1a9ae049ead6a4f",
    ),
    (
        "dsf_ai_service/curriculum/assets/speech_commands/down/"
        "01b4757a_nohash_0.wav",
        "4e2c363804dd774bdecea802185b43ca474c3cfe74a2b08ed749e4f093cc1fd9",
    ),
)
HELD_OUT_SOURCES = (
    (
        "harness/Hello Guala.mp3",
        "8e36966e9f308a7faef7d024d20d8880aae185467f45eeff9b60edf4b5e711dd",
    ),
    (
        "dsf_ai_service/curriculum/assets/speech_commands/down/"
        "0447d7c1_nohash_2.wav",
        "6dd0ce1ca257fe0d0877fdd539827f2ff3f3a67818e94383904b8c74d6acfda4",
    ),
)
UNRELATED_CHALLENGE_SOURCE = (
    "dsf_ai_service/curriculum/assets/speech_commands/yes/"
    "023808be_nohash_0.wav",
    "1006e4d3d7c06d8dd097e6948994fbea1945fc0a87cf21f4e53c9c302a07174c",
)
TRAINING_DISTRACTORS = (
    (
        "dsf_ai_service/curriculum/assets/speech_commands/go/"
        "022cd682_nohash_0.wav",
        "d5c16343f0a0a56964e982e5d7a5f0232d7bf8e80f0881fbfc9a9435b4679bb7",
    ),
    (
        "dsf_ai_service/curriculum/assets/speech_commands/yes/"
        "004ae714_nohash_0.wav",
        "d19540ed5ca22c50691baf73e2f30159a50992dc653b400cf7a975c3e37d8350",
    ),
)


def _scaled(values: np.ndarray, divisor: int) -> np.ndarray:
    return np.where(
        values >= 0,
        values // divisor,
        -((-values) // divisor),
    )


def _room_noise(
    sample_count: int,
    *,
    source_offset: int = 0,
) -> np.ndarray:
    indices = (
        np.arange(sample_count, dtype=np.int64) + source_offset
    )
    broadband = (
        ((indices * 1_103_515_245 + 12_345) & 65_535) - 32_768
    ) // 96
    hum = np.rint(
        220
        * np.sin(
            2 * np.pi * 60 * indices / PCM_SAMPLE_RATE_HZ
        )
    ).astype(np.int64)
    return (broadband + hum).astype(np.int32)


def _unrelated_room_pcm() -> bytes:
    sample_count = 8 * PCM_SAMPLE_RATE_HZ
    indices = np.arange(sample_count, dtype=np.int64)
    broadband = (
        (((indices + 97_531) * 1_664_525 + 1_013_904_223) & 65_535)
        - 32_768
    ) // 112
    hum = np.rint(
        180
        * np.sin(
            2 * np.pi * 137 * indices / PCM_SAMPLE_RATE_HZ
        )
    ).astype(np.int64)
    values = (broadband + hum).astype(np.int32)
    unrelated_voice = np.frombuffer(
        _checked_cognitive_source(*UNRELATED_CHALLENGE_SOURCE),
        dtype="<i2",
    ).astype(np.int32)
    start = int(1.2 * PCM_SAMPLE_RATE_HZ)
    values[start:start + len(unrelated_voice)] += _scaled(
        unrelated_voice,
        3,
    )
    if np.max(np.abs(values)) > 32_767:
        raise RuntimeError("held-out unrelated room schedule clipped")
    return values.astype("<i2").tobytes()


def _dense_room_pcm() -> tuple[bytes, bytes]:
    held_out_a, held_out_b = (
        np.frombuffer(
            _checked_cognitive_source(path, digest),
            dtype="<i2",
        ).astype(np.int32)
        for path, digest in HELD_OUT_SOURCES
    )
    sample_count = 48 * PCM_SAMPLE_RATE_HZ
    room = _room_noise(sample_count)
    held_out_a_continuous = np.resize(held_out_a, sample_count)
    held_out_b_continuous = np.resize(held_out_b, sample_count)
    dense = (
        room
        + _scaled(held_out_a_continuous, 4)
        + _scaled(held_out_b_continuous, 4)
    )
    if np.max(np.abs(dense)) > 32_767:
        raise RuntimeError("dense auditory room schedule clipped")
    noise_only = _room_noise(8 * PCM_SAMPLE_RATE_HZ)
    return (
        dense.astype("<i2").tobytes(),
        noise_only.astype("<i2").tobytes(),
    )


def _isolated_pcm(source: tuple[object, str]) -> bytes:
    heard = np.frombuffer(
        _checked_cognitive_source(*source),
        dtype="<i2",
    ).astype(np.int32)
    values = np.zeros(8 * PCM_SAMPLE_RATE_HZ, dtype=np.int32)
    start = int(0.8 * PCM_SAMPLE_RATE_HZ)
    if start + len(heard) > len(values):
        raise RuntimeError("isolated auditory contrast exceeds q window")
    values[start:start + len(heard)] = heard
    return values.astype("<i2").tobytes()


def _contextual_pcm(
    source: tuple[object, str],
    *,
    source_divisor: int,
    room_offset: int,
    distractor: tuple[object, str] | None = None,
) -> bytes:
    sample_count = 8 * PCM_SAMPLE_RATE_HZ
    values = _room_noise(
        sample_count,
        source_offset=room_offset,
    )
    heard = np.frombuffer(
        _checked_cognitive_source(*source),
        dtype="<i2",
    ).astype(np.int32)
    start = int(0.8 * PCM_SAMPLE_RATE_HZ)
    values[start:start + len(heard)] += _scaled(
        heard,
        source_divisor,
    )
    if distractor is not None:
        other = np.frombuffer(
            _checked_cognitive_source(*distractor),
            dtype="<i2",
        ).astype(np.int32)
        other_start = int(0.95 * PCM_SAMPLE_RATE_HZ)
        values[other_start:other_start + len(other)] += _scaled(
            other,
            3,
        )
    if np.max(np.abs(values)) > 32_767:
        raise RuntimeError(
            "contextual auditory learning schedule clipped"
        )
    return values.astype("<i2").tobytes()


def _poll_into(
    engine: Guala,
    stream_id: str,
    cursor: int,
    motifs: dict[int, dict[str, object]],
    temporals: dict[int, dict[str, object] | None],
) -> int:
    observed = engine.poll_continuous_auditory_terminals(
        stream_id=stream_id,
        after_sequence=cursor,
    )
    if observed["failures"]:
        raise RuntimeError(
            f"dense auditory terminal failure: {observed['failures']}"
        )
    for value in observed["results"]:
        sequence = value["sequence"]
        motifs[sequence] = value["auditory_motif"]
        temporals[sequence] = value["auditory_temporal_relations"]
    if observed["results"]:
        cursor = max(value["sequence"] for value in observed["results"])
    return cursor


def _run_stream(engine: Guala, pcm: bytes) -> dict[str, object]:
    chunk_bytes = PCM_CHUNK_SAMPLES * 2
    chunks = tuple(
        pcm[offset:offset + chunk_bytes]
        for offset in range(0, len(pcm), chunk_bytes)
    )
    if not chunks or any(len(value) != chunk_bytes for value in chunks):
        raise RuntimeError("dense auditory schedule is not 2s aligned")
    opened = asyncio.run(app_module.auditory_pcm_stream_open())
    stream_id = opened["stream_id"]
    durations = []
    maximum_backlog = 0.0
    end_backlog = 0.0
    motifs: dict[int, dict[str, object]] = {}
    temporals: dict[int, dict[str, object] | None] = {}
    cursor = -1
    try:
        source_clock = time.perf_counter()
        for sequence, chunk in enumerate(chunks):
            arrival = source_clock + sequence * 2.0
            remaining = arrival - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
            started = time.perf_counter()
            _post(
                stream_id=stream_id,
                sequence=sequence,
                sample_count=PCM_CHUNK_SAMPLES,
                pcm=chunk,
            )
            durations.append(time.perf_counter() - started)
            deadline = source_clock + (sequence + 1) * 2.0
            end_backlog = max(0.0, time.perf_counter() - deadline)
            maximum_backlog = max(maximum_backlog, end_backlog)
            cursor = _poll_into(
                engine,
                stream_id,
                cursor,
                motifs,
                temporals,
            )
        engine.wait_for_auditory_terminal_pipeline()
        cursor = _poll_into(
            engine,
            stream_id,
            cursor,
            motifs,
            temporals,
        )
        if (
            set(motifs) != set(range(len(chunks)))
            or set(temporals) != set(range(len(chunks)))
        ):
            raise RuntimeError("dense auditory pipeline lost a result")
        engine.poll_continuous_auditory_terminals(
            stream_id=stream_id,
            after_sequence=len(chunks) - 1,
        )
        engine.close_auditory_pcm_stream(
            stream_id,
            release_terminal=False,
        )
        app_module._auditory_pcm_streams.close(stream_id)
    except BaseException:
        try:
            engine.wait_for_auditory_terminal_pipeline()
        finally:
            raise
    return {
        "backlog_at_end_seconds": end_backlog,
        "maximum_backlog_seconds": maximum_backlog,
        "motifs": motifs,
        "p50_seconds": statistics.median(durations),
        "p95_seconds": sorted(durations)[
            (95 * (len(durations) - 1) + 99) // 100
        ],
        "sequence_count": len(chunks),
        "temporals": temporals,
    }


def _complete_sequences(
    result: dict[str, object],
) -> tuple[int, ...]:
    return tuple(
        sequence
        for sequence, motif in sorted(result["motifs"].items())
        if motif["firing_state"]
        != (
            AuditoryMotifObservationState
            .AWAITING_EXACT_WINDOW_COMPOSITION.value
        )
    )


def _q_evidence(motif: dict[str, object]) -> dict[str, object]:
    spans = motif["activation_spans"]
    return {
        "activation_span_count": len(spans),
        "activation_support_sha256": hashlib.sha256(
            json.dumps(
                spans,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        "authority_receipt_sha256": motif[
            "authority_receipt_sha256"
        ],
        "firing_cell_count": len(motif["firing_motif_neuron_ids"]),
        "source_experience_receipt_sha256": motif[
            "source_experience_receipt_sha256"
        ],
    }


def _summary(result: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in result.items()
        if key not in {"motifs", "temporals"}
    }


def _assembly_summary(
    assembly: dict[str, object],
) -> dict[str, object]:
    relations = assembly["relations"]
    identities = assembly["required_event_identities"]
    return {
        "assembly_id": assembly["assembly_id"],
        "authority_receipt_sha256": assembly[
            "authority_receipt_sha256"
        ],
        "contrast_exposure_receipt_sha256s": assembly[
            "contrast_exposure_receipt_sha256s"
        ],
        "positive_exposure_receipt_sha256s": assembly[
            "positive_exposure_receipt_sha256s"
        ],
        "relation_count": len(relations),
        "relation_set_sha256": hashlib.sha256(
            json.dumps(
                relations,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "required_event_identity_count": len(identities),
        "required_event_identity_set_sha256": hashlib.sha256(
            json.dumps(
                identities,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "schema": assembly["schema"],
    }


def _orphan_commands() -> tuple[str, ...]:
    current = os.getpid()
    excluded = {current}
    ancestor = current
    while ancestor > 1:
        try:
            status = open(
                f"/proc/{ancestor}/status",
                "r",
                encoding="utf-8",
            ).read().splitlines()
        except (FileNotFoundError, PermissionError):
            break
        parent_line = next(
            (
                line for line in status
                if line.startswith("PPid:")
            ),
            None,
        )
        if parent_line is None:
            break
        ancestor = int(parent_line.split(":", 1)[1].strip())
        excluded.add(ancestor)
    matches = []
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit() or int(entry.name) in excluded:
            continue
        try:
            command = open(
                f"/proc/{entry.name}/cmdline",
                "rb",
            ).read().replace(b"\0", b" ").decode(
                "utf-8",
                errors="replace",
            )
        except (FileNotFoundError, PermissionError):
            continue
        if (
            "probe_auditory_q_dense_room.py" in command
            or "guala-auditory-q-owner" in command
            or "guala-exact-field" in command
        ):
            matches.append(command)
    return tuple(sorted(matches))


def main() -> None:
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "0"
    os.environ["WAVE_ATLAS_ENABLED"] = "0"
    os.environ["WAVE_SUMMARY_ENQUEUE_ENABLED"] = "0"
    os.environ["SELF_HEARING_ENABLED"] = "0"
    os.environ["GUALA_EXACT_FIELD_EXECUTOR_REQUIRED"] = "1"
    os.environ["GUALA_CAUSAL_ACTION_KEY"] = (
        "dense-room-q-proof-authority"
    )
    component_sources = {
        "A": COMPONENT_A_SOURCES,
        "B": COMPONENT_B_SOURCES,
    }
    calibration_digests = {
        digest
        for values in component_sources.values()
        for _path, digest in values
    } | {digest for _path, digest in TRAINING_DISTRACTORS}
    held_out_digests = {
        digest for _path, digest in HELD_OUT_SOURCES
    }
    if (
        calibration_digests.intersection(held_out_digests)
        or UNRELATED_CHALLENGE_SOURCE[1] in calibration_digests
        or UNRELATED_CHALLENGE_SOURCE[1] in held_out_digests
        or len(calibration_digests) != 7
        or len(held_out_digests) != 2
    ):
        raise RuntimeError(
            "held-out auditory sources crossed calibration custody"
        )
    clean_pcm = {
        f"{component}_{ordinal}": _isolated_pcm(source)
        for component, sources in component_sources.items()
        for ordinal, source in enumerate(sources, start=1)
    }
    dense, noise_only = _dense_room_pcm()
    learning_pcm = dict(clean_pcm)
    learning_pcm.update({
        "A_noise_1": _contextual_pcm(
            COMPONENT_A_SOURCES[0],
            source_divisor=1,
            room_offset=19_937,
        ),
        "A_noise_2": _contextual_pcm(
            COMPONENT_A_SOURCES[1],
            source_divisor=2,
            room_offset=71_119,
        ),
        "A_overlap": _contextual_pcm(
            COMPONENT_A_SOURCES[0],
            source_divisor=2,
            room_offset=131_071,
            distractor=TRAINING_DISTRACTORS[0],
        ),
        "B_noise_1": _contextual_pcm(
            COMPONENT_B_SOURCES[0],
            source_divisor=1,
            room_offset=262_147,
        ),
        "B_noise_2": _contextual_pcm(
            COMPONENT_B_SOURCES[1],
            source_divisor=2,
            room_offset=524_309,
        ),
        "B_noise_3": _contextual_pcm(
            COMPONENT_B_SOURCES[2],
            source_divisor=2,
            room_offset=786_433,
        ),
        "B_overlap": _contextual_pcm(
            COMPONENT_B_SOURCES[0],
            source_divisor=2,
            room_offset=1_048_583,
            distractor=TRAINING_DISTRACTORS[1],
        ),
        "room_1": noise_only,
        "room_2": _room_noise(
            8 * PCM_SAMPLE_RATE_HZ,
            source_offset=2_097_169,
        ).astype("<i2").tobytes(),
    })
    positive_names = {
        "A": (
            "A_1",
            "A_2",
            "A_noise_1",
            "A_noise_2",
            "A_overlap",
        ),
        "B": (
            "B_1",
            "B_2",
            "B_3",
            "B_noise_1",
            "B_noise_2",
            "B_noise_3",
            "B_overlap",
        ),
    }
    room_names = ("room_1", "room_2")
    if os.environ.get("GUALA_DENSE_PROFILE_ONLY") == "1":
        dense = dense[:8 * PCM_SAMPLE_RATE_HZ * 2]
    unrelated_room = _unrelated_room_pcm()
    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    engine = Guala()
    neutral = engine._auditory_recurrent_motif_owner.status()
    if (
        neutral["motif_neuron_count"] != 0
        or neutral["pending_peak_cell_count"] != 0
    ):
        raise RuntimeError("dense auditory proof did not begin neutral")
    engine.prewarm_auditory_q_process()
    original_advance = engine.advance_continuous_auditory_terminal

    def submit(**values):
        with engine._auditory_transaction_lock:
            joint = engine._auditory_prediction_joint_by_transport.get(
                values["transport"].receipt_sha256
            )
        admission = engine.submit_continuous_auditory_terminal(**values)
        if admission.state != "queued":
            raise RuntimeError(
                "dense auditory terminal pipeline reached capacity"
            )
        return joint, admission

    engine.advance_continuous_auditory_terminal = submit
    app_module._guala = engine
    app_module._is_remote = lambda: False
    app_module._converse_inflight = 0
    app_module._converse_window_started_at = 0.0
    app_module._auditory_pcm_streams = AuditoryPCMStreamRegistry()
    try:
        stabilization_rounds = [{
            name: _summary(_run_stream(engine, pcm))
            for name, pcm in clean_pcm.items()
        }]

        measured_contrasts = {}
        exposure_receipts = {}
        retention_receipts = {}
        for name, pcm in learning_pcm.items():
            result = _run_stream(engine, pcm)
            complete = _complete_sequences(result)
            if complete != (3,):
                raise RuntimeError(
                    f"{name} contrast did not produce one exact q window"
                )
            motif = result["motifs"][3]
            if not motif["activation_spans"]:
                raise RuntimeError(
                    f"{name} contrast produced no local q activations"
                )
            exposure_receipt = motif[
                "source_experience_receipt_sha256"
            ]
            retention = (
                engine.retain_latest_auditory_temporal_exposure(
                    exposure_receipt
                )
            )
            measured_contrasts[name] = result
            exposure_receipts[name] = exposure_receipt
            retention_receipts[name] = retention

        assembly_a = engine.learn_auditory_temporal_acoustic_contrast(
            positive_exposure_receipt_sha256s=tuple(
                exposure_receipts[name]
                for name in positive_names["A"]
            ),
            contrast_exposure_receipt_sha256s=tuple(
                exposure_receipts[name]
                for name in positive_names["B"] + room_names
            ),
        )
        assembly_b = engine.learn_auditory_temporal_acoustic_contrast(
            positive_exposure_receipt_sha256s=tuple(
                exposure_receipts[name]
                for name in positive_names["B"]
            ),
            contrast_exposure_receipt_sha256s=tuple(
                exposure_receipts[name]
                for name in positive_names["A"] + room_names
            ),
        )
        if assembly_a is None or assembly_b is None:
            raise RuntimeError(
                "canonical L6 acoustic contrast formed no contextual "
                "q ensemble"
            )
        assembly_ids = tuple(sorted((
            assembly_a["assembly_id"],
            assembly_b["assembly_id"],
        )))
        if len(set(assembly_ids)) != 2:
            raise RuntimeError(
                "distinct acoustic contrasts collapsed to one assembly"
            )

        stress = _run_stream(engine, dense)
        if stress["backlog_at_end_seconds"] != 0.0:
            raise RuntimeError(
                "held-out dense room ended behind its physical source clock: "
                f"{stress['backlog_at_end_seconds']}"
            )
        complete_windows = _complete_sequences(stress)
        if not complete_windows:
            raise RuntimeError(
                "held-out dense room produced no complete physical q window"
            )
        co_firing = {}
        for sequence in complete_windows:
            firing = stress["temporals"][sequence]
            if firing is None:
                raise RuntimeError(
                    "complete q window lost temporal relation firing"
                )
            co_firing[sequence] = {
                "q_evidence": _q_evidence(
                    stress["motifs"][sequence]
                ),
                "temporal_firing": firing,
            }
            if (
                tuple(firing["complete_assembly_ids"])
                != assembly_ids
                or firing["state"] != "ambiguous"
            ):
                raise RuntimeError(
                    "held-out dense room did not contain both complete "
                    f"contextual q ensembles: {co_firing}"
                )

        room_only = _run_stream(engine, noise_only)
        room_firing = room_only["temporals"][3]
        if (
            room_firing is None
            or room_firing["complete_assembly_ids"]
            or room_firing["state"] != "unknown"
        ):
            raise RuntimeError(
                "room-only replay fired a learned contextual q ensemble"
            )

        held_out_unrelated = _run_stream(engine, unrelated_room)
        unrelated_firing = held_out_unrelated["temporals"][3]
        if (
            unrelated_firing is None
            or unrelated_firing["complete_assembly_ids"]
            or unrelated_firing["state"] != "unknown"
        ):
            raise RuntimeError(
                "source-disjoint unrelated room fired a learned contextual "
                "q ensemble"
            )

        committed = engine._auditory_q_process_committed_state
        if committed is None or committed.temporal_state is None:
            raise RuntimeError(
                "learned temporal state lost committed-state custody"
            )
        report = {
            "acoustic_assemblies": {
                "A": _assembly_summary(assembly_a),
                "B": _assembly_summary(assembly_b),
            },
            "contrast_measurements": {
                name: {
                    **_summary(result),
                    "q_evidence": _q_evidence(result["motifs"][3]),
                    "retention": retention_receipts[name],
                    "temporal_firing_before_learning": (
                        result["temporals"][3]
                    ),
                }
                for name, result in measured_contrasts.items()
            },
            "dense_pcm_sha256": hashlib.sha256(dense).hexdigest(),
            "dense_stress": _summary(stress),
            "full_window_temporal_co_firing": co_firing,
            "held_out_provenance": [
                {
                    "component_ordinal": component,
                    "source_file": source[0],
                    "source_pcm_sha256": source[1],
                    "used_during_learning": False,
                }
                for component, source in zip(
                    ("A", "B"),
                    HELD_OUT_SOURCES,
                    strict=True,
                )
            ],
            "held_out_unrelated": {
                **_summary(held_out_unrelated),
                "pcm_sha256": hashlib.sha256(
                    unrelated_room
                ).hexdigest(),
                "q_evidence": _q_evidence(
                    held_out_unrelated["motifs"][3]
                ),
                "source_file": UNRELATED_CHALLENGE_SOURCE[0],
                "source_pcm_sha256": (
                    UNRELATED_CHALLENGE_SOURCE[1]
                ),
                "temporal_firing": unrelated_firing,
                "used_during_learning": False,
            },
            "noise_only": {
                **_summary(room_only),
                "pcm_sha256": hashlib.sha256(
                    noise_only
                ).hexdigest(),
                "q_evidence": _q_evidence(
                    room_only["motifs"][3]
                ),
                "temporal_firing": room_firing,
            },
            "q_status": engine._auditory_q_process_status,
            "schema": "guala.audit.dense_room_temporal_q.v3",
            "stabilization_rounds": stabilization_rounds,
            "temporal_state_bytes": len(committed.temporal_state),
            "temporal_state_sha256": hashlib.sha256(
                committed.temporal_state
            ).hexdigest(),
        }
    finally:
        engine.advance_continuous_auditory_terminal = original_advance
        engine.shutdown()
        stop_exact_field_executor()
    orphans = _orphan_commands()
    if orphans:
        raise RuntimeError(
            f"dense auditory proof left orphan processes: {orphans}"
        )
    report["orphan_process_count"] = 0
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
