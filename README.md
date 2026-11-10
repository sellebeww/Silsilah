<div align="center">

# Silsilah

### Hoaks punya keluarga. Temukan leluhurnya.

<p>Pelacak mutasi pesan berantai: setiap laporan ditempatkan di pohon turunan varian dan sistem menunjuk varian tertua yang dilaporkan.</p>

<p><img src="https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white&labelColor=3a3f47" alt="Next.js 16"> <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white&labelColor=3a3f47" alt="React 19"> <img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white&labelColor=3a3f47" alt="TypeScript 5"> <img src="https://img.shields.io/badge/Python-NLP%20service-3776AB?logo=python&logoColor=white&labelColor=3a3f47" alt="Python NLP service"> <img src="https://img.shields.io/badge/Supabase-backend-3FCF8E?logo=supabase&logoColor=white&labelColor=3a3f47" alt="Supabase backend"> <img src="https://img.shields.io/badge/license-All%20rights%20reserved-1e3a8a?labelColor=3a3f47" alt="license All rights reserved"></p>

</div>

Untuk relawan pemeriksa fakta, jurnalis, guru literasi digital, dan peneliti disinformasi.

*English summary at the [bottom](#english-summary).*

## Masalah

Satu hoaks jarang beredar dalam satu bentuk: angkanya diganti, lembaganya ditukar, ajakannya diubah. Pemeriksa fakta lalu memeriksa versi yang sama berulang kali, dan pembaca tidak tahu versi mana yang lebih dulu dilaporkan atau apakah bantahan resmi untuk satu versi berlaku untuk versi lain.

## Cara kerja

1. **Kirim**: teks atau tangkapan layar (OCR di memori, gambar langsung dibuang).
2. **Samarkan**: nomor telepon, nama, email, NIK, dan identitas lain disamarkan *sebelum* apa pun ditulis. Gagal menyamarkan = kiriman ditolak (fail-closed).
3. **Tempatkan**: embedding menentukan keluarga dan induk di pohon, lalu kurator menyetujui (varian baru berstatus `pending`).
4. **Bandingkan**: diff kata dan kategori mutasi (angka, institusi, ajakan, tanggal, tempat, tautan) antara varian dan induknya.
5. **Tautkan**: kurator menambahkan tautan pemeriksaan fakta resmi (mis. TurnBackHoax/MAFINDO) secara manual dari daftar penerbit tepercaya.

Halaman pohon (`/keluarga/[id]`) dirender di server. Pemeriksa fakta dapat menyematkan ringkasan satu keluarga di artikel lewat widget (`/embed`).

## Arsitektur singkat

| Lapisan | Teknologi |
|---|---|
| `services/nlp` | Python 3.12, FastAPI: OCR (Tesseract `ind+eng`), anonimisasi (aturan + NER), embedding lokal (sentence-transformers), penempatan pohon, diff |
| `supabase` | Postgres + pgvector + Auth + RLS; migrasi di `supabase/migrations/` |
| `apps/web` | Next.js (App Router, TypeScript strict): UI publik, pohon, dasbor kurator, widget |

Klien tidak punya hak menulis varian. Hanya `services/nlp` (service role, lewat RPC) yang menulis; frontend membaca lewat anon key dan RLS. Detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), peta jalan: [docs/ROADMAP.md](docs/ROADMAP.md), risiko: [docs/RISKS.md](docs/RISKS.md).

## Menjalankan secara lokal

