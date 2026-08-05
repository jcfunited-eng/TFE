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
    ExactPhysicalStateDelta, ExactSignedDelta, PhysicalStateCoordinate, PhysicalStateDeltaEntry,
    SparsePhysicalStateDelta,
};
use crate::exact_rational::ExactRational;
use crate::reached_neuron_cohort::{
    ReachedCohortAnatomy, ReachedCohortPostExperienceSettlement, ReachedCohortRecurrenceSettlement,
};
use std::collections::VecDeque;

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
    InvalidRetainedFractal,
}

pub(crate) type StableNeuronLineage = [u8; 16];

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
    member_lineages: Box<[StableNeuronLineage]>,
    retained_fractals: Box<[SparsePhysicalStateDelta]>,
    original_bonds: Box<[StablePhysicalBondReference]>,
    recurrence_bonds: Box<[StablePhysicalBondReference]>,
    partial_cue_lineages: Box<[StableNeuronLineage]>,
}

impl AdmittedPhysicalMosaic {
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
    let (member_lineages, retained_fractals): (Vec<_>, Vec<_>) =
        member_fractals.into_iter().unzip();
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
        member_lineages: member_lineages.into_boxed_slice(),
        retained_fractals: retained_fractals.into_boxed_slice(),
        original_bonds: original_bonds.into_boxed_slice(),
        recurrence_bonds: recurrence_bonds.into_boxed_slice(),
        partial_cue_lineages: partial_cue_lineages.into_boxed_slice(),
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

const PHYSICAL_MOSAIC_CODEC_MAGIC: &[u8; 8] = b"GLMOS003";
const PHYSICAL_MOSAIC_CODEC_VERSION: u16 = 3;
const PHYSICAL_MOSAIC_CODEC_HEADER_BYTES: usize = 8 + 2 + 4 * 8;
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

fn encode_admitted_physical_mosaic_for_topology(
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
    encoded.extend_from_slice(PHYSICAL_MOSAIC_CODEC_MAGIC);
    encoded.extend_from_slice(&PHYSICAL_MOSAIC_CODEC_VERSION.to_le_bytes());
    push_codec_usize(&mut encoded, mosaic.member_lineages.len())?;
    push_codec_usize(&mut encoded, mosaic.original_bonds.len())?;
    push_codec_usize(&mut encoded, mosaic.recurrence_bonds.len())?;
    push_codec_usize(&mut encoded, mosaic.partial_cue_lineages.len())?;
    for (lineage, fractal) in mosaic
        .member_lineages
        .iter()
        .zip(mosaic.retained_fractals.iter())
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
            }
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

fn decode_admitted_physical_mosaic_for_topology(
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
    if reader.take(PHYSICAL_MOSAIC_CODEC_MAGIC.len())? != PHYSICAL_MOSAIC_CODEC_MAGIC {
        return Err(PhysicalMosaicCodecError::HeaderMismatch);
    }
    if reader.u16()? != PHYSICAL_MOSAIC_CODEC_VERSION {
        return Err(PhysicalMosaicCodecError::VersionMismatch);
    }
    let member_count = reader.usize()?;
    let original_contact_count = reader.usize()?;
    let recurrence_contact_count = reader.usize()?;
    let cue_count = reader.usize()?;
    validate_codec_counts(
        neuron_lineages.len(),
        bonds.len(),
        member_count,
        original_contact_count,
        recurrence_contact_count,
        cue_count,
    )?;
    if fractal_anatomies.len() != neuron_lineages.len() {
        return Err(PhysicalMosaicCodecError::CountOutsideAnatomy);
    }

    let mut member_lineages = Vec::new();
    let mut retained_fractals = Vec::new();
    let mut original_bonds = Vec::new();
    let mut recurrence_bonds = Vec::new();
    let mut partial_cue_lineages = Vec::new();
    member_lineages
        .try_reserve_exact(member_count)
        .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;
    retained_fractals
        .try_reserve_exact(member_count)
        .map_err(|_| PhysicalMosaicCodecError::AllocationFailed)?;
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
        member_lineages: member_lineages.into_boxed_slice(),
        retained_fractals: retained_fractals.into_boxed_slice(),
        original_bonds: original_bonds.into_boxed_slice(),
        recurrence_bonds: recurrence_bonds.into_boxed_slice(),
        partial_cue_lineages: partial_cue_lineages.into_boxed_slice(),
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
        PhysicalStateCoordinate::OpticalQuantumResidue => (24, 0),
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
        24 if index == 0 => PhysicalStateCoordinate::OpticalQuantumResidue,
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
) -> Result<(), PhysicalMosaicCodecError> {
    if member_count < 3
        || member_count > neuron_count
        || original_contact_count > contact_count
        || recurrence_contact_count > contact_count
        || cue_count == 0
        || cue_count >= member_count
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
    )?;
    if fractal_anatomies.len() != neuron_lineages.len()
        || mosaic.member_lineages.len() != mosaic.retained_fractals.len()
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
            || mosaic.member_lineages.binary_search(&left).is_err()
            || mosaic.member_lineages.binary_search(&right).is_err()
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
    if !mosaic_lineages_connect(
        &mosaic.member_lineages,
        &mosaic.recurrence_bonds,
        &mosaic.partial_cue_lineages,
    ) {
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
                if members.binary_search(&neighbour).is_ok() && !reached.contains(&neighbour) {
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

    fn mosaic() -> AdmittedPhysicalMosaic {
        AdmittedPhysicalMosaic {
            member_lineages: neuron_lineages().into(),
            retained_fractals: vec![fractal(1, 3), fractal(-7, 11), fractal(i128::MIN, 3)]
                .into_boxed_slice(),
            original_bonds: topology().into_boxed_slice(),
            recurrence_bonds: topology().into_boxed_slice(),
            partial_cue_lineages: vec![lineage(1)].into_boxed_slice(),
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
