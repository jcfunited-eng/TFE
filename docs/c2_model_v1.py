"""C-2 rebuild testbed v1 — Eve, 2026-07-04.
Question (pre-registered Q1): can per-neuron differentiation derived from
REAL per-neuron state (ring position; RNG for neuron identity BANNED)
survive the inner product and make population voting ADD over the
single-neuron ceiling? Failure precedent: global phase offsets cancel
in |<t,b>| (6/22 V1.c). Candidate here: ring-position-derived component
MASKS + attenuation profiles (non-unitary => cannot cancel).
Encoding: krimelack-like winding — characters drive 6 modality-frequency
oscillators, phases ACCUMULATE (integration dynamics, not a lookup);
polarity = 7th dim. Cue degradation: phase jitter + one modality dropped
(models transduction variability; without it the task is trivial).
"""
import numpy as np

D = 7            # 6 modality phases + polarity
K_MASK = 4       # components each neuron attends (subspace per neuron)

def encode(word, jitter=0.0, drop_mod=None, rng=None):
    # winding: each char advances 6 oscillators at modality-specific rates
    phases = np.zeros(6)
    rates = np.array([1.0, 1.618, 2.414, 3.303, 4.236, 5.192])  # incommensurate
    for i, ch in enumerate(word):
        drive = (ord(ch) % 97) / 97.0 * 2*np.pi
        phases += rates * drive / (1.0 + 0.1*i)   # early chars weigh more (no reset)
    if jitter > 0 and rng is not None:
        phases = phases + rng.normal(0, jitter, 6)
    v = np.exp(1j*phases)
    if drop_mod is not None:
        v[drop_mod] = 0.0
    pol = np.array([1.0 + 0j])
    return np.concatenate([v, pol])

def neuron_profiles(N):
    # REAL-state analog: ring position only. No RNG.
    r = np.arange(N) / N * 2*np.pi
    gains = 0.5 + 0.5*np.cos(r[:,None] + np.arange(D)[None,:]*2*np.pi/D)  # (N,D)
    order = np.argsort(-gains, axis=1)
    masks = np.zeros((N, D))
    for n in range(N):
        masks[n, order[n,:K_MASK]] = 1.0
    return gains*masks   # combined non-unitary per-neuron transform (N,D)

def run(n_concepts=100, N=64, jitter=0.35, trials=200, seed=7):
    rng = np.random.default_rng(seed)   # RNG for CUE NOISE ONLY (transduction), not neuron identity
    words = [f"c{idx}w{(idx*37)%91}" for idx in range(n_concepts)]
    prof = neuron_profiles(N)                                   # (N,D)
    stored = np.stack([encode(w) for w in words])               # (C,D) clean writes
    B = prof[:,None,:] * stored[None,:,:]                       # (N,C,D) per-neuron bindings
    single_hits = np.zeros(N); pop_hits = 0; unanimous = 0
    for _ in range(trials):
        c = rng.integers(n_concepts)
        cue = encode(words[c], jitter=jitter, drop_mod=int(rng.integers(6)), rng=rng)
        q = prof * cue[None,:]                                  # (N,D)
        scores = np.abs(np.einsum('nd,ncd->nc', np.conj(q), B)) # (N,C)
        votes = scores.argmax(axis=1)
        single_hits += (votes == c)
        counts = np.bincount(votes, minlength=n_concepts)
        pop_hits += (counts.argmax() == c)
        unanimous += (len(np.unique(votes)) == 1)
    print(f"N={N} C={n_concepts} jitter={jitter} trials={trials}")
    print(f"  single-neuron acc: mean {single_hits.mean()/trials:.3f}  best {single_hits.max()/trials:.3f}  worst {single_hits.min()/trials:.3f}")
    print(f"  population vote  : {pop_hits/trials:.3f}")
    print(f"  unanimity rate   : {unanimous/trials:.3f}  (degeneracy check: 1.0 = the 6/22 trap)")
    return single_hits.mean()/trials, single_hits.max()/trials, pop_hits/trials, unanimous/trials

if __name__ == "__main__":
    print("== BASELINE: no differentiation (all neurons identical profile) ==")
    import types
    g = neuron_profiles(64); gsave = g.copy()
    # monkeypatch-free baseline: run with N=1 replicated conceptually == single neuron
    run(N=1, jitter=0.35)
    print("\n== CANDIDATE: ring-position masks+gains, jitter sweep ==")
    for j in (0.2, 0.35, 0.5, 0.7):
        run(N=64, jitter=j)
    print("\n== scale check ==")
    run(N=256, jitter=0.5)
