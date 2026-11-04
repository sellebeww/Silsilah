# Anonimisasi

Modul: `services/nlp/src/silsilah/anonymizer`. Prinsip: **recall dulu**. Lebih baik menyamarkan berlebihan daripada membocorkan identitas. Setiap kegagalan menolak submission (fail-closed).

```python
from silsilah.anonymizer import anonymize, normalize_for_hash

result = anonymize(text)        # AnonResult(text, entities_found=[EntityCount(type, count)])
body_hash = sha256(normalize_for_hash(result.text))
```

`entities_found` hanya berisi tipe dan jumlah, tidak pernah nilai asli. Modul tidak melakukan logging. Pesan error tidak memuat teks input, dan traceback NER diputus (`from None`).

## Alur

1. **Normalisasi**: NFKC, buang karakter tak terlihat (zero-width, soft hyphen, bidi override), keycap emoji `0️⃣` → `0`, semua digit Unicode → ASCII, rapikan spasi.
2. **Regex** (`detectors.py`), urutannya penting:
   1. Tautan WhatsApp (`wa.me`, `chat.whatsapp.com`, …) → `[LINK_WA]`
   2. Undangan grup (`t.me`, `line.me/R/ti/g`, `discord.gg`, `facebook.com/groups`, …) → `[LINK_GRUP]`
   3. Email, termasuk `[at]`/`(at)`/`[dot]`/`[titik]` dan `nama @ domain` → `[EMAIL]`
   4. URL lain dipertahankan, tetapi query (`?…`) dan fragment (`#…`) dibuang.
   5. Deret angka (boleh berisi spasi/titik/strip/kurung, dan `O/o/I/l` sebagai digit bila tidak menempel ke huruf) diklasifikasi:
      - `+…` atau `62`/`0` + 9–13 digit nasional diawali `0[2-9]` → `[TELEPON]`
      - tepat 16 digit dengan kode provinsi dan tanggal lahir valid → `[NIK]`
      - 10–19 digit lain → `[REKENING]` (rekening, kartu), **kecuali** format nominal (`1.000.000`) atau didahului `Rp`/`IDR`/`$`
      - tanggal `dd-mm-yyyy` di awal deret dilewati, sisanya dipindai ulang
   6. Handle `@username` → `[AKUN]` (kecuali `@Rp5.000`, harga satuan)
3. **Nama, heuristik** (`names.py`): kata kapital (maks 4) sesudah sapaan (`Bapak/Ibu/Pak/Bu/Kak/Mas/Mbak/Bang/Dek/Teh/Uda/…`), gelar (`dr./Prof./Ir./Hj./Ustadz/…`, boleh bertumpuk), atau penanda atribusi (`a.n.`, `atas nama`, `nama:`, `CP`) → `[NAMA]`. Sesudah sapaan kekerabatan, satu kata huruf kecil juga disamarkan (`pak joko`). Sapaannya tetap terlihat.
4. **Nama, NER** (`ner.py`): `cahya/bert-base-indonesian-NER` (lokal, MIT), entitas `PER` dengan skor ≥ `NER_THRESHOLD` (0.5) → `[NAMA]`. Model diatur lewat `NER_MODEL`. Model gagal dimuat = error, tidak ada mode tanpa NER.
5. **`assert_no_pii`**: menjalankan ulang seluruh detektor regex pada hasil, ditambah pola email yang lebih longgar. Bila ada temuan, `PiiLeakError` dan submission ditolak.

## Aturan pembeda: orang vs lembaga

Lembaga dan jabatan adalah bagian dari mutasi yang dilacak ("Kementerian X" berubah menjadi "BPOM"), jadi tidak disamarkan. Aturan di `rules.py`:

