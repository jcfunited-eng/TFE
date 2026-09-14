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
    snapshot = world.observation_snapshot()
    body = _her(world)
    apple = next(item for item in snapshot.objects if item.object_id == "apple")
    radians = math.radians(body.pose.heading_millidegrees / 1000)
    world.admit_authored_arrival(EmbodiedObject(
        object_id, apple.radius_mm, apple.mass_grams,
        PositionMM(body.pose.position.x + round(ahead_mm * math.cos(radians)), body.pose.position.y + round(ahead_mm * math.sin(radians)), 0),
        reflectance_ppm=apple.reflectance_ppm, material=apple.material,
    ))


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
    assert max(sizes) < 64_000 and len(world.encoded_snapshot()) < 4_000_000
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
    edge_on_the_right = tuple(30 if (index % FOCAL_COLUMNS) < 26 else (250 if (index % FOCAL_COLUMNS) % 2 else 20) for index in range(FOCAL_COLUMNS * FOCAL_ROWS))
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
    acts = [r.observation["her_act"] for r in results]
    assert "take" in acts, acts[:12]
    taken = acts.index("take")
    assert results[taken].observation["world_action_refusal"] is None
    assert "release" in acts[taken:], acts[taken:]
    after = next(item for item in world.observation_snapshot().objects if item.object_id == "toy-bear")
    assert after.position is not None and after.position != before
    assert organism.counts["handled"] >= 1


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
    """Her head law: the wide field the head carries aims the focal cone. On a
    fresh world every object lies on the floor below head height; within a few
    beats her head has pitched down toward them (it never yaws), the focal field
    shows structure, and the head stays inside its declared bounds and is
    restored byte-exact with the body."""

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
    assert organism.head[0] == 0 and organism.head[1] < 0, organism.head
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
    act, why = organism._choose(key, acts)
    assert act == "step" and "first try of step" in why
    organism._state["acts"][key] = {"acts": {"step": [3, -0.6], "turn_left": [2, 0.5], "say": [1, 0.1]}, "tick": 1}
    act, why = organism._choose(key, acts)
    assert act == "rest" and "first try of rest" in why  # still untried
    organism._state["acts"][key]["acts"]["rest"] = [1, 0.0]
    act, why = organism._choose(key, acts)
    assert act == "turn_left" and "best so far" in why, why  # mean +0.25 beats +0.10, 0.0 and -0.2
    organism._state["acts"][key]["acts"]["step"] = [EXPLORE_EVERY - 4, -0.6]  # visits total = 8
    act, why = organism._choose(key, acts)
    assert act == "say" and "least tried" in why, why  # say and rest tied at 1 try; say first in order


def test_what_followed_is_valued_by_her_state_when_she_chose_and_a_refusal_costs() -> None:
    from dsf_ai_service.guala_functional_organism import NEED_FOOD, NEED_NEW, NEED_SOUND, REFUSAL_COST

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    key = "0123456789abcdef"
    organism._state["pending_act"] = {"key": key, "act": "step", "deficit": 0.25, "intake": 0, "refused": True}
    organism._settle("other", True, 0.0, 2)
    tries, total = organism._state["acts"][key]["acts"]["step"]
    assert tries == 1 and abs(total - (NEED_NEW * 0.75 - REFUSAL_COST)) < 1e-6
    organism._state["pending_act"] = {"key": key, "act": "step", "deficit": 0.6, "intake": 1000, "refused": False}
    organism._settle("other", False, 0.5, 3)
    tries, total = organism._state["acts"][key]["acts"]["step"]
    assert tries == 2 and abs(total - ((NEED_NEW * 0.75 - REFUSAL_COST) + NEED_FOOD * 0.6 + NEED_SOUND * 0.5)) < 1e-6
    assert organism._state["pending_act"] is None


def test_the_jaw_reflex_credits_the_act_that_brought_food_to_her_mouth() -> None:
    """Hungry, the caretaker holds an apple to her mouth: she bites by reflex
    (not from the record); the intake is credited to the act she last chose."""

    from dsf_ai_service.guala_functional_organism import NEED_FOOD

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    results = _run(organism, world, [UNATTENDED, UNATTENDED, _present("apple")])
    first_bite = results[2].observation
    assert first_bite["her_act"] == "bite" and "reflex" in first_bite["act_reason"], first_bite["her_act"]
    assert first_bite["real_nutrition_intake_zeptojoules"] > 0
    last = organism._state["last_chosen"]  # the act she chose the beat before the apple reached her mouth
    tries, total = organism._state["acts"][last["key"]]["acts"][last["act"]]
    assert total >= NEED_FOOD * float(last["deficit"]) - 1e-6, (last, tries, total)
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
