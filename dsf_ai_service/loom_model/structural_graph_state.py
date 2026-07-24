"""Bounded, code-free structural persistence for the Loom object graph.

The former organism/tapestry persistence path used ``pickle``.  Pickle keeps
an in-memory memo proportional to the entire graph and is executable input at
restore time.  This module stores the same graph as explicit typed nodes and
ordered edges in SQLite:

* only classes in the closed registry below may cross the boundary;
* only registered durable fields may cross the boundary;
* object/container aliases and cycles are preserved by explicit node ids;
* numpy values, dtype, shape, strides, and writeability are preserved;
* runtime process handles are excluded and rebuilt by existing restore hooks;
* traversal identity is held in one save-local map bounded by the node cap;
* two independently written passes must be byte-identical before publication;
* byte, node, and depth limits fail closed.

SQLite is storage framing only.  It does not interpret, reduce, score, or
otherwise alter DSF fields or cognition.
"""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import json
import math
import os
import sqlite3
import stat
import struct
import tempfile
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


SCHEMA = "guala.structural_graph.v1"
APPLICATION_ID = 0x47535231  # "GSR1"
USER_VERSION = 1
SQLITE_PAGE_SIZE = 4096
_CHECK_INTERVAL = 1024
_SCALAR_CACHE_CAPACITY = _CHECK_INTERVAL * 64
_NODE_BUFFER_BYTES = 8 * 1024 * 1024
_INLINE_ARRAY_BYTES = 1024 * 1024
_UNSET = object()
_IMMUTABLE_PENDING = object()


class StructuralGraphError(RuntimeError):
    """The structural artifact is incomplete, unsafe, or over capacity."""


