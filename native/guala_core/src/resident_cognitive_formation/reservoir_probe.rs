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

use super::{MotorUnitRecruitment, ResidentCognitiveFormationState};
use crate::articulated_body_joint_source_builder::{
    admit_articulated_body_consequence_source, exact_moved_effector_terminal,
};
use crate::auditory::{auditory_gammatone_stream_impl, zero_stream_state};
use crate::complete_neuron::RecoveryLaneAddress;
use crate::exact_rational::ExactRational;
use crate::joint_source_episode::decode_native_joint_source_episode;
use crate::joint_uf_source_adapter::admitted_episode_with_authored_intervals;
use crate::recovery_fluid_contact::ReachedRecoveryFluidAnatomy;
use crate::vestibular_neuron_path::FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES;
use crate::virtual_articulated_body::{
    settle_body_effector_drives, AdmittedBodyEffectorDrives, ArticulatedBodyState, BodyAxis,
    BodyEffectorDirection, BodyEffectorDrive, BodyEffectorTerminal, ARTICULATED_BODY_STATE_BYTES,
    BODY_AXES, BODY_SETTLEMENT_CLOCK_MICROSECONDS,
};
use crate::virtual_articulatory_body::settle_native_articulatory_interval;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{ToPrimitive, Zero};
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;

#[path = "memory_retention_probe.rs"]
mod memory_retention_probe;

const ENVELOPE_MAGIC: &[u8; 8] = b"GLORUN01";
const PRE_VESTIBULAR_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB07";
const PRE_ARTICULATED_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB08";
const PRE_PHONATORY_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB09";
const PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB10";
const CURRENT_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB11";
const CANAL_STATE_BYTES: usize = 32;
const IDENTITY_BYTES: usize = 36;
const PROBE_COCHLEAR_CHANNELS_PER_EAR: usize = 16;
const PROBE_EAR_COUNT: usize = 2;
const PROBE_LEGACY_EAR_PORT_COUNT: usize = 2;
const PROBE_COCHLEAR_HOP_SAMPLES: usize = 160;
const PROBE_ACOUSTIC_SAMPLE_RATE_HZ: usize = 16_000;
const PROBE_COCHLEAR_PRESSURE_LATTICE: f64 = 16_777_216.0;
const PROBE_INTERSAMPLE_PROFILE: &[u8] =
    b"guala.uf.v1.4.sampled_volume_and_relevance_piecewise_linear.v1";

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
/// does (same magics, same layout) and returns the organism tick, cognitive
/// bytes, and exact articulated body when that body exists in the fabric.
fn parse_envelope_with_body(bytes: &[u8]) -> (u64, Vec<u8>, Option<ArticulatedBodyState>) {
    let mut cursor = 0usize;
    assert_eq!(
        take(bytes, &mut cursor, 8),
        ENVELOPE_MAGIC,
        "envelope magic"
    );
    assert_eq!(take_u16(bytes, &mut cursor), 1, "envelope version");
    let _identity = take(bytes, &mut cursor, IDENTITY_BYTES);
    let organism_tick = take_u64(bytes, &mut cursor);
    let fabric_len = take_u32(bytes, &mut cursor) as usize;
    let fabric = take(bytes, &mut cursor, fabric_len);
    assert_eq!(cursor, bytes.len(), "envelope trailing bytes");

    let mut fc = 0usize;
    let fabric_magic = take(fabric, &mut fc, 8);
    assert!(
        fabric_magic == PRE_VESTIBULAR_FABRIC_MAGIC
            || fabric_magic == PRE_ARTICULATED_FABRIC_MAGIC
            || fabric_magic == PRE_PHONATORY_FABRIC_MAGIC
            || fabric_magic == PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC
            || fabric_magic == CURRENT_FABRIC_MAGIC,
        "fabric magic"
    );
    let fabric_version = take_u16(fabric, &mut fc);
    assert_eq!(
        fabric_version,
        if fabric_magic == CURRENT_FABRIC_MAGIC {
            11
        } else if fabric_magic == PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC {
            10
        } else if fabric_magic == PRE_PHONATORY_FABRIC_MAGIC {
            9
        } else if fabric_magic == PRE_ARTICULATED_FABRIC_MAGIC {
            8
        } else {
            7
        },
        "fabric version"
    );
    let _generation = take_u64(fabric, &mut fc);
    let joint_len = take_u32(fabric, &mut fc) as usize;
    let cognitive_len = take_u32(fabric, &mut fc) as usize;
    if fabric_magic == CURRENT_FABRIC_MAGIC
        || fabric_magic == PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC
        || fabric_magic == PRE_PHONATORY_FABRIC_MAGIC
        || fabric_magic == PRE_ARTICULATED_FABRIC_MAGIC
    {
        let _vestibular_anatomy = take(fabric, &mut fc, FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES);
        let _canal_state = take(fabric, &mut fc, CANAL_STATE_BYTES);
        let _vestibular_source_tick = take_u64(fabric, &mut fc);
    }
    let mut articulated_body = None;
    if fabric_magic == CURRENT_FABRIC_MAGIC
        || fabric_magic == PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC
        || fabric_magic == PRE_PHONATORY_FABRIC_MAGIC
    {
        let body_bytes = if fabric_magic == PRE_PHONATORY_FABRIC_MAGIC {
            ARTICULATED_BODY_STATE_BYTES
        } else {
            ArticulatedBodyState::encoded_length_from_prefix(&fabric[fc..])
                .expect("articulated body prefix")
        };
        let body = take(fabric, &mut fc, body_bytes);
        articulated_body = Some(ArticulatedBodyState::decode(body).expect("articulated body"));
    }
    if fabric_magic == CURRENT_FABRIC_MAGIC {
        let acoustic_len = take_u32(fabric, &mut fc) as usize;
        let _in_flight_acoustic = take(fabric, &mut fc, acoustic_len);
    }
    let _joint = take(fabric, &mut fc, joint_len);
    let cognitive = take(fabric, &mut fc, cognitive_len).to_vec();
    assert_eq!(fc, fabric.len(), "fabric trailing bytes");
    (organism_tick, cognitive, articulated_body)
}

pub(super) fn parse_envelope(bytes: &[u8]) -> (u64, Vec<u8>) {
    let (organism_tick, cognitive, _) = parse_envelope_with_body(bytes);
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
    let mounts = cohort
        .anatomy
        .mounts()
        .iter()
        .zip(cohort.anatomy.neuron_lineages())
        .zip(anatomies)
        .zip(cohort.state.neurons())
        .map(|(((mount, lineage), anatomy), state)| {
            let capacitance = anatomy.capacitance().picofarads();
            let potential = state
                .membrane_state()
                .potential_millivolts(anatomy.capacitance())
                .expect("probe membrane potential");
            let psi_winding_counts =
                state
                    .psi
                    .rings()
                    .iter()
                    .fold([0_u64; 3], |mut counts, ring| {
                        counts[usize::from((ring.winding() as i8 + 1) as u8)] += 1;
                        counts
                    });
            json!({
                "lineage": lineage
                    .iter()
                    .map(|byte| format!("{byte:02x}"))
                    .collect::<String>(),
                "layer": mount.place().layer(),
                "topology_index": mount.place().topology_index(),
                "source_site": mount.source_site().map(|site| format!("{:?}", site)),
                "gate_population": anatomy.gate_population().to_string(),
                "open_gate_population": state.gate.open_population().to_string(),
                "gate_dissipated_quanta": state.gate.dissipated_quanta().to_string(),
                "gate_dissipation_capacity_quanta":
                    anatomy.gate_dissipation_capacity_quanta().to_string(),
                "intracellular_carriers": state.carrier_reservoirs().intracellular().to_string(),
                "extracellular_carriers": state.carrier_reservoirs().extracellular().to_string(),
                "psi_winding_counts": {
                    "negative": psi_winding_counts[0],
                    "quiescent": psi_winding_counts[1],
                    "positive": psi_winding_counts[2],
                },
                "capacitance_picofarads": exact_json(capacitance),
                "membrane_potential_millivolts": exact_json(potential),
                "gate_reversal_potential_millivolts": exact_json(
                    anatomy.gate_reversal_potential_millivolts(),
                ),
            })
        })
        .collect::<Vec<_>>();
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
    let mut neurons_owing_return_work = 0usize;
    let mut return_work_residues: Vec<String> = Vec::new();
    for (anatomy, state) in anatomies.iter().zip(cohort.state.neurons().iter()) {
        gate_open_population += state.gate.open_population();
        if state.gate.open_population() != 0 {
            neurons_with_open_gates += 1;
        }
        let residue = state.receptor_quantum_residue.energy();
        if !residue.is_zero() {
            neurons_with_nonzero_residue += 1;
        }
        residues.push(format!("{}/{}", residue.numer(), residue.denom()));
        let (owed_numerator, owed_denominator) = state.membrane_return_work_residue.parts();
        if owed_numerator != 0 {
            neurons_owing_return_work += 1;
        }
        return_work_residues.push(format!("{owed_numerator}/{owed_denominator}"));
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
            psi.add(
                lane_fuel,
                lane_spent,
                lane_heat,
                lane_anatomy.capacities().0,
            );
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
            gate.add(
                lane_fuel,
                lane_spent,
                lane_heat,
                lane_anatomy.capacities().0,
            );
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
            plastic.add(
                lane_fuel,
                lane_spent,
                lane_heat,
                lane_anatomy.capacities().0,
            );
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

    // Experience-evidence detail (measurement only): the sparse resident
    // indices the retention law actually persisted, so an external driver can see per
    // hop when the retained original appeared and whether it carries any
    // electrical participation.
    fn experience_json(evidence: Option<&super::ResidentExperienceEvidence>) -> Value {
        match evidence {
            None => json!(null),
            Some(evidence) => {
                let gate_work_count = evidence.gate_work_perturbed_neurons.count();
                let active_contact_count = evidence.active_electrical_contacts.count();
                let member_delta_count = evidence.retained_members().map(<[_]>::len);
                json!({
                    "gate_work_perturbed_count": gate_work_count,
                    "active_electrical_contact_count": active_contact_count,
                    "post_experience_rest": evidence.is_retained(),
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
                .count(),
            "active_recurrence_contact_count": evidence
                .active_recurrence_contacts
                .count(),
        }),
    };

    let dark_rest_fuel_split = json!({
        "available": false,
        "reason": "retired mixed-unit authored feed; powered exact-energy contact not yet mounted"
    });

    // Recognition verdict (measurement only): replay EXACTLY the admission
    // decision `settle_resident_recurrence_interval` makes — same retained
    // experience, same learned state, same current cohort state, same
    // recurrence bits — and report the physics' own refusal variant instead
    // of inferring one.
    let recognition = match cohort.retained_experience.as_ref() {
        Some(retained) => {
            let recurrence = cohort.pending_recurrence.as_ref();
            let original =
                super::original_settlement(&cohort.anatomy, retained).expect("original settlement");
            let actual = super::recurrence_settlement(
                &cohort.anatomy,
                retained,
                &[],
                cohort.state.as_ref().clone(),
                recurrence.map_or_else(
                    || vec![None; cohort.anatomy.neuron_count()].into_boxed_slice(),
                    |evidence| {
                        evidence
                            .receptor_excitation_zeptojoules
                            .to_dense(cohort.anatomy.neuron_count())
                            .expect("canonical recurrence excitation indices")
                    },
                ),
                recurrence.map_or_else(
                    || vec![false; cohort.anatomy.neuron_count()].into_boxed_slice(),
                    |evidence| {
                        evidence
                            .gate_work_perturbed_neurons
                            .to_dense(cohort.anatomy.neuron_count())
                            .expect("canonical recurrence gate-work indices")
                    },
                ),
                recurrence.map_or_else(
                    || vec![false; cohort.anatomy.contact_count()].into_boxed_slice(),
                    |evidence| {
                        evidence
                            .active_recurrence_contacts
                            .to_dense(cohort.anatomy.contact_count())
                            .expect("canonical recurrence contact indices")
                    },
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
        None => json!({
            "retained_experience": cohort.retained_experience.is_some(),
            "pending_recurrence": cohort.pending_recurrence.is_some(),
            "pending_experience": cohort.pending_experience.is_some(),
            "verdict": "no retained experience",
        }),
    };

    json!({
        "neuron_count": cohort.anatomy.neuron_count(),
        "mounts": mounts,
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
        "receptor_quantum_residues": {
            "neurons_with_nonzero_residue": neurons_with_nonzero_residue,
            "residues_zeptojoules": residues,
        },
        // The sub-quantum membrane-return work each neuron has done and not
        // yet been billed a whole dissipation quantum for (exact rest-cost
        // law, 2026-08-06).  Bounded by the gate's own dissipation quantum.
        "membrane_return_work_residues": {
            "neurons_owing_return_work": neurons_owing_return_work,
            "owed_zeptojoules": return_work_residues,
        },
        "reservoir": {
            "available_energy_zeptojoules": exact_json(fuel),
            "spent_energy_zeptojoules": exact_json(spent),
            "thermal_energy_zeptojoules": exact_json(heat),
            "available_energy_capacity_zeptojoules": exact_json(fuel_capacity),
            "spent_energy_capacity_zeptojoules": exact_json(spent_capacity),
            "thermal_energy_capacity_zeptojoules": exact_json(heat_capacity),
        },
        "measured_fed_dark_rest_fuel_split": dark_rest_fuel_split,
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

fn exact_json(value: ExactRational) -> Value {
    let (numerator, denominator) = value.parts();
    json!({
        "numerator": numerator.to_string(),
        "denominator": denominator.to_string(),
    })
}

fn wide_exact_json(value: &BigRational) -> Value {
    json!({
        "numerator": value.numer().to_string(),
        "denominator": value.denom().to_string(),
    })
}

/// Measurement-only lower-bound model for the articulated body's missing
/// passive tissue.  This is deliberately not a production implementation:
/// it asks which exact, elapsed-time laws can release the copied body's
/// stopped axes without overshoot, and where repeated motor work overwhelms
/// that return.  One native mechanical step is one millisecond.  Backward
/// Euler is used because each step is an exact convex combination of the
/// current position and the anatomical neutral; it cannot manufacture an
/// overshoot.  Motor carriers remain explicit signed lattice displacements.
fn copied_body_passive_mechanics_range_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let time_constants_ms = [1_i64, 2, 4, 8, 16, 32, 64, 128, 256, 512];
    let observation_durations_ms = [1_u64, 4, 16, 64, 250, 1_000];
    let sustained_carriers_per_ms = [1_i64, 2, 4, 8, 16];
    let powers = |tau_ms: i64, elapsed_ms: u64| {
        let exponent = u32::try_from(elapsed_ms).expect("bounded harness duration");
        (
            BigInt::from(tau_ms).pow(exponent),
            BigInt::from(tau_ms + 1).pow(exponent),
        )
    };
    let exact_position_json =
        |position: i32, neutral: i32, decay_numerator: &BigInt, decay_denominator: &BigInt| {
            let numerator = BigInt::from(neutral) * decay_denominator
                + BigInt::from(position - neutral) * decay_numerator;
            json!({
                "numerator": numerator.to_string(),
                "denominator": decay_denominator.to_string(),
                "form": "unreduced exact rational",
            })
        };
    let moved_at_least_one =
        |position: i32, neutral: i32, decay_numerator: &BigInt, decay_denominator: &BigInt| {
            BigInt::from((i64::from(position) - i64::from(neutral)).unsigned_abs())
                * (decay_denominator - decay_numerator)
                >= *decay_denominator
        };

    let copied_axes = BODY_AXES
        .into_iter()
        .map(|axis| {
            let anatomy = axis.anatomy();
            (axis, anatomy, body.axis(axis))
        })
        .collect::<Vec<_>>();
    let stopped_non_neutral_axes = copied_axes
        .iter()
        .filter(|(_, anatomy, position)| {
            (*position == anatomy.minimum || *position == anatomy.maximum)
                && *position != anatomy.neutral
        })
        .map(|(axis, _, _)| format!("{axis:?}"))
        .collect::<Vec<_>>();

    let mut candidates = Vec::new();
    for tau_ms in time_constants_ms {
        let (decay_250_numerator, decay_250_denominator) = powers(tau_ms, 250);
        let (decay_64_numerator, decay_64_denominator) = powers(tau_ms, 64);
        let (decay_186_numerator, decay_186_denominator) = powers(tau_ms, 186);
        let (decay_2_000_numerator, decay_2_000_denominator) = powers(tau_ms, 2_000);
        let mut invariant_failures = Vec::new();
        let mut stopped_release = Vec::new();
        let mut first_visible_release_ms = Vec::new();
        if decay_250_numerator != &decay_64_numerator * &decay_186_numerator
            || decay_250_denominator != &decay_64_denominator * &decay_186_denominator
        {
            invariant_failures.push("elapsed_composition_failed".to_string());
        }
        for (axis, anatomy, predecessor) in &copied_axes {
            if (*predecessor == anatomy.minimum || *predecessor == anatomy.maximum)
                && *predecessor != anatomy.neutral
            {
                stopped_release.push(json!({
                    "axis": format!("{axis:?}"),
                    "predecessor": predecessor,
                    "neutral": anatomy.neutral,
                    "after_250_ms": exact_position_json(
                        *predecessor,
                        anatomy.neutral,
                        &decay_250_numerator,
                        &decay_250_denominator,
                    ),
                    "released_at_least_one_position_quantum": moved_at_least_one(
                        *predecessor,
                        anatomy.neutral,
                        &decay_250_numerator,
                        &decay_250_denominator,
                    ),
                }));
                let (at_1_000_numerator, at_1_000_denominator) = powers(tau_ms, 1_000);
                let first = if !moved_at_least_one(
                    *predecessor,
                    anatomy.neutral,
                    &at_1_000_numerator,
                    &at_1_000_denominator,
                ) {
                    None
                } else {
                    let mut below = 0_u64;
                    let mut at_or_above = 1_000_u64;
                    while below + 1 < at_or_above {
                        let midpoint = below + (at_or_above - below) / 2;
                        let (numerator, denominator) = powers(tau_ms, midpoint);
                        if moved_at_least_one(
                            *predecessor,
                            anatomy.neutral,
                            &numerator,
                            &denominator,
                        ) {
                            at_or_above = midpoint;
                        } else {
                            below = midpoint;
                        }
                    }
                    Some(at_or_above)
                };
                first_visible_release_ms.push(json!({
                    "axis": format!("{axis:?}"),
                    "first_at_least_one_quantum_ms": first,
                }));
            }
        }

        let zero_toward_maximum_span_axes = BODY_AXES
            .into_iter()
            .filter(|axis| axis.anatomy().neutral == axis.anatomy().maximum)
            .map(|axis| format!("{axis:?}"))
            .collect::<Vec<_>>();
        let neutral_pulse = json!({
            "toward_maximum_zero_span_axes": zero_toward_maximum_span_axes,
            "shared_nonzero_span_displacement_after_one_ms": {
                "numerator": tau_ms.to_string(),
                "denominator": (tau_ms + 1).to_string(),
            },
            "shared_nonzero_span_displacement_after_250_ms": {
                "numerator": decay_250_numerator.to_string(),
                "denominator": decay_250_denominator.to_string(),
            },
            "remains_exactly_nonzero_after_one_ms": true,
        });

        let mut sustained = Vec::new();
        for carriers_per_ms in sustained_carriers_per_ms {
            for direction in [-1_i64, 1_i64] {
                let mut hit_stop = Vec::new();
                let mut minimum_positive_span = None::<i32>;
                for (axis, anatomy, _) in &copied_axes {
                    let directional_span = if direction.is_negative() {
                        anatomy.neutral - anatomy.minimum
                    } else {
                        anatomy.maximum - anatomy.neutral
                    };
                    if directional_span == 0 {
                        hit_stop.push(format!("{axis:?}:zero_directional_span"));
                        continue;
                    }
                    minimum_positive_span = Some(
                        minimum_positive_span
                            .map_or(directional_span, |current| current.min(directional_span)),
                    );
                    let displacement_numerator = BigInt::from(tau_ms * carriers_per_ms)
                        * (&decay_2_000_denominator - &decay_2_000_numerator);
                    if displacement_numerator
                        >= BigInt::from(directional_span) * &decay_2_000_denominator
                    {
                        hit_stop.push(format!("{axis:?}"));
                    }
                }
                let maximum_normalized_displacement = minimum_positive_span.map(|span| {
                    json!({
                        "numerator": (BigInt::from(tau_ms * carriers_per_ms)
                            * (&decay_2_000_denominator - &decay_2_000_numerator)).to_string(),
                        "denominator": (BigInt::from(span)
                            * &decay_2_000_denominator).to_string(),
                        "minimum_positive_directional_span": span,
                    })
                });
                sustained.push(json!({
                    "carriers_per_ms": carriers_per_ms,
                    "direction": if direction.is_negative() { "toward_minimum" } else { "toward_maximum" },
                    "duration_ms": 2_000,
                    "would_press_anatomical_stop_axes_without_clamp": hit_stop,
                    "maximum_normalized_displacement": maximum_normalized_displacement,
                }));
            }
        }

        let duration_samples = observation_durations_ms
            .into_iter()
            .map(|elapsed_ms| {
                let (decay_numerator, decay_denominator) = powers(tau_ms, elapsed_ms);
                let visibly_released_stops = copied_axes
                    .iter()
                    .filter(|(_, anatomy, predecessor)| {
                        (*predecessor == anatomy.minimum || *predecessor == anatomy.maximum)
                            && *predecessor != anatomy.neutral
                    })
                    .filter(|(_, anatomy, predecessor)| {
                        moved_at_least_one(
                            *predecessor,
                            anatomy.neutral,
                            &decay_numerator,
                            &decay_denominator,
                        )
                    })
                    .count();
                json!({
                    "elapsed_ms": elapsed_ms,
                    "visibly_released_stopped_axes": visibly_released_stops,
                })
            })
            .collect::<Vec<_>>();
        candidates.push(json!({
            "passive_time_constant_ms": tau_ms,
            "invariant_failures": invariant_failures,
            "stopped_release": stopped_release,
            "first_visible_release": first_visible_release_ms,
            "duration_samples": duration_samples,
            "neutral_one_carrier_pulse": neutral_pulse,
            "sustained_drive": sustained,
        }));
    }
    json!({
        "production_compiled": false,
        "model_authority": "measurement-only lower bound; not authorized production mechanics",
        "native_mechanical_step_microseconds": 1_000,
        "equation": "q[n+1] = clamp((tau*(q[n]+u[n]) + neutral)/(tau+1))",
        "evaluation": "exact integer powers and inequalities; no floating point and no rational normalization",
        "copied_axis_count": copied_axes.len(),
        "copied_stopped_non_neutral_axes": stopped_non_neutral_axes,
        "time_constants_ms": time_constants_ms,
        "observation_durations_ms": observation_durations_ms,
        "sustained_carriers_per_ms": sustained_carriers_per_ms,
        "candidate_count": candidates.len(),
        "candidates": candidates,
    })
}

#[derive(Clone)]
struct ProbeAntagonistTissue {
    position: i64,
    minimum: i64,
    neutral: i64,
    maximum: i64,
    activation_units: [u128; 2],
    admitted_work: BigRational,
    dissipated_work: BigRational,
    stopped_load_quanta: u128,
}

impl ProbeAntagonistTissue {
    fn from_axis(body: &ArticulatedBodyState, axis: BodyAxis) -> Self {
        let anatomy = axis.anatomy();
        Self {
            position: i64::from(body.axis(axis)),
            minimum: i64::from(anatomy.minimum),
            neutral: i64::from(anatomy.neutral),
            maximum: i64::from(anatomy.maximum),
            activation_units: [0; 2],
            admitted_work: BigRational::zero(),
            dissipated_work: BigRational::zero(),
            stopped_load_quanta: 0,
        }
    }

    fn at_neutral(axis: BodyAxis) -> Self {
        let anatomy = axis.anatomy();
        Self {
            position: i64::from(anatomy.neutral),
            minimum: i64::from(anatomy.minimum),
            neutral: i64::from(anatomy.neutral),
            maximum: i64::from(anatomy.maximum),
            activation_units: [0; 2],
            admitted_work: BigRational::zero(),
            dissipated_work: BigRational::zero(),
            stopped_load_quanta: 0,
        }
    }

    fn direction_index(direction: BodyEffectorDirection) -> usize {
        match direction {
            BodyEffectorDirection::TowardMinimum => 0,
            BodyEffectorDirection::TowardMaximum => 1,
        }
    }

    fn directional_span(&self, direction: BodyEffectorDirection) -> u128 {
        match direction {
            BodyEffectorDirection::TowardMinimum => (self.neutral - self.minimum) as u128,
            BodyEffectorDirection::TowardMaximum => (self.maximum - self.neutral) as u128,
        }
    }

    fn admit(
        &mut self,
        direction: BodyEffectorDirection,
        carriers: u128,
        work_per_carrier: &BigRational,
        activation_lifetime_ms: u128,
        coupling_numerator: u128,
        coupling_denominator: u128,
    ) {
        let total_work = work_per_carrier * BigInt::from(carriers);
        self.admitted_work += &total_work;
        // Work custody closes at this boundary. The terminal activation is a
        // bounded material conformation (integer cross-bridge quanta), not a
        // repeatedly divided rational energy reservoir. Retaining a rational
        // fraction per millisecond was rejected because its denominator grew
        // with lifetime. The exact released work is therefore dissipated once
        // by the body transaction while the admitted conformation persists.
        self.dissipated_work += &total_work;
        let coupled_carriers = carriers.saturating_mul(coupling_numerator) / coupling_denominator;
        if coupled_carriers == 0 {
            self.stopped_load_quanta = self.stopped_load_quanta.saturating_add(carriers);
            return;
        }
        let index = Self::direction_index(direction);
        let capacity_units = self
            .directional_span(direction)
            .saturating_mul(activation_lifetime_ms);
        let requested_units = coupled_carriers.saturating_mul(activation_lifetime_ms);
        let available_units = capacity_units.saturating_sub(self.activation_units[index]);
        let admitted_units = requested_units.min(available_units);
        self.activation_units[index] = self.activation_units[index].saturating_add(admitted_units);
        self.stopped_load_quanta = self
            .stopped_load_quanta
            .saturating_add(carriers.saturating_sub(admitted_units / activation_lifetime_ms));
    }

    fn step_one_ms(&mut self, activation_lifetime_ms: u128, response_time_ms: u128) {
        let equivalent = |units: u128| {
            if units == 0 {
                0
            } else {
                1 + (units - 1) / activation_lifetime_ms
            }
        };
        let toward_minimum = equivalent(self.activation_units[0]);
        let toward_maximum = equivalent(self.activation_units[1]);
        let signed_activation = if toward_maximum >= toward_minimum {
            i128::try_from(toward_maximum - toward_minimum).expect("bounded positive activation")
        } else {
            -i128::try_from(toward_minimum - toward_maximum).expect("bounded negative activation")
        };
        let unclamped_target = i128::from(self.neutral) + signed_activation;
        let target =
            unclamped_target.clamp(i128::from(self.minimum), i128::from(self.maximum)) as i64;
        self.stopped_load_quanta = self
            .stopped_load_quanta
            .saturating_add(unclamped_target.abs_diff(i128::from(target)));
        let gap = self.position.abs_diff(target);
        if gap != 0 {
            let response = u64::try_from(response_time_ms).expect("bounded response time");
            let step = 1 + (gap - 1) / response;
            if target > self.position {
                self.position += i64::try_from(step).expect("bounded positive body step");
            } else {
                self.position -= i64::try_from(step).expect("bounded negative body step");
            }
        }
        for index in 0..2 {
            let before_units = self.activation_units[index];
            if before_units == 0 {
                continue;
            }
            let expired_units = 1 + (before_units - 1) / activation_lifetime_ms;
            self.activation_units[index] -= expired_units;
        }
    }

    fn work_closes(&self) -> bool {
        self.admitted_work == self.dissipated_work
    }
}

fn copied_body_antagonist_activation_range_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let activation_lifetimes_ms = [4_u128, 8, 16, 32, 64, 128, 256];
    let response_times_ms = [1_u128, 2, 4, 8, 16, 32, 64];
    let coupling_fractions = [(1_u128, 2_u128), (3, 4), (1, 1)];
    let learned = [
        (
            BodyAxis::VocalTractSection0Area,
            BodyEffectorDirection::TowardMaximum,
            BigRational::new(
                BigInt::parse_bytes(b"166767809696532795445407", 10).unwrap(),
                BigInt::parse_bytes(b"1100000000000000000000000", 10).unwrap(),
            ),
        ),
        (
            BodyAxis::VocalTractSection7Area,
            BodyEffectorDirection::TowardMinimum,
            BigRational::new(
                BigInt::parse_bytes(b"36616220961176220112151901", 10).unwrap(),
                BigInt::parse_bytes(b"237050000000000000000000000", 10).unwrap(),
            ),
        ),
    ];
    let stopped_axes = BODY_AXES
        .into_iter()
        .filter(|axis| {
            let anatomy = axis.anatomy();
            let position = body.axis(*axis);
            position != anatomy.neutral
                && (position == anatomy.minimum || position == anatomy.maximum)
        })
        .collect::<Vec<_>>();
    let mut candidates = Vec::new();
    let mut accepted_count = 0usize;
    for activation_lifetime_ms in activation_lifetimes_ms {
        for response_time_ms in response_times_ms {
            for (coupling_numerator, coupling_denominator) in coupling_fractions {
                let mut failures = Vec::new();
                let mut releases = Vec::new();
                for axis in &stopped_axes {
                    let mut tissue = ProbeAntagonistTissue::from_axis(body, *axis);
                    let predecessor = tissue.position;
                    tissue.step_one_ms(activation_lifetime_ms, response_time_ms);
                    let after_one = tissue.position;
                    let gap = predecessor.abs_diff(tissue.neutral);
                    if after_one == predecessor {
                        failures.push(format!("{axis:?}:did_not_release_in_one_ms"));
                    }
                    if gap > 1 && after_one == tissue.neutral {
                        failures.push(format!("{axis:?}:teleported_to_neutral"));
                    }
                    for _ in 1..16 {
                        tissue.step_one_ms(activation_lifetime_ms, response_time_ms);
                    }
                    if !tissue.work_closes() {
                        failures.push(format!("{axis:?}:legacy_release_work_did_not_close"));
                    }
                    releases.push(json!({
                        "axis": format!("{axis:?}"),
                        "predecessor": predecessor,
                        "after_one_ms": after_one,
                        "after_sixteen_ms": tissue.position,
                    }));
                }

                let mut pulse_results = Vec::new();
                for (axis, direction, work) in &learned {
                    let mut tissue = ProbeAntagonistTissue::at_neutral(*axis);
                    tissue.admit(
                        *direction,
                        1,
                        work,
                        activation_lifetime_ms,
                        coupling_numerator,
                        coupling_denominator,
                    );
                    let mut visible_ms = 0_u64;
                    let mut first_position = tissue.position;
                    for elapsed in 0..=512_u64 {
                        tissue.step_one_ms(activation_lifetime_ms, response_time_ms);
                        if elapsed == 0 {
                            first_position = tissue.position;
                        }
                        if tissue.position != tissue.neutral {
                            visible_ms += 1;
                        }
                    }
                    if first_position == tissue.neutral {
                        failures.push(format!("{axis:?}:one_carrier_twitch_absent"));
                    }
                    if !(16..=250).contains(&visible_ms) {
                        failures.push(format!(
                            "{axis:?}:visible_duration_{visible_ms}_outside_16_250"
                        ));
                    }
                    if tissue.position != tissue.neutral {
                        failures.push(format!("{axis:?}:did_not_return_by_512_ms"));
                    }
                    if !tissue.work_closes() {
                        failures.push(format!("{axis:?}:pulse_work_did_not_close"));
                    }
                    pulse_results.push(json!({
                        "axis": format!("{axis:?}"),
                        "direction": format!("{direction:?}"),
                        "first_position": first_position,
                        "visible_duration_ms": visible_ms,
                        "returned_by_512_ms": tissue.position == tissue.neutral,
                        "work_closed": tissue.work_closes(),
                    }));
                }

                let (axis, _, work) = &learned[0];
                let mut opposed = ProbeAntagonistTissue::at_neutral(*axis);
                opposed.admit(
                    BodyEffectorDirection::TowardMinimum,
                    8,
                    work,
                    activation_lifetime_ms,
                    coupling_numerator,
                    coupling_denominator,
                );
                opposed.admit(
                    BodyEffectorDirection::TowardMaximum,
                    8,
                    work,
                    activation_lifetime_ms,
                    coupling_numerator,
                    coupling_denominator,
                );
                opposed.step_one_ms(activation_lifetime_ms, response_time_ms);
                if opposed.position != opposed.neutral {
                    failures.push("opposed_drive_moved_axis".to_string());
                }
                if !opposed.work_closes() {
                    failures.push("opposed_drive_work_did_not_close".to_string());
                }

                let mut sustained = Vec::new();
                for rate in [1_u128, 2, 4, 8, 16] {
                    for (axis, direction, work) in &learned {
                        let mut tissue = ProbeAntagonistTissue::at_neutral(*axis);
                        for _ in 0..1_000 {
                            tissue.admit(
                                *direction,
                                rate,
                                work,
                                activation_lifetime_ms,
                                coupling_numerator,
                                coupling_denominator,
                            );
                            tissue.step_one_ms(activation_lifetime_ms, response_time_ms);
                        }
                        let at_stop =
                            tissue.position == tissue.minimum || tissue.position == tissue.maximum;
                        if rate == 1 && at_stop {
                            failures.push(format!("{axis:?}:one_per_ms_pinned"));
                        }
                        if at_stop && tissue.stopped_load_quanta == 0 {
                            failures.push(format!("{axis:?}:stop_without_load"));
                        }
                        if !tissue.work_closes() {
                            failures.push(format!("{axis:?}:sustained_work_did_not_close"));
                        }
                        sustained.push(json!({
                            "axis": format!("{axis:?}"),
                            "carriers_per_ms": rate.to_string(),
                            "position_after_1000_ms": tissue.position,
                            "at_stop": at_stop,
                            "stopped_load_quanta": tissue.stopped_load_quanta.to_string(),
                            "work_closed": tissue.work_closes(),
                        }));
                    }
                }

                let composition_axis = stopped_axes[0];
                let mut whole = ProbeAntagonistTissue::from_axis(body, composition_axis);
                let mut split = whole.clone();
                for _ in 0..250 {
                    whole.step_one_ms(activation_lifetime_ms, response_time_ms);
                }
                for _ in 0..64 {
                    split.step_one_ms(activation_lifetime_ms, response_time_ms);
                }
                for _ in 0..186 {
                    split.step_one_ms(activation_lifetime_ms, response_time_ms);
                }
                if whole.position != split.position
                    || whole.activation_units != split.activation_units
                    || whole.dissipated_work != split.dissipated_work
                {
                    failures.push("64_plus_186_did_not_equal_250".to_string());
                }
                let accepted = failures.is_empty();
                accepted_count += usize::from(accepted);
                candidates.push(json!({
                    "activation_lifetime_ms": activation_lifetime_ms.to_string(),
                    "response_time_ms": response_time_ms.to_string(),
                    "coupling": format!("{coupling_numerator}/{coupling_denominator}"),
                    "accepted": accepted,
                    "failures": failures,
                    "legacy_stop_release": releases,
                    "learned_one_carrier_pulses": pulse_results,
                    "opposed_drive_position": opposed.position,
                    "sustained_drive": sustained,
                    "duration_composition_position": whole.position,
                }));
            }
        }
    }
    json!({
        "production_compiled": false,
        "model_authority": "test-only bounded antagonist activation range",
        "native_mechanical_step_microseconds": 1_000,
        "activation_equation": "input carriers establish bounded terminal tension; ceil(active_units/lifetime) defines equilibrium displacement; active units and exact work decay together",
        "body_equation": "position advances ceil(|target-position|/response_time) toward clamped neutral-plus-net-antagonist-equilibrium",
        "work_equation": "admitted exact terminal work = retained activation work + explicit dissipated work",
        "activation_lifetimes_ms": activation_lifetimes_ms.map(|value| value.to_string()),
        "response_times_ms": response_times_ms.map(|value| value.to_string()),
        "coupling_fractions": coupling_fractions.map(|(n, d)| format!("{n}/{d}")),
        "candidate_count": candidates.len(),
        "accepted_count": accepted_count,
        "candidates": candidates,
    })
}

fn motor_reachability_json(state: &ResidentCognitiveFormationState) -> Value {
    let mut successor = state.clone();
    let externally_reached = successor
        .cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
                .filter_map(|(mount, lineage)| mount.source_site().is_some().then_some(*lineage))
        })
        .collect::<Vec<_>>();
    let motor_before = successor
        .cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
                .zip(cohort.state.neurons())
                .filter_map(|((mount, lineage), neuron)| {
                    (mount.place().layer() == 12).then_some((
                        *lineage,
                        neuron.gate.open_population(),
                        neuron.membrane_state().separated_elementary_charges(),
                    ))
                })
        })
        .collect::<Vec<_>>();
    let mut changed = std::collections::BTreeSet::new();
    let unchanged_developmental_resting_neuron_count = successor
        .resting_population
        .as_ref()
        .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
        .unwrap_or(0);
    let topology_index = successor.topology_index.clone();
    let observation = super::settle_internal_contact_interval(
        &mut successor.cohorts,
        &mut successor.electrical_fabric,
        &topology_index,
        None,
        &[],
        &[],
        &externally_reached,
        &externally_reached,
        &externally_reached,
        &externally_reached,
        &mut changed,
        successor.generation,
        unchanged_developmental_resting_neuron_count,
        &mut None,
        &std::collections::BTreeMap::new(),
        &[],
        &[],
        crate::exact_rational::ExactRational::integer(0),
        true,
    )
    .expect("maximal external frontier settles");
    let pending_post_quiescence_candidates = successor
        .cohorts
        .iter()
        .filter_map(|cohort| cohort.pending_experience.as_ref())
        .map(|experience| experience.pending_members().map_or(0, <[_]>::len))
        .sum::<usize>();
    let motor_after = successor
        .cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
                .zip(cohort.state.neurons())
                .filter_map(|((mount, lineage), neuron)| {
                    (mount.place().layer() == 12).then_some((
                        *lineage,
                        neuron.gate.open_population(),
                        neuron.membrane_state().separated_elementary_charges(),
                    ))
                })
        })
        .collect::<Vec<_>>();
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    json!({
        "external_receptor_count": externally_reached.len(),
        "dsf_delivery_count": observation.dsf_delivery_count,
        "physically_changed_neuron_count": changed.len(),
        "emitted_fractal_count": 0,
        "pending_post_quiescence_candidate_count": pending_post_quiescence_candidates,
        "motor_before": motor_before.into_iter().map(|(lineage, gate, charge)| json!({
            "lineage": lineage_hex(lineage),
            "open_gate_population": gate.to_string(),
            "membrane_charge": charge.to_string(),
        })).collect::<Vec<_>>(),
        "motor_after": motor_after.into_iter().map(|(lineage, gate, charge)| json!({
            "lineage": lineage_hex(lineage),
            "open_gate_population": gate.to_string(),
            "membrane_charge": charge.to_string(),
        })).collect::<Vec<_>>(),
        "motor_unit_recruitments": observation.motor_unit_recruitments.into_iter().map(|event| json!({
            "lineage": lineage_hex(event.neuron_lineage),
            "topology_index": event.topology_index,
            "outward_elementary_carriers": event.outward_elementary_carriers.to_string(),
            "body_afferent_paths": event.body_afferent_paths.into_iter().map(|path| json!({
                "body_regulation_lineage": lineage_hex(path.body_regulation_lineage),
                "integration_lineage": lineage_hex(path.integration_lineage),
                "receptor_lineage": lineage_hex(path.receptor_lineage),
                "receptor_sense_layer": path.receptor_site.sense().declared_layer(),
                "receptor_topology_index": path.receptor_site.topology_index(),
                "sensor_id": path.receptor_site.sensor_id(),
                "substream_id": path.receptor_site.substream_id(),
            })).collect::<Vec<_>>(),
            "preparation_transfers": event.preparation_transfers.into_iter().map(|preparation| json!({
                "sender": lineage_hex(preparation.transfer.sender),
                "sender_layer": preparation.sender_layer,
                "receiver": lineage_hex(preparation.transfer.receiver),
                "parallel_ordinal": preparation.transfer.bond.parallel_ordinal(),
                "transferred_whole_carriers": preparation.transfer.transferred_whole_carriers.to_string(),
            })).collect::<Vec<_>>(),
        })).collect::<Vec<_>>(),
    })
}

fn mounted_neuron_electrical_json(
    state: &ResidentCognitiveFormationState,
    lineage: [u8; 16],
) -> Value {
    for cohort in &state.cohorts {
        for (((mount, candidate), anatomy), neuron) in cohort
            .anatomy
            .mounts()
            .iter()
            .zip(cohort.anatomy.neuron_lineages())
            .zip(cohort.anatomy.neuron_anatomies())
            .zip(cohort.state.neurons())
        {
            if *candidate != lineage {
                continue;
            }
            let potential = neuron
                .membrane_state()
                .potential_millivolts(anatomy.capacitance())
                .expect("range-probe potential");
            let pump = crate::complete_neuron::membrane_gradient_pump_charge_bound(
                anatomy,
                neuron,
                super::WORLD_MECHANICAL_TICK_MICROSECONDS,
            )
            .expect("range-probe pump bound");
            return json!({
                "layer": mount.place().layer(),
                "membrane_charge": neuron.separated_elementary_charges().to_string(),
                "capacitance_picofarads": exact_json(anatomy.capacitance().picofarads()),
                "membrane_potential_millivolts": exact_json(potential),
                "open_gate_population": neuron.gate.open_population().to_string(),
                "one_clock_active_pump_bound": pump.charges.to_string(),
            });
        }
    }
    panic!("range-probe lineage absent")
}

fn mounted_neuron_ternary_winding_state_json(
    state: &ResidentCognitiveFormationState,
    lineage: [u8; 16],
) -> Value {
    for cohort in &state.cohorts {
        let Some(neuron_index) = cohort
            .anatomy
            .neuron_lineages()
            .iter()
            .position(|candidate| *candidate == lineage)
        else {
            continue;
        };
        let ordered_windings = cohort.state.neurons()[neuron_index]
            .psi
            .rings()
            .iter()
            .map(|ring| ring.winding() as i8)
            .collect::<Vec<_>>();
        let counts = ordered_windings
            .iter()
            .fold([0_u64; 3], |mut counts, winding| {
                counts[usize::from((*winding + 1) as u8)] += 1;
                counts
            });
        return json!({
            "ordered_windings": ordered_windings,
            "summary_counts": {
                "negative": counts[0],
                "quiescent": counts[1],
                "positive": counts[2],
            },
        });
    }
    panic!("ternary-range lineage absent")
}

fn apply_probe_gradient_population(
    state: &mut ResidentCognitiveFormationState,
    lineage: [u8; 16],
    effective_population: u32,
) -> Value {
    if effective_population <= 1 {
        return json!({
            "effective_population": effective_population,
            "additional_interval_microseconds": 0,
            "returned_elementary_charges": "0",
            "pumped_elementary_charges": "0",
            "pump_work_zeptojoules": exact_json(ExactRational::integer(0)),
        });
    }
    let additional_interval_microseconds = super::WORLD_MECHANICAL_TICK_MICROSECONDS
        .checked_mul(effective_population - 1)
        .expect("probe population interval");
    for cohort in &mut state.cohorts {
        let Some(neuron_index) = cohort
            .anatomy
            .neuron_lineages()
            .iter()
            .position(|candidate| *candidate == lineage)
        else {
            continue;
        };
        let prepared = crate::reached_neuron_cohort::prepare_reached_cohort_membrane_pumps(
            &cohort.anatomy,
            &cohort.state,
            &[neuron_index],
            additional_interval_microseconds,
            ExactRational::integer(0),
        )
        .expect("probe population-gradient settlement");
        let observation =
            crate::reached_neuron_cohort::apply_prepared_reached_cohort_membrane_pumps(
                std::sync::Arc::make_mut(&mut cohort.state),
                prepared,
            );
        return json!({
            "effective_population": effective_population,
            "additional_interval_microseconds": additional_interval_microseconds,
            "returned_elementary_charges": observation.returned_elementary_charges.to_string(),
            "pumped_elementary_charges": observation.pumped_elementary_charges.to_string(),
            "pump_work_zeptojoules": exact_json(
                observation.membrane_gradient_work_zeptojoules,
            ),
            "environment_energy_delivered_zeptojoules": exact_json(
                observation.environment_energy_delivered_zeptojoules,
            ),
        });
    }
    panic!("probe population-gradient lineage absent")
}

/// Test the one existing area-mismatch hypothesis without changing production
/// physics. One ordinary one-channel pump integrated for `N` identical channel
/// times is the current law's exact static-predecessor equivalent of `N`
/// parallel identical pump sites over one clock; its reversal-side and finite
/// reservoir bounds remain intact. The range is diagnostic only. It asks
/// whether restoring membrane-area-proportional gradient throughput can turn
/// an already-physical causal seed into forward L11 -> L12 carrier transport.
fn motor_bridge_gradient_population_range_json(state: &ResidentCognitiveFormationState) -> Value {
    let topology = state.topology_index.clone();
    let mut routes = state
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = state.electrical_fabric.lineages()[left];
            let right_lineage = state.electrical_fabric.lineages()[right];
            match (
                topology.layer_of(left_lineage),
                topology.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some((left_lineage, right_lineage)),
                (Some(12), Some(11)) => Some((right_lineage, left_lineage)),
                _ => None,
            }
        })
        .collect::<Vec<_>>();
    routes.sort_unstable();
    routes.dedup();
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let populations = [1_u32, 4, 16, 64, 256, 1_024, 4_096, 8_192];
    let mut route_results = Vec::new();
    for (ordering, motor) in routes {
        let mut founders = state
            .electrical_fabric
            .contact_endpoints()
            .filter_map(|(left, right)| {
                let left_lineage = state.electrical_fabric.lineages()[left];
                let right_lineage = state.electrical_fabric.lineages()[right];
                if left_lineage == ordering
                    && matches!(topology.layer_of(right_lineage), Some(7 | 10))
                {
                    Some(right_lineage)
                } else if right_lineage == ordering
                    && matches!(topology.layer_of(left_lineage), Some(7 | 10))
                {
                    Some(left_lineage)
                } else {
                    None
                }
            })
            .collect::<Vec<_>>();
        founders.sort_unstable();
        founders.dedup();
        let modes = [
            ("ordering_seeded", vec![ordering]),
            ("founding_pair_seeded", founders.clone()),
        ];
        let mut mode_results = Vec::new();
        for (mode, seeds) in modes {
            let mut population_results = Vec::new();
            for effective_population in populations {
                let mut successor = state.clone();
                let mut residency = None;
                let mut samples = Vec::new();
                for active_clock in 1_u64..=3 {
                    let pump = seeds
                        .iter()
                        .copied()
                        .map(|lineage| {
                            json!({
                                "lineage": lineage_hex(lineage),
                                "settlement": apply_probe_gradient_population(
                                    &mut successor,
                                    lineage,
                                    effective_population,
                                ),
                            })
                        })
                        .collect::<Vec<_>>();
                    let mut changed = std::collections::BTreeSet::new();
                    let unchanged_developmental_resting_neuron_count = successor
                        .resting_population
                        .as_ref()
                        .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
                        .unwrap_or(0);
                    let observation = super::settle_internal_contact_interval(
                        &mut successor.cohorts,
                        &mut successor.electrical_fabric,
                        &topology,
                        None,
                        &[],
                        &[],
                        &seeds,
                        &seeds,
                        &seeds,
                        &seeds,
                        &mut changed,
                        successor.generation + active_clock,
                        unchanged_developmental_resting_neuron_count,
                        &mut residency,
                        &std::collections::BTreeMap::new(),
                        &[],
                        &[],
                        ExactRational::integer(0),
                        true,
                    )
                    .expect("population-range contact settlement");
                    let signed_transfer = observation
                        .settled_directed_transfers
                        .iter()
                        .filter_map(|transfer| {
                            if transfer.sender == ordering && transfer.receiver == motor {
                                i128::try_from(transfer.transferred_whole_carriers).ok()
                            } else if transfer.sender == motor && transfer.receiver == ordering {
                                i128::try_from(transfer.transferred_whole_carriers)
                                    .ok()
                                    .and_then(i128::checked_neg)
                            } else {
                                None
                            }
                        })
                        .sum::<i128>();
                    samples.push(json!({
                        "active_clock": active_clock,
                        "pump": pump,
                        "ordering": mounted_neuron_electrical_json(&successor, ordering),
                        "motor": mounted_neuron_electrical_json(&successor, motor),
                        "signed_ordering_to_motor_whole_carriers": signed_transfer.to_string(),
                        "motor_recruited": observation.motor_unit_recruitments
                            .iter()
                            .any(|event| event.neuron_lineage == motor),
                    }));
                }
                population_results.push(json!({
                    "effective_population": effective_population,
                    "samples": samples,
                }));
            }
            mode_results.push(json!({
                "mode": mode,
                "seed_lineages": seeds.into_iter().map(lineage_hex).collect::<Vec<_>>(),
                "population_results": population_results,
            }));
        }
        route_results.push(json!({
            "ordering_lineage": lineage_hex(ordering),
            "motor_lineage": lineage_hex(motor),
            "ordering_capacitance_picofarads": mounted_neuron_electrical_json(state, ordering)
                ["capacitance_picofarads"].clone(),
            "modes": mode_results,
        }));
    }
    json!({
        "retained_causal_frontier_span": 3,
        "effective_population_range": populations,
        "routes": route_results,
    })
}

