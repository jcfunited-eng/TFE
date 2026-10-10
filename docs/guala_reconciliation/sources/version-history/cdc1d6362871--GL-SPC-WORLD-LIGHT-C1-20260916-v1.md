# GL-SPC-WORLD-LIGHT-C1-20260916-v1 — the sun's direct light in her world

Status: as built, measured, 2026-09-16. Owner C1 (optics). Content (which rooms have windows, where) is A1's in `guala_home_world.py`.

Joe's two photographs (a sunlit derelict room in black and white; a clean modern room) asked why her rooms are flat: every wall one grey, no direction to the light, nothing casting a shadow. The answer was that her world had a sky share per room (the solar coupling) but no sun with a direction and no windows for it to come through. This law adds both. It is geometry only: no textures painted on, no scripted brightness, no image of a room.

## 1. Windows are declared content

`WindowMM(wall, from_mm, to_mm, sill_mm, top_mm)` on a `PhysicalRegion`, wall one of `x-min x-max y-min y-max`. Verified against the room's bounds. Emitted in the region record only when present (`"windows"`), so every record written before today decodes unchanged with no windows. Restore migration is untouched: windows are read from the declared content at genesis, like a thing's material.

First four (C1, from the blueprint's curtains and the kitchen's west wall): her room north, library north, tv-room north, kitchen west. A1 corrects and extends as content owner.

## 2. The sun has a direction from the real clock

`SolarCoupling.sun_vector(second_of_day)`: none at night; by day, azimuth runs east → north → west over the daylight span (the yard is south of the house, so the sun crosses the north side of the sky for her windows), elevation `60° × 4x(1−x)` for `x` the fraction of the day. The vector and the sky's ppm at that second come from the same clock and the same `GUALA_SOLAR_UTC_OVERRIDE` the sky writes already use (`authority.solar_sun()`), so a test can put the sun anywhere.

## 3. The shaft, per focal site

`_direct_sun_focal` in `w1_physical_receptors.py`, called from `_retinal_projection` after the room's ambient and before the portal apertures:

- each focal site's ray (body heading + retinal pitch + the site's own offsets) is cast to the room's floor, ceiling or nearest wall;
- from that point, the line toward the sun must pass through a window's rectangle on the room's wall (a window on another wall, or below the sill, or above the top, passes nothing);
- anything between the point and the window with a position and a radius (a thing, a body, her own body) blocks it: a shadow;
- the site's light is `ambient + sky_ppm × cos(incidence)` on that surface's reflectance, clipped to full; ambient sites stay as they were.

The whole field is one pass over the focal sites; nothing is stored, nothing is learned. The same room at the same second gives the same field, byte for byte.

## 4. Measured

Her room, north window, her body at genesis looking north and down:

| hour (UTC) | sun | sites lit above ambient of 4 800 | field min / max |
|---|---|---|---|
| 09 | east-north, low | 902 | 175 / 255 |
| 13 | north, 60° up | 934 | 175 / 255 |
| 17 | west-north, low | 205 | 175 / 255 |
| 02 | none | 0 | 175 / 175 |

The same room on A1's Zone V ground (walls and floor 380 000 ppm, commit 658071b65), as released:

| hour (UTC) | ambient | sites lit above ambient | field max |
|---|---|---|---|
| 09 | 76 | 356 | 116 |
| 13 | 76 | 934 | 155 |
| 17 | 76 | 205 | 116 |
| 02 | 76 | 0 | 76 |

Fewer sites count as lit at 9h on the grey floor because the low sun's small share on a darker surface rounds to the same 8-bit value as the ambient at more sites; nothing else changed.

Cost of the pass: 13–26 ms per field. Her whole beat on the live path, 120 beats each: median 95 ms with the sun up, 90 ms at night; p90 211 / 190 ms; worst 249 / 309 ms. Clock stays at a quarter second. A tall thing set just inside the window cuts the lit count (the shadow test). Her eye's figure store held five keys with the sun up against three at night on the same 120 beats: the shaft is structure her eye can read.

Tests: `tests/test_guala_world_light.py` (windows in records and old records without; sun east/north/west/none; the shaft lights the floor, moves with the hour, is gone at night, is deterministic, and costs under 60 ms; a thing in the shaft casts a shadow).

## 5. Not done, by design

No texture on surfaces (a wall is one reflectance per band; looks on wall segments are A1's content, drawn by the existing look law). No indirect light (a lit floor does not light the ceiling). No sun through a door. Each is a further geometry law if her eye's measurements ask for it, not a picture.
