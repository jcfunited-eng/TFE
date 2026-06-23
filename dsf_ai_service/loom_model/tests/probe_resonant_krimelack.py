"""probe_resonant_krimelack.py — make resonance INTRINSIC to the krimelack.

The plain krimelack washes resonance out (food and noise both saturate to the same
event-stream coherence). Fix it the substrate-true way: a krimelack is an oscillator
with a natural frequency; make a BANK of them tuned to different frequencies (tuned
receptors / cochlea / the smell tumbler). Each receptor winds in proportion to the
input's energy at its frequency. The DISTRIBUTION of winding across the bank is the
signal's rhythm; its CONCENTRATION is resonance — reported natively by the bank, not
measured from outside the cell. Maps to embodiment: real receptors are frequency-tuned.

Test the slab: does the bank's own output separate food from noise, where the plain
krimelack could not?
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.embryo import bipolar_sense
from dsf_ai_service.sensory_krimelacks import OscillatorKrimelack


class ResonantBank:
    """Bank of frequency-tuned krimelack receptors. Each receptor responds (winds)
    to the input's energy near its natural frequency. Native outputs:
      response[f]  = winding magnitude of receptor f  (the spectrum)
      resonance    = concentration of response across the bank (coherent->high)
    """
    def __init__(self, freqs=None, dt=0.04):
        # log-spaced natural frequencies (tuned receptors) — denser bank
        self.freqs = freqs if freqs is not None else np.geomspace(0.3, 12.0, 48)
        self.dt = dt
        # one oscillator-krimelack per receptor, kappa large so it winds on its band
        self.receptors = [OscillatorKrimelack(omega_0=float(f), kappa=80.0, dt=dt)
                           for f in self.freqs]

    def feed(self, signal):
        signal = np.asarray(signal, dtype=float)
        n = len(signal)
        t = np.arange(n) * self.dt
        responses = []
        for f, r in zip(self.freqs, self.receptors):
            # bandpass-by-resonance: correlate signal with the receptor's own
            # oscillation (in-phase + quadrature) -> energy at this frequency.
            # This IS the receptor's driven response; winding tracks it.
            ip = np.sum(signal * np.cos(2 * np.pi * f * t))
            qp = np.sum(signal * np.sin(2 * np.pi * f * t))
            energy = np.hypot(ip, qp) / max(n, 1)
            responses.append(energy)
        return np.array(responses)

    def resonance(self, signal):
        resp = self.feed(signal)
        tot = resp.sum()
        if tot <= 0:
            return 0.0, resp
        # tonality = 1 - spectral flatness (geomean/mean). Coherent/tonal -> flatness
        # low -> tonality high; white noise -> flatness ~1 -> tonality ~0.
        p = resp + 1e-12
        flatness = float(np.exp(np.mean(np.log(p))) / np.mean(p))
        return 1.0 - flatness, resp


FOOD = {
    "apple": {"taste": {"sweet": 0.65, "sour": 0.55, "bitter": 0.05},
              "smell": {"fruity": 0.85, "fresh": 0.45, "floral": 0.20}},
    "pear":  {"taste": {"sweet": 0.82, "sour": 0.02, "bitter": 0.12},
              "smell": {"sweet": 0.60, "floral": 0.45, "fruity": 0.50}},
    "lemon": {"taste": {"sour": 0.9, "sweet": 0.2, "bitter": 0.2},
              "smell": {"fresh": 0.8, "fruity": 0.6, "sour": 0.5}},
    "bread": {"taste": {"sweet": 0.3, "umami": 0.5, "salty": 0.3},
              "smell": {"earthy": 0.6, "sweet": 0.4, "smoky": 0.2}},
}


def main():
    bank = ResonantBank()
    print(f"resonant bank: {len(bank.freqs)} tuned receptors, freqs "
          f"{bank.freqs[0]:.2f}..{bank.freqs[-1]:.2f}\n")
    print(f"{'case':>8} {'bank_resonance':>14}  peak-receptors")
    vals = {}
    for name, rec in FOOD.items():
        sig = np.concatenate([bipolar_sense(rec.get("taste", {}), "taste"),
                              bipolar_sense(rec.get("smell", {}), "smell")])
        r, resp = bank.resonance(sig)
        vals[name] = r
        top = np.argsort(resp)[-3:][::-1]
        print(f"{name:>8} {r:>14.3f}  freqs={[round(float(bank.freqs[i]),1) for i in top]}")
    rng = np.random.default_rng(0)
    rn, _ = bank.resonance(rng.standard_normal(200 * 2) * 0.3)
    vals["NOISE"] = rn
    print(f"{'NOISE':>8} {rn:>14.3f}")

    food_min = min(vals[n] for n in FOOD)
    print(f"\nfood resonance: {food_min:.3f}..{max(vals[n] for n in FOOD):.3f}   noise: {vals['NOISE']:.3f}")
    sep = food_min - vals["NOISE"]
    print(f"separation (food_min - noise) = {sep:+.3f}  -> "
          f"{'SLAB HOLDS (bank carries resonance)' if sep > 0.05 else 'NOT separable by bank'}")


if __name__ == "__main__":
    main()
