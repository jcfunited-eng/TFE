//! Native hot path for the causal sixteen-channel fourth-order gammatone field.
//!
//! Channel coefficients remain Python-owned and are passed in after the
//! production provider derives them.  This keeps the existing ERB topology and
//! coefficient rounding authoritative.  The loop below is an operation-ordered
//! port of `auditory_full_field_provider._cochlear_state_python`.

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const CHANNEL_COUNT: usize = 16;
const COCHLEAR_ORDER: usize = 4;
const OBSERVATION_HOP_SAMPLES: usize = 160;
const TWO_PI: f64 = 2.0 * std::f64::consts::PI;

type FieldArrays = (Vec<Vec<f64>>, Vec<Vec<f64>>);

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

fn auditory_gammatone_field_impl(
    signal: &[f64],
    pole_real: &[f64],
    pole_imag: &[f64],
    injection: &[f64],
) -> Result<FieldArrays, &'static str> {
    let observation_count = signal.len() / OBSERVATION_HOP_SAMPLES;
    let mut envelopes = vec![vec![0.0; CHANNEL_COUNT]; observation_count];
    let mut phases = vec![vec![0.0; CHANNEL_COUNT]; observation_count];

    let state_size = COCHLEAR_ORDER * CHANNEL_COUNT;
    let mut state_real = vec![0.0; state_size];
    let mut state_imag = vec![0.0; state_size];
    let mut previous_real = [0.0f64; CHANNEL_COUNT];
    let mut previous_imag = [0.0f64; CHANNEL_COUNT];
    let mut phase_turns = [0.0f64; CHANNEL_COUNT];
    let mut block_energy = [0.0f64; CHANNEL_COUNT];
    let mut stage_real = [0.0f64; CHANNEL_COUNT];
    let mut stage_imag = [0.0f64; CHANNEL_COUNT];
    let mut observation_index = 0usize;

    for (source_index, &sample) in signal.iter().enumerate() {
        stage_real.fill(sample);
        stage_imag.fill(0.0);

        for order_index in 0..COCHLEAR_ORDER {
            let stage_offset = order_index * CHANNEL_COUNT;
            for channel_index in 0..CHANNEL_COUNT {
                let state_index = stage_offset + channel_index;
                let prior_real = state_real[state_index];
                let prior_imag = state_imag[state_index];

                // Preserve Python's expression grouping:
                // pole * state + injection * stage_input. NumPy's complex128
                // loop uses FMA on the production x86_64 target; `mul_add`
                // makes that single rounding explicit instead of relying on
                // compiler contraction.
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
            let previous_channel_real = previous_real[channel_index];
            let previous_channel_imag = previous_imag[channel_index];
            let output_magnitude = output_real.hypot(output_imag);
            let previous_magnitude = previous_channel_real.hypot(previous_channel_imag);

            if output_magnitude > 0.0 && previous_magnitude > 0.0 {
                // Preserve NumPy complex128's multiply order, including the
                // signed-zero result once a decaying channel reaches the
                // subnormal range.
                let product_real =
                    output_real.mul_add(previous_channel_real, output_imag * previous_channel_imag);
                let product_imag = output_real
                    .mul_add(-previous_channel_imag, output_imag * previous_channel_real);
                phase_turns[channel_index] += product_imag.atan2(product_real) / TWO_PI;
            } else if output_magnitude > 0.0 && previous_magnitude == 0.0 {
                phase_turns[channel_index] = output_imag.atan2(output_real) / TWO_PI;
            }

            previous_real[channel_index] = output_real;
            previous_imag[channel_index] = output_imag;
            block_energy[channel_index] += output_magnitude * output_magnitude;
        }

        if (source_index + 1) % OBSERVATION_HOP_SAMPLES == 0 {
            for channel_index in 0..CHANNEL_COUNT {
                let magnitude =
                    (block_energy[channel_index] / OBSERVATION_HOP_SAMPLES as f64).sqrt();
                if magnitude > 1.0 + 1e-12 {
                    return Err("cochlear pressure exceeded its analytic bound");
                }
                envelopes[observation_index][channel_index] = magnitude.min(1.0);
                phases[observation_index][channel_index] = phase_turns[channel_index];
                block_energy[channel_index] = 0.0;
            }
            observation_index += 1;
        }
    }

    Ok((envelopes, phases))
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
    py.allow_threads(|| auditory_gammatone_field_impl(&signal, &pole_real, &pole_imag, &injection))
        .map_err(PyRuntimeError::new_err)
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(auditory_gammatone_field, module)?)?;
    Ok(())
}
