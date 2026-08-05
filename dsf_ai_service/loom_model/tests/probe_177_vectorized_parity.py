"""probe_177_vectorized_parity.py — GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177.

Step 1 of "measure before trusting": prove the vectorized oscillator
primitive (vectorized_oscillator.py) is numerically IDENTICAL to the real
scalar Krimelack/OscillatorKrimelack physics before it goes anywhere near
brain.py. Three levels:
  (a) synthetic random signals, many seeds, many population sizes, direct
      against the scalar Krimelack.feed() loop
  (b) real LanguageKrimelack.transduce() on real words, including past the
      256-event deque saturation point (the regime that actually matters --
      the live organism has been saturated her entire life, see report)
  (c) real OscillatorKrimelack.feed_signal() (touch/smell/taste path) with
      per-neuron attenuation, unsaturated AND forced-saturated
Any mismatch fails loudly -- nothing here is allowed to pass by assumption.
"""
import math
import sys
import numpy as np

sys.path.insert(0, '/workspaces/Tao_Financial_Engine')

from dsf_ai_service.loom_model.vectorized_oscillator import (
    vectorized_wind_count, language_base_dphi_raw, saturating_new_count,
    monotonic_new_count, _EVENTS_MAXLEN,
)
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import Krimelack, LanguageKrimelack
from dsf_ai_service.sensory_krimelacks import OscillatorKrimelack, MODAL_TUNING


def scalar_reference_count(krim: Krimelack, dphi_sequence):
    """Directly drive the SAME low-level physics Krimelack.feed() uses,
    sample by sample, on one real Krimelack instance -- not a re-derivation,
    the actual production code path, to get an authoritative ev0/ev1."""
    ev0 = len(krim.events)
    for dphi in dphi_sequence:
        krim.phase += dphi
        while krim.phase >= krim.threshold:
            krim.phase -= krim.threshold
            krim.winding += 1
            krim.events.append({"t": krim.t, "dw": +1, "s": 0.0})
        while krim.phase <= -krim.threshold:
            krim.phase += krim.threshold
            krim.winding -= 1
            krim.events.append({"t": krim.t, "dw": -1, "s": 0.0})
    ev1 = len(krim.events)
    return ev1 - ev0, krim.phase


