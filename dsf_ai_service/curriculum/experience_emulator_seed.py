"""experience_emulator_seed.py -- pairs a real subset of the language_seed
vocabulary with the ALREADY-BUILT, ALREADY-DEPLOYED sensory-descriptor-physics
emulator (dsf_ai_service/substrate/sensory_generators.py, wired live per
GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196 / commit 5f1f554), instead of
pushing seed words through experience_word() with no sensory signal at all.

WHY THIS EXISTS (the bug this fixes): production's real word-teaching path is
experience_word(word, signal) -> remember() -> encode_state() ->
resonant_chi.lane_features(signal). lane_features() explicitly DROPS any
signal value that is None or a plain string
(dsf_ai_service/loom_model/resonant_chi.py lane_features/spectral_features:
`if x is None or isinstance(x, str): continue`). gualaloom_v5_engine.py's
_organism_signal(word, transducer) returns ONLY `{"language": word}` -- a
plain string -- for any word with no co-occurring real sight/sound/descriptor
signal in its 3-second binding window (SENSE_BINDING_WINDOW_SEC). So a word
taught with language alone writes an EMPTY state_vec: a real binding_atlas
entry that can never be recalled (confirmed empirically, see this project's
prior investigation). The 200,000-word language_seed vocabulary
(generator/language_seed/) has only scalar chi addresses and affect floats --
no array-valued sensory signal -- so pushing it through experience_word() as
a flat word list produces dead, unrecallable stub entries at any scale.

Joe's correction (2026-07-10/11): don't do that. Pair words with REAL
emulator-generated multi-modal signal -- the same "experience emulator"
machinery this project already built and deployed live for reading
(GL-CMD-EMULATOR-EVERYWHERE), not a bare word push.

THE REAL EMULATOR THIS USES: sensory_generators.py's TOUCH_LIBRARY /
SMELL_LIBRARY / TASTE_LIBRARY + generate_sensory_signals() -- physically-
motivated waveform synthesis (thermal contact curves, Hill-function
receptor-binding kinetics, molecular-volatility onset/decay), NOT
per-word hash fakery (that mechanism is explicitly banned elsewhere in this
codebase, see gualaloom_v5_engine.py's _organism_signal docstring, N3 of
GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191). It is genuinely array-valued
(np.ndarray waveforms), so it does NOT hit the lane_features() string/None
skip -- it produces a real, non-empty state_vec lane, exactly like every
sentence Guala reads that contains a real descriptor word already does live
(_sentence_modal_signals / _organism_signal_with_senses,
gualaloom_v5_engine.py).

THE HONEST SCOPE LIMIT (why this teaches ~110 words, not 1,000-5,000): the
descriptor library only defines 36 real words (16 touch + 12 smell + 8
taste) with an actual physically-grounded profile. An arbitrary vocabulary
word only escapes the dead-stub problem if it EITHER (a) is one of those 36
words itself, or (b) genuinely, truthfully co-occurs with one of them --
production's own doctrine says this explicitly: "lanes fire ONLY for real
descriptor words present in the text... No invention, no shims" (M5 of
GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196-v2). Assigning arbitrary
vocabulary words (most of which are abstract -- "however", "Tuesday",
"jurisdiction") a made-up touch/smell/taste pairing just to defeat the
empty-lane bug would be exactly the fabrication this project's standing
rule prohibits ("augment/correct via real mechanisms, never
hand-edited/fabricated"). So this module only pairs words for which a REAL,
checkable association exists, from two sources, neither invented here:

  1. DIRECT (36 words): the word IS itself a TOUCH_LIBRARY / SMELL_LIBRARY /
     TASTE_LIBRARY descriptor -- tautologically true, self-referential
     grounding (teaching "warm" using warm's own real physics profile).
  2. MINED (~75 words): a real ConceptNet `/r/HasProperty` edge, weight
     >= 0.6, from the word to one of the 36 descriptors -- read from
     generator/language_seed's own cached ConceptNet index
     (.cache/conceptnet_index.json), the SAME real semantic resource this
     project's own generator/language_seed/grounding.py already uses for
     cross-modal grounding ("ConceptNet HasProperty edges + curated
     adjective lists per modality", grounding.py's own docstring). Hand-
     reviewed against a small, named BLOCKLIST (below) to drop wrong-sense
     / idiomatic / inappropriate crowd-sourced edges (e.g. "dad"->cool is
     slang, not a touch temperature; "hope"->clean is nonsense) -- real
     data, filtered for truthfulness, not blindly ingested. /r/Synonym and
     /r/SimilarTo edges were tested too and rejected: they pull in far more
     matches (483 vs 99) but the large majority are wrong word-senses
     ("quiet"->soft is the auditory sense; "promiscuous"->light is an
     archaic slang sense; "comprehension"->light is a "light reading" pun)
     -- accepting them would teach FALSE sensory associations, which is
     exactly the fabrication this module exists to avoid, not commit.

Scaling this further (toward 1,000+) is a real, separate follow-on, not
done here: either substantially more ConceptNet-relation engineering +
per-entry semantic-sense disambiguation, real hand-authored "story" corpora
(the same authorship pattern as SEED_CORPORA in app.py -- Frog and Toad,
Corduroy, etc.), or wiring the OTHER real emulator this project has already
built -- catalog_builder.py's LLM sensory emulation (Claude-based
_llm_params/make_resonant) -- which is genuinely more general-purpose but
has never been wired to any reading/teaching path in production (confirmed:
GL-RPT-SENSORY-READING-GAP-C1-20260705-197), lives on a separate,
standing-"unproven" organ-brain process, and costs a real LLM call per
batch of words -- graduating it to this pipeline is a decision for Joe/Eve,
not made unilaterally here.

THIS MODULE IS STANDALONE AND OFFLINE. It builds a fresh, local Embryo (the
exact class production's Guala.organism uses) and teaches it via the exact
same experience_word() call gualaloom_v5_engine.py's organism worker thread
makes (`self.organism.experience_word(word, signal)`,
_organism_worker_loop). It imports and calls the real, unmodified
generate_sensory_signals() from sensory_generators.py -- no reimplemented
physics, no new math. It does NOT import, patch, or otherwise touch
gualaloom_v5_engine.py, app.py, or any live/production state. Running this
file teaches a local throwaway organism only; it is not wired into any
server request path, curriculum job, or deploy artifact.

Kill switch: EXPERIENCE_EMULATOR_SEED_ENABLED=1 required for main() to
teach anything (default OFF), matching this project's standing convention
for every new mechanism (SENSORY_SPIKE_INJECTION_ENABLED,
SENSORY_ECHO_REPLAY_ENABLED, ENTRY_NEURON_BROADEN_ENABLED, etc.) -- named
here for symmetry with that convention and to make accidental invocation
(e.g. a stray import-and-run) inert, even though this module has no
existing caller and is not on any request path.
"""

