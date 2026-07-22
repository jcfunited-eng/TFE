//! Exact native execution of the continuous auditory terminal proposal DP.
//!
//! This module owns no recognition authority. It advances only the same
//! pressure/phase interval rows as
//! `substrate.auditory_incremental_terminal`; candidate spans must still be
//! rebuilt through the unchanged full L0--L4 field and settled by auditory L5
//! and reciprocity before anything can be released.
//!
//! Learned cells are immutable. Per-stream tracker state remains inside one
//! mutable Python-owned instance so the nested interval rows never cross the
//! Python/Rust boundary on each 10 ms frame. Python serializes calls with its
//! stream-owner lock; PyO3's mutable borrow rejects concurrent entry. The
//! heavy loop releases the GIL. Python retains evidence, pending-terminal,
//! ambiguity, and final-authority ownership.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::BTreeSet;
use std::sync::Arc;

const PCM_PRESSURE_QUANTUM: f64 = 1.0 / 32_768.0;
const TWO_PI: f64 = 2.0 * std::f64::consts::PI;
const COCHLEAR_CHANNEL_COUNT: usize = 16;
const OBSERVATION_HOP_SAMPLES: usize = 160;
const MAX_EVENT_HOPS: usize = 800;

type Interval = (f64, f64);
type IntervalSet = Vec<Interval>;
type Row = Vec<IntervalSet>;

/// left ports, left count, right ports, right count, terminal floor
type CellTransport = (Vec<Vec<f64>>, usize, Vec<Vec<f64>>, usize, usize, bool);

/// terminal spans, pending starts to remove, resource observed,
/// all tracker/pending state must be cleared, exact charged work cells,
/// active tracker count, sorted unique active starts
type StepTransport = (
    Vec<(usize, usize)>,
    Vec<usize>,
    bool,
    bool,
    usize,
    usize,
    Vec<usize>,
);

#[derive(Clone)]
struct Branch {
    ports: Vec<Vec<f64>>,
    sample_count: usize,
}

impl Branch {
    #[inline]
    fn sample(&self, port: usize, index: usize) -> (f64, f64) {
        let offset = index * 2;
        (self.ports[port][offset], self.ports[port][offset + 1])
    }

    #[inline]
    fn phase_advance(&self, port: usize, index: usize) -> f64 {
        if self.sample_count == 1 {
            return 0.0;
        }
        let right = index.max(1);
        self.sample(port, right).1 - self.sample(port, right - 1).1
    }

    #[inline]
    fn sample_on_reference(
        &self,
        port: usize,
        query_index: usize,
        query_count: usize,
    ) -> (f64, f64) {
        if self.sample_count == 1 || query_count == 1 {
            return (self.sample(port, 0).0, 0.0);
        }
        let position = (query_index * (self.sample_count - 1)) as f64 / (query_count - 1) as f64;
        let left_index = position.floor() as usize;
        let right_index = (left_index + 1).min(self.sample_count - 1);
        let weight = position - left_index as f64;
        let left_pressure = self.sample(port, left_index).0;
        let right_pressure = self.sample(port, right_index).0;
        let left_phase = self.phase_advance(port, left_index);
        let right_phase = self.phase_advance(port, right_index);
        (
            left_pressure + weight * (right_pressure - left_pressure),
            left_phase + weight * (right_phase - left_phase),
        )
    }

