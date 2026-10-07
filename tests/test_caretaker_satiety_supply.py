"""External supplier honors exact organism satiety; never changes body reserve."""
from fractions import Fraction
import copy
import pytest
from guala_caretaker import caretaker
from dsf_ai_service.guala_functional_organism import SATED_ABOVE

@pytest.mark.parametrize('reserve', [0, 299999, 300000, 345739, 424999, 425000, 500000])
def test_supplier_continues_past_lesson_hunger_until_actual_satiety(tmp_path, monkeypatch, reserve):
    assert SATED_ABOVE == Fraction(17, 20)
    calls = []
    monkeypatch.setattr(caretaker, 'STATE', str(tmp_path/'teacher-state.json'))
    monkeypatch.setattr(caretaker, 'LOG', str(tmp_path/'teacher.log'))
    monkeypatch.setattr(caretaker, 'say_word', lambda food: 0)
    monkeypatch.setattr(caretaker, 'present_food', lambda food: calls.append(food) or {'presented': True})
    obs = {'live_tick': 4000000, 'last_occurrence': {
        'her_sleep': {'asleep': False},
        'reserve_micrograms': reserve, 'reserve_capacity_micrograms': 500000,
        'metabolic_need_reserve_deficit': [500000-reserve, 500000],
        'embodiment': {'self_body_id': 'pupil', 'bodies': [{'body_id': 'pupil', 'reach_mm': 800, 'pose': {'position': {'x_mm': 0, 'y_mm': 0}}}],
                      'objects': [{'object_id': 'retained-crumb', 'oral_transfer_available': False, 'digestible_mass_micrograms': 2}]}}}
    before = copy.deepcopy(obs)
    state = {'next': 2305, 'presented': 2305, 'meal_cycle_index': 92}
    caretaker.maybe_feed(obs, state)
    assert calls == (['replenish-home-food'] if reserve < 425000 else [])
    assert obs == before
    assert state['next'] == 2305 and state['presented'] == 2305


def test_available_world_food_leaves_acquisition_to_the_pupil(tmp_path, monkeypatch):
    calls=[]
    monkeypatch.setattr(caretaker,'present_food',lambda x:calls.append(x))
    o={'live_tick':4000000,'last_occurrence':{'metabolic_need_reserve_deficit':[4,10],
       'embodiment':{'self_body_id':'pupil','bodies':[{'body_id':'pupil','reach_mm':800,'pose':{'position':{'x_mm':0,'y_mm':0}}}],
                    'objects':[{'object_id':'unknown-name','oral_transfer_available':True,'digestible_mass_micrograms':100000,'position':{'x_mm':2000,'y_mm':0}}]}}}
    caretaker.maybe_feed(o,{'meal_tick':0})
    assert calls==[]


def test_environmental_restock_is_actual_world_matter_without_moving_bodies():
    from dsf_ai_service.guala_home_world import home_world_authority
    from dsf_ai_service.guala_caretaker_hand import present_food
    world = home_world_authority(identity='883a68c7-bd6c-43f4-a2c2-e72b5a5b2c42')
    world.admit_authored_departure('bottle-milk')  # declared stock exhaustion fixture
    before = world.canonical_observation_snapshot()
    mass = lambda s: sum(x.material.digestible_mass_micrograms for x in s.objects if x.material)
    result = present_food(world, 'replenish-home-food')
    after = world.canonical_observation_snapshot()
    receipt = result['provision']
    assert result['presented'] and receipt['replenished'] == ['bottle-milk']
    assert mass(after)-mass(before) == receipt['external_digestible_mass_micrograms'] == 100000
    assert after.bodies == before.bodies
    milk = next(x for x in after.objects if x.object_id == 'bottle-milk')
    assert milk.held_by_body_id is None
    encoded = world.encoded_snapshot()
    restored = home_world_authority(identity='883a68c7-bd6c-43f4-a2c2-e72b5a5b2c42', encoded_world=encoded)
    assert restored.encoded_snapshot() == encoded
    assert present_food(restored, 'replenish-home-food')['provision']['status'] == 'unchanged'
    assert restored.encoded_snapshot() == encoded
