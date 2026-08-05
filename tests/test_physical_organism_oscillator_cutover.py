"""Decisive contracts for the nonsemantic physical organism closure."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.physical_oscillators import (
    PhysicalModalOscillator,
    PhysicalSensoryOscillatorBank,
    PhysicalSignalOscillator,
)
from dsf_ai_service.loom_model.structural_graph_state import (
    load_structural_graph,
    save_structural_graph,
    structural_graph_limits_from_environment,
    structural_registry_contract,
)
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import (
    Krimelack,
    LanguageKrimelack,
    ModalKrimelack,
    SensoryBank,
)


_ROOT = Path(__file__).resolve().parents[1]
_MIGRATED_GRAPH = Path(
    os.environ.get(
        "GUALA_MIGRATED_GRAPH_PROOF",
        "/tmp/guala-physical-runtime-migrated-20260728/"
        "guala_organism.sgr",
    )
)
_RETIRED_SOURCE_GRAPH = Path(
    os.environ.get(
        "GUALA_RETIRED_SOURCE_GRAPH_PROOF",
        "/tmp/guala-migration-post-unicode-20260728/"
        "guala_organism.sgr",
    )
)
_FORBIDDEN_MODULE_PARTS = (
    "binding_atlas",
    "gualaloom_v4_chi_atlas_l6",
    "gualaloom_v4_krimelack_dna",
    "resonant_chi",
    "retired_legacy_cognition",
)
_OSCILLATOR_FIELDS = (
    "dt",
    "events",
    "kappa",
    "label",
    "n_events",
    "omega_0",
    "phase",
    "t",
    "threshold",
    "winding",
)


def _state(value):
    if isinstance(value, float):
        return value.hex()
    if isinstance(value, list):
        return [_state(item) for item in value]
    if hasattr(value, "maxlen"):
        return {
            "items": [_state(item) for item in value],
            "maxlen": value.maxlen,
        }
    if isinstance(value, dict):
        return {
            key: _state(item)
            for key, item in sorted(value.items())
        }
    return value


def _physical_oscillator_state(value):
    return {
        field: _state(getattr(value, field))
        for field in _OSCILLATOR_FIELDS
    }


def _all_neurons(organism):
    return [
        neuron
        for hemisphere in organism.brain.hemispheres
        for neuron in hemisphere.cluster.neurons
    ]


def test_numeric_oscillator_arithmetic_is_bit_exact_to_retired_host():
    legacy = LanguageKrimelack()
    physical = PhysicalSignalOscillator(label="language")
    signals = (
        [0.0, 0.125, -0.25, 0.75, -1.0, 0.5],
        [1.25, -1.5, 0.03125, -0.0625] * 80,
        [0.2] * 400,
    )
    legacy.__dict__.pop("last_input_word", None)
    for signal in signals:
        legacy.feed(signal)
        physical.feed(signal)
        assert _physical_oscillator_state(physical) == (
            _physical_oscillator_state(legacy)
        )


def test_physical_bank_constructor_preserves_zero_state_without_word_api():
    legacy = SensoryBank()
    physical = PhysicalSensoryOscillatorBank()
    assert not hasattr(physical, "fire_for_word")
    assert tuple(physical.krimelacks) == tuple(legacy.krimelacks)
    for modality in physical.krimelacks:
        current = physical.krimelacks[modality]
        former = legacy.krimelacks[modality]
        assert isinstance(current, PhysicalModalOscillator)
        assert isinstance(former, ModalKrimelack)
        assert _physical_oscillator_state(current) == (
            _physical_oscillator_state(former)
        )
        assert current.modality == former.modality


def test_structural_registry_keeps_persisted_tags_and_full_fields():
    contract = structural_registry_contract()
    assert contract["language_krimelack"]["durable_fields"] == (
        _OSCILLATOR_FIELDS
    )
    assert contract["base_krimelack"]["durable_fields"] == (
        _OSCILLATOR_FIELDS
    )
    assert contract["modal_krimelack"]["durable_fields"] == tuple(
        sorted((*_OSCILLATOR_FIELDS, "modality"))
    )
    assert contract["sensory_bank"]["durable_fields"] == ("krimelacks",)
    neuron_fields = set(contract["loom_neuron"]["durable_fields"])
    assert {
        "_last_commit_chi",
        "_last_dsf",
        "chi_position",
        "krimelack",
        "krimelack_bank",
        "sensory_bank",
    }.issubset(neuron_fields)


def test_fresh_organism_import_closure_is_nonsemantic():
    code = """
