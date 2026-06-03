# Add image_chard to any residue JSON missing it.
import json, os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RES = ROOT / "memory" / "morphogen" / "residues"

def chard(title):
    return {
        "spine":{"gist":title or "residue","when":datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),"where":"internal","confidence":0.8},
        "primary_veins":[{"feature":"shape","type":"text","confidence":0.5}],
        "secondary_veins":[{"context":"residue","modality":"affect","confidence":0.4}],
        "tissue_hint":{"mood":"neutral","confidence":0.3}
    }

cnt=0
for p in RES.glob("*.json"):
    try:
        data=json.load(open(p,"r",encoding="utf-8"))
        if "image_chard" not in data:
            data["image_chard"]=chard(data.get("title") or data.get("origin"))
            json.dump(data, open(p,"w",encoding="utf-8"), indent=2)
            cnt+=1
    except: pass
print(f"[chardify] updated {cnt} residue(s)")