/// Exercise every learned layer-11/layer-12 route in the exact copied body
/// across one through eight consecutive active ordering clocks. This is a
/// diagnostic range, not an authored stimulus and not production code: it
/// asks whether the already-existing neuron/pump/contact physics can ever
/// turn an active ordering endpoint into forward motor preparation within the
/// organism's retained three-frontier causal span. Quiet/background traffic
/// continues to settle exactly as it does in the copied body.
fn motor_bridge_active_range_json(state: &ResidentCognitiveFormationState) -> Value {
    let topology = state.topology_index.clone();
    let mut routes = state
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = state.electrical_fabric.lineages()[left];
            let right_lineage = state.electrical_fabric.lineages()[right];
            match (
                topology.layer_of(left_lineage),
                topology.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some((left_lineage, right_lineage)),
                (Some(12), Some(11)) => Some((right_lineage, left_lineage)),
                _ => None,
            }
        })
        .collect::<Vec<_>>();
    routes.sort_unstable();
    routes.dedup();

    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let mut results = Vec::new();
    for (ordering, motor) in routes {
        let mut successor = state.clone();
        let mut causal_seeds = successor
            .electrical_fabric
            .contact_endpoints()
            .filter_map(|(left, right)| {
                let left_lineage = successor.electrical_fabric.lineages()[left];
                let right_lineage = successor.electrical_fabric.lineages()[right];
                if left_lineage == ordering
                    && matches!(topology.layer_of(right_lineage), Some(7 | 10))
                {
                    Some(right_lineage)
                } else if right_lineage == ordering
                    && matches!(topology.layer_of(left_lineage), Some(7 | 10))
                {
                    Some(left_lineage)
                } else {
                    None
                }
            })
            .collect::<Vec<_>>();
        causal_seeds.sort_unstable();
        causal_seeds.dedup();
        let mut residency = None;
        let mut samples = vec![json!({
            "active_clock": 0,
            "ordering": mounted_neuron_electrical_json(&successor, ordering),
            "motor": mounted_neuron_electrical_json(&successor, motor),
            "signed_ordering_to_motor_whole_carriers": "0",
            "motor_recruited": false,
        })];
        for active_clock in 1_u64..=8 {
            let mut changed = std::collections::BTreeSet::new();
            let unchanged_developmental_resting_neuron_count = successor
                .resting_population
                .as_ref()
                .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
                .unwrap_or(0);
            let topology = successor.topology_index.clone();
            let observation = super::settle_internal_contact_interval(
                &mut successor.cohorts,
                &mut successor.electrical_fabric,
                &topology,
                None,
                &[],
                &[],
                &causal_seeds,
                &causal_seeds,
                &causal_seeds,
                &causal_seeds,
                &mut changed,
                successor.generation + active_clock,
                unchanged_developmental_resting_neuron_count,
                &mut residency,
                &std::collections::BTreeMap::new(),
                &[],
                &[],
                ExactRational::integer(0),
                true,
            )
            .expect("active ordering range settles");
            let signed_transfer = observation
                .settled_directed_transfers
                .iter()
                .filter_map(|transfer| {
                    if transfer.sender == ordering && transfer.receiver == motor {
                        i128::try_from(transfer.transferred_whole_carriers).ok()
                    } else if transfer.sender == motor && transfer.receiver == ordering {
                        i128::try_from(transfer.transferred_whole_carriers)
                            .ok()
                            .and_then(i128::checked_neg)
                    } else {
                        None
                    }
                })
                .sum::<i128>();
            let motor_recruited = observation
                .motor_unit_recruitments
                .iter()
                .any(|event| event.neuron_lineage == motor);
            samples.push(json!({
                "active_clock": active_clock,
                "ordering": mounted_neuron_electrical_json(&successor, ordering),
                "motor": mounted_neuron_electrical_json(&successor, motor),
                "signed_ordering_to_motor_whole_carriers": signed_transfer.to_string(),
                "motor_recruited": motor_recruited,
                "changed_neuron_count": changed.len(),
            }));
        }
        results.push(json!({
            "ordering_lineage": lineage_hex(ordering),
            "motor_lineage": lineage_hex(motor),
            "causal_seed_lineages": causal_seeds.into_iter().map(lineage_hex).collect::<Vec<_>>(),
            "samples": samples,
        }));
    }
    json!({
        "maximum_active_clocks": 8,
        "retained_causal_frontier_span": 3,
        "routes": results,
    })
}

/// Follow only the copied body's own retained electrical frontier.  Unlike the
/// older bridge ranges this supplies no authored or synthetic seed: the first
/// clock begins with exactly the persisted active frontier, later clocks begin
/// with only the physical successor frontier produced by the preceding clock.
/// Three clocks match the organism's bounded retained causal-frontier span.
fn retained_frontier_motor_range_json(
    state: &ResidentCognitiveFormationState,
    initial_articulated_body: Option<&ArticulatedBodyState>,
    maximum_clocks: u64,
) -> Value {
    let mut successor = state.clone();
    let mut articulated_body = initial_articulated_body.cloned();
    let mut frontier = successor.active_electrical_frontier.to_vec();
    let mut residency = None;
    let mut learned_ordering_lineages = successor
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = successor.electrical_fabric.lineages()[left];
            let right_lineage = successor.electrical_fabric.lineages()[right];
            match (
                successor.topology_index.layer_of(left_lineage),
                successor.topology_index.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some(left_lineage),
                (Some(12), Some(11)) => Some(right_lineage),
                _ => None,
            }
        })
        .collect::<Vec<_>>();
    learned_ordering_lineages.sort_unstable();
    learned_ordering_lineages.dedup();
    let ordering_to_motor = successor
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = successor.electrical_fabric.lineages()[left];
            let right_lineage = successor.electrical_fabric.lineages()[right];
            match (
                successor.topology_index.layer_of(left_lineage),
                successor.topology_index.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some((left_lineage, right_lineage)),
                (Some(12), Some(11)) => Some((right_lineage, left_lineage)),
                _ => None,
            }
        })
        .collect::<std::collections::BTreeMap<_, _>>();
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let mut clocks = Vec::new();
    for active_clock in 1_u64..=maximum_clocks {
        let mut reached_lineages = frontier
            .iter()
            .flat_map(|entry| entry.affected_lineages().into_iter().flatten())
            .collect::<Vec<_>>();
        reached_lineages.sort_unstable();
        reached_lineages.dedup();
        let topology = successor.topology_index.clone();
        let mut relevant_lineages = learned_ordering_lineages.clone();
        for ordering in &learned_ordering_lineages {
            let ordering_flat = topology
                .flat_for_lineage(*ordering)
                .expect("learned ordering lineage present");
            relevant_lineages.extend(
                topology.neighbours_by_flat[ordering_flat]
                    .iter()
                    .map(|flat| topology.flat_locations[*flat].2),
            );
        }
        relevant_lineages.sort_unstable();
        relevant_lineages.dedup();
        let predecessor_electrical = successor
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .neuron_lineages()
                    .iter()
                    .copied()
                    .zip(cohort.anatomy.neuron_anatomies())
                    .zip(cohort.state.neurons())
            })
            .filter_map(|((lineage, anatomy), neuron)| {
                relevant_lineages
                    .contains(&lineage)
                    .then(|| (lineage, (anatomy.clone(), neuron.clone())))
            })
            .collect::<std::collections::BTreeMap<_, _>>();
        let mut changed = std::collections::BTreeSet::new();
        let unchanged_developmental_resting_neuron_count = successor
            .resting_population
            .as_ref()
            .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
            .unwrap_or(0);
        let observation = super::settle_internal_contact_interval(
            &mut successor.cohorts,
            &mut successor.electrical_fabric,
            &topology,
            successor.vocal_articulatory_effector_lineage,
            &frontier,
            &[],
            &reached_lineages,
            &reached_lineages,
            &[],
            &[],
            &mut changed,
            successor.generation + active_clock,
            unchanged_developmental_resting_neuron_count,
            &mut residency,
            &std::collections::BTreeMap::new(),
            &[],
            &[],
            ExactRational::integer(0),
            true,
        )
        .expect("retained copied-body frontier settles");
        let bridge_transfers = observation
            .settled_directed_transfers
            .iter()
            .filter_map(|transfer| {
                let sender_layer = topology.layer_of(transfer.sender)?;
                let receiver_layer = topology.layer_of(transfer.receiver)?;
                (matches!((sender_layer, receiver_layer), (11, 12) | (12, 11))).then(|| {
                    json!({
                        "sender": lineage_hex(transfer.sender),
                        "sender_layer": sender_layer,
                        "receiver": lineage_hex(transfer.receiver),
                        "receiver_layer": receiver_layer,
                        "transferred_whole_carriers": transfer
                            .transferred_whole_carriers
                            .to_string(),
                    })
                })
            })
            .collect::<Vec<_>>();
        let ordering_incident_transfers = observation
            .settled_directed_transfers
            .iter()
            .filter_map(|transfer| {
                (learned_ordering_lineages.contains(&transfer.sender)
                    || learned_ordering_lineages.contains(&transfer.receiver))
                .then(|| {
                    let (sender_anatomy, sender_state) = predecessor_electrical
                        .get(&transfer.sender)
                        .expect("incident sender predecessor present");
                    let (receiver_anatomy, receiver_state) = predecessor_electrical
                        .get(&transfer.receiver)
                        .expect("incident receiver predecessor present");
                    let released =
                        crate::sparse_electrical_contact::probe_directed_contact_work_zeptojoules(
                            sender_anatomy,
                            sender_state,
                            receiver_anatomy,
                            receiver_state,
                            transfer.transferred_whole_carriers,
                        );
                    json!({
                        "sender": lineage_hex(transfer.sender),
                        "sender_layer": topology.layer_of(transfer.sender),
                        "receiver": lineage_hex(transfer.receiver),
                        "receiver_layer": topology.layer_of(transfer.receiver),
                        "transferred_whole_carriers": transfer
                            .transferred_whole_carriers
                            .to_string(),
                        "single_edge_released_work_zeptojoules": released
                            .as_ref()
                            .ok()
                            .map(wide_exact_json),
                        "single_edge_work_error": released.err().map(|error| format!("{error:?}")),
                    })
                })
            })
            .collect::<Vec<_>>();
        // Test-only three-terminal energy range.  For each real L11 -> L7
        // whole-carrier event, preserve the exact number leaving L11 but
        // redirect a bounded range of those same carriers into its one
        // learned L12 motor.  No carrier or work is added.  This asks whether
        // a lean, directed, energy-descending transducer is physically
        // possible before any production law or retained state is authored.
        let split_extents = [1_u128, 2, 4, 8, 16, 24, 32, 48, 64];
        let mut three_terminal_route_range = Vec::new();
        for transfer in &observation.settled_directed_transfers {
            if topology.layer_of(transfer.sender) != Some(11)
                || topology.layer_of(transfer.receiver) != Some(7)
            {
                continue;
            }
            let Some(motor) = ordering_to_motor.get(&transfer.sender).copied() else {
                continue;
            };
            let (ordering_anatomy, ordering_state) = predecessor_electrical
                .get(&transfer.sender)
                .expect("ordering predecessor present");
            let (founding_anatomy, founding_state) = predecessor_electrical
                .get(&transfer.receiver)
                .expect("founding predecessor present");
            let (motor_anatomy, motor_state) = predecessor_electrical
                .get(&motor)
                .expect("motor predecessor present");
            let before_work = crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                ordering_anatomy,
                ordering_state,
            )
            .expect("ordering predecessor work")
                + crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                    founding_anatomy,
                    founding_state,
                )
                .expect("founding predecessor work")
                + crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                    motor_anatomy,
                    motor_state,
                )
                .expect("motor predecessor work");
            let total = transfer.transferred_whole_carriers;
            let samples = split_extents
                .iter()
                .copied()
                .filter(|split| *split <= total)
                .map(|split| {
                    let ordering_successor =
                        crate::complete_neuron::settle_membrane_pump_transport(
                            ordering_anatomy,
                            ordering_state,
                            i128::try_from(total).expect("ordering transfer width"),
                            None,
                            super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                        )
                        .expect("ordering split sender");
                    let founding_successor =
                        crate::complete_neuron::settle_membrane_pump_transport(
                            founding_anatomy,
                            founding_state,
                            -i128::try_from(total - split).expect("founding transfer width"),
                            None,
                            super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                        )
                        .expect("founding split receiver");
                    let motor_successor = crate::complete_neuron::settle_membrane_pump_transport(
                        motor_anatomy,
                        motor_state,
                        -i128::try_from(split).expect("motor transfer width"),
                        None,
                        super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                    )
                    .expect("motor split receiver");
                    let after_work =
                        crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                            ordering_anatomy,
                            &ordering_successor,
                        )
                        .expect("ordering successor work")
                            + crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                                founding_anatomy,
                                &founding_successor,
                            )
                            .expect("founding successor work")
                            + crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                                motor_anatomy,
                                &motor_successor,
                            )
                            .expect("motor successor work");
                    let work_released = &before_work - &after_work;
                    let terminal = crate::complete_neuron::settle_efferent_terminal_transport(
                        motor_anatomy,
                        &motor_successor,
                        split,
                        super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                    )
                    .expect("split-prepared motor terminal");
                    json!({
                        "split_to_motor_carriers": split.to_string(),
                        "remaining_to_founding_carriers": (total - split).to_string(),
                        "strict_energy_descent": work_released > BigRational::zero(),
                        "released_work_zeptojoules": wide_exact_json(&work_released),
                        "terminal_discharged_carriers": terminal
                            .as_ref()
                            .map(|(_, carriers, _)| carriers.to_string()),
                        "terminal_released_work_zeptojoules": terminal
                            .as_ref()
                            .map(|(_, _, work)| wide_exact_json(work)),
                    })
                })
                .collect::<Vec<_>>();
            three_terminal_route_range.push(json!({
                "ordering": lineage_hex(transfer.sender),
                "founding_receiver": lineage_hex(transfer.receiver),
                "motor": lineage_hex(motor),
                "original_ordering_outward_carriers": total.to_string(),
                "samples": samples,
            }));
        }
        let respiratory_efferent_carriers = observation
            .articulatory_unit_recruitments
            .iter()
            .try_fold(0_u128, |total, event| {
                total.checked_add(event.outward_elementary_carriers)
            })
            .expect("copied-body respiratory carrier width");
        let body_transition = match articulated_body.take() {
            None => None,
            Some(body) => {
                let learned_axes = observation
                    .motor_unit_recruitments
                    .iter()
                    .filter(|recruitment| {
                        recruitment
                            .preparation_transfers
                            .iter()
                            .any(|preparation| preparation.sender_layer == 11)
                    })
                    .map(|recruitment| recruitment.body_effector_terminal.axis())
                    .collect::<std::collections::BTreeSet<_>>();
                let mut carriers_by_terminal = std::collections::BTreeMap::<_, u128>::new();
                for recruitment in &observation.motor_unit_recruitments {
                    let carriers = carriers_by_terminal
                        .entry(recruitment.body_effector_terminal)
                        .or_default();
                    *carriers = carriers
                        .checked_add(recruitment.outward_elementary_carriers)
                        .expect("body carrier aggregation width");
                }
                let admitted = AdmittedBodyEffectorDrives::admit(
                    carriers_by_terminal
                        .into_iter()
                        .map(
                            |(terminal, outward_elementary_carriers)| BodyEffectorDrive {
                                terminal,
                                outward_elementary_carriers,
                            },
                        )
                        .collect(),
                )
                .expect("copied-body motor admissions");
                let transition = settle_body_effector_drives(
                    &body,
                    &admitted,
                    BODY_SETTLEMENT_CLOCK_MICROSECONDS,
                )
                .expect("copied-body motor settlement");
                let learned_consequences = transition
                    .proprioceptive_consequences
                    .iter()
                    .copied()
                    .filter(|consequence| learned_axes.contains(&consequence.axis))
                    .collect::<Vec<_>>();
                let sensory_return = if learned_consequences.is_empty() || active_clock != 1 {
                    None
                } else {
                    let source = admit_articulated_body_consequence_source(
                        state.generation + active_clock,
                        &learned_consequences,
                    )
                    .expect("copied-body proprioceptive return source");
                    let reached_load_receptors = source
                        .joint_source_ports()
                        .iter()
                        .filter(|port| {
                            port.physical_quantity
                                == crate::proprioceptive_receptor_work::EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
                                && port
                                    .exact_normalized_sources
                                    .iter()
                                    .any(|sample| sample > &BigRational::zero())
                        })
                        .map(|port| {
                            let site = super::NeuronSourceSite::from_source_port(port)
                                .expect("copied-body load source site");
                            let (cohort_index, neuron_index, lineage) = successor
                                .topology_index
                                .source_location(&site)
                                .expect("copied-body load source lookup")
                                .expect("copied-body load receptor must be mounted");
                            let predecessor = &successor.cohorts[cohort_index].state.neurons()
                                [neuron_index];
                            (
                                cohort_index,
                                neuron_index,
                                lineage,
                                port.body_proprioceptor_terminal,
                                predecessor.receptor_quantum_residue.energy(),
                                predecessor.gate.open_population(),
                            )
                        })
                        .collect::<Vec<_>>();
                    let intervals = vec![(1_i64, 1_000_i64); learned_consequences.len()];
                    let admitted = admitted_episode_with_authored_intervals(&source, &intervals)
                        .expect("copied-body proprioceptive return admission");
                    let (returned_successor, returned) = successor
                        .clone()
                        .advance_admitted_transition(
                            &admitted,
                            usize::MAX,
                            false,
                            ExactRational::integer(0),
                        )
                        .expect("copied-body proprioceptive return settlement");
                    let load_receptor_returns = reached_load_receptors
                        .into_iter()
                        .map(|(cohort_index, neuron_index, lineage, terminal, before, gate_before)| {
                            let after = &returned_successor.cohorts[cohort_index].state.neurons()
                                [neuron_index];
                            let successor_residue = after.receptor_quantum_residue.energy();
                            json!({
                                "lineage": lineage_hex(lineage),
                                "terminal": format!("{terminal:?}"),
                                "predecessor_residue_zeptojoules": wide_exact_json(&before),
                                "successor_residue_zeptojoules": wide_exact_json(&successor_residue),
                                "residue_changed": successor_residue != before,
                                "predecessor_open_gate_population": gate_before.to_string(),
                                "successor_open_gate_population": after.gate.open_population().to_string(),
                            })
                        })
                        .collect::<Vec<_>>();
                    Some(json!({
                        "port_count": source.joint_source_ports().len(),
                        "occurrence_count": source.joint_source_occurrences().len(),
                        "sample_count": source.joint_source_sample_count(),
                        "nonzero_load_receptor_returns": load_receptor_returns,
                        "externally_perturbed_body_receptor_count": returned
                            .externally_perturbed_body_receptor_count,
                        "physically_transitioned_neuron_count": returned
                            .physically_transitioned_neuron_count,
                        "dsf_delivery_count": returned.dsf_delivery_count,
                    }))
                };
                let consequences = transition
                .proprioceptive_consequences
                .iter()
                .map(|consequence| json!({
                    "axis": format!("{:?}", consequence.axis),
                    "predecessor_position": consequence.predecessor_position,
                    "successor_position": consequence.successor_position,
                    "signed_displacement": consequence.signed_displacement,
                    "toward_minimum_carriers": consequence.toward_minimum_carriers.to_string(),
                    "toward_maximum_carriers": consequence.toward_maximum_carriers.to_string(),
                    "applied_displacement_quanta": consequence
                        .applied_displacement_quanta
                        .to_string(),
                    "stalled_carriers": consequence.stalled_carriers.to_string(),
                }))
                .collect::<Vec<_>>();
                let acoustic = settle_native_articulatory_interval(
                    transition.successor,
                    &transition.proprioceptive_consequences,
                    respiratory_efferent_carriers,
                    4_000,
                )
                .expect("copied-body acoustic settlement");
                let acoustic_peak = acoustic
                    .radiated_pressure_pcm
                    .iter()
                    .map(|sample| sample.unsigned_abs())
                    .max()
                    .unwrap_or(0);
                let acoustic_nonzero_samples = acoustic
                    .radiated_pressure_pcm
                    .iter()
                    .filter(|sample| **sample != 0)
                    .count();
                articulated_body = Some(acoustic.successor_body);
                Some(json!({
                    "reached_terminal_count": transition.reached_terminal_count,
                    "consequences": consequences,
                    "sensory_return": sensory_return,
                    "respiratory_efferent_carriers": respiratory_efferent_carriers.to_string(),
                    "acoustic_peak_pressure": acoustic_peak,
                    "acoustic_nonzero_samples": acoustic_nonzero_samples,
                }))
            }
        };
        let motor_recruitments = observation
            .motor_unit_recruitments
            .iter()
            .map(|event| {
                json!({
                    "lineage": lineage_hex(event.neuron_lineage),
                    "terminal": format!("{:?}", event.body_effector_terminal),
                    "outward_elementary_carriers":
                        event.outward_elementary_carriers.to_string(),
                    "preparation_transfers": event
                        .preparation_transfers
                        .iter()
                        .map(|preparation| json!({
                            "sender": lineage_hex(preparation.transfer.sender),
                            "sender_layer": preparation.sender_layer,
                            "receiver": lineage_hex(preparation.transfer.receiver),
                            "transferred_whole_carriers": preparation
                                .transfer
                                .transferred_whole_carriers
                                .to_string(),
                        }))
                        .collect::<Vec<_>>(),
                })
            })
            .collect::<Vec<_>>();
        let next_frontier = observation.next_active_frontier.clone();
        let articulatory_recruitments = observation
            .articulatory_unit_recruitments
            .iter()
            .map(|event| {
                json!({
                    "lineage": lineage_hex(event.neuron_lineage),
                    "topology_index": event.topology_index,
                    "outward_elementary_carriers": event.outward_elementary_carriers.to_string(),
                    "preparation_transfers": event
                        .preparation_transfers
                        .iter()
                        .map(|preparation| json!({
                            "sender": lineage_hex(preparation.transfer.sender),
                            "sender_layer": preparation.sender_layer,
                            "receiver": lineage_hex(preparation.transfer.receiver),
                            "transferred_whole_carriers": preparation
                                .transfer
                                .transferred_whole_carriers
                                .to_string(),
                        }))
                        .collect::<Vec<_>>(),
                })
            })
            .collect::<Vec<_>>();
        clocks.push(json!({
            "clock": active_clock,
            "input_frontier_count": frontier.len(),
            "input_lineage_count": reached_lineages.len(),
            "changed_neuron_count": changed.len(),
            "settled_transfer_count": observation.settled_directed_transfers.len(),
            "bridge_transfers": bridge_transfers,
            "ordering_incident_transfers": ordering_incident_transfers,
            "three_terminal_route_range": three_terminal_route_range,
            "input_frontier_ordering_lineages": learned_ordering_lineages
                .iter()
                .copied()
                .filter(|lineage| reached_lineages.contains(lineage))
                .map(lineage_hex)
                .collect::<Vec<_>>(),
            "motor_recruitment_count": motor_recruitments.len(),
            "motor_recruitments": motor_recruitments,
            "articulated_body_transition": body_transition,
            "root_yaw_recruitment_count": observation.root_yaw_unit_recruitments.len(),
            "root_translation_recruitment_count":
                observation.root_translation_unit_recruitments.len(),
            "articulatory_recruitment_count":
                observation.articulatory_unit_recruitments.len(),
            "articulatory_recruitments": articulatory_recruitments,
            "next_frontier_count": next_frontier.len(),
        }));
        frontier = next_frontier;
    }
    json!({
        "synthetic_seed_count": 0,
        "maximum_clocks": maximum_clocks,
        "initial_frontier_count": state.active_electrical_frontier.len(),
        "clocks": clocks,
    })
}

