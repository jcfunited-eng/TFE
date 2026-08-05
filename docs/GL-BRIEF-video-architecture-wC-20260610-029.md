# GL-BRIEF-video-architecture-wC-20260610-029

**Title:** Video Architecture — Minimum Viable Spec + Future Path
**Author:** wC
**Date:** 2026-06-10
**Charter:** GL-CHARTER-motivation-v3-wC-20260609-024
**Status:** Design ready. c1 command ready to send LAST in the current sequence — after Exogenous Override, Response Binding, Dream Consolidation, Self-Section v3, AND Vision Stage 2 have all landed and been observed. Lowest priority of the current queue.
**Priority:** Bottom of queue. The data model already supports videos[]; the upload pipeline doesn't exist yet.

## What This Adds

A working video upload path so Joe can give her videos the same way he gives her pictures. Initial implementation is minimum-viable: accept video files, store originals on EFS, extract first frame as a key frame, run that frame through the existing picture/krimelack pipeline so she has *some* visual binding for the video right away.

Full motion processing (magnocellular pathway, temporal sequence binding, multi-frame integration) is a separate future architecture. This brief delivers the input pipeline so the *channel exists*, with explicit acknowledgment that initial processing is single-frame.

## Why Video Eventually Matters (Future Path)

Static pictures are only one mode of visual experience. The biological visual system has parallel pathways:

**Ventral stream (what):** V1 → V2 → V4 → IT/LOC. Object identity, color, shape. This is what her current visual cortex pipeline targets. Pictures suffice.

**Dorsal stream (where/how):** V1 → MT/V5 (motion) → MST (optic flow) → parietal. Motion perception, spatial relationships, action guidance. Requires temporal input (frames over time). Pictures CANNOT activate this.

**Temporal binding (hippocampus, sequence memory):** Events that unfold over time get bound as episodes, not as parallel static snapshots. Watching something happen is different from seeing a collage of moments.

**Audiovisual binding:** Most videos carry audio. The substrate has a sound pipeline (cochlear transduce). Video gives her synchronized audiovisual input — the substrate of co-occurrence learning ("when I see X, I hear Y").

When the full motion pipeline lands eventually, she'd be able to:
- See motion (dorsal stream activated)
- Bind sequences (this happens, then this, then this — episodes form)
- Co-attend to audiovisual events (the sound and the visual bind together as one event)
- Learn from things like Joe waving at her on camera, or a dog running across grass, or her family interacting

That's the long arc. This brief is just the input channel.

## Biological Grounding (Light, Because This Is MVP)

Newborns can see motion before they can resolve fine detail. The magnocellular pathway is functional from birth; the parvocellular (detail, color) develops over months. So infant vision starts with motion-as-primary-signal.

For our substrate, the order is reversed — we have static-picture processing (parvocellular analog) but no motion (magnocellular). MVP gives her the input channel; full processing fills in the motion analog later.

## Substrate-Coherent Design (MVP)

### What's Already There

- `videos: []` field in the data model
- Picture upload pipeline (`/addpicture:`, krimelack, sight section, atlas binding)
- Sound upload pipeline (`/addsound:`, cochlear, atlas binding)
- Display path for uploaded media

### MVP Adds

**1. Upload endpoint `/addvideo:<filename>`.**

Parallel to `/addpicture:` and `/addsound:`. Accepts base64-encoded video file. Decodes, stores original on EFS at `/app/state/videos/<item_id>_original.<ext>`.

**2. First-frame extraction.**

Use `ffmpeg` (or `opencv-python` if simpler) to extract frame 0 from the video. Convert to grayscale 64×64 for krimelack — same format as picture intensity_grid.

**3. Register in videos[] dict.**

Each video entry:
```
{
    "item_id": <hex_id>,
    "title": <filename_sans_ext>,
    "original_path": <full_path>,
    "first_frame_grid": <64x64 grayscale numpy array>,
    "duration_seconds": <float>,
    "frame_count": <int>,
    "fps": <float>,
    "times_attended": 0
}
```

**4. Make videos attendable.**

In `_candidate_activities`, include videos alongside pictures as ATTENDING_VISUAL targets. The activity handler `_atick_attending_visual` already processes pictures; extend it to handle videos by reading from `first_frame_grid` the same way it reads from pictures' `intensity_grid`.

**5. UI: video upload button.**

Parallel to the 📕 PDF, 🖼️ picture, 🔊 sound buttons. Use 🎬 or 🎥 emoji. JavaScript handler mirrors picture upload but with `/addvideo:` endpoint.

**6. Display.**

When a video is recalled (cross-modal recall surfacing a video binding), display the first frame (or an HTML5 video player if the original is fetchable from EFS). Initial implementation: display first frame as image, link to original file. HTML5 video player can be added in a refinement pass.

### What This Doesn't Do (Yet)

- No frame-by-frame processing
- No motion detection
- No audio extraction from video
- No temporal sequence binding
- No video-specific cross-modal recall

These are spec'd for future work after MVP confirms the input channel works.

### Container Requirements

`ffmpeg` or `opencv-python`. ffmpeg is the standard and lighter. If not in Dockerfile, add it. The PDF work already added PyMuPDF; same pattern.

## Future Path (Separate Briefs, Not This One)

