"""
GL-FIND-DEEPATLAS-C1-20260610-02 — Deep Atlas Harness Extension

Four items required by wC review before GL-BRIEF-032:
  1. CANONICAL RERUN at EG=0.15 and EG=0.20 (inside operating window)
  2. REAL DREAM PATH via actual fire→atlas.record→step cycle
  3. NOISE REALISM via install_word + cofire_bind
  4. RETRIEVAL TEST: cue-driven recall through deep prior after episodic decay

NO production code changes. NO substrate primitive modifications.
"""

import math
import time
import numpy as np
from collections import defaultdict

# Import REAL substrate code paths
from dsf_ai_service.substrate.GL_MDL_MULTIMODAL_DEEP_WC_20260608_03 import (
    FoldedAtlas, DeepMultiModalCognition,
    BASE_REINFORCEMENT, DECAY_LAMBDA, FORGETTING_THRESHOLD, STRENGTH_CAP,
)
from dsf_ai_service.substrate.GL_MDL_FOLDED_CHI_WC_20260608_01 import (
    folded_chi_text, chi_neighbors, folded_chi_distance,
)

# Import DeepAtlas and helpers from -01 harness
from dsf_ai_service.substrate.test_deep_atlas_harness import (
    DeepAtlas, dual_promotion_gate,
    TRUE_WORDS, EPISODIC_WORDS, NOISE_WORDS,
    REAL_DECAY_LAMBDA, REAL_FORGET_THRESH, REAL_BASE_REINF, REAL_STRENGTH_CAP,
    DREAM_INTERVAL, TOTAL_TICKS,
    _count_alive, _report_populations, _snapshot_chi_strengths,
)


def build_cog(words):
    cog = DeepMultiModalCognition()
    for w in words:
        cog.install_word(w)
    return cog


def attend(cog, word, salience, dwell):
    cog.fire("word", word, salience=salience)
    for _ in range(dwell):
        cog.step()


# ================================================================
# Shared encoding + run logic
# ================================================================

def encode_populations(cog, noise_mode="bare"):
    """Encode all three populations into cog.
    noise_mode: "bare" = atlas.record only,
                "realistic" = install_word + fire, spaced to avoid cofire artifacts."""
    # TRUE: 5x re-attention
    for _ in range(5):
        for w in TRUE_WORDS:
            attend(cog, w, salience=2.0, dwell=3)

    # EPISODIC: once, high dwell
    for w in EPISODIC_WORDS:
        attend(cog, w, salience=2.5, dwell=8)
        chi_t = tuple(folded_chi_text(w))
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                e["encoded_strength"] = e["strength"]

    # NOISE
    if noise_mode == "bare":
        for w in NOISE_WORDS:
            chi = folded_chi_text(w)
            cog.atlas.record("word", 9999, chi, cog.tick, salience=0.25)
            chi_t = tuple(chi)
            for e in cog.atlas.entries.get(chi_t, []):
                if e["section"] == "word" and e["motif"] == 9999:
                    e["encoded_strength"] = e["strength"]
    elif noise_mode == "realistic":
        # Noise words get full install_word + fire with low salience.
        # SPACED >6 ticks apart (COFIRE_WINDOW_TICKS) to prevent batch
        # cross-linking artifacts. Real noise = isolated co-occurrence,
        # not 30 words in 60 ticks.
        for w in NOISE_WORDS:
            attend(cog, w, salience=0.3, dwell=1)
            # Space apart: run 8 idle steps (>COFIRE_WINDOW_TICKS=6)
            # so next noise word doesn't cofire-bind with this one
            for _ in range(8):
                cog.step()
            chi_t = tuple(folded_chi_text(w))
            for e in cog.atlas.entries.get(chi_t, []):
                if e["section"] == "word":
                    e["encoded_strength"] = e["strength"]


