# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Normalisasi teks sebelum deteksi PII dan sebelum hashing."""

import re
import unicodedata

# Karakter tak terlihat yang sering dipakai untuk menyamarkan nomor: zero-width, soft hyphen, bidi override.
_INVISIBLE = re.compile("[­᠎​-‏‪-‮⁠-⁤﻿]")
_KEYCAP = re.compile("([0-9#*])️?⃣")
_NON_ASCII_DIGIT = re.compile(r"[^\x00-\x7f]")
_SPACES = re.compile(r"[^\S\n]+")
_TOKEN = re.compile(r"(\[[A-Z_]+\])")
_NON_WORD = re.compile(r"[\W_]+")


def _ascii_digit(match: re.Match[str]) -> str:
    char = match.group()
    return str(unicodedata.decimal(char)) if unicodedata.category(char) == "Nd" else char


def normalize(text: str) -> str:
    """NFKC, buang karakter tak terlihat, ubah semua digit Unicode ke ASCII, rapikan spasi."""
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE.sub("", text)
    text = _KEYCAP.sub(r"\1", text)
    text = _NON_ASCII_DIGIT.sub(_ascii_digit, text)
    text = _SPACES.sub(" ", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def normalize_for_hash(text: str) -> str:
    """Bentuk kanonik teks tersamar untuk body_hash: huruf kecil, tanpa tanda baca, token anonim utuh."""
    parts = _TOKEN.split(normalize(text))
    # split dengan grup tangkap: indeks ganjil adalah token seperti [NAMA]
    out = [part if i % 2 else _NON_WORD.sub(" ", part.casefold()) for i, part in enumerate(parts)]
    return " ".join(" ".join(out).split())
