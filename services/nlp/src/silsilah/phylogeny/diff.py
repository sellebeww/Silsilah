# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Diff mutasi induk -> anak: penyelarasan tingkat kata, klasifikasi kategori, ringkasan satu baris."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import cache
from importlib.resources import files
from typing import Any, Literal

import yaml

Category = Literal["number", "institution", "call_to_action", "date", "place", "url", "other"]
Op = Literal["replace", "insert", "delete", "reorder"]

# Token: placeholder anonim, URL, angka bertitik/berkoma/persen, kata (boleh bertanda hubung), tanda baca.
_TOKEN = re.compile(
    r"\[[A-Z_]+\]|(?:https?://|www\.)\S+|\d+(?:[.,:]\d+)*%?|[^\W\d_]+(?:[-'’][^\W\d_]+)*|[^\w\s]", re.UNICODE
)
# Tanggal (12-05-2026, 12/5) dan jam (20.00), tetapi bukan nominal bertitik ribuan (25.000.000).
_DATE_PATTERN = re.compile(
    r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b|\b\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[.:]\d{2}\b(?![.,]\d)"
)
_SENTENCE_END = frozenset(".!?")
_PUNCT = re.compile(r"[^\w\[\]]+")
# Di bawah rasio ini anak dianggap ditulis ulang (mis. terjemahan bahasa daerah); dirinci tidak bermakna.
REWRITE_RATIO = 0.5  # set tuning: rewrite <= 0,44; typo dan varian biasa >= 0,58
_CLAUSE_WORDS = 4
_LABELS: dict[Category, str] = {
    "number": "angka",
    "institution": "lembaga",
    "call_to_action": "ajakan",
    "date": "tanggal",
    "place": "tempat",
    "url": "tautan",
    "other": "teks",
}
_VERBS: dict[Op, str] = {
    "replace": "diganti",
    "insert": "ditambahkan",
    "delete": "dihapus",
    "reorder": "dipindah",
}


@dataclass(frozen=True)
class Mutation:
    category: Category
    op: Op
    before_text: str | None
    after_text: str | None
    position_hint: int  # offset karakter di teks anak


@dataclass(frozen=True)
class DiffResult:
    mutations: list[Mutation]
    summary: str
    rewritten: bool


@cache
def keywords() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(files(__package__).joinpath("keywords.yaml").read_text("utf-8"))
    return data


def _tokens(text: str) -> list[re.Match[str]]:
    return list(_TOKEN.finditer(text))


def _words(text: str | None) -> list[str]:
    return [w for w in _PUNCT.sub(" ", (text or "").casefold()).split() if w]


def _has_phrase(text: str, phrases: list[str]) -> bool:
    padded = f" {' '.join(_words(text))} "
    return any(f" {p} " in padded for p in phrases)


def classify(
    before: str | None, after: str | None, prev: str | None = None, next_: str | None = None
) -> Category:
    """Kategori satu perubahan (urutan prioritas di keywords.yaml), lalu dipertajam oleh kata di sekitarnya:
    "Kota [Lamunan -> Andaikata]" = tempat, "Bank [X -> Y]" = lembaga, "tanggal [20 -> 25] Juli" = tanggal."""
    category = _classify(before, after)
    kw = keywords()
    around = {w.casefold() for w in (prev, next_) if w}
    if category in ("other", "number") and around & set(kw["date"]["context_words"]):
        return "date"
    if category == "other" and prev:
        if prev.casefold() in kw["place"]["prefixes"]:
            return "place"
        if prev.casefold() in kw["institution"]["prefixes"]:
            return "institution"
    return category


def lexical_similarity(a: str, b: str) -> float:
    """Rasio kesamaan urutan token (0..1); peka terhadap perubahan angka/nama yang luput dari embedding."""
    return round(SequenceMatcher(None, _norm(_tokens(a)), _norm(_tokens(b)), autojunk=False).ratio(), 6)


def _classify(before: str | None, after: str | None) -> Category:
    kw = keywords()
    both = f"{before or ''} {after or ''}"
    folded = both.casefold()
    words = _words(both)
    cta = kw["call_to_action"]
    is_cta = any(w in cta["words"] for w in words)
    longest = max(len(_words(before)), len(_words(after)))
    first = (_words(after) or _words(before) or [""])[0]
    imperative = len(first) > 5 and any(first.endswith(s) for s in cta["imperative_suffixes"])
    if longest >= _CLAUSE_WORDS and (is_cta or imperative):
        return "call_to_action"
    url = kw["url"]
    if any(m in folded for m in url["markers"]) or re.search(
        r"\b[\w-]+\.(?:" + "|".join(url["tlds"]) + r")\b(?:/|$)", folded
    ):
        return "url"
    if _DATE_PATTERN.search(both) or any(w in kw["date"]["words"] for w in words):
        return "date"
    inst = kw["institution"]
    if _has_phrase(both, inst["prefixes"]) or any(w in inst["names"] for w in words):
        return "institution"
    if _has_phrase(both, kw["place"]["prefixes"]):
        return "place"
    if re.search(r"\d", both) or any(w in kw["number"]["words"] for w in words):
        return "number"
    if is_cta or imperative:
        return "call_to_action"
    return "other"


