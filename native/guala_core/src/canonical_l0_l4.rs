//! Exact-operation-order native port of the current canonical Python
//! `closed_experience._run_kernel` path.
//!
//! This is not the retired `v4::compute_dsf` event-statistics function.  It
//! carries L0 SEV, L1 gate/mosaic state, L2 interpretation, L3 resonance, and
//! the complete seven-field L4 trajectory.  L2 intentionally rebuilds L1,
//! matching the current frozen Python call graph.  A differential-only PyO3
//! bridge returns every binary64 bit and the canonical trace bytes; production
//! activation remains prohibited until zero-tolerance fixtures agree.

use std::collections::BTreeSet;

use num_bigint::BigInt;
#[cfg(feature = "diagnostic-api")]
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::sha256::sha256;

const EPS: f64 = 1e-8;
const KERNEL_PROVIDER_ID: &str = "glew.closed_experience.ratified_native_l0_l4.v3";
#[cfg(any(test, feature = "diagnostic-api"))]
const SNAPSHOT_MAGIC: &[u8; 8] = b"GLTRC001";

#[derive(Clone, Debug)]
struct Config {
    sigma_min: f64,
    delta_min: f64,
    kappa_min: f64,
    variance_window: usize,
    alpha1: f64,
    alpha2: f64,
    alpha3: f64,
    tau_d: f64,
    gate_boundary_strict_gt: bool,
    beta1: f64,
    beta2: f64,
    beta3: f64,
    mosaic_lattices: Vec<[f64; 3]>,
    theta_v: f64,
    theta_r: f64,
    gamma1: f64,
    gamma2: f64,
    gamma3: f64,
    lambda_u1: f64,
    lambda_u2: f64,
    lambda_u3: f64,
    chi_min: f64,
    chi_max: f64,
    psi_min: f64,
    psi_max: f64,
    u_max: f64,
    lambda1: f64,
    lambda2: f64,
    lambda3: f64,
    lambda4: f64,
    lambda5: f64,
    h_max: f64,
    epsilon_d: f64,
    eta_h: f64,
    eta_ias: f64,
    breath_xi: f64,
    breath_chi: f64,
    b_min: f64,
    b_max: f64,
}

impl Config {
    fn current() -> Self {
        Self {
            sigma_min: 1e-6,
            delta_min: 1e-6,
            kappa_min: 1e-6,
            variance_window: 20,
            alpha1: 1.0,
            alpha2: 1.0,
            alpha3: 1.0,
            tau_d: 0.20,
            gate_boundary_strict_gt: true,
            beta1: 1.0,
            beta2: 1.0,
            beta3: 1.0,
            mosaic_lattices: vec![[1.0, 1.0, 1.0], [2.0, 2.0, 2.0], [4.0, 4.0, 4.0]],
            theta_v: 1.0,
            theta_r: 1.0,
            gamma1: 1.0 / 3.0,
            gamma2: 1.0 / 3.0,
            gamma3: 1.0 / 3.0,
            lambda_u1: 1.0 / 3.0,
            lambda_u2: 1.0 / 3.0,
            lambda_u3: 1.0 / 3.0,
            chi_min: 0.25,
            chi_max: 0.75,
            psi_min: 0.25,
            psi_max: 0.75,
            u_max: 0.75,
            lambda1: 1.0,
            lambda2: 1.0,
            lambda3: 1.0,
            lambda4: 1.0,
            lambda5: 1.0,
            h_max: 0.20,
            epsilon_d: 0.00073,
            eta_h: 0.10,
            eta_ias: 0.10,
            breath_xi: 0.10,
            breath_chi: 0.10,
            b_min: -1.0,
            b_max: 1.0,
        }
    }
}

#[derive(Clone, Debug)]
struct Sev {
    f_norm: f64,
    df: f64,
    sigma: f64,
    kappa: f64,
    relevance: f64,
    n: i64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Gate {
    start: usize,
    end: usize,
}

#[derive(Clone, Debug)]
struct L1 {
    gate: Gate,
    tvr: [f64; 3],
    projections: Vec<[i64; 3]>,
    c: i64,
    delta_g: f64,
    n_gate: i64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Regime {
    Degenerate,
    Stable,
    Volatile,
    Transitional,
}

impl Regime {
    fn text(self) -> &'static str {
        match self {
            Self::Degenerate => "DEGENERATE",
            Self::Stable => "STABLE",
            Self::Volatile => "VOLATILE",
            Self::Transitional => "TRANSITIONAL",
        }
    }

