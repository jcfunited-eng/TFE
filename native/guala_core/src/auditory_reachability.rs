//! Exact native execution of auditory L5's monotone joint causal-path rule.
//!
//! The exact-rational L4 intersection remains owned by Python.  This module
//! receives that already-resolved interval and ports only the binary64 sample
//! recurrence and interval dynamic program, preserving the Python operation
//! order in `auditory_reciprocity._joint_cell_contains_python`.  Each packed
//! pair is pressure plus the provider-settled carrier phase advance for that
//! same observation; the second value is never differenced again here.  Phase
//! is unavailable whenever query or reference is at genesis because an
//! isolated event has no internal predecessor there.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[path = "auditory_incremental.rs"]
mod auditory_incremental;

const PCM_PRESSURE_QUANTUM: f64 = 1.0 / 32_768.0;
const TWO_PI: f64 = 2.0 * std::f64::consts::PI;
const COCHLEAR_CHANNEL_COUNT: usize = 16;
const MAX_EVENT_HOPS: usize = 800;
const MAX_REACHABILITY_WORK: usize = 1_000_000;

type Interval = (f64, f64);

#[derive(Clone, Copy)]
struct Witness<'a> {
    ports: &'a [Vec<f64>],
    sample_count: usize,
}

impl Witness<'_> {
    #[inline]
    fn sample(self, port: usize, index: usize) -> (f64, f64) {
        let offset = index * 2;
        (self.ports[port][offset], self.ports[port][offset + 1])
    }

    #[inline]
    fn phase_advance(self, port: usize, index: usize) -> f64 {
        self.sample(port, index).1
    }

    #[inline]
    fn interpolated_sample(
        self,
        port: usize,
        query_index: usize,
        query_count: usize,
    ) -> (f64, f64) {
        if self.sample_count == 1 || query_count == 1 {
            return (self.sample(port, 0).0, self.phase_advance(port, 0));
        }
        let position = (query_index * (self.sample_count - 1)) as f64 / (query_count - 1) as f64;
        let left = position.floor() as usize;
        let right = (left + 1).min(self.sample_count - 1);
        let weight = position - left as f64;
        let left_pressure = self.sample(port, left).0;
        let right_pressure = self.sample(port, right).0;
        let left_phase = self.phase_advance(port, left);
        let right_phase = self.phase_advance(port, right);
        (
            left_pressure + weight * (right_pressure - left_pressure),
            left_phase + weight * (right_phase - left_phase),
        )
    }

    #[inline]
    fn interpolated_phase_prior_pressure(
        self,
        port: usize,
        query_index: usize,
        query_count: usize,
    ) -> f64 {
        if self.sample_count == 1 {
            return self.sample(port, 0).0;
        }
        let position = if query_count == 1 {
            0.0
        } else {
            (query_index * (self.sample_count - 1)) as f64 / (query_count - 1) as f64
        };
        let prior_position = if position >= 1.0 {
            position - 1.0
        } else {
            position + 1.0
        };
        let left = prior_position.floor() as usize;
        let right = (left + 1).min(self.sample_count - 1);
        let weight = prior_position - left as f64;
        let left_pressure = self.sample(port, left).0;
        let right_pressure = self.sample(port, right).0;
        left_pressure + weight * (right_pressure - left_pressure)
    }
}

fn validate_witness(ports: &[Vec<f64>], sample_count: usize, name: &str) -> PyResult<()> {
    if ports.len() != COCHLEAR_CHANNEL_COUNT {
        return Err(PyValueError::new_err(format!(
            "{name} auditory witness requires exactly 16 cochlear ports"
        )));
    }
    if sample_count == 0 {
        return Err(PyValueError::new_err(format!(
            "{name} auditory witness is empty"
        )));
    }
    if sample_count > MAX_EVENT_HOPS {
        return Err(PyValueError::new_err(format!(
            "{name} auditory witness exceeds the 800-hop event boundary"
        )));
    }
    let expected = sample_count
        .checked_mul(2)
        .ok_or_else(|| PyValueError::new_err(format!("{name} sample count overflow")))?;
    if ports
        .iter()
        .any(|port| port.len() != expected || port.iter().any(|value| !value.is_finite()))
    {
        return Err(PyValueError::new_err(format!(
            "{name} auditory witness changed shape or contains non-finite values"
        )));
    }
    Ok(())
}

