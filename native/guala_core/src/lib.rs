//! Native deterministic Guala boundaries.
//!
//! Guala's mounted cognitive path uses the exact joint-source carrier and the
//! corrected joint-field kernel. Historical per-port field interfaces remain
//! temporarily compiled only for the separate legacy sensory boundary while
//! its consumers are retired; they are not mounted neuronal authority.

use pyo3::prelude::*;

pub use hippocampal_sparse_path::{HippocampalColdObject, HippocampalColdPort};
pub use joint_source_episode::{decode_native_joint_source_episode, NativeJointSourceEpisode};
pub use physical_cognitive_capital::{
    CognitiveCapability, CognitiveCapitalDimension, CognitiveCapitalEvidence,
    CognitiveCapitalEvidenceKind, CognitiveCapitalObservation, COGNITIVE_CAPITAL_SCHEMA,
};
pub use resident_d3_runtime::{
    create_native_resident_d3_genesis, create_native_resident_d3_genesis_with_growth_dna,
    transition_native_resident_d3, transition_native_resident_d3_with_authored_admissions,
    NativeResidentD3Transition,
};

mod auditory;
mod auditory_reachability;
mod canonical_basin;
#[cfg(test)]
mod canonical_causal_evidence;
mod canonical_l0_l4;
mod complete_neuron;
mod content_defined_chunker;
mod declared_geometric_anatomy;
mod developmental_electrical_anatomy;
mod elementary_charge_membrane;
mod elementary_charge_transfer;
#[cfg(test)]
mod embryonic_neuron_genesis_candidate;
mod exact_rational;
#[cfg(test)]
mod exact_time_grid_occurrence;
#[path = "full_field_bank_final.rs"]
mod full_field_bank;
#[cfg(test)]
mod hippocampal_reference_page;
mod hippocampal_directory_cold_store;
mod hippocampal_sparse_path;
pub mod joint_field_l0_l4;
mod joint_source_episode;
mod joint_uf_neuron_boundary;
mod joint_uf_source_adapter;
mod joint_uf_v1_4;
#[cfg(test)]
mod joint_uf_v1_4_dynamic_fixture;
#[cfg(test)]
mod lattice_closed_membrane;
mod local_cupula_hair_bundle_geometry;
mod local_gating_spring_energy;
mod local_membrane_conductance_balance;
mod local_tip_link_extension;
mod materialized_fabric;
mod metabolic_feeding;
mod mounted_joint_fractal;
mod neuron_source_anchor;
mod optical_receptor_work;
#[cfg(test)]
mod ordered_gate_delivery_candidate;
pub mod organism;
mod organism_runtime;
mod physical_cognitive_capital;
mod physical_mosaic;
#[cfg(test)]
mod positional_krimelack_boundary;
mod reached_neuron_cohort;
mod reached_vestibular_bundle_path;
mod recovery_fluid_contact;
mod resident_cognitive_formation;
mod resident_d3_runtime;
mod resident_receptor_transition;
mod sha256;
mod sparse_electrical_contact;
mod vestibular_joint_source_builder;
mod vestibular_neuron_path;
mod virtual_body_yaw_motion;
mod virtual_material_neuron_genesis;
mod virtual_vestibular_canal;

#[pyfunction]
fn organism_state_structure_check(
    encoded: Vec<u8>,
    max_input_bytes: u64,
    max_heap_bytes: u64,
) -> PyResult<bool> {
    organism::decode_structure(
        &encoded,
        organism::DecodeBudget {
            max_input_bytes,
            max_heap_bytes,
        },
    )
    .map(|_| true)
    .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
}

#[pyfunction]
fn unverified_organism_state_receipt(
    encoded: Vec<u8>,
    max_input_bytes: u64,
    max_heap_bytes: u64,
) -> PyResult<Vec<u8>> {
    organism::decode_structure(
        &encoded,
        organism::DecodeBudget {
            max_input_bytes,
            max_heap_bytes,
        },
    )
    .map(|state| state.source_receipt().to_vec())
    .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
}

#[pymodule]
fn guala_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    auditory::register(module)?;
    auditory_reachability::register(module)?;
    canonical_basin::register(module)?;
    canonical_l0_l4::register(module)?;
    content_defined_chunker::register(module)?;
    full_field_bank::register(module)?;
    joint_source_episode::register(module)?;
    materialized_fabric::register(module)?;
    organism_runtime::register(module)?;
    resident_d3_runtime::register(module)?;
    module.add_function(wrap_pyfunction!(organism_state_structure_check, module)?)?;
    module.add_function(wrap_pyfunction!(unverified_organism_state_receipt, module)?)?;
    module.add("__version__", "0.1.0")?;
    Ok(())
}
