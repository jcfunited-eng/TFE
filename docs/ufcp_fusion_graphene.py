"""
UFCP Fusion: Graphene Pathway
===============================
Graphene / twisted bilayer / intercalated graphite as fusion host.

Key advantages:
  - Honeycomb = natural hexagonal cage (6 C per ring)
  - Superconducting when twisted (MATBG ~1.5K) or intercalated (CaC6 ~11.5K)
  - Natural intercalation host (Li, H, B all demonstrated)
  - Tunable interlayer spacing via twist angle and intercalant
  - Stackable: multilayer = 3D cage structure
  - Abundant, cheap, non-toxic

The question: does graphene's honeycomb provide the cage geometry
needed for coherent N^2 W kernel enhancement?
"""

import math

e = 1.602e-19
MeV = 1e6 * e
hbar = 1.055e-34
c = 2.998e8
k_e = 8.988e9
m_p = 1.673e-27
fm = 1e-15
angstrom = 1e-10
log10e = math.log10(math.e)
alpha = 1/137.036

print("=" * 70)
print("UFCP FUSION: GRAPHENE PATHWAY")
print("=" * 70)

# ==============================================================
# Graphene geometry
# ==============================================================
print(f"\n--- GRAPHENE STRUCTURE ---\n")

a_CC = 1.42  # C-C bond length in graphene, Angstrom
a_hex = a_CC * math.sqrt(3)  # hexagonal lattice parameter = 2.46 A
r_void = a_CC  # distance from center of hexagonal ring to C atom

# Interlayer spacing
d_graphite = 3.35  # Angstrom (natural graphite)
d_LiC6 = 3.70      # Angstrom (lithium intercalated)
d_CaC6 = 4.52      # Angstrom (calcium intercalated)

print(f"C-C bond length:           {a_CC} Angstrom")
print(f"Hexagonal lattice param:   {a_hex:.2f} Angstrom")
print(f"Void center to C distance: {r_void} Angstrom")
print(f"")
print(f"Interlayer spacing:")
print(f"  Pure graphite:   {d_graphite} A")
print(f"  Li-intercalated: {d_LiC6} A")
print(f"  Ca-intercalated: {d_CaC6} A")

print(f"""
Intercalant sits between layers, at the center of the hexagonal
ring projected from above. Each fuel atom is surrounded by:
  - 6 C atoms in the layer above (hexagonal ring)
  - 6 C atoms in the layer below (hexagonal ring)
  - Total: 12 cage atoms (N=12, N^2=144)

  Top layer:    C---C
               / \\ / \\
              C   *   C     (* = intercalant site, directly above fuel)
               \\ / \\ /
                C---C

  Fuel atom:       O        (between layers)

  Bottom layer: C---C
               / \\ / \\
              C   *   C
               \\ / \\ /
                C---C

Distance from fuel to cage C atoms:
  In-plane: {r_void} A (to the 6 C in same-layer ring)
  Vertical: half the interlayer spacing
  3D distance: sqrt(r_void^2 + (d/2)^2)
""")

# ==============================================================
# Graphene-based fusion host candidates
# ==============================================================

E_zp = 0.025 * e  # zero-point energy

candidates = []

def calc_fusion(name, fuel, Z2, A2, d_fuel_A, N_cage, Tc, mid_factor, notes):
    """Calculate fusion parameters for a candidate."""
    m_red = m_p * A2 / (1 + A2)
    v_zp = math.sqrt(2 * E_zp / m_red)
    eta = Z2 * alpha * c / v_zp

    # W kernel extension with coherent N^2
    w_ext = 1.0 + 0.001 * mid_factor * Tc * N_cage  # N not N^2 in extension
    if Tc == 0:
        w_ext = 1.0

    eta_eff = eta / w_ext
    log_R = math.log10(1e13) + (-2 * math.pi * eta_eff * log10e) + math.log10(N_cage)

    # What if the coefficient is 0.01 instead of 0.001?
    w_ext_10x = 1.0 + 0.01 * mid_factor * Tc * N_cage if Tc > 0 else 1.0
    eta_eff_10x = eta / w_ext_10x
    log_R_10x = math.log10(1e13) + (-2 * math.pi * eta_eff_10x * log10e) + math.log10(N_cage)

    # What about 0.1?
    w_ext_100x = 1.0 + 0.1 * mid_factor * Tc * N_cage if Tc > 0 else 1.0
    eta_eff_100x = eta / w_ext_100x
    log_R_100x = math.log10(1e13) + (-2 * math.pi * eta_eff_100x * log10e) + math.log10(N_cage)

    return {
        "name": name, "fuel": fuel, "Z2": Z2, "N": N_cage, "Tc": Tc,
        "mid": mid_factor, "d_A": d_fuel_A,
        "eta": eta, "eta_eff": eta_eff, "w_ext": w_ext,
        "log_R": log_R,
        "eta_10x": eta_eff_10x, "log_R_10x": log_R_10x, "w_ext_10x": w_ext_10x,
        "eta_100x": eta_eff_100x, "log_R_100x": log_R_100x, "w_ext_100x": w_ext_100x,
        "notes": notes,
    }

