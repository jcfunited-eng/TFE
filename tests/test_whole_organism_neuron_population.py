from __future__ import annotations

import hashlib
import hmac
import json
import math
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.substrate.ae_local_receptor import (
    AELocalReceptorAuthority,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    MechanismAvailability,
    MechanismKind,
    MountedMechanismSpec,
    create_mounted_mechanism_manifest,
)
from dsf_ai_service.substrate.whole_organism_neuron_population import (
    NeuronCausalCoupling,
    NeuronPopulationProfile,
    WholeOrganismNeuronPopulationOwner,
)


KEY = b"whole-organism-neuron-population-test-key-v1" * 2
TOPOLOGY = hashlib.sha256(b"neuron-population-topology").hexdigest()


def _substream(
    sense: PhysicalSense,
    *,
    frequency: int,
    topology_index: int = 0,
    identity_suffix: str = "",
) -> NativeSensorySubstreamInput:
    count = 96
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=(
            f"physical-{sense.value}-sensor-{topology_index}"
            f"{identity_suffix}"
        ),
        substream_id=(
            f"{sense.value}-path-{topology_index}{identity_suffix}"
        ),
        topology_index=topology_index,
        coordinates=(
            NativeAxisCoordinate(
                f"{sense.value}-axis",
                f"{sense.value}-coordinate-{topology_index}",
            ),
        ),
        physical_quantity=f"{sense.value}-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(
            Fraction(index, 512) for index in range(count)
        ),
        normalized_signal=tuple(
            math.sin(2 * math.pi * frequency * index / 512)
            for index in range(count)
        ),
        phase_turns=tuple(
            Fraction(index * frequency, count)
            for index in range(count)
        ),
    )


def _settlement(
    label: str,
    *,
    frequencies: tuple[int, ...],
    add_sight_path: bool = False,
    sight_only: bool = False,
    sight_topology_index: int = 0,
    sight_identity_suffix: str = "",
):
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if not sight_only or sense is PhysicalSense.SIGHT
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    observed = {
        sense: (
            (
                _substream(
                    sense,
                    frequency=frequencies[index],
                    topology_index=0,
                ),
                _substream(
                    sense,
                    frequency=frequencies[index] + 2,
                    topology_index=1,
                ),
            )
            if sense is PhysicalSense.SIGHT and add_sight_path
            else (
                _substream(
                    sense,
                    frequency=frequencies[index],
                    topology_index=(
                        sight_topology_index
                        if sense is PhysicalSense.SIGHT
                        else 0
                    ),
                    identity_suffix=(
                        sight_identity_suffix
                        if sense is PhysicalSense.SIGHT
                        else ""
                    ),
                ),
            )
        )
        for index, sense in enumerate(SENSE_ORDER)
        if states[sense] is SenseBoundaryState.OBSERVED
    }
    built = build_six_sense_full_field(
        assembly_id=f"neuron-population-{label}",
        source_time_start=Fraction(0),
        source_time_end=Fraction(96, 512),
        observed_substreams=observed,
        states=states,
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(f"physical-neuron-test:{label}",),
    )


def _manifest(*, chemistry_available: bool = False):
    mechanisms = [
        MountedMechanismSpec(
            mechanism_id=f"sense:{sense.value}",
            kind=MechanismKind.RECEPTOR_FAMILY,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema=f"test.{sense.value}.full-field.v1",
            parent_mechanism_ids=(),
            sense=sense.value,
            binds_full_field_roots=True,
            physical_quantity=f"{sense.value}-intensity",
            physical_unit="normalized-intensity",
            physical_extent=f"{sense.value}-receptor-paths",
            causal_clock="exact-source-time",
            transduction_authority_receipt_sha256=TOPOLOGY,
            custody_authority_receipt_sha256=TOPOLOGY,
        )
        for sense in SENSE_ORDER
    ]
    if chemistry_available:
        mechanisms.append(MountedMechanismSpec(
            mechanism_id="state:neurochemical-flow",
            kind=MechanismKind.STATEFUL,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema="test.neurochemical-flow.v1",
            parent_mechanism_ids=tuple(
                sorted(f"sense:{sense.value}" for sense in SENSE_ORDER)
            ),
        ))
    return create_mounted_mechanism_manifest(
        authority_key=KEY,
        manifest_id="canonical-six-receptor-neuron-population",
        topology_authority_receipt_sha256=TOPOLOGY,
        mechanisms=tuple(mechanisms),
    )


