//! One sparse learned route from an exact externally reassembled formation to
//! its exact typed vocal motor. This module owns no semantic labels, scripts,
//! timers, population targets, or whole-organism action authority.

use super::*;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct VocalCognitiveActionRoute {
    pub(super) association_lineage: [u8; 16],
    pub(super) association_bond: StablePhysicalBondReference,
    pub(super) recurrent_lineage: [u8; 16],
    pub(super) ordering_lineage: [u8; 16],
    pub(super) motor_lineage: [u8; 16],
    pub(super) recurrent_bond: StablePhysicalBondReference,
    pub(super) learned_bond: StablePhysicalBondReference,
}

fn mounted_at<'a>(
    cohorts: &'a [ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    flat: usize,
) -> Result<&'a ReachedNeuronMount, FormationError> {
    let (cohort_index, neuron_index, _) = topology
        .flat_locations
        .get(flat)
        .copied()
        .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
    cohorts
        .get(cohort_index)
        .and_then(|cohort| cohort.anatomy.mounts().get(neuron_index))
        .ok_or(FormationError::NeuronLineageAuthorityAbsent)
}

fn fabric_bond_between(
    topology: &ResidentTopologyIndex,
    left_lineage: [u8; 16],
    right_lineage: [u8; 16],
) -> Result<Option<StablePhysicalBondReference>, FormationError> {
    let left_flat = topology.flat_for_lineage(left_lineage)?;
    let right_flat = topology.flat_for_lineage(right_lineage)?;
    let mut matching = topology.incident_contacts_by_flat[left_flat]
        .iter()
        .copied()
        .filter_map(|contact_index| {
            let contact = topology.contacts.get(contact_index)?;
            (matches!(contact.origin, ResidentContactOrigin::Fabric { .. })
                && ((contact.left == left_flat && contact.right == right_flat)
                    || (contact.left == right_flat && contact.right == left_flat)))
                .then_some(contact.stable_bond)
        })
        .collect::<Vec<_>>();
    matching.sort_unstable();
    matching.dedup();
    match matching.as_slice() {
        [] => Ok(None),
        [bond] => Ok(Some(*bond)),
        _ => Err(FormationError::NeuronLineageAuthorityChanged),
    }
}

fn integrations_for_receptor(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    receptor_lineage: [u8; 16],
) -> Result<Vec<[u8; 16]>, FormationError> {
    let receptor_flat = topology.flat_for_lineage(receptor_lineage)?;
    let receptor = mounted_at(cohorts, topology, receptor_flat)?;
    if receptor
        .source_site()
        .is_none_or(|site| site.sense() == PhysicalSourceSense::Body)
    {
        return Ok(Vec::new());
    }
    let integration_place = local_integration_place(receptor.place())?;
    let mut matching = topology.incident_contacts_by_flat[receptor_flat]
        .iter()
        .copied()
        .filter_map(|contact_index| {
            let contact = topology.contacts.get(contact_index)?;
            if !matches!(contact.origin, ResidentContactOrigin::Fabric { .. }) {
                return None;
            }
            let other = if contact.left == receptor_flat {
                contact.right
            } else {
                contact.left
            };
            let mount = mounted_at(cohorts, topology, other).ok()?;
            (mount.source_site().is_none() && mount.place() == integration_place)
                .then_some(topology.flat_locations[other].2)
        })
        .collect::<Vec<_>>();
    matching.sort_unstable();
    matching.dedup();
    Ok(matching)
}

/// True only when current sound physically reached one of this learned
/// route's own layer-6 integrations. Other senses, silence, and unrelated
/// sound cannot found a vocal act.
pub(super) fn current_sound_reaches_route(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    current_seed_lineages: &[[u8; 16]],
    route: VocalCognitiveActionRoute,
) -> Result<bool, FormationError> {
    let association_flat = topology.flat_for_lineage(route.association_lineage)?;
    let association_integrations = topology.neighbours_by_flat[association_flat]
        .iter()
        .copied()
        .filter_map(|flat| {
            (topology.layer_of(topology.flat_locations[flat].2) == Some(6))
                .then_some(topology.flat_locations[flat].2)
        })
        .collect::<BTreeSet<_>>();
    for cue in current_seed_lineages.iter().copied() {
        let cue_flat = topology.flat_for_lineage(cue)?;
        if mounted_at(cohorts, topology, cue_flat)?
            .source_site()
            .is_none_or(|site| site.sense() != PhysicalSourceSense::Sound)
        {
            continue;
        }
        if integrations_for_receptor(cohorts, topology, cue)?
            .iter()
            .any(|integration| association_integrations.contains(integration))
        {
            return Ok(true);
        }
    }
    Ok(false)
}

