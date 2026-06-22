"""
sweep_137_scaling_probe.py — GL-CMD-137: Concept-count + neuron-count scaling.
16 cells across 3 axes. Diagnostic.
"""

import sys, os, math, time, csv, random
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import grandurun_state, MODALITIES, STATE_DIM
from dsf_ai_service.loom_model.neuron import signal_attenuation, LoomNeuron

STEMS = ['flame','river','stone','garden','rabbit','forest','ocean',
         'cloud','silver','golden','crystal','shadow','flower',
         'mountain','meadow','castle','dragon','music','winter',
         'summer','autumn','spring','thunder','whisper','breeze',
         'harbor','valley','prairie','attic','glacier','canyon',
         'fountain','library','lantern','basket','hammer','willow',
         'cottage','harvest','doorway','ribbon','kettle','bridge',
         'orchard','signal','echo','marble','anchor','kitchen',
         'pebble','feather','candle','blanket','window','hearth',
         'cellar','pasture','thicket','ember','spruce','heron',
         'beacon','pavilion','arcade','linen','quartz','copper',
         'ivory','amber','jasper','onyx','cedar','maple','birch',
         'sycamore','reed','clover','chestnut','almond','pomelo',
         'quince','plum','cherry','peach','apple','pear','melon',
         'fennel','thyme','sage','basil','mint','rosemary',
         'parsley','tarragon','chive','clove','nutmeg','ginger',
         'cardamom','cinnamon','vanilla','pepper','saffron',
         'turmeric','marigold','iris','lily','tulip']

REPS = 3
BRAIN_SEED = 42


def generate_concepts(n, seed=42):
    rng = random.Random(seed)
    if n <= len(STEMS):
        return rng.sample(STEMS, n)
    singles = list(STEMS)
    rng.shuffle(singles)
    concepts = singles[:]
    pairs = [(a, b) for a in STEMS for b in STEMS if a != b]
    rng.shuffle(pairs)
    for a, b in pairs:
        if len(concepts) >= n:
            break
        compound = f'{a}{b}'
        if compound not in concepts:
            concepts.append(compound)
    return concepts[:n]


def _run_cell(config):
    n_concepts = config['n_concepts']
    seed_size = config.get('seed_size', 8)
    mask = config.get('mask', set(MODALITIES))

    corpus = generate_concepts(n_concepts, seed=42)

    brain = LoomBrain(brain_seed=BRAIN_SEED, seed_size=seed_size)
    pipeline = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))

    original_method = LoomNeuron._unwrapped_deltas

    def _patched_event_count(self, signals):
        rpos = getattr(self, 'ring_pos', 0)
        rN = getattr(self, 'ring_N', 1)
        deltas = {}
        for i, m in enumerate(MODALITIES):
            if m not in mask:
                deltas[m] = 0.0
                continue
            signal = signals.get(m)
            krim = self.krimelack_bank.get(m)
            if signal is None or krim is None:
                deltas[m] = 0.0
                continue
            att = signal_attenuation(rpos, rN, i)
            ev0 = len(krim.events) if hasattr(krim, 'events') else 0
            if m == "language":
                krim.transduce(signal, no_reset=True, omega_override=2.0 * att)
            elif hasattr(krim, 'feed_signal'):
                sig = list(signal) if not isinstance(signal, list) else signal
                sig_att = [s * att for s in sig]
                krim.feed_signal(sig_att)
            ev1 = len(krim.events)
            deltas[m] = float(ev1 - ev0)
        return deltas

    LoomNeuron._unwrapped_deltas = _patched_event_count

    try:
        tick = 0
        for rep in range(REPS):
            for w in corpus:
                pipeline.deliver_word(w, tick, ticks_per_word=1)
                tick += 1

        correct = 0
        right_cosines = []
        wrong_cosines = []
        for w in corpus:
            signals = pipeline._build_multi_modal_signals(w)
            votes = brain.recall(signals)
            top = votes.most_common(1)
            if top and top[0][0] == w:
                correct += 1

        accuracy = correct / n_concepts * 100

        # Unique predictions probe (5 sample queries on H0)
        sample_qs = corpus[:min(5, n_concepts)]
        unique_counts = []
        for q in sample_qs:
            sigs = pipeline._build_multi_modal_signals(q)
            preds = []
            for n in brain.hemispheres[0].cluster.neurons:
                n.binding_atlas._ensure_cache()
                if n.binding_atlas._matrix_cache is None:
                    continue
                snap = {mm: (n.krimelack_bank[mm].phase if hasattr(n.krimelack_bank[mm], 'phase') else 0,
                             n.krimelack_bank[mm].winding if hasattr(n.krimelack_bank[mm], 'winding') else 0)
                        for mm in MODALITIES if mm in n.krimelack_bank}
                qd = n._unwrapped_deltas(sigs)
                for mm, (p, ww) in snap.items():
                    k = n.krimelack_bank[mm]
                    if hasattr(k, 'phase'): k.phase = p
                    k.winding = ww
                qv = grandurun_state(qd)
                t_norm = np.linalg.norm(qv)
                if t_norm < 1e-12:
                    continue
                a_norms = np.linalg.norm(n.binding_atlas._matrix_cache, axis=1)
                valid = a_norms > 1e-12
                cos = np.zeros(n.binding_atlas._matrix_cache.shape[0])
                cos[valid] = (n.binding_atlas._matrix_cache[valid] @ (qv / t_norm)) / a_norms[valid]
                preds.append(n.binding_atlas._concepts_cache[int(np.argmax(cos))])
            unique_counts.append(len(set(preds)))

        avg_unique = float(np.mean(unique_counts)) if unique_counts else 0

    finally:
        LoomNeuron._unwrapped_deltas = original_method

    return {
        'T5_accuracy': round(accuracy, 1),
        'n_concepts': n_concepts,
        'seed_size': seed_size,
        'total_neurons': seed_size * 8,
        'mask': '|'.join(sorted(mask)),
        'n_unique_preds_avg': round(avg_unique, 1),
    }