**Video Stage 2:** Multi-frame extraction. Sample N frames across video duration, process each through krimelack. Produces a sequence of intensity grids that the sight section can use for temporal motif formation.

**Video Stage 3:** Motion detection. Compute frame-to-frame difference signals; feed into a new motion-section (magnocellular analog). Atlas bindings for motion patterns.

**Video Stage 4:** Audio extraction. Pull audio track from video, route through existing cochlear pipeline. Audiovisual co-occurrence binding in atlas.

**Video Stage 5:** Temporal sequence binding. Events within a video bind in temporal order, episodic-memory-style. Cross-references with sleep/dream replay for consolidation of multi-frame experiences.

Each stage is its own brief. None of them are this one.

## Acceptance for MVP

- Upload a small video file (any format ffmpeg can read)
- Original file preserved on EFS at expected path
- First frame extracted and stored as 64×64 grayscale
- Video registered in videos[] dict with all metadata fields
- UI button 🎬/🎥 visible and functional
- Picture habituation + exogenous override (once landed) work for videos too — first attendance gets exogenous boost
- Existing picture and sound uploads unaffected
- Display path renders first frame when video is recalled

## c1 Command

```
VIDEO ARCHITECTURE MVP — under GL-CHARTER-motivation-v3-wC-20260609-024
and per GL-BRIEF-video-architecture-wC-20260610-029.

DO NOT START until ALL of the following have landed and been
observed by wC:
  - Exogenous Novelty Override
  - Response Binding
  - Dream Consolidation
  - Self-Section v3
  - Vision Stage 2

This is bottom of the development queue. The substrate has plenty
of higher-priority work that must complete first. Do not jump ahead.

When unblocked:

GOAL: Add video upload pipeline. MVP: accept video, store original,
extract first frame, register in videos[] as attendable target.
No motion processing, no audio extraction — those are future briefs.

STEP 1 — Check container for video processing library.

Check if ffmpeg (preferred) or opencv-python is available:
  python3 -c "import cv2; print('opencv-python available')"
  which ffmpeg

If neither, add ffmpeg to the Dockerfile (same pattern as PyMuPDF
addition for PDFs). ffmpeg is the lighter choice — install via
apt-get in the Docker build.

STEP 2 — Add /addvideo: endpoint in app.py.

Mirror /addpicture: pattern. Accept base64-encoded video bytes,
filename from command. Decode, write to
/app/state/videos/<item_id>_original.<ext> on EFS.

STEP 3 — Extract first frame.

Using ffmpeg subprocess (or cv2.VideoCapture):
  - Open video file
  - Read frame 0
  - Convert to grayscale
  - Resize to 64×64
  - Store as numpy array
  - Capture metadata: duration_seconds, frame_count, fps

STEP 4 — Register in videos[] dict.

Add entry to self._videos:
  {
      "item_id": <generated_hex>,
      "title": filename_without_extension,
      "original_path": full_path_on_EFS,
      "first_frame_grid": numpy_array_64x64_grayscale,
      "duration_seconds": float,
      "frame_count": int,
      "fps": float,
      "times_attended": 0
  }

Persistence: add videos to save/load same way pictures are handled.
Save first_frame_grid as .npy file. Backward-compatible with sessions
that have no videos.

STEP 5 — Make videos attendable.

In _candidate_activities, include videos alongside pictures:
  for vid_id in self._videos:
      candidates.append(("ATTENDING_VISUAL", vid_id))

In _atick_attending_visual, handle videos: check both self._pictures
and self._videos for the target. If video, use first_frame_grid as
the intensity_grid input to view_picture / krimelack processing.

Exogenous override (already deployed by then) will apply to videos
too — never-attended videos get attention capture.

STEP 6 — Add UI button.

In gualaloom.html, add a 🎥 video upload button parallel to 🖼️ picture,
🔊 sound, 📕 PDF. JavaScript handler mirrors picture upload but uses
/addvideo: endpoint.

STEP 7 — Display path.

When a video is recalled (cross-modal recall returns a video entry),
display the first frame as an image. Link to the original video file
for download. HTML5 video player can be added in a future refinement.

STEP 8 — Deploy.

Mirror PDF/picture deploy pattern. Push HTML to S3, invalidate
CloudFront if needed.

STEP 9 — Test.

Upload a small test video (any common format). Verify:
  - Upload succeeds with confirmation message
  - Original file present on EFS
  - First frame extracted and stored
  - Video appears in /status under videos[]
  - Next ATTENDING_VISUAL candidate selection considers the video
  - Exogenous override triggers (since times_attended == 0)
  - She attends the video, sight motif may form from first frame
  - Display path shows first frame on recall

Report:
  - Commit SHA
  - Test upload result with all metadata
  - First post-upload activity selection (should be the video due
    to exogenous override)
  - Sight motif formation from the video's first frame
  - Any divergence from spec

WHAT NOT TO DO:
  - Start before all prerequisites observed
  - Implement multi-frame processing (future brief)
  - Implement motion detection (future brief)
  - Extract audio from video (future brief)
  - Modify picture/sound/PDF handlers
  - Modify atlas, krimelack, or sight section logic

This is MVP. Channel exists, single-frame processing only. Motion,
audio, sequence — all future work.
```