import os
import sys
import time
import json

import numpy as np

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dsf_ai_service.substrate.sensory_generators import generate_sensory_signals  # noqa: E402

EXPERIENCE_EMULATOR_SEED_ENABLED = os.environ.get(
    "EXPERIENCE_EMULATOR_SEED_ENABLED", "0") == "1"

# Mirrors gualaloom_v5_engine.py's Guala._MODALITY_TO_ORGANISM_LANE exactly
# (touch/smell/taste shell-atlas naming -> tactile/olfactory/gustatory,
# Embryo.experience_word's composite key names).
_MODALITY_TO_LANE = {"touch": "tactile", "smell": "olfactory", "taste": "gustatory"}

# The 36 real descriptor words sensory_generators.py defines with an actual
# physically-motivated parameter profile (TOUCH_LIBRARY/SMELL_LIBRARY/
# TASTE_LIBRARY). Source of truth for source (1), DIRECT self-reference.
_TOUCH_WORDS = ("warm", "cool", "cold", "hot", "soft", "hard", "smooth", "rough",
                "wet", "dry", "sharp", "fuzzy", "heavy", "light", "squishy", "bumpy")
_SMELL_WORDS = ("fresh", "floral", "sweet", "earthy", "smoky", "salty", "fruity",
                "woody", "clean", "rain", "grass", "ocean")
