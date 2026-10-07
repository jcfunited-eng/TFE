"""External waste export and food renewal; never body intake or learning."""
from dataclasses import replace
import pytest
from dsf_ai_service import guala_home_world as home
from dsf_ai_service.guala_caretaker_hand import nothing_left_to_bite
from dsf_ai_service.substrate.embodiment_world import PositionMM
IDENTITY = '5170058c-8fe7-489b-b173-47e9f69c3351'

def fixture(*, held=False):
    world = home.home_world_authority(identity=IDENTITY)
    with home._world_thermal_transaction(world):
        old = world._state.world
        apple = next((o for o in old.objects if o.object_id == 'apple'))
        objects = []
        for obj in old.objects:
            if obj.object_id in ('apple', 'garden-apple', 'bread-slice'):
                obj = replace(obj, material=replace(obj.material, digestible_mass_micrograms=2 if obj.object_id != 'bread-slice' else 1))
            if obj.object_id == 'bottle-milk':
                obj = replace(obj, material=replace(obj.material, digestible_mass_micrograms=1))
            if held and obj.object_id == 'garden-apple':
                obj = replace(obj, position=None, held_by_body_id=old.self_body_id)
            objects.append(obj)
        objects.append(replace(apple, object_id='unnamed-remnant', position=PositionMM(6000, 8000, 0), material=replace(apple.material, digestible_mass_micrograms=2)))
        bodies = tuple((replace(b, held_object_id='garden-apple') if held and b.body_id == old.self_body_id else b for b in old.bodies))
        home._commit_world_successor(world, replace(old, revision=old.revision + 1, objects=tuple(objects), bodies=bodies))
    return world

def digestible(world):
    return sum((o.material.digestible_mass_micrograms for o in world.canonical_observation_snapshot().objects if o.material))

def test_exact_external_mass_balance_and_declared_site_renewal():
    world = fixture()
    before = world.canonical_observation_snapshot()
    mass = digestible(world)
    pupil = next((b for b in before.bodies if b.body_id == before.self_body_id))
    milk = next((o for o in before.objects if o.object_id == 'bottle-milk'))
    assert milk.material.digestible_mass_micrograms == 1 and (not nothing_left_to_bite(pupil, milk))
    receipt = home.replenish_home_food(world)
    after = world.canonical_observation_snapshot()
    assert set(receipt['replenished']) == {'apple', 'garden-apple', 'bread-slice'}
    assert receipt['external_removed_digestible_mass_micrograms'] == 7
    assert digestible(world) + 7 == mass + receipt['external_digestible_mass_micrograms']
    assert after.bodies == before.bodies
    assert not any((o.object_id == 'unnamed-remnant' for o in after.objects))
    assert next((o for o in after.objects if o.object_id == 'bottle-milk')) == milk
    assert len(after.objects) == len(before.objects) - 1
    for obj in after.objects:
        if obj.object_id in receipt['replenished']:
            assert not nothing_left_to_bite(pupil, obj)
    garden = next((o for o in after.objects if o.object_id == 'garden-apple'))
    assert garden.position == PositionMM(14700, 14800, 0)

def test_held_residue_is_not_disposed_or_replaced():
    world = fixture(held=True)
    before = world.canonical_observation_snapshot()
    garden = next((o for o in before.objects if o.object_id == 'garden-apple'))
    receipt = home.replenish_home_food(world)
    after = world.canonical_observation_snapshot()
    assert 'garden-apple' not in receipt['replenished']
    assert all((x['object_id'] != 'garden-apple' for x in receipt['exported_remnants']))
    assert next((o for o in after.objects if o.object_id == 'garden-apple')) == garden
    assert after.bodies == before.bodies

def test_recurrent_supply_and_cold_world_preserve_exact_successor():
    world = fixture()
    home.replenish_home_food(world)
    raw = world.encoded_snapshot()
    restored = home.home_world_authority(identity=IDENTITY, encoded_world=raw)
    assert restored.encoded_snapshot() == raw
    receipt = home.replenish_home_food(restored)
    assert receipt['status'] == 'unchanged'
    assert receipt['external_digestible_mass_micrograms'] == receipt['external_removed_digestible_mass_micrograms'] == 0
    assert restored.encoded_snapshot() == raw

def test_failed_coupled_commit_keeps_all_remnants_and_prior_world(monkeypatch):
    world = fixture()
    raw = world.encoded_snapshot()
    commit = home._commit_world_successor

    def failed(authority, successor):
        commit(authority, successor)
        raise RuntimeError('after coupled commit')
    monkeypatch.setattr(home, '_commit_world_successor', failed)
    with pytest.raises(RuntimeError, match='after coupled commit'):
        home.replenish_home_food(world)
    assert world.encoded_snapshot() == raw

def test_every_replacement_moves_and_recurrent_exhaustion_alternates_sites():
    world = fixture()
    for _ in range(3):
        before = world.canonical_observation_snapshot()
        receipt = home.replenish_home_food(world)
        assert receipt['replenished']
        for supplied in receipt['supplied']:
            assert supplied['position'] != supplied['previous_position']
        with home._world_thermal_transaction(world):
            old = world._state.world
            objects = tuple((replace(o, material=replace(o.material, digestible_mass_micrograms=0)) if o.object_id in receipt['replenished'] else o for o in old.objects))
            home._commit_world_successor(world, replace(old, revision=old.revision + 1, objects=objects))
        assert len(world.canonical_observation_snapshot().objects) <= len(before.objects)

def test_zero_loose_core_is_removed_but_inert_furniture_is_preserved():
    world = fixture()
    with home._world_thermal_transaction(world):
        old = world._state.world
        apple = next((o for o in old.objects if o.object_id == 'apple'))
        core = replace(apple, object_id='apple-empty', position=PositionMM(6500, 8500, 0), material=replace(apple.material, digestible_mass_micrograms=0))
        home._commit_world_successor(world, replace(old, revision=old.revision + 1, objects=old.objects + (core,)))
    tree = next((o for o in world.canonical_observation_snapshot().objects if o.object_id == 'tree-apple'))
    receipt = home.replenish_home_food(world)
    after = world.canonical_observation_snapshot()
    assert any((r['object_id'] == 'apple-empty' and r['digestible_mass_micrograms'] == 0 for r in receipt['exported_remnants']))
    assert not any((o.object_id == 'apple-empty' for o in after.objects))
    assert next((o for o in after.objects if o.object_id == 'tree-apple')) == tree

def test_occupied_alternate_site_defers_supply_without_leaving_spent_food():
    world = fixture()
    with home._world_thermal_transaction(world):
        old = world._state.world
        obstacle = next((o for o in old.objects if o.object_id == 'toy-bear'))
        objects = tuple((replace(o, position=PositionMM(14700, 14800, 0)) if o is obstacle else o for o in old.objects))
        home._commit_world_successor(world, replace(old, revision=old.revision + 1, objects=objects))
    receipt = home.replenish_home_food(world)
    assert {'object_id': 'garden-apple', 'reason': 'replacement_sites_occupied'} in receipt['deferred']
    assert not any((o.object_id == 'garden-apple' for o in world.canonical_observation_snapshot().objects))
