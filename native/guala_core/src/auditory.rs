//! Native hot path for the causal sixteen-channel fourth-order gammatone field.
//!
//! Channel coefficients remain Python-owned and are passed in after the
//! production provider derives them.  The streaming entry point returns every
//! physical recurrence variable required to continue the next transport
//! chunk without resetting cochlear state.  The original stateless function
//! is retained as the zero-state compatibility entry point.

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const CHANNEL_COUNT: usize = 16;
const COCHLEAR_ORDER: usize = 4;
const OBSERVATION_HOP_SAMPLES: usize = 160;
const TWO_PI: f64 = 2.0 * std::f64::consts::PI;

type FieldArrays = (Vec<Vec<f64>>, Vec<Vec<f64>>, Vec<Vec<f64>>);
type StreamArrays = (
    Vec<Vec<f64>>,
    Vec<Vec<f64>>,
    Vec<Vec<f64>>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    usize,
);

fn validate_coefficients(pole_real: &[f64], pole_imag: &[f64], injection: &[f64]) -> PyResult<()> {
    if pole_real.len() != CHANNEL_COUNT
        || pole_imag.len() != CHANNEL_COUNT
        || injection.len() != CHANNEL_COUNT
    {
        return Err(PyValueError::new_err(
            "auditory gammatone requires exactly sixteen channel coefficients",
        ));
    }
    if pole_real
        .iter()
        .chain(pole_imag.iter())
        .chain(injection.iter())
        .any(|value| !value.is_finite())
    {
        return Err(PyValueError::new_err(
            "auditory gammatone coefficients must be finite",
        ));
    }
    Ok(())
}

