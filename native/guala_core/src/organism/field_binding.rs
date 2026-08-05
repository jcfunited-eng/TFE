//! Post-custody regeneration checks for sealed DSF delivery references.
//!
//! This boundary replays supplied canonical GLNEPI03 candidates through the
//! unchanged native L0--L4 bank generator. It proves exact reproduction of the
//! sealed delivery records and neuron field bits. It does not establish the
//! truth, provenance, or meaning of sensory inputs, world/body/wake state, or
//! any receipt outside the DSF delivery path.

use super::seal::{CanonicalBankBinding, CustodyVerifiedSeal};
use super::OrganismState;
use crate::full_field_bank::{
    regenerate_full_field_bank, FullFieldRegenerationBudget, RegeneratedFullFieldBank,
};
use sha2::{Digest, Sha256};
use std::{fmt, mem::size_of};

const CANDIDATE_MAGIC: &[u8; 8] = b"GLNEPI03";
const FIELD_COUNT: usize = 7;
const VERIFIED_ROW_BYTES: usize = FIELD_COUNT * size_of::<u64>();

#[derive(Clone, Copy)]
pub(crate) struct CandidatePayload<'a> {
    bytes: &'a [u8],
}

impl<'a> CandidatePayload<'a> {
    pub(crate) fn new(bytes: &'a [u8]) -> Self {
        Self { bytes }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DsfDeliveryVerificationBudget {
    pub(crate) max_candidate_count: u64,
    pub(crate) max_single_candidate_bytes: u64,
    pub(crate) max_total_candidate_bytes: u64,
    pub(crate) max_single_generated_bank_bytes: u64,
    pub(crate) max_total_generated_bank_bytes: u64,
    pub(crate) max_total_port_count: u64,
    pub(crate) max_total_sample_count: u64,
    pub(crate) max_total_field_row_count: u64,
    pub(crate) max_authority_count: u64,
    pub(crate) max_neuron_count: u64,
    pub(crate) max_verified_row_bytes: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum DsfDeliveryVerificationError {
    CandidateCountBudgetExceeded,
    CandidateCountMismatch,
    CandidateInputBudgetExceeded,
    TotalCandidateInputBudgetExceeded,
    AuthorityBudgetExceeded,
    NeuronBudgetExceeded,
    VerifiedRowBudgetExceeded,
    AllocationFailed,
    LengthOverflow,
    CandidateMagicMismatch,
    CandidateOrderOrSubstitution,
    Regeneration(String),
    BindingReceiptMismatch(&'static str),
    DeliveryReceiptMismatch(&'static str),
    MissingDeliveryAuthority,
    NeuronFieldMismatch { neuron_index: u64, field_index: u8 },
}

impl fmt::Display for DsfDeliveryVerificationError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::CandidateCountBudgetExceeded => {
                write!(output, "DSF candidate-count budget exceeded")
            }
            Self::CandidateCountMismatch => {
                write!(
                    output,
                    "DSF candidate count differs from sealed bank bindings"
                )
            }
            Self::CandidateInputBudgetExceeded => {
                write!(output, "one DSF candidate exceeds its input budget")
            }
            Self::TotalCandidateInputBudgetExceeded => {
                write!(output, "aggregate DSF candidate input budget exceeded")
            }
            Self::AuthorityBudgetExceeded => write!(output, "DSF authority budget exceeded"),
            Self::NeuronBudgetExceeded => write!(output, "DSF neuron budget exceeded"),
            Self::VerifiedRowBudgetExceeded => {
                write!(output, "DSF verified-row byte budget exceeded")
            }
            Self::AllocationFailed => write!(output, "DSF verification allocation failed"),
            Self::LengthOverflow => write!(output, "DSF verification length overflow"),
            Self::CandidateMagicMismatch => write!(output, "candidate is not GLNEPI03"),
            Self::CandidateOrderOrSubstitution => {
                write!(
                    output,
                    "candidate order or content differs from sealed bindings"
                )
            }
            Self::Regeneration(reason) => write!(output, "DSF bank regeneration failed: {reason}"),
            Self::BindingReceiptMismatch(name) => {
                write!(output, "regenerated bank differs at sealed {name}")
            }
            Self::DeliveryReceiptMismatch(name) => {
                write!(output, "regenerated delivery differs at sealed {name}")
            }
            Self::MissingDeliveryAuthority => {
                write!(
                    output,
                    "sealed bank binding has no contiguous delivery authority"
                )
            }
            Self::NeuronFieldMismatch {
                neuron_index,
                field_index,
            } => write!(
                output,
                "neuron {neuron_index} differs from regenerated DSF field {field_index}"
            ),
        }
    }
}

impl std::error::Error for DsfDeliveryVerificationError {}

/// Custody upgraded only through exact DSF bank/delivery reproduction.
///
/// This proves that every sealed DSF delivery receipt and all seven neuron
/// field-bit slots reproduce from the supplied GLNEPI03 candidates. It does not
/// verify semantic truth or the meanings of world, body, wake, evidence, growth,
/// specialization, fractal, or causal receipts.
pub(crate) struct DsfDeliveryVerifiedSeal {
    custody: CustodyVerifiedSeal,
}

impl DsfDeliveryVerifiedSeal {
    pub(crate) fn state(&self) -> &OrganismState {
        self.custody.state()
    }

    pub(crate) fn organism_state_receipt(&self) -> [u8; 32] {
        self.custody.organism_state_receipt()
    }
}

pub(crate) fn verify_dsf_deliveries(
    custody: CustodyVerifiedSeal,
    candidates: &[CandidatePayload<'_>],
    budget: DsfDeliveryVerificationBudget,
) -> Result<DsfDeliveryVerifiedSeal, DsfDeliveryVerificationError> {
    verify_dsf_deliveries_with(custody, candidates, budget, regenerate_full_field_bank)
}

fn verify_dsf_deliveries_with<F>(
    custody: CustodyVerifiedSeal,
    candidates: &[CandidatePayload<'_>],
    budget: DsfDeliveryVerificationBudget,
    mut regenerate: F,
) -> Result<DsfDeliveryVerifiedSeal, DsfDeliveryVerificationError>
where
    F: FnMut(&[u8], FullFieldRegenerationBudget) -> Result<RegeneratedFullFieldBank, String>,
{
    let bindings = custody.bank_bindings();
    let binding_count = u64_len(bindings.len())?;
    if binding_count > budget.max_candidate_count {
        return Err(DsfDeliveryVerificationError::CandidateCountBudgetExceeded);
    }
    if candidates.len() != bindings.len() {
        return Err(DsfDeliveryVerificationError::CandidateCountMismatch);
    }

    let state = custody.state();
    let authority_count = u64_len(state.dsf_delivery_authorities.len())?;
    if authority_count > budget.max_authority_count {
        return Err(DsfDeliveryVerificationError::AuthorityBudgetExceeded);
    }
    let neuron_count = u64_len(state.neurons.len())?;
    if neuron_count > budget.max_neuron_count {
        return Err(DsfDeliveryVerificationError::NeuronBudgetExceeded);
    }
    let verified_row_bytes = authority_count
        .checked_mul(u64_len(VERIFIED_ROW_BYTES)?)
        .ok_or(DsfDeliveryVerificationError::LengthOverflow)?;
    if verified_row_bytes > budget.max_verified_row_bytes {
        return Err(DsfDeliveryVerificationError::VerifiedRowBudgetExceeded);
    }

    let mut total_candidate_bytes = 0_u64;
    for (candidate, binding) in candidates.iter().zip(bindings) {
        let candidate_bytes = u64_len(candidate.bytes.len())?;
        if candidate_bytes > budget.max_single_candidate_bytes {
            return Err(DsfDeliveryVerificationError::CandidateInputBudgetExceeded);
        }
        total_candidate_bytes = total_candidate_bytes
            .checked_add(candidate_bytes)
            .ok_or(DsfDeliveryVerificationError::LengthOverflow)?;
        if total_candidate_bytes > budget.max_total_candidate_bytes {
            return Err(DsfDeliveryVerificationError::TotalCandidateInputBudgetExceeded);
        }
        if candidate.bytes.get(..CANDIDATE_MAGIC.len()) != Some(CANDIDATE_MAGIC.as_slice()) {
            return Err(DsfDeliveryVerificationError::CandidateMagicMismatch);
        }
        let candidate_receipt: [u8; 32] = Sha256::digest(candidate.bytes).into();
        if candidate_receipt != binding.candidate_receipt {
            return Err(DsfDeliveryVerificationError::CandidateOrderOrSubstitution);
        }
    }

    let mut verified_rows = Vec::new();
    verified_rows
        .try_reserve_exact(state.dsf_delivery_authorities.len())
        .map_err(|_| DsfDeliveryVerificationError::AllocationFailed)?;

    let mut authority_index = 0_usize;
    let mut used_bank_bytes = 0_u64;
    let mut used_ports = 0_u64;
    let mut used_samples = 0_u64;
    let mut used_field_rows = 0_u64;

    for (binding, candidate) in bindings.iter().zip(candidates) {
        let remaining_bank_bytes = budget
            .max_total_generated_bank_bytes
            .checked_sub(used_bank_bytes)
            .ok_or(DsfDeliveryVerificationError::LengthOverflow)?;
        let regenerated = regenerate(
            candidate.bytes,
            FullFieldRegenerationBudget {
                max_candidate_bytes: budget.max_single_candidate_bytes,
                max_bank_bytes: budget
                    .max_single_generated_bank_bytes
                    .min(remaining_bank_bytes),
                max_port_count: budget
                    .max_total_port_count
                    .checked_sub(used_ports)
                    .ok_or(DsfDeliveryVerificationError::LengthOverflow)?,
                max_sample_count: budget
                    .max_total_sample_count
                    .checked_sub(used_samples)
                    .ok_or(DsfDeliveryVerificationError::LengthOverflow)?,
                max_field_row_count: budget
                    .max_total_field_row_count
                    .checked_sub(used_field_rows)
                    .ok_or(DsfDeliveryVerificationError::LengthOverflow)?,
            },
        )
        .map_err(DsfDeliveryVerificationError::Regeneration)?;

        compare_binding(binding, &regenerated)?;
        used_bank_bytes = checked_add_usize(used_bank_bytes, regenerated.bank_bytes().len())?;
        used_ports = checked_add_usize(used_ports, regenerated.port_count())?;
        used_samples = checked_add_usize(used_samples, regenerated.sample_count())?;
        used_field_rows = checked_add_usize(used_field_rows, regenerated.field_row_count())?;

        let group_start = authority_index;
        while let Some(authority) = state.dsf_delivery_authorities.get(authority_index) {
            if authority.field_bank_receipt != binding.bank_receipt {
                break;
            }
            let delivery = regenerated
                .delivery(authority.port_index, authority.tuple_index)
                .map_err(|reason| DsfDeliveryVerificationError::Regeneration(reason.to_string()))?;
            if delivery.candidate_receipt != binding.candidate_receipt {
                return Err(DsfDeliveryVerificationError::BindingReceiptMismatch(
                    "candidate receipt",
                ));
            }
            if delivery.bank_receipt != authority.field_bank_receipt {
                return Err(DsfDeliveryVerificationError::DeliveryReceiptMismatch(
                    "bank receipt",
                ));
            }
            if delivery.kernel_config_receipt != authority.kernel_config_receipt {
                return Err(DsfDeliveryVerificationError::DeliveryReceiptMismatch(
                    "kernel-config receipt",
                ));
            }
            if delivery.port_index != authority.port_index {
                return Err(DsfDeliveryVerificationError::DeliveryReceiptMismatch(
                    "port index",
                ));
            }
            if delivery.tuple_index != authority.tuple_index {
                return Err(DsfDeliveryVerificationError::DeliveryReceiptMismatch(
                    "tuple index",
                ));
            }
            if delivery.trace_receipt != authority.trace_receipt {
                return Err(DsfDeliveryVerificationError::DeliveryReceiptMismatch(
                    "trace receipt",
                ));
            }
            if delivery.tuple_receipt != authority.tuple_receipt {
                return Err(DsfDeliveryVerificationError::DeliveryReceiptMismatch(
                    "tuple receipt",
                ));
            }
            if delivery.basin_receipt != authority.basin_receipt {
                return Err(DsfDeliveryVerificationError::DeliveryReceiptMismatch(
                    "basin receipt",
                ));
            }
            verified_rows.push(delivery.coordinate_bits);
            authority_index += 1;
        }
        if authority_index == group_start {
            return Err(DsfDeliveryVerificationError::MissingDeliveryAuthority);
        }
    }
    if authority_index != state.dsf_delivery_authorities.len() {
        return Err(DsfDeliveryVerificationError::MissingDeliveryAuthority);
    }

    for (neuron_index, neuron) in state.neurons.iter().enumerate() {
        let delivery_index = usize::try_from(neuron.local_dsf.authority_index)
            .map_err(|_| DsfDeliveryVerificationError::LengthOverflow)?;
        let regenerated_bits = verified_rows
            .get(delivery_index)
            .ok_or(DsfDeliveryVerificationError::MissingDeliveryAuthority)?;
        for field_index in 0..FIELD_COUNT {
            if neuron.local_dsf.coordinate_bits[field_index] != regenerated_bits[field_index] {
                return Err(DsfDeliveryVerificationError::NeuronFieldMismatch {
                    neuron_index: u64_len(neuron_index)?,
                    field_index: field_index as u8,
                });
            }
        }
    }

    Ok(DsfDeliveryVerifiedSeal { custody })
}

fn compare_binding(
    binding: &CanonicalBankBinding,
    regenerated: &RegeneratedFullFieldBank,
) -> Result<(), DsfDeliveryVerificationError> {
    if regenerated.candidate_receipt() != binding.candidate_receipt {
        return Err(DsfDeliveryVerificationError::BindingReceiptMismatch(
            "candidate receipt",
        ));
    }
    if regenerated.bank_receipt() != binding.bank_receipt {
        return Err(DsfDeliveryVerificationError::BindingReceiptMismatch(
            "bank receipt",
        ));
    }
    if regenerated.kernel_config_receipt() != binding.kernel_config_receipt {
        return Err(DsfDeliveryVerificationError::BindingReceiptMismatch(
            "kernel-config receipt",
        ));
    }
    Ok(())
}

fn checked_add_usize(current: u64, value: usize) -> Result<u64, DsfDeliveryVerificationError> {
    current
        .checked_add(u64_len(value)?)
        .ok_or(DsfDeliveryVerificationError::LengthOverflow)
}

fn u64_len(value: usize) -> Result<u64, DsfDeliveryVerificationError> {
    u64::try_from(value).map_err(|_| DsfDeliveryVerificationError::LengthOverflow)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::canonical_l0_l4::current_canonical_kernel_config_payload;
    use crate::full_field_bank::{
        regenerate_full_field_bank, FullFieldRegenerationBudget, RegeneratedDsfDelivery,
    };
    use crate::organism::genesis::{
        authenticate_genesis_identity, verify_genesis_identity, GenesisAuthenticationKey,
    };
    use crate::organism::seal::{
        seal_genesis, verify_genesis, CanonicalBankBinding, SealDecodeBudget, SealEncodeBudget,
        SealKey,
    };
    use crate::organism::{
        ArenaRange, DsfDeliveryAuthority, LocalDsfState, NeuronState, OrganismState, PackedTrits,
        ResourceObservation, StabilityEvidenceRanges, WakeState,
    };
    use std::cell::Cell;

    const SIGNED_UNIT_PROFILE: &[u8] = b"guala.live.native_sensory.F_equals_1_plus_s_over_2.v1";
    const IDENTITY: [u8; 16] = [
        0x10, 0x53, 0x2f, 0x91, 0x7b, 0x2d, 0x4a, 0xc8, 0x98, 0x04, 0x46, 0x73, 0x5d, 0xa1, 0x28,
        0xfe,
    ];
    const SEAL_ENCODE: SealEncodeBudget = SealEncodeBudget {
        max_organism_bytes: 1_000_000,
        max_output_bytes: 1_000_000,
        max_bank_bindings: 8,
    };
    const SEAL_DECODE: SealDecodeBudget = SealDecodeBudget {
        max_input_bytes: 1_000_000,
        max_organism_bytes: 1_000_000,
        max_decoded_heap_bytes: 1_000_000,
        max_bank_bindings: 8,
    };
    const UNBOUNDED_REGENERATION: FullFieldRegenerationBudget = FullFieldRegenerationBudget {
        max_candidate_bytes: u64::MAX,
        max_bank_bytes: u64::MAX,
        max_port_count: u64::MAX,
        max_sample_count: u64::MAX,
        max_field_row_count: u64::MAX,
    };

    struct Fixture {
        custody: CustodyVerifiedSeal,
        candidates: Vec<Vec<u8>>,
        exact_budget: DsfDeliveryVerificationBudget,
    }

    struct CandidateBankFixture {
        candidate: Vec<u8>,
        binding: CanonicalBankBinding,
        authority: DsfDeliveryAuthority,
        coordinate_bits: [u64; 7],
    }

    fn fixture_candidate(episode_id: &str) -> Vec<u8> {
        let mut output = Vec::new();
        output.extend_from_slice(CANDIDATE_MAGIC);
        output.extend_from_slice(&3_u16.to_le_bytes());
        push_bytes(&mut output, &current_canonical_kernel_config_payload());
        push_text(&mut output, episode_id);
        output.extend_from_slice(&[0, 1, 1, 1, 1, 1]);
        push_u32(&mut output, 2);

        for topology_index in 0..2 {
            output.push(0);
            push_u32(&mut output, topology_index);
            push_text(&mut output, "retina");
            push_text(
                &mut output,
                &format!("{episode_id}-retina-{topology_index}"),
            );
            output.extend_from_slice(&2_u16.to_le_bytes());
            push_text(&mut output, "row");
            push_text(&mut output, "0");
            push_text(&mut output, "column");
            push_text(&mut output, &topology_index.to_string());
            push_text(&mut output, "optical_intensity");
            push_text(&mut output, "normalized_binary64");
            push_text(&mut output, "exact-unit-source-relevance.v1");
            push_text(&mut output, "");
            push_text(&mut output, "signed-unit-affine-v1");
            for (numerator, denominator) in [("-1", "1"), ("1", "1"), ("1", "1"), ("1", "2")] {
                push_rational(&mut output, numerator, denominator);
            }
            push_bytes(&mut output, SIGNED_UNIT_PROFILE);

            let first = if episode_id.ends_with("-1") {
                ("1", "2", 0.5_f64, "5", "4", 1.25_f64)
            } else {
                ("1", "4", 0.25_f64, "9", "8", 1.125_f64)
            };
            let samples = [
                ("0", "1", first.2, "0", "1", first.3, first.4, first.5),
                ("1", "1", -0.5_f64, "1", "4", "3", "4", 0.75_f64),
            ];
            push_u32(&mut output, samples.len());
            for (
                time_numerator,
                time_denominator,
                signal,
                phase_numerator,
                phase_denominator,
                field_numerator,
                field_denominator,
                field,
            ) in samples
            {
                push_rational(&mut output, time_numerator, time_denominator);
                output.extend_from_slice(&signal.to_bits().to_le_bytes());
                push_rational(&mut output, phase_numerator, phase_denominator);
                push_rational(&mut output, "1", "1");
                push_rational(&mut output, field_numerator, field_denominator);
                output.extend_from_slice(&field.to_bits().to_le_bytes());
                output.extend_from_slice(&1.0_f64.to_bits().to_le_bytes());
            }
        }
        output
    }

    fn candidate_bank_fixture(episode_id: &str) -> CandidateBankFixture {
        let candidate = fixture_candidate(episode_id);
        let bank =
            regenerate_full_field_bank(&candidate, UNBOUNDED_REGENERATION).expect("fixture bank");
        let delivery = bank.delivery(0, 0).expect("fixture delivery");
        CandidateBankFixture {
            binding: CanonicalBankBinding {
                candidate_receipt: bank.candidate_receipt(),
                bank_receipt: bank.bank_receipt(),
                kernel_config_receipt: bank.kernel_config_receipt(),
            },
            authority: authority(&delivery),
            coordinate_bits: delivery.coordinate_bits,
            candidate,
        }
    }

    fn authority(delivery: &RegeneratedDsfDelivery) -> DsfDeliveryAuthority {
        DsfDeliveryAuthority {
            field_bank_receipt: delivery.bank_receipt,
            kernel_config_receipt: delivery.kernel_config_receipt,
            port_index: delivery.port_index,
            tuple_index: delivery.tuple_index,
            trace_receipt: delivery.trace_receipt,
            tuple_receipt: delivery.tuple_receipt,
            basin_receipt: delivery.basin_receipt,
        }
    }

    fn build_fixture(bank_count: usize) -> Fixture {
        fixture_with_mutation(bank_count, |_, _| {})
    }

    fn fixture_with_mutation<F>(bank_count: usize, mutate: F) -> Fixture
    where
        F: FnOnce(&mut OrganismState, &mut [CanonicalBankBinding]),
    {
        let mut banks: Vec<_> = (0..bank_count)
            .map(|index| candidate_bank_fixture(&format!("episode-{index}")))
            .collect();
        banks.sort_by_key(|bank| {
            (
                bank.binding.bank_receipt,
                bank.binding.candidate_receipt,
                bank.binding.kernel_config_receipt,
            )
        });

        let bindings: Vec<_> = banks.iter().map(|bank| bank.binding).collect();
        let authorities: Vec<_> = banks.iter().map(|bank| bank.authority.clone()).collect();
        let neurons: Vec<_> = banks
            .iter()
            .enumerate()
            .map(|(index, bank)| neuron(index, bank.coordinate_bits))
            .collect();
        let candidates: Vec<_> = banks.into_iter().map(|bank| bank.candidate).collect();
        let mut state = organism_state(authorities, neurons);
        let mut mutable_bindings = bindings;
        mutate(&mut state, &mut mutable_bindings);

        let key = SealKey::new(1, [9; 32]).expect("fixture key");
        let envelope =
            seal_genesis(&state, &key, &mutable_bindings, SEAL_ENCODE).expect("fixture seal");
        let head: [u8; 32] = Sha256::digest(&envelope).into();
        let genesis_key =
            GenesisAuthenticationKey::new(73, [0xa7; 32]).expect("genesis-only fixture key");
        let genesis_record =
            authenticate_genesis_identity(IDENTITY, &genesis_key).expect("fixture genesis record");
        let identity = verify_genesis_identity(
            genesis_record.as_bytes(),
            &genesis_key,
            genesis_record.trusted_head(),
        )
        .expect("fixture verified identity");
        let custody =
            verify_genesis(&envelope, &key, head, &identity, SEAL_DECODE).expect("fixture custody");

        let mut total_candidate_bytes = 0_u64;
        let mut single_candidate_bytes = 0_u64;
        let mut total_bank_bytes = 0_u64;
        let mut single_bank_bytes = 0_u64;
        let mut total_ports = 0_u64;
        let mut total_samples = 0_u64;
        let mut total_rows = 0_u64;
        for candidate in &candidates {
            let bank = regenerate_full_field_bank(candidate, UNBOUNDED_REGENERATION)
                .expect("measure fixture bank");
            let candidate_bytes = candidate.len() as u64;
            let bank_bytes = bank.bank_bytes().len() as u64;
            total_candidate_bytes += candidate_bytes;
            single_candidate_bytes = single_candidate_bytes.max(candidate_bytes);
            total_bank_bytes += bank_bytes;
            single_bank_bytes = single_bank_bytes.max(bank_bytes);
            total_ports += bank.port_count() as u64;
            total_samples += bank.sample_count() as u64;
            total_rows += bank.field_row_count() as u64;
        }
        let authority_count = custody.state().dsf_delivery_authorities.len() as u64;
        let neuron_count = custody.state().neurons.len() as u64;
        Fixture {
            custody,
            candidates,
            exact_budget: DsfDeliveryVerificationBudget {
                max_candidate_count: bank_count as u64,
                max_single_candidate_bytes: single_candidate_bytes,
                max_total_candidate_bytes: total_candidate_bytes,
                max_single_generated_bank_bytes: single_bank_bytes,
                max_total_generated_bank_bytes: total_bank_bytes,
                max_total_port_count: total_ports,
                max_total_sample_count: total_samples,
                max_total_field_row_count: total_rows,
                max_authority_count: authority_count,
                max_neuron_count: neuron_count,
                max_verified_row_bytes: authority_count * VERIFIED_ROW_BYTES as u64,
            },
        }
    }

    fn organism_state(
        dsf_delivery_authorities: Vec<DsfDeliveryAuthority>,
        neurons: Vec<NeuronState>,
    ) -> OrganismState {
        OrganismState {
            identity: IDENTITY,
            generation: 0,
            prior_state_receipt: [0; 32],
            authenticated_world_revision: [2; 32],
            body_state_receipt: [3; 32],
            admitted_evidence: vec![],
            trit_arena: PackedTrits::from_trits(&[]).expect("empty trits"),
            causal_receipt_arena: vec![],
            dsf_delivery_authorities,
            neurons,
            couplings: vec![],
            causal_frontier: vec![],
            formation_member_arena: vec![],
            formations: vec![],
            stability_evidence_arena: vec![],
            stability_evidence: StabilityEvidenceRanges {
                coherence: ArenaRange { start: 0, len: 0 },
                formation_entropy: ArenaRange { start: 0, len: 0 },
                breathing_variance: ArenaRange { start: 0, len: 0 },
                uncertainty: ArenaRange { start: 0, len: 0 },
                tapestry_drift: ArenaRange { start: 0, len: 0 },
            },
            wake: WakeState::Quiescent,
            resources: ResourceObservation {
                cpu_nanoseconds: 1,
                resident_bytes: 2,
                durable_bytes: 3,
                recovery_reserve_bytes: 4,
                python_calls: 0,
                native_calls: 1,
            },
        }
    }

    fn neuron(index: usize, coordinate_bits: [u64; 7]) -> NeuronState {
        NeuronState {
            lineage: [(index + 1) as u8; 16],
            growth_dna: [(index + 10) as u8; 32],
            specialization_receipt: [(index + 20) as u8; 32],
            field_position: index as u64 + 1,
            trit_range: ArenaRange { start: 0, len: 0 },
            oscillator_phase_bits: 0.25_f64.to_bits(),
            oscillator_winding: index as i64,
            local_dsf: LocalDsfState {
                coordinate_bits,
                authority_index: index as u64,
            },
            energetic_bits: 0.75_f64.to_bits(),
            refractory_until_generation: 2,
            fractal: [(index + 30) as u8; 32],
            evidence_receipt: [(index + 40) as u8; 32],
            recent_causal_range: ArenaRange { start: 0, len: 0 },
        }
    }

    fn candidate_refs(candidates: &[Vec<u8>]) -> Vec<CandidatePayload<'_>> {
        candidates
            .iter()
            .map(|candidate| CandidatePayload::new(candidate))
            .collect()
    }

    fn push_u32(output: &mut Vec<u8>, value: usize) {
        output.extend_from_slice(&(value as u32).to_le_bytes());
    }

    fn push_text(output: &mut Vec<u8>, value: &str) {
        output.extend_from_slice(&(value.len() as u16).to_le_bytes());
        output.extend_from_slice(value.as_bytes());
    }

    fn push_bytes(output: &mut Vec<u8>, value: &[u8]) {
        push_u32(output, value.len());
        output.extend_from_slice(value);
    }

    fn push_rational(output: &mut Vec<u8>, numerator: &str, denominator: &str) {
        push_text(output, numerator);
        push_text(output, denominator);
    }

    #[test]
    fn exact_regeneration_upgrades_custody_without_semantic_overclaim() {
        let fixture = build_fixture(2);
        let candidates = candidate_refs(&fixture.candidates);
        let verified = verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget)
            .expect("exact DSF delivery verification");
        assert_eq!(verified.state().identity, IDENTITY);
        assert_eq!(verified.state().neurons.len(), 2);
    }

    #[test]
    fn all_candidates_are_prehashed_before_exactly_one_regeneration_per_bank() {
        let fixture = build_fixture(2);
        let mut reversed = candidate_refs(&fixture.candidates);
        reversed.reverse();
        let calls = Cell::new(0_u64);
        assert_eq!(
            verify_dsf_deliveries_with(
                fixture.custody,
                &reversed,
                fixture.exact_budget,
                |candidate, budget| {
                    calls.set(calls.get() + 1);
                    regenerate_full_field_bank(candidate, budget)
                },
            )
            .err(),
            Some(DsfDeliveryVerificationError::CandidateOrderOrSubstitution)
        );
        assert_eq!(calls.get(), 0);

        let fixture = build_fixture(2);
        let candidates = candidate_refs(&fixture.candidates);
        let calls = Cell::new(0_u64);
        verify_dsf_deliveries_with(
            fixture.custody,
            &candidates,
            fixture.exact_budget,
            |candidate, budget| {
                calls.set(calls.get() + 1);
                regenerate_full_field_bank(candidate, budget)
            },
        )
        .expect("one regeneration per binding");
        assert_eq!(calls.get(), 2);
    }

    #[test]
    fn count_magic_and_substitution_fail_before_regeneration() {
        let fixture = build_fixture(1);
        let calls = Cell::new(0_u64);
        assert_eq!(
            verify_dsf_deliveries_with(
                fixture.custody,
                &[],
                fixture.exact_budget,
                |candidate, budget| {
                    calls.set(calls.get() + 1);
                    regenerate_full_field_bank(candidate, budget)
                },
            )
            .err(),
            Some(DsfDeliveryVerificationError::CandidateCountMismatch)
        );
        assert_eq!(calls.get(), 0);

        let fixture = build_fixture(1);
        let extra = [
            CandidatePayload::new(&fixture.candidates[0]),
            CandidatePayload::new(&fixture.candidates[0]),
        ];
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &extra, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::CandidateCountMismatch)
        );

        let fixture = fixture_with_mutation(1, |_, bindings| {
            bindings[0].candidate_receipt[0] ^= 1;
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::CandidateOrderOrSubstitution)
        );

        let fixture = build_fixture(1);
        let mut changed = fixture.candidates[0].clone();
        changed[0] ^= 1;
        let changed = [CandidatePayload::new(&changed)];
        let calls = Cell::new(0_u64);
        assert_eq!(
            verify_dsf_deliveries_with(
                fixture.custody,
                &changed,
                fixture.exact_budget,
                |candidate, budget| {
                    calls.set(calls.get() + 1);
                    regenerate_full_field_bank(candidate, budget)
                },
            )
            .err(),
            Some(DsfDeliveryVerificationError::CandidateMagicMismatch)
        );
        assert_eq!(calls.get(), 0);

        let fixture = build_fixture(1);
        let mut changed = fixture.candidates[0].clone();
        let last = changed.len() - 1;
        changed[last] ^= 1;
        let changed = [CandidatePayload::new(&changed)];
        let calls = Cell::new(0_u64);
        assert_eq!(
            verify_dsf_deliveries_with(
                fixture.custody,
                &changed,
                fixture.exact_budget,
                |candidate, budget| {
                    calls.set(calls.get() + 1);
                    regenerate_full_field_bank(candidate, budget)
                },
            )
            .err(),
            Some(DsfDeliveryVerificationError::CandidateOrderOrSubstitution)
        );
        assert_eq!(calls.get(), 0);
    }

