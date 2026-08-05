//! Canonical immutable evidence objects for one bounded causal occurrence.
//!
//! This module is deliberately unmounted. It defines byte-exact field and
//! DSF-delivery-impression objects; it does not index, retain, recall, recognize, or
//! form cognition. Full joint DSF field bodies remain explicit in the field
//! object. Object addresses are transport integrity, never physical authority.

use crate::joint_field_l0_l4::{
    bind_neuron_perspective, derive_requirement, run_joint_field_l0_l4,
    verify_dsf_delivery_impression, Availability, DsfDeliveryImpression, DsfDeliveryRecurrence,
    Exact, JointFieldBudget, JointFieldInput, L4JointDsf, NeuronFieldPerspective, RelationFact,
    StructuralTrit,
};
use num_bigint::{BigInt, Sign};
use num_rational::BigRational;
use num_traits::Zero;
use sha2::{Digest, Sha256};
use std::fmt;
use std::mem::size_of;
use std::sync::Arc;

const FIELD_MAGIC: &[u8; 8] = b"GLCFIELD";
const DELIVERY_IMPRESSION_MAGIC: &[u8; 8] = b"GLCDSFDI";
const VERSION: u16 = 1;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct ContentAddress(pub(crate) [u8; 32]);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ObjectKind {
    CompleteField,
    DsfDeliveryImpression,
    Occurrence,
    RetiredHippocampalReferencePage,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ImmutableObject {
    pub(crate) kind: ObjectKind,
    pub(crate) address: ContentAddress,
    pub(crate) bytes: Vec<u8>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct EvidenceBudget {
    pub(crate) max_object_bytes: usize,
    pub(crate) max_serialized_batch_bytes: usize,
    /// Logical retained bodies plus explicit codec temporaries. Internal
    /// num-bigint GCD/division scratch is bounded indirectly by exact-component
    /// admission but is not observable for byte-exact charging.
    pub(crate) max_peak_live_bytes: usize,
    /// Exact count of transition entries a caller admits for one bounded
    /// navigation operation. Required work is derived from observed cohorts.
    pub(crate) max_transition_work: usize,
    pub(crate) max_objects: usize,
    pub(crate) max_vertices: usize,
    pub(crate) max_frames: usize,
    pub(crate) max_edges: usize,
    pub(crate) max_groups: usize,
    pub(crate) max_group_members: usize,
    pub(crate) max_exact_component_bytes: usize,
    pub(crate) max_delivery_impression_coordinates: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ObjectRequirement {
    pub(crate) bytes: usize,
    pub(crate) decoded_working_bytes: usize,
    pub(crate) vertices: usize,
    pub(crate) frames: usize,
    pub(crate) edges: usize,
    pub(crate) groups: usize,
    pub(crate) group_members: usize,
    pub(crate) exact_component_bytes: usize,
    pub(crate) largest_exact_component_bytes: usize,
    pub(crate) delivery_impression_coordinates: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum EvidenceError {
    Invalid(&'static str),
    ArithmeticOverflow,
    AllocationFailed,
    BudgetExceeded {
        resource: &'static str,
        required: usize,
        available: usize,
    },
}

impl fmt::Display for EvidenceError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(reason) => write!(output, "invalid canonical evidence: {reason}"),
            Self::ArithmeticOverflow => write!(output, "canonical evidence arithmetic overflow"),
            Self::AllocationFailed => write!(output, "canonical evidence allocation failed"),
            Self::BudgetExceeded {
                resource,
                required,
                available,
            } => write!(
                output,
                "canonical evidence {resource} requires {required}, available {available}"
            ),
        }
    }
}

impl std::error::Error for EvidenceError {}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct DecodedDeliveryImpression {
    pub(crate) perspective: NeuronFieldPerspective,
    pub(crate) delivery_impression: DsfDeliveryImpression,
}

pub(crate) fn content_address(bytes: &[u8]) -> ContentAddress {
    ContentAddress(Sha256::digest(bytes).into())
}

pub(crate) fn immutable_object(kind: ObjectKind, bytes: Vec<u8>) -> ImmutableObject {
    ImmutableObject {
        kind,
        address: content_address(&bytes),
        bytes,
    }
}

fn checked_add(left: usize, right: usize) -> Result<usize, EvidenceError> {
    left.checked_add(right)
        .ok_or(EvidenceError::ArithmeticOverflow)
}

fn checked_mul(left: usize, right: usize) -> Result<usize, EvidenceError> {
    left.checked_mul(right)
        .ok_or(EvidenceError::ArithmeticOverflow)
}

fn checked_max(values: &[usize]) -> usize {
    values.iter().copied().max().unwrap_or(0)
}

fn fixed_array<const N: usize>(value: &[u8]) -> Result<[u8; N], EvidenceError> {
    value
        .try_into()
        .map_err(|_| EvidenceError::Invalid("fixed-width component changed"))
}

fn require(resource: &'static str, required: usize, available: usize) -> Result<(), EvidenceError> {
    if required > available {
        return Err(EvidenceError::BudgetExceeded {
            resource,
            required,
            available,
        });
    }
    Ok(())
}

fn signed_bytes_len(value: &BigInt) -> Result<usize, EvidenceError> {
    let bits = usize::try_from(value.bits()).map_err(|_| EvidenceError::ArithmeticOverflow)?;
    if bits == 0 {
        return Ok(1);
    }
    let magnitude_bytes = checked_add(bits, 7)? / 8;
    let sign_extension = usize::from(
        bits % 8 == 0 && (value.sign() != Sign::Minus || value.magnitude().count_ones() != 1),
    );
    checked_add(magnitude_bytes, sign_extension)
}

fn exact_component_bytes(value: &Exact) -> Result<usize, EvidenceError> {
    checked_add(
        signed_bytes_len(value.numer())?,
        signed_bytes_len(value.denom())?,
    )
}

fn bigint_heap_bytes(value: &BigInt) -> Result<usize, EvidenceError> {
    let bits = usize::try_from(value.bits()).map_err(|_| EvidenceError::ArithmeticOverflow)?;
    if bits == 0 {
        return Ok(0);
    }
    let word_bits = size_of::<usize>()
        .checked_mul(8)
        .ok_or(EvidenceError::ArithmeticOverflow)?;
    let words = checked_add(bits, word_bits - 1)? / word_bits;
    checked_mul(words, size_of::<usize>())
}

pub(crate) fn exact_heap_bytes(value: &Exact) -> Result<usize, EvidenceError> {
    checked_add(
        bigint_heap_bytes(value.numer())?,
        bigint_heap_bytes(value.denom())?,
    )
}

pub(crate) fn encoded_exact_bytes(value: &Exact) -> Result<usize, EvidenceError> {
    checked_add(8, exact_component_bytes(value)?)
}

fn add_exact(
    bytes: &mut usize,
    exact_bytes: &mut usize,
    largest_component: &mut usize,
    value: &Exact,
) -> Result<(), EvidenceError> {
    *bytes = checked_add(*bytes, encoded_exact_bytes(value)?)?;
    *exact_bytes = checked_add(*exact_bytes, exact_component_bytes(value)?)?;
    *largest_component = (*largest_component)
        .max(signed_bytes_len(value.numer())?)
        .max(signed_bytes_len(value.denom())?);
    Ok(())
}

fn add_exact_heap(total: &mut usize, value: &Exact) -> Result<(), EvidenceError> {
    *total = checked_add(*total, exact_heap_bytes(value)?)?;
    Ok(())
}

fn add_exact_slice_working(total: &mut usize, values: &Vec<Exact>) -> Result<(), EvidenceError> {
    *total = checked_add(*total, checked_mul(values.capacity(), size_of::<Exact>())?)?;
    for value in values {
        add_exact_heap(total, value)?;
    }
    Ok(())
}

fn add_exact_matrix_working(
    total: &mut usize,
    values: &Vec<Vec<Exact>>,
) -> Result<(), EvidenceError> {
    *total = checked_add(
        *total,
        checked_mul(values.capacity(), size_of::<Vec<Exact>>())?,
    )?;
    for row in values {
        add_exact_slice_working(total, row)?;
    }
    Ok(())
}

fn add_relation_slice_working(
    total: &mut usize,
    values: &Vec<RelationFact>,
) -> Result<(), EvidenceError> {
    *total = checked_add(
        *total,
        checked_mul(values.capacity(), size_of::<RelationFact>())?,
    )?;
    for value in values {
        for component in [
            &value.prior_product,
            &value.current_product,
            &value.displacement_product,
            &value.oriented_area,
        ] {
            add_exact_heap(total, component)?;
        }
    }
    Ok(())
}

fn measure_field_working_bytes(value: &L4JointDsf) -> Result<usize, EvidenceError> {
    let l3 = value.l3.as_ref();
    let l2 = l3.l2.as_ref();
    let l1 = l2.l1.as_ref();
    let l0 = l1.l0.as_ref();
    let input = l0.input.as_ref();
    let mut total = size_of::<L4JointDsf>();
    for bytes in [
        size_of::<crate::joint_field_l0_l4::L3ResonanceField>(),
        size_of::<crate::joint_field_l0_l4::L2Geometry>(),
        size_of::<crate::joint_field_l0_l4::L1Vtvr>(),
        size_of::<crate::joint_field_l0_l4::L0JointField>(),
        size_of::<JointFieldInput>(),
        checked_mul(6, checked_mul(2, size_of::<usize>())?)?,
    ] {
        total = checked_add(total, bytes)?;
    }
    total = checked_add(
        total,
        checked_mul(input.vertex_ids.capacity(), size_of::<String>())?,
    )?;
    for vertex in &input.vertex_ids {
        total = checked_add(total, vertex.capacity())?;
    }
    total = checked_add(
        total,
        checked_mul(input.groups.capacity(), size_of::<Vec<usize>>())?,
    )?;
    for group in &input.groups {
        total = checked_add(total, checked_mul(group.capacity(), size_of::<usize>())?)?;
    }
    add_exact_slice_working(&mut total, &input.times)?;
    add_exact_matrix_working(&mut total, &input.vectors)?;
    total = checked_add(
        total,
        checked_mul(l0.edges.capacity(), size_of::<(usize, usize)>())?,
    )?;
    total = checked_add(
        total,
        checked_mul(
            l0.frames.capacity(),
            size_of::<crate::joint_field_l0_l4::L0Frame>(),
        )?,
    )?;
    for frame in &l0.frames {
        add_exact_heap(&mut total, &frame.time)?;
        add_exact_heap(&mut total, &frame.delta_time)?;
        add_exact_slice_working(&mut total, &frame.vector)?;
        add_exact_slice_working(&mut total, &frame.displacement)?;
        add_exact_slice_working(&mut total, &frame.volume)?;
        add_relation_slice_working(&mut total, &frame.relation)?;
        total = checked_add(total, frame.observed_zero_groups.capacity().div_ceil(8))?;
    }
    add_exact_slice_working(&mut total, &l1.accumulated_volume)?;
    add_exact_matrix_working(&mut total, &l2.velocity)?;
    add_exact_matrix_working(&mut total, &l2.acceleration)?;
    total = checked_add(
        total,
        checked_mul(
            l2.relation_change.capacity(),
            size_of::<Vec<RelationFact>>(),
        )?,
    )?;
    for frame in &l2.relation_change {
        add_relation_slice_working(&mut total, frame)?;
    }
    add_exact_matrix_working(&mut total, &value.d_k)?;
    add_exact_matrix_working(&mut total, &value.m_k)?;
    total = checked_add(
        total,
        checked_mul(value.r_rev_k.capacity(), size_of::<Vec<bool>>())?,
    )?;
    for frame in &value.r_rev_k {
        total = checked_add(total, frame.capacity().div_ceil(8))?;
    }
    total = checked_add(
        total,
        checked_mul(value.u_star_k.capacity(), size_of::<Vec<Availability>>())?,
    )?;
    for frame in &value.u_star_k {
        total = checked_add(
            total,
            checked_mul(frame.capacity(), size_of::<Availability>())?,
        )?;
    }
    add_exact_matrix_working(&mut total, &value.p_k)?;
    add_exact_matrix_working(&mut total, &value.b_k)?;
    Ok(total)
}

fn measure_delivery_impression_working_bytes(
    perspective: &NeuronFieldPerspective,
    delivery_impression: &DsfDeliveryImpression,
) -> Result<usize, EvidenceError> {
    let mut total = checked_add(
        size_of::<NeuronFieldPerspective>(),
        size_of::<DsfDeliveryImpression>(),
    )?;
    for value in [
        &perspective.d_k,
        &perspective.m_k,
        &perspective.p_k,
        &perspective.b_k,
    ] {
        add_exact_heap(&mut total, value)?;
    }
    total = checked_add(
        total,
        checked_mul(
            perspective.incident_cohesion_edges.capacity(),
            size_of::<usize>(),
        )?,
    )?;
    total = checked_add(
        total,
        checked_mul(
            delivery_impression.delivery_sign_impression.capacity(),
            size_of::<StructuralTrit>(),
        )?,
    )?;
    Ok(total)
}

fn bigint_heap_upper_from_bits(bits: usize) -> Result<usize, EvidenceError> {
    if bits == 0 {
        return Ok(0);
    }
    let word_bits = checked_mul(size_of::<usize>(), 8)?;
    let words = checked_add(bits, word_bits - 1)? / word_bits;
    checked_mul(words, size_of::<usize>())
}

fn exact_heap_upper_from_bits(bits: usize) -> Result<usize, EvidenceError> {
    checked_mul(2, bigint_heap_upper_from_bits(bits)?)
}

pub(crate) fn exact_parse_logical_temporary_bytes(
    largest_component_bytes: usize,
) -> Result<usize, EvidenceError> {
    let component_bits = checked_mul(largest_component_bytes.max(1), 8)?;
    // Ratio normalization logically retains numerator, denominator, gcd, one
    // gcd clone, and one quotient. Allocator-private arithmetic scratch is not
    // observable; max_exact_component_bytes independently bounds its operands.
    checked_add(
        checked_mul(5, bigint_heap_upper_from_bits(component_bits)?)?,
        largest_component_bytes,
    )
}

#[allow(clippy::too_many_arguments)]
fn decoded_field_working_upper(
    vertices: usize,
    frames: usize,
    edges: usize,
    groups: usize,
    group_members: usize,
    string_bytes: usize,
    largest_component_bytes: usize,
) -> Result<usize, EvidenceError> {
    let base_bits = checked_mul(largest_component_bytes.max(1), 8)?;
    let normalized = checked_mul(vertices.max(1), checked_add(base_bits, 2)?)?;
    let displacement = checked_add(checked_mul(2, normalized)?, 1)?;
    let delta_time = checked_add(checked_mul(2, base_bits)?, 1)?;
    let volume = checked_add(displacement, delta_time)?;
    let relation = checked_max(&[
        checked_mul(2, normalized)?,
        checked_mul(2, displacement)?,
        checked_add(checked_mul(2, normalized)?, 1)?,
    ]);
    let accumulated = checked_mul(frames.max(1), checked_add(volume, 1)?)?;
    let velocity = checked_add(displacement, delta_time)?;
    let acceleration = checked_add(checked_add(checked_mul(2, velocity)?, delta_time)?, 1)?;
    let relation_change = checked_add(checked_mul(2, relation)?, 1)?;
    let breathing = checked_add(checked_mul(2, volume)?, 1)?;
    let largest_derived_bits = checked_max(&[
        base_bits,
        normalized,
        displacement,
        delta_time,
        volume,
        relation,
        accumulated,
        velocity,
        acceleration,
        relation_change,
        breathing,
    ]);
    let relation_count = checked_mul(2, checked_mul(frames, edges)?)?;
    let input_exact = checked_mul(frames, checked_add(vertices, 1)?)?;
    let l0_exact = checked_mul(frames, checked_add(2, checked_mul(3, vertices)?)?)?;
    let l2_exact = checked_mul(2, checked_mul(frames, vertices)?)?;
    let l4_exact = checked_mul(4, checked_mul(frames, vertices)?)?;
    let nonrelation_exact = checked_add(
        checked_add(input_exact, l0_exact)?,
        checked_add(vertices, checked_add(l2_exact, l4_exact)?)?,
    )?;
    let heap_exact_count = checked_add(nonrelation_exact, checked_mul(4, relation_count)?)?;
    let exact_heap = checked_mul(
        heap_exact_count,
        exact_heap_upper_from_bits(largest_derived_bits)?,
    )?;
    let nested_vectors = checked_add(groups, checked_mul(10, frames)?)?;
    let bool_bytes = checked_add(
        checked_mul(frames, groups.div_ceil(8))?,
        checked_add(
            checked_mul(frames, vertices.div_ceil(8))?,
            checked_mul(checked_mul(frames, vertices)?, size_of::<Availability>())?,
        )?,
    )?;
    let mut total = 0usize;
    for bytes in [
        size_of::<L4JointDsf>(),
        size_of::<crate::joint_field_l0_l4::L3ResonanceField>(),
        size_of::<crate::joint_field_l0_l4::L2Geometry>(),
        size_of::<crate::joint_field_l0_l4::L1Vtvr>(),
        size_of::<crate::joint_field_l0_l4::L0JointField>(),
        size_of::<JointFieldInput>(),
        checked_mul(6, checked_mul(2, size_of::<usize>())?)?,
        checked_mul(vertices, size_of::<String>())?,
        string_bytes,
        checked_mul(nested_vectors, size_of::<Vec<Exact>>())?,
        checked_mul(group_members, size_of::<usize>())?,
        checked_mul(edges, size_of::<(usize, usize)>())?,
        checked_mul(frames, size_of::<crate::joint_field_l0_l4::L0Frame>())?,
        checked_mul(nonrelation_exact, size_of::<Exact>())?,
        checked_mul(relation_count, size_of::<RelationFact>())?,
        bool_bytes,
        exact_heap,
    ] {
        total = checked_add(total, bytes)?;
    }
    Ok(total)
}

fn decoded_delivery_impression_working_upper(
    edges: usize,
    coordinates: usize,
    largest_component_bytes: usize,
) -> Result<usize, EvidenceError> {
    let exact_heap = checked_mul(
        4,
        exact_heap_upper_from_bits(checked_mul(largest_component_bytes.max(1), 8)?)?,
    )?;
    checked_add(
        checked_add(
            size_of::<NeuronFieldPerspective>(),
            size_of::<DsfDeliveryImpression>(),
        )?,
        checked_add(
            checked_mul(edges, size_of::<usize>())?,
            checked_add(
                checked_mul(coordinates, size_of::<StructuralTrit>())?,
                exact_heap,
            )?,
        )?,
    )
}

fn validate_full_field(value: &L4JointDsf, budget: EvidenceBudget) -> Result<(), EvidenceError> {
    let input = value.l3.l2.l1.l0.input.as_ref();
    let requirement =
        derive_requirement(input).map_err(|_| EvidenceError::Invalid("field input"))?;
    require("vertices", requirement.vertices, budget.max_vertices)?;
    require("frames", requirement.frames, budget.max_frames)?;
    require("edges", requirement.edges, budget.max_edges)?;
    let rebuilt = run_joint_field_l0_l4(
        input.clone(),
        JointFieldBudget {
            max_input_bytes: requirement.input_bytes,
            max_vertices: requirement.vertices,
            max_frames: requirement.frames,
            max_edges: requirement.edges,
            max_relation_facts: requirement.relation_facts,
            max_vertex_frame_values: requirement.vertex_frame_values,
        },
    )
    .map_err(|_| EvidenceError::Invalid("field does not reconstruct"))?;
    if rebuilt.l4.as_ref() != value {
        return Err(EvidenceError::Invalid(
            "field body differs from exact L0-L4 reconstruction",
        ));
    }
    Ok(())
}

pub(crate) fn measure_complete_field(
    value: &L4JointDsf,
    budget: EvidenceBudget,
) -> Result<ObjectRequirement, EvidenceError> {
    let input = value.l3.l2.l1.l0.input.as_ref();
    let vertices = input.vertex_ids.len();
    let frames = input.times.len();
    let edges = value.l3.l2.l1.l0.edges.len();
    let groups = input.groups.len();
    let group_members = input
        .groups
        .iter()
        .try_fold(0usize, |total, group| checked_add(total, group.len()))?;
    require("groups", groups, budget.max_groups)?;
    require("group members", group_members, budget.max_group_members)?;

    let mut bytes = checked_add(FIELD_MAGIC.len(), 2)?;
    let mut exact_bytes = 0usize;
    let mut largest_exact_component_bytes = 0usize;
    bytes = checked_add(bytes, 4)?;
    for vertex_id in &input.vertex_ids {
        bytes = checked_add(bytes, checked_add(4, vertex_id.len())?)?;
    }
    bytes = checked_add(bytes, 4)?;
    for group in &input.groups {
        bytes = checked_add(bytes, checked_add(4, checked_mul(group.len(), 8)?)?)?;
    }
    bytes = checked_add(bytes, 4)?;
    for time in &input.times {
        add_exact(
            &mut bytes,
            &mut exact_bytes,
            &mut largest_exact_component_bytes,
            time,
        )?;
    }
    bytes = checked_add(bytes, 4)?;
    for vector in &input.vectors {
        bytes = checked_add(bytes, 4)?;
        for value in vector {
            add_exact(
                &mut bytes,
                &mut exact_bytes,
                &mut largest_exact_component_bytes,
                value,
            )?;
        }
    }
    bytes = checked_add(bytes, 12)?;
    for frame in 0..frames {
        for vertex in 0..vertices {
            let d_k = value
                .d_k
                .get(frame)
                .and_then(|row| row.get(vertex))
                .ok_or(EvidenceError::Invalid("D_k field shape changed"))?;
            let m_k = value
                .m_k
                .get(frame)
                .and_then(|row| row.get(vertex))
                .ok_or(EvidenceError::Invalid("M_k field shape changed"))?;
            let p_k = value
                .p_k
                .get(frame)
                .and_then(|row| row.get(vertex))
                .ok_or(EvidenceError::Invalid("P_k field shape changed"))?;
            let b_k = value
                .b_k
                .get(frame)
                .and_then(|row| row.get(vertex))
                .ok_or(EvidenceError::Invalid("B_k field shape changed"))?;
            value
                .r_rev_k
                .get(frame)
                .and_then(|row| row.get(vertex))
                .ok_or(EvidenceError::Invalid("R_rev_k field shape changed"))?;
            value
                .u_star_k
                .get(frame)
                .and_then(|row| row.get(vertex))
                .ok_or(EvidenceError::Invalid("U_star_k field shape changed"))?;
            for value in [d_k, m_k, p_k, b_k] {
                add_exact(
                    &mut bytes,
                    &mut exact_bytes,
                    &mut largest_exact_component_bytes,
                    value,
                )?;
            }
            bytes = checked_add(bytes, 2)?;
        }
        for relation in value
            .cohesion(frame)
            .ok_or(EvidenceError::Invalid("cohesion frame is absent"))?
        {
            bytes = checked_add(bytes, 16)?;
            for component in [
                &relation.prior_product,
                &relation.current_product,
                &relation.displacement_product,
                &relation.oriented_area,
            ] {
                add_exact(
                    &mut bytes,
                    &mut exact_bytes,
                    &mut largest_exact_component_bytes,
                    component,
                )?;
            }
        }
    }
    bytes = checked_add(bytes, 32)?;
    require(
        "exact component bytes",
        exact_bytes,
        budget.max_exact_component_bytes,
    )?;
    require("object bytes", bytes, budget.max_object_bytes)?;
    Ok(ObjectRequirement {
        bytes,
        decoded_working_bytes: measure_field_working_bytes(value)?,
        vertices,
        frames,
        edges,
        groups,
        group_members,
        exact_component_bytes: exact_bytes,
        largest_exact_component_bytes,
        delivery_impression_coordinates: 0,
    })
}

pub(crate) fn encode_complete_field(
    value: &L4JointDsf,
    budget: EvidenceBudget,
) -> Result<Vec<u8>, EvidenceError> {
    let requirement = measure_complete_field(value, budget)?;
    let validation_peak = checked_mul(2, requirement.decoded_working_bytes)?;
    let encoding_peak = checked_add(
        requirement.decoded_working_bytes,
        checked_add(requirement.bytes, requirement.largest_exact_component_bytes)?,
    )?;
    require(
        "peak live bytes",
        validation_peak.max(encoding_peak),
        budget.max_peak_live_bytes,
    )?;
    // Measurement is allocation-free. Exact reconstruction starts only after
    // the caller has admitted the measured resource requirement.
    validate_full_field(value, budget)?;
    encode_complete_field_measured(value, requirement)
}

fn encode_complete_field_measured(
    value: &L4JointDsf,
    requirement: ObjectRequirement,
) -> Result<Vec<u8>, EvidenceError> {
    let mut output = Vec::new();
    output
        .try_reserve_exact(requirement.bytes)
        .map_err(|_| EvidenceError::AllocationFailed)?;
    output.extend_from_slice(FIELD_MAGIC);
    output.extend_from_slice(&VERSION.to_le_bytes());
    encode_input(&mut output, value.l3.l2.l1.l0.input.as_ref())?;
    push_u32(&mut output, requirement.frames)?;
    push_u32(&mut output, requirement.vertices)?;
    push_u32(&mut output, requirement.edges)?;
    for frame in 0..requirement.frames {
        for vertex in 0..requirement.vertices {
            push_exact(&mut output, &value.d_k[frame][vertex])?;
            push_exact(&mut output, &value.m_k[frame][vertex])?;
            output.push(u8::from(value.r_rev_k[frame][vertex]));
            output.push(match value.u_star_k[frame][vertex] {
                Availability::Genesis => 0,
                Availability::Observed => 1,
            });
            push_exact(&mut output, &value.p_k[frame][vertex])?;
            push_exact(&mut output, &value.b_k[frame][vertex])?;
        }
        for relation in value
            .cohesion(frame)
            .ok_or(EvidenceError::Invalid("cohesion frame is absent"))?
        {
            encode_relation(&mut output, relation)?;
        }
    }
    output.extend_from_slice(&value.authority_receipt_sha256);
    if output.len() != requirement.bytes {
        return Err(EvidenceError::Invalid(
            "field measurement differs from encoding",
        ));
    }
    Ok(output)
}

pub(crate) fn decode_complete_field(
    bytes: &[u8],
    budget: EvidenceBudget,
) -> Result<Arc<L4JointDsf>, EvidenceError> {
    let requirement = scan_complete_field_requirement(bytes, budget)?;
    require(
        "peak live bytes",
        checked_add(
            bytes.len(),
            checked_add(
                requirement.decoded_working_bytes,
                exact_parse_logical_temporary_bytes(requirement.largest_exact_component_bytes)?,
            )?,
        )?,
        budget.max_peak_live_bytes,
    )?;
    let mut parser = Parser::new(bytes);
    parser.expect(FIELD_MAGIC)?;
    parser.version()?;
    let input = parser.input()?;
    let derived = derive_requirement(&input).map_err(|_| EvidenceError::Invalid("field input"))?;
    let rebuilt = run_joint_field_l0_l4(
        input,
        JointFieldBudget {
            max_input_bytes: derived.input_bytes,
            max_vertices: derived.vertices,
            max_frames: derived.frames,
            max_edges: derived.edges,
            max_relation_facts: derived.relation_facts,
            max_vertex_frame_values: derived.vertex_frame_values,
        },
    )
    .map_err(|_| EvidenceError::Invalid("field does not reconstruct"))?;
    if parser.u32()? as usize != derived.frames
        || parser.u32()? as usize != derived.vertices
        || parser.u32()? as usize != derived.edges
    {
        return Err(EvidenceError::Invalid("field dimensions changed"));
    }
    for frame in 0..derived.frames {
        for vertex in 0..derived.vertices {
            if !parser.exact_matches(&rebuilt.l4.d_k[frame][vertex])?
                || !parser.exact_matches(&rebuilt.l4.m_k[frame][vertex])?
                || parser.boolean()? != rebuilt.l4.r_rev_k[frame][vertex]
                || parser.availability()? != rebuilt.l4.u_star_k[frame][vertex]
                || !parser.exact_matches(&rebuilt.l4.p_k[frame][vertex])?
                || !parser.exact_matches(&rebuilt.l4.b_k[frame][vertex])?
            {
                return Err(EvidenceError::Invalid("explicit DSF field body changed"));
            }
        }
        for expected in rebuilt
            .l4
            .cohesion(frame)
            .ok_or(EvidenceError::Invalid("cohesion frame is absent"))?
        {
            if usize::try_from(parser.u64()?).map_err(|_| EvidenceError::ArithmeticOverflow)?
                != expected.left
                || usize::try_from(parser.u64()?).map_err(|_| EvidenceError::ArithmeticOverflow)?
                    != expected.right
                || !parser.exact_matches(&expected.prior_product)?
                || !parser.exact_matches(&expected.current_product)?
                || !parser.exact_matches(&expected.displacement_product)?
                || !parser.exact_matches(&expected.oriented_area)?
            {
                return Err(EvidenceError::Invalid("explicit cohesion body changed"));
            }
        }
    }
    if parser.fixed::<32>()? != rebuilt.l4.authority_receipt_sha256 || !parser.finished() {
        return Err(EvidenceError::Invalid(
            "field receipt or trailing bytes changed",
        ));
    }
    Ok(rebuilt.l4)
}

pub(crate) fn measure_delivery_impression(
    perspective: &NeuronFieldPerspective,
    delivery_impression: &DsfDeliveryImpression,
    budget: EvidenceBudget,
) -> Result<ObjectRequirement, EvidenceError> {
    validate_delivery_impression_pair(perspective, delivery_impression, budget)?;
    let mut bytes = checked_add(DELIVERY_IMPRESSION_MAGIC.len(), 2)?;
    let mut exact_bytes = 0usize;
    let mut largest_exact_component_bytes = 0usize;
    bytes = checked_add(bytes, 16 + 8 + 8 + 32)?;
    for value in [
        &perspective.d_k,
        &perspective.m_k,
        &perspective.p_k,
        &perspective.b_k,
    ] {
        add_exact(
            &mut bytes,
            &mut exact_bytes,
            &mut largest_exact_component_bytes,
            value,
        )?;
    }
    bytes = checked_add(bytes, 2)?;
    bytes = checked_add(
        bytes,
        checked_add(
            4,
            checked_mul(perspective.incident_cohesion_edges.len(), 8)?,
        )?,
    )?;
    bytes = checked_add(bytes, 32)?;
    bytes = checked_add(bytes, 16 + 32 + 32 + 1 + 4)?;
    if delivery_impression
        .predecessor_impression_receipt_sha256
        .is_some()
    {
        bytes = checked_add(bytes, 32)?;
    }
    bytes = checked_add(bytes, delivery_impression.delivery_sign_impression.len())?;
    bytes = checked_add(bytes, 8 * 4 + 1 + 32 + 32)?;
    require(
        "exact component bytes",
        exact_bytes,
        budget.max_exact_component_bytes,
    )?;
    require(
        "delivery_impression coordinates",
        delivery_impression.delivery_sign_impression.len(),
        budget.max_delivery_impression_coordinates,
    )?;
    require("object bytes", bytes, budget.max_object_bytes)?;
    Ok(ObjectRequirement {
        bytes,
        decoded_working_bytes: measure_delivery_impression_working_bytes(
            perspective,
            delivery_impression,
        )?,
        vertices: 0,
        frames: 0,
        edges: perspective.incident_cohesion_edges.len(),
        groups: 0,
        group_members: 0,
        exact_component_bytes: exact_bytes,
        largest_exact_component_bytes,
        delivery_impression_coordinates: delivery_impression.delivery_sign_impression.len(),
    })
}

fn validate_delivery_impression_pair(
    perspective: &NeuronFieldPerspective,
    delivery_impression: &DsfDeliveryImpression,
    budget: EvidenceBudget,
) -> Result<(), EvidenceError> {
    verify_dsf_delivery_impression(delivery_impression)
        .map_err(|_| EvidenceError::Invalid("delivery_impression body"))?;
    if perspective.neuron_lineage != delivery_impression.neuron_lineage
        || perspective.complete_field_receipt_sha256
            != delivery_impression.complete_field_receipt_sha256
        || perspective.authority_receipt_sha256 != delivery_impression.perspective_receipt_sha256
    {
        return Err(EvidenceError::Invalid(
            "delivery_impression and perspective continuity changed",
        ));
    }
    require(
        "edges",
        perspective.incident_cohesion_edges.len(),
        budget.max_edges,
    )?;
    require(
        "delivery_impression coordinates",
        delivery_impression.delivery_sign_impression.len(),
        budget.max_delivery_impression_coordinates,
    )
}

pub(crate) fn encode_delivery_impression(
    perspective: &NeuronFieldPerspective,
    delivery_impression: &DsfDeliveryImpression,
    budget: EvidenceBudget,
) -> Result<Vec<u8>, EvidenceError> {
    let requirement = measure_delivery_impression(perspective, delivery_impression, budget)?;
    require(
        "peak live bytes",
        checked_add(
            requirement.decoded_working_bytes,
            checked_add(requirement.bytes, requirement.largest_exact_component_bytes)?,
        )?,
        budget.max_peak_live_bytes,
    )?;
    encode_delivery_impression_measured(perspective, delivery_impression, requirement)
}

fn encode_delivery_impression_measured(
    perspective: &NeuronFieldPerspective,
    delivery_impression: &DsfDeliveryImpression,
    requirement: ObjectRequirement,
) -> Result<Vec<u8>, EvidenceError> {
    let mut output = Vec::new();
    output
        .try_reserve_exact(requirement.bytes)
        .map_err(|_| EvidenceError::AllocationFailed)?;
    output.extend_from_slice(DELIVERY_IMPRESSION_MAGIC);
    output.extend_from_slice(&VERSION.to_le_bytes());
    encode_perspective(&mut output, perspective)?;
    encode_delivery_impression_body(&mut output, delivery_impression)?;
    if output.len() != requirement.bytes {
        return Err(EvidenceError::Invalid(
            "delivery_impression measurement differs from encoding",
        ));
    }
    Ok(output)
}

/// Structural decoding is not field authority. A caller must subsequently
/// bind the decoded perspective and delivery_impression to the separately resolved field.
pub(crate) fn decode_delivery_impression_structure(
    bytes: &[u8],
    budget: EvidenceBudget,
) -> Result<DecodedDeliveryImpression, EvidenceError> {
    let requirement = scan_delivery_impression_requirement(bytes, budget)?;
    require(
        "peak live bytes",
        checked_add(
            bytes.len(),
            checked_add(
                requirement.decoded_working_bytes,
                exact_parse_logical_temporary_bytes(requirement.largest_exact_component_bytes)?,
            )?,
        )?,
        budget.max_peak_live_bytes,
    )?;
    let mut parser = Parser::new(bytes);
    parser.expect(DELIVERY_IMPRESSION_MAGIC)?;
    parser.version()?;
    let perspective = parser.perspective(budget)?;
    let delivery_impression = parser.delivery_impression(budget)?;
    if !parser.finished() {
        return Err(EvidenceError::Invalid(
            "delivery_impression has trailing bytes",
        ));
    }
    validate_delivery_impression_pair(&perspective, &delivery_impression, budget)?;
    Ok(DecodedDeliveryImpression {
        perspective,
        delivery_impression,
    })
}

pub(crate) fn scan_delivery_impression_requirement(
    bytes: &[u8],
    budget: EvidenceBudget,
) -> Result<ObjectRequirement, EvidenceError> {
    require("object bytes", bytes.len(), budget.max_object_bytes)?;
    let mut scan = Scanner::new(bytes, budget);
    scan.expect(DELIVERY_IMPRESSION_MAGIC)?;
    scan.version()?;
    scan.take(16 + 8 + 8 + 32)?;
    scan.exact_bytes()?;
    scan.exact_bytes()?;
    scan.boolean()?;
    scan.availability()?;
    scan.exact_bytes()?;
    scan.exact_bytes()?;
    let edge_count = scan.u32()? as usize;
    require("edges", edge_count, budget.max_edges)?;
    scan.take(checked_mul(edge_count, 8)?)?;
    scan.take(32)?;
    scan.take(16 + 32 + 32)?;
    match scan.take(1)?[0] {
        0 => {}
        1 => {
            scan.take(32)?;
        }
        _ => return Err(EvidenceError::Invalid("optional digest flag changed")),
    }
    let coordinate_count = scan.u32()? as usize;
    require(
        "delivery_impression coordinates",
        coordinate_count,
        budget.max_delivery_impression_coordinates,
    )?;
    for trit in scan.take(coordinate_count)? {
        if *trit > 2 {
            return Err(EvidenceError::Invalid("structural trit changed"));
        }
    }
    scan.take(8 * 4)?;
    scan.boolean()?;
    scan.take(32 + 32)?;
    require(
        "exact component bytes",
        scan.exact_component_bytes,
        budget.max_exact_component_bytes,
    )?;
    if !scan.finished() {
        return Err(EvidenceError::Invalid(
            "delivery_impression has trailing bytes",
        ));
    }
    Ok(ObjectRequirement {
        bytes: bytes.len(),
        decoded_working_bytes: decoded_delivery_impression_working_upper(
            edge_count,
            coordinate_count,
            scan.largest_exact_component_bytes,
        )?,
        vertices: 0,
        frames: 0,
        edges: edge_count,
        groups: 0,
        group_members: 0,
        exact_component_bytes: scan.exact_component_bytes,
        largest_exact_component_bytes: scan.largest_exact_component_bytes,
        delivery_impression_coordinates: coordinate_count,
    })
}

pub(crate) fn validate_perspective_against_field(
    field: &L4JointDsf,
    perspective: &NeuronFieldPerspective,
) -> Result<(), EvidenceError> {
    let rebuilt = bind_neuron_perspective(
        field,
        perspective.neuron_lineage,
        perspective.vertex_index,
        perspective.frame_index,
    )
    .map_err(|_| EvidenceError::Invalid("perspective is outside its field"))?;
    if rebuilt != *perspective {
        return Err(EvidenceError::Invalid(
            "perspective does not reconstruct from field",
        ));
    }
    Ok(())
}

pub(crate) fn decode_field_bound_delivery_impression(
    bytes: &[u8],
    field: &L4JointDsf,
    budget: EvidenceBudget,
) -> Result<DecodedDeliveryImpression, EvidenceError> {
    let field_requirement = measure_complete_field(field, budget)?;
    let delivery_impression_requirement = scan_delivery_impression_requirement(bytes, budget)?;
    require(
        "peak live bytes",
        checked_add(
            field_requirement.decoded_working_bytes,
            checked_add(
                bytes.len(),
                checked_add(
                    checked_mul(2, delivery_impression_requirement.decoded_working_bytes)?,
                    exact_parse_logical_temporary_bytes(
                        delivery_impression_requirement.largest_exact_component_bytes,
                    )?,
                )?,
            )?,
        )?,
        budget.max_peak_live_bytes,
    )?;
    let decoded = decode_delivery_impression_structure(bytes, budget)?;
    validate_perspective_against_field(field, &decoded.perspective)?;
    let expected =
        crate::joint_field_l0_l4::settle_dsf_delivery_impression(field, &decoded.perspective, None)
            .map_err(|_| {
                EvidenceError::Invalid("field-bound delivery_impression cannot reconstruct")
            })?;
    if expected.delivery_sign_impression != decoded.delivery_impression.delivery_sign_impression {
        return Err(EvidenceError::Invalid(
            "delivery_impression impression does not reconstruct from field",
        ));
    }
    Ok(decoded)
}

pub(crate) fn scan_complete_field_requirement(
    bytes: &[u8],
    budget: EvidenceBudget,
) -> Result<ObjectRequirement, EvidenceError> {
    require("object bytes", bytes.len(), budget.max_object_bytes)?;
    let mut scan = Scanner::new(bytes, budget);
    scan.expect(FIELD_MAGIC)?;
    scan.version()?;
    let vertices = scan.u32()? as usize;
    require("vertices", vertices, budget.max_vertices)?;
    for _ in 0..vertices {
        scan.nonempty_bytes()?;
    }
    let groups = scan.u32()? as usize;
    require("groups", groups, budget.max_groups)?;
    let mut group_members = 0usize;
    for _ in 0..groups {
        let count = scan.u32()? as usize;
        group_members = checked_add(group_members, count)?;
        require("group members", group_members, budget.max_group_members)?;
        for _ in 0..count {
            if usize::try_from(scan.u64()?).map_err(|_| EvidenceError::ArithmeticOverflow)?
                >= vertices
            {
                return Err(EvidenceError::Invalid("group index is outside the field"));
            }
        }
    }
    let frames = scan.u32()? as usize;
    require("frames", frames, budget.max_frames)?;
    for _ in 0..frames {
        scan.exact_bytes()?;
    }
    if scan.u32()? as usize != frames {
        return Err(EvidenceError::Invalid("input frame counts differ"));
    }
    for _ in 0..frames {
        if scan.u32()? as usize != vertices {
            return Err(EvidenceError::Invalid("input vector width changed"));
        }
        for _ in 0..vertices {
            scan.exact_bytes()?;
        }
    }
    let edge_product = checked_mul(vertices, vertices.saturating_sub(1))?;
    let edges = edge_product / 2;
    require("edges", edges, budget.max_edges)?;
    if scan.u32()? as usize != frames
        || scan.u32()? as usize != vertices
        || scan.u32()? as usize != edges
    {
        return Err(EvidenceError::Invalid("field dimensions changed"));
    }
    for _ in 0..frames {
        for _ in 0..vertices {
            scan.exact_bytes()?;
            scan.exact_bytes()?;
            scan.boolean()?;
            scan.availability()?;
            scan.exact_bytes()?;
            scan.exact_bytes()?;
        }
        for _ in 0..edges {
            scan.u64()?;
            scan.u64()?;
            for _ in 0..4 {
                scan.exact_bytes()?;
            }
        }
    }
    scan.take(32)?;
    require(
        "exact component bytes",
        scan.exact_component_bytes,
        budget.max_exact_component_bytes,
    )?;
    if !scan.finished() {
        return Err(EvidenceError::Invalid("field has trailing bytes"));
    }
    Ok(ObjectRequirement {
        bytes: bytes.len(),
        decoded_working_bytes: decoded_field_working_upper(
            vertices,
            frames,
            edges,
            groups,
            group_members,
            scan.string_bytes,
            scan.largest_exact_component_bytes,
        )?,
        vertices,
        frames,
        edges,
        groups,
        group_members,
        exact_component_bytes: scan.exact_component_bytes,
        largest_exact_component_bytes: scan.largest_exact_component_bytes,
        delivery_impression_coordinates: 0,
    })
}

fn encode_input(output: &mut Vec<u8>, input: &JointFieldInput) -> Result<(), EvidenceError> {
    push_u32(output, input.vertex_ids.len())?;
    for value in &input.vertex_ids {
        push_bytes(output, value.as_bytes())?;
    }
    push_u32(output, input.groups.len())?;
    for group in &input.groups {
        push_u32(output, group.len())?;
        for index in group {
            output.extend_from_slice(
                &u64::try_from(*index)
                    .map_err(|_| EvidenceError::ArithmeticOverflow)?
                    .to_le_bytes(),
            );
        }
    }
    push_u32(output, input.times.len())?;
    for value in &input.times {
        push_exact(output, value)?;
    }
    push_u32(output, input.vectors.len())?;
    for vector in &input.vectors {
        push_u32(output, vector.len())?;
        for value in vector {
            push_exact(output, value)?;
        }
    }
    Ok(())
}

fn encode_relation(output: &mut Vec<u8>, value: &RelationFact) -> Result<(), EvidenceError> {
    output.extend_from_slice(
        &u64::try_from(value.left)
            .map_err(|_| EvidenceError::ArithmeticOverflow)?
            .to_le_bytes(),
    );
    output.extend_from_slice(
        &u64::try_from(value.right)
            .map_err(|_| EvidenceError::ArithmeticOverflow)?
            .to_le_bytes(),
    );
    for component in [
        &value.prior_product,
        &value.current_product,
        &value.displacement_product,
        &value.oriented_area,
    ] {
        push_exact(output, component)?;
    }
    Ok(())
}

fn encode_perspective(
    output: &mut Vec<u8>,
    value: &NeuronFieldPerspective,
) -> Result<(), EvidenceError> {
    output.extend_from_slice(&value.neuron_lineage);
    output.extend_from_slice(
        &u64::try_from(value.vertex_index)
            .map_err(|_| EvidenceError::ArithmeticOverflow)?
            .to_le_bytes(),
    );
    output.extend_from_slice(
        &u64::try_from(value.frame_index)
            .map_err(|_| EvidenceError::ArithmeticOverflow)?
            .to_le_bytes(),
    );
    output.extend_from_slice(&value.complete_field_receipt_sha256);
    push_exact(output, &value.d_k)?;
    push_exact(output, &value.m_k)?;
    output.push(u8::from(value.r_rev_k));
    output.push(match value.u_star_k {
        Availability::Genesis => 0,
        Availability::Observed => 1,
    });
    push_exact(output, &value.p_k)?;
    push_exact(output, &value.b_k)?;
    push_u32(output, value.incident_cohesion_edges.len())?;
    for edge in &value.incident_cohesion_edges {
        output.extend_from_slice(
            &u64::try_from(*edge)
                .map_err(|_| EvidenceError::ArithmeticOverflow)?
                .to_le_bytes(),
        );
    }
    output.extend_from_slice(&value.authority_receipt_sha256);
    Ok(())
}

fn encode_delivery_impression_body(
    output: &mut Vec<u8>,
    value: &DsfDeliveryImpression,
) -> Result<(), EvidenceError> {
    output.extend_from_slice(&value.neuron_lineage);
    output.extend_from_slice(&value.complete_field_receipt_sha256);
    output.extend_from_slice(&value.perspective_receipt_sha256);
    push_optional_digest(output, value.predecessor_impression_receipt_sha256);
    push_u32(output, value.delivery_sign_impression.len())?;
    for trit in &value.delivery_sign_impression {
        output.push(match trit {
            StructuralTrit::Negative => 0,
            StructuralTrit::Quiescent => 1,
            StructuralTrit::Positive => 2,
        });
    }
    for count in [
        value.delivery_recurrence.coordinate_count,
        value.delivery_recurrence.matching_nonnull,
        value.delivery_recurrence.matching_quiescent,
        value.delivery_recurrence.contradictions,
    ] {
        output.extend_from_slice(
            &u64::try_from(count)
                .map_err(|_| EvidenceError::ArithmeticOverflow)?
                .to_le_bytes(),
        );
    }
    output.push(u8::from(value.delivery_recurrence.predecessor_present));
    output.extend_from_slice(&value.delivery_recurrence.authority_receipt_sha256);
    output.extend_from_slice(&value.authority_receipt_sha256);
    Ok(())
}

fn push_optional_digest(output: &mut Vec<u8>, value: Option<[u8; 32]>) {
    output.push(u8::from(value.is_some()));
    if let Some(value) = value {
        output.extend_from_slice(&value);
    }
}

pub(crate) fn push_exact(output: &mut Vec<u8>, value: &Exact) -> Result<(), EvidenceError> {
    push_bytes(output, &value.numer().to_signed_bytes_be())?;
    push_bytes(output, &value.denom().to_signed_bytes_be())
}

pub(crate) fn parse_exact_at(payload: &[u8], offset: &mut usize) -> Result<Exact, EvidenceError> {
    fn take<'a>(
        payload: &'a [u8],
        offset: &mut usize,
        count: usize,
    ) -> Result<&'a [u8], EvidenceError> {
        let end = checked_add(*offset, count)?;
        if end > payload.len() {
            return Err(EvidenceError::Invalid("object ended early"));
        }
        let value = &payload[*offset..end];
        *offset = end;
        Ok(value)
    }
    fn component<'a>(payload: &'a [u8], offset: &mut usize) -> Result<&'a [u8], EvidenceError> {
        let count = u32::from_le_bytes(fixed_array(take(payload, offset, 4)?)?) as usize;
        take(payload, offset, count)
    }

    let numerator_bytes = component(payload, offset)?;
    let denominator_bytes = component(payload, offset)?;
    if denominator_bytes.is_empty() {
        return Err(EvidenceError::Invalid("exact denominator is empty"));
    }
    let numerator = BigInt::from_signed_bytes_be(numerator_bytes);
    let denominator = BigInt::from_signed_bytes_be(denominator_bytes);
    if denominator <= BigInt::zero() {
        return Err(EvidenceError::Invalid("exact denominator is not positive"));
    }
    let value = BigRational::new(numerator, denominator);
    if value.numer().to_signed_bytes_be() != numerator_bytes
        || value.denom().to_signed_bytes_be() != denominator_bytes
    {
        return Err(EvidenceError::Invalid("exact value is not canonical"));
    }
    Ok(value)
}

