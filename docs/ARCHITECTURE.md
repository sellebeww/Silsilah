# Arsitektur

## Alur

```
 Browser (form teks / unggah gambar)
    │  HTTPS, body tidak pernah dilog
    ▼
 services/nlp  POST /v1/submissions ───────────── semua di memori ──────────────┐
    │                                                                           │
    ├─ 1. OCR (jika gambar)   Tesseract ind+eng; byte gambar di-del setelahnya  │
    ├─ 2. Normalisasi         NFKC, rapikan spasi/emoji berulang                │
    ├─ 3. Anonimisasi         regex + NER → [TELEPON] [NAMA] [EMAIL] [NIK] ...  │
    │                         gagal = 422, tidak ada yang ditulis               │
    │  ═══════════ batas privasi: setelah titik ini hanya teks tersamar ═══════╡
    ├─ 4. Embedding           sentence-transformers lokal (EMBEDDING_MODEL)     │
    ├─ 5. Penempatan pohon    hash persis → kNN pgvector → duplikat/anak/baru   │
    ├─ 6. Diff                diff kata terhadap induk                          │
    └─ 7. Simpan              status = pending                                  ┘
    │
    ▼
 Supabase (Postgres + pgvector + RLS)
    │  kurator meninjau → status = published, tambah tautan fact-check resmi
    ▼
 apps/web  /pohon/[slug]  SSR, anon key, RLS: hanya published
```

## Langkah inti

1. **OCR.** Gambar dibaca ke memori (batas ukuran dan tipe MIME diperiksa), di-OCR, lalu referensinya dibuang. Tidak ada penulisan ke disk atau Supabase Storage.
2. **Normalisasi.** Unicode NFKC dan perapian whitespace. Teks hasil normalisasi adalah yang dianonimkan dan ditampilkan.
3. **Anonimisasi.** Pola regex (nomor telepon Indonesia `+62/08`, email, NIK 16 digit, nomor rekening, pelat nomor, URL dengan parameter pelacak) ditambah NER untuk nama orang. Diganti placeholder bertipe. Fail-closed: exception atau timeout = submission ditolak.
4. **Embedding.** Hanya dari teks tersamar. Prefiks sesuai model (e5: `query: `). Dimensi dari `EMBEDDING_DIM`.
5. **Penempatan.**
   - `sha256(teks tersamar ternormalisasi)` sama → laporan ulang varian yang ada (`report_count++`).
   - kNN kosinus tertinggi ≥ `PLACEMENT_SIM_DUPLICATE` → laporan ulang varian tetangga.
   - ≥ `PLACEMENT_SIM_FAMILY` → varian baru, anak dari tetangga terdekat di keluarga itu; skor kemiripan disimpan sebagai `placement_confidence`.
   - Di bawahnya → keluarga baru, varian ini menjadi akar.
   - **Varian tertua yang dilaporkan** = varian dengan `first_reported_on` terkecil dalam keluarga. Ini bukan klaim asal-usul; laporan baru bisa saja memuat teks yang beredar lebih dulu.
6. **Diff.** Diff tingkat kata (insert/delete/replace) terhadap induk, disimpan sebagai `jsonb`, deterministik.
7. **Simpan.** Varian baru berstatus `pending`; hanya `published` yang terlihat publik.

## Model data (sketsa, final di S1)

| Tabel | Kolom utama |
|---|---|
| `families` | `id`, `slug`, `title` (kurator), `status` |
| `variants` | `id`, `family_id`, `parent_id`, `text_anon`, `text_hash` unik, `embedding vector(384)`, `first_reported_on date`, `report_count`, `placement_confidence`, `diff jsonb`, `status` |
| `fact_checks` | `id`, `family_id`, `url`, `source` (daftar sumber resmi), `added_by` |
| `curators` | `user_id` (Supabase Auth), `role` |
| `takedown_requests` | `id`, `variant_id`, `reason`, `status`, `resolved_by` |

Tidak ada kolom pengirim, IP, perangkat, grup, atau lokasi. Waktu laporan disimpan per **tanggal**, bukan detik, supaya tidak bisa dicocokkan dengan aktivitas seseorang.

## Komponen dan batas tanggung jawab

| Komponen | Tanggung jawab | Tidak boleh |
|---|---|---|
| `services/nlp` | Satu-satunya yang melihat teks mentah/gambar. OCR, anonimisasi, embedding, penempatan, diff, tulis varian (service role). Rate limit di memori. | Menyimpan/melog teks mentah, gambar, atau IP |
| `supabase` | Penyimpanan data tersamar, RLS, Auth kurator, fungsi kNN | Menyimpan file gambar; memberi akses tulis ke anon |
| `apps/web` | SSR halaman pohon, UI kurator (moderasi, tautan fact-check, takedown), widget embed | Memegang service role key; memproses teks mentah |
| Kurator (manusia) | Publikasi, judul keluarga, re-parent manual, tautan fact-check resmi, takedown | Menambah tautan dari sumber di luar daftar resmi |

## RLS ringkas

- `anon`: `select` pada baris `status = 'published'` saja. Tanpa `insert/update/delete`.
- `curator` (authenticated + ada di `curators`): ubah status, judul, `parent_id`, `fact_checks`, `takedown_requests`.
- `service_role`: insert/update varian dari `services/nlp`.
