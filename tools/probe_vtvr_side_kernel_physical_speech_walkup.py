"""Progressive physical-speech test for the isolated VTVR side kernel.

This probe is not part of canonical hearing.  It advances one rung at a time
and stops at the first unmet requirement:

1. exact replay of one authenticated physical speech event;
2. recurrence across two source-disjoint speakers saying the same word;
3. rejection of a different word;
4. recurrence of the same recording at the mirrored source location.

The VTVR input has sixty-four simultaneous cochlear vertices: pressure
envelope and cumulative carrier phase for sixteen channels in each physical
ear.  The original PCM remains under the physical renderer's authenticated raw
custody.  Oracle directory names are never passed to the structural relation.
"""

from __future__ import annotations

import hashlib
import io
import json
import wave
import zipfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np

from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    signed_pcm16_samples,
)
from tools.isolated_vtvr_side_kernel_v2 import (
    JointFieldInput,
    SideKernelExperience,
    run_side_kernel,
    structural_relation,
)
from tools.isolated_w1_physical_stereo_path import (
    PhysicalStereoAuditAuthority,
    PhysicalStereoCapture,
)


ARCHIVE_PATH = Path("/tmp/mini_speech_commands.zip")
ARCHIVE_SHA256 = (
    "49650f2341b26d886b46b3f4fb8fed59e30300b17550f1ee4a768b3106cf93a0"
)
ARCHIVE_PREFIX = "mini_speech_commands/"
AUTHORITY = PhysicalStereoAuditAuthority(
    authority_key=b"isolated-vtvr-physical-speech-walkup-v1"
)


@dataclass(frozen=True, slots=True)
class SpeechItem:
    oracle_word: str
    speaker_id: str
    archive_member: str
    pcm_s16le: bytes
    wav_sha256: str


def _archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_item(
    archive: zipfile.ZipFile,
    *,
    word: str,
    excluded_speakers: frozenset[str],
) -> SpeechItem:
    prefix = f"{ARCHIVE_PREFIX}{word}/"
    for member in sorted(
        value
        for value in archive.namelist()
        if value.startswith(prefix) and value.endswith(".wav")
    ):
        filename = member.rsplit("/", 1)[-1]
        if "_nohash_" not in filename:
            continue
        speaker = filename.split("_nohash_", 1)[0]
        if speaker in excluded_speakers:
            continue
        wav_data = archive.read(member)
        with wave.open(io.BytesIO(wav_data), "rb") as source:
            if (
                source.getnchannels() != 1
                or source.getsampwidth() != 2
                or source.getframerate() != REQUIRED_SAMPLE_RATE_HZ
                or source.getnframes() != REQUIRED_SAMPLE_RATE_HZ
                or source.getcomptype() != "NONE"
            ):
                continue
            pcm = source.readframes(source.getnframes())
        return SpeechItem(
            oracle_word=word,
            speaker_id=speaker,
            archive_member=member,
            pcm_s16le=pcm,
            wav_sha256=hashlib.sha256(wav_data).hexdigest(),
        )
    raise RuntimeError(f"no authenticated one-second {word} recording")


def _physical_experience(
    item: SpeechItem,
    *,
    source_ordinal: int,
) -> tuple[PhysicalStereoCapture, SideKernelExperience]:
    capture = AUTHORITY.render(
        (item.pcm_s16le,),
        source_ordinals=(source_ordinal,),
    )
    ears = tuple(
        transduce_auditory_full_field(
            np.asarray(
                signed_pcm16_samples(value),
                dtype=np.float64,
            )
            / 32_768.0,
            sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
        )
        for value in (
            capture.left_pcm_s16le,
            capture.right_pcm_s16le,
        )
    )
    frame_count = min(ear.frame_count for ear in ears)
    if not 2 <= frame_count <= 100:
        raise RuntimeError("physical speech left the bounded observation rung")
    times = tuple(
        Fraction(
            ears[0].channels[0].causal_offsets_ns[index],
            1_000_000_000,
        )
        for index in range(frame_count)
    )
    vertex_ids = tuple(
        f"{ear_name}:pressure:{channel.name}"
        for ear_name in ("left", "right")
        for channel in AUDITORY_CHANNELS
    ) + tuple(
        f"{ear_name}:phase:{channel.name}"
        for ear_name in ("left", "right")
        for channel in AUDITORY_CHANNELS
    )
    vectors = []
    for frame_index in range(frame_count):
        pressure = tuple(
            Fraction.from_float(
                ear.channels[channel_index]
                .pressure_envelope_full_scale[frame_index]
            )
            for ear in ears
            for channel_index in range(len(AUDITORY_CHANNELS))
        )
        phase = tuple(
            Fraction.from_float(
                ear.channels[channel_index]
                .carrier_phase_turns[frame_index]
            )
            for ear in ears
            for channel_index in range(len(AUDITORY_CHANNELS))
        )
        vectors.append(pressure + phase)
    mounted = JointFieldInput.create(
        vertex_ids=vertex_ids,
        groups=(
            tuple(range(0, 32)),
            tuple(range(32, 64)),
        ),
        times=times,
        vectors=vectors,
    )
    return capture, run_side_kernel(mounted)


