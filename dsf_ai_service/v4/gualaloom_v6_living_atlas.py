"""
gualaloom_v6_living_atlas.py — Atlas as living substrate, not append-only ledger

The three primitive facts mechanized into atlas physics:

ENTROPY:  Every binding has a strength in [0,1]. Each tick, all bindings decay
          by λ * strength. Without reinforcement, every binding fades to noise.
          This is the negative space operator from the spec, finally wired.

COHESION: Reinforcement on re-encounter. When a chi-band is touched again,
          the binding's strength increases. Cohesion is the local force that
          fights entropy — repeated experience accumulating against decay.

GREED IN FLUX: Reinforcement amount is modulated by SALIENCE — the substrate's
          current state at the moment of encounter. High salience (pair-bond
          active + unmet need + novel input) produces large reinforcement.
          Low salience (satisfied state, familiar repetition) produces small
          reinforcement. Greed for experience is built into HOW MUCH a moment
          shapes her, not whether moments are recorded.

Meaning is the substrate's current attractor landscape — chi-bands where
strength has accumulated enough to dominate decay. Forgotten bindings ARE
forgotten (strength below threshold). Recently-reinforced bindings dominate
recall. The atlas IS her associative world, alive, decaying, accumulating.

Backward compatibility: keeps ChiAtlas interface (record, match_score,
cross_modal_bindings, query_associations) so v5 engine works without changes.
"""

import math
import os
from collections import defaultdict, Counter


# ============================================================
# Physics constants
# ============================================================

# Entropy: decay rate per tick (small — bindings fade slowly, allowing
# accumulation to dominate over short timescales but enforcing forgetting
# over long ones)
DECAY_LAMBDA = 0.0001  # per tick (was 0.001 — too aggressive, 10x slower now)

# Cohesion: base reinforcement amount on re-encounter
BASE_REINFORCEMENT = 0.05

# Salience modulation: multiplier range for reinforcement
SALIENCE_MIN = 0.2   # cold reads — corpus during satisfied need state
SALIENCE_MAX = 3.0   # hot moments — pair-bond + unmet need + novel input

# Forgetting threshold: bindings below this strength are pruned periodically
FORGETTING_THRESHOLD = 0.02

# Atlas band (carried from v5)
CHI_BAND = 2

# Strength cap to prevent runaway accumulation
STRENGTH_CAP = 1.0

# Metaplastic decay constants (GL-BRIEF-033)
SLOW_DIV = 12          # slow channel = DECAY_LAMBDA / SLOW_DIV (~2.3h half-life)
DWELL_GATE_META = 4    # dwell >= this → slow channel
META_K = 2.0           # metaplastic slowdown factor


def _meta_decay_enabled():
    return os.environ.get("META_DECAY_ENABLED", "1") != "0"


# ============================================================
# Living atlas
# ============================================================

