#![allow(dead_code)]

// This integration target compiles and executes only the narrow fixed-
// inventory and sensory-physics candidates. They are not registered in the
// production `guala_core` library. A candidate enters `src/lib.rs` only after
// whole-organism integration and release rehearsal.

#[path = "../src/bounded_physical_quanta.rs"]
mod bounded_physical_quanta;
#[path = "../src/elementary_charge_membrane.rs"]
mod elementary_charge_membrane;
#[path = "../src/elementary_charge_transfer.rs"]
mod elementary_charge_transfer;
#[path = "../src/exact_rational.rs"]
mod exact_rational;
#[path = "../src/finite_channel_ensemble.rs"]
mod finite_channel_ensemble;
#[path = "../src/local_cupula_hair_bundle_geometry.rs"]
mod local_cupula_hair_bundle_geometry;
#[path = "../src/local_gating_spring_energy.rs"]
mod local_gating_spring_energy;
#[path = "../src/local_membrane_conductance_balance.rs"]
mod local_membrane_conductance_balance;
#[path = "../src/local_tip_link_extension.rs"]
mod local_tip_link_extension;
#[path = "../src/localized_reaction_contacts.rs"]
mod localized_reaction_contacts;
#[path = "../src/reached_vestibular_bundle_path.rs"]
mod reached_vestibular_bundle_path;
#[path = "../src/vestibular_fluid_material.rs"]
mod vestibular_fluid_material;
#[path = "../src/virtual_body_yaw_motion.rs"]
mod virtual_body_yaw_motion;
#[path = "../src/virtual_body_yaw_occurrence.rs"]
mod virtual_body_yaw_occurrence;
#[path = "../src/virtual_vestibular_canal.rs"]
mod virtual_vestibular_canal;
