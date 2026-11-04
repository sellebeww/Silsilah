# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Evaluasi penempatan + diff pada dataset sintetis (tests/data/phylogeny). Jalankan: make eval

1. Sapuan grid T_family x T_edge pada set tuning.
2. Ambang terbaik diukur pada set holdout (tidak dipakai menyetel), dicetak sebagai Markdown.
"""

import itertools
import pathlib
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import yaml

from silsilah.ingest.embedding import SentenceTransformerEmbedding
from silsilah.ingest.settings import Settings
from silsilah.phylogeny.diff import diff
from silsilah.phylogeny.memory import InMemoryPhylogenyRepository
from silsilah.phylogeny.placement import PlacementService
from silsilah.phylogeny.tree import Node

DATA = pathlib.Path(__file__).resolve().parent.parent / "tests" / "data" / "phylogeny"
BASE = date(2026, 9, 1)
T_FAMILY = [round(0.40 + 0.05 * i, 2) for i in range(11)]
T_EDGE = [round(0.50 + 0.05 * i, 2) for i in range(10)]

Row = dict[str, Any]


@dataclass
class Outcome:
    family: dict[str, str]
    parent: dict[str, str | None]
    confidence: dict[str, str | None]
    oldest: set[str]
    categories: dict[str, list[str]]
    merges: int


def load(name: str) -> list[Row]:
    rows: list[Row] = yaml.safe_load((DATA / f"{name}.yaml").read_text("utf-8"))["variants"]
    return rows


def simulate(
    rows: list[Row], vectors: dict[str, tuple[float, ...]], t_family: float, t_edge: float
) -> Outcome:
    repo = InMemoryPhylogenyRepository()
    ids = itertools.count(1)
    service = PlacementService(repo, t_family, t_edge, new_id=lambda: f"F{next(ids)}")
    merges = 0
    for r in sorted(rows, key=lambda r: (r["order"], r["id"])):
        submitted = BASE + timedelta(days=r["order"])
        repo.add(Node(r["id"], r["first_seen"], r["precision"], submitted, 1, r["text"], vectors[r["id"]]))
        merges += bool(service.place(r["id"]).merge_suggestion)
    categories: dict[str, list[str]] = {}
    for rows_ in repo.mutations.values():
        for m in rows_:
            categories.setdefault(m.variant_id, []).append(m.category)
    return Outcome(
        family={k: str(v.family_id) for k, v in repo.records.items()},
        parent={k: u.parent_id for k, u in repo.updates.items()},
        confidence={k: u.edge_confidence for k, u in repo.updates.items()},
        oldest={k for k, u in repo.updates.items() if u.is_oldest},
        categories=categories,
        merges=merges,
    )


def score(rows: list[Row], out: Outcome) -> dict[str, float]:
    tp = fp = fn = 0
    for a, b in itertools.combinations(rows, 2):
        same_true = a["family"] == b["family"]
        same_pred = out.family[a["id"]] == out.family[b["id"]]
        tp += same_true and same_pred
        fp += same_pred and not same_true
        fn += same_true and not same_pred
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    # F0.5 dipakai memilih ambang: salah-gabung keluarga lebih merusak (mencemari klaim "tertua") daripada terpecah
    f05 = 1.25 * tp / (1.25 * tp + 0.25 * fn + fp) if tp else 0.0
    non_roots = [r for r in rows if r["parent"]]
    parent_acc = sum(out.parent[r["id"]] == r["parent"] for r in non_roots) / len(non_roots)
    families = Counter(r["family"] for r in rows)
    roots = [r for r in rows if not r["parent"] and families[r["family"]] > 1]
    oldest_acc = sum(r["id"] in out.oldest for r in roots) / len(roots)
    mean = (f05 + parent_acc + oldest_acc) / 3
    return {"f1": f1, "f05": f05, "parent": parent_acc, "oldest": oldest_acc, "mean": mean}


def diff_scores(rows: list[Row]) -> tuple[int, int, int, int, int, list[str]]:
    """Kategori diff pada tepi SEBENARNYA (induk asli -> anak), terpisah dari kesalahan memilih induk."""
    by_id = {r["id"]: r for r in rows}
    matched = total_true = total_pred = rewrite_ok = rewrite_total = 0
    failures: list[str] = []
    for r in rows:
        if not r["parent"] or r["mutations"] == "skip":
            continue
        result = diff(by_id[r["parent"]]["text"], r["text"])
        if r.get("rewrite"):
            rewrite_total += 1
            rewrite_ok += result.rewritten
            continue
        truth: Counter[str] = Counter(r["mutations"])
        pred: Counter[str] = Counter(str(m.category) for m in result.mutations)
        matched += sum((truth & pred).values())
        total_true += sum(truth.values())
        total_pred += sum(pred.values())
        if truth != pred:
            failures.append(
                f"`{r['id']}` benar={sorted(truth.elements())} prediksi={sorted(pred.elements())}"
            )
    return matched, total_true, total_pred, rewrite_ok, rewrite_total, failures


def sweep(
    rows: list[Row], vectors: dict[str, tuple[float, ...]]
) -> list[tuple[float, float, dict[str, float]]]:
    results = []
    for tf, te in itertools.product(T_FAMILY, T_EDGE):
        results.append((tf, te, score(rows, simulate(rows, vectors, tf, te))))
    # skor tertinggi; seri -> ambang lebih tinggi (lebih konservatif: lebih sedikit penggabungan keliru)
    results.sort(key=lambda x: (x[2]["mean"], x[0], x[1]), reverse=True)
    return results


def fmt(s: dict[str, float]) -> str:
    return f"{s['f1']:.3f} | {s['f05']:.3f} | {s['parent']:.3f} | {s['oldest']:.3f} | {s['mean']:.3f}"


def failures(rows: list[Row], out: Outcome) -> list[str]:
    lines = []
    clusters: dict[str, list[str]] = {}
    for r in rows:
        clusters.setdefault(out.family[r["id"]], []).append(r["id"])
    for members in clusters.values():
        if len({r["family"] for r in rows if r["id"] in members}) > 1:
            lines.append(f"- keluarga tergabung keliru: {', '.join(members)}")
    for fam in sorted({r["family"] for r in rows}):
        if len({out.family[r["id"]] for r in rows if r["family"] == fam}) > 1:
            lines.append(
                f"- keluarga {fam} terpecah: "
                + "; ".join(
                    ", ".join(m for m in members if m.startswith(fam))
                    for members in clusters.values()
                    if any(m.startswith(fam) for m in members)
                )
            )
    for r in rows:
        if r["parent"] and out.parent[r["id"]] != r["parent"]:
            lines.append(
                f"- induk `{r['id']}`: benar `{r['parent']}`, prediksi `{out.parent[r['id']]}` "
                f"(confidence {out.confidence[r['id']]}{', rewrite' if r.get('rewrite') else ''})"
            )
    for r in rows:
        if (
            not r["parent"]
            and r["id"] not in out.oldest
            and sum(x["family"] == r["family"] for x in rows) > 1
        ):
            pred = [o for o in out.oldest if out.family[o] == out.family[r["id"]]]
            lines.append(
                f"- tertua `{r['family']}`: benar `{r['id']}`, prediksi `{pred[0] if pred else '-'}`"
            )
    return lines


def main() -> None:
    settings = Settings("x", "x")
    embedder = SentenceTransformerEmbedding(settings.embedding_model, settings.embedding_dim)
    tune, holdout, holdout2 = load("tune"), load("holdout"), load("holdout2")
    vectors = {
        r["id"]: tuple(v)
        for r, v in zip(
            tune + holdout + holdout2,
            embedder.embed([r["text"] for r in tune + holdout + holdout2]),
            strict=True,
        )
    }
    results = sweep(tune, vectors)
    tf, te, _ = results[0]
    print(f"Model embedding: `{settings.embedding_model}`\n")
    print("### Sapuan pada set tuning (10 teratas)\n")
    print(
        "| T_family | T_edge | F1 keluarga | F0.5 keluarga | akurasi induk | akurasi tertua | skor |\n|---|---|---|---|---|---|---|"
    )
    for f, e, s in results[:10]:
        print(f"| {f:.2f} | {e:.2f} | {fmt(s)} |")
    print(f"\nTerpilih: **T_family = {tf:.2f}, T_edge = {te:.2f}**\n")
    print("### Hasil\n")
    print(
        "| Set | varian | F1 keluarga | F0.5 keluarga | akurasi induk | akurasi tertua | skor | saran gabung |\n|---|---|---|---|---|---|---|---|"
    )
    outs = {}
    for name, rows in (
        ("tuning", tune),
        ("holdout (terkontaminasi)", holdout),
        ("holdout2 (bersih)", holdout2),
    ):
        outs[name] = simulate(rows, vectors, tf, te)
        print(f"| {name} | {len(rows)} | {fmt(score(rows, outs[name]))} | {outs[name].merges} |")
    print("\n### Kategori diff (tepi sebenarnya)\n")
    print(
        "| Set | cocok / mutasi benar | presisi (cocok / prediksi) | rewrite terdeteksi |\n|---|---|---|---|"
    )
    diff_failures = {}
    for name, rows in (
        ("tuning", tune),
        ("holdout (terkontaminasi)", holdout),
        ("holdout2 (bersih)", holdout2),
    ):
        matched, total_true, total_pred, rw_ok, rw_total, diff_failures[name] = diff_scores(rows)
        print(
            f"| {name} | {matched}/{total_true} ({matched / total_true:.3f}) | {matched}/{total_pred} "
            f"({matched / total_pred:.3f}) | {rw_ok}/{rw_total} |"
        )
    for name, rows in (
        ("tuning", tune),
        ("holdout (terkontaminasi)", holdout),
        ("holdout2 (bersih)", holdout2),
    ):
        print(f"\n### Kasus gagal: {name}\n")
        print(
            "\n".join(failures(rows, outs[name]) + [f"- diff {f}" for f in diff_failures[name]])
            or "- (tidak ada)"
        )


if __name__ == "__main__":
    main()
