"""The functional organism (Joe, 2026-09-14): declared act laws over her own
measured state, the kernel over her sensed streams, bounded memory, exact
custody. Every test runs the real home world; the world validates her acts."""

from __future__ import annotations

import math
import struct

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    BODY_AXES, CAPACITY_MICROGRAMS, FunctionalOrganism, MAGIC, syllable_pcm,
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


def test_hungry_with_food_in_sight_she_turns_and_steps_toward_it() -> None:
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-far", 2_500)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    start = _her(world).pose.position
    results = _run(organism, world, [UNATTENDED] * 30)
    first = results[0].observation
    assert first["her_act"] == "approach" and first["world_action_refusal"] is None
    assert "apple-far" in first["seen"]
    assert any(r.observation["her_act"] == "bite" for r in results), [r.observation["her_act"] for r in results]
    assert organism.counts["strides"] >= 5
    assert _her(world).pose.position != start


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
    acts = [r.observation["her_act"] for r in results]
    assert "release" not in acts  # food in hand is kept while she is not hungry


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


def test_idle_she_babbles_through_her_airway_hears_herself_and_imitates_a_heard_sound() -> None:
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10  # not hungry
    organism._state["feeding"] = False
    results = _run(organism, world, [UNATTENDED] * 24)
    spoken = [r for r in results if r.pressure is not None]
    assert spoken, "she never babbled"
    receipt, pcm = spoken[0].pressure
    assert len(pcm) <= MAX_PRESSURE_BYTES and len(pcm) % 2 == 0 and receipt == __import__("hashlib").sha256(pcm).hexdigest()
    assert spoken[0].observation["said_drive"] is not None and spoken[0].observation["said"]
    assert organism._state["voice"], "she did not hear her own syllable"
    assert all(len(entry["heard"]) == 32 for entry in organism._state["voice"])
    # A sound from outside: within eight beats she answers with her nearest own sound.
    results = _run(organism, world, [_heard(_tone(370)), *([UNATTENDED] * 14)])
    assert results[0].observation["external_heard_sample_count"] == 4_000
    assert results[0].observation["her_act"] == "listen"
    answers = [r.observation for r in results if "answering a sound she heard" in (r.observation["act_reason"] or "")]
    assert answers and answers[0]["said_drive"] is not None, [r.observation["act_reason"] for r in results]
    assert 1 <= len(answers) <= 3, "a call is answered with a short bout"


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