/// Energy-only feasibility range for one future directional synaptic boundary.
/// It does not claim the inward transport is currently authored: it moves a
/// bounded range of whole carriers on a disposable copied neuron, measures the
/// exact retained membrane-plus-gradient work change, and then asks the
/// already-live efferent terminal law whether that prepared state can return
/// them as output.
fn motor_inward_preparation_energy_range_json(state: &ResidentCognitiveFormationState) -> Value {
    let topology = state.topology_index.clone();
    let mut motor_lineages = state
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = state.electrical_fabric.lineages()[left];
            let right_lineage = state.electrical_fabric.lineages()[right];
            match (
                topology.layer_of(left_lineage),
                topology.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some(right_lineage),
                (Some(12), Some(11)) => Some(left_lineage),
                _ => None,
            }
        })
        .collect::<Vec<_>>();
    motor_lineages.sort_unstable();
    motor_lineages.dedup();
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let extents = [1_u128, 2, 4, 8, 16, 24, 32, 64];
    let motors = motor_lineages
        .into_iter()
        .map(|motor_lineage| {
            let (anatomy, predecessor) = state
                .cohorts
                .iter()
                .find_map(|cohort| {
                    cohort
                        .anatomy
                        .neuron_lineages()
                        .iter()
                        .position(|lineage| *lineage == motor_lineage)
                        .map(|index| {
                            (
                                &cohort.anatomy.neuron_anatomies()[index],
                                &cohort.state.neurons()[index],
                            )
                        })
                })
                .expect("learned motor lineage present");
            let predecessor_work =
                crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                    anatomy,
                    predecessor,
                )
                .expect("predecessor motor work");
            let samples = extents
                .iter()
                .copied()
                .map(|extent| {
                    let inward = -i128::try_from(extent).expect("probe extent width");
                    let prepared = crate::complete_neuron::settle_membrane_pump_transport(
                        anatomy,
                        predecessor,
                        inward,
                        None,
                        super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                    )
                    .expect("probe inward preparation");
                    let prepared_work =
                        crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                            anatomy, &prepared,
                        )
                        .expect("prepared motor work");
                    let work_delta = &prepared_work - &predecessor_work;
                    let discharge = crate::complete_neuron::settle_efferent_terminal_transport(
                        anatomy,
                        &prepared,
                        extent,
                        super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                    )
                    .expect("prepared terminal discharge");
                    json!({
                        "inward_elementary_carriers": extent.to_string(),
                        "work_delta_zeptojoules": wide_exact_json(&work_delta),
                        "work_increased": work_delta > BigRational::zero(),
                        "prepared_membrane_charge": prepared
                            .separated_elementary_charges()
                            .to_string(),
                        "terminal_discharged_carriers": discharge
                            .as_ref()
                            .map(|(_, carriers, _)| carriers.to_string()),
                        "terminal_released_work_zeptojoules": discharge
                            .as_ref()
                            .map(|(_, _, work)| wide_exact_json(work)),
                    })
                })
                .collect::<Vec<_>>();
            json!({
                "motor_lineage": lineage_hex(motor_lineage),
                "predecessor_membrane_charge": predecessor
                    .separated_elementary_charges()
                    .to_string(),
                "samples": samples,
            })
        })
        .collect::<Vec<_>>();
    json!({
        "authored_transport": false,
        "purpose": "exact energy feasibility only",
        "inward_extent_range": extents,
        "motors": motors,
    })
}

fn severed_learned_motor_copy(
    state: &ResidentCognitiveFormationState,
) -> (ResidentCognitiveFormationState, usize) {
    let layer_of = |lineage| state.topology_index.layer_of(lineage);
    let removed = state
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left = state.electrical_fabric.lineages()[left];
            let right = state.electrical_fabric.lineages()[right];
            matches!(
                (layer_of(left), layer_of(right)),
                (Some(11), Some(12)) | (Some(12), Some(11))
            )
            .then_some(if left < right {
                (left, right)
            } else {
                (right, left)
            })
        })
        .collect::<std::collections::BTreeSet<_>>();
    let mut severed = state.clone();
    severed.electrical_fabric = severed
        .electrical_fabric
        .without_contact_pairs(&removed)
        .expect("test bridge severing");
    let keep_frontier = |entry: &super::ActiveElectricalFrontierEntry| {
        let Some(sender) = entry.sender() else {
            return true;
        };
        let receiver = entry.receiver();
        let pair = if sender < receiver {
            (sender, receiver)
        } else {
            (receiver, sender)
        };
        !removed.contains(&pair)
    };
    severed.active_electrical_frontier = severed
        .active_electrical_frontier
        .iter()
        .copied()
        .filter(keep_frontier)
        .collect::<Vec<_>>()
        .into_boxed_slice();
    severed.preceding_active_electrical_frontier = severed
        .preceding_active_electrical_frontier
        .iter()
        .copied()
        .filter(keep_frontier)
        .collect::<Vec<_>>()
        .into_boxed_slice();
    severed.older_active_electrical_frontier = severed
        .older_active_electrical_frontier
        .iter()
        .copied()
        .filter(keep_frontier)
        .collect::<Vec<_>>()
        .into_boxed_slice();
    severed.topology_index = std::sync::Arc::new(
        super::ResidentTopologyIndex::build(&severed.cohorts, &severed.electrical_fabric)
            .expect("test severed topology"),
    );
    (severed, removed.len())
}

/// Run the production one-carrier transduction through the complete copied-body
/// three-clock settlement, then repeat after physically severing every learned
/// L11/L12 bridge. Both successors are disposable in-memory copies.
fn integrated_motor_transduction_falsifier_json(
    state: &ResidentCognitiveFormationState,
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    let connected = retained_frontier_motor_range_json(state, articulated_body, 3);
    let (severed, severed_bridge_count) = severed_learned_motor_copy(state);
    let disconnected = retained_frontier_motor_range_json(&severed, articulated_body, 3);
    json!({
        "production_compiled": true,
        "connected": connected,
        "severed": disconnected,
        "severed_bridge_count": severed_bridge_count,
    })
}

fn allocate_source_work_by_learned_conductance(
    source_work: &BigRational,
    source_path_conductance: ExactRational,
    routes: &[([u8; 16], ExactRational)],
) -> std::collections::BTreeMap<[u8; 16], BigRational> {
    let exact_to_wide = |value: ExactRational| {
        let (numerator, denominator) = value.parts();
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    };
    let learned_conductance = routes
        .iter()
        .map(|(_, conductance)| exact_to_wide(*conductance))
        .filter(|conductance| conductance > &BigRational::zero())
        .fold(BigRational::zero(), |sum, conductance| sum + conductance);
    let source_conductance = exact_to_wide(source_path_conductance);
    let total_conductance = &source_conductance + learned_conductance;
    let mut allocated = std::collections::BTreeMap::new();
    if source_work <= &BigRational::zero()
        || source_conductance <= BigRational::zero()
        || total_conductance.is_zero()
    {
        return allocated;
    }
    for (motor, conductance) in routes {
        let conductance = exact_to_wide(*conductance);
        if conductance <= BigRational::zero() {
            continue;
        }
        *allocated.entry(*motor).or_insert_with(BigRational::zero) +=
            source_work * conductance / &total_conductance;
    }
    allocated
}

fn effective_conductance_for_bond(
    state: &ResidentCognitiveFormationState,
    bond: crate::physical_mosaic::StablePhysicalBondReference,
) -> ExactRational {
    let topology = state
        .topology_index
        .contacts
        .iter()
        .copied()
        .find(|entry| entry.stable_bond == bond)
        .expect("range-probe source bond remains mounted");
    let edge = super::materialize_resident_contact_edge(
        topology,
        &state.cohorts,
        &state.electrical_fabric,
    )
    .expect("range-probe source contact materializes");
    edge.anatomy
        .effective_conductance(&edge.state)
        .expect("range-probe source contact state matches anatomy")
}

fn source_work_permutation_falsifier_json() -> Value {
    let lineage = |suffix: u8| {
        let mut value = [0_u8; 16];
        value[15] = suffix;
        value
    };
    let source_a = BigRational::new(BigInt::from(3_u8), BigInt::from(7_u8));
    let source_b = BigRational::new(BigInt::from(5_u8), BigInt::from(11_u8));
    let total_forward = &source_a + &source_b;
    let total_reversed = &source_b + &source_a;
    let routes_forward = vec![
        (lineage(1), ExactRational::integer(2)),
        (lineage(2), ExactRational::integer(3)),
        (lineage(1), ExactRational::integer(5)),
        (lineage(3), ExactRational::integer(0)),
    ];
    let routes_reversed = routes_forward.iter().copied().rev().collect::<Vec<_>>();
    let source_conductance = ExactRational::integer(7);
    let forward = allocate_source_work_by_learned_conductance(
        &total_forward,
        source_conductance,
        &routes_forward,
    );
    let reversed = allocate_source_work_by_learned_conductance(
        &total_reversed,
        source_conductance,
        &routes_reversed,
    );
    let encode = |allocated: &std::collections::BTreeMap<[u8; 16], BigRational>| {
        allocated
            .iter()
            .map(|(motor, work)| {
                json!({
                    "motor_suffix": motor[15],
                    "allocated_source_work_zeptojoules": wide_exact_json(work),
                })
            })
            .collect::<Vec<_>>()
    };
    let allocated_total = forward
        .values()
        .cloned()
        .fold(BigRational::zero(), |sum, work| sum + work);
    let retained_source_heat = &total_forward - &allocated_total;
    json!({
        "multiple_sources": 2,
        "multiple_branches": routes_forward.len(),
        "converging_contacts_on_motor_one": 2,
        "zero_conductance_motor_absent": !forward.contains_key(&lineage(3)),
        "source_order_and_branch_order_invariant": forward == reversed,
        "allocated_plus_retained_heat_equals_source_work":
            &allocated_total + &retained_source_heat == total_forward,
        "retained_source_heat_zeptojoules": wide_exact_json(&retained_source_heat),
        "forward": encode(&forward),
        "reversed": encode(&reversed),
    })
}

/// Candidate 47E's conservation-correct motor settlement on one disposable
/// copied neuron.  The mounted pump determines direction and its whole-carrier
/// bound.  Existing recovery material pays as much of the exact stored-work
/// increase as it can; exact work released by the connected L11 source pays
/// only the shortfall.  That source contribution is therefore unavailable for
/// heat export.  No source carrier enters L12 and available+spent recovery
/// material is unchanged.
fn source_work_assisted_motor_sample_json(
    cohort: &super::ResidentReachedCohort,
    motor_neuron: usize,
    offered_source_work: &BigRational,
    interval_microseconds: u32,
    exhaust_motor_carriers: bool,
) -> Value {
    let exact_to_wide = |value: ExactRational| {
        let (numerator, denominator) = value.parts();
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    };
    let wide_to_exact = |value: &BigRational| {
        Some(ExactRational::new(value.numer().to_i128()?, value.denom().to_u128()?).ok()?)
    };
    let anatomy = &cohort.anatomy.neuron_anatomies()[motor_neuron];
    let resident_predecessor = &cohort.state.neurons()[motor_neuron];
    let exhausted_predecessor = exhaust_motor_carriers.then(|| {
        crate::complete_neuron::with_held_membrane_and_carriers(
            resident_predecessor,
            resident_predecessor.membrane_state(),
            0,
            0,
        )
    });
    let predecessor = exhausted_predecessor
        .as_ref()
        .unwrap_or(resident_predecessor);
    let reservoir_anatomy = cohort.anatomy.recovery_fluid_reservoir_anatomy();
    let predecessor_reservoir = cohort.state.recovery_fluid();
    let (_, spent_capacity, _) = reservoir_anatomy.capacities();
    let (available, spent, thermal) = predecessor_reservoir.physical_parts();
    let local_budget =
        exact_to_wide(available).min(exact_to_wide(spent_capacity) - exact_to_wide(spent));
    let source_budget = offered_source_work.clone().max(BigRational::zero());
    let total_budget = &local_budget + &source_budget;
    let bound = crate::complete_neuron::membrane_gradient_pump_charge_bound(
        anatomy,
        predecessor,
        interval_microseconds,
    )
    .expect("copied motor pump bound");
    let predecessor_work =
        crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(anatomy, predecessor)
            .expect("copied motor predecessor work");
    let direction_negative = bound.charges.is_negative();
    let full_magnitude = bound.charges.unsigned_abs();
    let reversal = anatomy.gate_reversal_potential_millivolts();
    let predecessor_drive = predecessor
        .membrane_state()
        .potential_millivolts(anatomy.capacitance())
        .expect("copied motor predecessor potential")
        .checked_sub(reversal)
        .expect("copied motor predecessor drive");
    let predecessor_sign = predecessor_drive.parts().0.signum();

    let mut lower = 0_u128;
    let mut upper = full_magnitude;
    let mut accepted_state = predecessor.clone();
    let mut accepted_work = BigRational::zero();
    let mut accepted_local = BigRational::zero();
    let mut accepted_source = BigRational::zero();
    while lower < upper {
        let middle = lower + (upper - lower + 1) / 2;
        let magnitude = match i128::try_from(middle) {
            Ok(value) => value,
            Err(_) => {
                upper = middle - 1;
                continue;
            }
        };
        let signed = if direction_negative {
            -magnitude
        } else {
            magnitude
        };
        let candidate = crate::complete_neuron::settle_membrane_pump_transport(
            anatomy,
            predecessor,
            signed,
            (middle == full_magnitude)
                .then_some(bound.successor_phase)
                .flatten(),
            interval_microseconds,
        )
        .expect("copied motor candidate transport");
        let successor_drive = candidate
            .membrane_state()
            .potential_millivolts(anatomy.capacitance())
            .expect("copied motor successor potential")
            .checked_sub(reversal)
            .expect("copied motor successor drive");
        let successor_sign = successor_drive.parts().0.signum();
        let stays_on_reversal_side = successor_sign == 0 || successor_sign == predecessor_sign;
        let successor_work = crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
            anatomy, &candidate,
        )
        .expect("copied motor successor work");
        let work = successor_work - &predecessor_work;
        if !stays_on_reversal_side || work <= BigRational::zero() || work > total_budget {
            upper = middle - 1;
            continue;
        }
        let local = work.clone().min(local_budget.clone());
        let source = &work - &local;
        let Some(local_exact) = wide_to_exact(&local) else {
            upper = middle - 1;
            continue;
        };
        let Ok(successor_available) = available.checked_sub(local_exact) else {
            upper = middle - 1;
            continue;
        };
        let Ok(successor_spent) = spent.checked_add(local_exact) else {
            upper = middle - 1;
            continue;
        };
        if crate::recovery_fluid_contact::RecoveryFluidReservoirState::new(
            reservoir_anatomy,
            successor_available,
            successor_spent,
            thermal,
        )
        .is_err()
        {
            upper = middle - 1;
            continue;
        }
        lower = middle;
        accepted_state = candidate;
        accepted_work = work;
        accepted_local = local;
        accepted_source = source;
    }

    let terminal = crate::complete_neuron::settle_efferent_terminal_transport(
        anatomy,
        &accepted_state,
        lower,
        interval_microseconds,
    )
    .expect("copied motor terminal settlement");
    let source_heat_remaining = &source_budget - &accepted_source;
    let recovery_material_before = exact_to_wide(available) + exact_to_wide(spent);
    let recovery_material_after = recovery_material_before.clone();
    json!({
        "interval_microseconds": interval_microseconds,
        "motor_carriers_artificially_exhausted": exhaust_motor_carriers,
        "offered_source_work_zeptojoules": wide_exact_json(&source_budget),
        "local_recovery_work_contribution_zeptojoules": wide_exact_json(&accepted_local),
        "source_work_contribution_zeptojoules": wide_exact_json(&accepted_source),
        "source_heat_remaining_zeptojoules": wide_exact_json(&source_heat_remaining),
        "pumped_elementary_carriers": if direction_negative {
            format!("-{}", lower)
        } else {
            lower.to_string()
        },
        "pump_work_zeptojoules": wide_exact_json(&accepted_work),
        "work_conservation_exact": accepted_work == accepted_local + accepted_source,
        "recovery_material_before_zeptojoules": wide_exact_json(&recovery_material_before),
        "recovery_material_after_zeptojoules": wide_exact_json(&recovery_material_after),
        "recovery_material_conserved": recovery_material_before == recovery_material_after,
        "terminal_discharged_carriers": terminal
            .as_ref()
            .map(|(_, carriers, _)| carriers.to_string()),
    })
}

/// Measurement-only candidate-47E regime map. The copied body's retained
/// frontier supplies each L11 founding event and its exact released work. The
/// connected L12 motor keeps its own carrier material and uses source work
/// only as a conserved contribution to its mounted reversal-gradient pump.
/// No production state is changed.
fn source_work_to_motor_reservoir_range_json(state: &ResidentCognitiveFormationState) -> Value {
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let exact_to_wide = |value: ExactRational| {
        let (numerator, denominator) = value.parts();
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    };

    let mut learned_routes =
        std::collections::BTreeMap::<[u8; 16], Vec<([u8; 16], ExactRational)>>::new();
    for ((left, right), (anatomy, contact_state)) in
        state.electrical_fabric.contact_endpoints().zip(
            state
                .electrical_fabric
                .anatomy()
                .contact_anatomies()
                .iter()
                .zip(state.electrical_fabric.state().contact_states()),
        )
    {
        let left_lineage = state.electrical_fabric.lineages()[left];
        let right_lineage = state.electrical_fabric.lineages()[right];
        let route = match (
            state.topology_index.layer_of(left_lineage),
            state.topology_index.layer_of(right_lineage),
        ) {
            (Some(11), Some(12)) => Some((left_lineage, right_lineage)),
            (Some(12), Some(11)) => Some((right_lineage, left_lineage)),
            _ => None,
        };
        if let Some((ordering, motor)) = route {
            learned_routes.entry(ordering).or_default().push((
                motor,
                anatomy
                    .effective_conductance(contact_state)
                    .expect("copied learned-contact state matches anatomy"),
            ));
        }
    }
    for routes in learned_routes.values_mut() {
        routes.sort_unstable_by_key(|(motor, _)| *motor);
    }

    let mut successor = state.clone();
    let mut frontier = successor.active_electrical_frontier.to_vec();
    let mut residency = None;
    let mut route_results = Vec::new();
    for active_clock in 1_u64..=3 {
        let mut reached_lineages = frontier
            .iter()
            .flat_map(|entry| entry.affected_lineages().into_iter().flatten())
            .collect::<Vec<_>>();
        reached_lineages.sort_unstable();
        reached_lineages.dedup();
        let predecessor = successor.clone();
        let topology = successor.topology_index.clone();
        let mut changed = std::collections::BTreeSet::new();
        let resting = successor
            .resting_population
            .as_ref()
            .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
            .unwrap_or(0);
        let observation = super::settle_internal_contact_interval(
            &mut successor.cohorts,
            &mut successor.electrical_fabric,
            &topology,
            successor.vocal_articulatory_effector_lineage,
            &frontier,
            &[],
            &reached_lineages,
            &reached_lineages,
            &[],
            &[],
            &mut changed,
            successor.generation + active_clock,
            resting,
            &mut residency,
            &std::collections::BTreeMap::new(),
            &[],
            &[],
            ExactRational::integer(0),
            true,
        )
        .expect("copied retained frontier settles for source-work range");

        let mut bad_bridge_extent = std::collections::BTreeMap::<[u8; 16], u128>::new();
        for transfer in &observation.settled_directed_transfers {
            if topology.layer_of(transfer.sender) == Some(11)
                && topology.layer_of(transfer.receiver) == Some(12)
            {
                *bad_bridge_extent.entry(transfer.sender).or_default() = bad_bridge_extent
                    .get(&transfer.sender)
                    .copied()
                    .unwrap_or(0)
                    .checked_add(transfer.transferred_whole_carriers)
                    .expect("test bridge extent width");
            }
        }

        let mut motor_work =
            std::collections::BTreeMap::<[u8; 16], (usize, usize, BigRational, Vec<Value>)>::new();
        for (ordering, diverted_extent) in bad_bridge_extent {
            let source_edges = observation
                .settled_directed_transfers
                .iter()
                .filter(|transfer| {
                    transfer.sender == ordering && topology.layer_of(transfer.receiver) == Some(7)
                })
                .collect::<Vec<_>>();
            if source_edges.len() != 1 {
                route_results.push(json!({
                    "active_clock": active_clock,
                    "ordering_lineage": lineage_hex(ordering),
                    "error": "candidate requires an order-independent multi-source reconciliation",
                    "source_edge_count": source_edges.len(),
                }));
                continue;
            }
            let source = source_edges[0];
            let original_extent = source
                .transferred_whole_carriers
                .checked_add(diverted_extent)
                .expect("original source extent width");
            let ordering_flat = predecessor
                .topology_index
                .flat_for_lineage(ordering)
                .expect("ordering lineage present");
            let receiver_flat = predecessor
                .topology_index
                .flat_for_lineage(source.receiver)
                .expect("source receiver lineage present");
            let (ordering_cohort, ordering_neuron, _) =
                predecessor.topology_index.flat_locations[ordering_flat];
            let (receiver_cohort, receiver_neuron, _) =
                predecessor.topology_index.flat_locations[receiver_flat];
            let source_work =
                crate::sparse_electrical_contact::probe_directed_contact_work_zeptojoules(
                    &predecessor.cohorts[ordering_cohort]
                        .anatomy
                        .neuron_anatomies()[ordering_neuron],
                    &predecessor.cohorts[ordering_cohort].state.neurons()[ordering_neuron],
                    &predecessor.cohorts[receiver_cohort]
                        .anatomy
                        .neuron_anatomies()[receiver_neuron],
                    &predecessor.cohorts[receiver_cohort].state.neurons()[receiver_neuron],
                    original_extent,
                )
                .expect("copied source work is exact");
            let source_conductance = effective_conductance_for_bond(&predecessor, source.bond);
            let routes = learned_routes
                .get(&ordering)
                .expect("observed bridge has retained learned route");
            let allocation = allocate_source_work_by_learned_conductance(
                &source_work,
                source_conductance,
                routes,
            );
            for (motor, branch_share) in allocation {
                let motor_flat = predecessor
                    .topology_index
                    .flat_for_lineage(motor)
                    .expect("learned motor lineage present");
                let (motor_cohort, motor_neuron, _) =
                    predecessor.topology_index.flat_locations[motor_flat];
                let motor_conductance = routes
                    .iter()
                    .filter(|(candidate, _)| *candidate == motor)
                    .fold(BigRational::zero(), |sum, (_, conductance)| {
                        sum + exact_to_wide(*conductance)
                    });
                let contribution = json!({
                    "active_clock": active_clock,
                    "ordering_lineage": lineage_hex(ordering),
                    "ordering_psi_ternary_winding_state":
                        mounted_neuron_ternary_winding_state_json(&predecessor, ordering),
                    "founding_receiver_lineage": lineage_hex(source.receiver),
                    "original_source_carriers": original_extent.to_string(),
                    "source_released_work_zeptojoules": wide_exact_json(&source_work),
                    "source_path_effective_conductance_picosiemens":
                        exact_json(source_conductance),
                    "motor_lineage": lineage_hex(motor),
                    "learned_contact_effective_conductance_picosiemens":
                        wide_exact_json(&motor_conductance),
                    "parallel_conductance_zeptojoules_share": wide_exact_json(&branch_share),
                });
                let entry = motor_work.entry(motor).or_insert_with(|| {
                    (motor_cohort, motor_neuron, BigRational::zero(), Vec::new())
                });
                assert_eq!(entry.0, motor_cohort, "motor cohort is stable");
                assert_eq!(entry.1, motor_neuron, "motor index is stable");
                entry.2 += &branch_share;
                entry.3.push(contribution);
            }
        }
        for (motor, (motor_cohort, motor_neuron, total_source_work, contributions)) in motor_work {
            let cohort = &predecessor.cohorts[motor_cohort];
            let predecessor_reservoir = cohort.state.recovery_fluid();
            let reservoir_anatomy = cohort.anatomy.recovery_fluid_reservoir_anatomy();
            let (available_capacity, spent_capacity, _) = reservoir_anatomy.capacities();
            let (available, spent, thermal) = predecessor_reservoir.physical_parts();
            let scales = [(0_i64, 1_i64), (1, 4), (1, 2), (1, 1), (2, 1), (4, 1)];
            let intervals = [62_500_u32, 125_000, 250_000, 500_000];
            let samples = scales
                .into_iter()
                .flat_map(|(scale_numerator, scale_denominator)| {
                    intervals.into_iter().map({
                        let total_source_work = total_source_work.clone();
                        move |interval_microseconds| {
                            let offered = total_source_work.clone() * BigInt::from(scale_numerator)
                                / BigInt::from(scale_denominator);
                            let mut sample = source_work_assisted_motor_sample_json(
                                cohort,
                                motor_neuron,
                                &offered,
                                interval_microseconds,
                                false,
                            );
                            sample["source_scale"] =
                                json!(format!("{scale_numerator}/{scale_denominator}"));
                            sample
                        }
                    })
                })
                .collect::<Vec<_>>();
            let exhausted_motor_carriers = source_work_assisted_motor_sample_json(
                cohort,
                motor_neuron,
                &total_source_work,
                250_000,
                true,
            );
            route_results.push(json!({
                "active_clock": active_clock,
                "motor_lineage": lineage_hex(motor),
                "contributing_route_count": contributions.len(),
                "contributing_routes": contributions,
                "total_source_work_zeptojoules": wide_exact_json(&total_source_work),
                "predecessor_available_work_zeptojoules": exact_json(available),
                "predecessor_spent_work_zeptojoules": exact_json(spent),
                "predecessor_thermal_work_zeptojoules": exact_json(thermal),
                "available_capacity_zeptojoules": exact_json(available_capacity),
                "spent_capacity_zeptojoules": exact_json(spent_capacity),
                "exhausted_motor_carriers_control": exhausted_motor_carriers,
                "samples": samples,
            }));
        }
        frontier = observation.next_active_frontier;
    }
    json!({
        "measurement_only": true,
        "production_compiled": false,
        "candidate": "47F absolute source/load conductance splits source work",
        "source_carriers_enter_motor": false,
        "a0116_transition_work_phase_reused": false,
        "recovery_material_created": false,
        "source_work_diverted_from_heat_when_spent": true,
        "synthetic_order_invariance": source_work_permutation_falsifier_json(),
        "route_results": route_results,
    })
}

/// Candidate-47I real-path census. Unlike the earlier 47F measurement model,
/// this invokes the production contact settlement and reports the learned
/// work that the mounted motor's intrinsic gate actually accepted. The copied
/// resident state alone supplies topology, conductance, source transition,
/// motor anatomy, and predecessor residue.
fn production_learned_motor_work_range_json(state: &ResidentCognitiveFormationState) -> Value {
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let mut successor = state.clone();
    let mut frontier = successor.active_electrical_frontier.to_vec();
    let mut residency = None;
    let mut route_results = Vec::new();
    let mut learned_bridge_carrier_transfers = 0_usize;
    let mut motor_recruitments = Vec::new();

    for active_clock in 1_u64..=3 {
        let mut reached_lineages = frontier
            .iter()
            .flat_map(|entry| entry.affected_lineages().into_iter().flatten())
            .collect::<Vec<_>>();
        reached_lineages.sort_unstable();
        reached_lineages.dedup();
        let topology = successor.topology_index.clone();
        let mut changed = std::collections::BTreeSet::new();
        let resting = successor
            .resting_population
            .as_ref()
            .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
            .unwrap_or(0);
        let observation = super::settle_internal_contact_interval(
            &mut successor.cohorts,
            &mut successor.electrical_fabric,
            &topology,
            successor.vocal_articulatory_effector_lineage,
            &frontier,
            &[],
            &reached_lineages,
            &reached_lineages,
            &[],
            &[],
            &mut changed,
            successor.generation + active_clock,
            resting,
            &mut residency,
            &std::collections::BTreeMap::new(),
            &[],
            &[],
            ExactRational::integer(0),
            true,
        )
        .expect("copied retained frontier settles through production learned-work law");

        learned_bridge_carrier_transfers += observation
            .settled_directed_transfers
            .iter()
            .filter(|transfer| {
                matches!(
                    (
                        topology.layer_of(transfer.sender),
                        topology.layer_of(transfer.receiver)
                    ),
                    (Some(11), Some(12)) | (Some(12), Some(11))
                )
            })
            .count();

        for preparation in &observation.learned_motor_work_preparations {
            let offer_balance_exact = preparation.total_offered_work_zeptojoules
                == preparation.accepted_work_zeptojoules.clone()
                    + preparation.retained_source_heat_zeptojoules.clone();
            let gate_balance_exact = preparation.predecessor_residue_zeptojoules.clone()
                + preparation.accepted_work_zeptojoules.clone()
                == preparation.delivered_gate_work_zeptojoules.clone()
                    + preparation.successor_residue_zeptojoules.clone()
                    + preparation.residue_narrowing_heat_zeptojoules.clone();
            route_results.push(json!({
                "active_clock": active_clock,
                "motor_lineage": lineage_hex(preparation.motor_lineage),
                "contributing_route_count": preparation.routes.len(),
                "contributing_routes": preparation.routes.iter().map(|route| json!({
                    "ordering_lineage": lineage_hex(route.ordering_lineage),
                    "founding_receiver_lineage": lineage_hex(route.founding_receiver_lineage),
                    "offered_work_zeptojoules": wide_exact_json(&route.offered_work_zeptojoules),
                })).collect::<Vec<_>>(),
                "total_source_work_zeptojoules":
                    wide_exact_json(&preparation.total_offered_work_zeptojoules),
                "accepted_work_zeptojoules":
                    wide_exact_json(&preparation.accepted_work_zeptojoules),
                "predecessor_residue_zeptojoules":
                    wide_exact_json(&preparation.predecessor_residue_zeptojoules),
                "successor_residue_zeptojoules":
                    wide_exact_json(&preparation.successor_residue_zeptojoules),
                "delivered_gate_work_zeptojoules":
                    wide_exact_json(&preparation.delivered_gate_work_zeptojoules),
                "retained_source_heat_zeptojoules":
                    wide_exact_json(&preparation.retained_source_heat_zeptojoules),
                "residue_narrowing_heat_zeptojoules":
                    wide_exact_json(&preparation.residue_narrowing_heat_zeptojoules),
                "offer_balance_exact": offer_balance_exact,
                "gate_input_balance_exact": gate_balance_exact,
            }));
        }
        motor_recruitments.extend(observation.motor_unit_recruitments.iter().map(|event| {
            json!({
                "active_clock": active_clock,
                "motor_lineage": lineage_hex(event.neuron_lineage),
                "outward_elementary_carriers": event.outward_elementary_carriers.to_string(),
                "learned_work_preparation_count": event.learned_work_preparations.len(),
            })
        }));
        frontier = observation.next_active_frontier;
    }

    json!({
        "measurement_only": true,
        "production_compiled": true,
        "candidate": "47I production learned-contact work transduction",
        "source_carriers_enter_motor": false,
        "learned_bridge_carrier_transfer_count": learned_bridge_carrier_transfers,
        "route_results": route_results,
        "motor_recruitments": motor_recruitments,
    })
}

