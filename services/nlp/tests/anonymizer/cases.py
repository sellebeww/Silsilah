# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Set uji sintetis anonimisasi. Semua nama, nomor, akun, dan lembaga di sini fiktif."""

import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from silsilah.anonymizer import AnonResult, normalize


@dataclass(frozen=True)
class Case:
    id: str
    text: str
    pii: tuple[tuple[str, str], ...] = ()  # (tipe, nilai asli) yang wajib hilang
    keep: tuple[str, ...] = ()  # potongan yang wajib tetap ada (uji positif-palsu)


def c(id: str, text: str, pii: Iterable[tuple[str, str]] = (), keep: Iterable[str] = ()) -> Case:
    return Case(id, text, tuple(pii), tuple(keep))


T, E, N, R, A, P, W, G = "TELEPON", "EMAIL", "NIK", "REKENING", "AKUN", "NAMA", "LINK_WA", "LINK_GRUP"

CASES = [
    # Telepon
    c("tel-dash", "Hubungi 0812-3456-7890 sekarang juga.", [(T, "0812-3456-7890")], ["sekarang juga."]),
    c("tel-intl", "Info lanjut: +62 812 3456 7890", [(T, "+62 812 3456 7890")], ["Info lanjut:"]),
    c("tel-62", "WA 6281234567890 ya", [(T, "6281234567890")], [" ya"]),
    c("tel-paren-dot", "Telp (0812) 3456.7890 siang hari", [(T, "(0812) 3456.7890")], ["siang hari"]),
    c("tel-spaced", "nomor: 0 8 1 2 3 4 5 6 7 8 9 0", [(T, "081234567890")]),
    c("tel-leet-O", "hub O812-3456-789O segera", [(T, "O812-3456-789O")], ["segera"]),
    c("tel-leet-l", "sms ke 08l2 3456 7890", [(T, "08l2 3456 7890")]),
    c("tel-zero-width", "Kontak 0812​3456​7890 malam ini", [(T, "081234567890")], ["malam ini"]),
    c("tel-fullwidth", "Telepon ０８１２３４５６７８９０", [(T, "081234567890")]),
    c("tel-keycap", "WA 0️⃣8️⃣1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣8️⃣9️⃣0️⃣", [(T, "081234567890")]),
    c(
        "tel-two",
        "Hubungi +62-812-3456-7890 / 0813 9876 5432",
        [(T, "+62-812-3456-7890"), (T, "0813 9876 5432")],
    ),
    c("tel-landline", "Kantor: (021) 5550 1234", [(T, "(021) 5550 1234")], ["Kantor:"]),
    c("tel-glued", "WA:081234567890", [(T, "081234567890")]),
    c("tel-glued-word", "telp08123456789 skrg", [(T, "08123456789")], ["skrg"]),
    c("tel-dash-spaced", "0812 - 3456 - 7890 (admin)", [(T, "081234567890")], ["(admin)"]),
    c("tel-dots", "Pemesanan 0857.1234.5678", [(T, "0857.1234.5678")], ["Pemesanan"]),
    # Email
    c("email-plain", "Kirim bukti ke rina.kartika@contoh.example ya", [(E, "rina.kartika@contoh.example")]),
    c("email-brackets", "email: sutrisno [at] contoh [dot] id", [(E, "sutrisno")]),
    c("email-paren", "admin(at)lapor-contoh.co.id", [(E, "admin(at)lapor-contoh.co.id")]),
    c("email-spaced", "tulis ke joko @ contoh.id", [(E, "joko @ contoh.id")], ["tulis ke"]),
    # NIK
    c("nik-plain", "NIK 3201121508900001 hilang", [(N, "3201121508900001")], ["hilang"]),
    c("nik-dots", "NIK: 3201.12.150890.0001", [(N, "3201121508900001")]),
    c("nik-groups", "nik 3201 1215 0890 0001", [(N, "3201121508900001")]),
    c(
        "nik-female",
        "KTP 3201125508900002 atas nama sendiri",
        [(N, "3201125508900002")],
        ["atas nama sendiri"],
    ),
    # Rekening / kartu
    c(
        "rek-bca",
        "Transfer ke rek BCA 1234567890 a.n. Sutrisno Wibowo",
        [(R, "1234567890"), (P, "Sutrisno Wibowo")],
        ["BCA", "a.n."],
    ),
    c("rek-card", "kartu 4111 1111 1111 1111 exp 12/29", [(R, "4111111111111111")], ["12/29"]),
    c("rek-mandiri", "Mandiri 123-00-1234567-8", [(R, "1230012345678")], ["Mandiri"]),
    c("rek-bri", "BRI 0021-01-012345-50-1", [(R, "002101012345501")], ["BRI"]),
    # Akun dan tautan
    c(
        "handle-two",
        "follow @rina_kartika dan @infohoaks.id",
        [(A, "rina_kartika"), (A, "infohoaks.id")],
        ["follow"],
    ),
    c("handle-url", "cek tiktok.com/@budi.santoso99 deh", [(A, "budi.santoso99")], ["tiktok.com/"]),
    c("wa-group", "Gabung grup https://chat.whatsapp.com/AbCdEfGh123", [(W, "AbCdEfGh123")], ["Gabung grup"]),
    c("wa-me", "chat langsung wa.me/6281234567890.", [(W, "6281234567890")], ["chat langsung"]),
    c(
        "tg-invite",
        "join t.me/joinchat/AAAAbbbb dan https://t.me/+AbCdEf",
        [(G, "AAAAbbbb"), (G, "AbCdEf")],
        ["join", "dan"],
    ),
    # Nama: heuristik sapaan
    c(
        "name-pak",
        "Kata Pak Sutrisno Wibowo, besok listrik padam.",
        [(P, "Sutrisno Wibowo")],
        ["besok listrik padam"],
    ),
    c("name-bu", "Bu Rina Kartikasari sudah transfer", [(P, "Rina Kartikasari")], ["sudah transfer"]),
    c(
        "name-dr",
        "dr. Hendra Gunawan, Sp.PD menyarankan minum air garam",
        [(P, "Hendra Gunawan")],
        ["menyarankan minum air garam"],
    ),
    c("name-lowercase", "td pak joko blg besok libur", [(P, "joko")], ["besok libur"]),
    c("name-two", "Mbak Ayu dan Mas Bagus Prakoso ikut", [(P, "Ayu"), (P, "Bagus Prakoso")], ["ikut"]),
    c(
        "name-titles",
        "Prof. Dr. Ir. Siti Rahmawati, M.Sc. menjelaskan",
        [(P, "Siti Rahmawati")],
        ["menjelaskan"],
    ),
    c("name-bin", "Ustadz Ahmad bin Abdullah berpesan", [(P, "Ahmad bin Abdullah")], ["berpesan"]),
    c(
        "name-layered",
        "Kak Rina, tolong sampaikan ke Bapak Joko Santoso dan Ibu Sri Wahyuni",
        [(P, "Rina"), (P, "Joko Santoso"), (P, "Sri Wahyuni")],
        ["tolong sampaikan"],
    ),
    c("name-caps", "PESAN DARI PAK SUTRISNO WIBOWO: BESOK LIBUR", [(P, "SUTRISNO WIBOWO")], ["BESOK LIBUR"]),
    # Nama: hanya NER
    c(
        "ner-plain",
        "Menurut Andi Saputra, warga Kota Lamunan, air sumur sudah tercemar.",
        [(P, "Andi Saputra")],
        ["Kota Lamunan"],
    ),
    c(
        "ner-signature",
        "Mohon disebarkan.\nSalam,\nDewi Lestari",
        [(P, "Dewi Lestari")],
        ["Mohon disebarkan."],
    ),
    c(
        "ner-official",
        "Menteri Kesehatan Budi Hartanto membantah kabar itu",
        [(P, "Budi Hartanto")],
        ["Menteri Kesehatan"],
    ),
    # Campur bahasa daerah dan singkatan chat
    c(
        "mix-jawa",
        "Lur, nomere Mas Bagus 0857 1234 5678, ojo lali disebar",
        [(P, "Bagus"), (T, "0857 1234 5678")],
        ["ojo lali disebar"],
    ),
    c(
        "mix-sunda",
        "Punten, kontak Teh Euis di 0821-9876-5432 nya",
        [(P, "Euis"), (T, "0821-9876-5432")],
        ["Punten"],
    ),
    c(
        "mix-chat",
        "yg mau daftar hub cp: 085612345678 (wa only) gpp",
        [(T, "085612345678")],
        ["(wa only) gpp"],
    ),
    c(
        "mix-minang",
        "Uda Rizal alah mangirim pitih ka rek 9876543210",
        [(P, "Rizal"), (R, "9876543210")],
        ["alah mangirim pitih"],
    ),
    # Positif-palsu: tidak boleh ada yang disamarkan
    c("fp-amount", "Bantuan Rp 500.000 untuk 10 hari", keep=["Rp 500.000", "10 hari"]),
    c("fp-big-amount", "Hadiah Rp 1.000.000.000 dibagikan gratis", keep=["Rp 1.000.000.000"]),
    c(
        "fp-institutions",
        "Kementerian Kesehatan dan BPOM menyatakan aman",
        keep=["Kementerian Kesehatan", "BPOM"],
    ),
    c("fp-who", "Menurut WHO dan UNICEF, vaksin aman", keep=["WHO", "UNICEF"]),
    c("fp-datetime", "Tanggal 12-05-2026 pukul 10.30 WIB", keep=["12-05-2026", "10.30"]),
    c("fp-ibu-kota", "Ibu kota pindah tahun 2026", keep=["Ibu kota", "2026"]),
    c(
        "fp-reduplication",
        "Bapak-bapak dan ibu-ibu sekalian, harap waspada",
        keep=["Bapak-bapak dan ibu-ibu"],
    ),
    c("fp-roles", "Pak Menteri dan Bu Gubernur hadir di acara", keep=["Pak Menteri", "Bu Gubernur"]),
    c("fp-discount", "Diskon 50% sampai 31 Desember 2026", keep=["50%", "31 Desember 2026"]),
    c(
        "fp-fictional-orgs",
        "Dirawat di RS Rekaan Medika dan Universitas Andaikata",
        keep=["RS Rekaan Medika", "Universitas Andaikata"],
    ),
    c(
        "fp-stats",
        "Dinas Kesehatan Kota Lamunan mencatat 1.250 kasus, naik 300 persen",
        keep=["Dinas Kesehatan Kota Lamunan", "1.250 kasus"],
    ),
    c("fp-postcode", "Kode pos 40115, RT 05 RW 03", keep=["40115", "RT 05 RW 03"]),
    c("fp-quake", "Gempa M 6,2 terjadi pukul 08.15 WIB", keep=["6,2", "08.15"]),
    c("fp-cta", "Sebarkan ke 20 grup sebelum jam 12.00", keep=["20 grup", "12.00"]),
    c("fp-gold", "Harga emas naik jadi Rp 1.250.000 per gram", keep=["Rp 1.250.000"]),
    c("fp-president", "Presiden mengumumkan libur nasional", keep=["Presiden mengumumkan"]),
    c("fp-email-word", "Kirim email ke alamat resmi di situs", keep=["Kirim email ke alamat resmi"]),
    c("fp-ref-number", "Laporan nomor 2026/05/001234", keep=["2026/05/001234"]),
]

