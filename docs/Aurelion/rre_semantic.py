
from __future__ import annotations
import os, re, math, json, random, hashlib
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Iterable
import numpy as np

def word_vec(word: str, dim: int = 64) -> np.ndarray:
    h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % (2**31 - 1)
    rng = np.random.default_rng(h)
    v = rng.standard_normal(dim)
    v = v / (np.linalg.norm(v) + 1e-9)
    return v

WORD_RE = re.compile(r"[A-Za-z']+")

def tokenize(text: str):
    return [w.lower() for w in WORD_RE.findall(text)]

def tokens_to_matrix(tokens: List[str], dim: int = 64):
    if not tokens: 
        return np.zeros((0, dim))
    return np.stack([word_vec(t, dim) for t in tokens], axis=0)

class SemanticStream:
    def __init__(self, tokens: List[str], dim: int = 64, window: int = 16, stride: int = 4):
        self.tokens = tokens
        self.dim = dim
        self.window = window
        self.stride = stride
        self.idx = 0

    @classmethod
    def from_file(cls, path: str, **kw):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        toks = tokenize(text)
        return cls(tokens=toks, **kw)

    def step(self) -> np.ndarray:
        if not self.tokens:
            return np.zeros((self.window, self.dim))
        if self.idx + self.window > len(self.tokens):
            self.idx = 0
        window_tokens = self.tokens[self.idx:self.idx+self.window]
        self.idx += self.stride
        return tokens_to_matrix(window_tokens, self.dim)

def coherence_phi(W: np.ndarray) -> float:
    if W.shape[0] < 2: return 0.0
    X = W / (np.linalg.norm(W, axis=1, keepdims=True) + 1e-9)
    S = X @ X.T
    n = X.shape[0]
    num = np.sum(S) - np.trace(S)
    den = n*(n-1)
    m = max(0.0, float(num/den))
    return min(1.0, m)

def entropy_H(W: np.ndarray, bins: int = 16) -> float:
    if W.shape[0] < 2: return 0.0
    X = W - np.mean(W, axis=0, keepdims=True)
    try:
        u, s, vh = np.linalg.svd(X, full_matrices=False)
        comp = X @ vh[0]
    except Exception:
        comp = X[:,0]
    hist, edges = np.histogram(comp, bins=bins)
    p = hist.astype(np.float64); p = p / (p.sum() + 1e-9)
    H = -(p * (np.log(p + 1e-12))).sum()
    Hmax = math.log(bins)
    return float(min(1.0, max(0.0, H / (Hmax + 1e-12))))

class Resonator:
    def __init__(self, dim: int = 64, window: int = 16):
        self.dim = dim; self.window = window
        self.hist_phi = []; self.hist_H = []
    def observe(self, W):
        phi = coherence_phi(W); H = entropy_H(W)
        self.hist_phi.append(phi); self.hist_H.append(H)
        self.hist_phi = self.hist_phi[-512:]; self.hist_H = self.hist_H[-512:]
        return phi, H
