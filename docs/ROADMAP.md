# Roadmap

Kriteria selesai tiap langkah: lihat "Definition of Done" di `CLAUDE.md`.

- [x] **S0 Fondasi dokumen**: CLAUDE.md, ARCHITECTURE, ROADMAP, RISKS.

## S1 Skema DB + RLS
- [ ] Inisialisasi `supabase/`, aktifkan ekstensi `vector`.
- [ ] Migrasi tabel `families`, `variants`, `fact_checks`, `curators`, `takedown_requests` (tanpa kolom identitas pengirim).
- [ ] Indeks HNSW kosinus pada `variants.embedding`; unik pada `text_hash`.
- [ ] Fungsi SQL kNN (`match_variants`) yang hanya bisa dipanggil service role.
- [ ] Kebijakan RLS: anon baca `published`, kurator moderasi, service role tulis.
- [ ] `seed.sql` dengan 2–3 keluarga hoaks sintetis fiktif.
- [ ] Tes pgTAP untuk setiap kebijakan RLS.

## S2 Anonimisasi
- [ ] Scaffold `services/nlp` (uv, ruff, mypy strict, pytest).
- [ ] Normalisasi teks (NFKC, whitespace).
- [ ] Regex: telepon Indonesia, email, NIK, rekening, pelat nomor, URL pelacak.
- [ ] NER nama orang dengan fallback aman.
- [ ] Placeholder bertipe; fail-closed bila error/timeout.
- [ ] Fixture PII sintetis + tes, termasuk kasus campur bahasa daerah dan ejaan alay.
- [ ] Filter log yang menolak field teks.

## S3 Ingest (teks / OCR / embedding)
- [ ] `POST /v1/submissions` untuk teks dan gambar (batas ukuran, tipe MIME).
- [ ] OCR Tesseract `ind+eng` di memori; byte gambar dibuang.
- [ ] Loader embedding dari env; tolak jika dimensi ≠ `EMBEDDING_DIM`.
- [ ] Tulis varian `pending` lewat service role.
- [ ] Tes: tidak ada teks mentah/gambar di DB, disk, atau log.

## S4 Pohon + diff
- [ ] Penempatan: hash persis → duplikat → anak → keluarga baru, ambang dari env.
- [ ] Simpan `placement_confidence`; tandai penempatan ragu untuk kurator.
- [ ] Hitung varian tertua yang dilaporkan per keluarga.
- [ ] Diff kata deterministik terhadap induk.
- [ ] Re-parent manual oleh kurator dengan validasi anti-siklus.
- [ ] Set evaluasi sintetis kecil untuk mengukur kualitas clustering.

## S5 API + UI pohon
- [ ] API baca: keluarga, pohon, varian, diff.
- [ ] Next.js `/pohon/[slug]` SSR, metadata SEO, JSON-LD.
- [ ] Visualisasi pohon + panel diff, label "tertua yang dilaporkan".
- [ ] Form submit (teks/gambar) dengan pemberitahuan privasi.
- [ ] Dasbor kurator: antrian `pending`, publikasi, judul keluarga.
- [ ] Cek aksesibilitas dasar (keyboard, kontras, alt text).

## S6 Fact-check link + widget + hardening + README
- [ ] Kurator menambah tautan fact-check dari daftar sumber resmi (allowlist domain).
- [ ] Widget embed ringan (iframe) untuk satu keluarga.
- [ ] Rate limit tanpa menyimpan IP; batas ukuran body.
- [ ] Alur takedown: formulir, antrian kurator, penghapusan permanen.
- [ ] Header keamanan, CSP, audit dependensi.
- [ ] README: tujuan, batas klaim, cara menjalankan, kebijakan privasi.
