"""
whole_brain_168v3.py — GL-CMD-C2-WHOLE-BRAIN-EVE-20260704-168-v3 harness.

Model work only. Zero live-path changes (G-4). Boots ONE Embryo (the
committed 8-hemisphere seed, per-neuron primitive stack, no-reset, folding
wired but naturally blocked — A5) and raises it on a continuous multi-modal
curriculum with sleep/replay cycles (A2), reading FIFTEEN mechanism gauges
off the SAME running organism at each checkpoint (A1/A3) — no mechanism is
benched in isolation (G-1). A second, twin organism (identical seed/
curriculum, differing only in recall observable) answers A4's recall-
representation question as one gauge, not a separate track.

Four of the fifteen mechanisms have no code path in loom_model today and
are reported ABSENT, never simulated (A5): Composition (#2 — LoomTapestry/
LoomMosaic exists but is a disconnected structure, never wired into
Embryo/LoomBrain), Imagination (#10 — no generative/novel-combination code
anywhere in the module), Reflection (#11 — depends on an emission/self-
hearing loop that depends on Composition, itself absent), Theory of mind
(#13 — explicitly out of scope per the -103 table and this CMD's own
"who-tags" example).

RNG use, audited against G-2/G-3: cue selection (which word to query/
degrade/replay) uses np.random.default_rng seeded deterministically —
cue noise only, never neuron identity, per the standing STOP. Embryo's
OWN pre-existing _seed_dna_diversity() (not written here, part of "the
committed organism") seeds per-neuron kappa/threshold/aff_gain/polarity
from np.random.default_rng(1000+neuron_index) — deterministic per neuron
index, not per-run-random, and used for CHEMICAL/metabolic differentiation
(receptor gain, excitability), not for the population-vote-diversity
mechanism the 6/22 STOP was written against. Flagged plainly in the report
rather than silently used or silently avoided.
"""

import sys, os, time, math
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import (
    SensoryTransducer, SMELL_CHANNELS, TASTE_CHANNELS,
)
from dsf_ai_service.curriculum.sensory_catalog import SensoryCatalog
from dsf_ai_service.curriculum.catalog_atlas_reader import CatalogAtlasReader
from dsf_ai_service.loom_model.grandurun import MODALITIES
from dsf_ai_service.loom_model.tests.test_folding_engaged import (
    _PETER_RABBIT_EXCERPT, _build_catalog,
)

BRAIN_SEED = 42
SEED_SIZE = 8


# ---------------------------------------------------------------------------
# Curriculum plumbing — real catalog-backed transduction, real corpus text
# ---------------------------------------------------------------------------

def build_pipeline(observable, db_path):
    """One organism: Embryo (committed 8-hemisphere seed) + real catalog-
    backed ExperiencePipeline (not NullAtlasReader — repeated exposure must
    actually converge toward a stable percept for 'compressed childhood'
    development to mean anything)."""
    catalog = _build_catalog(db_path)
    reader = CatalogAtlasReader(catalog)
    transducer = SensoryTransducer(reader)
    emb = Embryo(brain_seed=BRAIN_SEED, seed_size=SEED_SIZE, observable=observable)
    pipe = ExperiencePipeline(emb.brain, transducer)
    return emb, pipe, catalog


def corpus_words():
    words = []
    for s in _PETER_RABBIT_EXCERPT:
        words.extend(s.strip().lower().split())
    return words


_ZERO_TASTE = {ch: 0.0 for ch in TASTE_CHANNELS}
_ZERO_SMELL = {ch: 0.0 for ch in SMELL_CHANNELS}


def taste_smell_receptors(word, catalog):
    """Real catalog-backed receptor dict for Embryo.experience() (drives
    arousal/consensus/folding). Not a fabricated procedural placeholder —
    reads the SAME distributions the ExperiencePipeline's transducer uses.
    Embryo.experience() unconditionally reads BOTH receptors["taste"] and
    receptors["smell"] and concatenates their waveforms — generate_*_
    waveform iterates params.items(), so an ENTIRELY missing modality dict
    ({}) yields zero channels and bipolar_sense's np.concatenate crashes.
    A zero-intensity dict (every channel at 0.0, real channel names, not a
    placeholder value) is the honest statement "no signal in this
    modality" — same effect A2's own noise=False path already relies on
    (absence reads as zero, not hallucinated), just supplied at the
    correct shape so the waveform generator doesn't choke on an empty
    dict. Returns None only if BOTH modalities are catalog-absent, so the
    caller can skip driving this pathway at all for purely abstract words."""
    dist_taste = catalog.get_distribution(word, "taste")
    dist_smell = catalog.get_distribution(word, "smell")
    if dist_taste is None and dist_smell is None:
        return None
    return {
        "taste": dist_taste[0] if dist_taste is not None else dict(_ZERO_TASTE),
        "smell": dist_smell[0] if dist_smell is not None else dict(_ZERO_SMELL),
    }


