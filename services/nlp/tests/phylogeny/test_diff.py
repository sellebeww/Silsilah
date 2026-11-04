# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
import pytest

from silsilah.phylogeny.diff import diff, keywords

P = (
    "Info resmi: bantuan Rp 25.000.000 dari Kementerian Kesehatan untuk warga Kota Lamunan "
    "sebelum tanggal 20 Juli."
)


@pytest.mark.parametrize(
    ("child", "category", "summary"),
    [
        (P.replace("25.000.000", "50.000.000"), "number", "angka diganti 25.000.000 -> 50.000.000"),
        (P.replace("Kementerian Kesehatan", "Badan Pangan Rekaan"), "institution", "lembaga diganti"),
        (P.replace("Kota Lamunan", "Kota Andaikata"), "place", "tempat diganti"),
        (P.replace("20 Juli", "25 Juli"), "date", "tanggal diganti 20 -> 25"),
        (P + " Klaim lewat [TAUTAN]", "url", "tautan ditambahkan"),
        (P + " Segera sebarkan ke semua grup keluarga!", "call_to_action", "ajakan ditambahkan"),
    ],
)
def test_single_change_category_and_summary(child: str, category: str, summary: str) -> None:
    result = diff(P, child)
    assert [m.category for m in result.mutations] == [category]
    assert result.summary == summary


def test_thousands_are_numbers_not_dates() -> None:
    [m] = diff("denda Rp 1.000.000 per orang", "denda Rp 5.000.000 per orang").mutations
    assert m.category == "number"


def test_position_hint_points_into_child() -> None:
    child = P.replace("Kota Lamunan", "Kota Andaikata")
    [m] = diff(P, child).mutations
    assert child[m.position_hint :].startswith("Andaikata")


def test_two_added_sentences_classified_separately() -> None:
    result = diff(P, P + " Info dari Polsek Kota Andaikata. Sebarkan sekarang!")
    assert sorted(m.category for m in result.mutations) == ["call_to_action", "institution"]


def test_reordered_sentences_are_one_reorder_not_new_content() -> None:
    a = "Siapkan lilin dan senter. Listrik padam total selama 3 hari di Kota Lamunan."
    b = "Listrik padam total selama 3 hari di Kota Lamunan. Siapkan lilin dan senter."
    result = diff(a, b)
    assert [(m.category, m.op) for m in result.mutations] == [("other", "reorder")]
    assert result.summary == "urutan kalimat diubah"


def test_regional_rewrite_not_itemized() -> None:
    a = "Akan ada pemadaman listrik total di Kota Lamunan selama 5 hari mulai Senin. Siapkan lilin."
    b = "Listrik ning Kota Lamunan bakal mati total limang dina wiwit Senen. Siapke lilin lan cas HP."
    result = diff(a, b)
    assert result.rewritten and result.mutations == [] and "ditulis ulang" in result.summary


def test_identical_text_has_no_mutations() -> None:
    assert diff(P, P.upper()).summary == "tidak ada perubahan isi"


def test_keywords_come_from_yaml_data_file() -> None:
    kw = keywords()
    assert "sebarkan" in kw["call_to_action"]["words"] and "kementerian" in kw["institution"]["prefixes"]
