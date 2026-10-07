"""Physical depletion boundaries; no claim of learned or multi-room autonomy."""
from dataclasses import replace

from dsf_ai_service.guala_caretaker_hand import _is_core, nothing_left_to_bite, stray_core
from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism, _consequence_grounded_food_ids,
    _consequence_qualified_food_ids, candidates, is_genuine_food_object,
    things_in_sight,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.modular_column_substrate import ModularColumnSubstrate
from dsf_ai_service.substrate.embodiment_world import PositionMM

IDENTITY = '7a635ab2-225c-4222-98b4-975ce41b6a1a'


def scene(mass, taste=10, name='apple-spent'):
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    body = next(b for b in snapshot.bodies if b.body_id == snapshot.self_body_id)
    apple = next(o for o in snapshot.objects if o.object_id == 'apple')
    item = replace(apple, object_id=name,
                   position=PositionMM(body.pose.position.x + 600, body.pose.position.y, 0),
                   material=replace(apple.material, digestible_mass_micrograms=mass,
                                    tastant_mass_micrograms=(taste, 0, 0, 0, 0)))
    # This is a declared single-object component fixture, not body transport.
    return replace(snapshot, objects=(item,)), body, item


def test_zero_calorie_taste_residue_is_spent_but_positive_matter_is_preserved():
    snapshot, body, spent = scene(0)
    assert _is_core(spent)
    assert nothing_left_to_bite(body, spent)
    assert not is_genuine_food_object(spent, body)
    assert stray_core(snapshot, body).object_id == spent.object_id
    _, _, crumb = scene(2, taste=10)
    assert not _is_core(crumb)
    assert nothing_left_to_bite(body, crumb)
    assert not is_genuine_food_object(crumb, body)
    assert crumb.material.digestible_mass_micrograms == 2
    # A small enough object allows the same law to transfer a single microgram.
    small = replace(crumb, radius_mm=body.receptor_geometry.oral_radius_mm,
                    material=replace(crumb.material, digestible_mass_micrograms=1))
    assert not nothing_left_to_bite(body, small)
    assert is_genuine_food_object(small, body)
    assert spent.material.tastant_mass_micrograms == (10, 0, 0, 0, 0)


def test_food_eligibility_uses_material_not_a_name_or_taste_threshold():
    _, _, food = scene(100_000, taste=1600, name='unfamiliar-object')
    assert is_genuine_food_object(food)
    assert not is_genuine_food_object(replace(food, material=None))
    assert not is_genuine_food_object('apple')
    for name in ('apple-2', 'bread-slice', 'garden-apple', 'bottle-milk', 'unfamiliar-object'):
        zero = replace(food, object_id=name,
                       material=replace(food.material, digestible_mass_micrograms=0))
        assert not is_genuine_food_object(zero)


def test_current_mass_removes_core_from_all_nutrition_candidates_without_erasing_history():
    sub = ModularColumnSubstrate(columns=64)
    snapshot, body, spent = scene(0)
    history = {spent.object_id: {'position': (spent.position.x, spent.position.y, 0),
                                'radius_mm': spent.radius_mm, 'fed_count': 5,
                                'historical_intake_micrograms': 140_000, 'is_food': True}}
    import copy
    before = copy.deepcopy(history)
    options = candidates(snapshot, body, None, None, things_in_sight(snapshot), 1,
                         feeding=True, conserved_objects=history, modular_sub=sub)
    assert not any(c[0] in ('toward_food', 'grasp', 'take') and c[3] == spent.object_id for c in options)
    assert history == before
    fresh = replace(spent, material=replace(spent.material, digestible_mass_micrograms=3))
    fresh_snapshot = replace(snapshot, objects=(fresh,))
    history[spent.object_id]['currently_depleted'] = True
    before = copy.deepcopy(history)
    options = candidates(fresh_snapshot, body, None, None, things_in_sight(fresh_snapshot), 2,
                         feeding=True, conserved_objects=history, modular_sub=sub)
    assert any(c[0] in ('toward_food', 'grasp') and c[3] == fresh.object_id for c in options)
    assert history == before


def test_retained_actual_intake_is_not_rejected_by_object_spelling():
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state['meanings']['episode'] = {'consequences': {'bite': {
        'relief': 'feeding', 'intake': 7, 'target_id': 'unfamiliar-object'}}}
    organism._state['conserved_objects']['unfamiliar-object'] = {
        'historical_intake_micrograms': 7, 'fed_count': 1}
    before = organism.encoded()
    assert 'unfamiliar-object' in _consequence_grounded_food_ids(organism._state)
    assert 'unfamiliar-object' in _consequence_qualified_food_ids(organism._state)
    assert organism.encoded() == before
    assert FunctionalOrganism.restore(before).encoded() == before


def test_nutritional_eligibility_matches_actual_oral_transfer_without_destroying_crumbs():
    from dsf_ai_service.substrate.embodiment_world import OralContactCommand
    world = home_world_authority(identity=IDENTITY)
    state = world._state.world
    body = next(b for b in state.bodies if b.body_id == 'guala-body-1')
    for item in (o for o in state.objects if o.object_id in ('apple', 'bread-slice')):
        for mass in (0, 1, 2, 3, 4, 140000):
            food = replace(item, position=None, held_by_body_id=body.body_id,
                           material=replace(item.material, digestible_mass_micrograms=mass))
            held = replace(body, held_object_id=food.object_id)
            fixture = replace(state, bodies=tuple(held if b.body_id == held.body_id else b for b in state.bodies),
                              objects=tuple(food if o.object_id == food.object_id else o for o in state.objects))
            successor, status = world._transition(fixture, held.body_id, OralContactCommand(food.object_id, 250000))
            assert status == 'applied'
            result = next(b for b in successor.bodies if b.body_id == held.body_id).active_contact
            remaining = next(o for o in successor.objects if o.object_id == food.object_id).material.digestible_mass_micrograms
            assert is_genuine_food_object(food, held) == (result.transferred_digestible_micrograms > 0)
            assert nothing_left_to_bite(held, food) == (result.transferred_digestible_micrograms == 0)
            assert mass == remaining + result.transferred_digestible_micrograms
