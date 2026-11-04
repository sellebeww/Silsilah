# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Lapis 1: deteksi PII deterministik berbasis regex (nomor, email, akun, tautan)."""

import re
from collections import Counter
from collections.abc import Callable

TELEPON, EMAIL, NIK, REKENING, AKUN, LINK_WA, LINK_GRUP = (
    "TELEPON",
    "EMAIL",
    "NIK",
    "REKENING",
    "AKUN",
    "LINK_WA",
    "LINK_GRUP",
)

_LEET = str.maketrans("OoIl", "0011")
# Digit, atau O/o/I/l yang tidak menempel ke huruf lain (mis. "O812", "08l2") agar kata biasa tidak ikut.
_D = r"(?:[0-9]|(?<![^\W\d_])[OoIl](?![^\W\d_]))"
_DIGIT_RUN = re.compile(rf"(?<![0-9])(?:\+ ?|\( ?)?{_D}(?:[ \t.\-–—()]{{0,3}}{_D}){{5,24}}")
_DATE_PREFIX = re.compile(r"[(+]? ?\d{1,2}[-./]\d{1,2}[-./](?:\d{4}|\d{2})(?!\d)")
_AMOUNT = re.compile(r"\(?\d{1,3}(?:[.,]\d{3})+(?:,\d{1,2})?")
_CURRENCY_BEFORE = re.compile(r"(?i)(?:rp|idr|usd|\$|€|£)\.? ?$")
_NIK_PROVINCES = frozenset(
    [
        *range(11, 20),
        21,
        *range(31, 37),
        *range(51, 54),
        *range(61, 66),
        *range(71, 77),
        81,
        82,
        *range(91, 97),
    ]
)

_AT = r"(?:@| @ |\s?[\[({<]at[\])}>]\s?)"
_DOT = r"(?:\.|\s?[\[({<](?:dot|titik)[\])}>]\s?)"
# Panjang dibatasi agar tidak terjadi backtracking kuadratik pada teks panjang tanpa spasi.
_EMAIL = re.compile(
    rf"[\w.+-]{{1,64}}{_AT}[\w-]{{1,63}}(?:{_DOT}[\w-]{{1,63}}){{0,4}}{_DOT}[A-Za-z]{{2,24}}\b", re.I
)

_TAIL = r"[^\s<>\"']*"
_WA_LINK = re.compile(
    rf"(?<![\w.])(?:https?://)?(?:www\.)?"
    rf"(?:wa\.me|wa\.link|(?:api|chat|web)\.whatsapp\.com|whatsapp\.com/(?:channel|send))\b{_TAIL}",
    re.I,
)
_GROUP_LINK = re.compile(
    rf"(?<![\w.])(?:https?://)?(?:www\.)?"
    rf"(?:t\.me|telegram\.me|telegram\.dog|line\.me/R/ti/g|discord\.gg|discord(?:app)?\.com/invite"
    rf"|(?:facebook|fb)\.com/groups|signal\.group)\b{_TAIL}",
    re.I,
)
_URL = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+|(?<![\w.@])(?:[a-z0-9-]{1,63}\.){1,5}[a-z]{2,24}/[^\s<>\"']*", re.I
)
_HANDLE = re.compile(r"(?<![\w@.])@([A-Za-z0-9_](?:[A-Za-z0-9_.]{0,29}[A-Za-z0-9_])?)")
_TRAILING_PUNCT = ".,;:!?)]}\"'"


def _looks_like_nik(digits: str) -> bool:
    """Kode provinsi valid dan tanggal lahir masuk akal (perempuan: tanggal + 40)."""
    day = int(digits[6:8])
    day = day - 40 if day > 40 else day
    return int(digits[:2]) in _NIK_PROVINCES and 1 <= day <= 31 and 1 <= int(digits[8:10]) <= 12


def classify_digits(run: str, before: str = "") -> str | None:
    """Jenis PII untuk deretan angka, atau None bila tampak seperti angka biasa (nominal, tahun, jam)."""
    digits = re.sub(r"[^0-9]", "", run.translate(_LEET))
    if sum(c.isdigit() for c in run) < max(6, 0.75 * len(digits)):
        return None
    if run.lstrip("( ").startswith("+") and len(digits) >= 8:
        return TELEPON
    national = "0" + digits[2:] if digits.startswith("62") else digits
    if 9 <= len(national) <= 13 and national[0] == "0" and national[1] in "23456789":
        return TELEPON
    if len(digits) == 16 and _looks_like_nik(digits):
        return NIK
    if 10 <= len(digits) <= 19 and not (_AMOUNT.fullmatch(run.strip()) or _CURRENCY_BEFORE.search(before)):
        return REKENING
    return None


def _mask_digit_runs(text: str, counts: Counter[str]) -> str:
    out: list[str] = []
    pos = 0
    for m in _DIGIT_RUN.finditer(text):
        run = m.group()
        date = _DATE_PREFIX.match(run)
        if date:  # "12-05-2026 0812..." : tanggal dibiarkan, sisanya dipindai ulang
            replacement = date.group() + _mask_digit_runs(run[date.end() :], counts)
        else:
            kind = classify_digits(run, text[max(0, m.start() - 5) : m.start()])
            replacement = f"[{kind}]" if kind else run
            if kind:
                counts[kind] += 1
        out += [text[pos : m.start()], replacement]
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def _split_trailing(s: str) -> tuple[str, str]:
    core = s.rstrip(_TRAILING_PUNCT)
    return core, s[len(core) :]


def _mask_links(pattern: re.Pattern[str], token: str, text: str, counts: Counter[str]) -> str:
    def repl(m: re.Match[str]) -> str:
        counts[token] += 1
        return f"[{token}]" + _split_trailing(m.group())[1]

    return pattern.sub(repl, text)


def _strip_url_query(m: re.Match[str]) -> str:
    url, trailing = _split_trailing(m.group())
    return re.split(r"[?#]", url, maxsplit=1)[0] + trailing


def _mask_handle(counts: Counter[str]) -> Callable[[re.Match[str]], str]:
    def repl(m: re.Match[str]) -> str:
        name = m.group(1)
        # "@Rp5.000" adalah harga satuan, bukan akun
        if len(name) < 2 or not any(c.isalpha() or c == "_" for c in name) or name.lower().startswith("rp"):
            return m.group()
        counts[AKUN] += 1
        return f"[{AKUN}]"

    return repl


def mask_regex(text: str, counts: Counter[str]) -> str:
    """Samarkan tautan WA/grup, email, nomor, dan handle; buang query/fragment URL. Urutan penting."""
    text = _mask_links(_WA_LINK, LINK_WA, text, counts)
    text = _mask_links(_GROUP_LINK, LINK_GRUP, text, counts)
    text = _mask_links(_EMAIL, EMAIL, text, counts)
    text = _URL.sub(_strip_url_query, text)
    text = _mask_digit_runs(text, counts)
    return _HANDLE.sub(_mask_handle(counts), text)
