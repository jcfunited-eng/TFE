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

from dsf_ai_service.loom_model.embryo import Embryo, OPERATIONS
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
        # GL-RPT-BRAIN-IMAGINATION-REFLECTION-DESIGN-C1-20260711 found this
        # stale (2026-07-10 wave-memory migration replaced the flat
        # `_bindings` list with per-neuron wave `cells`; this file predates
        # that by one commit family) and flagged it for whoever next
        # touched this harness -- that's this session. Same accessor
        # test_cognition_path.py already uses post-migration.
        for c in n.binding_atlas.cells.values():
            for b in c.bindings:
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



# ---------------------------------------------------------------------------
# GL-CMD-ORGANISM-PERSIST-EVE-20260704-169-v1 — B3/B4: this harness becomes a
# resumable raising loop for ONE continuous organism. Extends -168-v3 above
# (untouched — run()/main-with-no-args still reproduces that historical,
# twin-comparison, single-shot report exactly as filed). Everything below is
# additive: a NEW organism, born once under B1's structural DNA (retiring
# the RNG-seeded diversity -168-v3 used), never restarted at Day 0 again.
# ---------------------------------------------------------------------------

import json
import subprocess

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', '..')
STATE_DIR = os.path.join(REPO_ROOT, 'backups', 'organism_169')
STATE_PATH = os.path.join(STATE_DIR, 'state.pkl.gz')
CHART_PATH = os.path.join(STATE_DIR, 'growth_chart.json')


def _load_chart(chart_path=CHART_PATH):
    if os.path.exists(chart_path):
        with open(chart_path) as f:
            return json.load(f)
    return {"identity_uuid": None, "sessions": []}


def _save_chart(chart, chart_path=CHART_PATH):
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    with open(chart_path, 'w') as f:
        json.dump(chart, f, indent=2, default=str)


def birth_or_load(state_path=STATE_PATH):
    """B1/B3: birth ONCE if no persisted state exists; otherwise load the
    SAME organism. Never re-instantiate a fresh Embryo when a prior state
    exists -- that would be a silent replacement (G-2)."""
    if os.path.exists(state_path):
        return Embryo.load_full_state(state_path), False   # loaded, not born
    emb = Embryo(brain_seed=BRAIN_SEED, seed_size=SEED_SIZE, observable="event_count")
    return emb, True                                        # freshly born


def _best_effort_s3_backup(local_path, reason):
    """B2's 'disk + S3'. This dev sandbox has neither boto3 installed nor
    AWS credentials (checked directly: `import boto3` fails here) -- so this
    degrades to disk-only and SAYS SO, per failures-first reporting. It
    never fabricates a successful upload. Written to the same convention as
    save_coordinator.py's _s3_loop (boto3.client('s3'), GUALA_S3_BACKUP_BUCKET
    env var) so it is a real, ready primitive for wherever this harness next
    runs with real AWS access -- just unverified from here."""
    try:
        import boto3
    except ImportError as e:
        return {"uploaded": False, "reason": f"boto3 unavailable in this sandbox: {e}"}
    bucket = os.environ.get("GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups")
    try:
        s3 = boto3.client("s3", region_name="us-east-1")
        key = f"guala/model-only/organism-169/{reason}/{os.path.basename(local_path)}"
        s3.upload_file(local_path, bucket, key)
        return {"uploaded": True, "bucket": bucket, "key": key}
    except Exception as e:
        return {"uploaded": False, "reason": str(e)}