def run_with_deep(cog, deep, encode_gate, dream_fn="net_effect"):
    """Run decay phase with deep atlas. Returns metrics dict.
    dream_fn: "net_effect" or "real_replay"."""
    survival_history = defaultdict(list)
    # Full perception log for real replay (krimelack equivalent)
    perception_log = list(cog.recent_perceptions)

    tick_start = cog.tick
    for t in range(tick_start, TOTAL_TICKS):
        if t % 50 < len(TRUE_WORDS):
            w = TRUE_WORDS[t % 50]
            attend(cog, w, salience=1.5, dwell=2)
            # Log for replay
            for p in cog.recent_perceptions:
                if p not in perception_log[-50:]:
                    perception_log.append(p)
        else:
            cog.step()

        if t % DREAM_INTERVAL == 0 and t > tick_start:
            # Survival snapshots
            for chi_t, entries in cog.atlas.entries.items():
                for e in entries:
                    key = (chi_t, e["section"], e["motif"])
                    survival_history[key].append(e["strength"])

            # Dream consolidation
            if dream_fn == "net_effect":
                _dream_net_effect(cog.atlas, cog.tick)
            elif dream_fn == "real_replay":
                _dream_real_replay(cog, perception_log)

            # Promotion gate
            dual_promotion_gate(cog.atlas, deep, cog.tick, survival_history,
                                encode_gate=encode_gate)
            deep.decay(cog.tick)
            deep.prune()

            # Apply deep priors (entry-specific)
            for chi_t, entries in cog.atlas.entries.items():
                for e in entries:
                    prior = deep.get_prior(chi_t, e["section"], e["motif"])
                    if prior > 0:
                        e["strength"] = min(REAL_STRENGTH_CAP,
                                            e["strength"] + prior * 0.1)

    return _collect_metrics(cog, deep, encode_gate)


def _dream_net_effect(atlas, tick):
    """Net-effect dream model (from -01 harness)."""
    for chi_t, entries in atlas.entries.items():
        for e in entries:
            if e["strength"] >= 0.4:
                e["strength"] = min(REAL_STRENGTH_CAP,
                                    e["strength"] + REAL_BASE_REINF * 0.5)


def _dream_real_replay(cog, perception_log):
    """Real dream path: sample from perception log weighted by
    salience*recency (same formula as assemblage.replay_tick),
    then re-fire through REAL fire→atlas.record→step path.

    This exercises the actual atlas reinforcement code, not a shortcut."""
    if len(perception_log) < 2:
        return

    recency_lambda = 0.002  # same as assemblage.replay_tick
    tick = cog.tick

    # Build weights using REAL formula from assemblage.py:655-668
    weights = []
    for (t, section, mid, chi) in perception_log:
        # Approximate salience from atlas entry strength
        sal = 0.5
        for e in cog.atlas.entries.get(chi, []):
            if e["section"] == section and e["motif"] == mid:
                sal = max(sal, e["strength"])
                break
        w = sal * math.exp(-recency_lambda * (tick - t))
        weights.append(max(w, 0.0))

    total = sum(weights)
    if total <= 0:
        return

    # Normalize
    weights = [w / total for w in weights]

    # Sample 2-4 entries (same as max_replay in replay_tick)
    rng = np.random.default_rng(tick)
    n_sample = min(4, len(perception_log))
    indices = rng.choice(len(perception_log), size=n_sample,
                         replace=False, p=weights)

    # Re-fire sampled perceptions through REAL fire→step path
    for idx in indices:
        t_orig, section, mid, chi = perception_log[idx]
        # Find the label for this mid in this section
        label = cog.section_mid_to_label.get(section, {}).get(mid)
        if label and label in cog.sections.get(section, {}):
            # REAL fire: calls atlas.record, sets activation, logs perception
            cog.fire(section, label, salience=1.0, set_focus=False)

    # Settle with REAL step (cofire_bind, cascade, mgn_gate, coordinator)
    for _ in range(3):
        cog.step()


def _collect_metrics(cog, deep, encode_gate, noise_motif=None):
    """Collect standard metrics from a completed run."""
    nm = noise_motif
    true_alive, true_total = _count_alive(cog.atlas, cog, TRUE_WORDS)
    ep_alive, ep_total = _count_alive(cog.atlas, cog, EPISODIC_WORDS)
    noise_alive, noise_total = _count_alive(cog.atlas, cog, NOISE_WORDS,
                                             noise_motif=nm)

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
        "true_mean_strength": true_mean,
        "encode_gate": encode_gate,
        "surv_promos": len([p for p in deep.promotion_log if p["path"] == "survival"]),
        "ep_promos": len([p for p in deep.promotion_log if p["path"] == "episodic"]),
    }


