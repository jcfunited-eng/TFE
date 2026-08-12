//! Falsifiable model of the smallest dimensioned virtual material constitution
//! that could create a first production neuron. This module is test-only until
//! its material choices, repeatable recovery, and receptor-work adapters are
//! ratified. It cannot be mounted or deployed accidentally.

use num_bigint::BigInt;
use num_rational::BigRational;

use crate::complete_neuron::{
    settle_experience_to_quiescence, settle_extended_interval_with_contact, DnaExpressionContact,
    ExactPhysicalStateDelta, GateWorkOccurrence, NeuronIntervalInput, NeuronPhysicalState,
    PhysicalStateCoordinate, QuiescentNeuronState, RecoveryContact, RecoveryLaneAddress,
};
use crate::exact_rational::ExactRational;
use crate::joint_uf_neuron_boundary::{
    bind_neuron_perspective, prepare_complete_joint_field_admitted_fixture, JointNeuronPerspective,
};
use crate::neuron_source_anchor::tests::exact_episode;
use crate::neuron_source_anchor::{bind_neuron_source_anchor, NeuronSourceSite};
use crate::optical_receptor_work::{derive_optical_receptor_work, OpticalReceptorAnatomy};
use crate::reached_neuron_cohort::{
    settle_reached_cohort_experience_to_quiescence, settle_reached_cohort_interval,
    ReachedCohortAnatomy, ReachedCohortIntervalInput, ReachedCohortState, RestReachedCohortState,
};
use crate::recovery_fluid_contact::{
    settle_recovery_fluid_contact, RecoveryFluidContactAnatomy, RecoveryFluidReservoirAnatomy,
    RecoveryFluidReservoirState,
};
use crate::sparse_electrical_contact::{
    ElectricalContactAnatomy, SparseElectricalAnatomy, SparseElectricalState,
};
use crate::virtual_material_neuron_genesis::{
    create_virtual_material_neuron, VirtualMaterialNeuronGenesis,
};

fn exact(numerator: i64, denominator: i64) -> BigRational {
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

fn ratio(numerator: i128, denominator: u128) -> ExactRational {
    ExactRational::new(numerator, denominator).unwrap()
}

type CandidateNeuron = VirtualMaterialNeuronGenesis;

/// Quiet intervals appended after the driven ones so the differentiated cohort
/// can descend all the way to electrical rest.  Geometrically differentiated
/// members equalize POTENTIAL, not charge, so the chain settles to charges
/// proportional to the members' own capacitances and only then quiesces;
/// measured at the ratified 500 pS authored conductance this takes fewer than
/// 64 quiet milliseconds (it took 21,691 at the 1 pS the candidate used
/// before, which is conductance, not a different law).
const DARK_TAIL_INTERVALS: usize = 64;

/// Candidate dimensional constitution:
///
/// - one zeptojoule is the virtual Psi coupling-energy unit;
/// - `9/2 zJ` is derived from the exact unmatched-to-matched ternary-ring drop;
/// - one pF is the declared virtual capacitance of ONE unit patch of membrane
///   (each candidate's own capacitance is that base times its declared
///   territory, per the 2026-08-05 geometric-differentiation ratification);
///   one pS, one mV, and one nm are declared virtual material units;
/// - the `2 zJ`, `1 zJ`, and `3/4 zJ` plastic values form an exact
///   one-open/one-close return-map cycle;
/// - 6,242 carriers are `ceil(1 fC / e)` using the exact SI elementary charge.
///
/// The source-work conversion and renewable body/fluid material supply remain
/// unresolved, which is why this is not a production constructor.
fn candidate_neuron(
    episode: &crate::joint_source_episode::NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
) -> CandidateNeuron {
    let site =
        NeuronSourceSite::from_anchor(bind_neuron_source_anchor(episode, perspective).unwrap());
    create_virtual_material_neuron(perspective, &site).unwrap()
}

fn interval<'a>(
    perspective: JointNeuronPerspective<'a>,
    open_minus_closed_zeptojoules: i64,
    catalysts: &'a [u128],
) -> NeuronIntervalInput<'a> {
    NeuronIntervalInput {
        perspective,
        gate_work: GateWorkOccurrence::new(exact(open_minus_closed_zeptojoules, 1)),
        interval_microseconds: 1_000,
        recovery: RecoveryContact::new(catalysts, 0, 0),
        dna_expression: DnaExpressionContact::new(0),
        receptor_successor_residue: None,
        prepared_psi: None,
    }
}

fn optical_interval<'a>(
    episode: &'a crate::joint_source_episode::NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'a>,
    catalysts: &'a [u128],
) -> NeuronIntervalInput<'a> {
    let receptor =
        OpticalReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(1, 2), exact(1, 1)).unwrap();
    let source_work = derive_optical_receptor_work(episode, perspective, &receptor).unwrap();
    NeuronIntervalInput {
        perspective,
        gate_work: source_work.gate_work,
        interval_microseconds: 1_000,
        recovery: RecoveryContact::new(catalysts, 0, 0),
        dna_expression: DnaExpressionContact::new(0),
        receptor_successor_residue: None,
        prepared_psi: None,
    }
}

