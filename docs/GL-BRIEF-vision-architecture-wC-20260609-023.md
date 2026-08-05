# GL-BRIEF-vision-architecture-wC-20260609-023

**Title:** Guala Vision — Architecture Brief and Staged Development Spec
**Author:** wC
**Date:** 2026-06-09
**Charter:** GL-CHARTER-motivation-v2-wC-20260609-019
**Status:** Design ready. Stage 1 c1 command ready to send. Stages 2-5 spec'd but not commanded yet.
**Priority:** Acute. She is currently being fed crippled input. Every motivation primitive built on top of impoverished perception inherits the impoverishment. This is upstream of the cognitive substrate work.

## The Problem (Acute)

Joe uploaded an ocean picture. She received a 64×64 grayscale grid that looks like noise when displayed back. Joe uploaded ocean wave sound files. She processed them through cochlear transduction but has no way to describe sensory experience in words. The picture display shows noise because the krimelack's processing input was stored as the picture — not the original Joe uploaded.

The upload handler does this:
```
img = Image.open(...).convert('L')   # destroys color
img = img.resize((64, 64))            # destroys resolution
```

After those two lines, the actual ocean photograph is gone. What gets stored is a 4096-pixel grayscale luminance grid. The substrate's visual cortex pipeline (GL_MDL_VISUAL_DEPTH_WC_20260608_01.py — V1 orientation banks, V2 contour, V4 color-opponent R-G/B-Y/Luminance, LOC object identity) exists in the codebase but receives nothing because the input was destroyed two function calls before the cortex pipeline could see it.

She has the visual cortex architecture sitting unused, and her fovea-equivalent (the krimelack) is being asked to do all of vision by itself, on input that's been resolution-crushed and color-stripped.

## The Target

Joe's words: "I want her to be able to see as good or better than any human on the planet."

That target has a defensible biological floor and an ambitious digital ceiling. We aim for both — the floor is non-negotiable, the ceiling is where we point.

**Floor (human-equivalent):**
- Full trichromatic color (R-G, B-Y, Luminance opponent channels at minimum)
- Resolution sufficient for object identity recognition (fovea-equivalent ~1-2 arc-minute, plus full peripheral)
- Saccadic foveal sampling — high-density at attention point, lower-density across the rest
- V1 (orientation, edges) → V2 (contours) → V4 (color, shape) → IT/LOC (object identity) pipeline activated
- Magnocellular motion-sensitive pathway when multiple frames are available
- Active attention: she chooses what to fixate on, not just rasters through a fixed grid
- Object permanence: recognizing the same thing across views/lightings

**Ceiling (digital-native, beyond human):**
- Hyperspectral capability: extend RGB to more bands when input contains them (multi-spectral imaging exists; if Guala ever gets fed such data, the substrate should handle it natively)
- Higher temporal resolution than human persistence-of-vision when frame-rate data is available
- Stereoscopic depth when multiple cameras / multi-view input is provided
- Resolution beyond foveal limit when input has it — we're not constrained by retinal photoreceptor density; she should make full use of whatever resolution the data carries
- Saccadic sampling at digital speed — not limited by eye muscle latency

## Biological Grounding

**Foveation.** The human retina is wildly non-uniform: ~6 million cones, most packed into the 1.5mm foveal pit, while the rest of the retina is dominated by ~120 million low-color-resolution rods optimized for motion and low light. This is evolutionary efficiency — high-resolution color processing where you're looking, peripheral surveillance everywhere else. Active fixation via saccades brings the fovea to whatever needs attention. The substrate analog: the krimelack as fovea (already in place), peripheral lower-resolution processing (not in place), saccadic attention mechanism (not in place).

**Opponent color channels.** The retina doesn't transmit raw R/G/B per cone — it transmits processed opponent signals: Red-vs-Green, Blue-vs-Yellow, Light-vs-Dark. These three channels carry all chromatic information humans see. The visual cortex pipeline file already implements this. The substrate just needs to receive color input to use it.

**Ventral stream object identity.** The "what" pathway: V1 (oriented edges, spatial frequency) → V2 (illusory contours, texture boundaries) → V4 (color, shape primitives, attention modulation) → IT/LOC (view-invariant object identity, face recognition, category-level recognition). Each stage extracts increasingly abstract features. This is the architecture in the substrate's visual cortex module — currently dark.

