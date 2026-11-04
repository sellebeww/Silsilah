# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Simpul uji dengan embedding kecil buatan agar kemiripan bisa dikendalikan persis."""

import math
from datetime import date

from silsilah.phylogeny.tree import Node


def unit(*xs: float) -> tuple[float, ...]:
    norm = math.sqrt(sum(x * x for x in xs))
    return tuple(x / norm for x in xs)


def node(
    id: str,
    first_seen: str,
    emb: tuple[float, ...],
    body: str = "teks",
    precision: str = "day",
    submitted: str = "2026-09-01",
    reports: int = 1,
) -> Node:
    return Node(
        id, date.fromisoformat(first_seen), precision, date.fromisoformat(submitted), reports, body, emb
    )
