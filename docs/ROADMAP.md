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
- [x] Timeout per submission: `SUBMIT_TIMEOUT_S` di level endpoint (S3).

## S3 Ingest (teks / OCR / embedding)
- [x] `POST /submit/text` dan `POST /submit/image` (≤ 5 MB, JPEG/PNG/WebP dicek dari isi).
- [x] OCR Tesseract `ind+eng` lewat stdin/stdout; gambar dibuang setelah teks diambil.
- [x] `EmbeddingProvider` lokal (MiniLM, L2, batch), dimuat sekali; tolak jika dimensi ≠ `EMBEDDING_DIM`.
- [x] Duplikat persis via `body_hash` (report_count naik, tanggal lebih awal diperbarui) lalu simpan `pending` lewat RPC service role.
- [x] Validasi, rate limit tanpa IP mentah, CORS terbatas, timeout per kiriman.
- [x] Tes: pipeline dengan DB tiruan, tidak ada teks mentah/gambar di disk atau log (audit hook), duplikat, validasi; pgTAP fungsi ingest.
- [x] Insert varian langsung dari klien dicabut (semua lewat anonimisasi).
- [ ] Dockerfile + docker-compose ditulis, tetapi build image dan tes OCR Tesseract asli BELUM terverifikasi (disk penuh saat S3).

## S4 Pohon + diff
- [x] Penempatan saat kurator menyetujui (`POST /moderation/variants/{id}/approve`): keluarga via centroid, induk, `edge_confidence`, `alt_parent_ids`, `merge_suggestion` (tanpa gabung otomatis).
- [x] Pohon keluarga dihitung ulang penuh tiap penempatan: deterministik, idempoten, rebalance otomatis.
- [x] `is_oldest_reported` + ketidakpastian (`date_precision`, `report_count`) di respons.
- [x] Diff kata + kategori dari `keywords.yaml`, baris `mutations`, ringkasan satu baris.
- [x] Dataset sintetis 8 keluarga + `make eval`; ambang dari sapuan grid (`docs/EVAL.md`).
- [x] Tes: idempotensi, rebalance, ambiguitas, tanggal tidak presisi, keluarga yang hendak bergabung.
- [ ] Migrasi `20261104000500_phylogeny.sql` + tes pgTAP ditulis, BELUM dijalankan (Docker tidak hidup, disk penuh).
- [ ] Re-parent dan gabung keluarga manual oleh kurator (S5, UI kurator).

## S5 API + UI pohon
- [ ] API baca: keluarga, pohon, varian, diff.
- [ ] Next.js `/pohon/[slug]` SSR, metadata SEO, JSON-LD.
- [ ] Visualisasi pohon + panel diff, label "tertua yang dilaporkan".
- [ ] Form submit (teks/gambar) dengan pemberitahuan privasi.
- [ ] Dasbor kurator: antrian `pending`, publikasi, judul keluarga.
- [ ] Cek aksesibilitas dasar (keyboard, kontras, alt text).

## S6 Fact-check link + widget + hardening + README
- [x] Tautan fact-check hanya dari allowlist domain: constraint DB + penyaringan ulang saat render (`trustedLinks`); halaman keluarga menampilkan "Hasil pemeriksaan fakta resmi" dengan nama penerbit, judul, label putusan, `rel="noopener noreferrer nofollow"`.
- [x] Widget embed: `/embed/[id]` (route group terpisah, tanpa header/footer), `public/embed.js` (iframe tersandbox, tinggi otomatis), `/embed` berisi kode salin-tempel.
- [x] Rate limit tanpa menyimpan IP; batas ukuran body teks (413/411) dan gambar.
- [x] Header keamanan web (CSP, HSTS, Referrer-Policy, frame-ancestors per route) dan API; `scripts/check_hygiene.py` (secret, log PII) di CI; audit dependensi di CI.
- [x] CI GitHub Actions: higiene, ruff/mypy/pytest, eslint/tsc/vitest/build, pgTAP, `make eval` (hanya melaporkan), audit.
- [x] README (Indonesia + ringkasan Inggris), CONTRIBUTING, SECURITY.
- [ ] Alur takedown: formulir ada (`/hapus`); antrean di dasbor kurator dan penghapusan permanen BELUM ada.
- [ ] CI belum pernah dijalankan; `package-lock.json` belum memuat devDependencies (regenerasi online lalu ganti `npm install` dengan `npm ci` di CI).
- [ ] Belum terverifikasi di lingkungan ini: tes web (vitest/eslint/tsc/build/e2e), pgTAP (migrasi 000500 dan 000600), tes anonimisasi (cache model NER tidak lengkap). Lihat laporan akhir S6.
