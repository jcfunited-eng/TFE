//! Ratified neuron ingress from one shared UF v1.4 occurrence.
//!
//! This module does not transition a neuron and cannot emit a neuronal
//! fractal.  It establishes the first lawful boundary required before that
//! transition: one stored complete joint result, one bounded coordinate-local
//! SEV view per reached neuron, and exact MathLoom representation of all seven
//! shared DSF fields. Sparse physical contacts are separate anatomy; they are
//! neither DSF content nor copied into this occurrence carrier.
//!
//! No UF operation is repeated here.  No per-vertex L4 value, synthetic edge,
//! availability bit, sign projection, score, owner, lock, receipt loop, or
//! persistence operation participates in the physics.

use std::sync::Arc;

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, ToPrimitive, Zero};

use crate::joint_source_episode::NativeJointSourceEpisode;
use crate::joint_uf_source_adapter::{
    evaluate_occurrence, evaluate_occurrence_with_admission, EvaluatedJointSourceOccurrence,
    JointUfSourceAdmission, JointUfSourceError,
};
use crate::joint_uf_v1_4::{DsfField, JointUfGate, JointUfResult, SevFrame};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum JointNeuronBoundaryError {
    Source(JointUfSourceError),
    OccurrenceAbsent,
    NotAnIsolatedSingleVertexOccurrence,
    MalformedSharedFieldShape,
    NeuronCoordinateAbsent,
    GateAbsent,
    FrameOutsideGate,
    NonFiniteDsf,
    EmptyMathLoomAnatomy,
    MathLoomAnatomyTooSmall {
        required_positions: usize,
        mounted_positions: usize,
    },
    AllocationFailed,
}

impl From<JointUfSourceError> for JointNeuronBoundaryError {
    fn from(value: JointUfSourceError) -> Self {
        Self::Source(value)
    }
}

/// One complete joint field body retained once.  The source bytes are shared
/// by `Arc`; they are not copied into a neuron or MathLoom delivery.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SharedCompleteJointField {
    source_body: Arc<[u8]>,
    source_authority: [u8; 32],
    occurrence_index: usize,
    evaluated: Arc<EvaluatedJointSourceOccurrence>,
}

impl SharedCompleteJointField {
    pub(crate) fn source_body(&self) -> &Arc<[u8]> {
        &self.source_body
    }

    pub(crate) fn source_authority(&self) -> [u8; 32] {
        self.source_authority
    }

    pub(crate) fn occurrence_index(&self) -> usize {
        self.occurrence_index
    }

    pub(crate) fn result(&self) -> &JointUfResult {
        &self.evaluated.field
    }

    pub(crate) fn port_indices(&self) -> &[usize] {
        &self.evaluated.port_indices
    }

    pub(crate) fn groups(&self) -> &[Vec<usize>] {
        &self.evaluated.groups
    }

    pub(crate) fn vertex_count(&self) -> usize {
        self.evaluated.port_indices.len()
    }
}

/// Evaluate one admitted source occurrence exactly once. The resulting shared
/// field is valid only when every SEV frame retains every declared vertex.
pub(crate) fn prepare_complete_joint_field(
    episode: &NativeJointSourceEpisode,
    occurrence_index: usize,
) -> Result<SharedCompleteJointField, JointNeuronBoundaryError> {
    if episode
        .joint_source_occurrences()
        .get(occurrence_index)
        .is_none()
    {
        return Err(JointNeuronBoundaryError::OccurrenceAbsent);
    }
    let evaluated = evaluate_occurrence(episode, occurrence_index)?;
    prepare_complete_joint_field_from_evaluated(
        episode.joint_source_body(),
        episode.joint_source_authority_receipt(),
        occurrence_index,
        evaluated,
    )
}

