# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Alur ingest. Teks mentah hanya hidup di memori fungsi ini; yang keluar hanya teks tersamar."""

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from silsilah.anonymizer import EntityCount, anonymize, assert_no_pii, normalize_for_hash
from silsilah.anonymizer.names import NameRecognizer

from .embedding import EmbeddingProvider
from .repository import VariantRepository

DatePrecision = Literal["day", "month", "year"]
MIN_CHARS, MAX_CHARS = 20, 5000
# Batas kolom variants.body_anonymized; token anonim bisa membuat teks sedikit lebih panjang dari input.
MAX_STORED_CHARS = 10_000
# Tanggal "hari ini" memakai WIB, sama dengan submitted_at di fungsi SQL.
WIB = timezone(timedelta(hours=7))


class SubmissionRejectedError(ValueError):
    """Kiriman ditolak karena isinya; pesan aman ditampilkan ke pengguna."""


@dataclass(frozen=True)
class SubmitResult:
    variant_id: str
    is_duplicate: bool
    report_count: int
    body_anonymized: str
    entities_found: list[EntityCount]


def today_wib() -> date:
    return datetime.now(WIB).date()


def start_of_period(d: date, precision: DatePrecision) -> date:
    """Tanggal perkiraan disimpan di awal periodenya (lihat constraint variants_date_matches_precision)."""
    if precision == "month":
        return d.replace(day=1)
    if precision == "year":
        return d.replace(month=1, day=1)
    return d


def check_text_length(text: str) -> None:
    n = len(text.strip())
    if not MIN_CHARS <= n <= MAX_CHARS:
        raise SubmissionRejectedError(f"Panjang teks harus {MIN_CHARS}-{MAX_CHARS} karakter (sekarang {n})")


class IngestPipeline:
    def __init__(
        self, repo: VariantRepository, embedder: EmbeddingProvider, ner: NameRecognizer | None = None
    ):
        self._repo = repo
        self._embedder = embedder
        self._ner = ner

    def submit(self, text: str, first_seen: date, precision: DatePrecision) -> SubmitResult:
        check_text_length(text)
        anon = anonymize(text, ner=self._ner)
        del text  # sejak titik ini hanya teks tersamar yang dipakai
        assert_no_pii(anon.text)
        if len(anon.text) > MAX_STORED_CHARS:
            raise SubmissionRejectedError("Teks terlalu panjang setelah dianonimkan")
        body_hash = hashlib.sha256(normalize_for_hash(anon.text).encode()).hexdigest()
        first_seen = start_of_period(first_seen, precision)

        stored = self._repo.register_duplicate(body_hash, first_seen, precision)
        if stored is None:
            [embedding] = self._embedder.embed([anon.text])
            stored = self._repo.insert_pending(anon.text, body_hash, embedding, first_seen, precision)
        return SubmitResult(
            stored.id, stored.is_duplicate, stored.report_count, anon.text, anon.entities_found
        )