# Distance calculations
def cage_dist(r_plane, d_layer):
    """3D distance from intercalant to cage atom."""
    return math.sqrt(r_plane**2 + (d_layer/2)**2)

# --- Candidate 1: LiC6 + hydrogen (existing material) ---
# Li between graphene layers, add H
# Li sits at hex center, H sits at adjacent hex center
# Li-H distance ~ lattice parameter 2.46 A in-plane
# But Li and H could share the same interlayer space
# Closer: Li-H ~ 1.5-2.0 A in confined interlayer
d_LiH_in_graphene = 1.8
N_LiC6 = 12  # 6 above + 6 below
# CaC6 is SC at 11.5K, LiC6 is not naturally SC but...
# Li-decorated graphene has been predicted to superconduct at ~8K
candidates.append(calc_fusion(
    "LiC6 graphite + H (p-Li7)", "p-Li7", 3, 7,
    d_LiH_in_graphene, N_LiC6, 8, 8.0,
    "Li already between layers. Add H. Predicted SC ~8K."
))

# --- Candidate 2: CaC6 + H + Li (SC at 11.5K) ---
# Ca between layers makes it SC. Co-intercalate Li and H.
candidates.append(calc_fusion(
    "CaC6 + Li + H (p-Li7)", "p-Li7", 3, 7,
    1.8, 12, 11.5, 8.0,
    "CaC6 is proven SC at 11.5K. Co-intercalate Li+H."
))

# --- Candidate 3: Magic angle twisted bilayer (MATBG) + Li + H ---
# MATBG superconducts at ~1.5K at 1.1 degree twist
# Moire pattern creates superlattice with LARGE periodic voids
# These voids can trap intercalants
# Moire period ~ 13 nm — huge cage, many atoms per ring
# But relevant N is still the local hexagonal ring: 6 per layer
candidates.append(calc_fusion(
    "MATBG + Li + H (p-Li7)", "p-Li7", 3, 7,
    1.5, 12, 1.5, 10.0,
    "Magic angle bilayer. Moire superlattice voids. SC ~1.5K."
))

# --- Candidate 4: Twisted trilayer graphene + Li + H ---
# Higher Tc than bilayer: up to ~3K
# Three layers = better cage confinement
# Fuel between layers 1-2, also between layers 2-3
# N = 6+6+6 = 18 (three hexagonal rings)
candidates.append(calc_fusion(
    "Twisted trilayer + Li + H (p-Li7)", "p-Li7", 3, 7,
    1.5, 18, 3, 12.0,
    "Trilayer: 3 hex rings = 18 cage atoms. SC ~3K."
))

# --- Candidate 5: Graphene + B substitution + H ---
# Replace some C with B in the graphene lattice
# Now B is IN the honeycomb ring itself
# H intercalated between layers sits directly adjacent to B
# B-H distance = C-C bond length minus the size difference ~ 1.5 A
# The B is literally part of the cage wall
candidates.append(calc_fusion(
    "B-doped graphene + H (p-B11)", "p-B11", 5, 11,
    1.5, 12, 8, 12.0,
    "Boron IN the honeycomb wall. H between layers. Maximum proximity."
))

# --- Candidate 6: BC3 honeycomb + H ---
# BC3: known compound, boron and carbon in honeycomb
# Each hex ring has alternating B and C
# B-B distance across ring: ~2.5 A
# H between layers, directly above B site
# This is a REAL MATERIAL that has been synthesized
candidates.append(calc_fusion(
    "BC3 honeycomb + H (p-B11)", "p-B11", 5, 11,
    1.6, 12, 5, 10.0,
    "BC3 is real. B in honeycomb lattice. H between layers."
))

# --- Candidate 7: h-BN (hexagonal boron nitride) + H ---
# Pure hexagonal BN — boron AND nitrogen in honeycomb
# Not normally SC, but under pressure or doping might be
# The structure is perfect: every other atom is boron
# H between layers sees 3 B + 3 N per ring = 6 cage atoms with 3 B
candidates.append(calc_fusion(
    "h-BN + H (p-B11)", "p-B11", 5, 11,
    1.5, 6, 0, 6.0,  # NOT superconducting
    "Perfect honeycomb with B. NOT superconducting. Control case."
))

