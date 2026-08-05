"""Isolated pre-L0 stabilized wavelet-Mellin recurrence walk-up.

This probe is not production hearing and does not modify the frozen L0--L4
kernel.  It asks one narrow falsification question: does the smallest
deterministic Irino--Patterson-shaped sensory transform produce an exactly
recurrent representation for two real recordings of the same phrase?

The transform follows the declared physical chain:

1. the existing W1 fourth-order, sixteen-channel cochlear recurrence is run at
   the native 16 kHz sample cadence rather than reduced to 10 ms RMS values;
2. the real part is half-wave rectified into a neural activity pattern (NAP);
3. exact local maxima strobe 35 ms response segments into a stabilized
   auditory image (SAI);
4. each SAI is expressed on the size-shape coordinate h = frequency * delay;
5. a Mellin transform over log channel frequency converts a uniform
   vocal-tract scale shift into phase, and only the Mellin magnitude is kept.

The two positive recordings are transformed independently before their roles
are used.  There is no transcript, learned label, score, nearest relation,
threshold, DTW, ML, or tuned acceptance value.  Equality means bit-exact
equality of every retained float64 Mellin magnitude after two declared
positive-scale quotients.  A failed positive equality stops the walk-up before
contrast recordings or Speech Commands are evaluated.

This is the smallest faithful *shape* of SWMT available from the current W1
cochlea, not a reproduction of the complete Auditory Image Model.  In
particular, W1 uses a gammatone rather than a level-dependent gammachirp, and
the simple exact local-maximum strobe below is not the mature AIM strobe
selection algorithm.  Those losses are part of the result and prevent this
probe from being promoted as production evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    COCHLEAR_ORDER,
    REQUIRED_SAMPLE_RATE_HZ,
    _cochlear_coefficients,
)
from tools.probe_auditory_full_field_discrimination import _decode_pcm


PROBE_SCHEMA = "guala.audit.auditory_stabilized_wavelet_mellin_recurrence.v1"
STROBED_RESPONSE_SECONDS_NUMERATOR = 35
STROBED_RESPONSE_SECONDS_DENOMINATOR = 1_000
STROBED_RESPONSE_SAMPLES = (
    REQUIRED_SAMPLE_RATE_HZ
    * STROBED_RESPONSE_SECONDS_NUMERATOR
    // STROBED_RESPONSE_SECONDS_DENOMINATOR
)
POSITIVE_RECORDINGS = (
    Path("harness/hello guala 1.mp3"),
    Path("harness/hello guala 2.mp3"),
)
CONTRAST_RECORDINGS = (
    Path("docs/Daddy says Hello.mp3"),
    Path("docs/Your Name is Guala.mp3"),
)


@dataclass(frozen=True, slots=True)
class MellinWitness:
    path: str
    pcm_sha256: str
    sample_count: int
    strobe_counts: tuple[int, ...]
    representation_shape: tuple[int, int]
    representation_sha256: str
    representation: np.ndarray


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sample_synchronous_nap(samples: np.ndarray) -> np.ndarray:
    """Run the existing W1 cochlear recurrence without its 10 ms reduction."""
    pole, injection = _cochlear_coefficients()
    state = np.zeros(
        (COCHLEAR_ORDER, COCHLEAR_CHANNEL_COUNT),
        dtype=np.complex128,
    )
    nap = np.empty(
        (COCHLEAR_CHANNEL_COUNT, len(samples)),
        dtype=np.float64,
    )
    for sample_index, sample in enumerate(samples):
        stage = np.full(
            COCHLEAR_CHANNEL_COUNT,
            float(sample),
            dtype=np.complex128,
        )
        for order_index in range(COCHLEAR_ORDER):
            state[order_index] = (
                pole * state[order_index] + injection * stage
            )
            stage = state[order_index]
        nap[:, sample_index] = np.maximum(state[-1].real, 0.0)
    return nap


def _stabilized_auditory_image(
    nap: np.ndarray,
) -> tuple[np.ndarray, tuple[int, ...]]:
    """Strobe every exact positive local maximum and average its response."""
    if nap.shape[1] < STROBED_RESPONSE_SAMPLES + 2:
        raise ValueError("recording is shorter than one strobed response")
    sai = np.zeros(
        (COCHLEAR_CHANNEL_COUNT, STROBED_RESPONSE_SAMPLES),
        dtype=np.float64,
    )
    counts = []
    last_start = nap.shape[1] - STROBED_RESPONSE_SAMPLES
    for channel_index in range(COCHLEAR_CHANNEL_COUNT):
        values = nap[channel_index]
        maxima = np.flatnonzero(
            (values[1:-1] > values[:-2])
            & (values[1:-1] >= values[2:])
            & (values[1:-1] > 0.0)
        ) + 1
        maxima = maxima[maxima <= last_start]
        counts.append(int(len(maxima)))
        if not len(maxima):
            continue
        for start in maxima:
            sai[channel_index] += values[
                start:start + STROBED_RESPONSE_SAMPLES
            ]
        sai[channel_index] /= float(len(maxima))
    if any(count == 0 for count in counts):
        raise RuntimeError("one or more cochlear channels produced no strobe")
    total = float(np.sum(sai))
    if not np.isfinite(total) or total <= 0.0:
        raise RuntimeError("stabilized auditory image has no positive activity")
    # Exact positive-gain quotient.  No acceptance tolerance follows it.
    sai /= total
    return sai, tuple(counts)


def _size_shape_image(sai: np.ndarray) -> np.ndarray:
    """Re-express SAI on h=f*delay using the native sample and channel grid."""
    centres = np.asarray(
        [channel.centre_hz for channel in AUDITORY_CHANNELS],
        dtype=np.float64,
    )
    lowest = float(centres[0])
    h_axis = (
        lowest
        * np.arange(STROBED_RESPONSE_SAMPLES, dtype=np.float64)
        / float(REQUIRED_SAMPLE_RATE_HZ)
    )
    sample_axis = np.arange(STROBED_RESPONSE_SAMPLES, dtype=np.float64)
    result = np.empty_like(sai)
    for channel_index, centre in enumerate(centres):
        delay_samples = (
            h_axis * float(REQUIRED_SAMPLE_RATE_HZ) / float(centre)
        )
        result[channel_index] = np.interp(
            delay_samples,
            sample_axis,
            sai[channel_index],
        )
    return result


def _mellin_magnitude(ssi: np.ndarray) -> np.ndarray:
    """Integrate SSI against complex sinusoids on log channel frequency."""
    centres = np.asarray(
        [channel.centre_hz for channel in AUDITORY_CHANNELS],
        dtype=np.float64,
    )
    log_centres = np.log(centres)
    log_span = float(log_centres[-1] - log_centres[0])
    modes = np.arange(COCHLEAR_CHANNEL_COUNT, dtype=np.float64)
    kernel = np.exp(
        -2.0j
        * np.pi
        * modes[:, None]
        * (log_centres[None, :] - log_centres[0])
        / log_span
    )
    # Trapezoidal quadrature weights in d(log f).
    weights = np.empty(COCHLEAR_CHANNEL_COUNT, dtype=np.float64)
    weights[0] = (log_centres[1] - log_centres[0]) / 2.0
    weights[-1] = (log_centres[-1] - log_centres[-2]) / 2.0
    weights[1:-1] = (
        log_centres[2:] - log_centres[:-2]
    ) / 2.0
    transformed = kernel @ (ssi * weights[:, None])
    magnitude = np.abs(transformed)
    total = float(np.sum(magnitude))
    if not np.isfinite(total) or total <= 0.0:
        raise RuntimeError("Mellin image has no positive activity")
    # Second positive-gain quotient removes integration-magnitude scale.
    magnitude /= total
    return np.ascontiguousarray(magnitude, dtype=np.float64)


def _witness(path: Path) -> MellinWitness:
    pcm = _decode_pcm(path)
    samples = (
        np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32768.0
    )
    nap = _sample_synchronous_nap(samples)
    sai, counts = _stabilized_auditory_image(nap)
    representation = _mellin_magnitude(_size_shape_image(sai))
    payload = {
        "dtype": representation.dtype.str,
        "shape": list(representation.shape),
        "values_hex": [value.hex() for value in representation.flat],
    }
    return MellinWitness(
        path=str(path),
        pcm_sha256=hashlib.sha256(pcm).hexdigest(),
        sample_count=len(samples),
        strobe_counts=counts,
        representation_shape=representation.shape,
        representation_sha256=hashlib.sha256(
            _canonical(payload)
        ).hexdigest(),
        representation=representation,
    )


def _public_witness(value: MellinWitness) -> dict[str, object]:
    return {
        "path": value.path,
        "pcm_sha256": value.pcm_sha256,
        "sample_count": value.sample_count,
        "strobe_counts": list(value.strobe_counts),
        "representation_shape": list(value.representation_shape),
        "representation_sha256": value.representation_sha256,
    }


def main() -> None:
    first = _witness(POSITIVE_RECORDINGS[0])
    repeat = _witness(POSITIVE_RECORDINGS[0])
    self_exact = np.array_equal(
        first.representation,
        repeat.representation,
    )
    second = _witness(POSITIVE_RECORDINGS[1])
    positive_exact = np.array_equal(
        first.representation,
        second.representation,
    )
    unequal_coordinates = int(np.count_nonzero(
        first.representation != second.representation
    ))
    report: dict[str, object] = {
        "schema": PROBE_SCHEMA,
        "production_changed": False,
        "l0_l4_changed": False,
        "input_roles_entered_transform": False,
        "constants": {
            "sample_rate_hz": REQUIRED_SAMPLE_RATE_HZ,
            "cochlear_channel_count": COCHLEAR_CHANNEL_COUNT,
            "cochlear_order": COCHLEAR_ORDER,
            "strobe_response_milliseconds": (
                STROBED_RESPONSE_SECONDS_NUMERATOR
            ),
            "strobe_response_samples": STROBED_RESPONSE_SAMPLES,
            "frequency_bounds_hz": [
                AUDITORY_CHANNELS[0].centre_hz,
                AUDITORY_CHANNELS[-1].centre_hz,
            ],
            "mellin_mode_count": COCHLEAR_CHANNEL_COUNT,
        },
        "declared_quotients": [
            "mean_over_exact_local_maximum_strobes_per_channel",
            "whole_sai_positive_gain",
            "mellin_magnitude_discards_log_frequency_translation_phase",
            "whole_mellin_image_positive_gain",
        ],
        "self_recurrence_exact": self_exact,
        "same_phrase_cross_recording_exact": positive_exact,
        "same_phrase_unequal_coordinate_count": unequal_coordinates,
        "same_phrase_coordinate_count": int(first.representation.size),
        "first": _public_witness(first),
        "second": _public_witness(second),
        "stopped_on_first_fail": not positive_exact,
        "contrasts_evaluated": False,
        "speech_commands_evaluated": False,
    }
    if not self_exact:
        report["decision"] = "invalid_nondeterministic_probe"
    elif not positive_exact:
        report["decision"] = "falsified_at_real_same_phrase_recurrence"
    else:
        contrasts = tuple(_witness(path) for path in CONTRAST_RECORDINGS)
        report["contrasts_evaluated"] = True
        report["contrasts"] = [
            {
                **_public_witness(value),
                "exactly_equal_to_positive": np.array_equal(
                    first.representation,
                    value.representation,
                ),
            }
            for value in contrasts
        ]
        report["decision"] = (
            "advance_to_source_disjoint_corpus"
            if not any(
                np.array_equal(
                    first.representation,
                    value.representation,
                )
                for value in contrasts
            )
            else "falsified_by_real_contrast"
        )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
