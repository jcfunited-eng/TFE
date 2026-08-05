"""Receipt-only custody for one fresh generated self-articulatory occurrence.

This authority closes four already-complete physical authorities:

* one exact articulatory synthesis,
* its freshly committed generated emission,
* the resulting binaural W1 self-acoustic mount, and
* the single settled-experience custody for that same occurrence.

The resulting receipt commits to every explicit D/M/R/U/C/P/B tuple retained
by settled-experience custody.  The tuple digest is only an integrity
commitment; it is never a reduced field used for recognition or decision
authority.  No waveform, PCM exemplar, bridge, label, transcript, score,
target, THING identity, or response choice is retained or accepted.

The authority is deliberately stateless.  A later consequence owner may
authenticate the receipt after cold restart with the same authority key and
profile, while the authoritative physical objects remain under their source
owners.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryGeneratedEmission,
    ArticulatorySelfVocalMotorOwner,
    ArticulatorySynthesis,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
    SettledExperienceSourceKind,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticMount,
    W1SelfAcousticPropagationAuthority,
)


PROFILE_SCHEMA = (
    "guala.fresh_articulatory_self_acoustic_custody.profile.v1"
)
RECEIPT_SCHEMA = (
    "guala.fresh_articulatory_self_acoustic_custody.receipt.v1"
)
FULL_DSF_CUSTODY_SCHEMA = (
    "guala.fresh_articulatory_self_acoustic_custody.full_dsf.v1"
)
FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID = (
    "fresh-articulatory-self-acoustic-custody"
)

_RECEIPT_DOMAIN = (
    b"guala-fresh-articulatory-self-acoustic-custody-receipt-v1\0"
)
_REQUIRED_OBSERVED_SENSES = ("body", "sight", "sound", "touch")
_HEX = frozenset("0123456789abcdef")
_MAX_PROFILE_ID_BYTES = 256
_MAX_CONFIGURED_FULL_FIELD_TUPLES = 4_000_000
_MAX_CONFIGURED_RECEIPT_BYTES = 1 * 1024 * 1024


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError(
            "fresh articulatory custody authority key must be bytes or text"
        )
    if not 32 <= len(result) <= 4_096:
        raise ValueError(
            "fresh articulatory custody authority key boundary changed"
        )
    return result


def _identifier(value: object, name: str, *, max_bytes: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > max_bytes
    ):
        raise ValueError(f"{name} is outside its exact identifier boundary")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _capacity(
    value: object,
    name: str,
    *,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= maximum
    ):
        raise ValueError(f"{name} is outside its explicit capacity")
    return value


def _fraction_text(value: object, name: str) -> str:
    if not isinstance(value, Fraction):
        raise ValueError(f"{name} is not an exact fraction")
    return f"{value.numerator}/{value.denominator}"


def _sign(
    key: bytes,
    domain: bytes,
    payload: Mapping[str, object],
) -> str:
    return hmac.new(
        key,
        domain + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class FreshArticulatorySelfAcousticCustodyProfile:
    profile_id: str
    max_full_field_tuples: int
    max_receipt_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_full_field_tuples: int,
        max_receipt_bytes: int,
    ) -> "FreshArticulatorySelfAcousticCustodyProfile":
        provisional = cls(
            profile_id=_identifier(
                profile_id,
                "fresh articulatory custody profile",
                max_bytes=_MAX_PROFILE_ID_BYTES,
            ),
            max_full_field_tuples=_capacity(
                max_full_field_tuples,
                "fresh articulatory full-field tuple capacity",
                maximum=_MAX_CONFIGURED_FULL_FIELD_TUPLES,
            ),
            max_receipt_bytes=_capacity(
                max_receipt_bytes,
                "fresh articulatory receipt byte capacity",
                maximum=_MAX_CONFIGURED_RECEIPT_BYTES,
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_full_field_tuples=(
                provisional.max_full_field_tuples
            ),
            max_receipt_bytes=provisional.max_receipt_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_full_field_tuples": self.max_full_field_tuples,
            "max_receipt_bytes": self.max_receipt_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _identifier(
            self.profile_id,
            "fresh articulatory custody profile",
            max_bytes=_MAX_PROFILE_ID_BYTES,
        )
        _capacity(
            self.max_full_field_tuples,
            "fresh articulatory full-field tuple capacity",
            maximum=_MAX_CONFIGURED_FULL_FIELD_TUPLES,
        )
        _capacity(
            self.max_receipt_bytes,
            "fresh articulatory receipt byte capacity",
            maximum=_MAX_CONFIGURED_RECEIPT_BYTES,
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError(
                "fresh articulatory custody profile authority changed"
            )

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class FreshArticulatorySelfAcousticCustodyReceipt:
    source_occurrence_id: str
    parent_settled_custody_receipt_sha256: str
    settled_custody_capability_receipt_sha256: str
    program_id: str
    articulatory_synthesis_receipt_sha256: str
    actuator_full_field_receipt_sha256: str
    generated_emission_receipt_sha256: str
    world_execution_receipt_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    self_acoustic_mount_receipt_sha256: str
    acoustic_settlement_receipt_sha256: str
    binaural_l5_receipt_sha256: str
    binaural_receptor_receipt_sha256: str
    prelearning_firing_receipt_sha256: str
    acoustic_observation_receipt_sha256: str
    observed_senses: tuple[str, ...]
    full_dsf_tuple_counts: tuple[tuple[str, int], ...]
    full_dsf_tuple_count: int
    full_dsf_custody_sha256: str
    profile_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "acoustic_observation_receipt_sha256": (
                self.acoustic_observation_receipt_sha256
            ),
            "acoustic_settlement_receipt_sha256": (
                self.acoustic_settlement_receipt_sha256
            ),
            "actuator_full_field_receipt_sha256": (
                self.actuator_full_field_receipt_sha256
            ),
            "articulatory_synthesis_receipt_sha256": (
                self.articulatory_synthesis_receipt_sha256
            ),
            "binaural_l5_receipt_sha256": (
                self.binaural_l5_receipt_sha256
            ),
            "binaural_receptor_receipt_sha256": (
                self.binaural_receptor_receipt_sha256
            ),
            "full_dsf_custody_sha256": (
                self.full_dsf_custody_sha256
            ),
            "full_dsf_tuple_count": self.full_dsf_tuple_count,
            "full_dsf_tuple_counts": [
                [sense, count]
                for sense, count in self.full_dsf_tuple_counts
            ],
            "generated_emission_receipt_sha256": (
                self.generated_emission_receipt_sha256
            ),
            "observed_senses": list(self.observed_senses),
            "parent_settled_custody_receipt_sha256": (
                self.parent_settled_custody_receipt_sha256
            ),
            "prelearning_firing_receipt_sha256": (
                self.prelearning_firing_receipt_sha256
            ),
            "profile_receipt_sha256": self.profile_receipt_sha256,
            "program_id": self.program_id,
            "schema": RECEIPT_SCHEMA,
            "self_acoustic_mount_receipt_sha256": (
                self.self_acoustic_mount_receipt_sha256
            ),
            "settled_custody_capability_receipt_sha256": (
                self.settled_custody_capability_receipt_sha256
            ),
            "source_occurrence_id": self.source_occurrence_id,
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


def fresh_articulatory_receipt_from_record(
    raw: object,
) -> FreshArticulatorySelfAcousticCustodyReceipt:
    """Restore one typed receipt record without granting it authority."""

    if not isinstance(raw, dict):
        raise ValueError(
            "fresh articulatory custody record changed"
        )
    expected = {
        "acoustic_observation_receipt_sha256",
        "acoustic_settlement_receipt_sha256",
        "actuator_full_field_receipt_sha256",
        "articulatory_synthesis_receipt_sha256",
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "binaural_l5_receipt_sha256",
        "binaural_receptor_receipt_sha256",
        "full_dsf_custody_sha256",
        "full_dsf_tuple_count",
        "full_dsf_tuple_counts",
        "generated_emission_receipt_sha256",
        "observed_senses",
        "parent_settled_custody_receipt_sha256",
        "prelearning_firing_receipt_sha256",
        "profile_receipt_sha256",
        "program_id",
        "schema",
        "self_acoustic_mount_receipt_sha256",
        "settled_custody_capability_receipt_sha256",
        "source_occurrence_id",
        "world_after_receipt_sha256",
        "world_before_receipt_sha256",
        "world_execution_receipt_sha256",
    }
    if set(raw) != expected or raw.get("schema") != RECEIPT_SCHEMA:
        raise ValueError(
            "fresh articulatory custody record schema changed"
        )
    observed = raw["observed_senses"]
    counts = raw["full_dsf_tuple_counts"]
    if (
        not isinstance(observed, list)
        or not isinstance(counts, list)
        or any(
            not isinstance(value, list) or len(value) != 2
            for value in counts
        )
    ):
        raise ValueError(
            "fresh articulatory custody record extent changed"
        )
    return FreshArticulatorySelfAcousticCustodyReceipt(
        source_occurrence_id=raw["source_occurrence_id"],
        parent_settled_custody_receipt_sha256=(
            raw["parent_settled_custody_receipt_sha256"]
        ),
        settled_custody_capability_receipt_sha256=(
            raw["settled_custody_capability_receipt_sha256"]
        ),
        program_id=raw["program_id"],
        articulatory_synthesis_receipt_sha256=(
            raw["articulatory_synthesis_receipt_sha256"]
        ),
        actuator_full_field_receipt_sha256=(
            raw["actuator_full_field_receipt_sha256"]
        ),
        generated_emission_receipt_sha256=(
            raw["generated_emission_receipt_sha256"]
        ),
        world_execution_receipt_sha256=(
            raw["world_execution_receipt_sha256"]
        ),
        world_before_receipt_sha256=(
            raw["world_before_receipt_sha256"]
        ),
        world_after_receipt_sha256=(
            raw["world_after_receipt_sha256"]
        ),
        self_acoustic_mount_receipt_sha256=(
            raw["self_acoustic_mount_receipt_sha256"]
        ),
        acoustic_settlement_receipt_sha256=(
            raw["acoustic_settlement_receipt_sha256"]
        ),
        binaural_l5_receipt_sha256=(
            raw["binaural_l5_receipt_sha256"]
        ),
        binaural_receptor_receipt_sha256=(
            raw["binaural_receptor_receipt_sha256"]
        ),
        prelearning_firing_receipt_sha256=(
            raw["prelearning_firing_receipt_sha256"]
        ),
        acoustic_observation_receipt_sha256=(
            raw["acoustic_observation_receipt_sha256"]
        ),
        observed_senses=tuple(observed),
        full_dsf_tuple_counts=tuple(
            (value[0], value[1]) for value in counts
        ),
        full_dsf_tuple_count=raw["full_dsf_tuple_count"],
        full_dsf_custody_sha256=raw["full_dsf_custody_sha256"],
        profile_receipt_sha256=raw["profile_receipt_sha256"],
        authority_hmac_sha256=raw["authority_hmac_sha256"],
        authority_receipt_sha256=raw["authority_receipt_sha256"],
    )


def _full_dsf_custody(
    settlement: CausalExperienceSettlement,
) -> tuple[
    tuple[str, ...],
    tuple[tuple[str, int], ...],
    int,
    str,
]:
    if not isinstance(settlement, CausalExperienceSettlement):
        raise TypeError(
            "fresh articulatory custody requires a causal settlement"
        )
    settlement.verify()
    observed = tuple(sorted(
        interpretation.sense
        for interpretation in settlement.interpretations
        if interpretation.state == "observed"
    ))
    if observed != _REQUIRED_OBSERVED_SENSES:
        raise ValueError(
            "fresh articulatory custody requires exactly observed "
            "BODY/SIGHT/SOUND/TOUCH"
        )

    records: list[dict[str, object]] = []
    counts: list[tuple[str, int]] = []
    total = 0
    by_sense = {
        interpretation.sense: interpretation
        for interpretation in settlement.interpretations
    }
    for sense_name in _REQUIRED_OBSERVED_SENSES:
        interpretation = by_sense[sense_name]
        if not interpretation.substreams:
            raise ValueError(
                f"fresh articulatory {sense_name} custody has no substream"
            )
        sense_count = 0
        substreams = []
        for substream in interpretation.substreams:
            if not substream.field_tuples:
                raise ValueError(
                    "fresh articulatory observed substream has no DSF tuple"
                )
            tuples = []
            for field_tuple in substream.field_tuples:
                names = tuple(
                    name for name, _value in field_tuple.fields
                )
                if names != DSF_FIELD_ORDER:
                    raise ValueError(
                        "fresh articulatory custody lost explicit "
                        "D/M/R/U/C/P/B order"
                    )
                fields = [
                    [
                        name,
                        _fraction_text(
                            value,
                            f"fresh articulatory {name}",
                        ),
                    ]
                    for name, value in field_tuple.fields
                ]
                tuples.append({
                    "authority_receipt_sha256": (
                        field_tuple.authority_receipt_sha256
                    ),
                    "fields": fields,
                    "source_index_end": field_tuple.source_index_end,
                    "source_index_start": (
                        field_tuple.source_index_start
                    ),
                    "source_l0_l4_trace_receipt_sha256": (
                        field_tuple
                        .source_l0_l4_trace_receipt_sha256
                    ),
                    "tuple_index": field_tuple.tuple_index,
                })
                sense_count += 1
            substreams.append({
                "coordinates": [
                    list(value) for value in substream.coordinates
                ],
                "field_tuples": tuples,
                "kernel_basin_receipt_sha256": (
                    substream.kernel_basin_receipt_sha256
                ),
                "physical_quantity": substream.physical_quantity,
                "physical_unit": substream.physical_unit,
                "profile_receipt_sha256": (
                    substream.profile_receipt_sha256
                ),
                "sensor_id": substream.sensor_id,
                "source_evidence_stream_receipt_sha256": (
                    substream.source_evidence_stream_receipt_sha256
                ),
                "source_sample_commitment_sha256": (
                    substream.source_sample_commitment_sha256
                ),
                "source_sample_count": substream.source_sample_count,
                "source_signal_commitment_sha256": (
                    substream.source_signal_commitment_sha256
                ),
                "substream_id": substream.substream_id,
                "topology_index": substream.topology_index,
            })
        if sense_count <= 0:
            raise ValueError(
                f"fresh articulatory {sense_name} custody has no DSF tuple"
            )
        counts.append((sense_name, sense_count))
        total += sense_count
        records.append({
            "boundary_receipt_sha256": (
                interpretation.boundary_receipt_sha256
            ),
            "relation": interpretation.relation,
            "sense": sense_name,
            "state": interpretation.state,
            "structural_fingerprint": (
                interpretation.structural_fingerprint
            ),
            "substreams": substreams,
            "topology_receipt_sha256": (
                interpretation.topology_receipt_sha256
            ),
        })

    commitment = _digest({
        "causal_settlement_receipt_sha256": (
            settlement.authority_receipt_sha256
        ),
        "records": records,
        "schema": FULL_DSF_CUSTODY_SCHEMA,
    })
    return observed, tuple(counts), total, commitment


class FreshArticulatorySelfAcousticCustodyAuthority:
    """Seal fresh generated self-hearing without retaining its waveform."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: FreshArticulatorySelfAcousticCustodyProfile,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        world_authority: EmbodimentWorldAuthority,
        acoustic_authority: W1SelfAcousticPropagationAuthority,
    ) -> None:
        if not isinstance(
            profile,
            FreshArticulatorySelfAcousticCustodyProfile,
        ):
            raise TypeError(
                "fresh articulatory custody requires its profile"
            )
        profile.verify()
        if not isinstance(
            articulatory_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "fresh articulatory custody requires its motor authority"
            )
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "fresh articulatory custody requires W1 world authority"
            )
        if not isinstance(
            acoustic_authority,
            W1SelfAcousticPropagationAuthority,
        ):
            raise TypeError(
                "fresh articulatory custody requires self-acoustic authority"
            )
        root = hashlib.sha256(_key(authority_key)).digest()
        self._receipt_key = hashlib.sha256(
            _RECEIPT_DOMAIN + root
        ).digest()
        self._profile = profile
        self._articulatory = articulatory_owner
        self._world = world_authority
        self._acoustic = acoustic_authority

    @property
    def profile(
        self,
    ) -> FreshArticulatorySelfAcousticCustodyProfile:
        return self._profile

    def owns_dependencies(
        self,
        *,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        world_authority: EmbodimentWorldAuthority,
    ) -> bool:
        """Report exact in-process ownership of the source authorities."""

        return (
            articulatory_owner is self._articulatory
            and world_authority is self._world
        )

    def verify_dependency_ownership(
        self,
        *,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        """Reject crossed source authorities before custody is consumed."""

        if not self.owns_dependencies(
            articulatory_owner=articulatory_owner,
            world_authority=world_authority,
        ):
            raise ValueError(
                "fresh articulatory custody dependencies changed owners"
            )

    def verify_world_ownership(
        self,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        """Reject a crossed W1 world without exposing source internals."""

        if world_authority is not self._world:
            raise ValueError(
                "fresh articulatory custody world changed owners"
            )

    def _verify_receipt_boundary(
        self,
        receipt: FreshArticulatorySelfAcousticCustodyReceipt,
    ) -> None:
        if not isinstance(
            receipt,
            FreshArticulatorySelfAcousticCustodyReceipt,
        ):
            raise TypeError(
                "fresh articulatory custody receipt is not typed"
            )
        for value, name in (
            (receipt.source_occurrence_id, "source occurrence"),
            (
                receipt.parent_settled_custody_receipt_sha256,
                "parent settled custody",
            ),
            (
                receipt.settled_custody_capability_receipt_sha256,
                "settled custody capability",
            ),
            (receipt.program_id, "articulatory program"),
            (
                receipt.articulatory_synthesis_receipt_sha256,
                "articulatory synthesis",
            ),
            (
                receipt.actuator_full_field_receipt_sha256,
                "actuator full field",
            ),
            (
                receipt.generated_emission_receipt_sha256,
                "generated emission",
            ),
            (receipt.world_execution_receipt_sha256, "world execution"),
            (receipt.world_before_receipt_sha256, "world before"),
            (receipt.world_after_receipt_sha256, "world after"),
            (
                receipt.self_acoustic_mount_receipt_sha256,
                "self-acoustic mount",
            ),
            (
                receipt.acoustic_settlement_receipt_sha256,
                "acoustic settlement",
            ),
            (receipt.binaural_l5_receipt_sha256, "binaural L5"),
            (
                receipt.binaural_receptor_receipt_sha256,
                "binaural receptor",
            ),
            (
                receipt.prelearning_firing_receipt_sha256,
                "prelearning firing",
            ),
            (
                receipt.acoustic_observation_receipt_sha256,
                "acoustic observation",
            ),
            (receipt.full_dsf_custody_sha256, "full DSF custody"),
            (receipt.profile_receipt_sha256, "custody profile"),
            (receipt.authority_hmac_sha256, "custody HMAC"),
            (receipt.authority_receipt_sha256, "custody authority"),
        ):
            _sha256(value, f"fresh articulatory {name}")
        if (
            receipt.profile_receipt_sha256
            != self._profile.authority_receipt_sha256
            or receipt.observed_senses != _REQUIRED_OBSERVED_SENSES
            or receipt.full_dsf_tuple_counts
            != tuple(sorted(receipt.full_dsf_tuple_counts))
            or tuple(
                sense
                for sense, _count in receipt.full_dsf_tuple_counts
            )
            != _REQUIRED_OBSERVED_SENSES
            or any(
                isinstance(count, bool)
                or not isinstance(count, int)
                or count <= 0
                for _sense, count in receipt.full_dsf_tuple_counts
            )
            or isinstance(receipt.full_dsf_tuple_count, bool)
            or not isinstance(receipt.full_dsf_tuple_count, int)
            or receipt.full_dsf_tuple_count
            != sum(
                count
                for _sense, count in receipt.full_dsf_tuple_counts
            )
            or receipt.full_dsf_tuple_count
            > self._profile.max_full_field_tuples
        ):
            raise ValueError(
                "fresh articulatory custody receipt boundary changed"
            )
        signature = _sign(
            self._receipt_key,
            _RECEIPT_DOMAIN,
            receipt.payload(),
        )
        if (
            not hmac.compare_digest(
                signature,
                receipt.authority_hmac_sha256,
            )
            or receipt.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": receipt.payload(),
            })
            or len(_canonical(receipt.record()))
            > self._profile.max_receipt_bytes
        ):
            raise ValueError(
                "fresh articulatory custody receipt authority changed"
            )

    def verify_receipt(
        self,
        receipt: FreshArticulatorySelfAcousticCustodyReceipt,
    ) -> None:
        """Authenticate one compact receipt without source reconstruction."""

        self._verify_receipt_boundary(receipt)

    def receipt_from_record(
        self,
        raw: object,
    ) -> FreshArticulatorySelfAcousticCustodyReceipt:
        """Restore and authenticate one canonical receipt record."""

        receipt = fresh_articulatory_receipt_from_record(raw)
        self.verify_receipt(receipt)
        if receipt.record() != raw:
            raise ValueError(
                "fresh articulatory custody record is noncanonical"
            )
        return receipt

    def _source_payload(
        self,
        *,
        synthesis: ArticulatorySynthesis,
        emission: ArticulatoryGeneratedEmission,
        acoustic_mount: W1SelfAcousticMount,
        settled_custody_authority: SettledExperienceCustodyAuthority,
        settled_custody_capability: (
            SettledExperienceConsumerCapability
        ),
    ) -> dict[str, object]:
        if not isinstance(synthesis, ArticulatorySynthesis):
            raise TypeError(
                "fresh articulatory custody synthesis is not typed"
            )
        if not isinstance(emission, ArticulatoryGeneratedEmission):
            raise TypeError(
                "fresh articulatory custody emission is not typed"
            )
        if not isinstance(acoustic_mount, W1SelfAcousticMount):
            raise TypeError(
                "fresh articulatory custody acoustic mount is not typed"
            )
        if not isinstance(
            settled_custody_authority,
            SettledExperienceCustodyAuthority,
        ):
            raise TypeError(
                "fresh articulatory custody requires settled authority"
            )
        if (
            not isinstance(
                settled_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or settled_custody_capability.consumer_id
            != FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID
        ):
            raise ValueError(
                "fresh articulatory custody requires its child capability"
            )

        self._articulatory.verify_synthesis(synthesis)
        if emission.synthesis is not synthesis:
            raise ValueError(
                "fresh articulatory custody changed synthesis occurrence"
            )
        self._articulatory.verify_generated_emission(
            emission,
            world_authority=self._world,
        )
        self._acoustic.verify_mount(acoustic_mount)
        view = settled_custody_authority.open_child(
            settled_custody_capability
        )
        settled = settled_custody_authority.custody
        if settled is None:
            raise RuntimeError(
                "fresh articulatory settled custody is unavailable"
            )

        execution = emission.execution_receipt
        emission_receipt = emission.emission_receipt
        mount_receipt = acoustic_mount.receipt
        synthesis_receipt = synthesis.receipt
        if (
            emission_receipt.program_id != synthesis.program.program_id
            or mount_receipt.motor_id != synthesis.program.program_id
            or emission_receipt.synthesis_receipt_sha256
            != synthesis_receipt.authority_receipt_sha256
            or mount_receipt.self_vocal_emission_receipt_sha256
            != emission_receipt.authority_receipt_sha256
            or emission_receipt.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
            or mount_receipt.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
            or emission_receipt.world_before_receipt_sha256
            != execution.before.authority_receipt_sha256
            or mount_receipt.world_before_receipt_sha256
            != execution.before.authority_receipt_sha256
            or emission_receipt.world_after_receipt_sha256
            != execution.after.authority_receipt_sha256
            or mount_receipt.world_after_receipt_sha256
            != execution.after.authority_receipt_sha256
            or mount_receipt.source_time_start
            != synthesis_receipt.source_time_start
            or mount_receipt.source_time_end
            != synthesis_receipt.source_time_end
        ):
            raise ValueError(
                "fresh articulatory synthesis, emission, and hearing "
                "crossed receipt authority"
            )

        if (
            view.source_kind
            is not SettledExperienceSourceKind.SELF_ACOUSTIC
            or view.source_occurrence_id
            != settled.source_occurrence_id
            or view.parent_custody_receipt_sha256
            != settled.authority_receipt_sha256
            or settled_custody_capability.source_occurrence_id
            != settled.source_occurrence_id
            or settled_custody_capability
            .parent_custody_receipt_sha256
            != settled.authority_receipt_sha256
            or view.world_execution != execution
            or view.world_observation != execution.after
            or view.self_acoustic_receipt != mount_receipt
            or view.causal_settlement
            != acoustic_mount.causal_settlement
            or view.binaural_auditory_l5
            != acoustic_mount.binaural_l5
            or view.binaural_receptor_settlement
            != acoustic_mount.receptor_settlement
            or view.self_acoustic_prelearning_firing
            != acoustic_mount.prelearning_firing
            or view.self_acoustic_observation
            != acoustic_mount.observation
            or view.occurrence_counter.source_occurrence_id
            != settled.source_occurrence_id
            or view.occurrence_counter.source_transduction_lineage_count
            != 1
            or view.occurrence_counter.full_field_build_lineage_count
            != 1
            or view.occurrence_counter.causal_settlement_lineage_count
            != 1
            or view.occurrence_counter.custody_count != 1
        ):
            raise ValueError(
                "fresh articulatory occurrence crossed settled custody"
            )

        (
            observed_senses,
            tuple_counts,
            tuple_count,
            full_dsf_custody_sha256,
        ) = _full_dsf_custody(view.causal_settlement)
        if tuple_count > self._profile.max_full_field_tuples:
            raise RuntimeError(
                "fresh articulatory full-field tuple capacity exhausted"
            )
        return {
            "acoustic_observation_receipt_sha256": (
                acoustic_mount.observation.authority_receipt_sha256
            ),
            "acoustic_settlement_receipt_sha256": (
                acoustic_mount.causal_settlement
                .authority_receipt_sha256
            ),
            "actuator_full_field_receipt_sha256": (
                synthesis.actuator_full_field_assembly
                .authority_receipt_sha256
            ),
            "articulatory_synthesis_receipt_sha256": (
                synthesis_receipt.authority_receipt_sha256
            ),
            "binaural_l5_receipt_sha256": (
                acoustic_mount.binaural_l5.authority_receipt_sha256
            ),
            "binaural_receptor_receipt_sha256": (
                acoustic_mount.receptor_settlement
                .authority_receipt_sha256
            ),
            "full_dsf_custody_sha256": full_dsf_custody_sha256,
            "full_dsf_tuple_count": tuple_count,
            "full_dsf_tuple_counts": tuple_counts,
            "generated_emission_receipt_sha256": (
                emission_receipt.authority_receipt_sha256
            ),
            "observed_senses": observed_senses,
            "parent_settled_custody_receipt_sha256": (
                settled.authority_receipt_sha256
            ),
            "prelearning_firing_receipt_sha256": (
                acoustic_mount.prelearning_firing
                .authority_receipt_sha256
            ),
            "profile_receipt_sha256": (
                self._profile.authority_receipt_sha256
            ),
            "program_id": synthesis.program.program_id,
            "self_acoustic_mount_receipt_sha256": (
                mount_receipt.authority_receipt_sha256
            ),
            "settled_custody_capability_receipt_sha256": (
                settled_custody_capability.authority_receipt_sha256
            ),
            "source_occurrence_id": settled.source_occurrence_id,
            "world_after_receipt_sha256": (
                execution.after.authority_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                execution.before.authority_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                execution.authority_receipt_sha256
            ),
        }

    def seal(
        self,
        *,
        synthesis: ArticulatorySynthesis,
        emission: ArticulatoryGeneratedEmission,
        acoustic_mount: W1SelfAcousticMount,
        settled_custody_authority: SettledExperienceCustodyAuthority,
        settled_custody_capability: (
            SettledExperienceConsumerCapability
        ),
    ) -> FreshArticulatorySelfAcousticCustodyReceipt:
        """Seal one fully verified occurrence without retaining its media."""

        payload = self._source_payload(
            synthesis=synthesis,
            emission=emission,
            acoustic_mount=acoustic_mount,
            settled_custody_authority=settled_custody_authority,
            settled_custody_capability=settled_custody_capability,
        )
        provisional = FreshArticulatorySelfAcousticCustodyReceipt(
            **payload,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = _sign(
            self._receipt_key,
            _RECEIPT_DOMAIN,
            provisional.payload(),
        )
        receipt = FreshArticulatorySelfAcousticCustodyReceipt(
            **payload,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify_receipt(receipt)
        return receipt

    def verify_occurrence(
        self,
        receipt: FreshArticulatorySelfAcousticCustodyReceipt,
        *,
        synthesis: ArticulatorySynthesis,
        emission: ArticulatoryGeneratedEmission,
        acoustic_mount: W1SelfAcousticMount,
        settled_custody_authority: SettledExperienceCustodyAuthority,
        settled_custody_capability: (
            SettledExperienceConsumerCapability
        ),
    ) -> None:
        """Re-verify a receipt against all four live source authorities."""

        self.verify_receipt(receipt)
        payload = self._source_payload(
            synthesis=synthesis,
            emission=emission,
            acoustic_mount=acoustic_mount,
            settled_custody_authority=settled_custody_authority,
            settled_custody_capability=settled_custody_capability,
        )
        if _canonical(receipt.payload()) != _canonical({
            **payload,
            "schema": RECEIPT_SCHEMA,
        }):
            raise ValueError(
                "fresh articulatory custody receipt changed occurrence"
            )

    def status(self) -> dict[str, object]:
        return {
            "full_field_authority": True,
            "max_full_field_tuples": (
                self._profile.max_full_field_tuples
            ),
            "max_receipt_bytes": self._profile.max_receipt_bytes,
            "profile_receipt_sha256": (
                self._profile.authority_receipt_sha256
            ),
            "retained_pcm_bytes": 0,
            "retained_receipts": 0,
            "schema": RECEIPT_SCHEMA,
            "stateful": False,
        }


__all__ = (
    "FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID",
    "FULL_DSF_CUSTODY_SCHEMA",
    "PROFILE_SCHEMA",
    "RECEIPT_SCHEMA",
    "FreshArticulatorySelfAcousticCustodyAuthority",
    "FreshArticulatorySelfAcousticCustodyProfile",
    "FreshArticulatorySelfAcousticCustodyReceipt",
    "fresh_articulatory_receipt_from_record",
)
