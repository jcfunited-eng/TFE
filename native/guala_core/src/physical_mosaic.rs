//! Physical mosaic admission over the definitive reached-neuron cohort.
//!
//! Learned structure remains in each neuron's retained plastic state and the
//! cohort's sparse physical contacts.  This boundary only admits a compact
//! reference to that distributed structure after an original lived settlement,
//! a later proper partial-cue physical recurrence proves the relationship.
//! Unlearned controls and cold equality remain external falsification tests,
//! not organism work. It stores no field
//! body, media, meaning, score, answer, transcript, receipt, owner, or history.

use crate::complete_neuron::{
    retained_physical_state_coordinate, ExactPhysicalStateDelta, ExactSignedDelta,
    PhysicalStateCoordinate, PhysicalStateDeltaEntry, SparsePhysicalStateDelta,
};
use crate::exact_rational::ExactRational;
use crate::reached_neuron_cohort::{
    ReachedCohortAnatomy, ReachedCohortPostExperienceSettlement, ReachedCohortRecurrenceSettlement,
};
use std::collections::{BTreeMap, VecDeque};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PhysicalMosaicError {
    WidthMismatch,
    FewerThanThreeRetainedFractals,
    OriginalRelationNotConnected,
    CueIsEmpty,
    CueIsNotPartial,
    CueOutsideFormation,
    RecurrenceDidNotReachFormation,
    RecurrenceDidNotChangeEveryMember,
    RecurrenceDidNotAlterFormation,
    InvalidRetainedFractal,
}

pub(crate) type StableNeuronLineage = [u8; 16];

/// Physical origin of the latest retained recurrence witness.  This is not a
/// semantic label: it distinguishes work entering through measured external
/// receptors from work arising inside the organism during exact metabolic
/// settlement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PhysicalMosaicRecurrenceOrigin {
    ExternallyObserved,
    InternallySimulated,
}

impl PhysicalMosaicRecurrenceOrigin {
    pub(crate) fn as_str(self) -> &'static str {
        match self {
            Self::ExternallyObserved => "externally_observed",
            Self::InternallySimulated => "internally_simulated",
        }
    }
}

/// A physical bond is identified by its stable endpoint lineages.  The
/// parallel ordinal distinguishes multiple real contacts between the same two
/// neurons without depending on a compartment-local contact index.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct StablePhysicalBondReference {
    left: StableNeuronLineage,
    right: StableNeuronLineage,
    parallel_ordinal: u32,
}

impl StablePhysicalBondReference {
    pub(crate) fn new(
        first: StableNeuronLineage,
        second: StableNeuronLineage,
        parallel_ordinal: u32,
    ) -> Option<Self> {
        if first == second {
            return None;
        }
        let (left, right) = if first < second {
            (first, second)
        } else {
            (second, first)
        };
        Some(Self {
            left,
            right,
            parallel_ordinal,
        })
    }

    pub(crate) fn endpoints(self) -> (StableNeuronLineage, StableNeuronLineage) {
        (self.left, self.right)
    }

