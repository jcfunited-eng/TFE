"""
brain.py — LoomBrain: 8-hemisphere seed substrate with cross-hemi couplings.

GL-CMD-113 V2.4, per GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-103 Part 3.

Construction: 8 hemispheres × 50 neurons = 400 seed neurons.
Cross-hemi wiring: projection neurons (5 per hemi) coupled to adjacent
hemispheres via Watts-Strogatz topology (committed constant).
"""

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

from .hemisphere import LoomHemisphere
from .cross_hemi import CrossHemiCouplings
from .topology import (
    HEMISPHERE_ADJACENCY, N_HEMISPHERES,
    K_INTERHEMI, PROJECTION_NEURONS_PER_HEMI,
    SEED_SIZE_PER_HEMISPHERE,
    HEMISPHERE_PRIMARY_MODALITY,
    validate_adjacency,
)

logger = logging.getLogger("guala.brain")

# --- GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2 (dual-write/dual-read) ---
# HEURISTIC: RECALL_INJECTION_WEIGHT=2.0 -- enough to prime propagation
# without saturating. Class: from-design. Measurement plan: verify cue
# injection produces propagation; adjust if recall is too silent/broad.
RECALL_INJECTION_WEIGHT = 2.0
# HEURISTIC: RECALL_PROPAGATION_WINDOW_MS=30.0 -- allows several spike
# hops. Class: from-design. Measurement plan: measure recall latency vs
# completeness; adjust if window too short (partial) or too long (blocking).
RECALL_PROPAGATION_WINDOW_MS = 30.0
# HEURISTIC: RECALL_ACTIVATION_THRESHOLD=0.3 -- captures meaningfully
# activated neurons. Class: from-design. Measurement plan: verify recall
# returns semantically-related concepts; adjust if too broad/narrow.
RECALL_ACTIVATION_THRESHOLD = 0.3
# HEURISTIC: VOTE_SCALE=5 -- converts membrane potential (float) to vote
# weight (int) for Counter compatibility with the legacy signature. Class:
# from-design. Measurement plan: verify vote distribution matches legacy
# shape enough for the four existing callers to work; adjust if top-
# concept selection differs qualitatively.
VOTE_SCALE = 5

# GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 4, STDP consumer):
# RECALL_STDP_GAIN converts a neuron's learned mean incoming synapse
# weight (above the untrained STDP_DEFAULT_SYNAPSE_WEIGHT baseline) into
# extra population-vote weight, so what STDP learned on the spike bus has
# a real consequence in recall instead of being write-only. Gain 1.0 is
# the identity mapping (from-design, not tuned): a neuron whose synapses
# average the untrained default votes with weight exactly 1.0 (behavior
# identical to before this change); a neuron potentiated to the
# per-synapse MAX_SYNAPSE_WEIGHT=5.0 ceiling votes with weight ~5.95 --
# bounded by the same synapse ceiling STDP itself already enforces, so no
# single neuron can outvote the population without having genuinely
# earned it spike by spike. Measurement plan: teach-pattern-shifts-recall
# test (tests/test_stdp_recall_consumer.py) + live /debug/stdp_state
# weight distribution vs recall top-vote share.
RECALL_STDP_GAIN = 1.0