def main():
    cells = []

    # Axis A: vocabulary scaling
    for n in [25, 50, 100, 200, 400]:
        cells.append((f'A_n{n}', dict(n_concepts=n)))

    # Axis B: brain-size scaling at 100 concepts
    for ss in [4, 8, 16, 32]:
        cells.append((f'B_ss{ss}', dict(n_concepts=100, seed_size=ss)))

    # Axis C: single-channel isolation at 50 concepts
    for m in MODALITIES:
        cells.append((f'C_{m[:3]}_only', dict(n_concepts=50, mask={m})))
    cells.append(('C_all_6', dict(n_concepts=50)))

    print(f"Running {len(cells)} cells")
    results = []
    for i, (cell_id, config) in enumerate(cells):
        t0 = time.time()
        print(f"  [{i+1}/{len(cells)}] {cell_id} (n={config['n_concepts']})...", end='', flush=True)
        try:
            row = _run_cell(config)
            elapsed = time.time() - t0
            row['cell_id'] = cell_id
            row['axis'] = cell_id.split('_')[0]
            results.append(row)
            print(f" T5={row['T5_accuracy']}% uniq={row['n_unique_preds_avg']} ({elapsed:.1f}s)")
        except Exception as e:
            print(f" ERROR: {e}")
            import traceback; traceback.print_exc()
            results.append(dict(cell_id=cell_id, T5_accuracy=-1, error=str(e)))

    out_dir = os.path.dirname(__file__)
    md_path = os.path.join(out_dir, 'sweep_results_137.md')
    csv_path = os.path.join(out_dir, 'sweep_results_137.csv')

    with open(md_path, 'w') as f:
        f.write('# GL-CMD-137 Scaling Probe Results\n\n')
        f.write('| cell | axis | n_concepts | neurons | mask | T5% | unique_preds |\n')
        f.write('|------|------|------------|---------|------|-----|-------------|\n')
        for r in results:
            f.write(f"| {r.get('cell_id','')} | {r.get('axis','')} | "
                    f"{r.get('n_concepts','')} | {r.get('total_neurons','')} | "
                    f"{r.get('mask','')[:20]} | {r.get('T5_accuracy','')} | "
                    f"{r.get('n_unique_preds_avg','')} |\n")

    if results:
        keys = list(results[0].keys())
        with open(csv_path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(results)

    print(f"\nResults: {md_path}")


if __name__ == '__main__':
    main()
