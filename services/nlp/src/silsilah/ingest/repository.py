# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Akses tabel variants lewat fungsi RPC PostgREST (service role). Lihat migrasi 20261104000400_ingest.sql."""

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import httpx


@dataclass(frozen=True)
class StoredVariant:
    id: str
    report_count: int
    is_duplicate: bool


class RepositoryError(RuntimeError):
    """Penyimpanan gagal. Pesan tanpa isi respons: error Postgres bisa menyertakan baris data."""


class VariantRepository(Protocol):
    def register_duplicate(
        self, body_hash: str, first_seen: date, precision: str
    ) -> StoredVariant | None: ...

    def insert_pending(
        self, body: str, body_hash: str, embedding: list[float], first_seen: date, precision: str
    ) -> StoredVariant: ...


class SupabaseVariantRepository:
    def __init__(self, supabase_url: str, service_role_key: str, client: httpx.Client | None = None) -> None:
        headers = {"apikey": service_role_key}
        # Kunci lama berupa JWT juga dikirim sebagai Bearer; kunci baru (sb_secret_...) cukup lewat apikey.
        if service_role_key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {service_role_key}"
        self._client = client or httpx.Client(timeout=10.0)
        self._base = f"{supabase_url}/rest/v1/rpc"
        self._headers = headers

    def _rpc(self, fn: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            resp = self._client.post(f"{self._base}/{fn}", json=params, headers=self._headers)
        except httpx.HTTPError as exc:
            raise RepositoryError(f"rpc {fn} gagal: {type(exc).__name__}") from None
        if resp.is_error:
            raise RepositoryError(f"rpc {fn} gagal: HTTP {resp.status_code}")
        rows: list[dict[str, Any]] = resp.json()
        return rows

    def register_duplicate(self, body_hash: str, first_seen: date, precision: str) -> StoredVariant | None:
        rows = self._rpc(
            "register_duplicate_report",
            {"p_body_hash": body_hash, "p_first_seen": first_seen.isoformat(), "p_date_precision": precision},
        )
        return StoredVariant(rows[0]["id"], rows[0]["report_count"], True) if rows else None

    def insert_pending(
        self, body: str, body_hash: str, embedding: list[float], first_seen: date, precision: str
    ) -> StoredVariant:
        rows = self._rpc(
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
        self._client.close()
