# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Lapis 2: nama orang lewat heuristik sapaan dan NER, dengan pengecualian lembaga dan jabatan."""

import re
from collections import Counter
from collections.abc import Callable

from .rules import (
    ATTRIBUTION,
    INSTITUTION_WORDS,
    KIN_HONORIFICS,
    NAME_CONNECTORS,
    OTHER_HONORIFICS,
    STOP_WORDS,
    TITLES,
)

NAMA = "NAMA"
NameRecognizer = Callable[[str], list[tuple[int, int]]]

_TRIGGERS = sorted([*KIN_HONORIFICS, *OTHER_HONORIFICS, *ATTRIBUTION], key=len, reverse=True)
_TRIGGER = re.compile(
    r"(?<![\w\-/.])(" + "|".join(re.escape(t) for t in _TRIGGERS) + r")\.?[ \t]*:?[ \t]+", re.I
)
_WORD = re.compile(r"[^\W\d_][\w'’.-]*")
_GAP = re.compile(r"[ \t]+")
_TOKEN = re.compile(r"\[[A-Z_]+\]")
# Gelar akademik di belakang nama (S.H., M.Sc., Sp.PD, S.Kom) bukan identitas; dibiarkan terlihat.
_DEGREE = re.compile(r"[A-Z][a-zA-Z]{0,2}\.[A-Za-z.]+")
_MAX_NAME_WORDS = 4


def _bare(word: str) -> str:
    return word.rstrip(".").casefold()


def _is_stop(word: str) -> bool:
    return _bare(word) in STOP_WORDS or _DEGREE.fullmatch(word) is not None


def _word_end(m: re.Match[str]) -> int:
    """Akhir kata tanpa titik akhir kalimat; inisial seperti "A." tetap utuh."""
    word = m.group()
    return m.end() - 1 if word.endswith(".") and len(word.rstrip(".")) > 1 else m.end()


def _name_after(text: str, pos: int, allow_lowercase: bool) -> tuple[int, int] | None:
    """Rentang nama sesudah sapaan: maks 4 kata kapital, berhenti di kata jabatan/lembaga/umum."""
    start = end = -1
    while True:
        m = _WORD.match(text, pos)
        if not m:
            break
        word, bare = m.group(), _bare(m.group())
        sentence_end = _word_end(m) < m.end()
        if start < 0 and bare in TITLES:
            pass  # gelar bertumpuk tetap terlihat: "Prof. Dr. Ir. <nama>"
        elif _is_stop(word):
            break
        elif word[0].isupper():
            start = m.start() if start < 0 else start
            end = _word_end(m)
            if text[start:end].count(" ") >= _MAX_NAME_WORDS - 1:
                break
        elif bare in NAME_CONNECTORS and start >= 0:
            pass  # "bin", "van": hanya disertakan bila diikuti kata kapital
        elif start < 0 and allow_lowercase and len(bare) >= 3 and bare.isalpha():
            return m.start(), m.end() - (1 if word.endswith(".") else 0)
        else:
            break
        gap = _GAP.match(text, m.end())
        if sentence_end or not gap:
            break
        pos = gap.end()
    return (start, end) if start >= 0 else None


def mask_honorific_names(text: str, counts: Counter[str]) -> str:
    """Samarkan nama sesudah sapaan/gelar/atribusi ("Bu Rina", "a.n. Sutrisno"); sapaannya tetap."""
    spans: list[tuple[int, int]] = []
    for m in _TRIGGER.finditer(text):
        span = _name_after(text, m.end(), m.group(1).casefold() in KIN_HONORIFICS)
        if span and (not spans or span[0] >= spans[-1][1]):
            spans.append(span)
    return _replace(text, spans, counts)


def _is_shouting(text: str) -> bool:
    letters = [c for c in _TOKEN.sub("", text) if c.isalpha()]
    return bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.6


def _clean_ner_span(
    text: str, start: int, end: int, tokens: list[tuple[int, int]], shouting: bool
) -> tuple[int, int] | None:
    """Rapikan span NER ke kata nama; None bila span adalah lembaga atau tidak menyisakan nama."""
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "'’-"):
        start -= 1
    while end < len(text) and (text[end].isalnum() or text[end] in "'’-"):
        end += 1
    words = [
        w for w in _WORD.finditer(text, start, end) if not any(ts <= w.start() < te for ts, te in tokens)
    ]
    if any(_bare(w.group()) in INSTITUTION_WORDS for w in words):
        return None
    # NER sering ikut menandai kata di sebelah token "[NAMA]"; di situ hanya kata kapital yang dipercaya.
    if any(ts <= end + 1 and te >= start - 1 for ts, te in tokens):
        words = [w for w in words if w.group()[0].isupper()]
    while words and _is_stop(words[0].group()):
        words.pop(0)
    while words and _is_stop(words[-1].group()):
        words.pop()
    if not words:
        return None
    # Akronim pendek (BPOM, WHO) hampir selalu lembaga, kecuali seluruh pesan ditulis kapital.
    if not shouting and all(w.group().isupper() and 2 <= len(w.group()) <= 6 for w in words):
        return None
    # NER kadang hanya menangkap nama depan ("Dewi" dari "Dewi Lestari"): ikutkan kata kapital sesudahnya.
    last = words[-1]
    while len(words) < _MAX_NAME_WORDS and (gap := _GAP.match(text, last.end())):
        nxt = _WORD.match(text, gap.end())
        if not nxt or not nxt.group()[0].isupper() or _is_stop(nxt.group()):
            break
        words.append(nxt)
        last = nxt
    return words[0].start(), _word_end(words[-1])


def mask_ner_names(text: str, recognizer: NameRecognizer, counts: Counter[str]) -> str:
    shouting = _is_shouting(text)
    tokens = [(t.start(), t.end()) for t in _TOKEN.finditer(text)]
    spans = sorted(
        span
        for s, e in recognizer(text)
        if (span := _clean_ner_span(text, s, e, tokens, shouting)) is not None
    )
    merged: list[tuple[int, int]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return _replace(text, merged, counts)


def _replace(text: str, spans: list[tuple[int, int]], counts: Counter[str]) -> str:
    for s, e in reversed(spans):
        text = f"{text[:s]}[{NAMA}]{text[e:]}"
    counts[NAMA] += len(spans)
    return text