    #[cfg(any(test, feature = "diagnostic-api"))]
    fn code(self) -> u8 {
        match self {
            Self::Degenerate => 0,
            Self::Stable => 1,
            Self::Volatile => 2,
            Self::Transitional => 3,
        }
    }
}

#[cfg_attr(not(any(test, feature = "diagnostic-api")), allow(dead_code))]
#[derive(Clone, Debug)]
struct L2 {
    gate: Gate,
    w: f64,
    cv: [f64; 3],
    s: f64,
    u: f64,
    ias: i64,
    regime: Regime,
    c: i64,
    delta_g: f64,
    n_gate: i64,
    tvr: [f64; 3],
    chi: f64,
    psi: f64,
}

#[cfg_attr(not(any(test, feature = "diagnostic-api")), allow(dead_code))]
#[derive(Clone, Debug)]
struct L3 {
    gate: Gate,
    r: f64,
    urf: f64,
    g: i64,
    u: f64,
    ias: i64,
    hyst: i64,
    raw: f64,
}

#[derive(Clone, Debug)]
struct L4 {
    gate: Gate,
    fields: [f64; 7],
}

#[derive(Clone, Debug)]
struct Trace {
    sev: Vec<Sev>,
    l1: Vec<L1>,
    l2: Vec<L2>,
    l3: Vec<L3>,
    l4: Vec<L4>,
}

fn run_kernel(field: &[f64], relevance: &[f64], config: &Config) -> Result<Trace, String> {
    if field.is_empty() || field.len() != relevance.len() {
        return Err("canonical kernel requires equal nonempty field and relevance".into());
    }
    if field
        .iter()
        .any(|value| !value.is_finite() || *value <= 0.0)
    {
        return Err("canonical L0 field must be finite and positive".into());
    }
    if relevance
        .iter()
        .any(|value| !value.is_finite() || !(0.0..=1.0).contains(value))
    {
        return Err("canonical L0 relevance must be finite and in [0,1]".into());
    }

    let sev = compute_sev(field, relevance, config);
    let gates = segment_gates(&sev, config);
    let l1 = build_l1(&sev, &gates, config);
    // Deliberate frozen operation: interpret_gates rebuilds L1 instead of
    // consuming the already-produced records.
    let l2 = interpret_gates(&sev, &gates, config);
    let l3 = compute_resonance(&l2, config)?;
    let l4 = compute_l4(&l3, &l2, config);
    if gates.is_empty()
        || [l1.len(), l2.len(), l3.len(), l4.len()]
            .iter()
            .any(|length| *length != gates.len())
    {
        return Err("canonical L0-L4 gate trajectory is incomplete".into());
    }
    for index in 0..gates.len() {
        if gates[index] != l1[index].gate
            || gates[index] != l2[index].gate
            || gates[index] != l3[index].gate
            || gates[index] != l4[index].gate
        {
            return Err("canonical L0-L4 gate identities diverged".into());
        }
    }
    Ok(Trace {
        sev,
        l1,
        l2,
        l3,
        l4,
    })
}

fn compute_sev(field: &[f64], relevance: &[f64], config: &Config) -> Vec<Sev> {
    let length = field.len();
    let f_norm: Vec<f64> = field.iter().map(|value| (*value + EPS).ln()).collect();
    let mut df = vec![0.0; length];
    for index in 1..length {
        df[index] = f_norm[index] - f_norm[index - 1];
    }
    let mut sigma = vec![0.0; length];
    let window = config.variance_window.max(1);
    for index in 0..length {
        let start = (index + 1).saturating_sub(window);
        let segment = &f_norm[start..=index];
        sigma[index] = if segment.len() > 1 {
            numpy_var(segment)
        } else {
            0.0
        };
    }
    let mut kappa = vec![0.0; length];
    if length > 2 {
        for index in 1..length - 1 {
            kappa[index] = (f_norm[index + 1] - 2.0 * f_norm[index] + f_norm[index - 1]).abs();
        }
    }
    (0..length)
        .map(|index| {
            let n = if sigma[index] <= config.sigma_min
                && df[index].abs() <= config.delta_min
                && kappa[index] <= config.kappa_min
            {
                1
            } else {
                0
            };
            Sev {
                f_norm: f_norm[index],
                df: df[index],
                sigma: sigma[index],
                kappa: kappa[index],
                relevance: relevance[index],
                n,
            }
        })
        .collect()
}

fn deviation(sev: &[Sev], config: &Config) -> Vec<f64> {
    sev.iter()
        .map(|value| {
            config.alpha1 * value.df.abs()
                + config.alpha2 * value.sigma
                + config.alpha3 * value.kappa
        })
        .collect()
}

fn segment_gates(sev: &[Sev], config: &Config) -> Vec<Gate> {
    if sev.is_empty() {
        return Vec::new();
    }
    let deviation = deviation(sev, config);
    let mut gates = Vec::new();
    let mut current_start = 0usize;
    for (index, value) in deviation.iter().enumerate().skip(1) {
        let boundary = if config.gate_boundary_strict_gt {
            *value > config.tau_d
        } else {
            *value >= config.tau_d
        };
        if boundary {
            gates.push(Gate {
                start: current_start,
                end: index - 1,
            });
            current_start = index;
        }
    }
    gates.push(Gate {
        start: current_start,
        end: sev.len() - 1,
    });
    gates
}

fn build_l1(sev: &[Sev], gates: &[Gate], config: &Config) -> Vec<L1> {
    if sev.is_empty() || gates.is_empty() {
        return Vec::new();
    }
    let tvr: Vec<[f64; 3]> = gates
        .iter()
        .map(|gate| {
            let mut volume_terms = Vec::with_capacity(gate.end - gate.start + 1);
            let mut relevance_terms = Vec::with_capacity(volume_terms.capacity());
            for value in &sev[gate.start..=gate.end] {
                volume_terms.push(
                    config.beta1 * value.df.abs()
                        + config.beta2 * value.sigma
                        + config.beta3 * value.kappa,
                );
                relevance_terms.push(value.relevance);
            }
            [
                gate.end.saturating_sub(gate.start) as f64,
                numpy_sum(&volume_terms),
                numpy_sum(&relevance_terms),
            ]
        })
        .collect();
    let projections: Vec<Vec<[i64; 3]>> = tvr
        .iter()
        .map(|value| {
            config
                .mosaic_lattices
                .iter()
                .map(|step| {
                    [
                        (value[0] / step[0]).floor() as i64,
                        (value[1] / step[1]).floor() as i64,
                        (value[2] / step[2]).floor() as i64,
                    ]
                })
                .collect()
        })
        .collect();
    let divergence: Vec<i64> = projections
        .iter()
        .map(|value| value.iter().copied().collect::<BTreeSet<_>>().len() as i64)
        .collect();
    let means: Vec<[f64; 3]> = gates
        .iter()
        .map(|gate| {
            let segment = &sev[gate.start..=gate.end];
            [
                numpy_sum(&segment.iter().map(|value| value.df).collect::<Vec<_>>())
                    / segment.len() as f64,
                numpy_sum(&segment.iter().map(|value| value.sigma).collect::<Vec<_>>())
                    / segment.len() as f64,
                numpy_sum(&segment.iter().map(|value| value.kappa).collect::<Vec<_>>())
                    / segment.len() as f64,
            ]
        })
        .collect();
    let mut drift = vec![0.0; gates.len()];
    for index in 1..gates.len() {
        drift[index] = norm3([
            means[index][0] - means[index - 1][0],
            means[index][1] - means[index - 1][1],
            means[index][2] - means[index - 1][2],
        ]);
    }
    gates
        .iter()
        .enumerate()
        .map(|(index, gate)| {
            let all_negative = sev[gate.start..=gate.end].iter().all(|value| value.n == 1);
            let n_gate =
                if all_negative && tvr[index][1] < config.theta_v && tvr[index][2] < config.theta_r
                {
                    1
                } else {
                    0
                };
            L1 {
                gate: *gate,
                tvr: tvr[index],
                projections: projections[index].clone(),
                c: divergence[index],
                delta_g: drift[index],
                n_gate,
            }
        })
        .collect()
}

fn interpret_gates(sev: &[Sev], gates: &[Gate], config: &Config) -> Vec<L2> {
    let l1 = build_l1(sev, gates, config);
    if l1.is_empty() {
        return Vec::new();
    }
    let mut mean = [0.0; 3];
    for dimension in 0..3 {
        mean[dimension] = l1
            .iter()
            .map(|value| value.tvr[dimension])
            .fold(0.0, |sum, value| sum + value)
            / l1.len() as f64;
    }
    let cv: Vec<[f64; 3]> = l1
        .iter()
        .map(|value| {
            [
                value.tvr[0] - mean[0],
                value.tvr[1] - mean[1],
                value.tvr[2] - mean[2],
            ]
        })
        .collect();
    let chi: Vec<f64> = l1
        .iter()
        .map(|value| value.tvr[1] / value.tvr[0].max(1e-12))
        .collect();
    let max_chi = chi
        .iter()
        .copied()
        .fold(f64::NEG_INFINITY, |left, right| left.max(right));
    let w: Vec<f64> = if max_chi <= 0.0 {
        vec![0.0; chi.len()]
    } else {
        chi.iter()
            .map(|value| (*value / max_chi).clamp(0.0, 1.0))
            .collect()
    };
    let cv_norm: Vec<f64> = cv.iter().map(|value| norm3(*value)).collect();
    let max_norm = cv_norm
        .iter()
        .copied()
        .fold(f64::NEG_INFINITY, |left, right| left.max(right));
    let psi: Vec<f64> = if max_norm <= 0.0 {
        vec![0.0; cv.len()]
    } else {
        cv_norm
            .iter()
            .map(|value| (*value / max_norm).clamp(0.0, 1.0))
            .collect()
    };
    let s: Vec<f64> = (0..l1.len())
        .map(|index| {
            let c_term = 1.0 / (1.0 + l1[index].c as f64);
            (config.gamma1 * w[index] + config.gamma2 * psi[index] + config.gamma3 * c_term)
                .clamp(0.0, 1.0)
        })
        .collect();
    let lattice_count = config.mosaic_lattices.len();
    let denominator_l = (lattice_count as i64 - 1).max(1) as f64;
    let mut delta_max = l1
        .iter()
        .map(|value| value.delta_g)
        .fold(0.0f64, |left, right| left.max(right));
    if delta_max <= 0.0 {
        delta_max = 1.0;
    }
    let u: Vec<f64> = l1
        .iter()
        .map(|value| {
            let c_term = if lattice_count <= 1 {
                0.0
            } else {
                (value.c as f64 - 1.0) / denominator_l
            };
            let drift_term = value.delta_g / delta_max;
            let negative_term = value.n_gate as f64;
            (config.lambda_u1 * c_term
                + config.lambda_u2 * drift_term
                + config.lambda_u3 * negative_term)
                .clamp(0.0, 1.0)
        })
        .collect();
    (0..l1.len())
        .map(|index| {
            let ias = if u[index] > config.u_max { 1 } else { 0 };
            let regime = if psi[index] > config.psi_max {
                Regime::Degenerate
            } else if chi[index] < config.chi_min && psi[index] < config.psi_min {
                Regime::Stable
            } else if chi[index] > config.chi_max {
                Regime::Volatile
            } else {
                Regime::Transitional
            };
            L2 {
                gate: l1[index].gate,
                w: w[index],
                cv: cv[index],
                s: s[index],
                u: u[index],
                ias,
                regime,
                c: l1[index].c,
                delta_g: l1[index].delta_g,
                n_gate: l1[index].n_gate,
                tvr: l1[index].tvr,
                chi: chi[index],
                psi: psi[index],
            }
        })
        .collect()
}

fn compute_resonance(l2: &[L2], config: &Config) -> Result<Vec<L3>, String> {
    if l2.is_empty() {
        return Ok(Vec::new());
    }
    let cv_norm: Vec<f64> = l2.iter().map(|value| norm3(value.cv)).collect();
    let max_norm = cv_norm
        .iter()
        .copied()
        .fold(f64::NEG_INFINITY, |left, right| left.max(right));
    let raw: Vec<f64> = l2
        .iter()
        .enumerate()
        .map(|(index, value)| {
            let psi = if max_norm > 0.0 {
                cv_norm[index] / max_norm
            } else {
                0.0
            };
            let c_term = 1.0 / (1.0 + value.c as f64);
            config.lambda1 * value.w
                + config.lambda2 * psi
                + config.lambda3 * value.s
                + config.lambda4 * c_term
                + config.lambda5 * (1.0 - value.u)
        })
        .collect();
    let z = config.lambda1 + config.lambda2 + config.lambda3 + config.lambda4 + config.lambda5;
    if z <= 0.0 {
        return Err("resonance normalization constant is not positive".into());
    }
    let r: Vec<f64> = raw
        .iter()
        .map(|value| (*value / z).clamp(0.0, 1.0))
        .collect();
    let mut hysteresis = vec![0i64; r.len()];
    for index in 1..r.len() {
        hysteresis[index] = if (r[index] - r[index - 1]).abs() > config.h_max {
            1
        } else {
            0
        };
    }
    Ok((0..l2.len())
        .map(|index| {
            let g = if l2[index].u <= config.u_max && l2[index].ias == 0 && hysteresis[index] == 0 {
                1
            } else {
                0
            };
            L3 {
                gate: l2[index].gate,
                r: r[index],
                urf: g as f64 * r[index],
                g,
                u: l2[index].u,
                ias: l2[index].ias,
                hyst: hysteresis[index],
                raw: raw[index],
            }
        })
        .collect())
}

fn compute_l4(l3: &[L3], l2: &[L2], config: &Config) -> Vec<L4> {
    if l3.is_empty() {
        return Vec::new();
    }
    let length = l3.len();
    let mut d: Vec<f64> = vec![0.0; length];
    let mut m: Vec<f64> = vec![0.0; length];
    let mut reversal: Vec<f64> = vec![0.0; length];
    let mut u_star: Vec<f64> = vec![0.0; length];
    let mut pressure: Vec<f64> = vec![0.0; length];
    let mut breathing: Vec<f64> = vec![0.0; length];
    breathing[0] = 0.0f64.clamp(config.b_min, config.b_max);
    u_star[0] = (l3[0].u + config.eta_h * l3[0].hyst as f64 + config.eta_ias * l3[0].ias as f64)
        .clamp(0.0, 1.0);
    pressure[0] = 0.0;
    for index in 1..length {
        let delta_r = l3[index].urf - l3[index - 1].urf;
        d[index] = if delta_r > config.epsilon_d {
            1.0
        } else if delta_r < -config.epsilon_d {
            -1.0
        } else {
            0.0
        };
        m[index] = if index >= 2 {
            l3[index].urf - 2.0 * l3[index - 1].urf + l3[index - 2].urf
        } else {
            0.0
        };
        reversal[index] = if d[index] * d[index - 1] < 0.0 {
            1.0
        } else {
            0.0
        };
        u_star[index] = (l3[index].u
            + config.eta_h * l3[index].hyst as f64
            + config.eta_ias * l3[index].ias as f64)
            .clamp(0.0, 1.0);
        pressure[index] = (d[index] - d[index - 1]).abs();
        let next_breath = breathing[index - 1] + config.breath_xi * (1.0 - u_star[index]) * delta_r
            - config.breath_chi * u_star[index];
        breathing[index] = next_breath.clamp(config.b_min, config.b_max);
    }
    (0..length)
        .map(|index| L4 {
            gate: l3[index].gate,
            fields: [
                d[index],
                m[index],
                reversal[index],
                u_star[index],
                l2[index].c as f64,
                pressure[index],
                breathing[index],
            ],
        })
        .collect()
}

// Mirrors NumPy's pairwise reduction for one contiguous float64 axis when the
// axis length is below the 128-element pairwise block size.
fn numpy_sum(values: &[f64]) -> f64 {
    if values.len() < 8 {
        return values.iter().copied().fold(0.0, |sum, value| sum + value);
    }
    if values.len() <= 128 {
        let mut partial = [
            values[0], values[1], values[2], values[3], values[4], values[5], values[6], values[7],
        ];
        let mut index = 8usize;
        while index + 8 <= values.len() {
            for lane in 0..8 {
                partial[lane] += values[index + lane];
            }
            index += 8;
        }
        let mut sum = ((partial[0] + partial[1]) + (partial[2] + partial[3]))
            + ((partial[4] + partial[5]) + (partial[6] + partial[7]));
        while index < values.len() {
            sum += values[index];
            index += 1;
        }
        return sum;
    }
    let midpoint = (values.len() / 2) - ((values.len() / 2) % 8);
    numpy_sum(&values[..midpoint]) + numpy_sum(&values[midpoint..])
}

fn numpy_var(values: &[f64]) -> f64 {
    let mean = numpy_sum(values) / values.len() as f64;
    let squared: Vec<f64> = values
        .iter()
        .map(|value| {
            let difference = *value - mean;
            difference * difference
        })
        .collect();
    numpy_sum(&squared) / values.len() as f64
}

fn norm3(value: [f64; 3]) -> f64 {
    (value[0] * value[0] + value[1] * value[1] + value[2] * value[2]).sqrt()
}

#[cfg(any(test, feature = "diagnostic-api"))]
fn snapshot(trace: &Trace) -> Result<Vec<u8>, String> {
    let mut output = Vec::new();
    output.extend_from_slice(SNAPSHOT_MAGIC);
    output.extend_from_slice(&1u16.to_le_bytes());
    put_count(&mut output, trace.sev.len())?;
    put_count(&mut output, trace.l1.len())?;
    for value in &trace.sev {
        for field in [
            value.f_norm,
            value.df,
            value.sigma,
            value.kappa,
            value.relevance,
        ] {
            output.extend_from_slice(&field.to_bits().to_le_bytes());
        }
        output.extend_from_slice(&value.n.to_le_bytes());
    }
    for value in &trace.l1 {
        put_gate(&mut output, value.gate)?;
        for field in value.tvr {
            output.extend_from_slice(&field.to_bits().to_le_bytes());
        }
        put_count(&mut output, value.projections.len())?;
        for projection in &value.projections {
            for coordinate in projection {
                output.extend_from_slice(&coordinate.to_le_bytes());
            }
        }
        output.extend_from_slice(&value.c.to_le_bytes());
        output.extend_from_slice(&value.delta_g.to_bits().to_le_bytes());
        output.extend_from_slice(&value.n_gate.to_le_bytes());
    }
    for value in &trace.l2 {
        put_gate(&mut output, value.gate)?;
        output.extend_from_slice(&value.w.to_bits().to_le_bytes());
        for field in value.cv {
            output.extend_from_slice(&field.to_bits().to_le_bytes());
        }
        for field in [value.s, value.u] {
            output.extend_from_slice(&field.to_bits().to_le_bytes());
        }
        output.extend_from_slice(&value.ias.to_le_bytes());
        output.push(value.regime.code());
        output.extend_from_slice(&value.c.to_le_bytes());
        output.extend_from_slice(&value.delta_g.to_bits().to_le_bytes());
        output.extend_from_slice(&value.n_gate.to_le_bytes());
        for field in value.tvr {
            output.extend_from_slice(&field.to_bits().to_le_bytes());
        }
        output.extend_from_slice(&value.chi.to_bits().to_le_bytes());
        output.extend_from_slice(&value.psi.to_bits().to_le_bytes());
    }
    for value in &trace.l3 {
        put_gate(&mut output, value.gate)?;
        for field in [value.r, value.urf] {
            output.extend_from_slice(&field.to_bits().to_le_bytes());
        }
        output.extend_from_slice(&value.g.to_le_bytes());
        output.extend_from_slice(&value.u.to_bits().to_le_bytes());
        output.extend_from_slice(&value.ias.to_le_bytes());
        output.extend_from_slice(&value.hyst.to_le_bytes());
        output.extend_from_slice(&value.raw.to_bits().to_le_bytes());
    }
    for value in &trace.l4 {
        put_gate(&mut output, value.gate)?;
        for field in value.fields {
            output.extend_from_slice(&field.to_bits().to_le_bytes());
        }
    }
    Ok(output)
}

fn canonical_trace(
    trace: &Trace,
    lane_id: &str,
    port_id: &str,
    adapter_digest: &str,
    source_digest: &str,
    kernel_input_map_json: &[u8],
    legacy_map: bool,
) -> Result<Vec<u8>, String> {
    validate_identifier(lane_id, "lane_id")?;
    validate_identifier(port_id, "port_id")?;
    validate_hex_digest(adapter_digest, "adapter digest")?;
    validate_hex_digest(source_digest, "source digest")?;
    if !legacy_map {
        validate_canonical_json_value(kernel_input_map_json)?;
    }
    let mut output = String::new();
    output.push('{');
    json_key(&mut output, "L0_SEV");
    output.push('[');
    for (index, value) in trace.sev.iter().enumerate() {
        comma(&mut output, index);
        output.push('{');
        json_key(&mut output, "F_norm");
        json_string(&mut output, &binary_text(value.f_norm));
        output.push(',');
        json_key(&mut output, "N");
        output.push_str(&value.n.to_string());
        output.push(',');
        json_key(&mut output, "dF");
        json_string(&mut output, &binary_text(value.df));
        output.push(',');
        json_key(&mut output, "kappa");
        json_string(&mut output, &binary_text(value.kappa));
        output.push(',');
        json_key(&mut output, "relevance");
        json_string(&mut output, &binary_text(value.relevance));
        output.push(',');
        json_key(&mut output, "sigma");
        json_string(&mut output, &binary_text(value.sigma));
        output.push('}');
    }
    output.push_str("],");
    json_key(&mut output, "L1_GateL1State");
    output.push('[');
    for (index, value) in trace.l1.iter().enumerate() {
        comma(&mut output, index);
        output.push('{');
        json_key(&mut output, "C_k");
        output.push_str(&value.c.to_string());
        output.push(',');
        json_key(&mut output, "N_gate");
        output.push_str(&value.n_gate.to_string());
        output.push(',');
        json_key(&mut output, "TVR");
        json_float_text_array(&mut output, &value.tvr);
        output.push(',');
        json_key(&mut output, "delta_g");
        json_string(&mut output, &binary_text(value.delta_g));
        output.push(',');
        json_key(&mut output, "end_idx");
        output.push_str(&value.gate.end.to_string());
        output.push(',');
        json_key(&mut output, "projections");
        output.push('[');
        for (projection_index, projection) in value.projections.iter().enumerate() {
            comma(&mut output, projection_index);
            output.push('[');
            output.push_str(&format!(
                "{},{},{}",
                projection[0], projection[1], projection[2]
            ));
            output.push(']');
        }
        output.push_str("],");
        json_key(&mut output, "start_idx");
        output.push_str(&value.gate.start.to_string());
        output.push('}');
    }
    output.push_str("],");
    json_key(&mut output, "L2_GateInterpretation");
    output.push('[');
    for (index, value) in trace.l2.iter().enumerate() {
        comma(&mut output, index);
        output.push('{');
        json_key(&mut output, "CV_k");
        json_float_text_array(&mut output, &value.cv);
        output.push(',');
        json_key(&mut output, "IAS_k");
        output.push_str(&value.ias.to_string());
        output.push(',');
        json_key(&mut output, "S_k");
        json_string(&mut output, &binary_text(value.s));
        output.push(',');
        json_key(&mut output, "U_k");
        json_string(&mut output, &binary_text(value.u));
        output.push(',');
        json_key(&mut output, "end_idx");
        output.push_str(&value.gate.end.to_string());
        output.push(',');
        json_key(&mut output, "regime");
        json_string(&mut output, value.regime.text());
        output.push(',');
        json_key(&mut output, "start_idx");
        output.push_str(&value.gate.start.to_string());
        output.push(',');
        json_key(&mut output, "w_k");
        json_string(&mut output, &binary_text(value.w));
        output.push('}');
    }
    output.push_str("],");
    json_key(&mut output, "L3_ResonanceResult");
    output.push('[');
    for (index, value) in trace.l3.iter().enumerate() {
        comma(&mut output, index);
        output.push('{');
        json_key(&mut output, "Hyst_k");
        output.push_str(&value.hyst.to_string());
        output.push(',');
        json_key(&mut output, "R_k");
        json_string(&mut output, &binary_text(value.r));
        output.push(',');
        json_key(&mut output, "URF_k");
        json_string(&mut output, &binary_text(value.urf));
        output.push(',');
        json_key(&mut output, "end_idx");
        output.push_str(&value.gate.end.to_string());
        output.push(',');
        json_key(&mut output, "g_k");
        output.push_str(&value.g.to_string());
        output.push(',');
        json_key(&mut output, "start_idx");
        output.push_str(&value.gate.start.to_string());
        output.push('}');
    }
    output.push_str("],");
    json_key(&mut output, "L4_DSF");
    output.push('[');
    for (index, value) in trace.l4.iter().enumerate() {
        comma(&mut output, index);
        output.push('{');
        for (field_index, (name, field)) in [
            ("B_k", value.fields[6]),
            ("C_k", value.fields[4]),
            ("D_k", value.fields[0]),
            ("M_k", value.fields[1]),
            ("P_k", value.fields[5]),
            ("R_rev_k", value.fields[2]),
            ("U_star_k", value.fields[3]),
        ]
        .iter()
        .enumerate()
        {
            comma(&mut output, field_index);
            json_key(&mut output, name);
            json_string(&mut output, &binary_text(*field));
        }
        output.push('}');
    }
    output.push_str("],");
    json_key(&mut output, "adapter_result_receipt_sha256");
    json_string(&mut output, adapter_digest);
    output.push(',');
    json_key(&mut output, "binary64_receipt_encoding");
    json_string(&mut output, "exact_Fraction.from_float");
    output.push(',');
    json_key(&mut output, "kernel_input_map");
    if legacy_map {
        json_string(&mut output, "F=1+s/2;inverse_s=2*(F-1)");
    } else {
        output.push_str(std::str::from_utf8(kernel_input_map_json).expect("validated UTF-8"));
    }
    output.push(',');
    json_key(&mut output, "kernel_provider");
    json_string(&mut output, KERNEL_PROVIDER_ID);
    output.push(',');
    json_key(&mut output, "lane_id");
    json_string(&mut output, lane_id);
    output.push(',');
    json_key(&mut output, "native_relevance_rule");
    json_string(&mut output, "exact_source_relevance_identity");
    output.push(',');
    json_key(&mut output, "port_id");
    json_string(&mut output, port_id);
    output.push(',');
    json_key(&mut output, "schema");
    json_string(
        &mut output,
        if legacy_map {
            "glew.provider.complete_signed_port_l0_l4_trace.v3"
        } else {
            "glew.provider.complete_physical_port_l0_l4_trace.v4"
        },
    );
    output.push(',');
    json_key(&mut output, "source_stream_receipt_sha256");
    json_string(&mut output, source_digest);
    output.push('}');
    Ok(output.into_bytes())
}

fn binary_text(value: f64) -> String {
    debug_assert!(value.is_finite());
    if value == 0.0 {
        return "0/1".into();
    }
    let bits = value.to_bits();
    let negative = bits >> 63 != 0;
    let exponent_bits = ((bits >> 52) & 0x7ff) as i32;
    let fraction_bits = bits & ((1u64 << 52) - 1);
    let (mantissa, exponent) = if exponent_bits == 0 {
        (fraction_bits, -1074)
    } else {
        ((1u64 << 52) | fraction_bits, exponent_bits - 1023 - 52)
    };
    let mut numerator = BigInt::from(mantissa);
    let mut denominator = BigInt::from(1u8);
    if exponent >= 0 {
        numerator <<= exponent as usize;
    } else {
        denominator <<= (-exponent) as usize;
    }
    if negative {
        numerator = -numerator;
    }
    let ratio = num_rational::BigRational::new(numerator, denominator);
    format!("{}/{}", ratio.numer(), ratio.denom())
}

fn validate_identifier(value: &str, name: &str) -> Result<(), String> {
    if value.is_empty() || value.trim() != value {
        return Err(format!("{name} is not a canonical identifier"));
    }
    Ok(())
}

fn validate_hex_digest(value: &str, name: &str) -> Result<(), String> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(format!("{name} is not a lowercase SHA-256 digest"));
    }
    Ok(())
}

