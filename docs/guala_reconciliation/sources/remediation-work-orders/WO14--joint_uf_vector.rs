//! Bounded native realization of the ratified joint vector UF lift.
//!
//! Authority: collaborative_todo.md active shared-producer contract. This
//! unmounted producer is not a neuron, controller, migration, or evidence of
//! feeding/speech. Existing scalar uf_core files are unchanged.
//!
//! Disclosed scalar-fixture differences: derived vector input without a log,
//! complete real context, strict Negative Space, >= structural boundaries,
//! actual-time integrals with shared endpoints, and unclamped adjusted U*.
//! L2 retains supplied-input mean/max definitions, not physical-bound or
//! predecessor-TVR substitutions. Binary64 reductions are explicitly ordered;
//! NumPy reduction bit-parity is not claimed. Values remain available as bits.
//!
//! Admission counts logical payload, not allocator overhead or process RSS.
//! A mounting process must separately enforce its actual memory envelope.

use std::sync::Arc;

// Frozen numerical constants from uf_core/config.py, not L5 gains.
const VARIANCE_WINDOW: usize = 20;
const SIGMA_MIN: f64 = 1e-6;
const DELTA_MIN: f64 = 1e-6;
const KAPPA_MIN: f64 = 1e-6;
const ALPHA: [f64; 3] = [1.0; 3];
const BETA: [f64; 3] = [1.0; 3];
const TAU_D: f64 = 0.20;
const LATTICES: [[f64; 3]; 3] = [[1.0; 3], [2.0; 3], [4.0; 3]];
const THETA_V: f64 = 1.0;
const THETA_R: f64 = 1.0;
const GAMMA: [f64; 3] = [1.0 / 3.0; 3];
const UNCERTAINTY_WEIGHTS: [f64; 3] = [1.0 / 3.0; 3];
const CHI_MIN: f64 = 0.25;
const CHI_MAX: f64 = 0.75;
const PSI_MIN: f64 = 0.25;
const PSI_MAX: f64 = 0.75;
const U_MAX: f64 = 0.75;
const RESONANCE_WEIGHTS: [f64; 5] = [1.0; 5];
const H_MAX: f64 = 0.20;
const EPSILON_D: f64 = 0.00073;
const ETA_H: f64 = 0.10;
const ETA_IAS: f64 = 0.10;
const BREATH_XI: f64 = 0.10;
const BREATH_CHI: f64 = 0.10;
const B_MIN: f64 = -1.0;
const B_MAX: f64 = 1.0;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum UfError {
    Invalid(&'static str), Capacity(&'static str), Arithmetic(&'static str),
}
type UfResult<T> = Result<T, UfError>;
fn finite(value: f64, reason: &'static str) -> UfResult<f64> {
    if value.is_finite() { Ok(value) } else { Err(UfError::Arithmetic(reason)) }
}
fn add(a: f64, b: f64) -> UfResult<f64> { finite(a + b, "binary64 addition") }
fn sub(a: f64, b: f64) -> UfResult<f64> { finite(a - b, "binary64 subtraction") }
fn mul(a: f64, b: f64) -> UfResult<f64> { finite(a * b, "binary64 multiplication") }
fn div(a: f64, b: f64) -> UfResult<f64> {
    if b == 0.0 { return Err(UfError::Arithmetic("zero divisor")); }
    finite(a / b, "binary64 division")
}
fn norm(values: &[f64]) -> UfResult<f64> {
    let mut sum = 0.0;
    for &value in values { sum = add(sum, mul(value, value)?)?; }
    finite(sum.sqrt(), "binary64 norm")
}
fn weighted3(values: [f64; 3], weights: [f64; 3]) -> UfResult<f64> {
    add(add(mul(weights[0], values[0])?, mul(weights[1], values[1])?)?,
        mul(weights[2], values[2])?)
}
fn gcd(mut a: u128, mut b: u128) -> u128 {
    while b != 0 { let remainder = a % b; a = b; b = remainder; }
    a
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct ExactTime { numerator: i64, denominator: u64 }
impl ExactTime {
    pub(crate) fn new(numerator: i64, denominator: u64) -> UfResult<Self> {
        if denominator == 0 || gcd(numerator.unsigned_abs() as u128, denominator as u128) != 1 {
            return Err(UfError::Invalid("source time is not a reduced finite rational"));
        }
        Ok(Self { numerator, denominator })
    }
    pub(crate) fn parts(self) -> (i64, u64) { (self.numerator, self.denominator) }
    fn products(self, other: Self) -> UfResult<(i128, i128)> {
        let left = (self.numerator as i128).checked_mul(other.denominator as i128)
            .ok_or(UfError::Arithmetic("source clock product"))?;
        let right = (other.numerator as i128).checked_mul(self.denominator as i128)
            .ok_or(UfError::Arithmetic("source clock product"))?;
        Ok((left, right))
    }
    fn after(self, earlier: Self) -> UfResult<bool> {
        let (left, right) = self.products(earlier)?;
        Ok(left > right)
    }
    fn since(self, earlier: Self) -> UfResult<ExactDuration> {
        let (left, right) = self.products(earlier)?;
        let difference = left.checked_sub(right).ok_or(UfError::Arithmetic("source clock subtraction"))?;
        if difference < 0 { return Err(UfError::Invalid("negative source duration")); }
        let denominator = (self.denominator as u128).checked_mul(earlier.denominator as u128)
            .ok_or(UfError::Arithmetic("source clock denominator"))?;
        let numerator = difference as u128;
        let divisor = gcd(numerator, denominator);
        Ok(ExactDuration { numerator: numerator / divisor, denominator: denominator / divisor })
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct ExactDuration { pub(crate) numerator: u128, pub(crate) denominator: u128 }
impl ExactDuration {
    fn binary64(self) -> UfResult<f64> {
        let value = div(self.numerator as f64, self.denominator as f64)?;
        if self.numerator != 0 && value <= 0.0 {
            return Err(UfError::Arithmetic("positive source duration lost in binary64"));
        }
        Ok(value)
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct ExactRelevance { numerator: u64, denominator: u64 }
impl ExactRelevance {
    pub(crate) fn new(numerator: u64, denominator: u64) -> UfResult<Self> {
        if denominator == 0 || numerator > denominator
            || gcd(numerator as u128, denominator as u128) != 1 {
            return Err(UfError::Invalid("joint relevance is not a reduced rational in [0,1]"));
        }
        Ok(Self { numerator, denominator })
    }
    pub(crate) fn parts(self) -> (u64, u64) { (self.numerator, self.denominator) }
    fn binary64(self) -> UfResult<f64> { div(self.numerator as f64, self.denominator as f64) }
}

/// A reference into the one immutable source body, not a semantic identifier.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct EvidenceRef { pub(crate) start: usize, pub(crate) end: usize }
impl EvidenceRef {
    fn validate(self, body_len: usize) -> UfResult<()> {
        if self.start >= self.end || self.end > body_len {
            return Err(UfError::Invalid("empty or out-of-body source evidence reference"));
        }
        Ok(())
    }
}
#[derive(Debug)]
pub(crate) struct CoordinateDeclaration {
    pub(crate) physical_quantity: EvidenceRef,
    pub(crate) physical_unit: EvidenceRef,
    pub(crate) physical_location: EvidenceRef,
    pub(crate) source_lineage: EvidenceRef,
    pub(crate) coordinate_law: EvidenceRef,
    pub(crate) physical_evidence: EvidenceRef,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct ContactSample {
    pub(crate) source_index: usize,
    pub(crate) edge_id: u64,
    pub(crate) from_vertex: usize,
    pub(crate) to_vertex: usize,
    pub(crate) state: EvidenceRef,
}
#[derive(Debug)]
pub(crate) struct SourceFrame {
    pub(crate) time: ExactTime,
    pub(crate) coordinates: Box<[f64]>,
    pub(crate) joint_relevance: ExactRelevance,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum IntersampleLaw {
    /// q and r are declared linear; merely declaring F linear is insufficient.
    SampledVolumeAndRelevancePiecewiseLinear { evidence: EvidenceRef },
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SourceCompletion {
    pub(crate) final_source_index: usize,
    pub(crate) evidence: EvidenceRef,
}
#[derive(Debug)]
pub(crate) struct JointSource {
    pub(crate) body: Arc<[u8]>,
    pub(crate) occurrence: EvidenceRef,
    pub(crate) clock_coordinate_law: EvidenceRef,
    pub(crate) clock_unit: EvidenceRef,
    pub(crate) joint_relevance_law: EvidenceRef,
    pub(crate) coordinates: Box<[CoordinateDeclaration]>,
    pub(crate) groups: Box<[Box<[usize]>]>,
    pub(crate) contacts: Box<[ContactSample]>,
    pub(crate) frames: Box<[SourceFrame]>,
    pub(crate) first_evaluation_index: usize,
    pub(crate) last_evaluation_index: usize,
    pub(crate) intersample_law: IntersampleLaw,
    pub(crate) completion: Option<SourceCompletion>,
}
/// Explicit payload/work admission. Actual process memory needs its own bound.
#[derive(Clone, Copy, Debug)]
pub(crate) struct AdmissionBounds {
    pub(crate) max_source_bytes: usize,
    pub(crate) max_frames: usize,
    pub(crate) max_vertices: usize,
    pub(crate) max_group_members: usize,
    pub(crate) max_contacts: usize,
    pub(crate) max_payload_bytes: usize,
}
fn checked_product(a: usize, b: usize) -> UfResult<usize> {
    a.checked_mul(b).ok_or(UfError::Capacity("payload size multiplication"))
}
fn checked_sum(a: usize, b: usize) -> UfResult<usize> {
    a.checked_add(b).ok_or(UfError::Capacity("payload size addition"))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct MissingSupport {
    pub(crate) predecessor: bool,
    pub(crate) variance_samples: usize,
    pub(crate) successor: bool,
}
impl MissingSupport {
    fn complete(self) -> bool { !self.predecessor && self.variance_samples == 0 && !self.successor }
}
#[derive(Debug)]
pub(crate) struct SevFrame {
    pub(crate) source_index: usize,
    pub(crate) support: MissingSupport,
    pub(crate) delta_field: Option<Box<[f64]>>,
    pub(crate) delta_norm: Option<f64>,
    pub(crate) window_mean_field: Option<Box<[f64]>>,
    pub(crate) variance_sum: Option<f64>,
    pub(crate) sigma: Option<f64>,
    pub(crate) curvature_vector: Option<Box<[f64]>>,
    pub(crate) kappa: Option<f64>,
    pub(crate) relevance: f64,
    pub(crate) negative_space: Option<bool>,
    pub(crate) deviation: Option<f64>,
    pub(crate) volume_integrand: Option<f64>,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct GateSupport { pub(crate) first: usize, pub(crate) last: usize }
#[derive(Debug)]
pub(crate) struct L1Field {
    pub(crate) support: GateSupport,
    pub(crate) duration: ExactDuration,
    pub(crate) tvr: [f64; 3],
    pub(crate) projections: [[i64; 3]; 3],
    pub(crate) divergence: usize,
    pub(crate) mean_vector: Box<[f64]>,
    pub(crate) predecessor_mean_difference: Option<Box<[f64]>>,
    pub(crate) drift: f64,
    pub(crate) negative_space_gate: bool,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Regime { Stable, Transitional, Volatile, Degenerate }
#[derive(Clone, Copy, Debug)]
pub(crate) struct L2Field {
    pub(crate) w: f64,
    pub(crate) cv: [f64; 3],
    pub(crate) cv_norm: f64,
    pub(crate) chi: f64,
    pub(crate) psi: f64,
    pub(crate) raw_s: f64,
    pub(crate) s: f64,
    pub(crate) raw_u: f64,
    pub(crate) u: f64,
    pub(crate) normalized_drift: f64,
    pub(crate) ias: bool,
    pub(crate) regime: Regime,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct L3Field {
    pub(crate) terms: [f64; 5],
    pub(crate) numerator: f64,
    pub(crate) normalization: f64,
    pub(crate) resonance: f64,
    pub(crate) hysteresis: bool,
    pub(crate) gate_open: bool,
    pub(crate) urf: f64,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct DsfField {
    pub(crate) d_k: f64,
    pub(crate) m_k: f64,
    pub(crate) r_rev_k: f64,
    pub(crate) u_star_k: f64,
    pub(crate) c_k: f64,
    pub(crate) p_k: f64,
    pub(crate) b_k: f64,
}
impl DsfField {
    pub(crate) fn ordered(self) -> [f64; 7] {
        [self.d_k, self.m_k, self.r_rev_k, self.u_star_k, self.c_k, self.p_k, self.b_k]
    }
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct L4Preparation {
    pub(crate) delta_urf: f64,
    pub(crate) raw_breath: f64,
    pub(crate) is_finite_evaluation_initialization: bool,
}
#[derive(Debug)]
pub(crate) struct CompletedGate {
    pub(crate) l1: L1Field,
    pub(crate) l2: L2Field,
    pub(crate) l3: L3Field,
    pub(crate) dsf: DsfField,
    pub(crate) l4_preparation: L4Preparation,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct L2Normalizers {
    pub(crate) tvr_mean: [f64; 3],
    pub(crate) maximum_density: f64,
    pub(crate) maximum_cv_norm: f64,
    pub(crate) maximum_gate_drift: f64,
    pub(crate) drift_divisor: f64,
}
#[derive(Debug)]
pub(crate) struct OpenGate {
    pub(crate) support: GateSupport,
    pub(crate) duration: ExactDuration,
    pub(crate) volume: f64,
    pub(crate) relevance: f64,
    pub(crate) mean_vector: Box<[f64]>,
    pub(crate) all_negative_space: bool,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum EpisodeAvailability {
    Complete, Open, Incomplete { first_unsupported: usize, missing: MissingSupport },
}
/// Separate global viability measurement, never an eighth local DSF coordinate.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum GlobalStability {
    UnavailableMissingMeasuredComponents,
    Available { value: f64, safe_mode: bool },
}

/// Canonical normalized measurements. The mounting kernel must supply the
/// measured horizon components; local B-P and a missing component are not
/// substitutes. No values are inferred from the seven local DSF coordinates.
#[derive(Clone, Copy, Debug)]
pub(crate) struct GlobalStabilityMeasurements {
    pub(crate) cohesion: f64,
    pub(crate) structural_entropy: f64,
    pub(crate) breathing_variance: f64,
    pub(crate) mean_uncertainty: f64,
    pub(crate) timebase_drift: f64,
}

impl GlobalStabilityMeasurements {
    /// Joe ratified +Coh, equal 0.20 weights and S_min=0.10, 2026-10-07.
    /// Ordered binary64 evaluation; no clipping, defaults or learned gains.
    fn evaluate(self) -> UfResult<GlobalStability> {
        let measurements = [self.cohesion, self.structural_entropy,
            self.breathing_variance, self.mean_uncertainty, self.timebase_drift];
        if measurements.iter().any(|value| !value.is_finite() || !(0.0..=1.0).contains(value)) {
            return Err(UfError::Invalid("global stability components must be measured and normalized to [0,1]"));
        }
        let mut value = mul(0.20, measurements[0])?;
        for &degradation in &measurements[1..] {
            value = add(value, mul(0.20, sub(1.0, degradation)?)?)?;
        }
        Ok(GlobalStability::Available { value, safe_mode: value < 0.10 })
    }
}

/// CSR references into source contacts; rows are never copied or synthesized.
#[derive(Debug)]
struct IncidentIndex { offsets: Box<[usize]>, rows: Box<[usize]> }
impl IncidentIndex {
    fn build(source: &JointSource) -> UfResult<Self> {
        let width = source.coordinates.len();
        let mut offsets = vec![0usize; checked_sum(width, 1)?];
        for contact in &source.contacts {
            offsets[contact.from_vertex + 1] = checked_sum(offsets[contact.from_vertex + 1], 1)?;
            offsets[contact.to_vertex + 1] = checked_sum(offsets[contact.to_vertex + 1], 1)?;
        }
        for index in 1..offsets.len() { offsets[index] = checked_sum(offsets[index], offsets[index - 1])?; }
        let mut cursors = offsets[..width].to_vec();
        let mut rows = vec![0usize; offsets[width]];
        for (row, contact) in source.contacts.iter().enumerate() {
            for vertex in [contact.from_vertex, contact.to_vertex] {
                rows[cursors[vertex]] = row;
                cursors[vertex] = checked_sum(cursors[vertex], 1)?;
            }
        }
        Ok(Self { offsets: offsets.into_boxed_slice(), rows: rows.into_boxed_slice() })
    }
    fn rows(&self, vertex: usize) -> &[usize] { &self.rows[self.offsets[vertex]..self.offsets[vertex + 1]] }
}

/// No mutation API. Later evaluations own distinct results and normalizers.
#[derive(Debug)]
pub(crate) struct SharedJointField {
    source: Arc<JointSource>,
    sev: Box<[SevFrame]>,
    gates: Box<[CompletedGate]>,
    normalizers: Option<L2Normalizers>,
    open_gate: Option<OpenGate>,
    availability: EpisodeAvailability,
    incident: IncidentIndex,
    admitted_payload_bound: usize,
}
impl SharedJointField {
    pub(crate) fn source(&self) -> &JointSource { &self.source }
    pub(crate) fn sev(&self) -> &[SevFrame] { &self.sev }
    pub(crate) fn gates(&self) -> &[CompletedGate] { &self.gates }
    pub(crate) fn normalizers(&self) -> Option<L2Normalizers> { self.normalizers }
    pub(crate) fn open_gate(&self) -> Option<&OpenGate> { self.open_gate.as_ref() }
    pub(crate) fn availability(&self) -> EpisodeAvailability { self.availability }
    pub(crate) fn admitted_payload_bound(&self) -> usize { self.admitted_payload_bound }
    pub(crate) fn global_stability(
        &self, measurements: Option<GlobalStabilityMeasurements>,
    ) -> UfResult<GlobalStability> {
        match measurements {
            Some(measured) => measured.evaluate(),
            None => Ok(GlobalStability::UnavailableMissingMeasuredComponents),
        }
    }
    pub(crate) fn perspective(&self, vertex: usize, gate: usize) -> UfResult<LocalPerspective<'_>> {
        if vertex >= self.source.coordinates.len() || gate >= self.gates.len() {
            return Err(UfError::Invalid("local perspective is outside shared result"));
        }
        Ok(LocalPerspective { shared: self, vertex, gate })
    }
}
#[derive(Clone, Copy)]
pub(crate) struct LocalPerspective<'a> { shared: &'a SharedJointField, vertex: usize, gate: usize }
impl<'a> LocalPerspective<'a> {
    pub(crate) fn shared(self) -> &'a SharedJointField { self.shared }
    pub(crate) fn vertex(self) -> usize { self.vertex }
    pub(crate) fn gate(self) -> &'a CompletedGate { &self.shared.gates[self.gate] }
    pub(crate) fn local_fields(self) -> impl Iterator<Item = (usize, f64, f64)> + 'a {
        let support = self.gate().l1.support;
        (support.first..=support.last).map(move |index| {
            let delta = self.shared.sev[index].delta_field.as_ref().expect("validated complete gate support");
            (index, self.shared.source.frames[index].coordinates[self.vertex], delta[self.vertex])
        })
    }
    /// All declared incident samples, including source context. Do not invent
    /// contact-state interpolation or discard prior contact evidence here.
    pub(crate) fn incident_contacts(self) -> impl Iterator<Item = &'a ContactSample> + 'a {
        self.shared.incident.rows(self.vertex).iter().map(move |&row| &self.shared.source.contacts[row])
    }
}

fn validate_source(source: &JointSource, bounds: AdmissionBounds) -> UfResult<usize> {
    use std::mem::size_of;
    let frames = source.frames.len();
    let width = source.coordinates.len();
    let contacts = source.contacts.len();
    if source.body.is_empty() || frames == 0 || width == 0 {
        return Err(UfError::Invalid("empty source body, frame sequence, or coordinate set"));
    }
    if source.body.len() > bounds.max_source_bytes || frames > bounds.max_frames
        || width > bounds.max_vertices || contacts > bounds.max_contacts {
        return Err(UfError::Capacity("source exceeds explicit admission"));
    }
    if source.groups.len() > width { return Err(UfError::Invalid("too many physical groups")); }
    let mut group_members = 0usize;
    for group in &source.groups { group_members = checked_sum(group_members, group.len())?; }
    if group_members != width || group_members > bounds.max_group_members {
        return Err(UfError::Invalid("groups do not partition admitted coordinates"));
    }
    if source.first_evaluation_index > source.last_evaluation_index || source.last_evaluation_index >= frames {
        return Err(UfError::Invalid("evaluation support range"));
    }
    // Logical payload admission, not allocator/Arc metadata or process RSS.
    // Multipliers count explicitly named simultaneous arrays.
    let vector_width = checked_sum(width, 2)?;
    let mut payload = source.body.len();
    for bytes in [
        size_of::<JointSource>(), size_of::<SharedJointField>(),
        checked_product(width, size_of::<CoordinateDeclaration>())?,
        checked_product(source.groups.len(), size_of::<Box<[usize]>>())?,
        checked_product(group_members, size_of::<usize>())?,
        checked_product(contacts, size_of::<ContactSample>())?,
        checked_product(frames, size_of::<SourceFrame>())?,
        checked_product(checked_product(frames, width)?, size_of::<f64>())?,
        checked_product(frames, size_of::<SevFrame>())?,
        // delta, rolling field mean, and curvature vector.
        checked_product(checked_product(checked_product(frames, width)?, 3)?, size_of::<f64>())?,
        checked_product(frames, size_of::<L1Field>())?,
        checked_product(frames, size_of::<CompletedGate>())?,
        // Gate mean and predecessor-mean difference.
        checked_product(checked_product(checked_product(frames, vector_width)?, 2)?, size_of::<f64>())?,
        checked_product(frames, size_of::<[f64; 3]>())?, // L2 CV temporary
        checked_product(checked_product(frames, 2)?, size_of::<f64>())?, // norm, density
        size_of::<GateAccumulator>(), size_of::<OpenGate>(),
        checked_product(checked_product(vector_width, 3)?, size_of::<f64>())?,
        checked_product(contacts, size_of::<(u64, usize, usize)>())?,
        checked_product(width, size_of::<bool>())?,
        checked_product(checked_sum(width, 1)?, size_of::<usize>())?, // CSR offsets
        checked_product(checked_product(contacts, 2)?, size_of::<usize>())?, // CSR rows
        checked_product(width, size_of::<usize>())?, // construction cursors
    ] { payload = checked_sum(payload, bytes)?; }
    if payload > bounds.max_payload_bytes {
        return Err(UfError::Capacity("derived logical payload exceeds explicit admission"));
    }
    for evidence in [source.occurrence, source.clock_coordinate_law, source.clock_unit, source.joint_relevance_law] {
        evidence.validate(source.body.len())?;
    }
    let IntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear { evidence } = source.intersample_law;
    evidence.validate(source.body.len())?;
    for coordinate in &source.coordinates {
        for evidence in [coordinate.physical_quantity, coordinate.physical_unit,
            coordinate.physical_location, coordinate.source_lineage,
            coordinate.coordinate_law, coordinate.physical_evidence] {
            evidence.validate(source.body.len())?;
        }
    }
    let mut seen = vec![false; width];
    let mut previous_group_first = None;
    for group in &source.groups {
        if group.is_empty() { return Err(UfError::Invalid("empty physical group")); }
        if previous_group_first.is_some_and(|previous| group[0] <= previous) {
            return Err(UfError::Invalid("physical groups are not canonically ordered"));
        }
        previous_group_first = Some(group[0]);
        let mut previous = None;
        for &vertex in group.iter() {
            if vertex >= width || seen[vertex] || previous.is_some_and(|p| vertex <= p) {
                return Err(UfError::Invalid("duplicate, unordered, or invalid physical group member"));
            }
            seen[vertex] = true;
            previous = Some(vertex);
        }
    }
    for (index, frame) in source.frames.iter().enumerate() {
        if frame.coordinates.len() != width || frame.coordinates.iter().any(|value| !value.is_finite()) {
            return Err(UfError::Invalid("source vector width or finiteness"));
        }
        ExactTime::new(frame.time.numerator, frame.time.denominator)?;
        ExactRelevance::new(frame.joint_relevance.numerator, frame.joint_relevance.denominator)?;
        if index > 0 && !frame.time.after(source.frames[index - 1].time)? {
            return Err(UfError::Invalid("source clocks are not strictly increasing"));
        }
    }
    let mut previous_contact = None;
    let mut endpoints = Vec::with_capacity(contacts);
    for contact in &source.contacts {
        let key = (contact.source_index, contact.edge_id);
        if contact.source_index >= frames || contact.from_vertex >= width || contact.to_vertex >= width
            || contact.from_vertex == contact.to_vertex || previous_contact.is_some_and(|previous| key <= previous) {
            return Err(UfError::Invalid("invalid or noncanonical sparse contact"));
        }
        contact.state.validate(source.body.len())?;
        endpoints.push((contact.edge_id, contact.from_vertex, contact.to_vertex));
        previous_contact = Some(key);
    }
    endpoints.sort_unstable(); // O(E log E), in-place; source order unchanged.
    for pair in endpoints.windows(2) {
        if pair[0].0 == pair[1].0 && pair[0] != pair[1] {
            return Err(UfError::Invalid("edge identity changed physical endpoints"));
        }
    }
    if let Some(completion) = source.completion {
        completion.evidence.validate(source.body.len())?;
        if completion.final_source_index != source.last_evaluation_index {
            return Err(UfError::Invalid("source completion does not name occurrence endpoint"));
        }
    }
    Ok(payload)
}

fn derive_sev(source: &JointSource) -> UfResult<Box<[SevFrame]>> {
    let width = source.coordinates.len();
    let count = source.frames.len();
    let mut result = Vec::with_capacity(count);
    for index in 0..count {
        let support = MissingSupport { predecessor: index == 0,
            variance_samples: VARIANCE_WINDOW.saturating_sub(index + 1), successor: index + 1 == count };
        let delta_field = if !support.predecessor {
            let mut values = Vec::with_capacity(width);
            for vertex in 0..width {
                values.push(sub(source.frames[index].coordinates[vertex], source.frames[index - 1].coordinates[vertex])?);
            }
            Some(values.into_boxed_slice())
        } else { None };
        let delta_norm = delta_field.as_ref().map(|values| norm(values)).transpose()?;
        let (window_mean_field, variance_sum, sigma) = if support.variance_samples == 0 {
            let first = index + 1 - VARIANCE_WINDOW;
            let mut means = vec![0.0; width];
            for frame in &source.frames[first..=index] {
                for (sum, &value) in means.iter_mut().zip(frame.coordinates.iter()) { *sum = add(*sum, value)?; }
            }
            for mean in &mut means { *mean = div(*mean, VARIANCE_WINDOW as f64)?; }
            let mut squared_sum = 0.0;
            for frame in &source.frames[first..=index] {
                for (&value, &mean) in frame.coordinates.iter().zip(means.iter()) {
                    let difference = sub(value, mean)?;
                    squared_sum = add(squared_sum, mul(difference, difference)?)?;
                }
            }
            (Some(means.into_boxed_slice()), Some(squared_sum), Some(div(squared_sum, VARIANCE_WINDOW as f64)?))
        } else { (None, None, None) };
        let curvature_vector = if !support.predecessor && !support.successor {
            let mut values = Vec::with_capacity(width);
            for vertex in 0..width {
                values.push(add(sub(source.frames[index + 1].coordinates[vertex],
                    mul(2.0, source.frames[index].coordinates[vertex])?)?, source.frames[index - 1].coordinates[vertex])?);
            }
            Some(values.into_boxed_slice())
        } else { None };
        let kappa = curvature_vector.as_ref().map(|values| norm(values)).transpose()?;
        let (negative_space, deviation, volume_integrand) = match (delta_norm, sigma, kappa) {
            (Some(delta), Some(variance), Some(curvature)) => (
                Some(variance < SIGMA_MIN && delta < DELTA_MIN && curvature < KAPPA_MIN),
                Some(weighted3([delta, variance, curvature], ALPHA)?),
                Some(weighted3([delta, variance, curvature], BETA)?)),
            _ => (None, None, None),
        };
        result.push(SevFrame { source_index: index, support, delta_field, delta_norm,
            window_mean_field, variance_sum, sigma, curvature_vector, kappa,
            relevance: source.frames[index].joint_relevance.binary64()?, negative_space,
            deviation, volume_integrand });
    }
    Ok(result.into_boxed_slice())
}

struct GateAccumulator {
    first: usize, last: usize, volume: f64, relevance: f64,
    mean_sums: Vec<f64>, count: usize, all_negative: bool,
}
impl GateAccumulator {
    fn new(frame: &SevFrame) -> UfResult<Self> {
        let delta = frame.delta_field.as_ref().ok_or(UfError::Invalid("incomplete gate start"))?;
        let mut sums = Vec::with_capacity(checked_sum(delta.len(), 2)?);
        sums.extend_from_slice(delta);
        sums.push(frame.sigma.ok_or(UfError::Invalid("missing gate-start variance"))?);
        sums.push(frame.kappa.ok_or(UfError::Invalid("missing gate-start curvature"))?);
        Ok(Self { first: frame.source_index, last: frame.source_index, volume: 0.0, relevance: 0.0,
            mean_sums: sums, count: 1,
            all_negative: frame.negative_space.ok_or(UfError::Invalid("missing gate-start Negative Space"))? })
    }
    fn extend(&mut self, source: &JointSource, sev: &[SevFrame], index: usize) -> UfResult<()> {
        if index != self.last + 1 { return Err(UfError::Invalid("nonadjacent gate support")); }
        let left = &sev[self.last];
        let right = &sev[index];
        if !right.support.complete() { return Err(UfError::Invalid("incomplete integral endpoint")); }
        let duration = source.frames[index].time.since(source.frames[self.last].time)?.binary64()?;
        if duration <= 0.0 { return Err(UfError::Invalid("nonpositive integral interval")); }
        let left_q = left.volume_integrand.ok_or(UfError::Invalid("missing left integrand"))?;
        let right_q = right.volume_integrand.ok_or(UfError::Invalid("missing right integrand"))?;
        self.volume = add(self.volume, mul(mul(add(left_q, right_q)?, 0.5)?, duration)?)?;
        self.relevance = add(self.relevance, mul(mul(add(left.relevance, right.relevance)?, 0.5)?, duration)?)?;
        let delta = right.delta_field.as_ref().ok_or(UfError::Invalid("missing gate delta"))?;
        let width = delta.len();
        for (sum, &value) in self.mean_sums[..width].iter_mut().zip(delta.iter()) { *sum = add(*sum, value)?; }
        self.mean_sums[width] = add(self.mean_sums[width], right.sigma.ok_or(UfError::Invalid("missing gate variance"))?)?;
        self.mean_sums[width + 1] = add(self.mean_sums[width + 1], right.kappa.ok_or(UfError::Invalid("missing gate curvature"))?)?;
        self.all_negative &= right.negative_space.ok_or(UfError::Invalid("missing gate Negative Space"))?;
        self.count = checked_sum(self.count, 1)?;
        self.last = index;
        Ok(())
    }
    fn into_open(self, source: &JointSource) -> UfResult<OpenGate> {
        let mut means = self.mean_sums;
        for mean in &mut means { *mean = div(*mean, self.count as f64)?; }
        Ok(OpenGate { support: GateSupport { first: self.first, last: self.last },
            duration: source.frames[self.last].time.since(source.frames[self.first].time)?,
            volume: self.volume, relevance: self.relevance,
            mean_vector: means.into_boxed_slice(), all_negative_space: self.all_negative })
    }
}
fn project(value: f64, spacing: f64) -> UfResult<i64> {
    let value = div(value, spacing)?.floor();
    // i64::MAX rounds up as f64; the upper bound is exclusive.
    if value < -9_223_372_036_854_775_808.0 || value >= 9_223_372_036_854_775_808.0 {
        return Err(UfError::Arithmetic("mosaic projection exceeds exact integer carrier"));
    }
    Ok(value as i64)
}
fn close_gate(accumulator: GateAccumulator, source: &JointSource, prior_mean: Option<&[f64]>) -> UfResult<L1Field> {
    let open = accumulator.into_open(source)?;
    if open.duration.numerator == 0 { return Err(UfError::Invalid("zero-duration gate cannot complete")); }
    let tvr = [open.duration.binary64()?, open.volume, open.relevance];
    let mut projections = [[0i64; 3]; 3];
    for lattice in 0..LATTICES.len() {
        for coordinate in 0..3 { projections[lattice][coordinate] = project(tvr[coordinate], LATTICES[lattice][coordinate])?; }
    }
    let mut divergence = 0usize;
    for index in 0..projections.len() {
        if !projections[..index].contains(&projections[index]) { divergence += 1; }
    }
    let predecessor_mean_difference = if let Some(prior) = prior_mean {
        let mut difference = Vec::with_capacity(prior.len());
        for (&current, &previous) in open.mean_vector.iter().zip(prior.iter()) { difference.push(sub(current, previous)?); }
        Some(difference.into_boxed_slice())
    } else { None };
    let drift = match &predecessor_mean_difference { Some(values) => norm(values)?, None => 0.0 };
    Ok(L1Field { support: open.support, duration: open.duration, tvr, projections,
        divergence, mean_vector: open.mean_vector, predecessor_mean_difference, drift,
        negative_space_gate: open.all_negative_space && open.volume < THETA_V && open.relevance < THETA_R })
}
fn derive_l1(source: &JointSource, sev: &[SevFrame]) -> UfResult<(Vec<L1Field>, Option<OpenGate>, EpisodeAvailability)> {
    let first = source.first_evaluation_index;
    let last = source.last_evaluation_index;
    if !sev[first].support.complete() {
        return Ok((Vec::new(), None, EpisodeAvailability::Incomplete { first_unsupported: first, missing: sev[first].support }));
    }
    let mut pending = GateAccumulator::new(&sev[first])?;
    let mut gates = Vec::with_capacity(last - first);
    let mut prior_mean: Option<Box<[f64]>> = None;
    for index in first + 1..=last {
        if !sev[index].support.complete() {
            return Ok((gates, Some(pending.into_open(source)?),
                EpisodeAvailability::Incomplete { first_unsupported: index, missing: sev[index].support }));
        }
        pending.extend(source, sev, index)?;
        if sev[index].deviation.ok_or(UfError::Invalid("missing gate deviation"))? >= TAU_D {
            let gate = close_gate(pending, source, prior_mean.as_deref())?;
            prior_mean = Some(gate.mean_vector.clone());
            gates.push(gate);
            pending = GateAccumulator::new(&sev[index])?;
        }
    }
    let availability = if source.completion.is_some() { EpisodeAvailability::Complete } else { EpisodeAvailability::Open };
    if source.completion.is_some() && pending.first != pending.last {
        gates.push(close_gate(pending, source, prior_mean.as_deref())?);
        Ok((gates, None, availability))
    } else {
        Ok((gates, Some(pending.into_open(source)?), availability))
    }
}

fn derive_l4(l1: &L1Field, l2: L2Field, l3: L3Field,
    predecessor: Option<&CompletedGate>, antepredecessor: Option<&CompletedGate>) -> UfResult<(DsfField, L4Preparation)> {
    let u_star = add(add(l2.u, mul(ETA_H, if l3.hysteresis { 1.0 } else { 0.0 })?)?,
        mul(ETA_IAS, if l2.ias { 1.0 } else { 0.0 })?)?;
    // Existing finite-evaluation preparation, never learned-state reset.
    let Some(previous) = predecessor else {
        return Ok((DsfField { d_k: 0.0, m_k: 0.0, r_rev_k: 0.0,
            u_star_k: u_star, c_k: l1.divergence as f64, p_k: 0.0, b_k: 0.0 },
            L4Preparation { delta_urf: 0.0, raw_breath: 0.0, is_finite_evaluation_initialization: true }));
    };
    let delta = sub(l3.urf, previous.l3.urf)?;
    let direction = if delta > EPSILON_D { 1.0 } else if delta < -EPSILON_D { -1.0 } else { 0.0 };
    let momentum = match antepredecessor {
        Some(earlier) => add(sub(l3.urf, mul(2.0, previous.l3.urf)?)?, earlier.l3.urf)?, None => 0.0,
    };
    let reversal = if mul(direction, previous.dsf.d_k)? < 0.0 { 1.0 } else { 0.0 };
    let pressure = sub(direction, previous.dsf.d_k)?.abs();
    let raw_breath = sub(add(previous.dsf.b_k, mul(mul(BREATH_XI, sub(1.0, u_star)?)?, delta)?)?, mul(BREATH_CHI, u_star)?)?;
    Ok((DsfField { d_k: direction, m_k: momentum, r_rev_k: reversal, u_star_k: u_star,
        c_k: l1.divergence as f64, p_k: pressure, b_k: raw_breath.clamp(B_MIN, B_MAX) },
        L4Preparation { delta_urf: delta, raw_breath, is_finite_evaluation_initialization: false }))
}
fn derive_l2_l4(l1: Vec<L1Field>) -> UfResult<(Box<[CompletedGate]>, Option<L2Normalizers>)> {
    if l1.is_empty() { return Ok((Vec::new().into_boxed_slice(), None)); }
    let count = l1.len();
    let mut mean = [0.0; 3];
    for gate in &l1 { for coordinate in 0..3 { mean[coordinate] = add(mean[coordinate], gate.tvr[coordinate])?; } }
    for value in &mut mean { *value = div(*value, count as f64)?; }
    let mut maximum_density = 0.0f64;
    let mut maximum_cv_norm = 0.0f64;
    let mut maximum_gate_drift = 0.0f64;
    let mut cvs = Vec::with_capacity(count);
    let mut cv_norms = Vec::with_capacity(count);
    let mut densities = Vec::with_capacity(count);
    for gate in &l1 {
        let cv = [sub(gate.tvr[0], mean[0])?, sub(gate.tvr[1], mean[1])?, sub(gate.tvr[2], mean[2])?];
        let cv_norm = norm(&cv)?;
        let density = div(gate.tvr[1], gate.tvr[0])?;
        maximum_density = maximum_density.max(density);
        maximum_cv_norm = maximum_cv_norm.max(cv_norm);
        maximum_gate_drift = maximum_gate_drift.max(gate.drift);
        cvs.push(cv); cv_norms.push(cv_norm); densities.push(density);
    }
    let drift_divisor = if maximum_gate_drift > 0.0 { maximum_gate_drift } else { 1.0 };
    let normalizers = L2Normalizers { tvr_mean: mean, maximum_density, maximum_cv_norm, maximum_gate_drift, drift_divisor };
    let mut result: Vec<CompletedGate> = Vec::with_capacity(count);
    for (index, gate) in l1.into_iter().enumerate() {
        let chi = densities[index];
        let cv = cvs[index];
        let cv_norm = cv_norms[index];
        let w = if maximum_density > 0.0 { div(chi, maximum_density)?.clamp(0.0, 1.0) } else { 0.0 };
        let psi = if maximum_cv_norm > 0.0 { div(cv_norm, maximum_cv_norm)?.clamp(0.0, 1.0) } else { 0.0 };
        let c_term = div(1.0, add(1.0, gate.divergence as f64)?)?;
        let raw_s = weighted3([w, psi, c_term], GAMMA)?;
        let s = raw_s.clamp(0.0, 1.0);
        let divergence_term = div(sub(gate.divergence as f64, 1.0)?, (LATTICES.len() - 1) as f64)?;
        let normalized_drift = div(gate.drift, drift_divisor)?;
        let raw_u = weighted3([divergence_term, normalized_drift, if gate.negative_space_gate { 1.0 } else { 0.0 }], UNCERTAINTY_WEIGHTS)?;
        let u = raw_u.clamp(0.0, 1.0);
        let ias = u > U_MAX;
        let regime = if psi > PSI_MAX { Regime::Degenerate }
            else if chi < CHI_MIN && psi < PSI_MIN { Regime::Stable }
            else if chi > CHI_MAX { Regime::Volatile } else { Regime::Transitional };
        let l2 = L2Field { w, cv, cv_norm, chi, psi, raw_s, s, raw_u, u, normalized_drift, ias, regime };
        let resonance_psi = if maximum_cv_norm > 0.0 { div(norm(&cv)?, maximum_cv_norm)? } else { 0.0 };
        let terms = [w, resonance_psi, s, c_term, sub(1.0, u)?];
        let mut numerator = mul(RESONANCE_WEIGHTS[0], terms[0])?;
        let mut normalization = RESONANCE_WEIGHTS[0];
        for term in 1..5 {
            numerator = add(numerator, mul(RESONANCE_WEIGHTS[term], terms[term])?)?;
            normalization = add(normalization, RESONANCE_WEIGHTS[term])?;
        }
        let resonance = div(numerator, normalization)?.clamp(0.0, 1.0);
        let hysteresis = match result.last() {
            Some(previous) => sub(resonance, previous.l3.resonance)?.abs() > H_MAX, None => false,
        };
        let gate_open = u <= U_MAX && !ias && !hysteresis;
        let urf = mul(if gate_open { 1.0 } else { 0.0 }, resonance)?;
        let l3 = L3Field { terms, numerator, normalization, resonance, hysteresis, gate_open, urf };
        let predecessor = result.last();
        let antepredecessor = result.len().checked_sub(2).map(|i| &result[i]);
        let (dsf, l4_preparation) = derive_l4(&gate, l2, l3, predecessor, antepredecessor)?;
        result.push(CompletedGate { l1: gate, l2, l3, dsf, l4_preparation });
    }
    Ok((result.into_boxed_slice(), Some(normalizers)))
}

pub(crate) fn evaluate_joint_source(source: Arc<JointSource>, bounds: AdmissionBounds) -> UfResult<Arc<SharedJointField>> {
    let admitted_payload_bound = validate_source(&source, bounds)?;
    let incident = IncidentIndex::build(&source)?;
    let sev = derive_sev(&source)?;
    let (l1, open_gate, availability) = derive_l1(&source, &sev)?;
    let (gates, normalizers) = derive_l2_l4(l1)?;
    Ok(Arc::new(SharedJointField { source, sev, gates, normalizers, open_gate,
        availability, incident, admitted_payload_bound }))
}

#[cfg(test)]
#[path = "joint_uf_vector_tests.rs"]
mod tests;

#[path = "joint_uf_source_codec.rs"]
pub(crate) mod source_codec;

#[path = "functional64_source.rs"]
pub(crate) mod physical_source;