    pub(crate) fn parallel_ordinal(self) -> u32 {
        self.parallel_ordinal
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct AdmittedPhysicalMosaic {
    original_only: bool,
    exact_pattern_recognition: bool,
    member_lineages: Box<[StableNeuronLineage]>,
    retained_fractals: Box<[SparsePhysicalStateDelta]>,
    retained_excitation_zeptojoules: Box<[ExactRational]>,
    original_bonds: Box<[StablePhysicalBondReference]>,
    recurrence_bonds: Box<[StablePhysicalBondReference]>,
    partial_cue_lineages: Box<[StableNeuronLineage]>,
    recurrence_origin: Option<PhysicalMosaicRecurrenceOrigin>,
}

impl AdmittedPhysicalMosaic {
    pub(crate) fn is_original_only(&self) -> bool {
        self.original_only
    }

    pub(crate) fn member_lineages(&self) -> &[StableNeuronLineage] {
        &self.member_lineages
    }

    pub(crate) fn retained_fractals(&self) -> &[SparsePhysicalStateDelta] {
        &self.retained_fractals
    }

    pub(crate) fn original_bonds(&self) -> &[StablePhysicalBondReference] {
        &self.original_bonds
    }

    pub(crate) fn recurrence_bonds(&self) -> &[StablePhysicalBondReference] {
        &self.recurrence_bonds
    }

    pub(crate) fn partial_cue_lineages(&self) -> &[StableNeuronLineage] {
        &self.partial_cue_lineages
    }

    pub(crate) fn recurrence_origin(&self) -> Option<PhysicalMosaicRecurrenceOrigin> {
        self.recurrence_origin
    }

    /// The retained physical structure that gives this formation continuity.
    /// Later cue and recurrence paths are evidence that this structure was
    /// reached again; they are not the structure's identity.  Two formations
    /// may therefore use the same neurons while retaining different exact
    /// neuronal changes, just as the same biological neurons participate in
    /// many memories.
    pub(crate) fn same_retained_structure(&self, other: &Self) -> bool {
        self.member_lineages == other.member_lineages
            && self.retained_fractals == other.retained_fractals
            && self.original_bonds == other.original_bonds
    }

    /// Resolve this retained formation into the local cohort. A mosaic owned
    /// by another cohort is simply absent here; ambiguous local lineage is an
    /// invalid anatomy rather than something cognition may guess through.
    fn local_member_indices(
        &self,
        anatomy: &ReachedCohortAnatomy,
    ) -> Result<Option<Vec<usize>>, PhysicalMosaicError> {
        let mut indices = Vec::with_capacity(self.member_lineages.len());
        for lineage in &self.member_lineages {
            let mut matches = anatomy
                .neuron_lineages()
                .iter()
                .enumerate()
                .filter_map(|(index, candidate)| (candidate == lineage).then_some(index));
            let Some(index) = matches.next() else {
                return Ok(None);
            };
            if matches.next().is_some() {
                return Err(PhysicalMosaicError::WidthMismatch);
            }
            indices.push(index);
        }
        Ok(Some(indices))
    }

    /// True only when current physical motion has reassembled this retained
    /// formation from either an external proper partial cue or an internally
    /// originated physical activation. Internal recovery may move the whole
    /// formation; external work may not call a complete replay a partial cue.
    /// The cue, member motion, and conducting path are transient physics; no
    /// name, semantic key, score, member-set identity, or stored cohort
    /// snapshot participates.
    pub(crate) fn reassembled_by_current_flow(
        &self,
        anatomy: &ReachedCohortAnatomy,
        cue_neurons: &[bool],
        current_retained_fractals: &[Option<SparsePhysicalStateDelta>],
        active_contacts: &[bool],
        internally_originated: bool,
    ) -> Result<bool, PhysicalMosaicError> {
        if cue_neurons.len() != anatomy.neuron_count()
            || current_retained_fractals.len() != anatomy.neuron_count()
            || active_contacts.len() != anatomy.contact_count()
        {
            return Err(PhysicalMosaicError::WidthMismatch);
        }
        if !self.exact_pattern_recognition {
            return Ok(false);
        }
        let Some(members) = self.local_member_indices(anatomy)? else {
            return Ok(false);
        };
        let member_mask = mask(anatomy.neuron_count(), &members)?;
        let cue = cue_neurons
            .iter()
            .enumerate()
            .filter_map(|(index, perturbed)| perturbed.then_some(index))
            .collect::<Vec<_>>();
        if cue.is_empty()
            || (!internally_originated && cue.len() >= members.len())
            || cue.len() > members.len()
            || cue.iter().any(|index| !member_mask[*index])
            || members.iter().enumerate().any(|(member_ordinal, index)| {
                current_retained_fractals[*index].as_ref()
                    != self.retained_fractals.get(member_ordinal)
            })
        {
            return Ok(false);
        }
        let endpoints = anatomy.contact_endpoints().collect::<Vec<_>>();
        Ok(connected_members(
            anatomy.neuron_count(),
            &members,
            &member_mask,
            &endpoints,
            active_contacts,
            &cue,
        ))
    }

    pub(crate) fn carries_only_retained_neuron_structure(&self) -> bool {
        !self.original_only
            && self.exact_pattern_recognition
            && self.retained_excitation_zeptojoules.is_empty()
            && self.retained_fractals.iter().all(|fractal| {
                !fractal.entries().is_empty()
                    && fractal
                        .entries()
                        .iter()
                        .all(|entry| retained_physical_state_coordinate(entry.coordinate()))
            })
    }

    pub(crate) fn carries_retained_original_structure(&self) -> bool {
        (self.original_only || self.exact_pattern_recognition)
            && self.retained_excitation_zeptojoules.is_empty()
            && self.retained_fractals.iter().all(|fractal| {
                !fractal.entries().is_empty()
                    && fractal
                        .entries()
                        .iter()
                        .all(|entry| retained_physical_state_coordinate(entry.coordinate()))
            })
    }

    pub(crate) fn resident_bytes(&self) -> Option<usize> {
        core::mem::size_of::<Self>()
            .checked_add(
                self.member_lineages
                    .len()
                    .checked_mul(core::mem::size_of::<StableNeuronLineage>())?,
            )?
            .checked_add(
                self.retained_fractals
                    .iter()
                    .try_fold(0usize, |total, fractal| {
                        total.checked_add(fractal.resident_bytes()?)
                    })?,
            )?
            .checked_add(
                self.retained_excitation_zeptojoules
                    .len()
                    .checked_mul(core::mem::size_of::<ExactRational>())?,
            )?
            .checked_add(
                self.original_bonds
                    .len()
                    .checked_mul(core::mem::size_of::<StablePhysicalBondReference>())?,
            )?
            .checked_add(
                self.recurrence_bonds
                    .len()
                    .checked_mul(core::mem::size_of::<StablePhysicalBondReference>())?,
            )?
            .checked_add(
                self.partial_cue_lineages
                    .len()
                    .checked_mul(core::mem::size_of::<StableNeuronLineage>())?,
            )
    }
}

#[cfg(test)]
impl AdmittedPhysicalMosaic {
    /// Test-only synthesis for the structural-identity (R1) law tests in the
    /// resident cognitive formation boundary.  Organism admission always
    /// runs through `admit_physical_mosaic`; this exists so the update-vs-new
    /// boundary can be exercised against explicit member and bond structures.
    pub(crate) fn from_parts_for_tests(
        member_lineages: Vec<StableNeuronLineage>,
        retained_fractals: Vec<SparsePhysicalStateDelta>,
        original_bonds: Vec<StablePhysicalBondReference>,
        recurrence_bonds: Vec<StablePhysicalBondReference>,
        partial_cue_lineages: Vec<StableNeuronLineage>,
    ) -> Self {
        Self {
            original_only: false,
            exact_pattern_recognition: true,
            member_lineages: member_lineages.into_boxed_slice(),
            retained_fractals: retained_fractals.into_boxed_slice(),
            retained_excitation_zeptojoules: Box::new([]),
            original_bonds: original_bonds.into_boxed_slice(),
            recurrence_bonds: recurrence_bonds.into_boxed_slice(),
            partial_cue_lineages: partial_cue_lineages.into_boxed_slice(),
            recurrence_origin: Some(PhysicalMosaicRecurrenceOrigin::ExternallyObserved),
        }
    }
}

/// Retain one organism-wide original from exact neuronal impressions and the
/// sparse bonds that physically carried this occurrence.  This is not yet a
/// recognized mosaic: a later proper partial cue must reassemble the same
/// member structure before `prove_physical_mosaic_recurrence` promotes it.
pub(crate) fn admit_physical_mosaic_original(
    neuron_lineages: &[StableNeuronLineage],
    fractal_anatomies: &[(usize, usize)],
    neuron_fractals: &[Option<SparsePhysicalStateDelta>],
    active_bonds: &[StablePhysicalBondReference],
) -> Result<AdmittedPhysicalMosaic, PhysicalMosaicError> {
    if neuron_lineages.len() != fractal_anatomies.len()
        || neuron_lineages.len() != neuron_fractals.len()
    {
        return Err(PhysicalMosaicError::WidthMismatch);
    }
    let mut members = neuron_lineages
        .iter()
        .copied()
        .zip(neuron_fractals.iter())
        .zip(fractal_anatomies.iter().copied())
        .filter_map(|((lineage, fractal), anatomy)| {
            fractal
                .as_ref()
                .map(|fractal| (lineage, fractal.clone(), anatomy))
        })
        .collect::<Vec<_>>();
    if members.len() < 3 {
        return Err(PhysicalMosaicError::FewerThanThreeRetainedFractals);
    }
    if members.iter().any(|(_, fractal, (ring_count, maximum))| {
        fractal.entries().is_empty()
            || fractal.entries().len() > *maximum
            || !fractal_coordinates_fit(fractal, *ring_count)
    }) {
        return Err(PhysicalMosaicError::InvalidRetainedFractal);
    }
    members.sort_by_key(|(lineage, _, _)| *lineage);
    if members.windows(2).any(|pair| pair[0].0 == pair[1].0) {
        return Err(PhysicalMosaicError::WidthMismatch);
    }
    let member_lineages = members
        .iter()
        .map(|(lineage, _, _)| *lineage)
        .collect::<Vec<_>>();
    let retained_fractals = members
        .into_iter()
        .map(|(_, fractal, _)| fractal)
        .collect::<Vec<_>>();
    let original_bonds = connecting_bond_witness(neuron_lineages, &member_lineages, active_bonds)
        .ok_or(PhysicalMosaicError::OriginalRelationNotConnected)?;
    Ok(AdmittedPhysicalMosaic {
        original_only: true,
        exact_pattern_recognition: false,
        member_lineages: member_lineages.into_boxed_slice(),
        retained_fractals: retained_fractals.into_boxed_slice(),
        retained_excitation_zeptojoules: Box::new([]),
        original_bonds: original_bonds.into_boxed_slice(),
        recurrence_bonds: Box::new([]),
        partial_cue_lineages: Box::new([]),
        recurrence_origin: None,
    })
}

fn current_recurrence_witness(
    retained: &AdmittedPhysicalMosaic,
    current_physical_deltas: &[(StableNeuronLineage, SparsePhysicalStateDelta)],
    active_bonds: &[StablePhysicalBondReference],
    partial_cue_lineages: &[StableNeuronLineage],
    internally_originated: bool,
    require_retained_fractal_equality: bool,
) -> Result<(Vec<StablePhysicalBondReference>, Vec<StableNeuronLineage>), PhysicalMosaicError> {
    if current_physical_deltas
        .windows(2)
        .any(|pair| pair[0].0 >= pair[1].0)
        || retained
            .member_lineages
            .iter()
            .zip(retained.retained_fractals.iter())
            .any(|(lineage, retained_fractal)| {
                current_physical_deltas
                    .binary_search_by_key(lineage, |(candidate, _)| *candidate)
                    .ok()
                    .and_then(|index| current_physical_deltas.get(index))
                    .is_none_or(|(_, current_fractal)| {
                        require_retained_fractal_equality
                            && current_fractal != retained_fractal
                    })
            })
    {
        return Err(PhysicalMosaicError::RecurrenceDidNotChangeEveryMember);
    }
    let mut cue = partial_cue_lineages.to_vec();
    cue.sort_unstable();
    cue.dedup();
    if cue.is_empty() {
        return Err(PhysicalMosaicError::CueIsEmpty);
    }
    if (!internally_originated && cue.len() >= retained.member_lineages.len())
        || cue.len() > retained.member_lineages.len()
    {
        return Err(PhysicalMosaicError::CueIsNotPartial);
    }
    if cue
        .iter()
        .any(|lineage| retained.member_lineages.binary_search(lineage).is_err())
    {
        return Err(PhysicalMosaicError::CueOutsideFormation);
    }
    let mut available_lineages = retained.member_lineages.to_vec();
    for bond in active_bonds {
        let (left, right) = bond.endpoints();
        available_lineages.push(left);
        available_lineages.push(right);
    }
    available_lineages.sort_unstable();
    available_lineages.dedup();
    let recurrence_bonds =
        connecting_bond_witness(&available_lineages, &retained.member_lineages, active_bonds)
            .ok_or(PhysicalMosaicError::RecurrenceDidNotReachFormation)?;
    Ok((recurrence_bonds, cue))
}

/// Promote an organism-wide retained original only when a later proper
/// partial cue and actual sparse contact flow reassemble every member.
pub(crate) fn prove_physical_mosaic_recurrence(
    original: &AdmittedPhysicalMosaic,
    current_physical_deltas: &[(StableNeuronLineage, SparsePhysicalStateDelta)],
    active_bonds: &[StablePhysicalBondReference],
    partial_cue_lineages: &[StableNeuronLineage],
) -> Result<AdmittedPhysicalMosaic, PhysicalMosaicError> {
    prove_physical_mosaic_recurrence_with_origin(
        original,
        current_physical_deltas,
        active_bonds,
        partial_cue_lineages,
        PhysicalMosaicRecurrenceOrigin::ExternallyObserved,
    )
}

pub(crate) fn prove_physical_mosaic_recurrence_with_origin(
    original: &AdmittedPhysicalMosaic,
    current_physical_deltas: &[(StableNeuronLineage, SparsePhysicalStateDelta)],
    active_bonds: &[StablePhysicalBondReference],
    partial_cue_lineages: &[StableNeuronLineage],
    origin: PhysicalMosaicRecurrenceOrigin,
) -> Result<AdmittedPhysicalMosaic, PhysicalMosaicError> {
    if !original.original_only {
        return Err(PhysicalMosaicError::WidthMismatch);
    }
    let (recurrence_bonds, cue) = current_recurrence_witness(
        original,
        current_physical_deltas,
        active_bonds,
        partial_cue_lineages,
        origin == PhysicalMosaicRecurrenceOrigin::InternallySimulated,
        true,
    )?;
    let mut recognized = original.clone();
    recognized.original_only = false;
    recognized.exact_pattern_recognition = true;
    recognized.recurrence_bonds = recurrence_bonds.into_boxed_slice();
    recognized.partial_cue_lineages = cue.into_boxed_slice();
    recognized.recurrence_origin = Some(origin);
    Ok(recognized)
}

/// Replace only the bounded latest recurrence witness when a recognized
/// organism-wide formation is physically reassembled through a different
/// current sparse route or proper partial cue. The original neuronal deltas
/// and original bonds remain unchanged. A repeated identical witness is
/// quiescent at this formation boundary and does not mint a counter or write.
pub(crate) fn alter_physical_mosaic_recurrence(
    retained: &AdmittedPhysicalMosaic,
    current_physical_deltas: &[(StableNeuronLineage, SparsePhysicalStateDelta)],
    active_bonds: &[StablePhysicalBondReference],
    partial_cue_lineages: &[StableNeuronLineage],
) -> Result<AdmittedPhysicalMosaic, PhysicalMosaicError> {
    alter_physical_mosaic_recurrence_with_origin(
        retained,
        current_physical_deltas,
        active_bonds,
        partial_cue_lineages,
        PhysicalMosaicRecurrenceOrigin::ExternallyObserved,
    )
}

pub(crate) fn alter_physical_mosaic_recurrence_with_origin(
    retained: &AdmittedPhysicalMosaic,
    current_physical_deltas: &[(StableNeuronLineage, SparsePhysicalStateDelta)],
    active_bonds: &[StablePhysicalBondReference],
    partial_cue_lineages: &[StableNeuronLineage],
    origin: PhysicalMosaicRecurrenceOrigin,
) -> Result<AdmittedPhysicalMosaic, PhysicalMosaicError> {
    if retained.original_only || !retained.exact_pattern_recognition {
        return Err(PhysicalMosaicError::WidthMismatch);
    }
    let (recurrence_bonds, cue) = current_recurrence_witness(
        retained,
        current_physical_deltas,
        active_bonds,
        partial_cue_lineages,
        origin == PhysicalMosaicRecurrenceOrigin::InternallySimulated,
        true,
    )?;
    if recurrence_bonds.as_slice() == retained.recurrence_bonds.as_ref()
        && cue.as_slice() == retained.partial_cue_lineages.as_ref()
        && retained.recurrence_origin == Some(origin)
    {
        return Err(PhysicalMosaicError::RecurrenceDidNotAlterFormation);
    }
    let mut altered = retained.clone();
    altered.recurrence_bonds = recurrence_bonds.into_boxed_slice();
    altered.partial_cue_lineages = cue.into_boxed_slice();
    altered.recurrence_origin = Some(origin);
    Ok(altered)
}

/// Reassemble an already-recognized formation through its own recurrent cell.
///
/// The caller must first prove that the formation's exact retained layer-9
/// endpoint carried a nonzero current transfer to this cue. That physical
/// formation-specific path replaces byte-for-byte replay of the original
/// interval delta: a living neuron's membrane, recovery, and plastic state may
/// have changed since the original experience. Every retained member must
/// still move now and the current active bonds must still connect the complete
/// retained formation. An original without recurrent-cell authority continues
/// to require exact retained-fractal equality above.
pub(crate) fn alter_recognized_physical_mosaic_recurrence_from_recurrent_flow(
    retained: &AdmittedPhysicalMosaic,
    current_physical_deltas: &[(StableNeuronLineage, SparsePhysicalStateDelta)],
    active_bonds: &[StablePhysicalBondReference],
    partial_cue_lineages: &[StableNeuronLineage],
    origin: PhysicalMosaicRecurrenceOrigin,
) -> Result<AdmittedPhysicalMosaic, PhysicalMosaicError> {
    if retained.original_only || !retained.exact_pattern_recognition {
        return Err(PhysicalMosaicError::WidthMismatch);
    }
    let (recurrence_bonds, cue) = current_recurrence_witness(
        retained,
        current_physical_deltas,
        active_bonds,
        partial_cue_lineages,
        origin == PhysicalMosaicRecurrenceOrigin::InternallySimulated,
        false,
    )?;
    if recurrence_bonds.as_slice() == retained.recurrence_bonds.as_ref()
        && cue.as_slice() == retained.partial_cue_lineages.as_ref()
        && retained.recurrence_origin == Some(origin)
    {
        return Err(PhysicalMosaicError::RecurrenceDidNotAlterFormation);
    }
    let mut altered = retained.clone();
    altered.recurrence_bonds = recurrence_bonds.into_boxed_slice();
    altered.partial_cue_lineages = cue.into_boxed_slice();
    altered.recurrence_origin = Some(origin);
    Ok(altered)
}

/// Admit the smallest physical collective unit only after later recurrence.
///
/// `original` is the post-quiescence settlement that produced the member
/// fractals. `recurrence` is the later actual partial-cue physical response.
/// The caller cannot substitute counters or labels for either settlement.
pub(crate) fn admit_physical_mosaic(
    anatomy: &ReachedCohortAnatomy,
    original: &ReachedCohortPostExperienceSettlement,
    recurrence: &ReachedCohortRecurrenceSettlement,
) -> Result<AdmittedPhysicalMosaic, PhysicalMosaicError> {
    let neuron_count = anatomy.neuron_count();
    let contact_count = anatomy.contact_count();
    if original.neuron_fractals.len() != neuron_count
        || original.gate_work_perturbed_neurons.len() != neuron_count
        || original.active_electrical_contacts.len() != contact_count
        || recurrence.neuron_physical_deltas.len() != neuron_count
        || recurrence.gate_work_perturbed_neurons.len() != neuron_count
        || recurrence.active_electrical_contacts.len() != contact_count
    {
        return Err(PhysicalMosaicError::WidthMismatch);
    }

    if original
        .neuron_fractals
        .iter()
        .enumerate()
        .any(|(index, fractal)| {
            fractal.as_ref().is_some_and(|fractal| {
                let neuron_anatomy = &anatomy.neuron_anatomies()[index];
                neuron_anatomy
                    .sparse_delta_coordinate_count()
                    .is_none_or(|maximum| fractal.entries().len() > maximum)
                    || !fractal_coordinates_fit(fractal, neuron_anatomy.psi_ring_count())
            })
        })
    {
        return Err(PhysicalMosaicError::InvalidRetainedFractal);
    }

    let members = original
        .neuron_fractals
        .iter()
        .enumerate()
        .filter_map(|(index, fractal)| fractal.as_ref().map(|_| index))
        .collect::<Vec<_>>();
    if members.len() < 3 {
        return Err(PhysicalMosaicError::FewerThanThreeRetainedFractals);
    }
    let member_mask = mask(neuron_count, &members)?;
    let endpoints = anatomy.contact_endpoints().collect::<Vec<_>>();
    let original_contacts = active_contacts_within(
        &endpoints,
        &original.active_electrical_contacts,
        &member_mask,
    );
    if !connected_members(
        neuron_count,
        &members,
        &member_mask,
        &endpoints,
        &original.active_electrical_contacts,
        &members[..1],
    ) {
        return Err(PhysicalMosaicError::OriginalRelationNotConnected);
    }

    let cue = recurrence
        .gate_work_perturbed_neurons
        .iter()
        .enumerate()
        .filter_map(|(index, perturbed)| perturbed.then_some(index))
        .collect::<Vec<_>>();
    if cue.is_empty() {
        return Err(PhysicalMosaicError::CueIsEmpty);
    }
    if cue.len() >= members.len() {
        return Err(PhysicalMosaicError::CueIsNotPartial);
    }
    if cue.iter().any(|index| !member_mask[*index]) {
        return Err(PhysicalMosaicError::CueOutsideFormation);
    }
    if !connected_members(
        neuron_count,
        &members,
        &member_mask,
        &endpoints,
        &recurrence.active_electrical_contacts,
        &cue,
    ) {
        return Err(PhysicalMosaicError::RecurrenceDidNotReachFormation);
    }
    if members
        .iter()
        .any(|index| recurrence.neuron_physical_deltas[*index].is_none())
    {
        return Err(PhysicalMosaicError::RecurrenceDidNotChangeEveryMember);
    }
    let all_bonds = stable_bonds_for_anatomy(anatomy)?;
    let mut member_fractals = members
        .iter()
        .map(|index| {
            (
                anatomy.neuron_lineages()[*index],
                original.neuron_fractals[*index].as_ref().unwrap().clone(),
            )
        })
        .collect::<Vec<_>>();
    member_fractals.sort_by_key(|(lineage, _)| *lineage);
    let mut member_lineages = Vec::with_capacity(member_fractals.len());
    let mut retained_fractals = Vec::with_capacity(member_fractals.len());
    for (lineage, fractal) in member_fractals {
        member_lineages.push(lineage);
        retained_fractals.push(fractal);
    }
    let mut original_bonds = original_contacts
        .iter()
        .map(|index| all_bonds[*index])
        .collect::<Vec<_>>();
    original_bonds.sort_unstable();
    let mut recurrence_bonds = active_contacts_within(
        &endpoints,
        &recurrence.active_electrical_contacts,
        &member_mask,
    )
    .iter()
    .map(|index| all_bonds[*index])
    .collect::<Vec<_>>();
    recurrence_bonds.sort_unstable();
    let mut partial_cue_lineages = cue
        .iter()
        .map(|index| anatomy.neuron_lineages()[*index])
        .collect::<Vec<_>>();
    partial_cue_lineages.sort_unstable();
    Ok(AdmittedPhysicalMosaic {
        original_only: false,
        exact_pattern_recognition: true,
        member_lineages: member_lineages.into_boxed_slice(),
        retained_fractals: retained_fractals.into_boxed_slice(),
        retained_excitation_zeptojoules: Box::new([]),
        original_bonds: original_bonds.into_boxed_slice(),
        recurrence_bonds: recurrence_bonds.into_boxed_slice(),
        partial_cue_lineages: partial_cue_lineages.into_boxed_slice(),
        recurrence_origin: Some(PhysicalMosaicRecurrenceOrigin::ExternallyObserved),
    })
}

fn stable_bonds_for_anatomy(
    anatomy: &ReachedCohortAnatomy,
) -> Result<Vec<StablePhysicalBondReference>, PhysicalMosaicError> {
    let mut bonds = Vec::with_capacity(anatomy.contact_count());
    for (left, right) in anatomy.contact_endpoints() {
        let left = anatomy.neuron_lineages()[left];
        let right = anatomy.neuron_lineages()[right];
        let (canonical_left, canonical_right) = if left < right {
            (left, right)
        } else {
            (right, left)
        };
        let parallel_ordinal = u32::try_from(
            bonds
                .iter()
                .filter(|bond: &&StablePhysicalBondReference| {
                    bond.left == canonical_left && bond.right == canonical_right
                })
                .count(),
        )
        .map_err(|_| PhysicalMosaicError::WidthMismatch)?;
        bonds.push(
            StablePhysicalBondReference::new(left, right, parallel_ordinal)
                .ok_or(PhysicalMosaicError::WidthMismatch)?,
        );
    }
    Ok(bonds)
}

fn mask(width: usize, indices: &[usize]) -> Result<Vec<bool>, PhysicalMosaicError> {
    let mut result = vec![false; width];
    for index in indices {
        let slot = result
            .get_mut(*index)
            .ok_or(PhysicalMosaicError::WidthMismatch)?;
        *slot = true;
    }
    Ok(result)
}

fn active_contacts_within(
    endpoints: &[(usize, usize)],
    active: &[bool],
    members: &[bool],
) -> Vec<usize> {
    endpoints
        .iter()
        .zip(active)
        .enumerate()
        .filter_map(|(index, ((left, right), active))| {
            (*active && members[*left] && members[*right]).then_some(index)
        })
        .collect()
}

/// The admission law's own connectivity predicate: every listed member is
/// reachable from the roots through contacts that were physically active,
/// walking only member-to-member bonds.  Shared verbatim with the retention
/// boundary (stimulus-boundary participation retention, ratified 2026-08-05)
/// so an original can be retained only if it would satisfy this exact
/// original-side admission requirement later.
pub(crate) fn connected_members(
    neuron_count: usize,
    members: &[usize],
    member_mask: &[bool],
    endpoints: &[(usize, usize)],
    active: &[bool],
    roots: &[usize],
) -> bool {
    let mut reached = vec![false; neuron_count];
    let mut queue = VecDeque::new();
    for root in roots {
        if *root >= neuron_count || !member_mask[*root] {
            return false;
        }
        if !reached[*root] {
            reached[*root] = true;
            queue.push_back(*root);
        }
    }
    while let Some(current) = queue.pop_front() {
        for ((left, right), active) in endpoints.iter().zip(active) {
            if !*active || !member_mask[*left] || !member_mask[*right] {
                continue;
            }
            let neighbour = if *left == current {
                Some(*right)
            } else if *right == current {
                Some(*left)
            } else {
                None
            };
            if let Some(neighbour) = neighbour {
                if !reached[neighbour] {
                    reached[neighbour] = true;
                    queue.push_back(neighbour);
                }
            }
        }
    }
    members.iter().all(|index| reached[*index])
}

const LEGACY_PHYSICAL_MOSAIC_CODEC_MAGIC: &[u8; 8] = b"GLMOS003";
const LEGACY_PHYSICAL_MOSAIC_CODEC_VERSION: u16 = 3;
const PHYSICAL_MOSAIC_CODEC_MAGIC: &[u8; 8] = b"GLMOS004";
const PHYSICAL_MOSAIC_CODEC_VERSION: u16 = 4;
const EXCITATION_PHYSICAL_MOSAIC_CODEC_MAGIC: &[u8; 8] = b"GLMOS005";
const EXCITATION_PHYSICAL_MOSAIC_CODEC_VERSION: u16 = 5;
const ORIGINAL_PHYSICAL_MOSAIC_CODEC_MAGIC: &[u8; 8] = b"GLMOS006";
const ORIGINAL_PHYSICAL_MOSAIC_CODEC_VERSION: u16 = 6;
const INTERNAL_PHYSICAL_MOSAIC_CODEC_MAGIC: &[u8; 8] = b"GLMOS007";
const INTERNAL_PHYSICAL_MOSAIC_CODEC_VERSION: u16 = 7;
const PHYSICAL_MOSAIC_CODEC_HEADER_BYTES: usize = 8 + 2 + 4 * 8;
const INTERNAL_PHYSICAL_MOSAIC_ORIGIN_BYTES: usize = 1;
const PHYSICAL_MOSAIC_MEMBER_HEADER_BYTES: usize = 16 + 8;
const PHYSICAL_MOSAIC_FRACTAL_ENTRY_BYTES: usize = 1 + 8 + 1 + 16 + 16;
const PHYSICAL_MOSAIC_BOND_BYTES: usize = 16 + 16 + 4;
const PHYSICAL_MOSAIC_LINEAGE_BYTES: usize = 16;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PhysicalMosaicCodecError {
    BudgetExceeded,
    ArithmeticWidth,
    AllocationFailed,
    Truncated,
    TrailingBytes,
    HeaderMismatch,
    VersionMismatch,
    CountOutsideAnatomy,
    MemberFractalWidthMismatch,
    NonCanonicalIndexOrder,
    IndexOutsideAnatomy,
    InvalidRetainedFractal,
    CueIsNotProperSubset,
    ContactLeavesFormation,
    OriginalRelationNotConnected,
    RecurrenceDidNotReachFormation,
}

/// Encode an already admitted physical mosaic against the exact reached cohort
/// it indexes. The byte budget limits transport allocation only; it is not a
/// cognitive or formation-size threshold.
pub(crate) fn encode_admitted_physical_mosaic(
    anatomy: &ReachedCohortAnatomy,
    mosaic: &AdmittedPhysicalMosaic,
    max_encoded_bytes: usize,
) -> Result<Vec<u8>, PhysicalMosaicCodecError> {
    let mut bonds =
        stable_bonds_for_anatomy(anatomy).map_err(|_| PhysicalMosaicCodecError::ArithmeticWidth)?;
    bonds.sort_unstable();
    let fractal_anatomies = admitted_fractal_anatomies(anatomy)?;
    encode_admitted_physical_mosaic_for_topology(
        anatomy.neuron_lineages(),
        &bonds,
        &fractal_anatomies,
        mosaic,
        max_encoded_bytes,
    )
}

/// Decode only references into the supplied reached cohort. No topology is
/// inferred from the encoded body, and no contact absent from anatomy can be
/// introduced by restart bytes.
pub(crate) fn decode_admitted_physical_mosaic(
    anatomy: &ReachedCohortAnatomy,
    encoded: &[u8],
    max_encoded_bytes: usize,
) -> Result<AdmittedPhysicalMosaic, PhysicalMosaicCodecError> {
    let mut bonds =
        stable_bonds_for_anatomy(anatomy).map_err(|_| PhysicalMosaicCodecError::ArithmeticWidth)?;
    bonds.sort_unstable();
    let fractal_anatomies = admitted_fractal_anatomies(anatomy)?;
    decode_admitted_physical_mosaic_for_topology(
        anatomy.neuron_lineages(),
        &bonds,
        &fractal_anatomies,
        encoded,
        max_encoded_bytes,
    )
}

fn admitted_fractal_anatomies(
    anatomy: &ReachedCohortAnatomy,
) -> Result<Vec<(usize, usize)>, PhysicalMosaicCodecError> {
    anatomy
        .neuron_anatomies()
        .iter()
        .map(|neuron| {
            neuron
                .sparse_delta_coordinate_count()
                .map(|maximum| (neuron.psi_ring_count(), maximum))
                .ok_or(PhysicalMosaicCodecError::ArithmeticWidth)
        })
        .collect()
}

pub(crate) fn encode_admitted_physical_mosaic_for_topology(
    neuron_lineages: &[StableNeuronLineage],
    bonds: &[StablePhysicalBondReference],
    fractal_anatomies: &[(usize, usize)],
    mosaic: &AdmittedPhysicalMosaic,
    max_encoded_bytes: usize,
) -> Result<Vec<u8>, PhysicalMosaicCodecError> {
    validate_decoded_mosaic(neuron_lineages, bonds, fractal_anatomies, mosaic)?;
    let required = physical_mosaic_encoded_bytes(mosaic)?;
    if required > max_encoded_bytes {
        return Err(PhysicalMosaicCodecError::BudgetExceeded);
    }
    let mut encoded = Vec::new();
    encoded
        .try_reserve_exact(required)
        .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;
    let excitation_layout =
        mosaic.retained_excitation_zeptojoules.len() == mosaic.member_lineages.len();
    if mosaic.recurrence_origin == Some(PhysicalMosaicRecurrenceOrigin::InternallySimulated) {
        if mosaic.original_only || excitation_layout || !mosaic.exact_pattern_recognition {
            return Err(PhysicalMosaicCodecError::MemberFractalWidthMismatch);
        }
        encoded.extend_from_slice(INTERNAL_PHYSICAL_MOSAIC_CODEC_MAGIC);
        encoded.extend_from_slice(&INTERNAL_PHYSICAL_MOSAIC_CODEC_VERSION.to_le_bytes());
    } else if mosaic.original_only {
        encoded.extend_from_slice(ORIGINAL_PHYSICAL_MOSAIC_CODEC_MAGIC);
        encoded.extend_from_slice(&ORIGINAL_PHYSICAL_MOSAIC_CODEC_VERSION.to_le_bytes());
    } else if excitation_layout {
        encoded.extend_from_slice(EXCITATION_PHYSICAL_MOSAIC_CODEC_MAGIC);
        encoded.extend_from_slice(&EXCITATION_PHYSICAL_MOSAIC_CODEC_VERSION.to_le_bytes());
    } else if mosaic.exact_pattern_recognition {
        encoded.extend_from_slice(PHYSICAL_MOSAIC_CODEC_MAGIC);
        encoded.extend_from_slice(&PHYSICAL_MOSAIC_CODEC_VERSION.to_le_bytes());
    } else {
        encoded.extend_from_slice(LEGACY_PHYSICAL_MOSAIC_CODEC_MAGIC);
        encoded.extend_from_slice(&LEGACY_PHYSICAL_MOSAIC_CODEC_VERSION.to_le_bytes());
    }
    push_codec_usize(&mut encoded, mosaic.member_lineages.len())?;
    push_codec_usize(&mut encoded, mosaic.original_bonds.len())?;
    push_codec_usize(&mut encoded, mosaic.recurrence_bonds.len())?;
    push_codec_usize(&mut encoded, mosaic.partial_cue_lineages.len())?;
    if mosaic.recurrence_origin == Some(PhysicalMosaicRecurrenceOrigin::InternallySimulated) {
        encoded.push(1);
    }
    for (member_ordinal, (lineage, fractal)) in mosaic
        .member_lineages
        .iter()
        .zip(mosaic.retained_fractals.iter())
        .enumerate()
    {
        encoded.extend_from_slice(lineage);
        push_codec_usize(&mut encoded, fractal.entries().len())?;
        for entry in fractal.entries() {
            let (tag, index) = encode_coordinate(entry.coordinate());
            encoded.push(tag);
            push_codec_usize(&mut encoded, index)?;
            match entry.delta() {
                ExactPhysicalStateDelta::Integral(delta) => {
                    let (negative, magnitude) = delta.parts();
                    encoded.push(0);
                    encoded.extend_from_slice(&magnitude.to_le_bytes());
                    encoded.extend_from_slice(&u128::from(negative).to_le_bytes());
                }
                ExactPhysicalStateDelta::Rational(delta) => {
                    let (numerator, denominator) = delta.parts();
                    encoded.push(1);
                    encoded.extend_from_slice(&numerator.to_le_bytes());
                    encoded.extend_from_slice(&denominator.to_le_bytes());
                }
                ExactPhysicalStateDelta::Energy(_) => {
                    return Err(PhysicalMosaicCodecError::InvalidRetainedFractal);
                }
            }
        }
        if excitation_layout {
            let (numerator, denominator) =
                mosaic.retained_excitation_zeptojoules[member_ordinal].parts();
            encoded.extend_from_slice(&numerator.to_le_bytes());
            encoded.extend_from_slice(&denominator.to_le_bytes());
        }
    }
    for bond in &mosaic.original_bonds {
        encode_bond(&mut encoded, *bond);
    }
    for bond in &mosaic.recurrence_bonds {
        encode_bond(&mut encoded, *bond);
    }
    for lineage in &mosaic.partial_cue_lineages {
        encoded.extend_from_slice(lineage);
    }
    if encoded.len() != required {
        return Err(PhysicalMosaicCodecError::ArithmeticWidth);
    }
    Ok(encoded)
}

pub(crate) fn decode_admitted_physical_mosaic_for_topology(
    neuron_lineages: &[StableNeuronLineage],
    bonds: &[StablePhysicalBondReference],
    fractal_anatomies: &[(usize, usize)],
    encoded: &[u8],
    max_encoded_bytes: usize,
) -> Result<AdmittedPhysicalMosaic, PhysicalMosaicCodecError> {
    if encoded.len() > max_encoded_bytes {
        return Err(PhysicalMosaicCodecError::BudgetExceeded);
    }
    let mut reader = PhysicalMosaicReader::new(encoded);
    let magic = reader.take(PHYSICAL_MOSAIC_CODEC_MAGIC.len())?;
    let (original_only, exact_pattern_recognition, excitation_layout, internal_layout) =
        if magic == INTERNAL_PHYSICAL_MOSAIC_CODEC_MAGIC {
            if reader.u16()? != INTERNAL_PHYSICAL_MOSAIC_CODEC_VERSION {
                return Err(PhysicalMosaicCodecError::VersionMismatch);
            }
            (false, true, false, true)
        } else if magic == ORIGINAL_PHYSICAL_MOSAIC_CODEC_MAGIC {
            if reader.u16()? != ORIGINAL_PHYSICAL_MOSAIC_CODEC_VERSION {
                return Err(PhysicalMosaicCodecError::VersionMismatch);
            }
            (true, false, false, false)
        } else if magic == EXCITATION_PHYSICAL_MOSAIC_CODEC_MAGIC {
            if reader.u16()? != EXCITATION_PHYSICAL_MOSAIC_CODEC_VERSION {
                return Err(PhysicalMosaicCodecError::VersionMismatch);
            }
            (false, true, true, false)
        } else if magic == PHYSICAL_MOSAIC_CODEC_MAGIC {
            if reader.u16()? != PHYSICAL_MOSAIC_CODEC_VERSION {
                return Err(PhysicalMosaicCodecError::VersionMismatch);
            }
            (false, true, false, false)
        } else if magic == LEGACY_PHYSICAL_MOSAIC_CODEC_MAGIC {
            if reader.u16()? != LEGACY_PHYSICAL_MOSAIC_CODEC_VERSION {
                return Err(PhysicalMosaicCodecError::VersionMismatch);
            }
            (false, false, false, false)
        } else {
            return Err(PhysicalMosaicCodecError::HeaderMismatch);
        };
    let member_count = reader.usize()?;
    let original_contact_count = reader.usize()?;
    let recurrence_contact_count = reader.usize()?;
    let cue_count = reader.usize()?;
    let recurrence_origin = if internal_layout {
        match reader.u8()? {
            1 => Some(PhysicalMosaicRecurrenceOrigin::InternallySimulated),
            _ => return Err(PhysicalMosaicCodecError::HeaderMismatch),
        }
    } else if original_only {
        None
    } else {
        Some(PhysicalMosaicRecurrenceOrigin::ExternallyObserved)
    };
    validate_codec_counts(
        neuron_lineages.len(),
        bonds.len(),
        member_count,
        original_contact_count,
        recurrence_contact_count,
        cue_count,
        original_only,
        internal_layout,
    )?;
    if fractal_anatomies.len() != neuron_lineages.len() {
        return Err(PhysicalMosaicCodecError::CountOutsideAnatomy);
    }

    let mut member_lineages = Vec::new();
    let mut retained_fractals = Vec::new();
    let mut retained_excitation_zeptojoules = Vec::new();
    let mut original_bonds = Vec::new();
    let mut recurrence_bonds = Vec::new();
    let mut partial_cue_lineages = Vec::new();
    member_lineages
        .try_reserve_exact(member_count)
        .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;
    retained_fractals
        .try_reserve_exact(member_count)
        .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;
    if excitation_layout {
        retained_excitation_zeptojoules
            .try_reserve_exact(member_count)
            .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;
    }
    original_bonds
        .try_reserve_exact(original_contact_count)
        .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;
    recurrence_bonds
        .try_reserve_exact(recurrence_contact_count)
        .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;
    partial_cue_lineages
        .try_reserve_exact(cue_count)
        .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;

    for _ in 0..member_count {
        let lineage = reader.lineage()?;
        let member = neuron_lineages
            .iter()
            .position(|candidate| candidate == &lineage)
            .ok_or(PhysicalMosaicCodecError::IndexOutsideAnatomy)?;
        let (ring_count, maximum_entries) = *fractal_anatomies
            .get(member)
            .ok_or(PhysicalMosaicCodecError::IndexOutsideAnatomy)?;
        let entry_count = reader.usize()?;
        if entry_count == 0 || entry_count > maximum_entries {
            return Err(PhysicalMosaicCodecError::InvalidRetainedFractal);
        }
        let entry_bytes = entry_count
            .checked_mul(PHYSICAL_MOSAIC_FRACTAL_ENTRY_BYTES)
            .ok_or(PhysicalMosaicCodecError::ArithmeticWidth)?;
        if entry_bytes > reader.remaining() {
            return Err(PhysicalMosaicCodecError::Truncated);
        }
        let mut entries = Vec::new();
        entries
            .try_reserve_exact(entry_count)
            .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;
        for _ in 0..entry_count {
            let coordinate = decode_coordinate(reader.u8()?, reader.usize()?)?;
            let kind = reader.u8()?;
            let first = reader.take(16)?;
            let second = reader.take(16)?;
            let delta = match kind {
                0 => {
                    let magnitude = u128::from_le_bytes(
                        first
                            .try_into()
                            .map_err(|_| PhysicalMosaicCodecError::Truncated)?,
                    );
                    let negative = u128::from_le_bytes(
                        second
                            .try_into()
                            .map_err(|_| PhysicalMosaicCodecError::Truncated)?,
                    );
                    let negative = match negative {
                        0 => false,
                        1 => true,
                        _ => return Err(PhysicalMosaicCodecError::InvalidRetainedFractal),
                    };
                    ExactPhysicalStateDelta::Integral(
                        ExactSignedDelta::from_parts(negative, magnitude)
                            .ok_or(PhysicalMosaicCodecError::InvalidRetainedFractal)?,
                    )
                }
                1 => {
                    let numerator = i128::from_le_bytes(
                        first
                            .try_into()
                            .map_err(|_| PhysicalMosaicCodecError::Truncated)?,
                    );
                    let denominator = u128::from_le_bytes(
                        second
                            .try_into()
                            .map_err(|_| PhysicalMosaicCodecError::Truncated)?,
                    );
                    ExactPhysicalStateDelta::Rational(
                        ExactRational::new(numerator, denominator)
                            .map_err(|_| PhysicalMosaicCodecError::InvalidRetainedFractal)?,
                    )
                }
                _ => return Err(PhysicalMosaicCodecError::InvalidRetainedFractal),
            };
            entries.push(
                PhysicalStateDeltaEntry::new(coordinate, delta)
                    .ok_or(PhysicalMosaicCodecError::InvalidRetainedFractal)?,
            );
        }
        let fractal = SparsePhysicalStateDelta::from_canonical_entries(entries)
            .ok_or(PhysicalMosaicCodecError::InvalidRetainedFractal)?;
        if !fractal_coordinates_fit(&fractal, ring_count) {
            return Err(PhysicalMosaicCodecError::InvalidRetainedFractal);
        }
        member_lineages.push(lineage);
        retained_fractals.push(fractal);
        if excitation_layout {
            let numerator = i128::from_le_bytes(
                reader
                    .take(16)?
                    .try_into()
                    .map_err(|_| PhysicalMosaicCodecError::Truncated)?,
            );
            let denominator = u128::from_le_bytes(
                reader
                    .take(16)?
                    .try_into()
                    .map_err(|_| PhysicalMosaicCodecError::Truncated)?,
            );
            retained_excitation_zeptojoules.push(
                ExactRational::new(numerator, denominator)
                    .map_err(|_| PhysicalMosaicCodecError::InvalidRetainedFractal)?,
            );
        }
    }
    for _ in 0..original_contact_count {
        original_bonds.push(reader.bond()?);
    }
    for _ in 0..recurrence_contact_count {
        recurrence_bonds.push(reader.bond()?);
    }
    for _ in 0..cue_count {
        partial_cue_lineages.push(reader.lineage()?);
    }
    reader.finish()?;
    let mosaic = AdmittedPhysicalMosaic {
        original_only,
        exact_pattern_recognition,
        member_lineages: member_lineages.into_boxed_slice(),
        retained_fractals: retained_fractals.into_boxed_slice(),
        retained_excitation_zeptojoules: retained_excitation_zeptojoules.into_boxed_slice(),
        original_bonds: original_bonds.into_boxed_slice(),
        recurrence_bonds: recurrence_bonds.into_boxed_slice(),
        partial_cue_lineages: partial_cue_lineages.into_boxed_slice(),
        recurrence_origin,
    };
    validate_decoded_mosaic(neuron_lineages, bonds, fractal_anatomies, &mosaic)?;
    Ok(mosaic)
}

fn encode_coordinate(coordinate: PhysicalStateCoordinate) -> (u8, usize) {
    match coordinate {
        PhysicalStateCoordinate::PsiWinding(index) => (0, index),
        PhysicalStateCoordinate::PsiDissipatedEnergy(index) => (1, index),
        PhysicalStateCoordinate::GateOpenPopulation => (2, 0),
        PhysicalStateCoordinate::GateDissipatedEnergy => (3, 0),
        PhysicalStateCoordinate::MembraneSeparatedCharge => (4, 0),
        PhysicalStateCoordinate::MembraneCarrierPhase => (5, 0),
        PhysicalStateCoordinate::ConductancePathCarrierPhase(index) => (6, index),
        PhysicalStateCoordinate::IntracellularCarrier => (7, 0),
        PhysicalStateCoordinate::ExtracellularCarrier => (8, 0),
        PhysicalStateCoordinate::RecoveryPsiFuel(index) => (9, index),
        PhysicalStateCoordinate::RecoveryPsiSpent(index) => (10, index),
        PhysicalStateCoordinate::RecoveryPsiExportedHeat(index) => (11, index),
        PhysicalStateCoordinate::RecoveryGateFuel => (12, 0),
        PhysicalStateCoordinate::RecoveryGateSpent => (13, 0),
        PhysicalStateCoordinate::RecoveryGateExportedHeat => (14, 0),
        PhysicalStateCoordinate::PlasticRestLength => (15, 0),
        PhysicalStateCoordinate::PlasticDissipatedEnergy => (16, 0),
        PhysicalStateCoordinate::RecoveryPlasticFuel => (17, 0),
        PhysicalStateCoordinate::RecoveryPlasticSpent => (18, 0),
        PhysicalStateCoordinate::RecoveryPlasticExportedHeat => (19, 0),
        PhysicalStateCoordinate::DnaSubstrate => (20, 0),
        PhysicalStateCoordinate::DnaFuel => (21, 0),
        PhysicalStateCoordinate::DnaExpressedProduct => (22, 0),
        PhysicalStateCoordinate::DnaWaste => (23, 0),
        PhysicalStateCoordinate::ReceptorQuantumResidue => (24, 0),
        PhysicalStateCoordinate::MembraneReturnWorkResidue => (25, 0),
        PhysicalStateCoordinate::PlasticDissipationResidue => (26, 0),
        PhysicalStateCoordinate::GateDissipationResidue => (27, 0),
    }
}

fn decode_coordinate(
    tag: u8,
    index: usize,
) -> Result<PhysicalStateCoordinate, PhysicalMosaicCodecError> {
    let coordinate = match tag {
        0 => PhysicalStateCoordinate::PsiWinding(index),
        1 => PhysicalStateCoordinate::PsiDissipatedEnergy(index),
        2 if index == 0 => PhysicalStateCoordinate::GateOpenPopulation,
        3 if index == 0 => PhysicalStateCoordinate::GateDissipatedEnergy,
        4 if index == 0 => PhysicalStateCoordinate::MembraneSeparatedCharge,
        5 if index == 0 => PhysicalStateCoordinate::MembraneCarrierPhase,
        6 => PhysicalStateCoordinate::ConductancePathCarrierPhase(index),
        7 if index == 0 => PhysicalStateCoordinate::IntracellularCarrier,
        8 if index == 0 => PhysicalStateCoordinate::ExtracellularCarrier,
        9 => PhysicalStateCoordinate::RecoveryPsiFuel(index),
        10 => PhysicalStateCoordinate::RecoveryPsiSpent(index),
        11 => PhysicalStateCoordinate::RecoveryPsiExportedHeat(index),
        12 if index == 0 => PhysicalStateCoordinate::RecoveryGateFuel,
        13 if index == 0 => PhysicalStateCoordinate::RecoveryGateSpent,
        14 if index == 0 => PhysicalStateCoordinate::RecoveryGateExportedHeat,
        15 if index == 0 => PhysicalStateCoordinate::PlasticRestLength,
        16 if index == 0 => PhysicalStateCoordinate::PlasticDissipatedEnergy,
        17 if index == 0 => PhysicalStateCoordinate::RecoveryPlasticFuel,
        18 if index == 0 => PhysicalStateCoordinate::RecoveryPlasticSpent,
        19 if index == 0 => PhysicalStateCoordinate::RecoveryPlasticExportedHeat,
        20 if index == 0 => PhysicalStateCoordinate::DnaSubstrate,
        21 if index == 0 => PhysicalStateCoordinate::DnaFuel,
        22 if index == 0 => PhysicalStateCoordinate::DnaExpressedProduct,
        23 if index == 0 => PhysicalStateCoordinate::DnaWaste,
        24 if index == 0 => PhysicalStateCoordinate::ReceptorQuantumResidue,
        25 if index == 0 => PhysicalStateCoordinate::MembraneReturnWorkResidue,
        26 if index == 0 => PhysicalStateCoordinate::PlasticDissipationResidue,
        27 if index == 0 => PhysicalStateCoordinate::GateDissipationResidue,
        _ => return Err(PhysicalMosaicCodecError::InvalidRetainedFractal),
    };
    Ok(coordinate)
}

fn fractal_coordinates_fit(fractal: &SparsePhysicalStateDelta, psi_ring_count: usize) -> bool {
    fractal
        .entries()
        .iter()
        .all(|entry| match entry.coordinate() {
            PhysicalStateCoordinate::PsiWinding(index)
            | PhysicalStateCoordinate::PsiDissipatedEnergy(index)
            | PhysicalStateCoordinate::RecoveryPsiFuel(index)
            | PhysicalStateCoordinate::RecoveryPsiSpent(index)
            | PhysicalStateCoordinate::RecoveryPsiExportedHeat(index) => index < psi_ring_count,
            PhysicalStateCoordinate::ConductancePathCarrierPhase(index) => index == 0,
            _ => true,
        })
}

fn validate_codec_counts(
    neuron_count: usize,
    contact_count: usize,
    member_count: usize,
    original_contact_count: usize,
    recurrence_contact_count: usize,
    cue_count: usize,
    original_only: bool,
    internally_originated: bool,
) -> Result<(), PhysicalMosaicCodecError> {
    if member_count < 3
        || member_count > neuron_count
        || original_contact_count > contact_count
        || recurrence_contact_count > contact_count
        || (original_only && (recurrence_contact_count != 0 || cue_count != 0))
        || (!original_only
            && (cue_count == 0
                || cue_count > member_count
                || (!internally_originated && cue_count == member_count)))
    {
        return Err(PhysicalMosaicCodecError::CountOutsideAnatomy);
    }
    Ok(())
}

fn physical_mosaic_encoded_bytes(
    mosaic: &AdmittedPhysicalMosaic,
) -> Result<usize, PhysicalMosaicCodecError> {
    let entry_count = mosaic
        .retained_fractals
        .iter()
        .try_fold(0usize, |total, fractal| {
            total.checked_add(fractal.entries().len())
        })
        .ok_or(PhysicalMosaicCodecError::ArithmeticWidth)?;
    PHYSICAL_MOSAIC_CODEC_HEADER_BYTES
        .checked_add(if mosaic.recurrence_origin
            == Some(PhysicalMosaicRecurrenceOrigin::InternallySimulated)
        {
            INTERNAL_PHYSICAL_MOSAIC_ORIGIN_BYTES
        } else {
            0
        })
        .ok_or(PhysicalMosaicCodecError::ArithmeticWidth)?
        .checked_add(
            mosaic
                .member_lineages
                .len()
                .checked_mul(PHYSICAL_MOSAIC_MEMBER_HEADER_BYTES)
                .ok_or(PhysicalMosaicCodecError::ArithmeticWidth)?,
        )
        .and_then(|bytes| {
            entry_count
                .checked_mul(PHYSICAL_MOSAIC_FRACTAL_ENTRY_BYTES)?
                .checked_add(bytes)
        })
        .and_then(|bytes| {
            mosaic
                .original_bonds
                .len()
                .checked_add(mosaic.recurrence_bonds.len())?
                .checked_mul(PHYSICAL_MOSAIC_BOND_BYTES)?
                .checked_add(
                    mosaic
                        .partial_cue_lineages
                        .len()
                        .checked_mul(PHYSICAL_MOSAIC_LINEAGE_BYTES)?,
                )?
                .checked_add(bytes)
        })
        .and_then(|bytes| {
            mosaic
                .retained_excitation_zeptojoules
                .len()
                .checked_mul(32)?
                .checked_add(bytes)
        })
        .ok_or(PhysicalMosaicCodecError::ArithmeticWidth)
}

fn validate_decoded_mosaic(
    neuron_lineages: &[StableNeuronLineage],
    available_bonds: &[StablePhysicalBondReference],
    fractal_anatomies: &[(usize, usize)],
    mosaic: &AdmittedPhysicalMosaic,
) -> Result<(), PhysicalMosaicCodecError> {
    validate_codec_counts(
        neuron_lineages.len(),
        available_bonds.len(),
        mosaic.member_lineages.len(),
        mosaic.original_bonds.len(),
        mosaic.recurrence_bonds.len(),
        mosaic.partial_cue_lineages.len(),
        mosaic.original_only,
        mosaic.recurrence_origin == Some(PhysicalMosaicRecurrenceOrigin::InternallySimulated),
    )?;
    let excitation_count = mosaic.retained_excitation_zeptojoules.len();
    if fractal_anatomies.len() != neuron_lineages.len()
        || mosaic.member_lineages.len() != mosaic.retained_fractals.len()
        || (excitation_count != 0 && excitation_count != mosaic.member_lineages.len())
        || (!mosaic.exact_pattern_recognition && excitation_count != 0)
        || (mosaic.original_only && mosaic.recurrence_origin.is_some())
        || (!mosaic.original_only && mosaic.recurrence_origin.is_none())
    {
        return Err(PhysicalMosaicCodecError::MemberFractalWidthMismatch);
    }
    validate_canonical_values(&mosaic.member_lineages)?;
    validate_canonical_values(&mosaic.original_bonds)?;
    validate_canonical_values(&mosaic.recurrence_bonds)?;
    validate_canonical_values(&mosaic.partial_cue_lineages)?;
    for (lineage, fractal) in mosaic.member_lineages.iter().zip(&mosaic.retained_fractals) {
        let member = neuron_lineages
            .iter()
            .position(|candidate| candidate == lineage)
            .ok_or(PhysicalMosaicCodecError::IndexOutsideAnatomy)?;
        let (ring_count, maximum_entries) = fractal_anatomies[member];
        if fractal.entries().is_empty()
            || fractal.entries().len() > maximum_entries
            || !fractal_coordinates_fit(fractal, ring_count)
        {
            return Err(PhysicalMosaicCodecError::InvalidRetainedFractal);
        }
    }
    if mosaic
        .partial_cue_lineages
        .iter()
        .any(|cue| mosaic.member_lineages.binary_search(cue).is_err())
    {
        return Err(PhysicalMosaicCodecError::CueIsNotProperSubset);
    }
    for bond in mosaic
        .original_bonds
        .iter()
        .chain(mosaic.recurrence_bonds.iter())
    {
        let (left, right) = bond.endpoints();
        if available_bonds.binary_search(bond).is_err()
            || !neuron_lineages.contains(&left)
            || !neuron_lineages.contains(&right)
        {
            return Err(PhysicalMosaicCodecError::ContactLeavesFormation);
        }
    }
    if !mosaic_lineages_connect(
        &mosaic.member_lineages,
        &mosaic.original_bonds,
        &mosaic.member_lineages[..1],
    ) {
        return Err(PhysicalMosaicCodecError::OriginalRelationNotConnected);
    }
    if !mosaic.original_only
        && !mosaic_lineages_connect(
            &mosaic.member_lineages,
            &mosaic.recurrence_bonds,
            &mosaic.partial_cue_lineages,
        )
    {
        return Err(PhysicalMosaicCodecError::RecurrenceDidNotReachFormation);
    }
    Ok(())
}

fn validate_canonical_values<T: Ord>(values: &[T]) -> Result<(), PhysicalMosaicCodecError> {
    if values.windows(2).any(|pair| pair[0] >= pair[1]) {
        return Err(PhysicalMosaicCodecError::NonCanonicalIndexOrder);
    }
    Ok(())
}

/// Return one canonical, bounded physical witness that connects every
/// fractal-owning member through the contacts that actually carried current.
/// Intermediate reached neurons need not themselves retain a fractal: an
/// integration cell can physically bind two sensory impressions while its
/// own working state remains transient. The witness is the union of the
/// breadth-first predecessor paths from the first canonical member, so it
/// stores no unused branch and never invents an edge.
fn connecting_bond_witness(
    available_lineages: &[StableNeuronLineage],
    members: &[StableNeuronLineage],
    active_bonds: &[StablePhysicalBondReference],
) -> Option<Vec<StablePhysicalBondReference>> {
    let root = *members.first()?;
    let mut index_by_lineage = BTreeMap::<StableNeuronLineage, usize>::new();
    for (index, lineage) in available_lineages.iter().copied().enumerate() {
        if index_by_lineage.insert(lineage, index).is_some() {
            return None;
        }
    }
    let root_index = *index_by_lineage.get(&root)?;
    let mut incident =
        vec![Vec::<(usize, StablePhysicalBondReference)>::new(); available_lineages.len()];
    for bond in active_bonds {
        let (left, right) = bond.endpoints();
        let (Some(left_index), Some(right_index)) =
            (index_by_lineage.get(&left), index_by_lineage.get(&right))
        else {
            continue;
        };
        incident[*left_index].push((*right_index, *bond));
        incident[*right_index].push((*left_index, *bond));
    }
    let mut predecessor =
        vec![None::<(usize, StablePhysicalBondReference)>; available_lineages.len()];
    let mut reached = vec![false; available_lineages.len()];
    let mut queue = VecDeque::new();
    reached[root_index] = true;
    queue.push_back(root_index);
    while let Some(current_index) = queue.pop_front() {
        for (neighbour_index, bond) in incident[current_index].iter().copied() {
            if !reached[neighbour_index] {
                reached[neighbour_index] = true;
                predecessor[neighbour_index] = Some((current_index, bond));
                queue.push_back(neighbour_index);
            }
        }
    }
    let mut witness = Vec::new();
    for member in members {
        let mut current = *index_by_lineage.get(member)?;
        if !reached[current] {
            return None;
        }
        while current != root_index {
            let (prior, bond) = predecessor[current]?;
            witness.push(bond);
            current = prior;
        }
    }
    witness.sort_unstable();
    witness.dedup();
    Some(witness)
}

fn mosaic_lineages_connect(
    members: &[StableNeuronLineage],
    bonds: &[StablePhysicalBondReference],
    roots: &[StableNeuronLineage],
) -> bool {
    let mut reached = roots.to_vec();
    let mut queue = VecDeque::from(roots.to_vec());
    while let Some(current) = queue.pop_front() {
        for bond in bonds {
            let (left, right) = bond.endpoints();
            let neighbour = if left == current {
                Some(right)
            } else if right == current {
                Some(left)
            } else {
                None
            };
            if let Some(neighbour) = neighbour {
                if !reached.contains(&neighbour) {
                    reached.push(neighbour);
                    queue.push_back(neighbour);
                }
            }
        }
    }
    members.iter().all(|lineage| reached.contains(lineage))
}

fn encode_bond(output: &mut Vec<u8>, bond: StablePhysicalBondReference) {
    let (left, right) = bond.endpoints();
    output.extend_from_slice(&left);
    output.extend_from_slice(&right);
    output.extend_from_slice(&bond.parallel_ordinal().to_le_bytes());
}

fn push_codec_usize(output: &mut Vec<u8>, value: usize) -> Result<(), PhysicalMosaicCodecError> {
    output.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| PhysicalMosaicCodecError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

struct PhysicalMosaicReader<'a> {
    encoded: &'a [u8],
    position: usize,
}

impl<'a> PhysicalMosaicReader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self {
            encoded,
            position: 0,
        }
    }

    fn take(&mut self, bytes: usize) -> Result<&'a [u8], PhysicalMosaicCodecError> {
        let end = self
            .position
            .checked_add(bytes)
            .ok_or(PhysicalMosaicCodecError::ArithmeticWidth)?;
        let value = self
            .encoded
            .get(self.position..end)
            .ok_or(PhysicalMosaicCodecError::Truncated)?;
        self.position = end;
        Ok(value)
    }

    fn remaining(&self) -> usize {
        self.encoded.len() - self.position
    }

    fn u8(&mut self) -> Result<u8, PhysicalMosaicCodecError> {
        Ok(self.take(1)?[0])
    }

    fn u16(&mut self) -> Result<u16, PhysicalMosaicCodecError> {
        Ok(u16::from_le_bytes(
            self.take(2)?
                .try_into()
                .map_err(|_| PhysicalMosaicCodecError::Truncated)?,
        ))
    }

    fn usize(&mut self) -> Result<usize, PhysicalMosaicCodecError> {
        let value = u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| PhysicalMosaicCodecError::Truncated)?,
        );
        usize::try_from(value).map_err(|_| PhysicalMosaicCodecError::CountOutsideAnatomy)
    }

    fn lineage(&mut self) -> Result<StableNeuronLineage, PhysicalMosaicCodecError> {
        self.take(16)?
            .try_into()
            .map_err(|_| PhysicalMosaicCodecError::Truncated)
    }

    fn bond(&mut self) -> Result<StablePhysicalBondReference, PhysicalMosaicCodecError> {
        let left = self.lineage()?;
        let right = self.lineage()?;
        let ordinal = u32::from_le_bytes(
            self.take(4)?
                .try_into()
                .map_err(|_| PhysicalMosaicCodecError::Truncated)?,
        );
        StablePhysicalBondReference::new(left, right, ordinal)
            .ok_or(PhysicalMosaicCodecError::ContactLeavesFormation)
    }

    fn finish(self) -> Result<(), PhysicalMosaicCodecError> {
        if self.position == self.encoded.len() {
            Ok(())
        } else {
            Err(PhysicalMosaicCodecError::TrailingBytes)
        }
    }
}

