//! Sparse fixed-residency material exchange between reached neuron recovery
//! lanes and one shared body/fluid control volume.
//!
//! Mounted contact anatomy carries finite catalyst and transport capacities.
//! Catalyst represents an unchanged expressed enzyme/contact at the site; fuel,
//! spent material, and heat are conserved state. Capacities are derived from
//! complete saturation of every mounted Psi, gate, and plastic dissipation
//! reservoir. No timer, reset, desired state, owner, lock, database, queued
//! work, or whole-brain scan is present here.

use crate::complete_neuron::{
    required_gate_recovery_extent_for_interval, settle_recovery_only, GateWorkOccurrence,
    NeuronPhysicalAnatomy, NeuronPhysicalError, NeuronPhysicalState, RecoveryContact,
    RecoveryError, RecoveryLaneAddress, RecoveryLaneAnatomy, RecoveryLaneState,
};
use crate::joint_uf_neuron_boundary::JointNeuronPerspective;

const ANATOMY_MAGIC: &[u8; 8] = b"GLRFA01\0";
const STATE_MAGIC: &[u8; 8] = b"GLRFS01\0";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryFluidReservoirAnatomy {
    fuel_capacity: u128,
    spent_capacity: u128,
    heat_capacity: u128,
}

impl RecoveryFluidReservoirAnatomy {
    pub(crate) fn new(fuel_capacity: u128, spent_capacity: u128, heat_capacity: u128) -> Self {
        Self {
            fuel_capacity,
            spent_capacity,
            heat_capacity,
        }
    }