fn reachability_work_count(
    query_count: usize,
    left_count: usize,
    right_count: usize,
    same_reference_fingerprint: bool,
) -> Option<usize> {
    let reference_count = left_count.max(right_count);
    let cells = query_count.checked_mul(reference_count)?;
    let recurrence = if query_count != reference_count && same_reference_fingerprint {
        reference_count.checked_mul(reference_count.saturating_sub(1))? / 2
    } else {
        0
    };
    cells.checked_add(recurrence)
}

fn validate_work_boundary(
    query_count: usize,
    left_count: usize,
    right_count: usize,
    same_reference_fingerprint: bool,
) -> PyResult<()> {
    let work = reachability_work_count(
        query_count,
        left_count,
        right_count,
        same_reference_fingerprint,
    )
    .ok_or_else(|| PyValueError::new_err("auditory joint path work count overflow"))?;
    if work > MAX_REACHABILITY_WORK {
        return Err(PyValueError::new_err(
            "auditory joint path exceeds the 1000000-work boundary",
        ));
    }
    Ok(())
}

#[inline]
fn intersect_lambda(
    interval: Interval,
    query: f64,
    left: f64,
    right: f64,
    uncertainty: f64,
) -> Option<Interval> {
    let (mut lower, mut upper) = interval;
    let difference = right - left;
    if difference == 0.0 {
        return if (query - left).abs() <= uncertainty {
            Some(interval)
        } else {
            None
        };
    }
    let first = (query - uncertainty - left) / difference;
    let second = (query + uncertainty - left) / difference;
    let coordinate_lower = first.min(second);
    let coordinate_upper = first.max(second);
    lower = lower.max(coordinate_lower);
    upper = upper.min(coordinate_upper);
    if lower <= upper {
        Some((lower, upper))
    } else {
        None
    }
}

#[inline]
fn phase_uncertainty(pressures: &[f64]) -> Option<f64> {
    if pressures.iter().any(|&value| value <= PCM_PRESSURE_QUANTUM) {
        return None;
    }
    let mut total = 0.0;
    for &value in pressures {
        total += (PCM_PRESSURE_QUANTUM / value).min(1.0).asin() / TWO_PI;
    }
    Some(total)
}

fn direct_state_equivalent(
    left: Witness<'_>,
    first: usize,
    second: usize,
    reference_count: usize,
) -> bool {
    let pressure_uncertainty = 2.0 * PCM_PRESSURE_QUANTUM;
    for port in 0..left.ports.len() {
        let (first_pressure, first_phase) = left.interpolated_sample(port, first, reference_count);
        let (second_pressure, second_phase) =
            left.interpolated_sample(port, second, reference_count);
        if (first_pressure - second_pressure).abs() > pressure_uncertainty {
            return false;
        }
        if first == 0 || second == 0 {
            continue;
        }
        let uncertainty = phase_uncertainty(&[
            first_pressure,
            left.interpolated_phase_prior_pressure(port, first, reference_count),
            second_pressure,
            left.interpolated_phase_prior_pressure(port, second, reference_count),
        ]);
        if let Some(value) = uncertainty {
            if (first_phase - second_phase).abs() > value {
                return false;
            }
        }
    }
    true
}

