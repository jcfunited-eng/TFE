//! Sparse exact electrical contact physics for reached neurons.
//!
//! Every contact reads one synchronous predecessor membrane generation,
//! computes `I = g(V_left - V_right)`, transfers one shared exact carrier
//! count from left to right, and applies equal-and-opposite membrane charge.
//! Contact state retains only the proper unresolved carrier phase.  Work and
//! current-state residency are linear in the reached neurons and contacts and
//! do not grow with organism age.
//!
//! This module contains no dense topology, neuron polling, owner, lock,
//! database, score, semantic label, receipt, or history log.

use crate::elementary_charge_membrane::{
    settle_membrane_elementary_charges, ElementaryChargeMembraneState, MembraneCapacitance,
    MembraneChargeError,
};
use crate::elementary_charge_transfer::{
    settle_elementary_charge_transfer, ChargeCarrierPhase, ChargeTransferError,
};
use crate::exact_rational::{ExactRational, ExactRationalError};

const PICOSIEMENS_MILLIVOLTS_PER_PICOAMPERE: u128 = 1_000;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum SparseElectricalError {
    InvalidEndpoint,
    IncompleteReachedFrontier,
    NonPositiveConductance,
    AnatomyStateWidth,
    InvalidEncoding,
    ArithmeticWidth,
    Rational(ExactRationalError),
    ChargeTransfer(ChargeTransferError),
    Membrane(MembraneChargeError),
}

impl From<ExactRationalError> for SparseElectricalError {
    fn from(value: ExactRationalError) -> Self {
        Self::Rational(value)
    }
}

impl From<ChargeTransferError> for SparseElectricalError {
    fn from(value: ChargeTransferError) -> Self {
        Self::ChargeTransfer(value)
    }
}