fn push_bytes(output: &mut Vec<u8>, value: &[u8]) -> Result<(), EvidenceError> {
    push_u32(output, value.len())?;
    output.extend_from_slice(value);
    Ok(())
}

fn push_u32(output: &mut Vec<u8>, value: usize) -> Result<(), EvidenceError> {
    output.extend_from_slice(
        &u32::try_from(value)
            .map_err(|_| EvidenceError::ArithmeticOverflow)?
            .to_le_bytes(),
    );
    Ok(())
}

struct Scanner<'a> {
    payload: &'a [u8],
    offset: usize,
    budget: EvidenceBudget,
    exact_component_bytes: usize,
    largest_exact_component_bytes: usize,
    string_bytes: usize,
}

impl<'a> Scanner<'a> {
    fn new(payload: &'a [u8], budget: EvidenceBudget) -> Self {
        Self {
            payload,
            offset: 0,
            budget,
            exact_component_bytes: 0,
            largest_exact_component_bytes: 0,
            string_bytes: 0,
        }
    }

    fn finished(&self) -> bool {
        self.offset == self.payload.len()
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], EvidenceError> {
        let end = checked_add(self.offset, count)?;
        if end > self.payload.len() {
            return Err(EvidenceError::Invalid("object ended early"));
        }
        let value = &self.payload[self.offset..end];
        self.offset = end;
        Ok(value)
    }

