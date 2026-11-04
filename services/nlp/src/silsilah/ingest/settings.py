# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Konfigurasi dari env. Variabel wajib yang hilang membuat layanan gagal start (lebih baik daripada diam)."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str | None = None
    # Dipilih lewat scripts/compare_embeddings.py: memisahkan keluarga jauh lebih jelas daripada e5-small.
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384
    embedding_prefix: str = ""
    ocr_langs: str = "ind+eng"
    cors_origins: tuple[str, ...] = field(default=("http://localhost:3000",))
    rate_limit_per_hour: int = 20
    submit_timeout_s: float = 30.0
    # Dari sapuan grid `make eval` (docs/EVAL.md), bukan tebakan.
    placement_sim_family: float = 0.60
    placement_sim_edge: float = 0.85

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        return cls(
            supabase_url=env["SUPABASE_URL"].rstrip("/"),
            supabase_service_role_key=env["SUPABASE_SERVICE_ROLE_KEY"],
            supabase_jwt_secret=env.get("SUPABASE_JWT_SECRET") or None,
            embedding_model=env.get("EMBEDDING_MODEL", cls.embedding_model),
            embedding_dim=int(env.get("EMBEDDING_DIM", cls.embedding_dim)),
            embedding_prefix=env.get("EMBEDDING_PREFIX", cls.embedding_prefix),
            ocr_langs=env.get("OCR_LANGS", cls.ocr_langs),
            cors_origins=tuple(
                o.strip() for o in env.get("CORS_ORIGINS", "http://localhost:3000").split(",")
            ),
            rate_limit_per_hour=int(env.get("RATE_LIMIT_PER_HOUR", cls.rate_limit_per_hour)),
            submit_timeout_s=float(env.get("SUBMIT_TIMEOUT_S", cls.submit_timeout_s)),
            placement_sim_family=float(env.get("PLACEMENT_SIM_FAMILY", cls.placement_sim_family)),
            placement_sim_edge=float(env.get("PLACEMENT_SIM_EDGE", cls.placement_sim_edge)),
        )