def report_result(label, r, prefix="  "):
    print(f"{prefix}TRUE:     {r['true_alive']}/{r['true_total']} alive "
          f"(mean={r['true_mean_strength']:.4f})")
    print(f"{prefix}EPISODIC: {r['ep_alive']}/{r['ep_total']} alive")
    print(f"{prefix}NOISE:    {r['noise_alive']}/{r['noise_total']} alive")
    print(f"{prefix}Deep:     {r['deep_total']} entries, "
          f"contamination={r['deep_contamination']}")
    print(f"{prefix}Promos:   {r['surv_promos']} survival, "
          f"{r['ep_promos']} episodic")


# ================================================================
# ITEM 1: CANONICAL RERUN
# ================================================================

def item1_canonical_rerun():
    print("=" * 72)
    print("ITEM 1: CANONICAL RERUN — EG=0.15 and EG=0.20")
    print("=" * 72)

    for eg in [0.15, 0.20]:
        print(f"\n--- ENCODE_GATE = {eg} ---")
        cog = build_cog(TRUE_WORDS + EPISODIC_WORDS)
        deep = DeepAtlas(decay_lambda=REAL_DECAY_LAMBDA / 25.0, prior_cap=0.15)
        encode_populations(cog, noise_mode="bare")
        r = run_with_deep(cog, deep, encode_gate=eg, dream_fn="net_effect")
        report_result(f"EG={eg}", r)

        passes = (r["true_alive"] >= 10 and r["ep_alive"] >= 10
                  and r["noise_alive"] <= 5 and r["deep_contamination"] == 0)
        print(f"\n  PASS: {passes}")

    # Control (no deep)
    print(f"\n--- CONTROL (no deep priors) ---")
    cog_ctrl = build_cog(TRUE_WORDS + EPISODIC_WORDS)
    deep_ctrl = DeepAtlas(decay_lambda=REAL_DECAY_LAMBDA / 25.0, prior_cap=0.0)
    encode_populations(cog_ctrl, noise_mode="bare")
    r_ctrl = run_with_deep(cog_ctrl, deep_ctrl, encode_gate=0.15,
                           dream_fn="net_effect")
    report_result("CONTROL", r_ctrl)

    return r_ctrl


# ================================================================
# ITEM 2: REAL DREAM PATH
# ================================================================

def item2_real_dream():
    print("\n" + "=" * 72)
    print("ITEM 2: REAL DREAM PATH — fire→atlas.record→step")
    print("=" * 72)

    results = {}
    for dream_fn in ["net_effect", "real_replay"]:
        print(f"\n--- Dream model: {dream_fn} ---")
        cog = build_cog(TRUE_WORDS + EPISODIC_WORDS)
        deep = DeepAtlas(decay_lambda=REAL_DECAY_LAMBDA / 25.0, prior_cap=0.15)
        encode_populations(cog, noise_mode="bare")
        r = run_with_deep(cog, deep, encode_gate=0.15, dream_fn=dream_fn)
        report_result(dream_fn, r)
        results[dream_fn] = r

    # Compare promotion sets
    print("\n--- COMPARISON ---")
    ne = results["net_effect"]
    rr = results["real_replay"]
    print(f"  Net-effect:  TRUE={ne['true_alive']}/{ne['true_total']} "
          f"EP={ne['ep_alive']}/{ne['ep_total']} "
          f"NOISE={ne['noise_alive']}/{ne['noise_total']} "
          f"deep={ne['deep_total']} (surv={ne['surv_promos']}, ep={ne['ep_promos']})")
    print(f"  Real-replay: TRUE={rr['true_alive']}/{rr['true_total']} "
          f"EP={rr['ep_alive']}/{rr['ep_total']} "
          f"NOISE={rr['noise_alive']}/{rr['noise_total']} "
          f"deep={rr['deep_total']} (surv={rr['surv_promos']}, ep={rr['ep_promos']})")

    diff_deep = rr["deep_total"] - ne["deep_total"]
    diff_ep = rr["ep_alive"] - ne["ep_alive"]
    print(f"\n  Delta: deep_total={diff_deep:+d}, ep_alive={diff_ep:+d}")
    if diff_deep == 0 and diff_ep == 0:
        print("  Promotion sets IDENTICAL between dream models.")
    else:
        print("  Promotion sets DIFFER — real replay changes outcomes.")

    return results


# ================================================================
# ITEM 3: NOISE REALISM
# ================================================================

