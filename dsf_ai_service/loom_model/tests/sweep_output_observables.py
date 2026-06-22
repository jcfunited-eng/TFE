"""
sweep_output_observables.py — GL-CMD-135: Wide parameter sweep.

Diagnostic sweep over 4 axes × 41 total cells.
Outputs sweep_results_135.csv and sweep_results_135.md.
"""

import sys, os, math, time, hashlib, csv, copy
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader
from dsf_ai_service.loom_model.grandurun import grandurun_state, recall_best, MODALITIES, STATE_DIM
from dsf_ai_service.loom_model.neuron import signal_attenuation

# Frozen 25-word curriculum
CORPUS = ['rabbit', 'garden', 'stone', 'river', 'mountain', 'flower', 'forest',
          'ocean', 'cloud', 'thunder', 'silver', 'golden', 'crystal', 'shadow',
          'whisper', 'flame', 'breeze', 'meadow', 'castle', 'dragon', 'music',
          'silence', 'winter', 'summer', 'autumn']
CORPUS_HASH = hashlib.md5('|'.join(CORPUS).encode()).hexdigest()
REPS = 3
BRAIN_SEED = 42


def _run_cell(config):
    """Run one sweep cell. Returns result dict."""
    observable = config['observable']
    mask = config['mask']
    kappa_lang = config['kappa_lang']
    threshold_lang = config['threshold_lang']
    kappa_sensory = config['kappa_sensory']

    brain = LoomBrain(brain_seed=BRAIN_SEED)
    pipeline = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))

    # Patch krimelack parameters
    for hemi in brain.hemispheres:
        for neuron in hemi.cluster.neurons:
            neuron.krimelack.kappa = kappa_lang
            neuron.krimelack.threshold = threshold_lang
            for m in ['tactile', 'olfactory', 'gustatory']:
                krim = neuron.krimelack_bank.get(m)
                if krim and hasattr(krim, '_inner'):
                    krim._inner.kappa = kappa_sensory
                    krim._inner.threshold = math.pi / 3  # sensory threshold stays

    # Monkey-patch _unwrapped_deltas to use specified observable + mask
    original_method = type(brain.hemispheres[0].cluster.neurons[0])._unwrapped_deltas

    def _patched_deltas(self, signals):
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
            n_samples = max(1, len(signal))

            p0 = float(krim.phase) if hasattr(krim, 'phase') else 0.0
            w0 = int(krim.winding) if hasattr(krim, 'winding') else 0
            ev0 = len(krim.events) if hasattr(krim, 'events') else 0

            if m == "language":
                krim.transduce(signal, no_reset=True, omega_override=2.0 * att)
            elif hasattr(krim, 'feed_signal'):
                sig = list(signal) if not isinstance(signal, list) else signal
                sig_att = [s * att for s in sig]
                krim.feed_signal(sig_att)

            p1 = float(krim.phase) if hasattr(krim, 'phase') else 0.0
            w1 = int(krim.winding) if hasattr(krim, 'winding') else 0
            ev1 = len(krim.events) if hasattr(krim, 'events') else 0

            threshold = getattr(krim, 'threshold',
                        getattr(getattr(krim, '_inner', None), 'threshold', math.pi / 3))
            delta_total = (w1 - w0) * threshold + (p1 - p0)
            winding_count = w1 - w0
            event_count = ev1 - ev0

            if observable == 'delta_total':
                deltas[m] = delta_total
            elif observable == 'delta_rate':
                deltas[m] = delta_total / n_samples
            elif observable == 'winding_count':
                deltas[m] = float(winding_count)
            elif observable == 'winding_rate':
                deltas[m] = winding_count / n_samples
            elif observable == 'event_count':
                deltas[m] = float(event_count)
            elif observable == 'event_rate':
                deltas[m] = event_count / n_samples
            elif observable == 'fingerprint_sum':
                if hasattr(krim, 'fingerprint'):
                    fp = krim.fingerprint()
                    deltas[m] = float(sum(fp)) if fp else 0.0
                else:
                    deltas[m] = 0.0
            else:
                deltas[m] = delta_total / n_samples
        return deltas

    # Apply monkey-patch
    from dsf_ai_service.loom_model.neuron import LoomNeuron
    LoomNeuron._unwrapped_deltas = _patched_deltas

    try:
        # Teach
        tick = 0
        for rep in range(REPS):
            for w in CORPUS:
                pipeline.deliver_word(w, tick, ticks_per_word=1)
                tick += 1

        # Compute T5 accuracy
        correct = 0
        total = 0
        for w in CORPUS:
            signals = pipeline._build_multi_modal_signals(w)
            votes = brain.recall(signals)
            top = votes.most_common(1)
            if top and top[0][0] == w:
                correct += 1
            total += 1
        accuracy = correct / total * 100

        # Per-concept per-modality std
        n0 = brain.hemispheres[0].cluster.neurons[0]
        n0.binding_atlas._ensure_cache()
        mat = n0.binding_atlas._matrix_cache
        labels = n0.binding_atlas._concepts_cache

        mod_stds = {}
        for mi, m in enumerate(MODALITIES):
            vals_per_concept = {}
            for lab, vec in zip(labels, mat):
                vals_per_concept.setdefault(lab, []).append(vec[mi] if mi < vec.shape[0] else 0)
            # Mean across reps, then std across concepts
            concept_means = [np.mean(v) for v in vals_per_concept.values()]
            mod_stds[m] = float(np.std(concept_means)) if len(concept_means) > 1 else 0.0

        # Right-concept and wrong-best cosine
        right_cosines = []
        wrong_best_cosines = []
        for w in CORPUS[:10]:
            signals = pipeline._build_multi_modal_signals(w)
            snap = {}
            for m_name in MODALITIES:
                krim = n0.krimelack_bank.get(m_name)
                if krim:
                    snap[m_name] = (
                        float(krim.phase) if hasattr(krim, 'phase') else 0,
                        int(krim.winding) if hasattr(krim, 'winding') else 0)
            qd = n0._unwrapped_deltas(signals)
            for m_name, (p, ww) in snap.items():
                krim = n0.krimelack_bank.get(m_name)
                if krim:
                    if hasattr(krim, 'phase'): krim.phase = p
                    krim.winding = ww
            qv = grandurun_state(qd)
            t_norm = np.linalg.norm(qv)
            if t_norm < 1e-12:
                continue
            a_norms = np.linalg.norm(mat, axis=1)
            valid = a_norms > 1e-12
            cos = np.zeros(mat.shape[0])
            cos[valid] = (mat[valid] @ (qv / t_norm)) / a_norms[valid]
            for lab, c in zip(labels, cos):
                if lab == w:
                    right_cosines.append(c)
                else:
                    wrong_best_cosines.append(c)

        right_mean = float(np.mean(right_cosines)) if right_cosines else 0
        wrong_mean = float(np.max(wrong_best_cosines)) if wrong_best_cosines else 0

    finally:
        # Restore original method
        LoomNeuron._unwrapped_deltas = original_method

    return {
        'T5_accuracy': round(accuracy, 1),
        'lang_std': round(mod_stds.get('language', 0), 6),
        'vis_std': round(mod_stds.get('visual', 0), 6),
        'aud_std': round(mod_stds.get('auditory', 0), 6),
        'tac_std': round(mod_stds.get('tactile', 0), 6),
        'ol_std': round(mod_stds.get('olfactory', 0), 6),
        'gus_std': round(mod_stds.get('gustatory', 0), 6),
        'right_cos': round(right_mean, 4),
        'wrong_cos': round(wrong_mean, 4),
    }


