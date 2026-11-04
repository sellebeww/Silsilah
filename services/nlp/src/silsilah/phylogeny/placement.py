# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Penempatan varian yang disetujui kurator: keluarga, induk, varian tertua yang dilaporkan, mutasi."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .diff import Category, diff
from .tree import Node, build_tree, cosine


@dataclass(frozen=True)
class Match:
    id: str
    family_id: str
    similarity: float


@dataclass(frozen=True)
class VariantRecord:
    node: Node | None  # None bila embedding belum ada
    family_id: str | None
    moderation_status: str


@dataclass(frozen=True)
class NodeUpdate:
    id: str
    parent_id: str | None
    edge_similarity: float | None
    edge_confidence: str | None
    alt_parent_ids: tuple[str, ...]
    is_oldest: bool
    mutation_summary: str | None


@dataclass(frozen=True)
class MutationRow:
    variant_id: str
    parent_variant_id: str
    category: Category
    before_text: str | None
    after_text: str | None
    position_hint: int


@dataclass(frozen=True)
class FamilyPlan:
    family_id: str
    variant_id: str
    new_family: bool
    merge_suggestion: tuple[str, ...]  # keluarga lain yang juga mirip; digabung hanya oleh kurator
    oldest: Node  # tertua yang dilaporkan; date_precision dan report_count = ketidakpastiannya
    nodes: list[NodeUpdate]
    mutations: list[MutationRow]


class PlacementError(RuntimeError):
    """Varian tidak bisa ditempatkan (tidak ada, ditolak, atau belum punya embedding)."""


class PhylogenyRepository(Protocol):
    def get_variant(self, variant_id: str) -> VariantRecord | None: ...

    def match(self, embedding: tuple[float, ...], threshold: float, count: int) -> list[Match]: ...

    def family_members(self, family_id: str) -> list[Node]: ...

    def apply(self, plan: FamilyPlan) -> None: ...

    def role_of(self, user_id: str) -> str | None: ...


def centroid(nodes: list[Node]) -> tuple[float, ...]:
    total = [sum(xs) for xs in zip(*(n.embedding for n in nodes), strict=True)]
    norm = sum(x * x for x in total) ** 0.5 or 1.0
    return tuple(x / norm for x in total)


def choose_family(scored: list[tuple[float, str]]) -> tuple[str | None, tuple[str, ...]]:
    """Keluarga dengan kemiripan centroid tertinggi; keluarga lain yang juga lolos menjadi saran gabung."""
    if not scored:
        return None, ()
    top = max(scored)[1]
    return top, tuple(sorted({fid for _, fid in scored} - {top}))


def plan_family(
    family_id: str,
    variant_id: str,
    new_family: bool,
    merge_suggestion: tuple[str, ...],
    members: list[Node],
    t_edge: float,
) -> FamilyPlan:
    tree = build_tree(members, t_edge)
    by_id = {n.id: n for n in members}
    nodes: list[NodeUpdate] = []
    mutations: list[MutationRow] = []
    for node in sorted(members, key=lambda n: n.id):
        edge = tree.edges[node.id]
        summary = None
        if edge.parent_id is not None:
            result = diff(by_id[edge.parent_id].body, node.body)
            summary = result.summary
            mutations += [
                MutationRow(node.id, edge.parent_id, m.category, m.before_text, m.after_text, m.position_hint)
                for m in result.mutations
            ]
        nodes.append(
            NodeUpdate(
                node.id,
                edge.parent_id,
                edge.similarity,
                edge.confidence,
                edge.alt_parent_ids,
                node.id == tree.root_id,
                summary,
            )
        )
    return FamilyPlan(
        family_id, variant_id, new_family, merge_suggestion, by_id[tree.root_id], nodes, mutations
    )


class PlacementService:
    def __init__(
        self,
        repo: PhylogenyRepository,
        t_family: float,
        t_edge: float,
        match_count: int = 20,
        new_id: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self.repo = repo
        self._t_family = t_family
        self._t_edge = t_edge
        self._match_count = match_count
        self._new_id = new_id

    def place(self, variant_id: str) -> FamilyPlan:
        """Setujui dan tempatkan. Aman diulang: varian yang sudah punya keluarga tetap di keluarganya."""
        record = self.repo.get_variant(variant_id)
        if record is None:
            raise PlacementError("varian tidak ditemukan")
        if record.moderation_status == "rejected":
            raise PlacementError("varian sudah ditolak")
        if record.node is None:
            raise PlacementError("varian belum punya embedding")
        node = record.node

        # match_variants (satu anggota mirip) hanya menyaring kandidat. Keputusan memakai centroid keluarga:
        # single-linkage merantai keluarga lewat varian bergaya chat/bahasa daerah yang mirip karena gayanya.
        candidates = {
            m.family_id
            for m in self.repo.match(node.embedding, self._t_family, self._match_count)
            if m.id != variant_id
        } | ({record.family_id} if record.family_id else set())
        members_of: dict[str, list[Node]] = {}
        scored: list[tuple[float, str]] = []
        for fid in sorted(candidates):
            members_of[fid] = [n for n in self.repo.family_members(fid) if n.id != variant_id]
            if members_of[fid]:
                sim = cosine(node.embedding, centroid(members_of[fid]))
                if sim >= self._t_family:
                    scored.append((sim, fid))

        if record.family_id is not None:  # sudah ditempatkan: tetap di keluarganya (idempoten)
            family_id, new_family = record.family_id, False
            merge = tuple(sorted({fid for _, fid in scored} - {family_id}))
        else:
            chosen, merge = choose_family(scored)
            new_family = chosen is None
            family_id = chosen or self._new_id()

        members = members_of.get(family_id, [])
        plan = plan_family(family_id, variant_id, new_family, merge, [*members, node], self._t_edge)
        self.repo.apply(plan)
        return plan