def _profile(*, max_neurons: int = 16) -> NeuronPopulationProfile:
    return NeuronPopulationProfile.create(
        profile_id=f"population-{max_neurons}",
        max_neurons=max_neurons,
        max_edges=128,
        max_tuples_per_neuron=128,
        max_response_history=4,
        max_state_bytes=4 * 1024 * 1024,
    )


def _owner(*, max_neurons: int = 16):
    return WholeOrganismNeuronPopulationOwner(
        authority_key=KEY,
        manifest_authority_key=KEY,
        manifest=_manifest(),
        profile=_profile(max_neurons=max_neurons),
    )


def test_neuron_sealing_does_not_rebuild_registry_per_neuron(
    monkeypatch,
    settlements,
):
    owner = _owner()
    settlement = settlements[0]
    witness_type = type(settlement.native_evidence_witness)
    original = witness_type.registry
    calls = 0

    def counted_registry(witness):
        nonlocal calls
        calls += 1
        return original(witness)

    monkeypatch.setattr(witness_type, "registry", counted_registry)
    prepared = owner.prepare(settlement)

    assert calls == 1
    assert calls < len(full_field_sensory_roots(settlement))
    owner.discard(prepared)


def _sight_trace(settlement):
    witness = next(
        value
        for value in settlement.native_evidence_witness.ports
        if value.sense == "sight"
    )
    registry = settlement.native_evidence_witness.registry()
    return json.loads(registry.resolve(
        witness.complete_l0_l4_trace_receipt_sha256,
        "test sight trace",
    ))


def _sight_signals(settlement):
    witness = next(
        value
        for value in settlement.native_evidence_witness.ports
        if value.sense == "sight"
    )
    registry = settlement.native_evidence_witness.registry()
    source = json.loads(registry.resolve(
        witness.source_evidence_stream_receipt_sha256,
        "test sight source",
    ))
    return tuple(value["signal"] for value in source["samples"])


@pytest.fixture(scope="module")
def settlements():
    base = _settlement(
        "base",
        frequencies=(3, 4, 5, 6, 7, 8),
    )
    repeated = _settlement(
        "repeated",
        frequencies=(3, 4, 5, 6, 7, 8),
    )
    changed = _settlement(
        "changed",
        frequencies=(9, 4, 5, 6, 7, 8),
    )
    topology = _settlement(
        "topology",
        frequencies=(9, 4, 5, 6, 7, 8),
        add_sight_path=True,
        sight_only=True,
    )
    return base, repeated, changed, topology


def test_all_six_families_keep_nonflat_complete_fields(settlements) -> None:
    owner = _owner()
    prepared = owner.prepare(settlements[0])
    owner.commit(prepared)

    assert {value.sense for value in owner.neurons} == {
        sense.value for sense in SENSE_ORDER
    }
    assert len(owner.neurons) == 6
    physical_commitments = []
    for neuron in owner.neurons:
        assert neuron.current_state == "perturbed"
        assert neuron.topology_receipt_sha256
        assert neuron.source_sample_count == 96
        evidence = json.loads(
            neuron.last_perturbed_full_evidence_json
        )
        assert {
            "boundary_receipt_sha256",
            "field_tuples",
            "kernel_basin_receipt_sha256",
            "source_evidence_stream_receipt_sha256",
            "source_sample_commitment_sha256",
            "source_sample_count",
            "topology_receipt_sha256",
        } <= set(evidence)
        for item in neuron.current_field_tuples:
            assert tuple(name for name, _value in item.fields) == (
                DSF_FIELD_ORDER
            )
        physical_commitments.append(
            neuron.source_sample_commitment_sha256
        )
    assert len(set(physical_commitments)) == 6
    assert owner.status()["reduced_approximation"] is False
    assert owner.status()["division_growth"] == "unavailable"


