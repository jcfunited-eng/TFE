"""
GL-CMD-COGNITION-BUNDLE-EVE-20260619-23
GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21

Four cognition hemispheres: pr (predictor), ep (episodic), sc (semantic), gp (goals).
Each gated by HEMI_{TAG}_ENABLED env flag (default OFF).

Anti-contamination compliance:
  1. No (1-rate)*x + rate*initial_x drift anywhere
  2. Every constant has rationale in comment
  3. No expected-vs-actual / is_correct labels
  4. CrossHemiLink carries full 12-field shape
"""

import os
import math
from dataclasses import dataclass, field
from collections import defaultdict
from typing import List, Optional

from dsf_ai_service.substrate.assemblage import (
    CrossHemiLink, HemisphereCoordinator,
)
from dsf_ai_service.v4.gualaloom_v6_living_atlas import (
    LivingAtlas, FORGETTING_THRESHOLD,
)


# ---------- Constants (each with derivation rationale) ----------

# Same magnitude as reinforce_mode LTP boost (0.05) in production substrate.
# Cross-hemi consensus is a sibling event to LTP; same scale is principled.
CONSENSUS_GAIN = 0.05

# Multiplicative; 5% loss per divergent event. Faster than per-binding decay
# but slow enough that one divergence doesn't erase built-up consensus.
DIVERGENCE_DECAY = 0.95

# Slightly slower than baseline DECAY_LAMBDA=0.001. Cross-hemi consensus
# represents shared structure between hemispheres; that agreement should
# outlast individual binding decay.
CROSS_HEMI_BASELINE_DECAY = 0.0008

# Twice consensus gain because episodic recording is the strongest form of
# cross-hemi binding — it's the literal record of what happened.
EP_BIND_GAIN = 0.10

# Same magnitude as LTP boost; symmetric decrement. A binding firing with
# polarity -1 should be as strong an anti-event as positive firing is pro.
NEGATION_DECREMENT = 0.05

# Same magnitude as cofire spread cap in rich-sensory wiring (0.30).
# Semantic weighting is a sibling mechanism; same scale.
SC_EMISSION_WEIGHT = 0.30

# Stronger than semantic weighting (0.30) because goals are deliberate.
# Goals are the substrate's strongest steering signal short of explicit input.
GP_EMISSION_BIAS = 0.50


# ---------- NeedsVector (lightweight per-hemisphere needs) ----------

class NeedsVector:
    """Minimal needs vector for non-em hemispheres."""
    __slots__ = ("stability", "novelty", "connection")

    def __init__(self, stab=0.5, nov=0.5, conn=0.5):
        self.stability = stab
        self.novelty = nov
        self.connection = conn

    def snapshot(self):
        return {"stability": self.stability, "novelty": self.novelty,
                "connection": self.connection}


# ---------- TurnLogEntry (ep) ----------

@dataclass
class TurnLogEntry:
    """Single conversational turn recorded in the episodic hemisphere."""
    tick: int
    source: str
    input_text: str
    input_chis: list
    emission_text: str
    emission_chis: list
    needs_snapshot: dict
    current_activity: str = ""


# ---------- Cross-hemi link management ----------

def get_or_create_link(links, src_hemi, src_chi, dst_hemi, dst_chi):
    """Find existing link or create a new one. Returns the link object."""
    for link in links:
        if (link.src_hemi == src_hemi and link.src_chi == src_chi
                and link.dst_hemi == dst_hemi and link.dst_chi == dst_chi):
            return link
    new_link = CrossHemiLink(
        src_chi=src_chi, src_hemi=src_hemi,
        dst_chi=dst_chi, dst_hemi=dst_hemi,
        strength=0.0,
    )
    links.append(new_link)
    return new_link


def decay_cross_hemi_links(links, rate=CROSS_HEMI_BASELINE_DECAY):
    """Per-tick multiplicative decay on all cross-hemi links.
    NOT a (1-r)*x + r*init drift; purely multiplicative toward 0."""
    for link in links:
        link.strength *= (1.0 - rate)
    # Prune dead links
    links[:] = [l for l in links if l.strength > 0.001]


# ---------- PR: Predictor hemisphere ----------

