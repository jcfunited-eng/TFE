//! One sparse learned vocal posture retained from one exact guided body
//! settlement. This module owns no words, phases, scripts, timers, scores, or
//! whole-organism action authority.

use super::*;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(super) struct VocalPreparationContact {
    pub(super) lineage: [u8; 16],
    pub(super) bond: StablePhysicalBondReference,
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(super) struct VocalActionPreparation {
    pub(super) ordering_lineage: [u8; 16],
    pub(super) associations: Vec<VocalPreparationContact>,
    pub(super) motors: Vec<VocalPreparationContact>,
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(super) struct VocalCognitiveActionRoute {
    pub(super) preparation: VocalActionPreparation,
    pub(super) motor_lineage: [u8; 16],
    pub(super) learned_bond: StablePhysicalBondReference,
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(super) struct VocalCognitiveActionContinuationRoute {
    pub(super) source_ordering_lineage: [u8; 16],
    pub(super) destination_ordering_lineage: [u8; 16],
    pub(super) continuation_bond: StablePhysicalBondReference,
}

pub(super) fn exact_completed_vocal_preparation_discharge(
    preparation: &VocalActionPreparation,
    recruitments: &[MotorUnitRecruitment],
) -> Result<Option<(BTreeSet<[u8; 16]>, Vec<MotorPreparationTransfer>)>, FormationError> {
    let mut exact_motors = BTreeSet::new();
    let mut exact_transfers = Vec::new();
    for motor in &preparation.motors {
        let matching_recruitments = recruitments
            .iter()
            .filter(|event| event.neuron_lineage == motor.lineage)
            .collect::<Vec<_>>();
        let [recruitment] = matching_recruitments.as_slice() else {
            return if matching_recruitments.is_empty() {
                Ok(None)
            } else {
                Err(FormationError::NeuronLineageAuthorityChanged)
            };
        };
        if recruitment.outward_elementary_carriers == 0 {
            return Ok(None);
        }
        let matching_transfers = recruitment
            .preparation_transfers
            .iter()
            .filter(|arrival| {
                arrival.sender_layer == 11
                    && arrival.transfer.sender == preparation.ordering_lineage
                    && arrival.transfer.receiver == motor.lineage
                    && arrival.transfer.bond == motor.bond
                    && arrival.transfer.transferred_whole_carriers != 0
            })
            .copied()
            .collect::<Vec<_>>();
        let [arrival] = matching_transfers.as_slice() else {
            return if matching_transfers.is_empty() {
                Ok(None)
            } else {
                Err(FormationError::NeuronLineageAuthorityChanged)
            };
        };
        if !exact_motors.insert(motor.lineage) {
            return Err(FormationError::NeuronLineageAuthorityChanged);
        }
        exact_transfers.push(*arrival);
    }
    if exact_motors.len() != preparation.motors.len() {
        return Ok(None);
    }
    exact_transfers.sort_unstable();
    Ok(Some((exact_motors, exact_transfers)))
}

/// Prove one coordinated posture across its finite physical body act.
///
/// A motor is present either because it discharged now from its exact learned
/// L11 branch, or because that exact externally caused branch transferred on
/// the immediately preceding frontier and the body now returns movement from
/// the same typed terminal.  The latter is existing proprioception joined to
/// an existing bounded transfer receipt; no completion bit or elapsed-time
/// rule is introduced.  A partial body act remains a refusal.
pub(super) fn exact_completed_vocal_preparation_body_act(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    preparation: &VocalActionPreparation,
    recruitments: &[MotorUnitRecruitment],
    predecessor_frontier: &[ActiveElectricalFrontierEntry],
    moved_body_effectors: &[BodyEffectorTerminal],
) -> Result<Option<(BTreeSet<[u8; 16]>, Vec<MotorPreparationTransfer>)>, FormationError> {
    let predecessors = preparation_predecessors(cohorts, topology, preparation)?;
    if predecessors.len() > 1 {
        return Err(FormationError::NeuronLineageAuthorityChanged);
    }
    let is_learned_continuation = predecessors.len() == 1;
    let mut exact_motors = BTreeSet::new();
    let mut exact_transfers = Vec::new();
    for motor in &preparation.motors {
        let current = recruitments
            .iter()
            .filter(|event| {
                event.neuron_lineage == motor.lineage
                    && event.outward_elementary_carriers > 0
                    && event.preparation_transfers.iter().any(|arrival| {
                        arrival.sender_layer == 11
                            && arrival.transfer.sender == preparation.ordering_lineage
                            && arrival.transfer.receiver == motor.lineage
                            && arrival.transfer.bond == motor.bond
                            && arrival.transfer.transferred_whole_carriers > 0
                    })
            })
            .collect::<Vec<_>>();
        if current.len() > 1 {
            return Err(FormationError::NeuronLineageAuthorityChanged);
        }
        let transfer = if let Some(recruitment) = current.first() {
            let matches = recruitment
                .preparation_transfers
                .iter()
                .filter(|arrival| {
                    arrival.sender_layer == 11
                        && arrival.transfer.sender == preparation.ordering_lineage
                        && arrival.transfer.receiver == motor.lineage
                        && arrival.transfer.bond == motor.bond
                        && arrival.transfer.transferred_whole_carriers > 0
                })
                .copied()
                .collect::<Vec<_>>();
            let [arrival] = matches.as_slice() else {
                return Err(FormationError::NeuronLineageAuthorityChanged);
            };
            *arrival
        } else {
            let motor_flat = topology.flat_for_lineage(motor.lineage)?;
            let (cohort_index, neuron_index, _) = topology.flat_locations[motor_flat];
            let terminal = cohorts[cohort_index].anatomy.mounts()[neuron_index]
                .body_effector_terminal()
                .ok_or(FormationError::NeuronLineageAuthorityChanged)?;
            if moved_body_effectors.binary_search(&terminal).is_err() {
                return Ok(None);
            }
            let prior = predecessor_frontier
                .iter()
                .copied()
                .filter(|entry| {
                    (entry.carries_external_ingress_cause() || is_learned_continuation)
                        && !entry.carries_body_owned_acoustic_efference()
                        && entry.directed_transfer().is_some_and(|transfer| {
                            transfer.sender == preparation.ordering_lineage
                                && transfer.receiver == motor.lineage
                                && transfer.bond == motor.bond
                                && transfer.transferred_whole_carriers > 0
                        })
                })
                .collect::<Vec<_>>();
            let [entry] = prior.as_slice() else {
                return if prior.is_empty() {
                    Ok(None)
                } else {
                    Err(FormationError::NeuronLineageAuthorityChanged)
                };
            };
            MotorPreparationTransfer {
                transfer: entry
                    .directed_transfer()
                    .ok_or(FormationError::NoncanonicalState)?,
                sender_layer: 11,
            }
        };
        if !exact_motors.insert(motor.lineage) {
            return Err(FormationError::NeuronLineageAuthorityChanged);
        }
        exact_transfers.push(transfer);
    }
    if exact_motors.len() != preparation.motors.len() {
        return Ok(None);
    }
    exact_transfers.sort_unstable();
    exact_transfers.dedup();
    if exact_transfers.len() != preparation.motors.len() {
        return Err(FormationError::NeuronLineageAuthorityChanged);
    }
    Ok(Some((exact_motors, exact_transfers)))
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
    let mut matching = Vec::new();
    for contact_index in topology.incident_contacts_by_flat[left_flat]
        .iter()
        .copied()
    {
        let contact = topology
            .contacts
            .get(contact_index)
            .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
        if matches!(contact.origin, ResidentContactOrigin::Fabric { .. })
            && ((contact.left == left_flat && contact.right == right_flat)
                || (contact.left == right_flat && contact.right == left_flat))
        {
            matching.push(contact.stable_bond);
        }
    }
    matching.sort_unstable();
    matching.dedup();
    match matching.as_slice() {
        [] => Ok(None),
        [bond] => Ok(Some(*bond)),
        _ => Err(FormationError::NeuronLineageAuthorityChanged),
    }
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
    let mut motors = Vec::new();
    for flat in topology.neighbours_by_flat[regulation_flat].iter().copied() {
        let mount = mounted_at(cohorts, topology, flat)?;
        let Some(terminal) = mount.body_effector_terminal() else {
            continue;
        };
        if mount.source_site().is_none()
            && mount.place().layer() == 12
            && terminal.axis().is_vocal_articulator()
        {
            motors.push(topology.flat_locations[flat].2);
        }
    }
    motors.sort_unstable();
    motors.dedup();
    match motors.as_slice() {
        [] => Ok(None),
        [motor] => Ok(Some(*motor)),
        _ => Err(FormationError::NeuronLineageAuthorityChanged),
    }
}

fn contacts_at_layers(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    ordering_flat: usize,
    layers: &[u32],
) -> Result<Vec<VocalPreparationContact>, FormationError> {
    let mut contacts = Vec::new();
    for contact_index in topology.incident_contacts_by_flat[ordering_flat]
        .iter()
        .copied()
    {
        let contact = topology.contacts[contact_index];
        if !matches!(contact.origin, ResidentContactOrigin::Fabric { .. }) {
            continue;
        }
        let other = if contact.left == ordering_flat {
            contact.right
        } else {
            contact.left
        };
        let lineage = topology.flat_locations[other].2;
        if !topology
            .layer_of(lineage)
            .is_some_and(|layer| layers.contains(&layer))
        {
            continue;
        }
        if topology.layer_of(lineage) == Some(12)
            && mounted_at(cohorts, topology, other)?
                .body_effector_terminal()
                .is_none_or(|terminal| !terminal.axis().is_vocal_articulator())
        {
            continue;
        }
        contacts.push(VocalPreparationContact {
            lineage,
            bond: contact.stable_bond,
        });
    }
    contacts.sort_unstable();
    contacts.dedup();
    Ok(contacts)
}

pub(super) fn vocal_action_preparation_for_ordering(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    ordering_lineage: [u8; 16],
) -> Result<Option<VocalActionPreparation>, FormationError> {
    if topology.layer_of(ordering_lineage) != Some(11) {
        return Ok(None);
    }
    let ordering_flat = topology.flat_for_lineage(ordering_lineage)?;
    let associations = contacts_at_layers(cohorts, topology, ordering_flat, &[7])?;
    let motors = contacts_at_layers(cohorts, topology, ordering_flat, &[12])?;
    if associations.len() < 2 || associations.len() != motors.len() {
        return Ok(None);
    }
    Ok(Some(VocalActionPreparation {
        ordering_lineage,
        associations,
        motors,
    }))
}

pub(super) fn preparation_predecessors(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    preparation: &VocalActionPreparation,
) -> Result<Vec<[u8; 16]>, FormationError> {
    let ordering_flat = topology.flat_for_lineage(preparation.ordering_lineage)?;
    let ordering_index = mounted_at(cohorts, topology, ordering_flat)?
        .place()
        .topology_index();
    let mut predecessors = Vec::new();
    for flat in topology.neighbours_by_flat[ordering_flat].iter().copied() {
        let lineage = topology.flat_locations[flat].2;
        if topology.layer_of(lineage) == Some(11)
            && mounted_at(cohorts, topology, flat)?
                .place()
                .topology_index()
                < ordering_index
        {
            predecessors.push(lineage);
        }
    }
    predecessors.sort_unstable();
    predecessors.dedup();
    Ok(predecessors)
}

pub(super) fn vocal_cognitive_action_route_for_motor(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    motor_lineage: [u8; 16],
) -> Result<Vec<VocalCognitiveActionRoute>, FormationError> {
    let motor_flat = topology.flat_for_lineage(motor_lineage)?;
    if mounted_at(cohorts, topology, motor_flat)?
        .body_effector_terminal()
        .is_none_or(|terminal| !terminal.axis().is_vocal_articulator())
    {
        return Ok(Vec::new());
    }
    let mut routes = Vec::new();
    for ordering_flat in topology.neighbours_by_flat[motor_flat].iter().copied() {
        let ordering = topology.flat_locations[ordering_flat].2;
        let Some(preparation) = vocal_action_preparation_for_ordering(cohorts, topology, ordering)?
        else {
            continue;
        };
        let Some(motor_contact) = preparation
            .motors
            .iter()
            .find(|contact| contact.lineage == motor_lineage)
        else {
            continue;
        };
        let learned_bond = motor_contact.bond;
        routes.push(VocalCognitiveActionRoute {
            preparation,
            motor_lineage,
            learned_bond,
        });
    }
    routes.sort_unstable();
    routes.dedup();
    Ok(routes)
}

/// Resolve the one coordinated vocal preparation whose retained formation
/// reassembled from current sound and whose complete learned motor set has
/// positive conserved donor-work offers in this same settlement. Formation
/// membership supplies recognition; the work arrivals supply action
/// preparation. Neither fact alone is authority, and a tie is noncanonical.
pub(super) fn exact_reassembled_work_founded_vocal_preparation(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    reassembled_member_lineages: &BTreeSet<[u8; 16]>,
    learned_work: &[LearnedMotorWorkOffer],
) -> Result<Option<[u8; 16]>, FormationError> {
    let mut candidate_orderings = learned_work
        .iter()
        .filter(|offer| offer.offered_work_zeptojoules > BigRational::zero())
        .map(|offer| offer.ordering_lineage)
        .collect::<Vec<_>>();
    candidate_orderings.sort_unstable();
    candidate_orderings.dedup();

    let mut matches = Vec::new();
    for ordering in candidate_orderings {
        let Some(preparation) = vocal_action_preparation_for_ordering(cohorts, topology, ordering)?
        else {
            continue;
        };
        if !preparation
            .associations
            .iter()
            .any(|association| reassembled_member_lineages.contains(&association.lineage))
        {
            continue;
        }
        let complete_work = preparation.motors.iter().all(|motor| {
            learned_work.iter().any(|offer| {
                offer.motor_lineage == motor.lineage
                    && offer.offered_work_zeptojoules > BigRational::zero()
                    && offer.ordering_lineage == ordering
                    && offer.learned_bond == motor.bond
            })
        });
        if complete_work {
            matches.push(ordering);
        }
    }
    matches.sort_unstable();
    matches.dedup();
    match matches.as_slice() {
        [] => Ok(None),
        [ordering] => Ok(Some(*ordering)),
        _ => Err(FormationError::NeuronLineageAuthorityChanged),
    }
}

pub(super) fn frontier_reaches_vocal_action_preparation(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    entry: ActiveElectricalFrontierEntry,
) -> Result<Option<[u8; 16]>, FormationError> {
    if !entry.carries_external_ingress_cause() {
        return Ok(None);
    }
    let Some(cause) = entry.cause else {
        return Ok(None);
    };
    let Some(sender) = entry.sender() else {
        return Ok(None);
    };
    let ordering = entry.frontier_lineage();
    let Some(preparation) = vocal_action_preparation_for_ordering(cohorts, topology, ordering)?
    else {
        return Ok(None);
    };
    if !preparation_predecessors(cohorts, topology, &preparation)?.is_empty() {
        return Ok(None);
    }
    Ok(preparation
        .associations
        .iter()
        .any(|association| {
            cause.bond == association.bond
                && canonical_lineage_pair(association.lineage, ordering)
                    == canonical_lineage_pair(entry.receiver, sender)
        })
        .then_some(ordering))
}

/// C102 preserves a current reassembly at the association endpoint of its
/// exact founder contact while that contact already holds real carrier phase.
/// Generic propagation may reach the same ordering, but cannot create this
/// association-side zero-carrier antecedent. Read only the immediately
/// preceding retained boundary; neither ancestry nor a permanent mark is used.
pub(super) fn reassembled_vocal_founder_bonds(
    topology: &ResidentTopologyIndex,
    preceding_frontier: &[ActiveElectricalFrontierEntry],
) -> BTreeSet<StablePhysicalBondReference> {
    preceding_frontier
        .iter()
        .copied()
        .filter(|entry| {
            entry.is_zero_carrier_frontier()
                && entry.carries_external_ingress_cause()
                && topology.layer_of(entry.frontier_lineage()) == Some(7)
        })
        .filter_map(|entry| entry.cause.map(|cause| cause.bond))
        .collect()
}

/// Admit the initial learned handoff, not any external arrival through shared
/// anatomy. Both sub-carrier and whole-carrier ordering arrivals qualify.
/// Thereafter the existing individual motor in-flight law carries unfinished
/// movement; it does not demand this earlier reassembly again.
pub(super) fn frontier_founds_vocal_action_preparation(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    entry: ActiveElectricalFrontierEntry,
    reassembled_founder_bonds: &BTreeSet<StablePhysicalBondReference>,
) -> Result<Option<[u8; 16]>, FormationError> {
    if !entry.cause.is_some_and(|cause| reassembled_founder_bonds.contains(&cause.bond)) {
        return Ok(None);
    }
    frontier_reaches_vocal_action_preparation(cohorts, topology, entry)
}

/// Resolve the one learned vocal preparation reached from an exact layer-7
/// association across this physical founder bond.  This does not decide from
/// activity or formation membership; it only verifies the already-grown
/// association-to-ordering anatomy.  More than one owner is noncanonical.
pub(super) fn vocal_action_preparation_from_association_founder(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    association_lineage: [u8; 16],
    founder_bond: StablePhysicalBondReference,
) -> Result<Option<[u8; 16]>, FormationError> {
    if topology.layer_of(association_lineage) != Some(7) {
        return Ok(None);
    }
    let association_flat = topology.flat_for_lineage(association_lineage)?;
    let mut matches = Vec::new();
    for ordering_flat in topology.neighbours_by_flat[association_flat]
        .iter()
        .copied()
    {
        let ordering = topology.flat_locations[ordering_flat].2;
        let Some(preparation) = vocal_action_preparation_for_ordering(cohorts, topology, ordering)?
        else {
            continue;
        };
        if !preparation_predecessors(cohorts, topology, &preparation)?.is_empty() {
            continue;
        }
        if preparation.associations.iter().any(|association| {
            association.lineage == association_lineage && association.bond == founder_bond
        }) {
            matches.push(ordering);
        }
    }
    matches.sort_unstable();
    matches.dedup();
    match matches.as_slice() {
        [] => Ok(None),
        [ordering] => Ok(Some(*ordering)),
        _ => Err(FormationError::NeuronLineageAuthorityChanged),
    }
}

/// Resolve one exact learned ordering-to-motor branch back to its coordinated
/// vocal preparation.  The branch itself remains the physical authority: this
/// helper neither widens permission to sibling contacts nor infers an action
/// from a motor lineage alone.
pub(super) fn vocal_action_preparation_from_motor_branch(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    ordering_lineage: [u8; 16],
    motor_lineage: [u8; 16],
    motor_bond: StablePhysicalBondReference,
) -> Result<Option<VocalActionPreparation>, FormationError> {
    let Some(preparation) =
        vocal_action_preparation_for_ordering(cohorts, topology, ordering_lineage)?
    else {
        return Ok(None);
    };
    Ok(preparation
        .motors
        .iter()
        .any(|motor| motor.lineage == motor_lineage && motor.bond == motor_bond)
        .then_some(preparation))
}

pub(super) fn vocal_cognitive_action_continuation_routes_from_source(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    source_ordering_lineage: [u8; 16],
) -> Result<Vec<VocalCognitiveActionContinuationRoute>, FormationError> {
    let Some(source) =
        vocal_action_preparation_for_ordering(cohorts, topology, source_ordering_lineage)?
    else {
        return Ok(Vec::new());
    };
    let source_flat = topology.flat_for_lineage(source_ordering_lineage)?;
    let source_index = mounted_at(cohorts, topology, source_flat)?
        .place()
        .topology_index();
    let mut routes = Vec::new();
    for destination_flat in topology.neighbours_by_flat[source_flat].iter().copied() {
        let destination = topology.flat_locations[destination_flat].2;
        if topology.layer_of(destination) != Some(11)
            || mounted_at(cohorts, topology, destination_flat)?
                .place()
                .topology_index()
                <= source_index
            || vocal_action_preparation_for_ordering(cohorts, topology, destination)?.is_none()
        {
            continue;
        }
        let Some(bond) = fabric_bond_between(topology, source.ordering_lineage, destination)?
        else {
            continue;
        };
        routes.push(VocalCognitiveActionContinuationRoute {
            source_ordering_lineage,
            destination_ordering_lineage: destination,
            continuation_bond: bond,
        });
    }
    routes.sort_unstable();
    routes.dedup();
    Ok(routes)
}

pub(super) fn vocal_cognitive_action_continuation_routes_for_motor(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    motor_lineage: [u8; 16],
) -> Result<Vec<VocalCognitiveActionContinuationRoute>, FormationError> {
    let mut routes = Vec::new();
    for destination in vocal_cognitive_action_route_for_motor(cohorts, topology, motor_lineage)? {
        let destination_flat =
            topology.flat_for_lineage(destination.preparation.ordering_lineage)?;
        let destination_index = mounted_at(cohorts, topology, destination_flat)?
            .place()
            .topology_index();
        for source_flat in topology.neighbours_by_flat[destination_flat]
            .iter()
            .copied()
        {
            let source = topology.flat_locations[source_flat].2;
            if topology.layer_of(source) != Some(11)
                || mounted_at(cohorts, topology, source_flat)?
                    .place()
                    .topology_index()
                    >= destination_index
                || vocal_action_preparation_for_ordering(cohorts, topology, source)?.is_none()
            {
                continue;
            }
            let Some(bond) =
                fabric_bond_between(topology, source, destination.preparation.ordering_lineage)?
            else {
                continue;
            };
            routes.push(VocalCognitiveActionContinuationRoute {
                source_ordering_lineage: source,
                destination_ordering_lineage: destination.preparation.ordering_lineage,
                continuation_bond: bond,
            });
        }
    }
    routes.sort_unstable();
    routes.dedup();
    Ok(routes)
}

pub(super) fn frontier_carries_vocal_action_continuation(
    predecessor_frontier: &[ActiveElectricalFrontierEntry],
    continuation: &VocalCognitiveActionContinuationRoute,
) -> bool {
    predecessor_frontier.iter().copied().any(|entry| {
        if entry.frontier_lineage() != continuation.destination_ordering_lineage
            || entry.carries_body_owned_acoustic_efference()
        {
            return false;
        }
        entry.directed_transfer().is_some_and(|transfer| {
            transfer.sender == continuation.source_ordering_lineage
                && transfer.receiver == continuation.destination_ordering_lineage
                && transfer.bond == continuation.continuation_bond
        })
    })
}

fn append_contact_once(
    electrical_fabric: &ResidentElectricalFabric,
    additions: &mut Vec<([u8; 16], [u8; 16], ExactRational)>,
    left: [u8; 16],
    right: [u8; 16],
) {
    if !electrical_fabric.contains_contact(left, right)
        && !additions
            .iter()
            .any(|(candidate_left, candidate_right, _)| {
                canonical_lineage_pair(*candidate_left, *candidate_right)
                    == canonical_lineage_pair(left, right)
            })
    {
        additions.push((
            left,
            right,
            ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
        ));
    }
}

fn existing_preparation(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    associations: &[[u8; 16]],
    motors: &[[u8; 16]],
    predecessors: &[[u8; 16]],
) -> Result<Option<[u8; 16]>, FormationError> {
    let Some(first_association) = associations.first().copied() else {
        return Ok(None);
    };
    let first_flat = topology.flat_for_lineage(first_association)?;
    let expected_associations = associations.iter().copied().collect::<BTreeSet<_>>();
    let expected_motors = motors.iter().copied().collect::<BTreeSet<_>>();
    let expected_predecessors = predecessors.iter().copied().collect::<Vec<_>>();
    let mut matches = Vec::new();
    for flat in topology.neighbours_by_flat[first_flat].iter().copied() {
        let ordering = topology.flat_locations[flat].2;
        let Some(preparation) = vocal_action_preparation_for_ordering(cohorts, topology, ordering)?
        else {
            continue;
        };
        if preparation
            .associations
            .iter()
            .map(|contact| contact.lineage)
            .collect::<BTreeSet<_>>()
            == expected_associations
            && preparation
                .motors
                .iter()
                .map(|contact| contact.lineage)
                .collect::<BTreeSet<_>>()
                == expected_motors
            && preparation_predecessors(cohorts, topology, &preparation)? == expected_predecessors
        {
            matches.push(ordering);
        }
    }
    matches.sort_unstable();
    matches.dedup();
    match matches.as_slice() {
        [] => Ok(None),
        [ordering] => Ok(Some(*ordering)),
        _ => Err(FormationError::NeuronLineageAuthorityChanged),
    }
}

fn preparation_with_exact_participants_exists(
    cohorts: &[ResidentReachedCohort],
    topology: &ResidentTopologyIndex,
    associations: &[[u8; 16]],
    motors: &[[u8; 16]],
    predecessors: &[[u8; 16]],
) -> Result<bool, FormationError> {
    let Some(first_association) = associations.first().copied() else {
        return Ok(false);
    };
    let expected_associations = associations.iter().copied().collect::<BTreeSet<_>>();
    let expected_motors = motors.iter().copied().collect::<BTreeSet<_>>();
    let expected_predecessors = predecessors.iter().copied().collect::<BTreeSet<_>>();
    let first_flat = topology.flat_for_lineage(first_association)?;
    for flat in topology.neighbours_by_flat[first_flat].iter().copied() {
        let ordering = topology.flat_locations[flat].2;
        let Some(preparation) = vocal_action_preparation_for_ordering(cohorts, topology, ordering)?
        else {
            continue;
        };
        if preparation
            .associations
            .iter()
            .map(|contact| contact.lineage)
            .collect::<BTreeSet<_>>()
            == expected_associations
            && preparation
                .motors
                .iter()
                .map(|contact| contact.lineage)
                .collect::<BTreeSet<_>>()
                == expected_motors
            && preparation_predecessors(cohorts, topology, &preparation)?
                .into_iter()
                .collect::<BTreeSet<_>>()
                == expected_predecessors
        {
            return Ok(true);
        }
    }
    Ok(false)
}

pub(super) fn mount_exact_reassembled_vocal_action_routes(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    electrical_fabric: &mut ResidentElectricalFabric,
    topology: &ResidentTopologyIndex,
    associations: &ReachedAssociationsByOccurrence,
    moved_regulations: &[Vec<[u8; 16]>],
    exact_sound_reassembled_members: &BTreeSet<[u8; 16]>,
    source_occurrence_spans: &[(usize, usize)],
    enacted_predecessor_orderings: &[[u8; 16]],
) -> Result<(), FormationError> {
    if associations.lineages.len() != moved_regulations.len() {
        return Err(FormationError::NoncanonicalState);
    }
    let mut expected_start = 0usize;
    for (start, end) in source_occurrence_spans.iter().copied() {
        if start != expected_start || end <= start || end > associations.lineages.len() {
            return Err(FormationError::NoncanonicalState);
        }
        expected_start = end;
    }
    if expected_start != associations.lineages.len() {
        return Err(FormationError::NoncanonicalState);
    }

    let mut predecessor_orderings = enacted_predecessor_orderings.to_vec();
    predecessor_orderings.sort_unstable();
    predecessor_orderings.dedup();
    for ordering in predecessor_orderings.iter().copied() {
        if vocal_action_preparation_for_ordering(cohorts, topology, ordering)?.is_none() {
            return Err(FormationError::NeuronLineageAuthorityChanged);
        }
    }
    let predecessor_motor_lineages = predecessor_orderings
        .iter()
        .copied()
        .map(|ordering| {
            let preparation = vocal_action_preparation_for_ordering(cohorts, topology, ordering)?
                .ok_or(FormationError::NeuronLineageAuthorityChanged)?;
            Ok(preparation
                .motors
                .into_iter()
                .map(|motor| motor.lineage)
                .collect::<BTreeSet<_>>())
        })
        .collect::<Result<Vec<_>, FormationError>>()?;

    let mut additions = Vec::<([u8; 16], [u8; 16], ExactRational)>::new();
    let mut planned_preparations =
        BTreeMap::<(Vec<[u8; 16]>, Vec<[u8; 16]>, Vec<[u8; 16]>), [u8; 16]>::new();
    let exact_predecessors = predecessor_orderings.clone();
    let mut grouped_associations =
        BTreeMap::<(Vec<[u8; 16]>, Vec<[u8; 16]>), Vec<(Vec<[u8; 16]>, bool)>>::new();
    for (start, end) in source_occurrence_spans.iter().copied() {
        let mut pairs = Vec::<([u8; 16], [u8; 16])>::new();
        let mut incomplete_vocal_occurrence = false;
        for occurrence in start..end {
            let mut motors = moved_regulations[occurrence]
                .iter()
                .copied()
                .map(|regulation| exact_vocal_motor_for_regulation(cohorts, topology, regulation))
                .collect::<Result<Vec<_>, _>>()?
                .into_iter()
                .flatten()
                .collect::<Vec<_>>();
            motors.sort_unstable();
            motors.dedup();
            if motors.is_empty() {
                continue;
            }
            let occurrence_associations = &associations.lineages[occurrence];
            if occurrence_associations.len() != 1 || motors.len() != 1 {
                incomplete_vocal_occurrence = true;
                break;
            }
            pairs.push((occurrence_associations[0], motors[0]));
        }
        pairs.sort_unstable();
        pairs.dedup();
        if incomplete_vocal_occurrence || pairs.len() < 2 {
            continue;
        }
        let associations_set = pairs
            .iter()
            .map(|(association, _)| *association)
            .collect::<BTreeSet<_>>();
        let motors_set = pairs
            .iter()
            .map(|(_, motor)| *motor)
            .collect::<BTreeSet<_>>();
        if associations_set.len() != pairs.len() || motors_set.len() != pairs.len() {
            return Err(FormationError::NeuronLineageAuthorityChanged);
        }
        if predecessor_motor_lineages.iter().any(|predecessor_motors| {
            motors_set
                .iter()
                .all(|motor| predecessor_motors.contains(motor))
        }) {
            // These consequences are the body's proprioceptive return from
            // the just-enacted source posture, not evidence of a following
            // posture.  Their exact motor directions are already owned by one
            // enacted predecessor preparation.  A simultaneous external
            // guide in a different posture remains eligible; an ambiguous
            // guide of the same posture is truthfully indistinguishable here
            // and therefore cannot author continuation anatomy.
            continue;
        }
        let association_lineages = associations_set.into_iter().collect::<Vec<_>>();
        let motor_lineages = motors_set.into_iter().collect::<Vec<_>>();
        if !association_lineages
            .iter()
            .any(|association| exact_sound_reassembled_members.contains(association))
        {
            // Guided motion can reveal an occurrence-local association, but
            // it cannot make that association belong to the tutor sound. A
            // later lived repetition must first reassemble retained sound
            // structure that physically owns at least one exact association
            // in this coordinated posture.
            continue;
        }
        let already_learned = preparation_with_exact_participants_exists(
            cohorts,
            topology,
            &association_lineages,
            &motor_lineages,
            &exact_predecessors,
        )?;
        grouped_associations
            .entry((motor_lineages, exact_predecessors.clone()))
            .or_default()
            .push((association_lineages, already_learned));
    }
    for ((motor_lineages, predecessors), mut association_candidates) in grouped_associations {
        association_candidates.sort_unstable();
        association_candidates.dedup();
        let novel = association_candidates
            .into_iter()
            .filter_map(|(associations, already_learned)| {
                (!already_learned).then_some(associations)
            })
            .collect::<Vec<_>>();
        let [association_lineages] = novel.as_slice() else {
            if novel.is_empty() {
                continue;
            }
            return Err(FormationError::NeuronLineageAuthorityChanged);
        };
        let key = (
            association_lineages.clone(),
            motor_lineages.clone(),
            predecessors.clone(),
        );
        let ordering = match existing_preparation(
            cohorts,
            topology,
            &association_lineages,
            &motor_lineages,
            &predecessors,
        )? {
            Some(ordering) => ordering,
            None => match planned_preparations.get(&key).copied() {
                Some(ordering) => ordering,
                None => mount_next_intrinsic_in_layer(
                    cohorts,
                    resting_population,
                    next_lineage_ordinal,
                    11,
                )?,
            },
        };
        planned_preparations.insert(key, ordering);
        for participant in predecessors
            .iter()
            .chain(association_lineages)
            .chain(&motor_lineages)
            .copied()
        {
            append_contact_once(electrical_fabric, &mut additions, ordering, participant);
        }
    }
    if !additions.is_empty() {
        *electrical_fabric = electrical_fabric
            .append_contacts(&additions)
            .map_err(FormationError::ResidentElectricalUnavailable)?;
    }
    Ok(())
}