fn validate_canonical_json_value(value: &[u8]) -> Result<(), String> {
    let text =
        std::str::from_utf8(value).map_err(|_| "kernel input map JSON is not UTF-8".to_string())?;
    if text.is_empty()
        || text.trim() != text
        || !matches!(text.as_bytes().first(), Some(b'{'))
        || !matches!(text.as_bytes().last(), Some(b'}'))
    {
        return Err("kernel input map is not one canonical JSON object".into());
    }
    Ok(())
}

fn json_key(output: &mut String, value: &str) {
    json_string(output, value);
    output.push(':');
}

fn json_string(output: &mut String, value: &str) {
    output.push('"');
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{0008}' => output.push_str("\\b"),
            '\u{000c}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            character if character <= '\u{001f}' => {
                output.push_str(&format!("\\u{:04x}", character as u32));
            }
            character => output.push(character),
        }
    }
    output.push('"');
}

fn json_float_text_array(output: &mut String, values: &[f64]) {
    output.push('[');
    for (index, value) in values.iter().enumerate() {
        comma(output, index);
        json_string(output, &binary_text(*value));
    }
    output.push(']');
}

fn comma(output: &mut String, index: usize) {
    if index != 0 {
        output.push(',');
    }
}

#[cfg(any(test, feature = "diagnostic-api"))]
fn put_count(output: &mut Vec<u8>, value: usize) -> Result<(), String> {
    let encoded = u32::try_from(value).map_err(|_| "trace count exceeds u32".to_string())?;
    output.extend_from_slice(&encoded.to_le_bytes());
    Ok(())
}

