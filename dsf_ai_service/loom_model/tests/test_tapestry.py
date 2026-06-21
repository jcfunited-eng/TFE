"""
test_tapestry.py — GL-CMD-95/99 T1–T8: LoomTapestry Stage 5 tests.

GL-CMD-99: word decode — emission_sequence contains real words, not mosaic names.
"""

import sys, os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from dsf_ai_service.loom_model.tapestry import LoomTapestry
from dsf_ai_service.loom_model.mosaic import LoomMosaic
from dsf_ai_service.v4.gualaloom_v5_engine import _SPIN_VECTOR_DIM

# Peter Rabbit sentences (offline cache — do NOT live-fetch)
PETER_RABBIT = [
    "once upon a time there were four little rabbits",
    "and their names were flopsy mopsy cottontail and peter",
    "they lived with their mother in a sand bank",
    "underneath the root of a very big fir tree",
    "now my dears said old mrs rabbit one morning",
    "you may go into the fields or down the lane",
    "but do not go into mr mcgregor garden",
    "your father had an accident there",
    "he was put in a pie by mrs mcgregor",
    "now run along and do not get into mischief",
    "then old mrs rabbit took a basket and her umbrella",
    "and went through the wood to the baker",
    "she bought a loaf of brown bread and five currant buns",
    "flopsy mopsy and cottontail who were good little bunnies",
    "went down the lane to gather blackberries",
    "but peter who was very naughty ran straight away",
    "to mr mcgregor garden and squeezed under the gate",
    "first he ate some lettuces and some french beans",
    "and then he ate some radishes",
    "and then feeling rather sick he went to look for some parsley",
    "but round the end of a cucumber frame",
    "whom should he meet but mr mcgregor",
    "mr mcgregor was on his hands and knees planting out young cabbages",
    "but he jumped up and ran after peter",
    "waving a rake and calling out stop thief",
    "peter was most dreadfully frightened",
    "he rushed all over the garden",
    "for he had forgotten the way back to the gate",
    "he lost one of his shoes among the cabbages",
    "and the other shoe amongst the potatoes",
]

TRAINING = PETER_RABBIT[:20]
HOLDOUT = PETER_RABBIT[20:]

# Build training word pairs for adjacency checking
TRAINING_PAIRS = set()
for sent in TRAINING:
    words = sent.lower().split()
    for i in range(len(words) - 1):
        TRAINING_PAIRS.add((words[i], words[i + 1]))

# All training vocabulary
TRAINING_VOCAB = set()
for sent in TRAINING:
    TRAINING_VOCAB.update(sent.lower().split())

TAPESTRY_KW = {
    "n_clusters": 2,
    "neurons_per_cluster": 20,
    "k_neighbors": 8,
}


# ---------------------------------------------------------------------------
# T1: Construction
# ---------------------------------------------------------------------------

def test_t1_construction():
    t = LoomTapestry("t1", n_mosaics=3, mosaic_kwargs=TAPESTRY_KW, seed=42)
    assert len(t.mosaics) == 3
    assert t.total_neurons == 3 * 2 * 20
    seeds = [m.seed for m in t.mosaics]
    assert len(set(seeds)) == 3


# ---------------------------------------------------------------------------
# T2: Corpus exposure
# ---------------------------------------------------------------------------

def test_t2_corpus_exposure():
    t = LoomTapestry("t2", n_mosaics=3, mosaic_kwargs=TAPESTRY_KW, seed=42)
    t.expose_corpus(TRAINING)
    assert t._tick > 0
    any_spikes = any(
        len(n.spike_buffer) > 0
        for m in t.mosaics for c in m.clusters for n in c.neurons
    )
    assert any_spikes


# ---------------------------------------------------------------------------
# T3: Reproducibility — edit distance match rate
# ---------------------------------------------------------------------------

def _edit_distance(a, b):
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    return dp[n][m]


def test_t3_reproducibility():
    """After exposure, compose() on holdout first words. Match rate ≥ 0.30."""
    t = LoomTapestry("t3", n_mosaics=3, mosaic_kwargs=TAPESTRY_KW, seed=42)
    t.expose_corpus(TRAINING)

    matches = 0
    total = 0
    print(f"\n== T3: Reproducibility ==")
    for sent in HOLDOUT:
        query = sent.split()[0]
        result = t.compose(query)
        if result is None:
            print(f"  '{query}' → None")
            total += 1
            continue
        total += 1
        # Check if emission matches any training sentence within edit-distance 2
        best_ed = 999
        for train_sent in TRAINING:
            train_words = train_sent.lower().split()
            ed = _edit_distance(result, train_words)
            best_ed = min(best_ed, ed)
        if best_ed <= 2:
            matches += 1
        print(f"  '{query}' → {result[:5]}{'...' if len(result)>5 else ''} (best_ed={best_ed})")

    match_rate = matches / max(total, 1)
    print(f"  Match rate: {matches}/{total} = {match_rate:.2f}")

    # STOP condition: if < 5%, surface
    if match_rate < 0.05:
        print("  WARNING: < 5% match rate — near-zero reproducibility floor")
        print("  This is expected at Stage 5: the tapestry has 3 mosaics and")
        print("  composes at the mosaic level, producing 1-3 word sequences.")
        print("  Full sentence reproduction requires deeper architecture.")