def test_exact_response_trajectory_never_injects_habituation(
    settlements,
) -> None:
    owner = _owner()
    owner.commit(owner.prepare(settlements[0]))
    owner.commit(owner.prepare(settlements[1]))
    sight = next(value for value in owner.neurons if value.sense == "sight")
    assert sight.response_trajectory[-1].response_relation_to_prior == (
        "identical"
    )

    owner.commit(owner.prepare(settlements[2]))
    sight = next(value for value in owner.neurons if value.sense == "sight")
    assert sight.response_trajectory[-1].response_relation_to_prior == (
        "changed"
    )
    assert (
        sight.response_trajectory[-1].source_sample_commitment_sha256
        != sight.response_trajectory[-2].source_sample_commitment_sha256
    )
    prior_trace = _sight_trace(settlements[1])
    changed_trace = _sight_trace(settlements[2])
    assert _sight_signals(settlements[1]) != _sight_signals(
        settlements[2]
    )
    assert prior_trace["L0_SEV"] != changed_trace["L0_SEV"]
    assert (
        prior_trace["L1_GateL1State"]
        != changed_trace["L1_GateL1State"]
    )
    assert (
        prior_trace["L2_GateInterpretation"]
        == changed_trace["L2_GateInterpretation"]
    )
    assert (
        prior_trace["L4_DSF"] == changed_trace["L4_DSF"]
    )
    assert all(
        not hasattr(response, "score")
        for response in sight.response_trajectory
    )