fn exact_vocal_motor_for_regulation(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    regulation_lineage: [u8; 16],
) -> Result<Option<[u8; 16]>, FormationError> {
    if topology.layer_of(regulation_lineage) != Some(8) {
        return Err(FormationError::NeuronLineageAuthorityChanged);
    }
    let regulation_flat = topology.flat_for_lineage(regulation_lineage)?;
    let mut motors = topology.neighbours_by_flat[regulation_flat]
        .iter()
        .copied()
        .filter_map(|flat| {
            let mount = mounted_at(cohorts, topology, flat).ok()?;
            let terminal = mount.body_effector_terminal()?;
            (mount.source_site().is_none()
                && mount.place().layer() == 12
                && terminal.axis().is_vocal_articulator())
                .then_some(topology.flat_locations[flat].2)
        })
        .collect::<Vec<_>>();
    motors.sort_unstable();
    motors.dedup();
    match motors.as_slice() {
        [] => Ok(None),
        [motor] => Ok(Some(*motor)),
        _ => Err(FormationError::NeuronLineageAuthorityChanged),
    }
}

/// Resolve the one current vocal route whose persisted first two relevant
/// contacts are exactly one layer-7 association and one layer-9 retained
/// formation. Contact insertion order is the physical authorship record.
pub(super) fn vocal_cognitive_action_route_for_motor(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    motor_lineage: [u8; 16],
) -> Result<Vec<VocalCognitiveActionRoute>, FormationError> {
    let motor_flat = topology.flat_for_lineage(motor_lineage)?;
    let motor_mount = mounted_at(cohorts, topology, motor_flat)?;
    if motor_mount.source_site().is_some()
        || motor_mount.place().layer() != 12
        || motor_mount
            .body_effector_terminal()
            .is_none_or(|terminal| !terminal.axis().is_vocal_articulator())
    {
        return Ok(Vec::new());
    }
    let mut routes = Vec::new();
    for ordering_flat in topology.neighbours_by_flat[motor_flat].iter().copied() {
        if topology.layer_of(topology.flat_locations[ordering_flat].2) != Some(11) {
            continue;
        }
        let ordering_lineage = topology.flat_locations[ordering_flat].2;
        let mut founders = Vec::new();
        for contact_index in topology.incident_contacts_by_flat[ordering_flat]
            .iter()
            .copied()
        {
            let contact = topology.contacts[contact_index];
            if !matches!(contact.origin, ResidentContactOrigin::Fabric { .. }) {
                continue;
            }
            let other_flat = if contact.left == ordering_flat {
                contact.right
            } else {
                contact.left
            };
            if matches!(topology.layer_of(topology.flat_locations[other_flat].2), Some(7 | 9 | 10))
            {
                founders.push((topology.flat_locations[other_flat].2, contact.stable_bond));
                if founders.len() == 2 {
                    break;
                }
            }
        }
        let [(first, first_bond), (second, second_bond)] = founders.as_slice() else {
            continue;
        };
        let (association_lineage, association_bond, recurrent_lineage, recurrent_bond) =
            match (topology.layer_of(*first), topology.layer_of(*second)) {
                (Some(7), Some(9)) => (*first, *first_bond, *second, *second_bond),
                (Some(9), Some(7)) => (*second, *second_bond, *first, *first_bond),
                _ => continue,
            };
        let Some(learned_bond) = fabric_bond_between(topology, ordering_lineage, motor_lineage)?
        else {
            continue;
        };
        routes.push(VocalCognitiveActionRoute {
            association_lineage,
            association_bond,
            recurrent_lineage,
            ordering_lineage,
            motor_lineage,
            recurrent_bond,
            learned_bond,
        });
    }
    routes.sort_by_key(|route| (route.ordering_lineage, route.recurrent_lineage));
    routes.dedup();
    Ok(routes)
}

