# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
import contextlib
import dataclasses
import logging
import time
from collections import Counter

import pytest

from silsilah.anonymizer import (
    AnonymizationError,
    PiiLeakError,
    anonymize,
    assert_no_pii,
    normalize,
    normalize_for_hash,
)
from silsilah.anonymizer.names import NameRecognizer

from .cases import CASES, Case, leaked


def no_ner(text: str) -> list[tuple[int, int]]:
    return []


@pytest.fixture(scope="session")
def ner() -> NameRecognizer:
    pytest.importorskip("transformers", reason="butuh extra ner: uv sync --extra ner")
    from silsilah.anonymizer.ner import default_recognizer

    return default_recognizer()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_case_no_leak(case: Case, ner: NameRecognizer) -> None:
    assert leaked(case, anonymize(case.text, ner=ner).text) == []


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_case_keeps_non_pii_and_counts_types(case: Case, ner: NameRecognizer) -> None:
    result = anonymize(case.text, ner=ner)
    assert [k for k in case.keep if k not in result.text] == []
    assert {e.type: e.count for e in result.entities_found} == dict(Counter(kind for kind, _ in case.pii))


def test_case_set_size() -> None:
    assert len(CASES) >= 40


def test_normalize_unicode_tricks() -> None:
    assert normalize("０８１２​３４ 0️⃣") == "081234 0"
    assert normalize("  a\t\tb \n  c ") == "a b\nc"


def test_normalize_for_hash_keeps_tokens_and_ignores_noise() -> None:
    a = normalize_for_hash("INFO!!  Hubungi [NAMA] di [TELEPON]...")
    b = normalize_for_hash("info hubungi [NAMA], di [TELEPON]")
    assert a == b == "info hubungi [NAMA] di [TELEPON]"
    assert normalize_for_hash("Rp 500.000") != normalize_for_hash("Rp 1.000.000")


def test_url_query_and_fragment_removed() -> None:
    out = anonymize("Baca https://berita.example/artikel/123?utm_source=wa&uid=99#top.", ner=no_ner).text
    assert out == "Baca https://berita.example/artikel/123."


@pytest.mark.parametrize(
    "text",
    ["0812-3456-7890", "a.b@contoh.id", "rina[at]contoh[dot]id", "wa.me/628", "t.me/+abc", "ikuti @budi_s"],
)
def test_assert_no_pii_rejects_leftovers(text: str) -> None:
    with pytest.raises(PiiLeakError) as exc:
        assert_no_pii(f"teks {text} teks")
    assert text not in str(exc.value)


def test_assert_no_pii_accepts_anonymized_text() -> None:
    assert_no_pii("Hubungi [NAMA] di [TELEPON], transfer Rp 1.000.000 sebelum 12-05-2026 @Rp5.000")


def test_result_holds_types_and_counts_only() -> None:
    result = anonymize("Hubungi 0812-3456-7890 atau 0813-1111-2222", ner=no_ner)
    assert [dataclasses.asdict(e) for e in result.entities_found] == [{"type": "TELEPON", "count": 2}]


def test_ner_filters_institutions_and_roles() -> None:
    text = "BPOM dan Menteri Kesehatan Budi Hartanto"

    def fake(t: str) -> list[tuple[int, int]]:
        return [(0, 4), (t.index("Menteri"), len(t))]

    assert anonymize(text, ner=fake).text == "BPOM dan Menteri Kesehatan [NAMA]"


def test_ner_failure_is_closed_and_hides_text() -> None:
    def broken(t: str) -> list[tuple[int, int]]:
        raise RuntimeError(f"gagal di {t}")

    with pytest.raises(AnonymizationError) as exc:
        anonymize("rahasia Sutrisno", ner=broken)
    assert "rahasia" not in str(exc.value) and exc.value.__suppress_context__


def test_missing_model_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable() -> NameRecognizer:
        raise OSError("model tidak ada")

    monkeypatch.setattr("silsilah.anonymizer.core.default_recognizer", unavailable)
    with pytest.raises(AnonymizationError, match="model NER tidak tersedia"):
        anonymize("teks biasa")


def test_too_long_rejected() -> None:
    with pytest.raises(AnonymizationError):
        anonymize("a" * 10_001, ner=no_ner)


@pytest.mark.parametrize("unit", ["a", "1 ", "a.b", "0", "@a", "x@", "Pak ", "08-"])
def test_no_catastrophic_backtracking(unit: str) -> None:
    text = (unit * 10_000)[:10_000]
    start = time.perf_counter()
    with contextlib.suppress(AnonymizationError):
        anonymize(text, ner=no_ner)
    assert time.perf_counter() - start < 2.0


def test_input_never_logged(caplog: pytest.LogCaptureFixture, ner: NameRecognizer) -> None:
    caplog.set_level(logging.DEBUG)
    anonymize("Pesan rahasia dari Bu Rina Kartikasari 0812-3456-7890", ner=ner)
    assert "rahasia" not in caplog.text and "Kartikasari" not in caplog.text
