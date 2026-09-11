//! Read-only census of one saved lesson's new association anatomy.
//! This module is reachable only through the test-only reservoir probe.

use super::*;
use crate::resident_cognitive_formation::CognitiveFormationObservation;
use std::collections::{BTreeMap, BTreeSet};

fn census(state: &ResidentCognitiveFormationState, associations: &[[u8; 16]]) -> Value {
    json!(associations.iter().map(|association| {
        let formations = state.formation_index
            .candidate_indices([*association], std::iter::empty())
            .into_iter()
            .filter_map(|index| {
                let retained = &state.mosaics[index];
                let mosaic = &retained.mosaic;
                let member = mosaic.member_lineages().binary_search(association).is_ok();
                let endpoint = mosaic.original_bonds().iter().any(|bond| {
                    let (left, right) = bond.endpoints();
                    left == *association || right == *association
                });
                if !member && !endpoint {
                    return None;
                }
                let member_layers = mosaic.member_lineages().iter()
                    .filter_map(|lineage| state.topology_index.layer_of(*lineage))
                    .collect::<BTreeSet<_>>();
                let bond_layers = mosaic.original_bonds().iter()
                    .flat_map(|bond| {
                        let (left, right) = bond.endpoints();
                        [left, right]
                    })
                    .filter_map(|lineage| state.topology_index.layer_of(lineage))
                    .collect::<BTreeSet<_>>();
                Some(json!({
                    "member": member,
                    "original_endpoint": endpoint,
                    "pending": mosaic.is_original_only(),
                    "retained_neurons_only": mosaic.carries_only_retained_neuron_structure(),
                    "member_layers": member_layers,
                    "original_bond_layers": bond_layers,
                    "member_count": mosaic.member_lineages().len(),
                    "original_bond_count": mosaic.original_bonds().len(),
                    "has_recurrent_cell": retained.recurrent_lineage.is_some(),
                }))
            }).collect::<Vec<_>>();
        json!({
            "association": association.iter().map(|byte| format!("{byte:02x}")).collect::<String>(),
            "formations": formations,
        })
    }).collect::<Vec<_>>())
}

fn decode_saved_cognitive(bytes: &[u8]) -> ResidentCognitiveFormationState {
    if ResidentCognitiveFormationState::encoded_is_current(bytes) {
        return ResidentCognitiveFormationState::decode(bytes, usize::MAX).unwrap();
    }
    let migrated = ResidentCognitiveFormationState::migrate_to_current_format(bytes, usize::MAX).unwrap();
    ResidentCognitiveFormationState::decode(&migrated, usize::MAX).unwrap()
}

#[test]
fn saved_lesson_association_retention() {
    let Ok(predecessor_path) = std::env::var("GUALA_MEMORY_PREDECESSOR") else { return; };
    let (_, cognitive, _) = parse_envelope_with_body(&fs::read(predecessor_path).unwrap());
    let predecessor = decode_saved_cognitive(&cognitive);
    let state_bytes = fs::read(std::env::var("GUALA_MEMORY_STATE").unwrap()).unwrap();
    let state = decode_saved_cognitive(&state_bytes);
    let body = ArticulatedBodyState::decode(
        &fs::read(std::env::var("GUALA_MEMORY_BODY").unwrap()).unwrap(),
    ).unwrap();
    let associations = state.topology_index.flat_locations.iter()
        .map(|location| location.2)
        .filter(|lineage| state.topology_index.layer_of(*lineage) == Some(7)
            && predecessor.topology_index.layer_of(*lineage).is_none())
        .collect::<Vec<_>>();
    assert_eq!(associations.len(), 4, "the saved one-lesson successor has four new associations");
    let before = census(&state, &associations);
    drop(predecessor);
    drop(cognitive);
    drop(state_bytes);
    let terminal_by_motor = state.cohorts.iter()
        .flat_map(|cohort| cohort.anatomy.mounts().iter().zip(cohort.anatomy.neuron_lineages()))
        .filter_map(|(mount, lineage)| mount.body_effector_terminal().map(|terminal| (*lineage, terminal)))
        .collect::<BTreeMap<_, _>>();
    let motors = terminal_by_motor.keys().copied().collect::<BTreeSet<_>>();
    let tail = run_guided_vocal_continuation(
        state, body, None, &[], 1, 4, &motors, &terminal_by_motor,
    );
    let after = census(&tail.state, &associations);
    fs::write(std::env::var("GUALA_MEMORY_OUT").unwrap(), serde_json::to_vec_pretty(&json!({
        "measurement_only": true,
        "continuation_clocks": 4,
        "before": before,
        "after": after,
        "pulses": tail.pulses,
        "internal_reassemblies": tail.internal_reassemblies,
    })).unwrap()).unwrap();
}

