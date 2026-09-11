"""Canonical physical home authority for the lean Guala runtime.

This module is environment anatomy only. It owns no organism, scheduler,
observer, persistence, lesson, action choice, or cognition.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
from typing import Any, Iterable
import uuid


TOUCH_RECEPTORS_AUTHORIZED = True
HOME_BOOK_OBJECT_ID = "book"

HOME_ROOM_SPAN_MM = 4_000
HOME_CEILING_MM = 2_600
# The backyard has no ceiling but the sky; this is the honest
# bound of the modelled air column above it, not a room lid.
BACKYARD_SKY_MM = 8_000


def _home_rooms_and_things() -> tuple[list[Any], list[Any], list[Any]]:
    """Her home, delivered from Eve's map (docs/GUALA_WORLD_EXPANSION_
    BLUEPRINT_20260831.md): a 20m x 16m lot — nine places including a
    full-width backyard under a high sky, a hallway spine wide enough
    for three bodies abreast, her own room with window wall, curtains,
    wall art and a toy chest, a library, a television room, a dining
    room, and the two absence rooms with an address. Every corridor
    keeps the five-body law (>= 1500mm clear); every thing is declared
    physically in all of her senses; nothing is mimed."""

    from dsf_ai_service.substrate.embodiment_world import (
        AirVolumeState,
        EmbodiedObject,
        ObjectMaterialState,
        PhysicalPortal,
        PhysicalRegion,
        PositionMM,
        RoomBoundsMM,
    )

    # (id, min_x, min_y, max_x, max_y, ceiling, light)
    plan = (
        ("kitchen",       0,      0,  7_000,  5_000, HOME_CEILING_MM, 900_000),
        ("dining",        7_000,  0, 12_000,  5_000, HOME_CEILING_MM, 820_000),
        ("daddys-room",  12_000,  0, 16_000,  5_000, HOME_CEILING_MM, 700_000),
        ("wcs-room",     16_000,  0, 20_000,  5_000, HOME_CEILING_MM, 700_000),
        ("her-room",      0,  5_000,  5_600, 10_000, HOME_CEILING_MM, 780_000),
        ("hallway",       5_600, 5_000, 9_000, 10_000, HOME_CEILING_MM, 760_000),
        ("library",       9_000, 5_000, 14_000, 10_000, HOME_CEILING_MM, 800_000),
        ("tv-room",      14_000, 5_000, 20_000, 10_000, HOME_CEILING_MM, 740_000),
        # The backyard's ceiling is the sky: tall, bright, outdoors.
        ("backyard",      0, 10_000, 20_000, 16_000, BACKYARD_SKY_MM, 950_000),
    )
    regions = [
        PhysicalRegion(
            region_id=name,
            bounds=RoomBoundsMM(
                minimum=PositionMM(min_x, min_y, 0),
                maximum=PositionMM(max_x, max_y, ceiling),
            ),
            ceiling_height_mm=ceiling,
            reflectance_ppm=(
                (480_000,) * 6 if name == "backyard" else (620_000,) * 6
            ),
            illumination_ppm=(light,) * 6,
        )
        for name, min_x, min_y, max_x, max_y, ceiling, light in plan
    ]
    # Doors 1.4m wide minimum; the hallway connects everything and the
    # backyard opens from the hallway, exactly as the blueprint says.
    portals = [
        PhysicalPortal(
            portal_id=f"door-{index}",
            region_ids=tuple(sorted(pair)),
            axis=axis,
            plane_mm=plane,
            aperture_min_mm=ap_min,
            aperture_max_mm=ap_max,
            height_mm=2_050,
        )
        for index, (pair, axis, plane, ap_min, ap_max) in enumerate((
            (("kitchen", "dining"),        "x",  7_000, 1_800, 3_200),
            (("dining", "daddys-room"),    "x", 12_000, 1_800, 3_200),
            (("daddys-room", "wcs-room"),  "x", 16_000, 1_800, 3_200),
            (("her-room", "hallway"),      "x",  5_600, 6_900, 8_300),
            (("hallway", "library"),       "x",  9_000, 6_900, 8_300),
            (("library", "tv-room"),       "x", 14_000, 6_900, 8_300),
            (("kitchen", "hallway"),       "y",  5_000, 5_600, 7_000),
            (("dining", "hallway"),        "y",  5_000, 7_300, 8_700),
            (("hallway", "backyard"),      "y", 10_000, 6_000, 7_400),
        ))
    ]
    # (id, absolute x, y, radius, mass, reflectance) — clearances are
    # pre-checked against every neighbouring radius and wall.
    furniture = (
        # kitchen, relaid uncluttered: a clear ring around the table.
        ("table",           2_000,  1_500, 850, 28_000, (700_000, 620_000, 520_000, 450_000, 410_000, 390_000)),
        ("table-chair",     2_000,  3_000, 320,  6_000, (300_000, 260_000, 240_000, 220_000, 210_000, 200_000)),
        ("bowl",            4_500,    800, 160,    700, (920_000, 910_000, 900_000, 880_000, 860_000, 840_000)),
        ("cup",             5_200,    800, 110,    300, (880_000, 870_000, 860_000, 840_000, 820_000, 800_000)),
        ("apple",           5_650,    900,  90,    180, (820_000, 260_000, 190_000, 170_000, 160_000, 150_000)),
        # her room: bed wall, soft things, desk corner, art at eye height.
        ("bed",             1_200,  8_800, 900, 40_000, (760_000, 720_000, 690_000, 640_000, 600_000, 560_000)),
        ("pillow",          1_200,  7_600, 260,  1_200, (900_000, 890_000, 880_000, 860_000, 840_000, 820_000)),
        ("blanket",         3_400,  9_300, 300,    900, (860_000, 620_000, 540_000, 500_000, 470_000, 450_000)),
        ("toy-bear",        4_800,  9_200, 180,    400, (520_000, 380_000, 300_000, 260_000, 240_000, 220_000)),
        ("toy-chest",       1_000,  5_600, 500,  8_000, (560_000, 430_000, 340_000, 300_000, 280_000, 260_000)),
        ("desk",            4_000,  6_400, 800, 32_000, (430_000, 330_000, 260_000, 220_000, 200_000, 190_000)),
        ("desk-chair",      5_150,  6_400, 320,  6_000, (300_000, 260_000, 240_000, 220_000, 210_000, 200_000)),
        ("curtains",        2_800,  9_700, 250,  1_500, (930_000, 760_000, 620_000, 540_000, 500_000, 470_000)),
        ("wall-art-shapes", 300,    7_000, 150,    600, (950_000, 300_000, 850_000, 200_000, 750_000, 250_000)),
        ("wall-art-weather", 300,   6_100, 150,    600, (350_000, 550_000, 900_000, 400_000, 650_000, 300_000)),
        ("glow-stars",      2_200,  9_700, 120,    300, (940_000, 930_000, 700_000, 400_000, 300_000, 260_000)),
        # library: shelves on the north wall, the reading lamp, a book home.
        ("shelf-a",        10_000,  9_500, 400, 30_000, (500_000, 400_000, 330_000, 290_000, 270_000, 250_000)),
        ("shelf-b",        12_500,  9_500, 400, 30_000, (500_000, 400_000, 330_000, 290_000, 270_000, 250_000)),
        ("book",           12_000,  7_500, 140,    900, (640_000, 520_000, 420_000, 360_000, 330_000, 310_000)),
        ("lamp",           13_500,  5_400, 180,  2_200, (880_000, 850_000, 780_000, 700_000, 650_000, 620_000)),
        # tv room: the watching place.
        ("television",     17_000,  9_200, 700, 12_000, (140_000, 140_000, 150_000, 160_000, 170_000, 180_000)),
        ("sofa",           17_000,  6_800, 950, 45_000, (360_000, 330_000, 380_000, 420_000, 430_000, 420_000)),
        ("rug",            15_000,  6_000, 600,  5_000, (540_000, 420_000, 360_000, 330_000, 320_000, 310_000)),
        # dining room.
        ("dining-table",    9_500,  2_500, 900, 30_000, (700_000, 620_000, 520_000, 450_000, 410_000, 390_000)),
        ("dining-chair",    9_500,  4_200, 320,  6_000, (300_000, 260_000, 240_000, 220_000, 210_000, 200_000)),
        # backyard: slide, swing, sandbox, garden patch under the sky.
        ("slide",           3_000, 13_500, 900, 25_000, (700_000, 720_000, 740_000, 700_000, 650_000, 600_000)),
        ("swing",           7_000, 14_000, 700, 15_000, (480_000, 430_000, 380_000, 340_000, 320_000, 300_000)),
        ("sandbox",        11_500, 13_500, 1_100, 60_000, (820_000, 780_000, 700_000, 620_000, 560_000, 520_000)),
        ("garden-patch",   16_500, 13_500, 1_200, 80_000, (300_000, 380_000, 300_000, 260_000, 240_000, 220_000)),
    )
    # (release ng/s per odour channel, tastants ug, surface mK, compliance
    #  ppm, roughness um, moisture ppm) — same channel meanings as before:
    #  0 fruit ester - 1 cooked savoury - 2 dairy fat - 3 wood/earth
    #  4 fabric dust - 5 paper ink - 6 warm electronics - 7 soap
    material_of = {
        "bed":             ((0, 0, 0, 0, 900, 0, 0, 120),   (0, 300, 0, 800, 0),        294_000, 600_000, 200, 55_000),
        "pillow":          ((0, 0, 0, 0, 600, 0, 0, 300),   (0, 300, 0, 800, 0),        294_000, 900_000, 120, 48_000),
        "blanket":         ((0, 0, 0, 0, 1_000, 0, 0, 150), (0, 300, 0, 800, 0),        294_000, 850_000, 150, 50_000),
        "toy-bear":        ((0, 0, 0, 0, 1_200, 0, 0, 60),  (0, 300, 0, 900, 0),        294_000, 800_000, 300, 42_000),
        "toy-chest":       ((0, 0, 0, 600, 80, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 50_000, 60, 20_000),
        "desk":            ((0, 0, 0, 700, 60, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "desk-chair":      ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "curtains":        ((0, 0, 0, 0, 700, 0, 0, 100),   (0, 0, 0, 600, 0),          293_000, 800_000, 120, 45_000),
        "wall-art-shapes": ((0, 0, 0, 30, 20, 700, 0, 0),   (0, 0, 0, 1_800, 0),        294_000, 60_000, 50, 18_000),
        "wall-art-weather": ((0, 0, 0, 30, 20, 700, 0, 0),  (0, 0, 0, 1_800, 0),        294_000, 60_000, 50, 18_000),
        "glow-stars":      ((0, 0, 0, 0, 10, 0, 120, 0),    (0, 0, 0, 900, 0),          294_000, 30_000, 10, 3_000),
        "book":            ((0, 0, 0, 40, 30, 900, 0, 0),   (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "shelf-a":         ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "shelf-b":         ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "lamp":            ((0, 0, 0, 0, 20, 0, 260, 0),    (0, 0, 0, 400, 0),          310_000, 20_000, 10, 2_000),
        "television":      ((0, 0, 0, 0, 40, 0, 700, 0),    (0, 0, 0, 400, 0),          306_000, 20_000, 5, 1_000),
        "sofa":            ((0, 0, 0, 120, 1_500, 0, 0, 90), (0, 300, 0, 800, 0),       294_000, 700_000, 400, 52_000),
        "rug":             ((0, 0, 0, 0, 2_200, 0, 0, 40),  (0, 300, 0, 900, 0),        294_000, 500_000, 800, 46_000),
        "table":           ((0, 0, 0, 800, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "table-chair":     ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "dining-table":    ((0, 0, 0, 800, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "dining-chair":    ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "bowl":            ((0, 300, 120, 0, 0, 0, 0, 200), (400, 900, 100, 200, 1_200), 294_000, 30_000, 8, 90_000),
        "apple":           ((4_200, 0, 0, 0, 0, 0, 0, 0),   (140_000, 200, 26_000, 900, 300), 292_000, 120_000, 15, 850_000),
        "cup":             ((0, 60, 40, 0, 0, 0, 0, 400),   (0, 0, 0, 0, 0),            291_000, 25_000, 6, 900_000),
        "slide":           ((0, 0, 0, 0, 30, 0, 80, 0),     (0, 0, 0, 300, 0),          288_000, 15_000, 8, 10_000),
        "swing":           ((0, 0, 0, 300, 400, 0, 0, 0),   (0, 200, 0, 900, 0),        288_000, 250_000, 300, 30_000),
        "sandbox":         ((0, 0, 0, 100, 600, 0, 0, 0),   (0, 100, 0, 400, 0),        290_000, 400_000, 900, 25_000),
        "garden-patch":    ((0, 0, 0, 1_600, 300, 0, 0, 0), (0, 100, 200, 700, 100),    289_000, 450_000, 700, 320_000),
    }
    reservoir_seconds = 864_000
    # Things that give off their own light (the emitter law): the lamp
    # shines warm, the glow stars glow softly — visible when her room
    # goes dark because emission does not fade with the room's light.
    emission_of = {
        "lamp": (620_000, 540_000, 380_000, 220_000, 160_000, 120_000),
        "glow-stars": (30_000, 90_000, 120_000, 60_000, 20_000, 10_000),
    }
    objects = [
        EmbodiedObject(
            name,
            radius,
            mass,
            PositionMM(x, y, 0),
            emission_ppm=emission_of.get(name, ()),
            reflectance_ppm=reflectance,
            material=ObjectMaterialState(
                odorant_reservoir_nanograms=tuple(
                    rate * reservoir_seconds for rate in material_of[name][0]
                ),
                odorant_release_nanograms_per_second=material_of[name][0],
                tastant_mass_micrograms=material_of[name][1],
                surface_temperature_millikelvin=material_of[name][2],
                compliance_ppm=material_of[name][3],
                roughness_micrometers=material_of[name][4],
                moisture_ppm=material_of[name][5],
            ),
        )
        for name, x, y, radius, mass, reflectance in furniture
    ]
    # Each room's air is derived from what stands in it, exactly as before,
    # with room membership resolved from each thing's authored position.
    def room_of(x: int, y: int) -> str:
        for name, min_x, min_y, max_x, max_y, _c, _l in plan:
            if min_x <= x < max_x and min_y <= y < max_y:
                return name
        raise RuntimeError(f"authored thing stands outside every room ({x},{y})")

    settled_seconds = 3_600
    channel_count = len(material_of["apple"][0])
    room_air = {name: [0] * channel_count for name, *_rest in plan}
    for name, x, y, *_rest in furniture:
        for channel, rate in enumerate(material_of[name][0]):
            room_air[room_of(x, y)][channel] += rate * settled_seconds
    bounds_of = {name: (min_x, min_y, max_x, max_y, ceiling)
                 for name, min_x, min_y, max_x, max_y, ceiling, _l in plan}
    regions = [
        replace(
            region,
            air=AirVolumeState(
                volume_cubic_mm=(
                    (bounds_of[region.region_id][2] - bounds_of[region.region_id][0])
                    * (bounds_of[region.region_id][3] - bounds_of[region.region_id][1])
                    * bounds_of[region.region_id][4]
                ),
                odorant_mass_nanograms=tuple(room_air[region.region_id]),
            ),
        )
        for region in regions
    ]
    portals = [
        replace(portal, air_flow_cubic_mm_per_second=2_000_000)
        for portal in portals
    ]
    return regions, portals, objects


def _home_thermal_anatomy(
    regions: Iterable[Any], portals: Iterable[Any]
) -> Any:
    """Derive one bounded core/skin/home heat circuit from signed geometry.

    This is Phase-1 virtual anatomy, not a claim about a later manufactured
    body. The child mass is the CDC female 48.5-month median rounded to one
    gram; the two-node capacity uses the published 2.98 kJ/(kg K) whole-body
    specific heat and a declared 90/10 core/skin partition. Air capacity and
    portal conductance derive from each room volume and doorway flow. The only
    authored building value is a finite HVAC boundary conductance at 23 C.
    """

    from dsf_ai_service.substrate.bounded_home_thermal_physics import (
        ConductiveThermalEdge,
        ThermalBathEdge,
        ThermalPowerSource,
    )
    from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
        CoupledThermalAnatomy,
    )

    ordered_regions = tuple(sorted(regions, key=lambda item: item.region_id))
    ordered_portals = tuple(sorted(portals, key=lambda item: item.portal_id))
    if not ordered_regions or any(item.air is None for item in ordered_regions):
        raise ValueError("the thermal home requires finite signed air volumes")
    room_index = {
        region.region_id: index for index, region in enumerate(ordered_regions)
    }
    # 1210.120 J/(m3 K), represented as uJ/(m3 mK).
    air_capacity_per_cubic_meter = 1_210_120
    room_capacities = tuple(
        region.air.volume_cubic_mm * air_capacity_per_cubic_meter
        // 1_000_000_000
        for region in ordered_regions
    )
    # 15.878 kg * 2.98 kJ/(kg K) = 47,316.44 J/K. On the module's
    # uJ/mK lattice that is 47,316,440, split without losing one quantum.
    whole_body_capacity = 15_878 * 2_980
    skin_capacity = whole_body_capacity // 10
    core_capacity = whole_body_capacity - skin_capacity
    skin_index = len(ordered_regions)
    core_index = skin_index + 1
    portal_edges = []
    for portal in ordered_portals:
        flow = portal.air_flow_cubic_mm_per_second
        if flow is None:
            raise ValueError("the thermal home requires signed portal air flow")
        left, right = portal.region_ids
        portal_edges.append(
            ConductiveThermalEdge(
                room_index[left],
                room_index[right],
                flow * air_capacity_per_cubic_meter // 1_000_000,
            )
        )
    metabolic_power = 41_500_000
    return CoupledThermalAnatomy(
        node_ids=(
            *(f"air:{region.region_id}" for region in ordered_regions),
            "body:cutaneous-shell",
            "body:core",
        ),
        initial_temperatures_millikelvin=(
            *(
                (293_150 if region.region_id == "backyard" else 296_150)
                for region in ordered_regions
            ),
            303_150,
            309_950,
        ),
        capacities_microjoules_per_millikelvin=(
            *room_capacities,
            skin_capacity,
            core_capacity,
        ),
        fixed_conductive_edges=(
            *portal_edges,
            ConductiveThermalEdge(core_index, skin_index, 6_102_941),
        ),
        room_air_node_by_region_id=tuple(
            (region.region_id, room_index[region.region_id])
            for region in ordered_regions
        ),
        skin_node_index=skin_index,
        core_node_index=core_index,
        skin_air_conductance_microwatts_per_kelvin=5_928_571,
        # Indoor rooms couple to the authored HVAC boundary; the backyard
        # is outdoors and couples hard to the open sky's own ambient.
        bath_edges=tuple(
            (
                ThermalBathEdge(index, 293_150, 2_500_000_000)
                if region.region_id == "backyard"
                else ThermalBathEdge(index, 296_150, 250_000_000)
            )
            for index, region in enumerate(ordered_regions)
        ),
        power_sources=(ThermalPowerSource(core_index, metabolic_power),),
        parameter_provenance=(
            "CDC female 48.5-month median body mass rounded to 15.878 kilograms",
            "measured whole-body specific heat 2.98 kilojoules per kilogram-kelvin",
            "FAO-WHO-UNU girls age 3-to-10 basal metabolic equation at declared mass",
            "published passive two-node core-skin heat-balance structure",
            "authored Phase-1 virtual-home 296150-millikelvin HVAC boundary",
        ),
    )



def _companion_body_surface_sites() -> tuple[Any, ...]:
    """Declare the bounded skin sites used by exact reciprocal contact.

    These are morphology, not gesture meanings.  Their material coefficients
    are pinned by three explicit substrate-scale reference responses:

    * a fully covered 60 x 80 mm palm compressed by 1 mm carries 9.6 N;
    * the same palm sliding 10 mm over one second carries 0.96 N tangentially;
    * the same palm held across a 1 K difference for one second transfers
      0.48 J.

    The coefficients are therefore derived once from those declarations and
    are never tuned by a lesson, behavior, or observer.  Guala's temperature
    is read from her live cutaneous thermal node; 310.15 K is the participant
    surface's declared finite reservoir boundary until that body gains its own
    thermal circulation.
    """

    if not TOUCH_RECEPTORS_AUTHORIZED:
        return ()
    from dsf_ai_service.substrate.body_surface_contact import (
        BodySurfaceMaterial,
        ExactVector3,
    )
    from dsf_ai_service.substrate.embodiment_world import (
        MountedBodySurfaceSite,
    )

    exact = Fraction
    x = ExactVector3(exact(1), exact(0), exact(0))
    y = ExactVector3(exact(0), exact(1), exact(0))
    z = ExactVector3(exact(0), exact(0), exact(1))
    skin = BodySurfaceMaterial(
        normal_stiffness_millinewtons_per_micrometre_per_square_micrometre=(
            exact(1, 500_000_000)
        ),
        tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre=(
            exact(1, 50_000)
        ),
        thermal_conductance_nanowatts_per_square_micrometre_millikelvin=(
            exact(1, 10_000)
        ),
    )

    def site(
        body_id: str,
        site_id: str,
        centre: tuple[int, int, int],
        normal: Any,
        tangent_u: Any,
        tangent_v: Any,
        half_extents: tuple[int, int],
        cutaneous_topology_index: int | None,
    ) -> Any:
        return MountedBodySurfaceSite(
            body_id=body_id,
            site_id=site_id,
            local_centre_micrometres=ExactVector3(
                *(exact(value) for value in centre)
            ),
            outward_normal=normal,
            tangent_u=tangent_u,
            tangent_v=tangent_v,
            half_extent_u_micrometres=exact(half_extents[0]),
            half_extent_v_micrometres=exact(half_extents[1]),
            material=skin,
            reference_temperature_millikelvin=310_150,
            cutaneous_topology_index=cutaneous_topology_index,
        )

    # The existing 3 x 9 contact sheet is Guala's declared body-surface
    # lattice.  These sparse morphology sites bind seven previously unnamed
    # locations without changing their native topology or receptor law.
    guala = (
        site("guala-body-1", "forehead", (230_000, 0, 1_100_000), x, y, z, (70_000, 55_000), 4),
        site("guala-body-1", "crown", (0, 0, 1_250_000), z, x, y, (75_000, 65_000), 3),
        site("guala-body-1", "left-shoulder", (180_000, 170_000, 900_000), x, y, z, (80_000, 75_000), 9),
        site("guala-body-1", "front-torso", (240_000, 0, 700_000), x, y, z, (150_000, 190_000), 13),
        site("guala-body-1", "right-shoulder", (180_000, -170_000, 900_000), x, y, z, (80_000, 75_000), 17),
        site("guala-body-1", "left-palm", (300_000, 150_000, 500_000), x, y, z, (30_000, 40_000), 18),
        site("guala-body-1", "right-palm", (300_000, -150_000, 500_000), x, y, z, (30_000, 40_000), 26),
    )
    # A facing participant has the opposite heading.  Its local lateral
    # tangents are therefore reversed so the two world-space contact bases
    # become exactly aligned when the surfaces oppose each other.
    participant = (
        site("person-body-1", "left-palm", (300_000, 200_000, 800_000), x, y.scaled(exact(-1)), z, (30_000, 40_000), None),
        site("person-body-1", "right-palm", (300_000, -200_000, 800_000), x, y.scaled(exact(-1)), z, (30_000, 40_000), None),
        site("person-body-1", "front-torso", (250_000, 0, 1_000_000), x, y.scaled(exact(-1)), z, (180_000, 260_000), None),
        site("person-body-1", "perioral", (260_000, 0, 1_450_000), x, y.scaled(exact(-1)), z, (25_000, 20_000), None),
        site("person-body-1", "downward-palm", (250_000, -180_000, 1_050_000), z.scaled(exact(-1)), x.scaled(exact(-1)), y.scaled(exact(-1)), (30_000, 40_000), None),
    )
    return guala + participant


def world_authority_key(identity: str) -> str:
    """Derive the stable authentication key for this organism's one world."""

    if not isinstance(identity, str):
        raise TypeError("organism identity is not text")
    try:
        parsed = uuid.UUID(identity)
    except ValueError as error:
        raise ValueError("organism identity is not canonical UUID text") from error
    if str(parsed) != identity:
        raise ValueError("organism identity is not canonical UUID text")
    return hashlib.sha256(
        f"guala.embodiment.world.v1:{identity}".encode("utf-8")
    ).hexdigest()


