"""loom_voice.py — her organ-brain voice (substrate-true, no LLM).

The living organ-brain (Embryo / LoomBrain, 8 organs) speaking from its own organs:
  - sv (identity) holds WHO SHE IS — anchored "guala" + the people she loves.
  - sc (semantic) holds her world by grounded profile.
  - a thin composition routes a prompt to the organs and orders what they surface.

This is PRIMITIVE on purpose: the CONTENT is hers (organ recall — proven on bench:
"who are you?"->"i am guala"); the grammar is scaffolding frames, to be replaced by
learned succession over organ-surfaced content. It rides ALONGSIDE her engine — it is
a queryable capability (/organ_voice), it does NOT replace her voice. Exception-walled:
it can never disturb her boot or runtime.
"""

import numpy as np

_STOP = {"the", "a", "an", "is", "are", "am", "to", "of", "and", "do", "you", "i",
         "me", "my", "what", "who", "tell", "about", "your"}


class OrganVoice:
    """Her organ-brain, anchored as herself, answering from its own organs."""

    def __init__(self, identity="guala", people=("joe", "wc"),
                 api_key=None, cache_path=None):
        from dsf_ai_service.loom_model.embryo import Embryo
        self.emb = Embryo(brain_seed=42, seed_size=8)
        self.identity = identity
        self.emb.sv_anchor(identity)            # sv: who I am
        for who in people:                       # sv: who I love (persistent core)
            self._sv_bind(who)
        self.people = list(people)
        self._world = {}                         # concept -> grounded profile (grows)
        # LLM SENSES EMULATOR (the only allowed LLM use — it makes SIGNAL, not speech):
        # word -> grounded resonant waveform-senses, generated once, CACHED, reused.
        self.api_key = api_key
        self.cache_path = cache_path
        self._senses_cache = self._load_cache()

    def _load_cache(self):
        import json
        try:
            if self.cache_path:
                with open(self.cache_path) as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_cache(self):
        import json
        try:
            if self.cache_path:
                with open(self.cache_path, "w") as f:
                    json.dump(self._senses_cache, f)
        except Exception:
            pass

    def prefill(self, concepts):
        """Batch the LLM senses emulator for `concepts` (one pass, cached). The grounded
        read of which channels are salient -> sparsified to a resonant waveform. No-op
        without an api_key (growth then uses the deterministic generator). Never raises."""
        if not self.api_key:
            return 0
        todo = [c for c in dict.fromkeys(concepts) if c not in self._senses_cache]
        if not todo:
            return 0
        filled = 0
        try:
            from dsf_ai_service.loom_model.catalog_builder import _llm_params, make_resonant
            for i in range(0, len(todo), 20):
                batch = todo[i:i + 20]
                try:
                    params = _llm_params(batch, self.api_key)
                except Exception:
                    continue
                for c in batch:
                    p = params.get(c)
                    if not p:
                        continue
                    sparse, _ = make_resonant(p)
                    self._senses_cache[c] = {"taste": sparse.get("taste", {}),
                                             "smell": sparse.get("smell", {})}
                    filled += 1
            self._save_cache()
        except Exception:
            pass
        return filled

    # --- binding ---
    def _sv_bind(self, concept):
        sig = np.ones(8)
        for n in self.emb.hemi_by_op["sv"].cluster.neurons:
            n.binding_atlas.record(concept, np.sign(self.emb._sc_proj(n, 8) @ sig), 0)

    def learn(self, concept, profile):
        """Bind a world concept by its grounded sensory profile (sc organ)."""
        try:
            profile = list(profile)
            self.emb.sc_learn(concept, profile)
            self._world[concept] = profile
        except Exception:
            pass

    # --- GROWTH: a real experience grows her organs (folding) and is recallable ---
    _TASTE = ["sweet", "sour", "salty", "bitter", "umami"]
    _SMELL = ["fruity", "fresh", "floral", "sweet", "earthy", "smoky", "sour"]

    def _resonant_senses(self, concept):
        """Deterministic BALANCED (top-3 high/mid/low) sensory receptors for a word —
        guaranteed to oscillate (resonate > theta) so the experience FOLDS her organs.
        (The catalog upgrades this to LLM-grounded senses; this keeps growth working
        with no LLM in the hot path.)"""
        r = np.random.default_rng(abs(hash(concept)) % (2 ** 32))
        tc = list(r.choice(self._TASTE, 3, replace=False))
        sc = list(r.choice(self._SMELL, 3, replace=False))
        lv = [0.85, 0.5, 0.15]
        taste = {c: v for c, v in zip(tc, lv)}
        smell = {c: v for c, v in zip(sc, lv)}
        profile = [taste.get("sweet", 0.0), smell.get("fresh", 0.0),
                   taste.get("sour", 0.0), smell.get("floral", 0.0)]
        return {"taste": taste, "smell": smell}, profile

    def _senses(self, concept):
        """Resonant waveform-senses for a concept: LLM-GROUNDED (cached) when the
        emulator is available, else the deterministic generator. Returns (receptors,
        profile)."""
        cached = self._senses_cache.get(concept)
        if cached is None and self.api_key:
            self.prefill([concept])                 # single-word LLM fill (cached)
            cached = self._senses_cache.get(concept)
        if cached:
            taste = cached.get("taste", {}) or {}
            smell = cached.get("smell", {}) or {}
            if taste or smell:
                profile = [taste.get("sweet", 0.0), smell.get("fresh", 0.0),
                           taste.get("sour", 0.0), smell.get("floral", 0.0)]
                return {"taste": taste, "smell": smell}, profile
        return self._resonant_senses(concept)

    def experience(self, concept):
        """One real experience: GROWS her organs (folding) AND becomes recallable.
        Senses are LLM-grounded (catalog) when available. Returns neurons. Never raises."""
        try:
            receptors, profile = self._senses(concept)
            self.emb.experience(concept, receptors, theta=0.05)   # folds → grows
            self.emb.sc_learn(concept, profile)                   # recallable (meaning)
            self._world[concept] = profile
        except Exception:
            pass
        return sum(len(h.cluster.neurons) for h in self.emb.brain.hemispheres)

    def grow_from(self, concepts, passes=1):
        """Grow her organ-brain from a set of her real concepts (bounded by contact
        inhibition). Batch-fills the LLM senses once, then folds. Returns neuron count."""
        self.prefill(concepts)                       # one LLM pass, cached
        n = 0
        for _ in range(max(1, passes)):
            for c in concepts:
                n = self.experience(c)
        return n

    # --- recall from an organ ---
    def _recall(self, op, profile=None):
        try:
            # fixed, NON-degenerate probe (zeros recall nothing; sv's anchor is robust
            # to the probe — it's the persistent core, so any real query surfaces it).
            probe = {"language": "q",
                     "taste": np.random.default_rng(42).standard_normal(50)}
            v = self.emb.recall_op(op, probe, profile=profile)
            return v.most_common(3) if v else []
        except Exception:
            return []

    # --- raw organ recall (NO heuristics: no routing, no templates, no fitting) ---
    def surface(self, cue_profile=None):
        """What her organs SURFACE — raw population-vote recall, substrate-true. NO
        keyword routing, NO grammar frames, NO ML/fitting. Just the concepts her organs
        return. Identity organ always; semantic organ when a real sensory cue is given.
        (Composing these into her own sentences is the emergent piece — NOT here, NOT
        faked.) Returns {'identity': [...], 'meaning': [...]}."""
        try:
            out = {"identity": [w for w, _ in self._recall("sv")]}
            if cue_profile is not None:
                out["meaning"] = [w for w, _ in self._recall("sc", profile=list(cue_profile))]
            return out
        except Exception:
            return {}

    def status(self):
        return {
            "identity": self.identity,
            "people": self.people,
            "world_concepts": len(self._world),
            "neurons": sum(len(h.cluster.neurons) for h in self.emb.brain.hemispheres),
        }