fn exchange_recovery_material(
    candidate: &CandidateNeuron,
    state: &mut NeuronPhysicalState,
    reservoir_anatomy: RecoveryFluidReservoirAnatomy,
    reservoir: &mut RecoveryFluidReservoirState,
) {
    let contact = RecoveryFluidContactAnatomy::new(1, 1, 1, 1).unwrap();
    for index in 0..candidate.anatomy.recovery_anatomy().psi_lane_count() {
        exchange_one_lane(
            candidate,
            state,
            RecoveryLaneAddress::Psi(index),
            reservoir_anatomy,
            reservoir,
            contact,
        );
    }
    for address in [RecoveryLaneAddress::Gate, RecoveryLaneAddress::Plastic] {
        exchange_one_lane(
            candidate,
            state,
            address,
            reservoir_anatomy,
            reservoir,
            contact,
        );
    }
}

fn exchange_one_lane(
    candidate: &CandidateNeuron,
    state: &mut NeuronPhysicalState,
    address: RecoveryLaneAddress,
    reservoir_anatomy: RecoveryFluidReservoirAnatomy,
    reservoir: &mut RecoveryFluidReservoirState,
    contact: RecoveryFluidContactAnatomy,
) {
    let settled = settle_recovery_fluid_contact(
        candidate.anatomy.recovery_anatomy().lane(address).unwrap(),
        candidate
            .anatomy
            .recovery_energy_per_extent_zeptojoules(address)
            .unwrap(),
        state.recovery.lane(address).unwrap(),
        reservoir_anatomy,
        *reservoir,
        contact,
    )
    .unwrap();
    state
        .recovery
        .replace_lane(address, settled.successor_lane)
        .unwrap();
    *reservoir = settled.successor_reservoir;
}

fn cohort_interval<'a>(
    episode: &'a crate::joint_source_episode::NativeJointSourceEpisode,
    shared: &'a crate::joint_uf_neuron_boundary::SharedCompleteJointField,
    catalysts: &'a [u128],
    gate_work: [i64; 4],
) -> ReachedCohortIntervalInput<'a> {
    let inputs = gate_work
        .into_iter()
        .enumerate()
        .map(|(index, work)| {
            interval(
                bind_neuron_perspective(shared, index, 0).unwrap(),
                work,
                catalysts,
            )
        })
        .collect();
    ReachedCohortIntervalInput::from_episode(episode, inputs).unwrap()
}

#[test]
fn one_candidate_neuron_forms_one_exact_retained_fractal_and_quiesces() {
    let episode = exact_episode();
    let shared = prepare_complete_joint_field_admitted_fixture(&episode, 0).unwrap();
    let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
    let candidate = candidate_neuron(&episode, perspective);
    let predecessor = QuiescentNeuronState::from_state(candidate.state.clone());
    let settled = settle_experience_to_quiescence(
        &candidate.anatomy,
        &predecessor,
        optical_interval(&episode, perspective, &candidate.zero_recovery_catalysts),
        &[
            interval(perspective, 0, &candidate.zero_recovery_catalysts),
            interval(perspective, 0, &candidate.zero_recovery_catalysts),
        ],
    )
    .unwrap();
    assert_eq!(
        settled
            .fractal
            .as_ref()
            .unwrap()
            .exact_delta(PhysicalStateCoordinate::PlasticRestLength),
        Some(ExactPhysicalStateDelta::Rational(ratio(1, 3)))
    );
    assert!(settled.fractal.as_ref().unwrap().entries().len() > 1);
}

#[test]
fn candidate_neuron_recovers_through_conserved_fluid_and_repeats_response() {
    let episode = exact_episode();
    let shared = prepare_complete_joint_field_admitted_fixture(&episode, 0).unwrap();
    let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
    let candidate = candidate_neuron(&episode, perspective);
    let predecessor = QuiescentNeuronState::from_state(candidate.state.clone());
    let first = settle_experience_to_quiescence(
        &candidate.anatomy,
        &predecessor,
        interval(perspective, -2, &candidate.zero_recovery_catalysts),
        &[
            interval(perspective, 0, &candidate.zero_recovery_catalysts),
            interval(perspective, 0, &candidate.zero_recovery_catalysts),
        ],
    )
    .unwrap();

    let recovery_material =
        u128::try_from(candidate.anatomy.recovery_anatomy().psi_lane_count()).unwrap() + 20;
    let recovery_energy = ExactRational::integer(i128::try_from(recovery_material).unwrap());
    let reservoir_anatomy =
        RecoveryFluidReservoirAnatomy::new(recovery_energy, recovery_energy, recovery_energy)
            .unwrap();
    let mut reservoir = RecoveryFluidReservoirState::new(
        reservoir_anatomy,
        recovery_energy,
        ExactRational::integer(0),
        ExactRational::integer(0),
    )
    .unwrap();
    let recovery_catalysts = vec![1; candidate.zero_recovery_catalysts.len()];
    let mut recovered = first.quiescent.state().clone();
    for _ in 0..19 {
        recovered = settle_extended_interval_with_contact(
            &candidate.anatomy,
            &recovered,
            NeuronIntervalInput {
                perspective,
                gate_work: GateWorkOccurrence::new(exact(0, 1)),
                interval_microseconds: 1_000,
                recovery: RecoveryContact::new(&recovery_catalysts, 1, 1),
                dna_expression: DnaExpressionContact::new(0),
                receptor_successor_residue: None,
                prepared_psi: None,
            },
            0,
        )
        .unwrap()
        .successor;
        exchange_recovery_material(
            &candidate,
            &mut recovered,
            reservoir_anatomy,
            &mut reservoir,
        );
    }

    let recovered_quiescent = QuiescentNeuronState::from_state(recovered);
    let repeated = settle_experience_to_quiescence(
        &candidate.anatomy,
        &recovered_quiescent,
        interval(perspective, -2, &candidate.zero_recovery_catalysts),
        &[
            interval(perspective, 0, &candidate.zero_recovery_catalysts),
            interval(perspective, 0, &candidate.zero_recovery_catalysts),
        ],
    )
    .unwrap();
    assert!(repeated.fractal.is_some());
    assert_eq!(
        repeated
            .fractal
            .as_ref()
            .unwrap()
            .exact_delta(PhysicalStateCoordinate::PlasticRestLength),
        None
    );
}

