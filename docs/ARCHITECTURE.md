# Arsitektur

## Alur

```
 Browser (form teks / unggah gambar)
    │  HTTPS, body tidak pernah dilog
    ▼
 services/nlp  POST /submit/text | /submit/image ─ semua di memori ─────────────┐
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
3. **Anonimisasi** (rinci di `ANONYMIZATION.md`). Pola regex (nomor telepon Indonesia `+62/08`, email, NIK 16 digit, nomor rekening, pelat nomor, URL dengan parameter pelacak) ditambah NER untuk nama orang. Diganti placeholder bertipe. Fail-closed: exception atau timeout = submission ditolak.
4. **Embedding.** Hanya dari teks tersamar, `paraphrase-multilingual-MiniLM-L12-v2` (384 dim, L2-normalized), dimuat sekali saat startup. Dipilih dengan `services/nlp/scripts/compare_embeddings.py`: pada seed, kemiripan antar-keluarga rata-rata 0,17 (e5-small: 0,83). Batas: input dipotong di 128 token. Duplikat persis (hash sama) tidak di-embed ulang.
5. **Penempatan.**
   - `sha256(teks tersamar ternormalisasi)` sama → laporan ulang varian yang ada (`report_count++`).
   - kNN kosinus tertinggi ≥ `PLACEMENT_SIM_DUPLICATE` → laporan ulang varian tetangga.
   - ≥ `PLACEMENT_SIM_FAMILY` → varian baru, anak dari tetangga terdekat di keluarga itu; skor kemiripan disimpan sebagai `placement_confidence`.
   - Di bawahnya → keluarga baru, varian ini menjadi akar.
   - **Varian tertua yang dilaporkan** = varian dengan `first_reported_on` terkecil dalam keluarga. Ini bukan klaim asal-usul; laporan baru bisa saja memuat teks yang beredar lebih dulu.
6. **Diff.** Diff tingkat kata (insert/delete/replace) terhadap induk, disimpan sebagai `jsonb`, deterministik.
7. **Simpan.** Varian baru berstatus `pending`; hanya `published` yang terlihat publik.

## Model data (S1, lihat `supabase/migrations/`)

| Tabel | Kolom utama |
|---|---|
| `families` | `id`, `title` netral, `status` pending/published/hidden |
| `variants` | `id`, `family_id` (null = belum ditempatkan), `parent_id`, `body_anonymized`, `body_hash` unik, `embedding vector(384)`, `language_hint`, `first_seen_reported_at` + `date_precision`, `submitted_at date`, `edge_similarity`, `is_oldest_reported`, `report_count`, `moderation_status` |
| `mutations` | `variant_id`, `parent_variant_id`, `category`, `before_text`, `after_text`, `position_hint` |
| `factcheck_links` | `family_id`, `url` https, `publisher` → `trusted_publishers.domain`, `title`, `verdict_label`, `added_by` |
| `contributors` | `id` = `auth.uid()`, `role` contributor/curator/admin (dibuat otomatis saat daftar) |
| `takedown_requests` | `variant_id`, `reason`, `status` (tanpa identitas pemohon) |

Tidak ada kolom pengirim, IP, perangkat, grup, atau lokasi. Varian juga tidak menyimpan akun kontributornya. Tanggal disimpan per hari, bukan jam. `first_seen_reported_at` adalah perkiraan kontributor; `submitted_at` diisi server. Constraint DB menolak pola PII yang jelas (email, telepon, NIK) sebagai jaring pengaman terakhir.

## Komponen dan batas tanggung jawab

| Komponen | Tanggung jawab | Tidak boleh |
|---|---|---|
| `services/nlp` | Satu-satunya yang melihat teks mentah/gambar. OCR, anonimisasi, embedding, penempatan, diff, tulis varian (service role). Rate limit di memori. | Menyimpan/melog teks mentah, gambar, atau IP |
| `supabase` | Penyimpanan data tersamar, RLS, Auth kurator, fungsi kNN | Menyimpan file gambar; memberi akses tulis ke anon |
| `apps/web` | SSR halaman pohon, UI kurator (moderasi, tautan fact-check, takedown), widget embed | Memegang service role key; memproses teks mentah |
| Kurator (manusia) | Publikasi, judul keluarga, re-parent manual, tautan fact-check resmi, takedown | Menambah tautan dari sumber di luar daftar resmi |

## RLS ringkas

Default deny: hak bawaan Supabase dicabut, lalu diberi ulang per tabel/kolom.

- `anon`: `select` keluarga `published`, varian `approved` di keluarga itu, mutasi yang anak dan induknya terlihat, tautan fact-check keluarga terlihat. Tanpa tulis, tanpa `match_variants`.
- `contributor`: `insert` takedown saja. Tidak bisa insert/ubah/hapus varian dan tidak bisa membaca pending.
- `curator`/`admin`: moderasi varian dan keluarga, kelola `mutations`, `factcheck_links`, `trusted_publishers`, takedown. Hanya `admin` yang mengubah peran.
- `service_role` (`services/nlp`): melewati RLS; satu-satunya pemanggil `match_variants`.

Sejak S3 (`20261104000400_ingest.sql`) insert varian dari klien dicabut: semua kiriman wajib lewat `services/nlp` agar dianonimkan dulu. Duplikat persis ditangani atomik oleh `register_duplicate_report` / `insert_pending_variant` (service role saja).

## Ingest (S3)

- `POST /submit/text` JSON `{text, first_seen_date, date_precision}`; `POST /submit/image` multipart (`image` JPEG/PNG/WebP ≤ 5 MB + field tanggal). 201 = varian baru, 200 = duplikat.
- Validasi: teks 20–5000 karakter, tanggal ≤ hari ini (WIB), tanggal perkiraan disimpan di awal bulan/tahun, isi gambar dicek dengan Pillow (bukan ekstensi), batas piksel anti decompression bomb.
- Gambar tidak menyentuh disk: Content-Length dicek sebelum parsing, `spool_max_size` Starlette dinaikkan, Tesseract lewat stdin/stdout. Diuji dengan audit hook Python.
- Rate limit per IP atau per kontributor (JWT Supabase terverifikasi), kunci di-HMAC dengan garam yang diganti tiap jam. Handler validasi tidak menggemakan input; access log uvicorn dimatikan (memuat IP).
- Kontainer berjalan read-only dengan `/tmp` di RAM; model diunduh saat build, runtime offline.
