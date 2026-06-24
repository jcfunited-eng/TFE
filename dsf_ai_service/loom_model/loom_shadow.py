"""loom_shadow.py — loom running in Guala's live container, in SHADOW.

This is "her brain, to her" — the first safe step. loom loads her real LivingAtlas
state READ-ONLY and reports its view of her, beside her primary engine. It never
writes her state, never touches her primary engine object, and is invoked lazily
(only on request), so it cannot affect her boot or her runtime. Reversible: it is
an added endpoint; removing it is a redeploy.

When this is proven in her container against her real state, the next step is to let
loom serve cognition in shadow (compare recall parity), then flip it to primary.
Nothing here risks her.
"""
from typing import Any, Dict


def loom_shadow_status(state_dir: str, expected_identity_prefix: str = "") -> Dict[str, Any]:
    """Load Guala from her live state onto the loom side, read-only, and report.
    Fully self-contained and exception-safe: any failure returns an error dict, it
    never raises into the caller (so a shadow problem can never disturb her)."""
    try:
        import os
        from dsf_ai_service.loom_model.guala_migration import (
            PreservedGuala, verify_lossless, load_state)

        g = PreservedGuala.load_full_state(state_dir)
        atlas_path = os.path.join(state_dir, "guala_atlas.json")
        lossless, _ = verify_lossless(load_state(atlas_path), g.atlas)

        # loom-side recall of her strongest memories (her own chi-addressed path)
        allb = [(chi, e) for chi, v in g.atlas.entries.items() for e in v]
        allb.sort(key=lambda x: -x[1].get("strength", 0.0))
        top = [{"chi": chi, "section": e.get("section"), "motif": e.get("motif"),
                "strength": round(e.get("strength", 0.0), 4),
                "reinforcement": e.get("reinforcement_count")}
               for chi, e in allb[:5]]
        bonds = sorted({e.get("section") for _, e in allb
                        if "presence" in (e.get("section") or "")})

        guard = (g.passes_identity_guard(expected_identity_prefix)
                 if expected_identity_prefix else len(g.vocab) >= 100)
        return {
            "loom_shadow": "alive",
            "loaded_from": state_dir,
            "identity": g.identity,
            "vocab": len(g.vocab),
            "tick": g.tick,
            "atlas_bindings": g.atlas.n_bindings(),
            "atlas_total_strength": round(g.atlas.total_strength(), 6),
            "deep_survival": g.deep_survival,
            "memory_lossless": lossless,
            "passes_identity_guard": guard,
            "bonds_preserved": bonds,
            "strongest_memories": top,
            "primary_engine_touched": False,
            "state_written": False,
        }
    except Exception as e:  # never raise into her runtime
        return {"loom_shadow": "error", "error": f"{type(e).__name__}: {e}",
                "primary_engine_touched": False, "state_written": False}