fn local_interval(
    query: Witness<'_>,
    left: Witness<'_>,
    right: Witness<'_>,
    query_index: usize,
    reference_index: usize,
    reference_count: usize,
    l4_interval: Interval,
) -> Option<Interval> {
    let pressure_uncertainty = 2.0 * PCM_PRESSURE_QUANTUM;
    let mut interval = l4_interval;
    for port in 0..query.ports.len() {
        let (query_pressure, query_phase) =
            query.interpolated_sample(port, query_index, query.sample_count);
        let (left_pressure, left_phase) =
            left.interpolated_sample(port, reference_index, reference_count);
        let (right_pressure, right_phase) =
            right.interpolated_sample(port, reference_index, reference_count);
        interval = intersect_lambda(
            interval,
            query_pressure,
            left_pressure,
            right_pressure,
            pressure_uncertainty,
        )?;
        if query_index == 0 || reference_index == 0 {
            continue;
        }
        let uncertainty = phase_uncertainty(&[
            query_pressure,
            query.interpolated_phase_prior_pressure(port, query_index, query.sample_count),
            left_pressure,
            left.interpolated_phase_prior_pressure(port, reference_index, reference_count),
            right_pressure,
            right.interpolated_phase_prior_pressure(port, reference_index, reference_count),
        ]);
        if let Some(value) = uncertainty {
            interval = intersect_lambda(interval, query_phase, left_phase, right_phase, value)?;
        }
    }
    Some(interval)
}

fn intersect_many(
    intervals: &[Interval],
    local: Interval,
    max_components: usize,
) -> Result<Vec<Interval>, ()> {
    let mut clipped = Vec::with_capacity(intervals.len());
    for &(lower, upper) in intervals {
        let candidate = (lower.max(local.0), upper.min(local.1));
        if candidate.0 <= candidate.1 {
            clipped.push(candidate);
        }
    }
    if clipped.is_empty() {
        return Ok(Vec::new());
    }
    clipped.sort_by(|first, second| {
        first
            .0
            .partial_cmp(&second.0)
            .unwrap()
            .then_with(|| first.1.partial_cmp(&second.1).unwrap())
    });
    let mut merged = Vec::with_capacity(clipped.len());
    merged.push(clipped[0]);
    for &(lower, upper) in &clipped[1..] {
        let last = merged.last_mut().unwrap();
        if lower <= last.1 {
            last.1 = last.1.max(upper);
        } else {
            merged.push((lower, upper));
        }
    }
    if merged.len() > max_components {
        Err(())
    } else {
        Ok(merged)
    }
}

