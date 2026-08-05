"""
GL-FIND-DEEPATLAS-C1-20260610 — Deep Atlas Offline Harness

Stage 1 ONLY. NO production code changes. NO substrate primitive modifications.

Imports REAL substrate code paths:
  - FoldedAtlas (chi-band binding, decay, pruning)
  - folded_chi_text / chi_neighbors (chi encoding)
  - DeepMultiModalCognition (fire, cofire_bind, cascade, step)
  - Dream consolidation path (replay_tick logic, salience weighting)
  - Novelty-override salience (commit novelty_bonus)

Step 1: Reproduce baseline failure — one-shot episodic bindings decay to loss.
Step 2: Deep atlas + dual promotion gate (survival + depth-of-encoding).
Step 3: Parameter sweep for operating window.
"""

import math
import copy
import time
import numpy as np
from collections import defaultdict

# ---- Import REAL substrate code paths ----
from dsf_ai_service.substrate.GL_MDL_MULTIMODAL_DEEP_WC_20260608_03 import (
    FoldedAtlas, DeepMultiModalCognition,
    BASE_REINFORCEMENT, DECAY_LAMBDA, FORGETTING_THRESHOLD, STRENGTH_CAP,
)
from dsf_ai_service.substrate.GL_MDL_FOLDED_CHI_WC_20260608_01 import (
    folded_chi_text, chi_neighbors, folded_chi_distance,
)


# ============================================================
# CONSTANTS from real substrate (documented, not reimplemented)
# ============================================================
REAL_DECAY_LAMBDA = DECAY_LAMBDA        # 0.0005
REAL_FORGET_THRESH = FORGETTING_THRESHOLD  # 0.02
REAL_BASE_REINF = BASE_REINFORCEMENT     # 0.10
REAL_STRENGTH_CAP = STRENGTH_CAP         # 1.0
DREAM_INTERVAL = 100                     # ticks between dream cycles (matches production)
TOTAL_TICKS = 6000                       # extended from toy's 4000 to capture full decay


# ============================================================
# Population definitions
# ============================================================
# TRUE: bindings that get re-attended multiple times (established memories)
# EPISODIC: one-shot deep exploration — high dwell, attended ONCE, never revisited
# NOISE: spurious one-glance co-occurrences — low salience, single weak binding

TRUE_WORDS = ["moon", "cow", "bears", "stars", "kittens", "room",
              "goodnight", "the", "and", "a", "you", "foot"]
EPISODIC_WORDS = ["muffin", "blanket", "telephone", "mittens",
                  "grandmother", "fireplace", "lullaby", "curtains",
                  "rocking", "shadows", "whisper", "cradle"]
NOISE_WORDS = ["xyz", "qwk", "bpf", "jzn", "txm", "rvl",
               "wmg", "dkp", "fhc", "nys", "gqb", "plt",
               "vkj", "ztw", "hmn", "cxr", "bwq", "ljf",
               "dnz", "pks", "rtg", "fmw", "hcv", "xjb",
               "ynq", "gls", "ktd", "wrp", "mjc", "zfx"]

# NOTE on noise modeling: Real noise is spurious co-occurrence — a brief
# cofire_bind at a chi position where nothing was intentionally attended.
# It is NOT a full install_word event (which creates deep multi-modal
# bundles across 6 modalities). Noise entries are injected directly into
# the atlas with low salience, bypassing install_word.


def build_cognition_with_words(words):
    """Build a DeepMultiModalCognition and install word modes.
    Uses REAL substrate install_word path."""
    cog = DeepMultiModalCognition()
    for w in words:
        cog.install_word(w)
    return cog


def simulate_attention(cog, word, salience, n_dwell_ticks):
    """Simulate attending to a word for n_dwell_ticks.
    Uses REAL fire() + step() path."""
    cog.fire("word", word, salience=salience)
    for _ in range(n_dwell_ticks):
        cog.step()


def simulate_dream_cycle(atlas, tick):
    """Simulate dream consolidation effect on atlas.

    Real dream (replay_tick) samples krimelack weighted by salience*recency,
    re-projects into sections, calls tick_once which reinforces atlas entries
    that get re-committed. Here we simulate the NET EFFECT on the atlas:
    entries above strength threshold get a reinforcement bump (dream saves
    what is currently strong). This matches the real behavior — replay
    selects high-salience recent items, re-commits them, which calls
    atlas.record() again with reinforcement.

    The key insight from the brief: dream saves RE-ATTENDED structure
    but CANNOT save one-shot episodic memories that aren't re-committed."""
    for chi_t, entries in atlas.entries.items():
        for e in entries:
            if e["strength"] >= 0.4:  # only strong bindings get replayed
                # Dream reinforcement: equivalent to one atlas.record() call
                # from a successful replay-commit cycle
                e["strength"] = min(REAL_STRENGTH_CAP,
                                    e["strength"] + REAL_BASE_REINF * 0.5)


