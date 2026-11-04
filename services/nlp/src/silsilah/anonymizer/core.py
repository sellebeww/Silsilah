# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""API anonimisasi. Fail-closed: setiap kegagalan menjadi AnonymizationError tanpa memuat teks input."""

import re
from collections import Counter
from dataclasses import dataclass

from .detectors import AKUN, EMAIL, LINK_GRUP, LINK_WA, NIK, REKENING, TELEPON, mask_regex
from .names import NAMA, NameRecognizer, mask_honorific_names, mask_ner_names
from .ner import default_recognizer
from .normalize import normalize

TOKEN_TYPES = (TELEPON, EMAIL, NIK, REKENING, AKUN, NAMA, LINK_WA, LINK_GRUP)
MAX_CHARS = 10_000

# Lebih longgar dari detektor email: tanpa syarat TLD, hanya untuk pemeriksaan akhir.
_STRICT_EMAIL = re.compile(
    r"[\w.+-](?:@|\s?[\[({<]at[\])}>]\s?)[\w-]*[A-Za-z][\w-]*\s?(?:\.|[\[({<](?:dot|titik)[\])}>])", re.I
)


class AnonymizationError(Exception):
    """Anonimisasi gagal; submission wajib ditolak. Pesan tidak pernah memuat teks input."""


class PiiLeakError(AnonymizationError):
    """Pola PII masih ditemukan pada hasil anonimisasi."""


@dataclass(frozen=True, slots=True)
class EntityCount:
    type: str
    count: int


@dataclass(frozen=True, slots=True)
class AnonResult:
    text: str
    entities_found: list[EntityCount]


def assert_no_pii(text: str) -> None:
    """Pindai ulang dengan seluruh detektor regex + email longgar; raise bila masih ada pola PII."""
    found: Counter[str] = Counter()
    mask_regex(text, found)
    if _STRICT_EMAIL.search(text):
        found[EMAIL] += 1
    if found:
        raise PiiLeakError("pola PII masih ada: " + ", ".join(sorted(found)))


def anonymize(text: str, ner: NameRecognizer | None = None) -> AnonResult:
    """Normalisasi lalu samarkan PII. ner=None memakai model default; tidak ada mode tanpa NER."""
    if not isinstance(text, str):
        raise TypeError("text harus str")
    if len(text) > MAX_CHARS:
        raise AnonymizationError(f"teks melebihi {MAX_CHARS} karakter")
    try:
        recognizer = ner if ner is not None else default_recognizer()
    except Exception as exc:
        raise AnonymizationError("model NER tidak tersedia") from exc

    counts: Counter[str] = Counter()
    out = mask_regex(normalize(text), counts)
    out = mask_honorific_names(out, counts)
    try:
        out = mask_ner_names(out, recognizer, counts)
    except Exception:
        # from None: traceback NER bisa memuat potongan teks
        raise AnonymizationError("NER gagal") from None
    assert_no_pii(out)
    return AnonResult(out, [EntityCount(t, counts[t]) for t in TOKEN_TYPES if counts[t]])
