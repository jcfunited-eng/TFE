from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.chemical_receiver import (
    CHEMICAL_AFFINE_CONSTRAINT_ID,
    KINETIC_RATE_TRANSITIONS,
    ChemicalBackendAuthority,
    ChemicalTimeUnitAuthority,
    CertifiedReceiverState,
    ExactReceiverState,
    MountedActivationSusceptibility,
    MountedChemicalRate,
    NativeActivationInterval,
    ReceiverEvolutionAuthority,
    ReceiverEvolutionStatus,
    ReceiverTransition,
    activation_susceptibility_authority_receipt_payload,
    chemical_backend_authority_receipt_payload,
    chemical_rate_authority_receipt_payload,
    chemical_time_unit_authority_receipt_payload,
    evolve_chemical_receiver,
    exact_receiver_state_receipt_payload,
    initial_receiver_authority_receipt_payload,
    native_activation_interval_receipt_payload,
    receiver_evolution_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)


PROFILE = b'{"schema":"glew.chemical_receiver.flux_coupling_test_profile.v1"}'


def _fact(name: str) -> bytes:
    return (
        '{"fact":"' + name + '","schema":"glew.test.physical_receipt.v1"}'
    ).encode("utf-8")


def _registry(payloads: tuple[bytes, ...]) -> ReceiptRegistry:
    unique = {receipt_sha256(payload): payload for payload in payloads}
    return ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=tuple(unique[digest] for digest in sorted(unique)),
    )


def _bounds(value) -> tuple[Fraction, Fraction]:
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


@dataclass(frozen=True)
class Scenario:
    state: ExactReceiverState
    authority: ReceiverEvolutionAuthority
    time_unit: ChemicalTimeUnitAuthority
    backend: ChemicalBackendAuthority
    susceptibility: MountedActivationSusceptibility
    rates: tuple[MountedChemicalRate, ...]
    interval: NativeActivationInterval
    payloads: tuple[bytes, ...]
    registry: ReceiptRegistry


