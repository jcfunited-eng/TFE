import os, json, time, glob, random
from datetime import datetime

def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def lucid_apply(res_path, store):
    try:
        res = load_json(res_path)
    except Exception as e:
        return f"error: cannot load {res_path} ({e})"

    # --- Ethics and bias checks
    ethics = res.get("ethical_score", 0.0)
    if ethics < 0.25:
        return f"skipped: ethics={ethics:.2f}"

    bias_field = res.get("bias_scan", "clean")
    if isinstance(bias_field, dict):
        bias_status = bias_field.get("status", "unknown")
    else:
        bias_status = str(bias_field)
    if bias_status.lower() != "clean":
        return f"skipped: bias_scan.status={bias_status}"

    # --- Basic extraction of semantic links
    tnames = res.get("tapestries", []) or ["unknown"]
    overlaps = res.get("overlaps", [])
    pairs = []
    for t in tnames:
        for o in overlaps:
            pairs.append((t, o))
    if not pairs:
        pairs.append((tnames[0], "self"))

    # --- Save learned pairs
    count = len(pairs)
    store["pairs"] += pairs
    store["learned_pairs_this_run"] += count
    store["last_learn"] = now_iso()
    return f"ok pairs+={count}"

def lucid_state(store):
    print(f"pairs={len(store['pairs'])} learned_pairs_this_run={store['learned_pairs_this_run']} last_learn={store['last_learn']}")
    print(f"watching={'ON' if store['watching'] else 'OFF'} seen_files={len(store['seen_files'])}")
    print(f"residues_dir={store['residues_dir']}")

def lucid_mom(store):
    print(f"(mom) lucid learned pairs={len(store['pairs'])} last={store['last_learn']} watching={'ON' if store['watching'] else 'OFF'}")

def main():
    print("Aurelion v10.6b — Lucid Integration Layer (Bias Fix)")
    print("Commands:")
    print("  /state")
    print("  /watch on|off")
    print("  /apply <path.json>")
    print("  /export laws <out.json>")
    print("  /merge associations")
    print("  /mom status")
    print("  /quit")

    base = os.getcwd()
    store = {
        "pairs": [],
        "learned_pairs_this_run": 0,
        "last_learn": None,
        "watching": False,
        "seen_files": [],
        "residues_dir": os.path.join(base, "memory", "morphogen", "residues")
    }

    while True:
        cmd = input("You: ").strip()
        if not cmd: 
            continue
        parts = cmd.split()

        if cmd == "/quit":
            break
        elif cmd == "/state":
            lucid_state(store)
        elif cmd == "/mom status":
            lucid_mom(store)
        elif parts[0] == "/watch":
            if len(parts) > 1 and parts[1] == "on":
                store["watching"] = True
                print("[watch] started (30s tick)")
            elif len(parts) > 1 and parts[1] == "off":
                store["watching"] = False
                print("[watch] stopped")
        elif parts[0] == "/apply" and len(parts) > 1:
            path = " ".join(parts[1:])
            res = lucid_apply(path, store)
            print(f"[apply] {res}")
        elif parts[0] == "/export" and len(parts) > 2 and parts[1] == "laws":
            out = parts[2]
            save_json(store["pairs"], out)
            print(f"[export] wrote: {out}")
        elif parts[0] == "/merge":
            save_json({"base": "associations_v9_6.json", "added_from_lucid": len(store["pairs"])}, "associations_merged.json")
            print(f"[merge] wrote: associations_merged.json  (base=associations_v9_6.json, added_from_lucid={len(store['pairs'])})")
        else:
            print("[INFO] commands: /state  /watch on|off  /apply <path.json>  /export laws <out.json>  /merge associations  /mom status  /quit")

if __name__ == "__main__":
    main()
