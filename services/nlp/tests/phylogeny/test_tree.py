# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
import random

from silsilah.phylogeny.tree import build_tree

from .helpers import node, unit

SAME = unit(1, 0, 0)
CLOSE = unit(1, 0.1, 0)
FAR = unit(0, 1, 0)


def test_root_is_oldest_reported_and_low_edge_goes_to_root() -> None:
    a = node("a", "2026-02-03", SAME)
    b = node("b", "2026-02-06", CLOSE)
    c = node("c", "2026-02-07", FAR)
    tree = build_tree([c, b, a], t_edge=0.85)
    assert tree.root_id == "a"
    assert (tree.edges["b"].parent_id, tree.edges["b"].confidence) == ("a", "high")
    assert (tree.edges["c"].parent_id, tree.edges["c"].confidence) == ("a", "low")
    assert tree.edges["a"].parent_id is None


def test_same_date_tie_broken_by_submitted_at() -> None:
    late = node("a", "2026-04-01", SAME, submitted="2026-09-07")
    early = node("b", "2026-04-01", SAME, submitted="2026-09-02")
    assert build_tree([late, early], t_edge=0.85).root_id == "b"


def test_imprecise_date_compared_from_start_of_period() -> None:
    month = node("bulan", "2026-02-01", SAME, precision="month")  # "Februari 2026"
    day = node("hari", "2026-02-14", SAME)
    tree = build_tree([day, month], t_edge=0.85)
    assert tree.root_id == "bulan" and tree.edges["hari"].parent_id == "bulan"


def test_ambiguous_parent_keeps_alternatives_and_picks_earlier() -> None:
    a = node("a", "2026-01-01", SAME, body="teks lain sama sekali")
    b = node("b", "2026-01-02", SAME, body="pesan dasar satu")
    c = node("c", "2026-01-03", SAME, body="pesan dasar dua")
    d = node("d", "2026-01-04", SAME, body="pesan dasar tiga")
    edge = build_tree([a, b, c, d], t_edge=0.85).edges["d"]
    assert edge.parent_id == "b" and set(edge.alt_parent_ids) == {"b", "c"}


def test_lexical_similarity_breaks_embedding_tie() -> None:
    # Embedding sama persis (buta angka); teks menentukan induk: kakek tidak boleh menang.
    root = node("a", "2026-01-01", SAME, body="Selama 3 hari listrik padam di Kota Lamunan")
    mid = node("b", "2026-01-02", SAME, body="Selama 5 hari listrik padam di Kota Lamunan")
    leaf = node("c", "2026-01-03", SAME, body="Selama 5 hari listrik padam di Kota Lamunan. Sebarkan!")
    edge = build_tree([root, mid, leaf], t_edge=0.85).edges["c"]
    assert edge.parent_id == "b" and edge.alt_parent_ids == ()


def test_deterministic_and_order_independent() -> None:
    nodes = [node(f"v{i}", f"2026-03-{i + 1:02d}", unit(1, i * 0.05, 0), body=f"teks {i}") for i in range(8)]
    expected = build_tree(nodes, t_edge=0.9)
    for seed in range(5):
        shuffled = nodes[:]
        random.Random(seed).shuffle(shuffled)
        assert build_tree(shuffled, t_edge=0.9) == expected


def test_rebalance_when_older_variant_arrives() -> None:
    b = node("b", "2026-02-06", SAME, body="selama 5 hari")
    c = node("c", "2026-02-10", CLOSE, body="selama 5 hari resmi")
    before = build_tree([b, c], t_edge=0.85)
    a = node("a", "2026-02-03", SAME, body="selama 3 hari", submitted="2026-09-09")
    after = build_tree([b, c, a], t_edge=0.85)
    assert before.root_id == "b"
    assert after.root_id == "a" and after.edges["b"].parent_id == "a" and after.edges["c"].parent_id == "b"