def _initial_scenario(
    *,
    port_id: str = "story-vision.native-port-0",
    source_time_start: Fraction = Fraction(0),
    source_time_end: Fraction = Fraction(1),
    components: tuple[Fraction, Fraction, Fraction] = (
        Fraction(1),
        Fraction(0),
        Fraction(0),
    ),
    susceptibility_value: Fraction = Fraction(1, 2),
    rate_values: tuple[Fraction, Fraction, Fraction] = (
        Fraction(1, 3),
        Fraction(1, 5),
        Fraction(1, 7),
    ),
    signed_native_signal: Fraction = Fraction(-2, 5),
) -> Scenario:
    time_derivation = _fact(f"{port_id}:physical-time-derivation")
    time_payload = chemical_time_unit_authority_receipt_payload(
        authority_id=f"{port_id}:time-authority",
        time_unit_id=f"{port_id}:local-physical-tick",
        seconds_per_unit=Fraction(1, 1000),
        derivation_receipt_sha256=receipt_sha256(time_derivation),
    )
    time_unit = ChemicalTimeUnitAuthority(
        f"{port_id}:time-authority",
        f"{port_id}:local-physical-tick",
        Fraction(1, 1000),
        receipt_sha256(time_derivation),
        receipt_sha256(time_payload),
    )

    backend_payload = chemical_backend_authority_receipt_payload(
        authority_id=f"{port_id}:certified-backend",
        working_precision_bits=256,
    )
    backend = ChemicalBackendAuthority(
        f"{port_id}:certified-backend",
        256,
        receipt_sha256(backend_payload),
    )

    native_signal_unit = "native-signed-boundary-flux"
    signal_unit_authority = _fact(f"{port_id}:native-signal-unit")
    susceptibility_derivation = _fact(
        f"{port_id}:R-to-A-susceptibility-derivation"
    )
    susceptibility_payload = activation_susceptibility_authority_receipt_payload(
        susceptibility_id=f"{port_id}:R-to-A-susceptibility",
        port_id=port_id,
        susceptibility_per_native_signal_unit_per_time_unit=(
            susceptibility_value
        ),
        native_signal_unit=native_signal_unit,
        native_signal_unit_authority_receipt_sha256=receipt_sha256(
            signal_unit_authority
        ),
        time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
        derivation_receipt_sha256=receipt_sha256(susceptibility_derivation),
    )
    susceptibility = MountedActivationSusceptibility(
        f"{port_id}:R-to-A-susceptibility",
        port_id,
        susceptibility_value,
        native_signal_unit,
        receipt_sha256(signal_unit_authority),
        time_unit.authority_receipt_sha256,
        receipt_sha256(susceptibility_derivation),
        receipt_sha256(susceptibility_payload),
    )

    rate_derivations = []
    rate_payloads = []
    rates = []
    for transition, value in zip(
        KINETIC_RATE_TRANSITIONS,
        rate_values,
        strict=True,
    ):
        derivation = _fact(f"{port_id}:{transition.value}:derivation")
        rate_id = f"{port_id}:{transition.value}:rate"
        payload = chemical_rate_authority_receipt_payload(
            rate_id=rate_id,
            port_id=port_id,
            transition=transition,
            rate_per_time_unit=value,
            time_unit_authority_receipt_sha256=(
                time_unit.authority_receipt_sha256
            ),
            derivation_receipt_sha256=receipt_sha256(derivation),
        )
        rates.append(
            MountedChemicalRate(
                rate_id,
                port_id,
                transition,
                value,
                time_unit.authority_receipt_sha256,
                receipt_sha256(derivation),
                receipt_sha256(payload),
            )
        )
        rate_derivations.append(derivation)
        rate_payloads.append(payload)
    ordered_rates = tuple(rates)

    initial_derivation = _fact(f"{port_id}:initial-condition-derivation")
    resting, active, desensitized = components
    initial_authority_payload = initial_receiver_authority_receipt_payload(
        initial_condition_id=f"{port_id}:initial-condition",
        port_id=port_id,
        source_time=source_time_start,
        time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
        total_receptor_mass=Fraction(1),
        resting_mass=resting,
        active_mass=active,
        desensitized_mass=desensitized,
        derivation_receipt_sha256=receipt_sha256(initial_derivation),
    )
    state_payload = exact_receiver_state_receipt_payload(
        port_id=port_id,
        source_time=source_time_start,
        time_unit_id=time_unit.time_unit_id,
        time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
        total_receptor_mass=Fraction(1),
        resting_mass=resting,
        active_mass=active,
        desensitized_mass=desensitized,
        initial_authority_receipt_sha256=receipt_sha256(
            initial_authority_payload
        ),
    )
    state = ExactReceiverState(
        port_id,
        source_time_start,
        time_unit.time_unit_id,
        time_unit.authority_receipt_sha256,
        Fraction(1),
        resting,
        active,
        desensitized,
        f"{port_id}:initial-condition",
        receipt_sha256(initial_derivation),
        receipt_sha256(initial_authority_payload),
        receipt_sha256(state_payload),
        state_payload,
    )

    observation = _fact(
        f"{port_id}:native-observation:{source_time_start}:{source_time_end}"
    )
    interval_payload = native_activation_interval_receipt_payload(
        interval_id=f"{port_id}:interval:{source_time_start}:{source_time_end}",
        port_id=port_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
        activation_susceptibility_receipt_sha256=(
            susceptibility.authority_receipt_sha256
        ),
        signed_native_signal=signed_native_signal,
        native_signal_unit=native_signal_unit,
        native_signal_unit_authority_receipt_sha256=receipt_sha256(
            signal_unit_authority
        ),
        native_observation_receipt_sha256=receipt_sha256(observation),
    )
    interval = NativeActivationInterval(
        f"{port_id}:interval:{source_time_start}:{source_time_end}",
        port_id,
        source_time_start,
        source_time_end,
        time_unit.authority_receipt_sha256,
        susceptibility.authority_receipt_sha256,
        signed_native_signal,
        native_signal_unit,
        receipt_sha256(signal_unit_authority),
        receipt_sha256(observation),
        receipt_sha256(interval_payload),
    )

    authority_id = f"{port_id}:evolution:{source_time_start}:{source_time_end}"
    authority_payload = receiver_evolution_authority_receipt_payload(
        authority_id=authority_id,
        port_id=port_id,
        prior_state_receipt_sha256=state.receipt_sha256,
        activation_interval_receipt_sha256=interval.interval_receipt_sha256,
        activation_susceptibility_receipt_sha256=(
            susceptibility.authority_receipt_sha256
        ),
        ordered_rate_receipt_sha256s=tuple(
            rate.authority_receipt_sha256 for rate in ordered_rates
        ),
        time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
        backend_authority_receipt_sha256=backend.authority_receipt_sha256,
    )
    authority = ReceiverEvolutionAuthority(
        authority_id,
        port_id,
        state.receipt_sha256,
        interval,
        susceptibility,
        ordered_rates,
        time_unit,
        backend,
        receipt_sha256(authority_payload),
    )
    payloads = (
        time_derivation,
        time_payload,
        backend_payload,
        signal_unit_authority,
        susceptibility_derivation,
        susceptibility_payload,
        *rate_derivations,
        *rate_payloads,
        initial_derivation,
        initial_authority_payload,
        state_payload,
        observation,
        interval_payload,
        authority_payload,
    )
    return Scenario(
        state,
        authority,
        time_unit,
        backend,
        susceptibility,
        ordered_rates,
        interval,
        payloads,
        _registry(payloads),
    )