impl From<MembraneChargeError> for SparseElectricalError {
    fn from(value: MembraneChargeError) -> Self {
        Self::Membrane(value)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ElectricalContactAnatomy {
    left_neuron: usize,
    right_neuron: usize,
    conductance_picosiemens: ExactRational,
}

impl ElectricalContactAnatomy {
    pub(crate) fn new(
        left_neuron: usize,
        right_neuron: usize,
        conductance_picosiemens: ExactRational,
        neuron_count: usize,
    ) -> Result<Self, SparseElectricalError> {
        if left_neuron >= neuron_count
            || right_neuron >= neuron_count
            || left_neuron == right_neuron
        {
            return Err(SparseElectricalError::InvalidEndpoint);
        }
        if conductance_picosiemens.parts().0 <= 0 {
            return Err(SparseElectricalError::NonPositiveConductance);
        }
        Ok(Self {
            left_neuron,
            right_neuron,
            conductance_picosiemens,
        })
    }

    pub(crate) fn endpoints(self) -> (usize, usize) {
        (self.left_neuron, self.right_neuron)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ElectricalContactState {
    carrier_phase: ChargeCarrierPhase,
}

impl ElectricalContactState {
    pub(crate) fn genesis() -> Self {
        Self {
            carrier_phase: ChargeCarrierPhase::zero(),
        }
    }

    pub(crate) fn from_carrier_phase(carrier_phase: ChargeCarrierPhase) -> Self {
        Self { carrier_phase }
    }

    pub(crate) fn carrier_phase(self) -> ChargeCarrierPhase {
        self.carrier_phase
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ElectricalContactTransition {
    pub(crate) successor: ElectricalContactState,
    pub(crate) outward_current_from_left_picoamperes: ExactRational,
    pub(crate) outward_elementary_charges_from_left: i128,
}

fn settle_contact(
    anatomy: ElectricalContactAnatomy,
    predecessor: ElectricalContactState,
    left_potential_millivolts: ExactRational,
    right_potential_millivolts: ExactRational,
    interval_microseconds: u32,
) -> Result<ElectricalContactTransition, SparseElectricalError> {
    let potential_difference = left_potential_millivolts.checked_sub(right_potential_millivolts)?;
    let current = anatomy
        .conductance_picosiemens
        .checked_mul(potential_difference)?
        .checked_div_unsigned(PICOSIEMENS_MILLIVOLTS_PER_PICOAMPERE)?;
    let carrier = settle_elementary_charge_transfer(
        predecessor.carrier_phase,
        current,
        interval_microseconds,
    )?;
    Ok(ElectricalContactTransition {
        successor: ElectricalContactState {
            carrier_phase: carrier.successor_phase,
        },
        outward_current_from_left_picoamperes: current,
        outward_elementary_charges_from_left: carrier.outward_elementary_charges,
    })
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SparseElectricalAnatomy {
    neuron_count: usize,
    contacts: Box<[ElectricalContactAnatomy]>,
}

impl SparseElectricalAnatomy {
    pub(crate) fn new(
        neuron_count: usize,
        contacts: Vec<ElectricalContactAnatomy>,
    ) -> Result<Self, SparseElectricalError> {
        if neuron_count == 0
            || contacts.iter().any(|contact| {
                contact.left_neuron >= neuron_count
                    || contact.right_neuron >= neuron_count
                    || contact.left_neuron == contact.right_neuron
            })
        {
            return Err(SparseElectricalError::InvalidEndpoint);
        }
        Ok(Self {
            neuron_count,
            contacts: contacts.into_boxed_slice(),
        })
    }

    pub(crate) fn neuron_count(&self) -> usize {
        self.neuron_count
    }

    pub(crate) fn contact_count(&self) -> usize {
        self.contacts.len()
    }

    pub(crate) fn contact_endpoints(&self) -> impl ExactSizeIterator<Item = (usize, usize)> + '_ {
        self.contacts.iter().map(|contact| contact.endpoints())
    }

    pub(crate) fn extend_neuron_count(
        &self,
        neuron_count: usize,
    ) -> Result<Self, SparseElectricalError> {
        if neuron_count < self.neuron_count {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        Self::new(neuron_count, self.contacts.to_vec())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SparseElectricalState {
    contacts: Box<[ElectricalContactState]>,
}

impl SparseElectricalState {
    pub(crate) fn genesis(anatomy: &SparseElectricalAnatomy) -> Self {
        Self {
            contacts: vec![ElectricalContactState::genesis(); anatomy.contacts.len()]
                .into_boxed_slice(),
        }
    }

    pub(crate) fn contact_count(&self) -> usize {
        self.contacts.len()
    }

    pub(crate) fn resident_contact_bytes(&self) -> Option<usize> {
        self.contacts
            .len()
            .checked_mul(core::mem::size_of::<ElectricalContactState>())
    }

    pub(crate) fn contact_states(&self) -> &[ElectricalContactState] {
        &self.contacts
    }

    pub(crate) fn from_contact_states(
        anatomy: &SparseElectricalAnatomy,
        contacts: Vec<ElectricalContactState>,
    ) -> Result<Self, SparseElectricalError> {
        if contacts.len() != anatomy.contacts.len() {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        Ok(Self {
            contacts: contacts.into_boxed_slice(),
        })
    }
}

const SPARSE_ELECTRICAL_CELL_CODEC_MAGIC: &[u8; 8] = b"GLSEC01\0";
const SPARSE_ELECTRICAL_CELL_CONTACT_BYTES: usize = 80;

/// Keep fixed sparse-contact anatomy and its unresolved carrier phase together
/// across cold restart. The encoding chooses no contacts or conductances.
pub(crate) fn encode_sparse_electrical_cell(
    anatomy: &SparseElectricalAnatomy,
    state: &SparseElectricalState,
) -> Result<Vec<u8>, SparseElectricalError> {
    if anatomy.contacts.len() != state.contacts.len() {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(SPARSE_ELECTRICAL_CELL_CODEC_MAGIC);
    push_electrical_usize(&mut encoded, anatomy.neuron_count)?;
    push_electrical_usize(&mut encoded, anatomy.contacts.len())?;
    for (contact, contact_state) in anatomy.contacts.iter().zip(state.contacts.iter()) {
        push_electrical_usize(&mut encoded, contact.left_neuron)?;
        push_electrical_usize(&mut encoded, contact.right_neuron)?;
        let (conductance_numerator, conductance_denominator) =
            contact.conductance_picosiemens.parts();
        encoded.extend_from_slice(&conductance_numerator.to_le_bytes());
        encoded.extend_from_slice(&conductance_denominator.to_le_bytes());
        let (phase_numerator, phase_denominator) = contact_state.carrier_phase.parts();
        encoded.extend_from_slice(&phase_numerator.to_le_bytes());
        encoded.extend_from_slice(&phase_denominator.to_le_bytes());
    }
    Ok(encoded)
}

pub(crate) fn decode_sparse_electrical_cell(
    encoded: &[u8],
) -> Result<(SparseElectricalAnatomy, SparseElectricalState), SparseElectricalError> {
    let mut reader = SparseElectricalCellReader::new(encoded);
    if reader.take(SPARSE_ELECTRICAL_CELL_CODEC_MAGIC.len())? != SPARSE_ELECTRICAL_CELL_CODEC_MAGIC
    {
        return Err(SparseElectricalError::InvalidEncoding);
    }
    let neuron_count = reader.usize()?;
    let contact_count = reader.usize()?;
    reader.require_records(contact_count, SPARSE_ELECTRICAL_CELL_CONTACT_BYTES)?;
    let mut contacts = Vec::new();
    let mut states = Vec::new();
    contacts
        .try_reserve_exact(contact_count)
        .map_err(|_| SparseElectricalError::ArithmeticWidth)?;
    states
        .try_reserve_exact(contact_count)
        .map_err(|_| SparseElectricalError::ArithmeticWidth)?;
    for _ in 0..contact_count {
        contacts.push(ElectricalContactAnatomy::new(
            reader.usize()?,
            reader.usize()?,
            ExactRational::new(reader.i128()?, reader.u128()?)?,
            neuron_count,
        )?);
        states.push(ElectricalContactState::from_carrier_phase(
            ChargeCarrierPhase::new(reader.i128()?, reader.u128()?)?,
        ));
    }
    if !reader.finished() {
        return Err(SparseElectricalError::InvalidEncoding);
    }
    let anatomy = SparseElectricalAnatomy::new(neuron_count, contacts)?;
    let state = SparseElectricalState::from_contact_states(&anatomy, states)?;
    Ok((anatomy, state))
}

fn push_electrical_usize(encoded: &mut Vec<u8>, value: usize) -> Result<(), SparseElectricalError> {
    encoded.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| SparseElectricalError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

struct SparseElectricalCellReader<'a> {
    encoded: &'a [u8],
    cursor: usize,
}

impl<'a> SparseElectricalCellReader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self { encoded, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], SparseElectricalError> {
        let end = self
            .cursor
            .checked_add(count)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        let value = self
            .encoded
            .get(self.cursor..end)
            .ok_or(SparseElectricalError::InvalidEncoding)?;
        self.cursor = end;
        Ok(value)
    }

    fn require_records(
        &self,
        count: usize,
        record_bytes: usize,
    ) -> Result<(), SparseElectricalError> {
        let required = count
            .checked_mul(record_bytes)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        let remaining = self
            .encoded
            .len()
            .checked_sub(self.cursor)
            .ok_or(SparseElectricalError::InvalidEncoding)?;
        if required > remaining {
            return Err(SparseElectricalError::InvalidEncoding);
        }
        Ok(())
    }

    fn usize(&mut self) -> Result<usize, SparseElectricalError> {
        usize::try_from(u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| SparseElectricalError::InvalidEncoding)?,
        ))
        .map_err(|_| SparseElectricalError::ArithmeticWidth)
    }

    fn i128(&mut self) -> Result<i128, SparseElectricalError> {
        Ok(i128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| SparseElectricalError::InvalidEncoding)?,
        ))
    }

    fn u128(&mut self) -> Result<u128, SparseElectricalError> {
        Ok(u128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| SparseElectricalError::InvalidEncoding)?,
        ))
    }

    fn finished(&self) -> bool {
        self.cursor == self.encoded.len()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SparseElectricalSettlement {
    pub(crate) successor_membranes: Box<[ElementaryChargeMembraneState]>,
    pub(crate) successor_contacts: SparseElectricalState,
    pub(crate) transitions: Box<[ElectricalContactTransition]>,
    pub(crate) outward_elementary_charges_by_neuron: Box<[i128]>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SparseElectricalTransferSettlement {
    pub(crate) successor_contacts: SparseElectricalState,
    pub(crate) transitions: Box<[ElectricalContactTransition]>,
    pub(crate) outward_elementary_charges_by_neuron: Box<[i128]>,
}

/// Settle sparse contact currents and their shared carrier phases from one
/// predecessor generation. The returned equal-and-opposite carrier counts are
/// not applied here; a reached neuron cohort must combine them atomically with
/// each neuron's same-interval local membrane and material consequences.
pub(crate) fn settle_sparse_electrical_transfers(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    interval_microseconds: u32,
) -> Result<SparseElectricalTransferSettlement, SparseElectricalError> {
    if predecessor_contacts.contacts.len() != anatomy.contacts.len()
        || capacitances.len() != anatomy.neuron_count
        || predecessor_membranes.len() != anatomy.neuron_count
    {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }

    let potentials = predecessor_membranes
        .iter()
        .copied()
        .zip(capacitances.iter().copied())
        .map(|(membrane, capacitance)| membrane.potential_millivolts(capacitance))
        .collect::<Result<Vec<_>, _>>()?;
    let mut outward_by_neuron = vec![0_i128; anatomy.neuron_count];
    let mut transitions = Vec::with_capacity(anatomy.contacts.len());
    let mut successor_contact_states = Vec::with_capacity(anatomy.contacts.len());

    for (index, contact) in anatomy.contacts.iter().copied().enumerate() {
        let transition = settle_contact(
            contact,
            predecessor_contacts.contacts[index],
            potentials[contact.left_neuron],
            potentials[contact.right_neuron],
            interval_microseconds,
        )?;
        let right_outward = transition
            .outward_elementary_charges_from_left
            .checked_neg()
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        outward_by_neuron[contact.left_neuron] = outward_by_neuron[contact.left_neuron]
            .checked_add(transition.outward_elementary_charges_from_left)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        outward_by_neuron[contact.right_neuron] = outward_by_neuron[contact.right_neuron]
            .checked_add(right_outward)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        successor_contact_states.push(transition.successor);
        transitions.push(transition);
    }

    let conserved = outward_by_neuron.iter().try_fold(0_i128, |total, value| {
        total
            .checked_add(*value)
            .ok_or(SparseElectricalError::ArithmeticWidth)
    })?;
    if conserved != 0 {
        return Err(SparseElectricalError::ArithmeticWidth);
    }

    Ok(SparseElectricalTransferSettlement {
        successor_contacts: SparseElectricalState {
            contacts: successor_contact_states.into_boxed_slice(),
        },
        transitions: transitions.into_boxed_slice(),
        outward_elementary_charges_by_neuron: outward_by_neuron.into_boxed_slice(),
    })
}

/// Settle only contacts whose two endpoints are in the supplied reached
/// frontier. A mounted contact crossing the frontier makes that frontier
/// physically incomplete: the neighbour must be reached rather than silently
/// ignored. Contacts wholly outside the frontier retain their exact state and
/// perform zero work.
pub(crate) fn settle_sparse_electrical_transfers_reached(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    reached_neurons: &[bool],
    interval_microseconds: u32,
) -> Result<SparseElectricalTransferSettlement, SparseElectricalError> {
    if predecessor_contacts.contacts.len() != anatomy.contacts.len()
        || capacitances.len() != anatomy.neuron_count
        || predecessor_membranes.len() != anatomy.neuron_count
        || reached_neurons.len() != anatomy.neuron_count
    {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }

    let potentials = predecessor_membranes
        .iter()
        .copied()
        .zip(capacitances.iter().copied())
        .map(|(membrane, capacitance)| membrane.potential_millivolts(capacitance))
        .collect::<Result<Vec<_>, _>>()?;
    let mut outward_by_neuron = vec![0_i128; anatomy.neuron_count];
    let mut transitions = Vec::with_capacity(anatomy.contacts.len());
    let mut successor_contact_states = Vec::with_capacity(anatomy.contacts.len());

    for (index, contact) in anatomy.contacts.iter().copied().enumerate() {
        let left_reached = reached_neurons[contact.left_neuron];
        let right_reached = reached_neurons[contact.right_neuron];
        if left_reached != right_reached {
            return Err(SparseElectricalError::IncompleteReachedFrontier);
        }
        let transition = if left_reached {
            settle_contact(
                contact,
                predecessor_contacts.contacts[index],
                potentials[contact.left_neuron],
                potentials[contact.right_neuron],
                interval_microseconds,
            )?
        } else {
            ElectricalContactTransition {
                successor: predecessor_contacts.contacts[index],
                outward_current_from_left_picoamperes: ExactRational::integer(0),
                outward_elementary_charges_from_left: 0,
            }
        };
        let right_outward = transition
            .outward_elementary_charges_from_left
            .checked_neg()
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        outward_by_neuron[contact.left_neuron] = outward_by_neuron[contact.left_neuron]
            .checked_add(transition.outward_elementary_charges_from_left)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        outward_by_neuron[contact.right_neuron] = outward_by_neuron[contact.right_neuron]
            .checked_add(right_outward)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        successor_contact_states.push(transition.successor);
        transitions.push(transition);
    }

    if outward_by_neuron.iter().try_fold(0_i128, |total, value| {
        total
            .checked_add(*value)
            .ok_or(SparseElectricalError::ArithmeticWidth)
    })? != 0
    {
        return Err(SparseElectricalError::ArithmeticWidth);
    }

    Ok(SparseElectricalTransferSettlement {
        successor_contacts: SparseElectricalState {
            contacts: successor_contact_states.into_boxed_slice(),
        },
        transitions: transitions.into_boxed_slice(),
        outward_elementary_charges_by_neuron: outward_by_neuron.into_boxed_slice(),
    })
}

/// Settle only the supplied sparse reached contact fabric.  Every current is
/// computed from the same predecessor membrane generation before any charge
/// consequence is applied.
pub(crate) fn settle_sparse_electrical_contacts(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    interval_microseconds: u32,
) -> Result<SparseElectricalSettlement, SparseElectricalError> {
    let transfer = settle_sparse_electrical_transfers(
        anatomy,
        predecessor_contacts,
        capacitances,
        predecessor_membranes,
        interval_microseconds,
    )?;

    let successor_membranes = predecessor_membranes
        .iter()
        .copied()
        .zip(capacitances.iter().copied())
        .zip(
            transfer
                .outward_elementary_charges_by_neuron
                .iter()
                .copied(),
        )
        .map(|((membrane, capacitance), outward)| {
            settle_membrane_elementary_charges(
                capacitance,
                membrane,
                outward,
                interval_microseconds,
            )
            .map(|transition| transition.successor)
        })
        .collect::<Result<Vec<_>, _>>()?;

    Ok(SparseElectricalSettlement {
        successor_membranes: successor_membranes.into_boxed_slice(),
        successor_contacts: transfer.successor_contacts,
        transitions: transfer.transitions,
        outward_elementary_charges_by_neuron: transfer.outward_elementary_charges_by_neuron,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn capacitances(count: usize) -> Vec<MembraneCapacitance> {
        vec![MembraneCapacitance::new(ExactRational::integer(1)).unwrap(); count]
    }

    fn total_charge(memebranes: &[ElementaryChargeMembraneState]) -> i128 {
        memebranes
            .iter()
            .map(|membrane| membrane.separated_elementary_charges())
            .sum()
    }

    #[test]
    fn three_neuron_one_contact_uses_one_predecessor_and_conserves_charge() {
        let contacts =
            vec![ElectricalContactAnatomy::new(0, 1, ExactRational::integer(1), 3).unwrap()];
        let anatomy = SparseElectricalAnatomy::new(3, contacts).unwrap();
        let state = SparseElectricalState::genesis(&anatomy);
        let membranes = vec![
            ElementaryChargeMembraneState::genesis(1_000_000_000),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(0),
        ];
        let settled = settle_sparse_electrical_contacts(
            &anatomy,
            &state,
            &capacitances(3),
            &membranes,
            1_000,
        )
        .unwrap();
        assert_eq!(anatomy.neuron_count(), 3);
        assert_eq!(anatomy.contact_count(), 1);
        assert_eq!(settled.transitions.len(), 1);
        assert!(settled.transitions[0].outward_elementary_charges_from_left > 0);
        assert_eq!(
            settled.outward_elementary_charges_by_neuron[0],
            settled.transitions[0].outward_elementary_charges_from_left
        );
        assert_eq!(
            settled.outward_elementary_charges_by_neuron[1],
            -settled.transitions[0].outward_elementary_charges_from_left
        );
        assert_eq!(settled.outward_elementary_charges_by_neuron[2], 0);
        assert_eq!(
            settled
                .outward_elementary_charges_by_neuron
                .iter()
                .sum::<i128>(),
            0
        );
        assert_eq!(
            total_charge(&settled.successor_membranes),
            total_charge(&membranes)
        );
    }

    #[test]
    fn sparse_reached_frontier_preserves_unreached_contacts_and_rejects_open_edges() {
        let contacts =
            vec![ElectricalContactAnatomy::new(0, 1, ExactRational::integer(1), 3).unwrap()];
        let anatomy = SparseElectricalAnatomy::new(3, contacts).unwrap();
        let state = SparseElectricalState::genesis(&anatomy);
        let membranes = vec![
            ElementaryChargeMembraneState::genesis(1_000_000_000),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(0),
        ];

        let isolated = settle_sparse_electrical_transfers_reached(
            &anatomy,
            &state,
            &capacitances(3),
            &membranes,
            &[false, false, true],
            1_000,
        )
        .unwrap();
        assert_eq!(isolated.successor_contacts, state);
        assert_eq!(
            isolated.outward_elementary_charges_by_neuron.as_ref(),
            &[0, 0, 0]
        );
        assert_eq!(
            isolated.transitions[0].outward_current_from_left_picoamperes,
            ExactRational::integer(0)
        );

        assert_eq!(
            settle_sparse_electrical_transfers_reached(
                &anatomy,
                &state,
                &capacitances(3),
                &membranes,
                &[true, false, false],
                1_000,
            ),
            Err(SparseElectricalError::IncompleteReachedFrontier)
        );

        let closed = settle_sparse_electrical_transfers_reached(
            &anatomy,
            &state,
            &capacitances(3),
            &membranes,
            &[true, true, false],
            1_000,
        )
        .unwrap();
        assert!(closed.transitions[0].outward_elementary_charges_from_left > 0);
        assert_eq!(
            closed
                .outward_elementary_charges_by_neuron
                .iter()
                .sum::<i128>(),
            0
        );
    }

    #[test]
    fn four_neuron_sparse_chain_has_fixed_current_state_shape_under_recurrence() {
        let contacts = vec![
            ElectricalContactAnatomy::new(0, 1, ExactRational::integer(1), 4).unwrap(),
            ElectricalContactAnatomy::new(1, 2, ExactRational::integer(1), 4).unwrap(),
            ElectricalContactAnatomy::new(2, 3, ExactRational::integer(1), 4).unwrap(),
        ];
        let anatomy = SparseElectricalAnatomy::new(4, contacts).unwrap();
        let capacitances = capacitances(4);
        let mut contact_state = SparseElectricalState::genesis(&anatomy);
        let mut membranes = vec![
            ElementaryChargeMembraneState::genesis(1_000_000_000),
            ElementaryChargeMembraneState::genesis(500_000_000),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(-500_000_000),
        ];
        let original_total = total_charge(&membranes);
        for _ in 0..100 {
            let settled = settle_sparse_electrical_contacts(
                &anatomy,
                &contact_state,
                &capacitances,
                &membranes,
                1_000,
            )
            .unwrap();
            assert_eq!(settled.successor_membranes.len(), 4);
            assert_eq!(settled.successor_contacts.contact_count(), 3);
            assert_eq!(settled.transitions.len(), 3);
            assert_eq!(total_charge(&settled.successor_membranes), original_total);
            membranes = settled.successor_membranes.into_vec();
            contact_state = settled.successor_contacts;
        }
    }

    #[test]
    fn absent_or_invalid_physical_contact_is_refused_without_topology_invention() {
        assert_eq!(
            ElectricalContactAnatomy::new(0, 0, ExactRational::integer(1), 1),
            Err(SparseElectricalError::InvalidEndpoint)
        );
        assert_eq!(
            ElectricalContactAnatomy::new(0, 1, ExactRational::integer(0), 2),
            Err(SparseElectricalError::NonPositiveConductance)
        );
    }

    #[test]
    fn sparse_contact_anatomy_and_phase_cold_restore_exactly() {
        let contacts = vec![
            ElectricalContactAnatomy::new(0, 1, ExactRational::new(3, 2).unwrap(), 3).unwrap(),
            ElectricalContactAnatomy::new(1, 2, ExactRational::new(5, 4).unwrap(), 3).unwrap(),
        ];
        let anatomy = SparseElectricalAnatomy::new(3, contacts).unwrap();
        let state = SparseElectricalState::from_contact_states(
            &anatomy,
            vec![
                ElectricalContactState::from_carrier_phase(ChargeCarrierPhase::new(1, 3).unwrap()),
                ElectricalContactState::from_carrier_phase(ChargeCarrierPhase::new(-2, 7).unwrap()),
            ],
        )
        .unwrap();
        let encoded = encode_sparse_electrical_cell(&anatomy, &state).unwrap();
        let (restored_anatomy, restored_state) = decode_sparse_electrical_cell(&encoded).unwrap();
        assert_eq!(restored_anatomy, anatomy);
        assert_eq!(restored_state, state);
        assert_eq!(
            encode_sparse_electrical_cell(&restored_anatomy, &restored_state).unwrap(),
            encoded
        );

        let mut impossible = Vec::new();
        impossible.extend_from_slice(SPARSE_ELECTRICAL_CELL_CODEC_MAGIC);
        impossible.extend_from_slice(&3_u64.to_le_bytes());
        impossible.extend_from_slice(&u64::MAX.to_le_bytes());
        assert_eq!(
            decode_sparse_electrical_cell(&impossible),
            Err(SparseElectricalError::ArithmeticWidth)
        );
    }
}
