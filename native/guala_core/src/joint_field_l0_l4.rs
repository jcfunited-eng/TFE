//! Exact native joint-field L0--L4 and neuron-perspective binding.
//!
//! This is Guala's versioned D1 joint-field path. It promotes only the exact
//! VTVR operators exercised by the isolated near-v1.3 walk-up. It does not
//! alter the historical per-port kernel, invent semantic labels, flatten the
//! field, or define the still-missing complete-neuron transition and
//! post-quiescence neuronal-fractal law.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{Signed, Zero};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::sync::Arc;

pub type Exact = BigRational;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JointFieldInput {
    pub vertex_ids: Vec<String>,
    pub groups: Vec<Vec<usize>>,
    pub times: Vec<Exact>,
    pub vectors: Vec<Vec<Exact>>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct JointFieldBudget {
    pub max_input_bytes: usize,
    pub max_vertices: usize,
    pub max_frames: usize,
    pub max_edges: usize,
    pub max_relation_facts: usize,
    pub max_vertex_frame_values: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct JointFieldRequirement {
    pub input_bytes: usize,
    pub vertices: usize,
    pub frames: usize,
    pub edges: usize,
    pub relation_facts: usize,
    pub vertex_frame_values: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum JointFieldError {
    Invalid(&'static str),
    ArithmeticOverflow,
    AllocationFailed,
    BudgetExceeded {
        resource: &'static str,
        required: usize,
        available: usize,
    },
}

impl fmt::Display for JointFieldError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(reason) => write!(output, "invalid joint field: {reason}"),
            Self::ArithmeticOverflow => write!(output, "joint-field resource arithmetic overflow"),
            Self::AllocationFailed => write!(output, "joint-field allocation failed"),
            Self::BudgetExceeded {
                resource,
                required,
                available,
            } => write!(
                output,
                "joint-field {resource} requires {required}, available {available}"
            ),
        }
    }
}

impl std::error::Error for JointFieldError {}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelationFact {
    pub left: usize,
    pub right: usize,
    pub prior_product: Exact,
    pub current_product: Exact,
    pub displacement_product: Exact,
    pub oriented_area: Exact,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct L0Frame {
    pub time: Exact,
    pub delta_time: Exact,
    pub vector: Vec<Exact>,
    pub displacement: Vec<Exact>,
    pub volume: Vec<Exact>,
    pub relation: Vec<RelationFact>,
    pub observed_zero_groups: Vec<bool>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct L0JointField {
    pub input: Arc<JointFieldInput>,
    pub edges: Vec<(usize, usize)>,
    pub frames: Vec<L0Frame>,
    pub raw_authority_receipt_sha256: [u8; 32],
    pub authority_receipt_sha256: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct L1Vtvr {
    pub l0: Arc<L0JointField>,
    pub accumulated_volume: Vec<Exact>,
    pub authority_receipt_sha256: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct L2Geometry {
    pub l1: Arc<L1Vtvr>,
    pub velocity: Vec<Vec<Exact>>,
    pub acceleration: Vec<Vec<Exact>>,
    pub relation_change: Vec<Vec<RelationFact>>,
    pub authority_receipt_sha256: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct L3ResonanceField {
    pub l2: Arc<L2Geometry>,
    pub quiescent: bool,
    pub authority_receipt_sha256: [u8; 32],
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Availability {
    Genesis,
    Observed,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct L4JointDsf {
    pub l3: Arc<L3ResonanceField>,
    pub d_k: Vec<Vec<Exact>>,
    pub m_k: Vec<Vec<Exact>>,
    pub r_rev_k: Vec<Vec<bool>>,
    pub u_star_k: Vec<Vec<Availability>>,
    pub p_k: Vec<Vec<Exact>>,
    pub b_k: Vec<Vec<Exact>>,
    pub authority_receipt_sha256: [u8; 32],
}

impl L4JointDsf {
    pub fn cohesion(&self, frame_index: usize) -> Option<&[RelationFact]> {
        self.l3
            .l2
            .l1
            .l0
            .frames
            .get(frame_index)
            .map(|frame| frame.relation.as_slice())
    }

    pub fn vertex_count(&self) -> usize {
        self.l3.l2.l1.l0.input.vertex_ids.len()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JointFieldExperience {
    pub l4: Arc<L4JointDsf>,
    pub requirement: JointFieldRequirement,
    pub authority_receipt_sha256: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NeuronFieldPerspective {
    pub neuron_lineage: [u8; 16],
    pub vertex_index: usize,
    pub frame_index: usize,
    pub complete_field_receipt_sha256: [u8; 32],
    pub d_k: Exact,
    pub m_k: Exact,
    pub r_rev_k: bool,
    pub u_star_k: Availability,
    pub incident_cohesion_edges: Vec<usize>,
    pub p_k: Exact,
    pub b_k: Exact,
    pub authority_receipt_sha256: [u8; 32],
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(i8)]
pub enum StructuralTrit {
    Negative = -1,
    Quiescent = 0,
    Positive = 1,
}

#[derive(Clone, Debug, Eq, PartialEq)]
/// Coordinate-wise recurrence of a sign-compressed DSF delivery impression.
/// This is observation evidence only; it is not DNA or growth authority.
pub struct DsfDeliveryRecurrence {
    pub coordinate_count: usize,
    pub matching_nonnull: usize,
    pub matching_quiescent: usize,
    pub contradictions: usize,
    pub predecessor_present: bool,
    pub authority_receipt_sha256: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
/// A local sign-compressed impression of one complete-field DSF delivery.
/// It is not a neuronal fractal or retained whole-neuron physical change.
pub struct DsfDeliveryImpression {
    pub neuron_lineage: [u8; 16],
    pub complete_field_receipt_sha256: [u8; 32],
    pub perspective_receipt_sha256: [u8; 32],
    pub predecessor_impression_receipt_sha256: Option<[u8; 32]>,
    pub delivery_sign_impression: Vec<StructuralTrit>,
    pub delivery_recurrence: DsfDeliveryRecurrence,
    pub authority_receipt_sha256: [u8; 32],
}

struct Authority(Sha256);

impl Authority {
    fn new(domain: &[u8]) -> Self {
        let mut value = Sha256::new();
        value.update((domain.len() as u64).to_be_bytes());
        value.update(domain);
        Self(value)
    }

    fn bytes(&mut self, value: &[u8]) {
        self.0.update((value.len() as u64).to_be_bytes());
        self.0.update(value);
    }

    fn usize(&mut self, value: usize) {
        self.0.update((value as u64).to_be_bytes());
    }

    fn rational(&mut self, value: &Exact) {
        self.bytes(&value.numer().to_signed_bytes_be());
        self.bytes(&value.denom().to_signed_bytes_be());
    }

    fn relation(&mut self, value: &RelationFact) {
        self.usize(value.left);
        self.usize(value.right);
        self.rational(&value.prior_product);
        self.rational(&value.current_product);
        self.rational(&value.displacement_product);
        self.rational(&value.oriented_area);
    }

    fn finish(self) -> [u8; 32] {
        self.0.finalize().into()
    }
}

fn checked_product(left: usize, right: usize) -> Result<usize, JointFieldError> {
    left.checked_mul(right)
        .ok_or(JointFieldError::ArithmeticOverflow)
}

fn rational_bytes(value: &Exact) -> Result<usize, JointFieldError> {
    value
        .numer()
        .to_signed_bytes_be()
        .len()
        .checked_add(value.denom().to_signed_bytes_be().len())
        .ok_or(JointFieldError::ArithmeticOverflow)
}

pub fn derive_requirement(
    input: &JointFieldInput,
) -> Result<JointFieldRequirement, JointFieldError> {
    let vertices = input.vertex_ids.len();
    let frames = input.times.len();
    let edge_product = vertices
        .checked_mul(vertices.saturating_sub(1))
        .ok_or(JointFieldError::ArithmeticOverflow)?;
    let edges = edge_product / 2;
    let relation_facts = checked_product(frames, edges)?;
    let vertex_frame_values = checked_product(frames, vertices)?;
    let mut input_bytes = 0usize;
    for value in &input.times {
        input_bytes = input_bytes
            .checked_add(rational_bytes(value)?)
            .ok_or(JointFieldError::ArithmeticOverflow)?;
    }
    for vector in &input.vectors {
        for value in vector {
            input_bytes = input_bytes
                .checked_add(rational_bytes(value)?)
                .ok_or(JointFieldError::ArithmeticOverflow)?;
        }
    }
    for vertex_id in &input.vertex_ids {
        input_bytes = input_bytes
            .checked_add(vertex_id.len())
            .ok_or(JointFieldError::ArithmeticOverflow)?;
    }
    Ok(JointFieldRequirement {
        input_bytes,
        vertices,
        frames,
        edges,
        relation_facts,
        vertex_frame_values,
    })
}

fn require(
    resource: &'static str,
    required: usize,
    available: usize,
) -> Result<(), JointFieldError> {
    if required > available {
        return Err(JointFieldError::BudgetExceeded {
            resource,
            required,
            available,
        });
    }
    Ok(())
}

fn validate(
    input: &JointFieldInput,
    budget: JointFieldBudget,
) -> Result<JointFieldRequirement, JointFieldError> {
    let requirement = derive_requirement(input)?;
    require(
        "input bytes",
        requirement.input_bytes,
        budget.max_input_bytes,
    )?;
    require("vertices", requirement.vertices, budget.max_vertices)?;
    require("frames", requirement.frames, budget.max_frames)?;
    require("edges", requirement.edges, budget.max_edges)?;
    require(
        "relation facts",
        requirement.relation_facts,
        budget.max_relation_facts,
    )?;
    require(
        "vertex-frame values",
        requirement.vertex_frame_values,
        budget.max_vertex_frame_values,
    )?;
    if requirement.vertices < 2 || requirement.frames < 2 {
        return Err(JointFieldError::Invalid(
            "joint causality requires at least two vertices and two frames",
        ));
    }
    if input.vectors.len() != requirement.frames
        || input
            .vectors
            .iter()
            .any(|vector| vector.len() != requirement.vertices)
    {
        return Err(JointFieldError::Invalid("vector topology changed"));
    }
    if input.times.windows(2).any(|pair| pair[1] <= pair[0]) {
        return Err(JointFieldError::Invalid(
            "causal times must strictly increase",
        ));
    }
    let vertex_ids: BTreeSet<&str> = input.vertex_ids.iter().map(String::as_str).collect();
    if vertex_ids.len() != requirement.vertices
        || vertex_ids
            .iter()
            .any(|value| value.is_empty() || value.trim() != *value)
    {
        return Err(JointFieldError::Invalid("vertex identity changed"));
    }
    if input.groups.is_empty() || input.groups.iter().any(Vec::is_empty) {
        return Err(JointFieldError::Invalid("physical groups are incomplete"));
    }
    let mut covered = Vec::new();
    covered
        .try_reserve_exact(requirement.vertices)
        .map_err(|_| JointFieldError::AllocationFailed)?;
    for group in &input.groups {
        let unique: BTreeSet<usize> = group.iter().copied().collect();
        if unique.len() != group.len() {
            return Err(JointFieldError::Invalid("physical group repeats a vertex"));
        }
        covered.extend(group.iter().copied());
    }
    covered.sort_unstable();
    if covered != (0..requirement.vertices).collect::<Vec<_>>() {
        return Err(JointFieldError::Invalid(
            "physical groups must partition every vertex exactly once",
        ));
    }
    Ok(requirement)
}

fn zero_vector(width: usize) -> Vec<Exact> {
    vec![Exact::zero(); width]
}

fn normalize(vector: &[Exact], groups: &[Vec<usize>]) -> Vec<Exact> {
    let mut result = zero_vector(vector.len());
    for group in groups {
        let magnitude: Exact = group.iter().map(|index| vector[*index].abs()).sum();
        for index in group {
            if !magnitude.is_zero() {
                result[*index] = &vector[*index] / &magnitude;
            }
        }
    }
    result
}

fn edges(width: usize) -> Vec<(usize, usize)> {
    (0..width)
        .flat_map(|left| ((left + 1)..width).map(move |right| (left, right)))
        .collect()
}

fn relation(
    prior: &[Exact],
    current: &[Exact],
    displacement: &[Exact],
    topology: &[(usize, usize)],
) -> Vec<RelationFact> {
    topology
        .iter()
        .map(|(left, right)| RelationFact {
            left: *left,
            right: *right,
            prior_product: &prior[*left] * &prior[*right],
            current_product: &current[*left] * &current[*right],
            displacement_product: &displacement[*left] * &displacement[*right],
            oriented_area: &prior[*left] * &current[*right] - &prior[*right] * &current[*left],
        })
        .collect()
}

fn relation_delta(prior: &RelationFact, current: &RelationFact) -> RelationFact {
    RelationFact {
        left: current.left,
        right: current.right,
        prior_product: &current.prior_product - &prior.prior_product,
        current_product: &current.current_product - &prior.current_product,
        displacement_product: &current.displacement_product - &prior.displacement_product,
        oriented_area: &current.oriented_area - &prior.oriented_area,
    }
}

fn structural_trit(value: &Exact) -> StructuralTrit {
    if value.is_zero() {
        StructuralTrit::Quiescent
    } else if value.is_positive() {
        StructuralTrit::Positive
    } else {
        StructuralTrit::Negative
    }
}

fn input_receipt(input: &JointFieldInput) -> [u8; 32] {
    let mut authority = Authority::new(b"guala.native.joint_field_input.v1");
    authority.usize(input.vertex_ids.len());
    for value in &input.vertex_ids {
        authority.bytes(value.as_bytes());
    }
    authority.usize(input.groups.len());
    for group in &input.groups {
        authority.usize(group.len());
        for index in group {
            authority.usize(*index);
        }
    }
    for time in &input.times {
        authority.rational(time);
    }
    for vector in &input.vectors {
        for value in vector {
            authority.rational(value);
        }
    }
    authority.finish()
}

fn l0_receipt(frames: &[L0Frame]) -> [u8; 32] {
    let mut authority = Authority::new(b"guala.native.joint_field_l0.v1");
    for frame in frames {
        authority.rational(&frame.time);
        authority.rational(&frame.delta_time);
        for field in [&frame.vector, &frame.displacement, &frame.volume] {
            for value in field {
                authority.rational(value);
            }
        }
        for value in &frame.relation {
            authority.relation(value);
        }
        for value in &frame.observed_zero_groups {
            authority.bytes(&[u8::from(*value)]);
        }
    }
    authority.finish()
}

pub fn run_joint_field_l0_l4(
    input: JointFieldInput,
    budget: JointFieldBudget,
) -> Result<JointFieldExperience, JointFieldError> {
    let requirement = validate(&input, budget)?;
    let input = Arc::new(input);
    let topology = edges(requirement.vertices);
    let normalized: Vec<Vec<Exact>> = input
        .vectors
        .iter()
        .map(|vector| normalize(vector, &input.groups))
        .collect();
    let mut frames = Vec::new();
    frames
        .try_reserve_exact(requirement.frames)
        .map_err(|_| JointFieldError::AllocationFailed)?;
    for index in 0..requirement.frames {
        let current = &normalized[index];
        let prior = if index == 0 {
            current
        } else {
            &normalized[index - 1]
        };
        let delta_time = if index == 0 {
            Exact::zero()
        } else {
            &input.times[index] - &input.times[index - 1]
        };
        let displacement = if index == 0 {
            zero_vector(requirement.vertices)
        } else {
            current
                .iter()
                .zip(prior)
                .map(|(now, before)| now - before)
                .collect()
        };
        let volume = displacement
            .iter()
            .map(|value| value.abs() * &delta_time)
            .collect();
        frames.push(L0Frame {
            time: input.times[index].clone(),
            delta_time,
            vector: current.clone(),
            displacement: displacement.clone(),
            volume,
            relation: relation(prior, current, &displacement, &topology),
            observed_zero_groups: input
                .groups
                .iter()
                .map(|group| {
                    group
                        .iter()
                        .all(|position| input.vectors[index][*position].is_zero())
                })
                .collect(),
        });
    }
    let raw_receipt = input_receipt(&input);
    let l0_authority = l0_receipt(&frames);
    let l0 = Arc::new(L0JointField {
        input,
        edges: topology,
        frames,
        raw_authority_receipt_sha256: raw_receipt,
        authority_receipt_sha256: l0_authority,
    });

    let accumulated_volume = (0..requirement.vertices)
        .map(|vertex| {
            l0.frames
                .iter()
                .map(|frame| frame.volume[vertex].clone())
                .sum()
        })
        .collect::<Vec<Exact>>();
    let mut l1_authority = Authority::new(b"guala.native.joint_field_l1_vtvr.v1");
    l1_authority.bytes(&l0.authority_receipt_sha256);
    for value in &accumulated_volume {
        l1_authority.rational(value);
    }
    let l1 = Arc::new(L1Vtvr {
        l0,
        accumulated_volume,
        authority_receipt_sha256: l1_authority.finish(),
    });

    let zero = zero_vector(requirement.vertices);
    let mut velocity = vec![zero.clone()];
    let mut acceleration = vec![zero];
    let mut relation_change = vec![l1.l0.frames[0]
        .relation
        .iter()
        .map(|value| relation_delta(value, value))
        .collect()];
    for index in 1..requirement.frames {
        let delta_time = &l1.l0.frames[index].delta_time;
        let current_velocity = l1.l0.frames[index]
            .vector
            .iter()
            .zip(&l1.l0.frames[index - 1].vector)
            .map(|(current, prior)| (current - prior) / delta_time)
            .collect::<Vec<_>>();
        acceleration.push(
            current_velocity
                .iter()
                .zip(&velocity[index - 1])
                .map(|(current, prior)| (current - prior) / delta_time)
                .collect(),
        );
        velocity.push(current_velocity);
        relation_change.push(
            l1.l0.frames[index - 1]
                .relation
                .iter()
                .zip(&l1.l0.frames[index].relation)
                .map(|(prior, current)| relation_delta(prior, current))
                .collect(),
        );
    }
    let mut l2_authority = Authority::new(b"guala.native.joint_field_l2.v1");
    l2_authority.bytes(&l1.authority_receipt_sha256);
    for field in [&velocity, &acceleration] {
        for frame in field {
            for value in frame {
                l2_authority.rational(value);
            }
        }
    }
    for frame in &relation_change {
        for value in frame {
            l2_authority.relation(value);
        }
    }
    let l2 = Arc::new(L2Geometry {
        l1,
        velocity,
        acceleration,
        relation_change,
        authority_receipt_sha256: l2_authority.finish(),
    });

    let quiescent = l2
        .l1
        .l0
        .frames
        .iter()
        .flat_map(|frame| &frame.volume)
        .all(Zero::is_zero);
    let mut l3_authority = Authority::new(b"guala.native.joint_field_l3.v1");
    l3_authority.bytes(&l2.authority_receipt_sha256);
    l3_authority.bytes(&[u8::from(quiescent)]);
    let l3 = Arc::new(L3ResonanceField {
        l2,
        quiescent,
        authority_receipt_sha256: l3_authority.finish(),
    });

    let d_k = l3
        .l2
        .l1
        .l0
        .frames
        .iter()
        .map(|frame| frame.displacement.clone())
        .collect::<Vec<_>>();
    let m_k = l3.l2.acceleration.clone();
    let mut r_rev_k = vec![vec![false; requirement.vertices]];
    let mut u_star_k = vec![vec![Availability::Genesis; requirement.vertices]];
    let mut p_k = vec![zero_vector(requirement.vertices)];
    let mut b_k = vec![zero_vector(requirement.vertices)];
    for index in 1..requirement.frames {
        r_rev_k.push(
            (0..requirement.vertices)
                .map(|vertex| &d_k[index - 1][vertex] * &d_k[index][vertex] < Exact::zero())
                .collect(),
        );
        u_star_k.push(vec![Availability::Observed; requirement.vertices]);
        p_k.push(m_k[index].iter().map(Signed::abs).collect());
        b_k.push(
            l3.l2.l1.l0.frames[index]
                .volume
                .iter()
                .zip(&l3.l2.l1.l0.frames[index - 1].volume)
                .map(|(current, prior)| current - prior)
                .collect(),
        );
    }
    let mut l4_authority = Authority::new(b"guala.native.joint_field_l4.v1");
    l4_authority.bytes(&l3.authority_receipt_sha256);
    for frame in 0..requirement.frames {
        for vertex in 0..requirement.vertices {
            l4_authority.rational(&d_k[frame][vertex]);
            l4_authority.rational(&m_k[frame][vertex]);
            l4_authority.bytes(&[u8::from(r_rev_k[frame][vertex])]);
            l4_authority.bytes(&[match u_star_k[frame][vertex] {
                Availability::Genesis => 0,
                Availability::Observed => 1,
            }]);
            l4_authority.rational(&p_k[frame][vertex]);
            l4_authority.rational(&b_k[frame][vertex]);
        }
        for relation in &l3.l2.l1.l0.frames[frame].relation {
            l4_authority.relation(relation);
        }
    }
    let l4 = Arc::new(L4JointDsf {
        l3,
        d_k,
        m_k,
        r_rev_k,
        u_star_k,
        p_k,
        b_k,
        authority_receipt_sha256: l4_authority.finish(),
    });
    let mut experience_authority = Authority::new(b"guala.native.joint_field_experience.v1");
    experience_authority.bytes(&l4.l3.l2.l1.l0.raw_authority_receipt_sha256);
    experience_authority.bytes(&l4.l3.l2.l1.l0.authority_receipt_sha256);
    experience_authority.bytes(&l4.l3.l2.l1.authority_receipt_sha256);
    experience_authority.bytes(&l4.l3.l2.authority_receipt_sha256);
    experience_authority.bytes(&l4.l3.authority_receipt_sha256);
    experience_authority.bytes(&l4.authority_receipt_sha256);
    Ok(JointFieldExperience {
        l4,
        requirement,
        authority_receipt_sha256: experience_authority.finish(),
    })
}

pub fn bind_neuron_perspective(
    l4: &L4JointDsf,
    neuron_lineage: [u8; 16],
    vertex_index: usize,
    frame_index: usize,
) -> Result<NeuronFieldPerspective, JointFieldError> {
    let frame = l4
        .l3
        .l2
        .l1
        .l0
        .frames
        .get(frame_index)
        .ok_or(JointFieldError::Invalid(
            "neuron frame is outside the field",
        ))?;
    if vertex_index >= l4.vertex_count() {
        return Err(JointFieldError::Invalid(
            "neuron vertex is outside the field",
        ));
    }
    let incident_cohesion_edges = frame
        .relation
        .iter()
        .enumerate()
        .filter_map(|(index, edge)| {
            (vertex_index == edge.left || vertex_index == edge.right).then_some(index)
        })
        .collect::<Vec<_>>();
    let mut authority = Authority::new(b"guala.native.neuron_field_perspective.v1");
    authority.bytes(&neuron_lineage);
    authority.usize(vertex_index);
    authority.usize(frame_index);
    authority.bytes(&l4.authority_receipt_sha256);
    authority.rational(&l4.d_k[frame_index][vertex_index]);
    authority.rational(&l4.m_k[frame_index][vertex_index]);
    authority.bytes(&[u8::from(l4.r_rev_k[frame_index][vertex_index])]);
    authority.bytes(&[match l4.u_star_k[frame_index][vertex_index] {
        Availability::Genesis => 0,
        Availability::Observed => 1,
    }]);
    for edge_index in &incident_cohesion_edges {
        authority.usize(*edge_index);
        authority.relation(&frame.relation[*edge_index]);
    }
    authority.rational(&l4.p_k[frame_index][vertex_index]);
    authority.rational(&l4.b_k[frame_index][vertex_index]);
    Ok(NeuronFieldPerspective {
        neuron_lineage,
        vertex_index,
        frame_index,
        complete_field_receipt_sha256: l4.authority_receipt_sha256,
        d_k: l4.d_k[frame_index][vertex_index].clone(),
        m_k: l4.m_k[frame_index][vertex_index].clone(),
        r_rev_k: l4.r_rev_k[frame_index][vertex_index],
        u_star_k: l4.u_star_k[frame_index][vertex_index],
        incident_cohesion_edges,
        p_k: l4.p_k[frame_index][vertex_index].clone(),
        b_k: l4.b_k[frame_index][vertex_index].clone(),
        authority_receipt_sha256: authority.finish(),
    })
}

pub fn reconstruct_cohesion(
    l4: &L4JointDsf,
    perspectives: &[NeuronFieldPerspective],
) -> Result<Vec<RelationFact>, JointFieldError> {
    if perspectives.len() != l4.vertex_count() {
        return Err(JointFieldError::Invalid(
            "neuron perspectives do not cover every field vertex",
        ));
    }
    let frame_index = perspectives
        .first()
        .ok_or(JointFieldError::Invalid("neuron perspectives are empty"))?
        .frame_index;
    let cohesion = l4
        .cohesion(frame_index)
        .ok_or(JointFieldError::Invalid("cohesion frame is absent"))?;
    let mut vertices = BTreeSet::new();
    let mut edge_witnesses = BTreeMap::<usize, usize>::new();
    for perspective in perspectives {
        if perspective.complete_field_receipt_sha256 != l4.authority_receipt_sha256
            || perspective.frame_index != frame_index
            || !vertices.insert(perspective.vertex_index)
        {
            return Err(JointFieldError::Invalid(
                "neuron perspectives do not share one field frame",
            ));
        }
        for edge_index in &perspective.incident_cohesion_edges {
            let edge = cohesion.get(*edge_index).ok_or(JointFieldError::Invalid(
                "neuron perspective references a missing cohesion edge",
            ))?;
            if perspective.vertex_index != edge.left && perspective.vertex_index != edge.right {
                return Err(JointFieldError::Invalid(
                    "neuron perspective references a nonincident edge",
                ));
            }
            *edge_witnesses.entry(*edge_index).or_default() += 1;
        }
    }
    if vertices != (0..l4.vertex_count()).collect()
        || edge_witnesses.len() != cohesion.len()
        || edge_witnesses.values().any(|count| *count != 2)
    {
        return Err(JointFieldError::Invalid(
            "neuron perspectives do not close the cohesion field",
        ));
    }
    Ok(cohesion.to_vec())
}

pub fn settle_dsf_delivery_impression(
    l4: &L4JointDsf,
    perspective: &NeuronFieldPerspective,
    predecessor: Option<&DsfDeliveryImpression>,
) -> Result<DsfDeliveryImpression, JointFieldError> {
    if perspective.complete_field_receipt_sha256 != l4.authority_receipt_sha256 {
        return Err(JointFieldError::Invalid(
            "delivery-impression perspective does not belong to the joint field",
        ));
    }
    if predecessor.is_some_and(|value| value.neuron_lineage != perspective.neuron_lineage) {
        return Err(JointFieldError::Invalid(
            "delivery-impression predecessor belongs to another neuron",
        ));
    }
    let cohesion = l4
        .cohesion(perspective.frame_index)
        .ok_or(JointFieldError::Invalid(
            "delivery-impression cohesion frame is absent",
        ))?;
    let mut impression = Vec::new();
    impression
        .try_reserve_exact(6 + perspective.incident_cohesion_edges.len() * 4)
        .map_err(|_| JointFieldError::AllocationFailed)?;
    impression.extend([
        structural_trit(&perspective.d_k),
        structural_trit(&perspective.m_k),
        if perspective.r_rev_k {
            StructuralTrit::Positive
        } else {
            StructuralTrit::Quiescent
        },
        match perspective.u_star_k {
            Availability::Genesis => StructuralTrit::Quiescent,
            Availability::Observed => StructuralTrit::Positive,
        },
        structural_trit(&perspective.p_k),
        structural_trit(&perspective.b_k),
    ]);
    for edge_index in &perspective.incident_cohesion_edges {
        let edge = cohesion.get(*edge_index).ok_or(JointFieldError::Invalid(
            "delivery-impression perspective references a missing edge",
        ))?;
        impression.extend([
            structural_trit(&edge.prior_product),
            structural_trit(&edge.current_product),
            structural_trit(&edge.displacement_product),
            structural_trit(&edge.oriented_area),
        ]);
    }
    let (matching_nonnull, matching_quiescent, contradictions) = predecessor
        .map(|prior| {
            if prior.delivery_sign_impression.len() != impression.len() {
                return Err(JointFieldError::Invalid(
                    "delivery-impression topology changed across recurrence",
                ));
            }
            Ok(prior.delivery_sign_impression.iter().zip(&impression).fold(
                (0usize, 0usize, 0usize),
                |mut counts, (left, right)| {
                    if left == right {
                        if *left == StructuralTrit::Quiescent {
                            counts.1 += 1;
                        } else {
                            counts.0 += 1;
                        }
                    } else if *left != StructuralTrit::Quiescent
                        && *right != StructuralTrit::Quiescent
                    {
                        counts.2 += 1;
                    }
                    counts
                },
            ))
        })
        .transpose()?
        .unwrap_or((0, 0, 0));
    let mut recurrence_authority = Authority::new(b"guala.native.dsf_delivery_recurrence.v1");
    recurrence_authority.usize(impression.len());
    recurrence_authority.usize(matching_nonnull);
    recurrence_authority.usize(matching_quiescent);
    recurrence_authority.usize(contradictions);
    recurrence_authority.bytes(&[u8::from(predecessor.is_some())]);
    let recurrence = DsfDeliveryRecurrence {
        coordinate_count: impression.len(),
        matching_nonnull,
        matching_quiescent,
        contradictions,
        predecessor_present: predecessor.is_some(),
        authority_receipt_sha256: recurrence_authority.finish(),
    };
    let mut authority = Authority::new(b"guala.native.dsf_delivery_impression.v1");
    authority.bytes(&perspective.neuron_lineage);
    authority.bytes(&perspective.complete_field_receipt_sha256);
    authority.bytes(&perspective.authority_receipt_sha256);
    if let Some(prior) = predecessor {
        authority.bytes(&prior.authority_receipt_sha256);
    } else {
        authority.bytes(&[]);
    }
    for value in &impression {
        authority.bytes(&[*value as i8 as u8]);
    }
    authority.bytes(&recurrence.authority_receipt_sha256);
    Ok(DsfDeliveryImpression {
        neuron_lineage: perspective.neuron_lineage,
        complete_field_receipt_sha256: perspective.complete_field_receipt_sha256,
        perspective_receipt_sha256: perspective.authority_receipt_sha256,
        predecessor_impression_receipt_sha256: predecessor
            .map(|value| value.authority_receipt_sha256),
        delivery_sign_impression: impression,
        delivery_recurrence: recurrence,
        authority_receipt_sha256: authority.finish(),
    })
}

pub fn verify_dsf_delivery_impression(
    value: &DsfDeliveryImpression,
) -> Result<(), JointFieldError> {
    let recurrence = &value.delivery_recurrence;
    if recurrence.coordinate_count != value.delivery_sign_impression.len()
        || recurrence
            .matching_nonnull
            .checked_add(recurrence.matching_quiescent)
            .and_then(|count| count.checked_add(recurrence.contradictions))
            .is_none_or(|count| count > recurrence.coordinate_count)
        || recurrence.predecessor_present != value.predecessor_impression_receipt_sha256.is_some()
    {
        return Err(JointFieldError::Invalid(
            "delivery recurrence evidence is incoherent",
        ));
    }
    let mut recurrence_authority = Authority::new(b"guala.native.dsf_delivery_recurrence.v1");
    recurrence_authority.usize(recurrence.coordinate_count);
    recurrence_authority.usize(recurrence.matching_nonnull);
    recurrence_authority.usize(recurrence.matching_quiescent);
    recurrence_authority.usize(recurrence.contradictions);
    recurrence_authority.bytes(&[u8::from(recurrence.predecessor_present)]);
    if recurrence_authority.finish() != recurrence.authority_receipt_sha256 {
        return Err(JointFieldError::Invalid(
            "delivery recurrence authority changed",
        ));
    }
    let mut authority = Authority::new(b"guala.native.dsf_delivery_impression.v1");
    authority.bytes(&value.neuron_lineage);
    authority.bytes(&value.complete_field_receipt_sha256);
    authority.bytes(&value.perspective_receipt_sha256);
    if let Some(prior) = value.predecessor_impression_receipt_sha256 {
        authority.bytes(&prior);
    } else {
        authority.bytes(&[]);
    }
    for trit in &value.delivery_sign_impression {
        authority.bytes(&[*trit as i8 as u8]);
    }
    authority.bytes(&recurrence.authority_receipt_sha256);
    if authority.finish() != value.authority_receipt_sha256 {
        return Err(JointFieldError::Invalid(
            "DSF delivery impression authority changed",
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    struct DifferentialAuthority(Sha256);

    impl DifferentialAuthority {
        fn new() -> Self {
            let mut value = Sha256::new();
            let domain = b"guala.test.python_native_joint_field.v1";
            value.update((domain.len() as u64).to_be_bytes());
            value.update(domain);
            Self(value)
        }

        fn bytes(&mut self, value: &[u8]) {
            self.0.update((value.len() as u64).to_be_bytes());
            self.0.update(value);
        }

        fn usize(&mut self, value: usize) {
            self.0.update((value as u64).to_be_bytes());
        }

        fn rational(&mut self, value: &Exact) {
            self.bytes(format!("{}/{}", value.numer(), value.denom()).as_bytes());
        }

        fn relation(&mut self, value: &RelationFact) {
            self.usize(value.left);
            self.usize(value.right);
            self.rational(&value.prior_product);
            self.rational(&value.current_product);
            self.rational(&value.displacement_product);
            self.rational(&value.oriented_area);
        }

        fn hex(self) -> String {
            self.0
                .finalize()
                .iter()
                .map(|value| format!("{value:02x}"))
                .collect()
        }
    }

    fn q(numerator: i64, denominator: i64) -> Exact {
        Exact::new(BigInt::from(numerator), BigInt::from(denominator))
    }

    fn input(multiplier: i64, changed_third: bool) -> JointFieldInput {
        let third = if changed_third { 4 } else { 3 };
        JointFieldInput {
            vertex_ids: vec!["sight:left".into(), "sound:left".into(), "body:hand".into()],
            groups: vec![vec![0, 1, 2]],
            times: vec![q(0, 1), q(1, 3), q(2, 3)],
            vectors: vec![
                vec![q(multiplier, 1), q(2 * multiplier, 1), q(3 * multiplier, 1)],
                vec![
                    q(2 * multiplier, 1),
                    q(multiplier, 1),
                    q(third * multiplier, 1),
                ],
                vec![
                    q(-multiplier, 1),
                    q(3 * multiplier, 1),
                    q(2 * multiplier, 1),
                ],
            ],
        }
    }

    fn budget(value: &JointFieldInput) -> JointFieldBudget {
        let required = derive_requirement(value).unwrap();
        JointFieldBudget {
            max_input_bytes: required.input_bytes,
            max_vertices: required.vertices,
            max_frames: required.frames,
            max_edges: required.edges,
            max_relation_facts: required.relation_facts,
            max_vertex_frame_values: required.vertex_frame_values,
        }
    }

    #[test]
    fn exact_joint_field_is_deterministic_and_nonflattened() {
        let value = input(1, false);
        let first = run_joint_field_l0_l4(value.clone(), budget(&value)).unwrap();
        let second = run_joint_field_l0_l4(value.clone(), budget(&value)).unwrap();
        assert_eq!(first, second);
        assert_eq!(first.requirement.vertices, 3);
        assert_eq!(first.requirement.edges, 3);
        assert_eq!(first.requirement.relation_facts, 9);
        assert_eq!(first.l4.cohesion(1).unwrap().len(), 3);
        assert_eq!(first.l4.d_k.len(), 3);
        assert_eq!(first.l4.d_k[1].len(), 3);
    }

    #[test]
    fn common_positive_gain_changes_raw_custody_not_structure() {
        let original = input(1, false);
        let gained = input(7, false);
        let left = run_joint_field_l0_l4(original.clone(), budget(&original)).unwrap();
        let right = run_joint_field_l0_l4(gained.clone(), budget(&gained)).unwrap();
        assert_ne!(
            left.l4.l3.l2.l1.l0.raw_authority_receipt_sha256,
            right.l4.l3.l2.l1.l0.raw_authority_receipt_sha256
        );
        assert_eq!(left.l4.l3.l2.l1.l0.frames, right.l4.l3.l2.l1.l0.frames);
        assert_eq!(
            left.l4.authority_receipt_sha256,
            right.l4.authority_receipt_sha256
        );
    }

    #[test]
    fn one_neuron_retains_vertex_fields_and_incident_relations() {
        let value = input(1, false);
        let experience = run_joint_field_l0_l4(value.clone(), budget(&value)).unwrap();
        let perspective = bind_neuron_perspective(&experience.l4, [1; 16], 0, 1).unwrap();
        assert_eq!(perspective.d_k, experience.l4.d_k[1][0]);
        assert_eq!(perspective.m_k, experience.l4.m_k[1][0]);
        assert_eq!(perspective.incident_cohesion_edges, vec![0, 1]);
        assert_eq!(
            perspective.complete_field_receipt_sha256,
            experience.l4.authority_receipt_sha256
        );
    }

    #[test]
    fn another_vertex_changes_the_reached_neurons_relational_perspective() {
        let baseline = input(1, false);
        let changed = input(1, true);
        let baseline = run_joint_field_l0_l4(baseline.clone(), budget(&baseline)).unwrap();
        let changed = run_joint_field_l0_l4(changed.clone(), budget(&changed)).unwrap();
        let left = bind_neuron_perspective(&baseline.l4, [1; 16], 0, 1).unwrap();
        let right = bind_neuron_perspective(&changed.l4, [1; 16], 0, 1).unwrap();
        assert_ne!(
            left.authority_receipt_sha256,
            right.authority_receipt_sha256
        );
    }

    #[test]
    fn three_neurons_close_the_complete_cohesion_field() {
        let value = input(1, false);
        let experience = run_joint_field_l0_l4(value.clone(), budget(&value)).unwrap();
        let perspectives = (0..3)
            .map(|index| {
                bind_neuron_perspective(&experience.l4, [index as u8; 16], index, 1).unwrap()
            })
            .collect::<Vec<_>>();
        assert_eq!(
            reconstruct_cohesion(&experience.l4, &perspectives).unwrap(),
            experience.l4.cohesion(1).unwrap()
        );
        assert!(reconstruct_cohesion(&experience.l4, &perspectives[..2]).is_err());
    }

    #[test]
    fn derived_budget_refuses_before_joint_field_construction() {
        let value = input(1, false);
        let mut constrained = budget(&value);
        constrained.max_relation_facts -= 1;
        assert_eq!(
            run_joint_field_l0_l4(value, constrained).unwrap_err(),
            JointFieldError::BudgetExceeded {
                resource: "relation facts",
                required: 9,
                available: 8,
            }
        );
    }

    #[test]
    fn matches_complete_python_vtvr_golden_field() {
        let value = input(1, false);
        let experience = run_joint_field_l0_l4(value.clone(), budget(&value)).unwrap();
        let mut authority = DifferentialAuthority::new();
        for frame in &experience.l4.l3.l2.l1.l0.frames {
            for field in [&frame.vector, &frame.displacement, &frame.volume] {
                for value in field {
                    authority.rational(value);
                }
            }
            for value in &frame.relation {
                authority.relation(value);
            }
        }
        for field in [
            &experience.l4.l3.l2.velocity,
            &experience.l4.l3.l2.acceleration,
        ] {
            for frame in field {
                for value in frame {
                    authority.rational(value);
                }
            }
        }
        for frame in &experience.l4.l3.l2.relation_change {
            for value in frame {
                authority.relation(value);
            }
        }
        authority.bytes(&[u8::from(experience.l4.l3.quiescent)]);
        for frame in 0..experience.requirement.frames {
            for vertex in 0..experience.requirement.vertices {
                authority.rational(&experience.l4.d_k[frame][vertex]);
                authority.rational(&experience.l4.m_k[frame][vertex]);
                authority.bytes(&[u8::from(experience.l4.r_rev_k[frame][vertex])]);
                authority.bytes(&[match experience.l4.u_star_k[frame][vertex] {
                    Availability::Genesis => 0,
                    Availability::Observed => 1,
                }]);
                authority.rational(&experience.l4.p_k[frame][vertex]);
                authority.rational(&experience.l4.b_k[frame][vertex]);
            }
            for value in experience.l4.cohesion(frame).unwrap() {
                authority.relation(value);
            }
        }
        assert_eq!(
            authority.hex(),
            "7362182eab89ee0b8122437e8347d27bd641356b7685602da66ea0f38375d884"
        );
    }

    #[test]
    fn one_perspective_settles_a_compact_dsf_delivery_impression() {
        let value = input(1, false);
        let experience = run_joint_field_l0_l4(value.clone(), budget(&value)).unwrap();
        let perspective = bind_neuron_perspective(&experience.l4, [9; 16], 0, 1).unwrap();
        let impression =
            settle_dsf_delivery_impression(&experience.l4, &perspective, None).unwrap();
        assert_eq!(impression.delivery_sign_impression.len(), 14);
        assert_eq!(
            impression.perspective_receipt_sha256,
            perspective.authority_receipt_sha256
        );
        assert_eq!(impression.delivery_recurrence.coordinate_count, 14);
        assert!(!impression.delivery_recurrence.predecessor_present);
        assert_eq!(impression.delivery_recurrence.matching_nonnull, 0);
    }

    #[test]
    fn recurrence_produces_exact_delivery_evidence_without_a_score() {
        let value = input(1, false);
        let experience = run_joint_field_l0_l4(value.clone(), budget(&value)).unwrap();
        let perspective = bind_neuron_perspective(&experience.l4, [9; 16], 0, 1).unwrap();
        let first = settle_dsf_delivery_impression(&experience.l4, &perspective, None).unwrap();
        let second =
            settle_dsf_delivery_impression(&experience.l4, &perspective, Some(&first)).unwrap();
        assert_eq!(
            first.delivery_sign_impression,
            second.delivery_sign_impression
        );
        assert!(second.delivery_recurrence.predecessor_present);
        assert_eq!(
            second.delivery_recurrence.matching_nonnull
                + second.delivery_recurrence.matching_quiescent,
            second.delivery_recurrence.coordinate_count
        );
        assert_eq!(second.delivery_recurrence.contradictions, 0);
        assert_eq!(
            second.predecessor_impression_receipt_sha256,
            Some(first.authority_receipt_sha256)
        );
        assert_ne!(
            first.authority_receipt_sha256,
            second.authority_receipt_sha256
        );
    }

    #[test]
    fn three_perspectives_produce_distinct_impressions_of_one_closed_field() {
        let value = input(1, false);
        let experience = run_joint_field_l0_l4(value.clone(), budget(&value)).unwrap();
        let perspectives = (0..3)
            .map(|index| {
                bind_neuron_perspective(&experience.l4, [index as u8; 16], index, 1).unwrap()
            })
            .collect::<Vec<_>>();
        reconstruct_cohesion(&experience.l4, &perspectives).unwrap();
        let impressions = perspectives
            .iter()
            .map(|value| settle_dsf_delivery_impression(&experience.l4, value, None).unwrap())
            .collect::<Vec<_>>();
        assert_eq!(
            impressions
                .iter()
                .map(|value| value.authority_receipt_sha256)
                .collect::<BTreeSet<_>>()
                .len(),
            3
        );
    }
}