def _result_payloads(result) -> tuple[bytes, ...]:
    assert isinstance(result.state, CertifiedReceiverState)
    assert result.relevance is not None
    assert result.receipt is not None
    return (
        result.state.receipt_payload,
        result.relevance.receipt_payload,
        result.receipt.effective_activation.receipt_payload,
        result.receipt.generator.receipt_payload,
        result.receipt.receipt_payload,
    )


def _continuation(
    *,
    prior: CertifiedReceiverState,
    base: Scenario,
    source_time_end: Fraction,
    signed_native_signal: Fraction,
    prior_result_payloads: tuple[bytes, ...],
) -> tuple[ReceiverEvolutionAuthority, ReceiptRegistry]:
    start = prior.source_time
    observation = _fact(
        f"{prior.port_id}:continued-observation:{start}:{source_time_end}"
    )
    interval_payload = native_activation_interval_receipt_payload(
        interval_id=f"{prior.port_id}:interval:{start}:{source_time_end}",
        port_id=prior.port_id,
        source_time_start=start,
        source_time_end=source_time_end,
        time_unit_authority_receipt_sha256=(
            base.time_unit.authority_receipt_sha256
        ),
        activation_susceptibility_receipt_sha256=(
            base.susceptibility.authority_receipt_sha256
        ),
        signed_native_signal=signed_native_signal,
        native_signal_unit=base.susceptibility.native_signal_unit,
        native_signal_unit_authority_receipt_sha256=(
            base.susceptibility.native_signal_unit_authority_receipt_sha256
        ),
        native_observation_receipt_sha256=receipt_sha256(observation),
    )
    interval = NativeActivationInterval(
        f"{prior.port_id}:interval:{start}:{source_time_end}",
        prior.port_id,
        start,
        source_time_end,
        base.time_unit.authority_receipt_sha256,
        base.susceptibility.authority_receipt_sha256,
        signed_native_signal,
        base.susceptibility.native_signal_unit,
        base.susceptibility.native_signal_unit_authority_receipt_sha256,
        receipt_sha256(observation),
        receipt_sha256(interval_payload),
    )
    authority_id = f"{prior.port_id}:evolution:{start}:{source_time_end}"
    authority_payload = receiver_evolution_authority_receipt_payload(
        authority_id=authority_id,
        port_id=prior.port_id,
        prior_state_receipt_sha256=prior.receipt_sha256,
        activation_interval_receipt_sha256=interval.interval_receipt_sha256,
        activation_susceptibility_receipt_sha256=(
            base.susceptibility.authority_receipt_sha256
        ),
        ordered_rate_receipt_sha256s=tuple(
            rate.authority_receipt_sha256 for rate in base.rates
        ),
        time_unit_authority_receipt_sha256=(
            base.time_unit.authority_receipt_sha256
        ),
        backend_authority_receipt_sha256=base.backend.authority_receipt_sha256,
    )
    authority = ReceiverEvolutionAuthority(
        authority_id,
        prior.port_id,
        prior.receipt_sha256,
        interval,
        base.susceptibility,
        base.rates,
        base.time_unit,
        base.backend,
        receipt_sha256(authority_payload),
    )
    registry = _registry(
        (
            *base.payloads,
            *prior_result_payloads,
            observation,
            interval_payload,
            authority_payload,
        )
    )
    return authority, registry


