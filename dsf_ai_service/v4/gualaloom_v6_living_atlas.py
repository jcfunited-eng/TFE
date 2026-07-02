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

# 60-T: BASE_REINFORCEMENT, SALIENCE_MIN, SALIENCE_MAX dropped.
# Salience returns raw derivation. Reinforcement scales with salience / (1 + local_density).
# Kept as module-level names for backward import compatibility (evaluates to None-ish).
BASE_REINFORCEMENT = None   # superseded by density-scaled impulse (60-T)
SALIENCE_MIN = None         # clamp removed — high salience is a real signal (60-T)
SALIENCE_MAX = None         # clamp removed — near-zero is also a real signal (60-T)
BUNDLE_SALIENCE_BOOST = 1.5   # GL-CMD-CROSS-MODAL-STRENGTHEN B2: bundled writes get extra impulse

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
               need_pressure=0.0, sensory_refs=None, episode_ref=None,
               source="corpus", bundle_id=None,
               presence=None, location=None, sky_state=None,
               polarity=1,
               function_score=0.0, phase_vec=None, **_extra):
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

        # 60-T: no salience clamp — raw derivation. High salience IS a real signal.
        # Impulse = salience / (1 + local_density): empty regions amplify, saturated regions attenuate.
        _local_strength = 0.0
        _wa = getattr(self, '_wave_atlas', None)
        if _wa is not None:
            _cell = _wa.cells.get(chi_value % 262144)
            if _cell is not None:
                _local_strength = _cell.aggregate_strength
        impulse = salience / (1.0 + _local_strength)
        # GL-CMD-CROSS-MODAL-STRENGTHEN B2: bundled writes earn extra impulse.
        if bundle_id is not None:
            impulse *= BUNDLE_SALIENCE_BOOST

        # GL-CLARITY-INVARIANCE-UNCAGE: clarity from affect state
        # GL-CMD-CROSS-MODAL-STRENGTHEN B3: bundled writes earn +0.2 clarity floor
        bundle_boost = 0.2 if bundle_id is not None else 0.0
        clarity = min(1.0, 0.3 + 0.3 * arousal + 0.2 * abs(valence)
                      + 0.2 * surprise + 0.1 * need_pressure + bundle_boost)

        # For each chi within band, find or create the entry
        for d in range(-self.band, self.band + 1):
            chi_k = chi_value + d
            entries = self.entries[chi_k]

            # Look for existing entry from same (section, motif, polarity).
            # GL-CMD-C1-POLARITY: +1 and -1 polarity are distinct binding instances.
            existing = None
            for e in entries:
                if (e["section"] == section_name and e["motif"] == motif_id
                        and e.get("polarity", 1) == polarity):
                    existing = e
                    break

            if existing is not None:
                # GL-CMD-CHI-BAND-MASS-CONSERVATION: capture pre-impulse strength
                old_strength = existing["strength"]
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
                # GL-METADATA-PIPELINE: store raw affect (max) + source (last-write-wins)
                existing["arousal"] = max(existing.get("arousal", 0.5), arousal)
                existing["valence"] = max(existing.get("valence", 0.0), valence)
                existing["surprise"] = max(existing.get("surprise", 0.0), surprise)
                existing["source"] = source
                # GL-CMD-CROSS-MODAL-BUNDLE: last-write-wins on bundle_id
                if bundle_id is not None:
                    existing["bundle_id"] = bundle_id
                # GL-CMD-EPISODE-BINDING: situation — last-write-wins
                if presence is not None:
                    existing["presence"] = presence
                if location is not None:
                    existing["location"] = location
                if sky_state is not None:
                    existing["sky_state"] = sky_state
                # episode_ref: first-encounter canonical — only set if empty
                if episode_ref is not None and existing.get("episode_ref") is None:
                    existing["episode_ref"] = episode_ref
                # GL-CMD-C1-POLARITY: per-binding-instance, NOT per-coordinate.
                # Both +1 and -1 bindings coexist for the same motif+chi.
                # Reinforce preserves the polarity written at binding creation.
                # (New polarity variants create new entries via the else path.)
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
                # GL-CMD-CHI-BAND-MASS-CONSERVATION: heterosynaptic redistribution.
                # actual_delta (not impulse) accounts for cap absorption.
                # Redistributes exactly what existing gained from all other entries
                # at this chi address, proportional to their current strength.
                actual_delta = existing["strength"] - old_strength
                if actual_delta > 0:
                    others = [e for e in entries if e is not existing]
                    total_other = sum(e["strength"] for e in others)
                    if total_other > 0:
                        for e in others:
                            share = e["strength"] / total_other
                            e["strength"] = max(0.0,
                                                e["strength"] - actual_delta * share)
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
                    # GL-METADATA-PIPELINE: raw affect + source for 8D grandurun
                    "arousal": arousal,
                    "valence": valence,
                    "surprise": surprise,
                    "source": source,
                    # GL-SPC-HEMISPHERE-ARCH: hemisphere tag (Phase 0: always em)
                    "hemisphere_id": "em",
                    # GL-CMD-CROSS-MODAL-BUNDLE: AE-native binding marker (None = untagged)
                    "bundle_id": bundle_id,
                    # GL-CMD-EPISODE-BINDING: situational context at binding formation
                    "episode_ref": episode_ref,
                    "presence":   presence,
                    "location":   location,
                    "sky_state":  sky_state,
                    # GL-CMD-C1-POLARITY: structural polarity {-1, 0, +1}, default +1
                    "polarity":   polarity,
                    # 60-C: substrate-derived function/content score (0=content, 1=function)
                    "function_score": function_score,
                })

        # Wave atlas parallel write (WAVE_ATLAS_ENABLED=1)
        self._parallel_wave_write(
            section_name, motif_id, chi_value, tick,
            salience, phase_vec, function_score,
            dwell_ticks, arousal, valence, surprise,
            need_pressure, sensory_refs, episode_ref,
            source, bundle_id, presence, location,
            sky_state, polarity,
        )

    def _parallel_wave_write(self, section_name, motif_id, chi_value, tick,
                              salience, phase_vec, function_score,
                              dwell_ticks, arousal, valence, surprise,
                              need_pressure, sensory_refs, episode_ref,
                              source, bundle_id, presence, location,
                              sky_state, polarity):
        """Forward write to WaveAtlas if wired (WAVE_ATLAS_ENABLED=1)."""
        _wa = getattr(self, '_wave_atlas', None)
        if _wa is None:
            return
        try:
            _wa.record(
                section_name, motif_id, chi_value, tick=tick,
                salience=salience, phase_vec=phase_vec,
                function_score=function_score,
                dwell_ticks=dwell_ticks, arousal=arousal, valence=valence,
                surprise=surprise, need_pressure=need_pressure,
                sensory_refs=sensory_refs, episode_ref=episode_ref,
                source=source, bundle_id=bundle_id, presence=presence,
                location=location, sky_state=sky_state, polarity=polarity,
            )
        except Exception as _e:
            import logging
            logging.getLogger("gualaloom").warning(
                "[WaveAtlas] parallel write error: %s", _e)

    def repair_pass(self):
        """GL-CMD-CHI-BAND-MASS-CONSERVATION: one-time renormalization at deploy.

        Rescales chi bands that have accumulated above n × BASELINE.
        BASELINE = (STRENGTH_CAP + FORGETTING_THRESHOLD) / 2 — substrate-derived
        midpoint of the meaningful strength range. No tuned constants.
        Rank order within each band preserved (proportional scale).
        Returns stats for deploy V2 verification.
        """
        BASELINE = (STRENGTH_CAP + FORGETTING_THRESHOLD) / 2
        repaired_bands = 0
        repaired_bindings = 0
        total_strength_before = 0.0
        total_strength_after = 0.0

        for chi_k, entries in self.entries.items():
            live = [e for e in entries if e["strength"] >= FORGETTING_THRESHOLD]
            if not live:
                continue
            n = len(live)
            current_total = sum(e["strength"] for e in live)
            total_strength_before += current_total
            target_total = n * BASELINE
            if current_total > target_total:
                scale = target_total / current_total
                for e in live:
                    e["strength"] *= scale
                repaired_bands += 1
                repaired_bindings += n
                total_strength_after += target_total
            else:
                total_strength_after += current_total

        return {
            "repaired_bands": repaired_bands,
            "repaired_bindings": repaired_bindings,
            "total_strength_before": round(total_strength_before, 2),
            "total_strength_after": round(total_strength_after, 2),
            "baseline_used": round(BASELINE, 4),
        }

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
        Returns count of forgotten bindings.

        GL-CMD-WAVE-DIET-82: decay parity — forgotten LivingAtlas bindings are
        removed from WaveAtlas in the same call so WaveAtlas stays bounded by
        the same physics, not by a cap. Join key: (section, motif, chi_original).
        """
        forgotten = 0
        forgotten_keys = set()
        for chi_k in list(self.entries.keys()):
            survivors = [e for e in self.entries[chi_k]
                         if e["strength"] >= FORGETTING_THRESHOLD]
            for e in self.entries[chi_k]:
                if e["strength"] < FORGETTING_THRESHOLD:
                    forgotten_keys.add((e["section"], e["motif"], e.get("chi", chi_k)))
            forgotten += len(self.entries[chi_k]) - len(survivors)
            if survivors:
                self.entries[chi_k] = survivors
            else:
                del self.entries[chi_k]
        # Prune WaveAtlas counterparts
        wa = getattr(self, '_wave_atlas', None)
        if forgotten_keys and wa is not None:
            for cell in wa.cells.values():
                orig = len(cell.bindings)
                cell.bindings = [
                    b for b in cell.bindings
                    if (b.get("section"), b.get("motif"), b.get("chi")) not in forgotten_keys
                ]
                if len(cell.bindings) != orig:
                    cell.aggregate_strength = sum(
                        float(b.get("strength", 0.05)) for b in cell.bindings)
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

    def bundle_grouped_bindings(self):
        """GL-CMD-CROSS-MODAL-BUNDLE: group live entries by item identifier extracted
        from bundle_id. Returns list of (item_id, sections_set, entries_list).

        bundle_id format:
          item:pic:<id>          — picture item (from view/attend)
          item:snd:<id>          — sound item (from addsound/attend)
          bundle:<name>:<tick>   — explicit /bundle command
          context:pic:<id>:<win> — auto-bundle during visual attention
          context:snd:<id>:<win> — auto-bundle during audio attention

        item:pic:X and context:pic:X:<win> group together under item key X.
        O(n) single pass over all entries."""
        import re
        groups = {}   # item_key -> {"sections": set, "entries": list}
        for entries in self.entries.values():
            for e in entries:
                if e["strength"] < FORGETTING_THRESHOLD:
                    continue
                bid = e.get("bundle_id")
                if not bid:
                    continue
                # Extract item key: pic/snd id, or bundle name+tick
                m = re.match(r"(?:item|context):(pic|snd):([^:]+)", bid)
                if m:
                    item_key = f"{m.group(1)}:{m.group(2)}"
                else:
                    # bundle:<name>:<tick> — use full bid as key
                    item_key = bid
                if item_key not in groups:
                    groups[item_key] = {"sections": set(), "entries": []}
                groups[item_key]["sections"].add(e["section"])
                groups[item_key]["entries"].append(e)
        # Return only groups with 2+ distinct sections (cross-modal)
        return [(k, g["sections"], g["entries"])
                for k, g in groups.items() if len(g["sections"]) >= 2]

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
