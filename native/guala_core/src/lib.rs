//! guala_core -- native (Rust) ports of the GualaLoom organism hot-path
//! kernels, verified hot by tools/bench_organism_core.py (2026-07-16):
//!
//!   1. krim_feed        -- per-sample oscillator winding loop
//!                          (dsf_ai_service/substrate/krimelack.py::Krimelack.step/feed_signal
//!                           AND dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py::Krimelack.feed
//!                           -- identical math, one implementation)
//!   2. word_signal /    -- LanguageKrimelack.transduce's char->signal expansion
//!      lang_transduce      + feed, one FFI crossing per word
//!   3. biquad_bandpass  -- GL_MDL_AUDITORY_CORTEX bandpass_filter biquad loop
//!   4. cochlear_feed    -- full CochlearBankKrimelack.feed_signal (6 bands x
//!                          (biquad + normalize + krimelack) + stable t-sort)
//!   5. fovea_feed       -- visual_krimelack.py::AdaptingFoveaKrimelack.tick loop
//!   6. fingerprint      -- gualaloom_v4_krimelack_dna.py::Krimelack.fingerprint
//!   7. compute_dsf      -- gualaloom_v4_uf_kernel.py::compute_dsf event statistics
//!   8. map_inject       -- loom_model/neuron.py::_map_inject Gaussian injection
//!   9. psi_settle       -- loom_model/neuron.py::PsiLattice.settle imaginary-time
//!                          evolution (16-dim complex, n_steps iterations)
//!
//! Design rules:
//!   - EXACT Python operation order is preserved (e.g. `(omega_0 + kappa*s)
//!     - omega_0` is NOT simplified to `kappa*s` -- they differ in floating
//!     point). Differential tests in tests/test_differential.py hold these
//!     to bit-exactness where the Python side is plain arithmetic, and to
//!     <=1e-9 relative where the Python side goes through BLAS/pairwise
//!     summation (psi_settle norms).
//!   - Lock-free by construction: every kernel is a pure function of its
//!     arguments; no shared state, no Mutex, no channel anywhere. All Python
//!     object state stays owned by Python; kernels take plain values.
//!   - The GIL is RELEASED (py.allow_threads) around every kernel loop, so
//!     concurrent feeder threads can actually run in parallel -- this is the
//!     structural fix for the 0.2-0.4x thread scaling the baseline measured.

use num_complex::Complex64;
use pyo3::prelude::*;

mod auditory;
mod auditory_reachability;

const F_PI: f64 = std::f64::consts::PI;

// ---------------------------------------------------------------------------
// 1. krim_feed -- oscillator winding loop
//    Exact port of Krimelack.feed (v4 krimelack_dna) / Krimelack.step+feed_signal
//    (substrate/krimelack.py). Same op order:
//      omega  = omega_0 + kappa * s
//      dphi   = (omega - omega_0) * dt
//      phase += dphi; t += dt
//      while phase >= threshold  { phase -= threshold; winding += 1; event(+1) }
//      while phase <= -threshold { phase += threshold; winding -= 1; event(-1) }
// ---------------------------------------------------------------------------

