
Aurelion v3.6 — Persistent Resonance + Mosaic Growth

WHAT'S NEW
- Persistent prototypes: high-φ meta-mosaics are stored and reused on future runs.
- Warm-start clustering: prior prototypes attract semantically similar sentences.
- Mosaic growth: prototypes merge/expand via token overlap and re-embedding.
- Autonomic Drift (optional): background rehearsal to consolidate prototypes.

FILES
- mosaic_memory.py      — persistent prototype store (mosaic_memory.jsonl)
- semantic_mosaic.py    — now supports warm-start via seed centroids
- aurelion_core_v36.py  — batch runner with persistence
- aurelion_drift.py     — optional background rehearsal loop
- embeddings.py         — semantic embeddings w/ TF-IDF fallback

INSTALL
python -m pip install --upgrade pip
python -m pip install sentence-transformers scikit-learn numpy pandas matplotlib

RUN
python aurelion_core_v36.py --batch "C:\Users\joeta\OneDrive\Desktop\Aurelion\corpora"

OPTIONAL REHEARSAL
python aurelion_drift.py
