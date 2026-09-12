//! One physical finalization path, including contact-free recovery intervals.
//! No pumping, cognition, DSF, retained evidence log, or second settlement.
use super::{
    materialize_resident_contact_edge, terminal_retains_prepared_action_charge,
    vocal_action_preparation_for_ordering, FormationError, NeuronPhysicalState,
    PhysicalEventProgress, ReachedCohortError, ResidentContactOrigin, ResidentElectricalFabric,
    ResidentReachedCohort, ResidentTopologyIndex, TransitionNeuronPredecessor,
    WORLD_MECHANICAL_TICK_MICROSECONDS,
};
use crate::causal_event_scheduler::CausalEventResidency;
use crate::elementary_charge_membrane::{ElementaryChargeMembraneState, MembraneCapacitance};
use std::collections::{BTreeMap, BTreeSet};
use std::sync::Arc;

type EndpointHolds = BTreeMap<[u8; 16], (ElementaryChargeMembraneState, u128, u128)>;
type SelectedPredecessors = BTreeMap<usize, Vec<(usize, NeuronPhysicalState)>>;

/// Earliest physical endpoint before this interval, not the post-return
/// snapshot. Live is used only when no stage changed the endpoint.
pub(super) fn held_endpoint(
    flat: usize,
    cohorts: &[ResidentReachedCohort],
    topology_index: &ResidentTopologyIndex,
    ingress: &EndpointHolds,
    transitions: &BTreeMap<[u8; 16], TransitionNeuronPredecessor>,
    selected: &SelectedPredecessors,
) -> Result<
    (
        ElementaryChargeMembraneState,
        MembraneCapacitance,
        u128,
        u128,
    ),
    FormationError,
> {
    let (cohort_index, neuron_index, lineage) = topology_index.flat_locations[flat];
    let capacitance = cohorts[cohort_index].anatomy.neuron_anatomies()[neuron_index].capacitance();
    if let Some((membrane, intracellular, extracellular)) = ingress.get(&lineage) {
        return Ok((*membrane, capacitance, *intracellular, *extracellular));
    }
    let state = transitions
        .get(&lineage)
        .map(|value| &value.state)
        .or_else(|| {
            selected.get(&cohort_index).and_then(|values| {
                values
                    .binary_search_by_key(&neuron_index, |(index, _)| *index)
                    .ok()
                    .map(|position| &values[position].1)
            })
        })
        .unwrap_or(&cohorts[cohort_index].state.neurons()[neuron_index]);
    Ok((
        state.membrane_state(),
        capacitance,
        state.carrier_reservoirs().intracellular(),
        state.carrier_reservoirs().extracellular(),
    ))
}