import json
import sys
from dsf_ai_service.loom_model.embryo import Embryo
organism = Embryo(seed_size=4)
neurons = [
    neuron
    for hemisphere in organism.brain.hemispheres
    for neuron in hemisphere.cluster.neurons
]
forbidden = [
    name
    for name in sys.modules
    if any(part in name for part in %r)
]
print(json.dumps({
    "forbidden": sorted(forbidden),
    "neuron_count": len(neurons),
    "oscillator_modules": sorted({
        type(neuron.krimelack).__module__ for neuron in neurons
    }),
    "bank_modules": sorted({
        type(neuron.sensory_bank).__module__ for neuron in neurons
    }),
    "bank_keys": sorted({
        tuple(neuron.krimelack_bank) for neuron in neurons
    }),
    "labels": sorted({neuron.krimelack.label for neuron in neurons}),
    "primary_modalities": sorted({
        neuron.primary_modality for neuron in neurons
    }),
}))
""" % (_FORBIDDEN_MODULE_PARTS,)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    census = json.loads(result.stdout)
    assert census == {
        "bank_modules": [
            "dsf_ai_service.loom_model.physical_oscillators"
        ],
        "bank_keys": [[
            "physical_signal",
            "tactile",
            "olfactory",
            "gustatory",
            "visual",
            "auditory",
        ]],
        "forbidden": [],
        "labels": ["physical_signal"],
        "neuron_count": 32,
        "oscillator_modules": [
            "dsf_ai_service.loom_model.physical_oscillators"
        ],
        "primary_modalities": ["physical_signal"],
    }


def test_current_graph_module_has_no_static_retired_import_edge():
    source = (
        _ROOT
        / "dsf_ai_service/loom_model/structural_graph_state.py"
    ).read_text(encoding="utf-8")
    assert "import BindingAtlas" not in source
    assert "import ChiAtlas" not in source
    assert "import retire_neuron_legacy_bindings" not in source
    assert "gualaloom_v4_krimelack_dna import" not in source
    assert "resonant_chi import" not in source


@pytest.mark.skipif(
    not _MIGRATED_GRAPH.is_file(),
    reason="authenticated migrated production graph is not mounted",
)
def test_real_migrated_graph_cold_restore_is_byte_exact(tmp_path):
    source_bytes = _MIGRATED_GRAPH.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    assert source_sha256 == (
        "2b67f072469d547226a67a794b4401d3bd59b1c237b14c9449bb02e"
        "891b15ccf"
    )

    restored = load_structural_graph(
        _MIGRATED_GRAPH,
        expected_root_type=Embryo,
        limits=structural_graph_limits_from_environment(),
    )
    neurons = _all_neurons(restored)
    assert len(neurons) == 106
    assert sum(neuron._last_dsf is not None for neuron in neurons) == 106
    assert {
        type(neuron.krimelack) for neuron in neurons
    } == {PhysicalSignalOscillator}
    assert {
        type(neuron.sensory_bank) for neuron in neurons
    } == {PhysicalSensoryOscillatorBank}
    assert min(neuron.krimelack.n_events for neuron in neurons) == 493435
    assert max(neuron.krimelack.n_events for neuron in neurons) == 237170908
    assert all(
        len(neuron.krimelack.events) == 256 for neuron in neurons
    )
    assert all(
        modal.n_events == 0
        and modal.winding == 0
        and len(modal.events) == 0
        for neuron in neurons
        for modal in neuron.sensory_bank.krimelacks.values()
    )

    round_trip = tmp_path / "guala_organism.sgr"
    save_structural_graph(
        restored,
        round_trip,
        limits=structural_graph_limits_from_environment(),
    )
    assert round_trip.read_bytes() == source_bytes


@pytest.mark.skipif(
    not (
        _RETIRED_SOURCE_GRAPH.is_file()
        and _MIGRATED_GRAPH.is_file()
    ),
    reason="authenticated pre/post migration graphs are not mounted",
)
def test_migration_only_reader_produces_exact_clean_graph(tmp_path):
    output = tmp_path / "migrated.sgr"
    code = """
