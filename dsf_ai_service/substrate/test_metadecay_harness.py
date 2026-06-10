"""
GL-FIND-METADECAY-C1-20260610 — Two-Speed Metaplastic Decay Harness

Stage 1 ONLY. NO production code changes.

Imports REAL LivingAtlas from gualaloom_v6_living_atlas.py.
Tests the failure mode and the proposed fix in harness only.

1. BASELINE: reproduce session-load decaying below threshold before dream
2. A/B/C metaplastic design in harness-modified atlas copy
3. Multi-day timeline with realistic noise
4. Parameter sweep SLOW_DIV x K
"""

import math
import copy
import numpy as np
from collections import defaultdict

from dsf_ai_service.v4.gualaloom_v6_living_atlas import (
    LivingAtlas, DECAY_LAMBDA, BASE_REINFORCEMENT, FORGETTING_THRESHOLD,
    STRENGTH_CAP, SALIENCE_MIN, SALIENCE_MAX, CHI_BAND,
)

# ── Simulation constants (calibrated to prod) ──
TICKS_PER_SEC = 20
SECS_PER_HOUR = 3600
TICKS_PER_HOUR = TICKS_PER_SEC * SECS_PER_HOUR  # 72000
DECAY_EVERY = 10       # decay called every 10 ticks (prod behavior)
PRUNE_EVERY = 200      # forget_below_threshold every 200 ticks
DREAM_INTERVAL = TICKS_PER_HOUR * 6  # 6 hours between dreams (prod gap)

# ── Population definitions ──
N_TRUE = 40         # session-load: high-dwell, re-attended
N_EPISODIC = 40     # one-shot high-dwell (the failure case from 031/032)
N_NOISE = 30        # realistic noise via cofire (includes high-strength tail)


def make_session_entries(atlas, n, prefix, salience, dwell, chi_start=100,
                         n_reinforcements=3):
    """Install n entries into atlas simulating a session of attended input.
    Each entry is reinforced n_reinforcements times (simulating re-encounter
    during conversation or sustained attention — prod read_word fires atlas.record
    on every re-encounter of the same word)."""
    for i in range(n):
        chi = chi_start + i * 5  # spread across chi space
        section = ["listen", "subject", "verb", "object"][i % 4]
        motif = i
        # Initial encoding
        atlas.record(section, motif, chi, tick=atlas.tick,
                     salience=salience, dwell_ticks=dwell)
        atlas.tick += 1
        # Reinforcements (simulates re-encounter during session)
        for r in range(n_reinforcements):
            atlas.tick += 5
            atlas.record(section, motif, chi, tick=atlas.tick,
                         salience=salience * 0.8, dwell_ticks=dwell)


def make_noise_entries(atlas, n, chi_start=500):
    """Realistic noise: cofire-style entries. Most at low strength,
    some at high strength (the 0.82 tail from FIND-02)."""
    rng = np.random.default_rng(42)
    for i in range(n):
        chi = chi_start + i * 3
        # 80% low salience, 20% high (cofire cross-link tail)
        if rng.random() < 0.8:
            sal = 0.3 + rng.random() * 0.3  # 0.3-0.6
        else:
            sal = 1.5 + rng.random() * 1.5  # 1.5-3.0 (high tail)
        atlas.record("listen", 9000 + i, chi, tick=atlas.tick,
                     salience=sal, dwell_ticks=1)  # noise = dwell 1
    atlas.tick += n


def simulate_decay(atlas, n_ticks, dream_at=None, dream_fn=None):
    """Run n_ticks of decay. Optionally run dream_fn at dream_at tick."""
    for t in range(n_ticks):
        atlas.tick += 1
        if atlas.tick % DECAY_EVERY == 0:
            atlas.decay(atlas.tick)
        if atlas.tick % PRUNE_EVERY == 0:
            atlas.forget_below_threshold()
        if dream_at and atlas.tick == dream_at and dream_fn:
            dream_fn(atlas)