def fingerprint(emb, pipe, probe_words):
    """G-1 proof artifact: a comprehensive, JSON-serializable snapshot of
    every piece of state a restore must reproduce exactly -- not spot
    checks. Every neuron actually present (population, not just the seed),
    its DNA/charge/topology, plus organism-level scalars and recall
    behavior on fixed probes."""
    neurons = []
    for h in emb.brain.hemispheres:
        tag = emb.op[h.hemi_id][0]
        for n in h.cluster.neurons:
            neurons.append({
                "hemi": tag, "id": n.neuron_id,
                "ring_pos": getattr(n, "ring_pos", None),
                "kappa": float(getattr(n.krimelack, "kappa", 0.0)),
                "threshold": float(getattr(n.krimelack, "threshold", 0.0)),
                "aff_gain": float(getattr(n, "_aff_gain", 0.0)),
                "polarity": float(getattr(n, "_polarity", 0.0)),
                "q": float(getattr(n, "_q", 0.0)),
                "neighbors": list(n.couplings.neighbors),
                # GL-RPT-BRAIN-IMAGINATION-REFLECTION-DESIGN-C1-20260711:
                # same stale-accessor bug as gauge_association above
                # (`_bindings` retired by the 2026-07-10 wave-memory
                # migration) -- found while auditing this file for the
                # same issue. BindingAtlas.bindings is the class's own
                # already-correct, already-tested property (sums both the
                # flat-vector `cells` path and the per-lane `_lane_bindings`
                # path), so this fix also makes fingerprint() correct for a
                # resonant_spectral-observable organism, which the old
                # accessor never was.
                "n_bindings": n.binding_atlas.bindings,
            })
    recall_votes = {w: emb.recall(pipe._build_multi_modal_signals(w)).most_common(3)
                    for w in probe_words}
    return {
        "identity_uuid": emb.identity_uuid,
        "tick": emb.tick,
        "arousal": emb.arousal,
        "div_pool": emb._div_pool,
        "strength": dict(emb.strength),
        "consensus": {f"{a}|{b}": v for (a, b), v in emb.consensus.items()},
        "population": {tag: len(emb.hemi_by_op[tag].cluster.neurons) for tag, _ in OPERATIONS},
        "neurons": neurons,
        "recall_votes": recall_votes,
    }


def _fingerprint_pipeline(emb, catalog_db):
    catalog = _build_catalog(catalog_db)
    reader = CatalogAtlasReader(catalog)
    transducer = SensoryTransducer(reader)
    pipe = ExperiencePipeline(emb.brain, transducer)
    return pipe, catalog


def _cli_fingerprint_after_birth(state_path, catalog_db, out_json):
    """Subprocess step 1 (G-1 proof): birth + light experience, fingerprint,
    save full state, exit -- this process then dies for real."""
    if os.path.exists(state_path):
        os.remove(state_path)
    emb = Embryo(brain_seed=BRAIN_SEED, seed_size=SEED_SIZE, observable="event_count")
    pipe, catalog = _fingerprint_pipeline(emb, catalog_db)
    words = ["peter", "rabbit", "garden", "mcgregor", "lettuces"]
    for w in words:
        emb.remember(w, pipe._build_multi_modal_signals(w))
        recept = taste_smell_receptors(w, catalog)
        if recept:
            emb.experience(w, recept)
    n0 = emb.brain.hemispheres[0].cluster.neurons[0]
    n0._q = 999.0
    emb._charge_and_fold(emb.brain.hemispheres[0], coherent=True, quantum=0.0)
    fp = fingerprint(emb, pipe, words)
    emb.save_full_state(state_path)
    with open(out_json, 'w') as f:
        json.dump(fp, f, indent=2, default=str)
    print(f"[fingerprint-after-birth] wrote {out_json}", flush=True)


def _cli_fingerprint_after_load(state_path, catalog_db, out_json):
    """Subprocess step 2 (G-1 proof): fresh process, load the saved state
    (no re-birth), fingerprint again with the SAME probe words."""
    emb = Embryo.load_full_state(state_path)
    pipe, _ = _fingerprint_pipeline(emb, catalog_db)
    words = ["peter", "rabbit", "garden", "mcgregor", "lettuces"]
    fp = fingerprint(emb, pipe, words)
    with open(out_json, 'w') as f:
        json.dump(fp, f, indent=2, default=str)
    print(f"[fingerprint-after-load] wrote {out_json}", flush=True)


def restore_honesty_check(work_dir):
    """G-1: save -> kill -> load (genuinely separate OS process) -> compare
    full fingerprints for EXACT equality. Must pin PYTHONHASHSEED=0 in both
    subprocesses: word-signal generation seeds from hash(word)
    (experience.py/sensory_transducer.py), and Python's string hash is
    process-salted by default -- confirmed empirically (recall flipped
    apple->pear across an unpinned before/after) before this fix. Returns
    (passed: bool, fp_before, fp_after, diff_summary)."""
    os.makedirs(work_dir, exist_ok=True)
    state_path = os.path.join(work_dir, "honesty_check_state.pkl.gz")
    catalog_db = os.path.join(work_dir, "honesty_check_catalog.sqlite3")
    fp_before_path = os.path.join(work_dir, "fp_before.json")
    fp_after_path = os.path.join(work_dir, "fp_after.json")
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"

    subprocess.run(
        [sys.executable, __file__, "--fingerprint-after-birth",
         state_path, catalog_db, fp_before_path],
        check=True, cwd=REPO_ROOT, env=env,
    )
    # process boundary: the birth process has fully exited by the time
    # run() returns above -- no shared memory, module globals, or caches
    # survive into the next call.
    subprocess.run(
        [sys.executable, __file__, "--fingerprint-after-load",
         state_path, catalog_db, fp_after_path],
        check=True, cwd=REPO_ROOT, env=env,
    )

    with open(fp_before_path) as f:
        fp_before = json.load(f)
    with open(fp_after_path) as f:
        fp_after = json.load(f)

    passed = (fp_before == fp_after)
    diff = None
    if not passed:
        diff = {k: (fp_before.get(k), fp_after.get(k))
                for k in fp_before if fp_before.get(k) != fp_after.get(k)}
    return passed, fp_before, fp_after, diff


