"""
Deep Atlas — two-layer memory with dual promotion gate.

GL-BRIEF-DEEPATLAS-DEPLOY-WC-20260610-032

Write path: dream cycle ONLY (never written by live attention).
Read path: on-attention additive prior, entry-specific, capped.
Persistence: separate table (guala_deep_atlas.json) for clean rollback.

Kill switches: DEEP_ATLAS_ENABLED (promotions), DEEP_PRIOR_ENABLED (read path).
"""

import math
import os
from collections import defaultdict

# Use same constants as working atlas
DECAY_LAMBDA = 0.0001 / 25.0   # 1/25th of working (0.000004)
FORGETTING_THRESHOLD = 0.02
STRENGTH_CAP = 1.0
PRIOR_CAP = 0.15               # max additive prior (saturation guard)

# Gate constants
ENCODE_GATE = 0.15              # compound gate: encoded_strength >= this
DWELL_GATE = 4                  # compound gate: AND dwell_ticks >= this
SURVIVAL_THETA = 0.4            # Path A: binding must stay above this
SURVIVAL_CONSECUTIVE = 3        # Path A: for this many consecutive dream cycles
TRANSFER_RATIO = 0.5            # deep starts at this fraction of working strength

# GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1: the threshold
# gualaloom_v5_engine.py's _entry_grants_grounding uses on a PROMOTED deep
# entry's own accumulated `strength` to decide it has earned real-speech
# eligibility (see that function's docstring). Deliberately reuses
# SURVIVAL_THETA itself rather than defining a second, parallel notion of
# "promoted enough" -- this is the same bar Path A already requires the
# WORKING-atlas evidence to clear (repeatedly, for SURVIVAL_CONSECUTIVE
# dream cycles) before an entry is even created here; requiring the DEEP
# entry's own post-TRANSFER_RATIO strength to independently reach that
# same fraction of STRENGTH_CAP means real, repeated post-promotion
# reinforcement, not just scraping past the gate once.
ELIGIBILITY_STRENGTH_THETA = SURVIVAL_THETA

# GL-CMD-DEEP-STORE-PHYSICS-86 Part 1: bounded co_occurrence container
# P1b derived floor: minimum single-step contribution from a band entry at
# the working-atlas forgetting threshold from zero weight:
#   new_w = 0*(1-FORGETTING_THRESHOLD) + FORGETTING_THRESHOLD^2 = FORGETTING_THRESHOLD^2
# Entries below this have never received meaningful reinforcement.
_CO_PRUNE_THRESH = FORGETTING_THRESHOLD ** 2  # 0.0004

# GL-BUG-HARD-NEIGHBORHOOD-CUTOFF follow-on (deferred by 983dfb3, applied
# here in _update_invariant): same decay constant and mean-normalization
# gualaloom_v6_living_atlas.py's match_score uses, for the same working
# atlas band (working_atlas is that same LivingAtlas class).
CHI_DISTANCE_DECAY = 0.5


def _deep_atlas_enabled():
    return os.environ.get("DEEP_ATLAS_ENABLED", "1") != "0"

def _deep_prior_enabled():
    return os.environ.get("DEEP_PRIOR_ENABLED", "1") != "0"