fn validate_stream_state(
    state_real: &[f64],
    state_imag: &[f64],
    previous_real: &[f64],
    previous_imag: &[f64],
    phase_turns: &[f64],
    block_energy: &[f64],
    partial_hop_phase_turns: &[f64],
    partial_hop_samples: usize,
) -> PyResult<()> {
    let state_size = COCHLEAR_ORDER * CHANNEL_COUNT;
    if state_real.len() != state_size
        || state_imag.len() != state_size
        || previous_real.len() != CHANNEL_COUNT
        || previous_imag.len() != CHANNEL_COUNT
        || phase_turns.len() != CHANNEL_COUNT
        || block_energy.len() != CHANNEL_COUNT
        || partial_hop_phase_turns.len() != CHANNEL_COUNT
        || partial_hop_samples >= OBSERVATION_HOP_SAMPLES
    {
        return Err(PyValueError::new_err(
            "auditory gammatone continuation state changed shape",
        ));
    }
    if state_real
        .iter()
        .chain(state_imag.iter())
        .chain(previous_real.iter())
        .chain(previous_imag.iter())
        .chain(phase_turns.iter())
        .chain(block_energy.iter())
        .chain(partial_hop_phase_turns.iter())
        .any(|value| !value.is_finite())
    {
        return Err(PyValueError::new_err(
            "auditory gammatone continuation state is not finite",
        ));
    }
    if block_energy.iter().any(|value| *value < 0.0) {
        return Err(PyValueError::new_err(
            "auditory gammatone block energy is negative",
        ));
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn auditory_gammatone_stream_impl(
    signal: &[f64],
    pole_real: &[f64],
    pole_imag: &[f64],
    injection: &[f64],
    mut state_real: Vec<f64>,
    mut state_imag: Vec<f64>,
    mut previous_real: Vec<f64>,
    mut previous_imag: Vec<f64>,
    mut phase_turns: Vec<f64>,
    mut block_energy: Vec<f64>,
    mut partial_hop_phase_turns: Vec<f64>,
    mut partial_hop_samples: usize,
) -> Result<StreamArrays, &'static str> {
    let observation_count = (partial_hop_samples + signal.len()) / OBSERVATION_HOP_SAMPLES;
    let mut envelopes = vec![vec![0.0; CHANNEL_COUNT]; observation_count];
    let mut phases = vec![vec![0.0; CHANNEL_COUNT]; observation_count];
    let mut phase_advances = vec![vec![0.0; CHANNEL_COUNT]; observation_count];
    let mut stage_real = [0.0f64; CHANNEL_COUNT];
    let mut stage_imag = [0.0f64; CHANNEL_COUNT];
    let mut observation_index = 0usize;

    for &sample in signal {
        stage_real.fill(sample);
        stage_imag.fill(0.0);

        for order_index in 0..COCHLEAR_ORDER {
            let stage_offset = order_index * CHANNEL_COUNT;
            for channel_index in 0..CHANNEL_COUNT {
                let state_index = stage_offset + channel_index;
                let prior_real = state_real[state_index];
                let prior_imag = state_imag[state_index];
                let multiplied_real = pole_real[channel_index]
                    .mul_add(prior_real, -(pole_imag[channel_index] * prior_imag));
                let multiplied_imag = pole_real[channel_index]
                    .mul_add(prior_imag, pole_imag[channel_index] * prior_real);
                let next_real =
                    multiplied_real + injection[channel_index] * stage_real[channel_index];
                let next_imag =
                    multiplied_imag + injection[channel_index] * stage_imag[channel_index];
                state_real[state_index] = next_real;
                state_imag[state_index] = next_imag;
                stage_real[channel_index] = next_real;
                stage_imag[channel_index] = next_imag;
            }
        }

        let output_offset = (COCHLEAR_ORDER - 1) * CHANNEL_COUNT;
        for channel_index in 0..CHANNEL_COUNT {
            let output_real = state_real[output_offset + channel_index];
            let output_imag = state_imag[output_offset + channel_index];
            let prior_real = previous_real[channel_index];
            let prior_imag = previous_imag[channel_index];
            let output_magnitude = output_real.hypot(output_imag);
            let prior_magnitude = prior_real.hypot(prior_imag);
            if output_magnitude > 0.0 && prior_magnitude > 0.0 {
                let product_real = output_real.mul_add(prior_real, output_imag * prior_imag);
                let product_imag = output_real.mul_add(-prior_imag, output_imag * prior_real);
                let phase_delta = product_imag.atan2(product_real) / TWO_PI;
                phase_turns[channel_index] += phase_delta;
                partial_hop_phase_turns[channel_index] += phase_delta;
            } else if output_magnitude > 0.0 && prior_magnitude == 0.0 {
                phase_turns[channel_index] = output_imag.atan2(output_real) / TWO_PI;
            }
            previous_real[channel_index] = output_real;
            previous_imag[channel_index] = output_imag;
            block_energy[channel_index] += output_magnitude * output_magnitude;
        }

        partial_hop_samples += 1;
        if partial_hop_samples == OBSERVATION_HOP_SAMPLES {
            for channel_index in 0..CHANNEL_COUNT {
                let magnitude =
                    (block_energy[channel_index] / OBSERVATION_HOP_SAMPLES as f64).sqrt();
                if magnitude > 1.0 + 1e-12 {
                    return Err("cochlear pressure exceeded its analytic bound");
                }
                envelopes[observation_index][channel_index] = magnitude.min(1.0);
                phases[observation_index][channel_index] = phase_turns[channel_index];
                phase_advances[observation_index][channel_index] =
                    partial_hop_phase_turns[channel_index];
                block_energy[channel_index] = 0.0;
                partial_hop_phase_turns[channel_index] = 0.0;
            }
            observation_index += 1;
            partial_hop_samples = 0;
        }
    }

    Ok((
        envelopes,
        phases,
        phase_advances,
        state_real,
        state_imag,
        previous_real,
        previous_imag,
        phase_turns,
        block_energy,
        partial_hop_phase_turns,
        partial_hop_samples,
    ))
}

fn zero_stream_state() -> (
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
) {
    (
        vec![0.0; COCHLEAR_ORDER * CHANNEL_COUNT],
        vec![0.0; COCHLEAR_ORDER * CHANNEL_COUNT],
        vec![0.0; CHANNEL_COUNT],
        vec![0.0; CHANNEL_COUNT],
        vec![0.0; CHANNEL_COUNT],
        vec![0.0; CHANNEL_COUNT],
        vec![0.0; CHANNEL_COUNT],
    )
}

#[pyfunction]
fn auditory_gammatone_field(
    py: Python<'_>,
    signal: Vec<f64>,
    pole_real: Vec<f64>,
    pole_imag: Vec<f64>,
    injection: Vec<f64>,
) -> PyResult<FieldArrays> {
    validate_coefficients(&pole_real, &pole_imag, &injection)?;
    if signal.iter().any(|value| !value.is_finite()) {
        return Err(PyValueError::new_err(
            "auditory gammatone input must be finite",
        ));
    }
    let (state_real, state_imag, previous_real, previous_imag, phase, energy, partial_phase) =
        zero_stream_state();
    let result = py
        .allow_threads(|| {
            auditory_gammatone_stream_impl(
                &signal,
                &pole_real,
                &pole_imag,
                &injection,
                state_real,
                state_imag,
                previous_real,
                previous_imag,
                phase,
                energy,
                partial_phase,
                0,
            )
        })
        .map_err(PyRuntimeError::new_err)?;
    Ok((result.0, result.1, result.2))
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn auditory_gammatone_stream(
    py: Python<'_>,
    signal: Vec<f64>,
    pole_real: Vec<f64>,
    pole_imag: Vec<f64>,
    injection: Vec<f64>,
    state_real: Vec<f64>,
    state_imag: Vec<f64>,
    previous_real: Vec<f64>,
    previous_imag: Vec<f64>,
    phase_turns: Vec<f64>,
    block_energy: Vec<f64>,
    partial_hop_phase_turns: Vec<f64>,
    partial_hop_samples: usize,
) -> PyResult<StreamArrays> {
    validate_coefficients(&pole_real, &pole_imag, &injection)?;
    validate_stream_state(
        &state_real,
        &state_imag,
        &previous_real,
        &previous_imag,
        &phase_turns,
        &block_energy,
        &partial_hop_phase_turns,
        partial_hop_samples,
    )?;
    if signal.iter().any(|value| !value.is_finite()) {
        return Err(PyValueError::new_err(
            "auditory gammatone input must be finite",
        ));
    }
    py.allow_threads(|| {
        auditory_gammatone_stream_impl(
            &signal,
            &pole_real,
            &pole_imag,
            &injection,
            state_real,
            state_imag,
            previous_real,
            previous_imag,
            phase_turns,
            block_energy,
            partial_hop_phase_turns,
            partial_hop_samples,
        )
    })
    .map_err(PyRuntimeError::new_err)
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(auditory_gammatone_field, module)?)?;
    module.add_function(wrap_pyfunction!(auditory_gammatone_stream, module)?)?;
    Ok(())
}