/// Re-present one causal occurrence already retained by the copied task-1429
/// body while carrying forward only the receiving motors' physical states.
/// Each presentation traverses the production sparse-contact and neuron
/// settlement. Resetting the source side makes this a controlled repeated-
/// experience falsifier, not an autonomy or natural-frequency claim.
fn production_replayed_motor_discharge_json(
    state: &ResidentCognitiveFormationState,
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let mut learned_motors = std::collections::BTreeSet::new();
    for (left, right) in state.electrical_fabric.contact_endpoints() {
        let left_lineage = state.electrical_fabric.lineages()[left];
        let right_lineage = state.electrical_fabric.lineages()[right];
        match (
            state.topology_index.layer_of(left_lineage),
            state.topology_index.layer_of(right_lineage),
        ) {
            (Some(11), Some(12)) => {
                learned_motors.insert(right_lineage);
            }
            (Some(12), Some(11)) => {
                learned_motors.insert(left_lineage);
            }
            _ => {}
        }
    }
    let mut carried_states = learned_motors
        .iter()
        .map(|lineage| {
            let (cohort_index, neuron_index) = mounted_neuron_location(state, *lineage);
            (
                *lineage,
                state.cohorts[cohort_index].state.neurons()[neuron_index].clone(),
            )
        })
        .collect::<std::collections::BTreeMap<_, _>>();
    let mut first_discharges = std::collections::BTreeMap::<[u8; 16], Value>::new();
    let mut first_vocal_recruitments: Vec<MotorUnitRecruitment> = Vec::new();
    let mut first_vocal_articulatory_recruitments = Vec::new();
    let mut all_offer_balances_exact = true;
    let mut all_gate_balances_exact = true;
    let mut learned_bridge_carrier_transfer_count = 0_usize;
    let mut completed_events = 0_u32;
    let mut cold_midpoint_exact = false;
    let mut natural_continuation = None;

    for repeated_event in 1_u32..=256 {
        let mut trial = state.clone();
        let mut replacements_by_cohort = std::collections::BTreeMap::<
            usize,
            Vec<(usize, crate::complete_neuron::NeuronPhysicalState)>,
        >::new();
        for (lineage, motor_state) in &carried_states {
            let (cohort_index, neuron_index) = mounted_neuron_location(&trial, *lineage);
            replacements_by_cohort
                .entry(cohort_index)
                .or_default()
                .push((neuron_index, motor_state.clone()));
        }
        for (cohort_index, replacements) in replacements_by_cohort {
            trial.cohorts[cohort_index].state = trial.cohorts[cohort_index]
                .state
                .with_replaced_neurons(&replacements)
                .expect("controlled copied motor-state carry")
                .into();
        }

        let topology = trial.topology_index.clone();
        let mut frontier = trial.active_electrical_frontier.to_vec();
        let mut residency = None;
        let mut event_motor_recruitments = Vec::new();
        let mut event_articulatory_recruitments = Vec::new();
        for active_clock in 1_u64..=2 {
            let mut reached_lineages = frontier
                .iter()
                .flat_map(|entry| entry.affected_lineages().into_iter().flatten())
                .collect::<Vec<_>>();
            reached_lineages.sort_unstable();
            reached_lineages.dedup();
            let mut changed = std::collections::BTreeSet::new();
            let resting = trial
                .resting_population
                .as_ref()
                .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
                .unwrap_or(0);
            let observation = super::settle_internal_contact_interval(
                &mut trial.cohorts,
                &mut trial.electrical_fabric,
                &topology,
                trial.vocal_articulatory_effector_lineage,
                &frontier,
                &[],
                &reached_lineages,
                &reached_lineages,
                &[],
                &[],
                &mut changed,
                trial.generation + active_clock,
                resting,
                &mut residency,
                &std::collections::BTreeMap::new(),
                &[],
                &[],
                ExactRational::integer(0),
                true,
            )
            .expect("controlled copied occurrence settles through production law");
            learned_bridge_carrier_transfer_count += observation
                .settled_directed_transfers
                .iter()
                .filter(|transfer| {
                    matches!(
                        (
                            topology.layer_of(transfer.sender),
                            topology.layer_of(transfer.receiver)
                        ),
                        (Some(11), Some(12)) | (Some(12), Some(11))
                    )
                })
                .count();
            for preparation in &observation.learned_motor_work_preparations {
                all_offer_balances_exact &= preparation.total_offered_work_zeptojoules
                    == preparation.accepted_work_zeptojoules.clone()
                        + preparation.retained_source_heat_zeptojoules.clone();
                all_gate_balances_exact &= preparation.predecessor_residue_zeptojoules.clone()
                    + preparation.accepted_work_zeptojoules.clone()
                    == preparation.delivered_gate_work_zeptojoules.clone()
                        + preparation.successor_residue_zeptojoules.clone()
                        + preparation.residue_narrowing_heat_zeptojoules.clone();
            }
            event_motor_recruitments.extend(observation.motor_unit_recruitments);
            event_articulatory_recruitments.extend(observation.articulatory_unit_recruitments);
            frontier = observation.next_active_frontier;
        }
        completed_events = repeated_event;

        for lineage in &learned_motors {
            let (cohort_index, neuron_index) = mounted_neuron_location(&trial, *lineage);
            carried_states.insert(
                *lineage,
                trial.cohorts[cohort_index].state.neurons()[neuron_index].clone(),
            );
        }
        if repeated_event == 26 {
            let encoded = trial
                .encode(usize::MAX)
                .expect("encode controlled midpoint");
            let restored = ResidentCognitiveFormationState::decode(&encoded, usize::MAX)
                .expect("decode controlled midpoint");
            cold_midpoint_exact = restored
                .encode(usize::MAX)
                .expect("re-encode controlled midpoint")
                == encoded;
            for lineage in &learned_motors {
                let (cohort_index, neuron_index) = mounted_neuron_location(&restored, *lineage);
                carried_states.insert(
                    *lineage,
                    restored.cohorts[cohort_index].state.neurons()[neuron_index].clone(),
                );
            }
        }

        for recruitment in event_motor_recruitments {
            if recruitment.learned_work_preparations.is_empty() {
                continue;
            }
            first_discharges
                .entry(recruitment.neuron_lineage)
                .or_insert_with(|| {
                    json!({
                        "repeated_event": repeated_event,
                        "motor_lineage": lineage_hex(recruitment.neuron_lineage),
                        "outward_elementary_carriers":
                            recruitment.outward_elementary_carriers.to_string(),
                        "terminal": format!("{:?}", recruitment.body_effector_terminal),
                    })
                });
            if recruitment.neuron_lineage.ends_with(&[0x00, 0xc5])
                || recruitment.neuron_lineage.ends_with(&[0x04, 0xfb])
            {
                if !first_vocal_recruitments
                    .iter()
                    .any(|prior| prior.neuron_lineage == recruitment.neuron_lineage)
                {
                    first_vocal_recruitments.push(recruitment);
                }
            }
        }
        first_vocal_articulatory_recruitments.extend(event_articulatory_recruitments);

        let vocal_c5 = first_discharges
            .keys()
            .any(|lineage| lineage.ends_with(&[0x00, 0xc5]));
        let vocal_4fb = first_discharges
            .keys()
            .any(|lineage| lineage.ends_with(&[0x04, 0xfb]));
        if vocal_c5 && vocal_4fb {
            natural_continuation = Some((trial, frontier, residency));
            break;
        }
    }

    let mut sustained_vocal_pulses = Vec::new();
    let mut sustained_body = articulated_body.cloned();
    if let Some((mut continued, mut frontier, mut residency)) = natural_continuation {
        for continuation_clock in 1_u64..=64 {
            let mut reached_lineages = frontier
                .iter()
                .flat_map(|entry| entry.affected_lineages().into_iter().flatten())
                .collect::<Vec<_>>();
            reached_lineages.sort_unstable();
            reached_lineages.dedup();
            let topology = continued.topology_index.clone();
            let mut changed = std::collections::BTreeSet::new();
            let resting = continued
                .resting_population
                .as_ref()
                .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
                .unwrap_or(0);
            let observation = super::settle_internal_contact_interval(
                &mut continued.cohorts,
                &mut continued.electrical_fabric,
                &topology,
                continued.vocal_articulatory_effector_lineage,
                &frontier,
                &[],
                &reached_lineages,
                &reached_lineages,
                &[],
                &[],
                &mut changed,
                continued.generation + 2 + continuation_clock,
                resting,
                &mut residency,
                &std::collections::BTreeMap::new(),
                &[],
                &[],
                ExactRational::integer(0),
                true,
            )
            .expect("post-opening copied motor continuation settles");
            let vocal = observation
                .motor_unit_recruitments
                .iter()
                .filter(|event| event.body_effector_terminal.axis().is_vocal_articulator())
                .collect::<Vec<_>>();
            let respiratory = observation
                .articulatory_unit_recruitments
                .iter()
                .try_fold(0_u128, |total, event| {
                    total.checked_add(event.outward_elementary_carriers)
                })
                .expect("continued respiratory carrier width");
            if !vocal.is_empty() || respiratory != 0 {
                sustained_vocal_pulses.push(json!({
                    "continuation_clock": continuation_clock,
                    "vocal_motors": vocal.iter().map(|event| json!({
                        "motor_lineage": lineage_hex(event.neuron_lineage),
                        "outward_elementary_carriers":
                            event.outward_elementary_carriers.to_string(),
                        "terminal": format!("{:?}", event.body_effector_terminal),
                    })).collect::<Vec<_>>(),
                    "respiratory_efferent_carriers": respiratory.to_string(),
                }));
            }
            if let Some(body) = sustained_body.as_ref() {
                let admitted = AdmittedBodyEffectorDrives::admit(
                    vocal
                        .iter()
                        .map(|event| BodyEffectorDrive {
                            terminal: event.body_effector_terminal,
                            outward_elementary_carriers: event.outward_elementary_carriers,
                        })
                        .collect(),
                )
                .expect("continued vocal body drives admit");
                sustained_body = Some(
                    settle_body_effector_drives(
                        body,
                        &admitted,
                        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
                    )
                    .expect("continued vocal body settles")
                    .successor,
                );
            }
            frontier = observation.next_active_frontier;
        }
    }

    let typed_body = if let Some(body) = articulated_body {
        let drives = first_vocal_recruitments
            .iter()
            .map(|recruitment| BodyEffectorDrive {
                terminal: recruitment.body_effector_terminal,
                outward_elementary_carriers: recruitment.outward_elementary_carriers,
            })
            .collect::<Vec<_>>();
        let admitted =
            AdmittedBodyEffectorDrives::admit(drives).expect("production-path vocal drives admit");
        let transition =
            settle_body_effector_drives(body, &admitted, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
                .expect("production-path vocal tissue settles");
        json!({
            "reached_terminal_count": transition.reached_terminal_count,
            "proprioceptive_consequences": transition
                .proprioceptive_consequences
                .iter()
                .map(|consequence| json!({
                    "axis": format!("{:?}", consequence.axis),
                    "predecessor_position": consequence.predecessor_position,
                    "successor_position": consequence.successor_position,
                    "signed_displacement": consequence.signed_displacement,
                    "applied_displacement_quanta":
                        consequence.applied_displacement_quanta.to_string(),
                    "stalled_carriers": consequence.stalled_carriers.to_string(),
                }))
                .collect::<Vec<_>>(),
            "successor_body_cold_round_trip_exact": ArticulatedBodyState::decode(
                &transition.successor.encode().expect("production-path body encodes"),
            )
            .expect("production-path body decodes") == transition.successor,
        })
    } else {
        json!({"error": "copied articulated body absent"})
    };
    let duration_unfolded_body = if let Some(body) = articulated_body {
        let drives = first_vocal_recruitments
            .iter()
            .map(|recruitment| BodyEffectorDrive {
                terminal: recruitment.body_effector_terminal,
                outward_elementary_carriers: recruitment.outward_elementary_carriers,
            })
            .collect::<Vec<_>>();
        let respiratory = first_vocal_articulatory_recruitments
            .iter()
            .try_fold(0_u128, |total, event| {
                total.checked_add(event.outward_elementary_carriers)
            })
            .expect("duration respiratory carrier width");
        let admitted =
            AdmittedBodyEffectorDrives::admit(drives).expect("duration vocal drives admit");

        let shortcut_body =
            settle_body_effector_drives(body, &admitted, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
                .expect("shortcut vocal body settles");
        let shortcut_acoustic = settle_native_articulatory_interval(
            shortcut_body.successor,
            &shortcut_body.proprioceptive_consequences,
            respiratory,
            4_000,
        )
        .expect("shortcut vocal acoustics settle");

        let mut unfolded_body = body.clone();
        let mut unfolded_pressure = Vec::with_capacity(4_000);
        let mut section_zero_positions = Vec::with_capacity(250);
        let mut section_seven_positions = Vec::with_capacity(250);
        for millisecond in 0..250 {
            let step_drives = if millisecond == 0 {
                &admitted
            } else {
                &AdmittedBodyEffectorDrives::quiescent()
            };
            let body_step = settle_body_effector_drives(
                &unfolded_body,
                step_drives,
                BODY_SETTLEMENT_CLOCK_MICROSECONDS,
            )
            .expect("one millisecond vocal tissue settles");
            let acoustic_step = settle_native_articulatory_interval(
                body_step.successor,
                &body_step.proprioceptive_consequences,
                if millisecond == 0 { respiratory } else { 0 },
                16,
            )
            .expect("one millisecond vocal acoustics settle");
            unfolded_pressure.extend_from_slice(&acoustic_step.radiated_pressure_pcm);
            unfolded_body = acoustic_step.successor_body;
            section_zero_positions.push(unfolded_body.axis(BodyAxis::VocalTractSection0Area));
            section_seven_positions.push(unfolded_body.axis(BodyAxis::VocalTractSection7Area));
        }
        let pressure_summary = |pressure: &[i16]| {
            json!({
                "sample_count": pressure.len(),
                "nonzero_sample_count": pressure.iter().filter(|sample| **sample != 0).count(),
                "absolute_peak": pressure
                    .iter()
                    .map(|sample| sample.unsigned_abs())
                    .max()
                    .unwrap_or(0),
            })
        };
        json!({
            "composition_control_not_natural_same_occurrence": true,
            "represented_duration_milliseconds": 250,
            "body_step_milliseconds": 1,
            "acoustic_samples_per_body_step": 16,
            "respiratory_efferent_carriers": respiratory.to_string(),
            "current_runtime_shortcut_pressure":
                pressure_summary(&shortcut_acoustic.radiated_pressure_pcm),
            "duration_unfolded_pressure": pressure_summary(&unfolded_pressure),
            "section_zero_position": {
                "predecessor": body.axis(BodyAxis::VocalTractSection0Area),
                "minimum_during": section_zero_positions.iter().min(),
                "maximum_during": section_zero_positions.iter().max(),
                "successor": unfolded_body.axis(BodyAxis::VocalTractSection0Area),
            },
            "section_seven_position": {
                "predecessor": body.axis(BodyAxis::VocalTractSection7Area),
                "minimum_during": section_seven_positions.iter().min(),
                "maximum_during": section_seven_positions.iter().max(),
                "successor": unfolded_body.axis(BodyAxis::VocalTractSection7Area),
            },
            "successor_body_cold_round_trip_exact": ArticulatedBodyState::decode(
                &unfolded_body.encode().expect("duration body encodes"),
            ).expect("duration body decodes") == unfolded_body,
        })
    } else {
        json!({"error": "copied articulated body absent"})
    };

    json!({
        "controlled_repeated_copied_occurrence": true,
        "autonomy_or_natural_frequency_claim": false,
        "completed_repeated_events": completed_events,
        "learned_motor_count": learned_motors.len(),
        "learned_bridge_carrier_transfer_count": learned_bridge_carrier_transfer_count,
        "all_offer_balances_exact": all_offer_balances_exact,
        "all_gate_balances_exact": all_gate_balances_exact,
        "cold_midpoint_round_trip_exact": cold_midpoint_exact,
        "first_discharges": first_discharges.into_values().collect::<Vec<_>>(),
        "first_vocal_recruitment_count": first_vocal_recruitments.len(),
        "articulatory_recruitment_count": first_vocal_articulatory_recruitments.len(),
        "typed_body": typed_body,
        "duration_unfolded_body": duration_unfolded_body,
        "natural_post_opening_vocal_pulses": sustained_vocal_pulses,
        "natural_post_opening_body": sustained_body.as_ref().map(|body| json!({
            "vocal_tract_section_0": body.axis(BodyAxis::VocalTractSection0Area),
            "vocal_tract_section_7": body.axis(BodyAxis::VocalTractSection7Area),
            "cold_round_trip_exact": ArticulatedBodyState::decode(
                &body.encode().expect("continued body encodes"),
            ).expect("continued body decodes") == *body,
        })),
    })
}

/// Test-only artificial unblock for the exact copied production body.
///
/// The two vocal ordering routes the body actually learned are each widened
/// to the other three tract terminals belonging to the same open/closed
/// directional synergy. This anatomy is deliberately authored by the test and
/// can never ship. It answers only one causal question: if the missing six
/// learned contacts existed, would the unchanged learned-work, motor, tissue,
/// breath, and pressure laws recruit a multi-axis vocal gesture? A negative
/// result falsifies contact coverage as the present blocker; a positive result
/// authorizes investigation of the developmental growth boundary, not this
/// artificial topology.
fn artificial_vocal_synergy_unblock_json(
    state: &ResidentCognitiveFormationState,
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let target_axes = [
        BodyAxis::VocalTractSection0Area,
        BodyAxis::VocalTractSection1Area,
        BodyAxis::VocalTractSection2Area,
        BodyAxis::VocalTractSection7Area,
    ];
    let motor_for_terminal = |terminal: BodyEffectorTerminal| {
        state
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| {
                (mount.source_site().is_none()
                    && mount.place().layer() == 12
                    && mount.body_effector_terminal() == Some(terminal))
                .then_some(*lineage)
            })
            .collect::<Vec<_>>()
    };
    let ordering_for_motor = |motor: [u8; 16]| {
        state
            .electrical_fabric
            .contact_endpoints()
            .filter_map(|(left, right)| {
                let left = state.electrical_fabric.lineages()[left];
                let right = state.electrical_fabric.lineages()[right];
                match (
                    state.topology_index.layer_of(left),
                    state.topology_index.layer_of(right),
                ) {
                    (Some(11), Some(12)) if right == motor => Some(left),
                    (Some(12), Some(11)) if left == motor => Some(right),
                    _ => None,
                }
            })
            .collect::<Vec<_>>()
    };

    let open_anchor_motors = motor_for_terminal(BodyEffectorTerminal::new(
        BodyAxis::VocalTractSection0Area,
        BodyEffectorDirection::TowardMaximum,
    ));
    let [open_anchor_motor] = open_anchor_motors.as_slice() else {
        return json!({"error": "section-0 maximum motor is not unique"});
    };
    let closed_anchor_motors = motor_for_terminal(BodyEffectorTerminal::new(
        BodyAxis::VocalTractSection7Area,
        BodyEffectorDirection::TowardMinimum,
    ));
    let [closed_anchor_motor] = closed_anchor_motors.as_slice() else {
        return json!({"error": "section-7 minimum motor is not unique"});
    };
    let open_orderings = ordering_for_motor(*open_anchor_motor);
    let [open_ordering] = open_orderings.as_slice() else {
        return json!({"error": "learned open ordering route is not unique"});
    };
    let open_ordering = *open_ordering;
    let closed_orderings = ordering_for_motor(*closed_anchor_motor);
    let [closed_ordering] = closed_orderings.as_slice() else {
        return json!({"error": "learned closed ordering route is not unique"});
    };
    let closed_ordering = *closed_ordering;

    let mut target_motors = Vec::<(&'static str, BodyEffectorTerminal, [u8; 16], [u8; 16])>::new();
    for axis in target_axes {
        for (phase, direction, ordering) in [
            (
                "closed",
                BodyEffectorDirection::TowardMinimum,
                closed_ordering,
            ),
            ("open", BodyEffectorDirection::TowardMaximum, open_ordering),
        ] {
            let terminal = BodyEffectorTerminal::new(axis, direction);
            let motors = motor_for_terminal(terminal);
            let [motor] = motors.as_slice() else {
                return json!({
                    "error": "target vocal motor is not unique",
                    "terminal": format!("{terminal:?}"),
                    "count": motors.len(),
                });
            };
            target_motors.push((phase, terminal, ordering, *motor));
        }
    }

    let mut artificially_bridged = state.clone();
    let mut additions = Vec::new();
    for (_, _, ordering, motor) in &target_motors {
        if !artificially_bridged
            .electrical_fabric
            .contains_contact(*ordering, *motor)
        {
            additions.push((
                *ordering,
                *motor,
                ExactRational::integer(super::DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            ));
        }
    }
    additions.sort_by_key(|(ordering, motor, _)| (*ordering, *motor));
    additions.dedup_by_key(|(ordering, motor, _)| (*ordering, *motor));
    artificially_bridged.electrical_fabric = artificially_bridged
        .electrical_fabric
        .append_contacts(&additions)
        .expect("artificial copied-body contact append");
    artificially_bridged.topology_index = std::sync::Arc::new(
        super::ResidentTopologyIndex::build(
            &artificially_bridged.cohorts,
            &artificially_bridged.electrical_fabric,
        )
        .expect("artificial copied-body topology"),
    );
    let artificially_encoded = artificially_bridged
        .encode(usize::MAX)
        .expect("artificial copied body encodes");
    let artificially_cold =
        ResidentCognitiveFormationState::decode(&artificially_encoded, usize::MAX)
            .expect("artificial copied body cold-decodes");
    let artificial_cold_exact = artificially_cold
        .encode(usize::MAX)
        .expect("artificial copied body re-encodes")
        == artificially_encoded;
    let artificial_source_population_scale =
        std::env::var("GUALA_PROBE_ARTIFICIAL_VOCAL_SOURCE_POPULATION_SCALE")
            .ok()
            .map(|value| {
                value
                    .parse::<u32>()
                    .expect("artificial vocal source population scale is u32")
            })
            .unwrap_or(1);
    assert!(
        (1..=16).contains(&artificial_source_population_scale),
        "artificial vocal source population scale must be 1..=16"
    );
    let replaced_population_scale = super::replace_artificial_learned_motor_source_population_scale(
        artificial_source_population_scale,
    );
    assert_eq!(
        replaced_population_scale, 1,
        "artificial population scale leaked across probe"
    );

    let mut carried_states = target_motors
        .iter()
        .map(|(_, _, _, motor)| {
            let (cohort_index, neuron_index) =
                mounted_neuron_location(&artificially_bridged, *motor);
            (
                *motor,
                artificially_bridged.cohorts[cohort_index].state.neurons()[neuron_index].clone(),
            )
        })
        .collect::<std::collections::BTreeMap<_, _>>();
    let target_set = target_motors
        .iter()
        .map(|(_, _, _, motor)| *motor)
        .collect::<std::collections::BTreeSet<_>>();
    let checkpoints = [1_u32, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1_024];
    let maximum_repeated_events =
        std::env::var("GUALA_PROBE_ARTIFICIAL_VOCAL_MAXIMUM_REPEATED_EVENTS")
            .ok()
            .map(|value| {
                value
                    .parse::<u32>()
                    .expect("artificial vocal maximum repeated events is u32")
            })
            .unwrap_or(256);
    assert!(
        (1..=1_024).contains(&maximum_repeated_events),
        "artificial vocal maximum repeated events must be 1..=1024"
    );
    let mut checkpoint_results = Vec::new();
    let mut first_discharge = std::collections::BTreeMap::<[u8; 16], u32>::new();
    let mut natural_continuation = None;
    let mut preparation_balances_exact = true;

    for repeated_event in 1_u32..=maximum_repeated_events {
        let mut trial = artificially_bridged.clone();
        let mut replacements_by_cohort = std::collections::BTreeMap::<
            usize,
            Vec<(usize, crate::complete_neuron::NeuronPhysicalState)>,
        >::new();
        for (lineage, motor_state) in &carried_states {
            let (cohort_index, neuron_index) = mounted_neuron_location(&trial, *lineage);
            replacements_by_cohort
                .entry(cohort_index)
                .or_default()
                .push((neuron_index, motor_state.clone()));
        }
        for (cohort_index, replacements) in replacements_by_cohort {
            trial.cohorts[cohort_index].state = trial.cohorts[cohort_index]
                .state
                .with_replaced_neurons(&replacements)
                .expect("artificial synergy motor-state carry")
                .into();
        }
        let topology = trial.topology_index.clone();
        let mut frontier = trial.active_electrical_frontier.to_vec();
        let mut residency = None;
        for active_clock in 1_u64..=2 {
            let mut reached_lineages = frontier
                .iter()
                .flat_map(|entry| entry.affected_lineages().into_iter().flatten())
                .collect::<Vec<_>>();
            reached_lineages.sort_unstable();
            reached_lineages.dedup();
            let mut changed = std::collections::BTreeSet::new();
            let resting = trial
                .resting_population
                .as_ref()
                .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
                .unwrap_or(0);
            let observation = super::settle_internal_contact_interval(
                &mut trial.cohorts,
                &mut trial.electrical_fabric,
                &topology,
                trial.vocal_articulatory_effector_lineage,
                &frontier,
                &[],
                &reached_lineages,
                &reached_lineages,
                &[],
                &[],
                &mut changed,
                trial.generation + active_clock,
                resting,
                &mut residency,
                &std::collections::BTreeMap::new(),
                &[],
                &[],
                ExactRational::integer(0),
                true,
            )
            .expect("artificial synergy repeated occurrence settles");
            for preparation in &observation.learned_motor_work_preparations {
                preparation_balances_exact &= preparation.total_offered_work_zeptojoules
                    == preparation.accepted_work_zeptojoules.clone()
                        + preparation.retained_source_heat_zeptojoules.clone();
                preparation_balances_exact &= preparation.predecessor_residue_zeptojoules.clone()
                    + preparation.accepted_work_zeptojoules.clone()
                    == preparation.delivered_gate_work_zeptojoules.clone()
                        + preparation.successor_residue_zeptojoules.clone()
                        + preparation.residue_narrowing_heat_zeptojoules.clone();
            }
            for recruitment in observation.motor_unit_recruitments {
                if target_set.contains(&recruitment.neuron_lineage)
                    && !recruitment.learned_work_preparations.is_empty()
                {
                    first_discharge
                        .entry(recruitment.neuron_lineage)
                        .or_insert(repeated_event);
                }
            }
            frontier = observation.next_active_frontier;
        }
        for lineage in &target_set {
            let (cohort_index, neuron_index) = mounted_neuron_location(&trial, *lineage);
            carried_states.insert(
                *lineage,
                trial.cohorts[cohort_index].state.neurons()[neuron_index].clone(),
            );
        }
        if checkpoints.contains(&repeated_event) {
            checkpoint_results.push(json!({
                "repeated_event": repeated_event,
                "target_motors_discharged": first_discharge.len(),
            }));
        }
        if first_discharge.len() == target_set.len() {
            natural_continuation = Some((trial, frontier, residency, repeated_event));
            break;
        }
    }

    let mut natural_pulses = Vec::new();
    let mut pressure = Vec::<i16>::new();
    let mut successor_body = articulated_body.cloned();
    let mut target_axis_positions: [Vec<i32>; 4] = std::array::from_fn(|index| {
        articulated_body
            .map(|body| vec![body.axis(target_axes[index])])
            .unwrap_or_default()
    });
    if let Some((mut continued, mut frontier, mut residency, _)) = natural_continuation {
        for continuation_clock in 1_u64..=128 {
            let mut reached_lineages = frontier
                .iter()
                .flat_map(|entry| entry.affected_lineages().into_iter().flatten())
                .collect::<Vec<_>>();
            reached_lineages.sort_unstable();
            reached_lineages.dedup();
            let topology = continued.topology_index.clone();
            let mut changed = std::collections::BTreeSet::new();
            let resting = continued
                .resting_population
                .as_ref()
                .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
                .unwrap_or(0);
            let observation = super::settle_internal_contact_interval(
                &mut continued.cohorts,
                &mut continued.electrical_fabric,
                &topology,
                continued.vocal_articulatory_effector_lineage,
                &frontier,
                &[],
                &reached_lineages,
                &reached_lineages,
                &[],
                &[],
                &mut changed,
                continued.generation + 2 + continuation_clock,
                resting,
                &mut residency,
                &std::collections::BTreeMap::new(),
                &[],
                &[],
                ExactRational::integer(0),
                true,
            )
            .expect("artificial synergy natural continuation settles");
            let vocal = observation
                .motor_unit_recruitments
                .iter()
                .filter(|recruitment| target_set.contains(&recruitment.neuron_lineage))
                .collect::<Vec<_>>();
            let respiratory = observation
                .articulatory_unit_recruitments
                .iter()
                .try_fold(0_u128, |total, event| {
                    total.checked_add(event.outward_elementary_carriers)
                })
                .expect("artificial synergy respiratory width");
            if !vocal.is_empty() || respiratory != 0 {
                let phases = vocal
                    .iter()
                    .flat_map(|recruitment| {
                        recruitment
                            .learned_work_preparations
                            .iter()
                            .flat_map(|preparation| preparation.routes.iter())
                            .filter_map(|route| {
                                if route.ordering_lineage == open_ordering {
                                    Some("open")
                                } else if route.ordering_lineage == closed_ordering {
                                    Some("closed")
                                } else {
                                    None
                                }
                            })
                    })
                    .collect::<std::collections::BTreeSet<_>>();
                natural_pulses.push(json!({
                    "continuation_clock": continuation_clock,
                    "phases": phases,
                    "vocal_motor_count": vocal.len(),
                    "vocal_motors": vocal.iter().map(|recruitment| json!({
                        "lineage": lineage_hex(recruitment.neuron_lineage),
                        "terminal": format!("{:?}", recruitment.body_effector_terminal),
                        "carriers": recruitment.outward_elementary_carriers.to_string(),
                    })).collect::<Vec<_>>(),
                    "respiratory_carriers": respiratory.to_string(),
                }));
            }
            if let Some(body) = successor_body.take() {
                let admitted = AdmittedBodyEffectorDrives::admit(
                    vocal
                        .iter()
                        .map(|recruitment| BodyEffectorDrive {
                            terminal: recruitment.body_effector_terminal,
                            outward_elementary_carriers: recruitment.outward_elementary_carriers,
                        })
                        .collect(),
                )
                .expect("artificial synergy body drives admit");
                let moved = settle_body_effector_drives(
                    &body,
                    &admitted,
                    BODY_SETTLEMENT_CLOCK_MICROSECONDS,
                )
                .expect("artificial synergy body settles");
                let acoustic = settle_native_articulatory_interval(
                    moved.successor,
                    &moved.proprioceptive_consequences,
                    respiratory,
                    4_000,
                )
                .expect("artificial synergy acoustics settle");
                pressure.extend_from_slice(&acoustic.radiated_pressure_pcm);
                successor_body = Some(acoustic.successor_body);
                for (index, axis) in target_axes.iter().copied().enumerate() {
                    target_axis_positions[index].push(
                        successor_body
                            .as_ref()
                            .expect("artificial successor body retained")
                            .axis(axis),
                    );
                }
            }
            frontier = observation.next_active_frontier;
        }
    }
    let pressure_peak = pressure
        .iter()
        .map(|sample| sample.unsigned_abs())
        .max()
        .unwrap_or(0);
    let nonzero_pressure_samples = pressure.iter().filter(|sample| **sample != 0).count();
    let pressure_wav = std::env::var("GUALA_PROBE_ARTIFICIAL_VOCAL_PRESSURE_WAV")
        .ok()
        .map(|path| {
            let data_bytes = u32::try_from(pressure.len() * std::mem::size_of::<i16>())
                .expect("artificial vocal WAV data width");
            let mut wav = Vec::with_capacity(44 + data_bytes as usize);
            wav.extend_from_slice(b"RIFF");
            wav.extend_from_slice(&(36_u32 + data_bytes).to_le_bytes());
            wav.extend_from_slice(b"WAVEfmt ");
            wav.extend_from_slice(&16_u32.to_le_bytes());
            wav.extend_from_slice(&1_u16.to_le_bytes());
            wav.extend_from_slice(&1_u16.to_le_bytes());
            wav.extend_from_slice(&16_000_u32.to_le_bytes());
            wav.extend_from_slice(&32_000_u32.to_le_bytes());
            wav.extend_from_slice(&2_u16.to_le_bytes());
            wav.extend_from_slice(&16_u16.to_le_bytes());
            wav.extend_from_slice(b"data");
            wav.extend_from_slice(&data_bytes.to_le_bytes());
            for sample in &pressure {
                wav.extend_from_slice(&sample.to_le_bytes());
            }
            fs::write(&path, &wav).expect("artificial vocal pressure WAV writes");
            json!({"path": path, "bytes": wav.len()})
        });
    let restored_population_scale =
        super::replace_artificial_learned_motor_source_population_scale(1);
    assert_eq!(
        restored_population_scale, artificial_source_population_scale,
        "artificial population scale changed during probe"
    );

    json!({
        "measurement_only": true,
        "artificial_topology_never_ships": true,
        "artificial_source_population_never_ships": true,
        "artificial_source_population_scale": artificial_source_population_scale,
        "maximum_repeated_events": maximum_repeated_events,
        "accepted_word_or_speech_claim": false,
        "open_ordering": lineage_hex(open_ordering),
        "closed_ordering": lineage_hex(closed_ordering),
        "target_motor_count": target_motors.len(),
        "artificial_contact_count": additions.len(),
        "artificial_contacts": additions.iter().map(|(ordering, motor, _)| json!({
            "ordering": lineage_hex(*ordering),
            "motor": lineage_hex(*motor),
        })).collect::<Vec<_>>(),
        "artificial_cold_round_trip_exact": artificial_cold_exact,
        "preparation_balances_exact": preparation_balances_exact,
        "first_discharges": target_motors.iter().map(|(phase, terminal, ordering, motor)| json!({
            "phase": phase,
            "terminal": format!("{terminal:?}"),
            "ordering": lineage_hex(*ordering),
            "motor": lineage_hex(*motor),
            "first_repeated_event": first_discharge.get(motor),
        })).collect::<Vec<_>>(),
        "range_checkpoints": checkpoint_results,
        "all_target_motors_discharged": first_discharge.len() == target_set.len(),
        "natural_continuation_pulses": natural_pulses,
        "pressure_sample_count": pressure.len(),
        "nonzero_pressure_samples": nonzero_pressure_samples,
        "pressure_peak": pressure_peak,
        "pressure_wav": pressure_wav,
        "target_axis_ranges": target_axes.iter().copied().enumerate().map(|(index, axis)| {
            let positions = &target_axis_positions[index];
            json!({
                "axis": format!("{axis:?}"),
                "sample_count": positions.len(),
                "predecessor": positions.first(),
                "minimum": positions.iter().min(),
                "maximum": positions.iter().max(),
                "successor": positions.last(),
            })
        }).collect::<Vec<_>>(),
        "successor_body_cold_round_trip_exact": successor_body.as_ref().is_some_and(|body| {
            ArticulatedBodyState::decode(&body.encode().expect("artificial successor body encodes"))
                .expect("artificial successor body decodes") == *body
        }),
    })
}

/// Copy-only developmental proof for the production motor-growth law.
///
/// A finite external guide moves the four already-declared tract axes through
/// their ordinary antagonist tissue. The resulting exact proprioceptive
/// consequences enter the unchanged full-field path while the copied body
/// carries its own resident frontier. Guidance supplies neither a contact nor
/// a motor command to cognition. Any new L11 -> L12 anatomy must therefore be
/// authored by the production closure law, from resident premotor activity
/// joined to the actually moved terminal and returned body consequence.
struct GuidedVocalContinuation {
    state: ResidentCognitiveFormationState,
    body: ArticulatedBodyState,
    residency: Option<crate::causal_event_scheduler::CausalEventResidency>,
    pulses: Vec<Value>,
    pressure: Vec<i16>,
    first_audible_frame: Option<Vec<i16>>,
    respiratory_carriers: u128,
    internal_reassemblies: u64,
    causal_thought_transitions: u64,
    learned_work_by_clock: Vec<Value>,
}

fn run_guided_vocal_continuation(
    mut state: ResidentCognitiveFormationState,
    mut body: ArticulatedBodyState,
    mut residency: Option<crate::causal_event_scheduler::CausalEventResidency>,
    initial_cue_sources: &[crate::joint_source_episode::NativeJointSourceEpisode],
    occurrence: u64,
    maximum_clocks: u64,
    target_motors: &std::collections::BTreeSet<[u8; 16]>,
    terminal_by_motor: &std::collections::BTreeMap<[u8; 16], BodyEffectorTerminal>,
) -> GuidedVocalContinuation {
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let mut pending_motor_consequence = None;
    let mut pending_self_pressure = None;
    let mut pulses = Vec::new();
    let mut pressure = Vec::<i16>::new();
    let mut first_audible_frame = None::<Vec<i16>>;
    let mut respiratory_carriers = 0_u128;
    let mut internal_reassemblies = 0_u64;
    let mut causal_thought_transitions = 0_u64;
    let mut learned_work_by_clock = Vec::new();
    let scheduled_guide_clock = (!initial_cue_sources.is_empty())
        .then(|| std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_NEXT_GUIDE_CLOCK").ok())
        .flatten()
        .map(|value| value.parse::<u64>().expect("next guide clock is u64"));
    let scheduled_guide_phase = scheduled_guide_clock.map(|_| {
        std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_NEXT_GUIDE_PHASE")
            .ok()
            .map(|value| value.parse::<usize>().expect("next guide phase is usize"))
            .unwrap_or(1)
    });
    let scheduled_guide_pressure = scheduled_guide_clock.map(|_| {
        let bytes = fs::read(
            std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_NEXT_GUIDE_PRESSURE_PCM")
                .expect("next guide pressure path must be set"),
        )
        .expect("next guide pressure reads");
        let phase = scheduled_guide_phase.expect("scheduled guide phase exists");
        assert_eq!(bytes.len(), 32_000);
        bytes
            .chunks_exact(2)
            .skip(phase * 4_000)
            .take(4_000)
            .map(|sample| i16::from_le_bytes([sample[0], sample[1]]))
            .collect::<Vec<_>>()
    });

    let mut target_preparations = target_motors
        .iter()
        .flat_map(|motor| {
            super::lean_sensorimotor_route::vocal_cognitive_action_route_for_motor(
                &state.cohorts,
                &state.topology_index,
                *motor,
            )
            .expect("target vocal preparations resolve")
            .into_iter()
            .map(|route| route.preparation)
        })
        .collect::<Vec<_>>();
    target_preparations.sort_unstable();
    target_preparations.dedup();

    for clock in 1..=maximum_clocks {
        super::reset_vocal_work_diagnostic();
        let mut admitted_sources = Vec::new();
        let consuming_body_owned_pressure = pending_self_pressure.is_some();
        if clock == 1 {
            admitted_sources.extend(
                initial_cue_sources
                    .iter()
                    .map(super::admitted_fixture_episode),
            );
        }
        if scheduled_guide_clock == Some(clock) {
            let guide_direction =
                match scheduled_guide_phase.expect("scheduled guide phase exists") % 4 {
                    0 | 2 => BodyEffectorDirection::TowardMinimum,
                    1 | 3 => BodyEffectorDirection::TowardMaximum,
                    _ => unreachable!(),
                };
            let mut axes = terminal_by_motor
                .values()
                .map(|terminal| terminal.axis())
                .collect::<Vec<_>>();
            axes.sort_unstable();
            axes.dedup();
            let drives = AdmittedBodyEffectorDrives::admit(
                axes.into_iter()
                    .map(|axis| BodyEffectorDrive {
                        terminal: BodyEffectorTerminal::new(axis, guide_direction),
                        outward_elementary_carriers: 1_500,
                    })
                    .collect(),
            )
            .expect("next guided posture admits");
            let guided =
                settle_body_effector_drives(&body, &drives, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
                    .expect("next guided posture settles");
            let source = admit_articulated_body_consequence_source(
                occurrence
                    .checked_add(clock)
                    .expect("next guide occurrence fits"),
                &guided.proprioceptive_consequences,
            )
            .expect("next guided posture consequence admits");
            admitted_sources.push(super::admitted_fixture_episode(&source));
            admitted_sources.push(super::admitted_fixture_episode(&probe_hearing_episode(
                scheduled_guide_pressure
                    .as_ref()
                    .expect("next guide pressure is present"),
                "candidate-exact-next-tutor-pressure",
            )));
            body = guided.successor;
        }
        if let Some(source) = pending_motor_consequence.take() {
            admitted_sources.push(super::admitted_fixture_episode(&source));
        }
        if let Some(source) = pending_self_pressure.take() {
            admitted_sources.push(super::admitted_fixture_episode(&source));
        }
        if admitted_sources.is_empty() {
            let silent_pressure = probe_self_hearing_episode(&[0_i16; 4_000]);
            admitted_sources.push(super::admitted_fixture_episode(&silent_pressure));
        }
        let (successor, observation) = state
            .advance_coexisting_admitted_transition_with_residency(
                &admitted_sources,
                usize::MAX,
                true,
                !consuming_body_owned_pressure,
                scheduled_guide_clock == Some(clock),
                &mut residency,
                ExactRational::integer(0),
            )
            .unwrap_or_else(|error| {
                panic!("guided vocal continuation clock {clock} settles: {error:?}")
            });
        let [route_matches, sound_matches, source_transitions, work_offers, work_acceptances] =
            super::vocal_work_diagnostic();
        internal_reassemblies = internal_reassemblies
            .checked_add(
                u64::try_from(observation.internally_reassembled_formation_cues.len())
                    .expect("continuation internal reassembly count fits u64"),
            )
            .expect("continuation internal reassembly count remains bounded");
        causal_thought_transitions = causal_thought_transitions
            .checked_add(
                observation
                    .internally_reassembled_formation_cues
                    .iter()
                    .map(|cue| u64::try_from(cue.causal_predecessors.len()).unwrap())
                    .sum::<u64>(),
            )
            .expect("continuation causal thought count remains bounded");
        let external_reassembly_receipts = observation
            .externally_reassembled_formation_frontiers
            .iter()
            .map(|reassembly| reassembly.formation_receipt)
            .collect::<std::collections::BTreeSet<_>>();
        let exact_sound_reassembled_members = super::exact_sound_reassembled_structure_lineages(
            &successor.cohorts,
            &successor.topology_index,
            &successor.mosaics,
            &successor.formation_index,
            &observation.externally_reassembled_formation_frontiers,
            usize::MAX,
        )
        .expect("exact sound reassembly members resolve");
        let target_associations = target_preparations
            .iter()
            .flat_map(|preparation| {
                preparation
                    .associations
                    .iter()
                    .map(|association| association.lineage)
            })
            .collect::<std::collections::BTreeSet<_>>();
        let exact_sound_target_associations = exact_sound_reassembled_members
            .intersection(&target_associations)
            .copied()
            .map(lineage_hex)
            .collect::<Vec<_>>();
        let mut exact_sound_reassembled_members_by_layer = std::collections::BTreeMap::new();
        for layer in exact_sound_reassembled_members
            .iter()
            .filter_map(|lineage| successor.topology_index.layer_of(*lineage))
        {
            *exact_sound_reassembled_members_by_layer
                .entry(layer)
                .or_insert(0usize) += 1;
        }
        let external_reassembly_witnesses = observation
            .externally_reassembled_formation_frontiers
            .iter()
            .map(|reassembly| {
                json!({
                    "receipt": reassembly.formation_receipt.iter()
                        .map(|byte| format!("{byte:02x}"))
                        .collect::<String>(),
                    "recurrent": lineage_hex(reassembly.recurrent_lineage),
                    "cues": reassembly.cue_lineages.iter().map(|lineage| {
                        let flat = successor.topology_index.flat_for_lineage(*lineage)
                            .expect("external reassembly cue resolves");
                        let (cohort, neuron, _) = successor.topology_index.flat_locations[flat];
                        let mount = &successor.cohorts[cohort].anatomy.mounts()[neuron];
                        json!({
                            "lineage": lineage_hex(*lineage),
                            "layer": mount.place().layer(),
                            "source_sense": mount.source_site().map(|site| format!("{:?}", site.sense())),
                        })
                    }).collect::<Vec<_>>(),
                })
            })
            .collect::<Vec<_>>();
        let mut exact_sound_reassembled_founders = Vec::new();
        for association in exact_sound_reassembled_members
            .iter()
            .copied()
            .filter(|lineage| successor.topology_index.layer_of(*lineage) == Some(7))
        {
            let association_flat = successor
                .topology_index
                .flat_for_lineage(association)
                .expect("exact reassembled association resolves");
            for resident_contact_index in successor.topology_index.incident_contacts_by_flat
                [association_flat]
                .iter()
                .copied()
            {
                let contact = successor.topology_index.contacts[resident_contact_index];
                let Some(ordering) = super::vocal_action_preparation_from_association_founder(
                    &successor.cohorts,
                    &successor.topology_index,
                    association,
                    contact.stable_bond,
                )
                .expect("exact reassembled founder resolves") else {
                    continue;
                };
                let super::ResidentContactOrigin::Fabric { contact_index } = contact.origin else {
                    panic!("exact learned founder is resident fabric");
                };
                exact_sound_reassembled_founders.push(json!({
                    "association": lineage_hex(association),
                    "ordering": lineage_hex(ordering),
                    "bond": format!("{:?}", contact.stable_bond),
                    "carrier_phase_numerator": successor.electrical_fabric.state()
                        .contact_states()[contact_index].carrier_phase().parts().0.to_string(),
                }));
            }
        }
        let mut reassembled_target_associations = std::collections::BTreeSet::new();
        for preparation in &target_preparations {
            for association in &preparation.associations {
                for candidate in successor
                    .formation_index
                    .candidate_indices([association.lineage], std::iter::empty())
                {
                    let retained = successor
                        .mosaics
                        .get(candidate)
                        .expect("formation index names retained mosaic");
                    let encoded = super::encode_resident_admitted_physical_mosaic(
                        &retained.mosaic,
                        usize::MAX,
                    )
                    .expect("retained mosaic encodes for diagnostic receipt");
                    if external_reassembly_receipts.contains(&super::sha256(&encoded)) {
                        reassembled_target_associations.insert(association.lineage);
                    }
                }
            }
        }
        let active_reassembled_association_frontiers = successor
            .active_electrical_frontier
            .iter()
            .filter(|entry| reassembled_target_associations.contains(&entry.frontier_lineage()))
            .map(|entry| {
                let cause = entry
                    .cause
                    .expect("active reassembled-association frontier has exact cause");
                json!({
                    "frontier": lineage_hex(entry.frontier_lineage()),
                    "sender": entry.sender().map(lineage_hex),
                    "receiver": lineage_hex(entry.receiver()),
                    "bond": format!("{:?}", cause.bond),
                    "transferred_whole_carriers": cause.transferred_whole_carriers.to_string(),
                    "is_in_flight": entry.is_in_flight(),
                    "body_owned_acoustic_efference": entry.carries_body_owned_acoustic_efference(),
                    "external_ingress_cause": entry.carries_external_ingress_cause(),
                })
            })
            .collect::<Vec<_>>();
        let externally_reassembled_preparations = target_preparations
            .iter()
            .map(|preparation| {
                let mut matching_associations = Vec::new();
                let mut matching_formation_receipts = std::collections::BTreeSet::new();
                for association in &preparation.associations {
                    let candidates = successor
                        .formation_index
                        .candidate_indices([association.lineage], std::iter::empty());
                    for candidate in candidates {
                        let retained = successor
                            .mosaics
                            .get(candidate)
                            .expect("formation index names retained mosaic");
                        let encoded = super::encode_resident_admitted_physical_mosaic(
                            &retained.mosaic,
                            usize::MAX,
                        )
                        .expect("retained mosaic encodes for diagnostic receipt");
                        let receipt = super::sha256(&encoded);
                        if external_reassembly_receipts.contains(&receipt) {
                            matching_associations.push(lineage_hex(association.lineage));
                            matching_formation_receipts.insert(
                                receipt
                                    .iter()
                                    .map(|byte| format!("{byte:02x}"))
                                    .collect::<String>(),
                            );
                        }
                    }
                }
                matching_associations.sort_unstable();
                matching_associations.dedup();
                json!({
                    "ordering": lineage_hex(preparation.ordering_lineage),
                    "association_count": preparation.associations.len(),
                    "matching_associations": matching_associations,
                    "matching_formation_receipts": matching_formation_receipts,
                })
            })
            .collect::<Vec<_>>();
        let founder_contact_witnesses = target_preparations
            .iter()
            .flat_map(|preparation| {
                preparation.associations.iter().map(|association| {
                    let route = observation.physical_frontier_routes.iter().find(|route| {
                        route.bond() == association.bond
                            && super::canonical_lineage_pair(
                                route.seed_lineage(),
                                route.adjacent_lineage(),
                            ) == super::canonical_lineage_pair(
                                association.lineage,
                                preparation.ordering_lineage,
                            )
                    });
                    let contact = successor
                        .topology_index
                        .contacts
                        .iter()
                        .find(|contact| contact.stable_bond == association.bond)
                        .expect("founder contact exists in exact successor topology");
                    let super::ResidentContactOrigin::Fabric { contact_index } = contact.origin else {
                        panic!("learned founder contact is resident fabric");
                    };
                    let anatomy = successor.electrical_fabric.anatomy().contact_anatomies()
                        [contact_index];
                    let (left_index, _) = anatomy.endpoints();
                    let left_lineage = successor.electrical_fabric.lineages()[left_index];
                    let phase_numerator = successor.electrical_fabric.state().contact_states()
                        [contact_index]
                        .carrier_phase()
                        .parts()
                        .0;
                    let outward_from_association_phase =
                        if left_lineage == association.lineage {
                            phase_numerator
                        } else {
                            -phase_numerator
                        };
                    let retained_causal_founder = successor.active_electrical_frontier.iter().any(
                        |entry| {
                            entry.frontier_lineage() == preparation.ordering_lineage
                                && entry.cause.is_some_and(|cause| cause.bond == association.bond)
                        },
                    );
                    let retained_external_founder = successor
                        .active_electrical_frontier
                        .iter()
                        .any(|entry| {
                            entry.frontier_lineage() == preparation.ordering_lineage
                                && entry.carries_external_ingress_cause()
                                && entry.cause.is_some_and(|cause| cause.bond == association.bond)
                        });
                    json!({
                        "ordering": lineage_hex(preparation.ordering_lineage),
                        "association": lineage_hex(association.lineage),
                        "visited": route.is_some(),
                        "seed": route.map(|route| lineage_hex(route.seed_lineage())),
                        "adjacent": route.map(|route| lineage_hex(route.adjacent_lineage())),
                        "directed_sender": route.and_then(|route| route.directed_sender()).map(lineage_hex),
                        "outward_from_association_phase_numerator": outward_from_association_phase.to_string(),
                        "retained_causal_founder": retained_causal_founder,
                        "retained_external_founder": retained_external_founder,
                    })
                })
            })
            .collect::<Vec<_>>();
        let motor_contact_witnesses = target_preparations
            .iter()
            .flat_map(|preparation| {
                preparation.motors.iter().map(|motor| {
                    let route = observation.physical_frontier_routes.iter().find(|route| {
                        route.bond() == motor.bond
                            && super::canonical_lineage_pair(
                                route.seed_lineage(),
                                route.adjacent_lineage(),
                            ) == super::canonical_lineage_pair(
                                preparation.ordering_lineage,
                                motor.lineage,
                            )
                    });
                    let contact = successor
                        .topology_index
                        .contacts
                        .iter()
                        .find(|contact| contact.stable_bond == motor.bond)
                        .expect("vocal motor contact exists in exact successor topology");
                    let super::ResidentContactOrigin::Fabric { contact_index } = contact.origin else {
                        panic!("learned vocal motor contact is resident fabric");
                    };
                    let anatomy = successor.electrical_fabric.anatomy().contact_anatomies()
                        [contact_index];
                    let (left_index, _) = anatomy.endpoints();
                    let left_lineage = successor.electrical_fabric.lineages()[left_index];
                    let phase_numerator = successor.electrical_fabric.state().contact_states()
                        [contact_index]
                        .carrier_phase()
                        .parts()
                        .0;
                    let outward_from_ordering_phase =
                        if left_lineage == preparation.ordering_lineage {
                            phase_numerator
                        } else {
                            -phase_numerator
                        };
                    let recruitment = observation.motor_unit_recruitments.iter().find(|event| {
                        event.neuron_lineage == motor.lineage
                    });
                    json!({
                        "ordering": lineage_hex(preparation.ordering_lineage),
                        "motor": lineage_hex(motor.lineage),
                        "visited": route.is_some(),
                        "seed": route.map(|route| lineage_hex(route.seed_lineage())),
                        "adjacent": route.map(|route| lineage_hex(route.adjacent_lineage())),
                        "directed_sender": route.and_then(|route| route.directed_sender()).map(lineage_hex),
                        "outward_from_ordering_phase_numerator": outward_from_ordering_phase.to_string(),
                        "recruited_carriers": recruitment.map(|event| event.outward_elementary_carriers.to_string()),
                    })
                })
            })
            .collect::<Vec<_>>();
        let total_offered = observation
            .learned_motor_work_preparations
            .iter()
            .fold(BigRational::zero(), |sum, preparation| {
                sum + &preparation.total_offered_work_zeptojoules
            });
        let total_accepted = observation
            .learned_motor_work_preparations
            .iter()
            .fold(BigRational::zero(), |sum, preparation| {
                sum + &preparation.accepted_work_zeptojoules
            });
        let continuation_routes = target_motors
            .iter()
            .flat_map(|motor| {
                super::lean_sensorimotor_route::vocal_cognitive_action_continuation_routes_for_motor(
                    &successor.cohorts,
                    &successor.topology_index,
                    *motor,
                )
                .expect("continuation routes resolve for exact clock witness")
            })
            .collect::<Vec<_>>();
        let mut continuation_branches_visited = 0usize;
        let mut continuation_source_to_destination_transfers = 0usize;
        let mut continuation_destination_to_source_transfers = 0usize;
        let mut continuation_zero_carrier_branches = 0usize;
        let mut continuation_forward_carrier_phases = 0usize;
        let mut continuation_reverse_carrier_phases = 0usize;
        let mut continuation_zero_carrier_phases = 0usize;
        let mut continuation_phase_witnesses = Vec::new();
        for route in &observation.physical_frontier_routes {
            let Some(continuation) = continuation_routes.iter().find(|continuation| {
                continuation.continuation_bond == route.bond()
                    && super::canonical_lineage_pair(
                        continuation.source_ordering_lineage,
                        continuation.destination_ordering_lineage,
                    ) == super::canonical_lineage_pair(
                        route.seed_lineage(),
                        route.adjacent_lineage(),
                    )
            }) else {
                continue;
            };
            continuation_branches_visited += 1;
            match route.directed_sender() {
                Some(sender) if sender == continuation.source_ordering_lineage => {
                    continuation_source_to_destination_transfers += 1;
                }
                Some(sender) if sender == continuation.destination_ordering_lineage => {
                    continuation_destination_to_source_transfers += 1;
                }
                Some(_) => panic!("continuation transfer sender belongs to exact bond"),
                None => continuation_zero_carrier_branches += 1,
            }
            let contact = successor
                .topology_index
                .contacts
                .iter()
                .find(|contact| contact.stable_bond == continuation.continuation_bond)
                .expect("continuation contact exists in exact successor topology");
            let super::ResidentContactOrigin::Fabric { contact_index } = contact.origin else {
                panic!("learned continuation contact is resident fabric");
            };
            let anatomy = successor.electrical_fabric.anatomy().contact_anatomies()[contact_index];
            let (left_index, _) = anatomy.endpoints();
            let left_lineage = successor.electrical_fabric.lineages()[left_index];
            let phase_numerator = successor.electrical_fabric.state().contact_states()
                [contact_index]
                .carrier_phase()
                .parts()
                .0;
            let outward_from_source_phase = if left_lineage == continuation.source_ordering_lineage
            {
                phase_numerator
            } else {
                -phase_numerator
            };
            match outward_from_source_phase.cmp(&0) {
                std::cmp::Ordering::Greater => continuation_forward_carrier_phases += 1,
                std::cmp::Ordering::Less => continuation_reverse_carrier_phases += 1,
                std::cmp::Ordering::Equal => continuation_zero_carrier_phases += 1,
            }
            let current_from_seed = route.outward_current_from_seed_picoamperes();
            let current_from_source =
                if route.seed_lineage() == continuation.source_ordering_lineage {
                    current_from_seed
                } else if route.seed_lineage() == continuation.destination_ordering_lineage {
                    current_from_seed
                        .checked_neg()
                        .expect("continuation current orientation is exact")
                } else {
                    panic!("continuation frontier seed belongs to exact bond");
                }
                .parts();
            continuation_phase_witnesses.push(json!({
                "source": lineage_hex(continuation.source_ordering_lineage),
                "destination": lineage_hex(continuation.destination_ordering_lineage),
                "seed": lineage_hex(route.seed_lineage()),
                "adjacent": lineage_hex(route.adjacent_lineage()),
                "directed_sender": route.directed_sender().map(lineage_hex),
                "outward_current_from_source_picoamperes": {
                    "numerator": current_from_source.0.to_string(),
                    "denominator": current_from_source.1.to_string(),
                },
                "outward_from_source_phase_numerator": outward_from_source_phase.to_string(),
            }));
        }
        let retained_destination_continuation_frontiers = continuation_routes
            .iter()
            .filter(|continuation| {
                super::lean_sensorimotor_route::frontier_carries_vocal_action_continuation(
                    &successor.active_electrical_frontier,
                    continuation,
                )
            })
            .count();
        let retained_source_continuation_frontiers = continuation_routes
            .iter()
            .filter(|continuation| {
                successor.active_electrical_frontier.iter().any(|entry| {
                    entry.frontier_lineage() == continuation.source_ordering_lineage
                        && ((entry.is_in_flight()
                            && entry.sender() == Some(continuation.source_ordering_lineage)
                            && entry.receiver() == continuation.destination_ordering_lineage
                            && entry
                                .cause
                                .is_some_and(|cause| cause.bond == continuation.continuation_bond))
                            || entry.directed_transfer().is_some_and(|transfer| {
                                transfer.bond == continuation.continuation_bond
                                    && super::canonical_lineage_pair(
                                        transfer.sender,
                                        transfer.receiver,
                                    ) == super::canonical_lineage_pair(
                                        continuation.source_ordering_lineage,
                                        continuation.destination_ordering_lineage,
                                    )
                            }))
                })
            })
            .count();
        let mut ordering_lineages = target_preparations
            .iter()
            .map(|preparation| preparation.ordering_lineage)
            .chain(continuation_routes.iter().flat_map(|route| {
                [
                    route.source_ordering_lineage,
                    route.destination_ordering_lineage,
                ]
            }))
            .collect::<Vec<_>>();
        ordering_lineages.sort_unstable();
        ordering_lineages.dedup();
        let ordering_membrane_witnesses = ordering_lineages
            .into_iter()
            .map(|ordering| {
                let flat = successor
                    .topology_index
                    .flat_for_lineage(ordering)
                    .expect("target ordering resolves in exact successor topology");
                let (cohort_index, neuron_index, _) = successor.topology_index.flat_locations[flat];
                let anatomy =
                    &successor.cohorts[cohort_index].anatomy.neuron_anatomies()[neuron_index];
                let neuron = &successor.cohorts[cohort_index].state.neurons()[neuron_index];
                let capacitance = anatomy.capacitance().picofarads().parts();
                let potential = neuron
                    .membrane_state()
                    .potential_millivolts(anatomy.capacitance())
                    .expect("target ordering potential is exact")
                    .parts();
                json!({
                    "ordering": lineage_hex(ordering),
                    "separated_elementary_charges": neuron
                        .separated_elementary_charges()
                        .to_string(),
                    "intracellular_carriers": neuron
                        .carrier_reservoirs()
                        .intracellular()
                        .to_string(),
                    "retained_receptor_work_zeptojoules": neuron
                        .receptor_quantum_residue
                        .energy()
                        .to_string(),
                    "gate_open_population": neuron.gate.open_population().to_string(),
                    "gate_dissipated_quanta": neuron.gate.dissipated_quanta().to_string(),
                    "capacitance_picofarads": {
                        "numerator": capacitance.0.to_string(),
                        "denominator": capacitance.1.to_string(),
                    },
                    "potential_millivolts": {
                        "numerator": potential.0.to_string(),
                        "denominator": potential.1.to_string(),
                    },
                })
            })
            .collect::<Vec<_>>();
        let continuation_route_count = observation
            .learned_motor_work_preparations
            .iter()
            .flat_map(|preparation| preparation.routes.iter())
            .filter(|route| {
                successor
                    .topology_index
                    .layer_of(route.founding_receiver_lineage)
                    == Some(11)
            })
            .count();
        let active_external_frontier_count = successor
            .active_electrical_frontier
            .iter()
            .filter(|entry| entry.carries_external_ingress_cause())
            .count();
        let target_association_integrations = target_associations
            .iter()
            .flat_map(|association| {
                let association_flat = successor
                    .topology_index
                    .flat_for_lineage(*association)
                    .expect("target association resolves in exact successor topology");
                successor.topology_index.incident_contacts_by_flat[association_flat]
                    .iter()
                    .filter_map(|contact_index| {
                        let contact = successor.topology_index.contacts[*contact_index];
                        let other_flat = if contact.left == association_flat {
                            contact.right
                        } else {
                            contact.left
                        };
                        let lineage = successor.topology_index.flat_locations[other_flat].2;
                        (successor.topology_index.layer_of(lineage) == Some(6)).then_some(lineage)
                    })
                    .collect::<Vec<_>>()
            })
            .collect::<std::collections::BTreeSet<_>>();
        let target_association_recurrences = target_associations
            .iter()
            .flat_map(|association| {
                let association_flat = successor
                    .topology_index
                    .flat_for_lineage(*association)
                    .expect("target association resolves in exact successor topology");
                successor.topology_index.neighbours_by_flat[association_flat]
                    .iter()
                    .filter_map(|flat| {
                        let lineage = successor.topology_index.flat_locations[*flat].2;
                        (successor.topology_index.layer_of(lineage) == Some(9)).then_some(lineage)
                    })
                    .collect::<Vec<_>>()
            })
            .collect::<std::collections::BTreeSet<_>>();
        let mut target_integration_sources_by_layer = std::collections::BTreeMap::new();
        for integration in &target_association_integrations {
            let integration_flat = successor
                .topology_index
                .flat_for_lineage(*integration)
                .expect("target integration resolves in exact successor topology");
            for contact_index in
                &successor.topology_index.incident_contacts_by_flat[integration_flat]
            {
                let contact = successor.topology_index.contacts[*contact_index];
                let other_flat = if contact.left == integration_flat {
                    contact.right
                } else {
                    contact.left
                };
                let (cohort_index, neuron_index, _) =
                    successor.topology_index.flat_locations[other_flat];
                let mount = &successor.cohorts[cohort_index].anatomy.mounts()[neuron_index];
                if mount.source_site().is_some() {
                    *target_integration_sources_by_layer
                        .entry(mount.place().layer())
                        .or_insert(0usize) += 1;
                }
            }
        }
        let active_external_target_association_frontiers = successor
            .active_electrical_frontier
            .iter()
            .filter(|entry| {
                entry.carries_external_ingress_cause()
                    && target_associations.contains(&entry.frontier_lineage())
            })
            .count();
        let active_external_target_integration_frontiers = successor
            .active_electrical_frontier
            .iter()
            .filter(|entry| {
                entry.carries_external_ingress_cause()
                    && target_association_integrations.contains(&entry.frontier_lineage())
            })
            .count();
        let active_external_target_recurrence_frontiers = successor
            .active_electrical_frontier
            .iter()
            .filter(|entry| {
                entry.carries_external_ingress_cause()
                    && target_association_recurrences.contains(&entry.frontier_lineage())
            })
            .count();
        let mut active_external_frontiers_by_layer = std::collections::BTreeMap::new();
        for layer in successor
            .active_electrical_frontier
            .iter()
            .filter(|entry| entry.carries_external_ingress_cause())
            .filter_map(|entry| successor.topology_index.layer_of(entry.frontier_lineage()))
        {
            *active_external_frontiers_by_layer
                .entry(layer)
                .or_insert(0usize) += 1;
        }
        let active_direct_vocal_motor_frontiers = successor
            .active_electrical_frontier
            .iter()
            .filter_map(|entry| entry.directed_transfer())
            .filter(|transfer| {
                successor.topology_index.layer_of(transfer.sender) == Some(11)
                    && target_motors.contains(&transfer.receiver)
            })
            .count();
        learned_work_by_clock.push(json!({
            "clock": clock,
            "externally_perturbed_neuron_count": observation.externally_perturbed_neuron_lineages.len(),
            "external_reassembly_count": observation.externally_reassembled_formation_frontiers.len(),
            "exact_sound_reassembled_member_count": exact_sound_reassembled_members.len(),
            "exact_sound_reassembled_members_by_layer": exact_sound_reassembled_members_by_layer,
            "exact_sound_target_associations": exact_sound_target_associations,
            "exact_sound_reassembled_founders": exact_sound_reassembled_founders,
            "external_reassembly_witnesses": external_reassembly_witnesses,
            "externally_reassembled_preparations": externally_reassembled_preparations,
            "active_reassembled_association_frontiers": active_reassembled_association_frontiers,
            "founder_contact_witnesses": founder_contact_witnesses,
            "motor_contact_witnesses": motor_contact_witnesses,
            "preparation_count": observation.learned_motor_work_preparations.len(),
            "continuation_route_count": continuation_route_count,
            "eligible_continuation_route_count": continuation_routes.len(),
            "continuation_branches_visited": continuation_branches_visited,
            "continuation_source_to_destination_transfers": continuation_source_to_destination_transfers,
            "continuation_destination_to_source_transfers": continuation_destination_to_source_transfers,
            "continuation_zero_carrier_branches": continuation_zero_carrier_branches,
            "continuation_forward_carrier_phases": continuation_forward_carrier_phases,
            "continuation_reverse_carrier_phases": continuation_reverse_carrier_phases,
            "continuation_zero_carrier_phases": continuation_zero_carrier_phases,
            "continuation_phase_witnesses": continuation_phase_witnesses,
            "ordering_membrane_witnesses": ordering_membrane_witnesses,
            "retained_destination_continuation_frontiers": retained_destination_continuation_frontiers,
            "retained_source_continuation_frontiers": retained_source_continuation_frontiers,
            "active_external_frontier_count": active_external_frontier_count,
            "active_external_target_association_frontiers": active_external_target_association_frontiers,
            "active_external_target_integration_frontiers": active_external_target_integration_frontiers,
            "active_external_target_recurrence_frontiers": active_external_target_recurrence_frontiers,
            "target_integration_sources_by_layer": target_integration_sources_by_layer,
            "active_external_frontiers_by_layer": active_external_frontiers_by_layer,
            "active_direct_vocal_motor_frontiers": active_direct_vocal_motor_frontiers,
            "total_offered_work_zeptojoules": total_offered.to_string(),
            "total_accepted_work_zeptojoules": total_accepted.to_string(),
            "vocal_work_diagnostic": {
                "exact_route_matches": route_matches,
                "current_sound_matches": sound_matches,
                "exact_source_transitions": source_transitions,
                "work_offers": work_offers,
                "accepted_work_preparations": work_acceptances,
            },
        }));
        let vocal = observation
            .motor_unit_recruitments
            .iter()
            .filter(|event| target_motors.contains(&event.neuron_lineage))
            .collect::<Vec<_>>();
        let respiratory = observation
            .articulatory_unit_recruitments
            .iter()
            .try_fold(0_u128, |total, event| {
                total.checked_add(event.outward_elementary_carriers)
            })
            .expect("continuation respiratory width");
        respiratory_carriers = respiratory_carriers
            .checked_add(respiratory)
            .expect("continuation respiratory total remains bounded");
        if !vocal.is_empty() || respiratory != 0 {
            let directions = vocal
                .iter()
                .filter_map(|event| terminal_by_motor.get(&event.neuron_lineage))
                .map(|terminal| format!("{:?}", terminal.direction()))
                .collect::<std::collections::BTreeSet<_>>();
            pulses.push(json!({
                "clock": clock,
                "motor_count": vocal.len(),
                "directions": directions,
                "respiratory_carriers": respiratory.to_string(),
                "motors": vocal.iter().map(|event| json!({
                    "lineage": lineage_hex(event.neuron_lineage),
                    "terminal": format!("{:?}", event.body_effector_terminal),
                    "carriers": event.outward_elementary_carriers.to_string(),
                    "preparation_transfers": event.preparation_transfers.iter().map(|preparation| json!({
                        "sender": lineage_hex(preparation.transfer.sender),
                        "receiver": lineage_hex(preparation.transfer.receiver),
                        "sender_layer": preparation.sender_layer,
                        "transferred_whole_carriers": preparation.transfer.transferred_whole_carriers.to_string(),
                        "bond": format!("{:?}", preparation.transfer.bond),
                    })).collect::<Vec<_>>(),
                    "learned_work_preparations": event.learned_work_preparations.iter().map(|preparation| json!({
                        "accepted_work_zeptojoules": preparation.accepted_work_zeptojoules.to_string(),
                        "routes": preparation.routes.iter().map(|route| json!({
                            "ordering": lineage_hex(route.ordering_lineage),
                            "founding_receiver": lineage_hex(route.founding_receiver_lineage),
                            "founding_bond": format!("{:?}", route.founding_bond),
                            "learned_bond": format!("{:?}", route.learned_bond),
                            "offered_work_zeptojoules": route.offered_work_zeptojoules.to_string(),
                        })).collect::<Vec<_>>(),
                    })).collect::<Vec<_>>(),
                })).collect::<Vec<_>>(),
            }));
        }
        let mut carriers_by_terminal = std::collections::BTreeMap::new();
        for event in &observation.motor_unit_recruitments {
            let carriers = carriers_by_terminal
                .entry(event.body_effector_terminal)
                .or_insert(0_u128);
            *carriers = carriers
                .checked_add(event.outward_elementary_carriers)
                .expect("continuation motor carriers remain bounded");
        }
        let admitted = if carriers_by_terminal.is_empty() {
            AdmittedBodyEffectorDrives::quiescent()
        } else {
            AdmittedBodyEffectorDrives::admit(
                carriers_by_terminal
                    .into_iter()
                    .map(
                        |(terminal, outward_elementary_carriers)| BodyEffectorDrive {
                            terminal,
                            outward_elementary_carriers,
                        },
                    )
                    .collect(),
            )
            .expect("continuation motor drives admit")
        };
        let moved =
            settle_body_effector_drives(&body, &admitted, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
                .expect("continuation vocal tissue settles");
        let acoustic = settle_native_articulatory_interval(
            moved.successor,
            &moved.proprioceptive_consequences,
            respiratory,
            4_000,
        )
        .expect("continuation vocal acoustics settle");
        if first_audible_frame.is_none()
            && acoustic
                .radiated_pressure_pcm
                .iter()
                .any(|sample| *sample != 0)
        {
            first_audible_frame = Some(acoustic.radiated_pressure_pcm.clone());
        }
        pressure.extend_from_slice(&acoustic.radiated_pressure_pcm);
        if !moved.proprioceptive_consequences.is_empty() {
            pending_motor_consequence = Some(
                admit_articulated_body_consequence_source(
                    occurrence
                        .checked_add(clock)
                        .and_then(|tick| tick.checked_add(1))
                        .expect("continuation motor consequence tick"),
                    &moved.proprioceptive_consequences,
                )
                .expect("continuation organism consequence source admits"),
            );
        }
        if acoustic
            .radiated_pressure_pcm
            .iter()
            .any(|sample| *sample != 0)
        {
            pending_self_pressure =
                Some(probe_self_hearing_episode(&acoustic.radiated_pressure_pcm));
        }
        state = successor;
        body = acoustic.successor_body;
    }

    GuidedVocalContinuation {
        state,
        body,
        residency,
        pulses,
        pressure,
        first_audible_frame,
        respiratory_carriers,
        internal_reassemblies,
        causal_thought_transitions,
        learned_work_by_clock,
    }
}

fn saved_guided_vocal_tail_json(
    mut state: ResidentCognitiveFormationState,
    mut body: ArticulatedBodyState,
    cue_pressure: Vec<i16>,
    occurrence: u64,
    maximum_clocks: u64,
    guide_carriers: u128,
    sound_only: bool,
) -> Value {
    let target_axes = [
        BodyAxis::VocalTractSection0Area,
        BodyAxis::VocalTractSection1Area,
        BodyAxis::VocalTractSection2Area,
        BodyAxis::VocalTractSection7Area,
    ];
    let target_terminals = target_axes
        .iter()
        .copied()
        .flat_map(|axis| {
            [
                BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum),
                BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMaximum),
            ]
        })
        .collect::<std::collections::BTreeSet<_>>();
    let terminal_by_motor = state
        .cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
        })
        .filter_map(|(mount, lineage)| {
            mount
                .body_effector_terminal()
                .filter(|terminal| target_terminals.contains(terminal))
                .map(|terminal| (*lineage, terminal))
        })
        .collect::<std::collections::BTreeMap<_, _>>();
    let target_motors = terminal_by_motor
        .keys()
        .copied()
        .collect::<std::collections::BTreeSet<_>>();
    let baseline_clocks = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_BASELINE_CLOCKS")
        .ok()
        .map(|value| {
            value
                .parse::<u64>()
                .expect("saved-tail baseline clocks are u64")
        })
        .unwrap_or(0);
    assert!(baseline_clocks <= 64);
    let baseline = (baseline_clocks > 0).then(|| {
        run_guided_vocal_continuation(
            state.clone(),
            body.clone(),
            None,
            &[],
            occurrence,
            baseline_clocks,
            &target_motors,
            &terminal_by_motor,
        )
    });
    let baseline_observation = baseline.as_ref().map(|baseline| {
        json!({
            "clocks": baseline_clocks,
            "pulses": baseline.pulses,
            "respiratory_carriers": baseline.respiratory_carriers.to_string(),
            "nonzero_pressure_samples": baseline.pressure.iter().filter(|sample| **sample != 0).count(),
            "learned_work_by_clock": baseline.learned_work_by_clock,
        })
    });
    let mut cue_residency = None;
    if let Some(baseline) = baseline {
        state = baseline.state;
        body = baseline.body;
        cue_residency = baseline.residency;
    }
    let (cue_body, mut cue_sources) = if sound_only {
        (body, Vec::new())
    } else {
        let cue_drives = AdmittedBodyEffectorDrives::admit(
            target_axes
                .iter()
                .copied()
                .map(|axis| BodyEffectorDrive {
                    terminal: BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum),
                    outward_elementary_carriers: guide_carriers,
                })
                .collect(),
        )
        .expect("saved-tail cue drives admit");
        let cue_moved =
            settle_body_effector_drives(&body, &cue_drives, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
                .expect("saved-tail cue tissue settles");
        let cue_body_source = admit_articulated_body_consequence_source(
            occurrence.checked_add(1).expect("saved-tail cue tick"),
            &cue_moved.proprioceptive_consequences,
        )
        .expect("saved-tail body consequence admits");
        (cue_moved.successor, vec![cue_body_source])
    };
    let cue_pressure_source = if sound_only {
        probe_hearing_episode(&cue_pressure, "candidate-exact-external-tutor-pressure")
    } else {
        probe_self_hearing_episode(&cue_pressure)
    };
    cue_sources.push(cue_pressure_source);
    let positive = run_guided_vocal_continuation(
        state,
        cue_body,
        cue_residency,
        &cue_sources,
        occurrence,
        maximum_clocks,
        &target_motors,
        &terminal_by_motor,
    );
    let encoded = positive
        .state
        .encode(usize::MAX)
        .expect("saved-tail successor encodes");
    let cold = ResidentCognitiveFormationState::decode(&encoded, usize::MAX)
        .expect("saved-tail successor cold-decodes");
    let cold_exact = cold
        .encode(usize::MAX)
        .expect("saved-tail cold successor re-encodes")
        == encoded;
    let successor_state_output = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_STATE_OUT")
        .ok()
        .map(|path| {
            fs::write(&path, &encoded).expect("saved-tail cognitive successor writes");
            json!({"path": path, "bytes": encoded.len()})
        });
    let successor_body_output = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_BODY_OUT")
        .ok()
        .map(|path| {
            let encoded_body = positive.body.encode().expect("saved-tail body encodes");
            fs::write(&path, &encoded_body).expect("saved-tail body successor writes");
            json!({"path": path, "bytes": encoded_body.len()})
        });
    json!({
        "measurement_only": true,
        "sound_only": sound_only,
        "saved_taught_state_advanced": true,
        "pre_cue_baseline": baseline_observation,
        "maximum_clocks": maximum_clocks,
        "pulses": positive.pulses,
        "respiratory_carriers": positive.respiratory_carriers.to_string(),
        "nonzero_pressure_samples": positive.pressure.iter().filter(|sample| **sample != 0).count(),
        "learned_work_by_clock": positive.learned_work_by_clock,
        "internal_reassemblies": positive.internal_reassemblies,
        "causal_thought_transitions": positive.causal_thought_transitions,
        "cold_round_trip_exact": cold_exact,
        "successor_body_acoustic_quiescent": positive
            .body
            .articulatory_acoustic_state()
            .is_quiescent(),
        "encoded_bytes": encoded.len(),
        "successor_state_output": successor_state_output,
        "successor_body_output": successor_body_output,
    })
}

fn guided_vocal_population_growth_json(
    initial: &ResidentCognitiveFormationState,
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    let Some(mut body) = articulated_body.cloned() else {
        return json!({"error": "copied articulated body absent"});
    };
    super::reset_vocal_work_diagnostic();
    let target_axes = [
        BodyAxis::VocalTractSection0Area,
        BodyAxis::VocalTractSection1Area,
        BodyAxis::VocalTractSection2Area,
        BodyAxis::VocalTractSection7Area,
    ];
    let target_terminals = target_axes
        .iter()
        .copied()
        .flat_map(|axis| {
            [
                BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum),
                BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMaximum),
            ]
        })
        .collect::<std::collections::BTreeSet<_>>();
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let vocal_routes = |state: &ResidentCognitiveFormationState| {
        let mut routes = std::collections::BTreeSet::new();
        for (mount, motor) in state.cohorts.iter().flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
        }) {
            let Some(terminal) = mount.body_effector_terminal() else {
                continue;
            };
            if !target_terminals.contains(&terminal) {
                continue;
            }
            for route in super::lean_sensorimotor_route::vocal_cognitive_action_route_for_motor(
                &state.cohorts,
                &state.topology_index,
                *motor,
            )
            .expect("persisted coordinated vocal route resolves")
            {
                routes.insert((route.preparation.ordering_lineage, *motor, terminal));
            }
        }
        routes
    };
    let vocal_learning_frontier = |state: &ResidentCognitiveFormationState| {
        let mut seen = std::collections::BTreeSet::new();
        let mut records = Vec::new();
        for (_, motor, terminal) in vocal_routes(state) {
            for route in super::lean_sensorimotor_route::vocal_cognitive_action_route_for_motor(
                &state.cohorts,
                &state.topology_index,
                motor,
            )
            .expect("persisted vocal route resolves")
            {
                for association in &route.preparation.associations {
                    if !seen.insert((
                        association.lineage,
                        route.preparation.ordering_lineage,
                        route.motor_lineage,
                    )) {
                        continue;
                    }
                    let contact = state
                        .topology_index
                        .contacts
                        .iter()
                        .find(|contact| contact.stable_bond == association.bond)
                        .expect("vocal posture founding contact remains mounted");
                    let super::ResidentContactOrigin::Fabric { contact_index } = contact.origin
                    else {
                        panic!("vocal posture founding contact is resident fabric");
                    };
                    let (left, _) = state.electrical_fabric.anatomy().contact_anatomies()
                        [contact_index]
                        .endpoints();
                    let association_is_left =
                        state.electrical_fabric.lineages()[left] == association.lineage;
                    let (phase_numerator, phase_denominator) =
                        state.electrical_fabric.state().contact_states()[contact_index]
                            .carrier_phase()
                            .parts();
                    let phase_from_association = if association_is_left {
                        phase_numerator
                    } else {
                        -phase_numerator
                    };
                    let exact_frontier = state
                        .active_electrical_frontier
                        .iter()
                        .copied()
                        .filter(|entry| {
                            entry
                                .cause
                                .is_some_and(|cause| cause.bond == association.bond)
                                && entry.sender() == Some(association.lineage)
                                && entry.receiver() == route.preparation.ordering_lineage
                        })
                        .map(|entry| {
                            json!({
                                "in_flight": entry.is_in_flight(),
                                "whole_carriers": entry.directed_transfer().map(|transfer| {
                                    transfer.transferred_whole_carriers.to_string()
                                }),
                                "body_owned_acoustic_efference": entry
                                    .carries_body_owned_acoustic_efference(),
                            })
                        })
                        .collect::<Vec<_>>();
                    records.push(json!({
                        "association": lineage_hex(association.lineage),
                        "ordering": lineage_hex(route.preparation.ordering_lineage),
                        "motor": lineage_hex(route.motor_lineage),
                        "terminal": format!("{terminal:?}"),
                        "phase_from_association": format!(
                            "{phase_from_association}/{phase_denominator}"
                        ),
                        "exact_frontier": exact_frontier,
                    }));
                }
            }
        }
        records
    };
    let before = vocal_routes(initial);
    let mut state = initial.clone();
    let maximum_cycles = std::env::var("GUALA_PROBE_GUIDED_VOCAL_CYCLES")
        .ok()
        .map(|value| value.parse::<u32>().expect("guided vocal cycles are u32"))
        .unwrap_or(64);
    assert!((1..=512).contains(&maximum_cycles));
    let sequence_repetitions = std::env::var("GUALA_PROBE_GUIDED_VOCAL_SEQUENCE_REPETITIONS")
        .ok()
        .map(|value| {
            value
                .parse::<u32>()
                .expect("guided vocal sequence repetitions are u32")
        })
        .unwrap_or(8);
    assert!((1..=64).contains(&sequence_repetitions));
    let guide_carriers = std::env::var("GUALA_PROBE_GUIDED_VOCAL_CARRIERS")
        .ok()
        .map(|value| {
            value
                .parse::<u128>()
                .expect("guided vocal carriers are u128")
        })
        .unwrap_or(1_500);
    assert!((1..=10_000).contains(&guide_carriers));
    let tutor_pressure_bytes = fs::read(
        std::env::var("GUALA_PROBE_GUIDED_VOCAL_TUTOR_PRESSURE_PCM")
            .expect("guided vocal tutor pressure path must be set"),
    )
    .expect("guided vocal tutor pressure reads");
    assert!(
        matches!(tutor_pressure_bytes.len(), 8_000 | 32_000),
        "guided vocal tutor pressure is one or four exact 4,000-sample intervals",
    );
    let tutor_pressure = tutor_pressure_bytes
        .chunks_exact(2)
        .map(|sample| i16::from_le_bytes([sample[0], sample[1]]))
        .collect::<Vec<_>>();
    assert!(
        tutor_pressure.iter().any(|sample| *sample != 0),
        "guided vocal tutor pressure must contain physical pressure",
    );
    let tutor_pressure_phases = tutor_pressure.chunks_exact(4_000).collect::<Vec<_>>();
    let route_growth_only =
        std::env::var_os("GUALA_PROBE_GUIDED_VOCAL_ROUTE_GROWTH_ONLY").is_some();
    let checkpoints = [1_u32, 2, 4, 8, 16, 32, 64, 128, 256];
    let mut observations = Vec::new();
    let mut vocal_learning_frontiers = Vec::new();
    let mut occurrence = 0_u64;
    let mut motor_discharges = 0_u64;
    let mut guided_vocal_discharges = Vec::new();
    let mut inter_demonstration_pulses = Vec::new();
    let mut completed_cycles = 0_u32;
    let mut guided_residency = None;
    let mut guided_pressure = Vec::<i16>::new();
    let mut first_learned_phase_pressure = None::<Vec<i16>>;
    let mut guided_respiratory_carriers = 0_u128;
    let mut guided_internal_reassemblies = 0_u64;
    let mut guided_causal_thought_transitions = 0_u64;
    let mut sequence_training_steps = 0_u32;
    let sequence_directions = [
        BodyEffectorDirection::TowardMinimum,
        BodyEffectorDirection::TowardMaximum,
        BodyEffectorDirection::TowardMinimum,
        BodyEffectorDirection::TowardMaximum,
    ];
    let sequence_start_phase = std::env::var("GUALA_PROBE_GUIDED_VOCAL_SEQUENCE_START_PHASE")
        .ok()
        .map(|value| {
            value
                .parse::<usize>()
                .expect("sequence start phase is usize")
        })
        .unwrap_or(0);
    assert!(sequence_start_phase < sequence_directions.len());
    let required_sequence_steps = sequence_repetitions
        .checked_mul(u32::try_from(sequence_directions.len()).unwrap())
        .expect("bounded sequence training width");
    let maximum_total_cycles = if route_growth_only {
        maximum_cycles
    } else {
        maximum_cycles
            .checked_add(required_sequence_steps)
            .expect("bounded guided range width")
    };
    'guided: for cycle in 1..=maximum_total_cycles {
        // Assistance follows the anatomy that has not yet completed its
        // learned population. Blind alternation is not a neutral control: the
        // organism's own sparse discharges have an endogenous phase, and the
        // old harness repeatedly assisted the opposite antagonist exactly
        // when the minimum anchor fired. Holding one ordinary tissue motion
        // until its bounded four-terminal cohort exists, then holding the
        // other, is the physical equivalent of a tutor sustaining the gesture.
        // It observes retained anatomy only; it neither predicts nor authors
        // a discharge, contact, carrier count, pose, or timing value.
        let reached_before = vocal_routes(&state)
            .iter()
            .map(|(_, _, terminal)| *terminal)
            .collect::<std::collections::BTreeSet<_>>();
        let direction_complete = |direction| {
            target_axes
                .iter()
                .copied()
                .all(|axis| reached_before.contains(&BodyEffectorTerminal::new(axis, direction)))
        };
        let population_complete = reached_before == target_terminals;
        if !population_complete && cycle > maximum_cycles {
            break 'guided;
        }
        let direction = if tutor_pressure_phases.len() == sequence_directions.len() {
            sequence_directions[(sequence_start_phase + usize::try_from(cycle - 1).unwrap())
                % sequence_directions.len()]
        } else if population_complete {
            sequence_directions[(sequence_start_phase
                + usize::try_from(sequence_training_steps).unwrap())
                % sequence_directions.len()]
        } else if !direction_complete(BodyEffectorDirection::TowardMinimum) {
            BodyEffectorDirection::TowardMinimum
        } else {
            BodyEffectorDirection::TowardMaximum
        };
        // Preserve the previously proved isolated-assistance boundary while
        // the missing spatial population grows. Once all eight terminals are
        // present, do not reset the body: the repeated antagonist phases must
        // unfold through the carried tissue, acoustic, neuronal, and recurrent
        // state that production itself retains.
        if occurrence != 0 && !population_complete {
            for _ in 0..32 {
                body = settle_body_effector_drives(
                    &body,
                    &AdmittedBodyEffectorDrives::quiescent(),
                    BODY_SETTLEMENT_CLOCK_MICROSECONDS,
                )
                .expect("guided vocal tissue recovery settles")
                .successor;
            }
        }
        occurrence += 1;
        let drives = AdmittedBodyEffectorDrives::admit(
            target_axes
                .iter()
                .copied()
                .map(|axis| BodyEffectorDrive {
                    terminal: BodyEffectorTerminal::new(axis, direction),
                    outward_elementary_carriers: guide_carriers,
                })
                .collect(),
        )
        .expect("finite guided vocal drives admit");
        let moved = settle_body_effector_drives(&body, &drives, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
            .expect("guided vocal tissue settles");
        let source = admit_articulated_body_consequence_source(
            occurrence,
            &moved.proprioceptive_consequences,
        )
        .expect("guided vocal consequence source admits");
        let tutor_pressure_source = probe_hearing_episode(
            tutor_pressure_phases[(sequence_start_phase + usize::try_from(cycle - 1).unwrap())
                % tutor_pressure_phases.len()],
            "candidate-exact-external-tutor-pressure",
        );
        let mut admitted_sources = vec![
            super::admitted_fixture_episode(&source),
            super::admitted_fixture_episode(&tutor_pressure_source),
        ];
        let (successor, observation) = state
            .advance_coexisting_admitted_transition_with_residency(
                &admitted_sources,
                usize::MAX,
                true,
                true,
                true,
                &mut guided_residency,
                ExactRational::integer(0),
            )
            .expect("guided consequence settles through production cognition");
        let vocal_discharges = observation
            .motor_unit_recruitments
            .iter()
            .filter(|event| target_axes.contains(&event.body_effector_terminal.axis()))
            .collect::<Vec<_>>();
        motor_discharges +=
            u64::try_from(vocal_discharges.len()).expect("vocal motor discharge count fits u64");
        guided_vocal_discharges.extend(vocal_discharges.into_iter().map(|event| {
            json!({
                "cycle": cycle,
                "occurrence": occurrence,
                "guided_direction": format!("{direction:?}"),
                "terminal": format!("{:?}", event.body_effector_terminal),
                "carriers": event.outward_elementary_carriers.to_string(),
                "learned_work_preparation_count": event.learned_work_preparations.len(),
            })
        }));
        guided_internal_reassemblies = guided_internal_reassemblies
            .checked_add(
                u64::try_from(observation.internally_reassembled_formation_cues.len())
                    .expect("guided internal reassembly count fits u64"),
            )
            .expect("guided internal reassembly count remains bounded");
        guided_causal_thought_transitions = guided_causal_thought_transitions
            .checked_add(
                observation
                    .internally_reassembled_formation_cues
                    .iter()
                    .map(|cue| u64::try_from(cue.causal_predecessors.len()).unwrap())
                    .sum::<u64>(),
            )
            .expect("guided causal thought transition count remains bounded");
        let mut carriers_by_terminal = std::collections::BTreeMap::new();
        for recruitment in &observation.motor_unit_recruitments {
            let carriers = carriers_by_terminal
                .entry(recruitment.body_effector_terminal)
                .or_insert(0_u128);
            *carriers = carriers
                .checked_add(recruitment.outward_elementary_carriers)
                .expect("guided motor carriers remain bounded");
        }
        let organism_drives = if carriers_by_terminal.is_empty() {
            AdmittedBodyEffectorDrives::quiescent()
        } else {
            AdmittedBodyEffectorDrives::admit(
                carriers_by_terminal
                    .into_iter()
                    .map(
                        |(terminal, outward_elementary_carriers)| BodyEffectorDrive {
                            terminal,
                            outward_elementary_carriers,
                        },
                    )
                    .collect(),
            )
            .expect("guided organism motor drives admit")
        };
        let organism_moved = settle_body_effector_drives(
            &moved.successor,
            &organism_drives,
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .expect("guided organism motor consequence settles");
        let respiratory = observation
            .articulatory_unit_recruitments
            .iter()
            .try_fold(0_u128, |total, event| {
                total.checked_add(event.outward_elementary_carriers)
            })
            .expect("guided respiratory width");
        guided_respiratory_carriers = guided_respiratory_carriers
            .checked_add(respiratory)
            .expect("guided respiratory total remains bounded");
        let acoustic = settle_native_articulatory_interval(
            organism_moved.successor,
            &organism_moved.proprioceptive_consequences,
            respiratory,
            4_000,
        )
        .expect("guided organism acoustics settle");
        if population_complete && first_learned_phase_pressure.is_none() {
            first_learned_phase_pressure = Some(acoustic.radiated_pressure_pcm.clone());
        }
        guided_pressure.extend_from_slice(&acoustic.radiated_pressure_pcm);
        state = successor;
        body = acoustic.successor_body;
        completed_cycles = cycle;
        vocal_learning_frontiers.push(json!({
            "cycle": cycle,
            "guided_direction": format!("{direction:?}"),
            "transfers": vocal_learning_frontier(&state),
        }));
        let routes = vocal_routes(&state);
        let reached = routes
            .iter()
            .map(|(_, _, terminal)| *terminal)
            .collect::<std::collections::BTreeSet<_>>();
        if checkpoints.contains(&cycle) || reached == target_terminals {
            observations.push(json!({
                "cycle": cycle,
                "vocal_route_count": routes.len(),
                "vocal_source_count": routes.iter().map(|(ordering, _, _)| *ordering).collect::<std::collections::BTreeSet<_>>().len(),
            }));
        }
        if population_complete {
            sequence_training_steps = sequence_training_steps
                .checked_add(1)
                .expect("guided sequence steps remain bounded");
        }
        if tutor_pressure_phases.len() == sequence_directions.len()
            && cycle % u32::try_from(sequence_directions.len()).unwrap() == 0
            && cycle < maximum_total_cycles
        {
            let pause_routes = vocal_routes(&state);
            let pause_motors = pause_routes
                .iter()
                .map(|(_, motor, _)| *motor)
                .collect::<std::collections::BTreeSet<_>>();
            let pause_terminals = pause_routes
                .iter()
                .map(|(_, motor, terminal)| (*motor, *terminal))
                .collect::<std::collections::BTreeMap<_, _>>();
            let pause = run_guided_vocal_continuation(
                state,
                body,
                guided_residency.take(),
                &[],
                occurrence,
                2,
                &pause_motors,
                &pause_terminals,
            );
            inter_demonstration_pulses.extend(pause.pulses.iter().cloned());
            guided_pressure.extend_from_slice(&pause.pressure);
            guided_respiratory_carriers = guided_respiratory_carriers
                .checked_add(pause.respiratory_carriers)
                .expect("guided pause respiratory total remains bounded");
            guided_internal_reassemblies = guided_internal_reassemblies
                .checked_add(pause.internal_reassemblies)
                .expect("guided pause reassembly count remains bounded");
            guided_causal_thought_transitions = guided_causal_thought_transitions
                .checked_add(pause.causal_thought_transitions)
                .expect("guided pause thought count remains bounded");
            state = pause.state;
            body = pause.body;
            guided_residency = pause.residency;
            occurrence = occurrence
                .checked_add(2)
                .expect("guided pause occurrence remains bounded");
        }
        if !route_growth_only
            && reached == target_terminals
            && sequence_training_steps >= required_sequence_steps
        {
            break 'guided;
        }
    }
    let after = vocal_routes(&state);
    if route_growth_only {
        let encoded = state
            .encode(usize::MAX)
            .expect("route-growth successor encodes");
        let teaching_state_output = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TEACHING_STATE_OUT")
            .ok()
            .map(|path| {
                fs::write(&path, &encoded).expect("route-growth cognitive state writes");
                json!({"path": path, "bytes": encoded.len()})
            });
        let teaching_body_output = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TEACHING_BODY_OUT")
            .ok()
            .map(|path| {
                let encoded_body = body.encode().expect("route-growth body encodes");
                fs::write(&path, &encoded_body).expect("route-growth body writes");
                json!({"path": path, "bytes": encoded_body.len()})
            });
        let cold = ResidentCognitiveFormationState::decode(&encoded, usize::MAX)
            .expect("route-growth successor cold-decodes");
        let cold_exact = cold
            .encode(usize::MAX)
            .expect("route-growth successor cold re-encodes")
            == encoded;
        let [route_matches, sound_matches, source_transitions, offers, acceptances] =
            super::vocal_work_diagnostic();
        return json!({
            "measurement_only": true,
            "route_growth_only": true,
            "single_sound_source_authority": true,
            "tutor_pressure_sample_count": tutor_pressure.len(),
            "tutor_phase_count": tutor_pressure_phases.len(),
            "maximum_cycles": maximum_cycles,
            "completed_cycles": completed_cycles,
            "before_route_count": before.len(),
            "after_route_count": after.len(),
            "added_route_count": after.len().saturating_sub(before.len()),
            "checkpoints": observations,
            "vocal_learning_frontiers": vocal_learning_frontiers,
            "motor_discharge_count": motor_discharges,
            "guided_vocal_discharges": guided_vocal_discharges,
            "guided_respiratory_carriers": guided_respiratory_carriers.to_string(),
            "guided_pressure_sample_count": guided_pressure.len(),
            "guided_pressure_nonzero_sample_count": guided_pressure.iter().filter(|sample| **sample != 0).count(),
            "first_learned_phase_pressure_nonzero_sample_count": first_learned_phase_pressure
                .as_ref()
                .map(|pressure| pressure.iter().filter(|sample| **sample != 0).count()),
            "vocal_work_diagnostic": {
                "exact_route_matches": route_matches,
                "current_sound_matches": sound_matches,
                "exact_source_transitions": source_transitions,
                "work_offers": offers,
                "accepted_work_preparations": acceptances,
            },
            "cold_round_trip_exact": cold_exact,
            "teaching_state_output": teaching_state_output,
            "teaching_body_output": teaching_body_output,
            "vocal_route_structure": vocal_route_structure_json(&state),
        });
    }
    let vocal_route_formation_memberships = |state: &ResidentCognitiveFormationState| {
        after
            .iter()
            .map(|(ordering, motor, terminal)| {
                let ordering_mosaics = state
                    .mosaics
                    .iter()
                    .filter(|retained| {
                        retained
                            .mosaic
                            .member_lineages()
                            .binary_search(ordering)
                            .is_ok()
                    })
                    .count();
                let motor_mosaics = state
                    .mosaics
                    .iter()
                    .filter(|retained| {
                        retained
                            .mosaic
                            .member_lineages()
                            .binary_search(motor)
                            .is_ok()
                    })
                    .count();
                let shared_mosaics = state
                    .mosaics
                    .iter()
                    .filter(|retained| {
                        retained
                            .mosaic
                            .member_lineages()
                            .binary_search(ordering)
                            .is_ok()
                            && retained
                                .mosaic
                                .member_lineages()
                                .binary_search(motor)
                                .is_ok()
                    })
                    .count();
                json!({
                    "ordering": lineage_hex(*ordering),
                    "motor": lineage_hex(*motor),
                    "terminal": format!("{terminal:?}"),
                    "ordering_mosaic_count": ordering_mosaics,
                    "motor_mosaic_count": motor_mosaics,
                    "shared_mosaic_count": shared_mosaics,
                })
            })
            .collect::<Vec<_>>()
    };
    let teaching_vocal_route_formation_memberships = vocal_route_formation_memberships(&state);
    let target_motors = after
        .iter()
        .map(|(_, motor, _)| *motor)
        .collect::<std::collections::BTreeSet<_>>();
    let terminal_by_motor = after
        .iter()
        .map(|(_, motor, terminal)| (*motor, *terminal))
        .collect::<std::collections::BTreeMap<_, _>>();
    let maximum_unguided_clocks = std::env::var("GUALA_PROBE_UNGUIDED_VOCAL_CLOCKS")
        .ok()
        .map(|value| value.parse::<u64>().expect("unguided vocal clocks are u64"))
        .unwrap_or(128);
    assert!((1..=1_024).contains(&maximum_unguided_clocks));
    let baseline_clocks = std::env::var("GUALA_PROBE_GUIDED_VOCAL_BASELINE_CLOCKS")
        .ok()
        .map(|value| {
            value
                .parse::<u64>()
                .expect("guided vocal baseline clocks are u64")
        })
        .unwrap_or(8);
    assert!((4..=64).contains(&baseline_clocks));
    let baseline = run_guided_vocal_continuation(
        state,
        body,
        guided_residency.take(),
        &[],
        occurrence,
        baseline_clocks,
        &target_motors,
        &terminal_by_motor,
    );
    let required_clean_baseline_clocks = baseline_clocks.min(4);
    let latest_baseline_pulse_clock = baseline
        .pulses
        .iter()
        .filter_map(|pulse| pulse.get("clock").and_then(Value::as_u64))
        .max()
        .unwrap_or(0);
    let clean_pressure_width = usize::try_from(required_clean_baseline_clocks)
        .expect("clean baseline clock width fits usize")
        .checked_mul(4_000)
        .expect("clean baseline pressure width remains bounded");
    let clean_pressure_start = baseline
        .pressure
        .len()
        .checked_sub(clean_pressure_width)
        .expect("baseline produced every requested pressure interval");
    let baseline_last_clocks_clean = latest_baseline_pulse_clock
        <= baseline_clocks - required_clean_baseline_clocks
        && baseline.pressure[clean_pressure_start..]
            .iter()
            .all(|sample| *sample == 0);
    let baseline_pulse_count = baseline.pulses.len();
    let baseline_pulses = baseline
        .pulses
        .iter()
        .map(|pulse| {
            json!({
                "clock": pulse.get("clock"),
                "motor_count": pulse.get("motor_count"),
                "directions": pulse.get("directions"),
                "respiratory_carriers": pulse.get("respiratory_carriers"),
            })
        })
        .collect::<Vec<_>>();
    let baseline_respiratory_carriers = baseline.respiratory_carriers;
    let baseline_nonzero_pressure_samples = baseline
        .pressure
        .iter()
        .filter(|sample| **sample != 0)
        .count();
    state = baseline.state;
    body = baseline.body;
    let teaching_encoded = state
        .encode(usize::MAX)
        .expect("guided teaching state encodes");
    let teaching_state_output = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TEACHING_STATE_OUT")
        .ok()
        .map(|path| {
            fs::write(&path, &teaching_encoded).expect("guided teaching cognitive state writes");
            json!({"path": path, "bytes": teaching_encoded.len()})
        });
    let teaching_body_output = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TEACHING_BODY_OUT")
        .ok()
        .map(|path| {
            let teaching_body_encoded = body.encode().expect("guided teaching body encodes");
            fs::write(&path, &teaching_body_encoded).expect("guided teaching body writes");
            json!({"path": path, "bytes": teaching_body_encoded.len()})
        });
    let teaching_cold = ResidentCognitiveFormationState::decode(&teaching_encoded, usize::MAX)
        .expect("guided teaching state cold-decodes");
    let teaching_cold_exact = teaching_cold
        .encode(usize::MAX)
        .expect("guided teaching cold re-encodes")
        == teaching_encoded;
    // The closed C-011/C-012 acceptance law is later partial-cue
    // continuation, not spontaneous initiation from silence. Recreate only
    // the first learned physical phase after cold: finite external tissue work
    // genuinely moves the copied body, its exact proprioception is admitted,
    // and the exact pressure Guala produced and heard during that first phase
    // is presented once. No later phase, motor request, trajectory, or sound
    // enters the organism. All following output must be organism-produced.
    let first_learned_phase_pressure = first_learned_phase_pressure
        .expect("complete learned sequence retained its first pressure phase");
    let continuation_cue_pressure_output =
        std::env::var("GUALA_PROBE_GUIDED_VOCAL_CUE_PRESSURE_PCM_OUT")
            .ok()
            .map(|path| {
                let pressure_bytes = first_learned_phase_pressure
                    .iter()
                    .flat_map(|sample| sample.to_le_bytes())
                    .collect::<Vec<_>>();
                fs::write(&path, &pressure_bytes).expect("continuation cue pressure writes");
                json!({"path": path, "bytes": pressure_bytes.len()})
            });
    let cue_drives = AdmittedBodyEffectorDrives::admit(
        target_axes
            .iter()
            .copied()
            .map(|axis| BodyEffectorDrive {
                terminal: BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum),
                outward_elementary_carriers: guide_carriers,
            })
            .collect(),
    )
    .expect("partial-cue drives admit");
    let cue_moved =
        settle_body_effector_drives(&body, &cue_drives, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
            .expect("partial-cue tissue settles");
    let cue_body_source = admit_articulated_body_consequence_source(
        occurrence.checked_add(1).expect("partial-cue tick"),
        &cue_moved.proprioceptive_consequences,
    )
    .expect("partial-cue body consequence admits");
    let cue_pressure_source = probe_self_hearing_episode(&first_learned_phase_pressure);
    let positive_cue_sources = vec![cue_body_source, cue_pressure_source];

    let positive = run_guided_vocal_continuation(
        teaching_cold.clone(),
        cue_moved.successor.clone(),
        None,
        &positive_cue_sources,
        occurrence,
        maximum_unguided_clocks,
        &target_motors,
        &terminal_by_motor,
    );

    // Negative controls run from exact clones of the same trained cold state.
    // They are comparison branches inside this one probe invocation and never
    // become organism state.
    let control_clocks = maximum_unguided_clocks.min(32);
    let silence = run_guided_vocal_continuation(
        teaching_cold.clone(),
        body.clone(),
        None,
        &[],
        occurrence,
        control_clocks,
        &target_motors,
        &terminal_by_motor,
    );
    let reversed_pressure = first_learned_phase_pressure
        .iter()
        .rev()
        .copied()
        .collect::<Vec<_>>();
    let reversed_source = probe_self_hearing_episode(&reversed_pressure);
    let reversed = run_guided_vocal_continuation(
        teaching_cold.clone(),
        body.clone(),
        None,
        &[reversed_source],
        occurrence,
        control_clocks,
        &target_motors,
        &terminal_by_motor,
    );
    let mut discontinuous_pressure = first_learned_phase_pressure.clone();
    let discontinuous_offset = discontinuous_pressure.len() / 2;
    discontinuous_pressure.rotate_left(discontinuous_offset);
    let discontinuous_source = probe_self_hearing_episode(&discontinuous_pressure);
    let discontinuous = run_guided_vocal_continuation(
        teaching_cold.clone(),
        body.clone(),
        None,
        &[discontinuous_source],
        occurrence,
        control_clocks,
        &target_motors,
        &terminal_by_motor,
    );
    let (severed_state, severed_contact_count) = severed_learned_motor_copy(&teaching_cold);
    let severed = run_guided_vocal_continuation(
        severed_state,
        cue_moved.successor,
        None,
        &positive_cue_sources,
        occurrence,
        control_clocks,
        &target_motors,
        &terminal_by_motor,
    );

    state = positive.state;
    let _positive_body = positive.body;
    let unguided_pulses = positive.pulses;
    let pressure = positive.pressure;
    let first_audible_frame = positive.first_audible_frame;
    let respiratory_carriers = positive.respiratory_carriers;
    let unguided_internal_reassemblies = positive.internal_reassemblies;
    let unguided_causal_thought_transitions = positive.causal_thought_transitions;
    let unguided_learned_work_by_clock = positive.learned_work_by_clock;
    let cue_control_results = json!({
        "control_clocks": control_clocks,
        "silence": {
            "pulses": silence.pulses,
            "learned_work_by_clock": silence.learned_work_by_clock,
            "respiratory_carriers": silence.respiratory_carriers.to_string(),
            "nonzero_pressure_samples": silence.pressure.iter().filter(|sample| **sample != 0).count(),
        },
        "time_reversed_first_pressure": {
            "pulses": reversed.pulses,
            "learned_work_by_clock": reversed.learned_work_by_clock,
            "respiratory_carriers": reversed.respiratory_carriers.to_string(),
            "nonzero_pressure_samples": reversed.pressure.iter().filter(|sample| **sample != 0).count(),
        },
        "discontinuous_first_pressure": {
            "pulses": discontinuous.pulses,
            "learned_work_by_clock": discontinuous.learned_work_by_clock,
            "respiratory_carriers": discontinuous.respiratory_carriers.to_string(),
            "nonzero_pressure_samples": discontinuous.pressure.iter().filter(|sample| **sample != 0).count(),
        },
        "severed": {
            "removed_learned_contact_count": severed_contact_count,
            "pulses": severed.pulses,
            "learned_work_by_clock": severed.learned_work_by_clock,
            "respiratory_carriers": severed.respiratory_carriers.to_string(),
            "nonzero_pressure_samples": severed.pressure.iter().filter(|sample| **sample != 0).count(),
        },
    });
    let pressure_peak = pressure
        .iter()
        .map(|sample| sample.unsigned_abs())
        .max()
        .unwrap_or(0);
    let nonzero_pressure_samples = pressure.iter().filter(|sample| **sample != 0).count();
    let self_hearing = first_audible_frame.as_ref().map(|frame| {
        let episode = probe_self_hearing_episode(frame);
        let locations = episode
            .joint_source_ports()
            .iter()
            .filter(|port| port.physical_quantity == "cochlear-band-pressure")
            .map(|port| {
                let site = super::NeuronSourceSite::from_source_port(port)
                    .expect("unguided cochlear source site");
                let (cohort_index, neuron_index, lineage) = state
                    .topology_index
                    .source_location(&site)
                    .expect("unguided cochlear topology lookup")
                    .expect("unguided cochlear receptor mounted");
                let neuron = &state.cohorts[cohort_index].state.neurons()[neuron_index];
                (
                    cohort_index,
                    neuron_index,
                    lineage,
                    neuron.receptor_quantum_residue.energy().clone(),
                    neuron.gate.open_population(),
                )
            })
            .collect::<Vec<_>>();
        let admitted = admitted_episode_with_authored_intervals(
            &episode,
            &vec![(1_i64, 4_i64); 3],
        )
        .expect("unguided self-hearing admission");
        let (successor, observation) = state
            .clone()
            .advance_admitted_transition(
                &admitted,
                usize::MAX,
                false,
                ExactRational::integer(0),
            )
            .expect("unguided self-hearing settles");
        let changed = locations
            .iter()
            .filter(|(cohort_index, neuron_index, _, before_residue, before_gate)| {
                let after = &successor.cohorts[*cohort_index].state.neurons()[*neuron_index];
                after.receptor_quantum_residue.energy() != before_residue
                    || after.gate.open_population() != *before_gate
            })
            .count();
        state = successor;
        json!({
            "cochlear_port_count": locations.len(),
            "changed_cochlear_count": changed,
            "physically_transitioned_neuron_count": observation.physically_transitioned_neuron_count,
            "dsf_delivery_count": observation.dsf_delivery_count,
        })
    });
    let pressure_wav = std::env::var("GUALA_PROBE_GUIDED_VOCAL_PRESSURE_WAV")
        .ok()
        .map(|path| {
            let data_bytes = u32::try_from(pressure.len() * std::mem::size_of::<i16>())
                .expect("guided vocal WAV data width");
            let mut wav = Vec::with_capacity(44 + data_bytes as usize);
            wav.extend_from_slice(b"RIFF");
            wav.extend_from_slice(&(36_u32 + data_bytes).to_le_bytes());
            wav.extend_from_slice(b"WAVEfmt ");
            wav.extend_from_slice(&16_u32.to_le_bytes());
            wav.extend_from_slice(&1_u16.to_le_bytes());
            wav.extend_from_slice(&1_u16.to_le_bytes());
            wav.extend_from_slice(&16_000_u32.to_le_bytes());
            wav.extend_from_slice(&32_000_u32.to_le_bytes());
            wav.extend_from_slice(&2_u16.to_le_bytes());
            wav.extend_from_slice(&16_u16.to_le_bytes());
            wav.extend_from_slice(b"data");
            wav.extend_from_slice(&data_bytes.to_le_bytes());
            for sample in &pressure {
                wav.extend_from_slice(&sample.to_le_bytes());
            }
            fs::write(&path, &wav).expect("guided vocal pressure WAV writes");
            json!({"path": path, "bytes": wav.len()})
        });
    let encoded = state.encode(usize::MAX).expect("guided successor encodes");
    let cold = ResidentCognitiveFormationState::decode(&encoded, usize::MAX)
        .expect("guided successor cold-decodes");
    let cold_exact = cold.encode(usize::MAX).expect("guided cold re-encodes") == encoded;
    let source_to_motors = after.iter().fold(
        std::collections::BTreeMap::<[u8; 16], std::collections::BTreeSet<[u8; 16]>>::new(),
        |mut map, (ordering, motor, _)| {
            map.entry(*ordering).or_default().insert(*motor);
            map
        },
    );
    let reached_terminals = after
        .iter()
        .map(|(_, _, terminal)| *terminal)
        .collect::<std::collections::BTreeSet<_>>();
    let mut result = json!({
        "measurement_only": true,
        "guidance_is_finite_external_tissue_work": true,
        "guidance_includes_external_tutor_pressure": true,
        "guidance_authors_no_contact_directly": true,
        "guide_carriers_per_terminal": guide_carriers.to_string(),
        "tutor_pressure_sample_count": tutor_pressure.len(),
        "tutor_pressure_nonzero_sample_count": tutor_pressure.iter().filter(|sample| **sample != 0).count(),
        "maximum_cycles": maximum_cycles,
        "completed_cycles": completed_cycles,
        "sequence_repetitions": sequence_repetitions,
        "sequence_training_steps": sequence_training_steps,
        "continuation_cue": {
            "kind": "one exact learned first-phase body consequence plus its exact self-pressure",
            "body_consequence_count": positive_cue_sources[0].joint_source_ports().len(),
            "pressure_sample_count": first_learned_phase_pressure.len(),
            "pressure_nonzero_sample_count": first_learned_phase_pressure.iter().filter(|sample| **sample != 0).count(),
            "cue_admitted_once": true,
            "later_motor_commands_authored": false,
            "pressure_output": continuation_cue_pressure_output,
        },
        "cue_control_results": cue_control_results,
        "teaching_cold_round_trip_exact": teaching_cold_exact,
        "teaching_state_output": teaching_state_output,
        "teaching_body_output": teaching_body_output,
        "teaching_vocal_route_formation_memberships": teaching_vocal_route_formation_memberships,
        "before_route_count": before.len(),
        "after_route_count": after.len(),
        "after_source_count": source_to_motors.len(),
        "all_eight_routes_grown": reached_terminals == target_terminals,
        "all_eight_terminals_reached": reached_terminals == target_terminals,
        "every_source_has_one_motor": source_to_motors.values().all(|motors| motors.len() == 1),
        "motor_discharges_during_guidance": motor_discharges,
        "guided_vocal_discharges": guided_vocal_discharges,
        "inter_demonstration_pulses": inter_demonstration_pulses,
        "guided_respiratory_carriers": guided_respiratory_carriers.to_string(),
        "guided_nonzero_pressure_samples": guided_pressure.iter().filter(|sample| **sample != 0).count(),
        "guided_internal_reassemblies": guided_internal_reassemblies,
        "guided_causal_thought_transitions": guided_causal_thought_transitions,
    });
    let tail = json!({
        "maximum_unguided_clocks": maximum_unguided_clocks,
        "pre_cue_baseline": {
            "clocks": baseline_clocks,
            "required_clean_clocks": required_clean_baseline_clocks,
            "pulse_count": baseline_pulse_count,
            "latest_pulse_clock": latest_baseline_pulse_clock,
            "pulses": baseline_pulses,
            "respiratory_carriers": baseline_respiratory_carriers.to_string(),
            "nonzero_pressure_samples": baseline_nonzero_pressure_samples,
            "last_clocks_clean": baseline_last_clocks_clean,
        },
        "unguided_pulses": unguided_pulses,
        "unguided_respiratory_carriers": respiratory_carriers.to_string(),
        "unguided_internal_reassemblies": unguided_internal_reassemblies,
        "unguided_causal_thought_transitions": unguided_causal_thought_transitions,
        "unguided_learned_work_by_clock": unguided_learned_work_by_clock,
        "pressure_sample_count": pressure.len(),
        "nonzero_pressure_samples": nonzero_pressure_samples,
        "pressure_peak": pressure_peak,
        "self_hearing": self_hearing,
        "pressure_wav": pressure_wav,
        "cold_round_trip_exact": cold_exact,
        "encoded_bytes": encoded.len(),
        "final_vocal_route_formation_memberships": vocal_route_formation_memberships(&state),
        "checkpoints": observations,
        "routes": after.iter().map(|(ordering, motor, terminal)| json!({
            "ordering": lineage_hex(*ordering),
            "motor": lineage_hex(*motor),
            "terminal": format!("{terminal:?}"),
        })).collect::<Vec<_>>(),
    });
    let Value::Object(result_fields) = &mut result else {
        unreachable!("guided vocal result is an object")
    };
    let Value::Object(tail_fields) = tail else {
        unreachable!("guided vocal result tail is an object")
    };
    result_fields.extend(tail_fields);
    result
}

