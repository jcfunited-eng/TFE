"""Read-only source--filter identifiability audit for canonical hearing.

This audit maps the quantities required by physical vocal source--filter
separation to the fields actually retained by the canonical cochlear provider
and unchanged L0--L4 mount.  It implements no separator.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from fractions import Fraction
from pathlib import Path

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate import auditory_kernel_mount
from dsf_ai_service.substrate.senses import auditory_full_field_provider


SCHEMA = "guala.audit.auditory_source_filter_mapping.v1"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _magnitude_nonidentifiability_witness() -> dict[str, object]:
    observed = (Fraction(2, 5), Fraction(3, 5))
    first_source = (Fraction(1), Fraction(1))
    first_filter = observed
    second_source = (Fraction(2), Fraction(1, 2))
    second_filter = (
        observed[0] / second_source[0],
        observed[1] / second_source[1],
    )
    first_product = tuple(
        source * transfer
        for source, transfer in zip(
            first_source, first_filter, strict=True
        )
    )
    second_product = tuple(
        source * transfer
        for source, transfer in zip(
            second_source, second_filter, strict=True
        )
    )
    if (
        first_product != observed
        or second_product != observed
        or (first_source, first_filter)
        == (second_source, second_filter)
    ):
        raise RuntimeError("source-filter magnitude witness failed")
    return {
        "observed_band_magnitudes": [_fraction(value) for value in observed],
        "factorization_a": {
            "excitation": [_fraction(value) for value in first_source],
            "transfer": [_fraction(value) for value in first_filter],
        },
        "factorization_b": {
            "excitation": [_fraction(value) for value in second_source],
            "transfer": [_fraction(value) for value in second_filter],
        },
        "products_are_exactly_equal": True,
    }


def _phase_nonidentifiability_witness() -> dict[str, object]:
    observed = (Fraction(1, 7), Fraction(-2, 9))
    first_source = (Fraction(0), Fraction(0))
    first_filter = observed
    second_source = (Fraction(1, 5), Fraction(-1, 6))
    second_filter = tuple(
        value - source
        for value, source in zip(observed, second_source, strict=True)
    )
    first_sum = tuple(
        source + transfer
        for source, transfer in zip(
            first_source, first_filter, strict=True
        )
    )
    second_sum = tuple(
        source + transfer
        for source, transfer in zip(
            second_source, second_filter, strict=True
        )
    )
    if (
        first_sum != observed
        or second_sum != observed
        or (first_source, first_filter)
        == (second_source, second_filter)
    ):
        raise RuntimeError("source-filter phase witness failed")
    return {
        "observed_band_phase_turns": [
            _fraction(value) for value in observed
        ],
        "decomposition_a": {
            "excitation_phase": [
                _fraction(value) for value in first_source
            ],
            "transfer_phase": [
                _fraction(value) for value in first_filter
            ],
        },
        "decomposition_b": {
            "excitation_phase": [
                _fraction(value) for value in second_source
            ],
            "transfer_phase": [
                _fraction(value) for value in second_filter
            ],
        },
        "phase_sums_are_exactly_equal": True,
    }


def run() -> dict[str, object]:
    provider_source = inspect.getsource(auditory_full_field_provider)
    mount_source = inspect.getsource(auditory_kernel_mount)
    mappings = (
        {
            "required_quantity": "native acoustic pressure waveform",
            "current_retention": (
                "available to the provider during transduction but not "
                "retained in the cochlear full-field capture"
            ),
            "mapping_state": "transient_only",
        },
        {
            "required_quantity": (
                "independently observed glottal excitation event train"
            ),
            "current_retention": "absent",
            "mapping_state": "missing",
        },
        {
            "required_quantity": (
                "fundamental-period and harmonic-index relations belonging "
                "to the excitation rather than the filter"
            ),
            "current_retention": (
                "no source-period or harmonic-lattice field; per-band "
                "carrier phase is the output of each gammatone resonator"
            ),
            "mapping_state": "missing",
        },
        {
            "required_quantity": "per-band acoustic response magnitude",
            "current_retention": (
                "10 ms RMS pressure envelope for each of 16 absolute ERB "
                "channels"
            ),
            "mapping_state": "retained_as_source_filter_product",
        },
        {
            "required_quantity": "per-band acoustic response phase motion",
            "current_retention": (
                "cumulative carrier phase and direct phase advance for each "
                "ERB resonator"
            ),
            "mapping_state": "retained_as_source_filter_sum",
        },
        {
            "required_quantity": (
                "vocal-tract transfer magnitude and phase independent of "
                "excitation"
            ),
            "current_retention": "absent",
            "mapping_state": "not_identifiable",
        },
        {
            "required_quantity": (
                "absolute-frequency formant resonance/ridge relations"
            ),
            "current_retention": (
                "absolute ERB centres and widths retained, but no "
                "cross-channel ridge or source-normalized envelope"
            ),
            "mapping_state": "coordinates_present_operator_missing",
        },
        {
            "required_quantity": "temporal articulation trajectories",
            "current_retention": (
                "10 ms causal trajectories and full independent "
                "D/M/R/U/C/P/B fields retained for pressure and phase"
            ),
            "mapping_state": "mixture_trajectory_present",
        },
    )
    payload = {
        "canonical_channel_count": (
            auditory_full_field_provider.COCHLEAR_CHANNEL_COUNT
        ),
        "canonical_code_modified": False,
        "direct_mapping_exists": False,
        "full_explicit_dsf_field_order": list(DSF_FIELD_ORDER),
        "identifiability_proofs": {
            "magnitude": _magnitude_nonidentifiability_witness(),
            "phase": _phase_nonidentifiability_witness(),
        },
        "implementation_performed": False,
        "mapping": list(mappings),
        "operator_presence": {
            "cross_band_relation_in_provider": (
                "cross_band" in provider_source.lower()
            ),
            "formant_operator_in_provider_or_mount": (
                "formant" in (
                    provider_source + mount_source
                ).lower()
            ),
            "glottal_excitation_field_in_provider_or_mount": (
                "glottal" in (
                    provider_source + mount_source
                ).lower()
            ),
            "harmonic_lattice_in_provider_or_mount": (
                "harmonic" in (
                    provider_source + mount_source
                ).lower()
            ),
        },
        "schema": SCHEMA,
        "smallest_missing_physical_authority": (
            "one causally independent vocal-excitation field paired with "
            "the acoustic response; for self-produced speech this can come "
            "from truthful laryngeal/vocal motor embodiment, while room "
            "audio alone does not uniquely expose it"
        ),
        "stop_reason": (
            "for every nonzero per-band q, excitation*q and transfer/q "
            "produce the same observed magnitude, and excitation phase+q "
            "with transfer phase-q produces the same observed phase; "
            "selecting one factorization would add an unapproved model "
            "assumption or heuristic"
        ),
    }
    return payload | {"authority_receipt_sha256": _digest(payload)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    encoded = json.dumps(
        report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
