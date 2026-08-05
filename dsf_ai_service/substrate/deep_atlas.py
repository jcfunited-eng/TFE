"""
Deep Atlas — two-layer memory with dual promotion gate.

GL-BRIEF-DEEPATLAS-DEPLOY-WC-20260610-032

Write path: dream cycle ONLY (never written by live attention).
Read path: on-attention additive prior, entry-specific, capped.
Persistence: separate table (guala_deep_atlas.json) for clean rollback.

Kill switches: DEEP_ATLAS_ENABLED (promotions), DEEP_PRIOR_ENABLED (read path).
"""

import copy
import json
import math
import os
import sys
from collections import defaultdict
from collections.abc import MutableMapping
from dataclasses import dataclass

from dsf_ai_service.substrate.deep_atlas_columnar import (
    SCHEMA as COLUMNAR_SCHEMA,
    DecodedColumnar,
    compact_v2_tables,
    decode_columnar_v3,
    encode_columnar_v3,
    mappings_equal,
    section_fingerprint,
    validate_columnar_v3,
)

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
DEEP_ATLAS_BUDGET_MB_ENV = "GUALA_DEEP_ATLAS_BUDGET_MB"
DEEP_ATLAS_DEFAULT_BUDGET_MB = 128


def _deep_atlas_budget_bytes():
    raw = os.environ.get(DEEP_ATLAS_BUDGET_MB_ENV)
    if raw is None:
        return DEEP_ATLAS_DEFAULT_BUDGET_MB * 1024 * 1024
    try:
        mb = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"{DEEP_ATLAS_BUDGET_MB_ENV} must be an integer MiB value") from exc
    if mb <= 0:
        raise ValueError(
            f"{DEEP_ATLAS_BUDGET_MB_ENV} must be greater than zero")
    return mb * 1024 * 1024


@dataclass(frozen=True)
class DeepAtlasCapacityRefusal:
    chi: int
    section: str
    motif: int
    current_bytes: int
    attempted_bytes: int
    budget_bytes: int
    operation: str


class DeepAtlasCapacityExceeded(RuntimeError):
    """Persisted deep state is larger than its declared resource owner."""


def _section_fingerprint(values):
    """Return the content address for one exact motif-weight mapping."""
    return section_fingerprint(values)


class _SectionView(MutableMapping):
    """Dictionary-compatible copy-on-write view of one shared section."""

    def __init__(self, owner, section):
        self._owner = owner
        self._section = section

    def __getitem__(self, key):
        return self._owner._section_values(self._section)[key]

    def __setitem__(self, key, value):
        self._owner._writable_section(self._section)[key] = value

    def __delitem__(self, key):
        del self._owner._writable_section(self._section)[key]

    def __iter__(self):
        return iter(self._owner._section_values(self._section))

    def __len__(self):
        return len(self._owner._section_values(self._section))


