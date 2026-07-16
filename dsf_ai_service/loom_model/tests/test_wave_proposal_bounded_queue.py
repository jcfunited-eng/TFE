"""
GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 5): the wave-field feed
returns as PROPOSALS over a BOUNDED queue (spec Cognition-core row).

Proves, against the real engine object:
  - the sensory proposal queue is bounded at WAVE_PROPOSAL_QUEUE_MAX (64);
  - overflow drops the OLDEST proposal (the field has moved on), never the
    newest, and never blocks the producer;
  - drops are counted (_organism_sensory_dropped_count) and logged as
    wave_proposal_dropped events;
  - task_done() accounting stays balanced through drops, so the seal's
    settle/quiesce joins can still complete (drained here via join()).

The organism worker is parked with the same cooperative pause the save
path uses (_organism_pause_req/_ack), so the overflow is deterministic --
no timing-dependent race with the drain.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def test_wave_proposal_queue_bounded_drop_oldest():
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    g = Guala()
    try:
        cap = g.WAVE_PROPOSAL_QUEUE_MAX
        assert g._organism_sensory_queue.maxsize == cap, (
            f"queue maxsize {g._organism_sensory_queue.maxsize} != "
            f"WAVE_PROPOSAL_QUEUE_MAX {cap} -- the bound is not wired")

        hemi_id = g.organism.brain.hemispheres[0].hemi_id
        # Start the worker (first enqueue), then park it between items so
        # nothing drains while we overflow.
        g._enqueue_organism_sensory(hemi_id, [0.1], tick=-1, input_chi=1)
        g._organism_pause_req.set()
        assert g._organism_pause_ack.wait(5.0), (
            "organism worker never acknowledged the cooperative pause")

        overflow = 10
        for i in range(cap + overflow):
            g._enqueue_organism_sensory(hemi_id, [0.1], tick=i, input_chi=1)

        assert g._organism_sensory_queue.qsize() <= cap, (
            f"queue grew past its bound: {g._organism_sensory_queue.qsize()}")
        assert g._organism_sensory_dropped_count >= overflow, (
            f"expected >= {overflow} counted drops, got "
            f"{g._organism_sensory_dropped_count}")
        # Drop-OLDEST: the earliest ticks are gone, the newest survive.
        remaining_ticks = sorted(
            item[2] for item in list(g._organism_sensory_queue.queue))
        assert remaining_ticks[-1] == cap + overflow - 1, (
            "the newest proposal was dropped -- bound must drop OLDEST")
        assert remaining_ticks[0] >= 0 and remaining_ticks[0] > -1, (
            "the oldest queued item survived a full overflow")

        # Loud, not silent: the drop event reached the substrate stream.
        kinds = [ev.kind for ev in g._substrate_events]
        assert "wave_proposal_dropped" in kinds, (
            "no wave_proposal_dropped event was logged for a real overflow")

        # /status surfaces the numbers.
        status = g.introspect()
        ow = status["organism_worker"]
        assert ow["wave_proposals_dropped"] >= overflow
        assert ow["wave_proposals_queued"] <= cap

        # Accounting stayed balanced: resume and drain to empty.
        g._organism_pause_req.clear()
        g._organism_sensory_queue.join()
        assert g._organism_sensory_queue.qsize() == 0
        print("test_wave_proposal_queue_bounded_drop_oldest: PASS")
    finally:
        g._organism_pause_req.clear()
        g.shutdown()


if __name__ == "__main__":
    test_wave_proposal_queue_bounded_drop_oldest()
    print("ALL PASS: test_wave_proposal_bounded_queue")