#[cfg(test)]
mod codec_tests {
    use super::*;

    const MEMBER_COUNT_OFFSET: usize = 10;
    const ORIGINAL_CONTACT_COUNT_OFFSET: usize = 18;
    const FIRST_MEMBER_OFFSET: usize = PHYSICAL_MOSAIC_CODEC_HEADER_BYTES;
    const FRACTAL_ENTRY_COUNT: usize = 2;
    const MEMBER_RECORD_BYTES: usize = PHYSICAL_MOSAIC_MEMBER_HEADER_BYTES
        + FRACTAL_ENTRY_COUNT * PHYSICAL_MOSAIC_FRACTAL_ENTRY_BYTES;
    const SECOND_MEMBER_OFFSET: usize = FIRST_MEMBER_OFFSET + MEMBER_RECORD_BYTES;
    const THIRD_MEMBER_OFFSET: usize = SECOND_MEMBER_OFFSET + MEMBER_RECORD_BYTES;
    const FIRST_RATIONAL_ENTRY_OFFSET: usize = FIRST_MEMBER_OFFSET
        + PHYSICAL_MOSAIC_MEMBER_HEADER_BYTES
        + PHYSICAL_MOSAIC_FRACTAL_ENTRY_BYTES;
    const FIRST_INTEGRAL_ENTRY_OFFSET: usize =
        FIRST_MEMBER_OFFSET + PHYSICAL_MOSAIC_MEMBER_HEADER_BYTES;
    const FIRST_INTEGRAL_KIND_OFFSET: usize = FIRST_INTEGRAL_ENTRY_OFFSET + 1 + 8;
    const FIRST_INTEGRAL_FIRST_PAYLOAD_OFFSET: usize = FIRST_INTEGRAL_KIND_OFFSET + 1;
    const FIRST_INTEGRAL_SECOND_PAYLOAD_OFFSET: usize = FIRST_INTEGRAL_FIRST_PAYLOAD_OFFSET + 16;
    const FIRST_RATIONAL_KIND_OFFSET: usize = FIRST_RATIONAL_ENTRY_OFFSET + 1 + 8;
    const FIRST_FRACTAL_NUMERATOR_OFFSET: usize = FIRST_RATIONAL_KIND_OFFSET + 1;
    const FIRST_FRACTAL_DENOMINATOR_OFFSET: usize = FIRST_FRACTAL_NUMERATOR_OFFSET + 16;
    const FIRST_ORIGINAL_CONTACT_OFFSET: usize =
        PHYSICAL_MOSAIC_CODEC_HEADER_BYTES + 3 * MEMBER_RECORD_BYTES;

