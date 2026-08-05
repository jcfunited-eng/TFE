
from __future__ import annotations
import warnings

class Embedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.backend = "tfidf"
        self.model = None
        self.vectorizer = None
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.backend = "st"
        except Exception as e:
            warnings.warn(
                "sentence-transformers not available, falling back to TF-IDF "
                f"(reason: {type(e).__name__}: {e}). To enable semantic mode, run:\n"
                "  python -m pip install sentence-transformers\n"
            )
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(max_features=4096, ngram_range=(1,2))

    def encode(self, texts):
        if self.backend == "st":
            return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        import numpy as np
        X = self.vectorizer.fit_transform(texts)
        X = X.toarray()
        norms = (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
        return X / norms