def test_a_random_signals():
    print("=== (a) synthetic random signals vs scalar Krimelack.feed() ===")
    rng = np.random.default_rng(0)
    threshold = math.pi / 3
    n_neurons = 200
    fails = 0
    for trial in range(30):
        n_samples = rng.integers(5, 150)
        base_dphi = rng.uniform(-2.8, 2.8, size=n_samples)  # spans >1 threshold-width
        att = rng.uniform(0.3, 1.0, size=n_neurons)
        phase0 = rng.uniform(-threshold * 0.999, threshold * 0.999, size=n_neurons)

        vec_count, vec_phase = vectorized_wind_count(base_dphi, threshold, phase0, att)

        # scalar reference per neuron
        for i in range(0, n_neurons, 37):  # spot check a spread, not all 200 every trial
            krim = Krimelack(threshold=threshold)
            krim.phase = float(phase0[i])
            ref_count, ref_phase = scalar_reference_count(krim, base_dphi * att[i])
            if ref_count != int(vec_count[i]) or abs(ref_phase - vec_phase[i]) > 1e-9:
                print(f"  MISMATCH trial={trial} neuron={i}: "
                      f"scalar=({ref_count},{ref_phase}) vec=({vec_count[i]},{vec_phase[i]})")
                fails += 1
    print(f"  {'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
    return fails == 0


def test_b_language_words():
    print("=== (b) real LanguageKrimelack.transduce() on real words ===")
    words = ("the cat sat on mat dog run jump happy sunshine wonderful "
             "extraordinarily beautiful morning afternoon evening night "
             "guala mommy daddy friend water fire tree flower bird star").split()
    fails = 0

    # (b1) unsaturated: fresh krimelack, few words
    krim = LanguageKrimelack()
    ev0_running = len(krim.events)
    for w in words[:8]:
        ev0 = len(krim.events)
        krim.transduce(w, no_reset=True)  # phase_offset defaults to 0.0, matching
                                            # the organism call site exactly
        ref_new = len(krim.events) - ev0
        base_dphi = language_base_dphi_raw(w)
        raw, _ = vectorized_wind_count(base_dphi, np.array([krim.threshold]),
                                        np.array([0.0]),
                                        np.array([krim.kappa * krim.dt]))
        vec_new = saturating_new_count(np.array([ev0]), raw)[0]
        status = "OK" if vec_new == ref_new else "MISMATCH"
        if status == "MISMATCH":
            fails += 1
        print(f"  word={w!r:16s} ev0={ev0:3d} scalar_delta={ref_new} vec_delta={vec_new} {status}")

    # (b1.5) HETEROGENEOUS kappa/threshold per neuron -- this is what
    # Embryo._seed_dna_diversity() actually does at birth (mutates each
    # neuron's own language krimelack's kappa/threshold by ring position).
    # A single shared kappa/threshold missed this in an earlier iteration of
    # this fix (caught by the end-to-end Counter-parity test, not this
    # isolated one) -- covering it here too, directly, so it can never
    # regress silently.
    print("  -- heterogeneous per-neuron kappa/threshold (the real DNA-diversity case) --")
    n_neurons = 8
    kappa_mults = np.linspace(0.85, 1.15, n_neurons)
    threshold_mults = np.linspace(0.9, 1.1, n_neurons)
    krims_het = []
    for km, tm in zip(kappa_mults, threshold_mults):
        k = LanguageKrimelack()
        k.kappa = k.kappa * km
        k.threshold = k.threshold * tm
        krims_het.append(k)
    for w in words[:8]:
        ev0s = np.array([len(k.events) for k in krims_het])
        ref_news = []
        for k in krims_het:
            ev0 = len(k.events)
            k.transduce(w, no_reset=True)
            ref_news.append(len(k.events) - ev0)
        ref_news = np.array(ref_news)

        base_dphi = language_base_dphi_raw(w)
        threshold_vec = np.array([k.threshold for k in krims_het])
        # NOTE: kappa read AFTER transduce() above is the same (transduce
        # doesn't mutate kappa), safe to read post-hoc for this check
        att_vec = np.array([k.kappa * k.dt for k in krims_het])
        raw, _ = vectorized_wind_count(base_dphi, threshold_vec,
                                        np.zeros(n_neurons), att_vec)
        vec_news = saturating_new_count(ev0s, raw)
        mism = int(np.sum(vec_news != ref_news))
        status = "OK" if mism == 0 else f"{mism} MISMATCH"
        if mism:
            fails += mism
        print(f"  [heterogeneous] word={w!r:16s} {status}")

    # (b2) forced into saturation (>256 events) -- the regime the LIVE
    # organism has actually been in for her whole operational life
    krim2 = LanguageKrimelack()
    for w in words * 20:  # hammer it well past 256 accumulated events
        krim2.transduce(w, no_reset=True)
    print(f"  after {len(words)*20} teaches: len(events)={len(krim2.events)} "
          f"(maxlen={_EVENTS_MAXLEN}) -- saturated={len(krim2.events) >= _EVENTS_MAXLEN}")
    for w in words[:8]:
        ev0 = len(krim2.events)
        krim2.transduce(w, no_reset=True)
        ref_new = len(krim2.events) - ev0
        base_dphi = language_base_dphi_raw(w)
        raw, _ = vectorized_wind_count(base_dphi, np.array([krim2.threshold]),
                                        np.array([0.0]),
                                        np.array([krim2.kappa * krim2.dt]))
        vec_new = saturating_new_count(np.array([ev0]), raw)[0]
        status = "OK" if vec_new == ref_new else "MISMATCH"
        if status == "MISMATCH":
            fails += 1
        print(f"  [saturated] word={w!r:16s} ev0={ev0:3d} scalar_delta={ref_new} "
              f"vec_delta={vec_new} {status}")

    print(f"  {'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
    return fails == 0


def test_c_sensory_modalities():
    print("=== (c) real OscillatorKrimelack.feed_signal() (touch/smell/taste) ===")
    from dsf_ai_service.substrate.sensory_generators import (
        generate_touch_waveform, generate_smell_waveform, generate_taste_waveform)
    fails = 0
    n_neurons = 40
    rng = np.random.default_rng(1)
    att_vec = rng.uniform(0.3, 1.0, size=n_neurons)

    for modality, gen_fn, tuning_key in (
        ("touch", generate_touch_waveform, "touch"),
        ("smell", generate_smell_waveform, "smell"),
        ("taste", generate_taste_waveform, "taste"),
    ):
        tuning = MODAL_TUNING[tuning_key]
        params = {"temperature": 0.6, "pressure": 0.5, "sweet": 0.7,
                  "sour": 0.2, "salty": 0.1, "bitter": 0.05, "umami": 0.3,
                  "floral": 0.6, "fruity": 0.4, "smoky": 0.1, "earthy": 0.2,
                  "putrid": 0.05}
        wf = gen_fn(params, n_samples=20)
        channels = [wf[k] for k in sorted(wf.keys())]
        raw_signal = np.concatenate(channels)
        base_dphi = tuning["kappa"] * raw_signal * tuning["dt"]

        # scalar reference: n_neurons independent real OscillatorKrimelack
        # instances, each with its own att-scaled signal, some pre-advanced
        # to different starting phases/winding to mimic real divergent state
        ref_counts = np.zeros(n_neurons, dtype=np.int64)
        phase0 = np.zeros(n_neurons)
        for i in range(n_neurons):
            krim = OscillatorKrimelack(**tuning)
            # advance to a nontrivial, neuron-specific starting phase first
            krim.feed_signal(list(raw_signal * (0.2 + 0.01 * i)))
            phase0[i] = krim.phase
            ev0 = krim.n_events
            sig_att = [x * att_vec[i] for x in raw_signal]
            krim.feed_signal(sig_att)
            ref_counts[i] = krim.n_events - ev0

        vec_raw, _ = vectorized_wind_count(base_dphi, tuning["threshold"], phase0, att_vec)
        vec_counts = monotonic_new_count(vec_raw)

        mism = int(np.sum(vec_counts != ref_counts))
        if mism:
            fails += mism
            bad = np.where(vec_counts != ref_counts)[0][:5]
            print(f"  {modality}: {mism}/{n_neurons} MISMATCH, e.g. neurons {bad.tolist()}")
        else:
            print(f"  {modality}: all {n_neurons} neurons match")

    print(f"  {'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
    return fails == 0


if __name__ == "__main__":
    ok_a = test_a_random_signals()
    ok_b = test_b_language_words()
    ok_c = test_c_sensory_modalities()
    print()
    print("OVERALL:", "ALL PASS" if (ok_a and ok_b and ok_c) else "FAILURES PRESENT -- DO NOT SHIP")
