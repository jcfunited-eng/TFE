# GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v2

**doc_id:** GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v2
**Author:** Eve
**Ordered by:** Joe (2026-07-07 session — after c1 halted GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1 on the recognized-but-unbridged coverage/event gap)
**Status:** Canonical. Supersedes `GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v1`.
**Life expectancy:** Current until superseded by v3.

## What changed from v1

v1 factored Phase 1 (event-driven neurons) and Phase 2 (STDP plasticity) as separable dispatches. c1's execution of Phase 1 revealed the factoring was wrong: event-driven firing without the STDP synapse layer produces a substrate that runs but doesn't recognize, remember, or respond — because recognition depends on synaptic weights that Phase 1 alone doesn't provide. Coverage-model chi_atlas can't bridge the gap because emission and recall depend on the coverage semantics that firing events don't produce.

v2 merges Phase 1 and Phase 2 into a single "Phase 1: Event-driven substrate with plasticity." All other phase content and all core commitments stand.

## Sections unchanged from v1

Sections 1 (Purpose), 2 (Core commitments), 3 (Architectural components except 3.4 revised below), 5 (Success criteria), 6 (Governance), 7 (Interfaces), 8 (Deprecation), 9 (Timeline), 10 (Commitment) are all preserved from v1 verbatim. Reference v1 for their content. This v2 document lists only what changed.

## Sections changed

### 3.4 — STDP plasticity (unchanged text; now belongs to Phase 1)

Content preserved from v1. Reassigned from Phase 2 to Phase 1. STDP is not a follow-on; it is a core mechanism required for recognition, memory, and response to work at all in the event-driven substrate.

### 4 — Development phases (revised)

**Phase 1: Event-driven substrate with plasticity.** Combines v1 Phase 1 and Phase 2. Includes:
- Neuron event loop (fires on spike arrival, decays between)
- Spike propagation queue (real-time delay lines)
- Local synapse weights per neuron, updated via STDP
- Membrane potential integration
- Refractory state
- Membrane-state emission and recall paths (replacing coverage-model chi_atlas dependencies)
- Deprecation of coverage-model chi_atlas at end of phase

Phase 1 harness verification: input arrives, propagates through coupled neurons, produces output; STDP-strengthened pathways from repeat exposure produce faster and more selective responses on subsequent exposure; recognition of repeated content improves over time.

**Phase 2 (was Phase 3): Sparse activity via lateral inhibition.** Content unchanged.

**Phase 3 (was Phase 4): Local metabolism.** Content unchanged.

**Phase 4 (was Phase 5): Neuromodulation.** Content unchanged.

**Phase 5 (was Phase 6): Sleep as work.** Content unchanged.

**Phase 6 (was Phase 7): Population-based seed.** Content unchanged.

Six phases total instead of seven. Demo-critical: Phase 1, Phase 2, Phase 6. Phases 3, 4, 5 can defer post-demo.

Timeline update:
- Phase 1 (event-driven + STDP + emission/recall migration): 8-10 days
- Phase 2 (sparse activity): 2-3 days
- Phase 6 (seed): 2-3 days plus generator work
- Total demo-critical: ~13-16 days. Fits three weeks with buffer.

---

### Changelog
- v2 (2026-07-07, Eve): merged Phase 1 and Phase 2 from v1 into single Phase 1. Recognizes that event-driven firing and STDP synapse plasticity are inseparable — the substrate doesn't produce recognition, memory, or response until both are in place. All other blueprint content preserved.
- v1 (2026-07-07, Eve): superseded.
