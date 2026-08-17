"""One atomic custody boundary for Guala's world and thermal body.

The wrapped authority remains an :class:`EmbodimentWorldAuthority`, so every
existing motor, consequence, and rollback path keeps the same typed physical
boundary.  This subclass adds only heat stocks and sparse heat exchange.  A
world action prepares one thermal successor from the same elapsed interval;
both commit, persist, and roll back together.

Temperature is never a comfort label, drive, action selector, or meaning.  It
is exact energy divided by an immutable heat capacity.  The mounted sensory
layer converts that physical quantity into local receptor work; it may not
author it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.substrate.bounded_home_thermal_physics import (
    BoundedThermalState,
    ConductiveThermalEdge,
    ThermalBathEdge,
    ThermalNodeState,
    ThermalPowerSource,
    ThermalTransition,
    advance_bounded_thermal_state,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    PreparedActionExecution,
)


COUPLED_SCHEMA = "guala.thermally_coupled_embodiment.state.v1"
COUPLED_DOMAIN = b"guala-thermally-coupled-embodiment-state-v1\0"
TRANSITION_SCHEMA = "guala.thermally_coupled_embodiment.transition.v1"
TRANSITION_DOMAIN = b"guala-thermally-coupled-embodiment-transition-v1\0"
MAX_COUPLED_STATE_BYTES = 4 * 1024 * 1024
MAX_IDENTIFIER_BYTES = 256


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
        raise ValueError("thermal embodiment authority key is invalid")
    return raw


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES
    ):
        raise ValueError(f"{label} is not a bounded canonical identifier")
    return value


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label} is outside its exact integer boundary")
    return value


def _signed_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} is not an exact integer")
    return value


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} is not a lowercase SHA-256 digest")
    return value


def _state_record(state: BoundedThermalState) -> dict[str, object]:
    return {
        "bath_residue_numerators": list(state.bath_residue_numerators),
        "conductive_residue_numerators": list(
            state.conductive_residue_numerators
        ),
        "nodes": [
            {
                "capacity_microjoules_per_millikelvin": (
                    node.capacity_microjoules_per_millikelvin
                ),
                "energy_microjoules": node.energy_microjoules,
            }
            for node in state.nodes
        ],
        "power_residue_numerators": list(state.power_residue_numerators),
    }


def _state_from_record(value: object) -> BoundedThermalState:
    expected = {
        "bath_residue_numerators",
        "conductive_residue_numerators",
        "nodes",
        "power_residue_numerators",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("thermal state fields changed")
    raw_nodes = value.get("nodes")
    raw_conductive = value.get("conductive_residue_numerators")
    raw_baths = value.get("bath_residue_numerators")
    raw_power = value.get("power_residue_numerators")
    if not all(
        isinstance(item, list)
        for item in (raw_nodes, raw_conductive, raw_baths, raw_power)
    ):
        raise ValueError("thermal state vectors changed")
    nodes = []
    for raw in raw_nodes:
        if not isinstance(raw, Mapping) or set(raw) != {
            "capacity_microjoules_per_millikelvin",
            "energy_microjoules",
        }:
            raise ValueError("thermal node fields changed")
        nodes.append(
            ThermalNodeState(
                energy_microjoules=_integer(
                    raw.get("energy_microjoules"), "thermal node energy"
                ),
                capacity_microjoules_per_millikelvin=_integer(
                    raw.get("capacity_microjoules_per_millikelvin"),
                    "thermal node capacity",
                    minimum=1,
                ),
            )
        )
    for vector in (raw_conductive, raw_baths, raw_power):
        if any(isinstance(item, bool) or not isinstance(item, int) for item in vector):
            raise ValueError("thermal residue vector changed")
    result = BoundedThermalState(
        nodes=tuple(nodes),
        conductive_residue_numerators=tuple(raw_conductive),
        bath_residue_numerators=tuple(raw_baths),
        power_residue_numerators=tuple(raw_power),
    )
    if _state_record(result) != value:
        raise ValueError("thermal state is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class CoupledThermalAnatomy:
    """Immutable heat capacities and sparse physical contacts."""

    node_ids: tuple[str, ...]
    initial_temperatures_millikelvin: tuple[int, ...]
    capacities_microjoules_per_millikelvin: tuple[int, ...]
    fixed_conductive_edges: tuple[ConductiveThermalEdge, ...]
    room_air_node_by_region_id: tuple[tuple[str, int], ...]
    skin_node_index: int
    core_node_index: int
    skin_air_conductance_microwatts_per_kelvin: int
    bath_edges: tuple[ThermalBathEdge, ...]
    power_sources: tuple[ThermalPowerSource, ...]
    parameter_provenance: tuple[str, ...]

    def room_nodes(self) -> dict[str, int]:
        return dict(self.room_air_node_by_region_id)

    def conductive_edges(self, room_id: str) -> tuple[ConductiveThermalEdge, ...]:
        room_nodes = self.room_nodes()
        if room_id not in room_nodes:
            raise ValueError("body thermal contact lost its physical region")
        return self.fixed_conductive_edges + tuple(
            ConductiveThermalEdge(
                self.skin_node_index,
                node_index,
                (
                    self.skin_air_conductance_microwatts_per_kelvin
                    if region_id == room_id
                    else 0
                ),
            )
            for region_id, node_index in self.room_air_node_by_region_id
        )

    def record(self) -> dict[str, object]:
        return {
            "bath_edges": [
                {
                    "bath_temperature_millikelvin": edge.bath_temperature_millikelvin,
                    "conductance_microwatts_per_kelvin": edge.conductance_microwatts_per_kelvin,
                    "node_index": edge.node_index,
                }
                for edge in self.bath_edges
            ],
            "capacities_microjoules_per_millikelvin": list(
                self.capacities_microjoules_per_millikelvin
            ),
            "core_node_index": self.core_node_index,
            "fixed_conductive_edges": [
                {
                    "conductance_microwatts_per_kelvin": edge.conductance_microwatts_per_kelvin,
                    "left_node_index": edge.left_node_index,
                    "right_node_index": edge.right_node_index,
                }
                for edge in self.fixed_conductive_edges
            ],
            "initial_temperatures_millikelvin": list(
                self.initial_temperatures_millikelvin
            ),
            "node_ids": list(self.node_ids),
            "parameter_provenance": list(self.parameter_provenance),
            "power_sources": [
                {
                    "node_index": source.node_index,
                    "power_microwatts": source.power_microwatts,
                }
                for source in self.power_sources
            ],
            "room_air_node_by_region_id": [
                [region_id, node_index]
                for region_id, node_index in self.room_air_node_by_region_id
            ],
            "skin_air_conductance_microwatts_per_kelvin": (
                self.skin_air_conductance_microwatts_per_kelvin
            ),
            "skin_node_index": self.skin_node_index,
        }

    @property
    def receipt_sha256(self) -> str:
        return _digest(self.record())

    def verify(self, region_ids: Sequence[str]) -> None:
        if (
            not 1 <= len(self.node_ids) <= 8
            or len(set(self.node_ids)) != len(self.node_ids)
            or any(_identifier(item, "thermal node id") != item for item in self.node_ids)
            or len(self.initial_temperatures_millikelvin) != len(self.node_ids)
            or len(self.capacities_microjoules_per_millikelvin) != len(self.node_ids)
        ):
            raise ValueError("thermal node anatomy changed")
        room_nodes = self.room_nodes()
        if (
            len(room_nodes) != len(self.room_air_node_by_region_id)
            or set(room_nodes) != set(region_ids)
            or len(set(room_nodes.values())) != len(room_nodes)
        ):
            raise ValueError("thermal room anatomy differs from world regions")
        if self.skin_node_index == self.core_node_index:
            raise ValueError("thermal skin and core occupy the same node")
        for index in (*room_nodes.values(), self.skin_node_index, self.core_node_index):
            if not 0 <= index < len(self.node_ids):
                raise ValueError("thermal anatomy references an absent node")
        if not self.parameter_provenance or any(
            _identifier(item, "thermal parameter provenance") != item
            for item in self.parameter_provenance
        ):
            raise ValueError("thermal anatomy lacks bounded parameter provenance")
        genesis = self.genesis_state()
        # Either room selects the same fixed topology and denominator layout.
        for room_id in sorted(room_nodes):
            genesis.verify(
                self.conductive_edges(room_id),
                self.bath_edges,
                self.power_sources,
            )

    def genesis_state(self) -> BoundedThermalState:
        node_count = len(self.node_ids)
        if len(self.capacities_microjoules_per_millikelvin) != node_count:
            raise ValueError("thermal genesis capacity width changed")
        state = BoundedThermalState(
            nodes=tuple(
                ThermalNodeState(
                    energy_microjoules=temperature * capacity,
                    capacity_microjoules_per_millikelvin=capacity,
                )
                for temperature, capacity in zip(
                    self.initial_temperatures_millikelvin,
                    self.capacities_microjoules_per_millikelvin,
                    strict=True,
                )
            ),
            conductive_residue_numerators=(0,) * (
                len(self.fixed_conductive_edges)
                + len(self.room_air_node_by_region_id)
            ),
            bath_residue_numerators=(0,) * len(self.bath_edges),
            power_residue_numerators=(0,) * len(self.power_sources),
        )
        return state


@dataclass(frozen=True, slots=True)
class ThermalTransitionReceipt:
    world_execution_receipt_sha256: str
    world_revision_before: int
    world_revision_after: int
    local_region_id: str
    duration_microseconds: int
    thermal_state_before_sha256: str
    thermal_state_after_sha256: str
    conductive_transfers_microjoules: tuple[int, ...]
    bath_transfers_into_nodes_microjoules: tuple[int, ...]
    powered_into_nodes_microjoules: tuple[int, ...]
    external_energy_into_nodes_microjoules: int
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "bath_transfers_into_nodes_microjoules": list(
                self.bath_transfers_into_nodes_microjoules
            ),
            "conductive_transfers_microjoules": list(
                self.conductive_transfers_microjoules
            ),
            "duration_microseconds": self.duration_microseconds,
            "external_energy_into_nodes_microjoules": (
                self.external_energy_into_nodes_microjoules
            ),
            "local_region_id": self.local_region_id,
            "powered_into_nodes_microjoules": list(
                self.powered_into_nodes_microjoules
            ),
            "schema": TRANSITION_SCHEMA,
            "thermal_state_after_sha256": self.thermal_state_after_sha256,
            "thermal_state_before_sha256": self.thermal_state_before_sha256,
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
            "world_revision_after": self.world_revision_after,
            "world_revision_before": self.world_revision_before,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class ThermalObservation:
    world_revision: int
    world_observation_receipt_sha256: str
    anatomy_receipt_sha256: str
    node_ids: tuple[str, ...]
    temperatures_millikelvin: tuple[Fraction, ...]
    latest_transition_receipt_sha256: str | None


@dataclass(frozen=True, slots=True)
class ThermalEndpointObservation:
    world_execution_receipt_sha256: str
    node_ids: tuple[str, ...]
    before_temperatures_millikelvin: tuple[Fraction, ...]
    after_temperatures_millikelvin: tuple[Fraction, ...]
    thermal_transition_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class _PendingThermal:
    prepared_world: PreparedActionExecution
    prior_state: BoundedThermalState
    candidate_state: BoundedThermalState
    candidate_world_revision: int
    candidate_world_observation_receipt_sha256: str
    receipt: ThermalTransitionReceipt
    prior_latest_transition: ThermalTransitionReceipt | None


class ThermallyCoupledEmbodimentWorldAuthority(EmbodimentWorldAuthority):
    """The existing world authority with one atomic bounded heat circuit."""

    def __init__(
        self,
        *,
        thermal_anatomy: CoupledThermalAnatomy,
        authority_key: bytes | str,
        **world_parameters: object,
    ) -> None:
        if not isinstance(thermal_anatomy, CoupledThermalAnatomy):
            raise TypeError("coupled thermal anatomy is not typed")
        self._thermal_key = _key(authority_key)
        self._thermal_lock = threading.RLock()
        self._thermal_anatomy = thermal_anatomy
        self._thermal_state = thermal_anatomy.genesis_state()
        self._thermal_world_revision = 0
        self._thermal_world_observation_receipt_sha256 = ""
        self._latest_thermal_transition: ThermalTransitionReceipt | None = None
        self._pending_thermal: _PendingThermal | None = None
        self._committed_thermal_tail: _PendingThermal | None = None
        super().__init__(authority_key=authority_key, **world_parameters)
        observation = super().observation_snapshot()
        thermal_anatomy.verify(tuple(item.region_id for item in observation.regions))
        self._thermal_state.verify(
            thermal_anatomy.conductive_edges(observation.room_id),
            thermal_anatomy.bath_edges,
            thermal_anatomy.power_sources,
        )
        self._thermal_world_revision = observation.revision
        self._thermal_world_observation_receipt_sha256 = (
            observation.authority_receipt_sha256
        )

    def _seal_transition(
        self,
        execution: ActionExecutionReceipt,
        room_id: str,
        transition: ThermalTransition,
    ) -> ThermalTransitionReceipt:
        payload = {
            "bath_transfers_into_nodes_microjoules": list(
                transition.bath_transfers_into_nodes_microjoules
            ),
            "conductive_transfers_microjoules": list(
                transition.conductive_transfers_microjoules
            ),
            "duration_microseconds": execution.elapsed_nanoseconds // 1_000,
            "external_energy_into_nodes_microjoules": (
                transition.external_energy_into_nodes_microjoules
            ),
            "local_region_id": room_id,
            "powered_into_nodes_microjoules": list(
                transition.powered_into_nodes_microjoules
            ),
            "schema": TRANSITION_SCHEMA,
            "thermal_state_after_sha256": _digest(
                _state_record(transition.successor)
            ),
            "thermal_state_before_sha256": _digest(
                _state_record(self._thermal_state)
            ),
            "world_execution_receipt_sha256": (
                execution.authority_receipt_sha256
            ),
            "world_revision_after": execution.after.revision,
            "world_revision_before": execution.before.revision,
        }
        signature = hmac.new(
            self._thermal_key,
            TRANSITION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        receipt = _digest({"authority_hmac_sha256": signature, "payload": payload})
        return ThermalTransitionReceipt(
            world_execution_receipt_sha256=execution.authority_receipt_sha256,
            world_revision_before=execution.before.revision,
            world_revision_after=execution.after.revision,
            local_region_id=room_id,
            duration_microseconds=execution.elapsed_nanoseconds // 1_000,
            thermal_state_before_sha256=payload["thermal_state_before_sha256"],
            thermal_state_after_sha256=payload["thermal_state_after_sha256"],
            conductive_transfers_microjoules=tuple(
                transition.conductive_transfers_microjoules
            ),
            bath_transfers_into_nodes_microjoules=tuple(
                transition.bath_transfers_into_nodes_microjoules
            ),
            powered_into_nodes_microjoules=tuple(
                transition.powered_into_nodes_microjoules
            ),
            external_energy_into_nodes_microjoules=(
                transition.external_energy_into_nodes_microjoules
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=receipt,
        )

    def prepare_port_command(self, **parameters: object):
        with self._thermal_lock:
            if self._pending_thermal is not None:
                raise RuntimeError("thermal embodiment already has a prepared action")
            prepared = super().prepare_port_command(**parameters)
            if isinstance(prepared, ActionExecutionReceipt):
                return prepared
            execution = prepared.execution_receipt
            if execution.elapsed_nanoseconds % 1_000:
                super().discard_prepared_action(prepared)
                raise ValueError("world action does not settle on the thermal microsecond lattice")
            if (
                execution.before.revision != self._thermal_world_revision
                or execution.before.authority_receipt_sha256
                != self._thermal_world_observation_receipt_sha256
            ):
                super().discard_prepared_action(prepared)
                raise RuntimeError("thermal body lost current world custody")
            room_id = execution.after.room_id
            try:
                transition = advance_bounded_thermal_state(
                    self._thermal_state,
                    conductive_edges=self._thermal_anatomy.conductive_edges(room_id),
                    bath_edges=self._thermal_anatomy.bath_edges,
                    power_sources=self._thermal_anatomy.power_sources,
                    duration_microseconds=execution.elapsed_nanoseconds // 1_000,
                )
                receipt = self._seal_transition(execution, room_id, transition)
            except BaseException:
                super().discard_prepared_action(prepared)
                raise
            self._pending_thermal = _PendingThermal(
                prepared_world=prepared,
                prior_state=self._thermal_state,
                candidate_state=transition.successor,
                candidate_world_revision=execution.after.revision,
                candidate_world_observation_receipt_sha256=(
                    execution.after.authority_receipt_sha256
                ),
                receipt=receipt,
                prior_latest_transition=self._latest_thermal_transition,
            )
            return prepared

    def _require_pending(self, prepared: PreparedActionExecution) -> _PendingThermal:
        pending = self._pending_thermal
        if pending is None or pending.prepared_world is not prepared:
            raise ValueError("prepared thermal action changed custody")
        return pending

    def verify_prepared_action(self, prepared: PreparedActionExecution) -> None:
        with self._thermal_lock:
            self._require_pending(prepared)
            super().verify_prepared_action(prepared)

    @contextmanager
    def prepared_action_visibility_transaction(
        self, prepared: PreparedActionExecution
    ):
        """Hold the thermal lock before the world's visibility lock."""

        with self._thermal_lock:
            self._require_pending(prepared)
            with super().prepared_action_visibility_transaction(prepared):
                yield

    def discard_prepared_action(self, prepared: PreparedActionExecution) -> None:
        with self._thermal_lock:
            self._require_pending(prepared)
            super().discard_prepared_action(prepared)
            self._pending_thermal = None

    def execute_port_command(
        self,
        *,
        port_id: str,
        command_payload: bytes,
        causal_intent_receipt_sha256: str,
        expected_revision: int,
    ) -> ActionExecutionReceipt:
        """Execute atomically with one invariant thermal-then-world lock order."""

        with self._thermal_lock:
            prepared = self.prepare_port_command(
                port_id=port_id,
                command_payload=command_payload,
                causal_intent_receipt_sha256=(
                    causal_intent_receipt_sha256
                ),
                expected_revision=expected_revision,
            )
            if isinstance(prepared, ActionExecutionReceipt):
                return prepared
            try:
                return self.commit_prepared_action(prepared)
            except BaseException:
                if self._pending_thermal is not None:
                    self.discard_prepared_action(prepared)
                raise

    def commit_prepared_action(
        self, prepared: PreparedActionExecution
    ) -> ActionExecutionReceipt:
        with self._thermal_lock:
            pending = self._require_pending(prepared)
            execution = super().commit_prepared_action(prepared)
            self._thermal_state = pending.candidate_state
            self._thermal_world_revision = pending.candidate_world_revision
            self._thermal_world_observation_receipt_sha256 = (
                pending.candidate_world_observation_receipt_sha256
            )
            self._latest_thermal_transition = pending.receipt
            self._pending_thermal = None
            self._committed_thermal_tail = pending
            return execution

    @contextmanager
    def committed_prepared_action_rollback_transaction(
        self, prepared: PreparedActionExecution
    ):
        with self._thermal_lock:
            tail = self._committed_thermal_tail
            if tail is None or tail.prepared_world is not prepared:
                raise ValueError("committed thermal action changed custody")
            with super().committed_prepared_action_rollback_transaction(
                prepared
            ) as rollback_world:
                rolled_back = [False]

                def rollback_both() -> None:
                    if rolled_back[0]:
                        raise RuntimeError("thermal action was already rolled back")
                    rollback_world()
                    self._thermal_state = tail.prior_state
                    self._thermal_world_revision = (
                        tail.receipt.world_revision_before
                    )
                    self._thermal_world_observation_receipt_sha256 = (
                        prepared.execution_receipt.before.authority_receipt_sha256
                    )
                    self._latest_thermal_transition = tail.prior_latest_transition
                    self._committed_thermal_tail = None
                    rolled_back[0] = True

                yield rollback_both

    def _coupled_encoded(
        self,
        world_encoded: bytes,
        state: BoundedThermalState,
        world_revision: int,
        world_observation_receipt_sha256: str,
        latest: ThermalTransitionReceipt | None,
    ) -> bytes:
        payload = {
            "anatomy_receipt_sha256": self._thermal_anatomy.receipt_sha256,
            "latest_thermal_transition": (
                latest.record() if latest is not None else None
            ),
            "schema": COUPLED_SCHEMA,
            "thermal_state": _state_record(state),
            "world_observation_receipt_sha256": (
                world_observation_receipt_sha256
            ),
            "world_revision": world_revision,
            "world_state_base64": base64.b64encode(world_encoded).decode("ascii"),
        }
        body = _canonical(payload)
        signature = hmac.new(
            self._thermal_key,
            COUPLED_DOMAIN + body,
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "authority_hmac_sha256": signature,
            "payload_base64": base64.b64encode(body).decode("ascii"),
            "schema": COUPLED_SCHEMA,
        })
        if len(encoded) > MAX_COUPLED_STATE_BYTES:
            raise ValueError("coupled thermal world exceeds its exact byte capacity")
        return encoded

    def encoded_snapshot(self) -> bytes:
        with self._thermal_lock:
            world = super().encoded_snapshot()
            return self._coupled_encoded(
                world,
                self._thermal_state,
                self._thermal_world_revision,
                self._thermal_world_observation_receipt_sha256,
                self._latest_thermal_transition,
            )

    def encoded_committed_prepared_action(
        self, prepared: PreparedActionExecution
    ) -> bytes:
        with self._thermal_lock:
            tail = self._committed_thermal_tail
            if tail is None or tail.prepared_world is not prepared:
                raise ValueError("committed thermal candidate changed custody")
            world = super().encoded_committed_prepared_action(prepared)
            return self._coupled_encoded(
                world,
                tail.candidate_state,
                tail.candidate_world_revision,
                tail.candidate_world_observation_receipt_sha256,
                tail.receipt,
            )

    def thermal_observation(self) -> ThermalObservation:
        with self._thermal_lock:
            world = super().observation_snapshot()
            if (
                world.revision != self._thermal_world_revision
                or world.authority_receipt_sha256
                != self._thermal_world_observation_receipt_sha256
            ):
                raise RuntimeError("thermal observation lost current world custody")
            return ThermalObservation(
                world_revision=world.revision,
                world_observation_receipt_sha256=(
                    world.authority_receipt_sha256
                ),
                anatomy_receipt_sha256=self._thermal_anatomy.receipt_sha256,
                node_ids=self._thermal_anatomy.node_ids,
                temperatures_millikelvin=tuple(
                    node.temperature_millikelvin
                    for node in self._thermal_state.nodes
                ),
                latest_transition_receipt_sha256=(
                    self._latest_thermal_transition.authority_receipt_sha256
                    if self._latest_thermal_transition is not None
                    else None
                ),
            )

    def thermal_endpoints_for_execution(
        self, execution: ActionExecutionReceipt
    ) -> ThermalEndpointObservation:
        """Expose only the exact thermal endpoints bound to one live tail."""

        if not isinstance(execution, ActionExecutionReceipt):
            raise TypeError("thermal endpoints require a typed world execution")
        with self._thermal_lock:
            candidate = self._pending_thermal or self._committed_thermal_tail
            if (
                candidate is None
                or candidate.prepared_world.execution_receipt is not execution
            ):
                raise ValueError("world execution has no coupled thermal tail")
            return ThermalEndpointObservation(
                world_execution_receipt_sha256=(
                    execution.authority_receipt_sha256
                ),
                node_ids=self._thermal_anatomy.node_ids,
                before_temperatures_millikelvin=tuple(
                    node.temperature_millikelvin
                    for node in candidate.prior_state.nodes
                ),
                after_temperatures_millikelvin=tuple(
                    node.temperature_millikelvin
                    for node in candidate.candidate_state.nodes
                ),
                thermal_transition_receipt_sha256=(
                    candidate.receipt.authority_receipt_sha256
                ),
            )

    def restore_encoded(
        self,
        encoded: bytes,
        *,
        allow_authenticated_physical_manifest_migration: bool = False,
        allow_legacy_thermal_genesis: bool = False,
    ) -> None:
        with self._thermal_lock:
            self._restore_encoded_locked(
                encoded,
                allow_authenticated_physical_manifest_migration=(
                    allow_authenticated_physical_manifest_migration
                ),
                allow_legacy_thermal_genesis=allow_legacy_thermal_genesis,
            )

    def _restore_encoded_locked(
        self,
        encoded: bytes,
        *,
        allow_authenticated_physical_manifest_migration: bool,
        allow_legacy_thermal_genesis: bool,
    ) -> None:
        if not isinstance(encoded, bytes) or not encoded or len(encoded) > MAX_COUPLED_STATE_BYTES:
            raise ValueError("coupled thermal world exceeds its exact byte capacity")
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("coupled thermal world is not canonical JSON") from error
        if not isinstance(envelope, Mapping) or envelope.get("schema") != COUPLED_SCHEMA:
            if not allow_legacy_thermal_genesis:
                raise ValueError("bare world requires explicit thermal genesis migration")
            prior_world = super().encoded_snapshot()
            try:
                super().restore_encoded(
                    encoded,
                    allow_authenticated_physical_manifest_migration=(
                        allow_authenticated_physical_manifest_migration
                    ),
                )
                observation = super().observation_snapshot()
                self._thermal_anatomy.verify(
                    tuple(item.region_id for item in observation.regions)
                )
            except BaseException:
                super().restore_encoded(prior_world)
                raise
            self._thermal_state = self._thermal_anatomy.genesis_state()
            self._thermal_world_revision = observation.revision
            self._thermal_world_observation_receipt_sha256 = (
                observation.authority_receipt_sha256
            )
            self._latest_thermal_transition = None
            self._pending_thermal = None
            self._committed_thermal_tail = None
            return
        if set(envelope) != {"authority_hmac_sha256", "payload_base64", "schema"}:
            raise ValueError("coupled thermal envelope fields changed")
        try:
            body = base64.b64decode(envelope["payload_base64"], validate=True)
            payload = json.loads(body.decode("utf-8"))
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("coupled thermal payload is invalid") from error
        if _canonical(payload) != body:
            raise ValueError("coupled thermal payload is not canonical")
        expected_signature = hmac.new(
            self._thermal_key,
            COUPLED_DOMAIN + body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected_signature, envelope.get("authority_hmac_sha256", "")
        ):
            raise ValueError("coupled thermal authority changed")
        expected = {
            "anatomy_receipt_sha256",
            "latest_thermal_transition",
            "schema",
            "thermal_state",
            "world_observation_receipt_sha256",
            "world_revision",
            "world_state_base64",
        }
        if not isinstance(payload, Mapping) or set(payload) != expected:
            raise ValueError("coupled thermal payload fields changed")
        if payload.get("anatomy_receipt_sha256") != self._thermal_anatomy.receipt_sha256:
            raise ValueError("coupled thermal anatomy changed")
        try:
            world_encoded = base64.b64decode(
                payload.get("world_state_base64"), validate=True
            )
        except (TypeError, ValueError) as error:
            raise ValueError("coupled world body is invalid") from error
        state = _state_from_record(payload.get("thermal_state"))
        revision = _integer(payload.get("world_revision"), "thermal world revision")
        receipt = _sha(
            payload.get("world_observation_receipt_sha256"),
            "thermal world observation receipt",
        )
        latest = self._transition_from_record(
            payload.get("latest_thermal_transition")
        )
        prior_world = super().encoded_snapshot()
        prior_state = self._thermal_state
        prior_revision = self._thermal_world_revision
        prior_receipt = self._thermal_world_observation_receipt_sha256
        try:
            super().restore_encoded(
                world_encoded,
                allow_authenticated_physical_manifest_migration=(
                    allow_authenticated_physical_manifest_migration
                ),
            )
            observation = super().observation_snapshot()
            self._thermal_anatomy.verify(
                tuple(item.region_id for item in observation.regions)
            )
            state.verify(
                self._thermal_anatomy.conductive_edges(observation.room_id),
                self._thermal_anatomy.bath_edges,
                self._thermal_anatomy.power_sources,
            )
            if revision != observation.revision or receipt != observation.authority_receipt_sha256:
                raise ValueError("thermal state does not bind the restored world")
            if latest is not None and (
                latest.world_revision_after != revision
                or latest.thermal_state_after_sha256 != _digest(_state_record(state))
            ):
                raise ValueError("latest thermal transition does not end at current state")
        except BaseException:
            super().restore_encoded(prior_world)
            self._thermal_state = prior_state
            self._thermal_world_revision = prior_revision
            self._thermal_world_observation_receipt_sha256 = prior_receipt
            raise
        self._thermal_state = state
        self._thermal_world_revision = revision
        self._thermal_world_observation_receipt_sha256 = receipt
        self._latest_thermal_transition = latest
        self._pending_thermal = None
        self._committed_thermal_tail = None

    def _transition_from_record(
        self, value: object
    ) -> ThermalTransitionReceipt | None:
        if value is None:
            return None
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "bath_transfers_into_nodes_microjoules",
            "conductive_transfers_microjoules",
            "duration_microseconds",
            "external_energy_into_nodes_microjoules",
            "local_region_id",
            "powered_into_nodes_microjoules",
            "schema",
            "thermal_state_after_sha256",
            "thermal_state_before_sha256",
            "world_execution_receipt_sha256",
            "world_revision_after",
            "world_revision_before",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != TRANSITION_SCHEMA
        ):
            raise ValueError("thermal transition fields changed")

        def signed_vector(name: str) -> tuple[int, ...]:
            raw = value.get(name)
            if not isinstance(raw, list):
                raise ValueError(f"thermal transition {name} changed")
            return tuple(_signed_integer(item, name) for item in raw)

        receipt = ThermalTransitionReceipt(
            world_execution_receipt_sha256=_sha(
                value.get("world_execution_receipt_sha256"),
                "thermal transition world execution",
            ),
            world_revision_before=_integer(
                value.get("world_revision_before"),
                "thermal transition prior revision",
            ),
            world_revision_after=_integer(
                value.get("world_revision_after"),
                "thermal transition successor revision",
            ),
            local_region_id=_identifier(
                value.get("local_region_id"), "thermal transition region"
            ),
            duration_microseconds=_integer(
                value.get("duration_microseconds"),
                "thermal transition duration",
                minimum=1,
            ),
            thermal_state_before_sha256=_sha(
                value.get("thermal_state_before_sha256"),
                "thermal predecessor state",
            ),
            thermal_state_after_sha256=_sha(
                value.get("thermal_state_after_sha256"),
                "thermal successor state",
            ),
            conductive_transfers_microjoules=signed_vector(
                "conductive_transfers_microjoules"
            ),
            bath_transfers_into_nodes_microjoules=signed_vector(
                "bath_transfers_into_nodes_microjoules"
            ),
            powered_into_nodes_microjoules=signed_vector(
                "powered_into_nodes_microjoules"
            ),
            external_energy_into_nodes_microjoules=_signed_integer(
                value.get("external_energy_into_nodes_microjoules"),
                "thermal external energy",
            ),
            authority_hmac_sha256=_sha(
                value.get("authority_hmac_sha256"),
                "thermal transition HMAC",
            ),
            authority_receipt_sha256=_sha(
                value.get("authority_receipt_sha256"),
                "thermal transition receipt",
            ),
        )
        if (
            receipt.world_revision_after != receipt.world_revision_before + 1
            or receipt.external_energy_into_nodes_microjoules
            != sum(receipt.bath_transfers_into_nodes_microjoules)
            + sum(receipt.powered_into_nodes_microjoules)
        ):
            raise ValueError("thermal transition conservation or revision changed")
        expected_signature = hmac.new(
            self._thermal_key,
            TRANSITION_DOMAIN + _canonical(receipt.payload()),
            hashlib.sha256,
        ).hexdigest()
        expected_receipt = _digest({
            "authority_hmac_sha256": expected_signature,
            "payload": receipt.payload(),
        })
        if (
            not hmac.compare_digest(
                expected_signature, receipt.authority_hmac_sha256
            )
            or expected_receipt != receipt.authority_receipt_sha256
            or receipt.record() != value
        ):
            raise ValueError("thermal transition authority changed")
        return receipt


__all__ = (
    "COUPLED_SCHEMA",
    "CoupledThermalAnatomy",
    "ThermalObservation",
    "ThermalEndpointObservation",
    "ThermalTransitionReceipt",
    "ThermallyCoupledEmbodimentWorldAuthority",
)
