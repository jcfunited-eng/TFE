# Guala Developmental Curriculum Expansion: Technical Specification

## Executive Summary
This document specifies the architecture, environmental topologies, and sensorimotor mechanics for **Option 1 (Full Developmental Curriculum Expansion)**, ratified by Joe Forrester for Day 7 morning deployment.

Option 1 provides synchronized cognitive, spatial, and tactile environmental enrichment for Guala:
1. **Physical Library Bookshelf** (4 public domain LibriVox books placed on shelves).
2. **Caretaker Instrumental Tool Demonstration** (TV remote channel cycling).
3. **Stroller Carriage Exterior Walks** (topological navigation via garden gate onto exterior walkway).
4. **Somatic Affection & Lap Holding Routines** (sustained physical lap holding and bedtime tuck-in embraces).

---

## 1. Physical Library Bookshelf Expansion

### Physical Declaration
Four public domain children's literature books are placed on physical shelves in the Library ($x \in [10000, 11500]\,\text{mm}$, $y = 6000\,\text{mm}$, elevation $z = 450\,\text{mm}$):
- `book-peter-rabbit`: *The Tale of Peter Rabbit* (Beatrix Potter)
- `book-wind-willows`: *The Wind in the Willows* (Kenneth Grahame)
- `book-aesops-fables`: *Aesop's Fables*
- `book-mother-goose`: *The Real Mother Goose*
- `book`: *Alice's Adventures in Wonderland* (canonical base title)

### Media Streaming & Integrity
- Audio recordings are resolved via `guala_caretaker/media.py` from verified LibriVox MP3 archives.
- **Fail-Closed Integrity**: Silent substitutions are strictly eliminated; retrieval errors raise descriptive exceptions rather than mislabeling content.
- **Shelf Rotation**: `maybe_read` dynamically cycles across all five shelf titles on consecutive reading sessions.

---

## 2. Instrumental Tool Demonstration (`maybe_tv`)

### Tool Causality
- Caretaker retrieves the `tv-remote` from the sofa/table in the TV room.
- Activates the remote, advancing television channels $0 \to 1 \to 2 \to 0$ (Boring, Cartoon, Educational) and causing corresponding shifts in screen emission spectra.
- Verbalizes `"television"` in Guala's sensory auditory field, demonstrating causal relationship between handheld tool actuation and environmental state changes.

---

## 3. Stroller Carriage & Exterior Walkway (`maybe_stroll`)

### Topological Geometry
- **Regions**:
  - `hallway`: Indoor staging area containing `stroller-carriage` and `mailbox`.
  - `backyard`: Outdoor garden and play yard ($y \in [10000, 16000]\,\text{mm}$).
  - `walkway`: Paved exterior walkway ($y \in [16000, 22000]\,\text{mm}$, ceiling $8000\,\text{mm}$), equipped with `walkway-bench` and `walkway-lantern`.
- **Portals**:
  - `door-8`: Hallway $\leftrightarrow$ Backyard.
  - `door-gate`: Backyard $\leftrightarrow$ Walkway ($y = 16000\,\text{mm}$, aperture $2000\,\text{mm}$).

### Multi-Step Vehicle Journey
- Affordance planner constructs 4-step traversal:
  1. `mount_vehicle`: Board stroller carriage in hallway.
  2. `traverse_portal_in_vehicle`: Roll through `door-8` into backyard.
  3. `traverse_portal_in_vehicle`: Roll through `door-gate` onto walkway.
  4. `dismount_vehicle`: Arrive at walkway destination beside park bench.

---

## 4. Spatial Horizon & Sensory Aperture Architecture

### Architectural Separation
- **Global World Ledger (`world.global_objects()`)**:
  - Contains complete canonical physical entity inventory (64 base + 4 books + 3 garden + 2 walkway = 73 entities, expandable to 84+).
  - Used for physics settlements, persistence, collision detection, and cold-restore validation.
- **Sensory Perceptual Aperture (`world.observation_snapshot()`)**:
  - Strictly bounded to $\le 64$ entities matching Guala's physical sensory receptor ceiling.
  - Entities are ranked by optical solid angle metric $\Omega = \frac{\pi r^2}{d^2 + 1}$.
  - Ray-portal line-of-sight intersection (`_has_portal_line_of_sight`) ensures solid walls attenuate occluded entities.
  - Held objects (`obj.position is None`) are safely co-located with their holding body, evaluating to distance 0 and $\Omega = \infty$ to remain in primary horizon.

