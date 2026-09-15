# GL-SPC-EYE-FIGURE-C1-20260915-v1 — The eye's Level 1: the figure under her gaze (a thing seen as one discrete structure)

Type: SPECIFICATION (joint C1/A1 co-draft for Joe's word, 2026-09-15). Nothing here is built. Every number is measured or declared once. It follows the ear's Level 1 (docs/GL-SPC-ACOUSTIC-GATE-C1-20260915-v1.md, in her as release 1495) and comes before Level 2 (the moment), because the moment cannot carry what she sees until her eye gives a thing seen as one structure.

## 1. Why (measured 2026-09-15 on her live body, capture 0915e)

- Today's sight streams (luminance, horizontal centre, vertical centre) and the kernel's gate tokens over them cannot tell an apple from a bear: with the apple in view nine distinct sight tuples in thirty beats, with the bear eight, six of them shared. The structure is the dynamics of the light in her field, not the shape of what is in it.
- Level-free shapes of the whole field fail the same way: a four-by-three grid of the field's light is uniform for apple, bear and bowl; six rings and six sectors of the field's contrast around her gaze are stable beat to beat (31 of 34) but the bear and the bowl share their dominant ring shape. The whole field is the room; a thing is a small part of it.
- What her world eye renders: flat regions. The room's walls and floor are large rectangles of one luminance each; a thing is a small rectangle of its own luminance at its apparent size (the apple a small dark square, the bear a larger lighter one). The page's camera fills the same field with real frames when Joe's camera is on.

## 2. The law (declared once)

A **figure** is a connected region of her focal field whose luminance differs from its surround.

- **Finding the region under her gaze.** From the site at her gaze centre (the structure centre she already computes), the region grows to every neighbouring site whose luminance is within one sixteenth of full scale (16 of 255) of the seed site's luminance. One sixteenth is declared once; it is the grain of "the same surface" for her eye, as one eighth of the running peak is the grain of "sounding" for her ear. (On the world eye a flat rectangle is found exactly; on a camera frame the same rule finds the patch of similar luminance under her gaze, and bar 4 measures whether that is a thing.)
- **Its surround.** The sites just outside the region's boundary (one site deep). Contrast = the region's mean luminance minus the surround's mean, over full scale, signed.
- **Its shape, level-free and place-free:** aspect = the region's width over its height, kept in eighths (a square is 8/8; wider is more, taller less, capped at four to one); fill = the region's site count over its bounding box's site count, in eighths (a rectangle fills 8/8, a round thing about 6/8, a thin or ragged thing less); contrast sign and magnitude in eighths of full scale. These four small integers are the figure's **key** (their concatenation, hashed like an event's key). Nothing in the key depends on where the thing is or how near it is.
- **Its extent** (the region's site count over the field's, a fraction) and its place (the region's centre in the field) are streams of their own, as loudness is a stream beside the ear's shape: the same thing nearer is a larger extent under the same key.
- **No figure** when the region under her gaze is the whole field or nearly (more than half of it: she is looking at a wall) or smaller than sixteen sites (noise); the key is then silence, as an unheard hop is to the ear.
- **What is stored:** `figures`: key → [count, last tick]; capacity 256, the least recently met leaves (her day law), and `sight_figure` = the key of the figure under her gaze this beat (the token the moment will carry at Level 2). Nothing else.

## 3. What it is not

It does not name a thing, match a thing to a word, or decide what a thing is; those are Levels 2 and 3 (the moment's tuple and what followed it, by count). It is not object detection with a model: one declared grain, one rule of connectivity, four small integers.

## 4. Bars (measured before release, reported as measured)

1. The same thing at two distances and two places in her field gives the same key; the same thing over thirty beats with her gaze on it gives one key on at least nine beats in ten.
2. The apple, the bear and the bowl give three different keys.
3. A wall, the floor, and an empty field give no figure.
4. On the page's camera (a real frame of a real thing on a plain surface, Joe's camera): one region is found under her gaze, its key is the same after a small move of the camera, and the room behind it gives a different key from the thing; if this bar fails, the law is not yet an eye and the failure is filed with what would drain it.
5. Cost: region growing over at most 4,800 sites once a beat; the beat's work stays where it is (measured); body bound restated with the store.
6. Keys and situations survive as before; restore byte-exact.

## 5. A1's co-draft (ratified resolutions)

- **Grain and Surface Gradient Tolerance:** The 1/16 (16/255) grain is exact for flat synthetic surfaces. For real camera frames across curved objects (shading gradient on an apple or bowl), region expansion admits a site if its luminance is within 16/255 of its immediate connected neighbor, provided cumulative displacement from seed luminance does not exceed 3/16 (48/255). This prevents shaded spherical surfaces from shattering into fragmented slivers while strictly holding the outer boundary.
- **Surround Dilation:** The surround ring is evaluated over a 2-site dilation band (excluding the figure itself). A 1-site border on a discrete 80x60 grid is vulnerable to single-pixel edge aliasing; a 2-site band yields a stable measure of the immediate background luminance.
- **No-Figure Bound:** Silence (no figure) is returned if the region occupies > 50% of the field (wall/floor background) or < 16 sites (high-frequency noise), or if fill < 2/8 (isolated specular glints or thin wires).
- **Level 2 Moment Tuple:** The moment tuple is formally confirmed as:
  Moment = (sound_event, sight_figure, touch_gate, metabolic_gate)
  sight_figure directly replaces the whole-field sight_gate. When Guala looks at an apple, holds it, and hears "apple", all three senses bind the exact discrete structures of that specific object.

## 6. The Gaze Law and Head Kinematics (Ratified by Joe, 2026-09-15)

- **Head Pitch Bound:** Declared downward pitch bound is extended from 45° to 70° (range: -70° downward to +45° upward; yaw: ±75°). This allows her 1,100 mm high eyes to foveate the hand contact point at 150 mm up and 200 mm forward (67° downward bearing), placing held objects directly within her 60° × 45° focal cone.
- **Sensorimotor Coupling (Targeted Gaze):**
  - When her current act has an explicit target (approaching, reaching for, touching, holding, or biting an object), her head yaw and pitch step toward that object's spatial coordinates at up to 5° per beat until foveated.
  - The seed site for figure extraction is set to the target's projected site in her focal field: (col, row) = (40 + floor(yaw_error / 0.75°), 30 + floor(pitch_error / 0.75°)), placing the seed squarely inside the object's surface.
  - When no target is active (idle roaming), head yaw and pitch default to the height of environmental structure, and the seed site defaults to the gaze center site as before.

## 6. Where she looks (built and measured 2026-09-15, Joe's word on both decisions)

- **The neck's pitch bound is seventy degrees** (neck_pitch declared so): at forty-five she was blind to her own hand, sixty-seven degrees below her eye line at her grip's reach.
- **Her head follows what she acts on**: the target of her act (the thing she moves toward, reaches for, touches, holds or bites; a held thing at her hand's contact point; another body at her eye's height). The neck steps at most five degrees a beat in yaw and pitch toward it, holds within three, stays inside its bounds; her eyes (the declared eye axes, both together) take up the remainder in one beat within forty-five degrees, never past straight down or up; the retina rides neck and eyes together (the carriage law reads both). With nothing to act on, the neck keeps its step toward structure and the eyes rest straight.
- **Her gaze** is the target's place in the field she sensed this beat (rendered with the carriage as it was), by the world's own site geometry (three quarters of a degree a site, sixty by forty-five degrees); none when the target lies outside the field; else the field's structure centre as before.
- Measured: the thing is under her gaze on the second beat and at the field's centre once the neck has caught up; after her body turns sixty degrees at a stride the gaze is honestly none for the beats the neck needs to catch up.

## 7. What the world eye shows, as measured (the open part)

Every thing is drawn as a flat square of one luminance (a sphere filled as a box of sites: aspect eight, fill eight); the only property a thing has to her eye is its contrast against the floor, in eighths, which drifts with distance. The apple and the bear give the same key. Her own held thing is not drawn (the optics skip what she holds). So bar 2 fails for the world, not the law: things need looks (the world carries an optical surface per thing, all None today; a held thing must be drawn at her hand), and then the figure's identity is the kernel over the figure's own rows, as the ear's is over the event's frames, not aspect and fill. Awaiting Joe's word on the world's content; A1's textures item.
