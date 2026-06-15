"""TF-IDF semantic search over codebase index."""
from __future__ import annotations

import json
from pathlib import Path


def search_root() -> Path:
    """Return the server-controlled project root used for search indexes."""
    return Path.cwd().resolve()


def _index_path() -> Path:
    return search_root() / ".anote" / "index" / "chunks.json"


def has_index() -> bool:
    return _index_path().exists()


def search_index(query: str, top_k: int = 10) -> list[dict]:
    index_file = _index_path()
    if not index_file.exists():
        return []
    try:
        chunks = json.loads(index_file.read_text())
    except Exception:
        return []
    if not chunks:
        return []
    try:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        corpus = [c.get("content", "") for c in chunks]
        vectorizer = TfidfVectorizer(max_features=3000, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(corpus)
        query_vec = vectorizer.transform([query])
        scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < 0.01:
                break
            chunk = chunks[int(idx)]
            results.append({
                "file": chunk.get("file", ""),
                "startLine": chunk.get("startLine", 0),
                "endLine": chunk.get("endLine", 0),
                "preview": chunk.get("content", "")[:200],
                "score": round(score, 4),
            })
        return results
    except Exception:
        return []