    fn expect(&mut self, expected: &[u8]) -> Result<(), EvidenceError> {
        if self.take(expected.len())? != expected {
            return Err(EvidenceError::Invalid("object kind changed"));
        }
        Ok(())
    }

    fn version(&mut self) -> Result<(), EvidenceError> {
        if u16::from_le_bytes(fixed_array(self.take(2)?)?) != VERSION {
            return Err(EvidenceError::Invalid("object version changed"));
        }
        Ok(())
    }

    fn u32(&mut self) -> Result<u32, EvidenceError> {
        Ok(u32::from_le_bytes(fixed_array(self.take(4)?)?))
    }

    fn u64(&mut self) -> Result<u64, EvidenceError> {
        Ok(u64::from_le_bytes(fixed_array(self.take(8)?)?))
    }

    fn nonempty_bytes(&mut self) -> Result<(), EvidenceError> {
        let count = self.u32()? as usize;
        if count == 0 {
            return Err(EvidenceError::Invalid("required bytes are empty"));
        }
        self.take(count)?;
        self.string_bytes = checked_add(self.string_bytes, count)?;
        Ok(())
    }

    fn exact_bytes(&mut self) -> Result<(), EvidenceError> {
        let numerator = self.u32()? as usize;
        self.take(numerator)?;
        let denominator = self.u32()? as usize;
        if denominator == 0 {
            return Err(EvidenceError::Invalid("exact denominator is empty"));
        }
        self.take(denominator)?;
        self.largest_exact_component_bytes = self
            .largest_exact_component_bytes
            .max(numerator)
            .max(denominator);
        self.exact_component_bytes = checked_add(
            self.exact_component_bytes,
            checked_add(numerator, denominator)?,
        )?;
        require(
            "exact component bytes",
            self.exact_component_bytes,
            self.budget.max_exact_component_bytes,
        )
    }

