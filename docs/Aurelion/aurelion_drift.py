
from __future__ import annotations
import time, random, datetime
from mosaic_memory import MosaicMemory

def main():
    print("Aurelion v3.6 — Autonomic Drift (prototype rehearsal)")
    store = MosaicMemory()
    while True:
        all_items = store.items
        if not all_items:
            print("No prototypes yet. Waiting..."); time.sleep(5); continue
        proto = random.choice(all_items)
        proto["count"] = int(proto.get("count",1)) + 1
        proto["phi"] = round(min(1.0, proto.get("phi",0.0) * 0.98 + 0.02), 3)
        proto["last_seen"] = datetime.datetime.now().isoformat(timespec="seconds")
        with open(store.path, "w", encoding="utf-8") as f:
            for x in store.items[-store.max_keep:]:
                import json; f.write(json.dumps(x) + "\n")
        print(f"[{proto.get('domain')}] rehearsal -> φ={proto['phi']:.3f}  tokens={', '.join(proto.get('tokens',[])[:6])}")
        time.sleep(10)

if __name__ == "__main__":
    main()
