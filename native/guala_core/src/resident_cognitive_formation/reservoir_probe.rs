//! Measurement-only probe (test code, never compiled into production).
//!
//! Decodes persisted `CURRENT` generation envelopes (`*.glorun` bodies) and
//! dumps every cohort's recovery-fluid reservoir, per-lane recovery state,
//! dissipation ledgers, and DNA-expression state as JSON, so an external
//! driver can measure per-lesson fuel burn on the exact production physics.
//!
//! Driven via environment variables:
//!   GUALA_PROBE_IN  = directory containing envelope body files (sorted by name)
//!   GUALA_PROBE_OUT = output path for the JSON report
//! When GUALA_PROBE_IN is absent the test is a no-op (ordinary `cargo test`
//! runs are unaffected).

use super::ResidentCognitiveFormationState;
use crate::complete_neuron::RecoveryLaneAddress;
use crate::recovery_fluid_contact::ReachedRecoveryFluidAnatomy;
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;

const ENVELOPE_MAGIC: &[u8; 8] = b"GLORUN01";
const FABRIC_MAGIC: &[u8; 8] = b"GLMFAB07";
const IDENTITY_BYTES: usize = 36;

fn take<'a>(bytes: &'a [u8], cursor: &mut usize, count: usize) -> &'a [u8] {
    let slice = &bytes[*cursor..*cursor + count];
    *cursor += count;
    slice
}

fn take_u16(bytes: &[u8], cursor: &mut usize) -> u16 {
    u16::from_le_bytes(take(bytes, cursor, 2).try_into().unwrap())
}

fn take_u32(bytes: &[u8], cursor: &mut usize) -> u32 {
    u32::from_le_bytes(take(bytes, cursor, 4).try_into().unwrap())
}

fn take_u64(bytes: &[u8], cursor: &mut usize) -> u64 {
    u64::from_le_bytes(take(bytes, cursor, 8).try_into().unwrap())
}

/// Parses the raw envelope exactly as `organism_runtime::parse_current_envelope`
/// does (same magics, same layout) and returns (organism_tick, cognitive bytes).
pub(super) fn parse_envelope(bytes: &[u8]) -> (u64, Vec<u8>) {
    let mut cursor = 0usize;
    assert_eq!(take(bytes, &mut cursor, 8), ENVELOPE_MAGIC, "envelope magic");
    assert_eq!(take_u16(bytes, &mut cursor), 1, "envelope version");
    let _identity = take(bytes, &mut cursor, IDENTITY_BYTES);
    let organism_tick = take_u64(bytes, &mut cursor);
    let fabric_len = take_u32(bytes, &mut cursor) as usize;
    let fabric = take(bytes, &mut cursor, fabric_len);
    assert_eq!(cursor, bytes.len(), "envelope trailing bytes");

    let mut fc = 0usize;
    assert_eq!(take(fabric, &mut fc, 8), FABRIC_MAGIC, "fabric magic");
    assert_eq!(take_u16(fabric, &mut fc), 7, "fabric version");
    let _generation = take_u64(fabric, &mut fc);
    let joint_len = take_u32(fabric, &mut fc) as usize;
    let cognitive_len = take_u32(fabric, &mut fc) as usize;
    let _joint = take(fabric, &mut fc, joint_len);
    let cognitive = take(fabric, &mut fc, cognitive_len).to_vec();
    assert_eq!(fc, fabric.len(), "fabric trailing bytes");
    (organism_tick, cognitive)
}

#[derive(Default)]
struct LaneTotals {
    fuel: u128,
    spent: u128,
    heat: u128,
    fuel_capacity: u128,
    min_neuron_fuel: Option<u128>,
    max_neuron_fuel: Option<u128>,
}

impl LaneTotals {
    fn add(&mut self, fuel: u128, spent: u128, heat: u128, fuel_capacity: u128) {
        self.fuel += fuel;
        self.spent += spent;
        self.heat += heat;
        self.fuel_capacity += fuel_capacity;
        self.min_neuron_fuel = Some(self.min_neuron_fuel.map_or(fuel, |m| m.min(fuel)));
        self.max_neuron_fuel = Some(self.max_neuron_fuel.map_or(fuel, |m| m.max(fuel)));
    }