fn wide_exact_from_json(value: &Value) -> BigRational {
    let numerator = value["numerator"]
        .as_str()
        .expect("exact JSON numerator")
        .parse::<BigInt>()
        .expect("exact JSON numerator integer");
    let denominator = value["denominator"]
        .as_str()
        .expect("exact JSON denominator")
        .parse::<BigInt>()
        .expect("exact JSON denominator integer");
    BigRational::new(numerator, denominator)
}

fn lineage_from_hex(value: &str) -> [u8; 16] {
    assert_eq!(value.len(), 32, "lineage hex width");
    let mut lineage = [0_u8; 16];
    for (index, byte) in lineage.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&value[index * 2..index * 2 + 2], 16).expect("lineage hex byte");
    }
    lineage
}

fn mounted_neuron_location(
    state: &ResidentCognitiveFormationState,
    lineage: [u8; 16],
) -> (usize, usize) {
    let flat = state
        .topology_index
        .flat_for_lineage(lineage)
        .expect("mounted lineage");
    let (cohort, neuron, _) = state.topology_index.flat_locations[flat];
    (cohort, neuron)
}

fn with_replaced_mounted_neuron(
    state: &ResidentCognitiveFormationState,
    lineage: [u8; 16],
    replacement: crate::complete_neuron::NeuronPhysicalState,
) -> ResidentCognitiveFormationState {
    let (cohort_index, neuron_index) = mounted_neuron_location(state, lineage);
    let mut successor = state.clone();
    successor.cohorts[cohort_index].state = successor.cohorts[cohort_index]
        .state
        .with_replaced_neurons(&[(neuron_index, replacement)])
        .expect("one in-range neuron replacement")
        .into();
    successor
}