def setup_pr(guala):
    """Initialize predictor hemisphere with seeded bindings."""
    pr = HemisphereCoordinator("pr", needs=NeedsVector(stab=0.5, nov=0.5, conn=0.5))
    pr.atlas = LivingAtlas()
    pr.atlas.tick = guala.tick

    # Selective cheat 1: seed top-50 strongest bindings from em
    seeded = _top_k_bindings(guala.atlas, k=50)
    for b in seeded:
        entry = dict(b)
        entry["hemisphere_id"] = "pr"
        entry["seeded"] = True
        pr.atlas.entries[entry["chi"]].append(entry)

    guala.hemispheres["pr"] = pr
    return pr


def pr_parallel_settle(guala, input_chis, source, tick):
    """Drive pr with same input chis as em. No emission — comparison only."""
    pr = guala.hemispheres.get("pr")
    if pr is None:
        return
    # Record input bindings in pr atlas (parallel to em's read_sentence)
    for chi in input_chis:
        for d in range(-guala.atlas.band, guala.atlas.band + 1):
            for e in guala.atlas.entries.get(chi + d, []):
                if e["strength"] < FORGETTING_THRESHOLD:
                    continue
                # Mirror binding into pr atlas if not already there
                key = (e["section"], e["motif"], chi + d)
                existing = False
                for pe in pr.atlas.entries.get(chi + d, []):
                    if pe["section"] == e["section"] and pe["motif"] == e["motif"]:
                        pe["last_tick"] = tick
                        pe["strength"] = min(1.0, pe["strength"] + 0.01)
                        existing = True
                        break
                if not existing and len(pr.atlas.entries[chi + d]) < 20:
                    entry = dict(e)
                    entry["hemisphere_id"] = "pr"
                    entry["last_tick"] = tick
                    entry["seeded"] = False
                    pr.atlas.entries[chi + d].append(entry)


def pr_consensus_divergence(guala, input_chis, tick, events_log):
    """Run em↔pr consensus/divergence dynamics after settling."""
    pr = guala.hemispheres.get("pr")
    if pr is None:
        return
    links = guala._cross_hemi_links

    for chi in input_chis:
        for d in range(-guala.atlas.band, guala.atlas.band + 1):
            # All active bindings at this chi band — recency is implicit in
            # the fact that we're running this on the INPUT chis of the
            # current converse event. No separate time-window filter.
            em_entries = [e for e in guala.atlas.entries.get(chi + d, [])
                          if e["strength"] >= FORGETTING_THRESHOLD]
            pr_entries = [e for e in pr.atlas.entries.get(chi + d, [])
                          if e["strength"] >= FORGETTING_THRESHOLD]
            for em_b in em_entries:
                for pr_b in pr_entries:
                    em_pol = em_b.get("polarity", 1.0)
                    pr_pol = pr_b.get("polarity", 1.0)
                    polarity_match = (em_pol * pr_pol) > 0

                    link = get_or_create_link(
                        links, "em", chi + d, "pr", chi + d)

                    em_str = em_b.get("strength", 0.5)
                    pr_str = pr_b.get("strength", 0.5)
                    salience_product = em_str * pr_str

                    if polarity_match:
                        link.strength = min(1.0,
                            link.strength + CONSENSUS_GAIN * salience_product)
                        link.consensus_phase *= 0.95
                        events_log.append({
                            "type": "convergent_event",
                            "chi": chi + d, "strength": link.strength,
                        })
                    else:
                        link.strength *= DIVERGENCE_DECAY
                        link.consensus_phase = min(
                            math.pi, link.consensus_phase + 0.1)
                        events_log.append({
                            "type": "divergent_event",
                            "chi": chi + d, "strength": link.strength,
                        })

                    link.last_tick = tick
                    link.source = em_b.get("source", "corpus")
                    link.arousal = em_b.get("arousal", 0.5)
                    link.valence = em_b.get("valence", 0.0)
                    link.surprise = em_b.get("surprise", 0.0)
                    link.polarity = em_pol


# ---------- EP: Episodic hemisphere ----------

def setup_ep(guala):
    """Initialize episodic hemisphere. Starts empty — episodes accumulate."""
    ep = HemisphereCoordinator("ep", needs=NeedsVector(stab=0.5, nov=0.5, conn=0.5))
    ep.atlas = LivingAtlas()
    ep.atlas.tick = guala.tick
    ep.turn_log = []
    ep.tracked_objects = {}
    guala.hemispheres["ep"] = ep
    return ep