    #[inline]
    fn phase_prior_pressure(&self, port: usize, query_index: usize, query_count: usize) -> f64 {
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

#[derive(Clone)]
struct Cell {
    left: Branch,
    right: Branch,
    reference_count: usize,
    terminal_floor: usize,
    recurrence_incoming: Vec<Vec<usize>>,
}

fn recurrence_incoming(branch: &Branch, reference_count: usize) -> Vec<Vec<usize>> {
    let pressure_uncertainty = 2.0 * PCM_PRESSURE_QUANTUM;
    let mut incoming = vec![Vec::new(); reference_count];
    for later in 2..reference_count {
        for earlier in (0..=(later - 2)).rev() {
            let mut equivalent = true;
            for port in 0..COCHLEAR_CHANNEL_COUNT {
                let (first_pressure, first_phase) =
                    branch.sample_on_reference(port, earlier, reference_count);
                let (second_pressure, second_phase) =
                    branch.sample_on_reference(port, later, reference_count);
                if (first_pressure - second_pressure).abs() > pressure_uncertainty {
                    equivalent = false;
                    break;
                }
                if let Some(uncertainty) = phase_uncertainty(&[
                    first_pressure,
                    branch.phase_prior_pressure(port, earlier, reference_count),
                    second_pressure,
                    branch.phase_prior_pressure(port, later, reference_count),
                ]) {
                    if (first_phase - second_phase).abs() > uncertainty {
                        equivalent = false;
                        break;
                    }
                }
            }
            if equivalent {
                incoming[later].push(earlier);
                incoming[earlier + 1].push(later);
                break;
            }
        }
    }
    incoming
}

#[derive(Clone, Debug, PartialEq)]
struct Tracker {
    cell_index: usize,
    start_sample: usize,
    frames_seen: usize,
    first_pressure: Vec<f64>,
    first_phase: Vec<f64>,
    previous_pressure: Vec<f64>,
    previous_phase: Vec<f64>,
    row: Option<Row>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum TrackerAdvance {
    Indeterminate,
    NoTerminal,
    Terminal,
}

fn validate_branch(ports: &[Vec<f64>], sample_count: usize, name: &str) -> PyResult<()> {
    if sample_count < 2 || sample_count > MAX_EVENT_HOPS {
        return Err(PyValueError::new_err(format!(
            "{name} incremental witness sample count is invalid"
        )));
    }
    if ports.len() != COCHLEAR_CHANNEL_COUNT {
        return Err(PyValueError::new_err(format!(
            "{name} incremental witness requires sixteen ports"
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
            "{name} incremental witness changed shape or contains non-finite values"
        )));
    }
    Ok(())
}

fn cells_from_transport(values: Vec<CellTransport>) -> PyResult<Vec<Cell>> {
    let mut cells = Vec::with_capacity(values.len());
    for (
        index,
        (
            left_ports,
            left_count,
            right_ports,
            right_count,
            terminal_floor,
            same_reference_fingerprint,
        ),
    ) in values.into_iter().enumerate()
    {
        validate_branch(&left_ports, left_count, &format!("cell {index} left"))?;
        validate_branch(&right_ports, right_count, &format!("cell {index} right"))?;
        if terminal_floor != left_count.min(right_count) {
            return Err(PyValueError::new_err(
                "incremental terminal floor differs from its witnesses",
            ));
        }
        let left = Branch {
            ports: left_ports,
            sample_count: left_count,
        };
        let reference_count = left_count.max(right_count);
        let recurrence_incoming = if same_reference_fingerprint {
            recurrence_incoming(&left, reference_count)
        } else {
            vec![Vec::new(); reference_count]
        };
        cells.push(Cell {
            left,
            right: Branch {
                ports: right_ports,
                sample_count: right_count,
            },
            reference_count,
            terminal_floor,
            recurrence_incoming,
        });
    }
    Ok(cells)
}

fn validate_vector(values: &[f64], name: &str) -> PyResult<()> {
    if values.len() != COCHLEAR_CHANNEL_COUNT || values.iter().any(|value| !value.is_finite()) {
        return Err(PyValueError::new_err(format!(
            "incremental {name} changed shape or contains non-finite values"
        )));
    }
    Ok(())
}

fn validate_row(row: &Row, reference_count: usize, max_components: usize) -> PyResult<()> {
    if row.len() != reference_count {
        return Err(PyValueError::new_err(
            "incremental tracker row changed reference cardinality",
        ));
    }
    for intervals in row {
        if intervals.len() > max_components {
            return Err(PyValueError::new_err(
                "incremental tracker row exceeded its interval boundary",
            ));
        }
        let mut prior_upper = None;
        for &(lower, upper) in intervals {
            if !lower.is_finite() || !upper.is_finite() || lower > upper {
                return Err(PyValueError::new_err(
                    "incremental tracker interval is invalid",
                ));
            }
            if prior_upper.is_some_and(|prior| lower <= prior) {
                return Err(PyValueError::new_err(
                    "incremental tracker intervals are not canonically disjoint",
                ));
            }
            prior_upper = Some(upper);
        }
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
    let result = (
        python_max(interval.0, python_min(first, second)),
        python_min(interval.1, python_max(first, second)),
    );
    if result.0 <= result.1 {
        Some(result)
    } else {
        None
    }
}

#[inline]
fn python_min(first: f64, second: f64) -> f64 {
    if second < first {
        second
    } else {
        first
    }
}

#[inline]
fn python_max(first: f64, second: f64) -> f64 {
    if second > first {
        second
    } else {
        first
    }
}

#[inline]
fn phase_uncertainty(pressures: &[f64]) -> Option<f64> {
    if pressures.iter().any(|&value| value <= PCM_PRESSURE_QUANTUM) {
        return None;
    }
    let mut total = 0.0;
    for &value in pressures {
        total += python_min(1.0, PCM_PRESSURE_QUANTUM / value).asin() / TWO_PI;
    }
    Some(total)
}

fn intersect_many(
    values: &[Interval],
    local: Interval,
    max_components: usize,
) -> Result<IntervalSet, ()> {
    let mut clipped = Vec::with_capacity(values.len());
    for &(lower, upper) in values {
        let candidate = (python_max(lower, local.0), python_min(upper, local.1));
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
            last.1 = python_max(last.1, upper);
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

fn local_interval(
    cell: &Cell,
    query_pressure: &[f64],
    query_phase_advance: &[f64],
    query_phase_prior_pressure: &[f64],
    reference_index: usize,
) -> Option<Interval> {
    let mut interval = (0.0, 1.0);
    let pressure_uncertainty = 2.0 * PCM_PRESSURE_QUANTUM;
    for port in 0..COCHLEAR_CHANNEL_COUNT {
        let (left_pressure, left_phase) =
            cell.left
                .sample_on_reference(port, reference_index, cell.reference_count);
        let (right_pressure, right_phase) =
            cell.right
                .sample_on_reference(port, reference_index, cell.reference_count);
        interval = intersect_lambda(
            interval,
            query_pressure[port],
            left_pressure,
            right_pressure,
            pressure_uncertainty,
        )?;
        let uncertainty = phase_uncertainty(&[
            query_pressure[port],
            query_phase_prior_pressure[port],
            left_pressure,
            cell.left
                .phase_prior_pressure(port, reference_index, cell.reference_count),
            right_pressure,
            cell.right
                .phase_prior_pressure(port, reference_index, cell.reference_count),
        ]);
        if let Some(value) = uncertainty {
            interval = intersect_lambda(
                interval,
                query_phase_advance[port],
                left_phase,
                right_phase,
                value,
            )?;
        }
    }
    Some(interval)
}

fn advance_row(
    cell: &Cell,
    previous: Option<&Row>,
    pressure: &[f64],
    phase_advance: &[f64],
    phase_prior_pressure: &[f64],
    max_components: usize,
) -> Result<Row, ()> {
    let mut current = vec![Vec::new(); cell.reference_count];
    for reference_index in 0..cell.reference_count {
        let mut predecessors = Vec::new();
        if previous.is_none() && reference_index == 0 {
            predecessors.push((0.0, 1.0));
        } else {
            if let Some(prior) = previous {
                predecessors.extend_from_slice(&prior[reference_index]);
            }
            if reference_index > 0 {
                predecessors.extend_from_slice(&current[reference_index - 1]);
            }
            if let Some(prior) = previous {
                if reference_index > 0 {
                    predecessors.extend_from_slice(&prior[reference_index - 1]);
                }
                for &recurrent in &cell.recurrence_incoming[reference_index] {
                    predecessors.extend_from_slice(&prior[recurrent]);
                }
            }
        }
        if predecessors.is_empty() {
            continue;
        }
        let Some(local) = local_interval(
            cell,
            pressure,
            phase_advance,
            phase_prior_pressure,
            reference_index,
        ) else {
            continue;
        };
        current[reference_index] = intersect_many(&predecessors, local, max_components)?;
    }
    Ok(current)
}

#[inline]
fn any_row(row: &Row) -> bool {
    row.iter().any(|intervals| !intervals.is_empty())
}

fn advance_tracker(
    tracker: &mut Tracker,
    cells: &[Cell],
    pressure: &[f64],
    phase: &[f64],
    max_components: usize,
) -> TrackerAdvance {
    let cell = &cells[tracker.cell_index];
    let delta: Vec<f64> = phase
        .iter()
        .zip(&tracker.previous_phase)
        .map(|(current, prior)| current - prior)
        .collect();
    let row = if tracker.row.is_none() {
        let first_row = match advance_row(
            cell,
            None,
            &tracker.first_pressure,
            &delta,
            pressure,
            max_components,
        ) {
            Ok(value) => value,
            Err(()) => return TrackerAdvance::Indeterminate,
        };
        if !any_row(&first_row) {
            return TrackerAdvance::NoTerminal;
        }
        match advance_row(
            cell,
            Some(&first_row),
            pressure,
            &delta,
            &tracker.first_pressure,
            max_components,
        ) {
            Ok(value) => value,
            Err(()) => return TrackerAdvance::Indeterminate,
        }
    } else {
        match advance_row(
            cell,
            tracker.row.as_ref(),
            pressure,
            &delta,
            &tracker.previous_pressure,
            max_components,
        ) {
            Ok(value) => value,
            Err(()) => return TrackerAdvance::Indeterminate,
        }
    };
    if !any_row(&row) {
        // Preserve the prior row exactly as the Python implementation did.
        return TrackerAdvance::NoTerminal;
    }
    let terminal =
        tracker.frames_seen + 1 >= cell.terminal_floor && !row[cell.reference_count - 1].is_empty();
    tracker.row = Some(row);
    tracker.frames_seen += 1;
    tracker.previous_pressure.clone_from_slice(pressure);
    tracker.previous_phase.clone_from_slice(phase);
    if terminal {
        TrackerAdvance::Terminal
    } else {
        TrackerAdvance::NoTerminal
    }
}

fn spawn(
    cells: &[Cell],
    completion_sample: usize,
    pressure: &[f64],
    phase: &[f64],
    trackers: &mut Vec<Tracker>,
) {
    let start_sample = completion_sample - OBSERVATION_HOP_SAMPLES;
    let pressure_uncertainty = 2.0 * PCM_PRESSURE_QUANTUM;
    for (cell_index, cell) in cells.iter().enumerate() {
        let mut interval = Some((0.0, 1.0));
        for port in 0..COCHLEAR_CHANNEL_COUNT {
            let (left, _) = cell.left.sample_on_reference(port, 0, cell.reference_count);
            let (right, _) = cell
                .right
                .sample_on_reference(port, 0, cell.reference_count);
            interval = intersect_lambda(
                interval.unwrap(),
                pressure[port],
                left,
                right,
                pressure_uncertainty,
            );
            if interval.is_none() {
                break;
            }
        }
        if interval.is_some() {
            trackers.push(Tracker {
                cell_index,
                start_sample,
                frames_seen: 1,
                first_pressure: pressure.to_vec(),
                first_phase: phase.to_vec(),
                previous_pressure: pressure.to_vec(),
                previous_phase: phase.to_vec(),
                row: None,
            });
        }
    }
}

fn active_starts(trackers: &[Tracker]) -> BTreeSet<usize> {
    trackers
        .iter()
        .map(|tracker| tracker.start_sample)
        .collect()
}

fn proposal_step_impl(
    cells: &[Cell],
    trackers: &mut Vec<Tracker>,
    completion_sample: usize,
    pressure: &[f64],
    phase: &[f64],
    pending_terminals: &[(usize, usize)],
    max_active_trackers: usize,
    max_work: usize,
    max_components: usize,
) -> StepTransport {
    let mut terminal_spans = BTreeSet::new();
    let mut remove_pending_starts = BTreeSet::new();
    let mounted_trackers = std::mem::take(trackers);
    let mut survivors = Vec::with_capacity(mounted_trackers.len() + cells.len());
    let mut resource = false;
    let mut work_cells = 0usize;

    for mut tracker in mounted_trackers {
        let cell = &cells[tracker.cell_index];
        let charge = cell.reference_count * if tracker.row.is_none() { 2 } else { 1 };
        work_cells = work_cells.saturating_add(charge);
        if work_cells > max_work {
            return (
                Vec::new(),
                Vec::new(),
                true,
                true,
                work_cells,
                0,
                Vec::new(),
            );
        }
        match advance_tracker(&mut tracker, cells, pressure, phase, max_components) {
            TrackerAdvance::Indeterminate => {
                resource = true;
                remove_pending_starts.insert(tracker.start_sample);
            }
            TrackerAdvance::NoTerminal => {
                if tracker.row.as_ref().is_some_and(any_row) {
                    survivors.push(tracker);
                }
            }
            TrackerAdvance::Terminal => {
                terminal_spans.insert((tracker.start_sample, completion_sample));
                survivors.push(tracker);
            }
        }
    }

    spawn(cells, completion_sample, pressure, phase, &mut survivors);
    if survivors.len() > max_active_trackers {
        return (
            Vec::new(),
            Vec::new(),
            true,
            true,
            work_cells,
            0,
            Vec::new(),
        );
    }

    let starts = active_starts(&survivors);
    let terminal_starts: BTreeSet<usize> =
        terminal_spans.iter().map(|(start, _end)| *start).collect();
    for &(start, end) in pending_terminals {
        if completion_sample > end && !terminal_starts.contains(&start) {
            remove_pending_starts.insert(start);
        }
    }
    let active_count = survivors.len();
    let active_start_values = starts.into_iter().collect();
    *trackers = survivors;

    (
        terminal_spans.into_iter().collect(),
        remove_pending_starts.into_iter().collect(),
        resource,
        false,
        work_cells,
        active_count,
        active_start_values,
    )
}

fn expire_before_impl(trackers: &mut Vec<Tracker>, keep_from: usize) -> bool {
    let prior = trackers.len();
    trackers.retain(|tracker| tracker.start_sample >= keep_from);
    trackers.len() != prior
}

fn discard_starts_impl(trackers: &mut Vec<Tracker>, starts: &BTreeSet<usize>) -> usize {
    let prior = trackers.len();
    trackers.retain(|tracker| !starts.contains(&tracker.start_sample));
    prior - trackers.len()
}

fn retain_at_or_after_impl(trackers: &mut Vec<Tracker>, sample: usize) -> usize {
    let prior = trackers.len();
    trackers.retain(|tracker| tracker.start_sample >= sample);
    prior - trackers.len()
}

/// Immutable learned proposal cells plus one serialized stream's exact state.
#[pyclass(module = "guala_core")]
pub(crate) struct AuditoryIncrementalProposalCells {
    cells: Arc<Vec<Cell>>,
    trackers: Vec<Tracker>,
}

#[pymethods]
impl AuditoryIncrementalProposalCells {
    #[new]
    fn new(cells: Vec<CellTransport>) -> PyResult<Self> {
        Ok(Self {
            cells: Arc::new(cells_from_transport(cells)?),
            trackers: Vec::new(),
        })
    }

    #[getter]
    fn cell_count(&self) -> usize {
        self.cells.len()
    }

    #[getter]
    fn active_tracker_count(&self) -> usize {
        self.trackers.len()
    }

    #[getter]
    fn active_starts(&self) -> Vec<usize> {
        active_starts(&self.trackers).into_iter().collect()
    }

    #[allow(clippy::too_many_arguments)]
    fn step(
        &mut self,
        py: Python<'_>,
        completion_sample: usize,
        pressure: Vec<f64>,
        phase: Vec<f64>,
        pending_terminals: Vec<(usize, usize)>,
        max_active_trackers: usize,
        max_work: usize,
        max_interval_components: usize,
    ) -> PyResult<StepTransport> {
        if completion_sample < OBSERVATION_HOP_SAMPLES
            || completion_sample % OBSERVATION_HOP_SAMPLES != 0
            || max_active_trackers == 0
            || max_work == 0
            || max_interval_components == 0
        {
            return Err(PyValueError::new_err(
                "incremental proposal step boundary is invalid",
            ));
        }
        validate_vector(&pressure, "frame pressure")?;
        validate_vector(&phase, "frame phase")?;
        if self.trackers.len() > max_active_trackers {
            return Err(PyValueError::new_err(
                "incremental proposal state exceeds tracker capacity",
            ));
        }
        for tracker in &self.trackers {
            if let Some(ref row) = tracker.row {
                validate_row(
                    row,
                    self.cells[tracker.cell_index].reference_count,
                    max_interval_components,
                )?;
            }
        }
        let mut pending_starts = BTreeSet::new();
        for &(start, end) in &pending_terminals {
            if start % OBSERVATION_HOP_SAMPLES != 0
                || end % OBSERVATION_HOP_SAMPLES != 0
                || end <= start
                || !pending_starts.insert(start)
            {
                return Err(PyValueError::new_err(
                    "incremental pending terminal state is invalid",
                ));
            }
        }
        let cells = Arc::clone(&self.cells);
        let trackers = &mut self.trackers;
        Ok(py.allow_threads(move || {
            proposal_step_impl(
                &cells,
                trackers,
                completion_sample,
                &pressure,
                &phase,
                &pending_terminals,
                max_active_trackers,
                max_work,
                max_interval_components,
            )
        }))
    }

    /// Drop trackers whose causal start has left PCM retention.
    fn expire_before(&mut self, keep_from: usize) -> PyResult<bool> {
        validate_sample_boundary(keep_from, "retention")?;
        Ok(expire_before_impl(&mut self.trackers, keep_from))
    }

    /// Drop every tracker belonging to the supplied causal starts.
    fn discard_starts(&mut self, starts: Vec<usize>) -> PyResult<usize> {
        let mut unique = BTreeSet::new();
        for start in starts {
            validate_sample_boundary(start, "discard start")?;
            unique.insert(start);
        }
        Ok(discard_starts_impl(&mut self.trackers, &unique))
    }

    /// Retain only trackers starting at or after a released event boundary.
    fn retain_at_or_after(&mut self, sample: usize) -> PyResult<usize> {
        validate_sample_boundary(sample, "release")?;
        Ok(retain_at_or_after_impl(&mut self.trackers, sample))
    }

    /// Clear all per-stream proposal state while preserving learned cells.
    fn clear(&mut self) -> usize {
        let prior = self.trackers.len();
        self.trackers.clear();
        prior
    }
}

fn validate_sample_boundary(sample: usize, name: &str) -> PyResult<()> {
    if sample % OBSERVATION_HOP_SAMPLES != 0 {
        return Err(PyValueError::new_err(format!(
            "incremental {name} sample is not on an observation boundary"
        )));
    }
    Ok(())
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<AuditoryIncrementalProposalCells>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Instant;

    fn repeated_ports(values: &[(f64, f64)]) -> Vec<Vec<f64>> {
        let packed: Vec<f64> = values
            .iter()
            .flat_map(|&(pressure, phase)| [pressure, phase])
            .collect();
        (0..COCHLEAR_CHANNEL_COUNT)
            .map(|_| packed.clone())
            .collect()
    }

    fn cell(values: &[(f64, f64)]) -> Cell {
        let branch = Branch {
            ports: repeated_ports(values),
            sample_count: values.len(),
        };
        Cell {
            left: branch.clone(),
            right: branch,
            reference_count: values.len(),
            terminal_floor: values.len(),
            recurrence_incoming: vec![Vec::new(); values.len()],
        }
    }

    fn frame(value: f64) -> Vec<f64> {
        vec![value; COCHLEAR_CHANNEL_COUNT]
    }

    fn step(
        cells: &[Cell],
        trackers: &mut Vec<Tracker>,
        completion: usize,
        pressure: f64,
        phase: f64,
        pending: &[(usize, usize)],
        max_active: usize,
        max_work: usize,
        max_components: usize,
    ) -> StepTransport {
        proposal_step_impl(
            cells,
            trackers,
            completion,
            &frame(pressure),
            &frame(phase),
            pending,
            max_active,
            max_work,
            max_components,
        )
    }

    #[test]
    fn interval_bounds_preserve_python_signed_zero_order() {
        assert!(!python_min(0.0, -0.0).is_sign_negative());
        assert!(python_min(-0.0, 0.0).is_sign_negative());
        assert!(!python_max(0.0, -0.0).is_sign_negative());
        assert!(python_max(-0.0, 0.0).is_sign_negative());
    }

    #[test]
    fn native_owner_preserves_state_across_steps() {
        let cells = vec![cell(&[(0.5, 0.0), (0.5, 0.1)])];
        let mut trackers = Vec::new();
        let first = step(&cells, &mut trackers, 160, 0.5, 0.0, &[], 10, 1_000, 64);
        assert_eq!(first.5, 1);
        assert_eq!(first.6, vec![0]);
        assert!(first.0.is_empty());
        assert_eq!(trackers.len(), 1);

        let second = step(&cells, &mut trackers, 320, 0.5, 0.1, &[], 10, 1_000, 64);
        assert_eq!(second.0, vec![(0, 320)]);
        assert_eq!(second.4, 4);
        assert_eq!(second.5, 2);
        assert_eq!(trackers.len(), 2);
    }

    #[test]
    fn established_tracker_retains_prior_row_after_empty_advance() {
        let cells = vec![cell(&[(0.5, 0.0), (0.5, 0.1)])];
        let mut trackers = Vec::new();
        step(&cells, &mut trackers, 160, 0.5, 0.0, &[], 10, 1_000, 64);
        step(&cells, &mut trackers, 320, 0.5, 0.1, &[], 10, 1_000, 64);
        trackers.truncate(1);
        let prior = trackers[0].row.clone();
        let third = step(&cells, &mut trackers, 480, 0.9, 0.2, &[], 10, 1_000, 64);
        assert_eq!(third.5, 1);
        assert_eq!(trackers[0].row, prior);
        assert!(third.0.is_empty());
    }

    #[test]
    fn duplicate_cell_terminals_are_sorted_and_deduplicated() {
        let learned = cell(&[(0.5, 0.0), (0.5, 0.1)]);
        let cells = vec![learned.clone(), learned];
        let mut trackers = Vec::new();
        step(&cells, &mut trackers, 160, 0.5, 0.0, &[], 10, 1_000, 64);
        let second = step(&cells, &mut trackers, 320, 0.5, 0.1, &[], 10, 1_000, 64);
        assert_eq!(second.0, vec![(0, 320)]);
        assert_eq!(second.5, 4);
        assert_eq!(trackers[0].cell_index, 0);
        assert_eq!(trackers[1].cell_index, 1);
    }

    #[test]
    fn work_overflow_clears_native_state_before_return() {
        let cells = vec![cell(&[(0.5, 0.0), (0.5, 0.1)])];
        let mut trackers = Vec::new();
        step(&cells, &mut trackers, 160, 0.5, 0.0, &[], 10, 1_000, 64);
        let overflow = step(&cells, &mut trackers, 320, 0.5, 0.1, &[(0, 160)], 10, 1, 64);
        assert!(overflow.0.is_empty());
        assert!(overflow.1.is_empty());
        assert!(overflow.2);
        assert!(overflow.3);
        assert_eq!(overflow.4, 4);
        assert_eq!(overflow.5, 0);
        assert!(trackers.is_empty());
    }

    #[test]
    fn active_tracker_overflow_clears_native_state_after_spawn() {
        let learned = cell(&[(0.5, 0.0), (0.5, 0.1)]);
        let cells = vec![learned.clone(), learned];
        let mut trackers = Vec::new();
        let result = step(&cells, &mut trackers, 160, 0.5, 0.0, &[], 1, 1_000, 64);
        assert!(result.0.is_empty());
        assert!(result.2);
        assert!(result.3);
        assert_eq!(result.4, 0);
        assert_eq!(result.5, 0);
        assert!(trackers.is_empty());
    }

    #[test]
    fn active_nonterminal_pending_start_closes_without_a_forced_proposal() {
        let cells = vec![cell(&[(0.5, 0.0), (0.5, 0.1), (0.5, 0.2)])];
        let mut trackers = Vec::new();
        step(&cells, &mut trackers, 160, 0.5, 0.0, &[], 10, 1_000, 64);
        let second = step(
            &cells,
            &mut trackers,
            320,
            0.5,
            0.1,
            &[(0, 160)],
            10,
            1_000,
            64,
        );
        assert!(second.0.is_empty());
        assert_eq!(second.1, vec![0]);
        assert!(!second.2);
        assert!(!second.3);
    }

    #[test]
    fn interval_component_exhaustion_removes_only_its_pending_start() {
        let cells = vec![cell(&[(0.5, 0.0), (0.5, 0.1)])];
        let row = vec![vec![(0.0, 0.4), (0.6, 1.0)]; 2];
        let mut trackers = vec![Tracker {
            cell_index: 0,
            start_sample: 0,
            frames_seen: 2,
            first_pressure: frame(0.5),
            first_phase: frame(0.0),
            previous_pressure: frame(0.5),
            previous_phase: frame(0.1),
            row: Some(row),
        }];
        let result = step(
            &cells,
            &mut trackers,
            480,
            0.5,
            0.2,
            &[(0, 320)],
            10,
            1_000,
            1,
        );
        assert_eq!(result.5, 1);
        assert_eq!(trackers[0].start_sample, 320);
        assert_eq!(result.1, vec![0]);
        assert!(result.2);
        assert!(!result.3);
    }

    #[test]
    fn native_filters_preserve_exact_start_boundaries() {
        let prototype = |start_sample| Tracker {
            cell_index: 0,
            start_sample,
            frames_seen: 1,
            first_pressure: frame(0.5),
            first_phase: frame(0.0),
            previous_pressure: frame(0.5),
            previous_phase: frame(0.0),
            row: None,
        };
        let mut trackers = vec![prototype(0), prototype(160), prototype(160), prototype(320)];
        assert_eq!(
            discard_starts_impl(&mut trackers, &BTreeSet::from([160])),
            2
        );
        assert_eq!(active_starts(&trackers), BTreeSet::from([0, 320]));
        assert!(expire_before_impl(&mut trackers, 160));
        assert_eq!(active_starts(&trackers), BTreeSet::from([320]));
        trackers.push(prototype(480));
        assert_eq!(retain_at_or_after_impl(&mut trackers, 480), 1);
        assert_eq!(active_starts(&trackers), BTreeSet::from([480]));
    }

    #[test]
    fn five_hundred_frame_state_residency_benchmark() {
        let cells = vec![cell(&[(0.5, 0.0), (0.5, 0.1)])];
        let mut trackers = Vec::new();
        let started = Instant::now();
        for hop in 1..=500 {
            let completion = hop * OBSERVATION_HOP_SAMPLES;
            let result = step(
                &cells,
                &mut trackers,
                completion,
                0.5,
                hop as f64 * 0.1,
                &[],
                1_000,
                10_000_000,
                64,
            );
            assert!(!result.3);
        }
        eprintln!(
            "500 native-resident proposal frames: {:?}, active trackers: {}",
            started.elapsed(),
            trackers.len()
        );
        assert_eq!(trackers.len(), 500);
    }
}
