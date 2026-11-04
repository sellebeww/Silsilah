# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Embedding teks tersamar. Model lokal, dimuat sekali per proses."""

from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedding:
    """sentence-transformers di CPU, vektor dinormalisasi L2 (cosine = dot product)."""

    def __init__(self, model_name: str, dim: int, prefix: str = "", batch_size: int = 32) -> None:
        from sentence_transformers import SentenceTransformer  # impor berat, hanya saat startup

        self._model = SentenceTransformer(model_name, device="cpu")
        actual = self._model.get_embedding_dimension()
        if actual != dim:
            raise ValueError(f"dimensi model {model_name} = {actual}, tetapi EMBEDDING_DIM = {dim}")
        self.dim = dim
        # Model keluarga e5 butuh "query: " (dilatih dengan prefiks); MiniLM default tanpa prefiks.
        self._prefix = prefix
        self._batch_size = batch_size

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(
            [self._prefix + t for t in texts],
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [[float(x) for x in v] for v in vectors]
