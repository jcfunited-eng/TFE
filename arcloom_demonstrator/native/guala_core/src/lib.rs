//! guala_core -- Minimal Standalone PyO3 Entry Point for ArcLoom Cortical Substrate
//! Shipped with arcloom_demonstrator v1.0.

use pyo3::prelude::*;

pub mod cortical_column;

#[pymodule]
fn guala_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    cortical_column::register(m)?;
    Ok(())
}
