"""Continuous foraging through ordinary world actions; no body relocation.

Single-source fixtures declare food availability in the world. They do not
write food beliefs, paths, learned state, body pose, or action outcomes.
The mature-body proof separately preserves the actual production history.
"""
from __future__ import annotations

import pytest

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import FunctionalOrganism, CAPACITY_MICROGRAMS, SATED_ABOVE
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.substrate.embodiment_world import NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM

IDENTITY = '7a635ab2-225c-4222-98b4-975ce41b6a1a'
UNATTENDED = PhysicalOccurrence('unattended', None)


def run_foraging(world, organism, *, require_satiety=False):
    loop = FunctionalPhysicalLoop()
    rooms = [world.canonical_observation_snapshot().room_id]
    eaten = set()
    total_intake = 0
    for _ in range(250):
        before = world.canonical_observation_snapshot()
        result = loop.settle(organism, world, UNATTENDED)
        after = world.canonical_observation_snapshot()
        if after.room_id != rooms[-1]:
            rooms.append(after.room_id)
            # A changed room must be joined by a real portal from the prior room.
            assert any(set(p.region_ids) == {rooms[-2], rooms[-1]} for p in after.portals)
        by_id = {o.object_id: o for o in after.objects}
        intake = 0
        for item in before.objects:
            if item.material is None or item.object_id not in by_id:
                continue
            remaining = by_id[item.object_id]
            assert remaining.material is not None
            consumed = item.material.digestible_mass_micrograms - remaining.material.digestible_mass_micrograms
            if consumed > 0:
                assert result.observation['her_act'] == 'bite'
                intake += consumed
                eaten.add(item.object_id)
        assert intake * NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM == result.observation['real_nutrition_intake_zeptojoules']
        total_intake += intake
        if (require_satiety and organism.reserve_micrograms >= int(CAPACITY_MICROGRAMS * SATED_ABOVE)) or (not require_satiety and intake > 0):
            return rooms, eaten, total_intake
    raise AssertionError(f'No requested intake/satiety after 250 ordinary intervals: rooms={rooms}, eaten={eaten}, reserve={organism.reserve_micrograms}, last={result.observation["act_reason"]}, refusal={result.observation["world_action_refusal"]}')


@pytest.mark.parametrize(('source', 'destination'), [('bowl', 'kitchen'), ('bottle-milk', 'dining'), ('garden-apple', 'backyard')])
def test_continuous_portal_navigation_and_actual_food_intake(source, destination):
    world = home_world_authority(identity=IDENTITY)
    # External fixture inventory only: one declared food source remains.
    for item in world.canonical_observation_snapshot().objects:
        if item.object_id != source and item.material is not None and item.material.digestible_mass_micrograms > 0:
            world.admit_authored_departure(item.object_id)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    rooms, eaten, intake = run_foraging(world, organism)
    assert rooms[0] == 'her-room'
    assert 'hallway' in rooms and destination in rooms
    assert eaten == {source} and intake > 0


def test_multi_source_autonomous_foraging_to_full_satiety():
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    # Explicit first-use hungry fixture, not a mutation of a retained organism.
    organism._state['reserve_micrograms'] = 0
    organism._state['feeding'] = True
    rooms, eaten, intake = run_foraging(world, organism, require_satiety=True)
    assert int(CAPACITY_MICROGRAMS * SATED_ABOVE) == 425000
    assert organism.reserve_micrograms >= 425000
    assert not organism.feeding
    assert len(eaten) >= 3 and intake >= organism.reserve_micrograms
    assert rooms[0] == 'her-room' and 'hallway' in rooms
