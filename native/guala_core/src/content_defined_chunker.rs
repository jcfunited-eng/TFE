//! Streaming native implementation of the immutable-generation content
//! chunk boundary operator.
//!
//! This is an exact port of
//! `ImmutableGenerationStore._iter_content_defined_chunks`: the gear table,
//! unsigned 64-bit wrapping arithmetic, minimum boundary, mask, maximum
//! boundary, and boundary reset are unchanged.  Input is deliberately capped
//! at the Python store's one-MiB source block so neither one call nor the
//! returned completed-block collection can grow without a fixed bound.

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

const SOURCE_BLOCK_BYTES: usize = 1024 * 1024;
const CHUNK_MIN_BYTES: usize = 1024 * 1024;
const CHUNK_TARGET_BYTES: usize = 4 * 1024 * 1024;
const CHUNK_MAX_BYTES: usize = 8 * 1024 * 1024;
const CHUNK_MASK: u64 = (CHUNK_TARGET_BYTES - 1) as u64;

fn gear_table() -> &'static [u64; 256] {
    static TABLE: OnceLock<[u64; 256]> = OnceLock::new();
    TABLE.get_or_init(|| {
        let mut table = [0_u64; 256];
        for (value, slot) in table.iter_mut().enumerate() {
            let mut digest = Sha256::new();
            digest.update(b"guala-content-defined-chunk-v1:");
            digest.update([value as u8]);
            let bytes = digest.finalize();
            *slot = u64::from_be_bytes(bytes[..8].try_into().expect("eight-byte prefix"));
        }
        table
    })
}

#[pyclass(module = "guala_core")]
pub(crate) struct ImmutableGenerationContentChunker {
    pending: Vec<u8>,
    gear: u64,
    finished: bool,
}

#[pymethods]
impl ImmutableGenerationContentChunker {
    #[new]
    fn new() -> Self {
        Self {
            pending: Vec::new(),
            gear: 0,
            finished: false,
        }
    }

    /// Consume exactly one bounded source block and return completed chunks.
    fn feed<'py>(&mut self, py: Python<'py>, block: Vec<u8>) -> PyResult<Vec<Bound<'py, PyBytes>>> {
        if self.finished {
            return Err(PyRuntimeError::new_err(
                "immutable-generation content chunker is already finished",
            ));
        }
        if block.len() > SOURCE_BLOCK_BYTES {
            return Err(PyValueError::new_err(format!(
                "immutable-generation source block exceeds {SOURCE_BLOCK_BYTES} bytes"
            )));
        }

        let completed = py.allow_threads(|| {
            let mut completed: Vec<Vec<u8>> = Vec::with_capacity(2);
            for byte in block {
                self.pending.push(byte);
                self.gear = self
                    .gear
                    .wrapping_shl(1)
                    .wrapping_add(gear_table()[byte as usize]);
                let length = self.pending.len();
                if length >= CHUNK_MIN_BYTES
                    && ((self.gear & CHUNK_MASK) == 0 || length >= CHUNK_MAX_BYTES)
                {
                    completed.push(std::mem::take(&mut self.pending));
                    self.gear = 0;
                }
            }
            completed
        });
        Ok(completed
            .iter()
            .map(|body| PyBytes::new(py, body))
            .collect())
    }

    /// Seal the stream and return its final short chunk, if one exists.
    fn finish<'py>(&mut self, py: Python<'py>) -> PyResult<Option<Bound<'py, PyBytes>>> {
        if self.finished {
            return Err(PyRuntimeError::new_err(
                "immutable-generation content chunker is already finished",
            ));
        }
        self.finished = true;
        if self.pending.is_empty() {
            return Ok(None);
        }
        self.gear = 0;
        let final_chunk = std::mem::take(&mut self.pending);
        Ok(Some(PyBytes::new(py, &final_chunk)))
    }

    #[getter]
    fn pending_bytes(&self) -> usize {
        self.pending.len()
    }

    #[getter]
    fn maximum_pending_bytes(&self) -> usize {
        CHUNK_MAX_BYTES
    }

    #[getter]
    fn maximum_source_block_bytes(&self) -> usize {
        SOURCE_BLOCK_BYTES
    }
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<ImmutableGenerationContentChunker>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gear_table_is_the_sha256_big_endian_table() {
        for value in 0_u16..=255 {
            let mut digest = Sha256::new();
            digest.update(b"guala-content-defined-chunk-v1:");
            digest.update([value as u8]);
            let bytes = digest.finalize();
            assert_eq!(
                gear_table()[value as usize],
                u64::from_be_bytes(bytes[..8].try_into().unwrap())
            );
        }
    }
}
