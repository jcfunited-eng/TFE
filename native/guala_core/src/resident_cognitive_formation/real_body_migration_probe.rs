//! Real-body migration proof (test code, never compiled into production).
//!
//! Reads one actual persisted production envelope (GUALA_REAL_BODY env),
//! extracts its cognitive image, decodes the retired format, migrates to
//! the current format, and proves structural equality plus decode of the
//! migrated bytes. No-op when the env var is absent.

use super::{ResidentCognitiveFormationState, ResidentReachedCohort};
use crate::complete_neuron::{
    settle_plastic_support_at_coordinate, sparse_physical_state_delta,
    sparse_retained_physical_state_delta, NeuronPhysicalAnatomy, NeuronPhysicalState,
    PlasticSupportAnatomy, PlasticSupportState,
};
use crate::exact_rational::ExactRational;
use crate::neuron_source_anchor::PhysicalSourceSense;
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::PathBuf;

#[test]
fn real_production_body_migrates_losslessly() {
    let Some(path) = std::env::var_os("GUALA_REAL_BODY") else {
        return;
    };
    let body = fs::read(PathBuf::from(path)).expect("real body readable");
    let (organism_tick, cognitive) = super::reservoir_probe::parse_envelope(&body);
    let budget = 2_147_483_590usize;
    assert!(
        ResidentCognitiveFormationState::decode(&cognitive, budget).is_err(),
        "ordinary restore must refuse the retired cognitive encoding",
    );
    let decoded = ResidentCognitiveFormationState::decode_for_one_way_migration(&cognitive, budget)
        .expect("authenticated live image is admitted only at the migration boundary");
    let retired = decoded
        .obsolete_unreferenced_developmental_routes()
        .expect("obsolete developmental routes are exact");
    let retired_set = retired.iter().copied().collect::<BTreeSet<_>>();
    let retained_cohorts = decoded
        .cohorts
        .iter()
        .filter(|cohort| {
            cohort
                .anatomy
                .neuron_lineages()
                .iter()
                .all(|lineage| !retired_set.contains(lineage))
        })
        .cloned()
        .collect::<Vec<_>>();
    let retired_contact_count = decoded
        .electrical_fabric
        .contact_endpoints()
        .filter(|(left, right)| {
            retired_set.contains(&decoded.electrical_fabric.lineages()[*left])
                || retired_set.contains(&decoded.electrical_fabric.lineages()[*right])
        })
        .count();
    let keep_frontier = |entry: &&super::ActiveElectricalFrontierEntry| {
        !retired_set.contains(&entry.receiver())
            && entry
                .sender()
                .as_ref()
                .is_none_or(|lineage| !retired_set.contains(lineage))
    };
    let retained_active_frontier = decoded
        .active_electrical_frontier
        .iter()
        .filter(keep_frontier)
        .copied()
        .collect::<Vec<_>>();
    let retained_preceding_frontier = decoded
        .preceding_active_electrical_frontier
        .iter()
        .filter(keep_frontier)
        .copied()
        .collect::<Vec<_>>();
    let retained_older_frontier = decoded
        .older_active_electrical_frontier
        .iter()
        .filter(keep_frontier)
        .copied()
        .collect::<Vec<_>>();
    let predecessor_contact_count = decoded.electrical_fabric.contact_count();
    eprintln!(
        "REAL_BODY_ROUTE_INVENTORY retired_routes={} predecessor_contacts={}",
        retired.len(),
        predecessor_contact_count,
    );
    let cleanup_probe = decoded
        .retire_obsolete_unreferenced_developmental_routes()
        .expect("selected production routes satisfy the exact retirement law");
    let cleanup_probe = cleanup_probe.as_ref().unwrap_or(&decoded);
    cleanup_probe
        .validate_current_motor_effectors()
        .expect("retirement preserves motor anatomy");
    cleanup_probe
        .validate_current_ordering_routes()
        .expect("retirement preserves ordering anatomy");
    eprintln!("REAL_BODY_ROUTE_CLEANUP_VALIDATED");
    cleanup_probe
        .encode(budget)
        .expect("corrected production cognition encodes as current V30");
    eprintln!("REAL_BODY_V30_ENCODING_VALIDATED");
    let migrated = ResidentCognitiveFormationState::migrate_to_current_format(&cognitive, budget)
        .expect("migration to current format");
    let redecoded =
        ResidentCognitiveFormationState::decode(&migrated, budget).expect("migrated image decodes");
    assert_eq!(redecoded.generation, decoded.generation);
    assert_eq!(redecoded.next_lineage_ordinal, decoded.next_lineage_ordinal);
    assert_eq!(
        redecoded.unexpressed_electrical_seeds,
        decoded.unexpressed_electrical_seeds
    );
    assert_eq!(redecoded.dormant_lineage_seeds, decoded.dormant_lineage_seeds);
    assert_eq!(redecoded.cohorts.as_ref(), retained_cohorts.as_slice());
    assert_eq!(
        redecoded.electrical_fabric.contact_count(),
        predecessor_contact_count - retired_contact_count
    );
    assert_eq!(
        redecoded.active_electrical_frontier.as_ref(),
        retained_active_frontier.as_slice()
    );
    assert_eq!(
        redecoded.preceding_active_electrical_frontier.as_ref(),
        retained_preceding_frontier.as_slice()
    );
    assert_eq!(
        redecoded.older_active_electrical_frontier.as_ref(),
        retained_older_frontier.as_slice()
    );
    assert_eq!(redecoded.mosaics, decoded.mosaics, "retained state changed");
    assert_eq!(redecoded.hippocampal, decoded.hippocampal);
    assert_eq!(
        redecoded.summary().complete_neuron_count,
        decoded.summary().complete_neuron_count - retired.len()
    );
    assert_eq!(
        ResidentCognitiveFormationState::migrate_to_current_format(&migrated, budget)
            .expect("current image remains current"),
        migrated,
        "the one-way migration is idempotent",
    );

    println!(
        "REAL_BODY_MIGRATION tick={} old_cognitive_bytes={} new_cognitive_bytes={} retired_routes={} old_contacts={} new_contacts={} cohorts={} reached_neurons={} resting_neurons={} mosaics={}",
        organism_tick,
        cognitive.len(),
        migrated.len(),
        retired.len(),
        predecessor_contact_count,
        redecoded.electrical_fabric.contact_count(),
        redecoded.cohorts.len(),
        redecoded.summary().complete_neuron_count,
        redecoded.summary().resting_neuron_count,
        redecoded.mosaics.len(),
    );
}

