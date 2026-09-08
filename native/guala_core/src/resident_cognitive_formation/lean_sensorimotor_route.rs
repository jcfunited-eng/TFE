//! One sparse learned route from an exact multisensory body occurrence to its
//! exact typed motor. This module owns no semantic labels, action scripts,
//! sequence state, population targets, or whole-organism scans.

use super::*;

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

/// Mount or reuse one quiescent `association -> ordering -> motor` route for
/// each exact moved vocal-body occurrence.
///
/// The association and moved regulation were both derived from the same
/// authenticated occurrence. The regulation already has one lived
/// proprioceptive contact to its fixed typed motor. This function reads only
/// those local incident contacts. It neither seeds the new ordering cell nor
/// causes an action in the teaching interval; later physical current across
/// the retained association/ordering contact is required.
pub(super) fn mount_exact_vocal_sensorimotor_routes(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    electrical_fabric: &mut ResidentElectricalFabric,
    topology: &ResidentTopologyIndex,
    associations: &ReachedAssociationsByOccurrence,
    moved_regulations: &[Vec<[u8; 16]>],
) -> Result<(), FormationError> {
    if associations.lineages.len() != moved_regulations.len() {
        return Err(FormationError::NoncanonicalState);
    }

    let local_neighbours = |lineage: [u8; 16]| -> Result<&[usize], FormationError> {
        let flat = topology.flat_for_lineage(lineage)?;
        topology
            .neighbours_by_flat
            .get(flat)
            .map(Box::as_ref)
            .ok_or(FormationError::NeuronLineageAuthorityAbsent)
    };

    let mut exact_routes = BTreeSet::<([u8; 16], [u8; 16])>::new();
    let mut additions = Vec::<([u8; 16], [u8; 16], ExactRational)>::new();
    for (occurrence_associations, occurrence_regulations) in
        associations.lineages.iter().zip(moved_regulations)
    {
        for association in occurrence_associations.iter().copied() {
            if topology.layer_of(association) != Some(7) {
                return Err(FormationError::NeuronLineageAuthorityChanged);
            }
            for regulation in occurrence_regulations.iter().copied() {
                if topology.layer_of(regulation) != Some(8) {
                    return Err(FormationError::NeuronLineageAuthorityChanged);
                }
                let mut motors = local_neighbours(regulation)?
                    .iter()
                    .copied()
                    .filter_map(|flat| {
                        let mount = mounted_at(cohorts, topology, flat).ok()?;
                        let terminal = mount.body_effector_terminal()?;
                        (mount.source_site().is_none()
                            && mount.place().layer() == 12)
                            .then_some((topology.flat_locations[flat].2, terminal))
                    })
                    .collect::<Vec<_>>();
                motors.sort_unstable();
                motors.dedup();
                let motor = match motors.as_slice() {
                    [(motor, terminal)] if terminal.axis().is_vocal_articulator() => motor,
                    [(_, _)] => continue,
                    _ => return Err(FormationError::NeuronLineageAuthorityChanged),
                };
                if !exact_routes.insert((association, *motor)) {
                    continue;
                }

                let mut matching_orderings = local_neighbours(association)?
                    .iter()
                    .copied()
                    .filter_map(|flat| {
                        (topology.layer_of(topology.flat_locations[flat].2) == Some(11))
                            .then_some((flat, topology.flat_locations[flat].2))
                    })
                    .filter_map(|(flat, lineage)| {
                        let mut motor_neighbours = topology.neighbours_by_flat[flat]
                            .iter()
                            .copied()
                            .filter_map(|neighbour| {
                                (mounted_at(cohorts, topology, neighbour)
                                    .ok()?
                                    .place()
                                    .layer()
                                    == 12)
                                    .then_some(topology.flat_locations[neighbour].2)
                            })
                            .collect::<Vec<_>>();
                        motor_neighbours.sort_unstable();
                        motor_neighbours.dedup();
                        (motor_neighbours.as_slice() == [*motor]).then_some(lineage)
                    })
                    .collect::<Vec<_>>();
                matching_orderings.sort_unstable();
                matching_orderings.dedup();
                let ordering = match matching_orderings.as_slice() {
                    [ordering] => *ordering,
                    [] => mount_next_intrinsic_in_layer(
                        cohorts,
                        resting_population,
                        next_lineage_ordinal,
                        11,
                    )?,
                    _ => return Err(FormationError::NeuronLineageAuthorityChanged),
                };
                if !electrical_fabric.contains_contact(association, regulation)
                    && !additions.iter().any(|(left, right, _)| {
                        canonical_lineage_pair(*left, *right)
                            == canonical_lineage_pair(association, regulation)
                    })
                {
                    additions.push((
                        association,
                        regulation,
                        ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                    ));
                }
                for participant in [association, *motor] {
                    if !electrical_fabric.contains_contact(ordering, participant)
                        && !additions.iter().any(|(left, right, _)| {
                            canonical_lineage_pair(*left, *right)
                                == canonical_lineage_pair(ordering, participant)
                        })
                    {
                        additions.push((
                            ordering,
                            participant,
                            ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                        ));
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