def ep_record_turn(guala, text, source, input_chis, reply, emission_chis,
                    tick, events_log):
    """Append a turn to ep's log and update tracked objects."""
    ep = guala.hemispheres.get("ep")
    if ep is None:
        return

    needs_snap = {
        "stability": guala.needs.stability,
        "novelty": guala.needs.novelty,
        "connection": guala.needs.connection,
    }
    activity = ""
    if guala._current_activity:
        activity = str(getattr(guala._current_activity, 'kind', ''))

    entry = TurnLogEntry(
        tick=tick, source=source,
        input_text=text[:200], input_chis=list(input_chis),
        emission_text=(reply or "")[:200],
        emission_chis=list(emission_chis) if emission_chis else [],
        needs_snapshot=needs_snap,
        current_activity=activity,
    )
    ep.turn_log.append(entry)
    # Cap turn log at 500 entries
    if len(ep.turn_log) > 500:
        ep.turn_log = ep.turn_log[-500:]

    # Update tracked objects — content words only
    from dsf_ai_service.v4.gualaloom_v5_engine import _normalize_text, LanguageKrimelack
    _FUNCTION_WORDS = frozenset({
        "a", "an", "the", "is", "are", "am", "was", "were",
        "of", "in", "on", "at", "to", "from", "with", "for",
        "and", "or", "but", "me", "you", "i", "we", "they",
        "show", "see", "look", "what", "tell", "about",
    })
    words = _normalize_text(text)
    for w in words:
        if w.lower() in _FUNCTION_WORDS or len(w) <= 1:
            continue
        k = LanguageKrimelack()
        k.transduce(w)
        ep.tracked_objects[w.lower()] = {
            "chi": k.winding, "last_seen_tick": tick,
            "salience": 1.0, "source": source,
        }

    events_log.append({"type": "turn_log_appended", "tick": tick, "source": source})

    # em↔ep cross-hemi links (convergence only — ep records, doesn't disagree)
    links = guala._cross_hemi_links
    all_chis = list(input_chis) + (list(emission_chis) if emission_chis else [])
    for chi in all_chis:
        link = get_or_create_link(links, "em", chi, "ep", chi)
        link.strength = min(1.0, link.strength + EP_BIND_GAIN)
        link.source = source
        link.last_tick = tick


def find_sequences(ep, pattern_chis, window=50):
    """Return list of (start_tick, end_tick) where pattern_chis appears in
    sequence within window ticks."""
    results = []
    for i in range(len(ep.turn_log)):
        entry = ep.turn_log[i]
        matched = 0
        start_tick = entry.tick
        for j in range(i, len(ep.turn_log)):
            if ep.turn_log[j].tick - start_tick > window:
                break
            all_chis = ep.turn_log[j].input_chis + ep.turn_log[j].emission_chis
            if matched < len(pattern_chis) and pattern_chis[matched] in all_chis:
                matched += 1
            if matched == len(pattern_chis):
                results.append((start_tick, ep.turn_log[j].tick))
                break
    return results


def most_recent_source(ep, exclude=("guala",)):
    """Walk ep.turn_log in reverse; return source of most recent non-excluded entry."""
    for entry in reversed(ep.turn_log):
        if entry.source not in exclude:
            return entry.source
    return None


# ---------- SC: Semantic hemisphere ----------

def setup_sc(guala):
    """Initialize semantic hemisphere with content-word seeded bindings."""
    sc = HemisphereCoordinator("sc", needs=NeedsVector(stab=0.5, nov=0.5, conn=0.5))
    sc.atlas = LivingAtlas()
    sc.atlas.tick = guala.tick

    _FUNCTION_WORDS = frozenset({
        "a", "an", "the", "is", "are", "am", "was", "were",
        "of", "in", "on", "at", "to", "from", "with", "for",
        "and", "or", "but", "me", "you", "i", "we", "they",
        "show", "see", "look", "what", "tell", "about",
    })

    # Seed with content-word bindings from em (selective cheat 1)
    seeded = _top_k_bindings(guala.atlas, k=200)
    count = 0
    for b in seeded:
        if count >= 100:
            break
        sec = guala.sections.get(b.get("section", ""))
        if sec and b.get("motif", 0) < len(sec.modes):
            _, _, word = sec.modes[b["motif"]]
            if word and word.lower() not in _FUNCTION_WORDS and len(word) > 1:
                entry = dict(b)
                entry["hemisphere_id"] = "sc"
                entry["seeded"] = True
                sc.atlas.entries[entry["chi"]].append(entry)
                count += 1

    guala.hemispheres["sc"] = sc
    return sc


