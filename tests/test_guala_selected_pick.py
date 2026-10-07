"""Physical selection and support-surface pickup; no autonomous-route claim."""
from dataclasses import replace
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_functional_organism import candidates, things_in_sight
from dsf_ai_service.substrate.embodiment_world import PickCommand, GraspContactCommand, PlaceCommand, PositionMM
from dsf_ai_service.substrate.modular_column_substrate import ModularColumnSubstrate
IDENTITY = '7a635ab2-225c-4222-98b4-975ce41b6a1a'


def fixture():
    world = home_world_authority(identity=IDENTITY)
    state = world._state.world
    body = next(b for b in state.bodies if b.body_id == state.self_body_id)
    origin = body.pose.position
    food = replace(next(o for o in state.objects if o.object_id == 'bottle-milk'),
                   position=PositionMM(origin.x + 500, origin.y, 0))
    support = replace(next(o for o in state.objects if o.object_id == 'pillow'), position=food.position)
    return world, replace(state, objects=(food, support)), body, food, support


def test_targeted_pick_reverses_lawful_placement_on_support():
    world, state, body, food, support = fixture()
    old, reason = world._transition(state, body.body_id, GraspContactCommand(250000))
    assert old is None and reason == 'grasp_contact_ambiguous'
    picked, reason = world._transition(state, body.body_id, PickCommand(food.object_id, 250000))
    assert reason == 'applied'
    assert next(b for b in picked.bodies if b.body_id == body.body_id).held_object_id == food.object_id
    picked_food = next(o for o in picked.objects if o.object_id == food.object_id)
    assert picked_food.material.digestible_mass_micrograms == food.material.digestible_mass_micrograms
    assert picked_food.material.tastant_mass_micrograms == food.material.tastant_mass_micrograms
    retained_support = next(o for o in picked.objects if o.object_id == support.object_id)
    assert retained_support.position == support.position
    assert retained_support.held_by_body_id == support.held_by_body_id
    assert retained_support.material.digestible_mass_micrograms == support.material.digestible_mass_micrograms
    assert retained_support.material.tastant_mass_micrograms == support.material.tastant_mass_micrograms
    placed, reason = world._transition(picked, body.body_id, PlaceCommand(food.object_id, food.position, 250000))
    assert reason == 'applied'
    assert next(o for o in placed.objects if o.object_id == food.object_id).position == food.position


def test_targeted_pick_still_refuses_rigid_obstruction_and_distant_food():
    world, state, body, food, support = fixture()
    blocker = replace(support, object_id='rigid-obstacle', radius_mm=30,
                      position=PositionMM(body.pose.position.x+350, body.pose.position.y, 0))
    blocked = replace(state, objects=(food, blocker))
    result, reason = world._transition(blocked, body.body_id, PickCommand(food.object_id, 250000))
    assert result is None and reason == 'pick_path_intersects_object'
    far = replace(food, position=PositionMM(body.pose.position.x+body.reach_mm+food.radius_mm, body.pose.position.y, 0))
    result, reason = world._transition(replace(state, objects=(far,)), body.body_id, PickCommand(food.object_id,250000))
    assert result is None and reason == 'pick_out_of_reach'


def test_nutritional_candidate_carries_its_selected_physical_object():
    world, state, body, food, support = fixture()
    snapshot = replace(world.canonical_observation_snapshot(), objects=state.objects)
    options = candidates(snapshot, body, None, None, things_in_sight(snapshot), 1,
                         feeding=True, modular_sub=ModularColumnSubstrate(columns=64))
    grasp = next(o for o in options if o[0] == 'grasp')
    assert grasp[3] == food.object_id
    assert grasp[2] == (PickCommand(food.object_id,250000),)