def _norm(tokens: list[re.Match[str]]) -> list[str]:
    return [t.group().casefold() for t in tokens]


Opcode = tuple[str, int, int, int, int]


def _merge_close(opcodes: Sequence[Opcode], pt: list[re.Match[str]]) -> list[Opcode]:
    """Gabungkan dua perubahan yang hanya dipisah satu kata sama: "Pasar Kota Lamunan" -> "Terminal Kota
    Andaikata" adalah satu perubahan tempat, bukan dua."""
    out: list[Opcode] = []
    for op in opcodes:
        if (
            op[0] != "equal"
            and len(out) >= 2
            and out[-1][0] == "equal"
            and out[-1][2] - out[-1][1] == 1
            and pt[out[-1][1]].group()[0].isalnum()
            and out[-2][0] != "equal"
        ):
            out.pop()
            first = out.pop()
            out.append(("replace", first[1], op[2], first[3], op[4]))
        else:
            out.append(op)
    return out


def _sentences(tokens: list[re.Match[str]], start: int, end: int) -> list[tuple[int, int]]:
    parts, begin = [], start
    for k in range(start, end - 1):
        if tokens[k].group() in _SENTENCE_END:
            parts.append((begin, k + 1))
            begin = k + 1
    parts.append((begin, end))
    return parts


def diff(parent: str, child: str) -> DiffResult:
    """Mutasi dari teks induk ke teks anak (keduanya sudah tersamar)."""
    pt, ct = _tokens(parent), _tokens(child)
    matcher = SequenceMatcher(None, _norm(pt), _norm(ct), autojunk=False)
    if matcher.ratio() < REWRITE_RATIO:
        return DiffResult([], "ditulis ulang (terlalu banyak perubahan untuk dirinci)", True)

    raw: list[tuple[Op, str | None, str | None, int, str | None, str | None]] = []
    for tag, i1, i2, j1, j2 in _merge_close(matcher.get_opcodes(), pt):
        if tag == "equal":
            continue
        # Sisipan/hapusan beberapa kalimat dipecah per kalimat: tiap kalimat bisa berkategori berbeda.
        pieces = (
            [(i1, i2, s, e) for s, e in _sentences(ct, j1, j2)]
            if tag == "insert"
            else [(s, e, j1, j2) for s, e in _sentences(pt, i1, i2)]
            if tag == "delete"
            else [(i1, i2, j1, j2)]
        )
        for a1, a2, b1, b2 in pieces:
            before = parent[pt[a1].start() : pt[a2 - 1].end()] if a2 > a1 else None
            after = child[ct[b1].start() : ct[b2 - 1].end()] if b2 > b1 else None
            if not _words(before) and not _words(after):
                continue  # hanya tanda baca
            pos = ct[b1].start() if b1 < len(ct) else len(child)
            prev = ct[b1 - 1].group() if b1 > 0 else None
            nxt = ct[b2].group() if b2 < len(ct) else None
            raw.append((tag, before, after, pos, prev, nxt))  # type: ignore[arg-type]

    # Blok yang dihapus lalu muncul lagi di tempat lain = urutan kalimat/paragraf berubah, bukan isi baru.
    deleted = {" ".join(_words(b)): k for k, (op, b, *_) in enumerate(raw) if op == "delete"}
    moved: set[int] = set()
    mutations: list[Mutation] = []
    for k, (op, _, after, pos, _, _) in enumerate(raw):
        key = " ".join(_words(after))
        if op == "insert" and key in deleted and len(key.split()) >= 3:
            moved |= {k, deleted.pop(key)}
            mutations.append(Mutation("other", "reorder", after, after, pos))
    for k, (op, before, after, pos, prev, nxt) in enumerate(raw):
        if k not in moved:
            mutations.append(Mutation(classify(before, after, prev, nxt), op, before, after, pos))
    mutations.sort(key=lambda m: m.position_hint)
    return DiffResult(mutations, summarize(mutations), False)


def summarize(mutations: list[Mutation]) -> str:
    """Ringkasan satu baris, mis. "angka diganti 3 -> 5; lembaga diganti; ajakan ditambahkan"."""
    parts: list[str] = []
    for m in mutations:
        text = f"{_LABELS[m.category]} {_VERBS[m.op]}"
        if m.op == "reorder":
            text = "urutan kalimat diubah"
        elif (
            m.op == "replace"
            and m.category in ("number", "date")
            and 0 < len(m.before_text or "") <= 20
            and 0 < len(m.after_text or "") <= 20
        ):
            text += f" {m.before_text} -> {m.after_text}"
        if text not in parts:
            parts.append(text)
    return "; ".join(parts) or "tidak ada perubahan isi"