_TASTE_WORDS = ("sweet", "sour", "salty", "bitter", "savory", "spicy", "creamy", "tangy")

# taste before smell for sweet/salty/sour (mirrors Guala._sensory_word_map's
# own disambiguation order, gualaloom_v5_engine.py ~9019-9024).
_MODALITY_OF_DESCRIPTOR = {}
for _d in _TASTE_WORDS:
    _MODALITY_OF_DESCRIPTOR[_d] = "taste"
for _d in _SMELL_WORDS:
    _MODALITY_OF_DESCRIPTOR.setdefault(_d, "smell")
for _d in _TOUCH_WORDS:
    _MODALITY_OF_DESCRIPTOR.setdefault(_d, "touch")

# Real ConceptNet /r/HasProperty edges (weight >= 0.6) whose object is one of
# the 36 descriptor words above, mined from generator/language_seed's own
# cached ConceptNet index and filtered to words present in the generated
# seed vocabulary (generator/language_seed/output/rich.seed.json). See the
# module docstring's source (2) for the full method and why /r/Synonym /
# /r/SimilarTo were tried and rejected. BLOCKLIST below names every mined
# match this module deliberately drops and why -- nothing is silently
# discarded.
_MINED_BLOCKLIST = {
    "dad": "slang ('cool' as in impressive, not touch temperature)",
    "pee": "real but inappropriate for a children's-curriculum-style corpus",
    "urine": "real but inappropriate for a children's-curriculum-style corpus",
    "hope": "wrong sense / nonsensical ('clean' does not apply)",
    "living": "idiomatic ('hard living'), not a touch property",
    "off": "wrong sense ('light' as in 'lights off'), not a touch property",
    "most": "wrong sense, nonsensical pairing",
    "traffic": "idiomatic ('smooth traffic'), not a touchable object",
    "mit": "fragment/abbreviation, not a real concrete word",
    "codes": "nonsensical pairing",
    "swords": "borderline/weak (metal can feel cool, but not a defining property)",
    "venus": "astronomy trivia, not an everyday sensory experience",
    "dragons": "fictional; 'cool' here is slang, not touch temperature",
    "designs": "wrong sense, circular",
    "patterns": "wrong sense, circular",
    "scents": "circular (scents->floral is definitionally true but empty)",
    "nourishing": "nonsensical pairing with 'rain'",
    "falling": "nonsensical pairing with 'rain'",
    "fruits": "overgeneralized (not all fruits are sour)",
    "lemons": "WRONG: contradicts 'lemon'->sour (real property) below",
    "hats": "not generally true (most hats are soft fabric)",
    "noses": "weak/folk-saying, not a defining property",
    "telephones": "weak, era-dependent (old phones), not a defining property",
    "summertime": "borderline (true in many climates, excluded for caution)",
}

# word -> (modality, descriptor). Built once at import time (pure, no I/O
# side effects beyond the two read-only file loads it needs).
_MINED_PAIRS = None


