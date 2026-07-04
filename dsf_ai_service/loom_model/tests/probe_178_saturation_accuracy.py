"""probe_178_saturation_accuracy.py — GL-CMD-LANGUAGE-SATURATION-ROOTCAUSE-
EVE-20260704-178.

L1/L2: measure exactly how fast the language channel's live contribution
collapses to zero as real teaching accumulates (matching the LIVE organism's
actual mechanism -- experience_moment() via remember(), single feed per
word, no_reset=True, event_count observable, real per-neuron kappa/
threshold heterogeneity).

L3(b) A/B: candidate fix (real n_events counter on Krimelack, mirroring the
sensory adapters' existing GL-CMD-SENSE-REPAIR pattern) vs the current
(len(deque) fallback) behavior -- compared cleanly on the SAME embryo state
at the SAME checkpoint: recall_fast() hardcodes the OLD (len-based,
saturating) computation (built in -177, unmodified since), while recall()
now automatically uses the NEW n_events counter once it exists on the
class (_unwrapped_deltas's hasattr() dispatch picks it up with no other
code change) -- a natural, already-available A/B pair, not a monkeypatch.
"""
import sys
import numpy as np

sys.path.insert(0, '/workspaces/Tao_Financial_Engine')

from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.v4.gualaloom_v5_engine import _organism_signal
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import MODALITIES

VOCAB = ('the cat sat on mat and looked at little dog who was running fast across '
         'green grass near old wooden fence while warm bright sun shone down them both '
         'today happy sunshine wonderful extraordinarily beautiful morning guala mommy '
         'daddy friend water fire tree flower bird star apple bread milk salt stone lamb '
         'night day ocean sea beach shore sand mud dirt snow river lake pond rock home '
         'room bed pillow blanket floor wall door window lamp light book toy ball hand').split()

LANG_IDX = MODALITIES.index('language')


def language_liveness(emb, transducer, probe_word):
    all_neurons = [n for h in emb.brain.hemispheres for n in h.cluster.neurons]
    sig = _organism_signal(probe_word, transducer)
    import copy
    emb_copy = copy.deepcopy(emb)
    copy_neurons = [n for h in emb_copy.brain.hemispheres for n in h.cluster.neurons]
    vecs = np.array([n.encode_state(sig) for n in copy_neurons])
    lang_vals = vecs[:, LANG_IDX]
    return int(np.sum(lang_vals != 0)), len(all_neurons)


def recall_accuracy(recall_fn, taught_so_far, transducer, sample_size=15, seed=0):
    rng = np.random.default_rng(seed)
    sample = list(rng.choice(taught_so_far, size=min(sample_size, len(taught_so_far)), replace=False))
    hits = 0
    for w in sample:
        sig = _organism_signal(w, transducer)
        votes = recall_fn(sig)
        if not votes:
            continue
        top = max(votes.items(), key=lambda kv: kv[1])[0]
        if top == w:
            hits += 1
    return hits, len(sample)


def run():
    emb = Embryo(brain_seed=42, seed_size=8, observable="event_count")
    transducer = SensoryTransducer(NullAtlasReader())

    checkpoints = [1, 5, 10, 14, 20, 30, 50, 100, 200]
    taught = 0
    taught_words = []
    print(f"{'words':>6} {'lang_live':>10} {'OLD(len)':>10} {'NEW(n_events)':>14}")
    for cp in checkpoints:
        while taught < cp:
            w = VOCAB[taught % len(VOCAB)]
            emb.remember(w, _organism_signal(w, transducer))
            taught_words.append(w)
            taught += 1
        n_live, n_total = language_liveness(emb, transducer, VOCAB[0])
        hits_old, n_sample = recall_accuracy(emb.recall_fast, taught_words, transducer)
        hits_new, _ = recall_accuracy(emb.recall, taught_words, transducer)
        print(f"{taught:6d} {n_live:6d}/{n_total:<3d} {hits_old:6d}/{n_sample:<3d} {hits_new:10d}/{n_sample}")


if __name__ == "__main__":
    run()
