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
    required_gate_recovery_extent_for_interval_with_psi, settle_recovery_only, GateWorkOccurrence,
    NeuronPhysicalAnatomy, NeuronPhysicalError, NeuronPhysicalState, PsiSettlement,
    RecoveryContact, RecoveryError, RecoveryLaneAddress, RecoveryLaneAnatomy, RecoveryLaneState,
};
use crate::exact_rational::{ExactRational, ExactRationalError};
use core::cmp::Ordering;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::ToPrimitive;

const ANATOMY_MAGIC: &[u8; 8] = b"GLRFA02\0";
const LEGACY_ANATOMY_MAGIC: &[u8; 8] = b"GLRFA01\0";
const STATE_MAGIC: &[u8; 8] = b"GLRFS02\0";
const LEGACY_STATE_MAGIC: &[u8; 8] = b"GLRFS01\0";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryFluidReservoirAnatomy {
    available_energy_capacity_zeptojoules: ExactRational,
    spent_energy_capacity_zeptojoules: ExactRational,
    thermal_energy_capacity_zeptojoules: ExactRational,
}

impl RecoveryFluidReservoirAnatomy {
    pub(crate) fn new(
        available_energy_capacity_zeptojoules: ExactRational,
        spent_energy_capacity_zeptojoules: ExactRational,
        thermal_energy_capacity_zeptojoules: ExactRational,
    ) -> Result<Self, RecoveryFluidError> {
        for value in [
            available_energy_capacity_zeptojoules,
            spent_energy_capacity_zeptojoules,
            thermal_energy_capacity_zeptojoules,
        ] {
            if wide_rational(value) < wide_rational(ExactRational::integer(0)) {
                return Err(RecoveryFluidError::StateOutsideAnatomy);
            }
        }
        Ok(Self {
            available_energy_capacity_zeptojoules,
            spent_energy_capacity_zeptojoules,
            thermal_energy_capacity_zeptojoules,
        })
    }

