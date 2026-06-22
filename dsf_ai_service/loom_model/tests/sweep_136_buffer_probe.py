"""
sweep_136_buffer_probe.py — GL-CMD-136: Verification + channel balance probe.
18 cells across 3 axes. Diagnostic only.
"""

import sys, os, math, time, hashlib, csv
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import grandurun_state, MODALITIES, STATE_DIM
from dsf_ai_service.loom_model.neuron import signal_attenuation, LoomNeuron

CORPUS_25 = ['rabbit', 'garden', 'stone', 'river', 'mountain', 'flower', 'forest',
             'ocean', 'cloud', 'thunder', 'silver', 'golden', 'crystal', 'shadow',
             'whisper', 'flame', 'breeze', 'meadow', 'castle', 'dragon', 'music',
             'silence', 'winter', 'summer', 'autumn']

HELD_OUT_25 = ['elephant', 'tornado', 'diamond', 'violin', 'pepper', 'blanket',
               'candle', 'feather', 'glacier', 'hammer', 'ivory', 'jungle',
               'kettle', 'lantern', 'marble', 'nectar', 'orchid', 'pebble',
               'quartz', 'ribbon', 'saffron', 'thistle', 'urchin', 'velvet', 'willow']

REPS = 3
BRAIN_SEED = 42

# C3 normalization factors (from V1.b audit)
C3_NORM = {"visual": 0.304878, "auditory": 0.026998, "tactile": 0.002936,
           "olfactory": 0.002146, "gustatory": 0.002293, "language": 0.034294}


def _run_cell(config):
    corpus = config.get('corpus', CORPUS_25)
    buffers = config.get('channel_buffers', {m: 1.0 for m in MODALITIES})
    mask = config.get('mask', set(MODALITIES))

    brain = LoomBrain(brain_seed=BRAIN_SEED)
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
            event_count = ev1 - ev0
            deltas[m] = float(event_count) * buffers.get(m, 1.0)
        return deltas

    LoomNeuron._unwrapped_deltas = _patched_event_count

    try:
        tick = 0
        for rep in range(REPS):
            for w in corpus:
                pipeline.deliver_word(w, tick, ticks_per_word=1)
                tick += 1

        correct = 0
        for w in corpus:
            signals = pipeline._build_multi_modal_signals(w)
            votes = brain.recall(signals)
            top = votes.most_common(1)
            if top and top[0][0] == w:
                correct += 1
        accuracy = correct / len(corpus) * 100

        # A1: symmetry probe (only for cells that request it)
        unique_preds = None
        if config.get('symmetry_probe'):
            unique_preds = {}
            for q in ['rabbit', 'river', 'dragon', 'winter', 'silver']:
                if q not in corpus:
                    continue
                sigs = pipeline._build_multi_modal_signals(q)
                preds = []
                for n in brain.hemispheres[0].cluster.neurons:
                    n.binding_atlas._ensure_cache()
                    if n.binding_atlas._matrix_cache is None:
                        preds.append(None); continue
                    snap = {mm: (n.krimelack_bank[mm].phase if hasattr(n.krimelack_bank[mm], 'phase') else 0,
                                 n.krimelack_bank[mm].winding if hasattr(n.krimelack_bank[mm], 'winding') else 0)
                            for mm in MODALITIES if mm in n.krimelack_bank}
                    qd = n._unwrapped_deltas(sigs)
                    for mm, (p, w_) in snap.items():
                        k = n.krimelack_bank[mm]
                        if hasattr(k, 'phase'): k.phase = p
                        k.winding = w_
                    qv = grandurun_state(qd)
                    scores = np.abs(n.binding_atlas._matrix_cache @ (qv / max(np.linalg.norm(qv), 1e-12)))
                    a_norms = np.linalg.norm(n.binding_atlas._matrix_cache, axis=1)
                    cos = np.zeros(scores.shape)
                    valid = a_norms > 1e-12
                    cos[valid] = scores[valid] / a_norms[valid]
                    preds.append(n.binding_atlas._concepts_cache[int(np.argmax(cos))])
                unique_preds[q] = len(set(preds))

    finally:
        LoomNeuron._unwrapped_deltas = original_method

    result = {'T5_accuracy': round(accuracy, 1),
              'buffers': '|'.join(f'{m[0]}={buffers.get(m,1.0)}' for m in MODALITIES),
              'corpus': config.get('corpus_name', 'original_25'),
              'mask': '|'.join(sorted(mask))}
    if unique_preds is not None:
        result['symmetry'] = unique_preds
    return result