    #[test]
    fn binding_and_all_delivery_receipts_fail_closed() {
        let fixture = fixture_with_mutation(1, |state, bindings| {
            bindings[0].bank_receipt[0] ^= 1;
            state.dsf_delivery_authorities[0].field_bank_receipt = bindings[0].bank_receipt;
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::BindingReceiptMismatch(
                "bank receipt"
            ))
        );

        let fixture = fixture_with_mutation(1, |state, bindings| {
            bindings[0].kernel_config_receipt[0] ^= 1;
            state.dsf_delivery_authorities[0].kernel_config_receipt =
                bindings[0].kernel_config_receipt;
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::BindingReceiptMismatch(
                "kernel-config receipt"
            ))
        );

        for (receipt_index, expected) in [
            (0_usize, "trace receipt"),
            (1_usize, "tuple receipt"),
            (2_usize, "basin receipt"),
        ] {
            let fixture = fixture_with_mutation(1, |state, _| {
                let authority = &mut state.dsf_delivery_authorities[0];
                match receipt_index {
                    0 => authority.trace_receipt[0] ^= 1,
                    1 => authority.tuple_receipt[0] ^= 1,
                    2 => authority.basin_receipt[0] ^= 1,
                    _ => unreachable!(),
                }
            });
            let candidates = candidate_refs(&fixture.candidates);
            assert_eq!(
                verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
                Some(DsfDeliveryVerificationError::DeliveryReceiptMismatch(
                    expected
                ))
            );
        }
    }