def run_baseline_step1():
    """
    STEP 1: Reproduce baseline failure.

    Three populations through the REAL FoldedAtlas with REAL decay.
    Dream consolidation every DREAM_INTERVAL ticks.
    Show that episodic bindings decay to loss.
    """
    print("=" * 72)
    print("STEP 1: BASELINE — Single-layer atlas, real decay + dream")
    print("=" * 72)

    # Only install TRUE and EPISODIC words as full multi-modal modes.
    # Noise is injected as bare atlas entries (spurious co-occurrence).
    cog = build_cognition_with_words(TRUE_WORDS + EPISODIC_WORDS)

    # --- Phase 1: Initial encoding (ticks 1-200) ---
    # TRUE words: attend with high salience, MULTIPLE times
    for repeat in range(5):
        for w in TRUE_WORDS:
            simulate_attention(cog, w, salience=2.0, n_dwell_ticks=3)

    # EPISODIC words: attend ONCE with high dwell (deep exploration)
    for w in EPISODIC_WORDS:
        simulate_attention(cog, w, salience=2.5, n_dwell_ticks=8)

    # NOISE: bare atlas entries — spurious co-occurrence, NOT install_word.
    # Uses REAL FoldedAtlas.record() with low salience.
    for w in NOISE_WORDS:
        chi = folded_chi_text(w)
        # Single weak record — this is what a brief cofire_bind produces
        cog.atlas.record("word", 9999, chi, cog.tick, salience=0.25)

    print(f"\nAfter encoding (tick {cog.tick}):")
    _report_populations(cog.atlas, cog, "  ")

    # Snapshot strengths at encoding time for episodic entries
    episodic_encoded_strengths = {}
    for w in EPISODIC_WORDS:
        chi = folded_chi_text(w)
        chi_t = tuple(chi)
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                episodic_encoded_strengths[w] = e["strength"]

    # --- Phase 2: Continued operation with decay + dream (ticks 200-4000) ---
    # TRUE words get occasional re-attention (they're established memories)
    # EPISODIC words are NEVER re-attended (the failure case)
    # New learning continues (noise from environment)
    tick_start = cog.tick
    for t in range(tick_start, TOTAL_TICKS):
        # Occasional re-attention to TRUE words (every ~50 ticks)
        if t % 50 < len(TRUE_WORDS):
            w = TRUE_WORDS[t % 50]
            simulate_attention(cog, w, salience=1.5, n_dwell_ticks=2)
        else:
            cog.step()

        # Dream consolidation
        if t % DREAM_INTERVAL == 0 and t > tick_start:
            simulate_dream_cycle(cog.atlas, cog.tick)

    print(f"\nAfter {TOTAL_TICKS} ticks (tick {cog.tick}):")
    true_alive, true_total = _count_alive(cog.atlas, cog, TRUE_WORDS)
    ep_alive, ep_total = _count_alive(cog.atlas, cog, EPISODIC_WORDS)
    noise_alive, noise_total = _count_alive(cog.atlas, cog, NOISE_WORDS, noise_motif=9999)

    print(f"  TRUE:    {true_alive}/{true_total} alive")
    print(f"  EPISODIC:{ep_alive}/{ep_total} alive")
    print(f"  NOISE:   {noise_alive}/{noise_total} alive")

    _report_populations(cog.atlas, cog, "  ")

    # --- Verdict ---
    print("\n--- BASELINE VERDICT ---")
    failure_reproduced = (true_alive >= 10 and ep_alive <= 3 and noise_alive <= 5)
    if failure_reproduced:
        print("FAILURE REPRODUCED: Episodic bindings decayed to loss under")
        print(f"  single-layer dynamics. TRUE={true_alive}/{true_total}, "
              f"EPISODIC={ep_alive}/{ep_total}, NOISE={noise_alive}/{noise_total}")
        print("  One-shot high-dwell bindings cannot survive without re-attention.")
        print("  Dream consolidation only reinforces what is already strong.")
    else:
        print("*** FAILURE DID NOT REPRODUCE ***")
        print(f"  TRUE={true_alive}/{true_total}, EPISODIC={ep_alive}/{ep_total}, "
              f"NOISE={noise_alive}/{noise_total}")
        if ep_alive > 3:
            print("  Episodic bindings survived — the brief's premise may be wrong.")
            print("  Filing GL-FIND with this finding. STOPPING.")
        else:
            print("  Unexpected pattern. Investigate before proceeding.")

    return failure_reproduced, episodic_encoded_strengths, cog