    fn lineage(value: u8) -> StableNeuronLineage {
        let mut lineage = [0; 16];
        lineage[15] = value;
        lineage
    }

    fn neuron_lineages() -> [StableNeuronLineage; 3] {
        [lineage(1), lineage(2), lineage(3)]
    }

    fn topology() -> Vec<StablePhysicalBondReference> {
        vec![
            StablePhysicalBondReference::new(lineage(1), lineage(2), 0).unwrap(),
            StablePhysicalBondReference::new(lineage(2), lineage(3), 0).unwrap(),
        ]
    }

    fn fractal_anatomies() -> [(usize, usize); 3] {
        [(1, 24); 3]
    }

    fn fractal(numerator: i128, denominator: u128) -> SparsePhysicalStateDelta {
        SparsePhysicalStateDelta::from_canonical_entries(vec![
            PhysicalStateDeltaEntry::new(
                PhysicalStateCoordinate::GateOpenPopulation,
                ExactPhysicalStateDelta::Integral(ExactSignedDelta::from_parts(false, 1).unwrap()),
            )
            .unwrap(),
            PhysicalStateDeltaEntry::new(
                PhysicalStateCoordinate::PlasticRestLength,
                ExactPhysicalStateDelta::Rational(
                    ExactRational::new(numerator, denominator).unwrap(),
                ),
            )
            .unwrap(),
        ])
        .unwrap()
    }