def main():
    cells = []

    # Axis A
    cells.append(('A1_symmetry', dict(symmetry_probe=True, corpus_name='original_25')))
    cells.append(('A2_no_aud', dict(mask=set(MODALITIES) - {'auditory'}, corpus_name='original_25')))
    cells.append(('A3_held_out', dict(corpus=HELD_OUT_25, corpus_name='held_out_25')))

    # Axis B — channel buffers
    for mod, short in [('auditory','aud'), ('visual','vis'), ('language','lang'),
                       ('tactile','tac'), ('gustatory','gus'), ('olfactory','ol')]:
        for f in [0.01, 100]:
            bufs = {m: 1.0 for m in MODALITIES}
            bufs[mod] = f
            label = f'B_{short}_{f}'
            cells.append((label, dict(channel_buffers=bufs, corpus_name='original_25')))

    # Axis C
    bufs_c1 = {m: 1.0 for m in MODALITIES}
    bufs_c1['auditory'] = 0.01; bufs_c1['visual'] = 100
    cells.append(('C1_invert_aud_vis', dict(channel_buffers=bufs_c1, corpus_name='original_25')))

    bufs_c2 = {m: 1.0 for m in MODALITIES}
    bufs_c2['auditory'] = 0.01; bufs_c2['visual'] = 100; bufs_c2['language'] = 10
    cells.append(('C2_invert_aud_all_sub', dict(channel_buffers=bufs_c2, corpus_name='original_25')))

    bufs_c3 = dict(C3_NORM)
    cells.append(('C3_uniform_amplify', dict(channel_buffers=bufs_c3, corpus_name='original_25')))

    print(f"Running {len(cells)} cells")
    results = []
    for i, (cell_id, config) in enumerate(cells):
        t0 = time.time()
        print(f"  [{i+1}/{len(cells)}] {cell_id}...", end='', flush=True)
        try:
            row = _run_cell(config)
            elapsed = time.time() - t0
            row['cell_id'] = cell_id
            results.append(row)
            sym = row.get('symmetry', '')
            print(f" T5={row['T5_accuracy']}% ({elapsed:.1f}s) {sym}")
        except Exception as e:
            print(f" ERROR: {e}")
            import traceback; traceback.print_exc()
            results.append(dict(cell_id=cell_id, T5_accuracy=-1, error=str(e)))

    out_dir = os.path.dirname(__file__)
    md_path = os.path.join(out_dir, 'sweep_results_136.md')
    csv_path = os.path.join(out_dir, 'sweep_results_136.csv')

    with open(md_path, 'w') as f:
        f.write('# GL-CMD-136 Buffer Probe Results\n\n')
        f.write('| cell | T5% | corpus | mask | buffers | symmetry |\n')
        f.write('|------|-----|--------|------|---------|----------|\n')
        for r in results:
            f.write(f"| {r.get('cell_id','')} | {r.get('T5_accuracy','')} | "
                    f"{r.get('corpus','')} | {r.get('mask','')} | "
                    f"{r.get('buffers','')} | {r.get('symmetry','')} |\n")

    keys = list(results[0].keys()) if results else []
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(results)

    print(f"\nResults: {md_path}")


if __name__ == '__main__':
    main()
