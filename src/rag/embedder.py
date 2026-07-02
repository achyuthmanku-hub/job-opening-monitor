"""Local sentence embeddings (384-dim, no API cost)."""

from functools import lru_cache
from typing import Optional

import numpy as np

EMBEDDING_DIM = 384
MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _load_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [vector.tolist() for vector in vectors]


def embedding_to_json(vector: list[float]) -> str:
    import json

    return json.dumps(vector)


def embedding_from_json(raw: str) -> Optional[np.ndarray]:
    import json

    if not raw:
        return None
    try:
        data = json.loads(raw)
        if not data:
            return None
        return np.array(data, dtype=np.float32)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
