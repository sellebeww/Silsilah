# Berkontribusi ke Silsilah

Terima kasih sudah mau membantu. Baca dulu [CLAUDE.md](CLAUDE.md) (prinsip dan konvensi) dan [README.md](README.md).

## Sebelum mengirim kode

Lisensi proyek saat ini tertutup (lihat [LICENSE](LICENSE)). **Buka isu dan tunggu persetujuan pemilik** sebelum mengirim pull request; ketentuan hak atas kontribusi ditetapkan pemilik.

Cara membantu tanpa kode: melapor pesan berantai lewat situs (setelah kiriman dianonimkan, kurator menyetujui), menjadi kurator, atau mengajukan penerbit pemeriksa fakta yang layak masuk daftar tepercaya.

## Prinsip yang tidak boleh dilanggar

1. **Privasi dulu.** Data pribadi disamarkan sebelum ditulis ke mana pun; anonimisasi gagal = ditolak.
2. **Klaim jujur.** Selalu "varian tertua yang dilaporkan". Jangan menulis "asal-usul", "sumber asli", atau "pembuat pertama" di UI, API, dokumen, maupun nama variabel.
3. **Tidak melacak orang.** Tanpa akun, nomor pengirim, grup, lokasi, atau IP.
4. **Tautan fact-check hanya ke sumber resmi** yang dimasukkan kurator. Tanpa scraping tanpa izin.
5. **Data uji 100% sintetis dan fiktif.** Jangan memakai hoaks nyata yang menyebut orang atau lembaga sungguhan.

Jika perubahan Anda bertentangan dengan salah satunya, berhenti dan tanyakan di isu.

## Alur kerja

- Satu perubahan logis per commit, format Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Tipe ketat: mypy strict, TypeScript `strict`. Tidak ada `Any`/`any` tanpa komentar alasan.
- Tes untuk logika inti (anonimisasi, penempatan, diff, RLS). Bug fix datang dengan tes regresi. Pola PII baru = kasus uji baru dengan fixture sintetis.
- Log hanya berisi ID, hash, durasi, dan kode error. Tidak pernah teks pesan atau body request.
- Teks UI Bahasa Indonesia; kode dan identifier Bahasa Inggris.
- Tabel baru: RLS aktif dan hak bawaan `anon`/`authenticated` dicabut. Varian hanya ditulis `services/nlp`.

## Sebelum mengirim

```bash
supabase test db tests/db
(cd services/nlp && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy src)
(cd apps/web && npm test && npm run lint && npx tsc --noEmit)
python3 scripts/check_hygiene.py
```

CI menjalankan semuanya, ditambah `make eval` (hanya melaporkan) dan audit dependensi.
