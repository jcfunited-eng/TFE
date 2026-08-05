#!/usr/bin/env python3
import csv
from pathlib import Path
from collections import defaultdict

def run_integrity_probe():
    p = Path("real_world_cleaned_universe_l5_row_trace_full.csv")
    if not p.exists():
        return print(f"File missing: {p}")
        
    counts = defaultdict(int)
    anomalies = defaultdict(int)
    
    b_values = []
    p_values = []
    d_values = set()
    s_values = []
    r_values = []
    
    with open(p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            counts["TOTAL_ROWS"] += 1
            
            try:
                B_val = float(row.get("B", row.get("B_k", 0)))
                P_val = float(row.get("P", row.get("P_k", 0)))
                D_val = float(row.get("D", row.get("D_k", 0)))
                S_UF = float(row.get("S_UF", 0))
                R_UF = float(row.get("R_UF", 0))
                
                b_values.append(B_val)
                p_values.append(P_val)
                d_values.add(D_val)
                s_values.append(S_UF)
                r_values.append(R_UF)
                
                # Invariant checks per TFE Specification
                if P_val not in [0.0, 1.0, 2.0]:
                    anomalies["P_NOT_VALID_INTEGER_STRESS"] += 1
                
                if D_val not in [-1.0, 0.0, 1.0]:
                    anomalies["D_NOT_VALID_DIRECTION"] += 1
                    
            except Exception:
                anomalies["DATA_TYPE_CORRUPTION"] += 1

    print("\n================ L0-L4 INTEGRITY REPORT ================")
    print(f"Total Rows Scanned:      {counts['TOTAL_ROWS']}")
    print(f"Unique 'D' values:       {sorted(list(d_values))}")
    print(f"'B' (Carry) Range:       {min(b_values):.4f} to {max(b_values):.4f}")
    print(f"'P' (Stress) Range:      {min(p_values):.4f} to {max(p_values):.4f}")
    print(f"'S_UF' (Support) Range:  {min(s_values):.4f} to {max(s_values):.4f}")
    print(f"'R_UF' (Resonance):      {min(r_values):.4f} to {max(r_values):.4f}")
    print("---------------- ANOMALIES DETECTED --------------------")
    if not anomalies:
        print("ZERO ANOMALIES. Data format is mathematically valid.")
    else:
        for k, v in anomalies.items():
            print(f"{k}: {v}")
    print("========================================================\n")

if __name__ == "__main__":
    run_integrity_probe()