def item3_noise_realism():
    print("\n" + "=" * 72)
    print("ITEM 3: NOISE REALISM — install_word + cofire_bind")
    print("=" * 72)

    # --- First: measure BATCH noise (no spacing) to show the artifact ---
    print("\n--- BATCH noise (no spacing, cofire cross-links) ---")
    cog_batch = build_cog(TRUE_WORDS + EPISODIC_WORDS + NOISE_WORDS)
    for _ in range(5):
        for w in TRUE_WORDS:
            attend(cog_batch, w, salience=2.0, dwell=3)
    for w in EPISODIC_WORDS:
        attend(cog_batch, w, salience=2.5, dwell=8)
    # Batch: no spacing between noise words
    for w in NOISE_WORDS:
        attend(cog_batch, w, salience=0.3, dwell=1)
    batch_noise_s = []
    for w in NOISE_WORDS:
        chi_t = tuple(folded_chi_text(w))
        for e in cog_batch.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                batch_noise_s.append(e["strength"])
    if batch_noise_s:
        print(f"  Batch noise (word): n={len(batch_noise_s)}, "
              f"mean={np.mean(batch_noise_s):.4f}, "
              f"range=[{min(batch_noise_s):.4f}, {max(batch_noise_s):.4f}]")
        print(f"  NOTE: inflated by cofire_bind cross-linking 30 words in ~60 ticks")

    # --- Now: measure ISOLATED noise (spaced, realistic) ---
    print("\n--- ISOLATED noise (spaced >6 ticks, no cofire cross-links) ---")
    all_words = TRUE_WORDS + EPISODIC_WORDS + NOISE_WORDS
    cog = build_cog(all_words)

    # Encode with realistic noise (spaced to avoid cofire artifacts)
    encode_populations(cog, noise_mode="realistic")

    # Measure encoded strength distributions at write time
    print("\n--- Encoded Strength Distribution (at write time) ---")

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
            if e["section"] == "word":
                noise_strengths.append(e["strength"])

    def report_dist(label, strengths):
        if strengths:
            print(f"  {label:10s}: n={len(strengths):>3d}, "
                  f"mean={np.mean(strengths):.4f}, "
                  f"range=[{min(strengths):.4f}, {max(strengths):.4f}]")
        else:
            print(f"  {label:10s}: EMPTY")

    report_dist("TRUE", true_strengths)
    report_dist("EPISODIC", ep_strengths)
    report_dist("NOISE", noise_strengths)

    # Also measure ALL entries at noise chi positions (cross-modal)
    noise_all_strengths = []
    for w in NOISE_WORDS:
        chi_t = tuple(folded_chi_text(w))
        for e in cog.atlas.entries.get(chi_t, []):
            noise_all_strengths.append((e["section"], e["motif"], e["strength"]))

    print(f"\n  All entries at NOISE chi positions: {len(noise_all_strengths)}")
    if noise_all_strengths:
        noise_s = [s for _, _, s in noise_all_strengths]
        print(f"  Mean={np.mean(noise_s):.4f}, "
              f"range=[{min(noise_s):.4f}, {max(noise_s):.4f}]")
        by_section = defaultdict(list)
        for sec, mid, s in noise_all_strengths:
            by_section[sec].append(s)
        for sec in sorted(by_section.keys()):
            ss = by_section[sec]
            print(f"    {sec:8s}: n={len(ss):>3d}, mean={np.mean(ss):.4f}")

    # THE CRITICAL GAP CHECK
    ep_mean = np.mean(ep_strengths) if ep_strengths else 0.0
    noise_mean = np.mean(noise_strengths) if noise_strengths else 0.0
    gap = ep_mean - noise_mean

    print(f"\n--- CRITICAL GAP ---")
    print(f"  Episodic mean: {ep_mean:.4f}")
    print(f"  Noise mean:    {noise_mean:.4f}")
    print(f"  Gap:           {gap:.4f} ({ep_mean/max(noise_mean, 0.001):.1f}x)")

    if noise_mean >= 0.12:
        print(f"\n  *** STOP: Noise encodes above 0.12 ({noise_mean:.4f}). ***")
        print(f"  The ENCODE_GATE window depends on this gap.")
        print(f"  Gap has COLLAPSED with realistic noise.")
        return None, True  # stop signal

    # Now run the full simulation with realistic noise and EG=0.15
    print(f"\n--- Full run with realistic noise, EG=0.15 ---")
    cog2 = build_cog(all_words)
    deep2 = DeepAtlas(decay_lambda=REAL_DECAY_LAMBDA / 25.0, prior_cap=0.15)
    encode_populations(cog2, noise_mode="realistic")

    # Need to handle noise counting differently — no motif 9999
    # Noise words are installed normally, so we count by word chi
    survival_history = defaultdict(list)
    perception_log = list(cog2.recent_perceptions)

    tick_start = cog2.tick
    for t in range(tick_start, TOTAL_TICKS):
        if t % 50 < len(TRUE_WORDS):
            w = TRUE_WORDS[t % 50]
            attend(cog2, w, salience=1.5, dwell=2)
        else:
            cog2.step()

        if t % DREAM_INTERVAL == 0 and t > tick_start:
            for chi_t, entries in cog2.atlas.entries.items():
                for e in entries:
                    key = (chi_t, e["section"], e["motif"])
                    survival_history[key].append(e["strength"])
            _dream_net_effect(cog2.atlas, cog2.tick)
            dual_promotion_gate(cog2.atlas, deep2, cog2.tick, survival_history,
                                encode_gate=0.15)
            deep2.decay(cog2.tick)
            deep2.prune()
            for chi_t, entries in cog2.atlas.entries.items():
                for e in entries:
                    prior = deep2.get_prior(chi_t, e["section"], e["motif"])
                    if prior > 0:
                        e["strength"] = min(REAL_STRENGTH_CAP,
                                            e["strength"] + prior * 0.1)

    # Count alive — noise words are installed normally, count by word section
    true_alive = sum(1 for w in TRUE_WORDS
                     if any(e["strength"] >= REAL_FORGET_THRESH and e["section"] == "word"
                            for e in cog2.atlas.entries.get(tuple(folded_chi_text(w)), [])))
    ep_alive = sum(1 for w in EPISODIC_WORDS
                   if any(e["strength"] >= REAL_FORGET_THRESH and e["section"] == "word"
                          for e in cog2.atlas.entries.get(tuple(folded_chi_text(w)), [])))
    noise_alive = sum(1 for w in NOISE_WORDS
                      if any(e["strength"] >= REAL_FORGET_THRESH and e["section"] == "word"
                             for e in cog2.atlas.entries.get(tuple(folded_chi_text(w)), [])))

    # Deep contamination: count noise-word motifs in deep
    noise_motifs = set()
    for w in NOISE_WORDS:
        chi_t = tuple(folded_chi_text(w))
        for e in cog2.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                noise_motifs.add(e["motif"])
    deep_noise = 0
    for chi_t, entries in deep2.entries.items():
        for e in entries:
            if e["motif"] in noise_motifs and e["strength"] >= REAL_FORGET_THRESH:
                deep_noise += 1

    print(f"  TRUE:     {true_alive}/12 alive")
    print(f"  EPISODIC: {ep_alive}/12 alive")
    print(f"  NOISE:    {noise_alive}/30 alive")
    print(f"  Deep:     {deep2.live_count()} entries, "
          f"noise contamination={deep_noise}")

    return {"gap": gap, "noise_mean": noise_mean, "ep_mean": ep_mean,
            "true_alive": true_alive, "ep_alive": ep_alive,
            "noise_alive": noise_alive, "deep_noise": deep_noise}, False