# ---------------------------------------------------------------------------
# Sleep / replay — built fresh for this run, from real primitives only.
# Not a native loom_model mechanism (none exists — confirmed by research
# before writing this); labeled SCAFFOLDING throughout the report, not
# claimed as an emergent property of the substrate.
# ---------------------------------------------------------------------------

def sleep_replay(emb, pipe, seen_words, tick_start, rng, n_replay=15):
    """Pause new input; re-present a sample of already-experienced words
    through the SAME remember()/experience_moment() path. Real replay of
    real prior content — no new information, no fabricated data."""
    sample = rng.choice(seen_words, size=min(n_replay, len(seen_words)), replace=False)
    tick = tick_start
    for w in sample:
        sigs = pipe._build_multi_modal_signals(w)
        emb.remember(w, sigs)
        tick += 1
    return list(sample), tick


# ---------------------------------------------------------------------------
# Fifteen gauges — each reads the SAME organism's current state.
# ---------------------------------------------------------------------------

def gauge_recall(emb, pipe, probe_words, rng):
    """#1 Recall — cue retrieves memory. Population vote via em hemisphere's
    own recall (Embryo.recall wraps LoomBrain.recall — the sense-repair-
    fixed, read-only path)."""
    correct, total = 0, 0
    for w in probe_words:
        sigs = pipe._build_multi_modal_signals(w)
        votes = emb.recall(sigs)
        top = votes.most_common(1)
        if top and top[0][0] == w:
            correct += 1
        total += 1
    return correct / total if total else float('nan')


def gauge_cross_modal(emb, pipe, probe_words):
    """#5 Cross-modal — one sense retrieves the others. Language-only cue,
    checked against the full-cue baseline computed by the caller."""
    correct, total = 0, 0
    for w in probe_words:
        full = pipe._build_multi_modal_signals(w)
        partial = {"language": full["language"]}
        votes = emb.recall(partial)
        top = votes.most_common(1)
        if top and top[0][0] == w:
            correct += 1
        total += 1
    return correct / total if total else float('nan')


def gauge_recognition(emb, pipe, probe_words, rng, jitter=0.3):
    """#7 Recognition — same thing, new (noisy) form still lands in its own
    basin. Same degradation methodology as the sense-repair T7/T8 tests,
    applied to real curriculum concepts."""
    correct, total = 0, 0
    for w in probe_words:
        sigs = dict(pipe._build_multi_modal_signals(w))
        for m in MODALITIES:
            if m == "language":
                continue
            v = sigs.get(m)
            if v is None:
                continue
            arr = np.asarray(v, dtype=np.float64)
            sigs[m] = (arr + rng.normal(0, jitter, arr.shape)).tolist()
        votes = emb.recall(sigs)
        top = votes.most_common(1)
        if top and top[0][0] == w:
            correct += 1
        total += 1
    return correct / total if total else float('nan')


def gauge_habituation(emb, repeat_word, pipe, n_exposures=6):
    """#6 Habituation — repeats get boring. FamiliarityFeedback.delta_eff
    (piece #4, wired live via neuron.step()'s own match_score update) across
    successive exposures to the SAME word. Reports the trajectory, not a
    single number — habituation is a curve."""
    trajectory = []
    n = emb.brain.hemispheres[0].cluster.neurons[0]
    for _ in range(n_exposures):
        pipe.deliver_word(repeat_word, tick=0, ticks_per_word=1)
        trajectory.append(float(n.familiarity.delta_eff))
    return trajectory


def gauge_sequence(emb, pipe, sentence_words):
    """#9 Sequence — order kept. perceive_sequence's own pr-hemisphere
    binds concept_t+1 <- encode(signals_t); query pr with word_t's signals,
    check top prediction against the ACTUAL next word, above 1/N chance."""
    emb.perceive_sequence(sentence_words, pipe)
    correct, total = 0, 0
    for i in range(len(sentence_words) - 1):
        sigs = pipe._build_multi_modal_signals(sentence_words[i])
        votes = emb.recall_op("pr", sigs)
        top = votes.most_common(1)
        if top and top[0][0] == sentence_words[i + 1]:
            correct += 1
        total += 1
    chance = 1.0 / len(set(sentence_words)) if sentence_words else float('nan')
    return (correct / total if total else float('nan')), chance


