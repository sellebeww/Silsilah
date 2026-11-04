# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""PhylogenyRepository di memori, meniru match_variants dan apply_family_plan. Untuk evaluasi dan tes."""

from dataclasses import replace

from .placement import FamilyPlan, Match, MutationRow, NodeUpdate, VariantRecord
from .tree import Node, cosine


class InMemoryPhylogenyRepository:
    def __init__(self) -> None:
        self.records: dict[str, VariantRecord] = {}
        self.updates: dict[str, NodeUpdate] = {}
        self.merge_suggestions: dict[str, tuple[str, ...]] = {}
        self.mutations: dict[str, list[MutationRow]] = {}  # per keluarga
        self.roles: dict[str, str] = {}

    def add(self, node: Node, status: str = "pending") -> None:
        self.records[node.id] = VariantRecord(node, None, status)

    def get_variant(self, variant_id: str) -> VariantRecord | None:
        return self.records.get(variant_id)

    def match(self, embedding: tuple[float, ...], threshold: float, count: int) -> list[Match]:
        found = [
            Match(r.node.id, r.family_id, cosine(embedding, r.node.embedding))
            for r in self.records.values()
            if r.moderation_status == "approved" and r.node is not None and r.family_id is not None
        ]
        return sorted((m for m in found if m.similarity >= threshold), key=lambda m: -m.similarity)[:count]

    def family_members(self, family_id: str) -> list[Node]:
        return [
            r.node
            for r in self.records.values()
            if r.family_id == family_id and r.moderation_status == "approved" and r.node is not None
        ]

    def role_of(self, user_id: str) -> str | None:
        return self.roles.get(user_id)

    def apply(self, plan: FamilyPlan) -> None:
        record = self.records[plan.variant_id]
        self.records[plan.variant_id] = replace(
            record, family_id=plan.family_id, moderation_status="approved"
        )
        self.merge_suggestions[plan.variant_id] = plan.merge_suggestion
        for update in plan.nodes:
            self.updates[update.id] = update
        self.mutations[plan.family_id] = list(plan.mutations)