    fn to_json(&self) -> Value {
        json!({
            "fuel": self.fuel.to_string(),
            "spent": self.spent.to_string(),
            "heat": self.heat.to_string(),
            "fuel_capacity": self.fuel_capacity.to_string(),
            "min_neuron_fuel": self.min_neuron_fuel.map(|v| v.to_string()),
            "max_neuron_fuel": self.max_neuron_fuel.map(|v| v.to_string()),
        })
    }
}

fn cohort_json(cohort: &super::ResidentReachedCohort) -> Value {
    let anatomies = cohort.anatomy.neuron_anatomies();
    let fluid_anatomy =
        ReachedRecoveryFluidAnatomy::derive(anatomies).expect("derive fluid anatomy");
    let (fuel_capacity, spent_capacity, heat_capacity) =
        fluid_anatomy.reservoir_anatomy().capacities();
    let (fuel, spent, heat) = cohort.state.recovery_fluid().physical_parts();

    let mut psi = LaneTotals::default();
    let mut gate = LaneTotals::default();
    let mut plastic = LaneTotals::default();
    let mut psi_dissipated = 0u128;
    let mut psi_dissipation_capacity = 0u128;
    let mut gate_dissipated = 0u128;
    let mut gate_dissipation_capacity = 0u128;
    let mut plastic_dissipated = 0u128;
    let mut plastic_dissipation_capacity = 0u128;
    let mut dna_substrate = 0u128;
    let mut dna_fuel = 0u128;
    let mut dna_product = 0u128;
    let mut dna_waste = 0u128;

    let mut gate_open_population = 0u128;
    let mut neurons_with_open_gates = 0usize;
    let mut neurons_with_nonzero_residue = 0usize;
    let mut residues: Vec<String> = Vec::new();
    for (anatomy, state) in anatomies.iter().zip(cohort.state.neurons().iter()) {
        gate_open_population += state.gate.open_population();
        if state.gate.open_population() != 0 {
            neurons_with_open_gates += 1;
        }
        let (residue_numerator, residue_denominator) = state.optical_quantum_residue.parts();
        if residue_numerator != 0 {
            neurons_with_nonzero_residue += 1;
        }
        residues.push(format!("{residue_numerator}/{residue_denominator}"));
        let _ = anatomy;
    }
    for (anatomy, state) in anatomies.iter().zip(cohort.state.neurons().iter()) {
        for index in 0..anatomy.psi_ring_count() {
            let address = RecoveryLaneAddress::Psi(index);
            let lane_state = state.recovery.lane(address).expect("psi lane state");
            let lane_anatomy = anatomy
                .recovery_anatomy()
                .lane(address)
                .expect("psi lane anatomy");
            let (lane_fuel, lane_spent, lane_heat) = lane_state.physical_parts();
            // Aggregate psi lanes per neuron; min/max here is per-lane.
            psi.add(lane_fuel, lane_spent, lane_heat, lane_anatomy.capacities().0);
            psi_dissipation_capacity += anatomy
                .probe_psi_ring_dissipation_capacity_quanta(index)
                .expect("psi ring capacity");
        }
        for ring in state.psi.rings() {
            psi_dissipated += ring.dissipated_quanta();
        }
        {
            let lane_state = state
                .recovery
                .lane(RecoveryLaneAddress::Gate)
                .expect("gate lane state");
            let lane_anatomy = anatomy
                .recovery_anatomy()
                .lane(RecoveryLaneAddress::Gate)
                .expect("gate lane anatomy");
            let (lane_fuel, lane_spent, lane_heat) = lane_state.physical_parts();
            gate.add(lane_fuel, lane_spent, lane_heat, lane_anatomy.capacities().0);
            gate_dissipated += state.gate.dissipated_quanta();
            gate_dissipation_capacity += anatomy.gate_dissipation_capacity_quanta();
        }
        {
            let lane_state = state
                .recovery
                .lane(RecoveryLaneAddress::Plastic)
                .expect("plastic lane state");
            let lane_anatomy = anatomy
                .recovery_anatomy()
                .lane(RecoveryLaneAddress::Plastic)
                .expect("plastic lane anatomy");
            let (lane_fuel, lane_spent, lane_heat) = lane_state.physical_parts();
            plastic.add(lane_fuel, lane_spent, lane_heat, lane_anatomy.capacities().0);
            plastic_dissipated += state.plastic.probe_dissipated_quanta();
            plastic_dissipation_capacity += anatomy.probe_plastic_dissipation_capacity_quanta();
        }
        let (substrate, dna_lane_fuel, product, waste) = state.dna_expression.probe_parts();
        dna_substrate += substrate;
        dna_fuel += dna_lane_fuel;
        dna_product += product;
        dna_waste += waste;
    }

    // Law 2 diagnosis (measurement only): the exact separated membrane charge
    // of every neuron and the retained sub-charge phase of every authored
    // chain contact, so an external driver can see whether inter-neuron
    // settlement is still moving WHOLE elementary charges or only carrying
    // sub-charge phase.
    let membrane_separated_elementary_charges = cohort
        .state
        .neurons()
        .iter()
        .map(|state| {
            state
                .membrane_state()
                .separated_elementary_charges()
                .to_string()
        })
        .collect::<Vec<String>>();
    let contact_carrier_phases = cohort
        .state
        .electrical()
        .contact_states()
        .iter()
        .map(|contact| {
            let (numerator, denominator) = contact.carrier_phase().parts();
            format!("{numerator}/{denominator}")
        })
        .collect::<Vec<String>>();

    // Experience-evidence detail (measurement only): the OR-masks the
    // retention law actually persisted, so an external driver can see per
    // hop when the retained original appeared and whether it carries any
    // electrical participation.
    fn experience_json(evidence: Option<&super::ResidentExperienceEvidence>) -> Value {
        match evidence {
            None => json!(null),
            Some(evidence) => {
                let gate_work_count = evidence
                    .gate_work_perturbed_neurons
                    .iter()
                    .filter(|bit| **bit)
                    .count();
                let active_contact_count = evidence
                    .active_electrical_contacts
                    .iter()
                    .filter(|bit| **bit)
                    .count();
                let member_delta_count = evidence.post_experience_rest.as_ref().map(|post| {
                    evidence
                        .pre_experience_rest
                        .neurons()
                        .iter()
                        .zip(post.neurons())
                        .filter(|(pre, post)| pre != post)
                        .count()
                });
                json!({
                    "gate_work_perturbed_count": gate_work_count,
                    "active_electrical_contact_count": active_contact_count,
                    "post_experience_rest": evidence.post_experience_rest.is_some(),
                    "member_delta_count": member_delta_count,
                })
            }
        }
    }
    let pending_experience_detail = experience_json(cohort.pending_experience.as_ref());
    let retained_experience_detail = experience_json(cohort.retained_experience.as_ref());
    let pending_recurrence_detail = match cohort.pending_recurrence.as_ref() {
        None => json!(null),
        Some(evidence) => json!({
            "gate_work_perturbed_count": evidence
                .gate_work_perturbed_neurons
                .iter()
                .filter(|bit| **bit)
                .count(),
            "active_recurrence_contact_count": evidence
                .active_recurrence_contacts
                .iter()
                .filter(|bit| **bit)
                .count(),
        }),
    };

    // Recognition verdict (measurement only): replay EXACTLY the admission
    // decision `settle_resident_recurrence_interval` makes — same retained
    // experience, same learned state, same current cohort state, same
    // recurrence bits — and report the physics' own refusal variant instead
    // of inferring one.
    let recognition = match (
        cohort.retained_experience.as_ref(),
        cohort
            .retained_experience
            .as_ref()
            .and_then(|retained| retained.post_experience_rest.as_ref()),
    ) {
        (Some(retained), Some(learned)) => {
            let recurrence = cohort.pending_recurrence.as_ref();
            let original = super::original_settlement(&cohort.anatomy, retained, learned)
                .expect("original settlement");
            let actual = super::recurrence_settlement(
                &cohort.anatomy,
                learned,
                cohort.state.clone(),
                recurrence.map_or_else(
                    || vec![false; cohort.anatomy.neuron_count()].into_boxed_slice(),
                    |evidence| evidence.gate_work_perturbed_neurons.clone(),
                ),
                recurrence.map_or_else(
                    || vec![false; cohort.anatomy.contact_count()].into_boxed_slice(),
                    |evidence| evidence.active_recurrence_contacts.clone(),
                ),
            )
            .expect("recurrence settlement");
            let verdict = match crate::physical_mosaic::admit_physical_mosaic(
                &cohort.anatomy,
                &original,
                &actual,
            ) {
                Ok(_) => "admitted".to_string(),
                Err(error) => format!("{error:?}"),
            };
            json!({
                "retained_experience": true,
                "pending_recurrence": recurrence.is_some(),
                "pending_experience": cohort.pending_experience.is_some(),
                "verdict": verdict,
            })
        }
        _ => json!({
            "retained_experience": cohort.retained_experience.is_some(),
            "pending_recurrence": cohort.pending_recurrence.is_some(),
            "pending_experience": cohort.pending_experience.is_some(),
            "verdict": "no retained experience",
        }),
    };

    json!({
        "neuron_count": cohort.anatomy.neuron_count(),
        "recognition": recognition,
        "pending_experience_detail": pending_experience_detail,
        "retained_experience_detail": retained_experience_detail,
        "pending_recurrence_detail": pending_recurrence_detail,
        "membrane_separated_elementary_charges": membrane_separated_elementary_charges,
        "contact_carrier_phases": contact_carrier_phases,
        "gate_state": {
            "total_open_population": gate_open_population.to_string(),
            "neurons_with_open_gates": neurons_with_open_gates,
        },
        "optical_quantum_residues": {
            "neurons_with_nonzero_residue": neurons_with_nonzero_residue,
            "residues_zeptojoules": residues,
        },
        "reservoir": {
            "fuel_quanta": fuel.to_string(),
            "spent_quanta": spent.to_string(),
            "heat_quanta": heat.to_string(),
            "fuel_capacity": fuel_capacity.to_string(),
            "spent_capacity": spent_capacity.to_string(),
            "heat_capacity": heat_capacity.to_string(),
        },
        "lanes": {
            "psi": psi.to_json(),
            "gate": gate.to_json(),
            "plastic": plastic.to_json(),
        },
        "dissipation": {
            "psi_dissipated": psi_dissipated.to_string(),
            "psi_capacity": psi_dissipation_capacity.to_string(),
            "gate_dissipated": gate_dissipated.to_string(),
            "gate_capacity": gate_dissipation_capacity.to_string(),
            "plastic_dissipated": plastic_dissipated.to_string(),
            "plastic_capacity": plastic_dissipation_capacity.to_string(),
        },
        "dna_expression": {
            "substrate_quanta": dna_substrate.to_string(),
            "fuel_quanta": dna_fuel.to_string(),
            "expressed_product_quanta": dna_product.to_string(),
            "waste_quanta": dna_waste.to_string(),
        },
    })
}