#[inline]
fn krim_feed_impl(
    mut phase: f64,
    mut t: f64,
    mut winding: i64,
    mut n_events: i64,
    omega_0: f64,
    kappa: f64,
    dt: f64,
    threshold: f64,
    signal: &[f64],
) -> (f64, f64, i64, i64, Vec<(f64, i64, f64)>) {
    let mut events: Vec<(f64, i64, f64)> = Vec::new();
    for &s in signal {
        let omega = omega_0 + kappa * s;
        let dphi = (omega - omega_0) * dt;
        phase += dphi;
        t += dt;
        while phase >= threshold {
            phase -= threshold;
            winding += 1;
            events.push((t, 1, s));
            n_events += 1;
        }
        while phase <= -threshold {
            phase += threshold;
            winding -= 1;
            events.push((t, -1, s));
            n_events += 1;
        }
    }
    (phase, t, winding, n_events, events)
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn krim_feed(
    py: Python<'_>,
    phase: f64,
    t: f64,
    winding: i64,
    n_events: i64,
    omega_0: f64,
    kappa: f64,
    dt: f64,
    threshold: f64,
    signal: Vec<f64>,
) -> (f64, f64, i64, i64, Vec<(f64, i64, f64)>) {
    py.allow_threads(|| {
        krim_feed_impl(
            phase, t, winding, n_events, omega_0, kappa, dt, threshold, &signal,
        )
    })
}

// ---------------------------------------------------------------------------
// 2. word_signal / lang_transduce
//    Exact port of LanguageKrimelack.transduce's signal construction:
//      vowels "aeiouy": base = -0.3 + (ord(c) - ord('a'))/25.0 * 0.5
//      alpha consonant: base = +0.4 + (ord(c) - ord('a'))/25.0 * 0.4
//      else:            base = 0.0
//      4 samples/char:  base + 0.05 * sin(i + j*pi/4)
// ---------------------------------------------------------------------------

fn word_signal_impl(word_lower: &str) -> Vec<f64> {
    let mut sig: Vec<f64> = Vec::with_capacity(word_lower.chars().count() * 4);
    for (i, c) in word_lower.chars().enumerate() {
        let base = if matches!(c, 'a' | 'e' | 'i' | 'o' | 'u' | 'y') {
            -0.3 + (c as u32 as f64 - 'a' as u32 as f64) / 25.0 * 0.5
        } else if c.is_alphabetic() {
            0.4 + (c as u32 as f64 - 'a' as u32 as f64) / 25.0 * 0.4
        } else {
            0.0
        };
        for j in 0..4u32 {
            sig.push(base + 0.05 * ((i as f64) + (j as f64) * F_PI / 4.0).sin());
        }
    }
    sig
}

/// word must already be lowercased by the caller (Python's str.lower is
/// Unicode-aware; the wrapper passes word.lower() so both sides agree).
#[pyfunction]
fn word_signal(py: Python<'_>, word: &str) -> Vec<f64> {
    py.allow_threads(|| word_signal_impl(word))
}

/// One-FFI-crossing transduce: build the char signal, then run the winding
/// loop starting from phase_offset (transduce sets self.phase = phase_offset
/// before feeding). omega_0 here is the EFFECTIVE omega for this call
/// (omega_override if the caller had one, else the krimelack's omega_0) --
/// mathematically inert (it cancels in dphi) but kept for exactness.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn lang_transduce(
    py: Python<'_>,
    word: &str,
    phase_offset: f64,
    t: f64,
    winding: i64,
    n_events: i64,
    omega_0: f64,
    kappa: f64,
    dt: f64,
    threshold: f64,
) -> (f64, f64, i64, i64, Vec<(f64, i64, f64)>) {
    py.allow_threads(|| {
        let sig = word_signal_impl(word);
        krim_feed_impl(
            phase_offset, t, winding, n_events, omega_0, kappa, dt, threshold, &sig,
        )
    })
}

// ---------------------------------------------------------------------------
// 3. biquad_bandpass -- exact port of GL_MDL_AUDITORY_CORTEX bandpass_filter
// ---------------------------------------------------------------------------

fn biquad_bandpass_impl(signal: &[f64], center_hz: f64, bandwidth_hz: f64, sample_rate: f64) -> Vec<f64> {
    let n = signal.len();
    let omega = 2.0 * F_PI * center_hz / sample_rate;
    let q = center_hz / bandwidth_hz.max(1.0);
    let alpha = omega.sin() / (2.0 * q);
    let b0 = alpha;
    let b1 = 0.0;
    let b2 = -alpha;
    let a0 = 1.0 + alpha;
    let a1 = -2.0 * omega.cos();
    let a2 = 1.0 - alpha;
    let (b0, b1, b2) = (b0 / a0, b1 / a0, b2 / a0);
    let (a1, a2) = (a1 / a0, a2 / a0);

    let mut y = vec![0.0f64; n];
    let (mut x1, mut x2, mut y1, mut y2) = (0.0f64, 0.0f64, 0.0f64, 0.0f64);
    for i in 0..n {
        let x = signal[i];
        y[i] = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1;
        x1 = x;
        y2 = y1;
        y1 = y[i];
    }
    y
}