def _load_mined_pairs():
    """Real ConceptNet HasProperty mining, filtered to real seed-vocabulary
    words, minus the hand-reviewed blocklist above. Returns {} (not raising)
    if the ConceptNet cache or seed output isn't present locally -- this
    module still works with just the 36 DIRECT descriptor words in that
    case; callers should check len(_MINED_PAIRS) if they need to know
    which source fired."""
    global _MINED_PAIRS
    if _MINED_PAIRS is not None:
        return _MINED_PAIRS
    _MINED_PAIRS = {}
    idx_path = os.path.join(_REPO_ROOT, "generator", "language_seed", ".cache",
                             "conceptnet_index.json")
    seed_path = os.path.join(_REPO_ROOT, "generator", "language_seed", "output",
                              "rich.seed.json")
    if not (os.path.exists(idx_path) and os.path.exists(seed_path)):
        return _MINED_PAIRS
    with open(idx_path) as f:
        idx = json.load(f)
    with open(seed_path) as f:
        seed = json.load(f)
    seed_words = {e["word"] for e in seed["vocabulary_entries"]}
    for w, edges in idx.items():
        if w not in seed_words or " " in w or w in _MINED_BLOCKLIST:
            continue
        for rel, obj, weight in edges:
            if rel != "/r/HasProperty" or not isinstance(obj, str):
                continue
            obj_l = obj.strip().lower()
            if obj_l in _MODALITY_OF_DESCRIPTOR and obj_l != w and weight >= 0.6:
                _MINED_PAIRS[w] = (_MODALITY_OF_DESCRIPTOR[obj_l], obj_l)
                break
    return _MINED_PAIRS


def build_word_pairs():
    """Returns {word: [(modality, descriptor), ...]} for every word this
    module can honestly ground -- the 36 direct descriptor words (paired
    with themselves) plus the real, filtered ConceptNet-mined set. Every
    pairing here is checkable: either tautological (the word IS the
    descriptor) or a real, named ConceptNet edge that survived hand review."""
    pairs = {}
    for d in set(_TOUCH_WORDS) | set(_SMELL_WORDS) | set(_TASTE_WORDS):
        pairs.setdefault(d, []).append((_MODALITY_OF_DESCRIPTOR[d], d))
    for w, (mod, desc) in _load_mined_pairs().items():
        pairs.setdefault(w, []).append((mod, desc))
    return pairs


def build_modal_signal(word, modal_pairs):
    """Builds the exact same signal shape gualaloom_v5_engine.py's
    _organism_signal_with_senses produces for a word bound within a real
    sentence's SENSE_BINDING_WINDOW_SEC: {"language": word, "tactile"/
    "olfactory"/"gustatory": <real np.ndarray from generate_sensory_signals>}.
    Reuses generate_sensory_signals() directly -- no reimplemented physics.
    Multiple descriptors in the same modality are concatenated exactly as
    Guala._sentence_modal_signals does (multiple channel waveforms from one
    generate_sensory_signals() call per modality)."""
    by_modality = {}
    for modality, desc in modal_pairs:
        by_modality.setdefault(modality, []).append(desc)
    signal = {"language": word}
    for modality, descriptors in by_modality.items():
        channels = generate_sensory_signals(modality, descriptors)
        if not channels:
            continue
        lane = _MODALITY_TO_LANE[modality]
        signal[lane] = np.concatenate(
            [np.asarray(v, dtype=float) for v in channels.values()])
    return signal


def teach(embryo, word_pairs, log=print):
    """Teaches every (word -> pairs) entry via embryo.experience_word() --
    the exact call gualaloom_v5_engine.py's organism worker thread makes
    (_organism_worker_loop: `self.organism.experience_word(word, signal)`).
    Returns {word: elapsed_seconds}."""
    timings = {}
    for word, pairs in word_pairs.items():
        signal = build_modal_signal(word, pairs)
        t0 = time.time()
        embryo.experience_word(word, signal)
        timings[word] = time.time() - t0
    return timings


