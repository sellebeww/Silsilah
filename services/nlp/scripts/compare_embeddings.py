# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
# Jalankan: uv run python scripts/compare_embeddings.py ../../supabase/seed.sql
"""Bandingkan model embedding pada seed sintetis: kemiripan intra-keluarga vs antar-keluarga."""

import itertools
import pathlib
import re
import statistics
import sys

from sentence_transformers import SentenceTransformer

seed = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
rows = re.findall(r"\('([abc])[a-f0-9-]+', '[f0-9a-f-]+', [^,]+,\s*'([^']+)'", seed)
# Varian tambahan sintetis: parafrase, campur bahasa daerah, dan pesan tak terkait.
extra = [
    (
        "a",
        "Kabar gembira!! Ada bantuan tunai sejuta rupiah per KK dari Lembaga Rekaan Sejahtera, buruan daftar di [TAUTAN], share ke grup lain ya",
    ),
    (
        "b",
        "Jare dokter, ngombe banyu uyah anget ping telu sedina iso nyegah flu Lamunan. Terusno nang keluarga.",
    ),
    ("c", "INFO!!! ATM Bank Contoh Makmur se-Kota Lamunan offline tgl 12 Mei, buruan tarik duit sblm telat"),
    ("x", "Jadwal ronda malam RT 05 minggu ini sudah dibagikan di grup warga."),
    ("y", "Resep rendang padang yang empuk dan bumbunya meresap sampai ke dalam."),
]
items = [(f, b) for f, b in rows] + extra
print(f"{len(items)} teks")

for name, prefix in [
    ("intfloat/multilingual-e5-small", "query: "),
    ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", ""),
]:
    model = SentenceTransformer(name, device="cpu")
    emb = model.encode([prefix + b for _, b in items], normalize_embeddings=True)
    intra: list[float] = []
    inter: list[float] = []
    for (i, (fi, _)), (j, (fj, _)) in itertools.combinations(enumerate(items), 2):
        sim = float(emb[i] @ emb[j])
        (intra if fi == fj and fi in "abc" else inter).append(sim)
    print(
        f"{name}: dim={emb.shape[1]} intra mean={statistics.mean(intra):.3f} min={min(intra):.3f} | "
        f"antar mean={statistics.mean(inter):.3f} max={max(inter):.3f} | margin(min intra - max antar)="
        f"{min(intra) - max(inter):.3f}"
    )
