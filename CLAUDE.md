# Silsilah

> Hoaks punya keluarga. Temukan leluhurnya.

Silsilah melacak mutasi pesan berantai (hoaks). Setiap laporan ditempatkan di pohon turunan varian, dan sistem menunjuk **varian tertua yang dilaporkan**. Yang dilacak adalah ISI pesan, bukan akun penyebar.

Pengguna: relawan pemeriksa fakta, jurnalis, guru literasi digital, peneliti disinformasi.

## Prinsip (tidak boleh dilanggar)

1. **Privasi dulu.** Nomor telepon, nama orang, email, NIK, dan identitas lain disamarkan SEBELUM apa pun ditulis ke database, log, atau penyimpanan. Teks mentah dan gambar asli tidak pernah disimpan. Anonimisasi gagal = submission ditolak (fail-closed).
2. **Klaim jujur.** Selalu "varian tertua yang dilaporkan", tidak pernah "asal-usul", "sumber asli", atau "pembuat pertama". Berlaku di UI, API, dokumen, dan nama variabel.
3. **Tidak melacak orang.** Tidak menyimpan akun, nomor pengirim, grup, lokasi, atau IP.
4. **Tautan pemeriksaan fakta hanya ke sumber resmi** (mis. TurnBackHoax/MAFINDO) yang dimasukkan kurator secara manual. Tidak ada scraping tanpa izin.
5. **Data uji dan seed 100% sintetis dan fiktif.** Jangan memakai hoaks nyata yang menyebut orang atau lembaga sungguhan sebagai korban.

Jika sebuah tugas bertentangan dengan prinsip di atas, berhenti dan tanyakan.

## Stack (tetap)

| Lapisan | Teknologi |
|---|---|
| Layanan NLP | Python 3.12, FastAPI, uv, pytest, ruff, mypy (strict) |
| Database | Supabase: Postgres + pgvector + Auth + RLS. Migrasi SQL di `supabase/migrations/` |
| Frontend | Next.js (App Router, TypeScript strict). Halaman pohon dirender server-side untuk SEO |
| Embedding | sentence-transformers lokal (default `paraphrase-multilingual-MiniLM-L12-v2`, 384 dim). Diatur lewat env |
| OCR | Tesseract `ind+eng`, di memori; byte gambar dibuang setelah teks diambil |

## Struktur folder

```
.
├── CLAUDE.md
├── docs/                    ARCHITECTURE, ROADMAP, RISKS
├── supabase/
│   ├── migrations/          SQL berurutan (skema, RLS, fungsi)
│   └── seed.sql             data sintetis saja
├── tests/db/                tes pgTAP untuk skema + RLS
├── services/nlp/            FastAPI: OCR, anonimisasi, embedding, penempatan, diff
│   ├── src/silsilah/
│   └── tests/
└── apps/web/                Next.js: UI publik, halaman pohon, dasbor kurator, widget
```

Folder di atas dibuat bertahap sesuai `docs/ROADMAP.md`; belum semuanya ada.

## Perintah

```bash
# Setup
supabase start                              # Postgres lokal + Auth
supabase db reset                           # terapkan migrasi + seed sintetis
(cd services/nlp && uv sync)                # model NER + embedding (~900 MB) terunduh saat pertama dipakai
cp .env.example .env                        # isi SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY
(cd apps/web && npm install)
brew install tesseract tesseract-lang       # macOS; butuh paket bahasa ind

# Test
supabase test db tests/db                   # tes RLS (pgTAP)
(cd services/nlp && uv run pytest)
(cd apps/web && npm test)

# Lint & tipe
(cd services/nlp && uv run ruff check . && uv run ruff format --check . && uv run mypy src)
(cd apps/web && npm run lint && npx tsc --noEmit)

# Run
(cd services/nlp && set -a && . ../../.env && set +a && uv run uvicorn --factory silsilah.ingest.app:create_app --reload --no-access-log)
docker compose up --build nlp               # image dengan Tesseract + model; FS read-only
docker build --target test services/nlp     # tes di dalam image, termasuk OCR Tesseract asli
(cd apps/web && npm run dev)
```