def test_flux_coupled_generator_preserves_exact_affine_mass_and_receipts():
    scenario = _initial_scenario(signed_native_signal=Fraction(-2, 5))
    result = evolve_chemical_receiver(
        state=scenario.state,
        authority=scenario.authority,
        receipt_registry=scenario.registry,
    )

    assert result.status is ReceiverEvolutionStatus.EVOLVED
    assert isinstance(result.state, CertifiedReceiverState)
    assert result.state.exact_affine_constraint_id == CHEMICAL_AFFINE_CONSTRAINT_ID
    bounds = tuple(_bounds(value) for value in result.state.components)
    assert sum((lower for lower, _ in bounds), Fraction(0)) <= Fraction(1)
    assert sum((upper for _, upper in bounds), Fraction(0)) >= Fraction(1)
    assert result.receipt is not None
    activation = result.receipt.effective_activation
    assert activation.signed_native_signal == Fraction(-2, 5)
    assert activation.native_signal_magnitude == Fraction(2, 5)
    assert activation.propensity_per_time_unit == Fraction(1, 5)
    assert result.receipt.generator.effective_activation_propensity_receipt_sha256 == (
        activation.receipt_sha256
    )
    for column in range(3):
        assert sum(
            (
                entry.value
                for entry in result.receipt.generator_entries
                if entry.column == column
            ),
            Fraction(0),
        ) == 0


def test_identical_prior_state_zero_flux_has_zero_activation_and_nonzero_differs():
    quiet = _initial_scenario(signed_native_signal=Fraction(0))
    sensed = _initial_scenario(signed_native_signal=Fraction(1, 2))
    assert quiet.state == sensed.state

    quiet_result = evolve_chemical_receiver(
        state=quiet.state,
        authority=quiet.authority,
        receipt_registry=quiet.registry,
    )
    sensed_result = evolve_chemical_receiver(
        state=sensed.state,
        authority=sensed.authority,
        receipt_registry=sensed.registry,
    )

    assert quiet_result.status is ReceiverEvolutionStatus.EVOLVED
    assert sensed_result.status is ReceiverEvolutionStatus.EVOLVED
    assert quiet_result.receipt is not None
    assert sensed_result.receipt is not None
    assert quiet_result.receipt.effective_activation.propensity_per_time_unit == 0
    assert sensed_result.receipt.effective_activation.propensity_per_time_unit > 0
    assert quiet_result.relevance is not None
    assert sensed_result.relevance is not None
    assert _bounds(quiet_result.relevance.value) == (Fraction(0), Fraction(0))
    assert _bounds(sensed_result.relevance.value)[0] > 0


