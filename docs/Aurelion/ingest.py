# ingest.py — read local files or (guarded) URLs and chunk for learning
import os, csv, re
from typing import List
from guard import SafeGuard

def _read_txt(path: str, guard: SafeGuard) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        return guard.scrub_pii(data)
    except Exception as e:
        return f"(read error: {e})"

def _read_csv(path: str, guard: SafeGuard, limit=20000) -> str:
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for i, row in enumerate(csv.reader(f)):
                out.append(" ".join(row))
                if i >= limit: break
        return guard.scrub_pii("\n".join(out))
    except Exception as e:
        return f"(csv read error: {e})"

def load_local(path: str, guard: SafeGuard) -> str:
    if not guard.allowed_path(path):
        return "(path not allowed)"
    if path.lower().endswith(".txt"):
        return _read_txt(path, guard)
    if path.lower().endswith(".csv"):
        return _read_csv(path, guard)
    return "(unsupported file type)"

def chunk_text(text: str, words=400) -> List[str]:
    toks = text.split()
    return [" ".join(toks[i:i+words]) for i in range(0, len(toks), words)]

def summarize_chunks(chunks: List[str], max_chunks=6) -> str:
    # very small heuristic summary (non-LLM): first sentences from first few chunks
    parts = []
    for ch in chunks[:max_chunks]:
        s = ch.strip().split(". ")
        parts.append(s[0].strip())
    return " | ".join(parts[:8])