fn transduced_gate_sample_json(
    anatomy: &crate::complete_neuron::NeuronPhysicalAnatomy,
    predecessor: &crate::complete_neuron::NeuronPhysicalState,
    offered_work: &BigRational,
    interval_microseconds: u32,
    maximum_events: u32,
    exhaust_intracellular_carriers: bool,
    exhaust_gate_dissipation: bool,
) -> (Value, crate::complete_neuron::NeuronPhysicalState) {
    let mut current = predecessor.clone();
    let mut first_open_event = None;
    let mut first_outward_event = None;
    let mut peak_outward = 0_i128;
    let mut all_offer_balances_close = true;
    let mut all_gate_input_balances_close = true;
    let mut all_carrier_balances_close = true;
    let mut maximum_residue_numerator_bytes = 0_usize;
    let mut maximum_residue_denominator_bytes = 0_usize;
    let mut total_accepted = BigRational::zero();
    let mut total_source_heat = BigRational::zero();
    let mut total_delivered = BigRational::zero();
    let mut total_residue_narrowing_heat = BigRational::zero();
    let mut total_gate_exported_heat = BigRational::zero();
    let mut checkpoints = Vec::new();

    for event in 1..=maximum_events {
        let predecessor_residue = current.receptor_quantum_residue.energy().clone();
        let predecessor_carriers = if exhaust_intracellular_carriers {
            current.carrier_reservoirs().extracellular()
        } else {
            current
                .carrier_reservoirs()
                .total()
                .expect("copied motor carrier total")
        };
        let settled = crate::complete_neuron::probe_transduced_gate_work_interval(
            anatomy,
            &current,
            offered_work.clone(),
            interval_microseconds,
            exhaust_intracellular_carriers,
            exhaust_gate_dissipation,
        )
        .expect("candidate-47H isolated gate settlement");
        let successor_residue = settled.successor.receptor_quantum_residue.energy().clone();
        let successor_carriers = settled
            .successor
            .carrier_reservoirs()
            .total()
            .expect("candidate motor carrier total");
        all_offer_balances_close &=
            *offered_work == &settled.accepted_work_zeptojoules + &settled.source_heat_zeptojoules;
        all_gate_input_balances_close &= predecessor_residue + &settled.accepted_work_zeptojoules
            == &settled.delivered_gate_work_zeptojoules
                + &successor_residue
                + &settled.residue_narrowing_heat_zeptojoules;
        all_carrier_balances_close &= predecessor_carriers == successor_carriers;
        total_accepted += &settled.accepted_work_zeptojoules;
        total_source_heat += &settled.source_heat_zeptojoules;
        total_delivered += &settled.delivered_gate_work_zeptojoules;
        total_residue_narrowing_heat += &settled.residue_narrowing_heat_zeptojoules;
        total_gate_exported_heat += &settled.gate_exported_heat_zeptojoules;
        maximum_residue_numerator_bytes = maximum_residue_numerator_bytes
            .max(successor_residue.numer().to_signed_bytes_le().len());
        maximum_residue_denominator_bytes = maximum_residue_denominator_bytes
            .max(successor_residue.denom().to_signed_bytes_le().len());
        let open_population = settled.successor.probe_gate_open_population();
        if open_population > 0 && first_open_event.is_none() {
            first_open_event = Some(event);
        }
        if settled.local_outward_elementary_charges > 0 && first_outward_event.is_none() {
            first_outward_event = Some(event);
        }
        peak_outward = peak_outward.max(settled.local_outward_elementary_charges);
        if event == 1
            || event == maximum_events
            || Some(event) == first_open_event
            || Some(event) == first_outward_event
        {
            checkpoints.push(json!({
                "event": event,
                "open_gate_population": open_population.to_string(),
                "local_outward_elementary_charges":
                    settled.local_outward_elementary_charges.to_string(),
                "successor_residue_zeptojoules": wide_exact_json(&successor_residue),
            }));
        }
        current = settled.successor;
    }

    let final_residue = current.receptor_quantum_residue.energy().clone();
    (
        json!({
            "interval_microseconds": interval_microseconds,
            "maximum_events": maximum_events,
            "offered_work_per_event_zeptojoules": wide_exact_json(offered_work),
            "intracellular_carriers_artificially_exhausted":
                exhaust_intracellular_carriers,
            "gate_dissipation_artificially_exhausted": exhaust_gate_dissipation,
            "first_open_event": first_open_event,
            "first_positive_outward_event": first_outward_event,
            "peak_local_outward_elementary_charges": peak_outward.to_string(),
            "final_open_gate_population": current.probe_gate_open_population().to_string(),
            "final_residue_zeptojoules": wide_exact_json(&final_residue),
            "total_accepted_work_zeptojoules": wide_exact_json(&total_accepted),
            "total_source_heat_zeptojoules": wide_exact_json(&total_source_heat),
            "total_delivered_gate_work_zeptojoules": wide_exact_json(&total_delivered),
            "total_residue_narrowing_heat_zeptojoules":
                wide_exact_json(&total_residue_narrowing_heat),
            "total_gate_exported_heat_zeptojoules":
                wide_exact_json(&total_gate_exported_heat),
            "all_offer_balances_close_exactly": all_offer_balances_close,
            "all_gate_input_balances_close_exactly": all_gate_input_balances_close,
            "all_carrier_balances_close_exactly": all_carrier_balances_close,
            "maximum_residue_numerator_bytes": maximum_residue_numerator_bytes,
            "maximum_residue_denominator_bytes": maximum_residue_denominator_bytes,
            "checkpoints": checkpoints,
        }),
        current,
    )
}