#[pyfunction]
#[pyo3(signature = (signal, center_hz, bandwidth_hz, sample_rate=200.0))]
fn biquad_bandpass(
    py: Python<'_>,
    signal: Vec<f64>,
    center_hz: f64,
    bandwidth_hz: f64,
    sample_rate: f64,
) -> Vec<f64> {
    py.allow_threads(|| biquad_bandpass_impl(&signal, center_hz, bandwidth_hz, sample_rate))
}

// ---------------------------------------------------------------------------
// 4. cochlear_feed -- full CochlearBankKrimelack.feed_signal:
//    for each band in COCHLEAR_BANDS (iterated in sorted-NAME order to match
//    Python's `for _band_name, band_data in sorted(cochlear.items())`):
//      filtered = bandpass(signal, freq, bw, 200)
//      norm = max(|filtered|); if norm > 1e-9: filtered /= norm
//      kappa = 100.0 + log10(freq/50) * 80
//      krimelack(omega_0=2.0, kappa, dt=0.04, threshold=pi/3) fed from zero state
//      total_winding += winding; events extended in band order
//    then events stable-sorted by t (Python list.sort is stable; ties across
//    bands keep sorted-name band order).
// ---------------------------------------------------------------------------

// (name, freq, bandwidth) in sorted-by-name order:
// high, low, low_mid, mid, mid_high, very_low
const COCHLEAR_BANDS_NAME_SORTED: [(f64, f64); 6] = [
    (92.0, 15.0),  // high
    (18.0, 8.0),   // low
    (35.0, 15.0),  // low_mid
    (55.0, 20.0),  // mid
    (75.0, 20.0),  // mid_high
    (8.0, 4.0),    // very_low
];

fn cochlear_feed_impl(signal: &[f64]) -> (i64, Vec<(f64, i64, f64)>) {
    let mut total_winding: i64 = 0;
    let mut all_events: Vec<(f64, i64, f64)> = Vec::new();
    for &(freq, bw) in COCHLEAR_BANDS_NAME_SORTED.iter() {
        let mut filtered = biquad_bandpass_impl(signal, freq, bw, 200.0);
        // norm = abs(filtered).max()  (0.0 for empty)
        let norm = filtered.iter().fold(0.0f64, |m, &v| m.max(v.abs()));
        if norm > 1e-9 {
            for v in filtered.iter_mut() {
                *v /= norm;
            }
        }
        let kappa = 100.0 + ((freq / 50.0).log10() * 80.0);
        let (_phase, _t, winding, _n_events, events) = krim_feed_impl(
            0.0,
            0.0,
            0,
            0,
            2.0,
            kappa,
            0.04,
            F_PI / 3.0,
            &filtered,
        );
        total_winding += winding;
        all_events.extend(events);
    }
    // Python: all_events.sort(key=lambda e: e["t"]) -- stable by t only.
    all_events.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    (total_winding, all_events)
}

#[pyfunction]
fn cochlear_feed(py: Python<'_>, signal: Vec<f64>) -> (i64, Vec<(f64, i64, f64)>) {
    py.allow_threads(|| cochlear_feed_impl(&signal))
}

// ---------------------------------------------------------------------------
// 5. fovea_feed -- exact port of VisualKrimelack.feed_signal's loop over
//    AdaptingFoveaKrimelack.tick(intensity, t=i*dt):
//      kappa_eff = kappa_max * adapt_state
//      omega = omega_0 + kappa_eff * intensity
//      phase += omega * DT
//      while phase >= 2pi  { winding += 1; phase -= 2pi; event(+1) }
//      while phase <= -2pi { winding -= 1; phase += 2pi; event(-1) }
//      if intensity > 0.1: adapt -= adapt * (intensity/adapt_tau) * DT
//      else:               adapt += (1 - adapt) * DT / recover_tau
//      adapt = clamp(adapt, 0.05, 1.0)
// ---------------------------------------------------------------------------