    fn exact_recurrence(
        retained: &AdmittedPhysicalMosaic,
    ) -> Vec<(StableNeuronLineage, SparsePhysicalStateDelta)> {
        retained
            .member_lineages()
            .iter()
            .copied()
            .zip(retained.retained_fractals().iter().cloned())
            .collect()
    }

    fn mosaic() -> AdmittedPhysicalMosaic {
        AdmittedPhysicalMosaic {
            original_only: false,
            exact_pattern_recognition: true,
            member_lineages: neuron_lineages().into(),
            retained_fractals: vec![fractal(1, 3), fractal(-7, 11), fractal(i128::MIN, 3)]
                .into_boxed_slice(),
            retained_excitation_zeptojoules: Box::new([]),
            original_bonds: topology().into_boxed_slice(),
            recurrence_bonds: topology().into_boxed_slice(),
            partial_cue_lineages: vec![lineage(1)].into_boxed_slice(),
            recurrence_origin: Some(PhysicalMosaicRecurrenceOrigin::ExternallyObserved),
        }
    }

    fn encoded() -> Vec<u8> {
        encode_admitted_physical_mosaic_for_topology(
            &neuron_lineages(),
            &topology(),
            &fractal_anatomies(),
            &mosaic(),
            1_024,
        )
        .unwrap()
    }