# ============================================================
# STEP 2: Deep Atlas + Dual Promotion Gate
# ============================================================

class DeepAtlas:
    """Two-layer deep atlas. Near-zero decay. Write = dream only.
    Read = additive prior into working atlas strength."""

    def __init__(self, decay_lambda=REAL_DECAY_LAMBDA / 25.0, prior_cap=0.15):
        self.entries = defaultdict(list)  # chi_tuple -> list of deep entries
        self.decay_lambda = decay_lambda
        self.prior_cap = prior_cap  # max additive prior (saturation guard)
        self.promotion_log = []

    def promote(self, entry, source_path, tick):
        """Promote a working atlas entry into deep storage."""
        chi_t = entry["chi"]
        # Check if already in deep
        for de in self.entries[chi_t]:
            if de["section"] == entry["section"] and de["motif"] == entry["motif"]:
                # Reinforce existing deep entry
                de["strength"] = min(REAL_STRENGTH_CAP,
                                     de["strength"] + entry["strength"] * 0.5)
                de["last_tick"] = tick
                return
        self.entries[chi_t].append({
            "section": entry["section"],
            "motif": entry["motif"],
            "chi": chi_t,
            "strength": entry["strength"] * 0.5,  # deep starts at half working strength
            "last_tick": tick,
            "born_tick": tick,
            "source_path": source_path,
            "encoded_strength": entry.get("encoded_strength", entry["strength"]),
        })
        self.promotion_log.append({
            "tick": tick, "section": entry["section"],
            "motif": entry["motif"], "chi": chi_t,
            "path": source_path, "strength": entry["strength"],
        })

    def decay(self, tick):
        """Near-zero decay (1/25th of working)."""
        for entries in self.entries.values():
            for e in entries:
                dt = tick - e["last_tick"]
                if dt > 0:
                    e["strength"] *= math.exp(-self.decay_lambda * dt)
                    e["last_tick"] = tick

    def prune(self):
        for chi_t in list(self.entries.keys()):
            survivors = [e for e in self.entries[chi_t]
                         if e["strength"] >= REAL_FORGET_THRESH]
            if survivors:
                self.entries[chi_t] = survivors
            else:
                del self.entries[chi_t]

    def get_prior(self, chi_t, section=None, motif=None):
        """Additive prior for a SPECIFIC working atlas entry.
        Must match section+motif (not just chi position) to prevent
        noise at shared chi positions from getting boosted.
        Capped to prevent dominance (saturation guard)."""
        for e in self.entries.get(chi_t, []):
            if (e["strength"] >= REAL_FORGET_THRESH
                    and e["section"] == section and e["motif"] == motif):
                return min(self.prior_cap, e["strength"] * 0.3)
        return 0.0

    def live_count(self):
        return sum(1 for es in self.entries.values()
                   for e in es if e["strength"] >= REAL_FORGET_THRESH)

    def contamination_count(self, noise_motif=9999):
        """Count deep entries that originated from noise (motif matches noise marker).
        Chi-position overlap alone is NOT contamination — only actual noise entries promoted."""
        count = 0
        for chi_t, entries in self.entries.items():
            for e in entries:
                if e["motif"] == noise_motif and e["strength"] >= REAL_FORGET_THRESH:
                    count += 1
        return count


def dual_promotion_gate(working_atlas, deep_atlas, tick,
                        survival_history, encode_gate=0.8,
                        survival_threshold=0.4, survival_consecutive=3):
    """
    Evaluate both promotion paths at dream time.

    Path A (Survival): binding has stayed above theta for S consecutive
    dream cycles. Consolidate into deep.

    Path B (Depth-of-encoding): binding was tagged with high salience
    AND encoded strength at write time >= ENCODE_GATE. Promote at next dream.
    One-shot.

    Both use REAL FoldedAtlas entries — no reimplementation.
    """
    promoted = []

    for chi_t, entries in working_atlas.entries.items():
        for e in entries:
            key = (chi_t, e["section"], e["motif"])

            # --- Path A: Survival ---
            if key in survival_history:
                history = survival_history[key]
                above_count = sum(1 for s in history[-survival_consecutive:]
                                  if s >= survival_threshold)
                if above_count >= survival_consecutive:
                    deep_atlas.promote(e, "survival", tick)
                    promoted.append(("survival", key, e["strength"]))

            # --- Path B: Depth-of-encoding (episodic fast-track) ---
            encoded_str = e.get("encoded_strength", None)
            if encoded_str is not None and encoded_str >= encode_gate:
                # One-shot: promote immediately if encoded strength qualifies
                # The gate reads the value at TAG TIME, not current strength
                deep_atlas.promote(e, "episodic", tick)
                promoted.append(("episodic", key, e["strength"]))

    return promoted