| Aturan | Contoh | Hasil |
|---|---|---|
| Span yang mengandung kata lembaga (`kementerian`, `dinas`, `rs`, `universitas`, `bank`, `bpom`, `who`, …) tidak disamarkan | `RS Budi Asih`, `Kementerian Kesehatan` | tetap |
| Kata jabatan (`presiden`, `menteri`, `gubernur`, `rt`, `dokter`, …) menghentikan penangkapan nama dan dibuang dari tepi span NER | `Pak Menteri`, `Menteri Kesehatan Budi Hartanto` | `Pak Menteri`, `Menteri Kesehatan [NAMA]` |
| Akronim 2–6 huruf kapital dari NER dianggap lembaga, kecuali seluruh pesan ditulis kapital | `BPOM`, `WHO` | tetap |
| Nama pribadi pejabat tetap disamarkan; jabatannya dipertahankan | `Presiden Fulan` | `Presiden [NAMA]` |
| Handle akun selalu disamarkan, termasuk akun lembaga | `@kemenkes_ri` | `[AKUN]` |

## Hasil evaluasi

Jalankan: `cd services/nlp && uv run python -m tests.anonymizer.eval_report`. Diukur 2026-11-04, model `cahya/bert-base-indonesian-NER` di CPU.

- **Recall** = nilai PII yang tidak lagi bisa ditemukan di output / total nilai PII (nomor dicek sebagai deret digit, nama per kata).
- **Precision** = token dengan tipe benar / total token yang dihasilkan.
- **Over-masking** = potongan teks non-PII yang wajib tetap ada (`keep`) tetapi hilang.

| Set | Konfigurasi | Recall | Precision | Over-masking |
|---|---|---|---|---|
| Tuning: 68 kasus, 60 nilai PII, 71 `keep` | regex + heuristik + NER | 60/60 (1,00) | 60/60 (1,00) | 0/71 |
| | regex + heuristik saja | 57/60 (0,95) | 1,00 | 0/71 |
| **Holdout**: 24 kasus, 23 nilai PII, 16 `keep` | regex + heuristik + NER | **23/23 (1,00)** | **23/23 (1,00)** | **1/16** |
| | regex + heuristik saja | 20/23 (0,87) | 1,00 | 1/16 |

Set tuning dipakai untuk menyetel aturan, jadi angkanya optimis. Kasus `name-lowercase-two` ditambahkan di S3 setelah uji integrasi menemukan nama dua kata huruf kecil bocor separuh (`pak sutrisno [NAMA]`). Set holdout (`HOLDOUT` di `tests/anonymizer/cases.py`) ditulis sesudah penyetelan dan tidak dipakai untuk menyetel. Satu kegagalannya: `PERHATIAN!!! BAPAK BUDIMAN SETIAWAN MENIPU WARGA` → `BAPAK [NAMA] WARGA` (kata kerja kapital ikut tersamar). Kedua set kecil dan sintetis, ditulis oleh orang yang sama dengan pembuat aturan. Angka di atas **bukan jaminan** untuk pesan nyata.

## Keterbatasan yang diketahui

1. **Nama tanpa sapaan bergantung penuh pada NER.** Tanpa NER, recall turun ke 0,87–0,95. Model dilatih pada teks formal, jadi nama huruf kecil tanpa sapaan, nama panggilan, dan nama satu kata di chat santai mudah lolos.
2. **Jenis PII yang belum dideteksi:** alamat jalan (`Jl. Melati No. 5`), pelat nomor, tanggal lahir lepas, angka yang ditulis dengan kata (`nol delapan satu dua`), digit yang dipisah huruf (`0812x3456`), email dengan kata polos (`rina at contoh dot id`), dan identitas di path URL (`/profil/rina-kartika`).
3. **Over-masking:** teks yang seluruhnya kapital bisa membuat kata sesudah nama ikut tersamar. Deret 10–19 digit yang bukan nominal (nomor pesanan, daftar tahun dipisah spasi) menjadi `[REKENING]`. Ini disengaja (recall dulu), tetapi bisa menghapus angka yang relevan untuk mutasi.
4. Nama orang di dalam nama lembaga (`RS Budi Asih`) sengaja dipertahankan.
5. Model NER ±440 MB dan dimuat di CPU; muat sekali per proses (`default_recognizer` di-cache).