#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(signature = (phase, winding_count, adapt_state, signal, omega_0=5.0, kappa_max=50.0, adapt_tau=12.0, recover_tau=60.0, dt=0.02))]
fn fovea_feed(
    py: Python<'_>,
    phase: f64,
    winding_count: i64,
    adapt_state: f64,
    signal: Vec<f64>,
    omega_0: f64,
    kappa_max: f64,
    adapt_tau: f64,
    recover_tau: f64,
    dt: f64,
) -> (f64, i64, f64, Vec<(f64, i64, f64)>) {
    py.allow_threads(|| {
        let winding_phase = 2.0 * F_PI;
        let mut phase = phase;
        let mut winding = winding_count;
        let mut adapt = adapt_state;
        let mut events: Vec<(f64, i64, f64)> = Vec::new();
        for (i, &intensity) in signal.iter().enumerate() {
            let t = (i as f64) * dt;
            let kappa_eff = kappa_max * adapt;
            let omega = omega_0 + kappa_eff * intensity;
            phase += omega * dt;
            while phase >= winding_phase {
                winding += 1;
                phase -= winding_phase;
                events.push((t, 1, intensity));
            }
            while phase <= -winding_phase {
                winding -= 1;
                phase += winding_phase;
                events.push((t, -1, intensity));
            }
            if intensity > 0.1 {
                adapt -= adapt * (intensity / adapt_tau) * dt;
            } else {
                adapt += (1.0 - adapt) * dt / recover_tau;
            }
            adapt = adapt.min(1.0).max(0.05);
        }
        (phase, winding, adapt, events)
    })
}

// ---------------------------------------------------------------------------
// 6. fingerprint -- exact port of v4 Krimelack.fingerprint:
//      n == 0 -> (0, 0, 0.0, 0, 0, 0, 0)
//      mean_s = sum(s)/n                (sequential left-to-right sum)
//      t_max  = max(t)
//      qi = min(3, int(t / (t_max/4 + 1e-9)))   (int() truncates toward 0)
// ---------------------------------------------------------------------------

#[pyfunction]
fn fingerprint(
    py: Python<'_>,
    ts: Vec<f64>,
    ss: Vec<f64>,
    winding: i64,
) -> (i64, i64, f64, i64, i64, i64, i64) {
    py.allow_threads(|| {
        let n = ss.len();
        if n == 0 {
            return (0, 0, 0.0, 0, 0, 0, 0);
        }
        let mut sum_s = 0.0f64;
        for &s in &ss {
            sum_s += s;
        }
        let mean_s = sum_s / n as f64;
        let mut t_max = f64::NEG_INFINITY;
        for &t in &ts {
            if t > t_max {
                t_max = t;
            }
        }
        let mut q = [0i64; 4];
        let denom = t_max / 4.0 + 1e-9;
        for &t in &ts {
            let qi = ((t / denom).trunc() as i64).min(3);
            // Python min(3, int(...)) with t >= 0 always lands in [0, 3];
            // clamp negatives defensively (cannot occur for krimelack t).
            let qi = qi.max(0) as usize;
            q[qi] += 1;
        }
        (n as i64, winding, mean_s, q[0], q[1], q[2], q[3])
    })
}

