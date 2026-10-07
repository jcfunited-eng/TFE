"""Environmental supply/custody tests, not proof of sustained self-feeding.

World fixtures declare missing/depleted material explicitly. Wake fixtures set
sleep pressure to its physical boundary; they do not simulate a whole night.
No neuron refusal is disabled and no action or intake is scripted in runtime.
"""
from __future__ import annotations
import ast
import copy
from dataclasses import replace
from pathlib import Path
import pytest
import dsf_ai_service.guala_home_world as home
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop, PhysicalOccurrence
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
IDENTITY = '5f9f6747-cd42-4282-b2be-9e055149dfb9'
ROOT = Path(__file__).resolve().parents[1]
UNATTENDED = PhysicalOccurrence('unattended', None)

def world_without_apple():
    world = home.home_world_authority(identity=IDENTITY)
    with home._world_thermal_transaction(world):
        old = world._state.world
        home._commit_world_successor(world, replace(old, revision=old.revision + 1, objects=tuple((o for o in old.objects if o.object_id != 'apple'))))
    return world

def digestible(world):
    return sum((o.material.digestible_mass_micrograms for o in world.global_objects() if o.material is not None))

def change_digestible(world, food_id, amount):
    with home._world_thermal_transaction(world):
        old = world._state.world
        objects = tuple((replace(o, material=replace(o.material, digestible_mass_micrograms=amount)) if o.object_id == food_id else o for o in old.objects))
        home._commit_world_successor(world, replace(old, revision=old.revision + 1, objects=objects))

def test_external_supply_mass_exact_and_taste_is_not_nutrition():
    world = world_without_apple()
    change_digestible(world, 'bottle-milk', 0)
    before = digestible(world)
    bodies = world._state.world.bodies
    receipt = home.replenish_home_food(world)
    assert receipt['replenished'] == ['apple', 'bottle-milk']
    assert receipt['external_digestible_mass_micrograms'] == 160000
    assert digestible(world) - before == receipt['external_digestible_mass_micrograms']
    assert world._state.world.bodies == bodies
    assert receipt['revision_after'] == receipt['revision_before'] + 1

def test_untransferable_positive_residue_is_exported_and_replaced():
    world = home.home_world_authority(identity=IDENTITY)
    change_digestible(world, 'bread-slice', 1)
    before = digestible(world)
    receipt = home.replenish_home_food(world)
    assert receipt['external_removed_digestible_mass_micrograms'] == 1
    assert receipt['external_digestible_mass_micrograms'] == 100000
    assert digestible(world) + 1 == before + 100000
    assert receipt['supplied'][0]['position'] != receipt['supplied'][0]['previous_position']

def test_supply_cold_world_restore_and_repeated_call_are_byte_exact():
    world = world_without_apple()
    first = home.replenish_home_food(world)
    encoded = world.encoded_snapshot()
    restored = home.home_world_authority(identity=IDENTITY, encoded_world=encoded)
    assert restored.encoded_snapshot() == encoded
    again = home.replenish_home_food(restored)
    assert first['external_digestible_mass_micrograms'] == 140000
    assert again['external_digestible_mass_micrograms'] == 0
    assert again['status'] == 'unchanged'
    assert restored.encoded_snapshot() == encoded

def test_commit_failure_rolls_back_complete_coupled_world(monkeypatch):
    world = world_without_apple()
    before = world.encoded_snapshot()
    original = home._commit_world_successor

    def fail_after_commit(authority, successor):
        original(authority, successor)
        raise RuntimeError('injected post-commit failure')
    monkeypatch.setattr(home, '_commit_world_successor', fail_after_commit)
    with pytest.raises(RuntimeError, match='post-commit failure'):
        home.replenish_home_food(world)
    assert world.encoded_snapshot() == before

def test_invalid_authority_is_not_reported_as_success():
    with pytest.raises(TypeError, match='world authority'):
        home.replenish_home_food(object())

def with_lived_food_evidence():
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1998)
    organism.migrate()
    organism._state['conserved_objects'] = {'bottle-milk': {'fed_count': 0, 'is_food': False, 'currently_depleted': True, 'non_nutritive': True, 'tested_non_food': True}, 'fixture-renamed-material': {'fed_count': 2, 'historical_intake_micrograms': 19, 'is_food': True, 'non_nutritive': False}}
    organism._state['conserved_objects']['bottle-milk'].update(object_id='bottle-milk', position=[8000, 3500, 0], radius_mm=70, room_id='dining', last_seen_tick=1900, confidence=1.0)
    organism._state['conserved_objects']['fixture-renamed-material'].update(object_id='fixture-renamed-material', position=[17000, 9000, 0], radius_mm=60, room_id='tv-room', last_seen_tick=1900, confidence=1.0)
    organism._state['tested_non_nutritive'] = ['bottle-milk']
    organism._state['unsuccessful_bite_held_id'] = 'bottle-milk'
    organism._state['asleep'] = True
    organism._state['sleep_pressure'] = 0
    return organism