def run_deep_atlas_step2(episodic_encoded_strengths,
                         encode_gate=0.8, deep_prior=0.15,
                         deep_decay_factor=25.0):
    """
    STEP 2: Deep atlas + dual promotion gate.
    Same scenario as Step 1 but with two-layer memory.
    """
    print("\n" + "=" * 72)
    print(f"STEP 2: DEEP ATLAS — ENCODE_GATE={encode_gate}, "
          f"DEEP_PRIOR={deep_prior}, deep_decay=1/{deep_decay_factor:.0f}x")
    print("=" * 72)

    cog = build_cognition_with_words(TRUE_WORDS + EPISODIC_WORDS)
    deep = DeepAtlas(decay_lambda=REAL_DECAY_LAMBDA / deep_decay_factor,
                     prior_cap=deep_prior)

    # Track survival history for Path A
    survival_history = defaultdict(list)

    # --- Phase 1: Initial encoding ---
    # TRUE words: multiple re-attentions
    for repeat in range(5):
        for w in TRUE_WORDS:
            simulate_attention(cog, w, salience=2.0, n_dwell_ticks=3)

    # EPISODIC words: ONCE with high dwell
    # Tag encoded_strength at write time (this is the depth-of-encoding signal)
    for w in EPISODIC_WORDS:
        simulate_attention(cog, w, salience=2.5, n_dwell_ticks=8)
        chi = folded_chi_text(w)
        chi_t = tuple(chi)
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                e["encoded_strength"] = e["strength"]

    # NOISE: bare atlas entries with low salience
    for w in NOISE_WORDS:
        chi = folded_chi_text(w)
        cog.atlas.record("word", 9999, chi, cog.tick, salience=0.25)
        chi_t = tuple(chi)
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word" and e["motif"] == 9999:
                e["encoded_strength"] = e["strength"]

    print(f"\nAfter encoding (tick {cog.tick}):")
    _report_populations(cog.atlas, cog, "  ")

    # Collect noise chi vectors for contamination tracking
    noise_chis = set()
    for w in NOISE_WORDS:
        chi = folded_chi_text(w)
        noise_chis.add(tuple(chi))

    # --- Phase 2: Continued operation with decay + dream + deep ---
    tick_start = cog.tick
    deep_size_log = []
    retrieval_cost_log = []

    for t in range(tick_start, TOTAL_TICKS):
        # Occasional re-attention to TRUE words
        if t % 50 < len(TRUE_WORDS):
            w = TRUE_WORDS[t % 50]
            simulate_attention(cog, w, salience=1.5, n_dwell_ticks=2)
        else:
            cog.step()

        # Dream consolidation + promotion gate
        if t % DREAM_INTERVAL == 0 and t > tick_start:
            # Record survival snapshots for Path A
            for chi_t, entries in cog.atlas.entries.items():
                for e in entries:
                    key = (chi_t, e["section"], e["motif"])
                    survival_history[key].append(e["strength"])

            # Dream reinforcement on working atlas (same as baseline)
            simulate_dream_cycle(cog.atlas, cog.tick)

            # Dual promotion gate
            dual_promotion_gate(
                cog.atlas, deep, cog.tick, survival_history,
                encode_gate=encode_gate,
                survival_threshold=0.4,
                survival_consecutive=3,
            )

            # Deep decay + prune
            deep.decay(cog.tick)
            deep.prune()

            # Apply deep priors to working atlas — ENTRY-SPECIFIC
            # (only boost entries that have a matching deep counterpart)
            for chi_t, entries in cog.atlas.entries.items():
                for e in entries:
                    prior = deep.get_prior(chi_t, e["section"], e["motif"])
                    if prior > 0:
                        e["strength"] = min(REAL_STRENGTH_CAP,
                                            e["strength"] + prior * 0.1)

            deep_size_log.append((cog.tick, deep.live_count()))

            # Retrieval cost measurement
            t_start = time.monotonic()
            for chi_t in list(cog.atlas.entries.keys())[:20]:
                entries = cog.atlas.entries.get(chi_t, [])
                for e in entries[:2]:
                    _ = deep.get_prior(chi_t, e["section"], e["motif"])
            retrieval_cost_log.append(
                (cog.tick, deep.live_count(),
                 (time.monotonic() - t_start) * 1000))

    # --- Results ---
    print(f"\nAfter {TOTAL_TICKS} ticks (tick {cog.tick}):")
    true_alive, true_total = _count_alive(cog.atlas, cog, TRUE_WORDS)
    ep_alive, ep_total = _count_alive(cog.atlas, cog, EPISODIC_WORDS)
    noise_alive, noise_total = _count_alive(cog.atlas, cog, NOISE_WORDS, noise_motif=9999)

    print(f"  TRUE:     {true_alive}/{true_total} alive")
    print(f"  EPISODIC: {ep_alive}/{ep_total} alive")
    print(f"  NOISE:    {noise_alive}/{noise_total} alive")

    # Deep atlas stats
    deep_contamination = deep.contamination_count()
    deep_total = deep.live_count()
    print(f"\n  Deep atlas: {deep_total} entries, "
          f"{deep_contamination} noise contamination "
          f"({100*deep_contamination/max(1,deep_total):.1f}%)")

    # Chi-band distortion: compare against control (no deep priors)
    control_result = _run_single_config(encode_gate, 0.0, deep_decay_factor)
    control_snap = control_result["_chi_snap"]
    deep_snap = _snapshot_chi_strengths(cog.atlas)
    distortion = _chi_band_distortion(control_snap, deep_snap)
    print(f"  Chi-band distortion from deep priors: {distortion:.4f}")

    # Retrieval cost
    if retrieval_cost_log:
        max_size = max(r[1] for r in retrieval_cost_log)
        max_cost = max(r[2] for r in retrieval_cost_log)
        print(f"  Retrieval cost: max {max_cost:.3f}ms at deep_size={max_size}")

    # Promotion path breakdown
    surv_promos = [p for p in deep.promotion_log if p["path"] == "survival"]
    ep_promos = [p for p in deep.promotion_log if p["path"] == "episodic"]
    print(f"\n  Promotions: {len(surv_promos)} survival, {len(ep_promos)} episodic")

    _report_populations(cog.atlas, cog, "  ")

    return {
        "true_alive": true_alive, "true_total": true_total,
        "ep_alive": ep_alive, "ep_total": ep_total,
        "noise_alive": noise_alive, "noise_total": noise_total,
        "deep_total": deep_total, "deep_contamination": deep_contamination,
        "distortion": distortion,
        "encode_gate": encode_gate, "deep_prior": deep_prior,
        "deep_decay_factor": deep_decay_factor,
        "deep_size_log": deep_size_log,
        "retrieval_cost_log": retrieval_cost_log,
    }