/// Evaluate one source occurrence with independently admitted causal time.
/// Source-authored affine maps supply every physical coordinate bound.
pub(crate) fn prepare_complete_joint_field_with_admission(
    episode: &NativeJointSourceEpisode,
    occurrence_index: usize,
    admission: &JointUfSourceAdmission,
) -> Result<SharedCompleteJointField, JointNeuronBoundaryError> {
    if episode
        .joint_source_occurrences()
        .get(occurrence_index)
        .is_none()
    {
        return Err(JointNeuronBoundaryError::OccurrenceAbsent);
    }
    let evaluated = evaluate_occurrence_with_admission(episode, occurrence_index, admission)?;
    prepare_complete_joint_field_from_evaluated(
        episode.joint_source_body(),
        episode.joint_source_authority_receipt(),
        occurrence_index,
        evaluated,
    )
}

/// Evaluate one admitted source occurrence exactly once and prepare the
/// explicit empty-contact topology used by the one-neuron golden proof.
pub(crate) fn prepare_isolated_single_neuron_field(
    episode: &NativeJointSourceEpisode,
    occurrence_index: usize,
) -> Result<SharedCompleteJointField, JointNeuronBoundaryError> {
    let shared = prepare_complete_joint_field(episode, occurrence_index)?;
    require_isolated_single_vertex(shared)
}

pub(crate) fn prepare_isolated_single_neuron_field_with_admission(
    episode: &NativeJointSourceEpisode,
    occurrence_index: usize,
    admission: &JointUfSourceAdmission,
) -> Result<SharedCompleteJointField, JointNeuronBoundaryError> {
    let shared = prepare_complete_joint_field_with_admission(episode, occurrence_index, admission)?;
    require_isolated_single_vertex(shared)
}

fn prepare_complete_joint_field_from_evaluated(
    source_body: Arc<[u8]>,
    source_authority: [u8; 32],
    occurrence_index: usize,
    evaluated: EvaluatedJointSourceOccurrence,
) -> Result<SharedCompleteJointField, JointNeuronBoundaryError> {
    let vertex_count = evaluated.port_indices.len();
    if vertex_count == 0
        || evaluated.field.sev.iter().any(|frame| {
            frame.field.len() != vertex_count || frame.delta_field.len() != vertex_count
        })
    {
        return Err(JointNeuronBoundaryError::MalformedSharedFieldShape);
    }
    Ok(SharedCompleteJointField {
        source_body,
        source_authority,
        occurrence_index,
        evaluated: Arc::new(evaluated),
    })
}

fn require_isolated_single_vertex(
    shared: SharedCompleteJointField,
) -> Result<SharedCompleteJointField, JointNeuronBoundaryError> {
    if shared.vertex_count() != 1
        || shared.groups().len() != 1
        || shared.groups()[0].as_slice() != [0]
    {
        return Err(JointNeuronBoundaryError::NotAnIsolatedSingleVertexOccurrence);
    }
    Ok(shared)
}

#[cfg(test)]
pub(crate) fn prepare_isolated_single_neuron_field_fixture(
    source_body: Arc<[u8]>,
    source_authority: [u8; 32],
    occurrence_index: usize,
    evaluated: EvaluatedJointSourceOccurrence,
) -> Result<SharedCompleteJointField, JointNeuronBoundaryError> {
    require_isolated_single_vertex(prepare_complete_joint_field_from_evaluated(
        source_body,
        source_authority,
        occurrence_index,
        evaluated,
    )?)
}

#[cfg(test)]
pub(crate) fn prepare_complete_joint_field_fixture(
    source_body: Arc<[u8]>,
    source_authority: [u8; 32],
    occurrence_index: usize,
    evaluated: EvaluatedJointSourceOccurrence,
) -> Result<SharedCompleteJointField, JointNeuronBoundaryError> {
    prepare_complete_joint_field_from_evaluated(
        source_body,
        source_authority,
        occurrence_index,
        evaluated,
    )
}