    pub(crate) fn capacities(self) -> (u128, u128, u128) {
        (self.fuel_capacity, self.spent_capacity, self.heat_capacity)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryFluidReservoirState {
    fuel_quanta: u128,
    spent_quanta: u128,
    heat_quanta: u128,
}

impl RecoveryFluidReservoirState {
    pub(crate) fn new(
        anatomy: RecoveryFluidReservoirAnatomy,
        fuel_quanta: u128,
        spent_quanta: u128,
        heat_quanta: u128,
    ) -> Result<Self, RecoveryFluidError> {
        if fuel_quanta > anatomy.fuel_capacity
            || spent_quanta > anatomy.spent_capacity
            || heat_quanta > anatomy.heat_capacity
        {
            return Err(RecoveryFluidError::StateOutsideAnatomy);
        }
        Ok(Self {
            fuel_quanta,
            spent_quanta,
            heat_quanta,
        })
    }

    pub(crate) fn physical_parts(self) -> (u128, u128, u128) {
        (self.fuel_quanta, self.spent_quanta, self.heat_quanta)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryFluidContactAnatomy {
    catalyst_capacity_per_interval: u128,
    fuel_inward_capacity_per_interval: u128,
    spent_outward_capacity_per_interval: u128,
    heat_outward_capacity_per_interval: u128,
}

impl RecoveryFluidContactAnatomy {
    pub(crate) fn new(
        catalyst_capacity_per_interval: u128,
        fuel_inward_capacity_per_interval: u128,
        spent_outward_capacity_per_interval: u128,
        heat_outward_capacity_per_interval: u128,
    ) -> Result<Self, RecoveryFluidError> {
        if catalyst_capacity_per_interval == 0
            || fuel_inward_capacity_per_interval == 0
            || spent_outward_capacity_per_interval == 0
            || heat_outward_capacity_per_interval == 0
        {
            return Err(RecoveryFluidError::EmptyContact);
        }
        Ok(Self {
            catalyst_capacity_per_interval,
            fuel_inward_capacity_per_interval,
            spent_outward_capacity_per_interval,
            heat_outward_capacity_per_interval,
        })
    }

    fn parts(self) -> (u128, u128, u128, u128) {
        (
            self.catalyst_capacity_per_interval,
            self.fuel_inward_capacity_per_interval,
            self.spent_outward_capacity_per_interval,
            self.heat_outward_capacity_per_interval,
        )
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryFluidNeuronAnatomy {
    psi_contacts: Box<[RecoveryFluidContactAnatomy]>,
    gate_contact: RecoveryFluidContactAnatomy,
    plastic_contact: RecoveryFluidContactAnatomy,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ReachedRecoveryFluidAnatomy {
    reservoir: RecoveryFluidReservoirAnatomy,
    neurons: Box<[RecoveryFluidNeuronAnatomy]>,
}

impl ReachedRecoveryFluidAnatomy {
    pub(crate) fn derive(neurons: &[NeuronPhysicalAnatomy]) -> Result<Self, RecoveryFluidError> {
        if neurons.is_empty() {
            return Err(RecoveryFluidError::AnatomyWidth);
        }
        let mut mounted = Vec::new();
        mounted
            .try_reserve_exact(neurons.len())
            .map_err(|_| RecoveryFluidError::ArithmeticWidth)?;
        let mut fuel_capacity = 0_u128;
        let mut spent_capacity = 0_u128;
        let mut heat_capacity = 0_u128;
        for neuron in neurons {
            let mut psi_contacts = Vec::new();
            psi_contacts
                .try_reserve_exact(neuron.psi_ring_count())
                .map_err(|_| RecoveryFluidError::ArithmeticWidth)?;
            for index in 0..neuron.psi_ring_count() {
                let contact = derive_contact(neuron, RecoveryLaneAddress::Psi(index))?;
                accumulate_contact(
                    contact,
                    &mut fuel_capacity,
                    &mut spent_capacity,
                    &mut heat_capacity,
                )?;
                psi_contacts.push(contact);
            }
            let gate_contact = derive_contact(neuron, RecoveryLaneAddress::Gate)?;
            accumulate_contact(
                gate_contact,
                &mut fuel_capacity,
                &mut spent_capacity,
                &mut heat_capacity,
            )?;
            let plastic_contact = derive_contact(neuron, RecoveryLaneAddress::Plastic)?;
            accumulate_contact(
                plastic_contact,
                &mut fuel_capacity,
                &mut spent_capacity,
                &mut heat_capacity,
            )?;
            mounted.push(RecoveryFluidNeuronAnatomy {
                psi_contacts: psi_contacts.into_boxed_slice(),
                gate_contact,
                plastic_contact,
            });
        }
        Ok(Self {
            reservoir: RecoveryFluidReservoirAnatomy::new(
                fuel_capacity,
                spent_capacity,
                heat_capacity,
            ),
            neurons: mounted.into_boxed_slice(),
        })
    }

    pub(crate) fn genesis_state(&self) -> RecoveryFluidReservoirState {
        RecoveryFluidReservoirState {
            fuel_quanta: self.reservoir.fuel_capacity,
            spent_quanta: 0,
            heat_quanta: 0,
        }
    }

    pub(crate) fn reservoir_anatomy(&self) -> RecoveryFluidReservoirAnatomy {
        self.reservoir
    }

    pub(crate) fn neuron_count(&self) -> usize {
        self.neurons.len()
    }

    fn neuron(&self, index: usize) -> Option<&RecoveryFluidNeuronAnatomy> {
        self.neurons.get(index)
    }
}

pub(crate) fn extend_reached_recovery_fluid_state(
    predecessor_anatomy: &ReachedRecoveryFluidAnatomy,
    successor_anatomy: &ReachedRecoveryFluidAnatomy,
    predecessor: RecoveryFluidReservoirState,
) -> Result<RecoveryFluidReservoirState, RecoveryFluidError> {
    if successor_anatomy.neurons.len() < predecessor_anatomy.neurons.len()
        || successor_anatomy.neurons[..predecessor_anatomy.neurons.len()]
            != predecessor_anatomy.neurons[..]
    {
        return Err(RecoveryFluidError::AnatomyWidth);
    }
    let predecessor_capacity = predecessor_anatomy.reservoir.capacities();
    let successor_capacity = successor_anatomy.reservoir.capacities();
    let predecessor_state = predecessor.physical_parts();
    let added_fuel_capacity = successor_capacity
        .0
        .checked_sub(predecessor_capacity.0)
        .ok_or(RecoveryFluidError::AnatomyWidth)?;
    if successor_capacity.1 < predecessor_capacity.1
        || successor_capacity.2 < predecessor_capacity.2
    {
        return Err(RecoveryFluidError::AnatomyWidth);
    }
    RecoveryFluidReservoirState::new(
        successor_anatomy.reservoir,
        predecessor_state
            .0
            .checked_add(added_fuel_capacity)
            .ok_or(RecoveryFluidError::ArithmeticWidth)?,
        predecessor_state.1,
        predecessor_state.2,
    )
}

fn derive_contact(
    neuron: &NeuronPhysicalAnatomy,
    address: RecoveryLaneAddress,
) -> Result<RecoveryFluidContactAnatomy, RecoveryFluidError> {
    let required = neuron.recovery_full_saturation_requirement(address)?;
    RecoveryFluidContactAnatomy::new(
        required.catalyst_quanta,
        required.fuel_quanta,
        required.spent_quanta,
        required.heat_quanta,
    )
}

fn accumulate_contact(
    contact: RecoveryFluidContactAnatomy,
    fuel: &mut u128,
    spent: &mut u128,
    heat: &mut u128,
) -> Result<(), RecoveryFluidError> {
    let (_, contact_fuel, contact_spent, contact_heat) = contact.parts();
    *fuel = fuel
        .checked_add(contact_fuel)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    *spent = spent
        .checked_add(contact_spent)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    *heat = heat
        .checked_add(contact_heat)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    Ok(())
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryFluidSettlement {
    pub(crate) successor_lane: RecoveryLaneState,
    pub(crate) successor_reservoir: RecoveryFluidReservoirState,
    pub(crate) inward_fuel_quanta: u128,
    pub(crate) outward_spent_quanta: u128,
    pub(crate) outward_heat_quanta: u128,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ResidentGateRecoverySettlement {
    pub(crate) successor_neuron: NeuronPhysicalState,
    pub(crate) successor_reservoir: RecoveryFluidReservoirState,
    pub(crate) required_extent: u128,
    pub(crate) settled_extent: u128,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum RecoveryFluidError {
    EmptyContact,
    AnatomyWidth,
    StateOutsideAnatomy,
    ArithmeticWidth,
    MaterialContinuity,
    InvalidEncoding,
    Recovery(RecoveryError),
    Neuron(NeuronPhysicalError),
}

impl From<RecoveryError> for RecoveryFluidError {
    fn from(value: RecoveryError) -> Self {
        Self::Recovery(value)
    }
}

impl From<NeuronPhysicalError> for RecoveryFluidError {
    fn from(value: NeuronPhysicalError) -> Self {
        Self::Neuron(value)
    }
}

pub(crate) fn settle_recovery_fluid_contact(
    lane_anatomy: RecoveryLaneAnatomy,
    predecessor_lane: RecoveryLaneState,
    reservoir_anatomy: RecoveryFluidReservoirAnatomy,
    predecessor_reservoir: RecoveryFluidReservoirState,
    contact: RecoveryFluidContactAnatomy,
) -> Result<RecoveryFluidSettlement, RecoveryFluidError> {
    let (lane_fuel, lane_spent, lane_heat) = predecessor_lane.physical_parts();
    let (lane_fuel_capacity, _, _) = lane_anatomy.capacities();
    let (reservoir_fuel, reservoir_spent, reservoir_heat) = predecessor_reservoir.physical_parts();
    if reservoir_fuel > reservoir_anatomy.fuel_capacity
        || reservoir_spent > reservoir_anatomy.spent_capacity
        || reservoir_heat > reservoir_anatomy.heat_capacity
    {
        return Err(RecoveryFluidError::StateOutsideAnatomy);
    }
    let inward_fuel = contact
        .fuel_inward_capacity_per_interval
        .min(reservoir_fuel)
        .min(
            lane_fuel_capacity
                .checked_sub(lane_fuel)
                .ok_or(RecoveryFluidError::StateOutsideAnatomy)?,
        );
    let outward_spent = contact
        .spent_outward_capacity_per_interval
        .min(lane_spent)
        .min(
            reservoir_anatomy
                .spent_capacity
                .checked_sub(reservoir_spent)
                .ok_or(RecoveryFluidError::StateOutsideAnatomy)?,
        );
    let outward_heat = contact
        .heat_outward_capacity_per_interval
        .min(lane_heat)
        .min(
            reservoir_anatomy
                .heat_capacity
                .checked_sub(reservoir_heat)
                .ok_or(RecoveryFluidError::StateOutsideAnatomy)?,
        );
    let successor_lane = RecoveryLaneState::from_physical_parts(
        lane_anatomy,
        lane_fuel
            .checked_add(inward_fuel)
            .ok_or(RecoveryFluidError::ArithmeticWidth)?,
        lane_spent - outward_spent,
        lane_heat - outward_heat,
    )?;
    let successor_reservoir = RecoveryFluidReservoirState::new(
        reservoir_anatomy,
        reservoir_fuel - inward_fuel,
        reservoir_spent
            .checked_add(outward_spent)
            .ok_or(RecoveryFluidError::ArithmeticWidth)?,
        reservoir_heat
            .checked_add(outward_heat)
            .ok_or(RecoveryFluidError::ArithmeticWidth)?,
    )?;
    Ok(RecoveryFluidSettlement {
        successor_lane,
        successor_reservoir,
        inward_fuel_quanta: inward_fuel,
        outward_spent_quanta: outward_spent,
        outward_heat_quanta: outward_heat,
    })
}

pub(crate) fn settle_resident_gate_recovery_before_interval(
    recovery_anatomy: &ReachedRecoveryFluidAnatomy,
    neuron_index: usize,
    neuron_anatomy: &NeuronPhysicalAnatomy,
    predecessor_neuron: &NeuronPhysicalState,
    perspective: JointNeuronPerspective<'_>,
    gate_work: &GateWorkOccurrence,
    predecessor_reservoir: RecoveryFluidReservoirState,
) -> Result<ResidentGateRecoverySettlement, RecoveryFluidError> {
    let mounted = recovery_anatomy
        .neuron(neuron_index)
        .ok_or(RecoveryFluidError::AnatomyWidth)?;
    if mounted.psi_contacts.len() != neuron_anatomy.psi_ring_count() {
        return Err(RecoveryFluidError::AnatomyWidth);
    }
    let required_extent = required_gate_recovery_extent_for_interval(
        neuron_anatomy,
        predecessor_neuron,
        perspective,
        gate_work,
    )?;
    if required_extent == 0 {
        return Ok(ResidentGateRecoverySettlement {
            successor_neuron: predecessor_neuron.clone(),
            successor_reservoir: predecessor_reservoir,
            required_extent,
            settled_extent: 0,
        });
    }
    let lane_anatomy = neuron_anatomy
        .recovery_anatomy()
        .lane(RecoveryLaneAddress::Gate)
        .ok_or(RecoveryError::AnatomyWidth)?;
    let predecessor_lane = predecessor_neuron
        .recovery
        .lane(RecoveryLaneAddress::Gate)
        .ok_or(RecoveryError::AnatomyWidth)?;
    let (catalyst_per_extent, fuel_per_extent, spent_per_extent, heat_per_extent) =
        lane_anatomy.stoichiometry();
    let (lane_fuel_capacity, lane_spent_capacity, lane_heat_capacity) = lane_anatomy.capacities();
    let (lane_fuel, lane_spent, lane_heat) = predecessor_lane.physical_parts();
    let (reservoir_fuel_capacity, reservoir_spent_capacity, reservoir_heat_capacity) =
        recovery_anatomy.reservoir.capacities();
    let (reservoir_fuel, reservoir_spent, reservoir_heat) = predecessor_reservoir.physical_parts();
    if lane_fuel > lane_fuel_capacity
        || lane_spent > lane_spent_capacity
        || lane_heat > lane_heat_capacity
        || reservoir_fuel > reservoir_fuel_capacity
        || reservoir_spent > reservoir_spent_capacity
        || reservoir_heat > reservoir_heat_capacity
    {
        return Err(RecoveryFluidError::StateOutsideAnatomy);
    }
    let contact = mounted.gate_contact;
    let settled_extent = required_extent
        // Conservation: the recovery reaction undoes dissipation, so it can
        // never run further than the dissipation that actually exists. The
        // lane settlement itself applies this bound, so omitting it here made
        // the pre-pass demand an extent the lane truthfully could not deliver
        // and refuse the whole transition with MaterialContinuity. Latent
        // until the ratified quantized-light law first opened a gate.
        .min(predecessor_neuron.gate.dissipated_quanta() / heat_per_extent)
        .min(lane_fuel / fuel_per_extent)
        .min((lane_spent_capacity - lane_spent) / spent_per_extent)
        .min((lane_heat_capacity - lane_heat) / heat_per_extent)
        .min(reservoir_fuel / fuel_per_extent)
        .min((reservoir_spent_capacity - reservoir_spent) / spent_per_extent)
        .min((reservoir_heat_capacity - reservoir_heat) / heat_per_extent)
        .min(contact.catalyst_capacity_per_interval / catalyst_per_extent)
        .min(contact.fuel_inward_capacity_per_interval / fuel_per_extent)
        .min(contact.spent_outward_capacity_per_interval / spent_per_extent)
        .min(contact.heat_outward_capacity_per_interval / heat_per_extent);
    if settled_extent == 0 {
        return Ok(ResidentGateRecoverySettlement {
            successor_neuron: predecessor_neuron.clone(),
            successor_reservoir: predecessor_reservoir,
            required_extent,
            settled_extent,
        });
    }
    let catalyst = settled_extent
        .checked_mul(catalyst_per_extent)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    let zero_psi_catalysts = vec![0; mounted.psi_contacts.len()];
    let recovered = settle_recovery_only(
        neuron_anatomy,
        predecessor_neuron,
        RecoveryContact::new(&zero_psi_catalysts, catalyst, 0),
    )?;
    if recovered.extent != settled_extent {
        return Err(RecoveryFluidError::MaterialContinuity);
    }
    let expected_fuel = settled_extent
        .checked_mul(fuel_per_extent)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    let expected_spent = settled_extent
        .checked_mul(spent_per_extent)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    let expected_heat = settled_extent
        .checked_mul(heat_per_extent)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    let recovered_lane = recovered
        .successor
        .recovery
        .lane(RecoveryLaneAddress::Gate)
        .ok_or(RecoveryError::AnatomyWidth)?;
    let exchanged = settle_recovery_fluid_contact(
        lane_anatomy,
        recovered_lane,
        recovery_anatomy.reservoir,
        predecessor_reservoir,
        contact,
    )?;
    if exchanged.inward_fuel_quanta != expected_fuel
        || exchanged.outward_spent_quanta != expected_spent
        || exchanged.outward_heat_quanta != expected_heat
    {
        return Err(RecoveryFluidError::MaterialContinuity);
    }
    let mut successor_neuron = recovered.successor;
    successor_neuron
        .recovery
        .replace_lane(RecoveryLaneAddress::Gate, exchanged.successor_lane)?;
    Ok(ResidentGateRecoverySettlement {
        successor_neuron,
        successor_reservoir: exchanged.successor_reservoir,
        required_extent,
        settled_extent,
    })
}

pub(crate) fn encode_reached_recovery_fluid_anatomy(
    anatomy: &ReachedRecoveryFluidAnatomy,
) -> Result<Vec<u8>, RecoveryFluidError> {
    let mut out = Vec::new();
    out.extend_from_slice(ANATOMY_MAGIC);
    push_three(&mut out, anatomy.reservoir.capacities());
    push_usize(&mut out, anatomy.neurons.len())?;
    for neuron in &anatomy.neurons {
        push_usize(&mut out, neuron.psi_contacts.len())?;
        for contact in neuron
            .psi_contacts
            .iter()
            .chain([&neuron.gate_contact, &neuron.plastic_contact])
        {
            push_four(&mut out, contact.parts());
        }
    }
    Ok(out)
}

pub(crate) fn decode_reached_recovery_fluid_anatomy(
    encoded: &[u8],
    neurons: &[NeuronPhysicalAnatomy],
) -> Result<ReachedRecoveryFluidAnatomy, RecoveryFluidError> {
    let mut reader = Reader::new(encoded);
    if reader.take(ANATOMY_MAGIC.len())? != ANATOMY_MAGIC {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    let reservoir =
        RecoveryFluidReservoirAnatomy::new(reader.u128()?, reader.u128()?, reader.u128()?);
    let count = reader.usize()?;
    if count != neurons.len() {
        return Err(RecoveryFluidError::AnatomyWidth);
    }
    let mut mounted = Vec::new();
    mounted
        .try_reserve_exact(count)
        .map_err(|_| RecoveryFluidError::ArithmeticWidth)?;
    for neuron in neurons {
        let psi_count = reader.usize()?;
        if psi_count != neuron.psi_ring_count() {
            return Err(RecoveryFluidError::AnatomyWidth);
        }
        let mut psi_contacts = Vec::new();
        psi_contacts
            .try_reserve_exact(psi_count)
            .map_err(|_| RecoveryFluidError::ArithmeticWidth)?;
        for _ in 0..psi_count {
            psi_contacts.push(reader.contact()?);
        }
        mounted.push(RecoveryFluidNeuronAnatomy {
            psi_contacts: psi_contacts.into_boxed_slice(),
            gate_contact: reader.contact()?,
            plastic_contact: reader.contact()?,
        });
    }
    if !reader.finished() {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    let decoded = ReachedRecoveryFluidAnatomy {
        reservoir,
        neurons: mounted.into_boxed_slice(),
    };
    if decoded != ReachedRecoveryFluidAnatomy::derive(neurons)? {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    Ok(decoded)
}

pub(crate) fn encode_reached_recovery_fluid_state(
    anatomy: &ReachedRecoveryFluidAnatomy,
    state: RecoveryFluidReservoirState,
) -> Result<Vec<u8>, RecoveryFluidError> {
    RecoveryFluidReservoirState::new(
        anatomy.reservoir,
        state.fuel_quanta,
        state.spent_quanta,
        state.heat_quanta,
    )?;
    let mut out = Vec::new();
    out.extend_from_slice(STATE_MAGIC);
    push_three(&mut out, state.physical_parts());
    Ok(out)
}

pub(crate) fn decode_reached_recovery_fluid_state(
    encoded: &[u8],
    anatomy: &ReachedRecoveryFluidAnatomy,
) -> Result<RecoveryFluidReservoirState, RecoveryFluidError> {
    let mut reader = Reader::new(encoded);
    if reader.take(STATE_MAGIC.len())? != STATE_MAGIC {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    let state = RecoveryFluidReservoirState::new(
        anatomy.reservoir,
        reader.u128()?,
        reader.u128()?,
        reader.u128()?,
    )?;
    if !reader.finished() {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    Ok(state)
}

fn push_three(out: &mut Vec<u8>, values: (u128, u128, u128)) {
    out.extend_from_slice(&values.0.to_le_bytes());
    out.extend_from_slice(&values.1.to_le_bytes());
    out.extend_from_slice(&values.2.to_le_bytes());
}

fn push_four(out: &mut Vec<u8>, values: (u128, u128, u128, u128)) {
    out.extend_from_slice(&values.0.to_le_bytes());
    out.extend_from_slice(&values.1.to_le_bytes());
    out.extend_from_slice(&values.2.to_le_bytes());
    out.extend_from_slice(&values.3.to_le_bytes());
}

fn push_usize(out: &mut Vec<u8>, value: usize) -> Result<(), RecoveryFluidError> {
    out.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| RecoveryFluidError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

struct Reader<'a> {
    bytes: &'a [u8],
    cursor: usize,
}

impl<'a> Reader<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], RecoveryFluidError> {
        let end = self
            .cursor
            .checked_add(count)
            .ok_or(RecoveryFluidError::ArithmeticWidth)?;
        let value = self
            .bytes
            .get(self.cursor..end)
            .ok_or(RecoveryFluidError::InvalidEncoding)?;
        self.cursor = end;
        Ok(value)
    }

    fn usize(&mut self) -> Result<usize, RecoveryFluidError> {
        usize::try_from(u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| RecoveryFluidError::InvalidEncoding)?,
        ))
        .map_err(|_| RecoveryFluidError::ArithmeticWidth)
    }

    fn u128(&mut self) -> Result<u128, RecoveryFluidError> {
        Ok(u128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| RecoveryFluidError::InvalidEncoding)?,
        ))
    }

    fn contact(&mut self) -> Result<RecoveryFluidContactAnatomy, RecoveryFluidError> {
        RecoveryFluidContactAnatomy::new(self.u128()?, self.u128()?, self.u128()?, self.u128()?)
    }

    fn finished(&self) -> bool {
        self.cursor == self.bytes.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lane_anatomy() -> RecoveryLaneAnatomy {
        RecoveryLaneAnatomy::new(1, 1, 1, 1, 1, 1, 1).unwrap()
    }

    #[test]
    fn reached_fluid_contact_conserves_fuel_spent_and_heat_exactly() {
        let lane_anatomy = lane_anatomy();
        let lane = RecoveryLaneState::from_physical_parts(lane_anatomy, 0, 1, 1).unwrap();
        let reservoir_anatomy = RecoveryFluidReservoirAnatomy::new(1, 1, 1);
        let reservoir = RecoveryFluidReservoirState::new(reservoir_anatomy, 1, 0, 0).unwrap();
        let settled = settle_recovery_fluid_contact(
            lane_anatomy,
            lane,
            reservoir_anatomy,
            reservoir,
            RecoveryFluidContactAnatomy::new(1, 1, 1, 1).unwrap(),
        )
        .unwrap();
        assert_eq!(settled.successor_lane.physical_parts(), (1, 0, 0));
        assert_eq!(settled.successor_reservoir.physical_parts(), (0, 1, 1));
        assert_eq!(settled.inward_fuel_quanta, 1);
        assert_eq!(settled.outward_spent_quanta, 1);
        assert_eq!(settled.outward_heat_quanta, 1);
        let predecessor_total = (
            lane.physical_parts().0 + reservoir.physical_parts().0,
            lane.physical_parts().1 + reservoir.physical_parts().1,
            lane.physical_parts().2 + reservoir.physical_parts().2,
        );
        let successor_total = (
            settled.successor_lane.physical_parts().0
                + settled.successor_reservoir.physical_parts().0,
            settled.successor_lane.physical_parts().1
                + settled.successor_reservoir.physical_parts().1,
            settled.successor_lane.physical_parts().2
                + settled.successor_reservoir.physical_parts().2,
        );
        assert_eq!(successor_total, predecessor_total);
    }
}