    fn boolean(&mut self) -> Result<(), EvidenceError> {
        if self.take(1)?[0] > 1 {
            return Err(EvidenceError::Invalid("boolean changed"));
        }
        Ok(())
    }

    fn availability(&mut self) -> Result<(), EvidenceError> {
        if self.take(1)?[0] > 1 {
            return Err(EvidenceError::Invalid("availability changed"));
        }
        Ok(())
    }
}

struct Parser<'a> {
    payload: &'a [u8],
    offset: usize,
}

impl<'a> Parser<'a> {
    fn new(payload: &'a [u8]) -> Self {
        Self { payload, offset: 0 }
    }

    fn finished(&self) -> bool {
        self.offset == self.payload.len()
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], EvidenceError> {
        let end = checked_add(self.offset, count)?;
        if end > self.payload.len() {
            return Err(EvidenceError::Invalid("object ended early"));
        }
        let value = &self.payload[self.offset..end];
        self.offset = end;
        Ok(value)
    }

    fn expect(&mut self, expected: &[u8]) -> Result<(), EvidenceError> {
        if self.take(expected.len())? != expected {
            return Err(EvidenceError::Invalid("object kind changed"));
        }
        Ok(())
    }

    fn version(&mut self) -> Result<(), EvidenceError> {
        if u16::from_le_bytes(fixed_array(self.take(2)?)?) != VERSION {
            return Err(EvidenceError::Invalid("object version changed"));
        }
        Ok(())
    }

