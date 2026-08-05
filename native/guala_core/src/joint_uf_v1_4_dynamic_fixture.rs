//! Frozen independent oracle for a dynamic, irregular-clock vector occurrence.
//!
//! Expected values were calculated directly from UF v1.4 equations outside
//! the Rust evaluator and frozen as IEEE-754 bits.  This file deliberately
//! performs no expected-value recomputation with production helpers.

use num_bigint::BigInt;
use num_rational::BigRational;

use crate::joint_uf_v1_4::{evaluate, GateInterval, JointIntersampleLaw, JointUfInput, Regime};

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

    let result = evaluate(input).unwrap();
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
        Regime::Degenerate,
        Regime::Transitional,
    ];
    let hysteresis = [false, false, true, false, true];
    let gate_open = [true, true, false, true, false];
    let expected_gate_bits: [[u64; 21]; 5] = [
        [
            0x3fe0000000000000,
            0x3fc3eb851eb851ec,
            0x3fb3333333333334,
            0x0000000000000000,
            0xbfe0000000000000,
            0xbfdc8f21300cf2b0,
            0xbfd428f5c28f5c29,
            0x3fd955e0411e8650,
            0x3fde3abbf8ca6434,
            0x0000000000000000,
            0x3fd3eb851eb851ec,
            0x3fe0ad29d4a05327,
            0x3fe27de4c9ea8e7b,
            0x3fe27de4c9ea8e7b,
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
            0x0000000000000000,
            0xbf9f587967359160,
            0xbfc1eb851eb851ec,
            0x3fe73fe5f3ca46d2,
            0x3fd8c32c32fc08f7,
            0x3fd565486a90ccaa,
            0x3fe247ae147ae148,
            0x3fb9d18d7028dfae,
            0x3fdc54ae79dfde3d,
            0x3fdc54ae79dfde3d,
            0xbff0000000000000,
            0x0000000000000000,
            0x0000000000000000,
            0x3fd565486a90ccaa,
            0x4000000000000000,
            0x3ff0000000000000,
            0xbfa5b97db2449e6e,
        ],
        [
            0x3fe0000000000000,
            0x3fd928f5c28f5c29,
            0x3fc6666666666666,
            0x3fd7f74171e31b94,
            0xbfe0000000000000,
            0xbfcab7dbf9b37efa,
            0xbfcb851eb851eb86,
            0x3ff0000000000000,
            0x3fe46036be39e27c,
            0x3fd00ec5fcd5d39c,
            0x3fe928f5c28f5c29,
            0x3fda4148755b4eeb,
            0x3fe5184b3218ecd3,
            0x0000000000000000,
            0xbff0000000000000,
            0xbfd3ad935fea9f84,
            0x0000000000000000,
            0x3fd6752c633c3a02,
            0x3ff0000000000000,
            0x0000000000000000,
            0xbfbb337f052d00c1,
        ],
        [
            0x4000000000000000,
            0x3ff791a240e04531,
            0x3feccccccccccccd,
            0x3fb2919adc074266,
            0x3ff0000000000000,
            0x3febe0d2a20bfc8f,
            0x3fe051eb851eb852,
            0x3fedf9f024ee076b,
            0x3fe753500c4f57cf,
            0x3fd871977474c376,
            0x3fe791a240e04531,
            0x3ff0000000000000,
            0x3fe69db0e49a32b3,
            0x3fe69db0e49a32b3,
            0x3ff0000000000000,
            0x3ff2640410c510e9,
            0x3ff0000000000000,
            0x3fd871977474c376,
            0x4008000000000000,
            0x4000000000000000,
            0xbfb9cbccb5e1db4a,
        ],
        [
            0x3ff0000000000000,
            0x3fdaa3d53eab2dcc,
            0x3fe199999999999a,
            0x3fdfd6f131dbf516,
            0x0000000000000000,
            0xbfc7c21d017bdbb4,
            0x3fc47ae147ae147c,
            0x3fe0f0efccaf9ae3,
            0x3fd61597487b9acc,
            0x3fe0000000000000,
            0x3fdaa3d53eab2dcc,
            0x3fc61321d57c8a90,
            0x3fd81145d396156f,
            0x0000000000000000,
            0xbff0000000000000,
            0xbff69db0e49a32b3,
            0x3ff0000000000000,
            0x3fe3333333333333,
            0x4000000000000000,
            0x4000000000000000,
            0xbfc8325493ff5c28,
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