// ---------------------------------------------------------------------------
// 7. compute_dsf -- exact port of gualaloom_v4_uf_kernel.compute_dsf.
//    Takes the event stream as parallel arrays (t, dw, s); returns the 8
//    DSF floats (D_k, M_k, R_rev, U_star, C_k, P_k, B_k, S_UF).
// ---------------------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (ts, dws, ss, atlas_similarity=0.0))]
fn compute_dsf(
    py: Python<'_>,
    ts: Vec<f64>,
    dws: Vec<f64>,
    ss: Vec<f64>,
    atlas_similarity: f64,
) -> (f64, f64, f64, f64, f64, f64, f64, f64) {
    py.allow_threads(|| {
        let n = dws.len();
        if n == 0 {
            return (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0);
        }
        let nf = n as f64;

        // D_k: net direction (sequential sum, matching Python sum())
        let mut net_w = 0.0f64;
        for &dw in &dws {
            net_w += dw;
        }
        let mut d_k = net_w / nf.max(1.0);
        d_k = d_k.max(-1.0).min(1.0);

        // M_k: mean of consecutive s diffs, scaled x2, clamped
        let m_k = if n >= 2 {
            let mut sum_d = 0.0f64;
            for i in 0..n - 1 {
                sum_d += ss[i + 1] - ss[i];
            }
            let m = sum_d / (n - 1) as f64;
            (m * 2.0).max(-1.0).min(1.0)
        } else {
            0.0
        };

        // R_rev: reversal rate
        let mut reversals = 0.0f64;
        for i in 0..n.saturating_sub(1) {
            if dws[i] * dws[i + 1] < 0.0 {
                reversals += 1.0;
            }
        }
        let r_rev = reversals / ((n as i64 - 1).max(1) as f64);

        // U_star: timing-variance freedom
        let u_star = if n >= 2 {
            let mut t_min = f64::INFINITY;
            let mut t_max = f64::NEG_INFINITY;
            for &t in &ts {
                if t < t_min {
                    t_min = t;
                }
                if t > t_max {
                    t_max = t;
                }
            }
            let t_range = t_max - t_min;
            if t_range > 0.0 {
                let expected_step = t_range / (n - 1) as f64;
                let mut var_sum = 0.0f64;
                for i in 0..n - 1 {
                    let a = ts[i + 1] - ts[i];
                    let d = a - expected_step;
                    var_sum += d * d;
                }
                let var = var_sum / (n - 1) as f64;
                (var.sqrt() / expected_step).min(1.0)
            } else {
                0.0
            }
        } else {
            1.0
        };

        // C_k: atlas similarity clamp
        let c_k = atlas_similarity.max(0.0).min(1.0);

        // P_k: event density
        let p_k = if n >= 2 {
            let t_range = ts[n - 1] - ts[0];
            (nf / (t_range * 50.0).max(1.0)).min(1.0)
        } else {
            0.0
        };

        // B_k: winding-direction consistency
        let mut pos = 0i64;
        let mut neg = 0i64;
        for &dw in &dws {
            if dw > 0.0 {
                pos += 1;
            }
            if dw < 0.0 {
                neg += 1;
            }
        }
        let b_k = (pos - neg).abs() as f64 / (pos + neg).max(1) as f64;

        let s_uf = (1.0 - u_star) * b_k;

        (d_k, m_k, r_rev, u_star, c_k, p_k, b_k, s_uf)
    })
}

// ---------------------------------------------------------------------------
// 8. map_inject -- exact port of loom_model/neuron.py::_map_inject:
//      chi_mode = chi % dim (Python semantics; chi is abs(winding) >= 0)
//      dist = min(|i - chi_mode|, dim - |i - chi_mode|)
//      gauss = exp(-dist^2 / (2 sigma^2))
//      amplitude = B_k + 0.10
// ---------------------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (chi, b_k, dim=16, sigma=1.0))]
fn map_inject(py: Python<'_>, chi: i64, b_k: f64, dim: i64, sigma: f64) -> Vec<f64> {
    py.allow_threads(|| {
        let chi_mode = chi.rem_euclid(dim); // Python % semantics
        let amplitude = b_k + 0.10;
        let mut out = Vec::with_capacity(dim as usize);
        for i in 0..dim {
            let ad = (i - chi_mode).abs();
            let dist = ad.min(dim - ad) as f64;
            out.push((-(dist * dist) / (2.0 * sigma * sigma)).exp() * amplitude);
        }
        out
    })
}