#[allow(clippy::too_many_arguments)]
pub(super) fn finalize_physical_events(
    cohorts: &mut [ResidentReachedCohort],
    electrical_fabric: &mut ResidentElectricalFabric,
    topology_index: &Arc<ResidentTopologyIndex>,
    events: &mut CausalEventResidency,
    physical_progress: &mut PhysicalEventProgress,
    selected: &[usize],
    selected_predecessor_neurons: &SelectedPredecessors,
    compact_original_indices: &[usize],
    due_return_flats: &[usize],
    passive_return_changed_flats: &[usize],
    co_recruited_articulatory_flats: &[usize],
    pre_source_membranes: &EndpointHolds,
    transition_predecessors: &BTreeMap<[u8; 16], TransitionNeuronPredecessor>,
    needs_rebuild: bool,
) -> Result<(), FormationError> {
    let clock = physical_progress.clock;
    let interval_microseconds = WORLD_MECHANICAL_TICK_MICROSECONDS;
    let flat_locations = topology_index.flat_locations.as_ref();
    let interval =
        u32::try_from(interval_microseconds).map_err(|_| FormationError::ArithmeticOverflow)?;
    // One endpoint read per reached neuron, not per contact: the
    // applied post-settlement material of every selected flat, once.
    // Alongside it, the wake law's exact changed-endpoint set: every
    // selected neuron whose physical state this interval actually
    // changed — by pumping, passive recovery, membrane settlement,
    // external ingress, or contact transfer. An unchanged endpoint
    // wakes nothing.
    let mut endpoint_cache = BTreeMap::new();
    for flat in selected.iter().copied() {
        let (cohort_index, neuron_index, _) = flat_locations[flat];
        let state = &cohorts[cohort_index].state.neurons()[neuron_index];
        let capacitance =
            cohorts[cohort_index].anatomy.neuron_anatomies()[neuron_index].capacitance();
        let membrane = state.membrane_state();
        endpoint_cache.insert(
            flat,
            (
                membrane
                    .potential_millivolts(capacitance)
                    .map_err(FormationError::InternalMembraneUnavailable)?,
                membrane.separated_elementary_charges(),
                capacitance,
                state.carrier_reservoirs().intracellular(),
            ),
        );
    }
    // The wake law's changed-endpoint set is UNIVERSAL: every neuron
    // whose state at this interval's end differs from the entry view —
    // external ingress (a silent zero-work settlement included),
    // pumping, passive recovery, membrane settlement, or contact
    // transfer. A receptor changed by silence is still a changed
    // endpoint, even though silence originates no causal frontier.
    let mut change_candidates = selected.iter().copied().collect::<BTreeSet<_>>();
    for lineage in pre_source_membranes.keys().copied() {
        change_candidates.insert(topology_index.flat_for_lineage(lineage)?);
    }
    for lineage in transition_predecessors.keys().copied() {
        change_candidates.insert(topology_index.flat_for_lineage(lineage)?);
    }
    change_candidates.extend(passive_return_changed_flats.iter().copied());
    change_candidates.extend(co_recruited_articulatory_flats.iter().copied());
    let mut changed_flats = Vec::new();
    for flat in change_candidates {
        let (cohort_index, neuron_index, lineage) = flat_locations[flat];
        let state = &cohorts[cohort_index].state.neurons()[neuron_index];
        let source_changed = pre_source_membranes
            .get(&lineage)
            .map(|(held_membrane, held_intracellular, held_extracellular)| {
                *held_membrane != state.membrane_state()
                    || *held_intracellular != state.carrier_reservoirs().intracellular()
                    || *held_extracellular != state.carrier_reservoirs().extracellular()
            })
            .unwrap_or(false);
        let transitioned = transition_predecessors
            .get(&lineage)
            .is_some_and(|predecessor| predecessor.state != *state);
        let selected_changed = selected_predecessor_neurons
            .get(&cohort_index)
            .and_then(|predecessors| {
                predecessors
                    .binary_search_by_key(&neuron_index, |(candidate, _)| *candidate)
                    .ok()
                    .map(|position| &predecessors[position])
            })
            .is_some_and(|(_, predecessor)| predecessor != state);
        let passive_return_changed = passive_return_changed_flats.binary_search(&flat).is_ok();
        let articulatory_changed = co_recruited_articulatory_flats.contains(&flat);
        if source_changed
            || transitioned
            || selected_changed
            || passive_return_changed
            || articulatory_changed
        {
            changed_flats.push(flat);
        }
    }
    for contact_index in compact_original_indices.iter().copied() {
        physical_progress
            .set_contact_clock(topology_index.contacts[contact_index].stable_bond, clock)?;
        let edge = materialize_resident_contact_edge(
            topology_index.contacts[contact_index],
            cohorts,
            electrical_fabric,
        )?;
        let successor_state = &edge.state;
        let (left_flat, right_flat) = (edge.left, edge.right);
        let (left_potential, left_charges, left_capacitance, left_available) = endpoint_cache
            .get(&left_flat)
            .ok_or(FormationError::NoncanonicalState)?;
        let (right_potential, right_charges, right_capacitance, right_available) = endpoint_cache
            .get(&right_flat)
            .ok_or(FormationError::NoncanonicalState)?;
        // One physical current authority in warm, cold and endpoint-wake paths.
        // Prior activity cannot grant a different schedule after restart.
        let standing = crate::sparse_electrical_contact::standing_contact_current(
            edge.anatomy,
            successor_state,
            *left_potential,
            *left_charges,
            *left_capacitance,
            *left_available,
            *right_potential,
            *right_charges,
            *right_capacitance,
            *right_available,
        )
        .map_err(FormationError::ResidentElectricalUnavailable)?;
        let due = match standing {
            Some(current) => crate::elementary_charge_transfer::next_whole_carrier_crossing_clocks(
                successor_state.carrier_phase(),
                current,
                interval,
            )
            .map_err(|_| FormationError::ArithmeticOverflow)?
            .map(|clocks_until| {
                clock
                    .checked_add(clocks_until)
                    .ok_or(FormationError::ArithmeticOverflow)
            })
            .transpose()?,
            None => None,
        };
        events
            .contact_schedule
            .reschedule_from_clock(clock, contact_index, due);
    }
    // The wake law: a changed endpoint wakes EVERY contact incident to
    // it, now — adding it to a later frontier is insufficient. A
    // sleeping incident contact first catches up exactly through the
    // pre-change span (its drive was frozen at the pre-pump
    // predecessor values this interval still holds), then reschedules
    // from its caught-up phase under the settlement authority against
    // the changed successor endpoints.
    let mut woken_contacts = Vec::new();
    for flat in changed_flats.iter().copied() {
        woken_contacts.extend(
            topology_index
                .incident_contacts_by_flat
                .get(flat)
                .ok_or(FormationError::NeuronLineageAuthorityAbsent)?
                .iter()
                .copied(),
        );
    }
    woken_contacts.sort_unstable();
    woken_contacts.dedup();
    for contact_index in woken_contacts {
        if compact_original_indices
            .binary_search(&contact_index)
            .is_ok()
        {
            continue;
        }
        let entry = topology_index.contacts[contact_index];
        let edge = materialize_resident_contact_edge(entry, cohorts, electrical_fabric)?;
        let mut sleeping_state = edge.state;
        let last = physical_progress.contact_clock(edge.stable_bond)?;
        // The endpoint's change reaches this sleeping neighbour at the
        // NEXT clock (the one-clock arrival law), so the sleeping span
        // integrates THROUGH this clock at the held pre-change drive;
        // the new drive counts from here.
        let span_end = clock;
        if last < span_end {
            // Pre-change drive: each endpoint as it stood before this
            // interval — the predecessor clone when the endpoint was
            // selected, its untouched live state otherwise.
            let (left_membrane, left_capacitance, left_available, _) = held_endpoint(
                edge.left,
                cohorts,
                topology_index,
                pre_source_membranes,
                transition_predecessors,
                selected_predecessor_neurons,
            )?;
            let (right_membrane, right_capacitance, right_available, _) = held_endpoint(
                edge.right,
                cohorts,
                topology_index,
                pre_source_membranes,
                transition_predecessors,
                selected_predecessor_neurons,
            )?;
            let left_potential = left_membrane
                .potential_millivolts(left_capacitance)
                .map_err(FormationError::InternalMembraneUnavailable)?;
            let right_potential = right_membrane
                .potential_millivolts(right_capacitance)
                .map_err(FormationError::InternalMembraneUnavailable)?;
            let standing = crate::sparse_electrical_contact::standing_contact_current(
                edge.anatomy,
                &sleeping_state,
                left_potential,
                left_membrane.separated_elementary_charges(),
                left_capacitance,
                left_available,
                right_potential,
                right_membrane.separated_elementary_charges(),
                right_capacitance,
                right_available,
            )
            .map_err(FormationError::ResidentElectricalUnavailable)?;
            if let Some(standing_current) = standing {
                let potential_difference = left_potential
                    .checked_sub(right_potential)
                    .map_err(|_| FormationError::ArithmeticOverflow)?;
                let caught = crate::causal_event_scheduler::catch_up_sleeping_contact(
                    crate::causal_event_scheduler::ContactIntegrationClock {
                        last_integrated_clock: last,
                    },
                    span_end,
                    sleeping_state.carrier_phase(),
                    sleeping_state.transition_work_phase(),
                    standing_current,
                    potential_difference,
                    interval,
                )
                .map_err(|_| FormationError::ArithmeticOverflow)?;
                assert_eq!(
                    caught.outward_elementary_charges,
                    0,
                    "a sleeping span crossed a whole carrier without its \
                     scheduled wake — the causal event schedule is unsound; \
                     contact={contact_index} last={last} span_end={span_end} \
                     clock={clock} rebuilt={needs_rebuild} \
                     endpoints=({}, {}) predecessor_phase={:?} current={:?} \
                     left_charges={} right_charges={} left_available={} \
                     right_available={}",
                    edge.left,
                    edge.right,
                    sleeping_state.carrier_phase().parts(),
                    standing_current.parts(),
                    left_membrane.separated_elementary_charges(),
                    right_membrane.separated_elementary_charges(),
                    left_available,
                    right_available,
                );
                sleeping_state =
                    sleeping_state.with_caught_up_carrier_phase(caught.successor_phase);
                match edge.origin {
                    ResidentContactOrigin::Fabric { contact_index } => {
                        electrical_fabric
                            .replace_contact_states(vec![(contact_index, sleeping_state.clone())])
                            .map_err(FormationError::ResidentElectricalUnavailable)?;
                    }
                    ResidentContactOrigin::Local {
                        cohort_index,
                        contact_index,
                        ..
                    } => {
                        Arc::make_mut(&mut cohorts[cohort_index].state)
                            .replace_electrical_contact_state(contact_index, sleeping_state.clone())
                            .map_err(FormationError::ResidentElectricalUnavailable)?;
                    }
                }
            }
        }
        physical_progress.set_contact_clock(edge.stable_bond, span_end)?;
        // New drive from the changed successor endpoints, full authority.
        let successor_endpoint = |flat: usize| -> Result<
            (
                crate::exact_rational::ExactRational,
                i128,
                crate::elementary_charge_membrane::MembraneCapacitance,
                u128,
            ),
            FormationError,
        > {
            if let Some(cached) = endpoint_cache.get(&flat) {
                return Ok(cached.clone());
            }
            let (cohort_index, neuron_index, _) = flat_locations[flat];
            let state = &cohorts[cohort_index].state.neurons()[neuron_index];
            let capacitance =
                cohorts[cohort_index].anatomy.neuron_anatomies()[neuron_index].capacitance();
            let membrane = state.membrane_state();
            Ok((
                membrane
                    .potential_millivolts(capacitance)
                    .map_err(FormationError::InternalMembraneUnavailable)?,
                membrane.separated_elementary_charges(),
                capacitance,
                state.carrier_reservoirs().intracellular(),
            ))
        };
        let (left_potential, left_charges, left_capacitance, left_available) =
            successor_endpoint(edge.left)?;
        let (right_potential, right_charges, right_capacitance, right_available) =
            successor_endpoint(edge.right)?;
        let standing = crate::sparse_electrical_contact::standing_contact_current(
            edge.anatomy,
            &sleeping_state,
            left_potential,
            left_charges,
            left_capacitance,
            left_available,
            right_potential,
            right_charges,
            right_capacitance,
            right_available,
        )
        .map_err(FormationError::ResidentElectricalUnavailable)?;
        let due = match standing {
            Some(current) => crate::elementary_charge_transfer::next_whole_carrier_crossing_clocks(
                sleeping_state.carrier_phase(),
                current,
                interval,
            )
            .map_err(|_| FormationError::ArithmeticOverflow)?
            .map(|clocks_until| {
                clock
                    .checked_add(clocks_until)
                    .ok_or(FormationError::ArithmeticOverflow)
            })
            .transpose()?,
            None => None,
        };
        events
            .contact_schedule
            .reschedule_from_clock(clock, contact_index, due);
    }
    let mut recovery_flats = changed_flats;
    recovery_flats.extend(due_return_flats.iter().copied());
    recovery_flats.sort_unstable();
    recovery_flats.dedup();
    for flat in recovery_flats {
        let (cohort_index, neuron_index, lineage) = flat_locations[flat];
        // The neuron's displacement changed this clock, so its return
        // rate changed. Catch its return phase up through this clock
        // at the HELD pre-change rate first — the change reaches this
        // separate path at the next clock — then reschedule under the
        // new rate. A crossing inside the caught-up span cannot occur:
        // its due would have fired.
        let last = physical_progress.recovery(lineage)?.last;
        let scheduled_return_due = events.recovery_schedule.due_clock(flat);
        if last < clock {
            // An unscheduled return means the descent law refused its
            // current for the whole span: zero flow, frozen phase.
            // Only a scheduled span integrates, at the exact held
            // state's current — membrane and compartments together.
            if scheduled_return_due.is_none() {
                physical_progress.set_recovery_clock(lineage, clock)?;
            } else {
                let (held_membrane, _, held_intracellular, held_extracellular) = held_endpoint(
                    flat,
                    cohorts,
                    topology_index,
                    pre_source_membranes,
                    transition_predecessors,
                    selected_predecessor_neurons,
                )?;
                let held_state = crate::complete_neuron::with_held_membrane_and_carriers(
                    &cohorts[cohort_index].state.neurons()[neuron_index],
                    held_membrane,
                    held_intracellular,
                    held_extracellular,
                );
                let held_current = crate::complete_neuron::passive_membrane_return_current(
                    &cohorts[cohort_index].anatomy.neuron_anatomies()[neuron_index],
                    &held_state,
                )
                .map_err(|error| {
                    FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                        neuron_index,
                        error,
                    })
                })?;
                if let Some(current) = held_current {
                    let caught =
                        crate::elementary_charge_transfer::settle_elementary_charge_transfer_clocks(
                            physical_progress.recovery(lineage)?.phase,
                            current,
                            interval,
                            clock - last,
                        )
                        .map_err(|_| FormationError::ArithmeticOverflow)?;
                    assert_eq!(
                        caught.outward_elementary_charges,
                        0,
                        "a sleeping membrane return crossed without its \
                         scheduled event — the return schedule is unsound; \
                         flat={flat} lineage={lineage:?} last={last} \
                         clock={clock} due={scheduled_return_due:?} \
                         phase={:?} current={:?} held_charges={} \
                         held_intracellular={} held_extracellular={}",
                        physical_progress.recovery(lineage)?.phase.parts(),
                        current.parts(),
                        held_membrane.separated_elementary_charges(),
                        held_intracellular,
                        held_extracellular,
                    );
                    physical_progress.set_recovery_phase(lineage, caught.successor_phase)?;
                }
            }
            physical_progress.set_recovery_clock(lineage, clock)?;
        }
        let mount = &cohorts[cohort_index].anatomy.mounts()[neuron_index];
        let neuron = &cohorts[cohort_index].state.neurons()[neuron_index];
        let coordinated_vocal_preparation = mount.place().layer() == 11
            && vocal_action_preparation_for_ordering(cohorts, topology_index, lineage)?.is_some();
        let mounted_terminal_ready =
            terminal_retains_prepared_action_charge(mount, neuron, coordinated_vocal_preparation);
        let due = if mounted_terminal_ready {
            Some(
                clock
                    .checked_add(1)
                    .ok_or(FormationError::ArithmeticOverflow)?,
            )
        } else {
            crate::complete_neuron::next_passive_membrane_return_crossing_clocks(
                &cohorts[cohort_index].anatomy.neuron_anatomies()[neuron_index],
                neuron,
                physical_progress.recovery(lineage)?.phase,
                interval,
            )
            .map_err(|error| {
                FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                    neuron_index,
                    error,
                })
            })?
            .map(|clocks_until| {
                clock
                    .checked_add(clocks_until)
                    .ok_or(FormationError::ArithmeticOverflow)
            })
            .transpose()?
        };
        events
            .recovery_schedule
            .reschedule_from_clock(clock, flat, due);
    }
    Ok(())
}
