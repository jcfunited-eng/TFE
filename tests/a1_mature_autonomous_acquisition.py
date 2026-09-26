"""Bounded unattended food-acquisition witness on the original copied live pair.

No offered food, authored movement, reserve/memory edits, forced wake/sleep,
or injected sensory cues. This is NOT complete AUT-01 acceptance by itself:
memory-guided pursuit and its causal control must be demonstrated separately
if no learned continuation occurs. Run only in a network-disabled container,
without live mounts, after candidate source review. The 256-interval budget is
a test limit, never an organism duration or action-selection rule.
"""
from __future__ import annotations

from pathlib import Path
import resource
import subprocess
import sys
import time

from a1_mature_caretaker_delivery import digest, persist, report, startup
from a1_mature_waking_retention import seed_copied_pair


def advance(actor):
    from dsf_ai_service.lean_actor import PhysicalOccurrence
    actor._adopt_checkpoint_if_ready()
    if actor._durability_blocked():
        assert actor._checkpoint.outstanding
        actor._receive_required_checkpoint()
    before = actor._runtime.live_organism_tick
    identity = actor._runtime.identity
    result = actor._settle(PhysicalOccurrence("unattended", None))
    assert result.native_interval_count == 1
    assert actor._runtime.live_organism_tick == before + 1
    assert actor._runtime.identity == identity
    assert len(actor._world.observation_snapshot().objects) <= 64
    return result.observation


def other_body_custody(actor):
    snapshot = actor._world.canonical_observation_snapshot()
    return tuple((body.body_id, body.pose, body.held_object_id)
                 for body in snapshot.bodies if body.body_id != snapshot.self_body_id)


def main():
    mode = sys.argv[1]
    assert mode in ("acquire", "cold")
    started = time.monotonic()
    if mode == "acquire":
        seed_copied_pair()
    actor = startup()
    try:
        if mode == "cold":
            advance(actor)
            persist(actor)
            report("cold_next_interval", tick=actor._runtime.live_organism_tick)
        else:
            assert actor._runtime.reserve_micrograms == 0
            assert actor._runtime.feeding
            before_intake = actor._runtime.counts["meals_micrograms"]
            before_bites = actor._runtime.counts["bites"]
            for name in ("episodic_binding_engine.py", "guala_functional_organism.py",
                         "guala_functional_loop.py", "guala_caretaker_hand.py",
                         "lean_production_app.py", "substrate/embodiment_world.py"):
                source = Path("/app/dsf_ai_service") / name
                report("source", path=str(source), sha256=digest(source.read_bytes()))
            moved = False
            certified_held = None
            learned_intervals = 0
            intake_seen = False
            for index in range(256):
                before_snapshot = actor._world.canonical_observation_snapshot()
                own_before = next(b for b in before_snapshot.bodies
                                  if b.body_id == before_snapshot.self_body_id)
                if own_before.held_object_id != certified_held:
                    certified_held = None
                other_before = other_body_custody(actor)
                observation = advance(actor)
                # No implicit caregiver repositioning/presentation can earn an
                # autonomous acquisition claim, even on an unattended request.
                assert observation.get("caregiver_presentation") is None
                motion = observation["actual_root_motion"]
                moved = moved or any(motion[1:])
                applied = observation["requested_world_action"]
                refusal = observation["world_action_refusal"]
                snapshot = actor._world.canonical_observation_snapshot()
                own = next(b for b in snapshot.bodies if b.body_id == snapshot.self_body_id)
                continued_custody = (certified_held is not None
                                     and own.held_object_id == certified_held)
                acquired_now = applied in ("grasp", "take") and refusal is None
                if acquired_now:
                    assert own.held_object_id is not None
                other_after = other_body_custody(actor)
                assert len(other_before) == len(other_after)
                for prior, successor in zip(other_before, other_after):
                    assert prior[0] == successor[0]
                    if prior[1] != successor[1]:
                        # Once independently acquired, food may be eaten while
                        # the empty-handed caregiver withdraws. Acquisition
                        # during caregiver movement still cannot qualify.
                        assert (continued_custody and prior[2] is None
                                and successor[2] is None), (
                            "another body moved before independent acquisition"
                        )
                    if prior[2] != successor[2]:
                        assert (applied == "take" and refusal is None
                                and prior[2] == own.held_object_id and successor[2] is None), (
                            "external custody changed without Guala taking that object"
                        )
                if not continued_custody:
                    certified_held = None
                if acquired_now:
                    certified_held = own.held_object_id
                reason = observation.get("act_reason") or ""
                learned_intervals += int(reason.startswith("learned continuation"))
                report("unattended", index=index + 1,
                       tick=actor._runtime.live_organism_tick,
                       act=observation["her_act"], reason=reason, applied=applied,
                       refusal=refusal, motion=motion,
                       reserve=actor._runtime.reserve_micrograms,
                       intake_micrograms=actor._runtime.counts["meals_micrograms"] - before_intake)
                if actor._runtime.counts["meals_micrograms"] > before_intake:
                    assert actor._runtime.counts["bites"] > before_bites
                    assert observation["real_nutrition_intake_zeptojoules"] > 0
                    contact = getattr(own, "active_contact", None)
                    intake_object = getattr(contact, "object_id", None)
                    assert (moved and certified_held is not None
                            and own.held_object_id == certified_held
                            and intake_object == certified_held), (
                        "intake source was not independently approached and acquired"
                    )
                    intake_seen = True
                    break
            report("acquisition_result", physical_self_acquisition=intake_seen,
                   learned_continuation_intervals=learned_intervals,
                   complete_aut01_acceptance=False,
                   elapsed_seconds=time.monotonic() - started)
            assert intake_seen, "no autonomous intake within the declared observation budget"
            persist(actor)
    finally:
        try:
            actor._finish_checkpoint()
        finally:
            actor.close()
    if mode == "acquire":
        subprocess.run([sys.executable, "-B", __file__, "cold"], check=True, timeout=60)
    report("finished", mode=mode, elapsed_seconds=time.monotonic() - started,
           max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    main()