// ---------------------------------------------------------------------------
// 9. psi_settle -- port of PsiLattice.settle.
//    H is real by construction (law-field diagonal from |psi_i|^2 with
//    abs = hypot, and the rank-1 injection outer product of a real vector).
//    Python evolves psi with numpy (BLAS matmul + pairwise-sum norm), so
//    this port is equal only to within summation-order rounding (~1e-14);
//    the differential test asserts <=1e-9 relative.
//      law_weights: the weights of laws whose family is symmetry.basic or
//      consistency.basic, in list order (both families apply the identical
//      diagonal formula; applied sequentially to match rounding).
// ---------------------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (psi, injection, law_weights, n_steps=30, eps=0.25))]
fn psi_settle(
    py: Python<'_>,
    psi: Vec<Complex64>,
    injection: Vec<f64>,
    law_weights: Vec<f64>,
    n_steps: usize,
    eps: f64,
) -> Vec<Complex64> {
    py.allow_threads(|| {
        let dim = psi.len();
        let mut psi = psi;

        // Diagonal law-field terms (uses PRE-settle psi, like Python: H is
        // built once from the psi copy before evolution starts).
        let mut diag = vec![0.0f64; dim];
        for &w in &law_weights {
            for i in 0..dim {
                let p = psi[i].re.hypot(psi[i].im).powi(2); // abs(psi)**2, hypot like CPython/numpy
                diag[i] -= w * p;
            }
        }

        // Rank-1 injection term: H -= inj_norm * |v><v|, v = injection/||injection||.
        // norm: sqrt of sequential sum of squares (numpy pairwise-sum order
        // differences are within test tolerance at dim<=16).
        let mut inj_sq = 0.0f64;
        for &v in &injection {
            inj_sq += v * v;
        }
        let inj_norm = inj_sq.sqrt();
        let mut h = vec![vec![0.0f64; dim]; dim];
        for (i, row) in h.iter_mut().enumerate() {
            row[i] = diag[i];
        }
        if inj_norm > 1e-9 {
            for i in 0..dim {
                let vi = injection[i] / inj_norm;
                for j in 0..dim {
                    let vj = injection[j] / inj_norm;
                    h[i][j] -= inj_norm * (vi * vj);
                }
            }
        }

        // Imaginary-time evolution: psi <- (I - eps*H) psi, renormalize.
        let uniform = Complex64::new(1.0 / (dim as f64).sqrt(), 0.0);
        let mut next = vec![Complex64::new(0.0, 0.0); dim];
        for _ in 0..n_steps {
            for i in 0..dim {
                let mut acc = Complex64::new(0.0, 0.0);
                let row = &h[i];
                for j in 0..dim {
                    acc += Complex64::new(row[j] * psi[j].re, row[j] * psi[j].im);
                }
                next[i] = psi[i] - Complex64::new(eps * acc.re, eps * acc.im);
            }
            let mut norm_sq = 0.0f64;
            for v in &next {
                norm_sq += v.re * v.re + v.im * v.im;
            }
            let norm = norm_sq.sqrt();
            if norm < 1e-12 {
                for v in psi.iter_mut() {
                    *v = uniform;
                }
            } else {
                for i in 0..dim {
                    psi[i] = Complex64::new(next[i].re / norm, next[i].im / norm);
                }
            }
        }
        psi
    })
}

// ---------------------------------------------------------------------------
// module
// ---------------------------------------------------------------------------

#[pymodule]
fn guala_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    auditory::register(m)?;
    auditory_reachability::register(m)?;
    m.add_function(wrap_pyfunction!(krim_feed, m)?)?;
    m.add_function(wrap_pyfunction!(word_signal, m)?)?;
    m.add_function(wrap_pyfunction!(lang_transduce, m)?)?;
    m.add_function(wrap_pyfunction!(biquad_bandpass, m)?)?;
    m.add_function(wrap_pyfunction!(cochlear_feed, m)?)?;
    m.add_function(wrap_pyfunction!(fovea_feed, m)?)?;
    m.add_function(wrap_pyfunction!(fingerprint, m)?)?;
    m.add_function(wrap_pyfunction!(compute_dsf, m)?)?;
    m.add_function(wrap_pyfunction!(map_inject, m)?)?;
    m.add_function(wrap_pyfunction!(psi_settle, m)?)?;
    m.add("__version__", "0.1.0")?;
    Ok(())
}