def test_with_nothing_new_in_her_room_she_leaves_through_a_doorway() -> None:
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    start_room = world.observation_snapshot().room_id
    rooms = {start_room}
    loop = FunctionalPhysicalLoop()
    for _ in range(900):
        result = loop.settle(organism, world, UNATTENDED)
        rooms.add(result.observation["embodiment"]["room_id"])
        if len(rooms) >= 2:
            break
    assert len(rooms) >= 2, rooms
    assert organism._state["visited"]


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
    for key in ("visited", "door_goal", "bout_syllables", "quiet_until_tick", "blocked_doors", "attended_tick", "unreachable_food", "food_goal", "food_refusals", "food_best_mm", "food_stall_beats", "ambient_sound", "answered_profile", "touched", "strides_since_pickup", "handled", "release_refusals", "touching", "listening_since", "call_profile", "answer_bout", "answer_target", "answer_pending", "answer_map", "food_rooms", "food_room_goal", "room_now"):
        state.pop(key, None)
    older = MAGIC + json.dumps(state, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    restored = FunctionalOrganism.restore(older)
    assert restored.live_organism_tick == 5 and restored.encoded() != older
    assert restored._state["voice_version"] == VOICE_VERSION and restored._state["voice"] == [] and restored._state["heard"] == []
    assert restored._state["visited"] == {} and restored._state["door_goal"] is None
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


def test_boxed_in_food_does_not_hold_her_in_place() -> None:
    """Hungry, with an apple in sight that every stride toward is refused
    (walled by furniture), she gives up on it for a while and searches on."""

    from dsf_ai_service.guala_functional_organism import GOAL_REFUSAL_LIMIT

    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    body = _her(world)
    apple = next(item for item in snapshot.objects if item.object_id == "apple")
    room = next(region for region in snapshot.regions if region.region_id == snapshot.room_id)
    floor = [(item.position, item.radius_mm) for item in snapshot.objects if item.position is not None]
    floor.append((body.pose.position, body.radius_mm))
    ring_mm, crate_mm = 650, 200

    def clear(position: PositionMM, radius_mm: int) -> bool:
        inside = (room.bounds.minimum.x + radius_mm <= position.x <= room.bounds.maximum.x - radius_mm
                  and room.bounds.minimum.y + radius_mm <= position.y <= room.bounds.maximum.y - radius_mm)
        return inside and all(math.hypot(position.x - p.x, position.y - p.y) > radius_mm + r + 60 for p, r in floor)

    # A clear place in her sight: ahead of her, where an apple and a ring of
    # eight crates around it fit without touching the furniture.
    centre = None
    for ahead in range(1_500, 3_400, 100):
        for turn in (0, 20_000, -20_000, 40_000, -40_000):
            radians = math.radians(((body.pose.heading_millidegrees + turn) % 360_000) / 1000)
            candidate = PositionMM(body.pose.position.x + round(ahead * math.cos(radians)), body.pose.position.y + round(ahead * math.sin(radians)), 0)
            crates = [PositionMM(candidate.x + round(ring_mm * math.cos(math.radians(d))), candidate.y + round(ring_mm * math.sin(math.radians(d))), 0) for d in range(0, 360, 45)]
            if clear(candidate, apple.radius_mm) and all(clear(c, crate_mm) for c in crates):
                centre = candidate
                break
        if centre is not None:
            break
    assert centre is not None, "no clear place for the walled apple in her room"
    world.admit_authored_arrival(EmbodiedObject("apple-walled", apple.radius_mm, apple.mass_grams, centre, reflectance_ppm=apple.reflectance_ppm, material=apple.material))
    for index, degrees in enumerate(range(0, 360, 45)):
        a = math.radians(degrees)
        world.admit_authored_arrival(EmbodiedObject(f"crate-{index}", crate_mm, 20_000, PositionMM(centre.x + round(ring_mm * math.cos(a)), centre.y + round(ring_mm * math.sin(a)), 0)))
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    results = _run(organism, world, [UNATTENDED] * (GOAL_REFUSAL_LIMIT + 30))
    acts = [r.observation["her_act"] for r in results]
    assert acts[0] == "approach"
    assert "apple-walled" in organism._state["unreachable_food"]
    later = acts[-20:]
    assert "approach" not in later or organism.counts["bites"] > 0, later


def test_an_open_microphone_does_not_make_her_repeat_one_syllable() -> None:
    """The same room sound every beat is answered once, then treated as the
    room; a new, louder sound is answered again; answers obey the bout."""

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    _run(organism, world, [UNATTENDED] * 24)  # she babbles and hears herself
    assert organism._state["voice"]
    results = _run(organism, world, [_heard(_tone(370))] * 40)
    listened = [r for r in results if r.observation["her_act"] == "listen"]
    assert 1 <= len(listened) <= 24, len(listened)  # she listens while it stands out, at most six seconds
    answers = [r for r in results if "answering a sound she heard" in (r.observation["act_reason"] or "")]
    assert len(answers) <= 3, len(answers)
    spoken = [r for r in results if r.pressure is not None]
    assert len(spoken) <= 12, len(spoken)


def test_not_hungry_she_feels_picks_up_carries_and_sets_down_light_things() -> None:
    """Her handling law: a light thing her hand reaches is felt, picked up,
    carried a while and set down somewhere else; what she handled is known
    and not handled again for a time; heavy things are only looked at."""

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    before = {item.object_id: (item.position.x, item.position.y) for item in world.observation_snapshot().objects if item.position is not None}
    loop = FunctionalPhysicalLoop()
    acts = []
    for _ in range(500):
        acts.append(loop.settle(organism, world, UNATTENDED).observation)
        if organism.counts["handled"] >= 2 and any(o["her_act"] == "release" and o["world_action_refusal"] is None for o in acts):
            break
    kinds = [o["her_act"] for o in acts]
    assert "touch" in kinds and "grasp" in kinds and "release" in kinds, set(kinds)
    first_touch = kinds.index("touch")
    assert kinds[first_touch + 1] == "grasp", kinds[first_touch:first_touch + 3]
    after = {item.object_id: (item.position.x, item.position.y) for item in world.observation_snapshot().objects if item.position is not None}
    moved = [k for k in before if k in after and before[k] != after[k]]
    assert moved, "nothing was carried anywhere"
    snapshot = world.observation_snapshot()
    for object_id in moved:
        item = next(i for i in snapshot.objects if i.object_id == object_id)
        assert item.mass_grams <= 2_000 and item.radius_mm <= 300
    assert set(organism._state["touched"]) >= set(moved)
    refused_releases = [o for o in acts if o["her_act"] == "release" and o["world_action_refusal"]]
    assert len(refused_releases) <= 3, len(refused_releases)


def test_her_gaze_follows_structure_not_brightness() -> None:
    from dsf_ai_service.guala_functional_organism import FOCAL_COLUMNS, FOCAL_ROWS, structure_centre

    flat_bright_top = tuple(240 if index // FOCAL_COLUMNS < FOCAL_ROWS // 2 else 200 for index in range(FOCAL_COLUMNS * FOCAL_ROWS))
    x, y = structure_centre(flat_bright_top)
    assert abs(x - 0.5) < 0.02 and abs(y - 0.5) < 0.06, (x, y)  # one horizontal edge at mid height; brightness above it holds nothing
    edge_on_the_right = tuple(30 if (index % FOCAL_COLUMNS) < 26 else (250 if (index % FOCAL_COLUMNS) % 2 else 20) for index in range(FOCAL_COLUMNS * FOCAL_ROWS))
    x, y = structure_centre(edge_on_the_right)
    assert x > 0.75 and abs(y - 0.5) < 0.05, (x, y)
    assert structure_centre(tuple([128] * (FOCAL_COLUMNS * FOCAL_ROWS))) == (0.5, 0.5)


def test_she_listens_while_spoken_to_answers_when_it_ends_and_her_answer_improves_with_exchanges() -> None:
    from dsf_ai_service.guala_functional_organism import heard_key

    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    _run(organism, world, [UNATTENDED] * 24)  # she babbles and hears herself
    assert organism._state["voice"]
    call = [_heard(_tone(370))] * 6
    distances = []
    for exchange in range(6):
        results = _run(organism, world, [*call, *([UNATTENDED] * 20)])
        acts = [r.observation["her_act"] for r in results]
        assert acts[0] == "listen", acts[:8]
        answers = [r.observation for r in results if "answering a sound she heard" in (r.observation["act_reason"] or "")]
        assert 1 <= len(answers) <= 3, (exchange, [r.observation["act_reason"] for r in results])
        assert all(o["said_drive"] is not None for o in answers)
        known = organism._state["answer_map"]
        assert known, "no answer was kept"
        key = next(iter(known))
        distances.append(float(known[key]["distance"]))
    assert organism.counts["answers_known"] >= 1
    assert distances[-1] <= distances[0], distances  # what she keeps never gets worse; it can only improve
    assert organism._state["answer_map"][next(iter(organism._state["answer_map"]))]["tries"] >= 3


def test_hungry_she_heads_for_the_room_where_she_ate() -> None:
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    # A meal in her room, presented by the caretaker.
    results = _run(organism, world, [UNATTENDED, _present("apple"), *([UNATTENDED] * 8)])
    assert any(r.observation["real_nutrition_intake_zeptojoules"] for r in results)
    assert organism._state["food_rooms"], organism._state["food_rooms"]
    fed_room = next(iter(organism._state["food_rooms"]))
    # Sated for a while, she roams elsewhere; then hungry again with nothing in sight.
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 9 // 10
    organism._state["feeding"] = False
    loop = FunctionalPhysicalLoop()
    for _ in range(400):
        o = loop.settle(organism, world, UNATTENDED).observation
        if o["embodiment"]["room_id"] != fed_room:
            break
    assert world.observation_snapshot().room_id != fed_room
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS // 2  # hungry now
    organism._state["feeding"] = True
    for _ in range(200):
        o = loop.settle(organism, world, UNATTENDED).observation
        if "where food was" in (o["act_reason"] or ""):
            break
    assert "where food was" in (o["act_reason"] or ""), o["act_reason"]
    assert organism._state["food_room_goal"] == fed_room


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