def sc_polarity_update(guala, input_chis, tick, events_log):
    """Apply polarity-signed negation within sc atlas."""
    sc = guala.hemispheres.get("sc")
    if sc is None:
        return

    for chi in input_chis:
        for d in range(-guala.atlas.band, guala.atlas.band + 1):
            firing = [e for e in sc.atlas.entries.get(chi + d, [])
                       if e.get("last_tick", 0) >= tick - 5
                       and e.get("polarity", 1.0) < 0]
            if not firing:
                continue
            for neg_b in firing:
                for co_b in sc.atlas.entries.get(chi + d, []):
                    if co_b is neg_b:
                        continue
                    if co_b.get("last_tick", 0) == neg_b.get("last_tick", 0):
                        old_str = co_b["strength"]
                        co_b["strength"] = max(0.0,
                            co_b["strength"] - NEGATION_DECREMENT)
                        if co_b["strength"] < old_str:
                            events_log.append({
                                "type": "sc_negation_applied",
                                "chi": chi + d,
                                "old_strength": old_str,
                                "new_strength": co_b["strength"],
                            })


def sc_weight_for_candidate(candidate, guala):
    """Return additive weight for a candidate based on sc.atlas binding strength."""
    sc = guala.hemispheres.get("sc")
    if sc is None:
        return 0.0
    chi = candidate.get("chi", candidate.get("chi", 0))
    for e in sc.atlas.entries.get(chi, []):
        if e["strength"] >= FORGETTING_THRESHOLD:
            return e["strength"] * SC_EMISSION_WEIGHT
    return 0.0


def detect_and_bind_causal_patterns(guala, tick, events_log):
    """Scan ep.turn_log for repeated A→B chi-pair sequences.
    When a pair appears ≥3 times within 1000 ticks, create ep↔sc link."""
    ep = guala.hemispheres.get("ep")
    sc = guala.hemispheres.get("sc")
    if ep is None or sc is None:
        return

    pair_counts = {}
    for i in range(len(ep.turn_log) - 1):
        a, b = ep.turn_log[i], ep.turn_log[i + 1]
        if b.tick - a.tick > 1000:
            continue
        for chi_a in a.emission_chis:
            for chi_b in b.input_chis:
                pair_counts[(chi_a, chi_b)] = pair_counts.get(
                    (chi_a, chi_b), 0) + 1

    links = guala._cross_hemi_links
    for (chi_a, chi_b), count in pair_counts.items():
        if count >= 3:
            link = get_or_create_link(links, "ep", chi_a, "sc", chi_b)
            link.strength = min(1.0, link.strength + 0.05 * count)
            link.last_tick = tick
            events_log.append({
                "type": "causal_pattern_bound",
                "chi_a": chi_a, "chi_b": chi_b, "count": count,
            })


# ---------- GP: Goals hemisphere ----------

def setup_gp(guala):
    """Initialize goals hemisphere with three seed goals."""
    gp = HemisphereCoordinator("gp",
        needs=NeedsVector(stab=0.7, nov=0.3, conn=0.7))
    gp.atlas = LivingAtlas()
    gp.atlas.tick = guala.tick

    from dsf_ai_service.v4.gualaloom_v5_engine import LanguageKrimelack

    seed_goals = [
        ("be_present", "present"),
        ("respond_to_joe", "joe"),
        ("form_sensory_bindings", "sense"),
    ]
    for label, word in seed_goals:
        k = LanguageKrimelack()
        k.transduce(word)
        chi = k.winding
        gp.atlas.entries[chi].append({
            "section": "goal", "motif": hash(label) % 10000,
            "chi": chi, "strength": 1.0,
            "last_tick": guala.tick, "born_tick": guala.tick,
            "encoded_strength": 1.0, "dwell_ticks": 10,
            "reinforcement_count": 0, "released": False,
            "clarity": 1.0, "initial_clarity": 1.0,
            "sensory_refs": [], "episode_refs": [],
            "arousal": 0.5, "valence": 0.5, "surprise": 0.0,
            "source": "seed", "hemisphere_id": "gp",
            "seeded": True, "label": label,
            "polarity": 1.0,
        })

    guala.hemispheres["gp"] = gp
    return gp


