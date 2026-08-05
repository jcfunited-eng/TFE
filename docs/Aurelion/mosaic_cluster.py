# -*- coding: utf-8 -*-
"""
mosaic_cluster.py — Aurelion Mosaic (fixed naming + tuned, NLTK lemmatizer, concise reports)
"""

from __future__ import annotations
import os, re, json, math, argparse, datetime, string
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity

# --- NLTK setup ---------------------------------------------------------------
try:
    import nltk
    from nltk.stem import WordNetLemmatizer
    _lemm = WordNetLemmatizer()
    _nltk_ok = True
except Exception:
    _lemm = None
    _nltk_ok = False

def _ensure_nltk():
    global _lemm, _nltk_ok
    if _nltk_ok and _lemm is not None:
        return
    try:
        import nltk
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)
        from nltk.stem import WordNetLemmatizer
        _lemm = WordNetLemmatizer()
        _nltk_ok = True
    except Exception:
        _nltk_ok = False
        _lemm = None

# --- Basic text cleanup -------------------------------------------------------
_STOP = set("""
a an the and or if of in on at to for from by with as is are was were be being been
it its itself this that those these there here when where which who whom whose while
he she they them his her their you your yours i me my we us our ours not no nor
do does did doing done can could will would shall should may might must also
about above below into over under again further then once only same very
than too more most some such each other both few many much so
""".split())

def _clean_text(s: str) -> str:
    s = s.replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _tokens(s: str) -> List[str]:
    s = s.lower()
    s = re.sub(r"[0-9]+", " ", s)
    toks = re.findall(r"[a-z][a-z\-']{1,}", s)
    out = []
    for t in toks:
        if t in _STOP: continue
        t = t.translate(str.maketrans("", "", string.punctuation))
        if len(t) < 2: continue
        if _lemm is not None:
            try: t = _lemm.lemmatize(t)
            except Exception: pass
        out.append(t)
    return out

def load_corpus(path: str) -> str:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")
    return _clean_text(text)

