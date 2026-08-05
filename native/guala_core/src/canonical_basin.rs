//! Exact canonical port-basin receipt generation from a complete native L4
//! trajectory.  Sign/zero classes are generated only as secondary metadata;
//! every authoritative seven-field binary64 value remains in its exact tuple
//! receipt.

use num_bigint::BigInt;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::sha256::sha256;

#[cfg(test)]
const FIELD_NAMES: [&str; 7] = ["D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"];

#[derive(Clone, Debug)]
pub(crate) struct PortBasinBytes {
    pub(crate) tuple_payloads: Vec<Vec<u8>>,
    pub(crate) tuple_digests: Vec<[u8; 32]>,
    pub(crate) basin_payload: Vec<u8>,
    pub(crate) basin_digest: [u8; 32],
}

pub(crate) fn generate_port_basin(
    lane_id: &str,
    port_id: &str,
    trace_digest: &[u8; 32],
    l0_count: usize,
    l1_gates: &[(usize, usize)],
    l2_regimes: &[String],
    l3_count: usize,
    l4_bits: &[[u64; 7]],
) -> Result<PortBasinBytes, String> {
    validate_identifier(lane_id, "lane_id")?;
    validate_identifier(port_id, "port_id")?;
    if l0_count == 0
        || l1_gates.is_empty()
        || l1_gates.len() != l2_regimes.len()
        || l1_gates.len() != l3_count
        || l1_gates.len() != l4_bits.len()
    {
        return Err("port basin does not retain a complete L0-L4 trajectory".into());
    }
    let mut prior_end = None;
    for (start, end) in l1_gates {
        if end < start || prior_end.map_or(*start != 0, |prior| *start != prior + 1) {
            return Err("port basin gates are not complete and ordered".into());
        }
        prior_end = Some(*end);
    }
    if prior_end != Some(l0_count - 1) {
        return Err("port basin gates do not cover every L0 sample".into());
    }
    for regime in l2_regimes {
        if !matches!(
            regime.as_str(),
            "DEGENERATE" | "STABLE" | "VOLATILE" | "TRANSITIONAL"
        ) {
            return Err("port basin has a noncanonical L2 regime".into());
        }
    }
    for row in l4_bits {
        if row.iter().any(|bits| !f64::from_bits(*bits).is_finite()) {
            return Err("port basin has a nonfinite L4 field".into());
        }
    }

    let trace_hex = hex_digest(trace_digest);
    let mut tuple_payloads = Vec::with_capacity(l4_bits.len());
    let mut tuple_digests = Vec::with_capacity(l4_bits.len());
    for (tuple_index, bits) in l4_bits.iter().enumerate() {
        let payload = exact_tuple_payload(lane_id, port_id, tuple_index, bits, &trace_hex);
        tuple_digests.push(sha256(&payload));
        tuple_payloads.push(payload);
    }
    let basin_payload = basin_payload(
        lane_id,
        port_id,
        &trace_hex,
        l0_count,
        l1_gates,
        l2_regimes,
        l3_count,
        l4_bits,
        &tuple_digests,
    );
    let basin_digest = sha256(&basin_payload);
    Ok(PortBasinBytes {
        tuple_payloads,
        tuple_digests,
        basin_payload,
        basin_digest,
    })
}

fn exact_tuple_payload(
    lane_id: &str,
    port_id: &str,
    tuple_index: usize,
    bits: &[u64; 7],
    trace_hex: &str,
) -> Vec<u8> {
    let mut output = String::new();
    output.push('{');
    key(&mut output, "exact_fields");
    output.push('{');
    for (index, (name, field_index)) in [
        ("B_k", 6usize),
        ("C_k", 4),
        ("D_k", 0),
        ("M_k", 1),
        ("P_k", 5),
        ("R_rev_k", 2),
        ("U_star_k", 3),
    ]
    .iter()
    .enumerate()
    {
        comma(&mut output, index);
        key(&mut output, name);
        string(
            &mut output,
            &binary_text(f64::from_bits(bits[*field_index])),
        );
    }
    output.push_str("},");
    key(&mut output, "lane_id");
    string(&mut output, lane_id);
    output.push(',');
    key(&mut output, "port_id");
    string(&mut output, port_id);
    output.push(',');
    key(&mut output, "schema");
    string(&mut output, "glew.global_uf.exact_dsf_field_tuple.v1");
    output.push(',');
    key(&mut output, "source_l0_l4_trace_receipt_sha256");
    string(&mut output, trace_hex);
    output.push(',');
    key(&mut output, "tuple_index");
    output.push_str(&tuple_index.to_string());
    output.push('}');
    output.into_bytes()
}