#[test]
fn real_production_body_expands_retinal_channels_once_and_retires_false_cognition() {
    let Some(path) = std::env::var_os("GUALA_REAL_BODY") else {
        return;
    };
    let body = fs::read(PathBuf::from(path)).expect("real body readable");
    let (organism_tick, cognitive) = super::reservoir_probe::parse_envelope(&body);
    let budget = 64_000_000usize;
    let decoded = ResidentCognitiveFormationState::decode(&cognitive, budget)
        .expect("live cognitive image decodes");
    let expanded = decoded
        .expand_legacy_receptor_channel_populations()
        .expect("live retinal channel population expands");

    assert_eq!(expanded.generation, decoded.generation);
    assert_eq!(expanded.next_lineage_ordinal, decoded.next_lineage_ordinal);
    assert_eq!(
        expanded.unexpressed_electrical_seeds,
        decoded.unexpressed_electrical_seeds
    );
    assert_eq!(
        expanded.dormant_lineage_seeds,
        decoded.dormant_lineage_seeds
    );
    assert_eq!(expanded.cohorts.len(), decoded.cohorts.len());
    assert!(expanded.mosaics.is_empty());
    assert_eq!(expanded.hippocampal, Default::default());
    for (before, after) in decoded.cohorts.iter().zip(expanded.cohorts.iter()) {
        assert_eq!(
            after.anatomy.neuron_lineages(),
            before.anatomy.neuron_lineages()
        );
        assert_eq!(
            after.anatomy.source_sites().collect::<Vec<_>>(),
            before.anatomy.source_sites().collect::<Vec<_>>()
        );
        assert_eq!(
            after.anatomy.contact_count(),
            before.anatomy.contact_count()
        );
        assert_eq!(
            after.anatomy.contact_endpoints().collect::<Vec<_>>(),
            before.anatomy.contact_endpoints().collect::<Vec<_>>(),
        );
        assert!(after.pending_experience.is_none());
        assert!(after.retained_experience.is_none());
        assert!(after.pending_recurrence.is_none());
    }
    let encoded = expanded.encode(budget).expect("expanded live body encodes");
    let cold = ResidentCognitiveFormationState::decode(&encoded, budget)
        .expect("expanded live body cold restores");
    assert_eq!(cold, expanded);
    assert_eq!(
        cold.expand_legacy_receptor_channel_populations()
            .expect("retinal expansion is idempotent"),
        cold,
    );
    println!(
        "REAL_BODY_RETINAL_EXPANSION tick={} old_cognitive_bytes={} new_cognitive_bytes={} cohorts={} retired_mosaics={} mosaics={}",
        organism_tick,
        cognitive.len(),
        encoded.len(),
        cold.cohorts.len(),
        decoded.mosaics.len(),
        cold.mosaics.len(),
    );
}