/// Test-only admitted fixture evaluation: fixture episodes author their own
/// coordinate bounds, and their source times span at most two units, so an
/// explicit five-unit maximum causal interval admits every fixture gate.
#[cfg(test)]
pub(crate) fn prepare_complete_joint_field_admitted_fixture(
    episode: &NativeJointSourceEpisode,
    occurrence_index: usize,
) -> Result<SharedCompleteJointField, JointNeuronBoundaryError> {
    prepare_complete_joint_field_with_admission(
        episode,
        occurrence_index,
        &JointUfSourceAdmission::new(BigRational::from_integer(BigInt::from(5))).unwrap(),
    )
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct JointNeuronPerspective<'a> {
    shared: &'a SharedCompleteJointField,
    gate_index: usize,
    coordinate_index: usize,
}

impl<'a> JointNeuronPerspective<'a> {
    pub(crate) fn shared(self) -> &'a SharedCompleteJointField {
        self.shared
    }

    pub(crate) fn gate(self) -> &'a JointUfGate {
        &self.shared.result().gates[self.gate_index]
    }

    pub(crate) fn dsf(self) -> &'a DsfField {
        &self.gate().dsf
    }

    pub(crate) fn coordinate_index(self) -> usize {
        self.coordinate_index
    }

    pub(crate) fn local_sev_len(self) -> usize {
        let interval = self.gate().interval;
        interval.last_sev - interval.first_sev + 1
    }

    pub(crate) fn local_sev(
        self,
        local_frame_index: usize,
    ) -> Result<LocalSevComponent<'a>, JointNeuronBoundaryError> {
        let interval = self.gate().interval;
        let source_index = interval
            .first_sev
            .checked_add(local_frame_index)
            .filter(|index| *index <= interval.last_sev)
            .ok_or(JointNeuronBoundaryError::FrameOutsideGate)?;
        let frame = self
            .shared
            .result()
            .sev
            .get(source_index)
            .ok_or(JointNeuronBoundaryError::FrameOutsideGate)?;
        Ok(LocalSevComponent {
            frame,
            coordinate_index: self.coordinate_index,
        })
    }
}

pub(crate) fn bind_neuron_perspective(
    shared: &SharedCompleteJointField,
    coordinate_index: usize,
    gate_index: usize,
) -> Result<JointNeuronPerspective<'_>, JointNeuronBoundaryError> {
    if coordinate_index >= shared.vertex_count() {
        return Err(JointNeuronBoundaryError::NeuronCoordinateAbsent);
    }
    if shared.result().gates.get(gate_index).is_none() {
        return Err(JointNeuronBoundaryError::GateAbsent);
    }
    Ok(JointNeuronPerspective {
        shared,
        gate_index,
        coordinate_index,
    })
}

pub(crate) fn bind_isolated_neuron_perspective(
    shared: &SharedCompleteJointField,
    gate_index: usize,
) -> Result<JointNeuronPerspective<'_>, JointNeuronBoundaryError> {
    if shared.vertex_count() != 1 {
        return Err(JointNeuronBoundaryError::NotAnIsolatedSingleVertexOccurrence);
    }
    bind_neuron_perspective(shared, 0, gate_index)
}

/// A borrowed single-coordinate view into one shared SEV frame.  The complete
/// vector remains stored once in the shared result.
#[derive(Clone, Copy, Debug)]
pub(crate) struct LocalSevComponent<'a> {
    frame: &'a SevFrame,
    coordinate_index: usize,
}

impl LocalSevComponent<'_> {
    pub(crate) fn source_index(self) -> usize {
        self.frame.source_index
    }

    pub(crate) fn field(self) -> f64 {
        self.frame.field[self.coordinate_index]
    }

    pub(crate) fn delta_field(self) -> f64 {
        self.frame.delta_field[self.coordinate_index]
    }

    pub(crate) fn shared_delta_norm(self) -> f64 {
        self.frame.delta_norm
    }

    pub(crate) fn shared_sigma(self) -> f64 {
        self.frame.sigma
    }

    pub(crate) fn shared_kappa(self) -> f64 {
        self.frame.kappa
    }

    pub(crate) fn joint_relevance(self) -> f64 {
        self.frame.relevance
    }

    pub(crate) fn shared_negative_space(self) -> bool {
        self.frame.negative_space
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(i8)]
pub(crate) enum BalancedTrit {
    Negative = -1,
    Quiescent = 0,
    Positive = 1,
}

