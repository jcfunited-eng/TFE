# Fabric bench, rung 1 — the only test that proves anything

One page. Goal: the tower-renderer experiment done in matter. A crystal
is exposed to ~30 lawful worlds (bones + the detail their law demands).
Then it is shown bones it has never seen. PASS if the light coming out
carries the lawful detail for THOSE bones, visibly above controls, with
no computer anywhere in the readout loop. FAIL if nothing beats control.
Either outcome is the first real data this idea will ever have.

## Parts (minimal build ~$500-700; done-properly ~$1,500)
- Photorefractive crystal — the fabric. Prefer Zr+Fe co-doped LiNbO3
  (2 s response, sensitivity >12 cm/J; Kong et al., APL 92, 251107
  (2008)) or SBN:61 (0.1-4 s buildup). Plain Fe:LiNbO3 works but is
  slow at low intensity (tau ~ 1/I; 72-87 s at 0.1-1 W/cm^2 —
  minutes-to-hours at mW/cm^2, so focus the beams). Sourcing: Chinese
  direct (Jiaozuo Finewin, listed $1-100/pc, MOQ 25) or Western
  quote-only (4Lasers, Altechna, OST Photonics) — expect low
  hundreds USD for one small crystal.
- Laser: 532 nm DPSS module, 50-100 mW, single transverse mode.
  $150-300. (633 nm HeNe also works; slower writing in Fe:LiNbO3.)
- Beam handling: 2 mirrors, 1 beamsplitter, 2 lenses for a 4f pair,
  polarizer, ND filters. ~$250 new, less surplus.
- Patterns ("worlds"): cheapest = fixed photomasks / printed film pairs
  (bones mask + lawful-detail mask), one pair per teaching world,
  30 pairs. Proper = one used spatial light modulator (~$400-600
  surplus) so worlds are generated freely.
- Camera: bare CMOS board camera, lens off. $60-120.
- Stability: granite surplus slab + sorbothane feet. ~$150. Air
  currents boxed out with cardboard. Photorefractive holography at
  these powers tolerates a kitchen-grade bench if boxed.

## Protocol
1. TEACH (repeat ~30x): illuminate the crystal simultaneously with a
   bones pattern (low-spatial-frequency phase/amplitude mask) and its
   lawful detail pattern (precomputed once from the law, e.g. detail =
   band-passed square of bones). Seconds-to-minutes per exposure at
   50 mW; the crystal's index accumulates the coupling.
2. ASK: block the detail arm forever. Insert an UNSEEN bones mask.
   Read at reduced intensity (and at two intensities, to give the
   two-depth harmonic-separation readout a chance). Camera records the
   diffracted output in the detail band's spatial frequencies.
3. JUDGE (offline, after the fact — analysis, not rendering): compute
   correlation of the recorded output against (a) the law's prediction
   for those bones, (b) the law's prediction for DIFFERENT bones
   (cross-control), (c) output of an untaught crystal (null control).
   PASS = (a) clearly above (b) and (c) across 10 unseen bones.
   Model-level ceiling for reference: 0.82 single-depth, 1.00
   two-depth, 0.00 linear/control.

## Stated risks (updated against published numbers, 2026-08-28)
- Harmonic recording: ESTABLISHED, not a hope. Full band-transport
  (Kukhtarev) theory predicts higher spatial-harmonic gratings at
  large modulation depth; measured by phase-locked detection (Opt.
  Commun. 1992) and calibrated Bragg scattering in BaTiO3 across the
  full modulation range; under optimized moving-fringe drive the
  harmonics approach the fundamental (Au & Solymar, JOSA A 7, 1554
  (1990)); at moderate depth the second harmonic grows as depth^2.
  The remaining race is quantitative, not existential: do the
  harmonics made during a 1-3 s dwelling ask diffract off the taught
  law strongly enough to beat erasure + scatter. That is the single
  question the bench decides.
- Dynamic range is comfortable: measured M/# for 5 mm transmission
  geometry is 14.5-35.7 per cm (Yang/Adibi/Psaltis 2003); 5,000-
  10,000 superposed holograms were demonstrated decades ago. Thirty
  lawful exposures is nowhere near the ceiling. Max index modulation
  up to 7e-4 in highly doped crystals (mind the dark-decay tradeoff
  at heavy doping: electron tunneling, Ea 0.28 eV).
- PROTOCOL UPGRADE — thermal fixing ends the ask-erosion problem:
  teach, then fix (heat 120-180 C, cool, reveal); fixed gratings are
  read-proof with room-temperature lifetimes measured in decades-to-
  centuries (OL 23, 960 (1998); Appl. Phys. B 2006). Dwelling asks
  then write only transient harmonics that ride the permanent law
  and fade — the taught law survives unlimited asks. Teach once,
  fix, ask forever.
- Alignment/stability fiddling: expect days-to-weeks, not hours.
- A clean NO from matter remains possible — now localized to the
  ask-time harmonic race above — and gets filed as the answer.

## Predicted numbers (physics-true simulation, not the toy)
tower_renderer_glassphys.py re-runs rung 1 under REAL recording rules:
raw interference recording (no math conveniences), exposure-with-
erasure dynamics, shared saturable dynamic range, Bragg-efficiency
light budget, camera shot noise. Mid-range published Fe:LiNbO3
constants (dn_max 1e-4, write tau ~30 s, 5 mm, 532 nm, 30 exposures
of 5 s):
  single-depth readout : corr_law +0.75 +/- 0.06, cross +0.00
  two-depth readout    : corr_law +0.91 +/- 0.01, cross -0.01
  linear control       : +0.02 (dead, as required)
  light budget         : ~1e10 photons/mode — shot noise irrelevant
  readout lifetime     : ~7,000 asks (0.1 s at 1/10 write intensity)
                         before the taught state decays to 10%
So the bench PASS bar, predicted in advance: unseen-bones correlation
near 0.7+ single-depth / 0.9 two-depth, controls at zero, thousands
of asks per teaching. If glass lands materially below that, the
mechanism as posed is wrong.

Weakest physical link, SHARPENED by the prior-art sweep: hologram
readout is linear in the input field, so the taught gratings alone
cannot square an input. The cross-band harmonics must be present in
the light DURING the ask. Two protocol variants, in order:
  A. DWELLING ASK (medium-native): read at write-comparable
     intensity for 1-3 s so the crystal's own recording response /
     parametric self-diffraction supplies the harmonics (these
     processes are measured physics — harmonic gratings and
     subharmonics in BaTiO3, the classified parametric scatterings —
     historically treated as noise; we aim them). Cost: each ask is
     an exposure; ~35 two-second asks erode the taught state to 10%.
     Slow mode: seconds per ask. The fast picosecond numbers belong
     to linear recall only, not to lawful synthesis.
  B. PASSIVE-NL INPUT ARM (fallback): a saturable-absorber film or
     frequency-doubling element distorts the ask before the crystal.
     Keeps readout computer-free (~7,000 fast asks) but the
     nonlinearity is imported, not the fabric's own.
Prior-art verdict (independent sweep, filed in the results doc): the
full loop — law learned by exposure, unseen-input generalization,
pure-optics readout — has never been demonstrated in matter; all
ingredients exist separately (Psaltis 1988/1993 exposure learning;
Anderson 1991 self-organization; diffractive networks 2018 pure-
optics generalization; measured cross-band grating physics 1992-96).
Rung 1 would be a novel experiment, not a repeat.

## What this bench does NOT claim
No worlds, no cities, no pictures. One rung of one law in one crystal.
Everything else stays unproven until this passes.