Prasyarat: Docker, [Supabase CLI](https://supabase.com/docs/guides/cli), [uv](https://docs.astral.sh/uv/), Node 22+, Tesseract (`brew install tesseract tesseract-lang` di macOS).

```bash
supabase start                      # Postgres + Auth lokal
supabase db reset                   # migrasi + seed sintetis
cp .env.example .env                # isi SUPABASE_SERVICE_ROLE_KEY dari `supabase status`
cp apps/web/.env.example apps/web/.env.local   # isi NEXT_PUBLIC_SUPABASE_ANON_KEY

docker compose up --build nlp       # layanan NLP di :8000 (FS read-only; model ~900 MB diunduh saat build)
(cd apps/web && npm install && npm run dev)    # http://localhost:3000
```

Tanpa Docker untuk NLP: `(cd services/nlp && uv sync && set -a && . ../../.env && set +a && uv run uvicorn --factory silsilah.ingest.app:create_app --no-access-log)`.

Tes dan lint:

```bash
supabase test db tests/db                                   # pgTAP: skema + RLS
(cd services/nlp && uv run pytest && uv run ruff check . && uv run mypy src)
(cd services/nlp && make eval)                              # evaluasi penempatan/diff -> docs/EVAL.md
(cd apps/web && npm test && npm run lint && npx tsc --noEmit)
python3 scripts/check_hygiene.py                            # secret dan log PII
```

Semua data seed dan fixture **sintetis dan fiktif**.

## Privasi dan etika

**Disimpan**: teks yang sudah disamarkan, hash isi, embedding, tanggal pertama kali diterima (dengan presisinya), jumlah laporan, tautan pemeriksaan fakta dari penerbit resmi.

**Tidak pernah disimpan atau dilog**: teks mentah, gambar asli, nomor pengirim, akun, grup, lokasi, IP. Rate limit memakai kunci ber-HMAC dengan garam yang diganti tiap jam, hanya di memori. Log hanya berisi ID, hash, durasi, dan kode error; CI memeriksanya otomatis.

**Batas klaim**: Silsilah hanya berkata **"varian tertua yang dilaporkan"**: varian paling awal yang *sampai ke sistem ini*. Itu bukan asal-usul, sumber asli, atau pembuat pertama; pesan serupa mungkin sudah beredar lebih dulu. Arah turunan diambil dari urutan tanggal laporan dan kemiripan isi, dan ditandai putus-putus bila tidak pasti.

**Penghapusan**: siapa pun dapat mengajukan penghapusan varian lewat `/hapus`; identitas pemohon tidak disimpan. Antrean takedown di dasbor kurator dan penghapusan permanen belum selesai (lihat ROADMAP S6).

## Keterbatasan (jujur)

- **Butuh kontributor.** Pohon baru berguna bila ada cukup laporan; di awal sebagian besar keluarga hanya punya satu atau dua varian.
- **Kualitas pengelompokan** untuk bahasa daerah, bahasa campur, dan ejaan alay masih lemah: rewrite bahasa daerah sering menjadi keluarga sendiri (terukur di [docs/EVAL.md](docs/EVAL.md) pada data sintetis; belum diuji pada data nyata). Kurator dapat memindahkan varian.
- **Anonimisasi tidak sempurna.** Presisi/recall ada di [docs/ANONYMIZATION.md](docs/ANONYMIZATION.md); pelat nomor dan alamat jalan belum dideteksi. Karena itu setiap varian ditinjau kurator sebelum terbit.
- **Tanggal diisi kontributor**, sehingga tanggal palsu bisa merebut posisi "tertua" (lihat [docs/RISKS.md](docs/RISKS.md) #8, masih terbuka).
- Rate limit hidup di memori satu proses; skala lebih dari satu worker butuh penyimpanan bersama.

## Berkontribusi

Lihat [CONTRIBUTING.md](CONTRIBUTING.md). Melaporkan kebocoran data atau celah keamanan: [SECURITY.md](SECURITY.md).

## Lisensi

Hak cipta © 2026 Vassel Goleyu. Semua hak dilindungi; kode ini belum dirilis sebagai sumber terbuka. Lihat [LICENSE](LICENSE). Izin tertulis dari pemilik diperlukan untuk menyalin, mengubah, atau mendistribusikan.

---

## English summary

**Silsilah** ("family tree" in Indonesian) tracks how chain-message hoaxes mutate. Each report is placed in a tree of variants and the system points to the **oldest *reported* variant**, never "the origin" or "the creator". It tracks message *content*, not people.

- **How it works:** submit text/screenshot → OCR in memory → PII anonymized *before anything is stored* (fail-closed) → embedding-based placement into a variant tree → curator approval → word-level diff and mutation categories → curator-added links to official fact-checks (allowlisted publishers only, e.g. TurnBackHoax/MAFINDO).
- **Stack:** Python/FastAPI NLP service, Supabase (Postgres + pgvector + RLS), Next.js frontend with an embeddable widget.
- **Privacy:** no raw text, original images, sender numbers, accounts, groups, locations, or IPs are stored or logged. All seed/test data is synthetic.
- **Honest limits:** needs contributors to be useful; clustering quality for regional languages and mixed-language text is weak (measured on synthetic data only); anonymization is imperfect (license plates and street addresses are not detected); contributor-supplied dates can be gamed.
- **Run locally:** see the commands above (`supabase start`, `docker compose up --build nlp`, `npm run dev`).
- **License:** proprietary, all rights reserved (Vassel Goleyu). Contact the owner before contributing code.