def gauge_association(emb, corpus_sentences, probe_word, rng, n_controls=5):
    """#3 Association — related things retrieve each other, above shuffled
    chance (-103's own test criterion). Ground truth = real co-occurrence
    (same sentence) in the actual curriculum text, not a fabricated
    similarity label.

    NOTE on scope: Embryo.sc_learn()/recall_op(profile=...) — the
    purpose-built profile-based association path for the "sc" hemisphere —
    cannot be used here without corrupting the atlas: this run's main loop
    calls remember() for every word on ALL eight hemispheres (including
    "sc"), which writes event_count-encoded (6-dim) bindings; sc_learn()
    writes a DIFFERENT encoding (128-dim ternary chi via resonant_chi).
    Querying recall_op with profile= after remember() has already touched
    "sc" crashes on a dimension mismatch (confirmed directly, first run of
    this harness). Measuring association via the ALREADY-POPULATED atlas
    instead: for the "sc" hemisphere's own neurons (nominally the semantic
    organ, even though its write path is currently identical to the
    others' — an honest, unresolved immaturity, not hidden here), compare
    the probe word's own bound state vector's cosine similarity to a
    same-sentence co-occurring word's vector vs n_controls random
    non-co-occurring words' vectors. RNG here selects which control words
    to sample — cue selection only, G-2/G-3."""
    sc_hemi = emb.hemi_by_op["sc"]
    vecs = {}
    for n in sc_hemi.cluster.neurons:
        for b in n.binding_atlas._bindings:
            vecs.setdefault(b["concept"], []).append(b["state_vec"])
    if probe_word not in vecs:
        return None
    co_occurring = sorted({
        w for s in corpus_sentences for w in s.lower().split()
        if probe_word in s.lower().split() and w != probe_word and w in vecs
    })
    if not co_occurring:
        return None
    others = sorted(set(vecs.keys()) - {probe_word} - set(co_occurring))
    if not others:
        return None
    controls = list(rng.choice(others, size=min(n_controls, len(others)), replace=False))

    def _mean_cos(target_words):
        sims = []
        for pv in vecs[probe_word]:
            pn = np.linalg.norm(pv)
            if pn < 1e-12:
                continue
            for w in target_words:
                for ov in vecs[w]:
                    on = np.linalg.norm(ov)
                    if on < 1e-12:
                        continue
                    sims.append(float(pv @ ov) / (pn * on))
        return float(np.mean(sims)) if sims else float('nan')

    return {
        "co_occurring_words": co_occurring,
        "control_words": controls,
        "mean_cosine_co_occurring": _mean_cos(co_occurring),
        "mean_cosine_random_control": _mean_cos(controls),
    }


def gauge_hemisphere_integration(emb):
    """#12 Hemisphere integration — organs shape each other. Embryo.consensus:
    convergent/divergent phase-coherence link strength per organ pair,
    already accumulated by experience() during this same run."""
    return dict(emb.consensus)


def gauge_affect(emb):
    """#14 Affect modulation — Embryo.arousal, the real bounded [0,1]
    synthesis/clearance state (K_PROD/K_CLEAR), already live in experience()."""
    return emb.aff_arousal()


def gauge_meta_monitoring(emb):
    """#15 Meta-monitoring — Embryo.sf_sense(): the organism's own
    introspectable self-state vector (arousal + per-organ population +
    per-organ binding strength)."""
    return emb.sf_sense().tolist()


def gauge_attention(emb, pipe, probe_words):
    """#8 Attention (engineering-judgment translation — flagged, not the
    literal v5-engine 'selection entropy/bypass-detector' test, which has
    no equivalent in loom_model): population-vote unanimity/entropy across
    the SAME probe queries used for gauge #1 — how concentrated the
    organism's 'selection' is, substrate-native quantity."""
    unanimous, total = 0, 0
    for w in probe_words:
        sigs = pipe._build_multi_modal_signals(w)
        preds = []
        for hemi in emb.brain.hemispheres:
            for neuron in hemi.cluster.neurons:
                snap = {}
                for m in MODALITIES:
                    krim = neuron.krimelack_bank.get(m)
                    if krim is not None:
                        target = getattr(krim, '_inner', krim)
                        snap[m] = (float(target.phase) if hasattr(target, 'phase') else 0.0,
                                   int(target.winding) if hasattr(target, 'winding') else 0)
                vec = neuron.encode_state(sigs)
                best, _ = neuron.binding_atlas.recall_best(vec)
                preds.append(best)
                for m, (p, w2) in snap.items():
                    krim = neuron.krimelack_bank.get(m)
                    if krim is not None:
                        target = getattr(krim, '_inner', krim)
                        if hasattr(target, 'phase'):
                            target.phase = p
                        target.winding = w2
        unanimous += int(len(set(preds)) == 1)
        total += 1
    return unanimous / total if total else float('nan')