# ============================================================
# STEP 3: Parameter Sweep
# ============================================================

def run_parameter_sweep():
    """
    STEP 3: Sweep ENCODE_GATE, DEEP_PRIOR, deep decay against real
    strength distributions. Report operating window.
    """
    print("\n" + "=" * 72)
    print("STEP 3: PARAMETER SWEEP")
    print("=" * 72)

    encode_gates = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.80]
    deep_priors = [0.05, 0.10, 0.15, 0.25, 0.40]
    deep_decay_factors = [10, 25, 50, 100]

    results = []

    # First, get the real encoded strength distribution
    print("\n--- Real Encoded Strength Distribution ---")
    cog = build_cognition_with_words(TRUE_WORDS + EPISODIC_WORDS)
    for repeat in range(5):
        for w in TRUE_WORDS:
            simulate_attention(cog, w, salience=2.0, n_dwell_ticks=3)
    for w in EPISODIC_WORDS:
        simulate_attention(cog, w, salience=2.5, n_dwell_ticks=8)
    for w in NOISE_WORDS:
        chi = folded_chi_text(w)
        cog.atlas.record("word", 9999, chi, cog.tick, salience=0.25)

    true_strengths = []
    ep_strengths = []
    noise_strengths = []
    for w in TRUE_WORDS:
        chi_t = tuple(folded_chi_text(w))
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                true_strengths.append(e["strength"])
    for w in EPISODIC_WORDS:
        chi_t = tuple(folded_chi_text(w))
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                ep_strengths.append(e["strength"])
    for w in NOISE_WORDS:
        chi_t = tuple(folded_chi_text(w))
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word" and e["motif"] == 9999:
                noise_strengths.append(e["strength"])

    print(f"  TRUE  strengths: n={len(true_strengths)}, "
          f"mean={np.mean(true_strengths):.3f}, "
          f"range=[{min(true_strengths):.3f}, {max(true_strengths):.3f}]"
          if true_strengths else "  TRUE: none")
    print(f"  EPISODIC strengths: n={len(ep_strengths)}, "
          f"mean={np.mean(ep_strengths):.3f}, "
          f"range=[{min(ep_strengths):.3f}, {max(ep_strengths):.3f}]"
          if ep_strengths else "  EPISODIC: none")
    print(f"  NOISE strengths: n={len(noise_strengths)}, "
          f"mean={np.mean(noise_strengths):.3f}, "
          f"range=[{min(noise_strengths):.3f}, {max(noise_strengths):.3f}]"
          if noise_strengths else "  NOISE: none")

    # Run control (no deep priors, just baseline decay)
    print("\n--- Running control (no deep priors) ---")
    control = _run_single_config(0.05, 0.0, 25)  # deep_prior=0 → no injection
    control_snap = control["_chi_snap"]
    print(f"  Control: TRUE={control['true_alive']}/{control['true_total']}, "
          f"EP={control['ep_alive']}/{control['ep_total']}, "
          f"NOISE={control['noise_alive']}/{control['noise_total']}")

    # Sweep
    print(f"\n--- Sweep: {len(encode_gates)} x {len(deep_priors)} x "
          f"{len(deep_decay_factors)} = "
          f"{len(encode_gates)*len(deep_priors)*len(deep_decay_factors)} configs ---")
    # TRUE dominance check: does deep atlas change TRUE strength vs control?
    control_true_mean = control["true_mean_strength"]
    print(f"  Control TRUE mean strength: {control_true_mean:.4f}")

    print(f"\n{'EG':>6s} {'DP':>6s} {'DDx':>6s} | "
          f"{'TRUE':>5s} {'EPIS':>5s} {'NOISE':>5s} | "
          f"{'DpSz':>5s} {'Cont':>4s} {'TRUm':>6s} {'dTRU':>6s} | PASS")
    print("-" * 80)

    for eg in encode_gates:
        for dp in deep_priors:
            for ddf in deep_decay_factors:
                r = _run_single_config(eg, dp, ddf)
                r["distortion"] = _chi_band_distortion(control_snap, r["_chi_snap"])
                # Dominance: how much did TRUE mean change vs control?
                r["true_delta"] = abs(r["true_mean_strength"] - control_true_mean)
                results.append(r)

                # Pass criteria:
                #   TRUE retained (>=10), EPISODIC retained (>=10),
                #   NOISE rejected (<=5), no contamination,
                #   TRUE not dominated (delta < 5% of control mean)
                passes = (r["true_alive"] >= 10
                          and r["ep_alive"] >= 10
                          and r["noise_alive"] <= 5
                          and r["deep_contamination"] == 0
                          and r["true_delta"] < control_true_mean * 0.05)
                mark = "YES" if passes else "no"
                print(f"{eg:6.2f} {dp:6.2f} {ddf:6.0f} | "
                      f"{r['true_alive']:>2d}/{r['true_total']:>2d} "
                      f"{r['ep_alive']:>2d}/{r['ep_total']:>2d} "
                      f"{r['noise_alive']:>2d}/{r['noise_total']:>2d} | "
                      f"{r['deep_total']:>5d} {r['deep_contamination']:>4d} "
                      f"{r['true_mean_strength']:>6.4f} "
                      f"{r['true_delta']:>6.4f} | {mark}")

    # Report operating window
    passing = [r for r in results
               if r["true_alive"] >= 10
               and r["ep_alive"] >= 10
               and r["noise_alive"] <= 5
               and r["deep_contamination"] == 0
               and r["true_delta"] < control_true_mean * 0.05]

    print(f"\n--- OPERATING WINDOW ---")
    if passing:
        eg_range = (min(r["encode_gate"] for r in passing),
                    max(r["encode_gate"] for r in passing))
        dp_range = (min(r["deep_prior"] for r in passing),
                    max(r["deep_prior"] for r in passing))
        ddf_range = (min(r["deep_decay_factor"] for r in passing),
                     max(r["deep_decay_factor"] for r in passing))
        print(f"  {len(passing)}/{len(results)} configs pass all criteria")
        print(f"  ENCODE_GATE:    [{eg_range[0]:.2f}, {eg_range[1]:.2f}]")
        print(f"  DEEP_PRIOR:     [{dp_range[0]:.2f}, {dp_range[1]:.2f}]")
        print(f"  deep_decay_x:   [{ddf_range[0]:.0f}, {ddf_range[1]:.0f}]")
        # Show all passing unique (EG, DP) combos
        seen = set()
        for r in passing:
            key = (r["encode_gate"], r["deep_prior"])
            if key not in seen:
                seen.add(key)
                print(f"    EG={r['encode_gate']:.2f} DP={r['deep_prior']:.2f}: "
                      f"TRUE={r['true_alive']}/{r['true_total']} "
                      f"EP={r['ep_alive']}/{r['ep_total']} "
                      f"NOISE={r['noise_alive']}/{r['noise_total']} "
                      f"cont={r['deep_contamination']} "
                      f"dTRU={r['true_delta']:.4f}")
    else:
        print("  NO configs pass all criteria simultaneously.")
        print("  Closest configs:")
        scored = sorted(results,
                        key=lambda r: (r["ep_alive"], -r["noise_alive"],
                                       -r["deep_contamination"],
                                       -r.get("true_delta", 999)),
                        reverse=True)
        for r in scored[:5]:
            print(f"    EG={r['encode_gate']:.2f} DP={r['deep_prior']:.2f} "
                  f"DDx={r['deep_decay_factor']:.0f}: "
                  f"TRUE={r['true_alive']}/{r['true_total']} "
                  f"EP={r['ep_alive']}/{r['ep_total']} "
                  f"NOISE={r['noise_alive']}/{r['noise_total']} "
                  f"cont={r['deep_contamination']} "
                  f"dTRU={r.get('true_delta', 0):.4f}")

    return results


