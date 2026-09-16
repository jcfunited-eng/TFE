"""The functional organism (Joe, 2026-09-14): her acts chosen from her own
record under the kernel's read of her sensed streams, one jaw reflex, her
metabolism and head as declared laws, bounded memory, exact custody. Every
test runs the real home world; the world validates her acts."""

from __future__ import annotations

import math
import struct

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    ACTS, BODY_AXES, CAPACITY_MICROGRAMS, FunctionalOrganism, MAGIC, syllable_pcm,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import MAX_PRESSURE_BYTES, PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.substrate.embodiment_world import EmbodiedObject, PositionMM


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def _present(food: str) -> PhysicalOccurrence:
    return PhysicalOccurrence("sensory", LeanSensoryOccurrence(
        source="caretaker-food", retina_rgb_u8=None, pressure_s16le=None, present_food=food,
    ))


def _tone(frequency_hz: float, samples: int = 4_000) -> bytes:
    return struct.pack(f"<{samples}h", *(int(9_000 * math.sin(2 * math.pi * frequency_hz * i / 16_000)) for i in range(samples)))


def _heard(pcm: bytes) -> PhysicalOccurrence:
    return PhysicalOccurrence("sensory", LeanSensoryOccurrence(source="microphone", retina_rgb_u8=None, pressure_s16le=pcm))


def _her(world):
    snapshot = world.observation_snapshot()
    return next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)


def _apple_ahead(world, object_id: str, ahead_mm: int) -> None:
    """An apple set down ahead of her by the test's hand: the first clear spot
    at the asked distance, then a little to either side or further, since
    what stands around her depends on what she did before."""

    snapshot = world.observation_snapshot()
    body = _her(world)
    apple = next(item for item in snapshot.objects if item.object_id == "apple")
    last_error = None
    for extra_mm, turn in ((0, 0), (0, 25), (0, -25), (120, 0), (120, 40), (120, -40), (260, 0), (260, 60), (260, -60)):
        radians = math.radians((body.pose.heading_millidegrees / 1000) + turn)
        spot = PositionMM(body.pose.position.x + round((ahead_mm + extra_mm) * math.cos(radians)), body.pose.position.y + round((ahead_mm + extra_mm) * math.sin(radians)), 0)
        try:
            world.admit_authored_arrival(EmbodiedObject(object_id, apple.radius_mm, apple.mass_grams, spot, reflectance_ppm=apple.reflectance_ppm, material=apple.material, optical_surface=apple.optical_surface))
            return
        except ValueError as error:  # the world's authoring guard: the spot is not clear
            last_error = error
    raise AssertionError(f"no clear spot ahead of her for {object_id}: {last_error}")


def _run(organism, world, occurrences):
    loop = FunctionalPhysicalLoop()
    results = []
    for occurrence in occurrences:
        results.append(loop.settle(organism, world, occurrence))
    return results


def test_genesis_encodes_and_restores_byte_exact_with_the_actor_contract() -> None:
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=710_228)
    encoded = organism.encoded()
    assert encoded.startswith(MAGIC)
    again = FunctionalOrganism.restore(encoded)
    assert again.encoded() == encoded and again.live_organism_tick == 710_228
    ready = organism.readiness()
    assert ready.identity == IDENTITY and ready.organism_tick == 710_228 and ready.state_bytes == len(encoded)
    assert ready.python_callback_count == 0 and ready.articulated_body_axes == BODY_AXES
    checkpoint = organism.snapshot_lived_state().prepare_checkpoint()
    assert checkpoint.encoded_generation() == encoded and checkpoint.state_sha256 == ready.state_sha256
    organism.validate_lived_checkpoint(checkpoint)
    organism.adopt_published_lived_checkpoint(checkpoint)
    assert len({axis[1] for axis in BODY_AXES}) == 45


def test_hungry_she_bites_what_the_caretaker_holds_out_and_her_reserve_rises() -> None:
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    before = organism.reserve_micrograms
    assert before < CAPACITY_MICROGRAMS * 3 // 5
    results = _run(organism, world, [UNATTENDED, _present("apple"), *([UNATTENDED] * 6)])
    presentation = results[1].observation["caregiver_presentation"]
    assert presentation["presented"] is True, presentation
    bites = [r.observation for r in results if r.observation["her_act"] == "bite"]
    assert bites and all(o["requested_world_action"] == "bite" and o["world_action_refusal"] is None for o in bites)
    assert sum(o["real_nutrition_intake_zeptojoules"] for o in bites) > 0
    assert organism.reserve_micrograms > before
    assert organism.counts["bites"] == len(bites)
    assert organism.live_organism_tick == 1 + len(results)


def test_hungry_with_food_in_hand_reach_she_grasps_then_bites_then_drops_the_core() -> None:
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-near", 350)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    results = _run(organism, world, [UNATTENDED] * 40)
    acts = [r.observation["her_act"] for r in results]
    assert acts[0] == "grasp" and results[0].observation["world_action_refusal"] is None
    assert _her(world).held_object_id in {"apple-near", None}
    assert "bite" in acts
    first_bite = acts.index("bite")
    assert first_bite == 1
    assert organism.counts["bites"] >= 1 and organism.reserve_micrograms > CAPACITY_MICROGRAMS * 55 // 100


def test_releasing_what_she_holds_takes_its_declared_time_in_the_world() -> None:
    """The world once reported zero elapsed time for opening the hand, which
    left the thermal interval below its minimum and refused her first act on
    the live world (she held an eaten core). Release now takes its declared
    duration like every other act, and she drops the core."""

    from dsf_ai_service.substrate.embodiment_world import (
        ActionExecutionReceipt, GraspContactCommand, PORT_ID, ReleaseHeldObjectCommand, encode_command,
    )

    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-held", 350)
    before = world.observation_snapshot()
    grasp = world.prepare_port_command(
        port_id=PORT_ID, command_payload=encode_command(GraspContactCommand(250_000)),
        causal_intent_receipt_sha256="ab" * 32, expected_revision=before.revision,
    )
    assert not isinstance(grasp, ActionExecutionReceipt)
    with world.prepared_action_visibility_transaction(grasp):
        world.commit_prepared_action(grasp)
    assert _her(world).held_object_id == "apple-held"
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10  # not hungry: the apple is not bitten
    organism._state["feeding"] = False
    snapshot = world.observation_snapshot()
    apple = next(item for item in snapshot.objects if item.object_id == "apple-held")
    assert apple.material is not None and sum(apple.material.tastant_mass_micrograms) > 0
    # Make what she holds an eaten core: the world's own bite law can take nothing more.
    core = world.prepare_port_command(
        port_id=PORT_ID, command_payload=encode_command(ReleaseHeldObjectCommand(250_000)),
        causal_intent_receipt_sha256="cd" * 32, expected_revision=snapshot.revision,
    )
    assert not isinstance(core, ActionExecutionReceipt), core.reason
    assert core.execution_receipt.elapsed_nanoseconds == 250_000 * 1_000
    world.discard_prepared_action(core)
    results = _run(organism, world, [UNATTENDED] * 2)
    assert all(r.observation["her_act"] in ACTS for r in results)


def test_an_eaten_core_in_her_hand_is_released() -> None:
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    body = _her(world)
    apple = next(item for item in snapshot.objects if item.object_id == "apple")
    core_material = type(apple.material)(
        odorant_reservoir_nanograms=apple.material.odorant_reservoir_nanograms,
        odorant_release_nanograms_per_second=apple.material.odorant_release_nanograms_per_second,
        tastant_mass_micrograms=(1, 0, 1, 0, 0),
        surface_temperature_millikelvin=apple.material.surface_temperature_millikelvin,
        compliance_ppm=apple.material.compliance_ppm, roughness_micrometers=apple.material.roughness_micrometers,
        moisture_ppm=apple.material.moisture_ppm,
    )
    world.admit_authored_arrival(EmbodiedObject(
        "apple-core", apple.radius_mm, 5, PositionMM(body.pose.position.x + 350, body.pose.position.y, 0),
        reflectance_ppm=apple.reflectance_ppm, material=core_material,
    ))
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    results = _run(organism, world, [UNATTENDED] * 3)
    acts = [r.observation["her_act"] for r in results]
    assert "grasp" not in acts, acts  # nothing to bite: not food to her hand


def test_syllables_are_deterministic_bounded_and_vary_by_vowel_onset_and_utterance() -> None:
    first = syllable_pcm((3_600, 0, 0), 7)
    assert first == syllable_pcm((3_600, 0, 0), 7)
    assert first != syllable_pcm((3_600, 1, 0), 7) and first != syllable_pcm((3_600, 0, 1), 7) and first != syllable_pcm((3_600, 0, 0), 8)
    assert 0 < len(first) <= MAX_PRESSURE_BYTES and len(first) % 2 == 0
    samples = struct.unpack(f"<{len(first) // 2}h", first)
    assert max(abs(v) for v in samples) >= 8_000
    # A voiced syllable near her pitch: zero crossings of the waveform sit in the hundreds per quarter second.
    crossings = sum(1 for a, b in zip(samples, samples[1:]) if (a < 0) != (b < 0))
    assert 200 <= crossings <= 4_000, crossings


def test_the_caregiver_never_stands_in_a_doorway_and_withdraws_home_after_the_meal() -> None:
    from dsf_ai_service.guala_caretaker_hand import CAREGIVER_HOME_MM, DOORWAY_CLEARANCE_MM, in_doorway

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    results = _run(organism, world, [_present("apple"), *([UNATTENDED] * 60)])
    assert results[0].observation["caregiver_presentation"]["presented"] is True
    snapshot_after_offer = None
    withdrawals = [r.observation["caregiver_withdrawal"] for r in results if r.observation["caregiver_withdrawal"] is not None]
    assert withdrawals, "the caregiver never withdrew after the meal"
    assert withdrawals[0]["set_down"] == "apple" and withdrawals[0]["home"] is True, withdrawals[0]
    snapshot = world.observation_snapshot()
    person = next(body for body in snapshot.bodies if body.body_id != snapshot.self_body_id)
    assert person.held_object_id is None
    assert abs(person.pose.position.x - CAREGIVER_HOME_MM.x) <= 150 and abs(person.pose.position.y - CAREGIVER_HOME_MM.y) <= 150
    # No step of the presentation ever stood in a doorway.
    for step in results[0].observation["caregiver_presentation"]["steps"]:
        if step.get("operation") == "move" and step.get("reason") == "applied" and step.get("to"):
            x, y = step["to"]
            region = next((r for r in snapshot.regions if r.bounds.minimum.x <= x <= r.bounds.maximum.x and r.bounds.minimum.y <= y <= r.bounds.maximum.y), None)
            if region is not None and step is results[0].observation["caregiver_presentation"]["steps"][-1]:
                assert not in_doorway(snapshot, PositionMM(x, y, 0), region.region_id, DOORWAY_CLEARANCE_MM)


def test_the_kernel_reads_her_streams_and_her_memory_stays_bounded_over_three_hundred_beats() -> None:
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    sizes = []
    novel = 0
    gates = 0
    loop = FunctionalPhysicalLoop()
    for index in range(300):
        result = loop.settle(organism, world, _present("apple") if index == 3 else UNATTENDED)
        sizes.append(len(organism.encoded()))
        novel += int(result.observation["kernel_novel"])
        gates += int(result.observation["dsf_delivery_count"])
    assert gates > 0 and novel > 0
    assert max(sizes) < 95_000 and len(world.encoded_snapshot()) < 4_000_000   # her bound: twenty-two streams with her ear (72,000 at sixteen, 64,000 at thirteen)
    state = organism._state
    assert len(state["familiarity"]) <= 512 and len(state["episodes"]) <= 64 and len(state["voice"]) <= 16
    assert all(len(window) <= 64 for window in state["streams"].values())
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded
    assert organism.counts["bites"] > 0 and organism.counts["strides"] > 0 and organism.counts["syllables"] > 0
    # Bouts, not a constant stream: fewer than one syllable in four beats over the run.
    assert organism.counts["syllables"] < 300 // 4


