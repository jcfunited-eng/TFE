"""Durable full-field neurons for the mounted whole organism.

One authenticated physical receptor substream becomes one neuron.  The
neuron retains the complete ordered D/M/R/U/C/P/B tuples plus native
source-index, gate, time, topology, sample, and settlement custody.  Hashes
authenticate records and never act as scalar identity or similarity.

Previously mounted paths that do not participate in a later settlement are
retained as exact quiescent zero.  New neurons can enter only when an exact
settlement carries a previously unseen authenticated receptor topology.
There is no applicable neuron-division law in this architecture, so division
growth is explicitly unavailable.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from typing import Mapping

from dsf_ai_service.substrate.ae_local_receptor import (
    AELocalReceptorActivation,
    AELocalReceptorVerifierMount,
    verify_ae_local_receptor_activation,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import ReceiptRegistry
from dsf_ai_service.substrate.causal_thing_mosaic import (
    FullFieldSensoryRoot,
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.physical_neuron_locality import (
    PhysicalNeuronTopologyRecord,
    nearest_neighbor_coupling_pairs,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    MechanismAvailability,
    MechanismKind,
    MountedMechanismManifest,
)


PROFILE_SCHEMA = "guala.whole_organism_neuron_population.profile.v1"
FIELD_TUPLE_SCHEMA = "guala.whole_organism_neuron.field_tuple.v1"
RESPONSE_SCHEMA = "guala.whole_organism_neuron.exact_response.v1"
NEURON_SCHEMA = "guala.whole_organism_neuron.v1"
EDGE_SCHEMA = "guala.whole_organism_neuron.coupling.v1"
MOSAIC_ROOT_BINDING_SCHEMA = (
    "guala.whole_organism_neuron.mosaic_root_binding.v1"
)
MOSAIC_ASSEMBLY_SCHEMA = "guala.whole_organism_neuron.mosaic_assembly.v1"
PREPARED_SCHEMA = "guala.whole_organism_neuron_population.prepared.v1"
STATE_SCHEMA = "guala.whole_organism_neuron_population.state.v1"
ENVELOPE_SCHEMA = (
    "guala.whole_organism_neuron_population.state_hmac.v1"
)

_NEURON_DOMAIN = b"guala-whole-organism-neuron-v1\0"
_EDGE_DOMAIN = b"guala-whole-organism-neuron-edge-v1\0"
_MOSAIC_ASSEMBLY_DOMAIN = (
    b"guala-whole-organism-neuron-mosaic-assembly-v1\0"
)
_PREPARED_DOMAIN = b"guala-whole-organism-neuron-prepared-v1\0"
_STATE_DOMAIN = b"guala-whole-organism-neuron-state-v1\0"
_HEX = frozenset("0123456789abcdef")
_ZERO_FIELDS = tuple((name, "0/1") for name in DSF_FIELD_ORDER)


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
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("neuron-population authority key changed")
    return hashlib.sha256(
        b"guala-whole-organism-neuron-population-v1\0" + raw
    ).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{label} changed")
    return value


def _fraction_text(value: object, label: str) -> str:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{label} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        first = int(numerator)
        second = int(denominator)
    except ValueError as error:
        raise ValueError(f"{label} is not an exact fraction") from error
    if second <= 0:
        raise ValueError(f"{label} has an invalid denominator")
    common = __import__("math").gcd(first, second)
    if f"{first // common}/{second // common}" != value:
        raise ValueError(f"{label} is not canonical")
    return value


@dataclass(frozen=True, slots=True)
class NeuronPopulationProfile:
    profile_id: str
    max_neurons: int
    max_edges: int
    max_tuples_per_neuron: int
    max_response_history: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_neurons: int,
        max_edges: int,
        max_tuples_per_neuron: int,
        max_response_history: int,
        max_state_bytes: int,
    ) -> "NeuronPopulationProfile":
        provisional = cls(
            profile_id=_identifier(profile_id, "population profile id"),
            max_neurons=_positive(max_neurons, "neuron capacity"),
            max_edges=_positive(max_edges, "neuron edge capacity"),
            max_tuples_per_neuron=_positive(
                max_tuples_per_neuron,
                "neuron tuple capacity",
            ),
            max_response_history=_positive(
                max_response_history,
                "neuron response-history capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes,
                "neuron state capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_neurons=provisional.max_neurons,
            max_edges=provisional.max_edges,
            max_tuples_per_neuron=(
                provisional.max_tuples_per_neuron
            ),
            max_response_history=provisional.max_response_history,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_edges": self.max_edges,
            "max_neurons": self.max_neurons,
            "max_state_bytes": self.max_state_bytes,
            "max_tuples_per_neuron": self.max_tuples_per_neuron,
            "max_response_history": self.max_response_history,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        expected = type(self).create(
            profile_id=self.profile_id,
            max_neurons=self.max_neurons,
            max_edges=self.max_edges,
            max_tuples_per_neuron=self.max_tuples_per_neuron,
            max_response_history=self.max_response_history,
            max_state_bytes=self.max_state_bytes,
        )
        if self != expected:
            raise ValueError("neuron-population profile changed")


@dataclass(frozen=True, slots=True)
class ExactNeuronFieldTuple:
    tuple_index: int
    source_index_start: int
    source_index_end: int
    fields: tuple[tuple[str, str], ...]
    tuple_authority_receipt_sha256: str
    source_l0_l4_trace_receipt_sha256: str

    def record(self) -> dict[str, object]:
        return {
            "fields": [list(value) for value in self.fields],
            "schema": FIELD_TUPLE_SCHEMA,
            "source_index_end": self.source_index_end,
            "source_index_start": self.source_index_start,
            "source_l0_l4_trace_receipt_sha256": (
                self.source_l0_l4_trace_receipt_sha256
            ),
            "tuple_authority_receipt_sha256": (
                self.tuple_authority_receipt_sha256
            ),
            "tuple_index": self.tuple_index,
        }


@dataclass(frozen=True, slots=True)
class ExactNeuronResponse:
    settlement_receipt_sha256: str
    kernel_basin_receipt_sha256: str
    boundary_receipt_sha256: str
    source_sample_commitment_sha256: str
    complete_l0_l4_trace_receipt_sha256: str
    canonical_response_sha256: str
    field_tuples: tuple[ExactNeuronFieldTuple, ...]
    response_relation_to_prior: str
    local_receptor_activation: AELocalReceptorActivation | None

    def record(self) -> dict[str, object]:
        return {
            "boundary_receipt_sha256": self.boundary_receipt_sha256,
            "field_tuples": [
                value.record() for value in self.field_tuples
            ],
            "kernel_basin_receipt_sha256": (
                self.kernel_basin_receipt_sha256
            ),
            "complete_l0_l4_trace_receipt_sha256": (
                self.complete_l0_l4_trace_receipt_sha256
            ),
            "canonical_response_sha256": (
                self.canonical_response_sha256
            ),
            "response_relation_to_prior": (
                self.response_relation_to_prior
            ),
            "local_receptor_activation": (
                None
                if self.local_receptor_activation is None
                else self.local_receptor_activation.record()
            ),
            "schema": RESPONSE_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "source_sample_commitment_sha256": (
                self.source_sample_commitment_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class WholeOrganismNeuron:
    neuron_id: str
    mechanism_id: str
    sense: str
    topology_index: int
    sensor_id: str
    substream_id: str
    topology_receipt_sha256: str
    transduction_authority_receipt_sha256: str
    custody_authority_receipt_sha256: str
    current_state: str
    current_field_tuples: tuple[ExactNeuronFieldTuple, ...]
    current_settlement_receipt_sha256: str | None
    source_sample_count: int
    source_sample_commitment_sha256: str
    source_evidence_stream_receipt_sha256: str
    kernel_basin_receipt_sha256: str
    boundary_receipt_sha256: str
    coordinates: tuple[tuple[str, str], ...]
    causal_clock: str
    last_perturbed_full_evidence_json: str
    complete_l0_l4_trace_json: str
    response_trajectory: tuple[ExactNeuronResponse, ...]
    current_local_receptor_activation: (
        AELocalReceptorActivation | None
    )
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "boundary_receipt_sha256": self.boundary_receipt_sha256,
            "causal_clock": self.causal_clock,
            "coordinates": [list(value) for value in self.coordinates],
            "current_field_tuples": [
                value.record() for value in self.current_field_tuples
            ],
            "current_settlement_receipt_sha256": (
                self.current_settlement_receipt_sha256
            ),
            "current_state": self.current_state,
            "custody_authority_receipt_sha256": (
                self.custody_authority_receipt_sha256
            ),
            "kernel_basin_receipt_sha256": (
                self.kernel_basin_receipt_sha256
            ),
            "last_perturbed_full_evidence_json": (
                self.last_perturbed_full_evidence_json
            ),
            "complete_l0_l4_trace_json": (
                self.complete_l0_l4_trace_json
            ),
            "mechanism_id": self.mechanism_id,
            "neuron_id": self.neuron_id,
            "schema": NEURON_SCHEMA,
            "sense": self.sense,
            "sensor_id": self.sensor_id,
            "source_evidence_stream_receipt_sha256": (
                self.source_evidence_stream_receipt_sha256
            ),
            "source_sample_commitment_sha256": (
                self.source_sample_commitment_sha256
            ),
            "source_sample_count": self.source_sample_count,
            "substream_id": self.substream_id,
            "topology_index": self.topology_index,
            "topology_receipt_sha256": self.topology_receipt_sha256,
            "response_trajectory": [
                value.record() for value in self.response_trajectory
            ],
            "current_local_receptor_activation": (
                None
                if self.current_local_receptor_activation is None
                else self.current_local_receptor_activation.record()
            ),
            "transduction_authority_receipt_sha256": (
                self.transduction_authority_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class NeuronCausalCoupling:
    source_neuron_id: str
    target_neuron_id: str
    settlement_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "schema": EDGE_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "source_neuron_id": self.source_neuron_id,
            "target_neuron_id": self.target_neuron_id,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class NeuronMosaicRootBinding:
    full_field_root: FullFieldSensoryRoot
    neuron_id: str
    neuron_authority_receipt_sha256: str
    response: ExactNeuronResponse

    def record(self) -> dict[str, object]:
        return {
            "full_field_root": self.full_field_root.record(),
            "neuron_authority_receipt_sha256": (
                self.neuron_authority_receipt_sha256
            ),
            "neuron_id": self.neuron_id,
            "response": self.response.record(),
            "schema": MOSAIC_ROOT_BINDING_SCHEMA,
        }


@dataclass(frozen=True, slots=True)
class NeuronMosaicAssembly:
    settlement_receipt_sha256: str
    root_bindings: tuple[NeuronMosaicRootBinding, ...]
    co_perturbation_couplings: tuple[NeuronCausalCoupling, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def full_field_roots(self) -> tuple[FullFieldSensoryRoot, ...]:
        return tuple(
            value.full_field_root for value in self.root_bindings
        )

    def payload(self) -> dict[str, object]:
        return {
            "co_perturbation_couplings": [
                value.record()
                for value in self.co_perturbation_couplings
            ],
            "root_bindings": [
                value.record() for value in self.root_bindings
            ],
            "schema": MOSAIC_ASSEMBLY_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedNeuronPopulationMutation:
    before_state_sha256: str
    prior_neurons: tuple[WholeOrganismNeuron, ...]
    prior_edges: tuple[NeuronCausalCoupling, ...]
    staged_neurons: tuple[WholeOrganismNeuron, ...]
    staged_edges: tuple[NeuronCausalCoupling, ...]
    settlement_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "before_state_sha256": self.before_state_sha256,
            "prior_edge_receipts": [
                value.authority_receipt_sha256
                for value in self.prior_edges
            ],
            "prior_neuron_receipts": [
                value.authority_receipt_sha256
                for value in self.prior_neurons
            ],
            "schema": PREPARED_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "staged_edge_receipts": [
                value.authority_receipt_sha256
                for value in self.staged_edges
            ],
            "staged_neuron_receipts": [
                value.authority_receipt_sha256
                for value in self.staged_neurons
            ],
        }


@dataclass(frozen=True, slots=True)
class NeuronPopulationUndo:
    prepared: PreparedNeuronPopulationMutation
    _prior_encoded_state: bytes = field(repr=False, compare=False)
    _staged_encoded_state: bytes = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)


class WholeOrganismNeuronPopulationOwner:
    """Own bounded current neurons and exact co-settlement coupling."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        manifest_authority_key: bytes | str,
        manifest: MountedMechanismManifest,
        profile: NeuronPopulationProfile,
        local_receptor_verifier: (
            AELocalReceptorVerifierMount | None
        ) = None,
    ) -> None:
        manifest.verify(manifest_authority_key)
        profile.verify()
        root = _key(authority_key)
        self._neuron_key = hashlib.sha256(
            _NEURON_DOMAIN + root
        ).digest()
        self._edge_key = hashlib.sha256(_EDGE_DOMAIN + root).digest()
        self._mosaic_assembly_key = hashlib.sha256(
            _MOSAIC_ASSEMBLY_DOMAIN + root
        ).digest()
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._manifest = manifest
        self._profile = profile
        self._specs = {
            value.sense: value
            for value in manifest.mechanisms
            if value.kind is MechanismKind.RECEPTOR_FAMILY
        }
        chemical_spec = next(
            (
                value
                for value in manifest.mechanisms
                if value.mechanism_id == "state:neurochemical-flow"
            ),
            None,
        )
        self._requires_local_receptor = (
            chemical_spec is not None
            and chemical_spec.availability
            is MechanismAvailability.AVAILABLE
        )
        if (
            self._requires_local_receptor
            and not isinstance(
                local_receptor_verifier,
                AELocalReceptorVerifierMount,
            )
        ):
            raise ValueError(
                "available neurochemical flow lacks receptor verifier"
            )
        if local_receptor_verifier is not None:
            local_receptor_verifier.verify()
        self._local_receptor_verifier = local_receptor_verifier
        self._neurons: tuple[WholeOrganismNeuron, ...] = ()
        self._edges: tuple[NeuronCausalCoupling, ...] = ()
        self._prepared: PreparedNeuronPopulationMutation | None = None
        self._encoded_state: bytes | None = None
        self._prepared_prior_encoded_state: bytes | None = None
        self._prepared_staged_encoded_state: bytes | None = None
        self._undo_authority = object()
        self._lock = threading.RLock()
        self._encoded_locked()

    @property
    def neurons(self) -> tuple[WholeOrganismNeuron, ...]:
        with self._lock:
            return self._neurons

    @property
    def edges(self) -> tuple[NeuronCausalCoupling, ...]:
        with self._lock:
            return self._edges

    def _field_tuples(
        self,
        evidence: Mapping[str, object],
    ) -> tuple[ExactNeuronFieldTuple, ...]:
        """Project tuples from a FullFieldSensoryRoot-verified mapping."""
        return tuple(
            ExactNeuronFieldTuple(
                tuple_index=item["tuple_index"],
                source_index_start=item["source_index_start"],
                source_index_end=item["source_index_end"],
                fields=tuple(
                    (value[0], value[1]) for value in item["fields"]
                ),
                tuple_authority_receipt_sha256=(
                    item["authority_receipt_sha256"]
                ),
                source_l0_l4_trace_receipt_sha256=(
                    item["source_l0_l4_trace_receipt_sha256"]
                ),
            )
            for item in evidence["field_tuples"]
        )

    def _seal_neuron(
        self,
        *,
        root: FullFieldSensoryRoot,
        settlement: CausalExperienceSettlement,
        evidence_registry: ReceiptRegistry,
        prior: WholeOrganismNeuron | None = None,
        local_receptor_activation: (
            AELocalReceptorActivation | None
        ) = None,
    ) -> WholeOrganismNeuron:
        root.verify()
        evidence = root.verified_evidence()
        spec = self._specs.get(root.sense)
        if (
            spec is None
            or spec.availability is not MechanismAvailability.AVAILABLE
        ):
            raise ValueError("settlement used an unavailable receptor family")
        sensor_id = _identifier(evidence.get("sensor_id"), "neuron sensor")
        substream_id = _identifier(
            evidence.get("substream_id"),
            "neuron substream",
        )
        topology = _sha(
            evidence.get("topology_receipt_sha256"),
            "neuron topology",
        )
        identity_payload = {
            "manifest_receipt_sha256": (
                self._manifest.authority_receipt_sha256
            ),
            "mechanism_id": spec.mechanism_id,
            "schema": "guala.whole_organism_neuron.identity.v1",
            "sense": root.sense,
            "sensor_id": sensor_id,
            "substream_id": substream_id,
            "topology_index": root.topology_index,
        }
        field_tuples = self._field_tuples(evidence)
        trace_receipt = field_tuples[
            0
        ].source_l0_l4_trace_receipt_sha256
        trace_bytes = evidence_registry.resolve(
            trace_receipt,
            "neuron complete L0-L4 trace",
        )
        trace = json.loads(trace_bytes)
        trace_json = _canonical(trace).decode("utf-8")
        canonical_response_sha256 = _digest({
            "L1_GateL1State": trace["L1_GateL1State"],
            "L2_GateInterpretation": trace["L2_GateInterpretation"],
            "L3_ResonanceResult": trace["L3_ResonanceResult"],
            "L4_DSF": trace["L4_DSF"],
            "schema": "guala.neuron.canonical_response.v1",
        })
        prior_response = (
            prior.response_trajectory[-1]
            if prior is not None and prior.response_trajectory
            else None
        )
        relation = (
            "first_physical_response"
            if prior_response is None
            else "identical"
            if prior_response.canonical_response_sha256
            == canonical_response_sha256
            else "changed"
        )
        response = ExactNeuronResponse(
            settlement_receipt_sha256=settlement.authority_receipt_sha256,
            kernel_basin_receipt_sha256=_sha(
                evidence["kernel_basin_receipt_sha256"],
                "neuron kernel basin",
            ),
            boundary_receipt_sha256=_sha(
                evidence["boundary_receipt_sha256"],
                "neuron boundary",
            ),
            source_sample_commitment_sha256=_sha(
                evidence["source_sample_commitment_sha256"],
                "neuron response sample commitment",
            ),
            complete_l0_l4_trace_receipt_sha256=trace_receipt,
            canonical_response_sha256=canonical_response_sha256,
            field_tuples=field_tuples,
            response_relation_to_prior=relation,
            local_receptor_activation=local_receptor_activation,
        )
        history = (
            (prior.response_trajectory if prior is not None else ())
            + (response,)
        )[-self._profile.max_response_history:]
        provisional = WholeOrganismNeuron(
            neuron_id=_digest(identity_payload),
            mechanism_id=spec.mechanism_id,
            sense=root.sense,
            topology_index=root.topology_index,
            sensor_id=sensor_id,
            substream_id=substream_id,
            topology_receipt_sha256=topology,
            transduction_authority_receipt_sha256=(
                spec.transduction_authority_receipt_sha256
            ),
            custody_authority_receipt_sha256=(
                spec.custody_authority_receipt_sha256
            ),
            current_state="perturbed",
            current_field_tuples=field_tuples,
            current_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            source_sample_count=evidence["source_sample_count"],
            source_sample_commitment_sha256=_sha(
                evidence["source_sample_commitment_sha256"],
                "neuron sample commitment",
            ),
            source_evidence_stream_receipt_sha256=_sha(
                evidence["source_evidence_stream_receipt_sha256"],
                "neuron evidence stream",
            ),
            kernel_basin_receipt_sha256=_sha(
                evidence["kernel_basin_receipt_sha256"],
                "neuron kernel basin",
            ),
            boundary_receipt_sha256=_sha(
                evidence["boundary_receipt_sha256"],
                "neuron boundary",
            ),
            coordinates=tuple(
                (value[0], value[1])
                for value in evidence["coordinates"]
            ),
            causal_clock=spec.causal_clock,
            last_perturbed_full_evidence_json=root.full_evidence_json,
            complete_l0_l4_trace_json=trace_json,
            response_trajectory=history,
            current_local_receptor_activation=(
                local_receptor_activation
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        return self._sign_neuron(provisional)

    def _sign_neuron(
        self,
        provisional: WholeOrganismNeuron,
    ) -> WholeOrganismNeuron:
        signature = hmac.new(
            self._neuron_key,
            _NEURON_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return WholeOrganismNeuron(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name not in {
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _quiescent(
        self,
        value: WholeOrganismNeuron,
        local_receptor_activation: (
            AELocalReceptorActivation | None
        ) = None,
    ) -> WholeOrganismNeuron:
        tuples = tuple(
            ExactNeuronFieldTuple(
                tuple_index=item.tuple_index,
                source_index_start=item.source_index_start,
                source_index_end=item.source_index_end,
                fields=_ZERO_FIELDS,
                tuple_authority_receipt_sha256=(
                    item.tuple_authority_receipt_sha256
                ),
                source_l0_l4_trace_receipt_sha256=(
                    item.source_l0_l4_trace_receipt_sha256
                ),
            )
            for item in value.current_field_tuples
        )
        return self._sign_neuron(WholeOrganismNeuron(
            **{
                name: getattr(value, name)
                for name in value.__dataclass_fields__
                if name not in {
                    "current_state",
                    "current_field_tuples",
                    "current_settlement_receipt_sha256",
                    "current_local_receptor_activation",
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            current_state="quiescent",
            current_field_tuples=tuples,
            current_settlement_receipt_sha256=None,
            current_local_receptor_activation=(
                local_receptor_activation
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        ))

    def _seal_edge(
        self,
        source: str,
        target: str,
        settlement_receipt: str,
    ) -> NeuronCausalCoupling:
        provisional = NeuronCausalCoupling(
            source_neuron_id=source,
            target_neuron_id=target,
            settlement_receipt_sha256=settlement_receipt,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._edge_key,
            _EDGE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return NeuronCausalCoupling(
            source_neuron_id=source,
            target_neuron_id=target,
            settlement_receipt_sha256=settlement_receipt,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def prepare(
        self,
        settlement: CausalExperienceSettlement,
        local_receptor_activations: tuple[
            AELocalReceptorActivation, ...
        ] | None = None,
    ) -> PreparedNeuronPopulationMutation:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("neuron population requires exact settlement")
        settlement.verify()
        roots = full_field_sensory_roots(settlement)
        evidence_registry = settlement.native_evidence_witness.registry()
        if self._requires_local_receptor:
            if (
                not isinstance(local_receptor_activations, tuple)
                or len(local_receptor_activations) != len(self._specs)
                or self._local_receptor_verifier is None
            ):
                raise ValueError(
                    "neuron population lacks complete local receptor state"
                )
            receptor_by_sense = {}
            for activation in local_receptor_activations:
                verify_ae_local_receptor_activation(
                    activation, self._local_receptor_verifier
                )
                if (
                    activation.sense in receptor_by_sense
                    or activation.settlement_receipt_sha256
                    != settlement.authority_receipt_sha256
                ):
                    raise ValueError(
                        "local receptor state crossed causal settlement"
                    )
                receptor_by_sense[activation.sense] = activation
            if set(receptor_by_sense) != set(self._specs):
                raise ValueError(
                    "local receptor state lost a mounted sense"
                )
            rooted_senses = {root.sense for root in roots}
            activated_senses = {
                sense
                for sense, activation in receptor_by_sense.items()
                if activation.activation_state == 1
            }
            if rooted_senses != activated_senses:
                raise ValueError(
                    "sensory roots and local receptor activation disagree"
                )
        else:
            if local_receptor_activations not in {None, ()}:
                raise ValueError(
                    "legacy neuron anatomy received unmounted receptors"
                )
            receptor_by_sense = {}
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "one neuron-population mutation is already prepared"
                )
            prior_encoded_state = self._encoded_locked()
            staged = {
                value.neuron_id: self._quiescent(
                    value,
                    receptor_by_sense.get(value.sense),
                )
                for value in self._neurons
            }
            prior_by_path = {
                (
                    value.sense,
                    value.topology_index,
                    value.sensor_id,
                    value.substream_id,
                ): value
                for value in self._neurons
            }
            perturbed = tuple(
                self._seal_neuron(
                    root=root,
                    settlement=settlement,
                    evidence_registry=evidence_registry,
                    prior=prior_by_path.get((
                        root.sense,
                        root.topology_index,
                        root.verified_evidence()["sensor_id"],
                        root.verified_evidence()["substream_id"],
                    )),
                    local_receptor_activation=(
                        receptor_by_sense.get(root.sense)
                    ),
                )
                for root in roots
            )
            for value in perturbed:
                staged[value.neuron_id] = value
            neurons = tuple(staged[key] for key in sorted(staged))
            if len(neurons) > self._profile.max_neurons:
                raise RuntimeError("neuron capacity exhausted")
            edges = {
                (value.source_neuron_id, value.target_neuron_id): value
                for value in self._edges
            }
            for source, target in nearest_neighbor_coupling_pairs(
                perturbed
            ):
                edge = self._seal_edge(
                    source,
                    target,
                    settlement.authority_receipt_sha256,
                )
                edges[(source, target)] = edge
            staged_edges = tuple(edges[key] for key in sorted(edges))
            if len(staged_edges) > self._profile.max_edges:
                raise RuntimeError("neuron coupling capacity exhausted")
            prior_neurons = self._neurons
            prior_edges = self._edges
            self._neurons = neurons
            self._edges = staged_edges
            try:
                staged_encoded_state = self._build_encoded_locked()
            finally:
                self._neurons = prior_neurons
                self._edges = prior_edges
            provisional = PreparedNeuronPopulationMutation(
                before_state_sha256=self._committed_sha_locked(),
                prior_neurons=self._neurons,
                prior_edges=self._edges,
                staged_neurons=neurons,
                staged_edges=staged_edges,
                settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._prepared_key,
                _PREPARED_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            prepared = PreparedNeuronPopulationMutation(
                **{
                    name: getattr(provisional, name)
                    for name in provisional.__dataclass_fields__
                    if name not in {
                        "authority_hmac_sha256",
                        "authority_receipt_sha256",
                    }
                },
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._prepared = prepared
            self._prepared_prior_encoded_state = prior_encoded_state
            self._prepared_staged_encoded_state = staged_encoded_state
            return prepared

    def _body_locked(self) -> dict[str, object]:
        return {
            "division_growth": {
                "reason": "no_authenticated_division_law",
                "state": "unavailable",
            },
            "edges": [value.record() for value in self._edges],
            "manifest_receipt_sha256": (
                self._manifest.authority_receipt_sha256
            ),
            "mounted_receptor_families": [
                {
                    "availability": value.availability.value,
                    "mechanism_id": value.mechanism_id,
                    "sense": value.sense,
                    "state": (
                        "perturbed"
                        if any(
                            neuron.sense == value.sense
                            and neuron.current_state == "perturbed"
                            for neuron in self._neurons
                        )
                        else "quiescent"
                        if value.availability
                        is MechanismAvailability.AVAILABLE
                        else "unavailable"
                    ),
                }
                for value in self._specs.values()
            ],
            "neurons": [value.record() for value in self._neurons],
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
        }

    def _committed_sha_locked(self) -> str:
        return hashlib.sha256(self._encoded_locked()).hexdigest()

    def _build_encoded_locked(self) -> bytes:
        body = self._body_locked()
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("neuron-population state capacity exhausted")
        return encoded

    def _encoded_locked(self) -> bytes:
        if self._encoded_state is None:
            self._encoded_state = self._build_encoded_locked()
        return self._encoded_state

    def _verify_prepared(
        self,
        value: PreparedNeuronPopulationMutation,
    ) -> None:
        if not isinstance(value, PreparedNeuronPopulationMutation):
            raise TypeError("prepared neuron mutation is not typed")
        expected = hmac.new(
            self._prepared_key,
            _PREPARED_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("prepared neuron authority changed")
        for neuron in value.prior_neurons + value.staged_neurons:
            self._verify_neuron(neuron)
        for edge in value.prior_edges + value.staged_edges:
            self._verify_edge(edge)

    def _verify_neuron(self, value: WholeOrganismNeuron) -> None:
        if not isinstance(value, WholeOrganismNeuron):
            raise TypeError("whole-organism neuron is not typed")
        if (
            value.sense not in self._specs
            or value.current_state not in {"perturbed", "quiescent"}
            or len(value.current_field_tuples)
            > self._profile.max_tuples_per_neuron
            or len(value.response_trajectory)
            > self._profile.max_response_history
        ):
            raise ValueError("whole-organism neuron extent changed")
        for item in value.current_field_tuples:
            if tuple(name for name, _field in item.fields) != DSF_FIELD_ORDER:
                raise ValueError("whole-organism neuron flattened its field")
        for response in value.response_trajectory:
            self._verify_response(response)
            if response.local_receptor_activation is not None:
                if self._local_receptor_verifier is None:
                    raise ValueError(
                        "neuron response has an unmounted local receptor"
                    )
                verify_ae_local_receptor_activation(
                    response.local_receptor_activation,
                    self._local_receptor_verifier,
                )
                if (
                    response.local_receptor_activation.sense
                    != value.sense
                    or response.local_receptor_activation.activation_state
                    != 1
                    or response.local_receptor_activation
                    .settlement_receipt_sha256
                    != response.settlement_receipt_sha256
                ):
                    raise ValueError(
                        "neuron response crossed local receptor activation"
                    )
        if value.current_local_receptor_activation is not None:
            if self._local_receptor_verifier is None:
                raise ValueError(
                    "neuron has an unmounted current local receptor"
                )
            verify_ae_local_receptor_activation(
                value.current_local_receptor_activation,
                self._local_receptor_verifier,
            )
            if (
                value.current_local_receptor_activation.sense
                != value.sense
                or (
                    value.current_state == "perturbed"
                    and value.current_local_receptor_activation
                    .activation_state != 1
                )
                or (
                    value.current_state == "perturbed"
                    and value.current_local_receptor_activation
                    .settlement_receipt_sha256
                    != value.current_settlement_receipt_sha256
                )
            ):
                raise ValueError(
                    "current neuron state crossed local receptor activation"
                )
        expected = hmac.new(
            self._neuron_key,
            _NEURON_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("whole-organism neuron authority changed")

    def _verify_response(self, value: ExactNeuronResponse) -> None:
        if not isinstance(value, ExactNeuronResponse):
            raise TypeError("exact neuron response is not typed")
        if (
            not value.field_tuples
            or len(value.field_tuples)
            > self._profile.max_tuples_per_neuron
            or value.response_relation_to_prior not in {
                "first_physical_response",
                "identical",
                "changed",
            }
        ):
            raise ValueError("neuron response trajectory changed")
        for digest, label in (
            (value.settlement_receipt_sha256, "neuron response settlement"),
            (value.kernel_basin_receipt_sha256, "neuron response basin"),
            (value.boundary_receipt_sha256, "neuron response boundary"),
            (
                value.source_sample_commitment_sha256,
                "neuron response sample commitment",
            ),
            (
                value.complete_l0_l4_trace_receipt_sha256,
                "neuron response trace",
            ),
            (value.canonical_response_sha256, "neuron canonical response"),
        ):
            _sha(digest, label)
        if (
            value.complete_l0_l4_trace_receipt_sha256
            != value.field_tuples[0].source_l0_l4_trace_receipt_sha256
        ):
            raise ValueError("neuron response crossed its L0-L4 trace")
        for item in value.field_tuples:
            if (
                tuple(name for name, _field in item.fields)
                != DSF_FIELD_ORDER
            ):
                raise ValueError(
                    "neuron response trajectory flattened its field"
                )

    def _verify_edge(self, value: NeuronCausalCoupling) -> None:
        if not isinstance(value, NeuronCausalCoupling):
            raise TypeError("neuron coupling is not typed")
        expected = hmac.new(
            self._edge_key,
            _EDGE_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("neuron coupling authority changed")

    def issue_mosaic_assembly(
        self,
        settlement: CausalExperienceSettlement,
    ) -> NeuronMosaicAssembly:
        """Bind one committed settlement to its exact neuronal perturbation."""

        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("neuron mosaic assembly requires exact settlement")
        settlement.verify()
        roots = full_field_sensory_roots(settlement)
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "cannot assemble an in-flight neuron mutation"
                )
            perturbed = tuple(
                value
                for value in self._neurons
                if (
                    value.current_state == "perturbed"
                    and value.current_settlement_receipt_sha256
                    == settlement.authority_receipt_sha256
                )
            )
            by_path: dict[
                tuple[str, int, str, str],
                WholeOrganismNeuron,
            ] = {}
            for neuron in perturbed:
                key = (
                    neuron.sense,
                    neuron.topology_index,
                    neuron.sensor_id,
                    neuron.substream_id,
                )
                if key in by_path:
                    raise ValueError(
                        "settlement repeats one perturbed neuron path"
                    )
                by_path[key] = neuron
            bindings = []
            used_neuron_ids = set()
            for root in roots:
                evidence = root.verified_evidence()
                path = (
                    root.sense,
                    root.topology_index,
                    evidence.get("sensor_id"),
                    evidence.get("substream_id"),
                )
                neuron = by_path.get(path)
                if neuron is None or not neuron.response_trajectory:
                    raise ValueError(
                        "full-field root lacks one perturbed neuron response"
                    )
                response = neuron.response_trajectory[-1]
                if (
                    neuron.neuron_id in used_neuron_ids
                    or response.settlement_receipt_sha256
                    != settlement.authority_receipt_sha256
                    or neuron.last_perturbed_full_evidence_json
                    != root.full_evidence_json
                ):
                    raise ValueError(
                        "full-field root crossed its perturbed neuron response"
                    )
                used_neuron_ids.add(neuron.neuron_id)
                bindings.append(NeuronMosaicRootBinding(
                    full_field_root=root,
                    neuron_id=neuron.neuron_id,
                    neuron_authority_receipt_sha256=(
                        neuron.authority_receipt_sha256
                    ),
                    response=response,
                ))
            if len(used_neuron_ids) != len(perturbed):
                raise ValueError(
                    "settlement has an extra perturbed neuron response"
                )
            expected_pairs = set(
                nearest_neighbor_coupling_pairs(perturbed)
            )
            coupling_by_pair = {
                (value.source_neuron_id, value.target_neuron_id): value
                for value in self._edges
                if value.settlement_receipt_sha256
                == settlement.authority_receipt_sha256
            }
            if set(coupling_by_pair) != expected_pairs:
                raise ValueError(
                    "settlement co-perturbation coupling set changed"
                )
            couplings = tuple(
                coupling_by_pair[key] for key in sorted(coupling_by_pair)
            )
            provisional = NeuronMosaicAssembly(
                settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                root_bindings=tuple(bindings),
                co_perturbation_couplings=couplings,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._mosaic_assembly_key,
                _MOSAIC_ASSEMBLY_DOMAIN
                + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            assembly = NeuronMosaicAssembly(
                settlement_receipt_sha256=(
                    provisional.settlement_receipt_sha256
                ),
                root_bindings=provisional.root_bindings,
                co_perturbation_couplings=(
                    provisional.co_perturbation_couplings
                ),
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self.verify_mosaic_assembly(
                assembly,
                expected_roots=roots,
                expected_settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
            )
            return assembly

    def verify_mosaic_assembly(
        self,
        assembly: NeuronMosaicAssembly,
        *,
        expected_roots: tuple[FullFieldSensoryRoot, ...] | None = None,
        expected_settlement_receipt_sha256: str | None = None,
    ) -> None:
        """Verify complete exact root, response, and coupling membership."""

        if not isinstance(assembly, NeuronMosaicAssembly):
            raise TypeError("neuron mosaic assembly is not typed")
        _sha(
            assembly.settlement_receipt_sha256,
            "neuron mosaic settlement",
        )
        if (
            not assembly.root_bindings
            or len(assembly.root_bindings) > self._profile.max_neurons
        ):
            raise ValueError("neuron mosaic root extent changed")
        expected_hmac = hmac.new(
            self._mosaic_assembly_key,
            _MOSAIC_ASSEMBLY_DOMAIN + _canonical(assembly.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                assembly.authority_hmac_sha256,
            )
            or assembly.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": assembly.payload(),
            })
        ):
            raise ValueError("neuron mosaic assembly authority changed")
        roots = tuple(
            value.full_field_root for value in assembly.root_bindings
        )
        if expected_roots is not None and roots != expected_roots:
            raise ValueError("neuron mosaic assembly roots changed")
        if (
            expected_settlement_receipt_sha256 is not None
            and assembly.settlement_receipt_sha256
            != _sha(
                expected_settlement_receipt_sha256,
                "expected neuron mosaic settlement",
            )
        ):
            raise ValueError("neuron mosaic assembly crossed settlement")
        neuron_ids = []
        root_records = []
        for binding in assembly.root_bindings:
            if not isinstance(binding, NeuronMosaicRootBinding):
                raise TypeError("neuron mosaic root binding is not typed")
            binding.full_field_root.verify()
            _identifier(binding.neuron_id, "mosaic neuron id")
            _sha(
                binding.neuron_authority_receipt_sha256,
                "mosaic neuron authority",
            )
            self._verify_response(binding.response)
            evidence = json.loads(
                binding.full_field_root.full_evidence_json
            )
            activation = binding.response.local_receptor_activation
            if activation is not None:
                if self._local_receptor_verifier is None:
                    raise ValueError(
                        "neuron mosaic response has unmounted receptor"
                    )
                verify_ae_local_receptor_activation(
                    activation,
                    self._local_receptor_verifier,
                )
                if (
                    activation.sense
                    != binding.full_field_root.sense
                    or activation.activation_state != 1
                    or activation.settlement_receipt_sha256
                    != assembly.settlement_receipt_sha256
                ):
                    raise ValueError(
                        "neuron mosaic response crossed local receptor"
                    )
            if (
                binding.response.settlement_receipt_sha256
                != assembly.settlement_receipt_sha256
                or binding.full_field_root.sense
                != evidence.get("sense")
                or binding.full_field_root.topology_index
                != evidence.get("topology_index")
                or self._field_tuples(evidence)
                != binding.response.field_tuples
                or evidence.get("kernel_basin_receipt_sha256")
                != binding.response.kernel_basin_receipt_sha256
                or evidence.get("boundary_receipt_sha256")
                != binding.response.boundary_receipt_sha256
                or evidence.get("source_sample_commitment_sha256")
                != binding.response.source_sample_commitment_sha256
            ):
                raise ValueError(
                    "neuron mosaic root crossed its exact response"
                )
            neuron_ids.append(binding.neuron_id)
            root_records.append(_canonical(
                binding.full_field_root.record()
            ))
        if (
            len(set(neuron_ids)) != len(neuron_ids)
            or len(set(root_records)) != len(root_records)
        ):
            raise ValueError(
                "neuron mosaic assembly repeats a neuron or root"
            )
        topology_views = []
        for binding in assembly.root_bindings:
            evidence = json.loads(
                binding.full_field_root.full_evidence_json
            )
            topology_views.append(PhysicalNeuronTopologyRecord(
                neuron_id=binding.neuron_id,
                sense=binding.full_field_root.sense,
                sensor_id=_identifier(
                    evidence.get("sensor_id"),
                    "mosaic neuron sensor",
                ),
                topology_index=(
                    binding.full_field_root.topology_index
                ),
                coordinates=tuple(
                    (value[0], value[1])
                    for value in evidence["coordinates"]
                ),
            ))
        expected_pairs = set(nearest_neighbor_coupling_pairs(
            tuple(topology_views)
        ))
        actual_pairs = set()
        for coupling in assembly.co_perturbation_couplings:
            self._verify_edge(coupling)
            pair = (
                coupling.source_neuron_id,
                coupling.target_neuron_id,
            )
            if (
                coupling.settlement_receipt_sha256
                != assembly.settlement_receipt_sha256
                or pair in actual_pairs
            ):
                raise ValueError(
                    "neuron mosaic coupling crossed settlement"
                )
            actual_pairs.add(pair)
        if actual_pairs != expected_pairs:
            raise ValueError(
                "neuron mosaic assembly lost or added a coupling"
            )

    def commit(
        self,
        value: PreparedNeuronPopulationMutation,
    ) -> NeuronPopulationUndo:
        with self._lock:
            if self._prepared != value:
                self._verify_prepared(value)
                raise ValueError("prepared neuron mutation is not current")
            if self._committed_sha_locked() != value.before_state_sha256:
                raise RuntimeError("neuron population changed before commit")
            prior_encoded_state = self._prepared_prior_encoded_state
            staged_encoded_state = self._prepared_staged_encoded_state
            if (
                prior_encoded_state is None
                or staged_encoded_state is None
                or self._encoded_locked() is not prior_encoded_state
            ):
                raise RuntimeError(
                    "prepared neuron encoding custody changed"
                )
            self._neurons = value.staged_neurons
            self._edges = value.staged_edges
            self._prepared = None
            self._encoded_state = staged_encoded_state
            self._prepared_prior_encoded_state = None
            self._prepared_staged_encoded_state = None
            return NeuronPopulationUndo(
                prepared=value,
                _prior_encoded_state=prior_encoded_state,
                _staged_encoded_state=staged_encoded_state,
                _owner_authority=self._undo_authority,
            )

    def discard(self, value: PreparedNeuronPopulationMutation) -> None:
        with self._lock:
            if self._prepared != value:
                self._verify_prepared(value)
                raise ValueError("prepared neuron mutation is not current")
            self._prepared = None
            self._prepared_prior_encoded_state = None
            self._prepared_staged_encoded_state = None

    def rollback(self, undo: NeuronPopulationUndo) -> None:
        if (
            not isinstance(undo, NeuronPopulationUndo)
            or undo._owner_authority is not self._undo_authority
        ):
            raise ValueError("neuron-population undo authority changed")
        value = undo.prepared
        with self._lock:
            if (
                self._prepared is not None
                or self._neurons != value.staged_neurons
                or self._edges != value.staged_edges
                or self._encoded_locked() is not undo._staged_encoded_state
                or not isinstance(undo._prior_encoded_state, bytes)
                or hashlib.sha256(
                    undo._prior_encoded_state
                ).hexdigest() != value.before_state_sha256
            ):
                raise ValueError(
                    "committed neuron mutation is not current"
                )
            self._neurons = value.prior_neurons
            self._edges = value.prior_edges
            self._encoded_state = undo._prior_encoded_state

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "cannot snapshot an in-flight neuron mutation"
                )
            return self._encoded_locked()

    @staticmethod
    def _tuple_from_raw(raw: Mapping[str, object]) -> ExactNeuronFieldTuple:
        return ExactNeuronFieldTuple(
            tuple_index=raw["tuple_index"],
            source_index_start=raw["source_index_start"],
            source_index_end=raw["source_index_end"],
            fields=tuple(
                (item[0], _fraction_text(item[1], "cold neuron field"))
                for item in raw["fields"]
            ),
            tuple_authority_receipt_sha256=_sha(
                raw["tuple_authority_receipt_sha256"],
                "cold tuple authority",
            ),
            source_l0_l4_trace_receipt_sha256=_sha(
                raw["source_l0_l4_trace_receipt_sha256"],
                "cold L0-L4 trace",
            ),
        )

    @staticmethod
    def _activation_from_raw(
        raw: Mapping[str, object] | None,
    ) -> AELocalReceptorActivation | None:
        if raw is None:
            return None
        if not isinstance(raw, Mapping):
            raise ValueError("cold local receptor activation changed")
        return AELocalReceptorActivation(
            issuer_id=raw["issuer_id"],
            sense=raw["sense"],
            activation_state=raw["activation_state"],
            settlement_receipt_sha256=raw[
                "settlement_receipt_sha256"
            ],
            chemical_boundary_receipt_sha256=raw[
                "chemical_boundary_receipt_sha256"
            ],
            flow_event_receipt_sha256=raw[
                "flow_event_receipt_sha256"
            ],
            flow_transition_receipt_sha256=raw[
                "flow_transition_receipt_sha256"
            ],
            target_id=raw["target_id"],
            component_id=raw["component_id"],
            carrier_passoff_receipt_sha256=raw[
                "carrier_passoff_receipt_sha256"
            ],
            local_target_exposure_receipt_sha256=raw[
                "local_target_exposure_receipt_sha256"
            ],
            ed25519_signature_hex=raw["ed25519_signature_hex"],
        )

    def _response_from_raw(
        self,
        raw: Mapping[str, object],
    ) -> ExactNeuronResponse:
        expected = {
            "boundary_receipt_sha256",
            "canonical_response_sha256",
            "complete_l0_l4_trace_receipt_sha256",
            "field_tuples",
            "kernel_basin_receipt_sha256",
            "local_receptor_activation",
            "response_relation_to_prior",
            "schema",
            "settlement_receipt_sha256",
            "source_sample_commitment_sha256",
        }
        if (
            not isinstance(raw, Mapping)
            or set(raw) != expected
            or raw.get("schema") != RESPONSE_SCHEMA
            or not isinstance(raw.get("field_tuples"), list)
        ):
            raise ValueError("cold exact neuron response changed")
        result = ExactNeuronResponse(
            settlement_receipt_sha256=raw[
                "settlement_receipt_sha256"
            ],
            kernel_basin_receipt_sha256=raw[
                "kernel_basin_receipt_sha256"
            ],
            boundary_receipt_sha256=raw[
                "boundary_receipt_sha256"
            ],
            source_sample_commitment_sha256=raw[
                "source_sample_commitment_sha256"
            ],
            complete_l0_l4_trace_receipt_sha256=raw[
                "complete_l0_l4_trace_receipt_sha256"
            ],
            canonical_response_sha256=raw[
                "canonical_response_sha256"
            ],
            field_tuples=tuple(
                self._tuple_from_raw(value)
                for value in raw["field_tuples"]
            ),
            response_relation_to_prior=raw[
                "response_relation_to_prior"
            ],
            local_receptor_activation=self._activation_from_raw(
                raw.get("local_receptor_activation")
            ),
        )
        self._verify_response(result)
        return result

    @staticmethod
    def _root_from_raw(raw: Mapping[str, object]) -> FullFieldSensoryRoot:
        expected = {
            "full_evidence_json",
            "physical_value_sha256",
            "schema",
            "sense",
            "topology_index",
        }
        if not isinstance(raw, Mapping) or set(raw) != expected:
            raise ValueError("cold neuron mosaic root changed")
        root = FullFieldSensoryRoot(
            sense=raw["sense"],
            topology_index=raw["topology_index"],
            physical_value_sha256=raw["physical_value_sha256"],
            full_evidence_json=raw["full_evidence_json"],
        )
        root.verify()
        return root

    def mosaic_assembly_from_record(
        self,
        raw: Mapping[str, object],
    ) -> NeuronMosaicAssembly:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "co_perturbation_couplings",
            "root_bindings",
            "schema",
            "settlement_receipt_sha256",
        }
        if (
            not isinstance(raw, Mapping)
            or set(raw) != expected
            or raw.get("schema") != MOSAIC_ASSEMBLY_SCHEMA
            or not isinstance(raw.get("root_bindings"), list)
            or not isinstance(
                raw.get("co_perturbation_couplings"),
                list,
            )
        ):
            raise ValueError("cold neuron mosaic assembly changed")
        bindings = []
        for value in raw["root_bindings"]:
            binding_expected = {
                "full_field_root",
                "neuron_authority_receipt_sha256",
                "neuron_id",
                "response",
                "schema",
            }
            if (
                not isinstance(value, Mapping)
                or set(value) != binding_expected
                or value.get("schema") != MOSAIC_ROOT_BINDING_SCHEMA
            ):
                raise ValueError(
                    "cold neuron mosaic root binding changed"
                )
            bindings.append(NeuronMosaicRootBinding(
                full_field_root=self._root_from_raw(
                    value["full_field_root"]
                ),
                neuron_id=value["neuron_id"],
                neuron_authority_receipt_sha256=(
                    value["neuron_authority_receipt_sha256"]
                ),
                response=self._response_from_raw(value["response"]),
            ))
        assembly = NeuronMosaicAssembly(
            settlement_receipt_sha256=raw[
                "settlement_receipt_sha256"
            ],
            root_bindings=tuple(bindings),
            co_perturbation_couplings=tuple(
                self._edge_from_raw(value)
                for value in raw["co_perturbation_couplings"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw[
                "authority_receipt_sha256"
            ],
        )
        self.verify_mosaic_assembly(assembly)
        return assembly

    def _neuron_from_raw(
        self,
        raw: Mapping[str, object],
    ) -> WholeOrganismNeuron:
        legacy = "current_local_receptor_activation" not in raw
        if legacy:
            legacy_payload = {
                name: value
                for name, value in raw.items()
                if name not in {
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            }
            legacy_signature = hmac.new(
                self._neuron_key,
                _NEURON_DOMAIN + _canonical(legacy_payload),
                hashlib.sha256,
            ).hexdigest()
            if (
                not hmac.compare_digest(
                    legacy_signature,
                    raw.get("authority_hmac_sha256", ""),
                )
                or raw.get("authority_receipt_sha256")
                != _digest({
                    "authority_hmac_sha256": legacy_signature,
                    "payload": legacy_payload,
                })
            ):
                raise ValueError(
                    "legacy whole-organism neuron authority changed"
                )
        responses = tuple(
            self._response_from_raw(
                item
                if not legacy
                else {
                    **item,
                    "local_receptor_activation": None,
                }
            )
            for item in raw["response_trajectory"]
        )
        result = WholeOrganismNeuron(
            neuron_id=raw["neuron_id"],
            mechanism_id=raw["mechanism_id"],
            sense=raw["sense"],
            topology_index=raw["topology_index"],
            sensor_id=raw["sensor_id"],
            substream_id=raw["substream_id"],
            topology_receipt_sha256=raw[
                "topology_receipt_sha256"
            ],
            transduction_authority_receipt_sha256=raw[
                "transduction_authority_receipt_sha256"
            ],
            custody_authority_receipt_sha256=raw[
                "custody_authority_receipt_sha256"
            ],
            current_state=raw["current_state"],
            current_field_tuples=tuple(
                self._tuple_from_raw(value)
                for value in raw["current_field_tuples"]
            ),
            current_settlement_receipt_sha256=raw[
                "current_settlement_receipt_sha256"
            ],
            source_sample_count=raw["source_sample_count"],
            source_sample_commitment_sha256=raw[
                "source_sample_commitment_sha256"
            ],
            source_evidence_stream_receipt_sha256=raw[
                "source_evidence_stream_receipt_sha256"
            ],
            kernel_basin_receipt_sha256=raw[
                "kernel_basin_receipt_sha256"
            ],
            boundary_receipt_sha256=raw[
                "boundary_receipt_sha256"
            ],
            coordinates=tuple(
                (item[0], item[1]) for item in raw["coordinates"]
            ),
            causal_clock=raw["causal_clock"],
            last_perturbed_full_evidence_json=raw[
                "last_perturbed_full_evidence_json"
            ],
            complete_l0_l4_trace_json=raw[
                "complete_l0_l4_trace_json"
            ],
            response_trajectory=responses,
            current_local_receptor_activation=(
                self._activation_from_raw(
                    raw.get("current_local_receptor_activation")
                )
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw[
                "authority_receipt_sha256"
            ],
        )
        if legacy:
            result = self._quiescent(result, None)
        self._verify_neuron(result)
        return result

    def _edge_from_raw(
        self,
        raw: Mapping[str, object],
    ) -> NeuronCausalCoupling:
        result = NeuronCausalCoupling(
            source_neuron_id=raw["source_neuron_id"],
            target_neuron_id=raw["target_neuron_id"],
            settlement_receipt_sha256=raw[
                "settlement_receipt_sha256"
            ],
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw[
                "authority_receipt_sha256"
            ],
        )
        self._verify_edge(result)
        return result

    @classmethod
    def migrate_authenticated_runtime_profile_v1_to_v2_encoded(
        cls,
        *,
        authority_key: bytes | str,
        manifest_authority_key: bytes | str,
        manifest: MountedMechanismManifest,
        legacy_profile: NeuronPopulationProfile,
        current_profile: NeuronPopulationProfile,
        encoded: bytes,
        local_receptor_verifier: (
            AELocalReceptorVerifierMount | None
        ) = None,
    ) -> bytes:
        """Reseal authenticated learned state under bounded anatomy v2."""

        legacy_profile.verify()
        current_profile.verify()
        if (
            legacy_profile.profile_id
            != "guala-live-whole-organism-neurons-v1"
            or legacy_profile.max_neurons != 256
            or legacy_profile.max_edges != (256 * 255) // 2
            or current_profile.profile_id
            != "guala-live-whole-organism-neurons-v2"
            or current_profile.max_neurons <= legacy_profile.max_neurons
            or current_profile.max_edges
            != (
                current_profile.max_neurons
                * (current_profile.max_neurons - 1)
                // 2
            )
            or current_profile.max_tuples_per_neuron
            != legacy_profile.max_tuples_per_neuron
            or current_profile.max_response_history
            != legacy_profile.max_response_history
            or current_profile.max_state_bytes
            != legacy_profile.max_state_bytes
        ):
            raise ValueError(
                "neuron-population runtime profile migration changed scope"
            )
        try:
            raw_envelope = json.loads(encoded)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "neuron-population profile migration state is unreadable"
            ) from error
        raw_body = (
            raw_envelope.get("body")
            if isinstance(raw_envelope, dict)
            else None
        )
        raw_neurons = (
            raw_body.get("neurons")
            if isinstance(raw_body, dict)
            else None
        )
        if (
            not isinstance(raw_neurons, list)
            or any(
                not isinstance(raw, Mapping)
                or "current_local_receptor_activation" not in raw
                or not isinstance(raw.get("response_trajectory"), list)
                or any(
                    not isinstance(response, Mapping)
                    or "local_receptor_activation" not in response
                    for response in raw.get("response_trajectory", ())
                )
                for raw in raw_neurons
            )
        ):
            raise ValueError(
                "neuron-population profile migration would rewrite "
                "legacy receptor state"
            )
        legacy = cls.restore_encoded(
            authority_key=authority_key,
            manifest_authority_key=manifest_authority_key,
            manifest=manifest,
            profile=legacy_profile,
            encoded=encoded,
            local_receptor_verifier=local_receptor_verifier,
        )
        if (
            len(legacy.neurons) > current_profile.max_neurons
            or len(legacy.edges) > current_profile.max_edges
        ):
            raise ValueError(
                "authenticated neuron population exceeds anatomy v2"
            )
        migrated = cls(
            authority_key=authority_key,
            manifest_authority_key=manifest_authority_key,
            manifest=manifest,
            profile=current_profile,
            local_receptor_verifier=local_receptor_verifier,
        )
        with migrated._lock:
            migrated._neurons = legacy.neurons
            migrated._edges = legacy.edges
            for neuron in migrated._neurons:
                migrated._verify_neuron(neuron)
            for edge in migrated._edges:
                migrated._verify_edge(edge)
            migrated._encoded_state = None
            result = migrated._encoded_locked()
        verified = cls.restore_encoded(
            authority_key=authority_key,
            manifest_authority_key=manifest_authority_key,
            manifest=manifest,
            profile=current_profile,
            encoded=result,
            local_receptor_verifier=local_receptor_verifier,
        )
        if (
            verified.neurons != legacy.neurons
            or verified.edges != legacy.edges
            or tuple(value.record() for value in verified.neurons)
            != tuple(value.record() for value in legacy.neurons)
            or tuple(value.record() for value in verified.edges)
            != tuple(value.record() for value in legacy.edges)
        ):
            raise RuntimeError(
                "neuron-population profile migration changed learned state"
            )
        return result

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        manifest_authority_key: bytes | str,
        manifest: MountedMechanismManifest,
        profile: NeuronPopulationProfile,
        encoded: bytes,
        local_receptor_verifier: (
            AELocalReceptorVerifierMount | None
        ) = None,
    ) -> "WholeOrganismNeuronPopulationOwner":
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > profile.max_state_bytes
        ):
            raise ValueError("neuron-population cold state is invalid")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "neuron-population cold state is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("neuron-population cold envelope changed")
        body = envelope.get("body")
        if (
            not isinstance(body, dict)
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != profile.record()
            or not isinstance(body.get("neurons"), list)
            or not isinstance(body.get("edges"), list)
        ):
            raise ValueError("neuron-population cold payload changed")
        legacy_flags = tuple(
            isinstance(raw, Mapping)
            and "current_local_receptor_activation" not in raw
            for raw in body["neurons"]
        )
        if legacy_flags and any(legacy_flags) and not all(legacy_flags):
            raise ValueError(
                "neuron-population mixed legacy receptor state"
            )
        legacy_receptor_state = not legacy_flags or all(legacy_flags)
        if (
            body.get("manifest_receipt_sha256")
            != manifest.authority_receipt_sha256
            and not legacy_receptor_state
        ):
            raise ValueError(
                "neuron-population cold manifest changed"
            )
        owner = cls(
            authority_key=authority_key,
            manifest_authority_key=manifest_authority_key,
            manifest=manifest,
            profile=profile,
            local_receptor_verifier=local_receptor_verifier,
        )
        expected = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected,
        ):
            raise ValueError("neuron-population cold authority changed")
        with owner._lock:
            owner._neurons = tuple(
                owner._neuron_from_raw(raw)
                for raw in body["neurons"]
            )
            owner._edges = tuple(
                owner._edge_from_raw(raw) for raw in body["edges"]
            )
            owner._encoded_state = None
            if (
                not legacy_receptor_state
                and owner._encoded_locked() != encoded
            ):
                raise ValueError(
                    "neuron-population cold round-trip changed state"
                )
        return owner

    def status(self) -> dict[str, object]:
        with self._lock:
            neurons_by_sense = {
                sense: sum(
                    neuron.sense == sense
                    for neuron in self._neurons
                )
                for sense in sorted(self._specs)
            }
            perturbed_neurons_by_sense = {
                sense: sum(
                    neuron.sense == sense
                    and neuron.current_state == "perturbed"
                    for neuron in self._neurons
                )
                for sense in sorted(self._specs)
            }
            return {
                "division_growth": "unavailable",
                "division_growth_reason": (
                    "no_authenticated_division_law"
                ),
                "edges": len(self._edges),
                "edge_capacity": self._profile.max_edges,
                "estimated_maximum_state_bytes": (
                    self._profile.max_state_bytes
                ),
                "full_field": True,
                "mounted_receptor_families": len(self._specs),
                "neurons": len(self._neurons),
                "neurons_by_sense": neurons_by_sense,
                "neuron_capacity": self._profile.max_neurons,
                "perturbed_neurons_by_sense": (
                    perturbed_neurons_by_sense
                ),
                "quiescent_neurons": sum(
                    value.current_state == "quiescent"
                    for value in self._neurons
                ),
                "receptor_active_quiescent_neurons": sum(
                    value.current_state == "quiescent"
                    and value.current_local_receptor_activation
                    is not None
                    and value.current_local_receptor_activation
                    .activation_state == 1
                    for value in self._neurons
                ),
                "unreconciled_legacy_neurons": sum(
                    self._requires_local_receptor
                    and value.current_local_receptor_activation is None
                    for value in self._neurons
                ),
                "reduced_approximation": False,
                "response_history_capacity": (
                    self._profile.max_response_history
                ),
                "schema": (
                    "guala.whole_organism_neuron_population.status.v1"
                ),
                "state_bytes": len(self._encoded_locked()),
                "state_capacity_bytes": self._profile.max_state_bytes,
                "tuples_per_neuron_capacity": (
                    self._profile.max_tuples_per_neuron
                ),
            }

    def has_committed_settlement(self, receipt_sha256: str) -> bool:
        """Return exact receipt custody for an already-advanced boundary."""
        _sha(receipt_sha256, "neuron settlement")
        with self._lock:
            return any(
                value.current_settlement_receipt_sha256 == receipt_sha256
                for value in self._neurons
            )


__all__ = (
    "ExactNeuronFieldTuple",
    "ExactNeuronResponse",
    "NeuronMosaicAssembly",
    "NeuronMosaicRootBinding",
    "NeuronCausalCoupling",
    "NeuronPopulationProfile",
    "NeuronPopulationUndo",
    "PreparedNeuronPopulationMutation",
    "WholeOrganismNeuron",
    "WholeOrganismNeuronPopulationOwner",
)
