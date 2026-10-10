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

## 3a. Where her beat sees it

Her beat's sight is the loop's own retina function (`_world_retina_u8` in `guala_functional_loop.py`), not the sensorium's capture; the sun is handed to it there from the same clock (`_sun_of(world)`). Until that line existed the law lived in the world and never reached her eye (found 2026-09-16 01:47Z, after release 1505; fixed in the release that followed). Test: the shaft reaches her eye on the path her beat uses (light suite, fifth test).

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

## 5. Not done, by design (as of the first build; see 6 for what the second build closed)

After the second build: no sun through a door; one bounce only (a lit floor lights the room evenly, not the ceiling more than the far wall); a thing's shadow is that of its sphere. Each is a further geometry law if her eye's measurements ask for it, not a picture.

## 6. Second build, 2026-09-16 02:30Z to 03:00Z: lamps, shadows, one bounce, light on things, looks (Joe: "what is this half ass bullshit")

Joe read her live field after 1506: a flat grey with one dim shape. Right: the sun through windows by day was all there was, and at night nothing. Built as one item, in the same pass:

- **Lights.** A room's lights are the sun (through its windows) and every thing in it that emits (a lamp, the screen while it broadcasts, her glow stars): the thing's centre, its radius and what it gives off per band. A lamp's light on a surface falls off with the square of the distance from the lamp's surface, times the incidence; anything standing between blocks it: a shadow on the floor behind a chair, day or night.
- **Light on things.** A round thing in the room is lit by the same lights: the share of its lit half that the eye sees, `(1 + L·V)/2`, blocked by whatever stands between. A thing standing in the shaft is brighter than one beside it.
- **One bounce.** The direct light that enters a room (the sun through each window by its area and the sun's angle on it; each lamp by its surface and emission) lands on the room's surfaces and comes back once, spread over them: flux × the paint's reflectance / the room's surface area, added to the room's ambient for its surfaces and its things. A lamp lights its room at night; a sunlit room glows.
- **Looks on surfaces.** `SurfaceLookMM(face, from, to, low, high, surface)` on a region: a rectangle of a wall, the floor or the ceiling carrying a palette-indexed pattern (the same surface type things use). The focal ray's hit point on that face reads the pattern's cell there. Anatomy, like paint: in the record only when present, in the anatomy identity, carried by the renovation. First two in her room: floor planks, the south wall's panels (C1); A1 extends.
- **One pass, vectorized.** All 4,800 focal rays at once (numpy, in the image): plane hits, faces, looks, each light's incidence, window test, shadows per occluder, then the pixel written at the retina's own eight-bit grain (a declared quantization; things keep their exact fractions). Cost measured in her room: looks only 3 ms, sun only 2 ms, sun + glow stars + looks + 13 occluders 6 ms (the scalar pass was 27 to 60 ms and put her beat at 286 ms median).

Measured through her real path (120 beats, genesis in her room with the apple): median 120 ms with the sun, 127 ms at night; p90 239 / 247 ms; worst 279 / 308 ms. Her focal field now carries 23 to 26 distinct values, 7 to 81, where before it was one grey with a shape.

Tests: the light suite (8): windows in records; the sun's path; the shaft, moving with the hour, gone at night, deterministic, under 60 ms; a thing's shadow in the shaft; the shaft on the path her beat uses (wide field rises only by the bounce and where a thing stands in the sun); a lamp lights the floor at night and a post beyond it casts a shadow; the bounce for lamp, sun, none; a floor look read where the rays meet it, in the records, refused outside its face.

## 7. Third build, 2026-09-16 02:45Z to 03:00Z: the shape law (Joe: "every god damn object is an orb")

Joe looked at the page: every thing an orb with a pattern. Right: the world's things were spheres by declaration, so no light could give them an edge or a face. Built:

- **A thing may be a box.** `EmbodiedObject.shape` ("sphere", the old law, or "box"), `size_mm` (its extents in its own frame), `heading_millidegrees` (its turn about the vertical), `elevation_mm` (its bottom above the floor: a framed picture on a wall, a thing on a shelf). Every planar law (reach, grasp, clearance, collision) keeps the footprint disc, which must cover the box's plan (verified). In the record only when not a sphere; old records decode unchanged; the renovation carries it as authored.
- **The eye meets its faces.** In the same vectorized pass as the room's surfaces: a slab test in each box's own frame along every focal ray; the nearest face wins over the room's surface; the face's normal lights it by the same lights (a table's top brighter than its side under a lamp; a picture's face flat to the wall); the thing's pattern is read on the face (u along its width, v up); a box in front hides what is behind it (depth by site), and a sphere nearer than the box is drawn over it.
- **Boxes block light as boxes.** A bed no longer shadows the room as a nine-hundred-millimetre ball; the shadow test runs the slab test from the surface point toward the light, for the vectorized pass and for the light on things. A thing's own faces are never shadowed by itself.
- **The lamp law.** A thing's emission is the light it puts on a surface one metre from its centre (its shade looks that bright); nearer it rises with the inverse square up to four times; farther it falls with the inverse square. The bounce takes a lamp's flux as that light over the one-metre sphere.

First shapes (C1, so the picture exists tonight): her bed 1 500 × 950 × 500, toy chest, desk, desk chair, the two framed pictures on the west wall as 40 mm boxes 560 wide and 760 tall at 1 300 mm, the library's shelves 700 × 300 × 1 800, the dining table. A1 converts the rest of the furniture (`HOME_SHAPES["thing"] = ((x, y, z), heading, elevation)`).

Measured (her room, genesis, the sky's share on the night floor by day; a floor lamp by night): fields of 27 to 187 distinct values, 0 to 202, where the first build had one grey. Pass cost with boxes 30 to 70 ms per field including the things loop. Tests: a box in the records and a sphere without one; a box wider than its footprint refused; from mid-room by lamplight the pictures show straight vertical edges and the desk more than one face; a crate in front hides a bright ball behind it.

## 8. Fourth build, 2026-09-16 03:15Z to 03:35Z: the whole house in shape, lamps at their heights, the nightlight, the cap

- 37 of 52 things are boxes (sofa, television, counters, tub, chairs, shelves, rug, mat, slide, sandbox, curtains, pillow …), each sized inside the footprint disc it already had, so no clearance or collision law moved; furniture wears its paint flat (a sofa is one grey whose faces the light tells apart); pictures, the television and the books keep their patterns.
- A sphere may carry `elevation_mm`: a shade on a stand, a pendant, the glow stars on the ceiling. Lights, shadows and the drawn disc use the true centre. Heights declared: kitchen pendant 1,500; dining pendant 1,600; desk lamp 750; vanity light 1,400; library floor lamp 1,300; glow stars 2,300.
- Her room's nightlight (radius 80, 300,000 at one metre, 250 mm up by the bear) so her nights are not black.
- The thing cap 64 → 128 (`DEFAULT_MAX_OBJECTS`), carried into a lived world by the production restore's authenticated migration.
- Colour and the eye's grain are A1's (ledger 03:10Z and 03:30Z): the six bands become three channels per site in the same rewrite that makes the field finer.

Renders (genesis stances, night floor): kitchen under the pendant 111 distinct values, 0 to 154; dining under its pendant 139, 2 to 157; her room by the nightlight 81, 2 to 87.