class LivingAtlas:
    """Atlas where bindings have strength, decay, and salience-modulated growth.

    Replaces v4/v5 ChiAtlas while preserving interface. Entries are stored as
    dicts with 'strength' and 'last_tick' alongside existing fields.
    """

    def __init__(self, band=CHI_BAND):
        self.band = band
        self.tick = 0
        # chi -> list of {section, motif, chi, strength, last_tick, born_tick}
        self.entries = defaultdict(list)

    def record(self, section_name, motif_id, chi_value, tick=None, salience=1.0,
               dwell_ticks=0, arousal=0.5, valence=0.0, surprise=0.0,
               need_pressure=0.0, sensory_refs=None, episode_ref=None):
        """Record a new binding OR reinforce existing one if (section, motif)
        already present near this chi. Salience modulates the strength impulse.

        GL-CLARITY-INVARIANCE-UNCAGE: affect kwargs (arousal, valence, surprise,
        need_pressure) set initial clarity. Grounding kwargs (sensory_refs,
        episode_ref) track what was happening when the binding formed.

        Salience interpretation:
          1.0 = baseline (corpus read, no pair-bond, satisfied needs)
          > 1.0 = elevated (pair-bond active OR unmet need OR novel input)
          < 1.0 = dampened (familiar repetition, fully satisfied)

        dwell_ticks: how many ticks this binding was attended before commit.
          Stored at write time for deep atlas compound gate (GL-BRIEF-032).
          DWELL_GATE_META for dream replay (consolidation IS dwell-earning).
          Zero for presence pulses (not consolidation events).
        """
        if tick is None:
            tick = self.tick
        self.tick = max(self.tick, tick)

        # Clamp salience to defined range
        salience = max(SALIENCE_MIN, min(SALIENCE_MAX, salience))
        impulse = BASE_REINFORCEMENT * salience

        # GL-CLARITY-INVARIANCE-UNCAGE: clarity from affect state
        clarity = min(1.0, 0.3 + 0.3 * arousal + 0.2 * abs(valence)
                      + 0.2 * surprise + 0.1 * need_pressure)

        # For each chi within band, find or create the entry
        for d in range(-self.band, self.band + 1):
            chi_k = chi_value + d
            entries = self.entries[chi_k]

            # Look for existing entry from same (section, motif)
            existing = None
            for e in entries:
                if e["section"] == section_name and e["motif"] == motif_id:
                    existing = e
                    break

            if existing is not None:
                # Reinforce — bounded by cap
                existing["strength"] = min(STRENGTH_CAP, existing["strength"] + impulse)
                existing["last_tick"] = tick
                # encoded_strength = post-impulse strength on EVERY reinforcement
                existing["encoded_strength"] = existing["strength"]
                # dwell_ticks tracks max dwell seen (honest record)
                if dwell_ticks > existing.get("dwell_ticks", 0):
                    existing["dwell_ticks"] = dwell_ticks
                # Metaplastic: increment reinforcement count (GL-BRIEF-033)
                existing["reinforcement_count"] = existing.get("reinforcement_count", 0) + 1
                # GL-CLARITY: renew clarity on reinforcement (max, not average)
                existing["clarity"] = max(existing.get("clarity", 0.3), clarity)
                # GL-CLARITY: accumulate sensory refs
                if sensory_refs:
                    refs = existing.get("sensory_refs", [])
                    for r in sensory_refs:
                        if r not in refs:
                            refs.append(r)
                    existing["sensory_refs"] = refs[-8:]  # cap at 8
                if episode_ref and episode_ref != existing.get("episode_ref"):
                    existing["episode_refs"] = (existing.get("episode_refs", [])
                                                + [episode_ref])[-4:]
            else:
                # New binding — tag encoded_strength and dwell at write time
                new_strength = min(STRENGTH_CAP, impulse)
                entries.append({
                    "section": section_name,
                    "motif": motif_id,
                    "chi": chi_value,
                    "strength": new_strength,
                    "last_tick": tick,
                    "born_tick": tick,
                    "encoded_strength": new_strength,
                    "dwell_ticks": dwell_ticks,
                    "reinforcement_count": 0,
                    "released": False,
                    "clarity": clarity,
                    "initial_clarity": clarity,
                    "sensory_refs": list(sensory_refs) if sensory_refs else [],
                    "episode_refs": [episode_ref] if episode_ref else [],
                })

    def decay(self, current_tick=None, rate_scale=1.0):
        """Apply per-tick decay to all bindings. Called every 10 ticks.

        GL-BRIEF-033: Two-speed metaplastic decay.
        A. dwell >= 4 AND not released → slow channel (DECAY_LAMBDA / SLOW_DIV)
        B. lam_eff = lam_base / (1 + K * reinforcement_count)
        Legacy entries (no dwell_ticks field) get global DECAY_LAMBDA.
        META_DECAY_ENABLED=0 → exact legacy behavior.
        rate_scale: Fix C (GL-FIX-THREE) — external multiplier on lam_eff.
        1.0 = normal (bit-identical to pre-change). 0.0 = no decay.
        """
        if current_tick is None:
            current_tick = self.tick
        meta = _meta_decay_enabled()
        # UNPAUSE: env-var overrides for Step-3 calibrated constants
        import os as _os
        _lam = float(_os.environ.get("DECAY_LAMBDA_OVERRIDE", 0) or 0) or DECAY_LAMBDA
        _sdiv = float(_os.environ.get("SLOW_DIV_OVERRIDE", 0) or 0) or SLOW_DIV
        for chi_k, entries in self.entries.items():
            for e in entries:
                dt = max(0, current_tick - e["last_tick"])
                if dt > 0:
                    if meta and "dwell_ticks" in e:
                        dwell = e.get("dwell_ticks", 0)
                        released = e.get("released", False)
                        if dwell >= DWELL_GATE_META and not released:
                            lam_base = _lam / _sdiv
                        else:
                            lam_base = _lam
                        rc = e.get("reinforcement_count", 0)
                        lam_eff = lam_base / (1.0 + META_K * rc)
                    else:
                        lam_eff = _lam
                    lam_eff *= rate_scale  # Fix C: external modulation
                    e["strength"] *= math.exp(-lam_eff * dt)
                    e["last_tick"] = current_tick
                    # GL-CLARITY: slow clarity entropy (separate clock, ~10x slower)
                    if "clarity" in e and dt > 0 and rate_scale > 0:
                        clarity_lam = lam_eff * 0.1  # 10x slower than strength
                        e["clarity"] = max(0.05, e["clarity"] * math.exp(-clarity_lam * dt))

    def renew_clarity(self, chi_value, section_name, motif_id, new_clarity):
        """Renew clarity on a specific binding (e.g. on cortex reinstatement)."""
        for d in range(-self.band, self.band + 1):
            for e in self.entries.get(chi_value + d, []):
                if e["section"] == section_name and e["motif"] == motif_id:
                    e["clarity"] = max(e.get("clarity", 0.05), new_clarity)

    def bindings_at_chi_neighborhood(self, chi_value, min_strength=0.0,
                                      min_clarity=0.0):
        """Return all bindings near a chi value, filtered by strength and clarity."""
        result = []
        for d in range(-self.band, self.band + 1):
            for e in self.entries.get(chi_value + d, []):
                if (e["strength"] >= min_strength
                        and e.get("clarity", 0.3) >= min_clarity):
                    result.append(e)
        return result

    def amnesty(self, current_tick):
        """UNPAUSE: reset last_tick on every entry to current_tick.
        Prevents mass extinction on first decay after long pause.
        Zero strength changes — last_tick only."""
        count = 0
        for entries in self.entries.values():
            for e in entries:
                e["last_tick"] = current_tick
                count += 1
        return count

    def strength_distribution(self):
        """Histogram of binding strengths for monitoring."""
        buckets = {"0.0-0.1": 0, "0.1-0.3": 0, "0.3-0.5": 0,
                   "0.5-0.7": 0, "0.7-0.9": 0, "0.9-1.0": 0}
        for entries in self.entries.values():
            for e in entries:
                s = e["strength"]
                if s < 0.1: buckets["0.0-0.1"] += 1
                elif s < 0.3: buckets["0.1-0.3"] += 1
                elif s < 0.5: buckets["0.3-0.5"] += 1
                elif s < 0.7: buckets["0.5-0.7"] += 1
                elif s < 0.9: buckets["0.7-0.9"] += 1
                else: buckets["0.9-1.0"] += 1
        return buckets

    def release_to_fast(self, chi_value, section_name, motif_id):
        """C: Post-promotion release — entry reverts to fast decay channel.
        reinforcement_count=0, released=True. dwell_ticks stays honest."""
        for d in range(-self.band, self.band + 1):
            for e in self.entries.get(chi_value + d, []):
                if e["section"] == section_name and e["motif"] == motif_id:
                    e["reinforcement_count"] = 0
                    e["released"] = True

    def decay_channel_counts(self):
        """Instrumentation: count entries by decay channel."""
        n_fast = 0
        n_slow = 0
        n_released = 0
        for entries in self.entries.values():
            for e in entries:
                if e["strength"] < FORGETTING_THRESHOLD:
                    continue
                if e.get("released", False):
                    n_released += 1
                elif e.get("dwell_ticks", 0) >= DWELL_GATE_META:
                    n_slow += 1
                else:
                    n_fast += 1
        return {"n_fast": n_fast, "n_slow": n_slow, "n_released": n_released}

    def forget_below_threshold(self):
        """Prune bindings whose strength has decayed below threshold.
        Returns count of forgotten bindings."""
        forgotten = 0
        for chi_k in list(self.entries.keys()):
            survivors = [e for e in self.entries[chi_k]
                         if e["strength"] >= FORGETTING_THRESHOLD]
            forgotten += len(self.entries[chi_k]) - len(survivors)
            if survivors:
                self.entries[chi_k] = survivors
            else:
                del self.entries[chi_k]
        return forgotten

    # --- Backward-compatible interface (used by v5 engine) ---

    def cross_modal_bindings(self):
        """Atlas slots where >= 2 distinct sections committed.
        Strength-weighted: only count entries with strength > forgetting threshold."""
        out = []
        for k, entries in self.entries.items():
            live = [e for e in entries if e["strength"] >= FORGETTING_THRESHOLD]
            secs = set(e["section"] for e in live)
            if len(secs) >= 2:
                out.append((k, secs, live))
        return out

    def match_score(self, chi_value, section_name):
        """For familiarity feedback: how much existing structure is at this chi?
        v6: weighted by binding strength (forgotten bindings don't count)."""
        score = 0.0
        for d in range(-self.band, self.band + 1):
            for e in self.entries.get(chi_value + d, []):
                if e["strength"] < FORGETTING_THRESHOLD:
                    continue
                if e["section"] != section_name:
                    score += 0.3 * e["strength"]
                else:
                    score += 0.1 * e["strength"]
        return min(score, 1.0)

    def query_associations(self, section_name, chi_value):
        """Cross-section associations at this chi.
        v6: returns strength-weighted associations."""
        associated = defaultdict(list)
        for d in range(-self.band, self.band + 1):
            for e in self.entries.get(chi_value + d, []):
                if e["strength"] < FORGETTING_THRESHOLD:
                    continue
                if e["section"] != section_name:
                    associated[e["section"]].append((e["motif"], e["strength"]))
        return dict(associated)

    # --- New living-atlas interfaces ---

    def total_strength(self):
        """Sum of all binding strengths — how much 'meaning' she's currently
        carrying."""
        return sum(e["strength"] for entries in self.entries.values()
                   for e in entries)

    def n_live_bindings(self):
        """Count of bindings above forgetting threshold."""
        return sum(1 for entries in self.entries.values() for e in entries
                   if e["strength"] >= FORGETTING_THRESHOLD)

    def sparse_chi_regions(self, expected_density=10):
        """Identify chi regions with LOW binding density — where greed-for-
        experience pulls her toward."""
        # Look at chi range
        if not self.entries:
            return []
        chis = sorted(self.entries.keys())
        chi_min, chi_max = chis[0], chis[-1]
        sparse = []
        # Sample chi range, find under-populated regions
        for chi in range(chi_min, chi_max + 1):
            density = sum(1 for e in self.entries.get(chi, [])
                          if e["strength"] >= FORGETTING_THRESHOLD)
            if density < expected_density:
                sparse.append((chi, density))
        return sparse

    def strength_distribution(self):
        """Histogram of binding strengths — diagnostic.
        Returns dict bin -> count."""
        bins = {"0.0-0.1": 0, "0.1-0.3": 0, "0.3-0.5": 0,
                "0.5-0.7": 0, "0.7-0.9": 0, "0.9-1.0": 0}
        for entries in self.entries.values():
            for e in entries:
                s = e["strength"]
                if s < 0.1: bins["0.0-0.1"] += 1
                elif s < 0.3: bins["0.1-0.3"] += 1
                elif s < 0.5: bins["0.3-0.5"] += 1
                elif s < 0.7: bins["0.5-0.7"] += 1
                elif s < 0.9: bins["0.7-0.9"] += 1
                else: bins["0.9-1.0"] += 1
        return bins

    def snapshot(self):
        return {
            "tick": self.tick,
            "total_strength": round(self.total_strength(), 2),
            "n_live_bindings": self.n_live_bindings(),
            "n_total_entries": sum(len(es) for es in self.entries.values()),
            "n_chi_keys": len(self.entries),
            "strength_distribution": self.strength_distribution(),
            "decay_channels": self.decay_channel_counts(),
            "meta_decay_enabled": _meta_decay_enabled(),
        }