# --- Candidate 8: Cu3O2 kagome + Li + H (from before, for comparison) ---
candidates.append(calc_fusion(
    "Cu3O2 kagome + Li + H (p-Li7)", "p-Li7", 3, 7,
    1.5, 6, 370, 8.0,
    "Previous winner. Kagome void channel."
))

# --- Candidate 9: MULTILAYER graphene superlattice ---
# Stack: graphene / Li / graphene / H / graphene / Li / graphene / H ...
# Each H layer is sandwiched between two graphene layers with Li on both sides
# Li-H distance minimized, N = 12 per H site, and the REPEATING structure
# means the condensate is reinforced by periodicity
# If the stack is SC, the coherence extends across many layers
candidates.append(calc_fusion(
    "Graphene/Li/H superlattice", "p-Li7", 3, 7,
    1.3, 24, 15, 15.0,  # 24 cage atoms (4 rings), estimated Tc ~15K
    "Engineered multilayer: maximize cage atoms and condensate overlap."
))

# --- Candidate 10: The dream — graphene scaffold at Cu3O2 kagome Tc ---
# What if you could make a graphene-based material SC at high Tc?
# Hydrogenated graphene (graphane) under pressure?
# Or graphene proximity-coupled to Cu3O2?
candidates.append(calc_fusion(
    "Graphene scaffold @ Tc=100K", "p-Li7", 3, 7,
    1.3, 24, 100, 15.0,
    "Hypothetical: graphene multilayer with high Tc via proximity or pressure."
))

# ==============================================================
# Results
# ==============================================================
print(f"\n{'='*70}")
print("GRAPHENE FUSION CANDIDATES (coefficient = 0.001)")
print(f"{'='*70}\n")

candidates.sort(key=lambda c: c["log_R"], reverse=True)

print(f"{'#':>2} | {'Structure':<38} | {'Tc':>4} | {'N':>3} | {'W ext':>5} | {'eta_eff':>7} | {'log(R)':>8}")
print(f"{'-'*2}-+-{'-'*38}-+-{'-'*4}-+-{'-'*3}-+-{'-'*5}-+-{'-'*7}-+-{'-'*8}")
for i, c in enumerate(candidates):
    print(f"{i+1:2} | {c['name']:<38} | {c['Tc']:4} | {c['N']:3} | {c['w_ext']:5.1f} | {c['eta_eff']:7.0f} | {c['log_R']:8.0f}")

print(f"\n{'='*70}")
print("SAME CANDIDATES (coefficient = 0.01 — 10x stronger W coupling)")
print(f"{'='*70}\n")

candidates.sort(key=lambda c: c["log_R_10x"], reverse=True)

print(f"{'#':>2} | {'Structure':<38} | {'W ext':>6} | {'eta':>5} | {'log(R)':>8} | {'Detectable?':>12}")
print(f"{'-'*2}-+-{'-'*38}-+-{'-'*6}-+-{'-'*5}-+-{'-'*8}-+-{'-'*12}")
for i, c in enumerate(candidates):
    det = "YES!" if c["log_R_10x"] > -15 else "close" if c["log_R_10x"] > -30 else "no"
    print(f"{i+1:2} | {c['name']:<38} | {c['w_ext_10x']:6.1f} | {c['eta_10x']:5.0f} | {c['log_R_10x']:8.0f} | {det:>12}")

print(f"\n{'='*70}")
print("SAME CANDIDATES (coefficient = 0.1 — 100x stronger W coupling)")
print(f"{'='*70}\n")

candidates.sort(key=lambda c: c["log_R_100x"], reverse=True)

print(f"{'#':>2} | {'Structure':<38} | {'W ext':>6} | {'eta':>5} | {'log(R)':>8} | {'Power/kg':>12}")
print(f"{'-'*2}-+-{'-'*38}-+-{'-'*6}-+-{'-'*5}-+-{'-'*8}-+-{'-'*12}")

Q_Li7 = 17.2 * MeV
Q_B11 = 8.7 * MeV
n_fuel = 2e25

