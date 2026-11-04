# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""PhylogenyRepository di atas PostgREST. Penulisan atomik lewat RPC apply_family_plan."""

import json
from dataclasses import asdict
from datetime import date
from typing import Any

import httpx

from silsilah.postgrest import PostgrestClient

from .placement import FamilyPlan, Match, VariantRecord
from .tree import Node

_COLUMNS = (
    "id,family_id,moderation_status,body_anonymized,embedding,"
    "first_seen_reported_at,date_precision,submitted_at,report_count"
)


def _node(row: dict[str, Any]) -> Node | None:
    if row["embedding"] is None:
        return None
    # PostgREST mengirim vector sebagai teks "[0.1,0.2,...]"
    embedding = row["embedding"] if isinstance(row["embedding"], list) else json.loads(row["embedding"])
    return Node(
        row["id"],
        date.fromisoformat(row["first_seen_reported_at"]),
        row["date_precision"],
        date.fromisoformat(row["submitted_at"]),
        row["report_count"],
        row["body_anonymized"],
        tuple(float(x) for x in embedding),
    )


class SupabasePhylogenyRepository:
    def __init__(self, supabase_url: str, service_role_key: str, client: httpx.Client | None = None) -> None:
        self._db = PostgrestClient(supabase_url, service_role_key, client)

    def get_variant(self, variant_id: str) -> VariantRecord | None:
        rows = self._db.select("variants", {"select": _COLUMNS, "id": f"eq.{variant_id}"})
        if not rows:
            return None
        return VariantRecord(_node(rows[0]), rows[0]["family_id"], rows[0]["moderation_status"])

    def match(self, embedding: tuple[float, ...], threshold: float, count: int) -> list[Match]:
        rows = self._db.rpc(
            "match_variants",
            {"query_embedding": list(embedding), "match_threshold": threshold, "match_count": count},
        )
        return [Match(r["id"], r["family_id"], float(r["similarity"])) for r in rows]

    def family_members(self, family_id: str) -> list[Node]:
        rows = self._db.select(
            "variants",
            {"select": _COLUMNS, "family_id": f"eq.{family_id}", "moderation_status": "eq.approved"},
        )
        return [n for r in rows if (n := _node(r)) is not None]

    def role_of(self, user_id: str) -> str | None:
        rows = self._db.select("contributors", {"select": "role", "id": f"eq.{user_id}"})
        return str(rows[0]["role"]) if rows else None

    def apply(self, plan: FamilyPlan) -> None:
        payload = asdict(plan)
        payload.pop("oldest")  # hanya untuk respons API
        self._db.rpc("apply_family_plan", {"p_plan": payload})

    def close(self) -> None:
        self._db.close()