### Env penting

| Variabel | Default | Catatan |
|---|---|---|
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Ganti model = migrasi re-embed; bandingkan dulu dengan `scripts/compare_embeddings.py` |
| `EMBEDDING_PREFIX` | kosong | Isi `query: ` untuk model keluarga e5 |
| `EMBEDDING_DIM` | `384` | Harus sama dengan kolom `vector(n)` |
| `OCR_LANGS` | `ind+eng` | |
| `NER_MODEL` | `cahya/bert-base-indonesian-NER` | Model gagal dimuat = anonimisasi ditolak |
| `NER_THRESHOLD` | `0.5` | Turunkan untuk recall lebih tinggi |
| `PLACEMENT_SIM_DUPLICATE` | `0.95` | ≥ ini: laporan ulang varian yang sama |
| `PLACEMENT_SIM_FAMILY` | `0.80` | < ini: keluarga baru. Wajib dikalibrasi ulang di S4: dengan MiniLM, kemiripan intra-keluarga di seed serendah 0,50 |
| `RATE_LIMIT_PER_HOUR` | `20` | Per IP atau per kontributor (JWT); kunci di-HMAC, tidak disimpan |
| `CORS_ORIGINS` | `http://localhost:3000` | Dipisah koma |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | | Service role HANYA di `services/nlp`, tidak pernah di frontend |

Rahasia di `.env` (tidak di-commit). Sediakan `.env.example`.

## Konvensi

- **Commit kecil**, satu perubahan logis per commit, format Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- **Tipe ketat**: mypy strict dan TypeScript `strict: true`. Tidak ada `Any`/`any` tanpa komentar alasan.
- **Tes untuk semua logika inti**: anonimisasi, penempatan pohon, diff, RLS. Bug fix datang bersama tes regresi.
- Anonimisasi diuji dengan fixture PII sintetis; tiap pola PII baru = kasus uji baru.
- Log hanya berisi ID, hash, durasi, dan kode error. Tidak pernah teks pesan (mentah maupun tersamar) atau body request.
- Teks UI dalam Bahasa Indonesia. Kode dan identifier dalam bahasa Inggris.
- Varian hanya ditulis oleh `services/nlp` (service role, lewat RPC `insert_pending_variant`); klien tidak punya hak insert. Frontend membaca lewat anon key + RLS. Setiap tabel baru: RLS aktif + revoke hak bawaan anon/authenticated.

## Definition of Done

Berlaku untuk setiap langkah:

- [ ] Semua tes, lint, dan cek tipe hijau.
- [ ] Tidak ada PII mentah atau data non-sintetis di kode, fixture, seed, atau log.
- [ ] Istilah "tertua yang dilaporkan" konsisten.
- [ ] `docs/` diperbarui bila arsitektur atau perilaku berubah; checklist ROADMAP dicentang.
- [ ] Di-commit dalam commit kecil.

Kriteria khusus per langkah:

| Langkah | Selesai bila |
|---|---|
| S1 Skema + RLS | `supabase db reset` bersih; tes pgTAP membuktikan anon hanya bisa membaca data `published` dan tidak bisa menulis |
| S2 Anonimisasi | Seluruh fixture PII sintetis tersamar; anonymizer error = submission ditolak; tidak ada jalur tulis yang melewatinya |
| S3 Ingest | Teks dan gambar masuk sampai baris varian ber-embedding; tes membuktikan byte gambar dan teks mentah tidak tersimpan/terlog |
| S4 Pohon + diff | Tes penempatan (duplikat, anak, keluarga baru) dan diff deterministik lulus; varian tertua yang dilaporkan dihitung benar |
| S5 API + UI | Halaman pohon SSR tampil dari seed sintetis, punya metadata SEO, dan lolos cek aksesibilitas dasar |
| S6 Hardening | Tautan fact-check hanya via kurator; widget berfungsi; rate limit + alur takedown ada; README lengkap |