class LoomBrain:
    """8-hemisphere seed substrate with small-world cross-hemi coupling.

    Construction:
      1. Create 8 hemispheres with deterministic seeds derived from brain_seed
      2. Wire cross-hemi couplings between projection neurons in adjacent hemispheres
      3. Validate topology at boot

    step() propagates input through all hemispheres and routes cross-hemi spikes.
    """

    def __init__(self, brain_seed: int = 42,
                 seed_size: int = SEED_SIZE_PER_HEMISPHERE,
                 k_neighbors: int = 16,
                 hemisphere_primary_modality: Optional[Dict[str, str]] = None,
                 observable: Optional[str] = None):
        self.brain_seed = brain_seed
        self.topology = HEMISPHERE_ADJACENCY.copy()
        # GL-CMD-146: cognition observable (opt-in). Resolution order:
        # explicit constructor arg > COGNITION_OBSERVABLE env var > "event_count".
        # The env var lets the existing test suite run under rank_order without
        # editing it; explicit arg still wins (single switch, both write+recall).
        # GL capacity solve: resonant_spectral is the production default (n=200 recall
        # 18% -> 100%). event_count remains opt-in via arg/env for the legacy path.
        observable = (observable
                      or os.environ.get("COGNITION_OBSERVABLE")
                      or "resonant_spectral")
        self.observable = observable

        # GL-CMD-140 (Decision 1): language-as-default. Heterogeneous krimelacks
        # (GL-CMD-139) did not unblock folding and broke cognition tests, so the
        # HEMISPHERE_PRIMARY_MODALITY map is no longer applied by default. It
        # remains in topology.py and can be opted into by passing it explicitly
        # once item 7 actually unblocks.
        primary_map = (hemisphere_primary_modality
                       if hemisphere_primary_modality is not None else {})

        # Validate topology at boot
        self._topology_metrics = validate_adjacency(self.topology)

        # Create hemispheres with deterministic seeds
        self.hemispheres: List[LoomHemisphere] = []
        for i in range(N_HEMISPHERES):
            hemi_id = f"H{i}"
            hemi_seed = brain_seed * 1000 + i  # deterministic per-hemi seed
            primary_modality = primary_map.get(hemi_id, "language")
            hemi = LoomHemisphere(
                hemi_id=hemi_id,
                seed=hemi_seed,
                seed_size=seed_size,
                k_neighbors=k_neighbors,
                primary_modality=primary_modality,
                observable=observable,
            )
            self.hemispheres.append(hemi)

        # Build lookup
        self._hemi_map: Dict[str, LoomHemisphere] = {
            h.hemi_id: h for h in self.hemispheres
        }

        # Wire cross-hemi couplings
        self._wire_cross_hemi()

        # --- GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2 ---
        # Set via set_spike_bus() / direct assignment by Guala once this
        # brain is wrapped by a live substrate. None by default -- step()'s
        # dual-write injection and recall_fast's "stdp"/"shadow" backends
        # both no-op gracefully when unset, so a bare LoomBrain()/Embryo()
        # (every existing test, probe, and the seed_organism() demo script)
        # is completely unaffected -- confirmed unreachable from current
        # production, which calls hemi.step()/cluster.step() directly.
        self._spike_bus = None
        self._guala_ref = None  # back-reference for _word_neuron_map, _all_neurons(), etc.

    # --- GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3: pickle round-trip ---
    # Same reasoning as LoomNeuron's pair in neuron.py: load_full_state()
    # (gualaloom_v5_engine.py) replaces self.organism wholesale via
    # pickle.load(), which never calls __init__. A pre-Phase-1-v2 pickle
    # restores a LoomBrain missing _spike_bus/_guala_ref entirely --
    # confirmed live, see GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1 finding 1.

    def __getstate__(self):
        """Exclude runtime-only references. _guala_ref especially --
        pickling a back-reference to the whole Guala object would drag
        the entire live substrate graph into this one field."""
        state = self.__dict__.copy()
        state.pop('_spike_bus', None)
        state.pop('_guala_ref', None)
        return state

    def __setstate__(self, state):
        """Restore __dict__. _spike_bus/_guala_ref intentionally left
        absent -- Guala.wire_spike_bus() sets both after restore, since
        only Guala holds the live SpikeBus instance and self-reference
        needed to wire them meaningfully."""
        self.__dict__.update(state)

    def set_spike_bus(self, spike_bus) -> None:
        self._spike_bus = spike_bus

    def wire_mood_broadcast(self, mood_source) -> None:
        """GL-CMD-MOOD-BROADCAST: wire a read-only global mood/affect
        source (see neuron.py's LoomNeuron.set_mood_source docstring for
        the contract -- must expose zero-arg .arousal()/.valence()
        methods; the real gualaloom_v5_engine.py Needs instance, self.needs
        on the live Guala engine, already does) onto every neuron in this
        brain.

        One-way: this call only ever WRITES a reference onto each neuron
        via set_mood_source(); it never reads or mutates anything on
        mood_source itself, and neither this file nor neuron.py ever call
        a mutating method on it -- only .arousal()/.valence(), both pure
        reads on the real Needs class.

        Mirrors gualaloom_v5_engine.py's wire_spike_bus() neuron-loop
        idiom, kept here (not there) so this dispatch touches zero lines
        of gualaloom_v5_engine.py -- the file this dispatch is explicitly
        scoped to never modify (verified via `git diff`). NOT called
        automatically from anywhere in this dispatch -- a future caller
        (Guala.wire_spike_bus(), or any other boot/restore hook) wires it
        in with one line: `self.organism.brain.wire_mood_broadcast(self.needs)`.
        Idempotent and safe to call multiple times, or with
        mood_source=None (clears the wiring on every neuron)."""
        for hemi in self.hemispheres:
            for neuron in hemi.cluster.neurons:
                neuron.set_mood_source(mood_source)

    def _wire_cross_hemi(self):
        """Wire projection neurons to targets in adjacent hemispheres.

        Each projection neuron gets K_INTERHEMI targets distributed across
        adjacent hemispheres. Projection neurons are spread across adjacents
        so that every adjacent hemisphere gets at least one incoming projection.
        """
        rng = np.random.default_rng(self.brain_seed)

        for i, hemi in enumerate(self.hemispheres):
            adjacent = [j for j in range(N_HEMISPHERES)
                        if self.topology[i, j] == 1]

            for p_idx, proj_nid in enumerate(hemi.projection_neuron_ids):
                target_assignments = []
                for k in range(K_INTERHEMI):
                    # Rotate through adjacents: each projection neuron starts
                    # at a different offset so all adjacents get coverage
                    adj_idx = (p_idx * K_INTERHEMI + k) % len(adjacent)
                    target_hemi_idx = adjacent[adj_idx]
                    target_hemi = self.hemispheres[target_hemi_idx]
                    target_neuron = rng.choice(target_hemi.cluster.neurons)
                    target_assignments.append(
                        (target_neuron.neuron_id, target_hemi.hemi_id)
                    )

                couplings = CrossHemiCouplings(targets=target_assignments)
                hemi.cross_hemi_couplings[proj_nid] = couplings

    def step(self, input_signal, tick: int, input_chi: Optional[int] = None,
             modality: Optional[str] = None) -> Dict[str, Dict[str, Dict]]:
        """GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2 item 4: dual-write.
        If a spike bus is wired AND input_chi is provided, ALSO inject the
        input as spikes (builds STDP synapse weights + word_neuron_map in
        parallel) -- THEN unconditionally run the existing iteration path
        UNCHANGED (still the only thing anything actually reads from
        during Phase 1; RECALL_BACKEND defaults to "legacy"). Confirmed
        via grep that LoomBrain.step() itself is not on the current
        production call path at all (production calls hemi.step()/
        cluster.step() directly) -- this dual-write only matters for
        callers that DO reach step() (ExperiencePipeline, tests, probes)
        plus any future production call site that starts calling it.

        input_chi: GL-CMD-BRAIN-STEP-CHI-DISPATCH-EVE-20260707-v2. Passed
        through unchanged to each hemisphere/cluster — no filtering at
        brain level. None preserves prior behavior exactly.

        Returns dict mapping hemi_id → {neuron_id → step_result} -- exact
        same shape as before, since the legacy iteration path is untouched.
        """
        # GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3: input_chi is not None
        # gate removed -- it contradicted _select_entry_neurons' own
        # random.sample fallback for input_chi=None (that fallback exists
        # specifically to handle this case). Not on the production path
        # today (see gualaloom_v5_engine.py's _organism_worker_loop for
        # where production injection actually lives now), but this method
        # is still reachable from ExperiencePipeline/tests/probes, and
        # leaving the gate would trip up any future revival of that path.
        if self._spike_bus is not None:
            try:
                self._inject_input_as_spikes(input_signal, input_chi, modality)
            except Exception:
                logger.exception("spike injection failed (non-fatal, legacy path continues)")

        return self._legacy_step_iteration(input_signal, tick, input_chi)

    def _legacy_step_iteration(self, input_signal, tick: int,
                                input_chi: Optional[int] = None) -> Dict[str, Dict[str, Dict]]:
        """Step all hemispheres, process folds, and route cross-hemi spikes.
        UNCHANGED body from pre-Phase-1 step() (renamed only) -- this is
        what every existing reader (binding_atlas via experience_moment,
        the folding/growth mechanism) still depends on throughout Phase 1.

        Folding is ON by default during step — substrate-true: real cells
        divide while they live. Contact inhibition (-105) bounds growth.
        """
        # Phase 1: step each hemisphere locally
        all_results: Dict[str, Dict[str, Dict]] = {}
        for hemi in self.hemispheres:
            all_results[hemi.hemi_id] = hemi.step(input_signal, tick, input_chi)

        # Phase 2: cross-hemi coupling refresh from DSF (per -98 mechanism)
        for hemi in self.hemispheres:
            for nid, couplings in hemi.cross_hemi_couplings.items():
                neuron = hemi.cluster._neuron_map.get(nid)
                if neuron is not None and neuron._last_dsf is not None:
                    couplings.update_from_dsf(neuron._last_dsf)

        # Phase 3: Folding Division
        self._last_fold_ids: Dict[str, List[str]] = {}
        for hemi in self.hemispheres:
            new_ids = hemi.cluster.process_folds(tick)
            if new_ids:
                self._last_fold_ids[hemi.hemi_id] = new_ids

        # Phase 4: collect cross-hemi spike packets from projection neurons
        all_packets = []
        for hemi in self.hemispheres:
            packets = hemi.get_spiking_projections(all_results[hemi.hemi_id])
            all_packets.extend(packets)

        # Phase 5: deliver packets to target hemispheres
        for packet in all_packets:
            target_hemi = self._hemi_map.get(packet["target_hemi_id"])
            if target_hemi is not None:
                target_hemi._incoming_spikes.append(packet)

        return all_results

    def _inject_input_as_spikes(self, input_signal, input_chi: int,
                                 modality: Optional[str] = None) -> None:
        """New (dual-write) path: convert input_signal into spike
        injections at entry neurons selected via Guala's chi-proximity
        helper. Runs ALONGSIDE _legacy_step_iteration, never instead of
        it, during Phase 1 transition."""
        from .injection_weight import (
            signal_to_injection_weight, SPIKE_INJECTION_MIN_WEIGHT)
        if self._guala_ref is None:
            return  # no Guala wrapper -- nothing to select entry neurons from
        entry_neurons = self._guala_ref._select_entry_neurons(input_chi, modality)
        if not entry_neurons:
            return
        weight = signal_to_injection_weight(input_signal)
        # GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 3): injection floor.
        # A signal below SPIKE_INJECTION_MIN_WEIGHT is silence (or float
        # dust from a not-yet-clamped wave residue) and injects NOTHING --
        # this is the sink-side half of the 2026-07-09 continuous-kick fix
        # (source-side half: WaveAtlas.tick_decay zero-clamp). Counted for
        # observability, never silently invisible.
        if weight < SPIKE_INJECTION_MIN_WEIGHT:
            self._injection_floor_skips = getattr(
                self, '_injection_floor_skips', 0) + 1
            return
        word = input_signal if isinstance(input_signal, str) else None
        metadata = {"input_chi": input_chi, "modality": modality}
        if word is not None:
            metadata["word"] = word
        for neuron in entry_neurons:
            self._spike_bus.inject(
                target_id=neuron.neuron_id,
                source_id="_input_injection_",
                weight=weight,
                arrival_delay_ms=0.0,
                metadata=metadata,
            )

    def total_neurons(self) -> int:
        """Total neuron count across all hemispheres."""
        return sum(len(h.cluster.neurons) for h in self.hemispheres)

    def get_neuron(self, neuron_id: str):
        """Find a neuron by global ID (searches all hemispheres)."""
        for hemi in self.hemispheres:
            n = hemi.cluster._neuron_map.get(neuron_id)
            if n is not None:
                return n
        return None

    def topology_metrics(self) -> Dict:
        """Return validated topology metrics computed at boot."""
        return self._topology_metrics

    def _stdp_vote_weight(self, neuron) -> float:
        """GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 4): the STDP
        CONSUMER. Neuron STDP has been updating _incoming_synapse_weights
        on the spike bus since Phase 1 with no production reader --
        learning without consequence. This converts a neuron's learned
        synaptic state into its population-vote weight: neurons whose
        incoming synapses were genuinely potentiated (taught patterns,
        pre-before-post causality, subthreshold correlation credit) count
        for more in every recall vote; untrained or depressed neurons
        count exactly as before (weight 1.0 at/below the untrained
        baseline -- depression never silences a neuron's vote, it only
        removes earned emphasis).

        weight = 1 + RECALL_STDP_GAIN * max(0, mean(learned) - default).

        Read under the neuron's own _neuron_lock -- the same lock every
        STDP mutator of this dict already holds (receive_spike,
        _apply_stdp_potentiation, _apply_subthreshold_potentiation,
        _receive_upstream_fire_notification, homeostatic scaling), so
        this read can never observe a half-updated dict. A neuron with no
        learned synapses at all (fresh, or restored pre-Phase-1) returns
        1.0 -- byte-identical vote behavior to before this change."""
        from .neuron import STDP_DEFAULT_SYNAPSE_WEIGHT
        lock = getattr(neuron, '_neuron_lock', None)
        weights = getattr(neuron, '_incoming_synapse_weights', None)
        if not weights:
            return 1.0
        if lock is not None:
            with lock:
                vals = list(weights.values())
        else:
            vals = list(weights.values())
        if not vals:
            return 1.0
        mean_w = sum(vals) / len(vals)
        return 1.0 + RECALL_STDP_GAIN * max(0.0, mean_w - STDP_DEFAULT_SYNAPSE_WEIGHT)

    def recall(self, query_signals: Dict[str, Any]) -> "Counter":
        """Population-vote recall across all neurons.

        For each neuron: feed query signals through krimelack bank in a
        non-binding pass, build target state vector, find best match in
        BindingAtlas. Aggregate votes. Full krimelack state restored after
        query (GL-CMD-SENSE-REPAIR): phase, t, winding, n_events, and the
        event buffer itself — not just phase/winding as before. Without
        this, a query is not actually read-only: n_events/events mutate
        during the query (feed_signal has no "peek" mode), so identical
        back-to-back queries with zero teaching between them would return
        different deltas, contaminating every later measurement.
        """
        from collections import Counter
        from .grandurun import grandurun_state, MODALITIES

        votes = Counter()
        for hemi in self.hemispheres:
            for neuron in hemi.cluster.neurons:
                # Snapshot pre-query state. Adapters (touch/smell/taste) hold
                # their real oscillator state on ._inner; krimelacks with no
                # ._inner (language, visual, auditory) hold it directly. The
                # adapters ALSO keep a post-feed mirror of .events/.winding on
                # themselves (see e.g. TactileKrimelack.feed_signal) — that
                # mirror must be snapshotted/restored too, not just ._inner,
                # or a caller reading krim.events directly (bypassing target)
                # would still see query-time contamination.
                snap = {}
                for m in MODALITIES:
                    krim = neuron.krimelack_bank.get(m)
                    if krim is None:
                        continue
                    target = getattr(krim, '_inner', krim)
                    outer_mirror = None
                    if target is not krim:
                        outer_mirror = (
                            krim,
                            krim.events.copy() if hasattr(krim, 'events') else None,
                            int(krim.winding) if hasattr(krim, 'winding') else None,
                        )
                    snap[m] = (
                        target,
                        float(target.phase) if hasattr(target, 'phase') else None,
                        float(target.t) if hasattr(target, 't') else None,
                        int(target.winding) if hasattr(target, 'winding') else None,
                        int(target.n_events) if hasattr(target, 'n_events') else None,
                        target.events.copy() if hasattr(target, 'events') else None,
                        outer_mirror,
                    )

                # Same encoding as the write path (switched by neuron.observable)
                target_vec = neuron.encode_state(query_signals)
                best_concept, _ = neuron.binding_atlas.recall_best(target_vec)
                if best_concept is not None:
                    # GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 4):
                    # vote weighted by learned STDP synapse strength --
                    # see _stdp_vote_weight. 1.0 (identical to the old
                    # +=1) for any untrained neuron.
                    votes[best_concept] += self._stdp_vote_weight(neuron)

                # Restore full state — recall must not pollute training OR
                # future recalls.
                for target, phase, t, winding, n_events, events, outer_mirror in snap.values():
                    if phase is not None:
                        target.phase = phase
                    if t is not None:
                        target.t = t
                    if winding is not None:
                        target.winding = winding
                    if n_events is not None:
                        target.n_events = n_events
                    if events is not None:
                        target.events = events
                    if outer_mirror is not None:
                        krim_outer, outer_events, outer_winding = outer_mirror
                        if outer_events is not None:
                            krim_outer.events = outer_events
                        if outer_winding is not None:
                            krim_outer.winding = outer_winding

        return votes

    def recall_fast(self, query_signals: Dict[str, Any]) -> "Counter":
        """GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2 item 5: dispatches
        to one of three backends via the RECALL_BACKEND env var. Default
        "legacy" (production stays here for the whole of Phase 1 per the
        dispatch's own protocol -- cutover is a future dispatch after
        shadow-mode verification): identical behavior to before this
        dispatch, byte-for-byte the same code path as
        _recall_fast_legacy. "shadow": runs both backends, logs a
        comparison, returns the LEGACY result (so shadow mode is
        observation-only, zero behavior change for callers). "stdp": runs
        ONLY the new STDP-graph-walk backend -- not used in production
        during this dispatch, exists for the follow-up shadow-mode test
        service.

        All four existing production callers (gualaloom_v5_engine.py:
        recognition/surprise at line ~1952, emission candidates at
        ~3528, single-word recall at ~4964, daydream association at
        ~5019) call this exact method unchanged and get the exact same
        Counter[concept -> vote_count] contract regardless of backend.
        """
        backend = os.environ.get("RECALL_BACKEND", "legacy")
        if backend == "stdp":
            return self._recall_fast_stdp(query_signals)
        elif backend == "shadow":
            legacy_votes = self._recall_fast_legacy(query_signals)
            try:
                stdp_votes = self._recall_fast_stdp(query_signals)
                self._log_recall_shadow_comparison(legacy_votes, stdp_votes, query_signals)
            except Exception:
                logger.exception("stdp shadow recall failed (non-fatal, legacy result still returned)")
            return legacy_votes
        else:
            return self._recall_fast_legacy(query_signals)

    def _recall_fast_stdp(self, query_signals: Dict[str, Any]) -> "Counter":
        """New (dual-write) recall backend: resolve the query into cue
        neurons via Guala's word_neuron_map (language) or chi (other
        modalities), inject cue spikes, let them propagate through the
        STDP-weighted coupling graph, read which neurons ended up
        activated, and aggregate their word associations into a vote
        Counter with the same shape legacy callers already expect.
        Returns an empty Counter (honest empty, matches legacy's own
        empty-evidence contract) if the spike bus or Guala wrapper isn't
        available -- e.g. every existing bare LoomBrain()/Embryo() test.
        """
        import math
        import time
        from collections import Counter

        votes = Counter()
        if self._spike_bus is None or self._guala_ref is None:
            return votes

        guala = self._guala_ref
        cue_neuron_ids = set()
        language_q = query_signals.get("language")
        if isinstance(language_q, str):
            cue_neuron_ids.update(guala._word_neuron_map.get(language_q.lower(), set()))

        for mod, sig in query_signals.items():
            if mod == "language" or sig is None:
                continue
            try:
                chi = self._compute_query_chi(sig)
            except Exception:
                continue
            if chi is None:
                continue
            cue_neuron_ids.update(n.neuron_id for n in guala._chi_to_neurons(chi))

        if not cue_neuron_ids:
            return votes

        for nid in cue_neuron_ids:
            self._spike_bus.inject(
                target_id=nid,
                source_id="_recall_cue_",
                weight=RECALL_INJECTION_WEIGHT,
                arrival_delay_ms=0.0,
                metadata={"purpose": "recall"},
            )

        time.sleep(RECALL_PROPAGATION_WINDOW_MS / 1000.0)

        now = time.monotonic()
        for neuron in guala._all_neurons():
            with neuron._neuron_lock:
                dt_ms = (now - neuron.last_update_time_s) * 1000.0
                if dt_ms > 0:
                    decay = math.exp(-dt_ms / neuron.tau_m_ms)
                    potential = (
                        neuron.membrane_rest
                        + (neuron.membrane_potential - neuron.membrane_rest) * decay
                    )
                else:
                    potential = neuron.membrane_potential

            if potential > RECALL_ACTIVATION_THRESHOLD:
                associated_word = guala._neuron_to_word(neuron)
                if associated_word is not None:
                    votes[associated_word] += max(1, int(potential * VOTE_SCALE))

        return votes

    def _compute_query_chi(self, sig) -> Optional[int]:
        """Chi for a non-language query signal, via the EXACT SAME
        mechanism Embryo._compute_input_chi uses for the write path
        (embryo.py:349-371, dsf_ai_service.substrate.krimelack.Krimelack)
        -- matches the upstream chi computation used elsewhere rather
        than inventing a second one. Returns None (not 0) for empty/
        all-zero signal, same "no real input" convention; also None on
        any Krimelack construction/feed failure, matching embryo.py's own
        defensive try/except around this exact computation."""
        import math
        import numpy as _np

        arr = _np.asarray(sig, dtype=float)
        if arr.size == 0 or not _np.any(arr):
            return None
        try:
            from dsf_ai_service.substrate.krimelack import Krimelack
            k = Krimelack(omega_0=2.0, kappa=60.0, dt=0.02, integration_threshold=math.pi / 3)
            k.feed_signal(arr)
            return k.winding % 100
        except Exception:
            return None

    def _log_recall_shadow_comparison(self, legacy_votes: "Counter", stdp_votes: "Counter",
                                       query: Dict[str, Any]) -> None:
        """Log discrepancies between legacy and STDP recall for later
        analysis during RECALL_BACKEND=shadow. Observation only -- never
        affects what recall_fast() returns."""
        legacy_top = legacy_votes.most_common(3)
        stdp_top = stdp_votes.most_common(3)
        logger.info("recall_shadow query=%r legacy_top3=%r stdp_top3=%r "
                    "legacy_total=%d stdp_total=%d top_match=%r",
                    {k: str(v)[:32] for k, v in query.items()},
                    [(str(w), c) for w, c in legacy_top],
                    [(str(w), c) for w, c in stdp_top],
                    sum(legacy_votes.values()), sum(stdp_votes.values()),
                    bool(legacy_top and stdp_top and legacy_top[0][0] == stdp_top[0][0]))

    def _recall_fast_legacy(self, query_signals: Dict[str, Any]) -> "Counter":
        """Vectorized, non-mutating population-vote recall. UNCHANGED
        body from pre-Phase-1 recall_fast() (renamed only) -- this is
        what production actually calls throughout Phase 1
        (RECALL_BACKEND defaults to "legacy").

        GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177, directions I1
        (peek-mode: read current krimelack state, never mutate -- no
        snapshot/restore needed at all, by construction) + I2 (batch the
        winding-oscillator physics across the whole neuron population in
        numpy instead of one Python-level step() call per neuron per
        modality). Numerically proven identical to recall() -- see
        tests/probe_177_vectorized_parity.py (scalar-vs-vectorized parity,
        including past the language-krimelack's 256-event deque saturation
        point) and tests/probe_177_end_to_end_parity.py (real Counter
        equality against this method's own un-vectorized twin, across
        multiple teaching depths).

        Scope: only proven correct for the exact modality set the live
        organism taps (gualaloom_v5_engine.py._organism_signal: language,
        tactile, olfactory, gustatory -- LanguageKrimelack and the
        OscillatorKrimelack-backed sensory adapters). Raises NotImplementedError
        rather than silently guessing if asked to handle any other krimelack
        type with a live signal (visual/auditory) -- those are never
        populated by the current caller, so this is not a live limitation,
        but a real one if this is ever reused for a different signal shape.

        GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-207: found live, not in the
        dispatch -- this vectorized path unconditionally builds a grandurun
        R^6 vector and hands it to binding_atlas.recall_best(), regardless
        of self.observable. Production's Embryo defaults to
        observable="resonant_spectral" (embryo.py), whose bindings are
        per-lane dicts / 128-dim ternary chi, not R^6. Every live call
        (gualaloom_v5_engine.py's organism.recall_fast, 4 call sites) was
        therefore hitting either a numpy shape-mismatch ValueError
        (uncaught at the _recognition_from_organism call site) or an
        empty-vote "honest empty" swallow (the 3 call sites wrapped in
        try/except) -- cross-sense recall wasn't just squashed, it never
        ran at all under the actual live observable. Dispatched by
        observable, checked once (uniform across a brain's neurons; see
        LoomHemisphere construction), so the proven event_count-vectorized
        path below (still the one probe_177 verifies) is untouched.
        """
        if self.observable == "resonant_spectral":
            return self._recall_fast_resonant_spectral(query_signals)

        import math
        from collections import Counter
        from .grandurun import MODALITIES
        from .vectorized_oscillator import (
            vectorized_wind_count, language_base_dphi_raw, saturating_new_count,
            monotonic_new_count,
        )
        from .neuron import signal_attenuation
        from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack

        votes = Counter()

        all_neurons = [n for hemi in self.hemispheres for n in hemi.cluster.neurons]
        n = len(all_neurons)
        if n == 0:
            return votes

        ring_pos = [getattr(nr, 'ring_pos', 0) for nr in all_neurons]
        ring_n = [getattr(nr, 'ring_N', 1) for nr in all_neurons]

        deltas_matrix = np.zeros((n, len(MODALITIES)), dtype=np.float64)

        for mi, m in enumerate(MODALITIES):
            signal = query_signals.get(m)
            if signal is None:
                continue  # deltas stay 0.0 -- matches _unwrapped_deltas exactly

            krims = [nr.krimelack_bank.get(m) for nr in all_neurons]
            present_mask = np.array([k is not None for k in krims], dtype=bool)
            if not present_mask.any():
                continue
            sample_krim = krims[int(np.argmax(present_mask))]

            if m == "language":
                if not isinstance(sample_krim, LanguageKrimelack):
                    raise NotImplementedError(
                        f"recall_fast: modality {m!r} krimelack is "
                        f"{type(sample_krim).__name__}, not LanguageKrimelack "
                        "-- outside the proven scope, refusing to guess.")
                # Per-neuron kappa/threshold, NOT a shared constant:
                # Embryo._seed_dna_diversity() mutates each neuron's OWN
                # language krimelack's kappa/threshold by ring position at
                # birth (the "chemical axis" of neuron DNA) -- confirmed by
                # direct introspection, a single sample neuron is NOT
                # representative here (unlike the sensory modalities below,
                # confirmed uniform). Attenuation is proven inert for
                # language (omega_override cancels in the dphi formula --
                # see vectorized_oscillator.py docstring and
                # tests/probe_177_vectorized_parity.py); kappa takes its
                # place as the per-neuron multiplier instead.
                base_dphi = language_base_dphi_raw(signal)
                threshold = np.array(
                    [k.threshold if k is not None else math.pi / 3 for k in krims],
                    dtype=np.float64,
                )
                att = np.array(
                    [k.kappa * k.dt if k is not None else 0.0 for k in krims],
                    dtype=np.float64,
                )
                # transduce()'s self.phase = float(phase_offset) runs
                # unconditionally (even under no_reset=True), and this call
                # site never passes phase_offset -- so phase always starts
                # at 0.0 here. Proven in probe_177_vectorized_parity.py (b).
                phase0 = np.zeros(n, dtype=np.float64)
                # GL-CMD-LANGUAGE-SATURATION-ROOTCAUSE-EVE-20260704-178:
                # mirror _unwrapped_deltas's OWN hasattr(krim, 'n_events')
                # dispatch exactly, PER-NEURON (neuron.py:846/858) -- this is
                # NOT optional/cosmetic. recall_fast() is what's actually
                # wired into the 3 live organism.recall() call sites
                # (window-3 cutover); if this branch stayed hardcoded to
                # len(events) after -178's n_events counter landed, -178's
                # whole fix would go live completely inert (recall_fast()
                # would keep computing the stale, saturated-to-zero delta
                # forever, silently defeating the fix the moment both land
                # together). Per-neuron, not a population-wide switch: a
                # restored (pickled, GL-CMD-169) organism could mix
                # pre-n_events neurons with post-n_events ones (e.g. folded
                # after an upgrade), and each neuron's krim is independent --
                # caught by -179's own restore-honesty-at-grown-size check,
                # not assumed uniform.
                has_n_events = np.array(
                    [k is not None and hasattr(k, 'n_events') for k in krims],
                    dtype=bool,
                )
                ev0 = np.array(
                    [(k.n_events if has_n_events[idx] else len(k.events))
                     if k is not None else 0
                     for idx, k in enumerate(krims)],
                    dtype=np.int64,
                )
                raw, _ = vectorized_wind_count(base_dphi, threshold, phase0, att)
                new_count = np.where(
                    has_n_events,
                    monotonic_new_count(raw),
                    saturating_new_count(ev0, raw),
                )
            else:
                if not hasattr(sample_krim, '_inner'):
                    raise NotImplementedError(
                        f"recall_fast: modality {m!r} krimelack is "
                        f"{type(sample_krim).__name__} with no ._inner "
                        "OscillatorKrimelack -- outside the proven scope, "
                        "refusing to guess.")
                inner0 = sample_krim._inner
                sig = signal if isinstance(signal, list) else list(signal)
                sig = np.asarray(sig, dtype=np.float64)
                base_dphi = inner0.kappa * sig * inner0.dt
                # Sensory kappa/threshold ARE uniform across neurons here
                # (_seed_dna_diversity only touches the PRIMARY, i.e.
                # language, krimelack -- confirmed by direct introspection),
                # so a single sample_krim's tuning is representative and
                # attenuation genuinely varies the signal per neuron (unlike
                # language, where it's baked into omega_0 and cancels).
                att = np.array(
                    [signal_attenuation(int(ring_pos[i]), int(ring_n[i]), mi)
                     for i in range(n)],
                    dtype=np.float64,
                )
                phase0 = np.array(
                    [k._inner.phase if k is not None else 0.0 for k in krims],
                    dtype=np.float64,
                )
                ev0 = np.array(
                    [k.n_events if k is not None else 0 for k in krims],
                    dtype=np.int64,
                )
                raw, _ = vectorized_wind_count(base_dphi, inner0.threshold, phase0, att)
                new_count = monotonic_new_count(raw)

            new_count = np.where(present_mask, new_count.astype(np.float64), 0.0)
            deltas_matrix[:, mi] = new_count

        # 2026-07-08 word-recognition fix: with only "language" ever
        # populated in a live query, deltas_matrix's rows are always a
        # scaled unit vector along one fixed axis (confirmed live:
        # cosine similarity between ANY two different words' query
        # vectors is 1.0), so a pure cosine-best scan can never
        # discriminate between words -- it always returns whichever
        # concept happens to sit closest to that one direction,
        # regardless of what was actually asked (confirmed: every real
        # emission for 24+ hours was the same single word). Checking the
        # query word itself against each neuron's own real, already-
        # recorded vocabulary first (recall_exact_or_best) resolves any
        # word she has real experience with directly and unambiguously,
        # the same "known word skips the fuzzy route" pattern
        # Section.receive() already uses. Falls through to the existing
        # fuzzy scan unchanged for words she's never bound.
        query_word = query_signals.get("language")
        query_concept = query_word.lower() if isinstance(query_word, str) else None
        for i, neuron in enumerate(all_neurons):
            best_concept, _ = neuron.binding_atlas.recall_exact_or_best(
                query_concept, deltas_matrix[i])
            if best_concept is not None:
                # GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 4): vote
                # weighted by learned STDP synapse strength -- see
                # _stdp_vote_weight. 1.0 for any untrained neuron.
                votes[best_concept] += self._stdp_vote_weight(neuron)

        return votes

    def _recall_fast_resonant_spectral(self, query_signals: Dict[str, Any]) -> "Counter":
        """recall_fast()'s resonant_spectral branch.

        Non-mutating by construction, same as the grandurun branch above,
        but for a different reason: resonant_spectral's encode_state never
        feeds a krimelack at all (no transduce()/feed_signal() call reads
        or advances oscillator state) -- it's a pure function of
        multi_modal_signals and the neuron's own cached projection
        matrices. There is no krimelack state to snapshot/restore here,
        so this can call the EXACT SAME encode_state() the write path
        (experience_moment) uses, with no risk of query contamination and
        no parity-drift risk between write and read (one function, not two
        descriptions of the same thing).

        GL-FIX-POPULATION-LANE-RECOMPUTE (2026-07-06): lane_features(query_
        signals) does not depend on the neuron (see neuron.encode_state's
        docstring) -- hoisted here so it's computed once per call instead of
        once per neuron. This is the live "recognition" hot path
        (organism.recall_fast, called synchronously per word), so the
        redundant recompute scaled directly with her neuron population and
        was paid on every word."""
        from collections import Counter
        from . import resonant_chi as rc
        votes = Counter()
        precomputed_lanes = rc.lane_features(query_signals)
        for hemi in self.hemispheres:
            for neuron in hemi.cluster.neurons:
                target = neuron.encode_state(query_signals, precomputed_lanes)
                best_concept, _ = neuron.binding_atlas.recall_best(target)
                if best_concept is not None:
                    # GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 4): THE
                    # production recall path (observable=resonant_spectral
                    # is the live default) -- votes weighted by learned
                    # STDP synapse strength so spike-bus learning finally
                    # has a consequence in what she recalls/says. 1.0 for
                    # any untrained neuron (behavior identical to the old
                    # +=1 until real potentiation exists).
                    votes[best_concept] += self._stdp_vote_weight(neuron)
        return votes