# Holdout: ditulis SETELAH aturan disetel pada CASES dan tidak dipakai untuk menyetel; hanya untuk eval_report.
HOLDOUT = [
    c(
        "h-arisan",
        "Yang mau ikut arisan hubungi Bu Nining 0838-1122-3344 ya bun",
        [(P, "Nining"), (T, "0838-1122-3344")],
        ["ikut arisan"],
    ),
    c(
        "h-kang",
        "Sumber: grup alumni, diteruskan oleh Kang Asep Supriatna",
        [(P, "Asep Supriatna")],
        ["grup alumni"],
    ),
    c(
        "h-an-nodot",
        "Transfer dana ke BNI 0123456789 an Rahmat Hidayat",
        [(R, "0123456789"), (P, "Rahmat Hidayat")],
        ["BNI"],
    ),
    c(
        "h-adik",
        "Info dari adik saya, Fitri, yang kerja di RSUD Kota Lamunan",
        [(P, "Fitri")],
        ["RSUD Kota Lamunan"],
    ),
    c(
        "h-darurat",
        "Kontak darurat: +62 857-0011-2233 (Pak Herman)",
        [(T, "+62 857-0011-2233"), (P, "Herman")],
    ),
    c("h-email", "dikirim oleh yanti.susanti88@contoh.example", [(E, "yanti.susanti88@contoh.example")]),
    c("h-ig", "IG @lamunan.info udah konfirmasi", [(A, "lamunan.info")], ["udah konfirmasi"]),
    c("h-wa-channel", "Gabung channel https://whatsapp.com/channel/0029VaAbCdEf", [(W, "0029VaAbCdEf")]),
    c(
        "h-ktp",
        "KTP atas nama Dimas Anggara NIK 3578011203950003",
        [(P, "Dimas Anggara"), (N, "3578011203950003")],
        ["KTP"],
    ),
    c("h-wartawan", "Wartawan Lestari Wulandari melaporkan dari lokasi", [(P, "Lestari Wulandari")]),
    c("h-dr-nodot", "Ini pesan dr Eko, dokter puskesmas", [(P, "Eko")], ["dokter puskesmas"]),
    c("h-rek-dash", "nomor rekening 1234-5678-9012 a/n Wahyu", [(R, "123456789012"), (P, "Wahyu")]),
    c("h-mbah", "Pesan dari Mbah Darmo di kampung", [(P, "Darmo")], ["di kampung"]),
    c("h-landline-spaced", "Telp: 0 2 2 - 7 7 7 - 8 8 8 8", [(T, "0227778888")]),
    c("h-cak", "hub. Cak Mamat 0819 1234 5678 sebelum jam 5", [(P, "Mamat"), (T, "0819 1234 5678")]),
    c(
        "h-shouting",
        "PERHATIAN!!! BAPAK BUDIMAN SETIAWAN MENIPU WARGA",
        [(P, "BUDIMAN SETIAWAN")],
        ["MENIPU WARGA"],
    ),
    c("h-mention", "mention aja @admin_grup123 kalau ada yg aneh", [(A, "admin_grup123")]),
    c("h-fp-gubernur", "Kata Gubernur Andaikata tadi pagi", keep=["Gubernur Andaikata"]),
    c("h-fp-cabai", "Harga cabai Rp35.000/kg, naik 2x lipat", keep=["Rp35.000/kg"]),
    c("h-fp-antrian", "Nomor antrian 0012 sudah dipanggil", keep=["0012"]),
    c("h-fp-dana", "Dana 2.500.000.000 dicairkan", keep=["2.500.000.000"]),
    c("h-fp-bpjs", "Hubungi call center BPJS Kesehatan 165", keep=["BPJS Kesehatan 165"]),
    c("h-fp-tanggal", "Video viral di desa Sukarekaan tanggal 03/04/2026", keep=["03/04/2026"]),
    c("h-fp-satgas", "Tim Satgas Covid Kota Lamunan mengonfirmasi", keep=["Satgas Covid Kota Lamunan"]),
]