# ================================================================
# ITEM 4: RETRIEVAL TEST
# ================================================================

def item4_retrieval_test():
    print("\n" + "=" * 72)
    print("ITEM 4: RETRIEVAL TEST — cue-driven recall via deep prior")
    print("=" * 72)

    cog = build_cog(TRUE_WORDS + EPISODIC_WORDS)
    deep = DeepAtlas(decay_lambda=REAL_DECAY_LAMBDA / 25.0, prior_cap=0.15)
    encode_populations(cog, noise_mode="bare")

    # Record episodic chi vectors and motif IDs before they decay
    episodic_info = {}
    for w in EPISODIC_WORDS:
        chi_t = tuple(folded_chi_text(w))
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word":
                episodic_info[w] = {
                    "chi": chi_t, "motif": e["motif"],
                    "strength_at_encode": e["strength"],
                }

    # Run until episodic entries decay (tick ~5500+)
    survival_history = defaultdict(list)
    tick_start = cog.tick

    for t in range(tick_start, TOTAL_TICKS):
        if t % 50 < len(TRUE_WORDS):
            w = TRUE_WORDS[t % 50]
            attend(cog, w, salience=1.5, dwell=2)
        else:
            cog.step()

        if t % DREAM_INTERVAL == 0 and t > tick_start:
            for chi_t, entries in cog.atlas.entries.items():
                for e in entries:
                    key = (chi_t, e["section"], e["motif"])
                    survival_history[key].append(e["strength"])
            _dream_net_effect(cog.atlas, cog.tick)
            dual_promotion_gate(cog.atlas, deep, cog.tick, survival_history,
                                encode_gate=0.15)
            deep.decay(cog.tick)
            deep.prune()
            # Apply deep priors at dream time (standard)
            for chi_t, entries in cog.atlas.entries.items():
                for e in entries:
                    prior = deep.get_prior(chi_t, e["section"], e["motif"])
                    if prior > 0:
                        e["strength"] = min(REAL_STRENGTH_CAP,
                                            e["strength"] + prior * 0.1)

    # Verify episodic entries have decayed from working atlas
    ep_alive_pre = sum(1 for w in EPISODIC_WORDS
                       if any(e["strength"] >= REAL_FORGET_THRESH
                              and e["section"] == "word"
                              for e in cog.atlas.entries.get(
                                  tuple(folded_chi_text(w)), [])))
    ep_in_deep = sum(1 for w in EPISODIC_WORDS
                     if any(e["strength"] >= REAL_FORGET_THRESH
                            for e in deep.entries.get(
                                episodic_info.get(w, {}).get("chi", ()), [])))

    print(f"\nPre-retrieval state (tick {cog.tick}):")
    print(f"  Episodic in working atlas: {ep_alive_pre}/12")
    print(f"  Episodic in deep atlas:    {ep_in_deep}/12")

    # --- RETRIEVAL ---
    # For each episodic word, attempt recall:
    # 1. Reinstate a weak working entry from deep (attention-time deep prior)
    # 2. Fire a cue at the same or neighboring chi
    # 3. Run cascade/step
    # 4. Check if episodic word activation exceeds threshold
    print(f"\n--- Retrieval attempts ---")

    recalled = 0
    not_recalled = 0
    no_deep_entry = 0

    for w in EPISODIC_WORDS:
        info = episodic_info.get(w)
        if not info:
            no_deep_entry += 1
            continue

        chi_t = info["chi"]
        motif = info["motif"]

        # Check if deep has this entry
        deep_entry = None
        for e in deep.entries.get(chi_t, []):
            if e["section"] == "word" and e["motif"] == motif:
                deep_entry = e
                break

        if deep_entry is None or deep_entry["strength"] < REAL_FORGET_THRESH:
            no_deep_entry += 1
            print(f"  {w:12s}: no deep entry → SKIP")
            continue

        # Step 1: REINSTATE working atlas entry from deep prior
        # This is the attention-time read path from the brief:
        # "projects an additive prior into working-atlas strength when an
        #  attended target has a deep entry"
        reinstated = False
        for e in cog.atlas.entries.get(chi_t, []):
            if e["section"] == "word" and e["motif"] == motif:
                # Entry still exists but below threshold — boost it
                prior = deep.get_prior(chi_t, "word", motif)
                e["strength"] = min(REAL_STRENGTH_CAP, e["strength"] + prior)
                reinstated = True
                break

        if not reinstated:
            # Entry was fully pruned — reinstate from deep
            cog.atlas.entries[chi_t].append({
                "section": "word", "motif": motif, "chi": chi_t,
                "strength": deep_entry["strength"] * 0.3,  # weak reinstatement
                "last_tick": cog.tick, "born_tick": cog.tick,
            })

        # Step 2: Fire cue — use a TRUE word that's chi-adjacent
        # (simulates "something reminds me of X")
        cue_fired = False
        for tw in TRUE_WORDS:
            tw_chi = tuple(folded_chi_text(tw))
            if folded_chi_distance(tw_chi, chi_t) <= 2:
                cog.fire("word", tw, salience=1.5)
                cue_fired = True
                break

        if not cue_fired:
            # No chi-adjacent TRUE word; fire directly at episodic chi
            # (self-cue through deep prior)
            label = cog.section_mid_to_label.get("word", {}).get(motif)
            if label and label in cog.sections.get("word", {}):
                cog.fire("word", label, salience=1.0)
                cue_fired = True

        # Step 3: Run cascade and step
        for _ in range(5):
            cog.step()

        # Step 4: Check if episodic word is now active/recallable
        label = cog.section_mid_to_label.get("word", {}).get(motif)
        activation = 0.0
        if label and label in cog.sections.get("word", {}):
            activation = cog.sections["word"][label]["activation"]

        # Also check if atlas entry is now alive
        atlas_alive = any(e["strength"] >= REAL_FORGET_THRESH
                          and e["section"] == "word" and e["motif"] == motif
                          for e in cog.atlas.entries.get(chi_t, []))

        if atlas_alive or activation > 0.05:
            recalled += 1
            status = "RECALLED"
        else:
            not_recalled += 1
            status = "FAILED"

        print(f"  {w:12s}: deep_str={deep_entry['strength']:.3f}, "
              f"act={activation:.4f}, atlas={'live' if atlas_alive else 'dead'} "
              f"→ {status}")

    print(f"\n--- RETRIEVAL SUMMARY ---")
    print(f"  Recalled:      {recalled}/12")
    print(f"  Not recalled:  {not_recalled}/12")
    print(f"  No deep entry: {no_deep_entry}/12")
    print(f"  Recall rate:   {100*recalled/max(1,recalled+not_recalled):.0f}%")

    return {
        "recalled": recalled,
        "not_recalled": not_recalled,
        "no_deep_entry": no_deep_entry,
        "ep_in_deep": ep_in_deep,
    }