    fn u8(&mut self) -> Result<u8, EvidenceError> {
        Ok(self.take(1)?[0])
    }

    fn u32(&mut self) -> Result<u32, EvidenceError> {
        Ok(u32::from_le_bytes(fixed_array(self.take(4)?)?))
    }

    fn u64(&mut self) -> Result<u64, EvidenceError> {
        Ok(u64::from_le_bytes(fixed_array(self.take(8)?)?))
    }

    fn fixed<const N: usize>(&mut self) -> Result<[u8; N], EvidenceError> {
        fixed_array(self.take(N)?)
    }

    fn bytes(&mut self) -> Result<&'a [u8], EvidenceError> {
        let count = self.u32()? as usize;
        self.take(count)
    }

    fn string(&mut self) -> Result<String, EvidenceError> {
        let bytes = self.bytes()?;
        let value = std::str::from_utf8(bytes)
            .map_err(|_| EvidenceError::Invalid("field string is not UTF-8"))?;
        if value.is_empty() {
            return Err(EvidenceError::Invalid("field string is empty"));
        }
        Ok(value.to_string())
    }

    fn exact(&mut self) -> Result<Exact, EvidenceError> {
        let numerator_bytes = self.bytes()?;
        let denominator_bytes = self.bytes()?;
        if denominator_bytes.is_empty() {
            return Err(EvidenceError::Invalid("exact denominator is empty"));
        }
        let numerator = BigInt::from_signed_bytes_be(numerator_bytes);
        let denominator = BigInt::from_signed_bytes_be(denominator_bytes);
        if denominator <= BigInt::zero() {
            return Err(EvidenceError::Invalid("exact denominator is not positive"));
        }
        let value = BigRational::new(numerator, denominator);
        if value.numer().to_signed_bytes_be() != numerator_bytes
            || value.denom().to_signed_bytes_be() != denominator_bytes
        {
            return Err(EvidenceError::Invalid("exact value is not canonical"));
        }
        Ok(value)
    }

    fn exact_matches(&mut self, expected: &Exact) -> Result<bool, EvidenceError> {
        let numerator_bytes = self.bytes()?;
        let denominator_bytes = self.bytes()?;
        if denominator_bytes.is_empty() {
            return Err(EvidenceError::Invalid("exact denominator is empty"));
        }
        if expected.numer().to_signed_bytes_be() != numerator_bytes {
            return Ok(false);
        }
        Ok(expected.denom().to_signed_bytes_be() == denominator_bytes)
    }

    fn boolean(&mut self) -> Result<bool, EvidenceError> {
        match self.u8()? {
            0 => Ok(false),
            1 => Ok(true),
            _ => Err(EvidenceError::Invalid("boolean changed")),
        }
    }

    fn availability(&mut self) -> Result<Availability, EvidenceError> {
        match self.u8()? {
            0 => Ok(Availability::Genesis),
            1 => Ok(Availability::Observed),
            _ => Err(EvidenceError::Invalid("availability changed")),
        }
    }

    fn input(&mut self) -> Result<JointFieldInput, EvidenceError> {
        let vertex_count = self.u32()? as usize;
        let mut vertex_ids = Vec::new();
        vertex_ids
            .try_reserve_exact(vertex_count)
            .map_err(|_| EvidenceError::AllocationFailed)?;
        for _ in 0..vertex_count {
            vertex_ids.push(self.string()?);
        }
        let group_count = self.u32()? as usize;
        let mut groups = Vec::new();
        groups
            .try_reserve_exact(group_count)
            .map_err(|_| EvidenceError::AllocationFailed)?;
        for _ in 0..group_count {
            let count = self.u32()? as usize;
            let mut group = Vec::new();
            group
                .try_reserve_exact(count)
                .map_err(|_| EvidenceError::AllocationFailed)?;
            for _ in 0..count {
                group.push(
                    usize::try_from(self.u64()?).map_err(|_| EvidenceError::ArithmeticOverflow)?,
                );
            }
            groups.push(group);
        }
        let time_count = self.u32()? as usize;
        let mut times = Vec::new();
        times
            .try_reserve_exact(time_count)
            .map_err(|_| EvidenceError::AllocationFailed)?;
        for _ in 0..time_count {
            times.push(self.exact()?);
        }
        let vector_count = self.u32()? as usize;
        let mut vectors = Vec::new();
        vectors
            .try_reserve_exact(vector_count)
            .map_err(|_| EvidenceError::AllocationFailed)?;
        for _ in 0..vector_count {
            let count = self.u32()? as usize;
            let mut vector = Vec::new();
            vector
                .try_reserve_exact(count)
                .map_err(|_| EvidenceError::AllocationFailed)?;
            for _ in 0..count {
                vector.push(self.exact()?);
            }
            vectors.push(vector);
        }
        Ok(JointFieldInput {
            vertex_ids,
            groups,
            times,
            vectors,
        })
    }

    fn perspective(
        &mut self,
        budget: EvidenceBudget,
    ) -> Result<NeuronFieldPerspective, EvidenceError> {
        let neuron_lineage = self.fixed()?;
        let vertex_index =
            usize::try_from(self.u64()?).map_err(|_| EvidenceError::ArithmeticOverflow)?;
        let frame_index =
            usize::try_from(self.u64()?).map_err(|_| EvidenceError::ArithmeticOverflow)?;
        let complete_field_receipt_sha256 = self.fixed()?;
        let d_k = self.exact()?;
        let m_k = self.exact()?;
        let r_rev_k = self.boolean()?;
        let u_star_k = self.availability()?;
        let p_k = self.exact()?;
        let b_k = self.exact()?;
        let edge_count = self.u32()? as usize;
        require("edges", edge_count, budget.max_edges)?;
        let mut incident_cohesion_edges = Vec::new();
        incident_cohesion_edges
            .try_reserve_exact(edge_count)
            .map_err(|_| EvidenceError::AllocationFailed)?;
        for _ in 0..edge_count {
            incident_cohesion_edges
                .push(usize::try_from(self.u64()?).map_err(|_| EvidenceError::ArithmeticOverflow)?);
        }
        Ok(NeuronFieldPerspective {
            neuron_lineage,
            vertex_index,
            frame_index,
            complete_field_receipt_sha256,
            d_k,
            m_k,
            r_rev_k,
            u_star_k,
            incident_cohesion_edges,
            p_k,
            b_k,
            authority_receipt_sha256: self.fixed()?,
        })
    }

    fn optional_digest(&mut self) -> Result<Option<[u8; 32]>, EvidenceError> {
        match self.u8()? {
            0 => Ok(None),
            1 => Ok(Some(self.fixed()?)),
            _ => Err(EvidenceError::Invalid("optional digest flag changed")),
        }
    }

    fn delivery_impression(
        &mut self,
        budget: EvidenceBudget,
    ) -> Result<DsfDeliveryImpression, EvidenceError> {
        let neuron_lineage = self.fixed()?;
        let complete_field_receipt_sha256 = self.fixed()?;
        let perspective_receipt_sha256 = self.fixed()?;
        let predecessor_impression_receipt_sha256 = self.optional_digest()?;
        let coordinate_count = self.u32()? as usize;
        require(
            "delivery_impression coordinates",
            coordinate_count,
            budget.max_delivery_impression_coordinates,
        )?;
        let mut delivery_sign_impression = Vec::new();
        delivery_sign_impression
            .try_reserve_exact(coordinate_count)
            .map_err(|_| EvidenceError::AllocationFailed)?;
        for _ in 0..coordinate_count {
            delivery_sign_impression.push(match self.u8()? {
                0 => StructuralTrit::Negative,
                1 => StructuralTrit::Quiescent,
                2 => StructuralTrit::Positive,
                _ => return Err(EvidenceError::Invalid("structural trit changed")),
            });
        }
        let recurrence = DsfDeliveryRecurrence {
            coordinate_count: usize::try_from(self.u64()?)
                .map_err(|_| EvidenceError::ArithmeticOverflow)?,
            matching_nonnull: usize::try_from(self.u64()?)
                .map_err(|_| EvidenceError::ArithmeticOverflow)?,
            matching_quiescent: usize::try_from(self.u64()?)
                .map_err(|_| EvidenceError::ArithmeticOverflow)?,
            contradictions: usize::try_from(self.u64()?)
                .map_err(|_| EvidenceError::ArithmeticOverflow)?,
            predecessor_present: self.boolean()?,
            authority_receipt_sha256: self.fixed()?,
        };
        Ok(DsfDeliveryImpression {
            neuron_lineage,
            complete_field_receipt_sha256,
            perspective_receipt_sha256,
            predecessor_impression_receipt_sha256,
            delivery_sign_impression,
            delivery_recurrence: recurrence,
            authority_receipt_sha256: self.fixed()?,
        })
    }
}