fn retinal_cells(
    state: &ResidentCognitiveFormationState,
) -> Vec<([u8; 16], NeuronPhysicalAnatomy, NeuronPhysicalState)> {
    let mut cells = state
        .cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .neuron_lineages()
                .iter()
                .zip(cohort.anatomy.source_sites())
                .zip(cohort.anatomy.neuron_anatomies())
                .zip(cohort.state.neurons())
                .filter_map(|(((lineage, site), anatomy), state)| {
                    (site.sense() == PhysicalSourceSense::Sight)
                        .then(|| (*lineage, anatomy.clone(), state.clone()))
                })
        })
        .collect::<Vec<_>>();
    cells.sort_by_key(|(lineage, _, _)| *lineage);
    cells
}

#[test]
fn real_production_body_reports_retinal_retention_capacity() {
    let Some(path) = std::env::var_os("GUALA_REAL_BODY") else {
        return;
    };
    let body = fs::read(PathBuf::from(path)).expect("real body readable");
    let (organism_tick, cognitive) = super::reservoir_probe::parse_envelope(&body);
    let decoded = ResidentCognitiveFormationState::decode(&cognitive, 64_000_000)
        .expect("live cognitive image decodes");
    let cells = retinal_cells(&decoded);
    let retained_experiences = decoded
        .cohorts
        .iter()
        .filter(|cohort| cohort.retained_experience.is_some())
        .count();
    let pending_experiences = decoded
        .cohorts
        .iter()
        .filter(|cohort| cohort.pending_experience.is_some())
        .count();
    let mut fully_yielded = 0usize;
    let mut virgin = 0usize;
    let mut partial = 0usize;
    let mut plastic_recovery = (0_u128, 0_u128, 0_u128);
    let mut dna = (0_u128, 0_u128, 0_u128, 0_u128);
    let mut open_gate_population = 0_u128;
    let mut plastic_dissipation = 0_u128;
    let mut gate_dissipation = 0_u128;
    for (_, anatomy, state) in &cells {
        let yielded = anatomy
            .probe_legacy_independent_yielded_population(&state.plastic)
            .expect("retained plastic population is exact");
        if yielded == 0 {
            virgin += 1;
        } else if yielded == anatomy.gate_population() {
            fully_yielded += 1;
        } else {
            partial += 1;
        }
        assert!(state.plastic.probe_rest_length_nanometres().parts().0 > 0);
        assert!(
            anatomy
                .probe_plastic_closed_coordinate_nanometres()
                .parts()
                .0
                > 0
        );
        let (local_recovery, local_dna) = state.probe_retention_material();
        open_gate_population += state.gate.open_population();
        gate_dissipation += state.gate.dissipated_quanta();
        plastic_dissipation += state.plastic.probe_dissipated_quanta();
        plastic_recovery.0 += local_recovery.0;
        plastic_recovery.1 += local_recovery.1;
        plastic_recovery.2 += local_recovery.2;
        dna.0 += local_dna.0;
        dna.1 += local_dna.1;
        dna.2 += local_dna.2;
        dna.3 += local_dna.3;
    }
    println!(
        "REAL_RETINAL_RETENTION_CAPACITY tick={} retinal={} fully_yielded={} partial={} virgin={} open_gate_population={} gate_dissipation={} plastic_dissipation={} plastic_recovery={:?} dna={:?} retained_experiences={} pending_experiences={} mosaics={}",
        organism_tick,
        cells.len(),
        fully_yielded,
        partial,
        virgin,
        open_gate_population,
        gate_dissipation,
        plastic_dissipation,
        plastic_recovery,
        dna,
        retained_experiences,
        pending_experiences,
        decoded.mosaics.len(),
    );
}