@dataclass(frozen=True)
class StructuralGraphLimits:
    """Explicit resource boundary for one structural artifact."""

    max_encoded_bytes: int
    max_nodes: int
    max_depth: int

    def __post_init__(self) -> None:
        for name in ("max_encoded_bytes", "max_nodes", "max_depth"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise StructuralGraphError(
                    f"{name} must be a positive integer")


@dataclass(frozen=True)
class ObjectSpec:
    tag: str
    cls: type
    durable_fields: frozenset[str]
    runtime_fields: frozenset[str] = frozenset()


def _fields(value: str) -> frozenset[str]:
    return frozenset(part for part in value.split() if part)


def _object_specs() -> tuple[ObjectSpec, ...]:
    """Build the closed registry lazily to avoid Loom import cycles."""
    from dsf_ai_service.loom_model.binding_atlas import BindingAtlas
    from dsf_ai_service.loom_model.brain import LoomBrain
    from dsf_ai_service.loom_model.cluster import LoomCluster
    from dsf_ai_service.loom_model.cross_hemi import CrossHemiCouplings
    from dsf_ai_service.loom_model.embryo import Embryo
    from dsf_ai_service.loom_model.hemisphere import LoomHemisphere
    from dsf_ai_service.loom_model.mosaic import LoomMosaic
    from dsf_ai_service.loom_model.neuron import (
        CouplingsJij,
        DNAExpressionSite,
        FamiliarityFeedback,
        LawField,
        LoomNeuron,
        PsiLattice,
        SpikeBuffer,
    )
    from dsf_ai_service.loom_model.substrate_dna import (
        CochlearBankKrimelack,
        GustatoryKrimelack,
        OlfactoryKrimelack,
        TactileKrimelack,
        VisualKrimelack,
    )
    from dsf_ai_service.loom_model.tapestry import LoomTapestry
    from dsf_ai_service.sensory_krimelacks import OscillatorKrimelack
    from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import ChiAtlas, L6_TCL
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import (
        Krimelack,
        LanguageKrimelack,
        ModalKrimelack,
        SensoryBank,
    )
    from dsf_ai_service.v4.gualaloom_v4_trit_register import Trit, TritRegister
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
    from dsf_ai_service.visual_krimelack import AdaptingFoveaKrimelack
    from wave_spillover import Cell

    neuron_runtime = _fields(
        "_neuron_lock _spike_bus _word_firing_callback _mood_source")
    brain_runtime = _fields("_spike_bus _guala_ref")
    return (
        ObjectSpec(
            "embryo", Embryo,
            _fields(
                "brain brain_seed seed_size identity_uuid op hemi_by_op "
                "consensus strength arousal tick _N_initial _div_pool "
                "_total_divisions _fold_events_buffer "
                "_causal_growth_reservoirs "
                "_causal_growth_parent_cursors "
                "_causal_growth_organ_cursor "
                "_causal_growth_applied_claims "
                "_recent_input_signatures _growth_cap_hits "
                "_reflection_snapshots _scP _identity _goal"),
        ),
        ObjectSpec(
            "brain", LoomBrain,
            _fields(
                "brain_seed topology observable _topology_metrics "
                "hemispheres _hemi_map _last_fold_ids "
                "_injection_floor_skips"),
            brain_runtime,
        ),
        ObjectSpec(
            "hemisphere", LoomHemisphere,
            _fields(
                "hemi_id seed seed_size cluster projection_neuron_ids "
                "cross_hemi_couplings _incoming_spikes _op_tag _decay_mult"),
        ),
        ObjectSpec(
            "cluster", LoomCluster,
            _fields(
                "cluster_id n_neurons k_neighbors seed primary_modality "
                "observable neurons _neuron_map"),
        ),
        ObjectSpec(
            "cross_hemi_couplings", CrossHemiCouplings,
            _fields("n_modes targets J"),
        ),
        ObjectSpec(
            "loom_neuron", LoomNeuron,
            _fields(
                "neuron_id primary_modality observable psi_lattice "
                "spike_buffer couplings familiarity laws dna_site "
                "trit_register l6_tcl chi_atlas krimelack sensory_bank "
                "krimelack_bank binding_atlas _tick _last_dsf _last_events "
                "_last_commit_chi _last_commit_intensity "
                "_coupling_injection _coupling_signal_accum "
                "_coupling_modulation_delta _coupling_omega_shift "
                "_positional_phase_offset ring_pos ring_N _aff_gain "
                "_polarity _fold_count _fold_sustain_count _fold_ticks _q "
                "membrane_potential membrane_rest membrane_threshold "
                "tau_m_ms refractory_period_ms last_update_time_s "
                "refractory_until_s chi_position "
                "_recent_presynaptic_fires _incoming_synapse_weights "
                "_last_fire_time_s _recent_fire_timestamps "
                "_fire_breaker_trip_count _last_breaker_log_time_s "
                "_last_origin_transducer _omega_history _lane_P "
                "_expended_energy _last_energy_update_time_s "
                "_energy_block_count"),
            neuron_runtime,
        ),
        ObjectSpec("psi_lattice", PsiLattice, _fields("psi")),
        ObjectSpec("spike_buffer", SpikeBuffer, _fields("_buf")),
        ObjectSpec(
            "couplings_jij", CouplingsJij,
            _fields("n_modes neighbors ring_distances J"),
        ),
        ObjectSpec(
            "familiarity_feedback", FamiliarityFeedback,
            _fields("delta_base match_score delta_eff"),
        ),
        ObjectSpec(
            "law_field", LawField,
            _fields("law_id family weight params bounds"),
        ),
        ObjectSpec(
            "dna_expression_site", DNAExpressionSite, _fields("_blueprint")),
        ObjectSpec(
            "binding_atlas", BindingAtlas,
            _fields(
                "cells _concept_to_chi _lane_bindings "
                "_lane_concept_shape_to_idx _m_row _m_concepts "
                "_m_matrix _m_len"),
        ),
        ObjectSpec(
            "chi_atlas", ChiAtlas, _fields("band entries tick")),
        ObjectSpec(
            "l6_tcl", L6_TCL, _fields("n_start capture_threshold")),
        ObjectSpec(
            "language_krimelack", LanguageKrimelack,
            _fields(
                "label omega_0 kappa threshold dt phase winding events "
                "n_events t last_input_word"),
        ),
        ObjectSpec(
            "modal_krimelack", ModalKrimelack,
            _fields(
                "label omega_0 kappa threshold dt phase winding events "
                "n_events t modality"),
        ),
        ObjectSpec(
            "base_krimelack", Krimelack,
            _fields(
                "label omega_0 kappa threshold dt phase winding events "
                "n_events t"),
        ),
        ObjectSpec(
            "sensory_bank", SensoryBank, _fields("krimelacks")),
        ObjectSpec(
            "oscillator_krimelack", OscillatorKrimelack,
            _fields(
                "omega_0 kappa threshold dt phase winding events "
                "n_events t"),
        ),
        ObjectSpec(
            "tactile_krimelack", TactileKrimelack,
            _fields("_inner _tuning events omega_0 winding"),
        ),
        ObjectSpec(
            "olfactory_krimelack", OlfactoryKrimelack,
            _fields("_inner _tuning events omega_0 winding"),
        ),
        ObjectSpec(
            "gustatory_krimelack", GustatoryKrimelack,
            _fields("_inner _tuning events omega_0 winding"),
        ),
        ObjectSpec(
            "visual_krimelack", VisualKrimelack,
            _fields("_fovea _n_events _phase events omega_0 winding"),
        ),
        ObjectSpec(
            "cochlear_bank_krimelack", CochlearBankKrimelack,
            _fields("_n_events _phase events omega_0 winding"),
        ),
        ObjectSpec(
            "adapting_fovea_krimelack", AdaptingFoveaKrimelack,
            _fields(
                "omega_0 kappa_max phase winding_count events adapt_state "
                "adapt_tau recover_tau"),
        ),
        ObjectSpec(
            "trit_register", TritRegister,
            _fields("n lambda_parity trits parity_K"),
        ),
        ObjectSpec(
            "trit", Trit, _fields("phi_A phi_B phi_C w")),
        ObjectSpec(
            "dsf", DSF,
            _fields("D_k M_k R_rev U_star C_k P_k B_k S_UF _arr"),
        ),
        ObjectSpec(
            "wave_cell", Cell,
            _fields(
                "bindings aggregate_strength phase_vec last_tick saturated"),
        ),
        ObjectSpec(
            "mosaic", LoomMosaic,
            _fields(
                "name n_clusters neurons_per_cluster k_neighbors seed "
                "clusters _tick"),
        ),
        ObjectSpec(
            "tapestry", LoomTapestry,
            _fields(
                "name n_mosaics seed _tick mosaics _engine_prev_word"),
        ),
    )


def _registry() -> tuple[dict[type, ObjectSpec], dict[str, ObjectSpec]]:
    specs = _object_specs()
    by_type = {spec.cls: spec for spec in specs}
    by_tag = {spec.tag: spec for spec in specs}
    if len(by_type) != len(specs) or len(by_tag) != len(specs):
        raise StructuralGraphError("structural class registry is ambiguous")
    return by_type, by_tag


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _decode_json(raw: bytes | None, context: str) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as error:
        raise StructuralGraphError(
            f"{context} metadata is not canonical UTF-8 JSON") from error


def _int_bytes(value: int) -> bytes:
    if value == 0:
        return b"\x00"
    length = max(1, (value.bit_length() + 8) // 8)
    return value.to_bytes(length, "big", signed=True)


def _int_from_bytes(raw: bytes) -> int:
    if not raw:
        raise StructuralGraphError("integer payload is empty")
    value = int.from_bytes(raw, "big", signed=True)
    if _int_bytes(value) != raw:
        raise StructuralGraphError("integer payload is not canonical")
    return value


def _array_descriptor(
    array: np.ndarray,
) -> tuple[dict[str, Any], int | None, int]:
    if (
        array.dtype.hasobject
        or array.dtype.fields is not None
        or array.dtype.metadata is not None
    ):
        raise StructuralGraphError(
            "object or structured numpy arrays are forbidden")
    shape = tuple(int(value) for value in array.shape)
    strides = tuple(int(value) for value in array.strides)
    if array.size == 0:
        pointer = None
        span = 0
        origin = 0
    else:
        minimum = 0
        maximum = 0
        for size, stride in zip(shape, strides):
            delta = (size - 1) * stride
            if delta < 0:
                minimum += delta
            else:
                maximum += delta
        span = maximum - minimum + int(array.dtype.itemsize)
        pointer = int(array.__array_interface__["data"][0])
        pointer += minimum
        origin = -minimum
    meta = {
        "dtype": array.dtype.str,
        "shape": list(shape),
        "strides": list(strides),
        "origin": origin,
        "writeable": bool(array.flags.writeable),
    }
    return meta, pointer, span


def _validated_array_descriptor(
    meta: Mapping[str, Any],
    payload_size: int,
) -> tuple[np.dtype, tuple[int, ...], tuple[int, ...], int, bool]:
    try:
        dtype = np.dtype(meta["dtype"])
        shape = tuple(int(value) for value in meta["shape"])
        strides = tuple(int(value) for value in meta["strides"])
        origin = int(meta["origin"])
        writeable = meta["writeable"]
    except Exception as error:
        raise StructuralGraphError("numpy descriptor is invalid") from error
    if (
        dtype.hasobject
        or dtype.fields is not None
        or dtype.metadata is not None
    ):
        raise StructuralGraphError(
            "object or structured numpy arrays are forbidden")
    if (
        not isinstance(writeable, bool)
        or len(shape) != len(strides)
        or any(value < 0 for value in shape)
        or origin < 0
    ):
        raise StructuralGraphError("numpy descriptor shape is invalid")
    if math.prod(shape) == 0:
        if payload_size:
            raise StructuralGraphError("empty numpy array has a payload")
    else:
        minimum = 0
        maximum = 0
        for size, stride in zip(shape, strides):
            delta = (size - 1) * stride
            if delta < 0:
                minimum += delta
            else:
                maximum += delta
        expected = maximum - minimum + dtype.itemsize
        if payload_size != expected or origin != -minimum:
            raise StructuralGraphError("numpy byte span differs from descriptor")
    return dtype, shape, strides, origin, writeable


def _restore_array(
    connection: sqlite3.Connection,
    node_id: int,
    meta: Mapping[str, Any],
    payload_size: int,
) -> np.ndarray:
    dtype, shape, strides, origin, writeable = _validated_array_descriptor(
        meta, payload_size)
    if math.prod(shape) == 0:
        backing = bytearray(max(1, dtype.itemsize))
        array = np.ndarray(
            shape=shape,
            dtype=dtype,
            buffer=backing,
            offset=0,
            strides=strides,
        )
    else:
        backing = bytearray(payload_size)
        target = memoryview(backing)
        offset = 0
        with connection.blobopen(
                "nodes", "payload", node_id, readonly=True) as blob:
            while offset < payload_size:
                chunk = blob.read(min(1024 * 1024, payload_size - offset))
                if not chunk:
                    raise StructuralGraphError(
                        "numpy payload ended before its declared size")
                target[offset:offset + len(chunk)] = chunk
                offset += len(chunk)
        array = np.ndarray(
            shape=shape,
            dtype=dtype,
            buffer=backing,
            offset=origin,
            strides=strides,
        )
    if not writeable:
        array.flags.writeable = False
    return array


def _connect(path: Path, *, writable: bool) -> sqlite3.Connection:
    if writable:
        connection = sqlite3.connect(str(path), isolation_level=None)
        connection.execute(f"PRAGMA page_size={SQLITE_PAGE_SIZE}")
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA temp_store=FILE")
        connection.execute("PRAGMA locking_mode=EXCLUSIVE")
        return connection
    uri = f"{path.resolve().as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True, isolation_level=None)
    connection.execute("PRAGMA query_only=ON")
    return connection


class _GraphWriter:
    def __init__(
        self,
        path: Path,
        *,
        limits: StructuralGraphLimits,
        root_type: type,
    ):
        self.path = path
        self.limits = limits
        self.root_type = root_type
        self.by_type, _ = _registry()
        self.connection = _connect(path, writable=True)
        self.node_count = 0
        self.page_size = SQLITE_PAGE_SIZE
        self._scalar_cache: dict[
            tuple[str, bytes, bytes], int] = {}
        self._identity_index: dict[int, int] = {}
        self._node_buffer: list[
            tuple[int, str, str | None, bytes | None, bytes | None]] = []
        self._node_buffer_bytes = 0
        self._edge_buffer: list[
            tuple[int, int, str | None, int | None, int]] = []
        self._initialize()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            BEGIN EXCLUSIVE;
            CREATE TABLE metadata(
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL
            ) WITHOUT ROWID;
            CREATE TABLE nodes(
                node_id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                type_tag TEXT,
                meta BLOB,
                payload BLOB
            );
            CREATE TABLE edges(
                parent_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                field_name TEXT,
                key_id INTEGER,
                value_id INTEGER NOT NULL,
                PRIMARY KEY(parent_id, position)
            ) WITHOUT ROWID;
            CREATE TEMP TABLE scalar_work(
                kind TEXT NOT NULL,
                meta BLOB NOT NULL,
                payload BLOB NOT NULL,
                node_id INTEGER NOT NULL UNIQUE,
                PRIMARY KEY(kind,meta,payload)
            ) WITHOUT ROWID;
            """
        )

    def _capacity_check(self, *, force: bool = False) -> None:
        if not force and self.node_count % _CHECK_INTERVAL:
            return
        pages = int(self.connection.execute(
            "PRAGMA page_count").fetchone()[0])
        if pages * self.page_size > self.limits.max_encoded_bytes:
            raise StructuralGraphError(
                "structural artifact exceeded its encoded-byte capacity")

    def _new_node(
        self,
        kind: str,
        *,
        type_tag: str | None = None,
        meta: bytes | None = None,
        payload: bytes | None = None,
    ) -> int:
        self.node_count += 1
        if self.node_count > self.limits.max_nodes:
            raise StructuralGraphError(
                "structural artifact exceeded its node capacity")
        node_id = self.node_count
        node_bytes = (
            len(kind.encode("utf-8"))
            + (0 if type_tag is None else len(type_tag.encode("utf-8")))
            + (0 if meta is None else len(meta))
            + (0 if payload is None else len(payload))
        )
        if (
            self._node_buffer
            and self._node_buffer_bytes + node_bytes > _NODE_BUFFER_BYTES
        ):
            self._flush_nodes()
            self._capacity_check()
        self._node_buffer.append(
            (node_id, kind, type_tag, meta, payload))
        self._node_buffer_bytes += node_bytes
        if (
            len(self._node_buffer) >= _CHECK_INTERVAL
            or self._node_buffer_bytes >= _NODE_BUFFER_BYTES
        ):
            self._flush_nodes()
            self._capacity_check()
        return node_id

    def _flush_nodes(self) -> None:
        if not self._node_buffer:
            return
        self.connection.executemany(
            "INSERT INTO nodes("
            "node_id,kind,type_tag,meta,payload"
            ") VALUES(?,?,?,?,?)",
            self._node_buffer,
        )
        self._node_buffer.clear()
        self._node_buffer_bytes = 0

    def _new_blob_node(
        self,
        kind: str,
        *,
        type_tag: str | None = None,
        meta: bytes | None = None,
        payload_size: int,
    ) -> int:
        if (
            isinstance(payload_size, bool)
            or not isinstance(payload_size, int)
            or payload_size < 0
            or payload_size > self.limits.max_encoded_bytes
        ):
            raise StructuralGraphError("structural payload size is invalid")
        self.node_count += 1
        if self.node_count > self.limits.max_nodes:
            raise StructuralGraphError(
                "structural artifact exceeded its node capacity")
        self._flush_nodes()
        node_id = self.node_count
        self.connection.execute(
            "INSERT INTO nodes("
            "node_id,kind,type_tag,meta,payload"
            ") VALUES(?,?,?,?,zeroblob(?))",
            (node_id, kind, type_tag, meta, payload_size),
        )
        self._capacity_check()
        return node_id

    def _scalar_node(
        self,
        kind: str,
        *,
        meta: bytes | None = None,
        payload: bytes | None = None,
    ) -> int:
        """Intern immutable scalar values in the on-disk traversal index."""
        lookup_meta = b"" if meta is None else meta
        lookup_payload = b"" if payload is None else payload
        cache_key = (kind, lookup_meta, lookup_payload)
        cached = self._scalar_cache.get(cache_key)
        if cached is not None:
            return cached
        row = self.connection.execute(
            "SELECT node_id FROM scalar_work "
            "WHERE kind=? AND meta=? AND payload=?",
            (kind, lookup_meta, lookup_payload),
        ).fetchone()
        if row is not None:
            node_id = int(row[0])
            if len(self._scalar_cache) < _SCALAR_CACHE_CAPACITY:
                self._scalar_cache[cache_key] = node_id
            return node_id
        node_id = self._new_node(
            kind,
            meta=meta,
            payload=payload,
        )
        self.connection.execute(
            "INSERT INTO scalar_work(kind,meta,payload,node_id) "
            "VALUES(?,?,?,?)",
            (kind, lookup_meta, lookup_payload, node_id),
        )
        if len(self._scalar_cache) < _SCALAR_CACHE_CAPACITY:
            self._scalar_cache[cache_key] = node_id
        return node_id

    def _known_composite(self, value: Any) -> int | None:
        return self._identity_index.get(id(value))

    def _register_composite(self, value: Any, node_id: int) -> None:
        python_id = id(value)
        if python_id in self._identity_index:
            raise StructuralGraphError(
                "structural composite identity was registered twice")
        self._identity_index[python_id] = node_id

    def _edge(
        self,
        parent_id: int,
        position: int,
        *,
        value_id: int,
        field_name: str | None = None,
        key_id: int | None = None,
    ) -> None:
        self._edge_buffer.append(
            (parent_id, position, field_name, key_id, value_id))
        if len(self._edge_buffer) >= _CHECK_INTERVAL:
            self._flush_edges()

    def _flush_edges(self) -> None:
        if not self._edge_buffer:
            return
        self.connection.executemany(
            "INSERT INTO edges("
            "parent_id,position,field_name,key_id,value_id"
            ") VALUES(?,?,?,?,?)",
            self._edge_buffer,
        )
        self._edge_buffer.clear()

    def write_value(self, value: Any, *, depth: int = 0) -> int:
        if depth > self.limits.max_depth:
            raise StructuralGraphError(
                "structural artifact exceeded its nesting depth")
        if value is None:
            return self._scalar_node("none")
        if type(value) is bool:
            return self._scalar_node(
                "bool",
                payload=b"\x01" if value else b"\x00",
            )
        if type(value) is int:
            return self._scalar_node("int", payload=_int_bytes(value))
        if type(value) is float:
            return self._scalar_node(
                "float",
                payload=struct.pack(">d", value),
            )
        if type(value) is complex:
            return self._scalar_node(
                "complex", payload=struct.pack(">dd", value.real, value.imag))
        if type(value) is str:
            return self._scalar_node(
                "str",
                payload=value.encode("utf-8"),
            )
        if type(value) is bytes:
            return self._scalar_node("bytes", payload=value)
        if isinstance(value, np.generic):
            dtype = value.dtype
            if (
                dtype.hasobject
                or dtype.fields is not None
                or dtype.metadata is not None
            ):
                raise StructuralGraphError(
                    "object or structured numpy scalars are forbidden")
            return self._scalar_node(
                "numpy_scalar",
                meta=_canonical_json({"dtype": dtype.str}),
                payload=value.tobytes(),
            )

        known = self._known_composite(value)
        if known is not None:
            return known

        if isinstance(value, np.ndarray):
            meta, pointer, payload_size = _array_descriptor(value)
            encoded_meta = _canonical_json(meta)
            if payload_size <= _INLINE_ARRAY_BYTES:
                payload = (
                    b""
                    if payload_size == 0
                    else ctypes.string_at(pointer, payload_size)
                )
                node_id = self._new_node(
                    "ndarray",
                    meta=encoded_meta,
                    payload=payload,
                )
            else:
                node_id = self._new_blob_node(
                    "ndarray",
                    meta=encoded_meta,
                    payload_size=payload_size,
                )
                assert pointer is not None
                offset = 0
                with self.connection.blobopen(
                        "nodes", "payload", node_id) as blob:
                    while offset < payload_size:
                        length = min(
                            1024 * 1024, payload_size - offset)
                        blob.write(ctypes.string_at(pointer + offset, length))
                        offset += length
            self._register_composite(value, node_id)
            return node_id

        if type(value) is dict:
            node_id = self._new_node("dict")
            self._register_composite(value, node_id)
            for position, (key, item) in enumerate(value.items()):
                key_id = self.write_value(key, depth=depth + 1)
                value_id = self.write_value(item, depth=depth + 1)
                self._edge(
                    node_id, position, key_id=key_id, value_id=value_id)
            return node_id

        if type(value) in (list, tuple, set, frozenset) or isinstance(
                value, deque):
            if type(value) is list:
                kind = "list"
                meta = None
            elif type(value) is tuple:
                kind = "tuple"
                meta = None
            elif type(value) is set:
                kind = "set"
                meta = None
            elif type(value) is frozenset:
                kind = "frozenset"
                meta = None
            elif type(value) is deque:
                kind = "deque"
                meta = _canonical_json({"maxlen": value.maxlen})
            else:
                raise StructuralGraphError(
                    f"unregistered container subclass: {type(value)!r}")
            node_id = self._new_node(kind, meta=meta)
            self._register_composite(value, node_id)
            for position, item in enumerate(value):
                item_id = self.write_value(item, depth=depth + 1)
                self._edge(node_id, position, value_id=item_id)
            return node_id

        spec = self.by_type.get(type(value))
        if spec is None:
            raise StructuralGraphError(
                "unregistered structural class: "
                f"{type(value).__module__}.{type(value).__qualname__}")
        node_id = self._new_node("object", type_tag=spec.tag)
        self._register_composite(value, node_id)
        raw_state = dict(getattr(value, "__dict__", {}))
        present_runtime = spec.runtime_fields.intersection(raw_state)
        for field in present_runtime:
            raw_state.pop(field, None)
        unknown = set(raw_state).difference(spec.durable_fields)
        if unknown:
            raise StructuralGraphError(
                f"{spec.tag} has unregistered durable fields: "
                f"{sorted(unknown)}")
        for position, (field_name, item) in enumerate(raw_state.items()):
            if field_name not in spec.durable_fields:
                raise StructuralGraphError(
                    f"{spec.tag}.{field_name} is not a durable field")
            item_id = self.write_value(item, depth=depth + 1)
            self._edge(
                node_id,
                position,
                field_name=field_name,
                value_id=item_id,
            )
        return node_id

    def finish(self, root: Any) -> None:
        if type(root) is not self.root_type:
            raise StructuralGraphError(
                "structural root has an unexpected class")
        root_id = self.write_value(root)
        root_spec = self.by_type.get(type(root))
        if root_spec is None:
            raise StructuralGraphError("structural root is unregistered")
        metadata = {
            "schema": SCHEMA,
            "root_id": root_id,
            "root_type": root_spec.tag,
            "node_count": self.node_count,
        }
        self._flush_nodes()
        self._flush_edges()
        for key, value in metadata.items():
            self.connection.execute(
                "INSERT INTO metadata(key,value) VALUES(?,?)",
                (key, _canonical_json(value)),
            )
        self.connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
        self.connection.execute(f"PRAGMA user_version={USER_VERSION}")
        self.connection.execute("COMMIT")
        self._capacity_check(force=True)
        self.connection.execute("PRAGMA optimize")
        self.connection.close()
        size = self.path.stat().st_size
        if size > self.limits.max_encoded_bytes:
            raise StructuralGraphError(
                "structural artifact exceeded its encoded-byte capacity")


def _write_pass(
    root: Any,
    path: Path,
    *,
    limits: StructuralGraphLimits,
    root_type: type,
) -> None:
    writer = _GraphWriter(path, limits=limits, root_type=root_type)
    try:
        writer.finish(root)
    except BaseException:
        with contextlib.suppress(Exception):
            writer.connection.close()
        raise


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_structural_graph(
    root: Any,
    path: str | os.PathLike[str],
    *,
    limits: StructuralGraphLimits,
    persistence_admission: Any | None = None,
) -> dict[str, Any]:
    """Write two identical bounded passes, then atomically publish one."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
            prefix="guala-structural-graph-") as temporary:
        first = Path(temporary) / "first.sgr"
        second = Path(temporary) / "second.sgr"
        _write_pass(
            root, first, limits=limits, root_type=type(root))
        _write_pass(
            root, second, limits=limits, root_type=type(root))
        first_digest = _sha256_file(first)
        second_digest = _sha256_file(second)
        if (
            first_digest != second_digest
            or first.stat().st_size != second.stat().st_size
        ):
            raise StructuralGraphError(
                "structural graph mutated during serialization")
        if persistence_admission is None:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
            )
            temporary_target = Path(temporary_name)
            try:
                with (
                    second.open("rb") as source,
                    os.fdopen(descriptor, "wb") as target,
                ):
                    descriptor = -1
                    for chunk in iter(
                            lambda: source.read(1024 * 1024), b""):
                        target.write(chunk)
                    target.flush()
                    os.fsync(target.fileno())
                os.replace(temporary_target, destination)
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
                with contextlib.suppress(FileNotFoundError):
                    temporary_target.unlink()
            directory_fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        else:
            persistence_admission.copy_regular_file(second, destination)
        return {
            "schema": SCHEMA,
            "bytes": second.stat().st_size,
            "sha256": second_digest,
        }


