//! Explicit retirement of the false hippocampal delivery-address page.
//!
//! A sign-compressed DSF delivery impression is observation evidence only. It
//! is not a retained post-quiescence neuronal fractal and therefore cannot be
//! admitted as a hippocampal leaf, navigation target, memory, or recall cue.

use std::fmt;

pub(crate) const HIPPOCAMPAL_REFERENCE_PAGE_UNAVAILABLE: &str =
    "hippocampal indexing is unavailable until its leaves are exact sparse post-quiescence whole-neuron physical-state deltas";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct HippocampalReferencePageUnavailable;

impl fmt::Display for HippocampalReferencePageUnavailable {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        output.write_str(HIPPOCAMPAL_REFERENCE_PAGE_UNAVAILABLE)
    }
}

impl std::error::Error for HippocampalReferencePageUnavailable {}

pub(crate) fn refuse_delivery_impression_indexing(
) -> Result<(), HippocampalReferencePageUnavailable> {
    Err(HippocampalReferencePageUnavailable)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn delivery_impressions_cannot_become_hippocampal_memory() {
        assert_eq!(
            refuse_delivery_impression_indexing()
                .unwrap_err()
                .to_string(),
            HIPPOCAMPAL_REFERENCE_PAGE_UNAVAILABLE
        );
    }
}