#[test]
fn real_production_body_reports_exact_retinal_interval_delta() {
    let (Some(before_path), Some(after_path)) = (
        std::env::var_os("GUALA_REAL_BODY"),
        std::env::var_os("GUALA_AFTER_BODY"),
    ) else {
        return;
    };
    let budget = 64_000_000usize;
    let decode = |path: PathBuf| {
        let body = fs::read(path).expect("interval body readable");
        let (_, cognitive) = super::reservoir_probe::parse_envelope(&body);
        ResidentCognitiveFormationState::decode(&cognitive, budget)
            .expect("interval cognitive image decodes")
    };
    let before = retinal_cells(&decode(PathBuf::from(before_path)));
    let after = retinal_cells(&decode(PathBuf::from(after_path)));
    assert_eq!(before.len(), after.len());
    let mut coordinate_counts = BTreeMap::<String, usize>::new();
    let mut per_neuron_deltas = Vec::new();
    let mut physically_changed = 0usize;
    let mut retained_changed = 0usize;
    for (prior, next) in before.iter().zip(&after) {
        assert_eq!(prior.0, next.0);
        assert_eq!(prior.1, next.1);
        if let Some(delta) =
            sparse_physical_state_delta(&prior.2, &next.2).expect("full interval delta is exact")
        {
            physically_changed += 1;
            per_neuron_deltas.push((prior.0, delta.entries().to_vec()));
            for entry in delta.entries() {
                *coordinate_counts
                    .entry(format!("{:?}", entry.coordinate()))
                    .or_default() += 1;
            }
        }
        retained_changed += usize::from(
            sparse_retained_physical_state_delta(&prior.2, &next.2)
                .expect("retained interval delta is exact")
                .is_some(),
        );
    }
    println!(
        "REAL_RETINAL_INTERVAL_DELTA retinal={} physically_changed={} retained_changed={} coordinates={:?} per_neuron={:?}",
        before.len(), physically_changed, retained_changed, coordinate_counts, per_neuron_deltas,
    );
}

#[test]
fn real_a_and_k_lessons_leave_distinct_retained_retinal_states() {
    let (Some(baseline_path), Some(a_path), Some(k_path)) = (
        std::env::var_os("GUALA_REAL_BODY"),
        std::env::var_os("GUALA_A_BODY"),
        std::env::var_os("GUALA_K_BODY"),
    ) else {
        return;
    };
    let budget = 64_000_000usize;
    let decode = |path: PathBuf| {
        let body = fs::read(path).expect("lesson body readable");
        let (_, cognitive) = super::reservoir_probe::parse_envelope(&body);
        ResidentCognitiveFormationState::decode(&cognitive, budget)
            .expect("lesson cognitive image decodes")
    };
    let baseline = decode(PathBuf::from(baseline_path))
        .expand_legacy_receptor_channel_populations()
        .expect("baseline retinal population expands");
    let a = decode(PathBuf::from(a_path));
    let k = decode(PathBuf::from(k_path));
    let baseline_cells = retinal_cells(&baseline);
    let a_cells = retinal_cells(&a);
    let k_cells = retinal_cells(&k);
    assert_eq!(baseline_cells.len(), a_cells.len());
    assert_eq!(baseline_cells.len(), k_cells.len());
    let mut distinct_retained = 0usize;
    for ((baseline_cell, a_cell), k_cell) in baseline_cells.iter().zip(&a_cells).zip(&k_cells) {
        assert_eq!(baseline_cell.0, a_cell.0);
        assert_eq!(baseline_cell.0, k_cell.0);
        assert_eq!(baseline_cell.1, a_cell.1);
        assert_eq!(baseline_cell.1, k_cell.1);
        let a_delta = sparse_retained_physical_state_delta(&baseline_cell.2, &a_cell.2)
            .expect("A retained delta is physical");
        let k_delta = sparse_retained_physical_state_delta(&baseline_cell.2, &k_cell.2)
            .expect("K retained delta is physical");
        if a_delta != k_delta {
            distinct_retained += 1;
        }
    }
    assert!(
        distinct_retained > 0,
        "A and K retained no distinct retinal state"
    );
    println!(
        "REAL_A_K_RETINAL_SEPARATION retinal_neurons={} distinct_retained_neurons={}",
        baseline_cells.len(),
        distinct_retained,
    );
}

