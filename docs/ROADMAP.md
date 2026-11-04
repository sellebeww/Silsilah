# Roadmap

Kriteria selesai tiap langkah: lihat "Definition of Done" di `CLAUDE.md`.

- [x] **S0 Fondasi dokumen**: CLAUDE.md, ARCHITECTURE, ROADMAP, RISKS.

## S1 Skema DB + RLS
- [x] Migrasi di `supabase/migrations/`, ekstensi `vector`.
- [ ] `supabase init` (`config.toml`): CLI belum terpasang saat S1, jalankan sekali sebelum `supabase start`.
- [x] Tabel `families`, `variants`, `mutations`, `factcheck_links`, `trusted_publishers`, `contributors`, `takedown_requests` (tanpa kolom identitas pengirim).
- [x] Indeks HNSW kosinus pada `variants.embedding`; unik pada `body_hash`.
- [x] `match_variants` (hanya approved, hanya service role).
- [x] RLS default-deny + grant per kolom: anon baca published/approved, kontributor kirim pending, kurator/admin moderasi.
- [x] `seed.sql`: 3 keluarga sintetis, 4–5 varian, mutasi angka/institusi/ajakan/tanggal/tempat.
- [x] Tes pgTAP `tests/db/rls.test.sql` (21 assertion).

## S2 Anonimisasi
- [x] Scaffold `services/nlp` (uv, ruff, mypy strict, pytest).
- [x] Normalisasi teks (NFKC, zero-width, digit Unicode, keycap) dan `normalize_for_hash`.
- [x] Regex: telepon, email (termasuk tersamar), NIK, rekening/kartu, handle, tautan WA/grup; query URL dibuang.
- [x] Nama: heuristik sapaan/gelar + NER `cahya/bert-base-indonesian-NER`; lembaga dan jabatan dikecualikan.
- [x] Placeholder bertipe; fail-closed (NER gagal/tidak ada, teks > 10.000 karakter, `assert_no_pii`).
- [x] 67 kasus sintetis + 24 holdout; precision/recall di `docs/ANONYMIZATION.md`.
- [x] Modul tanpa logging; error tidak memuat teks (diuji).
- [ ] Pelat nomor dan alamat jalan: belum dideteksi (lihat keterbatasan di ANONYMIZATION.md).
- [ ] Timeout per submission: diterapkan di S3 pada level endpoint.

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