#[allow(clippy::too_many_arguments)]
fn basin_payload(
    lane_id: &str,
    port_id: &str,
    trace_hex: &str,
    l0_count: usize,
    l1_gates: &[(usize, usize)],
    l2_regimes: &[String],
    l3_count: usize,
    l4_bits: &[[u64; 7]],
    tuple_digests: &[[u8; 32]],
) -> Vec<u8> {
    let mut output = String::new();
    output.push('{');
    key(&mut output, "exact_dsf_field_tuple_receipt_sha256s");
    output.push('[');
    for (index, digest) in tuple_digests.iter().enumerate() {
        comma(&mut output, index);
        string(&mut output, &hex_digest(digest));
    }
    output.push_str("],");
    key(&mut output, "l0_l4_trace_receipt_sha256");
    string(&mut output, trace_hex);
    output.push(',');
    key(&mut output, "lane_id");
    string(&mut output, lane_id);
    output.push(',');
    key(&mut output, "layers");
    output.push('[');
    layer(
        &mut output,
        &format!("L0-trace-{trace_hex}"),
        0,
        &[format!("samples-{l0_count:08}")],
        &[],
    );
    output.push(',');
    layer(
        &mut output,
        &format!("L1-trace-{trace_hex}"),
        1,
        &l1_gates
            .iter()
            .enumerate()
            .map(|(index, (start, end))| format!("gate-{index:08}-{start:08}-{end:08}"))
            .collect::<Vec<_>>(),
        &[],
    );
    output.push(',');
    layer(
        &mut output,
        &format!("L2-trace-{trace_hex}"),
        2,
        &l2_regimes
            .iter()
            .enumerate()
            .map(|(index, regime)| format!("gate-{index:08}-{regime}"))
            .collect::<Vec<_>>(),
        &[],
    );
    output.push(',');
    layer(
        &mut output,
        &format!("L3-trace-{trace_hex}"),
        3,
        &(0..l3_count)
            .map(|index| format!("gate-{index:08}"))
            .collect::<Vec<_>>(),
        &[],
    );
    output.push(',');
    let classes: Vec<(String, &'static str)> = l4_bits
        .iter()
        .enumerate()
        .flat_map(|(tuple_index, bits)| {
            [
                ("B_k", 6usize),
                ("C_k", 4),
                ("D_k", 0),
                ("M_k", 1),
                ("P_k", 5),
                ("R_rev_k", 2),
                ("U_star_k", 3),
            ]
            .into_iter()
            .map(move |(name, field_index)| {
                (
                    format!("{tuple_index:08}:{name}"),
                    sign_class(f64::from_bits(bits[field_index])),
                )
            })
        })
        .collect();
    layer(
        &mut output,
        &format!("L4-trace-{trace_hex}"),
        4,
        &(0..l4_bits.len())
            .map(|index| format!("gate-{index:08}"))
            .collect::<Vec<_>>(),
        &classes,
    );
    output.push_str("],");
    key(&mut output, "port_id");
    string(&mut output, port_id);
    output.push(',');
    key(&mut output, "schema");
    string(&mut output, "glew.global_uf.port_kernel_basin.v2");
    output.push('}');
    output.into_bytes()
}

fn layer(
    output: &mut String,
    branch_id: &str,
    layer_index: usize,
    gates: &[String],
    classes: &[(String, &'static str)],
) {
    output.push('{');
    key(output, "branch_id");
    string(output, branch_id);
    output.push(',');
    key(output, "gate_path");
    output.push('[');
    for (index, gate) in gates.iter().enumerate() {
        comma(output, index);
        string(output, gate);
    }
    output.push_str("],");
    key(output, "layer_index");
    output.push_str(&layer_index.to_string());
    output.push(',');
    key(output, "secondary_semialgebraic_coordinate_classes");
    output.push('[');
    for (index, (coordinate, value_class)) in classes.iter().enumerate() {
        comma(output, index);
        output.push('{');
        key(output, "coordinate_id");
        string(output, coordinate);
        output.push(',');
        key(output, "value_class");
        string(output, value_class);
        output.push('}');
    }
    output.push_str("]}");
}

fn sign_class(value: f64) -> &'static str {
    if value < 0.0 {
        "negative"
    } else if value > 0.0 {
        "positive"
    } else {
        "exact_zero"
    }
}

fn binary_text(value: f64) -> String {
    if value == 0.0 {
        return "0/1".into();
    }
    let bits = value.to_bits();
    let negative = bits >> 63 != 0;
    let exponent_bits = ((bits >> 52) & 0x7ff) as i32;
    let fraction_bits = bits & ((1u64 << 52) - 1);
    let (mantissa, exponent) = if exponent_bits == 0 {
        (fraction_bits, -1074)
    } else {
        ((1u64 << 52) | fraction_bits, exponent_bits - 1023 - 52)
    };
    let mut numerator = BigInt::from(mantissa);
    let mut denominator = BigInt::from(1u8);
    if exponent >= 0 {
        numerator <<= exponent as usize;
    } else {
        denominator <<= (-exponent) as usize;
    }
    if negative {
        numerator = -numerator;
    }
    let ratio = num_rational::BigRational::new(numerator, denominator);
    format!("{}/{}", ratio.numer(), ratio.denom())
}

fn validate_identifier(value: &str, name: &str) -> Result<(), String> {
    if value.is_empty() || value.trim() != value {
        return Err(format!("{name} is not a canonical identifier"));
    }
    Ok(())
}

fn key(output: &mut String, value: &str) {
    string(output, value);
    output.push(':');
}

fn string(output: &mut String, value: &str) {
    output.push('"');
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{0008}' => output.push_str("\\b"),
            '\u{000c}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            character if character <= '\u{001f}' => {
                output.push_str(&format!("\\u{:04x}", character as u32));
            }
            character => output.push(character),
        }
    }
    output.push('"');
}