class _GraphReader:
    def __init__(
        self,
        path: Path,
        *,
        limits: StructuralGraphLimits,
        expected_root_type: type,
    ):
        self.path = path
        self.limits = limits
        self.expected_root_type = expected_root_type
        _, self.by_tag = _registry()
        self._validate_path()
        self.connection = _connect(path, writable=False)
        self.nodes: list[Any] = []
        self._validate()

    def _validate_path(self) -> None:
        try:
            info = os.lstat(self.path)
        except OSError as error:
            raise StructuralGraphError(
                "structural artifact cannot be inspected") from error
        if not stat.S_ISREG(info.st_mode) or os.path.islink(self.path):
            raise StructuralGraphError(
                "structural artifact is not a regular file")
        if info.st_size > self.limits.max_encoded_bytes:
            raise StructuralGraphError(
                "structural artifact exceeds its encoded-byte capacity")

    def _validate(self) -> None:
        quick = self.connection.execute("PRAGMA quick_check").fetchall()
        if quick != [("ok",)]:
            raise StructuralGraphError("structural SQLite integrity failed")
        application_id = int(self.connection.execute(
            "PRAGMA application_id").fetchone()[0])
        user_version = int(self.connection.execute(
            "PRAGMA user_version").fetchone()[0])
        if application_id != APPLICATION_ID or user_version != USER_VERSION:
            raise StructuralGraphError("structural schema identity differs")
        objects = self.connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()
        names = {(row[0], row[1]) for row in objects}
        if names != {
            ("table", "edges"),
            ("table", "metadata"),
            ("table", "nodes"),
        }:
            raise StructuralGraphError(
                "structural artifact has an unexpected SQLite object")
        metadata_rows = self.connection.execute(
            "SELECT key,value FROM metadata ORDER BY key").fetchall()
        metadata = {
            key: _decode_json(value, f"metadata.{key}")
            for key, value in metadata_rows
        }
        if set(metadata) != {
            "node_count", "root_id", "root_type", "schema"
        }:
            raise StructuralGraphError(
                "structural metadata contract differs")
        if metadata["schema"] != SCHEMA:
            raise StructuralGraphError("structural schema differs")
        node_count = metadata["node_count"]
        root_id = metadata["root_id"]
        if (
            isinstance(node_count, bool)
            or not isinstance(node_count, int)
            or node_count <= 0
            or node_count > self.limits.max_nodes
            or isinstance(root_id, bool)
            or not isinstance(root_id, int)
            or not 1 <= root_id <= node_count
        ):
            raise StructuralGraphError("structural node census is invalid")
        actual_count, minimum, maximum = self.connection.execute(
            "SELECT COUNT(*),MIN(node_id),MAX(node_id) FROM nodes"
        ).fetchone()
        if (
            actual_count != node_count
            or minimum != 1
            or maximum != node_count
        ):
            raise StructuralGraphError("structural node ids are not contiguous")
        expected_spec = next(
            (
                spec for spec in self.by_tag.values()
                if spec.cls is self.expected_root_type
            ),
            None,
        )
        if expected_spec is None or metadata["root_type"] != expected_spec.tag:
            raise StructuralGraphError("structural root type differs")
        root_row = self.connection.execute(
            "SELECT kind,type_tag FROM nodes WHERE node_id=?",
            (root_id,),
        ).fetchone()
        if root_row != ("object", expected_spec.tag):
            raise StructuralGraphError("structural root node differs")
        dangling = self.connection.execute(
            """
            SELECT COUNT(*) FROM edges AS e
            LEFT JOIN nodes AS p ON p.node_id=e.parent_id
            LEFT JOIN nodes AS v ON v.node_id=e.value_id
            LEFT JOIN nodes AS k ON k.node_id=e.key_id
            WHERE p.node_id IS NULL OR v.node_id IS NULL
               OR (e.key_id IS NOT NULL AND k.node_id IS NULL)
            """
        ).fetchone()[0]
        if dangling:
            raise StructuralGraphError("structural edge has a dangling node")
        self.root_id = int(root_id)
        self.node_count = int(node_count)
        self.nodes = [_UNSET] * (self.node_count + 1)

    def _node_row(
        self, node_id: int
    ) -> tuple[str, str | None, bytes | None, int]:
        row = self.connection.execute(
            "SELECT kind,type_tag,meta,length(payload) "
            "FROM nodes WHERE node_id=?",
            (node_id,),
        ).fetchone()
        if row is None:
            raise StructuralGraphError("structural node is absent")
        return row[0], row[1], row[2], int(row[3] or 0)

    def _iter_edges(
        self, node_id: int
    ) -> Iterable[tuple[int, str | None, int | None, int]]:
        cursor = self.connection.execute(
            "SELECT position,field_name,key_id,value_id FROM edges "
            "WHERE parent_id=? ORDER BY position",
            (node_id,),
        )
        expected = 0
        for position, field_name, key_id, value_id in cursor:
            if position != expected:
                raise StructuralGraphError(
                    "structural edge positions are not contiguous")
            yield int(position), field_name, key_id, int(value_id)
            expected += 1

    def _payload(self, node_id: int, payload_size: int) -> bytes:
        if payload_size > self.limits.max_encoded_bytes:
            raise StructuralGraphError(
                "structural payload exceeds encoded capacity")
        row = self.connection.execute(
            "SELECT payload FROM nodes WHERE node_id=?",
            (node_id,),
        ).fetchone()
        if row is None:
            raise StructuralGraphError("structural node payload is absent")
        payload = b"" if row[0] is None else bytes(row[0])
        if len(payload) != payload_size:
            raise StructuralGraphError(
                "structural payload size changed during restore")
        return payload

    def read_value(self, node_id: int, *, depth: int = 0) -> Any:
        if depth > self.limits.max_depth:
            raise StructuralGraphError(
                "structural artifact exceeded its nesting depth")
        existing = self.nodes[node_id]
        if existing is _IMMUTABLE_PENDING:
            raise StructuralGraphError(
                "structural graph contains an immutable-container cycle")
        if existing is not _UNSET:
            return existing
        kind, type_tag, meta_raw, payload_size = self._node_row(node_id)
        meta = _decode_json(meta_raw, f"node {node_id}")

        if kind == "none":
            payload = self._payload(node_id, payload_size)
            value = None
        elif kind == "bool":
            payload = self._payload(node_id, payload_size)
            if payload not in (b"\x00", b"\x01"):
                raise StructuralGraphError("boolean payload is invalid")
            value = payload == b"\x01"
        elif kind == "int":
            payload = self._payload(node_id, payload_size)
            value = _int_from_bytes(payload)
        elif kind == "float":
            payload = self._payload(node_id, payload_size)
            if len(payload) != 8:
                raise StructuralGraphError("float payload is invalid")
            value = struct.unpack(">d", payload)[0]
        elif kind == "complex":
            payload = self._payload(node_id, payload_size)
            if len(payload) != 16:
                raise StructuralGraphError("complex payload is invalid")
            real, imaginary = struct.unpack(">dd", payload)
            value = complex(real, imaginary)
        elif kind == "str":
            payload = self._payload(node_id, payload_size)
            try:
                value = payload.decode("utf-8")
            except UnicodeDecodeError as error:
                raise StructuralGraphError(
                    "string payload is not UTF-8") from error
        elif kind == "bytes":
            value = self._payload(node_id, payload_size)
        elif kind == "numpy_scalar":
            payload = self._payload(node_id, payload_size)
            if not isinstance(meta, dict) or set(meta) != {"dtype"}:
                raise StructuralGraphError("numpy scalar metadata differs")
            dtype = np.dtype(meta["dtype"])
            if (
                dtype.hasobject
                or dtype.fields is not None
                or dtype.metadata is not None
                or len(payload) != dtype.itemsize
            ):
                raise StructuralGraphError("numpy scalar payload differs")
            value = np.frombuffer(payload, dtype=dtype, count=1)[0]
        elif kind == "ndarray":
            if not isinstance(meta, dict):
                raise StructuralGraphError("numpy metadata is absent")
            value = _restore_array(
                self.connection, node_id, meta, payload_size)
            self.nodes[node_id] = value
            return value
        elif kind == "dict":
            value = {}
            self.nodes[node_id] = value
            for _, field_name, key_id, value_id in self._iter_edges(node_id):
                if field_name is not None or key_id is None:
                    raise StructuralGraphError("dictionary edge differs")
                key = self.read_value(int(key_id), depth=depth + 1)
                item = self.read_value(value_id, depth=depth + 1)
                value[key] = item
            return value
        elif kind in {"list", "tuple", "set", "frozenset", "deque"}:
            if kind == "list":
                value = []
                self.nodes[node_id] = value
                for _, field, key, value_id in self._iter_edges(node_id):
                    if field is not None or key is not None:
                        raise StructuralGraphError("sequence edge differs")
                    value.append(
                        self.read_value(value_id, depth=depth + 1))
                return value
            if kind == "deque":
                if (
                    not isinstance(meta, dict)
                    or set(meta) != {"maxlen"}
                    or (
                        meta["maxlen"] is not None
                        and (
                            isinstance(meta["maxlen"], bool)
                            or not isinstance(meta["maxlen"], int)
                            or meta["maxlen"] <= 0
                        )
                    )
                ):
                    raise StructuralGraphError("deque metadata differs")
                value = deque(maxlen=meta["maxlen"])
                self.nodes[node_id] = value
                for _, field, key, value_id in self._iter_edges(node_id):
                    if field is not None or key is not None:
                        raise StructuralGraphError("sequence edge differs")
                    value.append(
                        self.read_value(value_id, depth=depth + 1))
                return value
            if kind == "set":
                value = set()
                self.nodes[node_id] = value
                for _, field, key, value_id in self._iter_edges(node_id):
                    if field is not None or key is not None:
                        raise StructuralGraphError("sequence edge differs")
                    value.add(
                        self.read_value(value_id, depth=depth + 1))
                return value
            self.nodes[node_id] = _IMMUTABLE_PENDING
            items = []
            for _, field, key, value_id in self._iter_edges(node_id):
                if field is not None or key is not None:
                    raise StructuralGraphError("sequence edge differs")
                items.append(self.read_value(value_id, depth=depth + 1))
            if kind == "tuple":
                value = tuple(items)
            else:
                value = frozenset(items)
            self.nodes[node_id] = value
            return value
        elif kind == "object":
            spec = self.by_tag.get(type_tag or "")
            if spec is None:
                raise StructuralGraphError(
                    f"structural class tag is unregistered: {type_tag!r}")
            value = spec.cls.__new__(spec.cls)
            self.nodes[node_id] = value
            state: dict[str, Any] = {}
            for _, field_name, key_id, value_id in self._iter_edges(node_id):
                if (
                    key_id is not None
                    or field_name is None
                    or field_name not in spec.durable_fields
                    or field_name in state
                ):
                    raise StructuralGraphError(
                        f"{spec.tag} field edge differs")
                state[field_name] = self.read_value(
                    value_id, depth=depth + 1)
            setter = getattr(spec.cls, "__setstate__", None)
            if setter is not None:
                setter(value, state)
            else:
                value.__dict__.update(state)
            runtime_overlap = spec.runtime_fields.intersection(state)
            if runtime_overlap:
                raise StructuralGraphError(
                    f"{spec.tag} restored runtime fields: "
                    f"{sorted(runtime_overlap)}")
            return value
        else:
            raise StructuralGraphError(
                f"structural node kind is unknown: {kind!r}")

        if next(iter(self._iter_edges(node_id)), None) is not None:
            raise StructuralGraphError(
                f"scalar structural node {node_id} has edges")
        self.nodes[node_id] = value
        return value

    def read_root(self) -> Any:
        root = self.read_value(self.root_id)
        if type(root) is not self.expected_root_type:
            raise StructuralGraphError(
                "restored structural root has an unexpected class")
        if any(value is _UNSET for value in self.nodes[1:]):
            raise StructuralGraphError(
                "structural artifact contains unreachable nodes")
        return root

    def close(self) -> None:
        self.connection.close()