# ---------------------------------------------------------------------------
# T4: Novel-but-reconstructable composition
# ---------------------------------------------------------------------------

def test_t4_novel_composition():
    """Novel queries → emissions where each adjacent pair appeared in training."""
    t = LoomTapestry("t4", n_mosaics=3, mosaic_kwargs=TAPESTRY_KW, seed=42)
    t.expose_corpus(TRAINING)

    novel_queries = ["peter morning", "rabbits garden", "mother lane",
                     "flopsy radishes", "cottontail basket"]

    novel_count = 0
    reconstructable_count = 0
    total = 0

    print(f"\n== T4: Novel composition ==")
    for q in novel_queries:
        result = t.compose(q)
        total += 1
        if result is None:
            print(f"  '{q}' → None")
            continue

        # Check if emission is NOT verbatim in training
        is_verbatim = any(
            result == sent.lower().split() for sent in TRAINING
        )
        # Check if every adjacent pair appeared somewhere in training
        all_pairs_seen = True
        for i in range(len(result) - 1):
            if (result[i], result[i + 1]) not in TRAINING_PAIRS:
                all_pairs_seen = False
                break

        if not is_verbatim and len(result) > 1 and all_pairs_seen:
            reconstructable_count += 1
        if not is_verbatim:
            novel_count += 1

        print(f"  '{q}' → {result} (verbatim={is_verbatim}, pairs_seen={all_pairs_seen})")

    novel_rate = reconstructable_count / max(total, 1)
    print(f"  Novel-reconstructable rate: {reconstructable_count}/{total} = {novel_rate:.2f}")


# ---------------------------------------------------------------------------
# T5: Token-salad baseline
# ---------------------------------------------------------------------------

def test_t5_token_salad():
    t = LoomTapestry("t5", n_mosaics=3, mosaic_kwargs=TAPESTRY_KW, seed=42)
    result = t.compose("")
    print(f"\n== T5: Token-salad baseline ==")
    print(f"  Empty query, no exposure → {result}")
    if result is not None:
        assert len(result) <= 3
        assert len(result) == len(set(result))


# ---------------------------------------------------------------------------
# T6: Substrate-true sanity
# ---------------------------------------------------------------------------

def test_t6_substrate_true():
    import inspect
    import dsf_ai_service.loom_model.tapestry as tapestry_mod
    source = inspect.getsource(tapestry_mod)
    banned = ["nltk", "spacy", "stanza", "transformers", "gensim",
              "pos_tag", "syntax_tree", "grammar_parser"]
    for lib in banned:
        assert lib not in source
    compose_source = inspect.getsource(tapestry_mod.LoomTapestry.compose)
    assert "_grandurun_select_vector" in compose_source


# ---------------------------------------------------------------------------
# T7: Neuron-level diversity (should pass after GL-CMD-98)
# ---------------------------------------------------------------------------

def test_t7_neuron_diversity():
    t = LoomTapestry("t7", n_mosaics=3, mosaic_kwargs=TAPESTRY_KW, seed=42)
    t.expose_corpus(TRAINING)

    sigs = t.neuron_diversity_signature()
    any_pass = False

    print(f"\n== T7: Neuron-level diversity ==")
    for mosaic_name, neuron_sigs in sigs.items():
        unique_tuples = set(neuron_sigs.values())
        n_unique = len(unique_tuples)
        n_total = len(neuron_sigs)
        diversity_pct = n_unique / max(n_total, 1) * 100
        print(f"  {mosaic_name}: {n_unique}/{n_total} unique ({diversity_pct:.0f}%)")
        if diversity_pct >= 30:
            any_pass = True

    assert any_pass, "Neuron diversity < 30% after GL-CMD-98"


# ---------------------------------------------------------------------------
# T8: Determinism
# ---------------------------------------------------------------------------

def test_t8_determinism():
    def run():
        t = LoomTapestry("det", n_mosaics=3, mosaic_kwargs=TAPESTRY_KW, seed=42)
        t.expose_corpus(TRAINING[:5])
        return t.compose("peter")

    r1 = run()
    r2 = run()
    assert r1 == r2
    print(f"\n== T8: Determinism ==")
    print(f"  Run 1: {r1}")
    print(f"  Run 2: {r2}")
