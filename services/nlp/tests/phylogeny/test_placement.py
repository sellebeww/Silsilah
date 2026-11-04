# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
import itertools

import pytest

from silsilah.phylogeny.memory import InMemoryPhylogenyRepository
from silsilah.phylogeny.placement import PlacementError, PlacementService
from silsilah.phylogeny.tree import Node

from .helpers import node, unit

BASE = "Akan ada pemadaman listrik total di Kota Lamunan selama 3 hari. Sebarkan ke keluarga."


def service() -> tuple[InMemoryPhylogenyRepository, PlacementService]:
    repo = InMemoryPhylogenyRepository()
    ids = itertools.count(1)
    return repo, PlacementService(repo, t_family=0.6, t_edge=0.85, new_id=lambda: f"F{next(ids)}")


def place(repo: InMemoryPhylogenyRepository, svc: PlacementService, n: Node) -> None:
    repo.add(n)
    svc.place(n.id)


def test_first_variant_creates_family_and_is_oldest() -> None:
    repo, svc = service()
    repo.add(node("a", "2026-02-03", unit(1, 0), body=BASE))
    plan = svc.place("a")
    assert plan.new_family and plan.family_id == "F1" and plan.oldest.id == "a"
    assert repo.records["a"].moderation_status == "approved"


def test_join_family_with_parent_mutations_and_summary() -> None:
    repo, svc = service()
    place(repo, svc, node("a", "2026-02-03", unit(1, 0), body=BASE))
    repo.add(node("b", "2026-02-06", unit(1, 0.05), body=BASE.replace("3 hari", "5 hari")))
    plan = svc.place("b")
    update = {n.id: n for n in plan.nodes}["b"]
    assert (plan.family_id, plan.new_family, update.parent_id) == ("F1", False, "a")
    assert update.mutation_summary == "angka diganti 3 -> 5"
    assert [(m.category, m.before_text, m.after_text) for m in plan.mutations] == [("number", "3", "5")]


def test_placement_is_idempotent() -> None:
    repo, svc = service()
    place(repo, svc, node("a", "2026-02-03", unit(1, 0), body=BASE))
    repo.add(node("b", "2026-02-06", unit(1, 0.05), body=BASE.replace("3", "5")))
    first = svc.place("b")
    assert svc.place("b") == first
    assert svc.place("a").nodes == first.nodes


def test_older_variant_reported_later_rebalances_tree() -> None:
    repo, svc = service()
    place(
        repo, svc, node("b", "2026-02-06", unit(1, 0.05), body=BASE.replace("3", "5"), submitted="2026-09-01")
    )
    place(repo, svc, node("c", "2026-02-10", unit(1, 0.1), body=BASE.replace("3", "5") + " Resmi."))
    repo.add(node("a", "2026-02-03", unit(1, 0), body=BASE, submitted="2026-09-09"))
    plan = svc.place("a")
    edges = {n.id: (n.parent_id, n.is_oldest) for n in plan.nodes}
    assert edges == {"a": (None, True), "b": ("a", False), "c": ("b", False)}
    assert plan.oldest.id == "a"


def test_similar_to_two_families_is_flagged_not_merged() -> None:
    repo, svc = service()
    place(repo, svc, node("x", "2026-01-01", unit(1, 0, 0), body="keluarga satu"))
    place(repo, svc, node("y", "2026-01-02", unit(0, 1, 0), body="keluarga dua"))
    repo.add(node("z", "2026-01-03", unit(1, 0.9, 0), body="mirip keduanya"))
    plan = svc.place("z")
    assert plan.family_id == "F1" and plan.merge_suggestion == ("F2",)
    assert repo.records["y"].family_id == "F2"


def test_centroid_prevents_chaining_through_one_member() -> None:
    repo, svc = service()
    # F1 rapat di sekitar (1,0,0); "b" agak melenceng ke arah (0,1,0)
    place(repo, svc, node("a1", "2026-01-01", unit(1, 0, 0)))
    place(repo, svc, node("a2", "2026-01-02", unit(1, 0.05, 0)))
    place(repo, svc, node("b", "2026-01-03", unit(1, 0.6, 0)))
    # mirip "b" (0.66) tetapi jauh dari pusat keluarga: jadi keluarga baru, bukan menempel lewat "b"
    repo.add(node("z", "2026-01-04", unit(0.2, 1, 0)))
    assert svc.place("z").new_family


@pytest.mark.parametrize(
    ("status", "embedding", "message"), [("rejected", True, "ditolak"), ("pending", False, "embedding")]
)
def test_unplaceable_variants(status: str, embedding: bool, message: str) -> None:
    repo, svc = service()
    repo.add(node("a", "2026-01-01", unit(1, 0)), status=status)
    if not embedding:
        repo.records["a"] = repo.records["a"].__class__(None, None, status)
    with pytest.raises(PlacementError, match=message):
        svc.place("a")
    with pytest.raises(PlacementError, match="tidak ditemukan"):
        svc.place("tidak-ada")
