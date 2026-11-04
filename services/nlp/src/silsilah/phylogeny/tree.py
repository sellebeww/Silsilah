# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Pohon turunan satu keluarga.

Pohon selalu dihitung ulang penuh dari anggota keluarga (tanggal + embedding), bukan ditambal per varian.
Hasilnya deterministik dan idempoten, dan varian lebih tua yang baru dilaporkan otomatis menjadi akar
(rebalance) tanpa logika khusus.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from .diff import lexical_similarity

Confidence = Literal["high", "low"]
TIE_MARGIN = 0.02


@dataclass(frozen=True)
class Node:
    id: str
    first_seen: date  # awal periode bila date_precision month/year
    date_precision: str
    submitted_at: date
    report_count: int
    body: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class Edge:
    parent_id: str | None
    similarity: float | None
    confidence: Confidence | None
    alt_parent_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tree:
    root_id: str
    edges: dict[str, Edge]


def order_key(node: Node) -> tuple[date, date, str]:
    """Urutan "lebih awal". Tanggal perkiraan dibandingkan dari awal periodenya (paling awal yang mungkin):
    itulah toleransi date_precision, sehingga varian "Februari 2026" boleh menjadi induk varian 14 Februari.
    Seri -> submitted_at paling awal -> id (agar deterministik)."""
    return (node.first_seen, node.submitted_at, node.id)


def cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    # embedding sudah dinormalisasi L2; dibulatkan agar perbandingan seri tidak goyah karena galat float
    return round(sum(x * y for x, y in zip(a, b, strict=True)), 6)


def build_tree(nodes: list[Node], t_edge: float, tie_margin: float = TIE_MARGIN) -> Tree:
    """Akar = varian tertua yang dilaporkan. Induk = varian lebih awal dengan kemiripan embedding tertinggi
    >= t_edge; bila tidak ada, cabang dari akar dengan confidence "low". Seri (< tie_margin) diputus dengan
    kemiripan token; bila tetap seri -> pilih yang lebih awal, simpan semua kandidat di alt_parent_ids."""
    ordered = sorted(nodes, key=order_key)
    root = ordered[0]
    edges = {root.id: Edge(None, None, None)}
    for i, node in enumerate(ordered[1:], start=1):
        earlier = ordered[:i]
        sims = [cosine(node.embedding, p.embedding) for p in earlier]
        best = max(sims)
        if best < t_edge:
            edges[node.id] = Edge(root.id, sims[0], "low")
            continue
        tied = [k for k, s in enumerate(sims) if s >= t_edge and best - s < tie_margin]
        if len(tied) > 1:
            # Embedding nyaris buta terhadap perubahan angka/nama, sehingga induk dan kakek sering seri;
            # kemiripan token memutus seri itu. Yang masih seri setelahnya = arah turunan tidak pasti.
            lex = {k: lexical_similarity(earlier[k].body, node.body) for k in tied}
            top = max(lex.values())
            tied = [k for k in tied if top - lex[k] < tie_margin]
        parent = earlier[tied[0]]  # earlier sudah terurut: indeks terkecil = paling awal
        alt = tuple(earlier[k].id for k in tied) if len(tied) > 1 else ()
        edges[node.id] = Edge(parent.id, sims[tied[0]], "high", alt)
    return Tree(root.id, edges)