def test_larger_flux_magnitude_physically_changes_relevance_from_same_state():
    low = _initial_scenario(
        susceptibility_value=Fraction(1),
        rate_values=(Fraction(0), Fraction(0), Fraction(0)),
        signed_native_signal=Fraction(1, 4),
    )
    high = _initial_scenario(
        susceptibility_value=Fraction(1),
        rate_values=(Fraction(0), Fraction(0), Fraction(0)),
        signed_native_signal=Fraction(3, 4),
    )
    assert low.state == high.state
    low_result = evolve_chemical_receiver(
        state=low.state,
        authority=low.authority,
        receipt_registry=low.registry,
    )
    high_result = evolve_chemical_receiver(
        state=high.state,
        authority=high.authority,
        receipt_registry=high.registry,
    )

    assert low_result.relevance is not None
    assert high_result.relevance is not None
    _, low_upper = _bounds(low_result.relevance.value)
    high_lower, _ = _bounds(high_result.relevance.value)
    assert low_upper < high_lower
    assert low_result.receipt is not None
    assert high_result.receipt is not None
    assert (
        low_result.receipt.effective_activation.propensity_per_time_unit
        == Fraction(1, 4)
    )
    assert (
        high_result.receipt.effective_activation.propensity_per_time_unit
        == Fraction(3, 4)
    )


def test_equal_positive_and_negative_magnitude_share_activation_but_keep_sign():
    negative = _initial_scenario(signed_native_signal=Fraction(-3, 5))
    positive = _initial_scenario(signed_native_signal=Fraction(3, 5))
    negative_result = evolve_chemical_receiver(
        state=negative.state,
        authority=negative.authority,
        receipt_registry=negative.registry,
    )
    positive_result = evolve_chemical_receiver(
        state=positive.state,
        authority=positive.authority,
        receipt_registry=positive.registry,
    )

    assert negative_result.signed_native_signal == Fraction(-3, 5)
    assert positive_result.signed_native_signal == Fraction(3, 5)
    assert negative_result.relevance is not None
    assert positive_result.relevance is not None
    assert negative_result.relevance.value == positive_result.relevance.value
    assert negative_result.receipt is not None
    assert positive_result.receipt is not None
    assert (
        negative_result.receipt.effective_activation.propensity_per_time_unit
        == positive_result.receipt.effective_activation.propensity_per_time_unit
    )
    assert negative_result.receipt.receipt_sha256 != (
        positive_result.receipt.receipt_sha256
    )


def test_zero_flux_allows_natural_desensitized_recovery_without_activation():
    scenario = _initial_scenario(
        components=(Fraction(0), Fraction(0), Fraction(1)),
        susceptibility_value=Fraction(7),
        rate_values=(Fraction(0), Fraction(0), Fraction(1)),
        signed_native_signal=Fraction(0),
    )
    result = evolve_chemical_receiver(
        state=scenario.state,
        authority=scenario.authority,
        receipt_registry=scenario.registry,
    )

    assert result.status is ReceiverEvolutionStatus.EVOLVED
    assert isinstance(result.state, CertifiedReceiverState)
    resting_lower, _ = _bounds(result.state.resting_mass)
    _, desensitized_upper = _bounds(result.state.desensitized_mass)
    assert resting_lower > 0
    assert desensitized_upper < 1
    assert result.relevance is not None
    assert _bounds(result.relevance.value) == (Fraction(0), Fraction(0))


def test_susceptibility_flux_and_unit_tamper_fail_closed_without_state_change():
    scenario = _initial_scenario()
    tampered_susceptibility = replace(
        scenario.susceptibility,
        susceptibility_per_native_signal_unit_per_time_unit=Fraction(9),
    )
    wrong_susceptibility = replace(
        scenario.authority,
        activation_susceptibility=tampered_susceptibility,
    )
    tampered_flux = replace(
        scenario.authority,
        activation_interval=replace(
            scenario.interval,
            signed_native_signal=Fraction(7, 9),
        ),
    )
    tampered_unit = replace(
        scenario.authority,
        activation_interval=replace(
            scenario.interval,
            native_signal_unit="another-native-unit",
        ),
    )

    for authority in (wrong_susceptibility, tampered_flux, tampered_unit):
        result = evolve_chemical_receiver(
            state=scenario.state,
            authority=authority,
            receipt_registry=scenario.registry,
        )
        assert result.status is ReceiverEvolutionStatus.UNKNOWN
        assert result.state is scenario.state
        assert result.relevance is None
        assert result.receipt is None
        assert "differs from its mounted receipt" in result.reason


