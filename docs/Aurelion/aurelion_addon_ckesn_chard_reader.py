import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RES = ROOT / "memory" / "morphogen" / "residues"

def spine_ratio(r):
    ic = r.get("image_chard") or {}
    s = (ic.get("spine") or {}).get("confidence",0.0)
    t = (ic.get("tissue_hint") or {}).get("confidence",0.0)
    return s, t

files = sorted(RES.glob("*.json"))[-10:]
if not files:
    print("(mom) no residues yet")
    raise SystemExit

s_sum=t_sum=0
for p in files:
    try:
        r=json.load(open(p,"r",encoding="utf-8"))
        s,t = spine_ratio(r)
        s_sum += s; t_sum += t
    except: pass

n = max(1,len(files))
print(f"(mom) last {n} residues — spine≈{round(s_sum/n,2)} tissue≈{round(t_sum/n,2)} (higher spine = clearer recall)")