def raise_session(n_days=1, n_sleep_replay=15, out=None):
    """B3: one session of the resumable raising loop for the ONE persistent
    organism. Loads it if it exists (else births it once, B1), feeds
    n_days of curriculum + sleep/replay, appends to the CUMULATIVE growth
    chart (B4 -- never restarts at Day 0), persists full state to disk +
    best-effort S3 (B2) at the end."""
    def log(msg):
        print(msg, flush=True)
        if out is not None:
            out.append(msg)

    if os.environ.get("PYTHONHASHSEED") != "0":
        log("WARNING: PYTHONHASHSEED != '0' in this process -- word-signal "
            "generation seeds from hash(word), which is process-salted "
            "without this pin (see restore-honesty check). Gauge values "
            "from this session are not directly comparable to a session "
            "run without the pin.")

    chart = _load_chart()
    session_no = len(chart["sessions"]) + 1

    emb, born = birth_or_load()
    if not born:
        assert chart["identity_uuid"] == emb.identity_uuid, (
            "G-2 violation: loaded organism's identity_uuid does not match "
            "the chart's recorded identity")

    # Rebuilt fresh every session, never persisted: _build_catalog seeds from
    # a fixed np.random.default_rng(42) over a fixed word set, so it is
    # bit-identical every time (verified as part of the G-1 restore-honesty
    # check, which rebuilds it in two separate processes) -- no reason to
    # carry this recreatable artifact in the durable state directory.
    import tempfile
    catalog_db = os.path.join(tempfile.mkdtemp(prefix="organism_169_catalog_"),
                               f"session{session_no}.sqlite3")
    catalog = _build_catalog(catalog_db)
    reader = CatalogAtlasReader(catalog)
    transducer = SensoryTransducer(reader)
    pipe = ExperiencePipeline(emb.brain, transducer)

    if born:
        chart["identity_uuid"] = emb.identity_uuid
        log(f"BIRTH (session {session_no}): identity_uuid={emb.identity_uuid}")
    else:
        pop = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
        log(f"LOADED (session {session_no}): identity_uuid={emb.identity_uuid} "
            f"tick={emb.tick} pop={pop}")

    cue_rng = np.random.default_rng(7)
    words = corpus_words()
    unique_words = sorted(set(words))
    day1_words = sorted(set(_PETER_RABBIT_EXCERPT[0].lower().split()) & set(unique_words))
    probe = list(cue_rng.choice(unique_words, size=min(10, len(unique_words)), replace=False))

    seen_words = []
    day_entries = []
    for day in range(n_days):
        for sentence in _PETER_RABBIT_EXCERPT:
            for w in sentence.strip().lower().split():
                sigs = pipe._build_multi_modal_signals(w)
                emb.remember(w, sigs)
                recept = taste_smell_receptors(w, catalog)
                if recept:
                    emb.experience(w, recept)
                if w not in seen_words:
                    seen_words.append(w)

        pre_fold = folding_status(emb)
        replayed, _ = sleep_replay(emb, pipe, seen_words, emb.tick, cue_rng,
                                    n_replay=n_sleep_replay)
        post_fold = folding_status(emb)

        seq_sentence = _PETER_RABBIT_EXCERPT[0].strip().lower().split()
        g9_acc, g9_chance = gauge_sequence(emb, pipe, seq_sentence)
        g6_traj = gauge_habituation(emb, "peter", pipe)
        g3 = gauge_association(emb, _PETER_RABBIT_EXCERPT, "peter", cue_rng)

        entry = {
            "session": session_no, "day_in_session": day, "tick": emb.tick,
            "g1_recall": gauge_recall(emb, pipe, probe, cue_rng),
            "g3_association": g3,
            "g4_retention_day1_words": gauge_retention(emb, pipe, day1_words),
            "g5_cross_modal": gauge_cross_modal(emb, pipe, probe),
            "g6_habituation_trajectory": g6_traj,
            "g7_recognition": gauge_recognition(emb, pipe, probe, cue_rng),
            "g8_attention_unanimity": gauge_attention(emb, pipe, probe),
            "g9_sequence": {"accuracy": g9_acc, "chance": g9_chance},
            "g12_hemisphere_consensus": {f"{a}|{b}": v for (a, b), v
                                          in gauge_hemisphere_integration(emb).items()},
            "g14_affect_arousal": gauge_affect(emb),
            "g15_meta_sf_sense": gauge_meta_monitoring(emb),
            "g2_composition": "ABSENT — no code path (per -168-v3 A5; LoomTapestry/"
                               "LoomMosaic re-confirmed genuinely unwired into Embryo/"
                               "LoomBrain, GL-RPT-BRAIN-IMAGINATION-REFLECTION-DESIGN-"
                               "C1-20260711-v1 §1, re-checked by direct grep this session)",
            # GL-RPT-BRAIN-IMAGINATION-REFLECTION-DESIGN-C1-20260711-v1 §4,
            # built for real 2026-07-11 (Embryo.imagine()/BindingAtlas.
            # latent_associations(), embryo.py/binding_atlas.py): real,
            # organism-native, population-vote novel-combination surfacing
            # over the "sc" hemisphere's own already-learned bindings —
            # narrower than the -168-v3 A5 "strong reading" (no emission
            # path exists yet to speak these), honestly still a diagnostic,
            # but no longer a hardcoded ABSENT string — real numbers from a
            # real mechanism, [] when there is genuinely nothing to surface
            # yet (not fabricated).
            "g10_imagination": emb.imagine(op_tag="sc", top_k=5),
            # Embryo.reflect()/_reflect_snapshot(): real self-state then-
            # vs-now comparison over sf_sense() history, sampled every 50
            # ticks by remember() itself (see embryo.py). None until the
            # organism has accumulated at least one real snapshot -- an
            # honest "nothing to reflect on yet" for a very young session,
            # not a fabricated baseline.
            "g11_reflection": emb.reflect(),
            "g13_theory_of_mind": "ABSENT — out of scope (per -168-v3 A5)",
            "folding": post_fold,
            "folding_event_this_day": {
                "mechanism": "q-charge (Embryo._charge_and_fold) — NOT n_eff/"
                             "L6_TCL folding, which stays correctly blocked "
                             "per -168-v3 A5",
                "delta_neurons": post_fold["total_neurons"] - pre_fold["total_neurons"],
            },
        }
        day_entries.append(entry)
        log(f"  session {session_no} day {day}: tick={entry['tick']} "
            f"g1={entry['g1_recall']:.2f} pop={post_fold['total_neurons']} "
            f"fold_delta={entry['folding_event_this_day']['delta_neurons']}")

    chart["sessions"].append({
        "session": session_no,
        "born_this_session": born,
        "checkpoints": day_entries,
    })
    _save_chart(chart)
    emb.save_full_state(STATE_PATH)
    s3_result = _best_effort_s3_backup(STATE_PATH, reason=f"session{session_no}")
    log(f"  persisted: disk={STATE_PATH} ({os.path.getsize(STATE_PATH)} bytes) "
        f"s3={s3_result}")
    return chart, s3_result


if __name__ == "__main__":
    if "--fingerprint-after-birth" in sys.argv:
        i = sys.argv.index("--fingerprint-after-birth")
        _cli_fingerprint_after_birth(*sys.argv[i + 1:i + 4])
    elif "--fingerprint-after-load" in sys.argv:
        i = sys.argv.index("--fingerprint-after-load")
        _cli_fingerprint_after_load(*sys.argv[i + 1:i + 4])
    elif "--raise-session" in sys.argv:
        raise_session()
    elif "--restore-honesty-check" in sys.argv:
        work_dir = sys.argv[sys.argv.index("--restore-honesty-check") + 1]
        passed, fp_before, fp_after, diff = restore_honesty_check(work_dir)
        print("RESTORE-HONESTY CHECK:", "PASSED" if passed else "FAILED")
        if not passed:
            print(json.dumps(diff, indent=2, default=str))
    else:
        run()