#[cfg(test)]
pub(crate) fn canonical_test_budget() -> EvidenceBudget {
    EvidenceBudget {
        max_object_bytes: 1 << 20,
        max_serialized_batch_bytes: 1 << 22,
        max_peak_live_bytes: 1 << 24,
        max_transition_work: 1_024,
        max_objects: 64,
        max_vertices: 16,
        max_frames: 16,
        max_edges: 120,
        max_groups: 16,
        max_group_members: 64,
        max_exact_component_bytes: 1 << 18,
        max_delivery_impression_coordinates: 256,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::joint_field_l0_l4::{settle_dsf_delivery_impression, JointFieldExperience};

    fn ratio(value: i64) -> Exact {
        BigRational::from_integer(value.into())
    }

    fn field(values: [[i64; 2]; 2]) -> JointFieldExperience {
        let input = JointFieldInput {
            vertex_ids: vec!["left".into(), "right".into()],
            groups: vec![vec![0], vec![1]],
            times: vec![ratio(1), ratio(2)],
            vectors: values
                .into_iter()
                .map(|frame| frame.into_iter().map(ratio).collect())
                .collect(),
        };
        let required = derive_requirement(&input).unwrap();
        run_joint_field_l0_l4(
            input,
            JointFieldBudget {
                max_input_bytes: required.input_bytes,
                max_vertices: required.vertices,
                max_frames: required.frames,
                max_edges: required.edges,
                max_relation_facts: required.relation_facts,
                max_vertex_frame_values: required.vertex_frame_values,
            },
        )
        .unwrap()
    }

    #[test]
    fn full_field_round_trip_preserves_every_explicit_component() {
        let value = field([[1, 3], [2, 5]]);
        let bytes = encode_complete_field(&value.l4, canonical_test_budget()).unwrap();
        let decoded = decode_complete_field(&bytes, canonical_test_budget()).unwrap();
        assert_eq!(decoded.as_ref(), value.l4.as_ref());
    }

    #[test]
    fn altered_field_body_and_trailing_bytes_are_rejected() {
        let value = field([[1, 3], [2, 5]]);
        let bytes = encode_complete_field(&value.l4, canonical_test_budget()).unwrap();
        let mut altered = bytes.clone();
        let body_index = altered.len() - 33;
        altered[body_index] ^= 1;
        assert!(decode_complete_field(&altered, canonical_test_budget()).is_err());
        let mut trailing = bytes;
        trailing.push(0);
        assert!(decode_complete_field(&trailing, canonical_test_budget()).is_err());
    }

    #[test]
    fn noncanonical_exact_encoding_is_rejected() {
        let value = field([[1, 3], [2, 5]]);
        let mut bytes = encode_complete_field(&value.l4, canonical_test_budget()).unwrap();
        // First exact time follows the fixed header, vertex ids, and two
        // one-member groups. Add a redundant leading sign byte to 1.
        let first_numerator_length = 63;
        bytes[first_numerator_length..first_numerator_length + 4]
            .copy_from_slice(&2u32.to_le_bytes());
        bytes.insert(first_numerator_length + 4, 0);
        assert!(decode_complete_field(&bytes, canonical_test_budget()).is_err());
    }

    #[test]
    fn delivery_impression_round_trip_requires_complete_body() {
        let value = field([[1, 3], [2, 5]]);
        let perspective = bind_neuron_perspective(&value.l4, [7; 16], 0, 1).unwrap();
        let delivery_impression =
            settle_dsf_delivery_impression(&value.l4, &perspective, None).unwrap();
        let bytes =
            encode_delivery_impression(&perspective, &delivery_impression, canonical_test_budget())
                .unwrap();
        let decoded =
            decode_field_bound_delivery_impression(&bytes, &value.l4, canonical_test_budget())
                .unwrap();
        assert_eq!(decoded.perspective, perspective);
        assert_eq!(decoded.delivery_impression, delivery_impression);
    }

    #[test]
    fn opaque_perspective_receipt_is_not_field_authority() {
        let value = field([[1, 3], [2, 5]]);
        let perspective = bind_neuron_perspective(&value.l4, [7; 16], 0, 1).unwrap();
        let delivery_impression =
            settle_dsf_delivery_impression(&value.l4, &perspective, None).unwrap();
        let mut substituted = perspective;
        substituted.d_k += ratio(1);
        let bytes =
            encode_delivery_impression(&substituted, &delivery_impression, canonical_test_budget())
                .unwrap();
        assert!(decode_delivery_impression_structure(&bytes, canonical_test_budget()).is_ok());
        assert!(
            decode_field_bound_delivery_impression(&bytes, &value.l4, canonical_test_budget())
                .is_err()
        );
    }

    #[test]
    fn signed_byte_measurement_matches_canonical_bigint_encoding() {
        for value in -100_000i64..=100_000 {
            let value = BigInt::from(value);
            assert_eq!(
                signed_bytes_len(&value).unwrap(),
                value.to_signed_bytes_be().len()
            );
        }
        for shift in 0..=512u32 {
            let power = BigInt::from(1u8) << shift;
            for delta in [-1i8, 0, 1] {
                let positive = &power + BigInt::from(delta);
                let negative = -&positive;
                assert_eq!(
                    signed_bytes_len(&positive).unwrap(),
                    positive.to_signed_bytes_be().len()
                );
                assert_eq!(
                    signed_bytes_len(&negative).unwrap(),
                    negative.to_signed_bytes_be().len()
                );
            }
        }
    }

    #[test]
    fn budget_is_enforced_before_field_encoding() {
        let value = field([[1, 3], [2, 5]]);
        let mut budget = canonical_test_budget();
        budget.max_vertices = 1;
        assert!(matches!(
            encode_complete_field(&value.l4, budget),
            Err(EvidenceError::BudgetExceeded {
                resource: "vertices",
                ..
            })
        ));
    }

    #[test]
    fn every_allocation_bearing_codec_refuses_zero_peak_budget() {
        let value = field([[1, 3], [2, 5]]);
        let perspective = bind_neuron_perspective(&value.l4, [7; 16], 0, 1).unwrap();
        let delivery_impression =
            settle_dsf_delivery_impression(&value.l4, &perspective, None).unwrap();
        let field_bytes = encode_complete_field(&value.l4, canonical_test_budget()).unwrap();
        let delivery_impression_bytes =
            encode_delivery_impression(&perspective, &delivery_impression, canonical_test_budget())
                .unwrap();
        let mut budget = canonical_test_budget();
        budget.max_peak_live_bytes = 0;
        for result in [
            encode_complete_field(&value.l4, budget).map(|_| ()),
            decode_complete_field(&field_bytes, budget).map(|_| ()),
            encode_delivery_impression(&perspective, &delivery_impression, budget).map(|_| ()),
            decode_delivery_impression_structure(&delivery_impression_bytes, budget).map(|_| ()),
            decode_field_bound_delivery_impression(&delivery_impression_bytes, &value.l4, budget)
                .map(|_| ()),
        ] {
            assert!(matches!(
                result,
                Err(EvidenceError::BudgetExceeded {
                    resource: "peak live bytes",
                    ..
                })
            ));
        }
    }
}