fn probe_u16(output: &mut Vec<u8>, value: usize) {
    output.extend_from_slice(&u16::try_from(value).expect("probe u16 width").to_le_bytes());
}

fn probe_u32(output: &mut Vec<u8>, value: usize) {
    output.extend_from_slice(&u32::try_from(value).expect("probe u32 width").to_le_bytes());
}

fn probe_text(output: &mut Vec<u8>, value: &str) {
    probe_u16(output, value.len());
    output.extend_from_slice(value.as_bytes());
}

fn probe_bytes(output: &mut Vec<u8>, value: &[u8]) {
    probe_u32(output, value.len());
    output.extend_from_slice(value);
}

fn probe_rational(output: &mut Vec<u8>, value: &BigRational) {
    probe_text(output, &value.numer().to_string());
    probe_text(output, &value.denom().to_string());
}

fn probe_lineage_hex(lineage: [u8; 16]) -> String {
    lineage.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn probe_cochlear_centre_hz(channel_index: usize) -> f64 {
    fn erb_rate(frequency_hz: f64) -> f64 {
        21.4 * (1.0 + 4.37e-3 * frequency_hz).log10()
    }
    let lower = erb_rate(80.0);
    let upper = erb_rate(7_500.0);
    let rate = lower
        + (upper - lower) * channel_index as f64 / (PROBE_COCHLEAR_CHANNELS_PER_EAR - 1) as f64;
    (10.0_f64.powf(rate / 21.4) - 1.0) / 4.37e-3
}

fn probe_acoustic_port(
    output: &mut Vec<u8>,
    topology_index: usize,
    fields: &[f64],
    cochlear: bool,
) {
    let cochlear_location = cochlear.then(|| {
        let local = topology_index - PROBE_LEGACY_EAR_PORT_COUNT;
        (
            local / PROBE_COCHLEAR_CHANNELS_PER_EAR,
            local % PROBE_COCHLEAR_CHANNELS_PER_EAR,
        )
    });
    output.push(1);
    probe_u32(output, topology_index);
    probe_text(output, "organism-ear-pressure");
    let substream_id = if let Some((ear, channel)) = cochlear_location {
        format!("cochlea-{ear}-band-{channel:02}")
    } else {
        format!("ear-{topology_index}")
    };
    probe_text(output, &substream_id);
    if let Some((ear, channel)) = cochlear_location {
        probe_u16(output, 3);
        probe_text(output, "ear");
        probe_text(output, &ear.to_string());
        probe_text(output, "cochlear-band");
        probe_text(output, &channel.to_string());
        probe_text(output, "centre-frequency-millihertz");
        probe_text(
            output,
            &format!(
                "{}",
                (probe_cochlear_centre_hz(channel) * 1_000.0).round() as i64
            ),
        );
    } else {
        probe_u16(output, 1);
        probe_text(output, "ear");
        probe_text(output, &topology_index.to_string());
    }
    probe_text(
        output,
        if cochlear {
            "cochlear-band-pressure"
        } else {
            "normalized_physical_excitation"
        },
    );
    probe_text(
        output,
        if cochlear {
            "fraction-of-declared-cochlear-reference-pressure"
        } else {
            "normalized_binary64"
        },
    );
    probe_text(output, "direct-physical-source");
    probe_text(output, "");
    probe_text(output, "identity-binary64");
    probe_rational(output, &BigRational::from_integer(BigInt::from(-1)));
    probe_rational(output, &BigRational::from_integer(BigInt::from(1)));
    probe_rational(output, &BigRational::zero());
    probe_rational(output, &BigRational::from_integer(BigInt::from(1)));
    probe_bytes(output, b"identity-binary64-v1");
    probe_u32(output, fields.len());
    for (index, field) in fields.iter().copied().enumerate() {
        probe_rational(
            output,
            &BigRational::new(BigInt::from(index), BigInt::from(100)),
        );
        output.extend_from_slice(&field.to_bits().to_le_bytes());
        probe_rational(output, &BigRational::zero());
        probe_rational(output, &BigRational::from_integer(BigInt::from(1)));
        probe_rational(
            output,
            &BigRational::from_float(field).expect("finite probe acoustic field"),
        );
    }
}

fn probe_acoustic_occurrence(output: &mut Vec<u8>, start: usize, count: usize, frames: usize) {
    probe_u32(output, count);
    for port_index in start..start + count {
        probe_u32(output, port_index);
    }
    probe_u32(output, frames);
    for index in 0..frames {
        probe_rational(
            output,
            &BigRational::new(BigInt::from(index), BigInt::from(100)),
        );
    }
    probe_bytes(output, PROBE_INTERSAMPLE_PROFILE);
    probe_u32(output, 1);
    probe_u32(output, count);
    for local_index in 0..count {
        probe_u32(output, local_index);
    }
    probe_bytes(output, b"explicit-joint-relevance-v1");
    probe_u32(output, frames);
    for _ in 0..frames {
        probe_rational(output, &BigRational::from_integer(BigInt::from(1)));
    }
}

fn probe_cochlear_coefficients() -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    fn erb_width_hz(frequency_hz: f64) -> f64 {
        24.7 * (4.37e-3 * frequency_hz + 1.0)
    }
    let mut pole_real = Vec::new();
    let mut pole_imag = Vec::new();
    let mut injection = Vec::new();
    for index in 0..PROBE_COCHLEAR_CHANNELS_PER_EAR {
        let centre = probe_cochlear_centre_hz(index);
        let radius = (-2.0 * std::f64::consts::PI * 1.019 * erb_width_hz(centre)
            / PROBE_ACOUSTIC_SAMPLE_RATE_HZ as f64)
            .exp();
        let angle = 2.0 * std::f64::consts::PI * centre / PROBE_ACOUSTIC_SAMPLE_RATE_HZ as f64;
        pole_real.push(radius * angle.cos());
        pole_imag.push(radius * angle.sin());
        injection.push(1.0 - radius);
    }
    (pole_real, pole_imag, injection)
}

fn probe_hearing_episode(
    pressure: &[i16],
    source_authority: &str,
) -> crate::joint_source_episode::NativeJointSourceEpisode {
    assert_eq!(pressure.len(), 4_000, "one exact 250 ms pressure interval");
    let normalized = pressure
        .iter()
        .map(|sample| f64::from(*sample) / 32_768.0)
        .collect::<Vec<_>>();
    let (pole_real, pole_imag, injection) = probe_cochlear_coefficients();
    let (state_real, state_imag, previous_real, previous_imag, phase, energy, partial) =
        zero_stream_state();
    let stream = auditory_gammatone_stream_impl(
        &normalized,
        &pole_real,
        &pole_imag,
        &injection,
        state_real,
        state_imag,
        previous_real,
        previous_imag,
        phase,
        energy,
        partial,
        0,
    )
    .expect("candidate pressure remains within cochlear analytic bound");
    let envelopes = stream.0;
    assert_eq!(
        envelopes.len(),
        pressure.len() / PROBE_COCHLEAR_HOP_SAMPLES,
        "complete cochlear frame count",
    );
    let legacy = (0..envelopes.len())
        .map(|index| normalized[(index + 1) * PROBE_COCHLEAR_HOP_SAMPLES - 1])
        .collect::<Vec<_>>();
    let bands = (0..PROBE_COCHLEAR_CHANNELS_PER_EAR)
        .map(|channel| {
            envelopes
                .iter()
                .map(|frame| {
                    let lattice = (frame[channel] * PROBE_COCHLEAR_PRESSURE_LATTICE).round();
                    assert!(
                        (0.0..=PROBE_COCHLEAR_PRESSURE_LATTICE).contains(&lattice),
                        "candidate cochlear envelope remains inside declared lattice",
                    );
                    lattice / PROBE_COCHLEAR_PRESSURE_LATTICE
                })
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>();
    let port_count =
        PROBE_LEGACY_EAR_PORT_COUNT + PROBE_EAR_COUNT * PROBE_COCHLEAR_CHANNELS_PER_EAR;
    let frames = envelopes.len();
    let mut output = b"GLJSRC02".to_vec();
    probe_u16(&mut output, 2);
    probe_text(&mut output, source_authority);
    output.extend_from_slice(&[1, 0, 1, 1, 1, 1]);
    probe_u32(&mut output, port_count);
    for topology_index in 0..PROBE_LEGACY_EAR_PORT_COUNT {
        probe_acoustic_port(&mut output, topology_index, &legacy, false);
    }
    for ear in 0..PROBE_EAR_COUNT {
        for channel in 0..PROBE_COCHLEAR_CHANNELS_PER_EAR {
            probe_acoustic_port(
                &mut output,
                PROBE_LEGACY_EAR_PORT_COUNT + ear * PROBE_COCHLEAR_CHANNELS_PER_EAR + channel,
                &bands[channel],
                true,
            );
        }
    }
    probe_u32(&mut output, 3);
    probe_acoustic_occurrence(&mut output, 0, PROBE_LEGACY_EAR_PORT_COUNT, frames);
    probe_acoustic_occurrence(
        &mut output,
        PROBE_LEGACY_EAR_PORT_COUNT,
        PROBE_COCHLEAR_CHANNELS_PER_EAR,
        frames,
    );
    probe_acoustic_occurrence(
        &mut output,
        PROBE_LEGACY_EAR_PORT_COUNT + PROBE_COCHLEAR_CHANNELS_PER_EAR,
        PROBE_COCHLEAR_CHANNELS_PER_EAR,
        frames,
    );
    decode_native_joint_source_episode(&output, port_count, port_count * frames, 3, 3 * frames)
        .expect("candidate hearing episode decodes")
}

fn probe_self_hearing_episode(
    pressure: &[i16],
) -> crate::joint_source_episode::NativeJointSourceEpisode {
    probe_hearing_episode(pressure, "candidate-exact-self-pressure")
}

/// Candidate-47H dynamic regime map over the immutable task-1429 body. This
/// calls only test-compiled neuron physics, carries the exact motor state over
/// repeated arrivals, and never presents a stimulus to the organism.
fn temporal_gate_work_range_json(
    state: &ResidentCognitiveFormationState,
    original_cognitive_bytes: &[u8],
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    let predecessor_bytes = state.encode(usize::MAX).expect("encode untouched V41 body");
    let untouched_v41_round_trip_exact = predecessor_bytes == original_cognitive_bytes;
    let source_census = production_learned_motor_work_range_json(state);
    let production_replayed_discharge =
        production_replayed_motor_discharge_json(state, articulated_body);
    let route_results = source_census["route_results"]
        .as_array()
        .expect("candidate-47F copied route results");
    let scales = [(0_i64, 1_i64), (1, 4), (1, 2), (1, 1), (2, 1), (4, 1)];
    let intervals = [62_500_u32, 125_000, 250_000, 500_000];
    let mut samples = Vec::new();
    let mut cold_continuation = Vec::new();
    let mut cold_tested_motors = std::collections::BTreeSet::new();

    for route in route_results {
        if route.get("error").is_some() {
            samples.push(route.clone());
            continue;
        }
        let motor_hex = route["motor_lineage"]
            .as_str()
            .expect("candidate motor lineage");
        let motor = lineage_from_hex(motor_hex);
        let active_clock = route["active_clock"]
            .as_u64()
            .expect("candidate active clock");
        let source_work = wide_exact_from_json(&route["total_source_work_zeptojoules"]);
        let (cohort_index, neuron_index) = mounted_neuron_location(state, motor);
        let cohort = &state.cohorts[cohort_index];
        let anatomy = &cohort.anatomy.neuron_anatomies()[neuron_index];
        let predecessor = &cohort.state.neurons()[neuron_index];

        for (scale_numerator, scale_denominator) in scales {
            let offered =
                &source_work * BigInt::from(scale_numerator) / BigInt::from(scale_denominator);
            for interval_microseconds in intervals {
                let (sample, _) = transduced_gate_sample_json(
                    anatomy,
                    predecessor,
                    &offered,
                    interval_microseconds,
                    256,
                    false,
                    false,
                );
                samples.push(json!({
                    "active_clock": active_clock,
                    "motor_lineage": motor_hex,
                    "source_scale": format!("{scale_numerator}/{scale_denominator}"),
                    "sample": sample,
                }));
            }
        }

        let (zero_work, _) = transduced_gate_sample_json(
            anatomy,
            predecessor,
            &BigRational::zero(),
            250_000,
            256,
            false,
            false,
        );
        let (exhausted_carriers, _) = transduced_gate_sample_json(
            anatomy,
            predecessor,
            &source_work,
            250_000,
            256,
            true,
            false,
        );
        let (exhausted_gate, _) = transduced_gate_sample_json(
            anatomy,
            predecessor,
            &source_work,
            250_000,
            256,
            false,
            true,
        );
        samples.push(json!({
            "active_clock": active_clock,
            "motor_lineage": motor_hex,
            "controls": {
                "zero_work": zero_work,
                "exhausted_intracellular_carriers": exhausted_carriers,
                "exhausted_gate_dissipation": exhausted_gate,
            },
        }));

        let is_vocal = motor_hex.ends_with("00c5") || motor_hex.ends_with("04fb");
        if is_vocal && cold_tested_motors.insert(motor) {
            let (uninterrupted, _) = transduced_gate_sample_json(
                anatomy,
                predecessor,
                &source_work,
                250_000,
                256,
                false,
                false,
            );
            let uninterrupted_crossing = uninterrupted["first_positive_outward_event"].as_u64();
            if let Some(crossing) = uninterrupted_crossing {
                let split = u32::try_from(crossing.saturating_sub(1)).unwrap();
                let (_, midpoint_neuron) = transduced_gate_sample_json(
                    anatomy,
                    predecessor,
                    &source_work,
                    250_000,
                    split,
                    false,
                    false,
                );
                let midpoint_state = with_replaced_mounted_neuron(state, motor, midpoint_neuron);
                let midpoint_bytes = midpoint_state
                    .encode(usize::MAX)
                    .expect("encode sub-threshold copied body");
                let cold_state =
                    ResidentCognitiveFormationState::decode(&midpoint_bytes, usize::MAX)
                        .expect("cold-decode sub-threshold copied body");
                let (cold_cohort, cold_neuron) = mounted_neuron_location(&cold_state, motor);
                let cold_anatomy =
                    &cold_state.cohorts[cold_cohort].anatomy.neuron_anatomies()[cold_neuron];
                let cold_predecessor =
                    &cold_state.cohorts[cold_cohort].state.neurons()[cold_neuron];
                let (continued, _) = transduced_gate_sample_json(
                    cold_anatomy,
                    cold_predecessor,
                    &source_work,
                    250_000,
                    256 - split,
                    false,
                    false,
                );
                let continued_relative = continued["first_positive_outward_event"].as_u64();
                cold_continuation.push(json!({
                    "motor_lineage": motor_hex,
                    "uninterrupted_first_positive_outward_event": crossing,
                    "cold_split_after_event": split,
                    "midpoint_encoded_bytes": midpoint_bytes.len(),
                    "midpoint_reencode_exact": cold_state
                        .encode(usize::MAX)
                        .expect("re-encode cold midpoint") == midpoint_bytes,
                    "continued_relative_first_positive_outward_event": continued_relative,
                    "cold_absolute_first_positive_outward_event":
                        continued_relative.map(|relative| u64::from(split) + relative),
                    "crossing_preserved_across_cold_restore":
                        continued_relative.map(|relative| u64::from(split) + relative)
                            == Some(crossing),
                }));
            } else {
                cold_continuation.push(json!({
                    "motor_lineage": motor_hex,
                    "uninterrupted_first_positive_outward_event": Value::Null,
                    "crossing_preserved_across_cold_restore": false,
                    "reason": "no outward event within 256 repeated real-work events",
                }));
            }
        }
    }

    let typed_vocal_body = if let Some(body) = articulated_body {
        let mut motor_drives = Vec::new();
        let mut motor_evidence = Vec::new();
        let mut respiratory_discharge_limit = 0_u128;
        let mut tested_vocal_motors = std::collections::BTreeSet::new();
        for route in route_results {
            if route.get("error").is_some() {
                continue;
            }
            let motor_hex = route["motor_lineage"]
                .as_str()
                .expect("candidate motor lineage");
            if (!motor_hex.ends_with("00c5") && !motor_hex.ends_with("04fb"))
                || !tested_vocal_motors.insert(motor_hex)
            {
                continue;
            }
            let motor = lineage_from_hex(motor_hex);
            let source_work = wide_exact_from_json(&route["total_source_work_zeptojoules"]);
            let (cohort_index, neuron_index) = mounted_neuron_location(state, motor);
            let cohort = &state.cohorts[cohort_index];
            let anatomy = &cohort.anatomy.neuron_anatomies()[neuron_index];
            let predecessor = &cohort.state.neurons()[neuron_index];
            let terminal = cohort.anatomy.mounts()[neuron_index]
                .body_effector_terminal()
                .expect("learned vocal motor has typed terminal");
            let (range, _) = transduced_gate_sample_json(
                anatomy,
                predecessor,
                &source_work,
                250_000,
                256,
                false,
                false,
            );
            let crossing = u32::try_from(
                range["first_positive_outward_event"]
                    .as_u64()
                    .expect("candidate vocal motor crosses"),
            )
            .expect("candidate crossing width");
            let (at_crossing, _) = transduced_gate_sample_json(
                anatomy,
                predecessor,
                &source_work,
                250_000,
                crossing,
                false,
                false,
            );
            let outward = at_crossing["peak_local_outward_elementary_charges"]
                .as_str()
                .expect("candidate vocal output")
                .parse::<u128>()
                .expect("candidate vocal output width");
            respiratory_discharge_limit = respiratory_discharge_limit
                .checked_add(outward)
                .expect("candidate respiratory limit width");
            motor_drives.push(BodyEffectorDrive {
                terminal,
                outward_elementary_carriers: outward,
            });
            motor_evidence.push(json!({
                "motor_lineage": motor_hex,
                "terminal": format!("{terminal:?}"),
                "first_positive_outward_event": crossing,
                "outward_elementary_carriers": outward.to_string(),
            }));
        }
        let respiratory_lineage = state
            .vocal_articulatory_effector_lineage
            .expect("copied body has dedicated respiratory effector");
        let (respiratory_cohort_index, respiratory_neuron_index) =
            mounted_neuron_location(state, respiratory_lineage);
        let respiratory_cohort = &state.cohorts[respiratory_cohort_index];
        let mut respiratory_state = respiratory_cohort.state.as_ref().clone();
        let prepared_metabolism = super::prepare_reached_cohort_membrane_pumps(
            &respiratory_cohort.anatomy,
            &respiratory_state,
            &[respiratory_neuron_index],
            250_000,
            ExactRational::integer(0),
        )
        .expect("candidate respiratory metabolism prepares");
        let respiratory_metabolism = super::apply_prepared_reached_cohort_membrane_pumps(
            &mut respiratory_state,
            prepared_metabolism,
        );
        let respiratory_terminal = crate::complete_neuron::settle_efferent_terminal_transport(
            &respiratory_cohort.anatomy.neuron_anatomies()[respiratory_neuron_index],
            &respiratory_state.neurons()[respiratory_neuron_index],
            respiratory_discharge_limit,
            250_000,
        )
        .expect("candidate respiratory terminal settles");
        let respiratory_efferent_carriers = respiratory_terminal
            .as_ref()
            .map_or(0, |(_, carriers, _)| *carriers);
        let admitted = AdmittedBodyEffectorDrives::admit(motor_drives)
            .expect("candidate vocal tissue drives admit");
        let body_transition =
            settle_body_effector_drives(body, &admitted, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
                .expect("candidate vocal tissue settles");
        let acoustic = settle_native_articulatory_interval(
            body_transition.successor.clone(),
            &body_transition.proprioceptive_consequences,
            respiratory_efferent_carriers,
            4_000,
        )
        .expect("candidate vocal pressure settles");
        let pressure_peak = acoustic
            .radiated_pressure_pcm
            .iter()
            .map(|sample| sample.unsigned_abs())
            .max()
            .unwrap_or(0);
        let nonzero_pressure_samples = acoustic
            .radiated_pressure_pcm
            .iter()
            .filter(|sample| **sample != 0)
            .count();
        let self_hearing_episode = probe_self_hearing_episode(&acoustic.radiated_pressure_pcm);
        let cochlear_locations = self_hearing_episode
            .joint_source_ports()
            .iter()
            .filter(|port| port.physical_quantity == "cochlear-band-pressure")
            .map(|port| {
                let site = super::NeuronSourceSite::from_source_port(port)
                    .expect("candidate cochlear source site");
                let (cohort_index, neuron_index, lineage) = state
                    .topology_index
                    .source_location(&site)
                    .expect("candidate cochlear topology lookup")
                    .expect("candidate cochlear receptor is mounted");
                let neuron = &state.cohorts[cohort_index].state.neurons()[neuron_index];
                (
                    cohort_index,
                    neuron_index,
                    lineage,
                    neuron.receptor_quantum_residue.energy().clone(),
                    neuron.gate.open_population(),
                )
            })
            .collect::<Vec<_>>();
        let self_hearing_intervals = vec![(1_i64, 4_i64); 3];
        let self_hearing_admitted = admitted_episode_with_authored_intervals(
            &self_hearing_episode,
            &self_hearing_intervals,
        )
        .expect("candidate self-hearing admission");
        let (self_heard_successor, self_hearing_observation) = state
            .clone()
            .advance_admitted_transition(
                &self_hearing_admitted,
                usize::MAX,
                false,
                ExactRational::integer(0),
            )
            .expect("candidate exact self-hearing settles");
        let cochlear_returns = cochlear_locations
            .into_iter()
            .map(
                |(cohort_index, neuron_index, lineage, before_residue, before_gate)| {
                    let after =
                        &self_heard_successor.cohorts[cohort_index].state.neurons()[neuron_index];
                    let after_residue = after.receptor_quantum_residue.energy().clone();
                    json!({
                        "lineage": probe_lineage_hex(lineage),
                        "residue_changed": after_residue != before_residue,
                        "gate_population_changed": after.gate.open_population() != before_gate,
                        "externally_perturbed": self_hearing_observation
                            .externally_perturbed_neuron_lineages
                            .contains(&lineage),
                    })
                },
            )
            .collect::<Vec<_>>();
        let externally_perturbed_cochlear_count = cochlear_returns
            .iter()
            .filter(|item| item["externally_perturbed"].as_bool() == Some(true))
            .count();
        let changed_cochlear_count = cochlear_returns
            .iter()
            .filter(|item| {
                item["residue_changed"].as_bool() == Some(true)
                    || item["gate_population_changed"].as_bool() == Some(true)
            })
            .count();
        json!({
            "motor_evidence": motor_evidence,
            "respiratory_discharge_limit": respiratory_discharge_limit.to_string(),
            "respiratory_efferent_carriers": respiratory_efferent_carriers.to_string(),
            "respiratory_metabolism_changed": respiratory_metabolism.changed(),
            "reached_terminal_count": body_transition.reached_terminal_count,
            "proprioceptive_consequences": body_transition
                .proprioceptive_consequences
                .iter()
                .map(|consequence| json!({
                    "axis": format!("{:?}", consequence.axis),
                    "predecessor_position": consequence.predecessor_position,
                    "successor_position": consequence.successor_position,
                    "signed_displacement": consequence.signed_displacement,
                    "applied_displacement_quanta": consequence
                        .applied_displacement_quanta
                        .to_string(),
                    "stalled_carriers": consequence.stalled_carriers.to_string(),
                }))
                .collect::<Vec<_>>(),
            "pressure_sample_count": acoustic.radiated_pressure_pcm.len(),
            "nonzero_pressure_samples": nonzero_pressure_samples,
            "pressure_peak": pressure_peak,
            "self_hearing": {
                "cochlear_port_count": cochlear_returns.len(),
                "externally_perturbed_cochlear_count": externally_perturbed_cochlear_count,
                "changed_cochlear_count": changed_cochlear_count,
                "physically_transitioned_neuron_count":
                    self_hearing_observation.physically_transitioned_neuron_count,
                "dsf_delivery_count": self_hearing_observation.dsf_delivery_count,
                "cochlear_returns": cochlear_returns,
                "successor_cognitive_body_encodes": self_heard_successor
                    .encode(usize::MAX)
                    .is_ok(),
            },
            "successor_body_cold_round_trip_exact": ArticulatedBodyState::decode(
                &acoustic
                    .successor_body
                    .encode()
                    .expect("candidate successor body encodes"),
            )
            .expect("candidate successor body decodes") == acoustic.successor_body,
        })
    } else {
        json!({"error": "copied articulated body absent"})
    };

    let (severed, severed_bridge_count) = severed_learned_motor_copy(state);
    let severed_route_count = production_learned_motor_work_range_json(&severed)["route_results"]
        .as_array()
        .map_or(0, Vec::len);
    json!({
        "measurement_only": true,
        "production_compiled": true,
        "candidate": "47I production learned-contact work transduction",
        "copied_body_cognitive_format": "GLCOG041",
        "untouched_v41_round_trip_exact": untouched_v41_round_trip_exact,
        "source_carriers_enter_motor": false,
        "a0116_transition_work_phase_reused": false,
        "recovery_material_created": false,
        "persistent_schema_bytes_added": 0,
        "maximum_repeated_events": 256,
        "source_scales": ["0/1", "1/4", "1/2", "1/1", "2/1", "4/1"],
        "interval_microseconds": intervals,
        "samples": samples,
        "cold_continuation": cold_continuation,
        "typed_vocal_body": typed_vocal_body,
        "production_path_census": source_census,
        "production_replayed_discharge": production_replayed_discharge,
        "severed_bridge_count": severed_bridge_count,
        "severed_route_count": severed_route_count,
        "permutation_falsifier_inherited_from_47f":
            source_census["synthetic_order_invariance"].clone(),
    })
}

fn source_work_motor_candidate_falsifier_json(state: &ResidentCognitiveFormationState) -> Value {
    let connected = source_work_to_motor_reservoir_range_json(state);
    let (severed, severed_bridge_count) = severed_learned_motor_copy(state);
    let disconnected = source_work_to_motor_reservoir_range_json(&severed);
    let severed_route_count = disconnected["route_results"].as_array().map_or(0, Vec::len);
    json!({
        "connected": connected,
        "severed": disconnected,
        "severed_bridge_count": severed_bridge_count,
        "severed_route_count": severed_route_count,
    })
}

/// Sweep the candidate source across the exact copied body's respiratory
/// carrier extent and the three physical articulator coordinates already
/// implicated by its learned vocal routes.  This is measurement-only: every
/// altered posture is a disposable in-memory control and no named sound,
/// target waveform, or production state is authored.
fn copied_body_l13_acoustic_range_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let current_glottis = body.axis(BodyAxis::GlottalAperture);
    let section_zero = body.axis(BodyAxis::VocalTractSection0Area);
    let section_seven = body.axis(BodyAxis::VocalTractSection7Area);
    let controls = [
        ("copied", current_glottis, section_zero, section_seven),
        (
            "glottis-minimum",
            BodyAxis::GlottalAperture.anatomy().minimum,
            section_zero,
            section_seven,
        ),
        (
            "glottis-neutral",
            BodyAxis::GlottalAperture.anatomy().neutral,
            section_zero,
            section_seven,
        ),
        (
            "glottis-maximum",
            BodyAxis::GlottalAperture.anatomy().maximum,
            section_zero,
            section_seven,
        ),
        (
            "learned-section-0-minus-one",
            current_glottis,
            section_zero.saturating_sub(1),
            section_seven,
        ),
        (
            "learned-section-0-plus-one",
            current_glottis,
            section_zero.saturating_add(1),
            section_seven,
        ),
        (
            "learned-section-7-minus-one",
            current_glottis,
            section_zero,
            section_seven.saturating_sub(1),
        ),
        (
            "learned-section-7-plus-one",
            current_glottis,
            section_zero,
            section_seven.saturating_add(1),
        ),
    ];
    let samples = controls
        .into_iter()
        .map(|(name, glottis, section_zero, section_seven)| {
            let mut axes = *body.axes();
            axes[BodyAxis::GlottalAperture.index()] = glottis;
            axes[BodyAxis::VocalTractSection0Area.index()] = section_zero;
            axes[BodyAxis::VocalTractSection7Area.index()] = section_seven;
            let control = ArticulatedBodyState::from_physical_state(
                axes,
                body.lung_air_microlitres(),
                body.proprioception_initialized(),
            )
            .and_then(|control| {
                control.with_articulatory_acoustic_state(body.articulatory_acoustic_state())
            })
            .expect("copied-body acoustic range posture");
            let work_range = [0_u128, 1, 2, 4, 8, 16]
                .into_iter()
                .map(|carriers| {
                    let transition =
                        settle_native_articulatory_interval(control.clone(), &[], carriers, 4_000)
                            .expect("copied-body acoustic range settlement");
                    let peak = transition
                        .radiated_pressure_pcm
                        .iter()
                        .map(|sample| sample.unsigned_abs())
                        .max()
                        .unwrap_or(0);
                    let nonzero = transition
                        .radiated_pressure_pcm
                        .iter()
                        .filter(|sample| **sample != 0)
                        .count();
                    json!({
                        "respiratory_efferent_carriers": carriers.to_string(),
                        "applied_respiratory_carriers": transition.applied_motor_quanta.to_string(),
                        "stalled_respiratory_carriers": transition.stalled_motor_quanta.to_string(),
                        "peak_pressure": peak,
                        "nonzero_pressure_samples": nonzero,
                    })
                })
                .collect::<Vec<_>>();
            json!({
                "control": name,
                "glottal_aperture": glottis,
                "learned_section_0_area": section_zero,
                "learned_section_7_area": section_seven,
                "work_range": work_range,
            })
        })
        .collect::<Vec<_>>();
    json!({
        "measurement_only": true,
        "input_body_round_trip_exact": ArticulatedBodyState::decode(
            &body.encode().expect("copied body range encoding")
        ).expect("copied body range decoding") == *body,
        "controls": samples,
    })
}

fn one_clock_body_return_falsifier_json(
    state: &ResidentCognitiveFormationState,
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    let connected = retained_frontier_motor_range_json(state, articulated_body, 1);
    json!({
        "production_compiled": true,
        "scope": "one connected motor clock plus its exact proprioceptive return",
        "connected": connected,
    })
}

fn artificial_neutral_unpin_control_json(
    state: &ResidentCognitiveFormationState,
    body: Option<&ArticulatedBodyState>,
) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let mut neutral_axes = *body.axes();
    for axis in BODY_AXES {
        let anatomy = axis.anatomy();
        let position = body.axis(axis);
        if (position == anatomy.minimum || position == anatomy.maximum)
            && position != anatomy.neutral
        {
            neutral_axes[axis.index()] = anatomy.neutral;
        }
    }
    let unpinned = ArticulatedBodyState::from_physical_state(
        neutral_axes,
        body.lung_air_microlitres(),
        body.proprioception_initialized(),
    )
    .expect("artificial neutral-axis control")
    .with_articulatory_acoustic_state(body.articulatory_acoustic_state())
    .expect("preserve copied acoustic state in artificial control");
    let forced_axis_changes = BODY_AXES
        .into_iter()
        .filter_map(|axis| {
            let before = body.axis(axis);
            let after = unpinned.axis(axis);
            (before != after).then(|| {
                json!({
                    "axis": format!("{axis:?}"),
                    "copied_position": before,
                    "artificial_position": after,
                })
            })
        })
        .collect::<Vec<_>>();
    let learned_bridge_replay = retained_frontier_motor_range_json(state, Some(&unpinned), 1);
    json!({
        "production_compiled": true,
        "control_only": true,
        "prohibited_as_repair": true,
        "purpose": "isolate whether copied retained and one-carrier learned motor traffic move when only pathological accumulated stops are artificially unpinned",
        "forced_axis_change_count": forced_axis_changes.len(),
        "forced_axis_changes": forced_axis_changes,
        "lung_air_preserved": unpinned.lung_air_microlitres() == body.lung_air_microlitres(),
        "proprioception_flag_preserved":
            unpinned.proprioception_initialized() == body.proprioception_initialized(),
        "acoustic_state_preserved":
            unpinned.articulatory_acoustic_state() == body.articulatory_acoustic_state(),
        "one_carrier_learned_bridge_replay": learned_bridge_replay,
    })
}

/// Exercise the compiled V8 body law on the exact decoded production body.
/// This changes only disposable in-memory copies. It does not neutralize the
/// input body, author a motor meaning, or bypass the ordinary body codec and
/// proprioceptive evidence boundary.
fn candidate_antagonist_tissue_proof_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let stopped_axes = BODY_AXES
        .into_iter()
        .filter(|axis| {
            let anatomy = axis.anatomy();
            let position = body.axis(*axis);
            position != anatomy.neutral
                && (position == anatomy.minimum || position == anatomy.maximum)
        })
        .collect::<Vec<_>>();
    let mut released = body.clone();
    let mut first_release = std::collections::BTreeMap::new();
    let mut returned_to_neutral_at_ms = None;
    for elapsed_ms in 1_u64..=4_096 {
        let transition = settle_body_effector_drives(
            &released,
            &AdmittedBodyEffectorDrives::quiescent(),
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .expect("candidate copied-body passive settlement");
        for axis in &stopped_axes {
            if transition.successor.axis(*axis) != body.axis(*axis) {
                first_release.entry(*axis).or_insert(elapsed_ms);
            }
        }
        released = transition.successor;
        if BODY_AXES
            .iter()
            .all(|axis| released.axis(*axis) == axis.anatomy().neutral)
            && BODY_AXES.iter().all(|axis| {
                [
                    BodyEffectorDirection::TowardMinimum,
                    BodyEffectorDirection::TowardMaximum,
                ]
                .into_iter()
                .all(|direction| {
                    released.antagonist_activation(BodyEffectorTerminal::new(*axis, direction)) == 0
                })
            })
        {
            returned_to_neutral_at_ms = Some(elapsed_ms);
            break;
        }
    }

    let learned_terminals = [
        BodyEffectorTerminal::new(
            BodyAxis::VocalTractSection0Area,
            BodyEffectorDirection::TowardMaximum,
        ),
        BodyEffectorTerminal::new(
            BodyAxis::VocalTractSection7Area,
            BodyEffectorDirection::TowardMinimum,
        ),
    ];
    let one_carrier_twitches = learned_terminals.map(|terminal| {
        let neutral = ArticulatedBodyState::at_neutral();
        let drive = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
            terminal,
            outward_elementary_carriers: 1,
        }])
        .expect("candidate learned one-carrier admission");
        let first =
            settle_body_effector_drives(&neutral, &drive, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
                .expect("candidate learned one-carrier settlement");
        let source =
            admit_articulated_body_consequence_source(1, &first.proprioceptive_consequences)
                .expect("candidate one-carrier body source");
        let mut exact_motor_causes = source
            .joint_source_ports()
            .iter()
            .map(exact_moved_effector_terminal)
            .collect::<Result<Vec<_>, _>>()
            .expect("candidate exact moved-terminal evidence")
            .into_iter()
            .flatten()
            .map(|cause| format!("{cause:?}"))
            .collect::<Vec<_>>();
        exact_motor_causes.sort_unstable();
        exact_motor_causes.dedup();
        let cold = ArticulatedBodyState::decode(
            &first.successor.encode().expect("candidate twitch encodes"),
        )
        .expect("candidate twitch cold decodes");
        let cold_exact = cold == first.successor;
        let first_position = first.successor.axis(terminal.axis());
        let first_activation = first.successor.antagonist_activation(terminal);
        let mut successor = cold;
        let mut returned_at_ms = None;
        for elapsed_ms in 2_u64..=512 {
            successor = settle_body_effector_drives(
                &successor,
                &AdmittedBodyEffectorDrives::quiescent(),
                BODY_SETTLEMENT_CLOCK_MICROSECONDS,
            )
            .expect("candidate twitch relaxation")
            .successor;
            if successor.axis(terminal.axis()) == terminal.axis().anatomy().neutral
                && successor.antagonist_activation(terminal) == 0
            {
                returned_at_ms = Some(elapsed_ms);
                break;
            }
        }
        json!({
            "terminal": format!("{terminal:?}"),
            "first_position": first_position,
            "first_activation_units": first_activation,
            "moved_on_first_ms": first_position != terminal.axis().anatomy().neutral,
            "exact_motor_causes": exact_motor_causes,
            "cold_restore_exact": cold_exact,
            "returned_to_neutral_at_ms": returned_at_ms,
        })
    });

    let axis = BodyAxis::VocalTractSection0Area;
    let minimum = BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum);
    let maximum = BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMaximum);
    let opposed = settle_body_effector_drives(
        &ArticulatedBodyState::at_neutral(),
        &AdmittedBodyEffectorDrives::admit(vec![
            BodyEffectorDrive {
                terminal: minimum,
                outward_elementary_carriers: 8,
            },
            BodyEffectorDrive {
                terminal: maximum,
                outward_elementary_carriers: 8,
            },
        ])
        .expect("candidate equal-antagonist admission"),
        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
    )
    .expect("candidate equal-antagonist settlement");

    let mut sustained = ArticulatedBodyState::at_neutral();
    let one_per_ms = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
        terminal: maximum,
        outward_elementary_carriers: 1,
    }])
    .expect("candidate sustained admission");
    let mut sustained_stall = 0_u128;
    for _ in 0..1_000 {
        let transition = settle_body_effector_drives(
            &sustained,
            &one_per_ms,
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .expect("candidate sustained settlement");
        sustained_stall = sustained_stall
            .checked_add(
                transition
                    .proprioceptive_consequences
                    .iter()
                    .map(|consequence| consequence.stalled_carriers)
                    .sum::<u128>(),
            )
            .expect("candidate sustained stall width");
        sustained = transition.successor;
    }

    let saturation = settle_body_effector_drives(
        &ArticulatedBodyState::at_neutral(),
        &AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
            terminal: maximum,
            outward_elementary_carriers: 100_000,
        }])
        .expect("candidate saturation admission"),
        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
    )
    .expect("candidate saturation settlement");

    let composition_drive = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
        terminal: maximum,
        outward_elementary_carriers: 1,
    }])
    .expect("candidate composition admission");
    let neutral = ArticulatedBodyState::at_neutral();
    let whole = settle_body_effector_drives(&neutral, &composition_drive, 250_000)
        .expect("candidate whole duration")
        .successor;
    let first = settle_body_effector_drives(&neutral, &composition_drive, 64_000)
        .expect("candidate split first duration")
        .successor;
    let split =
        settle_body_effector_drives(&first, &AdmittedBodyEffectorDrives::quiescent(), 186_000)
            .expect("candidate split second duration")
            .successor;

    json!({
        "production_law_compiled_in_test": true,
        "input_body_encoded_bytes": body.encode().expect("candidate input body encodes").len(),
        "v8_roundtrip_exact": ArticulatedBodyState::decode(
            &body.encode().expect("candidate copied body encodes")
        ).expect("candidate copied body decodes") == *body,
        "stopped_non_neutral_axes": stopped_axes
            .iter()
            .map(|axis| format!("{axis:?}"))
            .collect::<Vec<_>>(),
        "all_stops_released_on_first_ms": first_release.len() == stopped_axes.len()
            && first_release.values().all(|elapsed| *elapsed == 1),
        "first_release_ms": first_release
            .into_iter()
            .map(|(axis, elapsed)| (format!("{axis:?}"), elapsed))
            .collect::<std::collections::BTreeMap<_, _>>(),
        "all_axes_returned_to_neutral_at_ms": returned_to_neutral_at_ms,
        "learned_one_carrier_twitches": one_carrier_twitches,
        "equal_antagonists_position_unchanged": opposed.successor.axis(axis) == axis.anatomy().neutral,
        "equal_antagonists_activation_zero": opposed.successor.antagonist_activation(minimum) == 0
            && opposed.successor.antagonist_activation(maximum) == 0,
        "sustained_one_per_ms_position": sustained.axis(axis),
        "sustained_one_per_ms_is_interior": sustained.axis(axis) > axis.anatomy().minimum
            && sustained.axis(axis) < axis.anatomy().maximum,
        "sustained_one_per_ms_total_stall": sustained_stall.to_string(),
        "saturation_stalled_carriers": saturation.proprioceptive_consequences[0]
            .stalled_carriers.to_string(),
        "duration_64_plus_186_equals_250": split == whole,
    })
}