fn joint_path_contains_impl(
    query: Witness<'_>,
    left: Witness<'_>,
    right: Witness<'_>,
    same_reference_fingerprint: bool,
    l4_interval: Interval,
    max_components: usize,
) -> Option<bool> {
    let reference_count = left.sample_count.max(right.sample_count);
    let needs_recurrence = query.sample_count != reference_count && same_reference_fingerprint;
    let mut recurrence_incoming = vec![Vec::<usize>::new(); reference_count];
    if needs_recurrence {
        for later in 2..reference_count {
            for earlier in (0..=(later - 2)).rev() {
                if direct_state_equivalent(left, earlier, later, reference_count) {
                    recurrence_incoming[later].push(earlier);
                    recurrence_incoming[earlier + 1].push(later);
                    break;
                }
            }
        }
    }

    let mut previous = vec![Vec::<Interval>::new(); reference_count];
    for query_index in 0..query.sample_count {
        let mut current = vec![Vec::<Interval>::new(); reference_count];
        for reference_index in 0..reference_count {
            let mut predecessors = Vec::<Interval>::new();
            if query_index == 0 && reference_index == 0 {
                predecessors.push(l4_interval);
            } else {
                if query_index > 0 {
                    predecessors.extend_from_slice(&previous[reference_index]);
                }
                if reference_index > 0 {
                    predecessors.extend_from_slice(&current[reference_index - 1]);
                }
                if query_index > 0 && reference_index > 0 {
                    predecessors.extend_from_slice(&previous[reference_index - 1]);
                }
                if query_index > 0 {
                    for &recurrent_predecessor in &recurrence_incoming[reference_index] {
                        predecessors.extend_from_slice(&previous[recurrent_predecessor]);
                    }
                }
            }
            if predecessors.is_empty() {
                continue;
            }
            let Some(local) = local_interval(
                query,
                left,
                right,
                query_index,
                reference_index,
                reference_count,
                l4_interval,
            ) else {
                continue;
            };
            current[reference_index] = intersect_many(&predecessors, local, max_components).ok()?;
        }
        previous = current;
    }
    Some(!previous[reference_count - 1].is_empty())
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn auditory_joint_path_contains(
    py: Python<'_>,
    query_ports: Vec<Vec<f64>>,
    query_count: usize,
    left_ports: Vec<Vec<f64>>,
    left_count: usize,
    right_ports: Vec<Vec<f64>>,
    right_count: usize,
    same_reference_fingerprint: bool,
    l4_lower: f64,
    l4_upper: f64,
    max_interval_components: usize,
) -> PyResult<Option<bool>> {
    if query_ports.len() != COCHLEAR_CHANNEL_COUNT
        || left_ports.len() != COCHLEAR_CHANNEL_COUNT
        || right_ports.len() != COCHLEAR_CHANNEL_COUNT
    {
        return Err(PyValueError::new_err(
            "auditory joint path requires exactly 16 cochlear ports",
        ));
    }
    validate_work_boundary(
        query_count,
        left_count,
        right_count,
        same_reference_fingerprint,
    )?;
    validate_witness(&query_ports, query_count, "query")?;
    validate_witness(&left_ports, left_count, "left")?;
    validate_witness(&right_ports, right_count, "right")?;
    if !l4_lower.is_finite()
        || !l4_upper.is_finite()
        || l4_lower > l4_upper
        || max_interval_components == 0
    {
        return Err(PyValueError::new_err(
            "auditory joint path interval boundary is invalid",
        ));
    }
    Ok(py.allow_threads(|| {
        joint_path_contains_impl(
            Witness {
                ports: &query_ports,
                sample_count: query_count,
            },
            Witness {
                ports: &left_ports,
                sample_count: left_count,
            },
            Witness {
                ports: &right_ports,
                sample_count: right_count,
            },
            same_reference_fingerprint,
            (l4_lower, l4_upper),
            max_interval_components,
        )
    }))
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(auditory_joint_path_contains, module)?)?;
    auditory_incremental::register(module)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        reachability_work_count, validate_witness, validate_work_boundary, Witness,
        COCHLEAR_CHANNEL_COUNT, MAX_EVENT_HOPS, MAX_REACHABILITY_WORK,
    };

    #[test]
    fn packed_second_value_is_consumed_as_settled_phase_advance() {
        let ports = vec![vec![0.25, 0.375, 0.5, -0.625]];
        let witness = Witness {
            ports: &ports,
            sample_count: 2,
        };

        assert_eq!(witness.phase_advance(0, 0), 0.375);
        assert_eq!(witness.phase_advance(0, 1), -0.625);
    }

    #[test]
    fn singleton_retains_its_provider_settled_phase_advance() {
        let ports = vec![vec![0.25, -0.75]];
        let witness = Witness {
            ports: &ports,
            sample_count: 1,
        };

        assert_eq!(witness.interpolated_sample(0, 0, 1), (0.25, -0.75));
    }

    #[test]
    fn native_witness_requires_exact_cochlear_topology_and_event_bound() {
        let wrong_topology = vec![vec![0.25, 0.0]; COCHLEAR_CHANNEL_COUNT - 1];
        assert!(validate_witness(&wrong_topology, 1, "query").is_err());

        let oversized = vec![vec![0.25; (MAX_EVENT_HOPS + 1) * 2]; COCHLEAR_CHANNEL_COUNT];
        assert!(validate_witness(&oversized, MAX_EVENT_HOPS + 1, "query").is_err());
    }

    #[test]
    fn native_work_boundary_is_checked_with_python_identical_arithmetic() {
        assert_eq!(reachability_work_count(799, 800, 800, true), Some(958_800),);
        assert!(validate_work_boundary(799, 800, 800, true).is_ok());
        assert_eq!(MAX_REACHABILITY_WORK, 1_000_000);
        assert!(validate_work_boundary(899, 900, 900, true).is_err());
    }
}