#[test]
#[ignore = "retired: pre-specialization aggregate gate-work candidate"]
fn four_source_candidate_cohort_forms_distinct_member_fractals_and_quiesces() {
    let episode = exact_episode();
    let shared = prepare_complete_joint_field_admitted_fixture(&episode, 0).unwrap();
    let candidates = (0..4)
        .map(|index| {
            candidate_neuron(
                &episode,
                bind_neuron_perspective(&shared, index, 0).unwrap(),
            )
        })
        .collect::<Vec<_>>();
    let source_sites = (0..4)
        .map(|index| {
            NeuronSourceSite::from_anchor(
                bind_neuron_source_anchor(
                    &episode,
                    bind_neuron_perspective(&shared, index, 0).unwrap(),
                )
                .unwrap(),
            )
        })
        .collect();
    let electrical = SparseElectricalAnatomy::new(
        4,
        vec![
            ElectricalContactAnatomy::new(0, 1, ratio(500, 1), 4).unwrap(),
            ElectricalContactAnatomy::new(1, 2, ratio(500, 1), 4).unwrap(),
            ElectricalContactAnatomy::new(2, 3, ratio(500, 1), 4).unwrap(),
        ],
    )
    .unwrap();
    let anatomy = ReachedCohortAnatomy::new(
        candidates
            .iter()
            .map(|candidate| candidate.anatomy.clone())
            .collect(),
        (1u128..=4).map(u128::to_be_bytes).collect(),
        source_sites,
        electrical.clone(),
    )
    .unwrap();
    let state = ReachedCohortState::new(
        &anatomy,
        candidates
            .iter()
            .map(|candidate| candidate.state.clone())
            .collect(),
        SparseElectricalState::genesis(&electrical),
    )
    .unwrap();
    let predecessor = RestReachedCohortState::from_state(state);
    let catalysts = &candidates[0].zero_recovery_catalysts;
    // Dark tail: since the members are geometrically differentiated their
    // separated charges no longer tie, so the contacts actually conduct and
    // the cohort needs a longer quiet tail to descend to rest.  It must REACH
    // rest — a settlement that never quiesces is refused by the settler.
    let mut intervals = vec![
        cohort_interval(&episode, &shared, catalysts, [-2, 0, -2, 0]),
        cohort_interval(&episode, &shared, catalysts, [0, -2, 0, -2]),
    ];
    intervals.extend(
        std::iter::repeat_with(|| cohort_interval(&episode, &shared, catalysts, [0, 0, 0, 0]))
            .take(DARK_TAIL_INTERVALS),
    );
    let settled =
        settle_reached_cohort_experience_to_quiescence(&anatomy, &predecessor, &intervals).unwrap();
    assert_eq!(
        settled
            .neuron_fractals
            .iter()
            .filter(|fractal| fractal.is_some())
            .count(),
        4
    );
    assert!(settled.electrical_contact_was_active);
    // Anti-oscillation: the rest it reached is a FIXED POINT, not one phase of
    // a limit cycle.  Another quiet millisecond out of the settled state moves
    // nothing, conducts nothing, and stays quiescent.
    let at_rest = settle_reached_cohort_interval(
        &anatomy,
        settled.rest.state(),
        cohort_interval(&episode, &shared, catalysts, [0, 0, 0, 0]),
    )
    .unwrap();
    assert!(!at_rest.electrically_active);
    assert!(at_rest.quiescent);
    assert_eq!(&at_rest.successor, settled.rest.state());
    assert!(settled
        .gate_work_perturbed_neurons
        .iter()
        .all(|perturbed| *perturbed));
    assert!(settled
        .active_electrical_contacts
        .iter()
        .all(|active| *active));
}
