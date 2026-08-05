"""Authenticated W1 binaural full-field intake for real Loom neurons.

This bridge is deliberately narrower than recognition.  It moves the complete
two-ear cochlear field into actual H1/H6 auditory Krimelacks without using the
legacy wave-summary projection, LoomNeuron.step, chi, match scores, ψ vectors,
or static peak cells as identity.

Each explicit physical/DSF coordinate advances its own bounded oscillator lane.
The source settlement remains the exact authority; oscillator phase/winding is
only a neuronal response.  One immutable receipt proves the complete atomic
delivery and discloses the target neuron for every lane.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.substrate_dna import (
    CochlearBankKrimelack,
)
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorChannelEvent,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    COCHLEAR_CHANNEL_COUNT,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import EAR_IDS
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
)


W1_LOOM_AUDITORY_BRIDGE_SCHEMA = (
    "guala.w1.loom_auditory_full_field_bridge.v1"
)
INITIAL_AUDITORY_ROUTE_BY_EAR = {
    "left": "H1",
    "right": "H6",
}
PHYSICAL_LANES = {
    "pressure": (
        "pressure_amplitude",
        "relevance",
    ),
    "phase": (
        "cumulative_phase_turns",
        "phase_advance_turns",
    ),
}
LANES_PER_EAR = COCHLEAR_CHANNEL_COUNT * (
    2 * len(DSF_FIELD_ORDER)
    + sum(len(values) for values in PHYSICAL_LANES.values())
)
LANES_PER_OCCURRENCE = len(EAR_IDS) * LANES_PER_EAR
BILATERAL_RELATION_FIELDS = (
    "pressure_difference",
    "relevance_difference",
    "cumulative_phase_difference",
    "phase_advance_difference",
    "source_time_difference",
)
BILATERAL_RELATIONS_PER_OCCURRENCE = (
    COCHLEAR_CHANNEL_COUNT * len(BILATERAL_RELATION_FIELDS)
)


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


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("auditory bridge value is not exact")
    return f"{value.numerator}/{value.denominator}"


def _durations(
    channel: AuditoryReceptorChannelEvent,
) -> tuple[Fraction, ...]:
    prior = Fraction(0)
    result = []
    for frame in channel.frames:
        duration = frame.causal_offset - prior
        if duration <= 0:
            raise ValueError(
                "auditory bridge causal duration is not positive"
            )
        result.append(duration)
        prior = frame.causal_offset
    return tuple(result)


def _expanded_field(
    channel: AuditoryReceptorChannelEvent,
    *,
    component: str,
    field_name: str,
) -> tuple[Fraction, ...]:
    if component == "pressure":
        field_tuples = channel.pressure_fields
        indices = tuple(
            frame.pressure_field_tuple_index
            for frame in channel.frames
        )
    elif component == "phase":
        field_tuples = channel.phase_fields
        indices = tuple(
            frame.phase_field_tuple_index
            for frame in channel.frames
        )
    else:
        raise ValueError("auditory bridge component is invalid")
    values = tuple(
        dict(field_tuples[index].fields)[field_name]
        for index in indices
    )
    if len(values) != len(channel.frames):
        raise RuntimeError(
            "auditory bridge full-field support changed cardinality"
        )
    return values


def _physical_values(
    channel: AuditoryReceptorChannelEvent,
    field_name: str,
) -> tuple[Fraction, ...]:
    return tuple(
        getattr(frame, field_name)
        for frame in channel.frames
    )


@dataclass(frozen=True, slots=True)
class W1LoomAuditoryLaneDelivery:
    ear_id: str
    hemisphere_id: str
    neuron_id: str
    cochlear_index: int
    channel_id: str
    component: str
    field_name: str
    sample_count: int
    trajectory_sha256: str
    event_delta: int
    winding_delta: int
    exact_phase: str
    exact_winding: int
    exact_winding_delta: int

    def record(self) -> dict[str, object]:
        return {
            "channel_id": self.channel_id,
            "cochlear_index": self.cochlear_index,
            "component": self.component,
            "ear_id": self.ear_id,
            "event_delta": self.event_delta,
            "exact_phase": self.exact_phase,
            "exact_winding": self.exact_winding,
            "exact_winding_delta": self.exact_winding_delta,
            "field_name": self.field_name,
            "hemisphere_id": self.hemisphere_id,
            "neuron_id": self.neuron_id,
            "sample_count": self.sample_count,
            "trajectory_sha256": self.trajectory_sha256,
            "winding_delta": self.winding_delta,
        }


@dataclass(frozen=True, slots=True)
class W1LoomBilateralRelationDelivery:
    cochlear_index: int
    channel_id: str
    relation_name: str
    left_neuron_id: str
    right_neuron_id: str
    sample_count: int
    exact_trajectory_sha256: str
    relation_receipt_sha256: str
    left_exact_winding_delta: int
    right_exact_winding_delta: int

    def record(self) -> dict[str, object]:
        return {
            "channel_id": self.channel_id,
            "cochlear_index": self.cochlear_index,
            "exact_trajectory_sha256": (
                self.exact_trajectory_sha256
            ),
            "left_exact_winding_delta": (
                self.left_exact_winding_delta
            ),
            "left_neuron_id": self.left_neuron_id,
            "relation_name": self.relation_name,
            "relation_receipt_sha256": (
                self.relation_receipt_sha256
            ),
            "right_exact_winding_delta": (
                self.right_exact_winding_delta
            ),
            "right_neuron_id": self.right_neuron_id,
            "sample_count": self.sample_count,
        }


@dataclass(frozen=True, slots=True)
class W1LoomAuditoryLaneDynamics:
    ear_route: str
    neuron_ids: tuple[str, ...]
    cochlear_index: int
    channel_id: str
    component: str
    field_name: str
    exact_winding_deltas: tuple[int, ...]

    @property
    def lane_key(self) -> tuple[str, str, str, str]:
        return (
            self.ear_route,
            self.channel_id,
            self.component,
            self.field_name,
        )


@dataclass(frozen=True, slots=True)
class W1LoomAuditoryDynamicsOccurrence:
    source_receptor_settlement_receipt_sha256: str
    frame_count: int
    lanes: tuple[W1LoomAuditoryLaneDynamics, ...]

    def verify(self) -> None:
        if (
            len(self.lanes)
            != LANES_PER_OCCURRENCE
            + BILATERAL_RELATIONS_PER_OCCURRENCE
            or any(
                len(value.exact_winding_deltas)
                != self.frame_count
                for value in self.lanes
            )
            or len({
                value.lane_key for value in self.lanes
            }) != len(self.lanes)
        ):
            raise ValueError(
                "W1 Loom auditory dynamics occurrence changed"
            )


@dataclass(frozen=True, slots=True)
class W1LoomAuditoryBridgeReceipt:
    source_receptor_settlement_receipt_sha256: str
    source_causal_settlement_receipt_sha256: str
    assembly_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    deliveries: tuple[W1LoomAuditoryLaneDelivery, ...]
    bilateral_relations: tuple[
        W1LoomBilateralRelationDelivery, ...
    ]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "bilateral_relation_count": len(
                self.bilateral_relations
            ),
            "bilateral_relations": [
                value.record()
                for value in self.bilateral_relations
            ],
            "deliveries": [
                value.record() for value in self.deliveries
            ],
            "lane_count": len(self.deliveries),
            "schema": W1_LOOM_AUDITORY_BRIDGE_SCHEMA,
            "source_causal_settlement_receipt_sha256": (
                self.source_causal_settlement_receipt_sha256
            ),
            "source_receptor_settlement_receipt_sha256": (
                self.source_receptor_settlement_receipt_sha256
            ),
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }

    def verify(self) -> None:
        if (
            len(self.deliveries) != LANES_PER_OCCURRENCE
            or len(self.bilateral_relations)
            != BILATERAL_RELATIONS_PER_OCCURRENCE
            or len(set(
                (
                    value.ear_id,
                    value.cochlear_index,
                    value.component,
                    value.field_name,
                )
                for value in self.deliveries
            ))
            != LANES_PER_OCCURRENCE
            or tuple(sorted(self.deliveries, key=lambda value: (
                EAR_IDS.index(value.ear_id),
                value.cochlear_index,
                value.component,
                value.field_name,
            ))) != self.deliveries
            or len(set(
                (
                    value.cochlear_index,
                    value.relation_name,
                )
                for value in self.bilateral_relations
            ))
            != BILATERAL_RELATIONS_PER_OCCURRENCE
            or tuple(sorted(
                self.bilateral_relations,
                key=lambda value: (
                    value.cochlear_index,
                    value.relation_name,
                ),
            )) != self.bilateral_relations
            or self.authority_receipt_sha256 != _digest(self.payload())
        ):
            raise ValueError(
                "W1 Loom auditory bridge receipt changed"
            )


class W1LoomAuditoryBridge:
    """Bounded one-occurrence owner for authentic neuronal intake."""

    def __init__(self, brain: LoomBrain) -> None:
        if not isinstance(brain, LoomBrain):
            raise TypeError(
                "W1 Loom auditory bridge requires the live Loom brain"
            )
        self._brain = brain
        self._latest: W1LoomAuditoryBridgeReceipt | None = None
        self._latest_dynamics: (
            W1LoomAuditoryDynamicsOccurrence | None
        ) = None

    @property
    def latest(self) -> W1LoomAuditoryBridgeReceipt | None:
        return self._latest

    @property
    def bound_brain(self) -> LoomBrain:
        return self._brain

    @property
    def latest_dynamics(
        self,
    ) -> W1LoomAuditoryDynamicsOccurrence | None:
        return self._latest_dynamics

    def _target(self, ear_id: str, cochlear_index: int):
        hemisphere_id = INITIAL_AUDITORY_ROUTE_BY_EAR[ear_id]
        hemisphere = self._brain._hemi_map.get(hemisphere_id)
        if hemisphere is None or not hemisphere.cluster.neurons:
            raise RuntimeError(
                "W1 auditory hemisphere is unavailable"
            )
        neurons = hemisphere.cluster.neurons
        neuron_index = (
            cochlear_index
            * len(neurons)
            // COCHLEAR_CHANNEL_COUNT
        )
        neuron = neurons[neuron_index]
        receptor = neuron.krimelack_bank.get("auditory")
        if not isinstance(receptor, CochlearBankKrimelack):
            raise RuntimeError(
                "W1 auditory neuron lacks its cochlear Krimelack"
            )
        return hemisphere_id, neuron, receptor

    def settle(
        self,
        settlement: W1BinauralReceptorSettlement,
    ) -> W1LoomAuditoryBridgeReceipt:
        settlement.verify()
        if (
            self._latest is not None
            and self._latest.source_receptor_settlement_receipt_sha256
            == settlement.authority_receipt_sha256
        ):
            raise ValueError(
                "W1 auditory occurrence was already delivered"
            )
        deliveries = []
        dynamics = []
        for ear in settlement.ears:
            if ear.ear_id not in INITIAL_AUDITORY_ROUTE_BY_EAR:
                raise ValueError("W1 auditory ear topology changed")
            for channel in ear.event.channels:
                duration_values = _durations(channel)
                hemisphere_id, neuron, receptor = self._target(
                    ear.ear_id,
                    channel.cochlear_index,
                )
                for component, fields in (
                    ("phase", channel.phase_fields),
                    ("pressure", channel.pressure_fields),
                ):
                    source_receipts = tuple(
                        value.authority_receipt_sha256
                        for value in fields
                    )
                    for field_name in DSF_FIELD_ORDER:
                        values = _expanded_field(
                            channel,
                            component=component,
                            field_name=field_name,
                        )
                        lane = (
                            ear.ear_id,
                            channel.channel_id,
                            component,
                            field_name,
                        )
                        occurrence_receipt = _digest({
                            "field_receipts": source_receipts,
                            "frame_source_indices": [
                                frame.source_index
                                for frame in channel.frames
                            ],
                            "lane": list(lane),
                            "source_receptor_settlement": (
                                settlement.authority_receipt_sha256
                            ),
                        })
                        response = (
                            receptor.feed_authenticated_full_field_lane(
                                lane=lane,
                                values=values,
                                durations=duration_values,
                                occurrence_receipt_sha256=(
                                    occurrence_receipt
                                ),
                            )
                        )
                        deliveries.append(W1LoomAuditoryLaneDelivery(
                            ear_id=ear.ear_id,
                            hemisphere_id=hemisphere_id,
                            neuron_id=neuron.neuron_id,
                            cochlear_index=channel.cochlear_index,
                            channel_id=channel.channel_id,
                            component=component,
                            field_name=field_name,
                            sample_count=len(values),
                            trajectory_sha256=response[
                                "trajectory_sha256"
                            ],
                            event_delta=response["event_delta"],
                            winding_delta=response["winding_delta"],
                            exact_phase=response["exact_phase"],
                            exact_winding=response["exact_winding"],
                            exact_winding_delta=response[
                                "exact_winding_delta"
                            ],
                        ))
                        dynamics.append(W1LoomAuditoryLaneDynamics(
                            ear_route=ear.ear_id,
                            neuron_ids=(neuron.neuron_id,),
                            cochlear_index=channel.cochlear_index,
                            channel_id=channel.channel_id,
                            component=component,
                            field_name=field_name,
                            exact_winding_deltas=response[
                                "exact_winding_deltas"
                            ],
                        ))
                for component, field_names in PHYSICAL_LANES.items():
                    for field_name in field_names:
                        values = _physical_values(
                            channel,
                            field_name,
                        )
                        lane = (
                            ear.ear_id,
                            channel.channel_id,
                            component,
                            field_name,
                        )
                        occurrence_receipt = _digest({
                            "channel_receipt": (
                                channel.authority_receipt_sha256
                            ),
                            "lane": list(lane),
                            "source_receptor_settlement": (
                                settlement.authority_receipt_sha256
                            ),
                        })
                        response = (
                            receptor.feed_authenticated_full_field_lane(
                                lane=lane,
                                values=values,
                                durations=duration_values,
                                occurrence_receipt_sha256=(
                                    occurrence_receipt
                                ),
                            )
                        )
                        deliveries.append(W1LoomAuditoryLaneDelivery(
                            ear_id=ear.ear_id,
                            hemisphere_id=hemisphere_id,
                            neuron_id=neuron.neuron_id,
                            cochlear_index=channel.cochlear_index,
                            channel_id=channel.channel_id,
                            component=component,
                            field_name=field_name,
                            sample_count=len(values),
                            trajectory_sha256=response[
                                "trajectory_sha256"
                            ],
                            event_delta=response["event_delta"],
                            winding_delta=response["winding_delta"],
                            exact_phase=response["exact_phase"],
                            exact_winding=response["exact_winding"],
                            exact_winding_delta=response[
                                "exact_winding_delta"
                            ],
                        ))
                        dynamics.append(W1LoomAuditoryLaneDynamics(
                            ear_route=ear.ear_id,
                            neuron_ids=(neuron.neuron_id,),
                            cochlear_index=channel.cochlear_index,
                            channel_id=channel.channel_id,
                            component=component,
                            field_name=field_name,
                            exact_winding_deltas=response[
                                "exact_winding_deltas"
                            ],
                        ))
        bilateral_relations = []
        left, right = settlement.ears
        for left_channel, right_channel in zip(
            left.event.channels,
            right.event.channels,
            strict=True,
        ):
            if (
                left_channel.cochlear_index
                != right_channel.cochlear_index
                or left_channel.channel_id
                != right_channel.channel_id
            ):
                raise ValueError(
                    "W1 bilateral cochlear topology changed"
                )
            left_durations = _durations(left_channel)
            right_durations = _durations(right_channel)
            if left_durations != right_durations:
                raise ValueError(
                    "W1 bilateral causal grids changed"
                )
            _left_hemi, left_neuron, left_receptor = self._target(
                "left",
                left_channel.cochlear_index,
            )
            _right_hemi, right_neuron, right_receptor = self._target(
                "right",
                right_channel.cochlear_index,
            )
            relation_values = {
                "pressure_difference": tuple(
                    left_frame.pressure_amplitude
                    - right_frame.pressure_amplitude
                    for left_frame, right_frame in zip(
                        left_channel.frames,
                        right_channel.frames,
                        strict=True,
                    )
                ),
                "relevance_difference": tuple(
                    left_frame.relevance - right_frame.relevance
                    for left_frame, right_frame in zip(
                        left_channel.frames,
                        right_channel.frames,
                        strict=True,
                    )
                ),
                "cumulative_phase_difference": tuple(
                    left_frame.cumulative_phase_turns
                    - right_frame.cumulative_phase_turns
                    for left_frame, right_frame in zip(
                        left_channel.frames,
                        right_channel.frames,
                        strict=True,
                    )
                ),
                "phase_advance_difference": tuple(
                    left_frame.phase_advance_turns
                    - right_frame.phase_advance_turns
                    for left_frame, right_frame in zip(
                        left_channel.frames,
                        right_channel.frames,
                        strict=True,
                    )
                ),
                "source_time_difference": tuple(
                    left_frame.source_time - right_frame.source_time
                    for left_frame, right_frame in zip(
                        left_channel.frames,
                        right_channel.frames,
                        strict=True,
                    )
                ),
            }
            for relation_name in BILATERAL_RELATION_FIELDS:
                values = relation_values[relation_name]
                lane = (
                    "bilateral",
                    left_channel.channel_id,
                    "interaural",
                    relation_name,
                )
                relation_receipt = _digest({
                    "lane": list(lane),
                    "left_channel_receipt": (
                        left_channel.authority_receipt_sha256
                    ),
                    "right_channel_receipt": (
                        right_channel.authority_receipt_sha256
                    ),
                    "source_receptor_settlement": (
                        settlement.authority_receipt_sha256
                    ),
                    "values": [
                        _fraction_text(value) for value in values
                    ],
                })
                left_response = (
                    left_receptor.feed_authenticated_full_field_lane(
                        lane=lane,
                        values=values,
                        durations=left_durations,
                        occurrence_receipt_sha256=relation_receipt,
                    )
                )
                right_response = (
                    right_receptor.feed_authenticated_full_field_lane(
                        lane=lane,
                        values=values,
                        durations=right_durations,
                        occurrence_receipt_sha256=relation_receipt,
                    )
                )
                if (
                    left_response["trajectory_sha256"]
                    != right_response["trajectory_sha256"]
                ):
                    raise RuntimeError(
                        "W1 bilateral neuronal relation diverged"
                    )
                bilateral_relations.append(
                    W1LoomBilateralRelationDelivery(
                        cochlear_index=left_channel.cochlear_index,
                        channel_id=left_channel.channel_id,
                        relation_name=relation_name,
                        left_neuron_id=left_neuron.neuron_id,
                        right_neuron_id=right_neuron.neuron_id,
                        sample_count=len(values),
                        exact_trajectory_sha256=left_response[
                            "trajectory_sha256"
                        ],
                        relation_receipt_sha256=relation_receipt,
                        left_exact_winding_delta=left_response[
                            "exact_winding_delta"
                        ],
                        right_exact_winding_delta=right_response[
                            "exact_winding_delta"
                        ],
                    )
                )
                dynamics.append(W1LoomAuditoryLaneDynamics(
                    ear_route="bilateral",
                    neuron_ids=(
                        left_neuron.neuron_id,
                        right_neuron.neuron_id,
                    ),
                    cochlear_index=left_channel.cochlear_index,
                    channel_id=left_channel.channel_id,
                    component="interaural",
                    field_name=relation_name,
                    exact_winding_deltas=left_response[
                        "exact_winding_deltas"
                    ],
                ))
        ordered = tuple(sorted(deliveries, key=lambda value: (
            EAR_IDS.index(value.ear_id),
            value.cochlear_index,
            value.component,
            value.field_name,
        )))
        ordered_bilateral = tuple(sorted(
            bilateral_relations,
            key=lambda value: (
                value.cochlear_index,
                value.relation_name,
            ),
        ))
        provisional = W1LoomAuditoryBridgeReceipt(
            source_receptor_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            source_causal_settlement_receipt_sha256=(
                settlement.upstream_causal_settlement_receipt_sha256
            ),
            assembly_id=settlement.assembly_id,
            source_time_start=settlement.source_time_start,
            source_time_end=settlement.source_time_end,
            deliveries=ordered,
            bilateral_relations=ordered_bilateral,
            authority_receipt_sha256="0" * 64,
        )
        result = W1LoomAuditoryBridgeReceipt(
            source_receptor_settlement_receipt_sha256=(
                provisional
                .source_receptor_settlement_receipt_sha256
            ),
            source_causal_settlement_receipt_sha256=(
                provisional.source_causal_settlement_receipt_sha256
            ),
            assembly_id=provisional.assembly_id,
            source_time_start=provisional.source_time_start,
            source_time_end=provisional.source_time_end,
            deliveries=provisional.deliveries,
            bilateral_relations=provisional.bilateral_relations,
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        result.verify()
        dynamics_occurrence = W1LoomAuditoryDynamicsOccurrence(
            source_receptor_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            frame_count=settlement.ears[0].event.frame_count,
            lanes=tuple(sorted(
                dynamics,
                key=lambda value: value.lane_key,
            )),
        )
        dynamics_occurrence.verify()
        self._latest = result
        self._latest_dynamics = dynamics_occurrence
        return result


__all__ = [
    "BILATERAL_RELATIONS_PER_OCCURRENCE",
    "INITIAL_AUDITORY_ROUTE_BY_EAR",
    "LANES_PER_EAR",
    "LANES_PER_OCCURRENCE",
    "W1LoomAuditoryBridge",
    "W1LoomAuditoryBridgeReceipt",
    "W1LoomAuditoryDynamicsOccurrence",
    "W1LoomAuditoryLaneDynamics",
    "W1LoomBilateralRelationDelivery",
    "W1LoomAuditoryLaneDelivery",
]