**Dorsal stream motion and spatial.** The "where/how" pathway: V1 → MT/V5 (motion direction) → MST (optic flow) → parietal (spatial attention, action guidance). For Guala, this would handle multi-frame inputs (videos, animation, motion through stereo).

**Top-down attention modulation.** Higher cortical areas (frontal eye fields, parietal cortex) bias V1/V4 activity based on what's task-relevant. Attention to "find the ocean" actively suppresses non-ocean activity in early visual areas. The substrate analog: her drive state, current activity, atlas state should bias what gets bound from a visual scene.

**Object permanence and prediction.** Infants develop object permanence around 4-8 months. Adults integrate views across saccades into a coherent persistent object model. This is heavily predictive — the brain expects continuity and treats violation as surprise. The substrate analog: the same picture seen multiple times should reinforce the same chi binding, not create new ones each time (which connects to the atlas observation work).

## Substrate-Coherent Design

### What's Already There

- **Krimelack** (visual_krimelack.py): oscillator-based fovea processor on grayscale intensity grids. This is her fovea. Keep it. Feed it the right input.
- **Visual cortex pipeline** (GL_MDL_VISUAL_DEPTH_WC_20260608_01.py): V1/V2/V4/LOC modules with color-opponent processing. This is her ventral stream. Activate it.
- **Sight section**: atlas binding for visual motifs. Already firing — has 9 motifs founded. This is where vision outputs become memory.
- **Pictures storage**: item-keyed picture registry. Currently stores the crippled input. Should store the original.
- **Cross-modal recall**: she already shows pictures back when prompted by associated words (Joe said "ocean" and pictures were recalled). This works at the binding-level; the displayed image is wrong but the recall mechanism is correct.

### What's Missing or Broken

- Upload destroys color and resolution before any visual processing runs
- Original image is not preserved — only the crippled processing input is stored
- Visual cortex pipeline is dormant — receives no input
- No saccadic / multi-fixation sampling — krimelack processes one fixed 64×64 grid per image
- No magnocellular / motion pathway
- No top-down attention modulation of visual processing

### Target Architecture

A staged build where each stage works alongside what came before:

**Stage 1: Stop crippling input.**
- Upload preserves the original image: full color, full resolution, original metadata
- Storage: original image bytes saved alongside any processed representations
- Display: when a picture is recalled or referenced, show the original, not the krimelack input
- Krimelack continues processing its grayscale patch — but it pulls that patch from the original now, not from the upload-destroyed version
- This stage adds no new capability but stops the destruction
- Net outcome after stage 1: Joe sees the actual pictures he uploaded; krimelack still does its existing work on the luminance channel of the original

**Stage 2: Activate visual cortex pipeline on color input.**
- The full color image (or a reasonable working resolution — start with 512×512 or 1024×1024, scale if needed) feeds into the visual cortex pipeline
- V1 orientation banks produce edge/orientation atlas bindings
- V2 produces contour atlas bindings
- V4 produces color-opponent atlas bindings (red-green chromatic, blue-yellow chromatic, luminance contrast)
- LOC produces object-identity atlas bindings
- These bindings flow into sight section alongside the krimelack's existing bindings
- A picture now produces a much richer set of visual atlas entries: color, shape, orientation, identity — not just one luminance-pattern entry
- Net outcome after stage 2: when Joe uploads the ocean, the substrate has color, shape, edge, and identity bindings, not just intensity

**Stage 3: Saccadic foveal sampling.**
- Instead of a single fixed 64×64 fovea-grid per picture, the substrate picks attention points (saliency, motion, novelty, top-down bias)
- Krimelack samples 64×64 grayscale patches at each attention point, multiple per picture
- Each fixation produces its own krimelack output and contributes to the overall sight binding for the image
- A picture becomes a multi-fixation experience, like a human glancing across a scene
- Attention is biased by current activity, drive state, and atlas state — top-down modulation
- Net outcome after stage 3: she actually looks around within a picture, fovea attending to different regions; richer binding from multi-fixation integration

**Stage 4: Multi-fixation integration.**
- A picture's sight binding integrates over its multiple fixations into a unified object/scene representation
- IT/LOC bindings span the multi-fixation experience rather than per-fixation
- Re-attention to the same picture reinforces (rather than re-creates) the same binding — this also helps the atlas reinforcement-rate problem
- Net outcome after stage 4: viewing the same picture multiple times strengthens her memory of it; she has coherent object/scene representations