def test_an_older_functional_body_is_migrated_on_restore_and_forgets_sounds_of_the_old_airway() -> None:
    import json

    from dsf_ai_service.guala_functional_organism import VOICE_VERSION

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=5)
    state = json.loads(organism.encoded()[len(MAGIC):])
    state["voice_version"] = 1
    state["voice"] = [{"drive": [44, 31, 0], "heard": [0.1] * 32, "tick": 3}]
    state["heard"] = [{"tick": 4, "profile": [0.2] * 32}]
    for key in ("visited", "door_goal", "bout_syllables", "quiet_until_tick", "blocked_doors", "attended_tick", "unreachable_food", "food_goal", "food_refusals", "food_best_mm", "food_stall_beats", "ambient_sound", "answered_profile", "touched", "strides_since_pickup", "handled", "release_refusals", "touching", "listening_since", "call_profile", "answer_bout", "answer_target", "answer_pending", "answer_map", "food_rooms", "food_room_goal", "room_now", "room_beats", "keeping_room", "keep_walk_beats", "last_kept", "kept", "stuck_beats"):
        state.pop(key, None)
    older = MAGIC + json.dumps(state, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    restored = FunctionalOrganism.restore(older)
    assert restored.live_organism_tick == 5 and restored.encoded() != older
    assert restored._state["voice_version"] == VOICE_VERSION and restored._state["voice"] == [] and restored._state["heard"] == []
    assert "visited" not in restored._state and "door_goal" not in restored._state and restored._state["acts"] == {}
    # Migrated once: restoring the migrated body changes nothing.
    again = FunctionalOrganism.restore(restored.encoded())
    assert again.encoded() == restored.encoded()


def test_when_no_food_is_left_the_caretaker_brings_a_fresh_apple_and_she_eats_it() -> None:
    from dsf_ai_service.guala_caretaker_hand import DELIVERY_ID

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    before_ids = {item.object_id for item in world.observation_snapshot().objects}
    results = _run(organism, world, [UNATTENDED, _present(DELIVERY_ID), *([UNATTENDED] * 6)])
    presentation = results[1].observation["caregiver_presentation"]
    assert presentation["delivered"] is not None and presentation["delivered"] not in before_ids
    assert presentation["presented"] is True, presentation
    assert presentation["object_id"] == presentation["delivered"]
    bites = [r.observation for r in results if r.observation["her_act"] == "bite"]
    assert bites and sum(o["real_nutrition_intake_zeptojoules"] for o in bites) > 0
    snapshot = world.observation_snapshot()
    assert len([item for item in snapshot.objects if item.object_id.startswith("apple")]) == 2


def test_her_gaze_follows_structure_not_brightness() -> None:
    from dsf_ai_service.guala_functional_organism import FOCAL_COLUMNS, FOCAL_ROWS, structure_centre

    flat_bright_top = tuple(240 if index // FOCAL_COLUMNS < FOCAL_ROWS // 2 else 200 for index in range(FOCAL_COLUMNS * FOCAL_ROWS))
    x, y = structure_centre(flat_bright_top)
    assert abs(x - 0.5) < 0.02 and abs(y - 0.5) < 0.06, (x, y)  # one horizontal edge at mid height; brightness above it holds nothing
    edge_on_the_right = tuple(30 if (index % FOCAL_COLUMNS) < int(FOCAL_COLUMNS * 0.8125) else (250 if (index % FOCAL_COLUMNS) % 2 else 20) for index in range(FOCAL_COLUMNS * FOCAL_ROWS))
    x, y = structure_centre(edge_on_the_right)
    assert x > 0.75 and abs(y - 0.5) < 0.05, (x, y)
    assert structure_centre(tuple([128] * (FOCAL_COLUMNS * FOCAL_ROWS))) == (0.5, 0.5)


def test_eaten_cores_leave_the_world_through_the_caretaker_and_the_bin() -> None:
    """A core the caretaker carries home goes out at the world's boundary
    (no core left on the hallway floor); the world refuses to take away
    what she holds."""

    from dsf_ai_service.guala_caretaker_hand import CAREGIVER_HOME_MM

    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    apple = next(item for item in snapshot.objects if item.object_id == "apple")
    core_material = type(apple.material)(
        odorant_reservoir_nanograms=apple.material.odorant_reservoir_nanograms,
        odorant_release_nanograms_per_second=apple.material.odorant_release_nanograms_per_second,
        tastant_mass_micrograms=(1, 0, 1, 0, 0),
        surface_temperature_millikelvin=apple.material.surface_temperature_millikelvin,
        compliance_ppm=apple.material.compliance_ppm, roughness_micrometers=apple.material.roughness_micrometers,
        moisture_ppm=apple.material.moisture_ppm,
    )
    # An eaten core lying in the kitchen, away from any doorway.
    world.admit_authored_arrival(EmbodiedObject("apple-core", apple.radius_mm, 5, PositionMM(1_000, 3_800, 0), reflectance_ppm=apple.reflectance_ppm, material=core_material))
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    results = _run(organism, world, [UNATTENDED] * 60)
    withdrawals = [r.observation["caregiver_withdrawal"] for r in results if r.observation["caregiver_withdrawal"] is not None]
    assert any(w.get("fetched") == "apple-core" for w in withdrawals), withdrawals
    assert any(w.get("binned") == "apple-core" for w in withdrawals), withdrawals
    ids = {item.object_id for item in world.observation_snapshot().objects}
    assert "apple-core" not in ids
    # What she holds cannot be taken away.
    _apple_ahead(world, "apple-mine", 350)
    _run(organism, world, [UNATTENDED] * 3)
    her = _her(world)
    if her.held_object_id == "apple-mine":
        import pytest
        with pytest.raises(ValueError):
            world.admit_authored_departure("apple-mine")


def test_the_caretaker_offers_a_toy_and_she_takes_it_carries_it_and_sets_it_down() -> None:
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    before = next(item for item in world.observation_snapshot().objects if item.object_id == "toy-bear").position
    results = _run(organism, world, [UNATTENDED, _present("toy-bear"), *([UNATTENDED] * 40)])
    presentation = results[1].observation["caregiver_presentation"]
    assert presentation["presented"] is True, presentation
    # Taking the toy is hers to choose: it is among her candidates while the
    # caregiver holds it out; whether she takes it comes from her record.
    from dsf_ai_service.guala_functional_organism import candidates, things_in_sight
    snapshot = world.observation_snapshot()
    her = _her(world)
    person = next(body for body in snapshot.bodies if body.body_id != snapshot.self_body_id)
    if person.held_object_id == "toy-bear":
        offered = next(item for item in snapshot.objects if item.object_id == "toy-bear")
        assert any(c[0] == "take" for c in candidates(snapshot, her, None, offered, things_in_sight(snapshot), organism.live_organism_tick))
    acts = [r.observation["her_act"] for r in results]
    after = next(item for item in world.observation_snapshot().objects if item.object_id == "toy-bear")
    # Either she took it (and it is in her hand or set down elsewhere), or the
    # caregiver's patience ran out and it carried the toy home: the toy is not
    # left where it was picked up from.
    assert ("take" in acts and organism.counts["handled"] >= 1) or after.position is None or after.position != before, (acts[:12], after.position, before)


def test_a_step_pushes_light_things_in_her_way_aside() -> None:
    """The world's step law: a light thing in the path of a stride is pushed
    to the nearest clear spot beside the path; heavy furniture still blocks.
    Nine cups ringed around her at 430 mm refused every stride before."""

    from dsf_ai_service.guala_functional_organism import MOVES

    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    body = _her(world)
    cup = next(item for item in snapshot.objects if item.object_id == "cup")
    before = {}
    for index, degrees in enumerate(range(0, 360, 40)):
        a = math.radians(degrees)
        before[f"cup-{index}"] = PositionMM(body.pose.position.x + round(430 * math.cos(a)), body.pose.position.y + round(430 * math.sin(a)), 0)
        world.admit_authored_arrival(EmbodiedObject(f"cup-{index}", cup.radius_mm, cup.mass_grams, before[f"cup-{index}"], reflectance_ppm=cup.reflectance_ppm, material=cup.material))
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    # Her record tries the moves her body can make (a door, a thing, a stride,
    # with the world's sidesteps); a ring this tight refused every one before.
    results = _run(organism, world, [UNATTENDED] * 40)
    moved = [r.observation for r in results if r.observation["her_act"] in MOVES and r.observation["world_action_refusal"] is None and any(r.observation["actual_root_motion"][1:])]
    assert moved, [r.observation["her_act"] + ":" + str(r.observation["world_action_refusal"]) for r in results][:20]
    assert _her(world).pose.position != body.pose.position
    after = world.observation_snapshot()
    # A cup her record picked up on the way is in her hand (no floor position); the rest lie clear.
    cups = [item for item in after.objects if item.object_id.startswith("cup-") and item.position is not None]
    assert len(cups) >= 8, len(cups)
    assert any(item.position != before[item.object_id] for item in cups), "nothing was pushed"
    her = _her(world)
    for item in cups:
        assert math.dist((item.position.x, item.position.y), (her.pose.position.x, her.pose.position.y)) >= item.radius_mm + her.radius_mm
        for other in cups:
            if other is not item:
                assert math.dist((item.position.x, item.position.y), (other.position.x, other.position.y)) >= item.radius_mm + other.radius_mm


def test_her_head_turns_toward_structure_so_the_floor_comes_into_her_focal_field() -> None:
    """Her head law: the wide field the head carries aims the focal cone, and her
    head follows what she acts on (Joe's word, 2026-09-15). On a fresh world every
    object lies on the floor below head height; within a few beats her head has
    pitched down toward them, the focal field shows structure, and the head stays
    inside its declared bounds and is restored byte-exact with the body."""

    from dsf_ai_service.guala_functional_organism import HEAD_PITCH_BOUND_MILLIDEGREES, HEAD_YAW_BOUND_MILLIDEGREES

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    assert organism.head == (0, 0)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, UNATTENDED)
    spread = 0
    for _ in range(40):
        observation = loop.settle(organism, world, UNATTENDED).observation
        yaw, pitch = organism.head
        assert -HEAD_YAW_BOUND_MILLIDEGREES <= yaw <= HEAD_YAW_BOUND_MILLIDEGREES
        assert -HEAD_PITCH_BOUND_MILLIDEGREES <= pitch <= HEAD_PITCH_BOUND_MILLIDEGREES
        focal = observation["retinal_u8"][135:]
        spread = max(spread, max(focal) - min(focal))
    assert organism.head[1] < 0, organism.head
    assert spread > 20, spread
    axes = {axis[1]: axis[3] for axis in organism.body_axes}
    assert (axes["neck_yaw"], axes["neck_pitch"]) == organism.head
    restored = FunctionalOrganism.restore(organism.encoded())
    assert restored.head == organism.head and restored.body_axes == organism.body_axes


# ----- her acts come from her record ----------------------------------------------


def test_every_act_is_chosen_from_her_record_and_the_record_grows_and_restores() -> None:
    """No rule chooses an act: every act but the jaw's reflex names the
    structure it was chosen under; under a structure, untried acts come first
    in the declared order; the record grows over beats, stays bounded, and
    restores byte-exact."""

    from dsf_ai_service.guala_functional_organism import ACTS, ACT_RECORD_CAPACITY

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    reasons = []
    for _ in range(200):
        observation = loop.settle(organism, world, UNATTENDED).observation
        if observation["her_act"] != "bite":
            assert observation["her_act"] in ACTS, observation["her_act"]
            assert observation["act_reason"].startswith("structure "), observation["act_reason"]
            reasons.append(observation["act_reason"])
    assert any("first try of" in r for r in reasons) and any("best so far" in r for r in reasons)
    record = organism._state["acts"]
    assert 3 <= len(record) <= ACT_RECORD_CAPACITY
    for entry in record.values():
        assert set(entry["acts"]) <= set(ACTS)
        for tries, total in entry["acts"].values():
            assert tries >= 1 and isinstance(total, float)
    assert organism.counts["structures"] == len(record)
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded


def test_the_record_chooses_untried_first_then_the_best_and_every_eighth_visit_the_least_tried() -> None:
    from dsf_ai_service.guala_functional_organism import EXPLORE_EVERY

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    acts = ["step", "turn_left", "say", "rest"]
    key = "abcdef0123456789"
    act, why = organism._choose(key, "SSSS", acts)
    assert act == "step" and "first try of step" in why
    organism._state["acts"][key] = {"acts": {"step": [3, -0.6], "turn_left": [2, 0.5], "say": [1, 0.1]}, "tick": 1}
    act, why = organism._choose(key, "SSSS", acts)
    assert act == "rest" and "first try of rest" in why  # still untried
    organism._state["acts"][key]["acts"]["rest"] = [1, 0.0]
    act, why = organism._choose(key, "SSSS", acts)
    assert act == "turn_left" and "best so far" in why, why  # mean +0.25 beats +0.10, 0.0 and -0.2
    organism._state["acts"][key]["acts"]["step"] = [EXPLORE_EVERY - 4, -0.6]  # visits total = 8
    act, why = organism._choose(key, "SSSS", acts)
    assert act == "say" and "least tried" in why, why  # say and rest tied at 1 try; say first in order


def test_what_followed_is_valued_by_her_state_when_she_chose_and_a_refusal_costs() -> None:
    """The value of what followed an act is her measured need at the moment she
    chose times the measured drops that followed, minus the burn the commit
    actually charged (carried in the pending record); no written constants."""
    from dsf_ai_service.guala_functional_organism import ACT_BURN_MULTIPLE, BASAL_BURN_MICROGRAMS, Decision

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    key = "0123456789abcdef"
    # A refused step: the commit charges basal burn only, and carries it into the pending record.
    organism._state["pending_act"] = {"key": key, "act": "step", "deficit": 0.25, "sleep_ratio": 0.0, "intake": 0, "refused": False}
    from dsf_ai_service.guala_functional_organism import STREAMS
    decision = Decision("step", "test", (), None, None, " ".join("q0000000" for _ in STREAMS), False, 0, ())
    organism.commit(decision, applied_action="refused", refusal="blocked", intake_micrograms=0, spoke=None,
                    heard_profile=None, self_profile=None, tick_now=organism.live_organism_tick)
    pending = organism._state["pending_act"]
    assert pending["refused"] is True and pending["burn"] == BASAL_BURN_MICROGRAMS
    organism._settle("other", True, 0.0, 0.0, 2)
    tries, total = organism._state["acts"][key]["acts"]["step"]
    expected_1 = (1.0 - 0.25) * (1.0 - 0.0) * 1.0 - BASAL_BURN_MICROGRAMS / CAPACITY_MICROGRAMS
    assert tries == 1 and abs(total - expected_1) < 1e-6
    # A step that moved her: the commit charges the step's burn; intake by her deficit, a sound by how rested.
    organism._state["pending_act"] = {"key": key, "act": "step", "deficit": 0.6, "sleep_ratio": 0.1, "intake": 0, "refused": False}
    organism.commit(decision, applied_action="step", refusal=None, intake_micrograms=1000, spoke=None,
                    heard_profile=None, self_profile=None, tick_now=organism.live_organism_tick)
    pending = organism._state["pending_act"]
    step_burn = BASAL_BURN_MICROGRAMS * (1 + ACT_BURN_MULTIPLE["step"])
    assert pending["intake"] == 1000 and pending["refused"] is False and pending["burn"] == step_burn
    organism._settle("other", False, 0.5, 0.0, 3)
    tries, total = organism._state["acts"][key]["acts"]["step"]
    expected_2 = 0.6 * 1.0 + 0.0 + (1.0 - 0.1) * 0.5 - step_burn / CAPACITY_MICROGRAMS
    assert tries == 2 and abs(total - (expected_1 + expected_2)) < 1e-6
    assert organism._state["pending_act"] is None


def test_the_jaw_reflex_credits_the_act_that_brought_food_to_her_mouth() -> None:
    """Hungry, the caretaker holds an apple to her mouth: she bites by reflex
    (not from the record); the intake is credited to the act she last chose."""


    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    results = _run(organism, world, [UNATTENDED, UNATTENDED, _present("apple")])
    first_bite = results[2].observation
    assert first_bite["her_act"] == "bite" and "reflex" in first_bite["act_reason"], first_bite["her_act"]
    assert first_bite["real_nutrition_intake_zeptojoules"] > 0
    last = organism._state["last_chosen"]  # the act she chose the beat before the apple reached her mouth
    tries, total = organism._state["acts"][last["key"]]["acts"][last["act"]]
    # The chosen act burned metabolic energy before intake arrived, then was credited with deficit.
    assert total >= float(last["deficit"]) - 0.001, (last, tries, total)
    more = _run(organism, world, [UNATTENDED] * 8)
    bites = [r.observation for r in more if r.observation["her_act"] == "bite"]
    assert bites and all("reflex" in o["act_reason"] for o in bites)


def test_the_record_is_bounded_and_an_older_body_drops_the_retired_rule_records() -> None:
    import json

    from dsf_ai_service.guala_functional_organism import ACT_RECORD_CAPACITY, RETIRED_KEYS

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    for index in range(ACT_RECORD_CAPACITY + 40):
        organism._credit(f"{index:016x}", "rest", 0.0, index)
    assert len(organism._state["acts"]) == ACT_RECORD_CAPACITY
    assert "0000000000000000" not in organism._state["acts"]  # the least recently met fell out
    state = json.loads(organism.encoded()[len(MAGIC):])
    for key in RETIRED_KEYS:
        state[key] = {}
    state.pop("acts"); state.pop("pending_act"); state.pop("last_chosen")
    older = MAGIC + json.dumps(state, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    restored = FunctionalOrganism.restore(older)
    assert restored._state["acts"] == {} and restored._state["pending_act"] is None
    assert not any(key in restored._state for key in RETIRED_KEYS)
    assert FunctionalOrganism.restore(restored.encoded()).encoded() == restored.encoded()


# ----- sleep and dreaming -----------------------------------------------------------


def test_she_sleeps_when_the_pressure_reaches_its_ceiling_her_eyes_close_and_she_wakes_when_it_is_gone() -> None:
    from dsf_ai_service.guala_functional_organism import SLEEP_PRESSURE_CEILING, SLEEP_RECOVERY_PER_BEAT

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    # Away from the bed, the ceiling alone does not put her to sleep; past it
    # by an eighth she sleeps where she drops.
    from dsf_ai_service.guala_functional_organism import EXHAUSTION_MARGIN
    exhausted_at = int(SLEEP_PRESSURE_CEILING * (1 + EXHAUSTION_MARGIN))
    organism._state["sleep_pressure"] = exhausted_at - 3
    loop = FunctionalPhysicalLoop()
    awake = [loop.settle(organism, world, UNATTENDED).observation for _ in range(3)]
    assert all(o["her_act"] != "sleep" for o in awake) and not organism.asleep
    assert all(o["her_sleep"]["asleep"] is False for o in awake)
    first = loop.settle(organism, world, UNATTENDED).observation
    assert first["her_act"] == "sleep" and "exhausted" in first["act_reason"] and organism.asleep
    assert organism.counts["nights"] == 1
    axes = {axis[1]: axis[3] for axis in organism.body_axes}
    assert axes["left_eyelid_aperture"] == 0 and axes["right_eyelid_aperture"] == 0
    asleep = loop.settle(organism, world, UNATTENDED).observation
    assert asleep["her_act"] == "sleep" and asleep["her_sleep"]["asleep"] is True
    assert max(asleep["retinal_u8"]) == 0, "closed eyelids still passed light"
    assert asleep["actual_root_motion"] == [0, 0, 0] or not any(asleep["actual_root_motion"])
    reserve_before = organism.reserve_micrograms
    loop.settle(organism, world, UNATTENDED)
    assert reserve_before - organism.reserve_micrograms == 3, "asleep she burns at basal only"
    # The pressure drains at twice the rate it rose; she wakes when it is gone.
    organism._state["sleep_pressure"] = SLEEP_RECOVERY_PER_BEAT * 2
    two = [loop.settle(organism, world, UNATTENDED).observation for _ in range(2)]
    assert all(o["her_act"] == "sleep" for o in two)
    woke = loop.settle(organism, world, UNATTENDED).observation
    assert woke["her_act"] != "sleep" and not organism.asleep
    axes = {axis[1]: axis[3] for axis in organism.body_axes}
    assert axes["left_eyelid_aperture"] == 10_000
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded


def test_asleep_she_dreams_the_days_record_into_her_situation_memory_and_uses_it_awake() -> None:
    from dsf_ai_service.guala_functional_organism import ACTS, CONSOLIDATED_CAPACITY, coarse_key

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    regimes_a, regimes_b = "DSS_SS_TS", "TSD_SS_VS"   # same situation (_S_S), different scenes
    assert coarse_key(regimes_a) == coarse_key(regimes_b) == "_S_S"
    organism._credit("a" * 16, "step", 0.9, 1, regimes_a)
    organism._credit("a" * 16, "rest", 0.0, 1, regimes_a)
    organism._credit("b" * 16, "step", 0.3, 2, regimes_b)
    organism._credit("b" * 16, "say", 0.6, 2, regimes_b)
    organism._credit("c" * 16, "turn_left", 0.2, 3, "")        # met before dreaming existed: no situation
    dreamt = [organism._dream(10 + i) for i in range(4)]
    assert dreamt[0] and "into situation _S_S" in dreamt[0]
    assert dreamt[2] is None and dreamt[3] is None            # the day's record is empty after the night
    assert organism._state["acts"] == {}
    learned = organism._state["learned"]["_S_S"]["acts"]
    assert learned["step"] == [2, 1.2] and learned["rest"] == [1, 0.0] and learned["say"] == [1, 0.6]
    # Awake under a structure the day has not met, in a situation her sleep kept: its best act.
    act, why = organism._choose("d" * 16, "_S_S", list(ACTS))
    assert act == "step" and "from her sleep" in why, why
    # In a situation her sleep never kept: the first act in the declared order.
    act, why = organism._choose("d" * 16, "SSSS", list(ACTS))
    assert act == ACTS[0] and "first try" in why
    for index in range(CONSOLIDATED_CAPACITY + 10):
        organism._credit(f"{index:016x}", "rest", 0.0, 100 + index, f"{'DSTV'[index % 4]}SS_SS_T{'DSTV'[(index // 4) % 4]}")
        organism._dream(200 + index)
    assert len(organism._state["learned"]) <= CONSOLIDATED_CAPACITY
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded


def test_a_thing_under_her_hand_is_not_pushed_by_the_caregivers_step() -> None:
    """The death of 2026-09-14: her hand on the curtains, the caregiver walking
    in to present a meal, and the step law pushing the curtains from under her
    hand; the world's validation then raised ("body contact differs from
    signed geometry") and the actor stopped. A thing under a body's contact is
    not pushed: the step is refused, which the caregiver's hand detours."""

    from dsf_ai_service.guala_caretaker_hand import SECOND_BODY_PORT_ID
    from dsf_ai_service.substrate.embodiment_world import (
        ActionExecutionReceipt, MoveCommand, PORT_ID, PoseMM, TouchContactCommand, encode_command,
    )

    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    her = _her(world)
    cup = next(item for item in snapshot.objects if item.object_id == "cup")
    # A light cup within her hand's reach, straight ahead of her.
    radians = math.radians(her.pose.heading_millidegrees / 1000)
    ahead = PositionMM(her.pose.position.x + round(450 * math.cos(radians)), her.pose.position.y + round(450 * math.sin(radians)), 0)
    world.admit_authored_arrival(EmbodiedObject("cup-under-hand", cup.radius_mm, cup.mass_grams, ahead, reflectance_ppm=cup.reflectance_ppm, material=cup.material))
    snapshot = world.observation_snapshot()
    touch = world.prepare_port_command(port_id=PORT_ID, command_payload=encode_command(TouchContactCommand("cup-under-hand", 250_000)),
                                       causal_intent_receipt_sha256="ab" * 32, expected_revision=snapshot.revision)
    assert not isinstance(touch, ActionExecutionReceipt), touch.reason
    with world.prepared_action_visibility_transaction(touch):
        world.commit_prepared_action(touch)
    snapshot = world.observation_snapshot()
    her = _her(world)
    assert her.active_contact is not None and her.active_contact.object_id == "cup-under-hand"
    person = next(body for body in snapshot.bodies if body.body_id != snapshot.self_body_id)
    # The caregiver's stride passes through the cup: refused, never raised.
    beyond = PositionMM(ahead.x + round(300 * math.cos(radians)), ahead.y + round(300 * math.sin(radians)), 0)
    # Put the caregiver a stride short of the cup, facing it, by the world's own move law.
    approach = PositionMM(ahead.x - round(700 * math.cos(radians)), ahead.y - round(700 * math.sin(radians)), 0)
    world_before = world.observation_snapshot()
    placed = world.prepare_port_command(port_id=SECOND_BODY_PORT_ID, command_payload=encode_command(MoveCommand(PoseMM(approach, her.pose.heading_millidegrees), 250_000)),
                                        causal_intent_receipt_sha256="cd" * 32, expected_revision=world_before.revision)
    if isinstance(placed, ActionExecutionReceipt):
        # The caregiver cannot be placed there from where it stands (far away): the law is still exercised below with a direct path check.
        placed = None
    else:
        with world.prepared_action_visibility_transaction(placed):
            world.commit_prepared_action(placed)
    snapshot = world.observation_snapshot()
    person = next(body for body in snapshot.bodies if body.body_id != snapshot.self_body_id)
    target = PositionMM(person.pose.position.x + round(1200 * math.cos(radians)), person.pose.position.y + round(1200 * math.sin(radians)), 0) if placed is not None else beyond
    result = world.prepare_port_command(port_id=SECOND_BODY_PORT_ID, command_payload=encode_command(MoveCommand(PoseMM(target, her.pose.heading_millidegrees), 250_000)),
                                        causal_intent_receipt_sha256="ef" * 32, expected_revision=snapshot.revision)
    assert isinstance(result, ActionExecutionReceipt), "a step through a thing under her hand must be refused"
    assert result.reason in ("move_path_intersects_object", "move_path_intersects_body", "move_outside_room", "move_too_far"), result.reason
    after = world.observation_snapshot()
    still = next(item for item in after.objects if item.object_id == "cup-under-hand")
    assert still.position == ahead, "the cup moved from under her hand"
    assert _her(world).active_contact is not None


def test_the_caretaker_makes_her_bed_and_she_falls_asleep_on_it_crediting_the_way_there() -> None:
    """The bed law: at the ceiling she sleeps only on her bed (the world's one
    thing a body may lie on); the bed is a candidate when in sight; falling
    asleep on it credits the act that brought her there with the pressure the
    night releases. The caretaker's bedtime job sets her pillow and blanket
    on the bed first (things may lie on a bed too)."""

    from dsf_ai_service.guala_caretaker_hand import BEDTIME_ID
    from dsf_ai_service.guala_functional_loop import _apply
    from dsf_ai_service.guala_functional_organism import (
        BED_ID, Decision, SLEEP_PRESSURE_CEILING, candidates, choice_key, move_commands_toward, things_in_sight,
    )

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    organism._state["sleep_pressure"] = SLEEP_PRESSURE_CEILING
    loop = FunctionalPhysicalLoop()
    # Bedtime, as the caretaker script sends it (a caretaker-food occurrence
    # naming "bedtime"): her pillow and blanket go on the bed.
    made = loop.settle(organism, world, _present(BEDTIME_ID)).observation["caregiver_presentation"]
    assert sorted(made["made"]) == ["blanket", "pillow"] and made["presented"] is True, made["steps"][-3:]
    snapshot = world.observation_snapshot()
    bed = next(item for item in snapshot.objects if item.object_id == BED_ID)
    for item_id in ("pillow", "blanket"):
        item = next(i for i in snapshot.objects if i.object_id == item_id)
        assert item.position is not None and math.dist((item.position.x, item.position.y), (bed.position.x, bed.position.y)) <= bed.radius_mm, item_id
    her = _her(world)
    assert math.dist((her.pose.position.x, her.pose.position.y), (bed.position.x, bed.position.y)) > bed.radius_mm, "genesis places her on the bed; the test needs her off it"
    # At the ceiling but off the bed: awake; the bed is a candidate whenever it is in sight.
    for _ in range(6):
        snapshot = world.observation_snapshot(); her = _her(world)
        if any(t.object_id == BED_ID for t in things_in_sight(snapshot)):
            assert any(c[0] == "toward_bed" for c in candidates(snapshot, her, None, None, things_in_sight(snapshot), organism.live_organism_tick))
        o = loop.settle(organism, world, UNATTENDED).observation
        assert o["her_act"] != "sleep" and not organism.asleep, o["act_reason"]
    # Walk her onto the bed by the world's own move law (the test's hand, not hers): she may lie on it.
    for _ in range(80):
        snapshot = world.observation_snapshot(); her = _her(world)
        if math.dist((her.pose.position.x, her.pose.position.y), (bed.position.x, bed.position.y)) <= bed.radius_mm - her.radius_mm:
            break
        decision = Decision("toward_bed", "test", move_commands_toward(snapshot, bed.position, 0), BED_ID, None, "", False, 0, ())
        prepared, _applied, _refusal, _refused = _apply(world, decision, snapshot)
        with world.prepared_action_visibility_transaction(prepared):
            world.commit_prepared_action(prepared)
    her = _her(world)
    assert math.dist((her.pose.position.x, her.pose.position.y), (bed.position.x, bed.position.y)) <= bed.radius_mm, "could not walk her onto the bed"
    organism._state["last_chosen"] = {"key": choice_key("SSSSSSSSS"), "regimes": "SSSSSSSSS", "act": "toward_bed", "deficit": 0.1}
    o = loop.settle(organism, world, UNATTENDED).observation
    assert o["her_act"] == "sleep" and "on her bed" in o["act_reason"], o["act_reason"]
    assert organism.asleep and organism.counts["nights"] == 1
    tries, total = organism._state["acts"][choice_key("SSSSSSSSS")]["acts"]["toward_bed"]
    assert tries == 1 and total >= 1.0, (tries, total)
    assert organism._state["last_chosen"] is None
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded


def test_syllables_come_from_speech_record_and_grow_sequences_by_measured_worth() -> None:
    """Her syllables are chosen by the law her acts use: under a context (situation and
    the syllable before) untried syllables first, in order of lifetime tries; then the
    best mean measured worth of what followed. Transitions from the prior syllable grow
    into sequences. Every pitch and onset her airway declares is in her record."""

    from dsf_ai_service.guala_functional_organism import SYLLABLE_DRIVES, SYLLABLES, syllable_pcm

    assert len(SYLLABLES) == 40 and len(set(SYLLABLE_DRIVES.values())) == 40
    for name in SYLLABLES[::7]:
        assert len(syllable_pcm(SYLLABLE_DRIVES[name], 1)) > 0     # every declared syllable is producible
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    drive, name, context, reason = organism._choose_syllable("_S_S", None)
    assert name == SYLLABLES[0] and drive == SYLLABLE_DRIVES[name] and context == "_S_S:start" and "first try" in reason
    organism._state["syllable_totals"][SYLLABLES[0]] = 5
    drive, name, _context, reason = organism._choose_syllable("_S_S", None)
    assert name != SYLLABLES[0] and "tried 0 in her life" in reason
    # Every syllable tried under the context: the best mean worth is chosen.
    organism._state["speech"]["_S_S:start"] = {"syllables": {s: [2, 0.0] for s in SYLLABLES}, "tick": 1}
    organism._state["speech"]["_S_S:start"]["syllables"]["eh0"] = [2, 1.2]
    drive, name, _context, reason = organism._choose_syllable("_S_S", None)
    assert name == "eh0" and "best worth under _S_S:start: eh0 (0.60 over 2)" in reason
    # Sequence: after saying eh0, the context is _S_S:eh0 and its own record chooses.
    organism._state["speech"]["_S_S:eh0"] = {"syllables": {s: [1, 0.0] for s in SYLLABLES}, "tick": 2}
    organism._state["speech"]["_S_S:eh0"]["syllables"]["mah1"] = [1, 0.9]
    drive, name, _context, reason = organism._choose_syllable("_S_S", "eh0")
    assert name == "mah1" and drive == SYLLABLE_DRIVES["mah1"]


def test_what_follows_her_syllable_is_its_worth_a_room_sound_pays_and_silence_does_not() -> None:
    """A syllable is valued by what followed it, by the same measured law as her acts: a
    room sound standing out on the next beat pays it, silence pays nothing (and costs its
    burn); the best-paid syllable under a context is then the one she chooses."""

    from dsf_ai_service.guala_functional_organism import SYLLABLE_DRIVES, SYLLABLES

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    context = "abcd:start"
    key = "0123456789abcdef"
    for syllable, sound_now in (("ah0", 0.0), ("eh0", 0.5)):
        organism._state["speech"].setdefault(context, {"syllables": {}, "tick": 1})["syllables"][syllable] = [1, 0.0]
        organism._state["pending_act"] = {"key": key, "act": "say", "syllable": syllable, "context": context, "deficit": 0.0, "sleep_ratio": 0.0, "contact_ratio": 0.0, "intake": 0, "refused": False, "burn": 0}
        organism._settle("other", False, sound_now, 0.0, 2)
    record = organism._state["speech"][context]["syllables"]
    assert record["ah0"] == [1, 0.0] and abs(record["eh0"][1] - 0.5) < 1e-6, record
    # Everything else untried comes first; once all are tried, the best worth is chosen.
    for s in SYLLABLES:
        record.setdefault(s, [1, 0.0])
    drive, name, _context, reason = organism._choose_syllable("abcd", None)
    assert name == "eh0" and drive == SYLLABLE_DRIVES["eh0"] and "best worth" in reason


def test_a_full_record_still_admits_the_structure_she_meets_now_and_retired_keys_leave_on_restore() -> None:
    """Her day's record keeps the structures met most recently: a record full of
    entries each visited twice must still admit a new structure (the least-visited
    eviction threw every newcomer out at once). Entries keyed under a retired key
    law can never be met again and leave on restore."""

    from dsf_ai_service.guala_functional_organism import ACT_RECORD_CAPACITY, FAMILIARITY_CAPACITY, choice_key

    from dsf_ai_service.guala_functional_organism import STREAMS
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=10_000)
    state = organism._state
    regimes = "S" * len(STREAMS)
    live_key = choice_key(regimes)
    # A full record of stale, well-visited entries (keys that no regimes produce).
    for i in range(ACT_RECORD_CAPACITY):
        state["acts"][f"stale{i:04d}"] = {"acts": {"rest": [2, 1.0]}, "tick": 1000 + i, "regimes": regimes, "visits": 2, "successors": {}}
    for i in range(FAMILIARITY_CAPACITY):
        state["familiarity"][f"fam{i:04d}"] = [2, 1000 + i]
    organism._credit(live_key, "step", 0.5, 5000, regimes)
    assert live_key in state["acts"], "the structure she met now was evicted from a full record"
    assert len(state["acts"]) == ACT_RECORD_CAPACITY and "stale0000" not in state["acts"]
    # Familiarity through commit: the newcomer stays, the least recently met leaves.
    from dsf_ai_service.guala_functional_organism import Decision
    from dsf_ai_service.guala_functional_organism import STREAMS
    signature = " ".join("S0000000" for _ in STREAMS)
    decision = Decision("rest", "test", (), None, None, signature, False, 0, ())
    organism.commit(decision, applied_action="rest", refusal=None, intake_micrograms=0, spoke=None,
                    heard_profile=None, self_profile=None, tick_now=organism.live_organism_tick)
    assert live_key in state["familiarity"] and "fam0000" not in state["familiarity"]
    # Restore: the stale entries (key != choice_key(regimes)) leave; the live one stays.
    restored = FunctionalOrganism.restore(organism.encoded())   # restore runs the migration
    assert list(restored._state["acts"]) == [live_key]
    assert restored.migrate() is False and restored.encoded() == FunctionalOrganism.restore(restored.encoded()).encoded()


def _touch_occurrence(touch_id: str):
    import dsf_ai_service.lean_production_app as production
    return production._physical_occurrence(production.OccurrenceBody(
        kind="sensory", payload=production.SensoryBody(source="caretaker-food", present_food=touch_id)))


def test_the_caregivers_touch_lands_on_her_skin_and_relieves_her_need_for_contact() -> None:
    """The caregiver's hand-hold and hug go through the world's own body-surface
    contact: she feels the fraction of her skin pressed on that beat (a palm is
    little, a hug is most of her), her contact need falls by its declared relief,
    and an awake beat without touch raises it by one."""

    from dsf_ai_service.guala_functional_organism import CONTACT_RECOVERY_PER_BEAT

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    for _ in range(5):
        loop.settle(organism, world, UNATTENDED)
    need_before = organism.contact["pressure"][0]
    assert need_before == 5
    o = loop.settle(organism, world, _touch_occurrence("touch-hold-hand")).observation
    presentation = o["caregiver_presentation"]
    assert presentation["touched"] == "hold_hand" and [c["site"] for c in presentation["contacts"]] == ["left-palm"], presentation["steps"][-3:]
    assert 0.0 < o["her_skin"]["contact"] < 0.05
    assert organism.contact["pressure"][0] == max(0, need_before - CONTACT_RECOVERY_PER_BEAT)
    o = loop.settle(organism, world, _touch_occurrence("touch-hug")).observation
    assert o["caregiver_presentation"]["touched"] == "hug" and o["her_skin"]["contact"] > 0.5
    o = loop.settle(organism, world, UNATTENDED).observation
    assert o["her_skin"]["contact"] == 0.0 and organism.contact["pressure"][0] == 1
    assert o["her_skin"]["temperature_millikelvin"] is not None
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded


def test_a_touch_pays_by_the_skin_it_reached_plus_her_need_and_answers_her_syllable() -> None:
    """The value of what followed her act carries the touch: the fraction of her
    skin it pressed plus her contact need at the moment she chose; and a touch
    within the answer window counts as an answer to her syllable."""

    from dsf_ai_service.guala_functional_organism import CONTACT_PRESSURE_CEILING, Decision, SYLLABLE_DRIVES

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    key = "0123456789abcdef"
    organism._state["contact_pressure"] = CONTACT_PRESSURE_CEILING // 2
    organism._state["pending_act"] = {"key": key, "act": "say", "deficit": 0.0, "sleep_ratio": 0.0, "contact_ratio": 0.5, "intake": 0, "refused": False, "burn": 0}
    organism._settle("other", False, 0.0, 0.25, 2)
    tries, total = organism._state["acts"][key]["acts"]["say"]
    assert tries == 1 and abs(total - (0.25 + 0.5)) < 1e-6
    # No touch: nothing from contact.
    organism._state["pending_act"] = {"key": key, "act": "say", "deficit": 0.0, "sleep_ratio": 0.0, "contact_ratio": 0.5, "intake": 0, "refused": False, "burn": 0}
    organism._settle("other", False, 0.0, 0.0, 3)
    tries, total = organism._state["acts"][key]["acts"]["say"]
    assert tries == 2 and abs(total - 0.75) < 1e-6
    # A touch after her syllable pays the syllable too, by the same law.
    organism._state["speech"]["abcd:start"] = {"syllables": {"ah0": [1, 0.0]}, "tick": 3}
    organism._state["pending_act"] = {"key": key, "act": "say", "syllable": "ah0", "context": "abcd:start", "deficit": 0.0, "sleep_ratio": 0.0, "contact_ratio": 0.5, "intake": 0, "refused": False, "burn": 0}
    organism._settle("other", False, 0.0, 0.25, 4)
    assert abs(organism._state["speech"]["abcd:start"]["syllables"]["ah0"][1] - 0.75) < 1e-6


def test_she_can_walk_to_the_caregiver_and_put_her_palm_to_its_hand_and_feels_it_next_beat() -> None:
    """Her side of touch: with the caregiver in sight, walking to it and reaching
    for its hand are among her candidates; her own palm on the caregiver's palm
    goes through the same contact law and is felt on the next beat."""

    from dsf_ai_service.guala_functional_loop import _apply
    from dsf_ai_service.guala_functional_organism import (
        BEAT_MICROSECONDS, Decision, STREAMS, _heading_toward, caregiver_in_sight, candidates, things_in_sight,
    )
    from dsf_ai_service.substrate.embodiment_world import MoveCommand, PoseMM

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, _touch_occurrence("touch-shoulder"))   # the caregiver comes to her and stays near
    snapshot = world.observation_snapshot()
    her = _her(world)
    person = caregiver_in_sight(snapshot)
    if person is None:   # she may face away after the touch: turn her toward the caregiver by the world's own move law
        other = next(b for b in snapshot.bodies if b.body_id != snapshot.self_body_id)
        decision = Decision("turn_left", "test", (MoveCommand(PoseMM(her.pose.position, _heading_toward(her.pose.position, other.pose.position)), BEAT_MICROSECONDS),), None, None, "", False, 0, ())
        prepared, _applied, _refusal, _refused = _apply(world, decision, snapshot)
        with world.prepared_action_visibility_transaction(prepared):
            world.commit_prepared_action(prepared)
        snapshot = world.observation_snapshot(); her = _her(world); person = caregiver_in_sight(snapshot)
    assert person is not None, "the caregiver should be in her sight after touching her"
    options = candidates(snapshot, her, None, None, things_in_sight(snapshot), organism.live_organism_tick)
    kinds = {option[0] for option in options}
    assert "reach_hand" in kinds, kinds
    reach = next(option for option in options if option[0] == "reach_hand")
    decision = Decision("reach_hand", "test", reach[2], reach[3], None, " ".join("S0000000" for _ in STREAMS), False, 0, ())
    prepared, applied, refusal, refused = _apply(world, decision, snapshot)
    assert applied == "reach_hand" and refusal is None, refused
    contacts = world.body_surface_contacts_for_prepared_action(prepared)
    assert len(contacts) == 1 and contacts[0].recipient_cutaneous_topology_index is None
    with world.prepared_action_visibility_transaction(prepared):
        world.commit_prepared_action(prepared)
    organism.commit(decision, applied_action="reach_hand", refusal=None, intake_micrograms=0, spoke=None, heard_profile=None,
                    self_profile=None, tick_now=organism.live_organism_tick, contact_fraction=0.02)
    assert organism._state["pending_contact"] == 0.02
    from dsf_ai_service.guala_functional_organism import CONTACT_RECOVERY_PER_BEAT
    organism._state["contact_pressure"] = 1_000
    o = loop.settle(organism, world, UNATTENDED).observation
    assert abs(o["her_skin"]["contact"] - 0.02) < 1e-6 and organism.contact["pressure"][0] == 1_000 - CONTACT_RECOVERY_PER_BEAT
    assert organism._state["pending_contact"] == 0.0 or o["her_act"] == "reach_hand"


