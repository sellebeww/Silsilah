# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Pengenal nama berbasis model NER Indonesia (transformers, lokal)."""

import os
from functools import cache

DEFAULT_MODEL = "cahya/bert-base-indonesian-NER"


class TransformersNameRecognizer:
    """Mengembalikan rentang (start, end) entitas PER dengan skor >= threshold."""

    def __init__(self, model: str = DEFAULT_MODEL, threshold: float = 0.5) -> None:
        from transformers import pipeline  # impor berat, ditunda sampai benar-benar dibutuhkan

        # CPU eksplisit: hasil deterministik dan tidak bergantung pada GPU/MPS
        self._pipe = pipeline(
            "token-classification", model=model, aggregation_strategy="simple", device="cpu"
        )
        self._threshold = threshold

    def __call__(self, text: str) -> list[tuple[int, int]]:
        if not text.strip():
            return []
        return [
            (int(e["start"]), int(e["end"]))
            for e in self._pipe(text)
            if e["entity_group"] == "PER" and float(e["score"]) >= self._threshold
        ]


@cache
def default_recognizer() -> TransformersNameRecognizer:
    return TransformersNameRecognizer(
        os.environ.get("NER_MODEL", DEFAULT_MODEL), float(os.environ.get("NER_THRESHOLD", "0.5"))
    )