for i, c in enumerate(candidates):
    Q = Q_Li7 if "Li7" in c["fuel"] else Q_B11
    log_P = c["log_R_100x"] + math.log10(n_fuel) + math.log10(Q)

    if log_P > 6:
        pwr = f"{10**(log_P-6):.0e} MW"
    elif log_P > 3:
        pwr = f"{10**(log_P-3):.0e} kW"
    elif log_P > 0:
        pwr = f"{10**log_P:.0e} W"
    elif log_P > -3:
        pwr = f"{10**(log_P+3):.0e} mW"
    else:
        pwr = f"10^{log_P:.0f} W"

    print(f"{i+1:2} | {c['name']:<38} | {c['w_ext_100x']:6.0f} | {c['eta_100x']:5.1f} | {c['log_R_100x']:8.1f} | {pwr:>12}")

# ==============================================================
# The graphene insight
# ==============================================================
print(f"\n{'='*70}")
print("THE GRAPHENE INSIGHT")
print(f"{'='*70}\n")

best = candidates[0]
print(f"Winner: {best['name']}")
print(f"")

print(f"""
Why graphene changes the game:

1. MULTILAYER STACKING: Graphene layers can be stacked to create
   3D cage structures. Each fuel atom sees cage atoms from MULTIPLE
   layers. N=24 for a 4-layer cage (N^2=576) vs N=6 for kagome (N^2=36).
   That's 16x more coherent enhancement from geometry alone.

2. TUNABLE SPACING: Twist angle and intercalant choice control the
   interlayer distance precisely. You can dial in the optimal
   fuel-cage distance to within 0.1 Angstrom. No other material
   gives you this level of geometric control.

3. EXISTING INTERCALATION CHEMISTRY: Li, H, B, Ca, K, Na — all have
   been intercalated into graphite. The synthesis is known.
   You don't need to invent a new material. You need to combine
   existing techniques in a specific way.

4. PROXIMITY-COUPLED SUPERCONDUCTIVITY: Graphene on a SC substrate
   inherits superconductivity via proximity effect. You could
   deposit graphene multilayers on Cu3O2 — the kagome SC provides
   Tc=370K and the graphene provides the cage geometry.

5. SCALABILITY: Graphene is cheap. Chemical vapor deposition makes
   it in rolls. The cost of the active material would be negligible.

The dream configuration:
  Cu3O2 substrate (provides SC condensate at 370K)
  + Graphene multilayer on top (provides cage geometry)
  + Li + H intercalated between graphene layers
  + Proximity-coupled SC through the whole stack
  + 24-atom cage per fuel site, Tc=370K

This combines the best of both worlds:
  Cu3O2's high Tc × Graphene's perfect cage geometry
""")

# Final calculation for the dream config
dream = calc_fusion(
    "DREAM: Cu3O2/Graphene/Li/H", "p-Li7", 3, 7,
    1.3, 24, 370, 15.0,
    "Proximity-coupled graphene multilayer on Cu3O2 kagome."
)

print(f"{'='*70}")
print(f"DREAM CONFIGURATION: Cu3O2 substrate + Graphene cage + Li + H")
print(f"{'='*70}\n")

for label, coeff in [("0.001 (conservative)", "log_R"),
                      ("0.01 (moderate)", "log_R_10x"),
                      ("0.1 (strong)", "log_R_100x")]:
    lr = dream[coeff]
    Q = Q_Li7
    log_P = lr + math.log10(n_fuel) + math.log10(Q)

    if log_P > 9:
        pwr = f"10^{log_P:.0f} W = {10**(log_P-9):.0e} GW"
    elif log_P > 6:
        pwr = f"{10**(log_P-6):.0e} MW"
    elif log_P > 3:
        pwr = f"{10**(log_P-3):.0e} kW"
    elif log_P > 0:
        pwr = f"{10**log_P:.0e} W"
    else:
        pwr = f"10^{log_P:.0f} W"

    eta_key = "eta_eff" if coeff == "log_R" else "eta_10x" if coeff == "log_R_10x" else "eta_100x"
    w_key = "w_ext" if coeff == "log_R" else "w_ext_10x" if coeff == "log_R_10x" else "w_ext_100x"

    print(f"  W coefficient {label}:")
    print(f"    Extension: {dream[w_key]:.1f}x | eta: {dream[eta_key]:.1f} | Rate: 10^{lr:.0f}/atom/s | Power: {pwr}")
    print()

print(f"""
The W kernel coupling coefficient is THE unknown.
At 0.001: nothing detectable (eta still too high).
At 0.01:  the numbers start moving but still below detection.
At 0.1:   practical power levels from the dream configuration.

The MgB2 experiment measures this coefficient.
That one $3,000 experiment determines which row of this table
we're in — and whether fusion, antigravity, and everything else
is real or fantasy.
""")