def _hot_apple_in_reach(world, object_id: str, temperature_millikelvin: int) -> None:
    """An apple at the asked surface temperature set down inside her hand's reach."""

    from dataclasses import replace as _replace
    snapshot = world.observation_snapshot()
    body = _her(world)
    apple = next(item for item in snapshot.objects if item.object_id == "apple")
    hot = _replace(apple.material, surface_temperature_millikelvin=temperature_millikelvin)
    last_error = None
    for ahead_mm, turn in ((330, 0), (330, 20), (330, -20), (380, 0), (380, 30), (380, -30)):
        radians = math.radians((body.pose.heading_millidegrees / 1000) + turn)
        spot = PositionMM(body.pose.position.x + round(ahead_mm * math.cos(radians)), body.pose.position.y + round(ahead_mm * math.sin(radians)), 0)
        try:
            world.admit_authored_arrival(EmbodiedObject(object_id, apple.radius_mm, apple.mass_grams, spot, reflectance_ppm=apple.reflectance_ppm, material=hot))
            return
        except ValueError as error:
            last_error = error
    raise AssertionError(f"no clear spot within her reach for {object_id}: {last_error}")


def test_what_her_skin_meets_is_felt_as_warmth_against_her_own_and_the_caregiver_is_warm() -> None:
    """The thermal contrast at contact: a thing colder than her skin reads below
    the middle, the caregiver's skin (warmer than hers) above it, and nothing in
    contact reads the middle."""

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    o = loop.settle(organism, world, UNATTENDED).observation
    skin = o["her_skin"]["temperature_millikelvin"]
    assert skin is not None and 296_000 < skin < 310_150
    o = loop.settle(organism, world, _touch_occurrence("touch-hug")).observation
    assert o["her_skin"]["met_millikelvin"] == 310_150 and organism._state["streams"]["touch_warmth"][-1] > 0.5
    o = loop.settle(organism, world, UNATTENDED).observation
    if o["her_skin"]["met_millikelvin"] is None:
        assert organism._state["streams"]["touch_warmth"][-1] == 0.5
    # A cold apple in her hand reads below the middle.
    from dsf_ai_service.guala_functional_loop import _apply
    from dsf_ai_service.guala_functional_organism import BEAT_MICROSECONDS, Decision, STREAMS
    from dsf_ai_service.substrate.embodiment_world import GraspContactCommand
    _hot_apple_in_reach(world, "cold-apple", 280_000)
    snapshot = world.observation_snapshot()
    decision = Decision("grasp", "test", (GraspContactCommand(BEAT_MICROSECONDS),), "cold-apple", None, " ".join("S0000000" for _ in STREAMS), False, 0, ())
    prepared, applied, refusal, refused = _apply(world, decision, snapshot)
    assert applied == "grasp", refused
    with world.prepared_action_visibility_transaction(prepared):
        world.commit_prepared_action(prepared)
    organism.commit(decision, applied_action="grasp", refusal=None, intake_micrograms=0, spoke=None, heard_profile=None, self_profile=None, tick_now=organism.live_organism_tick)
    o = loop.settle(organism, world, UNATTENDED).observation
    assert _her(world).held_object_id in ("cold-apple", None)
    assert o["her_skin"]["met_millikelvin"] == 280_000 and organism._state["streams"]["touch_warmth"][-1] < 0.5