fn articulated_body_axis_census_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return Value::Null;
    };
    let axes = BODY_AXES
        .into_iter()
        .map(|axis| {
            let anatomy = axis.anatomy();
            let position = body.axis(axis);
            json!({
                "axis": format!("{axis:?}"),
                "minimum": anatomy.minimum,
                "neutral": anatomy.neutral,
                "maximum": anatomy.maximum,
                "position": position,
                "at_minimum": position == anatomy.minimum,
                "at_maximum": position == anatomy.maximum,
                "at_neutral": position == anatomy.neutral,
            })
        })
        .collect::<Vec<_>>();
    let limit_count = axes
        .iter()
        .filter(|axis| {
            axis["at_minimum"].as_bool() == Some(true) || axis["at_maximum"].as_bool() == Some(true)
        })
        .count();
    let quiescent = settle_body_effector_drives(
        body,
        &AdmittedBodyEffectorDrives::quiescent(),
        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
    )
    .expect("copied-body quiescent settlement");
    json!({
        "axis_count": axes.len(),
        "limit_count": limit_count,
        "lung_air_microlitres": body.lung_air_microlitres(),
        "proprioception_initialized": body.proprioception_initialized(),
        "acoustic_state_quiescent": body.articulatory_acoustic_state().is_quiescent(),
        "quiescent_successor_equals_predecessor": quiescent.successor == *body,
        "quiescent_reached_terminal_count": quiescent.reached_terminal_count,
        "quiescent_consequence_count": quiescent.proprioceptive_consequences.len(),
        "axes": axes,
    })
}

/// Read-only audit of the persisted vocal-route anatomy. This advances no
/// organism clock and authors no anatomy, work, frontier, or observation.
/// It distinguishes retired one-motor contacts from exact coordinated posture
/// preparations after lived route growth.
fn vocal_route_structure_json(state: &ResidentCognitiveFormationState) -> Value {
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let mut records = Vec::new();
    let mut vocal_motors = std::collections::BTreeSet::new();
    for (left_flat, right_flat) in state.electrical_fabric.contact_endpoints() {
        let left = state.electrical_fabric.lineages()[left_flat];
        let right = state.electrical_fabric.lineages()[right_flat];
        let (ordering, motor) = match (
            state.topology_index.layer_of(left),
            state.topology_index.layer_of(right),
        ) {
            (Some(11), Some(12)) => (left, right),
            (Some(12), Some(11)) => (right, left),
            _ => continue,
        };
        let Some(terminal) = state
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (*lineage == motor)
                    .then(|| mount.body_effector_terminal())
                    .flatten()
            })
        else {
            continue;
        };
        if !terminal.axis().is_vocal_articulator() {
            continue;
        }
        vocal_motors.insert(motor);
        let resolved_routes =
            super::lean_sensorimotor_route::vocal_cognitive_action_route_for_motor(
                &state.cohorts,
                &state.topology_index,
                motor,
            )
            .expect("persisted vocal routes resolve")
            .into_iter()
            .filter(|route| route.preparation.ordering_lineage == ordering)
            .collect::<Vec<_>>();
        let resolved_route_count = resolved_routes.len();
        let route_founders = resolved_routes
            .iter()
            .map(|route| {
                let association_ownership = route
                    .preparation
                    .associations
                    .iter()
                    .map(|contact| {
                        let owners = state
                            .formation_index
                            .candidate_indices([contact.lineage], std::iter::empty());
                        json!({
                            "association": lineage_hex(contact.lineage),
                            "formation_count": owners.len(),
                            "retained_count": owners.iter().filter(|index| {
                                !state.mosaics[**index].mosaic.is_original_only()
                            }).count(),
                            "recurrent_owners": owners.iter().filter_map(|index| {
                                state.mosaics[*index].recurrent_lineage.map(lineage_hex)
                            }).collect::<Vec<_>>(),
                        })
                    })
                    .collect::<Vec<_>>();
                json!({
                    "associations": route.preparation.associations.iter()
                        .map(|contact| lineage_hex(contact.lineage))
                        .collect::<Vec<_>>(),
                    "association_ownership": association_ownership,
                    "motors": route.preparation.motors.iter()
                        .map(|contact| lineage_hex(contact.lineage))
                        .collect::<Vec<_>>(),
                })
            })
            .collect::<Vec<_>>();
        let resolved_continuation_count =
            super::lean_sensorimotor_route::vocal_cognitive_action_continuation_routes_for_motor(
                &state.cohorts,
                &state.topology_index,
                motor,
            )
            .expect("persisted vocal continuation routes resolve")
            .into_iter()
            .filter(|route| route.destination_ordering_lineage == ordering)
            .count();
        let motor_flat = state
            .topology_index
            .flat_for_lineage(motor)
            .expect("persisted vocal motor resolves");
        let ordering_flat = state
            .topology_index
            .flat_for_lineage(ordering)
            .expect("persisted vocal ordering resolves");
        let (ordering_cohort, ordering_neuron, _) =
            state.topology_index.flat_locations[ordering_flat];
        let ordering_state = &state.cohorts[ordering_cohort].state.neurons()[ordering_neuron];
        let (motor_cohort, motor_neuron, _) = state.topology_index.flat_locations[motor_flat];
        let motor_anatomy = &state.cohorts[motor_cohort].anatomy.neuron_anatomies()[motor_neuron];
        let motor_state = &state.cohorts[motor_cohort].state.neurons()[motor_neuron];
        records.push(json!({
            "ordering": ordering.iter().map(|byte| format!("{byte:02x}")).collect::<String>(),
            "motor": motor.iter().map(|byte| format!("{byte:02x}")).collect::<String>(),
            "terminal": format!("{terminal:?}"),
            "coordinated_resolved": resolved_route_count == 1,
            "resolved_route_count": resolved_route_count,
            "resolved_continuation_count": resolved_continuation_count,
            "route_founders": route_founders,
            "ordering_separated_elementary_charges": ordering_state.separated_elementary_charges().to_string(),
            "motor_gate_open_population": motor_state.gate.open_population(),
            "motor_gate_population": motor_anatomy.gate_population(),
            "motor_gate_dissipated_quanta": motor_state.gate.dissipated_quanta(),
            "motor_gate_dissipation_capacity_quanta": motor_anatomy.gate_dissipation_capacity_quanta(),
            "motor_gate_dissipation_quantum_zeptojoules": motor_anatomy.gate_dissipation_quantum_zeptojoules().to_string(),
            "motor_receptor_residue_zeptojoules": motor_state.receptor_quantum_residue.energy().to_string(),
            "motor_separated_elementary_charges": motor_state.separated_elementary_charges().to_string(),
        }));
    }
    records.sort_by_key(|record| {
        (
            record["ordering"].as_str().unwrap_or_default().to_owned(),
            record["motor"].as_str().unwrap_or_default().to_owned(),
        )
    });
    let unresolved_route_contact_count = records
        .iter()
        .filter(|record| record["coordinated_resolved"].as_bool() != Some(true))
        .count();
    let mut association_motor_paths = Vec::new();
    for motor in vocal_motors.iter().copied() {
        let motor_flat = state
            .topology_index
            .flat_for_lineage(motor)
            .expect("persisted vocal motor resolves");
        let terminal = state
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (*lineage == motor)
                    .then(|| mount.body_effector_terminal())
                    .flatten()
            })
            .expect("persisted vocal motor has a typed terminal");
        let mut associations = std::collections::BTreeSet::new();
        for regulation_flat in state.topology_index.neighbours_by_flat[motor_flat]
            .iter()
            .copied()
        {
            let regulation = state.topology_index.flat_locations[regulation_flat].2;
            if state.topology_index.layer_of(regulation) != Some(8) {
                continue;
            }
            for affective_flat in state.topology_index.neighbours_by_flat[regulation_flat]
                .iter()
                .copied()
            {
                let affective = state.topology_index.flat_locations[affective_flat].2;
                if state.topology_index.layer_of(affective) != Some(10) {
                    continue;
                }
                for association_flat in state.topology_index.neighbours_by_flat[affective_flat]
                    .iter()
                    .copied()
                {
                    let association = state.topology_index.flat_locations[association_flat].2;
                    if state.topology_index.layer_of(association) == Some(7) {
                        associations.insert(association);
                    }
                }
            }
        }
        for association in associations {
            let association_flat = state
                .topology_index
                .flat_for_lineage(association)
                .expect("persisted association resolves");
            let recurrent_count = state.topology_index.neighbours_by_flat[association_flat]
                .iter()
                .copied()
                .filter(|flat| {
                    state
                        .topology_index
                        .layer_of(state.topology_index.flat_locations[*flat].2)
                        == Some(9)
                })
                .count();
            let formation_owners = state
                .formation_index
                .candidate_indices([association], std::iter::empty());
            association_motor_paths.push(json!({
                "association": lineage_hex(association),
                "motor": lineage_hex(motor),
                "terminal": format!("{terminal:?}"),
                "recurrent_count": recurrent_count,
                "formation_count": formation_owners.len(),
                "retained_formation_count": formation_owners.iter().filter(|index| {
                    !state.mosaics[**index].mosaic.is_original_only()
                }).count(),
            }));
        }
    }
    association_motor_paths.sort_by_key(|record| {
        (
            record["terminal"].as_str().unwrap_or_default().to_owned(),
            record["association"]
                .as_str()
                .unwrap_or_default()
                .to_owned(),
        )
    });
    let mut continuations = vocal_motors
        .into_iter()
        .flat_map(|motor| {
            super::lean_sensorimotor_route::vocal_cognitive_action_continuation_routes_for_motor(
                &state.cohorts,
                &state.topology_index,
                motor,
            )
            .expect("persisted vocal continuation routes resolve")
            .into_iter()
            .map(move |route| {
                json!({
                    "source": lineage_hex(route.source_ordering_lineage),
                    "destination": lineage_hex(route.destination_ordering_lineage),
                    "motor": lineage_hex(motor),
                    "bond": format!("{:?}", route.continuation_bond),
                })
            })
        })
        .collect::<Vec<_>>();
    continuations.sort_by_key(|record| {
        (
            record["source"].as_str().unwrap_or_default().to_owned(),
            record["destination"]
                .as_str()
                .unwrap_or_default()
                .to_owned(),
            record["motor"].as_str().unwrap_or_default().to_owned(),
        )
    });
    continuations.dedup();
    json!({
        "measurement_only": true,
        "organism_advanced": false,
        "vocal_route_contact_count": records.len(),
        "unresolved_or_legacy_route_contact_count": unresolved_route_contact_count,
        "association_motor_paths": association_motor_paths,
        "routes": records,
        "continuation_count": continuations.len(),
        "continuations": continuations,
    })
}

#[test]
fn reservoir_probe_dump() {
    assert!(
        std::env::var_os("GUALA_PROBE_GUIDED_VOCAL_ROUTE_GROWTH_ONLY").is_none()
            || std::env::var_os("GUALA_PROBE_GUIDED_VOCAL_POPULATION_GROWTH_ONLY").is_some()
            || std::env::var_os("GUALA_PROBE_GUIDED_VOCAL_GROWTH_STATE_IN").is_some(),
        "route-growth-only requires the population-growth selector or an explicit growth-state input",
    );
    if let Ok(taught_state_path) = std::env::var("GUALA_PROBE_GUIDED_VOCAL_GROWTH_STATE_IN") {
        let out_path = std::env::var("GUALA_PROBE_OUT").expect("GUALA_PROBE_OUT must be set");
        let taught_body_path = std::env::var("GUALA_PROBE_GUIDED_VOCAL_GROWTH_BODY_IN")
            .expect("saved guided-vocal growth body path must be set");
        let cognitive = fs::read(&taught_state_path).expect("read saved growth cognitive state");
        let cognitive =
            ResidentCognitiveFormationState::migrate_to_current_format(&cognitive, usize::MAX)
                .expect("migrate saved growth cognitive state to the candidate codec");
        let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
            .expect("decode saved growth cognitive state");
        let body = ArticulatedBodyState::decode(
            &fs::read(&taught_body_path).expect("read saved growth body"),
        )
        .expect("decode saved growth body");
        fs::write(
            out_path,
            serde_json::to_vec_pretty(&guided_vocal_population_growth_json(&state, Some(&body)))
                .unwrap(),
        )
        .expect("write saved-state guided-vocal growth result");
        return;
    }
    if let Ok(taught_state_path) = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_STATE_IN") {
        let out_path = std::env::var("GUALA_PROBE_OUT").expect("GUALA_PROBE_OUT must be set");
        let taught_body_path = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_BODY_IN")
            .expect("saved guided-vocal tail body path must be set");
        let cue_pressure_path = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_CUE_PRESSURE_PCM")
            .expect("saved guided-vocal tail cue pressure path must be set");
        let maximum_clocks = std::env::var("GUALA_PROBE_UNGUIDED_VOCAL_CLOCKS")
            .ok()
            .map(|value| value.parse::<u64>().expect("saved-tail clocks are u64"))
            .unwrap_or(12);
        let occurrence = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_OCCURRENCE")
            .ok()
            .map(|value| value.parse::<u64>().expect("saved-tail occurrence is u64"))
            .unwrap_or(20);
        let guide_carriers = std::env::var("GUALA_PROBE_GUIDED_VOCAL_CARRIERS")
            .ok()
            .map(|value| value.parse::<u128>().expect("saved-tail carriers are u128"))
            .unwrap_or(1_500);
        let cognitive = fs::read(&taught_state_path).expect("read saved taught cognitive state");
        let cognitive =
            ResidentCognitiveFormationState::migrate_to_current_format(&cognitive, usize::MAX)
                .expect("migrate saved taught cognitive state to the candidate codec");
        let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
            .expect("decode saved taught cognitive state");
        let body = ArticulatedBodyState::decode(
            &fs::read(&taught_body_path).expect("read saved taught body"),
        )
        .expect("decode saved taught body");
        let cue_pressure_bytes = fs::read(&cue_pressure_path).expect("read saved cue pressure");
        assert!(matches!(cue_pressure_bytes.len(), 8_000 | 32_000));
        let cue_phase = std::env::var("GUALA_PROBE_GUIDED_VOCAL_TAIL_CUE_PHASE")
            .ok()
            .map(|value| {
                value
                    .parse::<usize>()
                    .expect("saved-tail cue phase is usize")
            })
            .unwrap_or(0);
        let available_phases = cue_pressure_bytes.len() / 8_000;
        assert!(cue_phase < available_phases);
        let cue_pressure = cue_pressure_bytes
            .chunks_exact(2)
            .skip(cue_phase * 4_000)
            .take(4_000)
            .map(|sample| i16::from_le_bytes([sample[0], sample[1]]))
            .collect::<Vec<_>>();
        let sound_only = std::env::var_os("GUALA_PROBE_GUIDED_VOCAL_TAIL_SOUND_ONLY").is_some();
        fs::write(
            out_path,
            serde_json::to_vec_pretty(&saved_guided_vocal_tail_json(
                state,
                body,
                cue_pressure,
                occurrence,
                maximum_clocks,
                guide_carriers,
                sound_only,
            ))
            .unwrap(),
        )
        .expect("write saved guided-vocal tail result");
        return;
    }
    if let Ok(raw_cognitive_path) = std::env::var("GUALA_PROBE_RAW_COGNITIVE_IN") {
        let out_path = std::env::var("GUALA_PROBE_OUT").expect("GUALA_PROBE_OUT must be set");
        let cognitive = fs::read(&raw_cognitive_path).expect("read raw cognitive state");
        let cognitive =
            ResidentCognitiveFormationState::migrate_to_current_format(&cognitive, usize::MAX)
                .expect("migrate raw cognitive state to the candidate codec");
        let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
            .expect("decode raw cognitive state for vocal route structure");
        fs::write(
            out_path,
            serde_json::to_vec_pretty(&json!({
                "raw_cognitive_path": raw_cognitive_path,
                "vocal_route_structure": vocal_route_structure_json(&state),
            }))
            .unwrap(),
        )
        .expect("write raw cognitive vocal route structure");
        return;
    }
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
        let (organism_tick, cognitive, articulated_body) = parse_envelope_with_body(&bytes);
        let body_mechanics_range_only =
            std::env::var_os("GUALA_PROBE_BODY_MECHANICS_RANGE_ONLY").is_some();
        let artificial_unpin_only = std::env::var_os("GUALA_PROBE_ARTIFICIAL_UNPIN_ONLY").is_some();
        let motor_work_range_only = std::env::var_os("GUALA_PROBE_MOTOR_WORK_RANGE_ONLY").is_some();
        let source_work_motor_range_only =
            std::env::var_os("GUALA_PROBE_SOURCE_WORK_MOTOR_RANGE_ONLY").is_some();
        let temporal_gate_work_range_only =
            std::env::var_os("GUALA_PROBE_TEMPORAL_GATE_WORK_ONLY").is_some();
        let production_replayed_motor_only =
            std::env::var_os("GUALA_PROBE_PRODUCTION_REPLAYED_MOTOR_ONLY").is_some();
        let artificial_vocal_synergy_only =
            std::env::var_os("GUALA_PROBE_ARTIFICIAL_VOCAL_SYNERGY_ONLY").is_some();
        let guided_vocal_population_growth_only =
            std::env::var_os("GUALA_PROBE_GUIDED_VOCAL_POPULATION_GROWTH_ONLY").is_some();
        let vocal_route_structure_only =
            std::env::var_os("GUALA_PROBE_VOCAL_ROUTE_STRUCTURE_ONLY").is_some();
        let antagonist_activation_range_only =
            std::env::var_os("GUALA_PROBE_ANTAGONIST_ACTIVATION_RANGE_ONLY").is_some();
        let candidate_tissue_proof_only =
            std::env::var_os("GUALA_PROBE_CANDIDATE_TISSUE_PROOF_ONLY").is_some();
        let record = if vocal_route_structure_only {
            let cognitive =
                ResidentCognitiveFormationState::migrate_to_current_format(&cognitive, usize::MAX)
                    .expect("migrate cognitive state for vocal route structure");
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for vocal route structure");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "vocal_route_structure": vocal_route_structure_json(&state),
            })
        } else if guided_vocal_population_growth_only {
            let cognitive =
                ResidentCognitiveFormationState::migrate_to_current_format(&cognitive, usize::MAX)
                    .expect("migrate cognitive state for guided vocal population growth");
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for guided vocal population growth");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "guided_vocal_population_growth":
                    guided_vocal_population_growth_json(
                        &state,
                        articulated_body.as_ref(),
                    ),
            })
        } else if artificial_vocal_synergy_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for artificial vocal-synergy control");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "artificial_vocal_synergy_unblock":
                    artificial_vocal_synergy_unblock_json(
                        &state,
                        articulated_body.as_ref(),
                    ),
            })
        } else if production_replayed_motor_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for production motor replay");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "production_replayed_motor_discharge":
                    production_replayed_motor_discharge_json(
                        &state,
                        articulated_body.as_ref(),
                    ),
            })
        } else if temporal_gate_work_range_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for temporal gate-work range");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "temporal_gate_work_range":
                    temporal_gate_work_range_json(
                        &state,
                        &cognitive,
                        articulated_body.as_ref(),
                    ),
            })
        } else if source_work_motor_range_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for source-work motor range");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "source_work_to_motor_reservoir_range":
                    source_work_motor_candidate_falsifier_json(&state),
            })
        } else if candidate_tissue_proof_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for candidate tissue proof");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "candidate_antagonist_tissue_proof":
                    candidate_antagonist_tissue_proof_json(articulated_body.as_ref()),
                "connected_and_severed_motor_transduction":
                    integrated_motor_transduction_falsifier_json(
                        &state,
                        articulated_body.as_ref(),
                    ),
                "copied_body_l13_acoustic_range":
                    copied_body_l13_acoustic_range_json(articulated_body.as_ref()),
            })
        } else if body_mechanics_range_only {
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "copied_body_passive_mechanics_range":
                    copied_body_passive_mechanics_range_json(articulated_body.as_ref()),
            })
        } else if antagonist_activation_range_only {
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "copied_body_antagonist_activation_range":
                    copied_body_antagonist_activation_range_json(articulated_body.as_ref()),
            })
        } else if artificial_unpin_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for artificial unpin control");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "artificial_neutral_unpin_control":
                    artificial_neutral_unpin_control_json(&state, articulated_body.as_ref()),
            })
        } else if motor_work_range_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for motor-work range");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "motor_inward_preparation_energy_range":
                    motor_inward_preparation_energy_range_json(&state),
                "retained_frontier_motor_work_range":
                    retained_frontier_motor_range_json(
                        &state,
                        articulated_body.as_ref(),
                        1,
                    ),
            })
        } else if cognitive.is_empty() {
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
            let motor_reachability = motor_reachability_json(&state);
            let skip_ranges = std::env::var_os("GUALA_PROBE_SKIP_RANGES").is_some();
            let body_return_only = std::env::var_os("GUALA_PROBE_BODY_RETURN_ONLY").is_some();
            let production_body_range_only =
                std::env::var_os("GUALA_PROBE_PRODUCTION_BODY_RANGE_ONLY").is_some();
            let motor_bridge_active_range = (!skip_ranges && !production_body_range_only)
                .then(|| motor_bridge_active_range_json(&state));
            let motor_bridge_gradient_population_range = (!skip_ranges
                && !production_body_range_only)
                .then(|| motor_bridge_gradient_population_range_json(&state));
            let retained_frontier_motor_range = (!skip_ranges || production_body_range_only)
                .then(|| retained_frontier_motor_range_json(&state, articulated_body.as_ref(), 3));
            let motor_inward_preparation_energy_range =
                motor_inward_preparation_energy_range_json(&state);
            let integrated_motor_transduction_falsifier =
                (!body_return_only && !production_body_range_only).then(|| {
                    integrated_motor_transduction_falsifier_json(&state, articulated_body.as_ref())
                });
            let one_clock_body_return_falsifier = body_return_only
                .then(|| one_clock_body_return_falsifier_json(&state, articulated_body.as_ref()));
            // BOUNDARY CENSUS (bridge campaign): contact counts by exact
            // layer pair — the L11->L12 number is the bridge's scoreboard.
            let mut boundary_counts = std::collections::BTreeMap::<String, u64>::new();
            {
                let layer_of = |lineage: [u8; 16]| {
                    state.cohorts.iter().find_map(|cohort| {
                        cohort
                            .anatomy
                            .mounts()
                            .iter()
                            .zip(cohort.anatomy.neuron_lineages())
                            .find_map(|(mount, candidate)| {
                                (*candidate == lineage).then(|| mount.place().layer())
                            })
                    })
                };
                for (left, right) in state.electrical_fabric.contact_endpoints() {
                    let a = layer_of(state.electrical_fabric.lineages()[left]);
                    let b = layer_of(state.electrical_fabric.lineages()[right]);
                    if let (Some(a), Some(b)) = (a, b) {
                        let (low, high) = if a <= b { (a, b) } else { (b, a) };
                        *boundary_counts.entry(format!("{low}->{high}")).or_default() += 1;
                    }
                }
            }
            let mounted = state
                .cohorts
                .iter()
                .flat_map(|cohort| {
                    cohort
                        .anatomy
                        .mounts()
                        .iter()
                        .zip(cohort.anatomy.neuron_lineages())
                        .map(|(mount, lineage)| (*lineage, mount.place().layer()))
                })
                .collect::<Vec<_>>();
            let electrical_fabric = state
                .electrical_fabric
                .contact_endpoints()
                .zip(
                    state
                        .electrical_fabric
                        .anatomy()
                        .contact_anatomies()
                        .iter()
                        .zip(state.electrical_fabric.state().contact_states()),
                )
                .map(|((left, right), (anatomy, contact_state))| {
                    let left_lineage = state.electrical_fabric.lineages()[left];
                    let right_lineage = state.electrical_fabric.lineages()[right];
                    let layer = |lineage| {
                        mounted.iter().find_map(|(candidate, layer)| {
                            (*candidate == lineage).then_some(*layer)
                        })
                    };
                    let lineage_hex = |lineage: [u8; 16]| {
                        lineage
                            .iter()
                            .map(|byte| format!("{byte:02x}"))
                            .collect::<String>()
                    };
                    let (phase_numerator, phase_denominator) =
                        contact_state.carrier_phase().parts();
                    json!({
                        "left_lineage": lineage_hex(left_lineage),
                        "left_layer": layer(left_lineage),
                        "right_lineage": lineage_hex(right_lineage),
                        "right_layer": layer(right_lineage),
                        "conductance_picosiemens": exact_json(anatomy.conductance_picosiemens()),
                        "effective_conductance_picosiemens": exact_json(
                            anatomy
                                .effective_conductance(contact_state)
                                .expect("probe contact state matches anatomy"),
                        ),
                        "carrier_phase": format!("{phase_numerator}/{phase_denominator}"),
                        "conducting_channel_population": contact_state
                            .conducting_channel_population()
                            .to_string(),
                        "transition_work_phase": exact_json(
                            contact_state.transition_work_phase(),
                        ),
                    })
                })
                .collect::<Vec<_>>();
            let lineage_hex = |lineage: [u8; 16]| {
                lineage
                    .iter()
                    .map(|byte| format!("{byte:02x}"))
                    .collect::<String>()
            };
            let retained_mosaics = state
                .mosaics
                .iter()
                .map(|retained| {
                    json!({
                        "recurrent_lineage": retained.recurrent_lineage.map(lineage_hex),
                        "member_lineages": retained
                            .mosaic
                            .member_lineages()
                            .iter()
                            .copied()
                            .map(lineage_hex)
                            .collect::<Vec<_>>(),
                        "original_bonds": retained
                            .mosaic
                            .original_bonds()
                            .iter()
                            .map(|bond| {
                                let (left, right) = bond.endpoints();
                                json!({
                                    "left": lineage_hex(left),
                                    "right": lineage_hex(right),
                                    "parallel_ordinal": bond.parallel_ordinal(),
                                })
                            })
                            .collect::<Vec<_>>(),
                        "recurrence_bonds": retained
                            .mosaic
                            .recurrence_bonds()
                            .iter()
                            .map(|bond| {
                                let (left, right) = bond.endpoints();
                                json!({
                                    "left": lineage_hex(left),
                                    "right": lineage_hex(right),
                                    "parallel_ordinal": bond.parallel_ordinal(),
                                })
                            })
                            .collect::<Vec<_>>(),
                    })
                })
                .collect::<Vec<_>>();
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "articulated_body_axis_census":
                    articulated_body_axis_census_json(articulated_body.as_ref()),
                "generation": state.generation,
                "unexpressed_electrical_seed_count": state.unexpressed_electrical_seeds.len(),
                "dormant_lineage_seed_count": state.dormant_lineage_seeds.len(),
                "electrical_fabric": electrical_fabric,
                "retained_mosaics": retained_mosaics,
                "motor_reachability": motor_reachability,
                "motor_bridge_active_range": motor_bridge_active_range,
                "motor_bridge_gradient_population_range": motor_bridge_gradient_population_range,
                "retained_frontier_motor_range": retained_frontier_motor_range,
                "motor_inward_preparation_energy_range":
                    motor_inward_preparation_energy_range,
                "integrated_motor_transduction_falsifier":
                    integrated_motor_transduction_falsifier,
                "one_clock_body_return_falsifier": one_clock_body_return_falsifier,
                "boundary_contact_counts": boundary_counts.iter().map(|(k,v)| (k.clone(), json!(v))).collect::<serde_json::Map<_,_>>(),
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