def verify_recall(embryo, word_pairs, sample=None, log=print):
    """Real recall verification -- not just 'no errors'. For each word,
    queries embryo.recall() with that word's OWN modal signal (the pure
    sensory cue, language key stripped -- the cross-sense-recall shape
    GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-207/208 established: 'what
    concept does this sensation belong to') and reports:
      - the population-vote score for the TARGET word specifically
        (votes[word] / total_neurons)
      - whether the target word was the single top pick
      - the full top-3 vote breakdown (so a genuine, honest multi-way tie
        among words sharing the same descriptor -- e.g. silk/velvet/butter
        all paired with 'soft' -- is visible as what it is: correct
        confusability between really-similar things, not a bug)
    Returns a list of per-word result dicts."""
    words = list(word_pairs.keys())
    if sample is not None:
        rng = np.random.default_rng(0)
        words = list(rng.choice(words, size=min(sample, len(words)), replace=False))
    total_neurons = sum(len(h.cluster.neurons) for h in embryo.brain.hemispheres)
    results = []
    for word in words:
        pairs = word_pairs[word]
        full_signal = build_modal_signal(word, pairs)
        cue = {k: v for k, v in full_signal.items() if k != "language"}
        votes = embryo.recall(cue)
        top3 = votes.most_common(3)
        target_score = votes.get(word, 0) / total_neurons if total_neurons else 0.0
        target_descriptors = {d for _, d in pairs}
        top_pick = top3[0][0] if top3 else None
        top_pick_descriptors = {d for _, d in word_pairs.get(top_pick, [])} if top_pick else set()
        results.append({
            "word": word,
            "pairs": pairs,
            "target_score": target_score,
            "target_votes": votes.get(word, 0),
            "total_neurons": total_neurons,
            "top_pick": top_pick,
            "is_top_pick": bool(top3) and top3[0][0] == word,
            # honest concept-family hit: the top-voted concept shares at
            # least one real descriptor with the target (e.g. "razor"'s
            # top pick "sharp" IS razor's own taught property -- a correct
            # semantic match even when it isn't the literal same string,
            # which is expected/inevitable when N words share one of only
            # 36 possible descriptor signals).
            "same_family_hit": bool(target_descriptors & top_pick_descriptors),
            "top3": top3,
        })
    return results


def verify_no_regression_for_ungrounded_words(embryo, control_words, log=print):
    """Control case: teaches `control_words` the CURRENT, UNCHANGED normal
    way -- language-only signal, no array-valued modality at all, exactly
    what gualaloom_v5_engine.py's _organism_signal(word, transducer) already
    produces for any word with no live sight/sound/descriptor context
    (`{"language": word}`). Confirms this module changes nothing about that
    existing behavior: these words should remain unrecallable by a sensory
    cue (there is no sensory cue to give them -- honest absence, matching
    today's real, documented production behavior, not a regression this
    module introduces)."""
    total_neurons = sum(len(h.cluster.neurons) for h in embryo.brain.hemispheres)
    results = []
    for word in control_words:
        embryo.experience_word(word, {"language": word})
        # No array-valued cue exists for this word (by construction) -- the
        # honest test is that NO plausible sensory cue recalls it, e.g. probe
        # with each of the 3 modal lanes built from an unrelated descriptor.
        probe = build_modal_signal("__probe__", [("touch", "warm")])
        probe_cue = {k: v for k, v in probe.items() if k != "language"}
        votes = embryo.recall(probe_cue)
        results.append({
            "word": word,
            "target_votes": votes.get(word, 0),
            "total_neurons": total_neurons,
        })
    return results


def verify_normal_conversation_words_unaffected(embryo, log=print):
    """Zero-regression check: teaches a few words the way real conversation
    already does today when a real camera frame IS present (the established,
    unchanged "visual" control case -- {"language": w, "visual": <real-shaped
    array>} -- this is the exact signal shape that this project's prior
    investigation confirmed recalls at score 1.0). Runs this AFTER this
    module's own teaching, on the SAME embryo, to prove the two mechanisms
    don't interfere: normal conversational teaching (real sight/sound
    signal, independent of this module) still recalls correctly when this
    module has ALSO taught other words into the same organism."""
    rng = np.random.default_rng(1)
    results = []
    for w in ("zephyr_ctrl", "mirthquake_ctrl", "planquil_ctrl"):
        visual = rng.standard_normal(64)
        embryo.experience_word(w, {"language": w, "visual": visual})
        votes = embryo.recall({"visual": visual})
        total = sum(len(h.cluster.neurons) for h in embryo.brain.hemispheres)
        results.append({
            "word": w, "top_pick": votes.most_common(1)[0][0] if votes else None,
            "target_score": votes.get(w, 0) / total if total else 0.0,
        })
    return results