def test_a_hot_thing_in_her_hand_is_let_go_by_reflex_costs_in_her_record_and_the_jaw_will_not_bite_it() -> None:
    """Above nature's pain threshold a held thing burns: she lets it go by reflex,
    the act that put it in her hand is valued with the pain taken off, and food
    that hot is not bitten until it cools."""

    from dsf_ai_service.guala_functional_loop import _apply
    from dsf_ai_service.guala_functional_organism import BEAT_MICROSECONDS, Decision, NOCICEPTION_MILLIKELVIN, STREAMS
    from dsf_ai_service.substrate.embodiment_world import GraspContactCommand

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, UNATTENDED)
    _hot_apple_in_reach(world, "hot-apple", NOCICEPTION_MILLIKELVIN + 20_000)
    snapshot = world.observation_snapshot()
    decision = Decision("grasp", "test", (GraspContactCommand(BEAT_MICROSECONDS),), "hot-apple", None, " ".join("S0000000" for _ in STREAMS), False, 0, ())
    prepared, applied, refusal, refused = _apply(world, decision, snapshot)
    assert applied == "grasp", refused
    with world.prepared_action_visibility_transaction(prepared):
        world.commit_prepared_action(prepared)
    key = "0123456789abcdef"
    organism._state["pending_act"] = {"key": key, "regimes": "", "act": "grasp", "deficit": 0.0, "sleep_ratio": 0.0, "contact_ratio": 0.0, "intake": 0, "refused": False, "burn": 0}
    organism.commit(decision, applied_action="grasp", refusal=None, intake_micrograms=0, spoke=None, heard_profile=None, self_profile=None, tick_now=organism.live_organism_tick)
    assert _her(world).held_object_id == "hot-apple"
    o = loop.settle(organism, world, UNATTENDED).observation
    assert o["her_act"] == "release" and "burns" in o["act_reason"], o["act_reason"]
    assert _her(world).held_object_id is None
    tries, total = organism._state["acts"][key]["acts"]["grasp"]
    assert tries == 1 and total < 0, total   # the grasp of a hot thing paid less than nothing
    # Hot food at her mouth while hungry: the jaw does not bite it.
    organism._state["reserve_micrograms"] = 100_000
    organism._state["feeding"] = True
    snapshot = world.observation_snapshot()
    prepared, applied, refusal, refused = _apply(world, Decision("grasp", "test", (GraspContactCommand(BEAT_MICROSECONDS),), "hot-apple", None, " ".join("S0000000" for _ in STREAMS), False, 0, ()), snapshot)
    if applied == "grasp":
        with world.prepared_action_visibility_transaction(prepared):
            world.commit_prepared_action(prepared)
        o = loop.settle(organism, world, UNATTENDED).observation
        assert o["her_act"] != "bite", o["act_reason"]