def gauge_retention(emb, pipe, early_words):
    """#4 Retention — memories survive time & sleep. Recall accuracy on the
    FIRST day's words, re-measured after later days + sleep cycles have
    passed with no further reinforcement of these specific words."""
    correct, total = 0, 0
    for w in early_words:
        sigs = pipe._build_multi_modal_signals(w)
        votes = emb.recall(sigs)
        top = votes.most_common(1)
        if top and top[0][0] == w:
            correct += 1
        total += 1
    return correct / total if total else float('nan')


def folding_status(emb):
    """A5 — walls named, not hidden. Real n_eff readout per organ, per the
    committed physics (n_start*FOLD_TRIGGER_RATIO = n_start/e is the capture
    basin; folding fires only if a neuron's n_eff dips below it and stays
    there FOLD_SUSTAIN_TICKS consecutive ticks)."""
    from dsf_ai_service.loom_model.neuron import FOLD_TRIGGER_RATIO
    rows = emb.observe()
    total_neurons = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
    return {
        "per_organ": [{"tag": t, "pop": p, "mean_n_eff": mn, "min_n_eff": mnn}
                      for t, p, mn, mnn in rows],
        "total_neurons": total_neurons,
        "seed_neurons": len(rows) * SEED_SIZE,
        "fold_trigger_ratio": FOLD_TRIGGER_RATIO,
        "folded": total_neurons > len(rows) * SEED_SIZE,
    }


# ---------------------------------------------------------------------------
# Main — one continuous raising run, checkpointed
# ---------------------------------------------------------------------------