def _item_payload(item: SpeechItem) -> dict[str, object]:
    return {
        "archive_member": item.archive_member,
        "speaker_id": item.speaker_id,
        "wav_sha256": item.wav_sha256,
    }


def _comparison_payload(
    left_capture: PhysicalStereoCapture,
    left: SideKernelExperience,
    right_capture: PhysicalStereoCapture,
    right: SideKernelExperience,
) -> dict[str, object]:
    return {
        "left_capture_receipt_sha256": (
            left_capture.authority_receipt_sha256
        ),
        "left_structural_receipt_sha256": (
            left.L1.structural_authority_receipt_sha256
        ),
        "right_capture_receipt_sha256": (
            right_capture.authority_receipt_sha256
        ),
        "right_structural_receipt_sha256": (
            right.L1.structural_authority_receipt_sha256
        ),
        "structural_relation": structural_relation(left, right),
    }


def run_walkup() -> dict[str, object]:
    actual_archive_sha256 = _archive_sha256(ARCHIVE_PATH)
    if actual_archive_sha256 != ARCHIVE_SHA256:
        raise RuntimeError("authenticated speech archive receipt changed")
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        first = _read_item(
            archive,
            word="down",
            excluded_speakers=frozenset(),
        )
        second = _read_item(
            archive,
            word="down",
            excluded_speakers=frozenset((first.speaker_id,)),
        )
        different = _read_item(
            archive,
            word="stop",
            excluded_speakers=frozenset(
                (first.speaker_id, second.speaker_id)
            ),
        )

    first_capture, first_experience = _physical_experience(
        first,
        source_ordinal=0,
    )
    replay_capture, replay_experience = _physical_experience(
        first,
        source_ordinal=0,
    )
    replay = _comparison_payload(
        first_capture,
        first_experience,
        replay_capture,
        replay_experience,
    )
    report: dict[str, object] = {
        "archive_sha256": actual_archive_sha256,
        "input_structure": {
            "cochlear_channels_per_ear": len(AUDITORY_CHANNELS),
            "groups": (
                "bilateral pressure envelope",
                "bilateral cumulative carrier phase",
            ),
            "vertex_count": 64,
        },
        "rungs": [{"name": "exact physical speech replay", **replay}],
        "schema": "guala.research.vtvr_physical_speech_walkup.v1",
        "speech_items": {
            "different_word": _item_payload(different),
            "first_same_word": _item_payload(first),
            "second_same_word": _item_payload(second),
        },
    }
    if not replay["structural_relation"]:
        report["first_failed_rung"] = "exact physical speech replay"
        return report

    second_capture, second_experience = _physical_experience(
        second,
        source_ordinal=0,
    )
    recurrence = _comparison_payload(
        first_capture,
        first_experience,
        second_capture,
        second_experience,
    )
    report["rungs"].append({
        "name": "source-disjoint same-word recurrence",
        **recurrence,
    })
    if not recurrence["structural_relation"]:
        report["first_failed_rung"] = (
            "source-disjoint same-word recurrence"
        )
        return report

    different_capture, different_experience = _physical_experience(
        different,
        source_ordinal=0,
    )
    rejection_relation = structural_relation(
        first_experience,
        different_experience,
    )
    report["rungs"].append({
        "name": "different-word rejection",
        **_comparison_payload(
            first_capture,
            first_experience,
            different_capture,
            different_experience,
        ),
        "requirement_passed": not rejection_relation,
    })
    if rejection_relation:
        report["first_failed_rung"] = "different-word rejection"
        return report

    mirrored_capture, mirrored_experience = _physical_experience(
        first,
        source_ordinal=1,
    )
    location = _comparison_payload(
        first_capture,
        first_experience,
        mirrored_capture,
        mirrored_experience,
    )
    report["rungs"].append({
        "name": "same recording across source location",
        **location,
    })
    if not location["structural_relation"]:
        report["first_failed_rung"] = (
            "same recording across source location"
        )
        return report
    report["first_failed_rung"] = None
    return report


if __name__ == "__main__":
    print(json.dumps(run_walkup(), indent=2, sort_keys=True))
