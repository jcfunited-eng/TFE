// Included by canonical_l0_l4.rs so this production batch adapter can use the
// private typed trajectory without widening the differential surface.

#[derive(Clone, Debug)]
pub(crate) struct SettledCanonicalPort {
    pub(crate) trace_payload: Vec<u8>,
    pub(crate) trace_digest: [u8; 32],
    pub(crate) l0_count: usize,
    pub(crate) l1_gates: Vec<(usize, usize)>,
    pub(crate) l2_regimes: Vec<String>,
    pub(crate) l3_count: usize,
    pub(crate) l4_rows_bits: Vec<[u64; 7]>,
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn settle_current_canonical_port(
    field_bits: &[u64],
    relevance_bits: &[u64],
    lane_id: &str,
    port_id: &str,
    adapter_sha256: &str,
    source_sha256: &str,
    kernel_input_map_json: &[u8],
    legacy_map: bool,
) -> Result<SettledCanonicalPort, String> {
    let field: Vec<f64> = field_bits.iter().copied().map(f64::from_bits).collect();
    let relevance: Vec<f64> = relevance_bits
        .iter()
        .copied()
        .map(f64::from_bits)
        .collect();
    let trace = run_kernel(&field, &relevance, &Config::current())?;
    let trace_payload = canonical_trace(
        &trace,
        lane_id,
        port_id,
        adapter_sha256,
        source_sha256,
        kernel_input_map_json,
        legacy_map,
    )?;
    let trace_digest = sha256(&trace_payload);
    Ok(SettledCanonicalPort {
        trace_payload,
        trace_digest,
        l0_count: trace.sev.len(),
        l1_gates: trace
            .l1
            .iter()
            .map(|value| (value.gate.start, value.gate.end))
            .collect(),
        l2_regimes: trace
            .l2
            .iter()
            .map(|value| value.regime.text().to_owned())
            .collect(),
        l3_count: trace.l3.len(),
        l4_rows_bits: trace
            .l4
            .iter()
            .map(|value| value.fields.map(f64::to_bits))
            .collect(),
    })
}

pub(crate) fn current_canonical_kernel_config_payload() -> Vec<u8> {
    let config = Config::current();
    let mut output = Vec::new();
    output.extend_from_slice(b"GLKCFG01");
    output.extend_from_slice(&1u16.to_le_bytes());
    output.extend_from_slice(&(config.variance_window as u32).to_le_bytes());
    output.push(u8::from(config.gate_boundary_strict_gt));
    output.extend_from_slice(&(config.mosaic_lattices.len() as u16).to_le_bytes());
    for lattice in &config.mosaic_lattices {
        for value in lattice {
            output.extend_from_slice(&value.to_bits().to_le_bytes());
        }
    }
    for value in [
        config.sigma_min,
        config.delta_min,
        config.kappa_min,
        config.alpha1,
        config.alpha2,
        config.alpha3,
        config.tau_d,
        config.beta1,
        config.beta2,
        config.beta3,
        config.theta_v,
        config.theta_r,
        config.gamma1,
        config.gamma2,
        config.gamma3,
        config.lambda_u1,
        config.lambda_u2,
        config.lambda_u3,
        config.chi_min,
        config.chi_max,
        config.psi_min,
        config.psi_max,
        config.u_max,
        config.lambda1,
        config.lambda2,
        config.lambda3,
        config.lambda4,
        config.lambda5,
        config.h_max,
        config.epsilon_d,
        config.eta_h,
        config.eta_ias,
        config.breath_xi,
        config.breath_chi,
        config.b_min,
        config.b_max,
    ] {
        output.extend_from_slice(&value.to_bits().to_le_bytes());
    }
    output
}

#[pyfunction]
fn canonical_l0_l4_current_config<'py>(
    py: Python<'py>,
) -> (Bound<'py, PyBytes>, String) {
    let payload = current_canonical_kernel_config_payload();
    let digest = hex_digest(&sha256(&payload));
    (PyBytes::new(py, &payload), digest)
}

#[cfg(test)]
mod batch_api_tests {
    use super::*;

    #[test]
    fn config_payload_changes_if_any_frozen_bit_changes() {
        let first = current_canonical_kernel_config_payload();
        let second = current_canonical_kernel_config_payload();
        assert_eq!(first, second);
        assert_eq!(sha256(&first), sha256(&second));
        assert!(first.starts_with(b"GLKCFG01"));
    }

    #[test]
    fn settled_port_retains_every_layer_and_field() {
        let fields = [0.5f64, 0.75, 1.25, 0.6]
            .map(f64::to_bits);
        let relevance = [1.0f64, 0.5, 0.25, 0.75]
            .map(f64::to_bits);
        let digest = "0".repeat(64);
        let settled = settle_current_canonical_port(
            &fields,
            &relevance,
            "sight",
            "retina-0",
            &digest,
            &digest,
            b"{}",
            true,
        )
        .expect("settled port");
        assert_eq!(settled.l0_count, fields.len());
        assert_eq!(settled.l1_gates.len(), settled.l2_regimes.len());
        assert_eq!(settled.l1_gates.len(), settled.l3_count);
        assert_eq!(settled.l1_gates.len(), settled.l4_rows_bits.len());
        assert!(settled.trace_payload.starts_with(b"{\"L0_SEV\""));
        assert_eq!(settled.trace_digest, sha256(&settled.trace_payload));
    }
}