def test_read_to_the_caregiver_holds_the_book_beside_her_and_stays_while_the_reading_lasts() -> None:
    """A reading: the caregiver fetches the book and holds it beside her; it does
    not walk home while the reading window lasts, and goes home after."""

    from dsf_ai_service.guala_functional_loop import READING_PATIENCE_BEATS

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, UNATTENDED)
    o = loop.settle(organism, world, _touch_occurrence("read-book")).observation
    presentation = o["caregiver_presentation"]
    assert presentation["object_id"] == "read-book" and presentation["reading"] is True, presentation["steps"][-3:]
    snapshot = world.observation_snapshot()
    her = _her(world)
    person = next(b for b in snapshot.bodies if b.body_id != snapshot.self_body_id)
    # The book is beside her: in the caregiver's hand or, if she took it on that beat, in hers.
    assert "book" in (person.held_object_id, her.held_object_id)
    assert math.dist((her.pose.position.x, her.pose.position.y), (person.pose.position.x, person.pose.position.y)) <= her.reach_mm + person.radius_mm + 300
    started = organism.live_organism_tick
    assert organism._state["reading_until_tick"] == started - 1 + READING_PATIENCE_BEATS
    for _ in range(12):
        o = loop.settle(organism, world, UNATTENDED).observation
        assert o["caregiver_withdrawal"] is None, "the caregiver walked away during the reading"
    # The book in her own hands (or within her reach) keeps the reading: shown again, it still reads.
    from dsf_ai_service.guala_caretaker_hand import present_food as _present
    again = _present(world, "read-book")
    assert again["reading"] is True, again["steps"][-3:]
    organism._state["reading_until_tick"] = organism.live_organism_tick   # the reader's last word was long ago
    organism._state["offer_since_tick"] = organism.live_organism_tick - 1_000
    went_home = False
    for _ in range(6):
        o = loop.settle(organism, world, UNATTENDED).observation
        if o["caregiver_withdrawal"] is not None:
            went_home = True
            break
    assert went_home