fn interval_census(
    state: &ResidentCognitiveFormationState,
    observation: &CognitiveFormationObservation,
    associations: &[[u8; 16]],
) -> Value {
    let emitted = observation.emitted_neuron_fractals.iter()
        .map(|fractal| fractal.neuron_lineage).collect::<BTreeSet<_>>();
    let active = observation.active_physical_bonds.iter().copied().collect::<BTreeSet<_>>();
    json!(associations.iter().map(|association| {
        let topology = &state.topology_index;
        let flat = topology.flat_for_lineage(*association).unwrap();
        let mut participants = BTreeSet::from([*association]);
        let mut association_contacts = 0;
        let mut observed_active_contacts = 0;
        for index in &topology.incident_contacts_by_flat[flat] {
            let contact = topology.contacts[*index];
            let other = if contact.left == flat { contact.right } else { contact.left };
            let integration = topology.flat_locations[other].2;
            if topology.layer_of(integration) != Some(6) { continue; }
            association_contacts += 1;
            observed_active_contacts += usize::from(active.contains(&contact.stable_bond));
            participants.insert(integration);
            for source_index in &topology.incident_contacts_by_flat[other] {
                let source_contact = topology.contacts[*source_index];
                let source_flat = if source_contact.left == other {
                    source_contact.right
                } else { source_contact.left };
                let (cohort, neuron, lineage) = topology.flat_locations[source_flat];
                if matches!(topology.layer_of(lineage), Some(0..=5))
                    && state.cohorts[cohort].anatomy.mounts()[neuron].source_site().is_some() {
                    participants.insert(lineage);
                }
            }
        }
        let mut layers = BTreeMap::<u32, [usize; 4]>::new();
        for lineage in &participants {
            let flat = topology.flat_for_lineage(*lineage).unwrap();
            let (cohort_index, neuron, _) = topology.flat_locations[flat];
            let layer = topology.layer_of(*lineage).unwrap();
            let counts = layers.entry(layer).or_default();
            counts[0] += 1;
            counts[1] += usize::from(emitted.contains(lineage));
            if let Some(experience) = &state.cohorts[cohort_index].pending_experience {
                if let Some(members) = experience.pending_members() {
                    if let Some(member) = members.iter().find(|member| member.neuron_index == neuron) {
                        counts[2] += 1;
                        counts[3] += usize::from(member.settled);
                    }
                }
            }
        }
        json!({
            "association": association.iter().map(|byte| format!("{byte:02x}")).collect::<String>(),
            "mounted_neighborhood_is_only_an_upper_bound": true,
            "mounted_lineages": participants.iter().map(|lineage| lineage.iter()
                .map(|byte| format!("{byte:02x}")).collect::<String>()).collect::<Vec<_>>(),
            "layer_columns": ["mounted", "emitted_this_interval", "pending", "pending_settled"],
            "layers": layers,
            "association_l6_contacts": association_contacts,
            "observed_active_l6_contacts_not_causal_selector": observed_active_contacts,
        })
    }).collect::<Vec<_>>())
}