class _CoOccurrenceMap(MutableMapping):
    """Per-entry map whose unchanged section dictionaries are interned.

    The public behavior remains ``section -> {motif: weight}``.  A section is
    copied only when that particular deep entry mutates it, so sharing never
    changes the physics or couples two memories together.
    """

    def __init__(self, registry, values=None, references=None):
        self._registry = registry
        self._owned = {}
        self._references = {}
        for section, motif_values in (values or {}).items():
            self._owned[str(section)] = dict(motif_values)
        for section, reference in (references or {}).items():
            section = str(section)
            reference = sys.intern(str(reference))
            if reference not in registry:
                raise ValueError(
                    f"deep_atlas co-occurrence reference is missing: {reference}")
            self._references[section] = reference

    def _section_values(self, section):
        if section in self._owned:
            return self._owned[section]
        reference = self._references[section]
        return self._registry[reference]

    def _writable_section(self, section):
        section = str(section)
        if section not in self._owned:
            if section in self._references:
                frozen = self._registry[self._references.pop(section)]
                self._owned[section] = dict(frozen.items())
            else:
                self._owned[section] = {}
        return self._owned[section]

    def __getitem__(self, section):
        section = str(section)
        if section not in self._owned and section not in self._references:
            raise KeyError(section)
        return _SectionView(self, section)

    def __setitem__(self, section, values):
        section = str(section)
        if (isinstance(values, _SectionView)
                and values._owner is self and values._section == section):
            return
        self._owned[section] = dict(values)
        self._references.pop(section, None)

    def __delitem__(self, section):
        section = str(section)
        if section in self._owned:
            del self._owned[section]
            return
        if section in self._references:
            del self._references[section]
            return
        raise KeyError(section)

    def __iter__(self):
        return iter(dict.fromkeys((*self._references, *self._owned)))

    def __len__(self):
        return len(set(self._references) | set(self._owned))

    def immutable_section_values(self, section):
        """Return the exact shared table behind an immutable section.

        Restored deep-atlas entries normally refer to content-addressed,
        immutable section tables.  Read paths may safely cache a projection
        of one of those tables by its reference.  A section that has detached
        for a live write is owned and mutable, so it deliberately returns
        ``None`` and must be read directly every time.
        """
        section = str(section)
        reference = self._references.get(section)
        if reference is None:
            return None
        return reference, self._registry[reference]

    def setdefault(self, section, default=None):
        section = str(section)
        if section not in self:
            self._owned[section] = dict(default or {})
        return _SectionView(self, section)

    def persistence_references(self, output_tables):
        """Intern every section and return its exact persisted references."""
        references = {}
        for section in self:
            if section in self._references:
                reference = self._references[section]
                values = self._registry[reference]
            else:
                values = self._owned[section]
                reference = sys.intern(_section_fingerprint(values))
                existing = self._registry.get(reference)
                if (
                    existing is not None
                    and not mappings_equal(existing, values)
                ):
                    raise ValueError(
                        "deep_atlas co-occurrence content-address collision")
                if existing is None:
                    self._registry[reference] = values
                else:
                    values = existing
                self._references[section] = reference
                self._owned.pop(section, None)
            output_existing = output_tables.get(reference)
            if (
                output_existing is not None
                and not mappings_equal(output_existing, values)
            ):
                raise ValueError(
                    "deep_atlas output table content-address collision")
            output_tables[reference] = values
            references[section] = reference
        return references


def _deep_atlas_enabled():
    return os.environ.get("DEEP_ATLAS_ENABLED", "1") != "0"

def _deep_prior_enabled():
    return os.environ.get("DEEP_PRIOR_ENABLED", "1") != "0"