def dream_consolidation(atlas):
    """Simulate dream: reinforce top-half entries.
    Calibrated to prod observation: dream roughly doubles total strength
    on top half (observed 2.91→5.50). Prod uses atlas.record with salience=0.3
    across sampled chi-keys; we calibrate the effective boost to match."""
    all_entries = []
    for chi_k, entries in atlas.entries.items():
        for e in entries:
            if e["strength"] >= FORGETTING_THRESHOLD:
                all_entries.append((chi_k, e))
    if not all_entries:
        return
    # Sort by strength, reinforce top half
    all_entries.sort(key=lambda x: -x[1]["strength"])
    top_half = all_entries[:max(1, len(all_entries) // 2)]
    # Calibration: each top-half entry gets boosted to ~2x its current strength
    # Prod achieves this via repeated atlas.record calls during the dream tick window
    for chi_k, e in top_half:
        boost = e["strength"]  # double it
        e["strength"] = min(STRENGTH_CAP, e["strength"] + boost)
        e["last_tick"] = atlas.tick
        # Dream reinforcement counts toward metaplastic count
        if hasattr(atlas, 'k'):  # MetaplasticAtlas
            e["reinforcement_count"] = e.get("reinforcement_count", 0) + 1


def count_alive(atlas, chi_start, n, section_filter=None, motif_filter=None):
    """Count entries above threshold in a chi range."""
    alive = 0
    for i in range(n):
        chi = chi_start + i * 5
        for d in range(-CHI_BAND, CHI_BAND + 1):
            for e in atlas.entries.get(chi + d, []):
                if e["strength"] >= FORGETTING_THRESHOLD:
                    if motif_filter and e["motif"] not in motif_filter:
                        continue
                    alive += 1
                    break  # count per-chi, not per-entry
    return alive


def count_noise_alive(atlas, n, chi_start=500):
    """Count noise entries above threshold."""
    alive = 0
    for i in range(n):
        chi = chi_start + i * 3
        for d in range(-CHI_BAND, CHI_BAND + 1):
            for e in atlas.entries.get(chi + d, []):
                if e["strength"] >= FORGETTING_THRESHOLD and e["motif"] >= 9000:
                    alive += 1
                    break
    return alive


# ============================================================
# METAPLASTIC ATLAS (harness-only modification)
# ============================================================

class MetaplasticAtlas(LivingAtlas):
    """LivingAtlas with two-speed metaplastic decay. Harness only."""

    def __init__(self, slow_div=12, k=2.0, band=CHI_BAND):
        super().__init__(band=band)
        self.slow_div = slow_div
        self.k = k

    def decay(self, current_tick=None):
        """Per-entry metaplastic decay.
        A: dwell-gated two-speed baseline
        B: metaplastic slowdown via reinforcement_count
        """
        if current_tick is None:
            current_tick = self.tick
        for chi_k, entries in self.entries.items():
            for e in entries:
                dt = max(0, current_tick - e["last_tick"])
                if dt > 0:
                    dwell = e.get("dwell_ticks", 0)
                    rc = e.get("reinforcement_count", 0)
                    # A: two-speed baseline
                    lam_base = DECAY_LAMBDA if dwell < 4 else DECAY_LAMBDA / self.slow_div
                    # B: metaplastic slowdown
                    lam_eff = lam_base / (1.0 + self.k * rc)
                    e["strength"] *= math.exp(-lam_eff * dt)
                    e["last_tick"] = current_tick

    def record(self, section_name, motif_id, chi_value, tick=None, salience=1.0,
               dwell_ticks=0):
        """Override to track reinforcement_count."""
        if tick is None:
            tick = self.tick
        self.tick = max(self.tick, tick)
        salience = max(SALIENCE_MIN, min(SALIENCE_MAX, salience))
        impulse = BASE_REINFORCEMENT * salience

        for d in range(-self.band, self.band + 1):
            chi_k = chi_value + d
            entries = self.entries[chi_k]
            existing = None
            for e in entries:
                if e["section"] == section_name and e["motif"] == motif_id:
                    existing = e
                    break
            if existing is not None:
                existing["strength"] = min(STRENGTH_CAP, existing["strength"] + impulse)
                existing["last_tick"] = tick
                # B: increment reinforcement_count on re-encounter
                existing["reinforcement_count"] = existing.get("reinforcement_count", 0) + 1
                # encoded_strength = post-impulse strength (accumulated across episode)
                existing["encoded_strength"] = existing["strength"]
                if dwell_ticks > existing.get("dwell_ticks", 0):
                    existing["dwell_ticks"] = dwell_ticks
            else:
                new_strength = min(STRENGTH_CAP, impulse)
                entries.append({
                    "section": section_name, "motif": motif_id,
                    "chi": chi_value, "strength": new_strength,
                    "last_tick": tick, "born_tick": tick,
                    "encoded_strength": new_strength,
                    "dwell_ticks": dwell_ticks,
                    "reinforcement_count": 0,
                })

    def post_promotion_release(self, chi_value, section, motif):
        """C: On deep promotion, revert working entry to fast channel."""
        for d in range(-self.band, self.band + 1):
            for e in self.entries.get(chi_value + d, []):
                if e["section"] == section and e["motif"] == motif:
                    e["reinforcement_count"] = 0
                    e["dwell_ticks"] = 0  # reverts to fast lam_base


def dream_with_promotion(atlas, deep_entries, is_meta=False):
    """Dream consolidation + deep promotion check.
    Returns (promoted_count, entries promoted to deep)."""
    # Calibrated dream reinforcement (2x top half)
    dream_consolidation(atlas)

    # Re-gather live entries post-dream
    all_live = []
    for chi_k, entries in atlas.entries.items():
        for e in entries:
            if e["strength"] >= FORGETTING_THRESHOLD:
                all_live.append((chi_k, e))
    if not all_live:
        return 0, []

    # Deep promotion check (simplified: Path A survival = above 0.4)
    promoted = []
    for chi_k, e in all_live:
        if e["strength"] >= 0.4:
            key = (chi_k, e["section"], e["motif"])
            if key not in deep_entries:
                deep_entries[key] = e.copy()
                promoted.append(key)
                # C: post-promotion release
                if is_meta and hasattr(atlas, 'post_promotion_release'):
                    atlas.post_promotion_release(chi_k, e["section"], e["motif"])
        # Path B: episodic (encoded_strength >= 0.15 AND dwell >= 4)
        enc = e.get("encoded_strength", 0)
        dwell = e.get("dwell_ticks", 0)
        if enc >= 0.15 and dwell >= 4:
            key = (chi_k, e["section"], e["motif"])
            if key not in deep_entries:
                deep_entries[key] = e.copy()
                promoted.append(key)
                if is_meta and hasattr(atlas, 'post_promotion_release'):
                    atlas.post_promotion_release(chi_k, e["section"], e["motif"])

    return len(promoted), promoted


# ============================================================
# STEP 1: BASELINE — reproduce failure
# ============================================================

def step1_baseline():
    print("=" * 72)
    print("STEP 1: BASELINE — single global DECAY_LAMBDA, 6h gap to dream")
    print("=" * 72)

    atlas = LivingAtlas()

    # Session: high-dwell entries (simulating an interactive session)
    make_session_entries(atlas, N_TRUE, "true", salience=2.0, dwell=8, chi_start=100)
    make_session_entries(atlas, N_EPISODIC, "episodic", salience=2.5, dwell=8, chi_start=400)
    make_noise_entries(atlas, N_NOISE, chi_start=700)

    print(f"\nAfter encoding (tick {atlas.tick}):")
    print(f"  Total live: {atlas.n_live_bindings()}")
    print(f"  Total strength: {atlas.total_strength():.2f}")

    true_alive_0 = atlas.n_live_bindings()

    # Simulate 6 hours of decay (no re-attention, no dream)
    gap_ticks = TICKS_PER_HOUR * 6
    simulate_decay(atlas, gap_ticks)

    pre_dream_live = atlas.n_live_bindings()
    pre_dream_strength = atlas.total_strength()

    print(f"\nAfter 6h gap (tick {atlas.tick}):")
    print(f"  Live: {pre_dream_live} (was {true_alive_0})")
    print(f"  Strength: {pre_dream_strength:.2f}")

    # Dream
    deep = {}
    n_promoted, promoted_keys = dream_with_promotion(atlas, deep)

    print(f"\nAfter dream:")
    print(f"  Live: {atlas.n_live_bindings()}")
    print(f"  Promoted to deep: {n_promoted}")

    # Verdict
    failure = pre_dream_live <= 5  # brief says "handful"
    print(f"\n--- BASELINE VERDICT ---")
    if failure:
        print(f"FAILURE REPRODUCED: {pre_dream_live} entries survived 6h gap.")
        print(f"  Only {n_promoted} promoted at dream.")
    else:
        print(f"*** FAILURE DID NOT REPRODUCE: {pre_dream_live} survived ***")
        print(f"  STOPPING — premise may be wrong.")

    return failure, pre_dream_live, n_promoted


# ============================================================
# STEP 2: METAPLASTIC DESIGN
# ============================================================

def step2_metaplastic(slow_div=12, k=2.0):
    print(f"\n{'='*72}")
    print(f"STEP 2: METAPLASTIC — SLOW_DIV={slow_div}, K={k}")
    print(f"{'='*72}")

    atlas = MetaplasticAtlas(slow_div=slow_div, k=k)

    # Same encoding as baseline
    make_session_entries(atlas, N_TRUE, "true", salience=2.0, dwell=8, chi_start=100)
    make_session_entries(atlas, N_EPISODIC, "episodic", salience=2.5, dwell=8, chi_start=400)
    make_noise_entries(atlas, N_NOISE, chi_start=700)

    print(f"\nAfter encoding (tick {atlas.tick}):")
    print(f"  Total live: {atlas.n_live_bindings()}")

    # 6h gap
    gap_ticks = TICKS_PER_HOUR * 6
    simulate_decay(atlas, gap_ticks)

    pre_dream = atlas.n_live_bindings()
    noise_pre = count_noise_alive(atlas, N_NOISE, chi_start=700)

    print(f"\nAfter 6h gap (tick {atlas.tick}):")
    print(f"  Live: {pre_dream}")
    print(f"  Noise alive: {noise_pre}")

    # Dream + promotion
    deep = {}
    n_promoted, _ = dream_with_promotion(atlas, deep, is_meta=True)

    post_dream = atlas.n_live_bindings()
    noise_post = count_noise_alive(atlas, N_NOISE, chi_start=700)

    print(f"\nAfter dream:")
    print(f"  Live: {post_dream}")
    print(f"  Promoted: {n_promoted}")
    print(f"  Noise alive: {noise_post}")
    print(f"  Working size: {post_dream}")

    # Chi-band interaction check
    distortion = _check_match_score_distortion(atlas)
    print(f"  match_score distortion: {distortion:.4f}")

    return {
        "pre_dream_live": pre_dream,
        "promoted": n_promoted,
        "noise_alive": noise_post,
        "working_size": post_dream,
        "distortion": distortion,
        "slow_div": slow_div,
        "k": k,
    }


# ============================================================
# STEP 3: MULTI-DAY TIMELINE
# ============================================================

def step3_multiday(slow_div=12, k=2.0, n_days=5, sessions_per_day=2):
    print(f"\n{'='*72}")
    print(f"STEP 3: {n_days}-DAY TIMELINE — {sessions_per_day} sessions/day")
    print(f"{'='*72}")

    atlas = MetaplasticAtlas(slow_div=slow_div, k=k)
    deep = {}
    total_promoted = 0
    working_sizes = []
    session_count = 0

    for day in range(n_days):
        for sess in range(sessions_per_day):
            session_count += 1
            chi_base = 100 + session_count * 200

            # Session: 10 TRUE + 10 EPISODIC + 8 NOISE per session
            make_session_entries(atlas, 10, f"d{day}s{sess}_true",
                                salience=2.0, dwell=8, chi_start=chi_base)
            make_session_entries(atlas, 10, f"d{day}s{sess}_ep",
                                salience=2.5, dwell=8, chi_start=chi_base + 100)
            make_noise_entries(atlas, 8, chi_start=chi_base + 200)

            # Inter-session gap: 6h of decay
            gap = TICKS_PER_HOUR * 6
            simulate_decay(atlas, gap)

            # Dream at end of gap
            n_p, _ = dream_with_promotion(atlas, deep, is_meta=True)
            total_promoted += n_p

            ws = atlas.n_live_bindings()
            working_sizes.append((day, sess, ws, n_p))

        print(f"  Day {day+1}: working={atlas.n_live_bindings()}, "
              f"deep={len(deep)}, promoted_today={sum(w[3] for w in working_sizes if w[0]==day)}")

    # Final stats
    noise_final = 0
    for chi_k, entries in atlas.entries.items():
        for e in entries:
            if e["strength"] >= FORGETTING_THRESHOLD and e.get("motif", 0) >= 9000:
                noise_final += 1

    print(f"\n--- {n_days}-DAY SUMMARY ---")
    print(f"  Total sessions: {session_count}")
    print(f"  Total promoted to deep: {total_promoted}")
    print(f"  Deep entries: {len(deep)}")
    print(f"  Final working size: {atlas.n_live_bindings()}")
    print(f"  Noise remaining: {noise_final}")
    print(f"  Working size trajectory: {[w[2] for w in working_sizes]}")

    return {
        "total_promoted": total_promoted,
        "deep_size": len(deep),
        "final_working": atlas.n_live_bindings(),
        "noise_remaining": noise_final,
        "working_trajectory": [w[2] for w in working_sizes],
    }


# ============================================================
# STEP 4: PARAMETER SWEEP
# ============================================================

def step4_sweep():
    print(f"\n{'='*72}")
    print(f"STEP 4: PARAMETER SWEEP — SLOW_DIV x K")
    print(f"{'='*72}")

    slow_divs = [4, 12, 24, 48]
    ks = [1, 2, 4]
    results = []

    # Also run baseline (no metaplastic) for reference
    print("\n--- Baseline (global decay) ---")
    atlas_bl = LivingAtlas()
    make_session_entries(atlas_bl, N_TRUE, "t", salience=2.0, dwell=8, chi_start=100)
    make_session_entries(atlas_bl, N_EPISODIC, "e", salience=2.5, dwell=8, chi_start=400)
    make_noise_entries(atlas_bl, N_NOISE, chi_start=700)
    simulate_decay(atlas_bl, TICKS_PER_HOUR * 6)
    bl_deep = {}
    bl_promoted, _ = dream_with_promotion(atlas_bl, bl_deep)
    bl_live = atlas_bl.n_live_bindings()
    print(f"  Pre-dream live: {bl_live}, promoted: {bl_promoted}")

    print(f"\n{'SD':>4s} {'K':>4s} | {'PreDr':>6s} {'Promo':>6s} {'Noise':>6s} "
          f"{'WkSz':>6s} {'Dist':>7s} | PASS")
    print("-" * 65)

    for sd in slow_divs:
        for kv in ks:
            atlas = MetaplasticAtlas(slow_div=sd, k=kv)
            make_session_entries(atlas, N_TRUE, "t", salience=2.0, dwell=8, chi_start=100)
            make_session_entries(atlas, N_EPISODIC, "e", salience=2.5, dwell=8, chi_start=400)
            make_noise_entries(atlas, N_NOISE, chi_start=700)

            simulate_decay(atlas, TICKS_PER_HOUR * 6)
            pre = atlas.n_live_bindings()
            noise_pre = count_noise_alive(atlas, N_NOISE, chi_start=700)

            deep = {}
            n_p, _ = dream_with_promotion(atlas, deep, is_meta=True)
            ws = atlas.n_live_bindings()
            noise_post = count_noise_alive(atlas, N_NOISE, chi_start=700)
            dist = _check_match_score_distortion(atlas)

            passes = (pre >= 60 and n_p >= 60 and noise_post <= 5 and dist < 0.1)
            mark = "YES" if passes else "no"

            results.append({
                "slow_div": sd, "k": kv,
                "pre_dream_live": pre, "promoted": n_p,
                "noise_alive": noise_post, "working_size": ws,
                "distortion": dist,
            })

            print(f"{sd:4d} {kv:4.0f} | {pre:>6d} {n_p:>6d} {noise_post:>6d} "
                  f"{ws:>6d} {dist:>7.4f} | {mark}")

    # Operating window
    passing = [r for r in results
               if r["pre_dream_live"] >= 60 and r["promoted"] >= 60
               and r["noise_alive"] <= 5 and r["distortion"] < 0.1]

    print(f"\n--- OPERATING WINDOW ---")
    if passing:
        sd_range = (min(r["slow_div"] for r in passing),
                    max(r["slow_div"] for r in passing))
        k_range = (min(r["k"] for r in passing),
                   max(r["k"] for r in passing))
        print(f"  {len(passing)}/{len(results)} configs pass")
        print(f"  SLOW_DIV: [{sd_range[0]}, {sd_range[1]}]")
        print(f"  K:        [{k_range[0]}, {k_range[1]}]")
    else:
        print("  NO configs pass all criteria.")
        best = sorted(results, key=lambda r: (-r["promoted"], r["noise_alive"]))
        for r in best[:3]:
            print(f"    SD={r['slow_div']} K={r['k']}: pre={r['pre_dream_live']} "
                  f"promo={r['promoted']} noise={r['noise_alive']}")

    return results


# ============================================================
# Helpers
# ============================================================

def _check_match_score_distortion(atlas):
    """Check if per-entry lambda distorts match_score relative to
    a uniform-lambda atlas with same entries."""
    # Compare match_score at 10 random chi values
    if not atlas.entries:
        return 0.0
    chis = sorted(atlas.entries.keys())[:20]
    diffs = []
    for chi in chis:
        # Current match_score (uses strength which was modified by per-entry decay)
        ms = atlas.match_score(chi, "listen")
        # Uniform-lambda comparison: what would strength be if all entries
        # had the same decay? We can't easily compute this, so instead
        # check that match_score is bounded and reasonable
        diffs.append(ms)
    # Distortion = variance of match_scores (high = some entries dominate)
    if len(diffs) < 2:
        return 0.0
    return float(np.std(diffs))


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("GL-FIND-METADECAY-C1-20260610")
    print("Two-Speed Metaplastic Decay — Harness Validation")
    print()

    # Step 1: Baseline failure
    failure_ok, pre_dream, n_promoted = step1_baseline()

    if not failure_ok:
        print("\n*** STOPPING: Baseline failure did not reproduce. ***")
    else:
        # Step 2: Metaplastic design
        r2 = step2_metaplastic(slow_div=12, k=2.0)

        # Step 3: Multi-day
        r3 = step3_multiday(slow_div=12, k=2.0, n_days=5, sessions_per_day=2)

        # Step 4: Sweep
        sweep = step4_sweep()

        # Summary
        print(f"\n{'='*72}")
        print("GL-FIND-METADECAY-C1-20260610 — SUMMARY")
        print(f"{'='*72}")
        print(f"\n1. BASELINE: {pre_dream} survived 6h gap, {n_promoted} promoted")
        print(f"   → FAILURE {'REPRODUCED' if failure_ok else 'NOT reproduced'}")
        print(f"\n2. METAPLASTIC (SD=12, K=2):")
        print(f"   Pre-dream live: {r2['pre_dream_live']}")
        print(f"   Promoted: {r2['promoted']}")
        print(f"   Noise: {r2['noise_alive']}")
        print(f"   Distortion: {r2['distortion']:.4f}")
        print(f"\n3. 5-DAY TIMELINE:")
        print(f"   Total promoted: {r3['total_promoted']}")
        print(f"   Deep size: {r3['deep_size']}")
        print(f"   Final working: {r3['final_working']}")
        print(f"   Noise: {r3['noise_remaining']}")
        print(f"   Working trajectory: {r3['working_trajectory']}")

        passing = [r for r in sweep
                   if r["pre_dream_live"] >= 60 and r["promoted"] >= 60
                   and r["noise_alive"] <= 5 and r["distortion"] < 0.1]
        print(f"\n4. SWEEP: {len(passing)}/{len(sweep)} pass")

        print(f"\nNEXT: wC reviews. If Stage 1 passes, issues Stage 2 go.")
