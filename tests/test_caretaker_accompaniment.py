"""External caregiver movement is physical; pupil transport is forbidden."""
import hashlib
from dataclasses import replace
import pytest
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_caretaker_hand import escort_to_room, domestic_patrol, nothing_left_to_bite
from dsf_ai_service.lean_embodiment_observation import lean_embodiment_observation
from guala_caretaker import caretaker

IDENTITY = '1346a63d-e61b-49bb-b380-fa72756ec6b5'

def pupil(world):
    s = world.canonical_observation_snapshot()
    return next(b for b in s.bodies if b.body_id == s.self_body_id)

@pytest.mark.parametrize('room', ['kitchen', 'dining', 'backyard'])
def test_caregiver_invitation_uses_real_portals_without_pupil_relocation(room, monkeypatch):
    world = home_world_authority(identity=IDENTITY)
    before = pupil(world)
    def forbidden(*args, **kwargs):
        pytest.fail('authored body transport is not accompaniment')
    monkeypatch.setattr(type(world), 'admit_authored_body_transport', forbidden)
    result = escort_to_room(world, room)
    assert result['presented'], result
    assert not result['child_arrived']
    assert pupil(world).pose == before.pose
    assert any(s['operation'] == 'move' and s['reason'] == 'applied' for s in result['steps'])
    current = world.canonical_observation_snapshot()
    person = next(b for b in current.bodies if b.body_id != current.self_body_id)
    region = next(r for r in current.regions if r.region_id == room)
    assert region.bounds.contains_floor_disc(person.pose.position, person.radius_mm)
    # Exact paired world bytes preserve both bodies' actual outcomes.
    saved = world.encoded_snapshot()
    restored = home_world_authority(identity=IDENTITY, encoded_world=saved)
    assert restored.encoded_snapshot() == saved
    assert pupil(restored).pose == before.pose


def test_patrol_reports_unreachable_region_as_refused_without_false_success():
    world = home_world_authority(identity=IDENTITY)
    before = world.encoded_snapshot()
    result = domestic_patrol(world, 'nonexistent-room')
    assert result['presented'] is False
    assert world.encoded_snapshot() == before


def test_teacher_food_observation_uses_actual_material_and_oral_law():
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.canonical_observation_snapshot()
    body = pupil(world)
    observation = lean_embodiment_observation(snapshot, ())
    actual = {x.object_id: x for x in snapshot.objects}
    for item in observation['objects']:
        obj = actual[item['object_id']]
        assert item['oral_transfer_available'] == (not nothing_left_to_bite(body, obj))
        assert item['digestible_mass_micrograms'] == (None if obj.material is None else obj.material.digestible_mass_micrograms)
    o = {'last_occurrence': {'embodiment': observation}}
    _, foods = caretaker.food_state(o, set())
    assert foods
    assert all(not nothing_left_to_bite(body, actual[x]) for x in foods)


def test_hungry_tutor_preserves_foraging_and_does_not_decode_babble(tmp_path, monkeypatch):
    world = home_world_authority(identity=IDENTITY)
    emb = lean_embodiment_observation(world.canonical_observation_snapshot(), ())
    observation = {'live_tick': 20000, 'last_occurrence': {
        'metabolic_need_reserve_deficit': [1, 1], 'her_sleep': {'asleep': False},
        'embodiment': emb, 'said': 'pah0-lah0'}}
    requests = []
    monkeypatch.setattr(caretaker, 'present_food', lambda x: requests.append(x))
    monkeypatch.setattr(caretaker, 'STATE', str(tmp_path/'state.json'))
    monkeypatch.setattr(caretaker, 'LOG', str(tmp_path/'log'))
    state = {'next': 2305, 'presented': 2305}
    caretaker.maybe_feed(observation, state)
    assert requests == []
    assert state == {'next': 2305, 'presented': 2305}