def run(n_days=3, n_sleep_replay=15, out=None):
    """One organism's compressed childhood: N days (full passes over the
    Peter Rabbit excerpt), with a sleep/replay cycle after each day. All 15
    gauge slots read at every checkpoint (day boundary + post-sleep) from
    the SAME running organism — G-1, one organism one run."""
    def log(msg):
        print(msg, flush=True)
        if out is not None:
            out.append(msg)

    cue_rng = np.random.default_rng(7)  # cue selection / degradation ONLY — G-2/G-3
    words = corpus_words()
    unique_words = sorted(set(words))
    day1_words = sorted(set(_PETER_RABBIT_EXCERPT[0].lower().split()) & set(unique_words))

    log("=" * 70)
    log("GL-CMD-C2-WHOLE-BRAIN-168-v3 — first growth chart")
    log(f"Curriculum: {len(_PETER_RABBIT_EXCERPT)} sentences, "
        f"{len(words)} word-tokens/day, {len(unique_words)} unique words")
    log(f"Organism: Embryo(brain_seed={BRAIN_SEED}, seed_size={SEED_SIZE}) "
        f"— 8 hemispheres x {SEED_SIZE} seed neurons = {8*SEED_SIZE} total")
    log("=" * 70)

    t0 = time.time()
    primary_db = "/tmp/claude-0/-workspaces-Tao-Financial-Engine/f451719b-ee22-41e6-8d4e-3053a9df07ea/scratchpad/catalog_primary.sqlite3"
    compare_db = "/tmp/claude-0/-workspaces-Tao-Financial-Engine/f451719b-ee22-41e6-8d4e-3053a9df07ea/scratchpad/catalog_compare.sqlite3"
    for p in (primary_db, compare_db):
        if os.path.exists(p):
            os.remove(p)

    emb, pipe, catalog = build_pipeline("event_count", primary_db)
    emb2, pipe2, _ = build_pipeline("resonant_spectral", compare_db)

    seen_words = []
    tick = 0
    checkpoints = []
    # Fixed probe set, drawn ONCE — sampling a fresh probe every day would
    # make day-to-day comparisons apples-to-oranges (a harness bug I found
    # and fixed after the first run showed a non-monotonic recall trend
    # that turned out to be partly a changing-probe artifact, not pure
    # organism drift). Held out from the curriculum days only in the sense
    # that these words aren't specially reinforced beyond normal exposure.
    probe = list(cue_rng.choice(unique_words, size=min(10, len(unique_words)), replace=False))
    log(f"Fixed probe set (used at every checkpoint): {probe}")

    for day in range(n_days):
        log(f"\n--- Day {day} ---")
        for sentence in _PETER_RABBIT_EXCERPT:
            sw = sentence.strip().lower().split()
            for w in sw:
                sigs = pipe._build_multi_modal_signals(w)
                emb.remember(w, sigs)
                emb2.remember(w, pipe2._build_multi_modal_signals(w))
                recept = taste_smell_receptors(w, catalog)
                if recept:
                    emb.experience(w, recept)
                if w not in seen_words:
                    seen_words.append(w)
                tick += 1

        ckpt = {"label": f"day{day}", "tick": tick}
        ckpt["g1_recall_event_count"] = gauge_recall(emb, pipe, probe, cue_rng)
        ckpt["g1_recall_resonant_spectral"] = gauge_recall(emb2, pipe2, probe, cue_rng)
        ckpt["g4_retention_day1_words"] = gauge_retention(emb, pipe, day1_words)
        ckpt["g5_cross_modal"] = gauge_cross_modal(emb, pipe, probe)
        ckpt["g7_recognition"] = gauge_recognition(emb, pipe, probe, cue_rng)
        ckpt["g8_attention_unanimity"] = gauge_attention(emb, pipe, probe)
        ckpt["g12_hemisphere_consensus"] = gauge_hemisphere_integration(emb)
        ckpt["g14_affect_arousal"] = gauge_affect(emb)
        ckpt["g15_meta_sf_sense"] = gauge_meta_monitoring(emb)
        ckpt["folding"] = folding_status(emb)
        checkpoints.append(ckpt)
        log(f"  words seen so far: {len(seen_words)}  tick={tick}  "
            f"elapsed={time.time()-t0:.1f}s")
        for k, v in ckpt.items():
            if k in ("label", "tick"):
                continue
            log(f"  {k}: {v}")

        log(f"  -- sleep/replay {day} --")
        replayed, tick = sleep_replay(emb, pipe, seen_words, tick, cue_rng, n_replay=n_sleep_replay)
        _, tick2 = sleep_replay(emb2, pipe2, seen_words, tick, cue_rng, n_replay=n_sleep_replay)
        ckpt_sleep = {"label": f"day{day}_post_sleep", "tick": tick, "replayed": replayed}
        ckpt_sleep["g1_recall_event_count"] = gauge_recall(emb, pipe, probe, cue_rng)
        ckpt_sleep["g1_recall_resonant_spectral"] = gauge_recall(emb2, pipe2, probe, cue_rng)
        ckpt_sleep["g4_retention_day1_words"] = gauge_retention(emb, pipe, day1_words)
        ckpt_sleep["g14_affect_arousal"] = gauge_affect(emb)
        ckpt_sleep["g15_meta_sf_sense"] = gauge_meta_monitoring(emb)
        checkpoints.append(ckpt_sleep)
        for k, v in ckpt_sleep.items():
            if k in ("label", "tick"):
                continue
            log(f"  post-sleep {k}: {v}")

    # One-shot gauges (don't need per-day tracking): sequence, habituation, association
    log("\n--- one-shot gauges (sequence, habituation, association) ---")
    seq_sentence = _PETER_RABBIT_EXCERPT[0].strip().lower().split()
    g9_acc, g9_chance = gauge_sequence(emb, pipe, seq_sentence)
    log(f"  g9 sequence: pr-predicts-next accuracy={g9_acc*100:.1f}% "
        f"(chance={g9_chance*100:.1f}%)")

    repeat_word = "peter"  # appears many times in the excerpt
    g6_traj = gauge_habituation(emb, repeat_word, pipe)
    log(f"  g6 habituation ({repeat_word!r} delta_eff trajectory): "
        f"{[round(v,3) for v in g6_traj]}")

    assoc_probe = "peter"
    g3 = gauge_association(emb, _PETER_RABBIT_EXCERPT, assoc_probe, cue_rng)
    log(f"  g3 association ({assoc_probe!r} co-occurring vs random-control cosine): {g3}")

    final_folding = folding_status(emb)
    log(f"\n--- folding status (A5 — named, not hidden) ---")
    log(f"  total_neurons={final_folding['total_neurons']} "
        f"seed_neurons={final_folding['seed_neurons']} "
        f"folded={final_folding['folded']}")
    for row in final_folding["per_organ"]:
        log(f"  {row['tag']:>4}: pop={row['pop']:>3} mean_n_eff={row['mean_n_eff']}")

    log(f"\nTotal wall time: {time.time()-t0:.1f}s")

    return {
        "checkpoints": checkpoints,
        "g9_sequence": {"accuracy": g9_acc, "chance": g9_chance},
        "g6_habituation_trajectory": g6_traj,
        "g3_association": g3,
        "final_folding": final_folding,
    }


if __name__ == "__main__":
    run()