def test_ports_remain_independent_and_cross_port_authority_is_unknown():
    audio = _initial_scenario(
        port_id="story-audio.native-port-0",
        signed_native_signal=Fraction(1),
    )
    touch = _initial_scenario(
        port_id="story-touch.native-port-0",
        signed_native_signal=Fraction(0),
    )
    joint = _registry((*audio.payloads, *touch.payloads))
    audio_result = evolve_chemical_receiver(
        state=audio.state,
        authority=audio.authority,
        receipt_registry=joint,
    )
    touch_result = evolve_chemical_receiver(
        state=touch.state,
        authority=touch.authority,
        receipt_registry=joint,
    )
    crossed = evolve_chemical_receiver(
        state=touch.state,
        authority=audio.authority,
        receipt_registry=joint,
    )

    assert audio_result.relevance is not None
    assert touch_result.relevance is not None
    assert _bounds(audio_result.relevance.value)[0] > 0
    assert _bounds(touch_result.relevance.value) == (Fraction(0), Fraction(0))
    assert crossed.status is ReceiverEvolutionStatus.UNKNOWN
    assert crossed.state is touch.state


def test_missing_authority_never_defaults_and_activation_cannot_be_a_rate():
    scenario = _initial_scenario()
    for authority in (
        replace(scenario.authority, activation_interval=None),
        replace(scenario.authority, activation_susceptibility=None),
        replace(scenario.authority, time_unit=None),
        replace(scenario.authority, backend=None),
    ):
        result = evolve_chemical_receiver(
            state=scenario.state,
            authority=authority,
            receipt_registry=scenario.registry,
        )
        assert result.status is ReceiverEvolutionStatus.UNKNOWN
        assert result.state is scenario.state
        assert result.relevance is None

    forbidden = MountedChemicalRate(
        "forbidden-R-to-A-rate",
        scenario.state.port_id,
        ReceiverTransition.NATIVE_ACTIVATION,
        Fraction(1),
        scenario.time_unit.authority_receipt_sha256,
        scenario.rates[0].derivation_receipt_sha256,
        scenario.rates[0].authority_receipt_sha256,
    )
    with pytest.raises(ReceiptError, match="requires susceptibility"):
        forbidden.verify(scenario.registry)


def test_checkpoint_restart_continuation_is_exact_and_missing_state_is_refused():
    scenario = _initial_scenario(signed_native_signal=Fraction(-1, 3))
    first = evolve_chemical_receiver(
        state=scenario.state,
        authority=scenario.authority,
        receipt_registry=scenario.registry,
    )
    assert first.status is ReceiverEvolutionStatus.EVOLVED
    assert isinstance(first.state, CertifiedReceiverState)
    continuation, restart_registry = _continuation(
        prior=first.state,
        base=scenario,
        source_time_end=Fraction(2),
        signed_native_signal=Fraction(2, 7),
        prior_result_payloads=_result_payloads(first),
    )
    uninterrupted = evolve_chemical_receiver(
        state=first.state,
        authority=continuation,
        receipt_registry=restart_registry,
    )
    restarted = evolve_chemical_receiver(
        state=first.state,
        authority=continuation,
        receipt_registry=restart_registry,
    )
    assert uninterrupted.status is ReceiverEvolutionStatus.EVOLVED
    assert restarted == uninterrupted

    missing_state = ReceiptRegistry(
        profile_binding_sha256=restart_registry.profile_binding_sha256,
        records=tuple(
            record
            for record in restart_registry.records
            if record.digest != first.state.receipt_sha256
        ),
    )
    refused = evolve_chemical_receiver(
        state=first.state,
        authority=continuation,
        receipt_registry=missing_state,
    )
    assert refused.status is ReceiverEvolutionStatus.UNKNOWN
    assert refused.state is first.state
    assert "not mounted" in refused.reason