#[test]
fn repeated_a_and_k_recurrence_coordinate_probe() {
    let (Some(a1_path), Some(a2_path), Some(k2_path)) = (
        std::env::var_os("GUALA_A1_BODY"),
        std::env::var_os("GUALA_A2_BODY"),
        std::env::var_os("GUALA_K2_BODY"),
    ) else {
        return;
    };
    let budget = 64_000_000usize;
    let decode = |path: PathBuf| {
        let body = fs::read(path).expect("recurrence body readable");
        let (_, cognitive) = super::reservoir_probe::parse_envelope(&body);
        ResidentCognitiveFormationState::decode(&cognitive, budget)
            .expect("recurrence cognitive image decodes")
    };
    let a1 = decode(PathBuf::from(a1_path));
    let a2 = decode(PathBuf::from(a2_path));
    let k2 = decode(PathBuf::from(k2_path));
    let original_cohort = a1
        .cohorts
        .iter()
        .find(|cohort| cohort.retained_experience.is_some())
        .expect("A1 retained cohort");
    let a2_cohort = a2
        .cohorts
        .iter()
        .find(|cohort| {
            cohort.anatomy.neuron_lineages() == original_cohort.anatomy.neuron_lineages()
        })
        .expect("A2 matching cohort");
    let k2_cohort = k2
        .cohorts
        .iter()
        .find(|cohort| {
            cohort.anatomy.neuron_lineages() == original_cohort.anatomy.neuron_lineages()
        })
        .expect("K2 matching cohort");
    let populations = |cohort: &ResidentReachedCohort| {
        cohort
            .state
            .neurons()
            .iter()
            .map(|neuron| neuron.probe_gate_open_population())
            .collect::<Vec<_>>()
    };
    let learned_state = |index: usize| {
        original_cohort
            .state
            .neurons()
            .get(index)
            .expect("contact endpoint retained in resident state")
    };
    let support_coordinate = |cohort: &ResidentReachedCohort,
                              state: &crate::complete_neuron::NeuronPhysicalState,
                              index: usize| {
        ExactRational::integer(1)
            .checked_add(
                ExactRational::integer(
                    i128::try_from(state.probe_gate_open_population()).unwrap(),
                )
                .checked_div_unsigned(cohort.anatomy.neuron_anatomies()[index].gate_population())
                .unwrap(),
            )
            .unwrap()
    };
    let material = PlasticSupportAnatomy::definitive_virtual_material().unwrap();
    let mut original_yielded = 0usize;
    let mut repeated_yielded = 0usize;
    let mut novel_yielded = 0usize;
    let mut repeated_refused = 0usize;
    let mut novel_refused = 0usize;
    let contact_genesis = PlasticSupportState::definitive_virtual_genesis();
    let actual_retained_contacts = original_cohort
        .state
        .electrical()
        .contact_states()
        .iter()
        .filter(|contact| contact.legacy_plastic_compatibility_state() != contact_genesis)
        .count();
    for (left, right) in original_cohort.anatomy.contact_endpoints() {
        let contact_coordinate =
            |cohort: &ResidentReachedCohort,
             state: &crate::reached_neuron_cohort::ReachedCohortState| {
                ExactRational::integer(1)
                    .checked_add(
                        support_coordinate(cohort, &state.neurons()[left], left)
                            .checked_sub(support_coordinate(
                                cohort,
                                &state.neurons()[right],
                                right,
                            ))
                            .unwrap()
                            .checked_abs()
                            .unwrap(),
                    )
                    .unwrap()
            };
        let original = settle_plastic_support_at_coordinate(
            &material,
            &PlasticSupportState::definitive_virtual_genesis(),
            ExactRational::integer(1)
                .checked_add(
                    support_coordinate(original_cohort, learned_state(left), left)
                        .checked_sub(support_coordinate(
                            original_cohort,
                            learned_state(right),
                            right,
                        ))
                        .unwrap()
                        .checked_abs()
                        .unwrap(),
                )
                .unwrap(),
        )
        .unwrap();
        original_yielded += usize::from(original.changed);
        let repeated = settle_plastic_support_at_coordinate(
            &material,
            &original.successor,
            contact_coordinate(a2_cohort, &a2_cohort.state),
        );
        repeated_yielded += usize::from(repeated.as_ref().is_ok_and(|value| value.changed));
        repeated_refused += usize::from(repeated.is_err());
        let novel = settle_plastic_support_at_coordinate(
            &material,
            &original.successor,
            contact_coordinate(k2_cohort, &k2_cohort.state),
        );
        novel_yielded += usize::from(novel.as_ref().is_ok_and(|value| value.changed));
        novel_refused += usize::from(novel.is_err());
    }
    println!(
        "RECURRENCE_POPULATIONS predecessor={:?} a={:?} k={:?} contact_yield original={} repeated={} novel={} actual_retained={} refused_repeated={} refused_novel={}",
        populations(original_cohort),
        populations(a2_cohort),
        populations(k2_cohort),
        original_yielded,
        repeated_yielded,
        novel_yielded,
        actual_retained_contacts,
        repeated_refused,
        novel_refused,
    );
}