fn focused_input_census(
    state: &ResidentCognitiveFormationState,
    observation: &CognitiveFormationObservation,
    associations: &[[u8; 16]],
    focused: &[([u8; 16], Vec<crate::physical_mosaic::StablePhysicalBondReference>)],
    earlier_emissions: &BTreeSet<[u8; 16]>,
) -> Value {
    let emitted = observation.emitted_neuron_fractals.iter()
        .map(|fractal| fractal.neuron_lineage).collect::<BTreeSet<_>>();
    let hex = |lineage: &[u8; 16]| lineage.iter()
        .map(|byte| format!("{byte:02x}")).collect::<String>();
    json!(associations.iter().map(|association| {
        let inputs = focused.iter().filter(|entry| entry.0 == *association)
            .map(|(_, bonds)| {
                let endpoints = bonds.iter().flat_map(|bond| {
                    let (left, right) = bond.endpoints();
                    [left, right]
                }).collect::<BTreeSet<_>>();
                let mut layers = BTreeMap::<u32, [usize; 3]>::new();
                for lineage in &endpoints {
                    let counts = layers.entry(state.topology_index.layer_of(*lineage).unwrap()).or_default();
                    counts[0] += 1;
                    counts[1] += usize::from(emitted.contains(lineage));
                    counts[2] += usize::from(earlier_emissions.contains(lineage));
                }
                json!({
                    "bond_count": bonds.len(),
                    "endpoint_layers": layers,
                    "bonds": bonds.iter().map(|bond| {
                        let (left, right) = bond.endpoints();
                        json!([hex(&left), hex(&right)])
                    }).collect::<Vec<_>>(),
                })
            }).collect::<Vec<_>>();
        json!({
            "association": hex(association),
            "columns": ["exact_endpoints", "emitted_now", "emitted_on_earlier_trace_clock"],
            "inputs": inputs,
        })
    }).collect::<Vec<_>>())
}

#[test]
fn saved_lesson_fractal_admission_trace() { run_saved_lesson_trace(false); }

#[test]
#[ignore = "requires the authenticated saved production lesson paths"]
fn candidate117_saved_lesson_exact_sound_body_handoff() { run_saved_lesson_trace(true); }


fn settle_trace_body(
    body: &ArticulatedBodyState,
    observation: &CognitiveFormationObservation,
) -> (
    crate::virtual_articulatory_body::ArticulatoryBodyTransition,
    Vec<crate::virtual_articulated_body::BodyProprioceptiveConsequence>,
) {
    let mut carriers = BTreeMap::new();
    for event in &observation.motor_unit_recruitments {
        let total = carriers.entry(event.body_effector_terminal).or_insert(0_u128);
        *total = total.checked_add(event.outward_elementary_carriers).unwrap();
    }
    let drives = if carriers.is_empty() { AdmittedBodyEffectorDrives::quiescent() } else {
        AdmittedBodyEffectorDrives::admit(carriers.into_iter().map(|(terminal, outward_elementary_carriers)| {
            BodyEffectorDrive { terminal, outward_elementary_carriers }
        }).collect()).unwrap()
    };
    let respiratory = observation.articulatory_unit_recruitments.iter()
        .try_fold(0_u128, |total, event| total.checked_add(event.outward_elementary_carriers)).unwrap();
    let moved = settle_body_effector_drives(&body, &drives, BODY_SETTLEMENT_CLOCK_MICROSECONDS).unwrap();
    let acoustic = settle_native_articulatory_interval(
        moved.successor, &moved.proprioceptive_consequences, respiratory, 4_000,
    ).unwrap();
    (acoustic, moved.proprioceptive_consequences)
}

