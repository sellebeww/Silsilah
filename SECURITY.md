# Keamanan dan kebocoran data

## Melaporkan celah atau kebocoran data

**Jangan** membuka isu publik untuk celah keamanan atau data pribadi yang bocor, dan **jangan menempelkan data pribadi** (nomor telepon, nama, NIK, email, tangkapan layar) di laporan. Cukup sebut ID varian atau URL halaman.

Gunakan salah satu:

1. **GitHub → tab Security → "Report a vulnerability"** (laporan privat ke pemilik repo).
2. Kontak pemilik: _belum diisi; pemilik perlu menambahkan alamat email khusus keamanan di sini sebelum rilis publik_.

Yang kami anggap kebocoran: data pribadi yang lolos anonimisasi dan tampil di halaman publik atau API; teks mentah atau gambar asli yang tersimpan; IP atau identitas pengirim yang tercatat; akses tulis tak sah (mis. anon menulis varian); tautan fact-check ke domain di luar daftar penerbit tepercaya.

## Jika data Anda muncul di Silsilah

Ajukan penghapusan varian lewat halaman **/hapus** (identitas pemohon tidak disimpan). Kurator meninjau setiap permintaan. Catatan: antrean takedown di dasbor kurator dan penghapusan permanen belum selesai (lihat S6 di [docs/ROADMAP.md](docs/ROADMAP.md)); sampai itu ada, penarikan dilakukan manual oleh pemilik basis data.

## Yang kami lakukan

- Triase laporan secepatnya; varian yang bocor segera dicabut dari publikasi (`published` → ditarik) sebelum diperbaiki.
- Pola yang lolos dijadikan kasus uji baru di fixture anonimisasi sintetis.
- Kami tidak menjanjikan tenggat tetap karena proyek ini dijalankan sukarela.

## Pertahanan yang ada

Anonimisasi fail-closed sebelum penyimpanan; RLS default-deny (diuji dengan pgTAP); service role hanya di `services/nlp`; rate limit tanpa menyimpan IP; header CSP/HSTS/Referrer-Policy; widget disematkan dalam iframe tersandbox; pemeriksaan otomatis di CI terhadap secret dan log yang memuat data pesan; audit dependensi di CI.
