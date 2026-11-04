# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Klien PostgREST (Supabase) dengan service role. Pesan error tidak pernah memuat isi respons."""

from typing import Any

import httpx


class RepositoryError(RuntimeError):
    """Penyimpanan gagal. Pesan tanpa isi respons: error Postgres bisa menyertakan baris data."""


class PostgrestClient:
    def __init__(self, supabase_url: str, service_role_key: str, client: httpx.Client | None = None) -> None:
        headers = {"apikey": service_role_key}
        # Kunci lama berupa JWT juga dikirim sebagai Bearer; kunci baru (sb_secret_...) cukup lewat apikey.
        if service_role_key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {service_role_key}"
        self._client = client or httpx.Client(timeout=10.0)
        self._base = f"{supabase_url}/rest/v1"
        self._headers = headers

    def _send(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            resp = self._client.request(method, f"{self._base}/{path}", headers=self._headers, **kwargs)
        except httpx.HTTPError as exc:
            raise RepositoryError(f"{path} gagal: {type(exc).__name__}") from None
        if resp.is_error:
            raise RepositoryError(f"{path} gagal: HTTP {resp.status_code}")
        return resp.json() if resp.content else None

    def rpc(self, fn: str, params: dict[str, Any]) -> Any:
        return self._send("POST", f"rpc/{fn}", json=params)

    def select(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = self._send("GET", table, params=params)
        return rows

    def close(self) -> None:
        self._client.close()