fn run_saved_lesson_trace(require_handoff: bool) {
    let predecessor_path = match std::env::var("GUALA_MEMORY_PREDECESSOR") {
        Ok(path) => path,
        Err(_) if require_handoff => panic!("authenticated predecessor path is required"),
        Err(_) => return,
    };
    let (_, cognitive, _) = parse_envelope_with_body(&fs::read(predecessor_path).unwrap());
    let predecessor = decode_saved_cognitive(&cognitive);
    let mut state = decode_saved_cognitive(
        &fs::read(std::env::var("GUALA_MEMORY_STATE").unwrap()).unwrap(),
    );
    let mut body = ArticulatedBodyState::decode(
        &fs::read(std::env::var("GUALA_MEMORY_BODY").unwrap()).unwrap(),
    ).unwrap();
    let associations = state.topology_index.flat_locations.iter().map(|entry| entry.2)
        .filter(|lineage| state.topology_index.layer_of(*lineage) == Some(7)
            && predecessor.topology_index.layer_of(*lineage).is_none()).collect::<Vec<_>>();
    assert_eq!(associations.len(), 4, "trace is scoped to the saved single lesson");
    drop(predecessor);
    drop(cognitive);
    let terminal_by_motor = state.cohorts.iter()
        .flat_map(|cohort| cohort.anatomy.mounts().iter().zip(cohort.anatomy.neuron_lineages()))
        .filter_map(|(mount, lineage)| mount.body_effector_terminal().map(|terminal| (*lineage, terminal)))
        .collect::<BTreeMap<_, _>>();
    let motors = terminal_by_motor.keys().copied().collect::<BTreeSet<_>>();
    // Establish exact equivalence to the existing chronology before trusting
    // this diagnostic loop. No physics or memory code is duplicated here.
    let oracle = run_guided_vocal_continuation(
        state.clone(), body.clone(), None, &[], 1, 4, &motors, &terminal_by_motor,
    );
    let expected_state = oracle.state.encode(usize::MAX).unwrap();
    let expected_body = oracle.body.encode().unwrap();
    drop(oracle);
    let mut residency = None;
    let mut pending_motor = None;
    let mut pending_sound = None;
    let mut intervals = Vec::new();
    let mut earlier_emissions = BTreeSet::new();
    for clock in 1..=4_u64 {
        let consuming_body_owned_pressure = pending_sound.is_some();
        let mut sources = Vec::new();
        if let Some(source) = pending_motor.take() { sources.push(source); }
        if let Some(source) = pending_sound.take() { sources.push(source); }
        if sources.is_empty() { sources.push(probe_self_hearing_episode(&[0_i16; 4_000])); }
        let admitted = sources.iter().map(super::super::admitted_fixture_episode).collect::<Vec<_>>();
        super::super::FOCUSED_ORIGINAL_INPUT_TRACE.with(|slot| {
            assert!(slot.borrow_mut().replace(Vec::new()).is_none());
        });
        super::super::CAUSAL_ORIGINAL_INPUT_TRACE.with(|slot| {
            assert!(slot.borrow_mut().replace(Vec::new()).is_none());
        });
        let (successor, observation) = state.advance_coexisting_admitted_transition_with_residency(
            &admitted, usize::MAX, true, !consuming_body_owned_pressure, false,
            &mut residency, ExactRational::integer(0), None,
        ).unwrap();
        let focused = super::super::FOCUSED_ORIGINAL_INPUT_TRACE.with(|slot| {
            slot.borrow_mut().take().unwrap()
        });
        let causal = super::super::CAUSAL_ORIGINAL_INPUT_TRACE.with(|slot| {
            slot.borrow_mut().take().unwrap()
        });
        let hex = |lineage: &[u8; 16]| lineage.iter()
            .map(|byte| format!("{byte:02x}")).collect::<String>();
        intervals.push(json!({
            "clock": clock,
            "raw_causal_bonds_before_selection": causal.iter().map(|bond| {
                let (left, right) = bond.endpoints();
                json!([hex(&left), hex(&right), bond.parallel_ordinal()])
            }).collect::<Vec<_>>(),
            "emitted_lineages": observation.emitted_neuron_fractals.iter()
                .map(|fractal| hex(&fractal.neuron_lineage)).collect::<Vec<_>>(),
            "total_emitted_fractals": observation.emitted_neuron_fractals.len(),
            "association_neighborhoods": interval_census(&successor, &observation, &associations),
            "formation_census": census(&successor, &associations),
            "exact_focused_inputs": focused_input_census(
                &successor, &observation, &associations, &focused, &earlier_emissions,
            ),
        }));
        earlier_emissions.extend(observation.emitted_neuron_fractals.iter()
            .map(|fractal| fractal.neuron_lineage));
        let (acoustic, consequences) = settle_trace_body(&body, &observation);
        if !consequences.is_empty() {
            pending_motor = Some(admit_articulated_body_consequence_source(
                1 + clock + 1, &consequences,
            ).unwrap());
        }
        if acoustic.radiated_pressure_pcm.iter().any(|sample| *sample != 0) {
            pending_sound = Some(probe_self_hearing_episode(&acoustic.radiated_pressure_pcm));
        }
        state = successor;
        body = acoustic.successor_body;
    }
    assert_eq!(state.encode(usize::MAX).unwrap(), expected_state, "diagnostic must preserve exact native successor");
    assert_eq!(body.encode().unwrap(), expected_body, "diagnostic must preserve exact body successor");
    let cold = ResidentCognitiveFormationState::decode(&expected_state, usize::MAX).unwrap();
    assert_eq!(cold.encode(usize::MAX).unwrap(), expected_state);
    let exact_handoffs = associations.iter().map(|association| {
        let indices = state.formation_index.candidate_indices([*association], std::iter::empty());
        let owner_count = indices.len();
        let matching = indices.into_iter().filter(|index| {
            let original = &state.mosaics[*index].mosaic;
            let hubs = super::super::pending_original_association_lineages(
                original, &state.topology_index,
            ).unwrap();
            let sound = original.member_lineages().iter()
                .filter(|lineage| state.topology_index.layer_of(**lineage) == Some(1)).count();
            let body = original.member_lineages().iter()
                .filter(|lineage| state.topology_index.layer_of(**lineage) == Some(5)).count();
            hubs.as_slice() == [*association] && sound >= 3 && body >= 1
                && original.member_lineages().binary_search(association).is_ok()
        }).collect::<Vec<_>>();
        owner_count == 1 && matching.len() == 1
    }).collect::<Vec<_>>();
    let handoff_closed = exact_handoffs.iter().all(|closed| *closed);
    let leaf_count = state.settled_fractals.len();
    assert!(leaf_count <= state.topology_index.flat_locations.len());
    let mut next_interval_restart_exact = false;
    if require_handoff && handoff_closed {
        let consuming_body_owned_pressure = pending_sound.is_some();
        let mut sources = Vec::new();
        if let Some(source) = pending_motor.take() { sources.push(source); }
        if let Some(source) = pending_sound.take() { sources.push(source); }
        if sources.is_empty() { sources.push(probe_self_hearing_episode(&[0_i16; 4_000])); }
        let admitted = sources.iter().map(super::super::admitted_fixture_episode).collect::<Vec<_>>();
        let (warm_next, warm_observation) = state.advance_coexisting_admitted_transition_with_residency(
            &admitted, usize::MAX, true, !consuming_body_owned_pressure, false,
            &mut residency, ExactRational::integer(0), None,
        ).unwrap();
        let (cold_next, cold_observation) = cold.advance_coexisting_admitted_transition_with_residency(
            &admitted, usize::MAX, true, !consuming_body_owned_pressure, false,
            &mut None, ExactRational::integer(0), None,
        ).unwrap();
        assert_eq!(warm_next.encode(usize::MAX).unwrap(), cold_next.encode(usize::MAX).unwrap());
        assert_eq!(warm_observation, cold_observation);
        let warm_body = settle_trace_body(&body, &warm_observation);
        let cold_body = settle_trace_body(
            &ArticulatedBodyState::decode(&expected_body).unwrap(), &cold_observation,
        );
        assert_eq!(warm_body, cold_body, "exact body, pressure and physical return survive restart");
        next_interval_restart_exact = true;
    }
    fs::write(std::env::var("GUALA_MEMORY_OUT").unwrap(), serde_json::to_vec_pretty(&json!({
        "measurement_only": !require_handoff,
        "existing_continuation_successor_exact": true,
        "exact_sound_body_handoffs": exact_handoffs,
        "sound_body_handoff_closed": handoff_closed,
        "settled_leaf_count": leaf_count,
        "cold_codec_exact": true,
        "next_interval_restart_exact": next_interval_restart_exact,
        "intervals": intervals,
    })).unwrap()).unwrap();
    if require_handoff {
        assert!(handoff_closed, "each distinct hub must retain real sound and body leaves");
        assert!(next_interval_restart_exact);
    }
}