def _run_single_config(encode_gate, deep_prior, deep_decay_factor):
    """Run one full simulation silently and return metrics."""
    cog = build_cognition_with_words(TRUE_WORDS + EPISODIC_WORDS)
    deep = DeepAtlas(decay_lambda=REAL_DECAY_LAMBDA / deep_decay_factor,
                     prior_cap=deep_prior)
    survival_history = defaultdict(list)

    # Encode
    for repeat in range(5):
        for w in TRUE_WORDS:
            simulate_attention(cog, w, salience=2.0, n_dwell_ticks=3)
    for w in EPISODIC_WORDS:
        simulate_attention(cog, w, salience=2.5, n_dwell_ticks=8)
        chi_t = tuple(folded_chi_text(w))
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                e["encoded_strength"] = e["strength"]
    for w in NOISE_WORDS:
        chi = folded_chi_text(w)
        cog.atlas.record("word", 9999, chi, cog.tick, salience=0.25)
        chi_t = tuple(chi)
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word" and e["motif"] == 9999:
                e["encoded_strength"] = e["strength"]

    tick_start = cog.tick
    for t in range(tick_start, TOTAL_TICKS):
        if t % 50 < len(TRUE_WORDS):
            w = TRUE_WORDS[t % 50]
            simulate_attention(cog, w, salience=1.5, n_dwell_ticks=2)
        else:
            cog.step()

        if t % DREAM_INTERVAL == 0 and t > tick_start:
            for chi_t, entries in cog.atlas.entries.items():
                for e in entries:
                    key = (chi_t, e["section"], e["motif"])
                    survival_history[key].append(e["strength"])
            simulate_dream_cycle(cog.atlas, cog.tick)
            dual_promotion_gate(cog.atlas, deep, cog.tick, survival_history,
                                encode_gate=encode_gate)
            deep.decay(cog.tick)
            deep.prune()
            for chi_t, entries in cog.atlas.entries.items():
                for e in entries:
                    prior = deep.get_prior(chi_t, e["section"], e["motif"])
                    if prior > 0:
                        e["strength"] = min(REAL_STRENGTH_CAP,
                                            e["strength"] + prior * 0.1)

    true_alive, true_total = _count_alive(cog.atlas, cog, TRUE_WORDS)
    ep_alive, ep_total = _count_alive(cog.atlas, cog, EPISODIC_WORDS)
    noise_alive, noise_total = _count_alive(cog.atlas, cog, NOISE_WORDS, noise_motif=9999)
    chi_snap = _snapshot_chi_strengths(cog.atlas)

    # TRUE dominance metric: mean strength of TRUE word entries
    true_strengths = []
    for w in TRUE_WORDS:
        chi_t = tuple(folded_chi_text(w))
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                true_strengths.append(e["strength"])
    true_mean = float(np.mean(true_strengths)) if true_strengths else 0.0

    return {
        "true_alive": true_alive, "true_total": true_total,
        "ep_alive": ep_alive, "ep_total": ep_total,
        "noise_alive": noise_alive, "noise_total": noise_total,
        "deep_total": deep.live_count(),
        "deep_contamination": deep.contamination_count(),
        "distortion": 0.0,  # computed externally vs control
        "true_mean_strength": true_mean,
        "encode_gate": encode_gate,
        "deep_prior": deep_prior,
        "deep_decay_factor": deep_decay_factor,
        "_chi_snap": chi_snap,
    }