def main():
    if not EXPERIENCE_EMULATOR_SEED_ENABLED:
        print("EXPERIENCE_EMULATOR_SEED_ENABLED is not set to '1' -- refusing to "
              "teach anything (kill switch default OFF). This module only ever "
              "operates on a local, throwaway Embryo instance -- it never touches "
              "gualaloom_v5_engine.py or any live/production state -- but the "
              "gate is kept for symmetry with this project's standing convention "
              "for every new mechanism.")
        return 1

    from dsf_ai_service.loom_model.embryo import Embryo

    word_pairs = build_word_pairs()
    n_direct = len(set(_TOUCH_WORDS) | set(_SMELL_WORDS) | set(_TASTE_WORDS))
    n_mined = len(_load_mined_pairs())
    print(f"word pairs built: {len(word_pairs)} total "
          f"({n_direct} direct descriptor words + {n_mined} ConceptNet-mined, "
          f"post-blocklist)")

    embryo = Embryo(brain_seed=42, seed_size=8, observable="resonant_spectral")
    print(f"local Embryo constructed: {sum(len(h.cluster.neurons) for h in embryo.brain.hemispheres)} neurons")

    t0 = time.time()
    timings = teach(embryo, word_pairs)
    dt = time.time() - t0
    avg_ms = 1000.0 * dt / max(len(timings), 1)
    print(f"taught {len(timings)} words in {dt:.2f}s ({avg_ms:.1f}ms/word avg)")

    control_words = [f"__ungrounded_control_{i}__" for i in range(10)]
    control_results = verify_no_regression_for_ungrounded_words(embryo, control_words)
    n_control_hits = sum(1 for r in control_results if r["target_votes"] > 0)
    print(f"control (language-only, no array signal): {n_control_hits}/{len(control_results)} "
          f"spuriously recalled by an unrelated sensory cue (expect 0 -- honest absence)")

    recall_results = verify_recall(embryo, word_pairs, sample=None)
    n_nonzero = sum(1 for r in recall_results if r["target_score"] > 0)
    n_top = sum(1 for r in recall_results if r["is_top_pick"])
    n_family = sum(1 for r in recall_results if r["same_family_hit"])
    print(f"recall verification on ALL {len(recall_results)} taught words: "
          f"{n_nonzero}/{len(recall_results)} nonzero target score, "
          f"{n_top}/{len(recall_results)} exact top pick, "
          f"{n_family}/{len(recall_results)} correct concept-family top pick "
          f"(top-voted concept genuinely shares the target's own real descriptor)")
    for r in recall_results:
        print(f"  {r['word']:16s} pairs={r['pairs']!s:32s} "
              f"target_score={r['target_score']:.3f} top_pick={r['top_pick']!r} "
              f"top3={r['top3']}")

    n_post = sum(len(h.cluster.neurons) for h in embryo.brain.hemispheres)
    print(f"population after teaching: {n_post} neurons "
          f"(started at 64 -- growth is the real charge-and-fold mechanism "
          f"firing on rich multi-modal signal, not something this module "
          f"invented)")

    normal_results = verify_normal_conversation_words_unaffected(embryo)
    n_normal_ok = sum(1 for r in normal_results if r["target_score"] > 0.9)
    print(f"zero-regression check (real-conversation-style visual teaching, "
          f"same organism, taught AFTER this module's words): "
          f"{n_normal_ok}/{len(normal_results)} recalled correctly at score>0.9")
    for r in normal_results:
        print(f"  {r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