class DeepAtlas:
    """Near-zero-decay atlas. Write = dream only. Read = on-attention prior."""

    def __init__(self):
        # chi_value -> list of deep entries
        self.entries = defaultdict(list)
        self.tick = 0
        # Instrumentation
        self.promotions_survival = 0
        self.promotions_episodic = 0
        self.gate_rejects = []  # recent rejects for diagnostics (capped)
        # Cache env-var reads at init time — these flags don't change at runtime.
        self._prior_enabled = _deep_prior_enabled()
        self._atlas_enabled = _deep_atlas_enabled()

    def promote(self, entry, source_path, tick, working_atlas=None):
        """Promote a working atlas entry into deep storage.
        Called ONLY during dream cycle. Two paths, same write.
        GL-CLARITY-INVARIANCE-UNCAGE: inherits clarity, sensory_refs,
        episode_refs from working atlas. Initializes co_occurrence invariant."""
        if not self._atlas_enabled:
            return False
        self.tick = max(self.tick, tick)
        chi_k = entry.get("chi", 0)
        section = entry.get("section", "")
        motif = entry.get("motif", 0)

        # Check if already in deep — reinforce + update invariant
        for de in self.entries[chi_k]:
            if de["section"] == section and de["motif"] == motif:
                de["strength"] = min(STRENGTH_CAP,
                                     de["strength"] + entry["strength"] * TRANSFER_RATIO)
                de["last_tick"] = tick
                # GL-CLARITY: update clarity (max of existing and incoming)
                de["clarity"] = max(de.get("clarity", 0.3),
                                    entry.get("clarity", 0.3))
                # GL-METADATA-PIPELINE: propagate affect (max) + source (last-write-wins) + polarity
                de["arousal"] = max(de.get("arousal", 0.5), entry.get("arousal", 0.5))
                de["valence"] = max(de.get("valence", 0.0), entry.get("valence", 0.0))
                de["surprise"] = max(de.get("surprise", 0.0), entry.get("surprise", 0.0))
                de["source"] = entry.get("source", "corpus")
                # GL-CLARITY: update co_occurrence invariant on re-promotion
                if working_atlas:
                    self._update_invariant(de, chi_k, working_atlas)
                return True

        # New deep entry — carry response links on promotion (GL-BRIEF-028 Amendment A)
        deep_entry = {
            "section": section,
            "motif": motif,
            "chi": chi_k,
            "strength": entry["strength"] * TRANSFER_RATIO,
            "last_tick": tick,
            "born_tick": tick,
            "encoded_strength_at_write": entry.get("encoded_strength", entry["strength"]),
            "dwell_at_write": entry.get("dwell_ticks", 0),
            "source_path": source_path,
            "promoted_at_tick": tick,
            # GL-CLARITY-INVARIANCE-UNCAGE: inherit from working atlas entry
            "clarity": entry.get("clarity", 0.3),
            "initial_clarity": entry.get("initial_clarity", 0.3),
            # GL-METADATA-PIPELINE: raw affect + source + polarity for 8D grandurun
            "arousal": entry.get("arousal", 0.5),
            "valence": entry.get("valence", 0.0),
            "surprise": entry.get("surprise", 0.0),
            "source": entry.get("source", "corpus"),
            "polarity": 1.0,  # TODO: derive polarity from sentiment when grounded text pipeline available
            "sensory_refs": list(entry.get("sensory_refs", [])),
            "episode_refs": list(entry.get("episode_refs", [])),
            "co_occurrence": {},  # section_name -> {motif_id: weight}
        }
        # Copy response link fields if present — Q&A pairs survive as pairs
        if entry.get("response_context"):
            deep_entry["response_context"] = list(entry["response_context"])
        if entry.get("received_response"):
            deep_entry["received_response"] = list(entry["received_response"])
        # GL-CLARITY: initialize co_occurrence from current atlas neighborhood
        if working_atlas:
            self._update_invariant(deep_entry, chi_k, working_atlas)
        self.entries[chi_k].append(deep_entry)

        if source_path == "survival":
            self.promotions_survival += 1
        elif source_path == "episodic":
            self.promotions_episodic += 1
        return True

    def _update_invariant(self, deep_entry, chi_k, working_atlas):
        """Update co_occurrence invariant dict using strength-weighted integration.

        GL-CMD-DAYDREAM-PARALLEL-42 §2.3: replaced 0.92/0.08 EMA constants with
        weight = e["strength"]. Integration rate equals the evidence's own strength:
        strong bindings integrate fast, weak ones integrate slowly.
        new_w = old_w * (1 - strength) + strength * strength

        §2.4: removed 0.05 strength floor. Newly-arrived motifs (e.g. DNA-expanded
        modifier/ground from -36) now contribute proportionally at any strength.

        GL-BUG-HARD-NEIGHBORHOOD-CUTOFF follow-on (deferred by 983dfb3,
        applied here): the band loop below used to treat every entry within
        the working atlas's search band as equally relevant regardless of
        its distance from chi_k -- the same hard-cutoff bug match_score had
        before that fix. This feeds live daydream/novel-jump writes (see
        gualaloom_v5_engine.py's _daydream_tick), so it was worth doing for
        real. Each entry's strength is scaled by the same mean-normalized
        exp(-CHI_DISTANCE_DECAY*|d|) falloff match_score uses (an entry
        spread evenly across the band integrates the same as before), then
        clamped to 1.0 before it's used as the EMA integration rate /
        evidence weight below -- required because an on-target weight_scale
        exceeds 1.0 with this decay constant, and the new_w formula assumes
        strength in [0, 1] (an unclamped value would flip the sign of the
        (1 - strength) term)."""
        co = deep_entry.get("co_occurrence", {})
        band = getattr(working_atlas, 'band', 2)

        offsets = range(-band, band + 1)
        decays = [math.exp(-CHI_DISTANCE_DECAY * abs(d)) for d in offsets]
        mean_decay = sum(decays) / len(decays)

        # P1a: snapshot pre-call mass per section for mass conservation
        touched = set()
        pre_masses = {}

        for d, decay in zip(offsets, decays):
            weight_scale = decay / mean_decay
            for e in working_atlas.entries.get(chi_k + d, []):
                # §2.4: no strength floor — proportional contribution at any strength
                raw_strength = e.get("strength", 0.0)
                if raw_strength <= 0.0:
                    continue
                strength = min(1.0, raw_strength * weight_scale)
                sec = e.get("section", "")
                mid = str(e.get("motif", 0))
                sec_dict = co.get(sec, {})
                if sec not in touched:
                    pre_masses[sec] = sum(sec_dict.values())
                    touched.add(sec)
                old_w = sec_dict.get(mid, 0.0)
                # §2.3: substrate-physical integration rate = evidence strength
                new_w = old_w * (1.0 - strength) + strength * strength
                # P1b: prune below derived floor immediately
                if new_w < _CO_PRUNE_THRESH:
                    sec_dict.pop(mid, None)
                else:
                    sec_dict[mid] = new_w
                if sec_dict:
                    co[sec] = sec_dict
                elif sec in co:
                    del co[sec]

        # P1a: per-section mass conservation — reinforcement draws proportionally
        # from existing weights so section total cannot grow beyond its pre-call mass.
        # Sections with no prior mass (newly established) are exempt; their mass
        # is set by first reinforcement.
        for sec in touched:
            sec_dict = co.get(sec, {})
            if not sec_dict:
                continue
            M_pre = pre_masses.get(sec, 0.0)
            if M_pre <= 0.0:
                continue  # newly established section — mass set by first reinforcement
            M_post = sum(sec_dict.values())
            if M_post > M_pre:
                scale = M_pre / M_post
                for k in list(sec_dict.keys()):
                    sec_dict[k] *= scale
                    if sec_dict[k] < _CO_PRUNE_THRESH:
                        del sec_dict[k]
            if sec_dict:
                co[sec] = sec_dict
            elif sec in co:
                del co[sec]

        deep_entry["co_occurrence"] = co

    def get_invariant(self, chi_value, section_name, motif_id):
        """Retrieve co_occurrence invariant for a cortex entry."""
        for de in self.entries.get(chi_value, []):
            if de["section"] == section_name and de["motif"] == motif_id:
                return de.get("co_occurrence", {})
        return {}

    def decay(self, current_tick, rate_scale=1.0, max_dt=500):
        """Near-zero decay (1/25th of working).
        GL-BRIEF-SLEEP-DECAY-PERMANENT: pause-idempotent, same shape as
        working atlas (efd39dd). rate_scale=0 when DECAY_PAUSED=1 keeps
        last_tick current with bit-identical strength.
        max_dt caps effective decay window per call."""
        self.tick = max(self.tick, current_tick)
        for entries in self.entries.values():
            for e in entries:
                dt = min(max_dt, max(0, current_tick - e["last_tick"]))
                if dt > 0:
                    e["strength"] *= math.exp(-DECAY_LAMBDA * rate_scale * dt)
                    e["last_tick"] = current_tick

    def prune(self):
        """Remove entries below forgetting threshold."""
        for chi_k in list(self.entries.keys()):
            survivors = [e for e in self.entries[chi_k]
                         if e["strength"] >= FORGETTING_THRESHOLD]
            if survivors:
                self.entries[chi_k] = survivors
            else:
                del self.entries[chi_k]

    def get_prior(self, chi_value, section, motif):
        """On-attention additive prior. Entry-specific (section+motif match).
        Returns 0.0 if DEEP_PRIOR_ENABLED=0."""
        if not self._prior_enabled:
            return 0.0
        for e in self.entries.get(chi_value, []):
            if (e["strength"] >= FORGETTING_THRESHOLD
                    and e["section"] == section and e["motif"] == motif):
                return min(PRIOR_CAP, e["strength"] * 0.3)
        return 0.0

    def dream_promotion_gate(self, working_atlas, tick, survival_history):
        """Evaluate both promotion paths at dream time.

        Path A (Survival): binding above theta for S consecutive dreams.
        Path B (Episodic): encoded_strength >= ENCODE_GATE AND dwell >= DWELL_GATE.
                          Gate reads values at TAG time (stored on entry).

        Returns list of (path, chi, section, motif) promoted."""
        if not self._atlas_enabled:
            return []

        promoted = []
        band = getattr(working_atlas, 'band', 2)

        for chi_k, entries in working_atlas.entries.items():
            for e in entries:
                if e["strength"] < FORGETTING_THRESHOLD:
                    continue

                key = (chi_k, e.get("section", ""), e.get("motif", 0))

                # --- Path A: Survival ---
                if key in survival_history:
                    history = survival_history[key]
                    recent = history[-SURVIVAL_CONSECUTIVE:]
                    if (len(recent) >= SURVIVAL_CONSECUTIVE
                            and all(s >= SURVIVAL_THETA for s in recent)):
                        self.promote(e, "survival", tick,
                                     working_atlas=working_atlas)
                        promoted.append(("survival", chi_k,
                                         e.get("section"), e.get("motif")))
                        continue  # don't double-promote

                # --- Path B: Episodic (compound gate) ---
                enc_str = e.get("encoded_strength")
                dwell = e.get("dwell_ticks", 0)
                # GL-CMD-GROUNDED-PROMOTION-35: cross-modal grounding (bundle_id set)
                # is dwell-earning. Text writes linked to a sensory modality write
                # in the same tick window share a bundle_id (sight_frame:<tick> or
                # sound_frame:<tick>). Same principle as dream consolidation IS
                # dwell-earning (gualaloom_v6_living_atlas.py line 108).
                grounded = e.get("bundle_id") is not None
                if enc_str is not None and enc_str >= ENCODE_GATE and (dwell >= DWELL_GATE or grounded):
                    self.promote(e, "episodic", tick,
                                 working_atlas=working_atlas)
                    promoted.append(("episodic", chi_k,
                                     e.get("section"), e.get("motif")))
                else:
                    # Log gate reject (capped for memory)
                    if enc_str is not None and len(self.gate_rejects) < 200:
                        failed_gate = []
                        if enc_str < ENCODE_GATE:
                            failed_gate.append(f"enc={enc_str:.3f}<{ENCODE_GATE}")
                        if dwell < DWELL_GATE and not grounded:
                            failed_gate.append(f"dwell={dwell}<{DWELL_GATE} (not grounded)")
                        if failed_gate:
                            self.gate_rejects.append({
                                "tick": tick, "chi": chi_k,
                                "section": e.get("section"),
                                "motif": e.get("motif"),
                                "failed": ", ".join(failed_gate),
                            })

        return promoted

    # --- Instrumentation ---

    def live_count(self):
        return sum(1 for es in self.entries.values()
                   for e in es if e["strength"] >= FORGETTING_THRESHOLD)

    def total_strength(self):
        return sum(e["strength"] for es in self.entries.values()
                   for e in es if e["strength"] >= FORGETTING_THRESHOLD)

    def snapshot(self):
        """For /status deep block."""
        return {
            "n_entries": self.live_count(),
            "total_strength": round(self.total_strength(), 2),
            "promotions_survival": self.promotions_survival,
            "promotions_episodic": self.promotions_episodic,
            "enabled": _deep_atlas_enabled(),
            "prior_enabled": _deep_prior_enabled(),
            "recent_gate_rejects": self.gate_rejects[-5:],
        }

    # --- Persistence (separate table) ---

    def to_json(self):
        """Serialize for guala_deep_atlas.json."""
        live = self.live_count()
        entries_ser = {}
        for chi_k, es in self.entries.items():
            entries_ser[str(chi_k)] = [
                {k: v for k, v in e.items()} for e in es
            ]
        return {
            "schema": "deep_atlas_v1",
            "tick": self.tick,
            "saved_n_entries": live,           # GL-CMD-DEEP-ATLAS-PERSIST: count at save
            "entries": entries_ser,
            "promotions_survival": self.promotions_survival,
            "promotions_episodic": self.promotions_episodic,
        }

    def load_from_json(self, data):
        """Restore from guala_deep_atlas.json.
        Returns saved_n_entries so caller can run loss alarm."""
        if data.get("schema") != "deep_atlas_v1":
            print("[deep_atlas] Unknown schema — starting fresh")
            return 0
        self.tick = data.get("tick", 0)
        self.promotions_survival = data.get("promotions_survival", 0)
        self.promotions_episodic = data.get("promotions_episodic", 0)
        self.entries = defaultdict(list)
        for k, es in data.get("entries", {}).items():
            self.entries[int(k)] = list(es)
        return data.get("saved_n_entries", self.live_count())