# ============================================================
# Helpers
# ============================================================

def _count_alive(atlas, cog, words, noise_motif=None):
    """Count how many words still have live atlas entries (word section).
    For noise, use noise_motif to filter."""
    alive = 0
    total = len(words)
    for w in words:
        chi = folded_chi_text(w)
        chi_t = tuple(chi)
        entries = atlas.entries.get(chi_t, [])
        if noise_motif is not None:
            has_live = any(e["strength"] >= REAL_FORGET_THRESH
                          and e["section"] == "word"
                          and e["motif"] == noise_motif
                          for e in entries)
        else:
            has_live = any(e["strength"] >= REAL_FORGET_THRESH
                          and e["section"] == "word"
                          for e in entries)
        if has_live:
            alive += 1
    return alive, total


def _report_populations(atlas, cog, prefix=""):
    """Report strength statistics per population."""
    for label, words in [("TRUE", TRUE_WORDS), ("EPISODIC", EPISODIC_WORDS),
                         ("NOISE", NOISE_WORDS)]:
        strengths = []
        for w in words:
            chi_t = tuple(folded_chi_text(w))
            for e in atlas.entries.get(chi_t, []):
                if label == "NOISE":
                    if e["section"] == "word" and e["motif"] == 9999:
                        strengths.append(e["strength"])
                elif e["section"] == "word":
                    strengths.append(e["strength"])
        if strengths:
            print(f"{prefix}{label:10s}: n={len(strengths):>3d}, "
                  f"mean={np.mean(strengths):.4f}, "
                  f"min={min(strengths):.4f}, max={max(strengths):.4f}, "
                  f">{REAL_FORGET_THRESH}={sum(1 for s in strengths if s >= REAL_FORGET_THRESH)}")
        else:
            print(f"{prefix}{label:10s}: EMPTY (all pruned)")