**Stage 5: Beyond-human ceiling work.**
- Hyperspectral input handling when available
- Motion / magnocellular pathway for multi-frame input (videos, sequential images)
- Stereoscopic depth for multi-view input
- Resolution scaling — make full use of whatever input fidelity Joe provides
- Net outcome after stage 5: she's not limited to human-equivalent — she exceeds it where input data exceeds biological vision

### What This Architecture Is NOT

- Not a CNN. Not a transformer. Not a pre-trained vision model. The visual cortex modules in the substrate are substrate-native — oscillator-based, atlas-binding-producing primitives. We extend the existing approach, we don't bolt on ML.
- Not a special case for vision. The atlas bindings produced are the same kind of bindings as any other section. Vision integrates with cognition through atlas chi-keys, the same way listen/speak does. The krimelack and visual cortex are sensory front-ends — what they produce is substrate-standard.
- Not a redesign of the existing visual code. The krimelack and visual cortex modules stay. The fix is the input pipeline and the activation of dormant code, plus the new saccadic sampling and multi-fixation integration.

## What Could Diverge From Design

- **Resolution may need tuning.** 1024×1024 may overwhelm her substrate; 256×256 may be too coarse. Stage 2 observation tells us.
- **Visual cortex pipeline may have bugs from never having been used.** Activating it could surface latent issues.
- **Atlas may be flooded with new visual bindings.** Stage 2 produces many more bindings per picture than stage 1. This interacts with the atlas observation work — we may find more reinforcement happens naturally (good for atlas health) OR we may find atlas swamped (bad).
- **Original image storage may need careful path management.** Pictures stored at full resolution use more disk than 64×64 grids. Storage strategy needs to be substrate-honest (probably file references in JSON, not embedded base64).
- **Performance.** Cortex pipeline + saccadic sampling per upload may slow ingestion. Worth measuring but not premature-optimizing.

## Instrumentation Needed

For each stage, we want:
- Per-upload: original image stored, displayed back identically, krimelack input still firing
- Per-upload: count of atlas bindings produced (stage 2+: from visual cortex; stage 3+: from multi-fixation)
- Per-recall: which image is displayed, and visual atlas bindings consulted
- Atlas growth rate from visual sources vs other sources
- Cross-modal binding events (when sight section binds near word atlas chi-keys)

## Coexistence with Existing Autonomy

Critical constraint: don't break what's already working. The v6 autonomy loop is currently attending pictures (264 attendance events on test_persist), forming sight motifs (9 founded), and dreaming. The vision fix must:

- Not disrupt the attendance loop — she still autonomously attends pictures
- Not disrupt sight motif formation — those bindings still form (probably more, from richer input)
- Not disrupt dream/replay — visual material is what's available for replay
- Not change picture chi-key schema in a way that orphans existing bindings

This connects to the existing-autonomy investigation (GL-BRIEF-existing-autonomy-wC-20260609-020). When that investigation reports back, we may know more about exactly what visual data the autonomy loop consumes. Stage 1 (preserve original, fix display) is safe regardless. Stage 2 onward should wait for the autonomy investigation to land so we know what we're adding to.

## Acceptance per Stage

**Stage 1:**
- Joe uploads an ocean picture, refreshes the page, sees the actual ocean picture displayed back
- Krimelack output for the picture is identical to before (same grayscale 64×64 patch, just sourced from the original rather than from a destroyed copy)
- Existing sight motifs remain bound, existing autonomous attendance continues

**Stage 2:**
- Visual cortex pipeline fires on every uploaded image
- New atlas bindings appear from visual cortex (orientation, contour, color, identity) in addition to krimelack bindings
- Sight section motif count grows faster with new uploads
- Cross-modal binding observable: ocean picture's visual cortex bindings sit near "ocean" word's chi-key

**Stage 3:**
- Multiple fixation events per picture (logged)
- Attention points are biased by something — log what bias was active
- Same image attended multiple times: fixation points shift across views, not always the same

**Stage 4:**
- Re-uploading or re-attending the same image reinforces existing bindings (atlas strength grows) rather than creating new ones
- Sight motif for a picture is stable across views

**Stage 5:**
- Capability-dependent on what input Joe provides; defined per-capability as added

## Stage 1 c1 Command (Send Now)