def load_structural_graph(
    path: str | os.PathLike[str],
    *,
    expected_root_type: type,
    limits: StructuralGraphLimits,
) -> Any:
    """Validate and reconstruct one closed structural graph."""
    reader = _GraphReader(
        Path(path),
        limits=limits,
        expected_root_type=expected_root_type,
    )
    try:
        return reader.read_root()
    finally:
        reader.close()


def structural_registry_contract() -> dict[str, dict[str, tuple[str, ...]]]:
    """Expose the closed field contract for parity tests and audits."""
    return {
        spec.tag: {
            "durable_fields": tuple(sorted(spec.durable_fields)),
            "runtime_fields": tuple(sorted(spec.runtime_fields)),
        }
        for spec in _object_specs()
    }


def structural_graph_limits_from_environment() -> StructuralGraphLimits:
    """Read explicit infrastructure capacities; never cognition thresholds."""
    values = {}
    sources = {
        "max_encoded_bytes": (
            "GUALA_MAX_STRUCTURAL_GRAPH_BYTES",
            os.environ.get(
                "GUALA_MAX_COLD_GENERATION_BYTES",
                str(2 * 1024 * 1024 * 1024),
            ),
        ),
        "max_nodes": (
            "GUALA_MAX_STRUCTURAL_GRAPH_NODES",
            "4000000",
        ),
        "max_depth": (
            "GUALA_MAX_STRUCTURAL_GRAPH_DEPTH",
            "256",
        ),
    }
    for field, (name, fallback) in sources.items():
        raw = os.environ.get(name, fallback)
        try:
            value = int(raw)
        except (TypeError, ValueError) as error:
            raise StructuralGraphError(
                f"{name} must be a positive integer") from error
        if value <= 0:
            raise StructuralGraphError(
                f"{name} must be a positive integer")
        values[field] = value
    return StructuralGraphLimits(**values)


__all__ = [
    "SCHEMA",
    "StructuralGraphError",
    "StructuralGraphLimits",
    "load_structural_graph",
    "save_structural_graph",
    "structural_graph_limits_from_environment",
    "structural_registry_contract",
]