    #[test]
    fn every_neuron_field_bit_and_signed_zero_are_exact() {
        for field_index in 0..FIELD_COUNT {
            let fixture = fixture_with_mutation(1, |state, _| {
                state.neurons[0].local_dsf.coordinate_bits[field_index] ^= 1;
            });
            let candidates = candidate_refs(&fixture.candidates);
            assert_eq!(
                verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
                Some(DsfDeliveryVerificationError::NeuronFieldMismatch {
                    neuron_index: 0,
                    field_index: field_index as u8,
                })
            );
        }

        let zero_fixture = build_fixture(1);
        let zero_index = zero_fixture.custody.state().neurons[0]
            .local_dsf
            .coordinate_bits
            .iter()
            .position(|bits| *bits == 0)
            .expect("fixture contains an exact positive-zero DSF field");
        drop(zero_fixture);

        let fixture = fixture_with_mutation(1, |state, _| {
            state.neurons[0].local_dsf.coordinate_bits[zero_index] = (-0.0_f64).to_bits();
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::NeuronFieldMismatch {
                neuron_index: 0,
                field_index: zero_index as u8,
            })
        );

        let fixture = fixture_with_mutation(1, |state, _| {
            state.neurons[0].local_dsf.coordinate_bits[0] = f64::from_bits(1).to_bits();
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::NeuronFieldMismatch {
                neuron_index: 0,
                field_index: 0,
            })
        );
    }