fn comma(output: &mut String, index: usize) {
    if index != 0 {
        output.push(',');
    }
}

fn hex_digest(digest: &[u8; 32]) -> String {
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn parse_hex_digest(value: &str) -> Result<[u8; 32], String> {
    if value.len() != 64 {
        return Err("trace digest is not 64 hexadecimal characters".into());
    }
    let mut output = [0u8; 32];
    for (index, byte) in output.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&value[index * 2..index * 2 + 2], 16)
            .map_err(|_| "trace digest is not lowercase hexadecimal".to_string())?;
    }
    if hex_digest(&output) != value {
        return Err("trace digest is not lowercase hexadecimal".into());
    }
    Ok(output)
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn canonical_port_basin_differential<'py>(
    py: Python<'py>,
    lane_id: String,
    port_id: String,
    trace_sha256: String,
    l0_count: usize,
    l1_gates: Vec<(usize, usize)>,
    l2_regimes: Vec<String>,
    l3_count: usize,
    l4_rows_bits: Vec<Vec<u64>>,
) -> PyResult<(
    Vec<Bound<'py, PyBytes>>,
    Vec<String>,
    Bound<'py, PyBytes>,
    String,
)> {
    let trace_digest = parse_hex_digest(&trace_sha256).map_err(PyValueError::new_err)?;
    let rows: Vec<[u64; 7]> = l4_rows_bits
        .into_iter()
        .enumerate()
        .map(|(index, row)| {
            row.try_into().map_err(|_| {
                PyValueError::new_err(format!("L4 row {index} does not retain all seven fields"))
            })
        })
        .collect::<PyResult<_>>()?;
    let basin = generate_port_basin(
        &lane_id,
        &port_id,
        &trace_digest,
        l0_count,
        &l1_gates,
        &l2_regimes,
        l3_count,
        &rows,
    )
    .map_err(PyValueError::new_err)?;
    Ok((
        basin
            .tuple_payloads
            .iter()
            .map(|payload| PyBytes::new(py, payload))
            .collect(),
        basin.tuple_digests.iter().map(hex_digest).collect(),
        PyBytes::new(py, &basin.basin_payload),
        hex_digest(&basin.basin_digest),
    ))
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(canonical_port_basin_differential, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tuple_receipts_retain_every_exact_field() {
        let trace = sha256(b"trace");
        let rows = [[
            1.0f64.to_bits(),
            (-0.25f64).to_bits(),
            0.0f64.to_bits(),
            0.75f64.to_bits(),
            3.0f64.to_bits(),
            2.0f64.to_bits(),
            (-0.0f64).to_bits(),
        ]];
        let basin = generate_port_basin(
            "sight",
            "retina-0",
            &trace,
            1,
            &[(0, 0)],
            &["STABLE".into()],
            1,
            &rows,
        )
        .expect("basin");
        let tuple = std::str::from_utf8(&basin.tuple_payloads[0]).unwrap();
        for name in FIELD_NAMES {
            assert!(tuple.contains(name));
        }
        assert!(tuple.contains("\"B_k\":\"0/1\""));
        assert!(std::str::from_utf8(&basin.basin_payload)
            .unwrap()
            .contains("\"value_class\":\"exact_zero\""));
    }
}
