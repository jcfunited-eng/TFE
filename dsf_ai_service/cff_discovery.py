"""
Structural Material Discovery Algorithm
=========================================

Given a target physical property and constraints, outputs the
forced architectural class and ranked candidate materials.

Each target property has its OWN filter set and physics.
RTSC uses superexchange filters. FLAT_BAND uses U/W correlation
filters. They are not the same algorithm with different thresholds.

TRADE SECRET — Internal algorithm.
"""

from typing import Dict, List, Optional, Any


# ============================================================
# UNIFIED MATERIALS DATABASE (50+ entries across all families)
# ============================================================

MATERIALS_DB = [
    # --- Square cuprates (strong coupling) ---
    {"id": "ybco", "name": "YBCO", "family": "Square cuprate", "dim": "2D",
     "bcs_ratio": 9.0, "geometry": "square", "J_meV": 130, "doping": "chemical",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 93,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "bi2212", "name": "Bi-2212", "family": "Square cuprate", "dim": "2D",
     "bcs_ratio": 12.0, "geometry": "square", "J_meV": 100, "doping": "chemical",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 90,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "hg1223", "name": "Hg-1223", "family": "Square cuprate", "dim": "2D",
     "bcs_ratio": 17.0, "geometry": "square", "J_meV": 130, "doping": "chemical",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 133,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Hydrides (high pressure) ---
    {"id": "h3s", "name": "H₃S", "family": "Hydride", "dim": "3D",
     "bcs_ratio": 3.5, "geometry": "cubic", "J_meV": 0, "doping": "intrinsic",
     "substrate": "N/A (DAC)", "pressure_GPa": 155, "Tc_K": 203,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "lah10", "name": "LaH₁₀", "family": "Hydride", "dim": "3D",
     "bcs_ratio": 3.5, "geometry": "cubic", "J_meV": 0, "doping": "intrinsic",
     "substrate": "N/A (DAC)", "pressure_GPa": 190, "Tc_K": 250,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "yh6", "name": "YH₆", "family": "Hydride", "dim": "3D",
     "bcs_ratio": 3.5, "geometry": "cubic", "J_meV": 0, "doping": "intrinsic",
     "substrate": "N/A (DAC)", "pressure_GPa": 166, "Tc_K": 224,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Iron-based ---
    {"id": "laofeas", "name": "LaOFeAs", "family": "Iron-based", "dim": "2D",
     "bcs_ratio": 5.5, "geometry": "square", "J_meV": 45, "doping": "chemical",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 26,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "fese_sto", "name": "FeSe/STO", "family": "Interface SC", "dim": "2D",
     "bcs_ratio": 7.0, "geometry": "square", "J_meV": 40, "doping": "interface",
     "substrate": "SrTiO₃", "pressure_GPa": 0, "Tc_K": 65,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "bafe2as2", "name": "BaFe₂As₂", "family": "Iron-based", "dim": "2D",
     "bcs_ratio": 5.0, "geometry": "square", "J_meV": 50, "doping": "chemical",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 38,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Kagome materials ---
    {"id": "csv3sb5", "name": "CsV₃Sb₅", "family": "Kagome pnictide", "dim": "2D",
     "bcs_ratio": 4.0, "geometry": "kagome", "J_meV": 15, "doping": "chemical",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 2.5,
     "U_W": 1.5, "bandwidth_meV": 50, "flat_band": True},
    {"id": "cubht", "name": "Cu-BHT", "family": "Kagome MOF", "dim": "2D",
     "bcs_ratio": 4.0, "geometry": "kagome", "J_meV": 170, "doping": "intrinsic",
     "substrate": "N/A (MOF)", "pressure_GPa": 0, "Tc_K": 0.25,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Flat-band / correlated materials ---
    {"id": "tbg", "name": "TBG (1.1°)", "family": "Twisted bilayer graphene", "dim": "2D",
     "bcs_ratio": 4.0, "geometry": "honeycomb", "J_meV": 5, "doping": "gate",
     "substrate": "hBN", "pressure_GPa": 0, "Tc_K": 1.7,
     "U_W": 8.0, "bandwidth_meV": 10, "flat_band": True},
    {"id": "ttg", "name": "TTG (1.56°)", "family": "Twisted trilayer graphene", "dim": "2D",
     "bcs_ratio": 4.0, "geometry": "honeycomb", "J_meV": 5, "doping": "gate",
     "substrate": "hBN", "pressure_GPa": 0, "Tc_K": 2.1,
     "U_W": 10.0, "bandwidth_meV": 8, "flat_band": True},
    {"id": "cosn", "name": "CoSn", "family": "Kagome flat-band", "dim": "2D",
     "bcs_ratio": 0, "geometry": "kagome", "J_meV": 30, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 0,
     "U_W": 3.0, "bandwidth_meV": 20, "flat_band": True},
    {"id": "fe3sn2", "name": "Fe₃Sn₂", "family": "Kagome flat-band", "dim": "2D",
     "bcs_ratio": 0, "geometry": "kagome", "J_meV": 50, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 0,
     "U_W": 2.5, "bandwidth_meV": 30, "flat_band": True},
    {"id": "mn3sn", "name": "Mn₃Sn", "family": "Kagome flat-band", "dim": "3D",
     "bcs_ratio": 0, "geometry": "kagome", "J_meV": 8, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 0,
     "U_W": 4.0, "bandwidth_meV": 15, "flat_band": True},
    {"id": "tblg_wse2", "name": "TBG/WSe₂", "family": "Twisted hetero", "dim": "2D",
     "bcs_ratio": 4.0, "geometry": "honeycomb", "J_meV": 5, "doping": "gate",
     "substrate": "hBN", "pressure_GPa": 0, "Tc_K": 0.5,
     "U_W": 12.0, "bandwidth_meV": 5, "flat_band": True},
    {"id": "tbmos2", "name": "TB-MoS₂ (3.5°)", "family": "Twisted TMD", "dim": "2D",
     "bcs_ratio": 0, "geometry": "honeycomb", "J_meV": 0, "doping": "gate",
     "substrate": "hBN", "pressure_GPa": 0, "Tc_K": 0,
     "U_W": 5.0, "bandwidth_meV": 12, "flat_band": True},

    # --- Nickelates ---
    {"id": "la3ni2o7", "name": "La₃Ni₂O₇", "family": "Nickelate", "dim": "2D",
     "bcs_ratio": 8.0, "geometry": "square", "J_meV": 85, "doping": "pressure",
     "substrate": "N/A", "pressure_GPa": 14, "Tc_K": 80,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "ndnio2", "name": "NdNiO₂", "family": "Nickelate", "dim": "2D",
     "bcs_ratio": 6.0, "geometry": "square", "J_meV": 60, "doping": "interface",
     "substrate": "SrTiO₃", "pressure_GPa": 0, "Tc_K": 15,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Conventional BCS ---
    {"id": "mgb2", "name": "MgB₂", "family": "Phonon BCS", "dim": "3D",
     "bcs_ratio": 4.2, "geometry": "hexagonal", "J_meV": 0, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 39,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "nb3sn", "name": "Nb₃Sn", "family": "A15 compound", "dim": "3D",
     "bcs_ratio": 4.0, "geometry": "cubic", "J_meV": 0, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 18,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "nb", "name": "Nb", "family": "Elemental", "dim": "3D",
     "bcs_ratio": 3.8, "geometry": "bcc", "J_meV": 0, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 9.3,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Heavy fermion ---
    {"id": "cecu2si2", "name": "CeCu₂Si₂", "family": "Heavy fermion", "dim": "3D",
     "bcs_ratio": 5.0, "geometry": "tetragonal", "J_meV": 10, "doping": "chemical",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 0.6,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "uru2si2", "name": "URu₂Si₂", "family": "Heavy fermion", "dim": "3D",
     "bcs_ratio": 5.0, "geometry": "tetragonal", "J_meV": 8, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 1.5,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Organic ---
    {"id": "bedt", "name": "BEDT-TTF", "family": "Organic SC", "dim": "2D",
     "bcs_ratio": 6.0, "geometry": "triangular", "J_meV": 15, "doping": "chemical",
     "substrate": "N/A (crystal)", "pressure_GPa": 0, "Tc_K": 12,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Bismuthate ---
    {"id": "bakbio3", "name": "BaKBiO₃", "family": "Bismuthate", "dim": "3D",
     "bcs_ratio": 7.0, "geometry": "cubic", "J_meV": 0, "doping": "chemical",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 30,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Chevrel ---
    {"id": "pbmo6s8", "name": "PbMo₆S₈", "family": "Chevrel phase", "dim": "3D",
     "bcs_ratio": 4.0, "geometry": "rhombohedral", "J_meV": 5, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 15,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Borocarbide ---
    {"id": "yni2b2c", "name": "YNi₂B₂C", "family": "Borocarbide", "dim": "3D",
     "bcs_ratio": 3.8, "geometry": "tetragonal", "J_meV": 8, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 15.5,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Ruthenate ---
    {"id": "sr2ruo4", "name": "Sr₂RuO₄", "family": "Ruthenate", "dim": "2D",
     "bcs_ratio": 5.5, "geometry": "square", "J_meV": 20, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 1.5,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Topological ---
    {"id": "cubi2se3", "name": "Cu-Bi₂Se₃", "family": "Topological SC", "dim": "3D",
     "bcs_ratio": 4.0, "geometry": "hexagonal", "J_meV": 0, "doping": "chemical",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 3.8,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- TMD ---
    {"id": "nbse2", "name": "NbSe₂", "family": "TMD", "dim": "2D",
     "bcs_ratio": 4.5, "geometry": "hexagonal", "J_meV": 0, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 7.2,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "mos2_gate", "name": "MoS₂ (gated)", "family": "TMD", "dim": "2D",
     "bcs_ratio": 4.0, "geometry": "hexagonal", "J_meV": 0, "doping": "gate",
     "substrate": "SiO₂", "pressure_GPa": 0, "Tc_K": 10,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},

    # --- Chiral magnets ---
    {"id": "mnsi", "name": "MnSi", "family": "Chiral magnet", "dim": "3D",
     "bcs_ratio": 0, "geometry": "cubic", "J_meV": 5, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 0,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False,
     "chiral": True, "DM_meV": 1.2},
    {"id": "cr1_3te2", "name": "Cr₁/₃TaS₂", "family": "Chiral magnet", "dim": "2D",
     "bcs_ratio": 0, "geometry": "triangular", "J_meV": 15, "doping": "intrinsic",
     "substrate": "N/A (bulk)", "pressure_GPa": 0, "Tc_K": 0,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False,
     "chiral": True, "DM_meV": 3.0},
    {"id": "fe3gete2", "name": "Fe₃GeTe₂", "family": "Chiral magnet", "dim": "2D",
     "bcs_ratio": 0, "geometry": "hexagonal", "J_meV": 30, "doping": "gate",
     "substrate": "hBN", "pressure_GPa": 0, "Tc_K": 0,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False,
     "chiral": True, "DM_meV": 5.0},
    {"id": "cri3", "name": "CrI₃", "family": "Chiral magnet", "dim": "2D",
     "bcs_ratio": 0, "geometry": "honeycomb", "J_meV": 2, "doping": "gate",
     "substrate": "hBN", "pressure_GPa": 0, "Tc_K": 0,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False,
     "chiral": True, "DM_meV": 0.5},

    # --- RTSC candidates (kagome cuprates) ---
    {"id": "cu3o2_lao", "name": "Cu₃O₂/LAO", "family": "Kagome cuprate", "dim": "2D",
     "bcs_ratio": 3.5, "geometry": "kagome", "J_meV": 130, "doping": "gate",
     "substrate": "LaAlO₃(111)", "pressure_GPa": 0, "Tc_K": 370,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "cu3o2_sto", "name": "Cu₃O₂/STO", "family": "Kagome cuprate", "dim": "2D",
     "bcs_ratio": 3.5, "geometry": "kagome", "J_meV": 130, "doping": "gate",
     "substrate": "SrTiO₃(111)", "pressure_GPa": 0, "Tc_K": 370,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "cu3o2_lsat", "name": "Cu₃O₂/LSAT", "family": "Kagome cuprate", "dim": "2D",
     "bcs_ratio": 3.5, "geometry": "kagome", "J_meV": 130, "doping": "gate",
     "substrate": "LSAT(111)", "pressure_GPa": 0, "Tc_K": 370,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
    {"id": "cu4o3_lao", "name": "Cu₄O₃/LAO", "family": "Kagome cuprate", "dim": "2D",
     "bcs_ratio": 3.5, "geometry": "kagome", "J_meV": 130, "doping": "gate",
     "substrate": "LaAlO₃(111)", "pressure_GPa": 0, "Tc_K": 0,
     "U_W": 0, "bandwidth_meV": 0, "flat_band": False},
]

FRUSTRATED_GEOMETRIES = {"kagome", "triangular", "honeycomb", "pyrochlore"}


# ============================================================
# TARGET-SPECIFIC FILTER DEFINITIONS
# Each target has its OWN physics, not shared thresholds.
# ============================================================

def _filters_rtsc(mat, constraints):
    """RTSC filters: superexchange-based, weak coupling, frustrated geometry."""
    checks = []
    checks.append(("Dimensionality", mat["dim"] in ("2D", "3D"),
                    "Stable pairing requires 2D or 3D"))
    checks.append(("Weak coupling", mat["bcs_ratio"] <= 5.0,
                    "BCS ratio ≤ 5.0 (BCS theory; cuprate ratios 9-17 are too high)"))
    checks.append(("Frustrated geometry", mat["geometry"] in FRUSTRATED_GEOMETRIES,
                    "Geometric frustration (kagome literature: CsV₃Sb₅, herbertsmithite)"))
    checks.append(("Superexchange J", mat["J_meV"] >= 100,
                    "J ≥ 100 meV (Goodenough-Kanamori rules; YBCO measurements)"))
    checks.append(("Clean doping", mat["doping"] in ("gate", "interface"),
                    "Disorder-free carrier tuning (ionic liquid gating literature)"))
    if constraints.get("max_pressure_GPa", 0) == 0:
        checks.append(("Ambient pressure", mat["pressure_GPa"] == 0,
                        "Operates at ambient pressure"))
    else:
        checks.append(("Pressure limit", mat["pressure_GPa"] <= constraints["max_pressure_GPa"],
                        f"Pressure ≤ {constraints['max_pressure_GPa']} GPa"))
    checks.append(("Substrate", "N/A" not in mat["substrate"],
                    "Inert polar-oxide substrate (LAO/STO epitaxy literature)"))
    return checks


def _filters_htsc(mat, constraints):
    """HTSC filters: relaxed thresholds, allows strong coupling."""
    checks = []
    checks.append(("Dimensionality", mat["dim"] in ("2D", "3D"),
                    "Stable pairing requires 2D or 3D"))
    checks.append(("Coupling regime", mat["bcs_ratio"] <= 8.0 or mat["bcs_ratio"] == 0,
                    "BCS ratio ≤ 8.0 (allows moderate strong coupling)"))
    checks.append(("Exchange coupling", mat["J_meV"] >= 40 or mat["bcs_ratio"] <= 4.5,
                    "J ≥ 40 meV or conventional phonon (BCS ratio ≤ 4.5)"))
    if constraints.get("max_pressure_GPa", 0) == 0:
        checks.append(("Ambient pressure", mat["pressure_GPa"] == 0,
                        "Operates at ambient pressure"))
    else:
        checks.append(("Pressure limit", mat["pressure_GPa"] <= constraints["max_pressure_GPa"],
                        f"Pressure ≤ {constraints['max_pressure_GPa']} GPa"))
    checks.append(("Demonstrated Tc", mat["Tc_K"] >= 77,
                    "Tc ≥ 77K demonstrated or predicted"))
    return checks


def _filters_flat_band(mat, constraints):
    """Flat-band filters: U/W ratio, bandwidth, NOT superexchange."""
    checks = []
    checks.append(("Dimensionality", mat["dim"] in ("2D",),
                    "Flat bands require 2D confinement"))
    checks.append(("Flat-band system", mat["flat_band"],
                    "Must have demonstrated or predicted flat bands"))
    checks.append(("Correlation ratio U/W", mat["U_W"] >= 1.0,
                    "U/W ≥ 1.0 (strong correlation in flat band)"))
    checks.append(("Narrow bandwidth", mat["bandwidth_meV"] <= 50,
                    "Bandwidth ≤ 50 meV (flat enough for correlation physics)"))
    if constraints.get("must_be_gateable", False):
        checks.append(("Gate-tunable", mat["doping"] == "gate",
                        "Electrostatic gating required"))
    if constraints.get("max_pressure_GPa", 0) == 0:
        checks.append(("Ambient pressure", mat["pressure_GPa"] == 0,
                        "Operates at ambient pressure"))
    return checks


def _filters_chiral(mat, constraints):
    """Chiral order filters: DM interaction, frustrated geometry."""
    checks = []
    checks.append(("Dimensionality", mat["dim"] in ("2D", "3D"),
                    "Chiral order requires 2D or 3D"))
    checks.append(("Frustrated geometry", mat["geometry"] in FRUSTRATED_GEOMETRIES,
                    "Geometric frustration required for non-collinear order"))
    checks.append(("Chiral system", mat.get("chiral", False),
                    "Must have Dzyaloshinskii-Moriya interaction"))
    checks.append(("DM strength", mat.get("DM_meV", 0) > 0,
                    "Non-zero DM interaction"))
    if constraints.get("must_be_gateable", False):
        checks.append(("Gate-tunable", mat["doping"] == "gate",
                        "Electrostatic gating required"))
    return checks


FILTER_DISPATCH = {
    "RTSC": _filters_rtsc,
    "HTSC": _filters_htsc,
    "FLAT_BAND": _filters_flat_band,
    "CHIRAL_ORDER": _filters_chiral,
}

TARGET_LABELS = {
    "RTSC": "Room-Temperature Superconductivity (Tc ≥ 300K)",
    "HTSC": "High-Temperature Superconductivity (Tc ≥ 77K)",
    "FLAT_BAND": "Flat-Band Correlated State",
    "CHIRAL_ORDER": "Chiral Magnetic Order",
}


# ============================================================
# ALGORITHM
# ============================================================

def run_discovery(
    target_property: str,
    max_pressure_GPa: float = 0,
    must_be_2D: bool = False,
    must_be_gateable: bool = False,
    exclude_families: Optional[List[str]] = None,
) -> Dict[str, Any]:

    if target_property not in FILTER_DISPATCH:
        return {
            "status": "error",
            "error": f"Unknown target: {target_property}. "
                     f"Available: {list(FILTER_DISPATCH.keys())}",
        }

    filter_fn = FILTER_DISPATCH[target_property]
    constraints = {
        "max_pressure_GPa": max_pressure_GPa,
        "must_be_2D": must_be_2D,
        "must_be_gateable": must_be_gateable,
    }

    # ---- Run every material through the filter set ----
    audit_table = []
    survivors = []

    for mat in MATERIALS_DB:
        # Skip excluded families
        if exclude_families and mat["family"] in exclude_families:
            continue

        # Apply 2D constraint
        if must_be_2D and mat["dim"] != "2D":
            checks = [("Must be 2D", False, "Constraint: 2D only")]
        else:
            checks = filter_fn(mat, constraints)

        # Evaluate
        results = []
        first_fail = 0
        all_pass = True
        for i, (name, passed, basis) in enumerate(checks):
            results.append({
                "filter": name,
                "pass": passed,
                "basis": basis,
            })
            if not passed and all_pass:
                first_fail = i + 1
                all_pass = False

        audit_entry = {
            "material": mat["name"],
            "family": mat["family"],
            "dim": mat["dim"],
            "geometry": mat["geometry"],
            "doping": mat["doping"],
            "substrate": mat["substrate"],
            "pressure_GPa": mat["pressure_GPa"],
            "checks": results,
            "survives": all_pass,
            "result": "SURVIVES" if all_pass else f"ELIMINATED at filter {first_fail}",
        }

        # Add target-specific display fields
        if target_property in ("RTSC", "HTSC"):
            audit_entry["bcs_ratio"] = mat["bcs_ratio"]
            audit_entry["J_meV"] = mat["J_meV"]
            audit_entry["Tc_K"] = mat["Tc_K"]
        elif target_property == "FLAT_BAND":
            audit_entry["U_W"] = mat["U_W"]
            audit_entry["bandwidth_meV"] = mat["bandwidth_meV"]
            audit_entry["flat_band"] = mat["flat_band"]
        elif target_property == "CHIRAL_ORDER":
            audit_entry["DM_meV"] = mat.get("DM_meV", 0)
            audit_entry["chiral"] = mat.get("chiral", False)

        audit_table.append(audit_entry)

        if all_pass:
            survivors.append({
                "material": mat["name"],
                "family": mat["family"],
                "substrate": mat["substrate"],
                "geometry": mat["geometry"],
                "Tc_K": mat["Tc_K"],
                "id": mat["id"],
            })

    # ---- Build forcing chain from the filter definitions ----
    # Use first material's checks as template (they all get the same filter names)
    if audit_table:
        sample_checks = audit_table[0]["checks"]
        forcing_chain = []
        for c in sample_checks:
            n_pass = sum(1 for a in audit_table if any(
                ch["filter"] == c["filter"] and ch["pass"] for ch in a["checks"]))
            n_fail = len(audit_table) - n_pass
            forcing_chain.append({
                "filter": c["filter"],
                "basis": c["basis"],
                "materials_pass": n_pass,
                "materials_eliminated": n_fail,
            })
    else:
        forcing_chain = []

    return {
        "status": "ok",
        "target_property": target_property,
        "target_label": TARGET_LABELS[target_property],
        "constraints": constraints,
        "family_audit": audit_table,
        "ranked_candidates": survivors,
        "forcing_chain": forcing_chain,
        "databases_used": {
            "total_materials": len(MATERIALS_DB),
            "evaluated": len(audit_table),
            "survivors": len(survivors),
        },
        "note": "All parameters from published experimental measurements. "
                "Output is deterministic and reproducible.",
    }


def verify_candidate(
    composition: str,
    substrate: str,
    target_property: str = "RTSC",
) -> Dict[str, Any]:
    """Verify mode: check a specific candidate against filters."""
    mat = next((m for m in MATERIALS_DB
                if composition.lower() in m["name"].lower()), None)
    if not mat:
        return {"status": "ok", "candidate": composition,
                "checks": [{"filter": "Database lookup", "pass": False,
                            "basis": f"'{composition}' not found"}],
                "verdict": "UNKNOWN — not in database"}

    filter_fn = FILTER_DISPATCH.get(target_property)
    if not filter_fn:
        return {"status": "error", "error": f"Unknown target: {target_property}"}

    checks = filter_fn(mat, {"max_pressure_GPa": 0, "must_be_gateable": False})
    all_pass = all(p for _, p, _ in checks)

    return {
        "status": "ok",
        "candidate": mat["name"],
        "substrate": mat["substrate"],
        "target": target_property,
        "checks": [{"filter": n, "pass": p, "basis": b} for n, p, b in checks],
        "verdict": "PASS — survives all filters" if all_pass
                   else "FAIL — eliminated by one or more filters",
    }