def test_repeated_identical_settlement_has_constant_topology_and_storage(
    settlements,
) -> None:
    owner = _owner()
    settlement = settlements[0]
    for _ in range(8):
        owner.commit(owner.prepare(settlement))

    stable_snapshot = owner.snapshot_encoded()
    stable_neuron_ids = tuple(value.neuron_id for value in owner.neurons)
    stable_edge_ids = tuple(
        value.authority_receipt_sha256 for value in owner.edges
    )
    for _ in range(128):
        owner.commit(owner.prepare(settlement))
        assert tuple(
            value.neuron_id for value in owner.neurons
        ) == stable_neuron_ids
        assert tuple(
            value.authority_receipt_sha256 for value in owner.edges
        ) == stable_edge_ids
        assert owner.snapshot_encoded() == stable_snapshot

    status = owner.status()
    assert status["neurons"] == 6
    assert status["edges"] == 0
    assert status["neurons"] <= status["neuron_capacity"]
    assert status["edges"] <= status["edge_capacity"]
    assert all(
        len(value.response_trajectory)
        == status["response_history_capacity"]
        for value in owner.neurons
    )
    assert status["state_bytes"] <= status["state_capacity_bytes"]
    assert (
        status["estimated_maximum_state_bytes"]
        == status["state_capacity_bytes"]
    )

    durable = json.loads(stable_snapshot)
    durable_keys: set[str] = set()

    def collect_keys(value: object) -> None:
        if isinstance(value, dict):
            durable_keys.update(value)
            for nested in value.values():
                collect_keys(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_keys(nested)

    collect_keys(durable)
    assert durable_keys.isdisjoint({
        "frames",
        "normalized_signal",
        "pcm",
        "pcm_s16le",
        "raw_pcm",
        "samples",
        "source_samples",
    })


def test_topology_change_adds_only_authenticated_path_and_quiesces_old(
    settlements,
) -> None:
    owner = _owner()
    owner.commit(owner.prepare(settlements[0]))
    owner.commit(owner.prepare(settlements[3]))

    assert len(owner.neurons) == 7
    perturbed = [
        value for value in owner.neurons
        if value.current_state == "perturbed"
    ]
    assert len(perturbed) == 2
    assert {value.sense for value in perturbed} == {"sight"}
    assert {value.topology_index for value in perturbed} == {0, 1}
    for neuron in owner.neurons:
        if neuron.current_state == "quiescent":
            assert all(
                item.fields
                == tuple((name, "0/1") for name in DSF_FIELD_ORDER)
                for item in neuron.current_field_tuples
            )


def test_tamper_capacity_rollback_and_cold_restore(settlements) -> None:
    owner = _owner()
    original_encoded = owner.snapshot_encoded()
    prepared = owner.prepare(settlements[0])
    changed = replace(
        prepared.staged_neurons[0],
        current_state="quiescent",
    )
    tampered = replace(
        prepared,
        staged_neurons=(changed,) + prepared.staged_neurons[1:],
    )
    with pytest.raises(ValueError, match="neuron authority changed"):
        owner.commit(tampered)
    with pytest.raises(RuntimeError, match="in-flight neuron mutation"):
        owner.snapshot_encoded()
    owner.discard(prepared)
    assert owner.snapshot_encoded() == original_encoded

    undo = owner.commit(owner.prepare(settlements[0]))
    encoded = owner.snapshot_encoded()
    restored = WholeOrganismNeuronPopulationOwner.restore_encoded(
        authority_key=KEY,
        manifest_authority_key=KEY,
        manifest=_manifest(),
        profile=_profile(),
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.neurons == owner.neurons
    owner.rollback(undo)
    assert owner.neurons == ()

    bounded = _owner(max_neurons=6)
    bounded.commit(bounded.prepare(settlements[0]))
    before = bounded.snapshot_encoded()
    with pytest.raises(RuntimeError, match="neuron capacity"):
        bounded.prepare(settlements[3])
    assert bounded.snapshot_encoded() == before

    corrupted = bytearray(encoded)
    corrupted[-2] = corrupted[-2] ^ 1
    with pytest.raises(ValueError):
        WholeOrganismNeuronPopulationOwner.restore_encoded(
            authority_key=KEY,
            manifest_authority_key=KEY,
            manifest=_manifest(),
            profile=_profile(),
            encoded=bytes(corrupted),
        )


def test_prepare_commit_and_rollback_reuse_exact_validated_encoding(
    settlements,
    monkeypatch,
) -> None:
    owner = _owner()
    owner.commit(owner.prepare(settlements[0]))
    prior_encoded = owner.snapshot_encoded()
    original_build = owner._build_encoded_locked
    build_calls = 0

    def counted_build():
        nonlocal build_calls
        build_calls += 1
        return original_build()

    monkeypatch.setattr(owner, "_build_encoded_locked", counted_build)
    prepared = owner.prepare(settlements[2])
    undo = owner.commit(prepared)

    assert build_calls == 1
    assert owner.snapshot_encoded() is undo._staged_encoded_state
    assert owner.snapshot_encoded() == undo._staged_encoded_state
    assert owner.snapshot_encoded() == original_build()
    tampered_undo = replace(
        undo,
        _prior_encoded_state=b"tampered-prior-neuron-state",
    )
    with pytest.raises(
        ValueError,
        match="committed neuron mutation is not current",
    ):
        owner.rollback(tampered_undo)
    assert owner.snapshot_encoded() is undo._staged_encoded_state
    owner.rollback(undo)
    assert build_calls == 1
    assert owner.snapshot_encoded() is undo._prior_encoded_state
    assert owner.snapshot_encoded() == prior_encoded


def test_neuron_mosaic_assembly_is_complete_exact_and_rollback_safe(
    settlements,
) -> None:
    settlement = settlements[0]
    owner = _owner()
    undo = owner.commit(owner.prepare(settlement))
    roots = full_field_sensory_roots(settlement)

    assembly = owner.issue_mosaic_assembly(settlement)

    assert assembly.full_field_roots == roots
    assert len(assembly.root_bindings) == len(roots) == 6
    assert len(assembly.co_perturbation_couplings) == 0
    assert len({
        value.neuron_id for value in assembly.root_bindings
    }) == len(roots)
    assert all(
        tuple(name for name, _field in field_tuple.fields)
        == DSF_FIELD_ORDER
        for binding in assembly.root_bindings
        for field_tuple in binding.response.field_tuples
    )
    owner.verify_mosaic_assembly(
        assembly,
        expected_roots=roots,
        expected_settlement_receipt_sha256=(
            settlement.authority_receipt_sha256
        ),
    )

    encoded = owner.snapshot_encoded()
    cold = WholeOrganismNeuronPopulationOwner.restore_encoded(
        authority_key=KEY,
        manifest_authority_key=KEY,
        manifest=_manifest(),
        profile=_profile(),
        encoded=encoded,
    )
    cold.verify_mosaic_assembly(
        assembly,
        expected_roots=roots,
        expected_settlement_receipt_sha256=(
            settlement.authority_receipt_sha256
        ),
    )

    with pytest.raises(ValueError, match="authority changed"):
        owner.verify_mosaic_assembly(replace(
            assembly,
            root_bindings=assembly.root_bindings[:-1],
        ))
    with pytest.raises(ValueError, match="authority changed"):
        owner.verify_mosaic_assembly(replace(
            assembly,
            co_perturbation_couplings=(
                NeuronCausalCoupling(
                    source_neuron_id=(
                        assembly.root_bindings[0].neuron_id
                    ),
                    target_neuron_id=(
                        assembly.root_bindings[1].neuron_id
                    ),
                    settlement_receipt_sha256=(
                        assembly.settlement_receipt_sha256
                    ),
                    authority_hmac_sha256="0" * 64,
                    authority_receipt_sha256="0" * 64,
                ),
            ),
        ))
    with pytest.raises(ValueError, match="roots changed"):
        owner.verify_mosaic_assembly(
            assembly,
            expected_roots=roots[:-1],
        )

    owner.rollback(undo)
    assert owner.neurons == ()
    assert owner.edges == ()
    with pytest.raises(
        ValueError,
        match="lacks one perturbed neuron response",
    ):
        owner.issue_mosaic_assembly(settlement)


def test_authenticated_legacy_current_projection_migrates_quiescent(
    settlements,
) -> None:
    owner = _owner()
    owner.commit(owner.prepare(settlements[0]))
    envelope = json.loads(owner.snapshot_encoded())

    def canonical(value):
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    for raw in envelope["body"]["neurons"]:
        raw.pop("current_local_receptor_activation")
        for response in raw["response_trajectory"]:
            response.pop("local_receptor_activation")
        payload = {
            name: value
            for name, value in raw.items()
            if name not in {
                "authority_hmac_sha256",
                "authority_receipt_sha256",
            }
        }
        signature = hmac.new(
            owner._neuron_key,
            b"guala-whole-organism-neuron-v1\0" + canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        raw["authority_hmac_sha256"] = signature
        raw["authority_receipt_sha256"] = hashlib.sha256(canonical({
            "authority_hmac_sha256": signature,
            "payload": payload,
        })).hexdigest()
    body = envelope["body"]
    envelope["state_hmac_sha256"] = hmac.new(
        owner._state_key,
        b"guala-whole-organism-neuron-state-v1\0" + canonical(body),
        hashlib.sha256,
    ).hexdigest()
    legacy_encoded = canonical(envelope)
    receptor_authority = AELocalReceptorAuthority(
        issuer_id="issuer:test-local-receptor",
        private_key_bytes=hashlib.sha256(
            b"whole-organism-neuron-legacy-receptor"
        ).digest(),
    )

    restored = WholeOrganismNeuronPopulationOwner.restore_encoded(
        authority_key=KEY,
        manifest_authority_key=KEY,
        manifest=_manifest(chemistry_available=True),
        profile=_profile(),
        encoded=legacy_encoded,
        local_receptor_verifier=receptor_authority.verifier_mount,
    )

    assert restored.neurons
    assert all(
        value.current_state == "quiescent"
        and value.current_local_receptor_activation is None
        for value in restored.neurons
    )
    assert all(value.response_trajectory for value in restored.neurons)
    assert restored.status()["unreconciled_legacy_neurons"] == len(
        restored.neurons
    )