#[cfg(any(test, feature = "diagnostic-api"))]
fn put_gate(output: &mut Vec<u8>, gate: Gate) -> Result<(), String> {
    put_count(output, gate.start)?;
    put_count(output, gate.end)
}

#[cfg(feature = "diagnostic-api")]
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn canonical_l0_l4_trace_differential<'py>(
    py: Python<'py>,
    field_bits: Vec<u64>,
    relevance_bits: Vec<u64>,
    lane_id: String,
    port_id: String,
    adapter_sha256: String,
    source_sha256: String,
    kernel_input_map_json: Vec<u8>,
    legacy_map: bool,
) -> PyResult<(Bound<'py, PyBytes>, Bound<'py, PyBytes>, String)> {
    let field: Vec<f64> = field_bits.into_iter().map(f64::from_bits).collect();
    let relevance: Vec<f64> = relevance_bits.into_iter().map(f64::from_bits).collect();
    let trace =
        run_kernel(&field, &relevance, &Config::current()).map_err(PyValueError::new_err)?;
    let snapshot = snapshot(&trace).map_err(PyValueError::new_err)?;
    let payload = canonical_trace(
        &trace,
        &lane_id,
        &port_id,
        &adapter_sha256,
        &source_sha256,
        &kernel_input_map_json,
        legacy_map,
    )
    .map_err(PyValueError::new_err)?;
    let digest = hex_digest(&sha256(&payload));
    Ok((
        PyBytes::new(py, &snapshot),
        PyBytes::new(py, &payload),
        digest,
    ))
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    #[cfg(feature = "diagnostic-api")]
    module.add_function(wrap_pyfunction!(
        canonical_l0_l4_trace_differential,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(canonical_l0_l4_current_config, module)?)?;
    Ok(())
}

fn hex_digest(digest: &[u8; 32]) -> String {
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
}

include!("canonical_l0_l4_batch_api.rs");

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn complete_field_is_never_flattened() {
        let trace = run_kernel(
            &[0.5, 0.75, 1.25, 0.6, 1.4],
            &[1.0, 0.5, 0.25, 0.75, 1.0],
            &Config::current(),
        )
        .expect("canonical trace");
        assert!(!trace.l4.is_empty());
        assert!(trace.l4.iter().all(|row| row.fields.len() == 7));
        let snapshot = snapshot(&trace).expect("snapshot");
        assert!(snapshot.starts_with(SNAPSHOT_MAGIC));
    }

    #[test]
    fn binary_fraction_text_matches_python_fraction_from_float_examples() {
        assert_eq!(binary_text(0.0), "0/1");
        assert_eq!(binary_text(-0.0), "0/1");
        assert_eq!(binary_text(0.5), "1/2");
        assert_eq!(binary_text(-0.125), "-1/8");
        assert_eq!(
            binary_text(f64::from_bits(1)),
            format!("1/{}", BigInt::from(1u8) << 1074usize),
        );
    }

    #[test]
    fn canonical_trace_is_deterministic_and_receipted() {
        let trace = run_kernel(
            &[0.5, 0.5, 0.75, 1.0],
            &[1.0, 1.0, 1.0, 1.0],
            &Config::current(),
        )
        .expect("trace");
        let digest = "0".repeat(64);
        let first = canonical_trace(&trace, "sight", "retina-0", &digest, &digest, b"{}", true)
            .expect("first");
        let second = canonical_trace(&trace, "sight", "retina-0", &digest, &digest, b"{}", true)
            .expect("second");
        assert_eq!(first, second);
        assert_eq!(sha256(&first), sha256(&second));
    }
}
