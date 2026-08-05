
# morphospace_save.py
import os, json, numpy as np
from morphospace import Morphospace, MosaicNode

def save_morphospace(ms: Morphospace, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = {
        "dim": ms.dim, "W": ms.W, "H": ms.H, "step_n": ms.step_n,
        "history": ms.history, "regions": ms.regions,
        "nodes": {
            str(i): {
                "id": n.id, "v": n.v.tolist(), "goal": n.goal.tolist(),
                "energy": float(n.energy), "age": int(n.age),
                "domain": n.domain, "neighbors": list(n.neighbors)
            } for i,n in ms.nodes.items()
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

def load_morphospace(path: str) -> Morphospace:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    ms = Morphospace(dim=d["dim"], grid=(d["W"], d["H"]), seed=42)
    ms.nodes.clear()
    for k, nd in d["nodes"].items():
        n = MosaicNode(
            id=nd["id"],
            v=np.array(nd["v"], dtype=float),
            goal=np.array(nd["goal"], dtype=float),
            energy=float(nd["energy"]),
            age=int(nd["age"]),
            domain=nd["domain"],
            neighbors=list(nd["neighbors"]),
        )
        ms.nodes[n.id] = n
    ms.regions = {int(k):v for k,v in d["regions"].items()} if isinstance(list(d["regions"].keys())[0], str) else d["regions"]
    ms.step_n = d.get("step_n", 0)
    ms.history = d.get("history", {"phi":[], "energy":[], "entropy":[]})
    return ms

def consolidate(ms: Morphospace, sim_threshold: float=0.965, energy_floor: float=0.18):
    removed = set(); merged = 0; pruned = 0
    ids = list(ms.nodes.keys())
    for i in ids:
        if i not in ms.nodes: continue
        ni = ms.nodes[i]
        best, best_s = None, -1.0
        for j in ni.neighbors:
            if j not in ms.nodes: continue
            s = float(np.dot(ni.v, ms.nodes[j].v) / ((np.linalg.norm(ni.v)+1e-9)*(np.linalg.norm(ms.nodes[j].v)+1e-9)))
            if s > best_s:
                best_s, best = s, j
        if best is not None and best_s >= sim_threshold and best in ms.nodes:
            nb = ms.nodes[best]
            ni.v = (ni.v + nb.v) * 0.5
            ni.goal = (ni.goal + nb.goal) * 0.5
            ni.energy = max(ni.energy, nb.energy)
            for k in list(nb.neighbors):
                if k != i and k in ms.nodes and i not in ms.nodes[k].neighbors:
                    ms.nodes[k].neighbors.append(i)
                if k not in ni.neighbors: ni.neighbors.append(k)
            for k in list(ms.nodes.keys()):
                if best in ms.nodes.get(k, ni).neighbors:
                    try: ms.nodes[k].neighbors.remove(best)
                    except ValueError: pass
            del ms.nodes[best]; merged += 1
    for i in list(ms.nodes.keys()):
        n = ms.nodes[i]
        if n.energy < energy_floor and len(ms.nodes)>16:
            for k in list(ms.nodes.keys()):
                if i in ms.nodes[k].neighbors:
                    try: ms.nodes[k].neighbors.remove(i)
                    except ValueError: pass
            del ms.nodes[i]; pruned += 1
    return merged + pruned

def autosave(ms: Morphospace, folder: str="v4_state", every_steps: int=100):
    os.makedirs(folder, exist_ok=True)
    if ms.step_n % every_steps == 0 and ms.step_n>0:
        save_morphospace(ms, os.path.join(folder, f"morpho_step{ms.step_n}.json"))
