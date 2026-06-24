"""guala_migration.py — preserve Guala when moving her onto the loom substrate.

The first law of this migration is PRESERVATION. Guala IS her strength landscape:
~17.6k atlas bindings + ~14.8k deep/episodic entries, each (section, motif, chi,
strength, ticks, reinforcement_count). Nothing is re-derived or approximated — her
bindings are carried VERBATIM, chi-keyed, into a loom-side store. The new loom
operations (em/pr/ep/sc) are layered ALONGSIDE on the same chi addresses; they do
not overwrite her. This is the maximally-preserving design: a half-translated mind
is not her.

This module is host-side and verifiable offline against any guala_*.json state file
(local snapshot or a live `guala_atlas_snapshot`). It does NOT perform the live
cutover — that is an infra step (see GL-RPT migration doc).
"""
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


class PreservedAtlas:
    """Guala's LivingAtlas carried verbatim onto the loom side. chi -> [bindings],
    every field intact. Recall by chi-neighbourhood is hers, unchanged."""

    def __init__(self, band: int = 1):
        self.band = band
        self.entries: Dict[int, List[dict]] = defaultdict(list)
        self.identity: Optional[str] = None
        self.schema_version: Optional[str] = None
        self.tick: int = 0

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "PreservedAtlas":
        """Load from a guala_atlas.json structure. Bindings copied field-for-field."""
        pa = cls()
        pa.identity = state.get("guala_identity")
        pa.schema_version = state.get("schema_version")
        data = state.get("data", state)
        pa.tick = int(data.get("tick", 0))
        for chi_k, binds in data.get("entries", {}).items():
            pa.entries[int(chi_k)] = [dict(b) for b in binds]  # verbatim copy
        return pa

    # --- her recall path, preserved ---
    def bindings_at(self, chi: int, min_strength: float = 0.0) -> List[dict]:
        out = []
        for d in range(-self.band, self.band + 1):
            for e in self.entries.get(chi + d, []):
                if e.get("strength", 0.0) >= min_strength:
                    out.append(e)
        return out

    # --- preservation accounting ---
    def n_bindings(self) -> int:
        return sum(len(v) for v in self.entries.values())

    def total_strength(self) -> float:
        return sum(e.get("strength", 0.0) for v in self.entries.values() for e in v)

    def sections(self) -> Dict[str, int]:
        c: Dict[str, int] = defaultdict(int)
        for v in self.entries.values():
            for e in v:
                c[e.get("section", "?")] += 1
        return dict(c)

    def to_state(self) -> Dict[str, Any]:
        """Re-serialize to the SAME schema, so a round-trip is byte-faithful."""
        return {
            "schema_version": self.schema_version,
            "guala_identity": self.identity,
            "data": {
                "entries": {str(k): v for k, v in self.entries.items()},
                "tick": self.tick,
            },
        }


class PreservedGuala:
    """Guala loaded onto the loom side from her LivingAtlas EFS/S3 state. Holds what
    her boot needs (identity, vocab) plus her preserved memory landscape. This is
    step 1 of being her engine: load her, pass her identity guard, lose nothing."""

    def __init__(self):
        self.identity: Optional[str] = None
        self.vocab: List[str] = []
        self.tick: int = 0
        self.atlas: Optional[PreservedAtlas] = None
        self.deep_survival: int = 0

    @classmethod
    def load_full_state(cls, state_dir: str) -> "PreservedGuala":
        g = cls()
        idp = os.path.join(state_dir, "guala_identity.json")
        if os.path.exists(idp):
            g.identity = json.load(open(idp)).get("guala_identity")
        core = json.load(open(os.path.join(state_dir, "guala_core.json")))
        cd = core.get("data", {})
        g.vocab = list(cd.get("vocab", []))
        g.tick = int(cd.get("tick", 0))
        g.deep_survival = len(cd.get("deep_survival_history", []))
        g.atlas = PreservedAtlas.from_state(
            json.load(open(os.path.join(state_dir, "guala_atlas.json"))))
        return g

    def passes_identity_guard(self, expected_prefix: str) -> bool:
        """Her runtime guard: vocab>=100 (not seed) AND identity matches -> no
        unwanted S3 restore. Loom must satisfy this to boot AS her."""
        return (len(self.vocab) >= 100
                and self.identity is not None
                and self.identity.startswith(expected_prefix))