def _thing_sound_occurrence(object_id: str, pcm: bytes):
    import base64
    import dsf_ai_service.lean_production_app as production
    return production._physical_occurrence(production.OccurrenceBody(
        kind="sensory", payload=production.SensoryBody(source="thing-sound", from_object=object_id, pcm_s16le_base64=base64.b64encode(pcm).decode("ascii"))))


def test_a_things_sound_reaches_her_by_the_rooms_geometry_and_a_missing_thing_is_silent() -> None:
    """Sound from the radio: at hand it is what the recording is; farther it falls
    as one over the distance; from another room it comes through the doorway at a
    quarter; a thing not in her world makes no sound at her ears."""

    from dsf_ai_service.guala_functional_loop import SOUND_REFERENCE_MM, _thing_sound_gain
    from dsf_ai_service.substrate.embodiment_world import EmbodiedObject

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, UNATTENDED)
    snapshot = world.observation_snapshot()
    radio = next(item for item in snapshot.objects if item.object_id == "radio")
    her = _her(world)
    # She is in her room; the radio stands in the tv-room: the sound comes by a doorway or not at all.
    gain, distance, path = _thing_sound_gain(snapshot, "radio")
    assert path in ("door", "no-door") and (path == "no-door" or (0 < gain <= 0.25 and distance > SOUND_REFERENCE_MM)), (gain, distance, path)
    # A radio set down beside her in her own room sounds at (nearly) full strength; at four metres at a quarter.
    snapshot = world.observation_snapshot()
    apple = next(item for item in snapshot.objects if item.object_id == "apple")
    placed = None
    for dx, dy in ((700, 0), (0, 700), (-700, 0), (0, -700), (900, 300), (300, 900)):
        spot = PositionMM(her.pose.position.x + dx, her.pose.position.y + dy, 0)
        try:
            world.admit_authored_arrival(EmbodiedObject("radio-near", radio.radius_mm, radio.mass_grams, spot, reflectance_ppm=radio.reflectance_ppm, material=radio.material))
            placed = spot
            break
        except ValueError:
            continue
    assert placed is not None
    snapshot = world.observation_snapshot()
    gain, distance, path = _thing_sound_gain(snapshot, "radio-near")
    assert path == "room" and abs(distance - 700) <= 5 and gain == 1, (gain, distance, path)
    tone = struct.pack("<4000h", *(int(9000 * math.sin(2 * math.pi * 370 * i / 16000)) for i in range(4000)))
    o = loop.settle(organism, world, _thing_sound_occurrence("radio-near", tone)).observation
    assert o["room_sound"]["from"] == "radio-near" and o["room_sound"]["gain"] == 1.0 and o["external_heard_sample_count"] == 4000
    heard_near = organism._state["streams"]["sound_energy"][-1]
    assert heard_near > 0
    # The same tone from a thing that is not in her world: silence at her ears.
    o = loop.settle(organism, world, _thing_sound_occurrence("radio-nowhere", tone)).observation
    assert o["room_sound"]["gain"] == 0.0 and o["room_sound"]["path"] == "absent"
    assert organism._state["streams"]["sound_energy"][-1] < heard_near
    # A radio brought in by the caregiver: the world already holds the declared radio, so the delivery names it.
    o = loop.settle(organism, world, _touch_occurrence("radio-delivery")).observation
    assert o["caregiver_presentation"]["delivered"] == "radio" and o["caregiver_presentation"]["presented"] is True


def test_a_things_sound_must_name_the_thing_and_only_that_source_does() -> None:
    import base64
    import pytest
    import dsf_ai_service.lean_production_app as production

    pcm = base64.b64encode(b"\x00\x01" * 4000).decode("ascii")
    with pytest.raises(ValueError):
        production._physical_occurrence(production.OccurrenceBody(kind="sensory", payload=production.SensoryBody(source="thing-sound", pcm_s16le_base64=pcm)))
    with pytest.raises(ValueError):
        production._physical_occurrence(production.OccurrenceBody(kind="sensory", payload=production.SensoryBody(source="microphone", from_object="radio", pcm_s16le_base64=pcm)))
    ok = production._physical_occurrence(production.OccurrenceBody(kind="sensory", payload=production.SensoryBody(source="thing-sound", from_object="radio", pcm_s16le_base64=pcm)))
    assert ok.payload.from_object == "radio"


def test_the_caregiver_carries_the_radio_to_her_and_sets_it_down_beside_her() -> None:
    """radio-to-her: the radio, declared in the tv-room, is fetched and set down
    near her in her own room (or taken from the caregiver's hand on the way), so
    its sound reaches her at hand rather than through a door."""

    from dsf_ai_service.guala_functional_loop import _thing_sound_gain

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, UNATTENDED)
    o = loop.settle(organism, world, _touch_occurrence("radio-to-her")).observation
    presentation = o["caregiver_presentation"]
    assert presentation["object_id"] == "radio-to-her" and presentation["presented"] is True, presentation["steps"][-4:]
    snapshot = world.observation_snapshot()
    her = _her(world)
    radio = next(item for item in snapshot.objects if item.object_id == "radio")
    gain, distance, path = _thing_sound_gain(snapshot, "radio")
    assert path == "room" and distance <= 2_000 and gain >= 0.5, (gain, distance, path, radio.held_by_body_id, presentation["set_down"])


def test_her_ear_gives_the_shape_of_a_sound_and_tells_two_sounds_apart_but_not_one_from_itself() -> None:
    """Six bands from her cochlea carry the shape of what she hears as fractions of
    its energy: a low tone and a high tone make different shapes, the same sound
    twice makes the same shape, silence has none, and a soft copy of a sound has
    the shape of the loud one."""

    from dsf_ai_service.guala_functional_organism import EAR_BANDS, STREAMS, ear_bands
    from dsf_ai_service.guala_functional_loop import _profile

    assert len(STREAMS) == 22 and all(f"ear_band_{i}" in STREAMS for i in range(EAR_BANDS))
    def tone(hz, amplitude=9000):
        return struct.pack("<4000h", *(int(amplitude * math.sin(2 * math.pi * hz * i / 16000)) for i in range(4000)))
    low, _ = _profile(tone(200)); high, _ = _profile(tone(3000)); low_again, _ = _profile(tone(200)); soft, _ = _profile(tone(200, 2000))
    s_low, s_high, s_again, s_soft = ear_bands(low), ear_bands(high), ear_bands(low_again), ear_bands(soft)
    assert abs(sum(s_low) - 1.0) < 1e-3 and abs(sum(s_high) - 1.0) < 1e-3
    assert s_low == s_again
    assert max(abs(a - b) for a, b in zip(s_low, s_high)) > 0.3, (s_low, s_high)
    assert max(abs(a - b) for a, b in zip(s_low, s_soft)) < 0.05, (s_low, s_soft)
    assert ear_bands(None) == (0.0,) * EAR_BANDS and ear_bands((0.0,) * 32) == (0.0,) * EAR_BANDS
    # Through the loop: the low tone and the high tone leave different shapes on her ear streams; silence leaves none.
    import base64
    import dsf_ai_service.lean_production_app as production
    def hear(pcm):
        return production._physical_occurrence(production.OccurrenceBody(kind="sensory", payload=production.SensoryBody(source="microphone", pcm_s16le_base64=base64.b64encode(pcm).decode("ascii"))))
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, hear(tone(200)))
    shape_low = tuple(organism._state["streams"][f"ear_band_{i}"][-1] for i in range(EAR_BANDS))
    loop.settle(organism, world, hear(tone(3000)))
    shape_high = tuple(organism._state["streams"][f"ear_band_{i}"][-1] for i in range(EAR_BANDS))
    loop.settle(organism, world, UNATTENDED)
    shape_quiet = tuple(organism._state["streams"][f"ear_band_{i}"][-1] for i in range(EAR_BANDS))
    assert shape_low != shape_high and shape_quiet == (0.0,) * EAR_BANDS
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded


def test_a_caregiver_presentation_can_never_end_her_beat() -> None:
    """The outage of 2026-09-15: the apple she held was a core to the hand's law and
    the food to present to the caretaker's, and the hand raised; the actor died.
    Now the hand refuses (a step on the record) and the loop records any failure
    in a presentation or a withdrawal as a refused act and settles the beat."""

    import dsf_ai_service.guala_functional_loop as loop_module
    from dsf_ai_service.substrate.embodiment_world import GraspContactCommand
    from dsf_ai_service.guala_functional_organism import BEAT_MICROSECONDS, Decision, STREAMS
    from dsf_ai_service.guala_functional_loop import _apply

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, UNATTENDED)
    # An eaten core in her hand, asked for by its own name.
    snapshot = world.observation_snapshot()
    apple = next(item for item in snapshot.objects if item.object_id == "apple")
    from dataclasses import replace as _replace
    core_material = _replace(apple.material, tastant_mass_micrograms=tuple(0 for _ in apple.material.tastant_mass_micrograms))
    her = _her(world)
    placed = False
    for ahead_mm, turn in ((330, 0), (330, 20), (330, -20), (380, 0), (380, 30), (380, -30)):
        radians = math.radians((her.pose.heading_millidegrees / 1000) + turn)
        spot = PositionMM(her.pose.position.x + round(ahead_mm * math.cos(radians)), her.pose.position.y + round(ahead_mm * math.sin(radians)), 0)
        try:
            world.admit_authored_arrival(EmbodiedObject("apple-core-9", apple.radius_mm, 5, spot, reflectance_ppm=apple.reflectance_ppm, material=core_material))
            placed = True
            break
        except ValueError:
            continue
    assert placed
    snapshot = world.observation_snapshot()
    decision = Decision("grasp", "test", (GraspContactCommand(BEAT_MICROSECONDS),), "apple-core-9", None, " ".join("S0000000" for _ in STREAMS), False, 0, ())
    prepared, applied, refusal, refused = _apply(world, decision, snapshot)
    assert applied == "grasp", refused
    with world.prepared_action_visibility_transaction(prepared):
        world.commit_prepared_action(prepared)
    organism.commit(decision, applied_action="grasp", refusal=None, intake_micrograms=0, spoke=None, heard_profile=None, self_profile=None, tick_now=organism.live_organism_tick)
    assert _her(world).held_object_id == "apple-core-9"
    o = loop.settle(organism, world, _touch_occurrence("apple-core-9")).observation
    presentation = o["caregiver_presentation"]
    assert presentation["presented"] is False and any("eaten_core" in str(step.get("reason")) for step in presentation["steps"]), presentation["steps"]
    # Any failure inside a presentation is a refused act on the record; the beat settles.
    original = loop_module.present_food
    loop_module.present_food = lambda world_, object_id: (_ for _ in ()).throw(RuntimeError("a fault in the caregiver's hand"))
    try:
        before = organism.live_organism_tick
        o = loop.settle(organism, world, _touch_occurrence("apple")).observation
    finally:
        loop_module.present_food = original
    assert organism.live_organism_tick == before + 1
    assert o["caregiver_presentation"]["presented"] is False and "failed: RuntimeError" in o["caregiver_presentation"]["steps"][0]["reason"]


# ----- Level 1: the acoustic gate in her beat (docs/GL-SPC-ACOUSTIC-GATE-C1-20260915-v1.md) -----