    #[test]
    fn complete_sparse_fractals_round_trip_and_reencode_canonically() {
        let bytes = encoded();
        let decoded = decode_admitted_physical_mosaic_for_topology(
            &neuron_lineages(),
            &topology(),
            &fractal_anatomies(),
            &bytes,
            bytes.len(),
        )
        .unwrap();
        assert_eq!(decoded, mosaic());
        assert_eq!(
            decoded
                .retained_fractals()
                .iter()
                .map(|fractal| {
                    fractal
                        .exact_delta(PhysicalStateCoordinate::PlasticRestLength)
                        .unwrap()
                })
                .collect::<Vec<_>>(),
            vec![
                ExactPhysicalStateDelta::Rational(ExactRational::new(1, 3).unwrap()),
                ExactPhysicalStateDelta::Rational(ExactRational::new(-7, 11).unwrap()),
                ExactPhysicalStateDelta::Rational(ExactRational::new(i128::MIN, 3).unwrap()),
            ]
        );
        assert_eq!(
            encode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &decoded,
                bytes.len(),
            )
            .unwrap(),
            bytes
        );
    }

    #[test]
    fn organism_original_requires_later_physical_recurrence_before_recognition() {
        let original = admit_physical_mosaic_original(
            &neuron_lineages(),
            &fractal_anatomies(),
            &[
                Some(fractal(1, 3)),
                Some(fractal(-7, 11)),
                Some(fractal(5, 13)),
            ],
            &topology(),
        )
        .unwrap();
        assert!(original.is_original_only());
        assert!(original.carries_retained_original_structure());
        assert!(!original.carries_only_retained_neuron_structure());
        let bytes = encode_admitted_physical_mosaic_for_topology(
            &neuron_lineages(),
            &topology(),
            &fractal_anatomies(),
            &original,
            1_024,
        )
        .unwrap();
        assert_eq!(&bytes[..8], ORIGINAL_PHYSICAL_MOSAIC_CODEC_MAGIC);
        let cold = decode_admitted_physical_mosaic_for_topology(
            &neuron_lineages(),
            &topology(),
            &fractal_anatomies(),
            &bytes,
            bytes.len(),
        )
        .unwrap();
        assert_eq!(cold, original);

        let mut mismatched_recurrence = exact_recurrence(&cold);
        mismatched_recurrence[0].1 = fractal(2, 3);
        assert_eq!(
            prove_physical_mosaic_recurrence(
                &cold,
                &mismatched_recurrence,
                &topology(),
                &[lineage(1)],
            ),
            Err(PhysicalMosaicError::RecurrenceDidNotChangeEveryMember)
        );

        let recognized = prove_physical_mosaic_recurrence(
            &cold,
            &exact_recurrence(&cold),
            &topology(),
            &[lineage(1)],
        )
        .unwrap();
        assert!(!recognized.is_original_only());
        assert!(recognized.carries_only_retained_neuron_structure());
        assert_eq!(recognized.original_bonds(), topology());
        assert_eq!(recognized.recurrence_bonds(), topology());
        assert_eq!(recognized.partial_cue_lineages(), &[lineage(1)]);
    }

    #[test]
    fn recognized_organism_formation_replaces_only_a_changed_recurrence_witness() {
        let original = admit_physical_mosaic_original(
            &neuron_lineages(),
            &fractal_anatomies(),
            &[
                Some(fractal(1, 3)),
                Some(fractal(-7, 11)),
                Some(fractal(5, 13)),
            ],
            &topology(),
        )
        .unwrap();
        let recognized = prove_physical_mosaic_recurrence(
            &original,
            &exact_recurrence(&original),
            &topology(),
            &[lineage(1)],
        )
        .unwrap();
        let mut alternate = vec![
            StablePhysicalBondReference::new(lineage(1), lineage(4), 0).unwrap(),
            StablePhysicalBondReference::new(lineage(4), lineage(2), 0).unwrap(),
            StablePhysicalBondReference::new(lineage(2), lineage(3), 0).unwrap(),
        ];
        alternate.sort_unstable();
        let altered = alter_physical_mosaic_recurrence(
            &recognized,
            &exact_recurrence(&recognized),
            &alternate,
            &[lineage(3)],
        )
        .unwrap();

        assert_eq!(altered.member_lineages(), recognized.member_lineages());
        assert_eq!(altered.retained_fractals(), recognized.retained_fractals());
        assert_eq!(altered.original_bonds(), recognized.original_bonds());
        assert_eq!(altered.recurrence_bonds(), alternate);
        assert_eq!(altered.partial_cue_lineages(), &[lineage(3)]);
        assert_eq!(
            alter_physical_mosaic_recurrence(
                &altered,
                &exact_recurrence(&altered),
                &alternate,
                &[lineage(3)],
            ),
            Err(PhysicalMosaicError::RecurrenceDidNotAlterFormation)
        );
    }

    #[test]
    fn recognized_recurrent_flow_does_not_require_absolute_interval_replay() {
        let original = admit_physical_mosaic_original(
            &neuron_lineages(),
            &fractal_anatomies(),
            &[
                Some(fractal(1, 3)),
                Some(fractal(-7, 11)),
                Some(fractal(5, 13)),
            ],
            &topology(),
        )
        .unwrap();
        let recognized = prove_physical_mosaic_recurrence(
            &original,
            &exact_recurrence(&original),
            &topology(),
            &[lineage(1)],
        )
        .unwrap();
        let mut later_living_deltas = exact_recurrence(&recognized);
        later_living_deltas[0].1 = fractal(2, 3);

        assert_eq!(
            alter_physical_mosaic_recurrence(
                &recognized,
                &later_living_deltas,
                &topology(),
                &[lineage(2)],
            ),
            Err(PhysicalMosaicError::RecurrenceDidNotChangeEveryMember)
        );

        let recurrent = alter_recognized_physical_mosaic_recurrence_from_recurrent_flow(
            &recognized,
            &later_living_deltas,
            &topology(),
            &[lineage(2)],
            PhysicalMosaicRecurrenceOrigin::ExternallyObserved,
        )
        .unwrap();
        assert_eq!(recurrent.retained_fractals(), recognized.retained_fractals());
        assert_eq!(recurrent.partial_cue_lineages(), &[lineage(2)]);

        assert_eq!(
            alter_recognized_physical_mosaic_recurrence_from_recurrent_flow(
                &recognized,
                &later_living_deltas[..2],
                &topology(),
                &[lineage(2)],
                PhysicalMosaicRecurrenceOrigin::ExternallyObserved,
            ),
            Err(PhysicalMosaicError::RecurrenceDidNotChangeEveryMember)
        );
    }

    #[test]
    fn internally_simulated_recurrence_retains_origin_and_cold_restores() {
        let external = mosaic();
        let internal = alter_physical_mosaic_recurrence_with_origin(
            &external,
            &exact_recurrence(&external),
            &topology(),
            &neuron_lineages(),
            PhysicalMosaicRecurrenceOrigin::InternallySimulated,
        )
        .unwrap();
        assert_eq!(
            internal.recurrence_origin(),
            Some(PhysicalMosaicRecurrenceOrigin::InternallySimulated)
        );
        let encoded = encode_admitted_physical_mosaic_for_topology(
            &neuron_lineages(),
            &topology(),
            &fractal_anatomies(),
            &internal,
            1_024,
        )
        .unwrap();
        assert_eq!(&encoded[..8], INTERNAL_PHYSICAL_MOSAIC_CODEC_MAGIC);
        let cold = decode_admitted_physical_mosaic_for_topology(
            &neuron_lineages(),
            &topology(),
            &fractal_anatomies(),
            &encoded,
            encoded.len(),
        )
        .unwrap();
        assert_eq!(cold, internal);
        assert_eq!(
            cold.recurrence_origin().map(PhysicalMosaicRecurrenceOrigin::as_str),
            Some("internally_simulated")
        );
    }

    #[test]
    fn transient_integration_cells_can_physically_connect_retained_sensory_fractals() {
        let lineages = [lineage(1), lineage(2), lineage(3), lineage(4), lineage(5)];
        let bonds = vec![
            StablePhysicalBondReference::new(lineage(1), lineage(2), 0).unwrap(),
            StablePhysicalBondReference::new(lineage(2), lineage(3), 0).unwrap(),
            StablePhysicalBondReference::new(lineage(3), lineage(4), 0).unwrap(),
            StablePhysicalBondReference::new(lineage(4), lineage(5), 0).unwrap(),
        ];
        let original = admit_physical_mosaic_original(
            &lineages,
            &[(1, 24); 5],
            &[
                Some(fractal(1, 3)),
                None,
                Some(fractal(2, 3)),
                None,
                Some(fractal(4, 3)),
            ],
            &bonds,
        )
        .unwrap();
        assert_eq!(
            original.member_lineages(),
            &[lineage(1), lineage(3), lineage(5)]
        );
        assert_eq!(original.original_bonds(), bonds);

        let encoded = encode_admitted_physical_mosaic_for_topology(
            &lineages,
            &bonds,
            &[(1, 24); 5],
            &original,
            2_048,
        )
        .unwrap();
        let cold = decode_admitted_physical_mosaic_for_topology(
            &lineages,
            &bonds,
            &[(1, 24); 5],
            &encoded,
            encoded.len(),
        )
        .unwrap();
        let recognized = prove_physical_mosaic_recurrence(
            &cold,
            &exact_recurrence(&cold),
            &bonds,
            &[lineage(1)],
        )
        .unwrap();
        assert_eq!(recognized.recurrence_bonds(), bonds);
    }

    #[test]
    fn stable_lineage_codec_is_independent_of_neuron_enumeration_order() {
        let canonical = encoded();
        let reversed_lineages = [lineage(3), lineage(2), lineage(1)];
        let reversed_anatomies = [(1, 24); 3];
        assert_eq!(
            encode_admitted_physical_mosaic_for_topology(
                &reversed_lineages,
                &topology(),
                &reversed_anatomies,
                &mosaic(),
                canonical.len(),
            )
            .unwrap(),
            canonical
        );
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &reversed_lineages,
                &topology(),
                &reversed_anatomies,
                &canonical,
                canonical.len(),
            )
            .unwrap(),
            mosaic()
        );
    }

    #[test]
    fn malformed_counts_are_rejected_before_allocation() {
        let mut member_count = encoded();
        member_count[MEMBER_COUNT_OFFSET..MEMBER_COUNT_OFFSET + 8]
            .copy_from_slice(&u64::MAX.to_le_bytes());
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &member_count,
                member_count.len(),
            ),
            Err(PhysicalMosaicCodecError::CountOutsideAnatomy)
        );

        let mut contact_count = encoded();
        contact_count[ORIGINAL_CONTACT_COUNT_OFFSET..ORIGINAL_CONTACT_COUNT_OFFSET + 8]
            .copy_from_slice(&3_u64.to_le_bytes());
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &contact_count,
                contact_count.len(),
            ),
            Err(PhysicalMosaicCodecError::CountOutsideAnatomy)
        );
    }

    #[test]
    fn malformed_neuron_and_contact_indices_are_rejected() {
        let mut neuron = encoded();
        neuron[THIRD_MEMBER_OFFSET..THIRD_MEMBER_OFFSET + 16].copy_from_slice(&lineage(4));
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &neuron,
                neuron.len(),
            ),
            Err(PhysicalMosaicCodecError::IndexOutsideAnatomy)
        );

        let mut contact = encoded();
        contact[FIRST_ORIGINAL_CONTACT_OFFSET + 16..FIRST_ORIGINAL_CONTACT_OFFSET + 32]
            .copy_from_slice(&lineage(4));
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &contact,
                contact.len(),
            ),
            Err(PhysicalMosaicCodecError::ContactLeavesFormation)
        );
    }

    #[test]
    fn noncanonical_indices_and_rationals_are_rejected() {
        let mut duplicate_member = encoded();
        duplicate_member[SECOND_MEMBER_OFFSET..SECOND_MEMBER_OFFSET + 16]
            .copy_from_slice(&lineage(1));
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &duplicate_member,
                duplicate_member.len(),
            ),
            Err(PhysicalMosaicCodecError::NonCanonicalIndexOrder)
        );

        let mut noncanonical_ratio = encoded();
        noncanonical_ratio[FIRST_FRACTAL_NUMERATOR_OFFSET..FIRST_FRACTAL_NUMERATOR_OFFSET + 16]
            .copy_from_slice(&2_i128.to_le_bytes());
        noncanonical_ratio[FIRST_FRACTAL_DENOMINATOR_OFFSET..FIRST_FRACTAL_DENOMINATOR_OFFSET + 16]
            .copy_from_slice(&6_u128.to_le_bytes());
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &noncanonical_ratio,
                noncanonical_ratio.len(),
            ),
            Err(PhysicalMosaicCodecError::InvalidRetainedFractal)
        );
    }

    #[test]
    fn physically_impossible_coordinate_delta_kind_pairs_are_rejected() {
        let mut rational_gate_population = encoded();
        rational_gate_population[FIRST_INTEGRAL_KIND_OFFSET] = 1;
        rational_gate_population
            [FIRST_INTEGRAL_FIRST_PAYLOAD_OFFSET..FIRST_INTEGRAL_FIRST_PAYLOAD_OFFSET + 16]
            .copy_from_slice(&1_i128.to_le_bytes());
        rational_gate_population
            [FIRST_INTEGRAL_SECOND_PAYLOAD_OFFSET..FIRST_INTEGRAL_SECOND_PAYLOAD_OFFSET + 16]
            .copy_from_slice(&1_u128.to_le_bytes());
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &rational_gate_population,
                rational_gate_population.len(),
            ),
            Err(PhysicalMosaicCodecError::InvalidRetainedFractal)
        );

        let mut integral_rest_length = encoded();
        integral_rest_length[FIRST_RATIONAL_KIND_OFFSET] = 0;
        integral_rest_length[FIRST_FRACTAL_NUMERATOR_OFFSET..FIRST_FRACTAL_NUMERATOR_OFFSET + 16]
            .copy_from_slice(&1_u128.to_le_bytes());
        integral_rest_length
            [FIRST_FRACTAL_DENOMINATOR_OFFSET..FIRST_FRACTAL_DENOMINATOR_OFFSET + 16]
            .copy_from_slice(&0_u128.to_le_bytes());
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &integral_rest_length,
                integral_rest_length.len(),
            ),
            Err(PhysicalMosaicCodecError::InvalidRetainedFractal)
        );
    }

    #[test]
    fn truncation_trailing_bytes_and_budget_excess_are_distinct() {
        let bytes = encoded();
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &bytes[..bytes.len() - 1],
                bytes.len(),
            ),
            Err(PhysicalMosaicCodecError::Truncated)
        );
        let mut trailing = bytes.clone();
        trailing.push(0);
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &trailing,
                trailing.len(),
            ),
            Err(PhysicalMosaicCodecError::TrailingBytes)
        );
        assert_eq!(
            decode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &bytes,
                bytes.len() - 1,
            ),
            Err(PhysicalMosaicCodecError::BudgetExceeded)
        );
    }

    #[test]
    fn disconnected_or_foreign_contact_state_cannot_be_encoded() {
        let mut disconnected = mosaic();
        disconnected.original_bonds = vec![topology()[0]].into_boxed_slice();
        assert_eq!(
            encode_admitted_physical_mosaic_for_topology(
                &neuron_lineages(),
                &topology(),
                &fractal_anatomies(),
                &disconnected,
                1_024,
            ),
            Err(PhysicalMosaicCodecError::OriginalRelationNotConnected)
        );

        let foreign_topology = vec![
            StablePhysicalBondReference::new(lineage(1), lineage(2), 0).unwrap(),
            StablePhysicalBondReference::new(lineage(2), lineage(4), 0).unwrap(),
        ];
        let foreign_lineages = [lineage(1), lineage(2), lineage(3), lineage(4)];
        assert_eq!(
            encode_admitted_physical_mosaic_for_topology(
                &foreign_lineages,
                &foreign_topology,
                &[(1, 24); 4],
                &mosaic(),
                1_024,
            ),
            Err(PhysicalMosaicCodecError::ContactLeavesFormation)
        );
    }
}