_LEET = str.maketrans("OoIl", "0011")
_DIGIT_TYPES = {T, N, R}


def _digits(s: str) -> str:
    return re.sub(r"\D", "", normalize(s).translate(_LEET))


def leaked(case: Case, output: str) -> list[str]:
    """Tipe PII yang nilai aslinya masih bisa ditemukan di output."""
    out_digits, out_fold = _digits(output), output.casefold()
    out_words = set(re.findall(r"\w+", out_fold))
    leaks = []
    for kind, value in case.pii:
        if kind in _DIGIT_TYPES:
            hit = _digits(value) in out_digits
        elif kind == P:
            hit = any(w in out_words for w in re.findall(r"\w{3,}", value.casefold()) if w not in {"bin"})
        elif kind == E:
            local = re.split(r"\s?(?:@|\[at\]|\(at\))", value)[0].casefold()
            hit = local in out_fold
        else:
            hit = value.casefold() in out_fold
        if hit:
            leaks.append(kind)
    return leaks


def evaluate(run: Callable[[str], AnonResult], cases: list[Case]) -> dict[str, float | int]:
    """Recall = nilai PII yang hilang / total. Precision = token bertipe benar / token yang dihasilkan."""
    total = removed = produced = correct = keep_violations = 0
    for case in cases:
        result = run(case.text)
        expected = Counter(kind for kind, _ in case.pii)
        found = Counter({e.type: e.count for e in result.entities_found})
        total += len(case.pii)
        removed += len(case.pii) - len(leaked(case, result.text))
        produced += sum(found.values())
        correct += sum((expected & found).values())
        keep_violations += sum(k not in result.text for k in case.keep)
    return {
        "cases": len(cases),
        "pii_values": total,
        "recall": removed / total,
        "precision": correct / produced if produced else 1.0,
        "tokens_produced": produced,
        "keep_violations": keep_violations,
    }