from pathlib import Path
from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.structural_graph_state import (
    save_structural_graph,
    structural_graph_limits_from_environment,
)
from tools.guala_legacy_organism_graph_reader import (
    load_authenticated_legacy_organism_graph,
)
organism = load_authenticated_legacy_organism_graph(
    Embryo,
    Path(%r),
)
neurons = [
    neuron
    for hemisphere in organism.brain.hemispheres
    for neuron in hemisphere.cluster.neurons
]
assert len(neurons) == 106
assert sum(neuron._last_dsf is not None for neuron in neurons) == 106
assert not any(hasattr(neuron, "binding_atlas") for neuron in neurons)
assert not any(hasattr(neuron, "chi_atlas") for neuron in neurons)
save_structural_graph(
    organism,
    Path(%r),
    limits=structural_graph_limits_from_environment(),
)
""" % (str(_RETIRED_SOURCE_GRAPH), str(output))
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert output.read_bytes() == _MIGRATED_GRAPH.read_bytes()


@pytest.mark.skipif(
    not _RETIRED_SOURCE_GRAPH.is_file(),
    reason="authenticated retired source graph is not mounted",
)
def test_current_reader_rejects_retired_graph_without_loading_it():
    code = """
import json
import sys
from pathlib import Path
from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.structural_graph_state import (
    StructuralGraphError,
    load_structural_graph,
    structural_graph_limits_from_environment,
)
try:
    load_structural_graph(
        Path(%r),
        expected_root_type=Embryo,
        limits=structural_graph_limits_from_environment(),
    )
except StructuralGraphError as error:
    message = str(error)
else:
    raise AssertionError("current reader admitted a retired graph")
forbidden = [
    name
    for name in sys.modules
    if any(part in name for part in %r)
]
print(json.dumps({"forbidden": sorted(forbidden), "message": message}))
""" % (str(_RETIRED_SOURCE_GRAPH), _FORBIDDEN_MODULE_PARTS)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {
        "forbidden": [],
        "message": (
            "retired neuronal cognition requires the authenticated "
            "one-way migration reader"
        ),
    }


@pytest.mark.skipif(
    not _MIGRATED_GRAPH.is_file(),
    reason="authenticated migrated production graph is not mounted",
)
def test_real_migrated_graph_cold_import_closure_is_nonsemantic():
    code = """
import json
import sys
from pathlib import Path
from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.structural_graph_state import (
    load_structural_graph,
    structural_graph_limits_from_environment,
)
organism = load_structural_graph(
    Path(%r),
    expected_root_type=Embryo,
    limits=structural_graph_limits_from_environment(),
)
neurons = [
    neuron
    for hemisphere in organism.brain.hemispheres
    for neuron in hemisphere.cluster.neurons
]
forbidden = [
    name
    for name in sys.modules
    if any(part in name for part in %r)
]
print(json.dumps({
    "dsf_count": sum(neuron._last_dsf is not None for neuron in neurons),
    "forbidden": sorted(forbidden),
    "neuron_count": len(neurons),
}))
""" % (str(_MIGRATED_GRAPH), _FORBIDDEN_MODULE_PARTS)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {
        "dsf_count": 106,
        "forbidden": [],
        "neuron_count": 106,
    }
