import uuid
from dataclasses import replace

from dsf_ai_service.guala_home_world import home_world_authority, replenish_home_food, nocturnal_house_tidying
from dsf_ai_service.substrate.embodiment_world import (
    OralContactCommand,
    BodyContactState,
    PositionMM,
    PoseMM,
    _derived_contact_patch_square_mm,
    _receptor_position,
)


def test_crumb_scale_mastication_down_to_zero():
    """Verify that when an item has residual micro-crumbs (<= 100 ug),
    an oral contact action swallows the remaining crumbs completely down to 0 ug.
    """
    world = home_world_authority(identity=str(uuid.uuid4()))
    bread = next(o for o in world._state.world.objects if o.object_id == "bread-slice")

    # Simulate crumb-scale residue (4 micrograms remaining, matching live ECS bug observation)
    crumb_mat = replace(
        bread.material,
        tastant_mass_micrograms=(0, 4, 0, 0, 0),
        digestible_mass_micrograms=4,
    )
    crumb_bread = replace(bread, position=None, held_by_body_id="guala-body-1", material=crumb_mat)

    her = next(b for b in world._state.world.bodies if b.body_id == "guala-body-1")
    her = replace(her, held_object_id="bread-slice")

    w_state = replace(
        world._state.world,
        bodies=tuple(her if b.body_id == "guala-body-1" else b for b in world._state.world.bodies),
        objects=tuple(crumb_bread if o.object_id == "bread-slice" else o for o in world._state.world.objects),
    )

    next_world, status = world._transition(
        w_state,
        "guala-body-1",
        OralContactCommand(object_id="bread-slice", duration_microseconds=250_000),
    )
    assert status == "applied"
    after_bread = next(o for o in next_world.objects if o.object_id == "bread-slice")
    assert sum(after_bread.material.tastant_mass_micrograms) == 0, "Crumb tastants must be swallowed to 0"
    assert getattr(after_bread.material, "digestible_mass_micrograms", 0) == 0, "Crumb digestible mass must be 0"


def test_replenish_home_food_restores_missing_and_depleted_sustenance():
    """Verify that replenish_home_food detects depleted or absent food and atomically restocks fresh items."""
    world = home_world_authority(identity=str(uuid.uuid4()))

    # Remove apple and deplete bread-slice
    bread = next(o for o in world._state.world.objects if o.object_id == "bread-slice")
    depleted_bread = replace(
        bread,
        material=replace(
            bread.material,
            tastant_mass_micrograms=(0, 0, 0, 0, 0),
            digestible_mass_micrograms=0,
        ),
    )
    world._state = replace(
        world._state,
        world=replace(
            world._state.world,
            objects=tuple(
                depleted_bread if o.object_id == "bread-slice" else o
                for o in world._state.world.objects
                if o.object_id != "apple"
            ),
        ),
    )

    # Confirm apple is missing and bread is depleted
    assert not any(o.object_id == "apple" for o in world._state.world.objects)
    bread_before = next(o for o in world._state.world.objects if o.object_id == "bread-slice")
    assert sum(bread_before.material.tastant_mass_micrograms) == 0

    # Replenish
    replenished = replenish_home_food(world)
    assert "apple" in replenished
    assert "bread-slice" in replenished

    # Confirm apple is now present and bread has fresh tastants
    apple_after = next(o for o in world._state.world.objects if o.object_id == "apple")
    assert sum(apple_after.material.tastant_mass_micrograms) > 1000

    bread_after = next(o for o in world._state.world.objects if o.object_id == "bread-slice")
    assert sum(bread_after.material.tastant_mass_micrograms) > 1000


def test_replenish_home_food_preserves_busy_objects_under_active_contact():
    """Verify that replenish_home_food does NOT displace or teleport an object that is in active contact,
    avoiding breaking somatic geometry.
    """
    world = home_world_authority(identity=str(uuid.uuid4()))
    her = next(b for b in world._state.world.bodies if b.body_id == "guala-body-1")
    rec_pos = _receptor_position(her, her.receptor_geometry.oral_offset_mm)
    bread = next(o for o in world._state.world.objects if o.object_id == "bread-slice")
    bread_held = replace(
        bread,
        position=None,
        held_by_body_id="guala-body-1",
        material=replace(bread.material, tastant_mass_micrograms=(0, 0, 0, 0, 0), digestible_mass_micrograms=0),
    )

    patch = _derived_contact_patch_square_mm(
        receptor_position=rec_pos,
        receptor_radius_mm=her.receptor_geometry.oral_radius_mm,
        object_position=rec_pos,
        object_radius_mm=bread.radius_mm,
    )
    contact = BodyContactState(kind="oral", object_id="bread-slice", contact_patch_square_mm=patch, duration_microseconds=250_000)
    her_in_contact = replace(her, held_object_id="bread-slice", active_contact=contact)

    # Remove apple to ensure replenishment runs
    world._state = replace(
        world._state,
        world=replace(
            world._state.world,
            bodies=tuple(her_in_contact if b.body_id == "guala-body-1" else b for b in world._state.world.bodies),
            objects=tuple(bread_held if o.object_id == "bread-slice" else o for o in world._state.world.objects if o.object_id != "apple"),
        ),
    )

    # Replenish: apple should be replenished, but bread-slice must be preserved untouched
    replenished = replenish_home_food(world)
    assert "apple" in replenished
    assert "bread-slice" not in replenished, "Busy bread-slice must not be replenished while held in contact"

    # Confirm active contact and held custody is preserved exactly
    bread_after = next(o for o in world._state.world.objects if o.object_id == "bread-slice")
    assert bread_after.held_by_body_id == "guala-body-1"
    her_after = next(b for b in world._state.world.bodies if b.body_id == "guala-body-1")
    assert her_after.active_contact == contact


def test_nocturnal_tidying_restocks_nourishment():
    """Verify nocturnal_house_tidying restocks nourishing food during sleep."""
    world = home_world_authority(identity=str(uuid.uuid4()))

    # Remove all foods
    world._state = replace(
        world._state,
        world=replace(
            world._state.world,
            objects=tuple(
                o for o in world._state.world.objects
                if o.object_id not in ("apple", "bread-slice", "bottle-milk")
            ),
        ),
    )
    assert not any(o.object_id in ("apple", "bread-slice", "bottle-milk") for o in world._state.world.objects)

    # Execute nocturnal tidying
    nocturnal_house_tidying(world)

    # Confirm all three items are back in the home
    obj_ids = {o.object_id for o in world._state.world.objects}
    assert "apple" in obj_ids
    assert "bread-slice" in obj_ids
    assert "bottle-milk" in obj_ids
