//! Read-only census of one saved lesson's new association anatomy.
//! This module is reachable only through the test-only reservoir probe.

use super::*;
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

#[test]
fn saved_lesson_association_retention() {
    let Ok(predecessor_path) = std::env::var("GUALA_MEMORY_PREDECESSOR") else { return; };
    let (_, cognitive, _) = parse_envelope_with_body(&fs::read(predecessor_path).unwrap());
    let predecessor = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX).unwrap();
    let state_bytes = fs::read(std::env::var("GUALA_MEMORY_STATE").unwrap()).unwrap();
    let state = ResidentCognitiveFormationState::decode(&state_bytes, usize::MAX).unwrap();
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