def build_cells():
    """Build all 41 sweep cells."""
    cells = []
    defaults = dict(observable='delta_rate', mask=set(MODALITIES),
                    kappa_lang=80.0, threshold_lang=math.pi/3, kappa_sensory=60.0)

    # Axis 1: observable choice (7 cells)
    for obs in ['delta_total', 'delta_rate', 'winding_count', 'winding_rate',
                'event_count', 'event_rate', 'fingerprint_sum']:
        c = {**defaults, 'observable': obs}
        cells.append(('axis1', obs, c))

    # Axis 2: modality mask (6 cells)
    masks = {
        'all_6': set(MODALITIES),
        'no_language': set(MODALITIES) - {'language'},
        'sensory_3': {'tactile', 'olfactory', 'gustatory'},
        'language_only': {'language'},
        'no_lang_no_aud': set(MODALITIES) - {'language', 'auditory'},
        'no_lang_no_vis': set(MODALITIES) - {'language', 'visual'},
    }
    for name, mask in masks.items():
        c = {**defaults, 'mask': mask}
        cells.append(('axis2', name, c))

    # Axis 3: language kappa x threshold (25 cells)
    for kl in [1, 5, 20, 80, 320]:
        for th in [math.pi/12, math.pi/6, math.pi/3, math.pi/2, math.pi]:
            c = {**defaults, 'kappa_lang': float(kl), 'threshold_lang': th}
            label = f'k{kl}_th{th:.2f}'
            cells.append(('axis3', label, c))

    # Axis 4: sensory kappa (3 cells)
    for ks in [15, 60, 240]:
        c = {**defaults, 'kappa_sensory': float(ks)}
        cells.append(('axis4', f'ks{ks}', c))

    return cells