impl BalancedTrit {
    fn as_bigint(self) -> BigInt {
        BigInt::from(self as i8)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DsfFactFamily {
    Displacement,
    Motion,
    Reversal,
    Uncertainty,
    Cohesion,
    Pressure,
    Breathing,
}

const DSF_FACT_FAMILIES: [DsfFactFamily; 7] = [
    DsfFactFamily::Displacement,
    DsfFactFamily::Motion,
    DsfFactFamily::Reversal,
    DsfFactFamily::Uncertainty,
    DsfFactFamily::Cohesion,
    DsfFactFamily::Pressure,
    DsfFactFamily::Breathing,
];

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ExactTernaryWord {
    numerator: Box<[BalancedTrit]>,
    denominator: Box<[BalancedTrit]>,
}

impl ExactTernaryWord {
    pub(crate) fn numerator(&self) -> &[BalancedTrit] {
        &self.numerator
    }

    pub(crate) fn denominator(&self) -> &[BalancedTrit] {
        &self.denominator
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct TypedMathLoomConstraint {
    family: DsfFactFamily,
    binary64_bits: u64,
    exact_value: BigRational,
    word: ExactTernaryWord,
}

impl TypedMathLoomConstraint {
    pub(crate) fn family(&self) -> DsfFactFamily {
        self.family
    }

    pub(crate) fn binary64_bits(&self) -> u64 {
        self.binary64_bits
    }

    pub(crate) fn exact_value(&self) -> &BigRational {
        &self.exact_value
    }

    pub(crate) fn word(&self) -> &ExactTernaryWord {
        &self.word
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MathLoomAnatomy {
    positions: usize,
}

impl MathLoomAnatomy {
    pub(crate) fn new(positions: usize) -> Result<Self, JointNeuronBoundaryError> {
        if positions == 0 {
            return Err(JointNeuronBoundaryError::EmptyMathLoomAnatomy);
        }
        Ok(Self { positions })
    }

    pub(crate) fn positions(self) -> usize {
        self.positions
    }
}

#[derive(Clone, Debug)]
pub(crate) struct BorrowedMathLoomDelivery<'a> {
    perspective: JointNeuronPerspective<'a>,
    constraints: Box<[TypedMathLoomConstraint]>,
}

impl<'a> BorrowedMathLoomDelivery<'a> {
    pub(crate) fn perspective(&self) -> JointNeuronPerspective<'a> {
        self.perspective
    }

    pub(crate) fn constraints(&self) -> &[TypedMathLoomConstraint] {
        &self.constraints
    }
}

/// Convert all seven shared DSF values into exact rational balanced ternary.
/// The original binary64 bits remain alongside the exact rational word.
pub(crate) fn settle_shared_dsf_mathloom<'a>(
    perspective: JointNeuronPerspective<'a>,
    anatomy: MathLoomAnatomy,
) -> Result<BorrowedMathLoomDelivery<'a>, JointNeuronBoundaryError> {
    let values = perspective.dsf().ordered();
    let mut constraints = Vec::new();
    constraints
        .try_reserve_exact(values.len())
        .map_err(|_| JointNeuronBoundaryError::AllocationFailed)?;
    for (family, value) in DSF_FACT_FAMILIES.into_iter().zip(values) {
        if !value.is_finite() {
            return Err(JointNeuronBoundaryError::NonFiniteDsf);
        }
        let exact_value =
            BigRational::from_float(value).ok_or(JointNeuronBoundaryError::NonFiniteDsf)?;
        let required_positions = required_positions(&exact_value);
        if required_positions > anatomy.positions {
            return Err(JointNeuronBoundaryError::MathLoomAnatomyTooSmall {
                required_positions,
                mounted_positions: anatomy.positions,
            });
        }
        constraints.push(TypedMathLoomConstraint {
            family,
            binary64_bits: value.to_bits(),
            word: encode_exact(&exact_value, anatomy.positions)?,
            exact_value,
        });
    }
    Ok(BorrowedMathLoomDelivery {
        perspective,
        constraints: constraints.into_boxed_slice(),
    })
}

/// Derive the smallest mounted positional width that retains every explicit
/// DSF numerator and denominator bit-exactly for this reached gate. This is a
/// growth requirement, not a heuristic capacity estimate.
pub(crate) fn required_mathloom_positions(
    perspective: JointNeuronPerspective<'_>,
) -> Result<usize, JointNeuronBoundaryError> {
    perspective
        .dsf()
        .ordered()
        .into_iter()
        .map(|value| {
            if !value.is_finite() {
                return Err(JointNeuronBoundaryError::NonFiniteDsf);
            }
            let exact =
                BigRational::from_float(value).ok_or(JointNeuronBoundaryError::NonFiniteDsf)?;
            Ok(required_positions(&exact))
        })
        .try_fold(1_usize, |maximum, required| {
            required.map(|required| maximum.max(required))
        })
}

fn required_positions(value: &BigRational) -> usize {
    balanced_digits(value.numer()).max(balanced_digits(value.denom()))
}

fn balanced_digits(value: &BigInt) -> usize {
    if value.is_zero() {
        return 1;
    }
    let mut residual = value.clone();
    let three = BigInt::from(3_u8);
    let mut digits = 0_usize;
    while !residual.is_zero() {
        let remainder = normalized_remainder(&residual);
        residual = match remainder {
            0 => residual / &three,
            1 => (residual - 1_u8) / &three,
            2 => (residual + 1_u8) / &three,
            _ => unreachable!(),
        };
        digits += 1;
    }
    digits
}

fn encode_exact(
    value: &BigRational,
    positions: usize,
) -> Result<ExactTernaryWord, JointNeuronBoundaryError> {
    Ok(ExactTernaryWord {
        numerator: encode_integer(value.numer(), positions)?.into_boxed_slice(),
        denominator: encode_integer(value.denom(), positions)?.into_boxed_slice(),
    })
}

fn encode_integer(
    value: &BigInt,
    positions: usize,
) -> Result<Vec<BalancedTrit>, JointNeuronBoundaryError> {
    let mut output = Vec::new();
    output
        .try_reserve_exact(positions)
        .map_err(|_| JointNeuronBoundaryError::AllocationFailed)?;
    let mut residual = value.clone();
    let three = BigInt::from(3_u8);
    for _ in 0..positions {
        let remainder = normalized_remainder(&residual);
        let trit = match remainder {
            0 => {
                residual /= &three;
                BalancedTrit::Quiescent
            }
            1 => {
                residual = (residual - 1_u8) / &three;
                BalancedTrit::Positive
            }
            2 => {
                residual = (residual + 1_u8) / &three;
                BalancedTrit::Negative
            }
            _ => unreachable!(),
        };
        output.push(trit);
    }
    if !residual.is_zero() {
        return Err(JointNeuronBoundaryError::MathLoomAnatomyTooSmall {
            required_positions: balanced_digits(value),
            mounted_positions: positions,
        });
    }
    Ok(output)
}

fn normalized_remainder(value: &BigInt) -> u8 {
    let three = BigInt::from(3_u8);
    match (value % &three)
        .to_i8()
        .expect("modulo-three remainder fits i8")
    {
        -2 => 1,
        -1 => 2,
        0 => 0,
        1 => 1,
        2 => 2,
        _ => unreachable!(),
    }
}

#[cfg(test)]
mod tests {
    use num_traits::ToPrimitive;

    use super::*;
    use crate::joint_uf_v1_4::{
        evaluate_with_physical_bounds, JointIntersampleLaw, JointUfCoordinateBounds, JointUfInput,
        JointUfPhysicalBounds,
    };

    fn evaluate_fixture(input: JointUfInput, bounds: &[(f64, f64)]) -> JointUfResult {
        evaluate_with_physical_bounds(
            input,
            JointUfPhysicalBounds::new(
                bounds
                    .iter()
                    .map(|(minimum, maximum)| {
                        JointUfCoordinateBounds::new(*minimum, *maximum).unwrap()
                    })
                    .collect(),
                BigRational::from_integer(BigInt::from(2)),
            )
            .unwrap(),
        )
        .unwrap()
    }

    fn evaluated_single_vertex() -> EvaluatedJointSourceOccurrence {
        let result = evaluate_fixture(
            JointUfInput {
                times: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::new(BigInt::from(1), BigInt::from(2)),
                    BigRational::from_integer(BigInt::from(1)),
                    BigRational::from_integer(BigInt::from(2)),
                ],
                fields: vec![vec![0.0], vec![0.3], vec![0.3], vec![0.0]],
                relevance: vec![0.1, 0.2, 0.3, 0.4],
                intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
            },
            &[(0.0, 0.3)],
        );
        EvaluatedJointSourceOccurrence {
            port_indices: vec![7],
            groups: vec![vec![0]],
            field: result,
        }
    }

    fn shared_fixture() -> SharedCompleteJointField {
        prepare_isolated_single_neuron_field_fixture(
            Arc::from([1_u8, 2, 3]),
            [9; 32],
            4,
            evaluated_single_vertex(),
        )
        .unwrap()
    }

    fn reconstruct(word: &[BalancedTrit]) -> BigInt {
        let mut result = BigInt::zero();
        let mut place = BigInt::one();
        for trit in word {
            result += trit.as_bigint() * &place;
            place *= 3_u8;
        }
        result
    }

    #[test]
    fn one_shared_body_exposes_one_local_component_without_copying_the_field() {
        let shared = shared_fixture();
        let perspective = bind_isolated_neuron_perspective(&shared, 0).unwrap();
        assert!(std::ptr::eq(perspective.shared(), &shared));
        assert_eq!(shared.port_indices(), &[7]);
        assert_eq!(shared.groups(), &[vec![0]]);
        assert_eq!(shared.source_authority(), [9; 32]);
        assert_eq!(shared.occurrence_index(), 4);
        assert_eq!(shared.source_body().as_ref(), &[1, 2, 3]);
        assert_eq!(shared.vertex_count(), 1);
        assert_eq!(perspective.coordinate_index(), 0);
        assert!(perspective.local_sev_len() >= 2);
        let local = perspective.local_sev(0).unwrap();
        let shared_frame = &shared.result().sev[perspective.gate().interval.first_sev];
        assert_eq!(local.source_index(), shared_frame.source_index);
        assert_eq!(local.field().to_bits(), shared_frame.field[0].to_bits());
        assert_eq!(
            local.delta_field().to_bits(),
            shared_frame.delta_field[0].to_bits()
        );
        assert_eq!(
            local.shared_delta_norm().to_bits(),
            shared_frame.delta_norm.to_bits()
        );
        assert_eq!(local.shared_sigma().to_bits(), shared_frame.sigma.to_bits());
        assert_eq!(local.shared_kappa().to_bits(), shared_frame.kappa.to_bits());
        assert_eq!(
            local.joint_relevance().to_bits(),
            shared_frame.relevance.to_bits()
        );
        assert_eq!(local.shared_negative_space(), shared_frame.negative_space);
    }

    #[test]
    fn all_seven_shared_dsf_facts_round_trip_exactly_through_mathloom() {
        let shared = shared_fixture();
        let perspective = bind_isolated_neuron_perspective(&shared, 0).unwrap();
        let values = perspective.dsf().ordered();
        let positions = values
            .iter()
            .map(|value| required_positions(&BigRational::from_float(*value).unwrap()))
            .max()
            .unwrap();
        assert_eq!(required_mathloom_positions(perspective).unwrap(), positions);
        let delivery =
            settle_shared_dsf_mathloom(perspective, MathLoomAnatomy::new(positions).unwrap())
                .unwrap();
        assert!(std::ptr::eq(delivery.perspective().shared(), &shared));
        assert_eq!(delivery.constraints().len(), 7);
        for ((constraint, family), value) in delivery
            .constraints()
            .iter()
            .zip(DSF_FACT_FAMILIES)
            .zip(values)
        {
            assert_eq!(constraint.family(), family);
            assert_eq!(constraint.binary64_bits(), value.to_bits());
            assert_eq!(
                reconstruct(constraint.word().numerator()),
                constraint.exact_value().numer().clone()
            );
            assert_eq!(
                reconstruct(constraint.word().denominator()),
                constraint.exact_value().denom().clone()
            );
            assert_eq!(
                constraint.exact_value().to_f64().unwrap().to_bits(),
                value.to_bits()
            );
        }
    }

    #[test]
    fn insufficient_mounted_mathloom_anatomy_refuses_without_reduction() {
        let shared = shared_fixture();
        let perspective = bind_isolated_neuron_perspective(&shared, 1).unwrap();
        let error =
            settle_shared_dsf_mathloom(perspective, MathLoomAnatomy::new(1).unwrap()).unwrap_err();
        assert!(matches!(
            error,
            JointNeuronBoundaryError::MathLoomAnatomyTooSmall { .. }
        ));
    }

    #[test]
    fn multivertex_or_group_shape_cannot_enter_the_isolated_proof() {
        let mut evaluated = evaluated_single_vertex();
        evaluated.port_indices.push(8);
        for frame in &mut evaluated.field.sev {
            frame.field.push(frame.field[0]);
            frame.delta_field.push(frame.delta_field[0]);
        }
        assert_eq!(
            prepare_isolated_single_neuron_field_fixture(Arc::from([1_u8]), [0; 32], 0, evaluated,),
            Err(JointNeuronBoundaryError::NotAnIsolatedSingleVertexOccurrence)
        );
    }

    #[test]
    fn three_neurons_borrow_distinct_local_coordinates_from_one_shared_field() {
        let result = evaluate_fixture(
            JointUfInput {
                times: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::new(BigInt::from(1), BigInt::from(2)),
                    BigRational::from_integer(BigInt::from(1)),
                    BigRational::from_integer(BigInt::from(2)),
                ],
                fields: vec![
                    vec![0.0, 10.0, -2.0],
                    vec![0.3, 11.0, -1.5],
                    vec![0.3, 12.0, -1.0],
                    vec![0.0, 13.0, -0.5],
                ],
                relevance: vec![0.1, 0.2, 0.3, 0.4],
                intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
            },
            &[(0.0, 0.3), (10.0, 13.0), (-2.0, -0.5)],
        );
        let shared = prepare_complete_joint_field_fixture(
            Arc::from([4_u8, 5, 6]),
            [7; 32],
            2,
            EvaluatedJointSourceOccurrence {
                port_indices: vec![11, 12, 13],
                groups: vec![vec![0, 1], vec![2]],
                field: result,
            },
        )
        .unwrap();
        assert_eq!(shared.vertex_count(), 3);
        let perspectives = [
            bind_neuron_perspective(&shared, 0, 0).unwrap(),
            bind_neuron_perspective(&shared, 1, 0).unwrap(),
            bind_neuron_perspective(&shared, 2, 0).unwrap(),
        ];
        let source_frame = perspectives[0].gate().interval.first_sev;
        assert!(perspectives
            .iter()
            .all(|perspective| std::ptr::eq(perspective.shared(), &shared)));
        for (coordinate, perspective) in perspectives.into_iter().enumerate() {
            assert_eq!(perspective.coordinate_index(), coordinate);
            assert_eq!(
                perspective.local_sev(0).unwrap().field().to_bits(),
                shared.result().sev[source_frame].field[coordinate].to_bits()
            );
            assert_eq!(
                perspective.local_sev(0).unwrap().delta_field().to_bits(),
                shared.result().sev[source_frame].delta_field[coordinate].to_bits()
            );
        }
        assert_eq!(
            bind_neuron_perspective(&shared, 3, 0).unwrap_err(),
            JointNeuronBoundaryError::NeuronCoordinateAbsent
        );
    }
}