#[test]
fn reservoir_probe_dump() {
    let Ok(input) = std::env::var("GUALA_PROBE_IN") else {
        return;
    };
    let out_path = std::env::var("GUALA_PROBE_OUT").expect("GUALA_PROBE_OUT must be set");
    let mut entries: Vec<PathBuf> = fs::read_dir(&input)
        .expect("read probe input directory")
        .map(|entry| entry.expect("dir entry").path())
        .filter(|path| path.extension().map_or(false, |ext| ext == "glorun"))
        .collect();
    entries.sort();
    let mut records = Vec::new();
    for path in &entries {
        let bytes = fs::read(path).expect("read envelope");
        let (organism_tick, cognitive) = parse_envelope(&bytes);
        let record = if cognitive.is_empty() {
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "cognitive": "absent",
                "cohorts": [],
            })
        } else {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state");
            let cohorts: Vec<Value> = state.cohorts.iter().map(cohort_json).collect();
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "generation": state.generation,
                "unexpressed_electrical_seed_count": state.unexpressed_electrical_seeds.len(),
                "dormant_lineage_seed_count": state.dormant_lineage_seeds.len(),
                "cohorts": cohorts,
            })
        };
        records.push(record);
    }
    fs::write(
        &out_path,
        serde_json::to_string_pretty(&json!({ "records": records })).expect("serialize"),
    )
    .expect("write probe output");
}