    pub(crate) fn capacities(self) -> (ExactRational, ExactRational, ExactRational) {
        (
            self.available_energy_capacity_zeptojoules,
            self.spent_energy_capacity_zeptojoules,
            self.thermal_energy_capacity_zeptojoules,
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryFluidReservoirState {
    available_energy_zeptojoules: ExactRational,
    spent_energy_zeptojoules: ExactRational,
    thermal_energy_zeptojoules: ExactRational,
}

impl RecoveryFluidReservoirState {
    pub(crate) fn new(
        anatomy: RecoveryFluidReservoirAnatomy,
        available_energy_zeptojoules: ExactRational,
        spent_energy_zeptojoules: ExactRational,
        thermal_energy_zeptojoules: ExactRational,
    ) -> Result<Self, RecoveryFluidError> {
        let zero = wide_rational(ExactRational::integer(0));
        if wide_rational(available_energy_zeptojoules) < zero
            || wide_rational(spent_energy_zeptojoules) < zero
            || wide_rational(thermal_energy_zeptojoules) < zero
            || wide_rational(available_energy_zeptojoules)
                > wide_rational(anatomy.available_energy_capacity_zeptojoules)
            || wide_rational(spent_energy_zeptojoules)
                > wide_rational(anatomy.spent_energy_capacity_zeptojoules)
            || wide_rational(thermal_energy_zeptojoules)
                > wide_rational(anatomy.thermal_energy_capacity_zeptojoules)
        {
            return Err(RecoveryFluidError::StateOutsideAnatomy);
        }
        Ok(Self {
            available_energy_zeptojoules,
            spent_energy_zeptojoules,
            thermal_energy_zeptojoules,
        })
    }

    pub(crate) fn physical_parts(self) -> (ExactRational, ExactRational, ExactRational) {
        (
            self.available_energy_zeptojoules,
            self.spent_energy_zeptojoules,
            self.thermal_energy_zeptojoules,
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PoweredEnvironmentExchange {
    pub(crate) successor: RecoveryFluidReservoirState,
    pub(crate) delivered_energy_zeptojoules: ExactRational,
    pub(crate) exported_heat_zeptojoules: ExactRational,
}

/// Settle one always-available phase-one incubator contact.
///
/// External power converts already-retained spent energy-equivalent material
/// back into available body energy; it does not create extra body material or
/// refill to a target.  The independent heat path removes only heat that is
/// physically present.  Both transfers are bounded by the contact's exact
/// energy for this elapsed interval and the finite destination/source state.
pub(crate) fn settle_powered_environment_exchange(
    anatomy: RecoveryFluidReservoirAnatomy,
    predecessor: RecoveryFluidReservoirState,
    maximum_interval_energy_zeptojoules: ExactRational,
) -> Result<PoweredEnvironmentExchange, RecoveryFluidError> {
    let zero = ExactRational::integer(0);
    if wide_rational(maximum_interval_energy_zeptojoules) < wide_rational(zero) {
        return Err(RecoveryFluidError::StateOutsideAnatomy);
    }
    let (available_capacity, _, _) = anatomy.capacities();
    let (available, spent, thermal) = predecessor.physical_parts();
    let delivered_wide = wide_rational(maximum_interval_energy_zeptojoules)
        .min(wide_rational(spent))
        .min(wide_rational(available_capacity) - wide_rational(available));
    let delivered = match narrow_rational(delivered_wide) {
        Ok(value) => value,
        Err(RecoveryFluidError::ArithmeticWidth) => zero,
        Err(error) => return Err(error),
    };
    let delivered = if representable_reservoir_change(available, delivered, 1, false)
        && representable_reservoir_change(spent, delivered, 1, true)
    {
        delivered
    } else {
        zero
    };
    let exported_heat_wide =
        wide_rational(maximum_interval_energy_zeptojoules).min(wide_rational(thermal));
    let exported_heat = match narrow_rational(exported_heat_wide) {
        Ok(value) => value,
        Err(RecoveryFluidError::ArithmeticWidth) => zero,
        Err(error) => return Err(error),
    };
    let exported_heat = if representable_reservoir_change(thermal, exported_heat, 1, true) {
        exported_heat
    } else {
        zero
    };
    let successor = RecoveryFluidReservoirState::new(
        anatomy,
        wide_add(available, delivered)?,
        wide_sub(spent, delivered)?,
        wide_sub(thermal, exported_heat)?,
    )?;
    Ok(PoweredEnvironmentExchange {
        successor,
        delivered_energy_zeptojoules: delivered,
        exported_heat_zeptojoules: exported_heat,
    })
}

fn wide_rational(value: ExactRational) -> BigRational {
    let (numerator, denominator) = value.parts();
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

fn narrow_rational(value: BigRational) -> Result<ExactRational, RecoveryFluidError> {
    ExactRational::new(
        value
            .numer()
            .to_i128()
            .ok_or(RecoveryFluidError::ArithmeticWidth)?,
        value
            .denom()
            .to_u128()
            .ok_or(RecoveryFluidError::ArithmeticWidth)?,
    )
    .map_err(Into::into)
}

fn wide_add(
    left: ExactRational,
    right: ExactRational,
) -> Result<ExactRational, RecoveryFluidError> {
    narrow_rational(wide_rational(left) + wide_rational(right))
}

fn wide_sub(
    left: ExactRational,
    right: ExactRational,
) -> Result<ExactRational, RecoveryFluidError> {
    narrow_rational(wide_rational(left) - wide_rational(right))
}

impl From<ExactRationalError> for RecoveryFluidError {
    fn from(_: ExactRationalError) -> Self {
        Self::ArithmeticWidth
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

    pub(crate) fn parts(self) -> (u128, u128, u128, u128) {
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
    minimum_recovery_energy_per_extent_zeptojoules: ExactRational,
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
        let mut energy_capacity = ExactRational::integer(0);
        let mut minimum_recovery_energy = None;
        for neuron in neurons {
            let mut psi_contacts = Vec::new();
            psi_contacts
                .try_reserve_exact(neuron.psi_ring_count())
                .map_err(|_| RecoveryFluidError::ArithmeticWidth)?;
            for index in 0..neuron.psi_ring_count() {
                let contact = derive_contact(neuron, RecoveryLaneAddress::Psi(index))?;
                accumulate_contact_energy(
                    neuron,
                    RecoveryLaneAddress::Psi(index),
                    contact,
                    &mut energy_capacity,
                    &mut minimum_recovery_energy,
                )?;
                psi_contacts.push(contact);
            }
            let gate_contact = derive_contact(neuron, RecoveryLaneAddress::Gate)?;
            accumulate_contact_energy(
                neuron,
                RecoveryLaneAddress::Gate,
                gate_contact,
                &mut energy_capacity,
                &mut minimum_recovery_energy,
            )?;
            let plastic_contact = derive_contact(neuron, RecoveryLaneAddress::Plastic)?;
            accumulate_contact_energy(
                neuron,
                RecoveryLaneAddress::Plastic,
                plastic_contact,
                &mut energy_capacity,
                &mut minimum_recovery_energy,
            )?;
            mounted.push(RecoveryFluidNeuronAnatomy {
                psi_contacts: psi_contacts.into_boxed_slice(),
                gate_contact,
                plastic_contact,
            });
        }
        Ok(Self {
            reservoir: RecoveryFluidReservoirAnatomy::new(
                energy_capacity,
                energy_capacity,
                energy_capacity,
            )?,
            neurons: mounted.into_boxed_slice(),
            minimum_recovery_energy_per_extent_zeptojoules: minimum_recovery_energy
                .ok_or(RecoveryFluidError::AnatomyWidth)?,
        })
    }

    pub(crate) fn genesis_state(&self) -> RecoveryFluidReservoirState {
        RecoveryFluidReservoirState {
            available_energy_zeptojoules: self.reservoir.available_energy_capacity_zeptojoules,
            spent_energy_zeptojoules: ExactRational::integer(0),
            thermal_energy_zeptojoules: ExactRational::integer(0),
        }
    }

    pub(crate) fn reservoir_anatomy(&self) -> RecoveryFluidReservoirAnatomy {
        self.reservoir
    }

    pub(crate) fn neuron_count(&self) -> usize {
        self.neurons.len()
    }

    pub(crate) fn minimum_recovery_energy_per_extent_zeptojoules(&self) -> ExactRational {
        self.minimum_recovery_energy_per_extent_zeptojoules
    }

    fn neuron(&self, index: usize) -> Option<&RecoveryFluidNeuronAnatomy> {
        self.neurons.get(index)
    }

    /// The mounted fluid contact serving one neuron's named recovery lane.
    /// Every lane of every mounted neuron already carries this anatomy; the
    /// gate lane was simply the only one any settlement ever addressed.
    pub(crate) fn mounted_contact(
        &self,
        neuron_index: usize,
        address: RecoveryLaneAddress,
    ) -> Option<RecoveryFluidContactAnatomy> {
        let mounted = self.neuron(neuron_index)?;
        match address {
            RecoveryLaneAddress::Psi(index) => mounted.psi_contacts.get(index).copied(),
            RecoveryLaneAddress::Gate => Some(mounted.gate_contact),
            RecoveryLaneAddress::Plastic => Some(mounted.plastic_contact),
        }
    }
}

pub(crate) fn extend_reached_recovery_fluid_state(
    predecessor_anatomy: &ReachedRecoveryFluidAnatomy,
    successor_anatomy: &ReachedRecoveryFluidAnatomy,
    predecessor: RecoveryFluidReservoirState,
) -> Result<RecoveryFluidReservoirState, RecoveryFluidError> {
    if successor_anatomy.neurons.len() < predecessor_anatomy.neurons.len()
        || predecessor_anatomy
            .neurons
            .iter()
            .zip(&successor_anatomy.neurons)
            .any(|(predecessor_neuron, successor_neuron)| {
                successor_neuron.psi_contacts.len() < predecessor_neuron.psi_contacts.len()
                    || successor_neuron.psi_contacts[..predecessor_neuron.psi_contacts.len()]
                        != predecessor_neuron.psi_contacts[..]
                    || successor_neuron.gate_contact != predecessor_neuron.gate_contact
                    || successor_neuron.plastic_contact != predecessor_neuron.plastic_contact
            })
    {
        return Err(RecoveryFluidError::AnatomyWidth);
    }
    let predecessor_capacity = predecessor_anatomy.reservoir.capacities();
    let successor_capacity = successor_anatomy.reservoir.capacities();
    let predecessor_state = predecessor.physical_parts();
    if successor_capacity.0.checked_cmp(predecessor_capacity.0)? == Ordering::Less
        || successor_capacity.1.checked_cmp(predecessor_capacity.1)? == Ordering::Less
        || successor_capacity.2.checked_cmp(predecessor_capacity.2)? == Ordering::Less
    {
        return Err(RecoveryFluidError::AnatomyWidth);
    }
    // Growing anatomy creates empty capacity, never energy.
    RecoveryFluidReservoirState::new(
        successor_anatomy.reservoir,
        predecessor_state.0,
        predecessor_state.1,
        predecessor_state.2,
    )
}

/// Carry one reservoir across a one-way expansion of already-mounted recovery
/// contacts. Existing fuel, spent material, and heat remain exact; only the
/// newly represented contact capacity contributes virgin fuel. No history or
/// occurrence is copied.
pub(crate) fn expand_reached_recovery_fluid_state(
    predecessor_anatomy: &ReachedRecoveryFluidAnatomy,
    successor_anatomy: &ReachedRecoveryFluidAnatomy,
    predecessor: RecoveryFluidReservoirState,
) -> Result<RecoveryFluidReservoirState, RecoveryFluidError> {
    if predecessor_anatomy.neurons.len() != successor_anatomy.neurons.len() {
        return Err(RecoveryFluidError::AnatomyWidth);
    }
    for (predecessor_neuron, successor_neuron) in predecessor_anatomy
        .neurons
        .iter()
        .zip(&successor_anatomy.neurons)
    {
        if predecessor_neuron.psi_contacts != successor_neuron.psi_contacts
            || !contact_is_componentwise_extension(
                predecessor_neuron.gate_contact,
                successor_neuron.gate_contact,
            )
            || !contact_is_componentwise_extension(
                predecessor_neuron.plastic_contact,
                successor_neuron.plastic_contact,
            )
        {
            return Err(RecoveryFluidError::AnatomyWidth);
        }
    }
    let predecessor_capacity = predecessor_anatomy.reservoir.capacities();
    let successor_capacity = successor_anatomy.reservoir.capacities();
    if successor_capacity.0.checked_cmp(predecessor_capacity.0)? == Ordering::Less
        || successor_capacity.1.checked_cmp(predecessor_capacity.1)? == Ordering::Less
        || successor_capacity.2.checked_cmp(predecessor_capacity.2)? == Ordering::Less
    {
        return Err(RecoveryFluidError::AnatomyWidth);
    }
    let (available, spent, thermal) = predecessor.physical_parts();
    RecoveryFluidReservoirState::new(successor_anatomy.reservoir, available, spent, thermal)
}

fn contact_is_componentwise_extension(
    predecessor: RecoveryFluidContactAnatomy,
    successor: RecoveryFluidContactAnatomy,
) -> bool {
    let predecessor = predecessor.parts();
    let successor = successor.parts();
    if predecessor.0 == 0 || predecessor.1 == 0 || predecessor.2 == 0 || predecessor.3 == 0 {
        return false;
    }
    if successor.0 % predecessor.0 != 0
        || successor.1 % predecessor.1 != 0
        || successor.2 % predecessor.2 != 0
        || successor.3 % predecessor.3 != 0
    {
        return false;
    }
    let scale = successor.0 / predecessor.0;
    scale != 0
        && successor.1 / predecessor.1 == scale
        && successor.2 / predecessor.2 == scale
        && successor.3 / predecessor.3 == scale
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

fn accumulate_contact_energy(
    neuron: &NeuronPhysicalAnatomy,
    address: RecoveryLaneAddress,
    contact: RecoveryFluidContactAnatomy,
    energy: &mut ExactRational,
    minimum_recovery_energy: &mut Option<ExactRational>,
) -> Result<(), RecoveryFluidError> {
    let lane = neuron
        .recovery_anatomy()
        .lane(address)
        .ok_or(RecoveryFluidError::AnatomyWidth)?;
    let (_, fuel_per_extent, spent_per_extent, heat_per_extent) = lane.stoichiometry();
    let (_, contact_fuel, contact_spent, contact_heat) = contact.parts();
    let extents = contact_fuel / fuel_per_extent;
    if contact_fuel % fuel_per_extent != 0
        || contact_spent / spent_per_extent != extents
        || contact_spent % spent_per_extent != 0
        || contact_heat / heat_per_extent != extents
        || contact_heat % heat_per_extent != 0
    {
        return Err(RecoveryFluidError::MaterialContinuity);
    }
    let energy_per_extent = neuron.recovery_energy_per_extent_zeptojoules(address)?;
    if minimum_recovery_energy
        .map(|minimum| energy_per_extent.checked_cmp(minimum))
        .transpose()?
        .is_none_or(|ordering| ordering == Ordering::Less)
    {
        *minimum_recovery_energy = Some(energy_per_extent);
    }
    let contact_energy = energy_per_extent.checked_mul_unsigned(extents)?;
    *energy = energy.checked_add(contact_energy)?;
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
    energy_per_extent_zeptojoules: ExactRational,
    predecessor_lane: RecoveryLaneState,
    reservoir_anatomy: RecoveryFluidReservoirAnatomy,
    predecessor_reservoir: RecoveryFluidReservoirState,
    contact: RecoveryFluidContactAnatomy,
) -> Result<RecoveryFluidSettlement, RecoveryFluidError> {
    let (lane_fuel, lane_spent, lane_heat) = predecessor_lane.physical_parts();
    let (lane_fuel_capacity, _, _) = lane_anatomy.capacities();
    let (reservoir_available, reservoir_spent, reservoir_thermal) =
        predecessor_reservoir.physical_parts();
    RecoveryFluidReservoirState::new(
        reservoir_anatomy,
        reservoir_available,
        reservoir_spent,
        reservoir_thermal,
    )?;
    if energy_per_extent_zeptojoules.checked_cmp(ExactRational::integer(0))? != Ordering::Greater {
        return Err(RecoveryFluidError::MaterialContinuity);
    }
    let (_, fuel_per_extent, spent_per_extent, heat_per_extent) = lane_anatomy.stoichiometry();
    let mut inward_extent = (contact.fuel_inward_capacity_per_interval / fuel_per_extent)
        .min((lane_fuel_capacity - lane_fuel) / fuel_per_extent)
        .min(whole_extents_carried(
            reservoir_available,
            energy_per_extent_zeptojoules,
        )?);
    let mut outward_spent_extent = (contact.spent_outward_capacity_per_interval / spent_per_extent)
        .min(lane_spent / spent_per_extent)
        .min(whole_extents_carried_difference(
            reservoir_anatomy.spent_energy_capacity_zeptojoules,
            reservoir_spent,
            energy_per_extent_zeptojoules,
        )?);
    let mut outward_heat_extent = (contact.heat_outward_capacity_per_interval / heat_per_extent)
        .min(lane_heat / heat_per_extent)
        .min(whole_extents_carried_difference(
            reservoir_anatomy.thermal_energy_capacity_zeptojoules,
            reservoir_thermal,
            energy_per_extent_zeptojoules,
        )?);
    if !representable_reservoir_change(
        reservoir_available,
        energy_per_extent_zeptojoules,
        inward_extent,
        true,
    ) {
        inward_extent = 0;
    }
    if !representable_reservoir_change(
        reservoir_spent,
        energy_per_extent_zeptojoules,
        outward_spent_extent,
        false,
    ) {
        outward_spent_extent = 0;
    }
    if !representable_reservoir_change(
        reservoir_thermal,
        energy_per_extent_zeptojoules,
        outward_heat_extent,
        false,
    ) {
        outward_heat_extent = 0;
    }
    let inward_fuel = inward_extent
        .checked_mul(fuel_per_extent)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    let outward_spent = outward_spent_extent
        .checked_mul(spent_per_extent)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    let outward_heat = outward_heat_extent
        .checked_mul(heat_per_extent)
        .ok_or(RecoveryFluidError::ArithmeticWidth)?;
    let inward_energy = energy_per_extent_zeptojoules.checked_mul_unsigned(inward_extent)?;
    let spent_energy = energy_per_extent_zeptojoules.checked_mul_unsigned(outward_spent_extent)?;
    let thermal_energy = energy_per_extent_zeptojoules.checked_mul_unsigned(outward_heat_extent)?;
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
        wide_sub(reservoir_available, inward_energy)?,
        wide_add(reservoir_spent, spent_energy)?,
        wide_add(reservoir_thermal, thermal_energy)?,
    )?;
    Ok(RecoveryFluidSettlement {
        successor_lane,
        successor_reservoir,
        inward_fuel_quanta: inward_fuel,
        outward_spent_quanta: outward_spent,
        outward_heat_quanta: outward_heat,
    })
}

pub(crate) fn whole_extents_carried(
    energy: ExactRational,
    energy_per_extent: ExactRational,
) -> Result<u128, RecoveryFluidError> {
    whole_extents_carried_wide(wide_rational(energy), energy_per_extent)
}

pub(crate) fn whole_extents_carried_difference(
    capacity: ExactRational,
    occupied: ExactRational,
    energy_per_extent: ExactRational,
) -> Result<u128, RecoveryFluidError> {
    whole_extents_carried_wide(
        wide_rational(capacity) - wide_rational(occupied),
        energy_per_extent,
    )
}

fn whole_extents_carried_wide(
    energy: BigRational,
    energy_per_extent: ExactRational,
) -> Result<u128, RecoveryFluidError> {
    if energy < BigRational::from_integer(BigInt::from(0))
        || wide_rational(energy_per_extent) <= BigRational::from_integer(BigInt::from(0))
    {
        return Err(RecoveryFluidError::MaterialContinuity);
    }
    let whole_extents = (energy / wide_rational(energy_per_extent)).to_integer();
    // Reaction extent is represented by u128 everywhere downstream.  More
    // carried energy than that is not an arithmetic failure: it means this
    // reservoir is not the limiting material.  The lane and contact minima
    // below still choose the exact, representable local extent.
    Ok(match whole_extents.to_u128() {
        Some(value) => value,
        None => u128::MAX,
    })
}

fn representable_reservoir_change(
    predecessor: ExactRational,
    energy_per_extent: ExactRational,
    extent: u128,
    subtract: bool,
) -> bool {
    let change = wide_rational(energy_per_extent) * BigRational::from_integer(BigInt::from(extent));
    let successor = if subtract {
        wide_rational(predecessor) - change
    } else {
        wide_rational(predecessor) + change
    };
    narrow_rational(successor).is_ok()
}

pub(crate) fn recovery_exchange_extent_is_representable(
    reservoir: RecoveryFluidReservoirState,
    energy_per_extent: ExactRational,
    extent: u128,
) -> bool {
    let (available, spent, thermal) = reservoir.physical_parts();
    representable_reservoir_change(available, energy_per_extent, extent, true)
        && representable_reservoir_change(spent, energy_per_extent, extent, false)
        && representable_reservoir_change(thermal, energy_per_extent, extent, false)
}

pub(crate) fn settle_resident_gate_recovery_before_interval(
    recovery_anatomy: &ReachedRecoveryFluidAnatomy,
    neuron_index: usize,
    neuron_anatomy: &NeuronPhysicalAnatomy,
    predecessor_neuron: &NeuronPhysicalState,
    gate_work: &GateWorkOccurrence,
    prepared_psi: &PsiSettlement,
    predecessor_reservoir: RecoveryFluidReservoirState,
) -> Result<ResidentGateRecoverySettlement, RecoveryFluidError> {
    let mounted = recovery_anatomy
        .neuron(neuron_index)
        .ok_or(RecoveryFluidError::AnatomyWidth)?;
    if mounted.psi_contacts.len() != neuron_anatomy.psi_ring_count() {
        return Err(RecoveryFluidError::AnatomyWidth);
    }
    let required_extent = required_gate_recovery_extent_for_interval_with_psi(
        neuron_anatomy,
        predecessor_neuron,
        gate_work,
        prepared_psi,
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
    let (reservoir_available_capacity, reservoir_spent_capacity, reservoir_thermal_capacity) =
        recovery_anatomy.reservoir.capacities();
    let (reservoir_available, reservoir_spent, reservoir_thermal) =
        predecessor_reservoir.physical_parts();
    if lane_fuel > lane_fuel_capacity
        || lane_spent > lane_spent_capacity
        || lane_heat > lane_heat_capacity
        || wide_rational(reservoir_available) > wide_rational(reservoir_available_capacity)
        || wide_rational(reservoir_spent) > wide_rational(reservoir_spent_capacity)
        || wide_rational(reservoir_thermal) > wide_rational(reservoir_thermal_capacity)
    {
        return Err(RecoveryFluidError::StateOutsideAnatomy);
    }
    let contact = mounted.gate_contact;
    let energy_per_extent =
        neuron_anatomy.recovery_energy_per_extent_zeptojoules(RecoveryLaneAddress::Gate)?;
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
        .min(whole_extents_carried(
            reservoir_available,
            energy_per_extent,
        )?)
        .min(whole_extents_carried_difference(
            reservoir_spent_capacity,
            reservoir_spent,
            energy_per_extent,
        )?)
        .min(whole_extents_carried_difference(
            reservoir_thermal_capacity,
            reservoir_thermal,
            energy_per_extent,
        )?)
        .min(contact.catalyst_capacity_per_interval / catalyst_per_extent)
        .min(contact.fuel_inward_capacity_per_interval / fuel_per_extent)
        .min(contact.spent_outward_capacity_per_interval / spent_per_extent)
        .min(contact.heat_outward_capacity_per_interval / heat_per_extent);
    let settled_extent = if recovery_exchange_extent_is_representable(
        predecessor_reservoir,
        energy_per_extent,
        settled_extent,
    ) {
        settled_extent
    } else {
        0
    };
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
        energy_per_extent,
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
    push_exact_three(&mut out, anatomy.reservoir.capacities());
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
    let magic = reader.take(ANATOMY_MAGIC.len())?;
    if magic != ANATOMY_MAGIC && magic != LEGACY_ANATOMY_MAGIC {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    let legacy_capacities = if magic == LEGACY_ANATOMY_MAGIC {
        Some((reader.u128()?, reader.u128()?, reader.u128()?))
    } else {
        None
    };
    let declared_reservoir = if legacy_capacities.is_none() {
        Some(RecoveryFluidReservoirAnatomy::new(
            reader.exact_rational()?,
            reader.exact_rational()?,
            reader.exact_rational()?,
        )?)
    } else {
        None
    };
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
    let contacts = ReachedRecoveryFluidAnatomy {
        reservoir: RecoveryFluidReservoirAnatomy::new(
            ExactRational::integer(0),
            ExactRational::integer(0),
            ExactRational::integer(0),
        )?,
        neurons: mounted.into_boxed_slice(),
        minimum_recovery_energy_per_extent_zeptojoules: ExactRational::integer(0),
    };
    let derived = ReachedRecoveryFluidAnatomy::derive(neurons)?;
    if contacts.neurons != derived.neurons {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    if let Some(declared) = declared_reservoir {
        if declared != derived.reservoir {
            return Err(RecoveryFluidError::InvalidEncoding);
        }
    } else if legacy_capacities != Some(legacy_raw_capacities(&derived)?) {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    Ok(derived)
}

pub(crate) fn encode_reached_recovery_fluid_state(
    anatomy: &ReachedRecoveryFluidAnatomy,
    state: RecoveryFluidReservoirState,
) -> Result<Vec<u8>, RecoveryFluidError> {
    RecoveryFluidReservoirState::new(
        anatomy.reservoir,
        state.available_energy_zeptojoules,
        state.spent_energy_zeptojoules,
        state.thermal_energy_zeptojoules,
    )?;
    let mut out = Vec::new();
    out.extend_from_slice(STATE_MAGIC);
    push_exact_three(&mut out, state.physical_parts());
    Ok(out)
}

pub(crate) fn decode_reached_recovery_fluid_state(
    encoded: &[u8],
    anatomy: &ReachedRecoveryFluidAnatomy,
) -> Result<RecoveryFluidReservoirState, RecoveryFluidError> {
    let mut reader = Reader::new(encoded);
    let magic = reader.take(STATE_MAGIC.len())?;
    if magic != STATE_MAGIC && magic != LEGACY_STATE_MAGIC {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    let state = if magic == STATE_MAGIC {
        RecoveryFluidReservoirState::new(
            anatomy.reservoir,
            reader.exact_rational()?,
            reader.exact_rational()?,
            reader.exact_rational()?,
        )?
    } else {
        let legacy = (reader.u128()?, reader.u128()?, reader.u128()?);
        let legacy_capacity = legacy_raw_capacities(anatomy)?;
        if legacy != (0, legacy_capacity.1, legacy_capacity.2) {
            return Err(RecoveryFluidError::InvalidEncoding);
        }
        let capacity = anatomy.reservoir.capacities();
        RecoveryFluidReservoirState::new(
            anatomy.reservoir,
            ExactRational::integer(0),
            capacity.1,
            capacity.2,
        )?
    };
    if !reader.finished() {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    Ok(state)
}

fn push_exact_three(out: &mut Vec<u8>, values: (ExactRational, ExactRational, ExactRational)) {
    for value in [values.0, values.1, values.2] {
        let (numerator, denominator) = value.parts();
        out.extend_from_slice(&numerator.to_le_bytes());
        out.extend_from_slice(&denominator.to_le_bytes());
    }
}

fn legacy_raw_capacities(
    anatomy: &ReachedRecoveryFluidAnatomy,
) -> Result<(u128, u128, u128), RecoveryFluidError> {
    anatomy
        .neurons
        .iter()
        .try_fold((0_u128, 0_u128, 0_u128), |mut total, neuron| {
            for contact in neuron
                .psi_contacts
                .iter()
                .chain([&neuron.gate_contact, &neuron.plastic_contact])
            {
                let parts = contact.parts();
                total.0 = total
                    .0
                    .checked_add(parts.1)
                    .ok_or(RecoveryFluidError::ArithmeticWidth)?;
                total.1 = total
                    .1
                    .checked_add(parts.2)
                    .ok_or(RecoveryFluidError::ArithmeticWidth)?;
                total.2 = total
                    .2
                    .checked_add(parts.3)
                    .ok_or(RecoveryFluidError::ArithmeticWidth)?;
            }
            Ok(total)
        })
}

pub(crate) fn encode_legacy_reached_recovery_fluid_anatomy(
    anatomy: &ReachedRecoveryFluidAnatomy,
) -> Result<Vec<u8>, RecoveryFluidError> {
    let mut out = Vec::new();
    out.extend_from_slice(LEGACY_ANATOMY_MAGIC);
    let capacities = legacy_raw_capacities(anatomy)?;
    for value in [capacities.0, capacities.1, capacities.2] {
        out.extend_from_slice(&value.to_le_bytes());
    }
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

pub(crate) fn is_legacy_recovery_fluid_state(encoded: &[u8]) -> bool {
    encoded.get(..LEGACY_STATE_MAGIC.len()) == Some(LEGACY_STATE_MAGIC)
}

/// Reconstruct the single retired reservoir endpoint that the production body
/// may carry during the one-way exact-energy cutover.  No partial or energized
/// legacy state can be authored through this boundary.
pub(crate) fn encode_legacy_exhausted_recovery_fluid_state(
    anatomy: &ReachedRecoveryFluidAnatomy,
    state: RecoveryFluidReservoirState,
) -> Result<Vec<u8>, RecoveryFluidError> {
    let raw_capacity = legacy_raw_capacities(anatomy)?;
    let exact_capacity = anatomy.reservoir.capacities();
    if state.physical_parts()
        != (
            ExactRational::integer(0),
            exact_capacity.1,
            exact_capacity.2,
        )
    {
        return Err(RecoveryFluidError::InvalidEncoding);
    }
    let mut out = Vec::from(LEGACY_STATE_MAGIC.as_slice());
    for value in [0_u128, raw_capacity.1, raw_capacity.2] {
        out.extend_from_slice(&value.to_le_bytes());
    }
    Ok(out)
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

    fn exact_rational(&mut self) -> Result<ExactRational, RecoveryFluidError> {
        let numerator = i128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| RecoveryFluidError::InvalidEncoding)?,
        );
        let denominator = self.u128()?;
        Ok(ExactRational::new(numerator, denominator)?)
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

    fn one_contact_fluid_anatomy() -> ReachedRecoveryFluidAnatomy {
        let quantum = ExactRational::new(1, 8).unwrap();
        let contact = RecoveryFluidContactAnatomy::new(1, 1, 1, 1).unwrap();
        ReachedRecoveryFluidAnatomy {
            reservoir: RecoveryFluidReservoirAnatomy::new(quantum, quantum, quantum).unwrap(),
            neurons: vec![RecoveryFluidNeuronAnatomy {
                psi_contacts: Box::new([]),
                gate_contact: contact,
                plastic_contact: contact,
            }]
            .into_boxed_slice(),
            minimum_recovery_energy_per_extent_zeptojoules: quantum,
        }
    }

    #[test]
    fn reached_fluid_contact_conserves_fuel_spent_and_heat_exactly() {
        let lane_anatomy = lane_anatomy();
        let lane = RecoveryLaneState::from_physical_parts(lane_anatomy, 0, 1, 1).unwrap();
        let quantum = ExactRational::new(1, 16).unwrap();
        let reservoir_anatomy =
            RecoveryFluidReservoirAnatomy::new(quantum, quantum, quantum).unwrap();
        let reservoir = RecoveryFluidReservoirState::new(
            reservoir_anatomy,
            quantum,
            ExactRational::integer(0),
            ExactRational::integer(0),
        )
        .unwrap();
        let settled = settle_recovery_fluid_contact(
            lane_anatomy,
            quantum,
            lane,
            reservoir_anatomy,
            reservoir,
            RecoveryFluidContactAnatomy::new(1, 1, 1, 1).unwrap(),
        )
        .unwrap();
        assert_eq!(settled.successor_lane.physical_parts(), (1, 0, 0));
        assert_eq!(
            settled.successor_reservoir.physical_parts(),
            (ExactRational::integer(0), quantum, quantum)
        );
        assert_eq!(settled.inward_fuel_quanta, 1);
        assert_eq!(settled.outward_spent_quanta, 1);
        assert_eq!(settled.outward_heat_quanta, 1);
        assert_eq!(reservoir.physical_parts().0, quantum);
        assert_eq!(settled.successor_reservoir.physical_parts().1, quantum);
        assert_eq!(settled.successor_reservoir.physical_parts().2, quantum);
    }

    #[test]
    fn reservoir_validation_does_not_refuse_a_finite_mixed_denominator() {
        let capacity = ExactRational::integer(i128::MAX);
        let finite = ExactRational::new(i128::MAX - 2, 3).unwrap();
        assert_eq!(
            finite.checked_cmp(capacity),
            Err(ExactRationalError::ArithmeticWidth)
        );

        let anatomy = RecoveryFluidReservoirAnatomy::new(capacity, capacity, capacity).unwrap();
        let state = RecoveryFluidReservoirState::new(anatomy, finite, finite, finite).unwrap();
        assert_eq!(state.physical_parts(), (finite, finite, finite));
    }

    #[test]
    fn unrepresentable_spent_transfer_stalls_without_rejecting_or_losing_material() {
        let lane_anatomy = lane_anatomy();
        let lane = RecoveryLaneState::from_physical_parts(lane_anatomy, 0, 1, 1).unwrap();
        let quantum = ExactRational::new(9, 2).unwrap();
        let production_spent = ExactRational::new(
            170136804081459245624562613934865220851,
            2336099068760000000000000000000000,
        )
        .unwrap();
        assert!(wide_add(production_spent, quantum).is_err());
        let capacity = ExactRational::integer(i128::MAX);
        let reservoir_anatomy =
            RecoveryFluidReservoirAnatomy::new(capacity, capacity, capacity).unwrap();
        let reservoir = RecoveryFluidReservoirState::new(
            reservoir_anatomy,
            ExactRational::integer(0),
            production_spent,
            ExactRational::integer(0),
        )
        .unwrap();
        let settled = settle_recovery_fluid_contact(
            lane_anatomy,
            quantum,
            lane,
            reservoir_anatomy,
            reservoir,
            RecoveryFluidContactAnatomy::new(1, 1, 1, 1).unwrap(),
        )
        .unwrap();
        assert_eq!(settled.outward_spent_quanta, 0);
        assert_eq!(settled.outward_heat_quanta, 1);
        assert_eq!(settled.successor_lane.physical_parts(), (0, 1, 0));
        assert_eq!(
            settled.successor_reservoir.physical_parts(),
            (ExactRational::integer(0), production_spent, quantum)
        );
    }

    #[test]
    fn unrepresentable_powered_exchange_stalls_without_refusing_the_interval() {
        let production_value = ExactRational::new(
            170136804081459245624562613934865220851,
            2336099068760000000000000000000000,
        )
        .unwrap();
        let quantum = ExactRational::new(9, 2).unwrap();
        let capacity = ExactRational::integer(i128::MAX);
        let anatomy = RecoveryFluidReservoirAnatomy::new(capacity, capacity, capacity).unwrap();
        let predecessor = RecoveryFluidReservoirState::new(
            anatomy,
            production_value,
            quantum,
            ExactRational::integer(0),
        )
        .unwrap();
        let settled = settle_powered_environment_exchange(anatomy, predecessor, quantum).unwrap();
        assert_eq!(
            settled.delivered_energy_zeptojoules,
            ExactRational::integer(0)
        );
        assert_eq!(settled.exported_heat_zeptojoules, ExactRational::integer(0));
        assert_eq!(settled.successor, predecessor);
    }

    #[test]
    fn legacy_exhausted_endpoint_repairs_to_exact_energy_once() {
        let anatomy = one_contact_fluid_anatomy();
        let mut encoded = Vec::from(LEGACY_STATE_MAGIC.as_slice());
        for value in [0_u128, 2, 2] {
            encoded.extend_from_slice(&value.to_le_bytes());
        }
        let repaired = decode_reached_recovery_fluid_state(&encoded, &anatomy).unwrap();
        assert_eq!(
            repaired.physical_parts(),
            (
                ExactRational::integer(0),
                ExactRational::new(1, 8).unwrap(),
                ExactRational::new(1, 8).unwrap(),
            )
        );
        assert!(encode_reached_recovery_fluid_state(&anatomy, repaired)
            .unwrap()
            .starts_with(STATE_MAGIC));
    }

    #[test]
    fn partial_legacy_mixed_unit_reservoir_is_refused() {
        let anatomy = one_contact_fluid_anatomy();
        let mut encoded = Vec::from(LEGACY_STATE_MAGIC.as_slice());
        for value in [1_u128, 1, 1] {
            encoded.extend_from_slice(&value.to_le_bytes());
        }
        assert_eq!(
            decode_reached_recovery_fluid_state(&encoded, &anatomy),
            Err(RecoveryFluidError::InvalidEncoding)
        );
    }
}