class DeepAtlas:
    """Near-zero-decay atlas. Write = dream only. Read = on-attention prior."""

    def __init__(self, max_bytes=None):
        # chi_value -> list of deep entries
        self.entries = defaultdict(list)
        # Exact content-addressed section dictionaries shared by entries.
        # Sharing is representation only; _CoOccurrenceMap detaches a section
        # before any mutation.
        self._co_occurrence_registry = {}
        self.tick = 0
        # Instrumentation
        self.promotions_survival = 0
        self.promotions_episodic = 0
        self.reinstatements = 0
        self.gate_rejects = []  # recent rejects for diagnostics (capped)
        self.max_bytes = (
            _deep_atlas_budget_bytes()
            if max_bytes is None else int(max_bytes))
        if self.max_bytes <= 0:
            raise ValueError("deep atlas max_bytes must be greater than zero")
        self._logical_bytes = 0
        self.capacity_refusals = []
        # Cache env-var reads at init time — these flags don't change at runtime.
        self._prior_enabled = _deep_prior_enabled()
        self._atlas_enabled = _deep_atlas_enabled()

    @staticmethod
    def _plain_co_occurrence(co_occurrence):
        return {
            str(section): dict(co_occurrence[section])
            for section in co_occurrence
        }

    @classmethod
    def _plain_entry(cls, entry):
        plain = {
            key: copy.deepcopy(value)
            for key, value in entry.items()
            if key != "co_occurrence"
        }
        plain["co_occurrence"] = cls._plain_co_occurrence(
            entry.get("co_occurrence", {}))
        return plain

    @classmethod
    def _entry_logical_bytes(cls, entry):
        return len(json.dumps(
            cls._plain_entry(entry), allow_nan=False, ensure_ascii=False,
            separators=(",", ":"), sort_keys=True).encode("utf-8"))

    def _install_plain_co_occurrence(self, entry):
        entry["co_occurrence"] = _CoOccurrenceMap(
            self._co_occurrence_registry,
            values=entry.get("co_occurrence", {}))
        return entry

    def _record_capacity_refusal(
            self, *, chi, section, motif, attempted_bytes, operation):
        refusal = DeepAtlasCapacityRefusal(
            chi=int(chi), section=str(section), motif=int(motif),
            current_bytes=self._logical_bytes,
            attempted_bytes=int(attempted_bytes),
            budget_bytes=self.max_bytes, operation=str(operation))
        self.capacity_refusals.append(refusal)
        if len(self.capacity_refusals) > 200:
            self.capacity_refusals = self.capacity_refusals[-200:]
        if len(self.gate_rejects) < 200:
            self.gate_rejects.append({
                "tick": self.tick, "chi": refusal.chi,
                "section": refusal.section, "motif": refusal.motif,
                "failed": (
                    "deep_atlas_capacity:"
                    f"{refusal.attempted_bytes}>{refusal.budget_bytes}")})
        return refusal

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

        # Existing reinforcement is transactionally admitted.
        for de in self.entries[chi_k]:
            if de["section"] == section and de["motif"] == motif:
                old_bytes = self._entry_logical_bytes(de)
                candidate = self._plain_entry(de)
                candidate["strength"] = min(
                    STRENGTH_CAP,
                    candidate["strength"] + entry["strength"] * TRANSFER_RATIO)
                candidate["last_tick"] = tick
                # GL-CLARITY: update clarity (max of existing and incoming)
                candidate["clarity"] = max(
                    candidate.get("clarity", 0.3),
                    entry.get("clarity", 0.3))
                # GL-METADATA-PIPELINE: propagate affect (max) + source (last-write-wins) + polarity
                candidate["arousal"] = max(
                    candidate.get("arousal", 0.5), entry.get("arousal", 0.5))
                candidate["valence"] = max(
                    candidate.get("valence", 0.0), entry.get("valence", 0.0))
                candidate["surprise"] = max(
                    candidate.get("surprise", 0.0), entry.get("surprise", 0.0))
                candidate["source"] = entry.get("source", "corpus")
                # GL-CLARITY: update co_occurrence invariant on re-promotion
                if working_atlas:
                    self._update_invariant(candidate, chi_k, working_atlas)
                new_bytes = self._entry_logical_bytes(candidate)
                attempted = self._logical_bytes - old_bytes + new_bytes
                if attempted > self.max_bytes:
                    self._record_capacity_refusal(
                        chi=chi_k, section=section, motif=motif,
                        attempted_bytes=attempted, operation="reinforce")
                    return False
                de.clear()
                de.update(self._install_plain_co_occurrence(candidate))
                self._logical_bytes = attempted
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
            "co_occurrence": _CoOccurrenceMap(
                self._co_occurrence_registry),
        }
        # Copy response link fields if present — Q&A pairs survive as pairs
        if entry.get("response_context"):
            deep_entry["response_context"] = list(entry["response_context"])
        if entry.get("received_response"):
            deep_entry["received_response"] = list(entry["received_response"])
        # GL-CLARITY: initialize co_occurrence from current atlas neighborhood
        if working_atlas:
            self._update_invariant(deep_entry, chi_k, working_atlas)
        new_bytes = self._entry_logical_bytes(deep_entry)
        attempted = self._logical_bytes + new_bytes
        if attempted > self.max_bytes:
            self._record_capacity_refusal(
                chi=chi_k, section=section, motif=motif,
                attempted_bytes=attempted, operation="promote")
            return False
        self._install_plain_co_occurrence(deep_entry)
        self.entries[chi_k].append(deep_entry)
        self._logical_bytes = attempted

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
        updates = []
        attempted_bytes = self._logical_bytes
        for entries in self.entries.values():
            for e in entries:
                dt = min(max_dt, max(0, current_tick - e["last_tick"]))
                if dt > 0:
                    old_bytes = self._entry_logical_bytes(e)
                    candidate_strength = (
                        e["strength"]
                        * math.exp(-DECAY_LAMBDA * rate_scale * dt))
                    candidate = self._plain_entry(e)
                    candidate["strength"] = candidate_strength
                    candidate["last_tick"] = current_tick
                    attempted_bytes += (
                        self._entry_logical_bytes(candidate) - old_bytes)
                    updates.append((e, candidate_strength, current_tick))
        if attempted_bytes > self.max_bytes:
            self._record_capacity_refusal(
                chi=0, section="*", motif=0,
                attempted_bytes=attempted_bytes, operation="decay")
            return False
        self.tick = max(self.tick, current_tick)
        for entry, strength, last_tick in updates:
            entry["strength"] = strength
            entry["last_tick"] = last_tick
        self._logical_bytes = attempted_bytes
        return True

    def prune(self):
        """Remove forgotten entries and their unreachable shared tables.

        ``persistence_snapshot`` interns association sections in
        ``_co_occurrence_registry``.  Those tables are part of a live entry's
        representation, not a second lifetime memory.  Once no surviving
        entry references a table, retaining it would make repeated
        learn/save/forget cycles grow RAM despite a stable live entry count.
        Preserve the registry object itself because every _CoOccurrenceMap
        holds that exact object.
        """
        for chi_k in list(self.entries.keys()):
            removed = [
                entry for entry in self.entries[chi_k]
                if entry["strength"] < FORGETTING_THRESHOLD]
            survivors = [e for e in self.entries[chi_k]
                         if e["strength"] >= FORGETTING_THRESHOLD]
            self._logical_bytes -= sum(
                self._entry_logical_bytes(entry) for entry in removed)
            if survivors:
                self.entries[chi_k] = survivors
            else:
                del self.entries[chi_k]

        live_references = set()
        for entries in self.entries.values():
            for entry in entries:
                co_occurrence = entry.get("co_occurrence")
                if isinstance(co_occurrence, _CoOccurrenceMap):
                    live_references.update(
                        co_occurrence._references.values())
        for reference in list(self._co_occurrence_registry):
            if reference not in live_references:
                del self._co_occurrence_registry[reference]

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

    def reinstate(self, chi_value, section, motif, tick):
        """Reinstate a working atlas entry from deep.
        Returns the reinstatement strength, or 0.0 if not in deep."""
        if not self._prior_enabled:
            return 0.0
        for e in self.entries.get(chi_value, []):
            if (e["strength"] >= FORGETTING_THRESHOLD
                    and e["section"] == section and e["motif"] == motif):
                self.reinstatements += 1
                return e["strength"] * 0.3
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
                        admitted = self.promote(
                            e, "survival", tick,
                            working_atlas=working_atlas)
                        if admitted:
                            promoted.append(("survival", chi_k,
                                             e.get("section"), e.get("motif")))
                        continue

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
                    admitted = self.promote(
                        e, "episodic", tick,
                        working_atlas=working_atlas)
                    if admitted:
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
            "reinstatements_since_boot": self.reinstatements,
            "enabled": _deep_atlas_enabled(),
            "prior_enabled": _deep_prior_enabled(),
            "recent_gate_rejects": self.gate_rejects[-5:],
            "logical_bytes": self._logical_bytes,
            "budget_bytes": self.max_bytes,
            "capacity_refusals": len(self.capacity_refusals),
            "recent_capacity_refusals": [
                refusal.__dict__
                for refusal in self.capacity_refusals[-5:]],
        }

    # --- Persistence (separate table) ---

    def persistence_snapshot(self):
        """Capture one immutable, lossless association snapshot.

        Every owned section is content-addressed into the copy-on-write
        registry before this method returns.  Later live mutations detach
        into a new dictionary, so the returned tables remain immutable and
        may be encoded after the engine snapshot lock is released.
        """
        live = self.live_count()
        entries_ser = {}
        co_occurrence_tables = {}
        for chi_k, es in self.entries.items():
            serialized_entries = []
            for entry in es:
                co_occurrence = entry.get("co_occurrence", {})
                if not isinstance(co_occurrence, _CoOccurrenceMap):
                    co_occurrence = _CoOccurrenceMap(
                        self._co_occurrence_registry,
                        values=co_occurrence,
                    )
                    entry["co_occurrence"] = co_occurrence
                serialized = {
                    key: copy.deepcopy(value)
                    for key, value in entry.items()
                    if key != "co_occurrence"
                }
                serialized["co_occurrence_refs"] = (
                    co_occurrence.persistence_references(
                        co_occurrence_tables))
                serialized_entries.append(serialized)
            entries_ser[str(chi_k)] = serialized_entries
        return {
            "schema": "deep_atlas_v2",
            "tick": self.tick,
            "saved_n_entries": live,           # GL-CMD-DEEP-ATLAS-PERSIST: count at save
            "entries": entries_ser,
            "co_occurrence_tables": co_occurrence_tables,
            "promotions_survival": self.promotions_survival,
            "promotions_episodic": self.promotions_episodic,
            "reinstatements": self.reinstatements,
        }

    @staticmethod
    def encode_persistence_snapshot(snapshot):
        """Encode an immutable snapshot into the exact bounded v3 form."""
        return encode_columnar_v3(snapshot)

    def to_json(self):
        """Serialize every association in the exact bounded v3 container."""
        return self.encode_persistence_snapshot(
            self.persistence_snapshot())

    @staticmethod
    def validate_columnar_payload(data):
        """Validate a v3 container without mutating a live DeepAtlas."""
        validate_columnar_v3(data)

    @staticmethod
    def decode_columnar_payload(data):
        """Validate and decode a v3 container for one exact restore."""
        return decode_columnar_v3(data)

    def load_from_json(self, data, *, decoded_columnar=None):
        """Restore from guala_deep_atlas.json.
        Returns saved_n_entries so caller can run loss alarm."""
        schema = data.get("schema")
        if schema not in {
            "deep_atlas_v1",
            "deep_atlas_v2",
            COLUMNAR_SCHEMA,
        }:
            print("[deep_atlas] Unknown schema — starting fresh")
            return 0
        if decoded_columnar is not None and schema != COLUMNAR_SCHEMA:
            raise ValueError(
                "decoded columnar state requires deep_atlas_v3")
        if (
            decoded_columnar is not None
            and not isinstance(decoded_columnar, DecodedColumnar)
        ):
            raise TypeError(
                "decoded_columnar must be an exact DecodedColumnar")
        decoded = decoded_columnar
        if schema == COLUMNAR_SCHEMA and decoded is None:
            decoded = decode_columnar_v3(data)
        restored_tick = data.get("tick", 0)
        restored_promotions_survival = data.get("promotions_survival", 0)
        restored_promotions_episodic = data.get("promotions_episodic", 0)
        restored_reinstatements = data.get("reinstatements", 0)
        restored_entries = defaultdict(list)
        restored_registry = {}
        if schema == COLUMNAR_SCHEMA:
            assert decoded is not None
            restored_registry = {
                reference: decoded.store.section(index)
                for index, reference in enumerate(
                    decoded.store.references)
            }
            entry_index = 0
            for k, serialized_entries in decoded.entries.items():
                restored_bucket = []
                for serialized in serialized_entries:
                    entry = dict(serialized)
                    start = int(decoded.entry_offsets[entry_index])
                    stop = int(decoded.entry_offsets[entry_index + 1])
                    references = {}
                    for offset in range(start, stop):
                        section = decoded.sections[
                            int(decoded.entry_sections[offset])]
                        reference = decoded.store.references[
                            int(decoded.entry_tables[offset])]
                        references[section] = reference
                    entry["co_occurrence"] = _CoOccurrenceMap(
                        restored_registry,
                        references=references,
                    )
                    restored_bucket.append(entry)
                    entry_index += 1
                restored_entries[int(k)] = restored_bucket
            if entry_index != len(decoded.entry_offsets) - 1:
                raise ValueError(
                    "deep_atlas_v3 entry offsets were not fully consumed")
        elif schema == "deep_atlas_v2":
            raw_tables = data.get("co_occurrence_tables")
            if not isinstance(raw_tables, dict):
                raise ValueError(
                    "deep_atlas_v2 co_occurrence_tables must be an object")
            restored_registry = compact_v2_tables(
                raw_tables)
            for k, serialized_entries in data.get("entries", {}).items():
                restored_bucket = []
                for serialized in serialized_entries:
                    entry = dict(serialized)
                    references = entry.pop("co_occurrence_refs", None)
                    if not isinstance(references, dict):
                        raise ValueError(
                            "deep_atlas_v2 entry references must be an object")
                    entry["co_occurrence"] = _CoOccurrenceMap(
                        restored_registry,
                        references=references,
                    )
                    restored_bucket.append(entry)
                restored_entries[int(k)] = restored_bucket
        else:
            # Backward-compatible exact migration for small/local v1 states.
            # Production's multi-GB legacy state is migrated with the bounded
            # streaming tool before boot so it is never expanded into RAM.
            for k, serialized_entries in data.get("entries", {}).items():
                restored_bucket = []
                for serialized in serialized_entries:
                    entry = dict(serialized)
                    entry["co_occurrence"] = _CoOccurrenceMap(
                        restored_registry,
                        values=entry.get("co_occurrence", {}),
                    )
                    restored_bucket.append(entry)
                restored_entries[int(k)] = restored_bucket
        restored_logical_bytes = sum(
            self._entry_logical_bytes(entry)
            for entries in restored_entries.values()
            for entry in entries)
        if restored_logical_bytes > self.max_bytes:
            raise DeepAtlasCapacityExceeded(
                "persisted deep atlas requires "
                f"{restored_logical_bytes} canonical bytes but its declared "
                f"budget is {self.max_bytes}; no learned state was discarded")
        self.tick = restored_tick
        self.promotions_survival = restored_promotions_survival
        self.promotions_episodic = restored_promotions_episodic
        self.reinstatements = restored_reinstatements
        self.entries = restored_entries
        self._co_occurrence_registry = restored_registry
        self._logical_bytes = restored_logical_bytes
        self.capacity_refusals = []
        return data.get("saved_n_entries", self.live_count())