/// Grow or reuse one quiescent L7 + L9 -> L11 -> L12 vocal route only when
/// the external cue really reassembled the retained L9 formation in the same
/// lived occurrence as the tutor's moved vocal regulation. No action is
/// prepared in this birth interval.
pub(super) fn mount_exact_reassembled_vocal_action_routes(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    electrical_fabric: &mut ResidentElectricalFabric,
    topology: &ResidentTopologyIndex,
    associations: &ReachedAssociationsByOccurrence,
    moved_regulations: &[Vec<[u8; 16]>],
    reassemblies: &[ExternallyReassembledFormationFrontierObservation],
) -> Result<(), FormationError> {
    if associations.lineages.len() != moved_regulations.len() {
        return Err(FormationError::NoncanonicalState);
    }
    let mut exact_routes = BTreeSet::new();
    let mut additions = Vec::<([u8; 16], [u8; 16], ExactRational)>::new();
    for (occurrence_associations, occurrence_regulations) in
        associations.lineages.iter().zip(moved_regulations)
    {
        for association in occurrence_associations.iter().copied() {
            let association_flat = topology.flat_for_lineage(association)?;
            let association_integrations = topology.neighbours_by_flat[association_flat]
                .iter()
                .copied()
                .filter_map(|flat| {
                    (topology.layer_of(topology.flat_locations[flat].2) == Some(6))
                        .then_some(topology.flat_locations[flat].2)
                })
                .collect::<BTreeSet<_>>();
            let mut matching_recurrents = BTreeSet::new();
            for reassembly in reassemblies {
                let mut matched = false;
                for cue in reassembly.cue_lineages.iter().copied() {
                    if integrations_for_receptor(cohorts, topology, cue)?
                        .iter()
                        .any(|integration| association_integrations.contains(integration))
                    {
                        matched = true;
                        break;
                    }
                }
                if matched {
                    matching_recurrents.insert(reassembly.recurrent_lineage);
                }
            }
            for recurrent in matching_recurrents {
                if topology.layer_of(recurrent) != Some(9) {
                    return Err(FormationError::NeuronLineageAuthorityChanged);
                }
                for regulation in occurrence_regulations.iter().copied() {
                    let Some(motor) =
                        exact_vocal_motor_for_regulation(cohorts, topology, regulation)?
                    else {
                        continue;
                    };
                    if !exact_routes.insert((association, recurrent, motor)) {
                        continue;
                    }
                    let mut existing = Vec::new();
                    for ordering_flat in
                        topology.neighbours_by_flat[association_flat].iter().copied()
                    {
                        let ordering = topology.flat_locations[ordering_flat].2;
                        if topology.layer_of(ordering) != Some(11) {
                            continue;
                        }
                        let founders = topology.incident_contacts_by_flat[ordering_flat]
                            .iter()
                            .copied()
                            .filter_map(|contact_index| {
                                let contact = topology.contacts[contact_index];
                                if !matches!(contact.origin, ResidentContactOrigin::Fabric { .. }) {
                                    return None;
                                }
                                let other = if contact.left == ordering_flat {
                                    contact.right
                                } else {
                                    contact.left
                                };
                                matches!(
                                    topology.layer_of(topology.flat_locations[other].2),
                                    Some(7 | 9 | 10)
                                )
                                .then_some(topology.flat_locations[other].2)
                            })
                            .take(2)
                            .collect::<Vec<_>>();
                        if founders.as_slice() == [association, recurrent]
                            || founders.as_slice() == [recurrent, association]
                        {
                            existing.push(ordering);
                        }
                    }
                    existing.sort_unstable();
                    existing.dedup();
                    let ordering = match existing.as_slice() {
                        [ordering] => *ordering,
                        [] => mount_next_intrinsic_in_layer(
                            cohorts,
                            resting_population,
                            next_lineage_ordinal,
                            11,
                        )?,
                        _ => return Err(FormationError::NeuronLineageAuthorityChanged),
                    };
                    for participant in [association, recurrent, motor] {
                        if !electrical_fabric.contains_contact(ordering, participant)
                            && !additions.iter().any(|(left, right, _)| {
                                canonical_lineage_pair(*left, *right)
                                    == canonical_lineage_pair(ordering, participant)
                            })
                        {
                            additions.push((
                                ordering,
                                participant,
                                ExactRational::integer(
                                    DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS,
                                ),
                            ));
                        }
                    }
                }
            }
        }
    }
    if !additions.is_empty() {
        *electrical_fabric = electrical_fabric
            .append_contacts(&additions)
            .map_err(FormationError::ResidentElectricalUnavailable)?;
    }
    Ok(())
}