def home_world_authority(
    *,
    identity: str,
    encoded_world: bytes | None = None,
    migrate_physical_return: bool = False,
) -> Any:
    """Build the declared home and optionally cold-restore its exact state."""

    from dsf_ai_service.substrate.embodiment_world import (
        BodyReceptorGeometry,
        EmbodiedBody,
        EmbodimentPort,
        PORT_ID,
        SECOND_BODY_PORT_ID,
        PoseMM,
        PositionMM,
        ScreenBroadcast,
        SolarCoupling,
    )
    from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
        ThermallyCoupledEmbodimentWorldAuthority,
    )

    receptors = BodyReceptorGeometry(
        retinal_offset_mm=PositionMM(200, 0, 1_100),
        left_ear_offset_mm=PositionMM(0, 0, 1_050),
        right_ear_offset_mm=PositionMM(0, 180, 1_050),
        touch_offset_mm=PositionMM(200, 0, 150),
        touch_radius_mm=300,
        oral_offset_mm=PositionMM(200, 0, 1_020),
        oral_radius_mm=60,
        olfactory_offset_mm=PositionMM(210, 0, 1_060),
        odorant_saturation_nanograms_per_cubic_meter=(1_000_000,) * 8,
        tastant_saturation_micrograms=(200_000,) * 5,
        touch_mass_span_grams=45_000,
        touch_temperature_min_millikelvin=273_000,
        touch_temperature_max_millikelvin=323_000,
        touch_roughness_span_micrometers=1_000,
    )
    regions, portals, objects = _home_rooms_and_things()
    authority = ThermallyCoupledEmbodimentWorldAuthority(
        authority_key=world_authority_key(identity),
        thermal_anatomy=_home_thermal_anatomy(regions, portals),
        self_body_id="guala-body-1",
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(2_600, 7_600, 0), 0),
                radius_mm=250,
                reach_mm=800,
                receptor_geometry=receptors,
            ),
            EmbodiedBody(
                "person-body-1",
                PoseMM(PositionMM(7_300, 7_500, 0), 180_000),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(SECOND_BODY_PORT_ID, "person-body-1"),
        ),
        regions=regions,
        portals=portals,
        initial_objects=objects,
        contact_optical_surface_sequences=(),
        body_surface_sites=_companion_body_surface_sites(),
        max_regions=12,
        max_portals=16,
        solar_coupling=SolarCoupling(
            outdoor_region_ids=("backyard",),
            window_share_ppm_by_region_id=(("her-room", 250_000),),
        ),
        screen_broadcasts=(
            ScreenBroadcast(
                object_id="television",
                seconds_per_frame=45,
                frames=(
                    (850_000, 500_000, 200_000, 120_000, 90_000, 70_000),
                    (200_000, 350_000, 800_000, 400_000, 150_000, 90_000),
                    (120_000, 700_000, 300_000, 650_000, 200_000, 110_000),
                    (600_000, 600_000, 600_000, 600_000, 600_000, 600_000),
                    (90_000, 120_000, 180_000, 260_000, 500_000, 700_000),
                    (40_000, 40_000, 50_000, 40_000, 40_000, 40_000),
                ),
            ),
        ),
    )
    if encoded_world is None:
        return authority
    if not isinstance(encoded_world, bytes) or not encoded_world:
        raise ValueError("persisted world is not a nonempty byte body")
    authority.restore_encoded(
        encoded_world,
        allow_physical_return_migration=migrate_physical_return,
    )
    if not migrate_physical_return and bytes(authority.encoded_snapshot()) != encoded_world:
        raise RuntimeError("ordinary home-world restore changed canonical bytes")
    if not any(
        item.object_id == HOME_BOOK_OBJECT_ID
        for item in authority.observation_snapshot().objects
    ):
        raise RuntimeError("the persistent home lost its physical book")
    return authority