    #[test]
    fn valid_wrong_and_out_of_range_port_and_tuple_indices_fail_closed() {
        let fixture = fixture_with_mutation(1, |state, _| {
            state.dsf_delivery_authorities[0].port_index = 1;
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert!(matches!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget),
            Err(DsfDeliveryVerificationError::DeliveryReceiptMismatch(_))
        ));

        let fixture = fixture_with_mutation(1, |state, _| {
            state.dsf_delivery_authorities[0].port_index = u64::MAX;
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::Regeneration(
                "regenerated bank port index is outside the bank".into()
            ))
        );

        let fixture = fixture_with_mutation(1, |state, _| {
            state.dsf_delivery_authorities[0].tuple_index = 1;
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::DeliveryReceiptMismatch(
                "tuple receipt"
            ))
        );

        let fixture = fixture_with_mutation(1, |state, _| {
            state.dsf_delivery_authorities[0].tuple_index = u64::MAX;
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::Regeneration(
                "regenerated bank tuple index is outside the port".into()
            ))
        );
    }

    #[test]
    fn one_bank_with_multiple_authorities_regenerates_once() {
        let fixture = fixture_with_mutation(1, |state, _| {
            let candidate = fixture_candidate("episode-0");
            let bank = regenerate_full_field_bank(&candidate, UNBOUNDED_REGENERATION)
                .expect("multi-authority fixture bank");
            let second = bank.delivery(0, 1).expect("second tuple");
            state.dsf_delivery_authorities.push(authority(&second));
            state.neurons.push(neuron(1, second.coordinate_bits));
        });
        let candidates = candidate_refs(&fixture.candidates);
        let calls = Cell::new(0_u64);
        verify_dsf_deliveries_with(
            fixture.custody,
            &candidates,
            fixture.exact_budget,
            |candidate, budget| {
                calls.set(calls.get() + 1);
                regenerate_full_field_bank(candidate, budget)
            },
        )
        .expect("one bank serves its contiguous authority group");
        assert_eq!(calls.get(), 1);
    }