def sliding_windows(toks: List[str], win: int, steps: int) -> List[List[str]]:
    n = max(1, min(steps, max(1, len(toks)//max(1, win//2))))
    starts = np.linspace(0, max(0, len(toks)-win), num=n, dtype=int)
    return [toks[s:s+win] for s in starts]

def tfidf_matrix(windows: List[List[str]], max_features: int=4000, ngram: Tuple[int,int]=(1,2)):
    docs = [" ".join(w) for w in windows]
    vec = TfidfVectorizer(max_features=max_features, ngram_range=ngram, analyzer="word")
    X = vec.fit_transform(docs)
    terms = np.array(vec.get_feature_names_out())
    return X.toarray(), terms

def select_terms(X: np.ndarray, terms: np.ndarray, top_k: int=600) -> Tuple[np.ndarray, np.ndarray]:
    var = X.var(axis=0)
    idx = np.argsort(var)[::-1][:min(top_k, X.shape[1])]
    return X[:, idx], terms[idx]

def cosine_phi(vectors: np.ndarray) -> float:
    if vectors.shape[1] < 2: return 0.0
    A = normalize(vectors, norm='l2', axis=0)
    sim = cosine_similarity(A.T)
    iu = np.triu_indices(sim.shape[0], k=1)
    return float(sim[iu].mean()) if iu[0].size > 0 else 0.0

def cluster_activation(vectors: np.ndarray) -> np.ndarray:
    return vectors.sum(axis=1)

def entropy01(x: np.ndarray) -> float:
    x = np.maximum(0.0, x)
    s = x.sum()
    if s <= 1e-12: return 1.0
    p = x / s
    p = p[p > 0]
    H = -(p * np.log(p + 1e-12)).sum()
    Hmax = math.log(len(p) + 1e-12)
    return float(H / (Hmax + 1e-12))

def norm01(v: np.ndarray) -> np.ndarray:
    lo, hi = np.nanmin(v), np.nanmax(v)
    if hi - lo < 1e-12: return np.zeros_like(v)
    return (v - lo) / (hi - lo)

def agglomerate(term_vectors: np.ndarray, terms: np.ndarray, k: int, min_cluster: int) -> List[List[int]]:
    V = normalize(term_vectors, norm='l2', axis=0)
    clusters = [[i] for i in range(V.shape[1])]
    term_cos = cosine_similarity(V.T)
    while len(clusters) > max(k, 1):
        best_pair, best_sim = None, -1.0
        for i in range(len(clusters)):
            for j in range(i+1, len(clusters)):
                ii, jj = clusters[i], clusters[j]
                sim = term_cos[np.ix_(ii, jj)].mean()
                if sim > best_sim:
                    best_sim, best_pair = sim, (i, j)
        if not best_pair: break
        i, j = best_pair
        merged = clusters[i] + clusters[j]
        clusters = [c for idx, c in enumerate(clusters) if idx not in (i, j)]
        clusters.append(merged)
    return [c for c in clusters if len(c) >= min_cluster]

# --- Main --------------------------------------------------------------------
def discover_mosaics(text: str, steps: int=400, window: int=256,
                     top_terms: int=600, k: int=6, min_cluster: int=3) -> Dict:
    _ensure_nltk()
    toks = _tokens(text)
    if len(toks) < 64:
        return {"status":"too_short","message":f"Corpus too short ({len(toks)} tokens).","clusters":[]}
    wins = sliding_windows(toks, win=window, steps=steps)
    X, terms = tfidf_matrix(wins)
    Xs, sel_terms = select_terms(X, terms, top_k=top_terms)
    M = Xs
    if np.var(M, axis=0).mean() < 1e-5 and top_terms < 1500:
        Xs, sel_terms = select_terms(X, terms, top_k=1200)
        M = Xs
    clusters_idx = agglomerate(M, sel_terms, k=k, min_cluster=min_cluster)
    results = []
    for ids in clusters_idx:
        Vc = M[:, ids]
        phi = max(0.0, min(1.0, cosine_phi(Vc)))
        act = cluster_activation(Vc)
        e_raw = float(np.linalg.norm(act))
        H = max(0.0, min(1.0, entropy01(np.abs(act))))
        toks_in_cluster = [sel_terms[i] for i in ids]
        results.append({"phi":phi,"H":H,"energy_raw":e_raw,"tokens":toks_in_cluster})
    if not results:
        return {"status":"no_clusters","message":"No clusters met min size.","clusters":[]}
    energies = np.array([r["energy_raw"] for r in results])
    e_norm = norm01(energies)
    for r,en in zip(results,e_norm):
        r["energy"]=float(en)
        r["score"]=float(r["phi"]*(1.0-r["H"])*(0.5+0.5*en))
        del r["energy_raw"]
    results.sort(key=lambda z:z["score"],reverse=True)
    return {"status":"ok","steps":steps,"window":window,"k":k,
            "min_cluster":min_cluster,
            "recent_phi_mean":float(np.mean([r["phi"] for r in results])),
            "recent_H_mean":float(np.mean([r["H"] for r in results])),
            "clusters":results}

def write_outputs(payload: Dict, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    jpath = outdir / f"mosaic_{ts}.json"
    rpath = outdir / f"mosaic_{ts}_report.txt"
    with jpath.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    lines = []
    lines.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Mosaic report")
    lines.append(f"Status: {payload.get('status')}")
    lines.append(f"Recent φ mean: {payload.get('recent_phi_mean',0):.3f}  "
                 f"Recent H mean: {payload.get('recent_H_mean',0):.3f}")
    lines.append(f"{'rank':>4}  {'score':>6}  {'φ':>4}  {'H':>4}  {'energy':>6}  tokens")
    lines.append("-"*72)
    for i,c in enumerate(payload.get("clusters",[]),1):
        toks=", ".join(c["tokens"][:10])
        lines.append(f"{i:>4}  {c['score']:.3f}  {c['phi']:.3f}  {c['H']:.3f}  {c['energy']:.3f}  {toks}")
    with rpath.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return jpath, rpath

def main():
    ap = argparse.ArgumentParser(description="Aurelion Mosaic Cluster (fixed + concise)")
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--window", type=int, default=256)
    ap.add_argument("--top_terms", type=int, default=600)
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--min_cluster", type=int, default=3)
    ap.add_argument("--outdir", default="mosaic_logs")
    args = ap.parse_args()
    text = load_corpus(args.corpus)
    payload = discover_mosaics(text, steps=args.steps, window=args.window,
                               top_terms=args.top_terms, k=args.k, min_cluster=args.min_cluster)
    jpath, rpath = write_outputs(payload, Path(args.outdir))
    print(f"Mosaic saved: {jpath}")
    print(f"Report saved: {rpath}")

if __name__ == "__main__":
    main()