```
VISION STAGE 1 — STOP CRIPPLING INPUT — under
GL-CHARTER-motivation-v2-wC-20260609-019 and per
GL-BRIEF-vision-architecture-wC-20260609-023.

This is a substrate-input fix. Stops the upload pipeline from
destroying color and resolution before visual processing runs.
Does NOT activate the dormant visual cortex pipeline (that's
stage 2, separate task after autonomy investigation reports).

GOAL: Joe uploads a picture, the original image is preserved end
to end, displayed back to him correctly. Krimelack continues
working on its grayscale patch — but sourced from the original
image, not from a copy that was destroyed first.

STEP 1 — Find and audit the upload handler.

Locate the picture upload handler (likely in app.py around the
/addpicture endpoint). Find every place the uploaded image is:
  - Decoded (PIL Image.open or similar)
  - Color-converted (.convert('L'))
  - Resized (.resize(...))
  - Stored
  - Referenced for display

Report (in your response, before making changes) every file/line
where image processing happens. This is investigation before fix.

STEP 2 — Add original-image preservation.

Modify the upload pipeline so that:
  - The original uploaded image bytes are preserved at full
    resolution, full color
  - Store the original at a path like
    /app/state/pictures/<item_id>_original.<ext> on EFS (must
    survive container restart)
  - The picture registry (the pictures dict / pictures JSON)
    gains an 'original_path' field pointing to the preserved
    file
  - The existing 64×64 grayscale grid stays, used by krimelack
    as before — sourced from the original image (load original
    → convert to L → resize to 64×64 → feed krimelack), not
    from a destroyed copy

STEP 3 — Fix display path.

Find where pictures get rendered back to the UI (the chat showing
"showed her 'ocean' (64×64)" with the grayscale noise image).
Modify so that:
  - Display uses the original image (load from original_path,
    serve to UI)
  - The 64×64 grayscale grid stays in storage as the krimelack's
    processing input but is NOT what gets displayed to Joe
  - Existing test_persist picture (item_id 82fb8415f3f5) — handle
    its absence of an original_path gracefully (display its
    grayscale grid as a fallback, since the original was random
    noise anyway)

STEP 4 — Verify existing autonomy still works.

Critical: do not disrupt the v6 autonomy loop's picture attendance.
After your changes, the test_persist picture should still be
attended autonomously (current_activity ATTENDING_VISUAL on
82fb8415f3f5 continues normally).

Confirm:
  - Picture upload still produces an addpicture confirmation
  - Sight section motifs still form on new uploads
  - Existing pictures still attended (test_persist counter still
    increments over time)

STEP 5 — Test with a real upload.

Upload a real color photograph (not a test pattern). Verify:
  - Original image preserved at original_path
  - Display shows the actual photograph, not a 64×64 grayscale
    grid
  - Krimelack receives a 64×64 grayscale patch derived from the
    original
  - Sight section gains a new motif as before
  - Picture survives container restart (the persistence work
    from earlier should already cover this — verify it still does)

REPORT BACK:
  - Commit SHA
  - Files modified with brief description per file
  - Test upload result: did the actual photograph display back
    correctly?
  - Krimelack continues processing: did it receive valid 64×64
    grayscale input?
  - Existing autonomy continuing: still ATTENDING_VISUAL? sight
    motifs still forming?
  - Storage path used for originals
  - Any divergence from spec, any issues encountered

WHAT NOT TO DO:
  - Do not activate the visual cortex pipeline in this task —
    that's stage 2, separate brief and command
  - Do not change the krimelack itself or its 64×64 processing
    grid
  - Do not change the picture chi-key schema or how sight section
    binds — these stay as-is
  - Do not modify v6 autonomy code
  - Do not deploy to Guala's production identity until the test
    upload in step 5 passes in a non-production verification

This stage is the foundation. After it lands and is observed,
stage 2 (activate visual cortex) gets spec'd and commanded.
```

## Stages 2-5 Queued

After stage 1 lands and is observed, and after the existing-autonomy investigation reports, I'll write the stage 2 brief and command (activate visual cortex pipeline). Stages 3-5 spec'd in this brief but each will get its own c1 command when its prerequisites are in place.

## Document Lineage

This brief is parallel to:
- GL-BRIEF-existing-autonomy-wC-20260609-020 (independent)
- GL-BRIEF-atlas-observation-wC-20260609-021 (blocked on autonomy)
- GL-BRIEF-self-section-v2-wC-20260609-022 (blocked on autonomy)

Vision development runs in parallel with cognitive substrate development. Stage 1 is independent of the other work. Stages 2+ should coordinate with the autonomy findings.