def test_cold_organism_restore_preserves_food_experience_exactly():
    organism = with_lived_food_evidence()
    before = organism.encoded()
    restored = FunctionalOrganism.restore(before)
    assert restored.encoded() == before

def test_real_wake_interval_provisions_without_crediting_intake_or_rewriting_beliefs():
    world = world_without_apple()
    organism = with_lived_food_evidence()
    before = copy.deepcopy(organism._state['conserved_objects'])
    meals = organism._state['meals_micrograms']
    result = FunctionalPhysicalLoop().settle(organism, world, UNATTENDED)
    assert not organism.asleep
    assert organism.live_organism_tick == 1999
    receipt = result.observation['food_replenishment']
    assert receipt['status'] == 'applied'
    assert receipt['external_digestible_mass_micrograms'] == 140000
    assert organism._state['meals_micrograms'] == meals
    assert result.observation['real_nutrition_intake_zeptojoules'] == 0
    for object_id, entry in before.items():
        for field, value in entry.items():
            assert organism._state['conserved_objects'][object_id][field] == value

def test_wake_failure_is_visible_and_does_not_replay_the_committed_interval(monkeypatch):
    world = world_without_apple()
    organism = with_lived_food_evidence()
    start = organism.live_organism_tick

    def fail(authority):
        raise ValueError('injected supply refusal')
    monkeypatch.setattr(home, 'replenish_home_food', fail)
    result = FunctionalPhysicalLoop().settle(organism, world, UNATTENDED)
    assert organism.live_organism_tick == start + 1
    assert not organism.asleep
    receipt = result.observation['food_replenishment']
    assert receipt['status'] == 'failed'
    assert receipt['error_type'] == 'ValueError'
    assert 'injected supply refusal' in receipt['error']
    assert not any((o.object_id == 'apple' for o in world.global_objects()))

def test_no_timer_restock_or_restore_provisioning_path():
    loop_tree = ast.parse((ROOT / 'dsf_ai_service/guala_functional_loop.py').read_text())
    advance = next((n for n in ast.walk(loop_tree) if isinstance(n, ast.FunctionDef) and n.name == '_advance'))
    assert not any((isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and isinstance(n.right, ast.Constant) and (n.right.value == 2000) for n in ast.walk(advance)))
    app = ast.parse((ROOT / 'dsf_ai_service/lean_production_app.py').read_text())
    restore = next((n for n in ast.walk(app) if isinstance(n, ast.FunctionDef) and n.name == '_restore_production_actor'))
    assert not any((isinstance(n, ast.Name) and n.id == 'replenish_home_food' for n in ast.walk(restore)))

@pytest.mark.parametrize('prior_state', ['missing', 'exhausted', 'residual', 'held'])
def test_backyard_apple_supply_preserves_mass_custody_and_cold_successor(prior_state):
    world = home.home_world_authority(identity=IDENTITY)
    with home._world_thermal_transaction(world):
        old = world._state.world
        apple = next((o for o in old.objects if o.object_id == 'garden-apple'))
        objects = old.objects
        bodies = old.bodies
        if prior_state == 'missing':
            objects = tuple((o for o in objects if o.object_id != apple.object_id))
        else:
            apple = replace(apple, material=replace(apple.material, digestible_mass_micrograms=1 if prior_state == 'residual' else 0))
            if prior_state == 'held':
                apple = replace(apple, position=None, held_by_body_id=old.self_body_id)
                bodies = tuple((replace(b, held_object_id=apple.object_id) if b.body_id == old.self_body_id else b for b in bodies))
            objects = tuple((apple if o.object_id == apple.object_id else o for o in objects))
        home._commit_world_successor(world, replace(old, revision=old.revision + 1, objects=objects, bodies=bodies))
    before = world.encoded_snapshot()
    before_mass = digestible(world)
    before_bodies = world._state.world.bodies
    receipt = home.replenish_home_food(world)
    supplied_mass = 140000 if prior_state != 'held' else 0
    assert receipt['external_digestible_mass_micrograms'] == supplied_mass
    assert digestible(world) - before_mass + receipt['external_removed_digestible_mass_micrograms'] == supplied_mass
    assert world._state.world.bodies == before_bodies
    if supplied_mass:
        assert receipt['replenished'] == ['garden-apple']
        supplied = next((o for o in world.global_objects() if o.object_id == 'garden-apple'))
        assert supplied.material.digestible_mass_micrograms == 140000
        assert (supplied.position.x, supplied.position.y) == ((14000, 14100) if prior_state == 'missing' else (14700, 14800))
    else:
        assert world.encoded_snapshot() == before
    successor = world.encoded_snapshot()
    restored = home.home_world_authority(identity=IDENTITY, encoded_world=successor, migrate_physical_return=False)
    assert restored.encoded_snapshot() == successor
    assert home.replenish_home_food(restored)['external_digestible_mass_micrograms'] == 0
    assert restored.encoded_snapshot() == successor
