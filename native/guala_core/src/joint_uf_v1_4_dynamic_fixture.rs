//! Frozen independent oracle for a dynamic, irregular-clock vector occurrence
//! under the ratified declared-physical-bounds law (UF v1.4 joint lift,
//! ratified 2026-08-04).
//!
//! Expected values were computed independently from the UF v1.4 specification
//! equations (UF_Spec_v1_4_0_skeleton) in IEEE-754 binary64, outside the Rust
//! evaluator, and frozen as exact bits on 2026-08-05. The independent
//! computation and this evaluator agreed bit-for-bit on every value below.
//! This file deliberately performs no expected-value recomputation with
//! production helpers.
//!
//! Declared physical bounds for this occurrence: both coordinates bounded to
//! [-1, 1]; maximum admitted gate interval 100. The L2 normalization maxima
//! are derived from these declared bounds, so the frozen bits are specific to
//! this declaration.

use num_bigint::BigInt;
use num_rational::BigRational;

use crate::joint_uf_v1_4::{
    evaluate_with_physical_bounds, GateInterval, JointIntersampleLaw, JointUfCoordinateBounds,
    JointUfInput, JointUfPhysicalBounds, Regime,
};

fn rational(numerator: i64, denominator: i64) -> BigRational {
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

fn bits(values: &[f64]) -> Vec<u64> {
    values.iter().map(|value| value.to_bits()).collect()
}

#[test]
fn independent_dynamic_multigate_oracle_matches_every_l0_l4_family() {
    let input = JointUfInput {
        times: vec![
            rational(0, 1),
            rational(1, 2),
            rational(3, 2),
            rational(2, 1),
            rational(4, 1),
            rational(5, 1),
        ],
        fields: vec![
            vec![0.0, 0.0],
            vec![0.3, 0.0],
            vec![0.3, 0.0],
            vec![0.0, 0.4],
            vec![0.0, 0.4],
            vec![0.2, 0.1],
        ],
        relevance: vec![0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
    };
    let bounds = JointUfPhysicalBounds::new(
        vec![JointUfCoordinateBounds::new(-1.0, 1.0).unwrap(); 2],
        rational(100, 1),
    )
    .unwrap();
    let result = evaluate_with_physical_bounds(input, bounds).unwrap();
    assert_eq!(result.sev.len(), 6);
    let expected_sev = [
        [
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x3fb999999999999a,
            0x0000000000000000,
        ],
        [
            0x3fd3333333333333,
            0x0000000000000000,
            0x3fd3333333333333,
            0x0000000000000000,
            0x3fd3333333333333,
            0x3f970a3d70a3d70a,
            0x3fd3333333333333,
            0x3fc999999999999a,
            0x3fe3eb851eb851ec,
        ],
        [
            0x3fd3333333333333,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x3f947ae147ae147b,
            0x3fe0000000000000,
            0x3fd3333333333333,
            0x3fe0a3d70a3d70a4,
        ],
        [
            0x0000000000000000,
            0x3fd999999999999a,
            0xbfd3333333333333,
            0x3fd999999999999a,
            0x3fe0000000000000,
            0x3faae147ae147ae2,
            0x3fe0000000000000,
            0x3fd999999999999a,
            0x3ff0d70a3d70a3d7,
        ],
        [
            0x0000000000000000,
            0x3fd999999999999a,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x3faeb851eb851eba,
            0x3fd71355d04de190,
            0x3fe0000000000000,
            0x3fdaea600dbe8567,
        ],
        [
            0x3fc999999999999a,
            0x3fb999999999999a,
            0x3fc999999999999a,
            0xbfd3333333333334,
            0x3fd71355d04de190,
            0x3faa4fa4fa4fa4fc,
            0x0000000000000000,
            0x3fe3333333333333,
            0x3fda5d4a6f97d630,
        ],
    ];
    for (index, sev) in result.sev.iter().enumerate() {
        assert_eq!(sev.source_index, index);
        assert_eq!(
            bits(&[
                sev.field[0],
                sev.field[1],
                sev.delta_field[0],
                sev.delta_field[1],
                sev.delta_norm,
                sev.sigma,
                sev.kappa,
                sev.relevance,
                sev.deviation,
            ]),
            expected_sev[index],
        );
        assert_eq!(sev.negative_space, index == 0);
    }

    assert_eq!(result.gates.len(), 5);
    let intervals = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)];
    let projections = [
        [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
        [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        [[2, 1, 0], [1, 0, 0], [0, 0, 0]],
        [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
    ];
    let divergence = [1, 2, 1, 3, 2];
    let regimes = [
        Regime::Transitional,
        Regime::Transitional,
        Regime::Volatile,
        Regime::Transitional,
        Regime::Transitional,
    ];
    let hysteresis = [false, false, false, false, false];
    let gate_open = [true, true, true, true, true];
    let expected_gate_bits: [[u64; 21]; 5] = [
        [
            0x3fe0000000000000,
            0x3fc3eb851eb851ec,
            0x3fb3333333333334,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x3f9e659aedfabcd5,
            0x3fc699911f3fc7de,
            0x0000000000000000,
            0x3fd3eb851eb851ec,
            0x0000000000000000,
            0x3fd5d706d94cb659,
            0x3fd5d706d94cb659,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x3ff0000000000000,
            0x0000000000000000,
            0x0000000000000000,
        ],
        [
            0x3ff0000000000000,
            0x3fe247ae147ae148,
            0x3fd0000000000000,
            0x3fd003468688bb1a,
            0x3fe0000000000000,
            0x3fda99999999999a,
            0x3fc6666666666666,
            0x3fabe4f37184f01d,
            0x3fc092eb59910e63,
            0x3fc6a0bd78236471,
            0x3fe247ae147ae148,
            0x3f44da85a7447900,
            0x3fd12ab197d01550,
            0x3fd12ab197d01550,
            0xbff0000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x3fc6a0bd78236471,
            0x4000000000000000,
            0x3ff0000000000000,
            0xbf9841f19b03b09b,
        ],
        [
            0x3fe0000000000000,
            0x3fd928f5c28f5c29,
            0x3fc6666666666666,
            0x3fd7f74171e31b94,
            0xbfe0000000000000,
            0xbfc6ccccccccccce,
            0xbfb3333333333334,
            0x3fb332496ca6d44c,
            0x3fc88dea48cb7312,
            0x3f8f0018a9429fe8,
            0x3fe928f5c28f5c29,
            0x3f409a240eef1127,
            0x3fd66d90c275c36e,
            0x3fd66d90c275c36e,
            0x3ff0000000000000,
            0x3fc3de68d8449e4e,
            0x3ff0000000000000,
            0x3f8f0018a9429fe8,
            0x3ff0000000000000,
            0x4000000000000000,
            0xbf91845fad9fd533,
        ],
        [
            0x4000000000000000,
            0x3ff791a240e04531,
            0x3feccccccccccccd,
            0x3fb2919adc074266,
            0x3ff8000000000000,
            0x3ff14764d03c6e27,
            0x3fe7333333333334,
            0x3fb1fb81e51aae7b,
            0x3fbb7cd44e61b178,
            0x3fd5855f218f9f89,
            0x3fe791a240e04531,
            0x3f5ebec182997bd9,
            0x3fcbfc954520d3fa,
            0x3fcbfc954520d3fa,
            0xbff0000000000000,
            0xbfcb644a95160f1e,
            0x3ff0000000000000,
            0x3fd5855f218f9f89,
            0x4008000000000000,
            0x4000000000000000,
            0xbfae743b69bf25b0,
        ],
        [
            0x3ff0000000000000,
            0x3fdaa3d53eab2dcc,
            0x3fe199999999999a,
            0x3fdfd6f131dbf516,
            0xbff0000000000000,
            0xbff0e8acf13579be,
            0xbfd6666666666666,
            0x3fa4535b6ec139b8,
            0x3fbff3e6c84e473d,
            0x3fc7e84c4684f236,
            0x3fdaa3d53eab2dcc,
            0x3f572c530d38e185,
            0x3fd0ccc021025c6d,
            0x3fd0ccc021025c6d,
            0x3ff0000000000000,
            0x3fc67b773cae97c2,
            0x3ff0000000000000,
            0x3fc7e84c4684f236,
            0x4000000000000000,
            0x4000000000000000,
            0xbfb31877f5ec47c5,
        ],
    ];

    for (index, gate) in result.gates.iter().enumerate() {
        assert_eq!(
            gate.interval,
            GateInterval {
                first_sev: intervals[index].0,
                last_sev: intervals[index].1,
            }
        );
        assert_eq!(gate.l1.projections, projections[index]);
        assert_eq!(gate.l1.c, divergence[index]);
        assert!(!gate.l1.negative_space_gate);
        assert_eq!(gate.l2.regime, regimes[index]);
        assert_eq!(gate.l3.hysteresis, hysteresis[index]);
        assert_eq!(gate.l3.gate_open, gate_open[index]);
        assert_eq!(
            bits(&[
                gate.l1.tvr[0],
                gate.l1.tvr[1],
                gate.l1.tvr[2],
                gate.l1.drift,
                gate.l2.cv[0],
                gate.l2.cv[1],
                gate.l2.cv[2],
                gate.l2.w,
                gate.l2.s,
                gate.l2.u,
                gate.l2.chi,
                gate.l2.psi,
                gate.l3.resonance,
                gate.l3.urf,
                gate.dsf.d_k,
                gate.dsf.m_k,
                gate.dsf.r_rev_k,
                gate.dsf.u_star_k,
                gate.dsf.c_k,
                gate.dsf.p_k,
                gate.dsf.b_k,
            ]),
            expected_gate_bits[index],
        );
    }
}