    #[test]
    fn shared_authority_and_redirected_valid_authority_fail_by_direct_row_index() {
        let fixture = fixture_with_mutation(1, |state, _| {
            let mut second = neuron(1, state.neurons[0].local_dsf.coordinate_bits);
            second.local_dsf.authority_index = 0;
            second.local_dsf.coordinate_bits[3] ^= 1;
            state.neurons.push(second);
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget).err(),
            Some(DsfDeliveryVerificationError::NeuronFieldMismatch {
                neuron_index: 1,
                field_index: 3,
            })
        );

        let fixture = fixture_with_mutation(1, |state, _| {
            let candidate = fixture_candidate("episode-0");
            let bank = regenerate_full_field_bank(&candidate, UNBOUNDED_REGENERATION)
                .expect("redirect fixture bank");
            let second = bank.delivery(0, 1).expect("redirect fixture tuple");
            state.dsf_delivery_authorities.push(authority(&second));
            state.neurons.push(neuron(1, second.coordinate_bits));
            state.neurons[0].local_dsf.authority_index = 1;
            state.neurons[1].local_dsf.authority_index = 0;
        });
        let candidates = candidate_refs(&fixture.candidates);
        assert!(matches!(
            verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget),
            Err(DsfDeliveryVerificationError::NeuronFieldMismatch { .. })
        ));
    }

    #[test]
    fn every_budget_accepts_exact_limit_and_rejects_one_over() {
        let fixture = build_fixture(1);
        let candidates = candidate_refs(&fixture.candidates);
        verify_dsf_deliveries(fixture.custody, &candidates, fixture.exact_budget)
            .expect("every exact limit");

        assert_budget_failure(
            |budget| budget.max_candidate_count -= 1,
            DsfDeliveryVerificationError::CandidateCountBudgetExceeded,
        );
        assert_budget_failure(
            |budget| budget.max_single_candidate_bytes -= 1,
            DsfDeliveryVerificationError::CandidateInputBudgetExceeded,
        );
        assert_budget_failure(
            |budget| budget.max_total_candidate_bytes -= 1,
            DsfDeliveryVerificationError::TotalCandidateInputBudgetExceeded,
        );
        assert_budget_failure(
            |budget| budget.max_authority_count -= 1,
            DsfDeliveryVerificationError::AuthorityBudgetExceeded,
        );
        assert_budget_failure(
            |budget| budget.max_neuron_count -= 1,
            DsfDeliveryVerificationError::NeuronBudgetExceeded,
        );
        assert_budget_failure(
            |budget| budget.max_verified_row_bytes -= 1,
            DsfDeliveryVerificationError::VerifiedRowBudgetExceeded,
        );
        assert_regeneration_budget_failure(
            |budget| budget.max_single_generated_bank_bytes -= 1,
            "native regenerated bank exceeds caller-derived output budget",
        );
        assert_regeneration_budget_failure(
            |budget| budget.max_total_generated_bank_bytes -= 1,
            "native regenerated bank exceeds caller-derived output budget",
        );
        assert_regeneration_budget_failure(
            |budget| budget.max_total_port_count -= 1,
            "native regenerated bank exceeds caller-derived port budget",
        );
        assert_regeneration_budget_failure(
            |budget| budget.max_total_sample_count -= 1,
            "native regenerated bank exceeds caller-derived sample budget",
        );
        assert_regeneration_budget_failure(
            |budget| budget.max_total_field_row_count -= 1,
            "native regenerated bank exceeds caller-derived field-row budget",
        );
    }

    fn assert_regeneration_budget_failure<F>(mutate: F, message: &str)
    where
        F: FnOnce(&mut DsfDeliveryVerificationBudget),
    {
        let fixture = build_fixture(1);
        let candidates = candidate_refs(&fixture.candidates);
        let mut budget = fixture.exact_budget;
        mutate(&mut budget);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, budget).err(),
            Some(DsfDeliveryVerificationError::Regeneration(message.into()))
        );
    }

    fn assert_budget_failure<F>(mutate: F, expected: DsfDeliveryVerificationError)
    where
        F: FnOnce(&mut DsfDeliveryVerificationBudget),
    {
        let fixture = build_fixture(1);
        let candidates = candidate_refs(&fixture.candidates);
        let mut budget = fixture.exact_budget;
        mutate(&mut budget);
        assert_eq!(
            verify_dsf_deliveries(fixture.custody, &candidates, budget).err(),
            Some(expected)
        );
    }
}