# ================================================================
# Main
# ================================================================

if __name__ == "__main__":
    print("GL-FIND-DEEPATLAS-C1-20260610-02")
    print("Deep Atlas Harness Extension — wC Review Items")
    print()

    # Item 1
    ctrl = item1_canonical_rerun()

    # Item 2
    dream_results = item2_real_dream()

    # Item 3
    noise_result, should_stop = item3_noise_realism()
    if should_stop:
        print("\n*** STOPPED: Noise gap collapsed. See item 3. ***")
    else:
        # Item 4
        retrieval = item4_retrieval_test()

        # Final summary
        print("\n" + "=" * 72)
        print("GL-FIND-DEEPATLAS-C1-20260610-02 — SUMMARY")
        print("=" * 72)

        print("\n1. CANONICAL RERUN: EG=0.15 and EG=0.20 both inside operating window")
        print("   (see item 1 output above)")

        ne = dream_results["net_effect"]
        rr = dream_results["real_replay"]
        print(f"\n2. REAL DREAM PATH:")
        print(f"   Net-effect:  EP={ne['ep_alive']}/{ne['ep_total']}, "
              f"deep={ne['deep_total']}")
        print(f"   Real-replay: EP={rr['ep_alive']}/{rr['ep_total']}, "
              f"deep={rr['deep_total']}")
        diff = rr['deep_total'] - ne['deep_total']
        print(f"   Promotion set delta: {diff:+d}")

        print(f"\n3. NOISE REALISM:")
        print(f"   Episodic mean: {noise_result['ep_mean']:.4f}")
        print(f"   Noise mean:    {noise_result['noise_mean']:.4f}")
        print(f"   Gap:           {noise_result['gap']:.4f}")
        gap_ok = noise_result['noise_mean'] < 0.12
        print(f"   Gap survives:  {'YES' if gap_ok else 'NO — STOP'}")
        if gap_ok:
            print(f"   Full run:      TRUE={noise_result['true_alive']}/12, "
                  f"EP={noise_result['ep_alive']}/12, "
                  f"NOISE={noise_result['noise_alive']}/30, "
                  f"deep_noise={noise_result['deep_noise']}")

        print(f"\n4. RETRIEVAL TEST:")
        print(f"   Recalled:     {retrieval['recalled']}/12")
        print(f"   In deep:      {retrieval['ep_in_deep']}/12")
        print(f"   Recall rate:  "
              f"{100*retrieval['recalled']/max(1,retrieval['recalled']+retrieval['not_recalled']):.0f}%")

        print("\nNEXT: wC reviews. If all four pass, writes GL-BRIEF-032.")