def main():
    cells = build_cells()
    print(f"Running {len(cells)} cells. Corpus hash: {CORPUS_HASH}")

    results = []
    for i, (axis, cell_id, config) in enumerate(cells):
        t0 = time.time()
        print(f"  [{i+1}/{len(cells)}] {axis}/{cell_id}...", end='', flush=True)
        try:
            row = _run_cell(config)
            elapsed = time.time() - t0
            row.update(axis=axis, cell_id=cell_id,
                       observable=config['observable'],
                       mask='|'.join(sorted(config['mask'])),
                       kappa_lang=config['kappa_lang'],
                       threshold_lang=round(config['threshold_lang'], 4),
                       kappa_sensory=config['kappa_sensory'])
            results.append(row)
            print(f" T5={row['T5_accuracy']}% ({elapsed:.1f}s)")
        except Exception as e:
            print(f" ERROR: {e}")
            results.append(dict(axis=axis, cell_id=cell_id, T5_accuracy=-1,
                               error=str(e)))

    # Write CSV
    out_dir = os.path.dirname(__file__)
    csv_path = os.path.join(out_dir, 'sweep_results_135.csv')
    md_path = os.path.join(out_dir, 'sweep_results_135.md')

    if results:
        keys = list(results[0].keys())
        with open(csv_path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(results)

        with open(md_path, 'w') as f:
            f.write('# GL-CMD-135 Sweep Results\n\n')
            f.write(f'Corpus: {len(CORPUS)} words, hash={CORPUS_HASH}\n\n')
            f.write('| axis | cell | T5% | lang_std | tac_std | ol_std | gus_std | right_cos | wrong_cos |\n')
            f.write('|------|------|-----|----------|---------|--------|---------|-----------|----------|\n')
            for r in results:
                f.write(f"| {r.get('axis','')} | {r.get('cell_id','')} | "
                        f"{r.get('T5_accuracy','')} | {r.get('lang_std','')} | "
                        f"{r.get('tac_std','')} | {r.get('ol_std','')} | "
                        f"{r.get('gus_std','')} | {r.get('right_cos','')} | "
                        f"{r.get('wrong_cos','')} |\n")

    print(f"\nResults written to {csv_path} and {md_path}")


if __name__ == '__main__':
    main()