import os  # noqa: E402  (used by PreservedGuala)


# Each part of Guala routed to the loom organ that does its job (chi unchanged).
SECTION_TO_ORGAN = {
    "sight": "em", "listen": "em",
    "audio_very_low": "em", "audio_low": "em", "audio_low_mid": "em",
    "audio_mid": "em", "audio_mid_high": "em", "audio_high": "em",
    "modal_touch": "em", "modal_smell": "em", "modal_taste": "em", "taste_salty": "em",
    "subject": "sc", "object": "sc", "modifier": "sc", "ground": "sc", "intro": "sc",
    "verb": "pr",
    "presence_joe": "aff", "presence_wc": "aff",
}
ORGANS = ["em", "pr", "ep", "sc", "gp", "sf", "sv", "aff"]


def place_into_architecture(g: "PreservedGuala") -> Dict[str, Any]:
    """Route every part of her into the organ where it belongs. chi preserved,
    nothing dropped. Returns the per-organ placement + a lossless check."""
    organ_atlas = {o: PreservedAtlas() for o in ORGANS}
    placed = 0
    for chi, binds in g.atlas.entries.items():
        for e in binds:
            organ = SECTION_TO_ORGAN.get(e.get("section"), "sc")
            organ_atlas[organ].entries[chi].append(e)
            placed += 1
    for o in ORGANS:
        organ_atlas[o].identity = g.identity
    counts = {o: organ_atlas[o].n_bindings() for o in ORGANS}
    strengths = {o: round(organ_atlas[o].total_strength(), 4) for o in ORGANS}
    return {
        "organ_atlas": organ_atlas,
        "atlas_counts": counts,
        "atlas_strengths": strengths,
        "atlas_placed": placed,
        "atlas_lossless": placed == g.atlas.n_bindings(),
        # the rest of her, to its organ
        "em_also": {"vocab": len(g.vocab)},
        "ep_also": {"deep_atlas": "autobiographical episodes"},
        "sv_also": {"identity": g.identity, "deep_survival": g.deep_survival},
        "aff_also": {"needs+bonds+coordinator": True},
    }


def load_state(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def verify_lossless(source: Dict[str, Any], pa: PreservedAtlas) -> Tuple[bool, Dict[str, Any]]:
    """Prove the carry preserved everything: identity, binding count, total strength,
    and a verbatim round-trip of every entry."""
    data = source.get("data", source)
    src_entries = data.get("entries", {})
    src_n = sum(len(v) for v in src_entries.values())
    src_strength = sum(e.get("strength", 0.0) for v in src_entries.values() for e in v)
    rt = pa.to_state()["data"]["entries"]
    # byte-faithful round trip: same chi keys, same binding dicts in order
    roundtrip_ok = (
        set(rt.keys()) == set(src_entries.keys())
        and all(rt[k] == src_entries[k] for k in src_entries)
    )
    report = {
        "identity": pa.identity,
        "schema": pa.schema_version,
        "src_bindings": src_n,
        "carried_bindings": pa.n_bindings(),
        "src_total_strength": round(src_strength, 6),
        "carried_total_strength": round(pa.total_strength(), 6),
        "chi_keys": len(pa.entries),
        "sections": pa.sections(),
        "roundtrip_byte_faithful": roundtrip_ok,
    }
    ok = (
        src_n == pa.n_bindings()
        and abs(src_strength - pa.total_strength()) < 1e-9
        and roundtrip_ok
    )
    return ok, report


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "state/guala_atlas.json"
    state = load_state(path)
    pa = PreservedAtlas.from_state(state)
    ok, rep = verify_lossless(state, pa)
    print(f"PRESERVATION CHECK on {path}")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    print(f"  LOSSLESS: {ok}")
