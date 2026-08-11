//! Pure bounded-continuous vector lift of the frozen UF v1.4 L0--L4 kernel.
//!
//! The cognitive adapter supplies one simultaneous, dimensionless vector field
//! and one joint relevance field over a strictly ordered source clock.  This
//! module performs one complete causal UF evaluation.  Its rolling operands
//! are transient calculation work, never persistent L0--L4, neuronal, or
//! cognitive state.  The kernel boundary remains one complete temporal input
//! and one complete joint-field output.
//!
//! Every L2 normalizer is derived before evaluation from explicit physical
//! coordinate bounds and the maximum admitted gate interval. No observed gate
//! or future sample becomes a normalizer. The only Guala lift is scalar-to-
//! vector L0 arithmetic; L1--L4 remain shared once for the complete field.

use std::collections::{BTreeSet, VecDeque};

use num_rational::BigRational;
use num_traits::{ToPrimitive, Zero};

const W: usize = 20;
const SIGMA_MIN: f64 = 1e-6;
const DELTA_MIN: f64 = 1e-6;
const KAPPA_MIN: f64 = 1e-6;
const TAU_D: f64 = 0.20;
const THETA_V: f64 = 1.0;
const THETA_R: f64 = 1.0;
const ONE_THIRD: f64 = 1.0 / 3.0;
const CHI_MIN: f64 = 0.25;
const CHI_MAX: f64 = 0.75;
const PSI_MIN: f64 = 0.25;
const PSI_MAX: f64 = 0.75;
const U_MAX: f64 = 0.75;
const H_MAX: f64 = 0.20;
const EPSILON_D: f64 = 0.00073;
const ETA_H: f64 = 0.10;
const ETA_IAS: f64 = 0.10;
const BREATH_XI: f64 = 0.10;
const BREATH_CHI: f64 = 0.10;
const B_MIN: f64 = -1.0;
const B_MAX: f64 = 1.0;
const I64_MIN_INCLUSIVE: f64 = -9_223_372_036_854_775_808.0;
const I64_MAX_EXCLUSIVE: f64 = 9_223_372_036_854_775_808.0;
const LATTICES: [[f64; 3]; 3] = [[1.0, 1.0, 1.0], [2.0, 2.0, 2.0], [4.0, 4.0, 4.0]];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum JointIntersampleLaw {
    /// Between adjacent source clocks, the sampled L1 volume integrand
    /// q=beta1*||Delta F||+beta2*sigma+beta3*kappa and r are each linear.
    /// This law is stronger and more precise than merely declaring F linear.
    SampledVolumeAndRelevancePiecewiseLinear,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct JointUfInput {
    pub(crate) times: Vec<BigRational>,
    pub(crate) fields: Vec<Vec<f64>>,
    pub(crate) relevance: Vec<f64>,
    pub(crate) intersample_law: JointIntersampleLaw,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct JointUfCoordinateBounds {
    minimum: f64,
    maximum: f64,
}

impl JointUfCoordinateBounds {
    pub(crate) fn new(minimum: f64, maximum: f64) -> Result<Self, JointUfError> {
        finite(minimum, "joint coordinate minimum is not finite")?;
        finite(maximum, "joint coordinate maximum is not finite")?;
        if maximum < minimum {
            return Err(JointUfError::Unavailable(
                "joint coordinate bounds are reversed",
            ));
        }
        Ok(Self { minimum, maximum })
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct JointUfPhysicalBounds {
    coordinates: Box<[JointUfCoordinateBounds]>,
    maximum_gate_interval: BigRational,
    maximum_density: f64,
    maximum_contrast_norm: f64,
    maximum_gate_drift: f64,
}

impl JointUfPhysicalBounds {
    pub(crate) fn new(
        coordinates: Vec<JointUfCoordinateBounds>,
        maximum_gate_interval: BigRational,
    ) -> Result<Self, JointUfError> {
        if coordinates.is_empty() {
            return Err(JointUfError::Unavailable(
                "joint physical bounds have no coordinate",
            ));
        }
        let maximum_interval = maximum_gate_interval
            .to_f64()
            .filter(|value| value.is_finite() && *value > 0.0)
            .ok_or(JointUfError::Unavailable(
                "maximum gate interval is not positive finite binary64",
            ))?;
        let mut squared_span_sum = 0.0;
        for coordinate in &coordinates {
            let span = finite(
                coordinate.maximum - coordinate.minimum,
                "joint coordinate span overflow",
            )?;
            squared_span_sum = add(
                squared_span_sum,
                multiply(span, span, "joint coordinate span square overflow")?,
                "joint coordinate span accumulation overflow",
            )?;
        }
        let maximum_delta = finite(squared_span_sum.sqrt(), "joint maximum delta is not finite")?;
        let maximum_sigma = finite(
            squared_span_sum / 4.0,
            "joint maximum dispersion is not finite",
        )?;
        let maximum_kappa = multiply(2.0, maximum_delta, "joint maximum curvature overflow")?;
        let maximum_density = add(
            add(
                maximum_delta,
                maximum_sigma,
                "joint maximum density overflow",
            )?,
            maximum_kappa,
            "joint maximum density overflow",
        )?;
        let maximum_volume = multiply(
            maximum_density,
            maximum_interval,
            "joint maximum volume overflow",
        )?;
        let maximum_contrast_norm = norm(&[maximum_interval, maximum_volume, maximum_interval])?;
        let maximum_gate_drift = norm(&[
            multiply(2.0, maximum_delta, "joint maximum drift overflow")?,
            maximum_sigma,
            maximum_kappa,
        ])?;
        Ok(Self {
            coordinates: coordinates.into_boxed_slice(),
            maximum_gate_interval,
            maximum_density,
            maximum_contrast_norm,
            maximum_gate_drift,
        })
    }

    pub(crate) fn width(&self) -> usize {
        self.coordinates.len()
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SevFrame {
    pub(crate) source_index: usize,
    pub(crate) field: Vec<f64>,
    pub(crate) delta_field: Vec<f64>,
    pub(crate) delta_norm: f64,
    pub(crate) sigma: f64,
    pub(crate) kappa: f64,
    pub(crate) relevance: f64,
    pub(crate) negative_space: bool,
    pub(crate) deviation: f64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct GateInterval {
    pub(crate) first_sev: usize,
    pub(crate) last_sev: usize,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct L1Field {
    pub(crate) tvr: [f64; 3],
    pub(crate) projections: Vec<[i64; 3]>,
    pub(crate) c: u64,
    pub(crate) drift: f64,
    pub(crate) negative_space_gate: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Regime {
    Stable,
    Transitional,
    Volatile,
    Degenerate,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct L2Field {
    pub(crate) w: f64,
    pub(crate) cv: [f64; 3],
    pub(crate) s: f64,
    pub(crate) regime: Regime,
    pub(crate) u: f64,
    pub(crate) ias: bool,
    pub(crate) chi: f64,
    pub(crate) psi: f64,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct L3Field {
    pub(crate) resonance: f64,
    pub(crate) hysteresis: bool,
    pub(crate) gate_open: bool,
    pub(crate) urf: f64,
}

#[derive(Clone, Copy, Debug, PartialEq)]
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
        [
            self.d_k,
            self.m_k,
            self.r_rev_k,
            self.u_star_k,
            self.c_k,
            self.p_k,
            self.b_k,
        ]
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct JointUfGate {
    pub(crate) interval: GateInterval,
    pub(crate) l1: L1Field,
    pub(crate) l2: L2Field,
    pub(crate) l3: L3Field,
    pub(crate) dsf: DsfField,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct JointUfResult {
    pub(crate) sev: Vec<SevFrame>,
    pub(crate) gates: Vec<JointUfGate>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum JointUfError {
    Unavailable(&'static str),
    NonFinite(&'static str),
}

fn finite(value: f64, label: &'static str) -> Result<f64, JointUfError> {
    if value.is_finite() {
        Ok(value)
    } else {
        Err(JointUfError::NonFinite(label))
    }
}

fn add(left: f64, right: f64, label: &'static str) -> Result<f64, JointUfError> {
    finite(left + right, label)
}

fn multiply(left: f64, right: f64, label: &'static str) -> Result<f64, JointUfError> {
    finite(left * right, label)
}

fn norm(values: &[f64]) -> Result<f64, JointUfError> {
    let mut squared = 0.0;
    for value in values {
        squared = add(
            squared,
            multiply(*value, *value, "vector square overflow")?,
            "vector norm overflow",
        )?;
    }
    finite(squared.sqrt(), "vector norm is not finite")
}

fn norm3(values: [f64; 3]) -> Result<f64, JointUfError> {
    norm(&values)
}

fn positive_duration(duration: &BigRational) -> Result<f64, JointUfError> {
    duration
        .to_f64()
        .filter(|value| value.is_finite() && *value > 0.0)
        .ok_or(JointUfError::Unavailable(
            "exact source interval is not positive finite binary64",
        ))
}

fn gate_intervals(sev: &[SevFrame]) -> Vec<GateInterval> {
    let mut result = Vec::new();
    let last = sev.len() - 1;
    let mut start = 0usize;
    for index in 1..=last {
        if sev[index].deviation >= TAU_D {
            result.push(GateInterval {
                first_sev: start,
                last_sev: index,
            });
            start = index;
        }
    }
    if start < last {
        result.push(GateInterval {
            first_sev: start,
            last_sev: last,
        });
    }
    result
}

fn projection(tvr: [f64; 3], lattice: [f64; 3]) -> Result<[i64; 3], JointUfError> {
    let mut result = [0i64; 3];
    for index in 0..3 {
        let projected = finite(tvr[index] / lattice[index], "lattice projection overflow")?.floor();
        if !(I64_MIN_INCLUSIVE..I64_MAX_EXCLUSIVE).contains(&projected) {
            return Err(JointUfError::Unavailable(
                "lattice projection exceeds exact integer range",
            ));
        }
        result[index] = projected as i64;
    }
    Ok(result)
}

#[derive(Clone, Debug, PartialEq)]
struct SourceSample {
    source_index: usize,
    interval_from_predecessor: BigRational,
    field: Vec<f64>,
    relevance: f64,
}

#[derive(Clone, Debug, PartialEq)]
struct ResolvedFrame {
    interval_from_predecessor: BigRational,
    sev: SevFrame,
}

#[derive(Clone, Debug, PartialEq)]
struct OpenGate {
    first_source_index: usize,
    last: ResolvedFrame,
    duration: BigRational,
    volume: f64,
    relevance: f64,
    mean_sum: Vec<f64>,
    sample_count: usize,
    all_negative: bool,
}

impl OpenGate {
    fn new(frame: ResolvedFrame, width: usize) -> Result<Self, JointUfError> {
        let mut mean_sum = Vec::with_capacity(width + 2);
        mean_sum.extend_from_slice(&frame.sev.delta_field);
        mean_sum.push(frame.sev.sigma);
        mean_sum.push(frame.sev.kappa);
        Ok(Self {
            first_source_index: frame.sev.source_index,
            all_negative: frame.sev.negative_space,
            last: frame,
            duration: BigRational::zero(),
            volume: 0.0,
            relevance: 0.0,
            mean_sum,
            sample_count: 1,
        })
    }

    fn extend(&mut self, frame: ResolvedFrame) -> Result<(), JointUfError> {
        let dt = positive_duration(&frame.interval_from_predecessor)?;
        self.duration += &frame.interval_from_predecessor;
        let left_volume = add(
            add(
                self.last.sev.delta_norm,
                self.last.sev.sigma,
                "gate volume overflow",
            )?,
            self.last.sev.kappa,
            "gate volume overflow",
        )?;
        let right_volume = add(
            add(
                frame.sev.delta_norm,
                frame.sev.sigma,
                "gate volume overflow",
            )?,
            frame.sev.kappa,
            "gate volume overflow",
        )?;
        self.volume = add(
            self.volume,
            multiply(
                multiply(
                    add(left_volume, right_volume, "gate volume overflow")?,
                    0.5,
                    "gate volume overflow",
                )?,
                dt,
                "gate volume integral overflow",
            )?,
            "gate volume integral overflow",
        )?;
        self.relevance = add(
            self.relevance,
            multiply(
                multiply(
                    add(
                        self.last.sev.relevance,
                        frame.sev.relevance,
                        "relevance overflow",
                    )?,
                    0.5,
                    "relevance overflow",
                )?,
                dt,
                "relevance integral overflow",
            )?,
            "relevance integral overflow",
        )?;
        for (sum, delta) in self.mean_sum[..frame.sev.delta_field.len()]
            .iter_mut()
            .zip(&frame.sev.delta_field)
        {
            *sum = add(*sum, *delta, "gate mean overflow")?;
        }
        let width = frame.sev.delta_field.len();
        self.mean_sum[width] = add(self.mean_sum[width], frame.sev.sigma, "gate mean overflow")?;
        self.mean_sum[width + 1] = add(
            self.mean_sum[width + 1],
            frame.sev.kappa,
            "gate mean overflow",
        )?;
        self.sample_count = self
            .sample_count
            .checked_add(1)
            .ok_or(JointUfError::Unavailable("gate sample count overflow"))?;
        self.all_negative &= frame.sev.negative_space;
        self.last = frame;
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ContinuousJointUfStep {
    pub(crate) sev: Option<SevFrame>,
    pub(crate) gate: Option<JointUfGate>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ContinuousJointUf {
    bounds: JointUfPhysicalBounds,
    intersample_law: JointIntersampleLaw,
    history: VecDeque<Vec<f64>>,
    pending: Option<SourceSample>,
    open_gate: Option<OpenGate>,
    prior_gate_mean: Option<Vec<f64>>,
    prior_tvr: Option<[f64; 3]>,
    prior_resonance: Option<f64>,
    prior_urf: Option<f64>,
    anteprior_urf: Option<f64>,
    prior_direction: f64,
    breath: f64,
    admitted_samples: usize,
    finalized_samples: usize,
    finalized_gates: usize,
    finished: bool,
}

impl ContinuousJointUf {
    pub(crate) fn new(bounds: JointUfPhysicalBounds, intersample_law: JointIntersampleLaw) -> Self {
        Self {
            bounds,
            intersample_law,
            history: VecDeque::with_capacity(W),
            pending: None,
            open_gate: None,
            prior_gate_mean: None,
            prior_tvr: None,
            prior_resonance: None,
            prior_urf: None,
            anteprior_urf: None,
            prior_direction: 0.0,
            breath: 0.0,
            admitted_samples: 0,
            finalized_samples: 0,
            finalized_gates: 0,
            finished: false,
        }
    }

    pub(crate) fn push_initial_sample(
        &mut self,
        field: Vec<f64>,
        relevance: f64,
    ) -> Result<ContinuousJointUfStep, JointUfError> {
        if self.admitted_samples != 0 {
            return Err(JointUfError::Unavailable(
                "continuous joint evaluation already has its initial sample",
            ));
        }
        self.push_sample(BigRational::zero(), field, relevance)
    }

    pub(crate) fn push_interval_sample(
        &mut self,
        interval_from_predecessor: BigRational,
        field: Vec<f64>,
        relevance: f64,
    ) -> Result<ContinuousJointUfStep, JointUfError> {
        if self.admitted_samples == 0 {
            return Err(JointUfError::Unavailable(
                "continuous joint evaluation lacks its initial sample",
            ));
        }
        positive_duration(&interval_from_predecessor)?;
        self.push_sample(interval_from_predecessor, field, relevance)
    }

    fn push_sample(
        &mut self,
        interval_from_predecessor: BigRational,
        field: Vec<f64>,
        relevance: f64,
    ) -> Result<ContinuousJointUfStep, JointUfError> {
        if self.finished {
            return Err(JointUfError::Unavailable(
                "continuous joint evaluation is already finished",
            ));
        }
        self.admit_sample(&field, relevance)?;
        if let Some(pending) = &self.pending {
            self.preflight_gate_interval(&pending.interval_from_predecessor)?;
        }
        let sample = SourceSample {
            source_index: self.admitted_samples,
            interval_from_predecessor,
            field,
            relevance,
        };
        self.admitted_samples = self
            .admitted_samples
            .checked_add(1)
            .ok_or(JointUfError::Unavailable("source sample count overflow"))?;
        if sample.source_index == 0 {
            let resolved = self.resolve_sample(sample, None)?;
            let gate = self.admit_resolved(resolved.clone())?;
            return Ok(ContinuousJointUfStep {
                sev: Some(resolved.sev),
                gate,
            });
        }
        let Some(pending) = self.pending.take() else {
            self.pending = Some(sample);
            return Ok(ContinuousJointUfStep {
                sev: None,
                gate: None,
            });
        };
        let resolved = self.resolve_sample(pending, Some(&sample.field))?;
        self.pending = Some(sample);
        let gate = self.admit_resolved(resolved.clone())?;
        Ok(ContinuousJointUfStep {
            sev: Some(resolved.sev),
            gate,
        })
    }

    pub(crate) fn finish(&mut self) -> Result<ContinuousJointUfStep, JointUfError> {
        if self.finished {
            return Err(JointUfError::Unavailable(
                "continuous joint evaluation is already finished",
            ));
        }
        if self.admitted_samples < 2 {
            return Err(JointUfError::Unavailable(
                "joint occurrence lacks a positive causal interval",
            ));
        }
        let pending = self.pending.as_ref().ok_or(JointUfError::Unavailable(
            "continuous joint evaluation lacks its terminal sample",
        ))?;
        self.preflight_gate_interval(&pending.interval_from_predecessor)?;
        let pending = self.pending.take().ok_or(JointUfError::Unavailable(
            "continuous joint evaluation lacks its terminal sample",
        ))?;
        let resolved = self.resolve_sample(pending, None)?;
        let boundary_gate = self.admit_resolved(resolved.clone())?;
        let terminal_gate = if boundary_gate.is_some() {
            boundary_gate
        } else {
            self.close_open_gate_if_positive_duration()?
        };
        self.open_gate = None;
        self.finished = true;
        Ok(ContinuousJointUfStep {
            sev: Some(resolved.sev),
            gate: terminal_gate,
        })
    }

    pub(crate) fn finalized_sample_count(&self) -> usize {
        self.finalized_samples
    }

    pub(crate) fn bounded_resident_bytes(&self) -> Result<usize, JointUfError> {
        let width = self.bounds.width();
        let vectors = W
            .checked_add(5)
            .and_then(|count| count.checked_mul(width))
            .and_then(|values| values.checked_mul(core::mem::size_of::<f64>()))
            .ok_or(JointUfError::Unavailable(
                "continuous UF resident size overflow",
            ))?;
        core::mem::size_of::<Self>()
            .checked_add(vectors)
            .and_then(|value| {
                value.checked_add(
                    width.checked_mul(core::mem::size_of::<JointUfCoordinateBounds>())?,
                )
            })
            .ok_or(JointUfError::Unavailable(
                "continuous UF resident size overflow",
            ))
    }

    fn admit_sample(&self, field: &[f64], relevance: f64) -> Result<(), JointUfError> {
        if field.len() != self.bounds.width() {
            return Err(JointUfError::Unavailable(
                "joint field width differs from declared physical bounds",
            ));
        }
        for (value, bounds) in field.iter().zip(self.bounds.coordinates.iter()) {
            finite(*value, "joint field input is not finite")?;
            if *value < bounds.minimum || *value > bounds.maximum {
                return Err(JointUfError::Unavailable(
                    "joint field input exceeds declared physical bounds",
                ));
            }
        }
        finite(relevance, "joint relevance is not finite")?;
        if !(0.0..=1.0).contains(&relevance) {
            return Err(JointUfError::Unavailable(
                "joint relevance is outside [0,1]",
            ));
        }
        match self.intersample_law {
            JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear => Ok(()),
        }
    }

    fn preflight_gate_interval(
        &self,
        interval_from_predecessor: &BigRational,
    ) -> Result<(), JointUfError> {
        if let Some(open) = &self.open_gate {
            if &open.duration + interval_from_predecessor > self.bounds.maximum_gate_interval {
                return Err(JointUfError::Unavailable(
                    "gate exceeds declared maximum causal interval",
                ));
            }
        }
        Ok(())
    }

    fn resolve_sample(
        &mut self,
        sample: SourceSample,
        lookahead: Option<&[f64]>,
    ) -> Result<ResolvedFrame, JointUfError> {
        let width = self.bounds.width();
        let mut delta_field = vec![0.0; width];
        if let Some(previous) = self.history.back() {
            for vertex in 0..width {
                delta_field[vertex] = finite(
                    sample.field[vertex] - previous[vertex],
                    "joint first difference overflow",
                )?;
            }
        }
        let delta_norm = norm(&delta_field)?;

        let retained = self.history.len().min(W - 1);
        let window_start = self.history.len() - retained;
        let sample_count = retained + 1;
        let mut mean = vec![0.0; width];
        for source in self.history.iter().skip(window_start) {
            for vertex in 0..width {
                mean[vertex] = add(mean[vertex], source[vertex], "joint mean overflow")?;
            }
        }
        for vertex in 0..width {
            mean[vertex] = add(mean[vertex], sample.field[vertex], "joint mean overflow")?;
            mean[vertex] = finite(
                mean[vertex] / sample_count as f64,
                "joint mean is not finite",
            )?;
        }
        let mut dispersion = 0.0;
        for source in self.history.iter().skip(window_start) {
            for vertex in 0..width {
                let deviation =
                    finite(source[vertex] - mean[vertex], "variance deviation overflow")?;
                dispersion = add(
                    dispersion,
                    multiply(deviation, deviation, "variance square overflow")?,
                    "variance accumulation overflow",
                )?;
            }
        }
        for vertex in 0..width {
            let deviation = finite(
                sample.field[vertex] - mean[vertex],
                "variance deviation overflow",
            )?;
            dispersion = add(
                dispersion,
                multiply(deviation, deviation, "variance square overflow")?,
                "variance accumulation overflow",
            )?;
        }
        let sigma = finite(dispersion / sample_count as f64, "variance is not finite")?;
        let kappa = if sample.source_index == 0 || lookahead.is_none() {
            0.0
        } else {
            let previous = self
                .history
                .back()
                .ok_or(JointUfError::Unavailable("curvature predecessor is absent"))?;
            let next = lookahead.expect("lookahead presence checked");
            let mut curvature = Vec::with_capacity(width);
            for vertex in 0..width {
                curvature.push(finite(
                    next[vertex] - 2.0 * sample.field[vertex] + previous[vertex],
                    "curvature overflow",
                )?);
            }
            norm(&curvature)?
        };
        let negative_space = sigma < SIGMA_MIN && delta_norm < DELTA_MIN && kappa < KAPPA_MIN;
        let deviation = add(
            add(delta_norm, sigma, "deviation overflow")?,
            kappa,
            "deviation overflow",
        )?;
        if self.history.len() == W {
            self.history.pop_front();
        }
        self.history.push_back(sample.field.clone());
        self.finalized_samples = self
            .finalized_samples
            .checked_add(1)
            .ok_or(JointUfError::Unavailable("finalized sample count overflow"))?;
        Ok(ResolvedFrame {
            interval_from_predecessor: sample.interval_from_predecessor,
            sev: SevFrame {
                source_index: sample.source_index,
                field: sample.field,
                delta_field,
                delta_norm,
                sigma,
                kappa,
                relevance: sample.relevance,
                negative_space,
                deviation,
            },
        })
    }

    fn admit_resolved(
        &mut self,
        frame: ResolvedFrame,
    ) -> Result<Option<JointUfGate>, JointUfError> {
        let Some(mut open) = self.open_gate.take() else {
            self.open_gate = Some(OpenGate::new(frame, self.bounds.width())?);
            return Ok(None);
        };
        open.extend(frame.clone())?;
        if frame.sev.deviation >= TAU_D {
            let gate = self.finalize_gate(open)?;
            self.open_gate = Some(OpenGate::new(frame, self.bounds.width())?);
            Ok(Some(gate))
        } else {
            self.open_gate = Some(open);
            Ok(None)
        }
    }

    fn close_open_gate_if_positive_duration(
        &mut self,
    ) -> Result<Option<JointUfGate>, JointUfError> {
        let Some(open) = self.open_gate.take() else {
            return Ok(None);
        };
        if open.first_source_index == open.last.sev.source_index {
            self.open_gate = Some(open);
            return Ok(None);
        }
        self.finalize_gate(open).map(Some)
    }

    fn finalize_gate(&mut self, open: OpenGate) -> Result<JointUfGate, JointUfError> {
        if open.duration > self.bounds.maximum_gate_interval {
            return Err(JointUfError::Unavailable(
                "gate exceeds declared maximum causal interval",
            ));
        }
        let duration = positive_duration(&open.duration)?;
        let tvr = [duration, open.volume, open.relevance];
        let projections = LATTICES
            .iter()
            .map(|lattice| projection(tvr, *lattice))
            .collect::<Result<Vec<_>, _>>()?;
        let c = projections.iter().copied().collect::<BTreeSet<_>>().len() as u64;
        let mut mean = open.mean_sum;
        for value in &mut mean {
            *value = finite(*value / open.sample_count as f64, "gate mean is not finite")?;
        }
        let drift = match &self.prior_gate_mean {
            None => 0.0,
            Some(prior) => norm(
                &mean
                    .iter()
                    .zip(prior)
                    .map(|(current, previous)| current - previous)
                    .collect::<Vec<_>>(),
            )?,
        };
        let l1 = L1Field {
            tvr,
            projections,
            c,
            drift,
            negative_space_gate: open.all_negative
                && open.volume < THETA_V
                && open.relevance < THETA_R,
        };
        let cv = match self.prior_tvr {
            None => [0.0; 3],
            Some(prior) => [tvr[0] - prior[0], tvr[1] - prior[1], tvr[2] - prior[2]],
        };
        let chi = finite(tvr[1] / tvr[0], "structural density is not finite")?;
        let w = normalized_by_declared_bound(
            chi,
            self.bounds.maximum_density,
            "structural density exceeds declared physical bound",
        )?;
        let psi = normalized_by_declared_bound(
            norm3(cv)?,
            self.bounds.maximum_contrast_norm,
            "gate contrast exceeds declared physical bound",
        )?;
        let normalized_drift = normalized_by_declared_bound(
            drift,
            self.bounds.maximum_gate_drift,
            "gate drift exceeds declared physical bound",
        )?;
        let c_term = 1.0 / (1.0 + c as f64);
        let s = finite(
            ONE_THIRD * w + ONE_THIRD * psi + ONE_THIRD * c_term,
            "structural score is not finite",
        )?
        .clamp(0.0, 1.0);
        let divergence = (c as f64 - 1.0) / (LATTICES.len() as f64 - 1.0);
        let u = finite(
            ONE_THIRD * divergence
                + ONE_THIRD * normalized_drift
                + ONE_THIRD * if l1.negative_space_gate { 1.0 } else { 0.0 },
            "uncertainty is not finite",
        )?
        .clamp(0.0, 1.0);
        let regime = if psi > PSI_MAX {
            Regime::Degenerate
        } else if chi < CHI_MIN && psi < PSI_MIN {
            Regime::Stable
        } else if chi > CHI_MAX {
            Regime::Volatile
        } else {
            Regime::Transitional
        };
        let l2 = L2Field {
            w,
            cv,
            s,
            regime,
            u,
            ias: u > U_MAX,
            chi,
            psi,
        };
        let resonance = finite(
            (l2.w + l2.psi + l2.s + c_term + (1.0 - l2.u)) / 5.0,
            "resonance is not finite",
        )?
        .clamp(0.0, 1.0);
        let hysteresis = self
            .prior_resonance
            .is_some_and(|prior| (resonance - prior).abs() > H_MAX);
        let gate_open = l2.u <= U_MAX && !l2.ias && !hysteresis;
        let urf = if gate_open { resonance } else { 0.0 };
        let l3 = L3Field {
            resonance,
            hysteresis,
            gate_open,
            urf,
        };
        let (delta, d, momentum, reversal, pressure) = match self.prior_urf {
            None => (0.0, 0.0, 0.0, 0.0, 0.0),
            Some(prior_urf) => {
                let delta = finite(urf - prior_urf, "URF difference overflow")?;
                let d = direction(delta);
                let momentum = match self.anteprior_urf {
                    None => 0.0,
                    Some(anteprior) => {
                        finite(urf - 2.0 * prior_urf + anteprior, "URF momentum overflow")?
                    }
                };
                (
                    delta,
                    d,
                    momentum,
                    if d * self.prior_direction < 0.0 {
                        1.0
                    } else {
                        0.0
                    },
                    (d - self.prior_direction).abs(),
                )
            }
        };
        let u_star = finite(
            l2.u + ETA_H * if l3.hysteresis { 1.0 } else { 0.0 }
                + ETA_IAS * if l2.ias { 1.0 } else { 0.0 },
            "adjusted uncertainty overflow",
        )?
        .clamp(0.0, 1.0);
        if self.prior_urf.is_some() {
            self.breath = finite(
                self.breath + BREATH_XI * (1.0 - u_star) * delta - BREATH_CHI * u_star,
                "breathing field overflow",
            )?
            .clamp(B_MIN, B_MAX);
        }
        let dsf = DsfField {
            d_k: d,
            m_k: momentum,
            r_rev_k: reversal,
            u_star_k: u_star,
            c_k: c as f64,
            p_k: pressure,
            b_k: self.breath,
        };
        let interval = GateInterval {
            first_sev: open.first_source_index,
            last_sev: open.last.sev.source_index,
        };
        self.prior_gate_mean = Some(mean);
        self.prior_tvr = Some(tvr);
        self.prior_resonance = Some(resonance);
        self.anteprior_urf = self.prior_urf;
        self.prior_urf = Some(urf);
        self.prior_direction = d;
        self.finalized_gates = self
            .finalized_gates
            .checked_add(1)
            .ok_or(JointUfError::Unavailable("finalized gate count overflow"))?;
        Ok(JointUfGate {
            interval,
            l1,
            l2,
            l3,
            dsf,
        })
    }
}

fn normalized_by_declared_bound(
    value: f64,
    bound: f64,
    overflow: &'static str,
) -> Result<f64, JointUfError> {
    if value < 0.0 || value > bound {
        return Err(JointUfError::Unavailable(overflow));
    }
    if bound > 0.0 {
        finite(value / bound, "declared-bound normalization is not finite")
    } else if value == 0.0 {
        Ok(0.0)
    } else {
        Err(JointUfError::Unavailable(overflow))
    }
}

fn direction(delta: f64) -> f64 {
    if delta > EPSILON_D {
        1.0
    } else if delta < -EPSILON_D {
        -1.0
    } else {
        0.0
    }
}

pub(crate) fn evaluate_with_physical_bounds(
    input: JointUfInput,
    bounds: JointUfPhysicalBounds,
) -> Result<JointUfResult, JointUfError> {
    if input.times.len() < 2 {
        return Err(JointUfError::Unavailable(
            "joint occurrence lacks a positive causal interval",
        ));
    }
    if input.fields.len() != input.times.len() || input.relevance.len() != input.times.len() {
        return Err(JointUfError::Unavailable(
            "joint occurrence fields do not cover the exact time domain",
        ));
    }
    let mut evaluator = ContinuousJointUf::new(bounds, input.intersample_law);
    let mut sev = Vec::with_capacity(input.times.len());
    let mut gates = Vec::new();
    for index in 0..input.times.len() {
        let step = if index == 0 {
            evaluator.push_initial_sample(input.fields[index].clone(), input.relevance[index])?
        } else {
            if input.times[index] <= input.times[index - 1] {
                return Err(JointUfError::Unavailable(
                    "joint source time does not strictly increase",
                ));
            }
            evaluator.push_interval_sample(
                &input.times[index] - &input.times[index - 1],
                input.fields[index].clone(),
                input.relevance[index],
            )?
        };
        if let Some(frame) = step.sev {
            sev.push(frame);
        }
        if let Some(gate) = step.gate {
            gates.push(gate);
        }
    }
    let terminal = evaluator.finish()?;
    if let Some(frame) = terminal.sev {
        sev.push(frame);
    }
    if let Some(gate) = terminal.gate {
        gates.push(gate);
    }
    if gates.is_empty() {
        return Err(JointUfError::Unavailable(
            "joint occurrence contains no positive-duration gate",
        ));
    }
    Ok(JointUfResult { sev, gates })
}

pub(crate) fn evaluate(input: JointUfInput) -> Result<JointUfResult, JointUfError> {
    let _ = input;
    Err(JointUfError::Unavailable(
        "explicit physical coordinate bounds and maximum gate interval are required",
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn constant(width: usize, times: Vec<BigRational>, relevance: f64) -> JointUfInput {
        JointUfInput {
            fields: vec![vec![0.0; width]; times.len()],
            relevance: vec![relevance; times.len()],
            times,
            intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
        }
    }

    fn integer_times(frames: usize) -> Vec<BigRational> {
        (0..frames)
            .map(|value| BigRational::from_integer(value.into()))
            .collect()
    }

    fn bounds(width: usize, maximum_gate_interval: i64) -> JointUfPhysicalBounds {
        JointUfPhysicalBounds::new(
            vec![JointUfCoordinateBounds::new(-1.0, 1.0).unwrap(); width],
            BigRational::from_integer(maximum_gate_interval.into()),
        )
        .unwrap()
    }

    fn bounded(input: JointUfInput) -> Result<JointUfResult, JointUfError> {
        let width = input.fields.first().map_or(0, Vec::len);
        evaluate_with_physical_bounds(input, bounds(width, 100))
    }

    fn millisecond_input(frames: usize) -> JointUfInput {
        let pattern = [[0.0, 0.0], [0.4, 0.0], [0.4, -0.3], [-0.2, 0.2]];
        JointUfInput {
            times: (0..frames)
                .map(|index| BigRational::new(index.into(), 1_000.into()))
                .collect(),
            fields: (0..frames)
                .map(|index| pattern[index % pattern.len()].to_vec())
                .collect(),
            relevance: (0..frames).map(|index| (index % 5) as f64 / 5.0).collect(),
            intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
        }
    }

    fn stream(input: &JointUfInput) -> (JointUfResult, ContinuousJointUf) {
        let mut evaluator =
            ContinuousJointUf::new(bounds(input.fields[0].len(), 1), input.intersample_law);
        let mut sev = Vec::new();
        let mut gates = Vec::new();
        for index in 0..input.times.len() {
            let step = if index == 0 {
                evaluator
                    .push_initial_sample(input.fields[index].clone(), input.relevance[index])
                    .unwrap()
            } else {
                evaluator
                    .push_interval_sample(
                        &input.times[index] - &input.times[index - 1],
                        input.fields[index].clone(),
                        input.relevance[index],
                    )
                    .unwrap()
            };
            if let Some(frame) = step.sev {
                sev.push(frame);
            }
            if let Some(gate) = step.gate {
                gates.push(gate);
            }
        }
        let terminal = evaluator.finish().unwrap();
        sev.push(terminal.sev.unwrap());
        if let Some(gate) = terminal.gate {
            gates.push(gate);
        }
        (JointUfResult { sev, gates }, evaluator)
    }

    #[test]
    fn constant_vector_matches_independent_closed_form_fixture() {
        let result = bounded(constant(3, integer_times(24), 0.5)).unwrap();
        assert_eq!(result.sev.len(), 24);
        assert_eq!(result.gates.len(), 1);
        let gate = &result.gates[0];
        assert_eq!(
            gate.interval,
            GateInterval {
                first_sev: 0,
                last_sev: 23,
            }
        );
        assert_eq!(gate.l1.tvr, [23.0, 0.0, 11.5]);
        assert_eq!(gate.l1.projections, [[23, 0, 11], [11, 0, 5], [5, 0, 2]]);
        assert_eq!(gate.l1.c, 3);
        assert!(!gate.l1.negative_space_gate);
        assert_eq!(gate.l2.w, 0.0);
        assert_eq!(gate.l2.cv, [0.0, 0.0, 0.0]);
        assert_eq!(gate.l2.s, 1.0 / 12.0);
        assert_eq!(gate.l2.u, 1.0 / 3.0);
        assert_eq!(gate.l2.regime, Regime::Stable);
        assert_eq!(gate.l3.resonance, 0.2);
        assert!(gate.l3.gate_open);
        assert_eq!(gate.l3.urf, 0.2);
        assert_eq!(
            gate.dsf.ordered(),
            [0.0, 0.0, 0.0, 1.0 / 3.0, 3.0, 0.0, 0.0]
        );
    }

    #[test]
    fn every_source_frame_is_retained_including_endpoints_and_partial_window() {
        let mut input = constant(1, integer_times(3), 0.0);
        input.fields = vec![vec![0.0], vec![1.0], vec![0.0]];
        let result = bounded(input).unwrap();
        assert_eq!(result.sev.len(), 3);
        assert_eq!(result.sev[0].source_index, 0);
        assert_eq!(result.sev[2].source_index, 2);
        assert_eq!(result.sev[0].delta_field, [0.0]);
        assert_eq!(result.sev[0].kappa, 0.0);
        assert_eq!(result.sev[1].kappa, 2.0);
        assert_eq!(result.sev[2].kappa, 0.0);
    }

    #[test]
    fn gate_boundary_uses_pdf_greater_than_or_equal_convention() {
        let frames = [0.0, TAU_D, TAU_D - f64::EPSILON, TAU_D + f64::EPSILON]
            .into_iter()
            .enumerate()
            .map(|(source_index, deviation)| SevFrame {
                source_index,
                field: vec![0.0],
                delta_field: vec![0.0],
                delta_norm: 0.0,
                sigma: 0.0,
                kappa: 0.0,
                relevance: 0.0,
                negative_space: true,
                deviation,
            })
            .collect::<Vec<_>>();
        assert_eq!(
            gate_intervals(&frames),
            vec![
                GateInterval {
                    first_sev: 0,
                    last_sev: 1,
                },
                GateInterval {
                    first_sev: 1,
                    last_sev: 3,
                },
            ]
        );
    }

    #[test]
    fn closed_evaluation_has_no_cross_occurrence_state() {
        let input = constant(2, integer_times(24), 0.5);
        let first = bounded(input.clone()).unwrap();
        let second = bounded(input).unwrap();
        assert_eq!(first, second);
        assert_eq!(first.gates[0].l1.drift, 0.0);
        assert_eq!(first.gates[0].dsf.d_k, 0.0);
        assert_eq!(first.gates[0].dsf.m_k, 0.0);
        assert_eq!(first.gates[0].dsf.b_k, 0.0);
    }

    #[test]
    fn irregular_ordered_clock_uses_exact_duration_and_declared_trapezoids() {
        let times = vec![
            BigRational::from_integer(0.into()),
            BigRational::new(1.into(), 4.into()),
            BigRational::new(3.into(), 4.into()),
            BigRational::from_integer(2.into()),
        ];
        let result = bounded(constant(2, times, 0.5)).unwrap();
        assert_eq!(result.gates.len(), 1);
        assert_eq!(result.gates[0].l1.tvr, [2.0, 0.0, 1.0]);
    }

    #[test]
    fn bounded_batch_and_sequential_millisecond_evaluation_are_bit_identical() {
        let input = millisecond_input(64);
        let batch = evaluate_with_physical_bounds(input.clone(), bounds(2, 1)).unwrap();
        let (sequential, evaluator) = stream(&input);
        assert_eq!(sequential, batch);
        assert_eq!(evaluator.finalized_sample_count(), input.times.len());
        assert_eq!(sequential.gates.len(), evaluator.finalized_gates);
    }

    #[test]
    fn exact_transient_calculation_is_invariant_to_window_split() {
        let input = millisecond_input(73);
        let mut uninterrupted = ContinuousJointUf::new(
            bounds(2, 1),
            JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
        );
        let mut uninterrupted_gates = Vec::new();
        for index in 0..29 {
            let step = if index == 0 {
                uninterrupted
                    .push_initial_sample(input.fields[index].clone(), input.relevance[index])
                    .unwrap()
            } else {
                uninterrupted
                    .push_interval_sample(
                        &input.times[index] - &input.times[index - 1],
                        input.fields[index].clone(),
                        input.relevance[index],
                    )
                    .unwrap()
            };
            if let Some(gate) = step.gate {
                uninterrupted_gates.push(gate);
            }
        }
        let mut restored = uninterrupted.clone();
        let mut restored_gates = uninterrupted_gates.clone();
        for index in 29..input.times.len() {
            let interval = &input.times[index] - &input.times[index - 1];
            let left = uninterrupted
                .push_interval_sample(
                    interval.clone(),
                    input.fields[index].clone(),
                    input.relevance[index],
                )
                .unwrap();
            let right = restored
                .push_interval_sample(
                    interval,
                    input.fields[index].clone(),
                    input.relevance[index],
                )
                .unwrap();
            assert_eq!(left, right);
            if let Some(gate) = left.gate {
                uninterrupted_gates.push(gate);
            }
            if let Some(gate) = right.gate {
                restored_gates.push(gate);
            }
        }
        let left = uninterrupted.finish().unwrap();
        let right = restored.finish().unwrap();
        assert_eq!(left, right);
        if let Some(gate) = left.gate {
            uninterrupted_gates.push(gate);
        }
        if let Some(gate) = right.gate {
            restored_gates.push(gate);
        }
        assert_eq!(uninterrupted, restored);
        assert_eq!(uninterrupted_gates, restored_gates);
    }

    #[test]
    fn resident_history_and_sample_work_remain_bounded_with_age() {
        let mut evaluator = ContinuousJointUf::new(
            bounds(2, 100),
            JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
        );
        evaluator.push_initial_sample(vec![0.0, 0.0], 0.0).unwrap();
        for _ in 1..=100 {
            evaluator
                .push_interval_sample(
                    BigRational::new(1.into(), 1_000.into()),
                    vec![0.0, 0.0],
                    0.0,
                )
                .unwrap();
        }
        let resident = evaluator.bounded_resident_bytes().unwrap();
        assert_eq!(evaluator.history.len(), W);
        for _ in 101..=10_000 {
            evaluator
                .push_interval_sample(
                    BigRational::new(1.into(), 1_000.into()),
                    vec![0.0, 0.0],
                    0.0,
                )
                .unwrap();
        }
        assert_eq!(evaluator.history.len(), W);
        assert_eq!(evaluator.bounded_resident_bytes().unwrap(), resident);
        assert_eq!(evaluator.finalized_sample_count(), 10_000);
        evaluator.finish().unwrap();
        assert_eq!(evaluator.finalized_sample_count(), 10_001);
    }

    #[test]
    fn future_samples_cannot_rewrite_a_finalized_gate_or_dsf() {
        let prefix = millisecond_input(3);
        let mut first = ContinuousJointUf::new(
            bounds(2, 1),
            JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
        );
        first
            .push_initial_sample(prefix.fields[0].clone(), prefix.relevance[0])
            .unwrap();
        first
            .push_interval_sample(
                BigRational::new(1.into(), 1_000.into()),
                prefix.fields[1].clone(),
                prefix.relevance[1],
            )
            .unwrap();
        let finalized = first
            .push_interval_sample(
                BigRational::new(1.into(), 1_000.into()),
                prefix.fields[2].clone(),
                prefix.relevance[2],
            )
            .unwrap()
            .gate
            .unwrap();
        let frozen = finalized.clone();
        for field in [vec![1.0, -1.0], vec![-1.0, 1.0], vec![0.8, 0.8]] {
            first
                .push_interval_sample(BigRational::new(1.into(), 1_000.into()), field, 0.9)
                .unwrap();
        }
        assert_eq!(finalized, frozen);
        assert_eq!(finalized.dsf.ordered(), frozen.dsf.ordered());
    }

    #[test]
    fn invalid_relevance_time_and_projection_overflow_refuse() {
        let mut invalid_relevance = constant(1, integer_times(2), 0.0);
        invalid_relevance.relevance[1] = 1.5;
        assert_eq!(
            bounded(invalid_relevance),
            Err(JointUfError::Unavailable(
                "joint relevance is outside [0,1]"
            ))
        );

        let mut invalid_time = constant(1, integer_times(2), 0.0);
        invalid_time.times[1] = invalid_time.times[0].clone();
        assert_eq!(
            bounded(invalid_time),
            Err(JointUfError::Unavailable(
                "joint source time does not strictly increase"
            ))
        );

        assert_eq!(
            projection([I64_MAX_EXCLUSIVE, 0.0, 0.0], [1.0, 1.0, 1.0]),
            Err(JointUfError::Unavailable(
                "lattice projection exceeds exact integer range"
            ))
        );
    }
}
