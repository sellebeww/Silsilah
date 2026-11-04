# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Akses tabel variants lewat fungsi RPC PostgREST (service role). Lihat migrasi 20261104000400_ingest.sql."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import httpx

from silsilah.postgrest import PostgrestClient, RepositoryError

__all__ = ["RepositoryError", "StoredVariant", "SupabaseVariantRepository", "VariantRepository"]


@dataclass(frozen=True)
class StoredVariant:
    id: str
    report_count: int
    is_duplicate: bool


class VariantRepository(Protocol):
    def register_duplicate(
        self, body_hash: str, first_seen: date, precision: str
    ) -> StoredVariant | None: ...

    def insert_pending(
        self, body: str, body_hash: str, embedding: list[float], first_seen: date, precision: str
    ) -> StoredVariant: ...


class SupabaseVariantRepository:
    def __init__(self, supabase_url: str, service_role_key: str, client: httpx.Client | None = None) -> None:
        self._db = PostgrestClient(supabase_url, service_role_key, client)

    def register_duplicate(self, body_hash: str, first_seen: date, precision: str) -> StoredVariant | None:
        rows = self._db.rpc(
            "register_duplicate_report",
            {"p_body_hash": body_hash, "p_first_seen": first_seen.isoformat(), "p_date_precision": precision},
        )
        return StoredVariant(rows[0]["id"], rows[0]["report_count"], True) if rows else None

    def insert_pending(
        self, body: str, body_hash: str, embedding: list[float], first_seen: date, precision: str
    ) -> StoredVariant:
        rows = self._db.rpc(
            "insert_pending_variant",
            {
                "p_body": body,
                "p_body_hash": body_hash,
                "p_embedding": embedding,
                "p_language_hint": None,
                "p_first_seen": first_seen.isoformat(),
                "p_date_precision": precision,
            },
        )
        if not rows:
            raise RepositoryError("rpc insert_pending_variant tidak mengembalikan baris")
        return StoredVariant(rows[0]["id"], rows[0]["report_count"], rows[0]["is_duplicate"])

    def close(self) -> None:
        self._db.close()