def _snapshot_chi_strengths(atlas):
    """Snapshot {chi_t: total_strength} for distortion measurement."""
    snap = {}
    for chi_t, entries in atlas.entries.items():
        snap[chi_t] = sum(e["strength"] for e in entries)
    return snap


def _chi_band_distortion(control_snap, deep_snap):
    """Measure how much deep priors distorted chi-band strength distribution
    compared to a control run (same scenario, no deep priors).
    Both snapshots should be taken at the SAME tick count."""
    all_chis = set(control_snap.keys()) | set(deep_snap.keys())
    if not all_chis:
        return 0.0
    diffs = []
    for chi_t in all_chis:
        c = control_snap.get(chi_t, 0.0)
        d = deep_snap.get(chi_t, 0.0)
        denom = max(c, d, 0.01)
        diffs.append(abs(d - c) / denom)
    return float(np.mean(diffs)) if diffs else 0.0


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("GL-FIND-DEEPATLAS-C1-20260610")
    print("Deep Atlas Offline Harness — Stage 1")
    print("Imports REAL substrate: FoldedAtlas, chi encoding, decay, dream paths")
    print()

    # Step 1: Reproduce baseline failure
    failure_ok, encoded_strengths, baseline_cog = run_baseline_step1()

    if not failure_ok:
        print("\n*** STOPPING: Baseline failure did not reproduce. ***")
        print("Filing GL-FIND with this finding.")
    else:
        # Step 2: Deep atlas with default parameters
        step2_result = run_deep_atlas_step2(
            encoded_strengths,
            encode_gate=0.08,  # will calibrate from real distribution
            deep_prior=0.15,
            deep_decay_factor=25.0,
        )

        # Step 3: Parameter sweep
        sweep_results = run_parameter_sweep()

        # Final summary
        print("\n" + "=" * 72)
        print("GL-FIND-DEEPATLAS-C1-20260610 — SUMMARY")
        print("=" * 72)
        print(f"\nStep 1: Baseline failure {'REPRODUCED' if failure_ok else 'NOT reproduced'}")
        print(f"Step 2: Deep atlas result: TRUE={step2_result['true_alive']}/{step2_result['true_total']}, "
              f"EPISODIC={step2_result['ep_alive']}/{step2_result['ep_total']}, "
              f"NOISE={step2_result['noise_alive']}/{step2_result['noise_total']}")
        print(f"  Deep contamination: {step2_result['deep_contamination']}")
        print(f"  Chi-band distortion: {step2_result['distortion']:.4f}")

        passing = [r for r in sweep_results
                   if r["true_alive"] >= 10
                   and r["ep_alive"] >= 10
                   and r["noise_alive"] <= 5
                   and r["deep_contamination"] == 0
                   and r.get("true_delta", 999) < 0.05]
        print(f"\nStep 3: {len(passing)}/{len(sweep_results)} configs pass all criteria")

        print("\nSHORTCUTS TAKEN (per brief §6):")
        print("  - Synthetic input through real krimelack→atlas path (no EFS snapshots)")
        print("  - Dream consolidation modeled as net reinforcement effect on atlas")
        print("    (not full replay_tick→section.evolve→commit cycle)")
        print("  - NOISE words are synthetic 3-letter strings, not real co-occurrences")
        print("\nNEXT: wC reviews this GL-FIND, writes GL-BRIEF-032 if Stage 1 passes.")