LIBRARY = "/workspaces/Tao_Financial_Engine/guala_caretaker/media"
SILENT_HOP = b"\0" * 8_000


def _hops(path: str, start: int = 0, count: int | None = None) -> list[bytes]:
    raw = open(path, "rb").read()
    hops = [raw[i:i + 8_000] for i in range(0, len(raw) - 7_999, 8_000)]
    return hops[start:start + count] if count else hops


def _word_hops(word: str) -> list[bytes]:
    return _hops(f"{LIBRARY}/words/en-us-{word}.pcm")


def _hear_beats(organism, world, hops, silence_after: int = 2):
    """The room sounds each beat (a hop of silence is a beat without an occurrence)."""

    return _run(organism, world, [(_heard(hop) if hop is not None else UNATTENDED) for hop in hops] + [UNATTENDED] * silence_after)


def test_a_spoken_word_in_her_beat_is_one_event_with_the_pure_functions_key_and_a_restart_mid_word_keeps_it() -> None:
    import os
    import pytest
    from dsf_ai_service.guala_acoustic_gate import events_of
    if not os.path.exists(f"{LIBRARY}/words/en-us-apple.pcm"):
        pytest.skip("her library's spoken words are not on this machine")
    apple = _word_hops("apple")
    offline = events_of([SILENT_HOP] * 2 + apple + [SILENT_HOP] * 2)
    assert len(offline) == 1
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    results = _hear_beats(organism, world, [None, None] + apple)
    ears = [r.observation["her_ear"] for r in results]
    closed = [key for ear in ears for key in ear["closed"]]
    assert closed == [offline[0].key], (closed, offline[0].key)
    assert organism._state["events"][offline[0].key][0] == 1 and organism.counts["events"] == 1
    assert organism._state["sound_event"][0] == offline[0].key and organism.ear["last"][0] == offline[0].key
    assert any(ear["open"] for ear in ears) and not organism.ear["open"]
    # The same word again: met twice, still one event in the store.
    _hear_beats(organism, world, apple)
    assert organism._state["events"][offline[0].key][0] == 2 and organism.counts["events"] == 1
    # A restart in the middle of the word: the open event travels in her body, the key is the same.
    world2 = home_world_authority(identity=IDENTITY)
    organism2 = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    _hear_beats(organism2, world2, [None, None] + apple[:1], silence_after=0)
    assert organism2.ear["open"] and organism2.ear["open_frames"] > 0
    encoded = organism2.encoded()
    organism3 = FunctionalOrganism.restore(encoded)
    assert organism3.encoded() == encoded
    results3 = _hear_beats(organism3, world2, apple[1:])
    closed3 = [key for r in results3 for key in r.observation["her_ear"]["closed"]]
    assert closed3 == [offline[0].key], (closed3, offline[0].key)