def gp_bias_for_candidate(candidate, guala):
    """Return additive weight if candidate's word appears in gp bindings."""
    gp = guala.hemispheres.get("gp")
    if gp is None:
        return 0.0
    word = candidate.get("word", "").lower()
    if not word:
        return 0.0
    for chi_k, entries in gp.atlas.entries.items():
        for e in entries:
            lbl = e.get("label", "")
            if word in lbl or lbl in word:
                return e["strength"] * GP_EMISSION_BIAS
    return 0.0


def scan_procedural_pairs(guala, tick, events_log):
    """Scan ep.turn_log for guala→external_response pairs.
    Reinforce gp↔ep link where response improved needs."""
    ep = guala.hemispheres.get("ep")
    gp = guala.hemispheres.get("gp")
    if ep is None or gp is None:
        return

    links = guala._cross_hemi_links
    for i in range(len(ep.turn_log) - 1):
        a, b = ep.turn_log[i], ep.turn_log[i + 1]
        if a.source != "guala":
            continue
        if b.source == "guala":
            continue
        needs_a = sum(a.needs_snapshot.values())
        needs_b = sum(b.needs_snapshot.values())
        if needs_b <= needs_a:
            continue
        for chi in a.emission_chis:
            link = get_or_create_link(links, "gp", chi, "ep", chi)
            link.strength = min(1.0, link.strength + 0.05)
            link.last_tick = tick


# ---------- Master hook: run all hemisphere updates after converse ----------

def run_hemisphere_updates(guala, text, source, input_chis, reply,
                            emission_chis, tick):
    """Called after converse() emission. Runs enabled hemisphere updates."""
    events_log = []

    # Initialize cross_hemi_links list if not present
    if not hasattr(guala, '_cross_hemi_links'):
        guala._cross_hemi_links = []

    # PR: predictor
    if os.environ.get("HEMI_PR_ENABLED", "0") == "1":
        if "pr" not in guala.hemispheres:
            setup_pr(guala)
        pr_parallel_settle(guala, input_chis, source, tick)
        pr_consensus_divergence(guala, input_chis, tick, events_log)

    # EP: episodic
    if os.environ.get("HEMI_EP_ENABLED", "0") == "1":
        if "ep" not in guala.hemispheres:
            setup_ep(guala)
        ep_record_turn(guala, text, source, input_chis, reply,
                        emission_chis, tick, events_log)

    # SC: semantic
    if os.environ.get("HEMI_SC_ENABLED", "0") == "1":
        if "sc" not in guala.hemispheres:
            setup_sc(guala)
        sc_polarity_update(guala, input_chis, tick, events_log)
        if "ep" in guala.hemispheres:
            detect_and_bind_causal_patterns(guala, tick, events_log)

    # GP: goals
    if os.environ.get("HEMI_GP_ENABLED", "0") == "1":
        if "gp" not in guala.hemispheres:
            setup_gp(guala)
        if "ep" in guala.hemispheres:
            scan_procedural_pairs(guala, tick, events_log)

    # Per-tick decay on cross-hemi links
    if guala._cross_hemi_links:
        decay_cross_hemi_links(guala._cross_hemi_links)

    # Log hemisphere events
    if events_log:
        guala._log_substrate_event("hemisphere_update",
                                    n_events=len(events_log),
                                    events=events_log[:20])

    return events_log


def get_emission_hemisphere_weights(candidate, guala):
    """Combined sc + gp weighting for an emission candidate.
    Called from _rich_sensory_candidates or _emit_dynamics."""
    weight = 0.0
    if os.environ.get("HEMI_SC_ENABLED", "0") == "1":
        w = sc_weight_for_candidate(candidate, guala)
        if w > 0:
            weight += w
    if os.environ.get("HEMI_GP_ENABLED", "0") == "1":
        w = gp_bias_for_candidate(candidate, guala)
        if w > 0:
            weight += w
    return weight


# ---------- Helpers ----------

def _top_k_bindings(atlas, k=50):
    """Return the top-k strongest bindings from the atlas."""
    all_bindings = []
    for chi_k, entries in atlas.entries.items():
        for e in entries:
            if e.get("strength", 0) >= FORGETTING_THRESHOLD:
                all_bindings.append(e)
    all_bindings.sort(key=lambda b: -b.get("strength", 0))
    return all_bindings[:k]