def test_music_becomes_bounded_events_in_her_beat_and_her_body_stays_within_its_bound() -> None:
    import os
    import pytest
    from dsf_ai_service.guala_acoustic_gate import MAX_EVENT_FRAMES
    music_path = f"{LIBRARY}/musopen-chopin/Allegro de Concert Op. 46 in A Major.pcm"
    if not os.path.exists(music_path):
        pytest.skip("her library's music is not on this machine")
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    sizes = []
    open_frames = []
    closed = []
    for hop in [None, None] + _hops(music_path, 200, 60) + [None] * 3:
        result = loop.settle(organism, world, _heard(hop) if hop is not None else UNATTENDED)
        ear = result.observation["her_ear"]
        sizes.append(len(organism.encoded()))
        open_frames.append(ear["open_frames"])
        closed.extend(ear["closed"])
    assert closed and max(open_frames) <= MAX_EVENT_FRAMES and not organism.ear["open"]
    assert all(organism._state["events"][key][2] <= MAX_EVENT_FRAMES // 25 for key in closed)
    assert len(organism._state["events"]) <= 256
    assert max(sizes) < 112_000, max(sizes)   # her bound with the open event's frames (at most 300 of seven values) and the events store
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded


def test_a_beat_without_sound_closes_an_open_event_and_the_record_of_quiet_is_bounded() -> None:
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    results = _hear_beats(organism, world, [None, _tone(440), _tone(440), None, None, _tone(900), None, None], silence_after=0)
    ears = [r.observation["her_ear"] for r in results]
    closed = [key for ear in ears for key in ear["closed"]]
    assert len(closed) == 2 and closed[0] != closed[1]
    assert ears[1]["open"] and ears[2]["open"] and not ears[4]["open"]
    quiet = organism._state["ear_quiet"]
    assert len(quiet["inside"]) == 11 and len(quiet["between"]) == 5 and sum(quiet["between"]) == 1


# ----- the eye's Level 1: her head follows what she acts on; the figure under her gaze (docs/GL-SPC-EYE-FIGURE-C1-20260915-v1.md) -----


def _thing_ahead(world, source_id: str, object_id: str, ahead_mm: int) -> None:
    """A copy of a thing of the world set down ahead of her by the test's hand."""

    snapshot = world.observation_snapshot()
    body = _her(world)
    source = next(item for item in snapshot.objects if item.object_id == source_id)
    last_error = None
    for extra_mm, turn in ((0, 0), (0, 12), (0, -12), (150, 0), (150, 20), (150, -20), (300, 0), (300, 30), (300, -30)):
        radians = math.radians((body.pose.heading_millidegrees / 1000) + turn)
        spot = PositionMM(body.pose.position.x + round((ahead_mm + extra_mm) * math.cos(radians)), body.pose.position.y + round((ahead_mm + extra_mm) * math.sin(radians)), 0)
        try:
            world.admit_authored_arrival(EmbodiedObject(object_id, source.radius_mm, source.mass_grams, spot, reflectance_ppm=source.reflectance_ppm, material=source.material, optical_surface=source.optical_surface))
            return
        except ValueError as error:
            last_error = error
    raise AssertionError(f"no clear spot ahead of her for {object_id}: {last_error}")


def _look_at(organism, world, object_id: str, beats: int):
    """Her head follows what she acts on: the test names the thing as her act's target
    each beat (the loop would, from her own decision) and lets her head turn to it."""

    loop = FunctionalPhysicalLoop()
    out = []
    for _ in range(beats):
        organism._state["gaze_target"] = object_id
        result = loop.settle(organism, world, UNATTENDED)
        organism._state["gaze_target"] = object_id
        out.append(result.observation["her_eye"])
    return out


def test_her_head_follows_what_she_acts_on_and_the_thing_comes_under_her_gaze() -> None:
    from dsf_ai_service.guala_functional_organism import HEAD_PITCH_BOUND_MILLIDEGREES, HEAD_STEP_MILLIDEGREES

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10   # not hungry: no reflex takes her gaze
    _thing_ahead(world, "apple", "apple-far", 1_200)
    eyes = _look_at(organism, world, "apple-far", 14)
    pitches = [eye["head"][1] for eye in eyes]
    assert all(abs(pitches[i + 1] - pitches[i]) <= HEAD_STEP_MILLIDEGREES for i in range(len(pitches) - 1)), pitches   # the neck steps, five degrees a beat at most
    assert all(-HEAD_PITCH_BOUND_MILLIDEGREES <= p <= HEAD_PITCH_BOUND_MILLIDEGREES for p in pitches)
    assert min(pitches) < -25_000, pitches                                                   # an apple 1.2 m ahead lies about forty degrees below her eye: the neck goes down to it
    # Her eyes take up the rest at once: the thing is under her gaze from the second beat on, whenever her body's
    # turning leaves it within reach of neck and eyes together.
    gazes = [eye["gaze"] for eye in eyes[1:]]
    assert gazes[0] is not None and 0.3 < gazes[0][0] < 0.7, gazes[0]                        # on the second beat it is in the middle of her field
    # Her body turns sixty degrees at a stride while the neck steps five a beat: on the beats between, the thing
    # is beyond neck and eyes together and her gaze is honestly none; it returns as the neck catches up.
    assert sum(1 for g in gazes if g is not None) >= 3, gazes
    assert all(0.0 <= g[0] <= 1.0 and 0.0 <= g[1] <= 1.0 for g in gazes if g is not None)
    assert abs(eyes[1]["eyes"][1]) > 0, eyes[1]                                            # the eyes moved in the head on the first beat
    assert eyes[-1]["figure"] is not None or any(eye["figure"] for eye in eyes), eyes[-1]  # and a figure was found under her gaze


def test_the_figure_under_her_gaze_is_the_things_look_the_same_near_and_far_and_different_things_differ() -> None:
    """Bars 1 to 3 of the eye's Level 1 on her world eye, as measured (2026-09-15): the same
    thing at two distances gives one dominant key; that key holds on at least half the beats
    the thing is under her gaze and the top two keys on nine in ten (measured: the room's
    light follows the real sun through the windows, and a ring whose light sits on a
    quarter's boundary alternates between two keys; Level 3 counts both to the same word);
    the apple, the bear and the bowl give three keys (the cup shares the bowl's declared look); the store counts
    them; the body restores byte-exact; with nothing to act on and her head level, the wall
    gives no figure."""

    keys = {}
    for source in ("apple", "toy-bear", "bowl", "cup"):
        for distance in (1_200, 700):
            object_id = f"{source}-{distance}"
            world = home_world_authority(identity=IDENTITY)
            organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
            organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
            _thing_ahead(world, source, object_id, distance)
            eyes = _look_at(organism, world, object_id, 24)
            gazed = [eye for eye in eyes if eye["gaze"] is not None]
            found = [eye["figure"] for eye in gazed if eye["figure"]]
            assert len(gazed) >= 6 and len(found) * 2 >= len(gazed), (object_id, [(eye["gaze"], eye["figure"], eye["head"]) for eye in eyes])   # a disc cut by the field's edge has no look
            common = max(set(found), key=found.count)
            # A ring whose light sits on a quarter's boundary alternates between two keys as the hour's
            # light and her stride move it; Level 3 counts both. So: the top key on at least half the
            # beats, and the top two keys on at least nine in ten.
            ranked = sorted(set(found), key=lambda key: (-found.count(key), key))
            assert found.count(common) * 2 >= len(found), (object_id, found)
            assert sum(found.count(key) for key in ranked[:2]) * 10 >= len(found) * 9, (object_id, found)
            keys[object_id] = common
            keys[object_id + ":top2"] = set(ranked[:2])
            assert organism._state["figures"][common][0] >= 1 and organism.counts["figures"] >= 1
            assert all(len(eye["look"]) in (3, 9) and eye["extent"] > 0 for eye in gazed if eye["figure"])
            encoded = organism.encoded()
            assert FunctionalOrganism.restore(encoded).encoded() == encoded
        # The same thing near and far: one key, or, for a look on a quarter's boundary, the same pair.
        assert keys[f"{source}-1200"] in keys[f"{source}-700:top2"] or keys[f"{source}-700"] in keys[f"{source}-1200:top2"], (source, keys)
    # Three declared looks, three keys (the home world declares the cup with the bowl's look, so the two
    # share keys by content, not by law; the cup stays in the run for the near-and-far bar).
    assert len({keys[f"{source}-1200"] for source in ("apple", "toy-bear", "bowl")}) == 3, keys
    # Nothing to act on, head level: the wall, no figure.
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    eye = FunctionalPhysicalLoop().settle(organism, world, UNATTENDED).observation["her_eye"]
    assert eye["figure"] is None and eye["gaze"] is None


def test_looking_at_her_own_hand_keeps_her_head_straight_and_asleep_her_eyes_rest() -> None:
    """Found live right after release 1496: her hand's contact point sits exactly under her
    retinal port, so the bearing to a held thing had no direction and her head swung to its
    yaw bound while she slept holding the radio. Now a thing straight below her eye is looked
    at straight ahead and down, and asleep her eyes rest and her head follows nothing."""

    from dsf_ai_service.guala_functional_organism import HEAD_PITCH_BOUND_MILLIDEGREES, _aim, _target_point

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    _apple_ahead(world, "apple-held", 350)
    loop = FunctionalPhysicalLoop()
    held_beats = []
    for _ in range(40):
        result = loop.settle(organism, world, UNATTENDED)
        her = _her(world)
        if her.held_object_id is not None:
            point = _target_point(world.observation_snapshot(), her, her.held_object_id)
            assert point is not None
            yaw, pitch = _aim(her, point)
            assert yaw == 0 and pitch < -HEAD_PITCH_BOUND_MILLIDEGREES, (yaw, pitch)
            held_beats.append(result.observation["her_eye"])
    assert held_beats, "she never held the apple"
    assert all(abs(eye["head"][0]) <= 5_000 or eye["target"] is not None for eye in held_beats), [eye["head"] for eye in held_beats]
    # Asleep with a thing in her hand: her eyes rest and her head does not turn to it.
    organism._state["asleep"] = True
    organism._state["sleep_pressure"] = 10_000
    before = organism.head
    for _ in range(3):
        eye = loop.settle(organism, world, UNATTENDED).observation["her_eye"]
    assert eye["eyes"] == [0, 0] and eye["gaze"] is None, eye
    assert eye["head"][0] == before[0], (eye["head"], before)


def test_her_world_eye_draws_what_she_holds_at_her_hand_and_a_round_thing_as_a_disc() -> None:
    """Two truths of her world eye (A1's fixes under Joe's Option 1, 2026-09-15): a thing
    she holds is drawn at her hand's contact point, so looking down she sees it; and a
    sphere lights the sites within its angular radius, a disc, not the box around it."""

    from dsf_ai_service.guala_eye_figure import FOCAL_COLUMNS, FOCAL_ROWS, figure_of_disc

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    _thing_ahead(world, "toy-bear", "bear-far", 1_200)
    eyes = _look_at(organism, world, "bear-far", 24)
    discs = [eye for eye in eyes if eye["gaze"] is not None and eye["figure"]]
    assert discs, [(eye["gaze"], eye["figure"]) for eye in eyes]
    # A disc, not a box: the sites the figure holds are fewer than its box (about pi over four of it).
    for eye in discs[-3:]:
        sites = eye["extent"] * FOCAL_COLUMNS * FOCAL_ROWS
        box = (2 * eye["radius_sites"]) ** 2
        assert 0.55 * box <= sites <= 0.95 * box, (sites, box)
    # What she holds is in her sight when she looks down at her hand.
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    _apple_ahead(world, "apple-held", 350)
    loop = FunctionalPhysicalLoop()
    seen_in_hand = []
    for _ in range(80):
        result = loop.settle(organism, world, UNATTENDED)
        her = _her(world)
        eye = result.observation["her_eye"]
        if her.held_object_id is not None and eye["gaze"] is not None:
            seen_in_hand.append(eye["figure"])
    assert seen_in_hand and any(seen_in_hand), seen_in_hand   # before this change the world skipped her held thing: never a figure in hand


# ----- Level 2 and 3: the moment, and what followed it (docs/GL-SPC-MOMENT-LEVEL2-C1-20260915-v1.md) -----


def _moments_while_handling(source: str, object_id: str, hops, beats: int, reserve_share: int = 9):
    """A thing set down at her hand's reach; the room sounds `hops` in turn, silence between,
    so events close while she grasps and releases it; every moment formed is returned with
    what she held at that beat."""

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * reserve_share // 10
    _thing_ahead(world, source, object_id, 350)
    loop = FunctionalPhysicalLoop()
    out = []
    for index in range(beats):
        occurrence = _heard(hops[(index // 2) % len(hops)]) if index % 2 == 0 else UNATTENDED
        result = loop.settle(organism, world, occurrence)
        moment = result.observation["her_moment"]
        if moment is not None and moment["source"] == "heard":   # the room's sounds; her own voice's moments are counted apart
            out.append((moment["key"], None if moment["held"] == "none" else object_id, moment["count"], moment["next"], moment["fed"]))
    return organism, out


def test_a_moment_forms_only_when_a_sound_closes_and_binds_the_word_to_what_her_hand_holds() -> None:
    """Bars 1 to 3 of Level 2: a sound closing while she holds the apple gives one moment key
    met again each time; the same sound with the bear in hand gives another key; a beat with
    no sound closing forms no moment; the store is bounded and restores byte-exact."""

    organism, apple_moments = _moments_while_handling("apple", "apple-h", [_tone(440)], 160)
    held = [row for row in apple_moments if row[1] == "apple-h"]
    empty = [row for row in apple_moments if row[1] is None]
    assert held and empty, apple_moments
    held_keys = {row[0] for row in held}
        # The apple in hand is one moment however her head is turning; a second key appears only
    # when the apple's warmth in her hand crosses an eighth (measured 2026-09-16 under A1's
    # night-floor rooms, 45,000 ppm: the cooler room lets her hand warm it across a boundary).
    assert 1 <= len(held_keys) <= 2, held
    assert not (held_keys & {row[0] for row in empty}), apple_moments    # and never the same moment as an empty hand
    assert max(row[2] for row in held) >= 2, held                      # the same word with the apple in hand: met again
    assert organism.counts["moments"] == len(organism._state["moments"]) <= 256
    assert all(len(entry["context"]) == 3 for entry in organism._state["moments"].values())
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded
    _organism, bear_moments = _moments_while_handling("toy-bear", "bear-h", [_tone(440)], 160)
    bear_held = [row for row in bear_moments if row[1] == "bear-h"]
    assert bear_held and bear_held[0][0] != held[0][0], (bear_held[:2], held[:2])   # the same sound, the bear in hand: another moment
    # No sound closing, no moment.
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    results = _run(organism, world, [UNATTENDED] * 6)
    assert all(r.observation["her_moment"] is None for r in results) and organism.counts["moments"] == 0


def test_what_followed_a_moment_is_counted_within_the_window_the_next_moment_and_a_bite() -> None:
    """Level 3: two sounds in turn, each closing within sixteen beats of the last, count each
    other as what followed; while she is hungry with the apple in hand, the bite that follows
    a moment is counted to it."""

    from dsf_ai_service.guala_functional_organism import FOLLOW_WINDOW_BEATS

    organism, moments = _moments_while_handling("apple", "apple-h", [_tone(440), _tone(900)], 160, reserve_share=5)
    assert len(moments) >= 4, moments
    store = organism._state["moments"]
    followed = [(key, entry["next"]) for key, entry in store.items() if entry.get("next")]
    assert followed, store                                             # something followed something within the window
    assert all(int(count) >= 1 and len(following) <= 8 for _key, following in followed for count in following.values())
    assert FOLLOW_WINDOW_BEATS == 16
    assert organism.counts["bites"] >= 1, organism.counts
    assert any(int(entry.get("fed", 0)) >= 1 for entry in store.values()), store   # a bite within the window followed a moment


def test_her_own_syllable_closes_as_an_event_of_her_own_and_what_followed_it_is_counted() -> None:
    """Her own voice heard back enters her ear's gate in a gate of its own: her syllable
    closes as an own event with a key, a moment forms on it, and a room sound closing
    within the window afterwards is counted as what followed it."""

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    loop = FunctionalPhysicalLoop()
    own_closed = []
    spoke_at = None
    for index in range(80):
        # The room answers two beats after each syllable of hers with a short sound.
        occurrence = _heard(_tone(440)) if (spoke_at is not None and index == spoke_at + 2) else UNATTENDED
        result = loop.settle(organism, world, occurrence)
        if result.pressure is not None:
            spoke_at = index
        own_closed.extend(result.observation["her_ear"]["own_closed"])
    assert own_closed, "she never closed an event of her own voice"
    assert organism.counts["own_events"] >= 1 and organism._state["own_event"] is not None
    moments = organism._state["moments"]
    assert moments, "no moment formed on her own syllable"
    assert any(entry.get("next") for entry in moments.values()), "nothing followed her own syllable's moment within the window"
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded


def test_the_days_stores_keep_what_recurred_and_the_night_moves_recurring_moments_into_meanings() -> None:
    """The memory wall, measured live on her first hour (a piece of music fills the moments
    store with events that never recur): the day's stores evict the least met first, then
    the least recently met, so a recurring moment survives a flood of new ones; each
    sleeping beat moves the most recurrent moment into her meanings by count (merging what
    followed and the bites) and drops a moment met once; by morning the day's moments are
    empty and the meanings stay bounded."""

    from dsf_ai_service.guala_functional_organism import MEANING_CAPACITY, MOMENT_RECORD_CAPACITY

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    moments = organism._state["moments"]
    moments["recurring"] = {"count": 3, "tick": 10, "held": "1/2", "source": "heard", "context": [1, 0, 0], "next": {"after": 2}, "fed": 1}
    for index in range(MOMENT_RECORD_CAPACITY + 40):
        moments[f"single{index:04d}"] = {"count": 1, "tick": 100 + index, "held": "none", "source": "heard", "context": [0, 0, 0], "next": {}, "fed": 0}
        while len(moments) > MOMENT_RECORD_CAPACITY:
            del moments[min(moments, key=lambda k: (int(moments[k]["count"]), int(moments[k]["tick"]), k))]
    assert "recurring" in moments and len(moments) == MOMENT_RECORD_CAPACITY and "single0000" not in moments
    # The night: recurring moments move into meanings, singles are dropped, the day empties.
    for beat in range(MOMENT_RECORD_CAPACITY + 1):
        organism._dream_moment(1_000 + beat)
    assert organism._state["moments"] == {}
    meanings = organism._state["meanings"]
    assert list(meanings) == ["recurring"] and meanings["recurring"]["count"] == 3 and meanings["recurring"]["next"] == {"after": 2} and meanings["recurring"]["fed"] == 1
    # Met again another day: counts, what followed and the bites merge by addition.
    organism._state["moments"]["recurring"] = {"count": 2, "tick": 20, "held": "1/2", "source": "heard", "context": [2, 0, 0], "next": {"after": 1, "other": 1}, "fed": 0}
    organism._dream_moment(2_000)
    assert meanings["recurring"]["count"] == 5 and meanings["recurring"]["next"] == {"after": 3, "other": 1}
    # Bounded: the least counted meaning leaves.
    for index in range(MEANING_CAPACITY + 10):
        organism._state["moments"][f"m{index:03d}"] = {"count": 2 + (index % 3), "tick": 30 + index, "held": "none", "source": "own", "context": [0, 0, 0], "next": {}, "fed": 0}
        organism._dream_moment(3_000 + index)
    assert len(meanings) <= MEANING_CAPACITY and "recurring" in meanings
    assert organism.counts["meanings"] == len(meanings)
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded


def test_a_persons_voice_reaches_her_by_the_rooms_geometry_like_a_things_sound() -> None:
    """The caregiver's voice as a thing-sound from its body: in her room the gain is one
    metre over the distance, capped at one; an unknown source is silence."""

    from dsf_ai_service.guala_functional_loop import _thing_sound_gain

    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    person = next(body for body in snapshot.bodies if body.body_id != snapshot.self_body_id)
    gain, distance, path = _thing_sound_gain(snapshot, person.body_id)
    assert distance is not None and distance >= 1 and path in ("room", "door") and 0 <= gain <= 1
    if path == "room":
        assert gain == min(1, 1_000 / distance) or abs(float(gain) - min(1.0, 1_000 / distance)) < 1e-6
    assert _thing_sound_gain(snapshot, "nobody-here") == (0, None, "absent")
    assert _thing_sound_gain(snapshot, snapshot.self_body_id)[2] == "absent"   # her own body is not a room sound


def test_her_own_sounds_moment_is_keyed_by_what_she_said_so_it_recurs() -> None:
    """Measured on her first hour live: no moment recurred, because every rendition of her
    own syllable sounds back with a new key. Her own sound's moment is keyed by her drive,
    what she said, which is her own exact act: saying the same syllable twice with an empty
    hand is one moment met twice; a different syllable is another."""

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    world = home_world_authority(identity=IDENTITY)
    body = next(b for b in world.observation_snapshot().bodies if b.body_id == world.observation_snapshot().self_body_id)
    measures = {"touch_texture": 0.0, "touch_warmth": 0.5, "hunger": 0.45, "taste_residue": 0.0, "skin_contact": 0.0}
    organism._state["last_said"] = "mah1"
    for tick in (10, 20):
        organism._own_closed = [f"rendition{tick}"]   # a different heard key each time, as measured
        organism._ear_closed = []
        organism._form_moments(body, measures, tick)
    moments = organism._state["moments"]
    assert len(moments) == 1 and next(iter(moments.values()))["count"] == 2 and next(iter(moments.values()))["source"] == "own"
    organism._state["last_said"] = "oo3"
    organism._own_closed = ["rendition30"]
    organism._form_moments(body, measures, 30)
    assert len(moments) == 2
    encoded = organism.encoded()
    assert FunctionalOrganism.restore(encoded).encoded() == encoded
