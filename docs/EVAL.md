# Evaluasi penempatan pohon dan diff mutasi (S4)

Jalankan: `cd services/nlp && make eval`. Diukur 2026-11-04 dengan `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` di CPU.

## Dataset (`services/nlp/tests/data/phylogeny/`, semua sintetis dan fiktif)

| Set | Keluarga (varian) | Pengganggu | Peran |
|---|---|---|---|
| `tune.yaml` | 3 (7, 6, 7) | 2 | Sapuan ambang dan penyetelan aturan |
| `holdout.yaml` | 3 (7, 6, 6) | 2 | **Terkontaminasi**: kegagalannya memicu perbaikan (lihat bawah) |
| `holdout2.yaml` | 2 (7, 6) | 1 | **Bersih**: ditulis setelah semuanya dikunci, dijalankan sekali |

Setiap keluarga punya pohon kebenaran dan memuat: akar yang dilaporkan setelah turunannya, tanggal tidak presisi (bulan/tahun), bahasa Jawa/Sunda (rewrite), singkatan chat dan typo, serta urutan kalimat yang dibalik. Varian diproses satu per satu sesuai urutan laporan memakai `PlacementService` yang sama dengan produksi (repo di memori).

**Metrik**
- **F1 keluarga**: pairwise F1 atas pasangan varian (sekeluarga atau tidak). F0.5 juga dilaporkan.
- **Akurasi induk**: varian non-akar yang induk prediksinya sama dengan induk sebenarnya.
- **Akurasi tertua**: keluarga (≥ 2 varian) yang akar sebenarnya ditandai `is_oldest_reported`.
- **Kategori diff**: dihitung pada tepi sebenarnya (induk asli → anak), agar terpisah dari kesalahan memilih induk. Varian typo (`skip`) tidak dinilai; rewrite dinilai dari terdeteksinya sebagai rewrite.

## Pemilihan ambang (sapuan grid pada set tuning)

Skor = rata-rata (F0.5 keluarga, akurasi induk, akurasi tertua). F0.5 dipakai karena salah-gabung keluarga lebih merusak daripada keluarga terpecah: salah-gabung mencemari klaim "tertua yang dilaporkan", sedangkan keluarga terpecah bisa digabung kurator. Bila skor seri, dipilih ambang yang lebih tinggi (konservatif).

| T_family (T_edge 0,85) | 0,40–0,45 | **0,50–0,60** | 0,65–0,75 | 0,80 | 0,85 | 0,90 |
|---|---|---|---|---|---|---|
| F1 keluarga | 0,942 | **1,000** | 0,944 | 0,893 | 0,761 | 0,643 |
| akurasi induk | 0,882 | **0,882** | 0,882 | 0,824 | 0,765 | 0,706 |

| T_edge (T_family 0,60) | 0,50–0,85 | 0,90 | 0,95 |
|---|---|---|---|
| akurasi induk | **0,882** | 0,824 | 0,706 |

**Terpilih: `PLACEMENT_SIM_FAMILY=0.60`, `PLACEMENT_SIM_EDGE=0.85`.** Tebakan awal 0,80 untuk T_family akan menghasilkan F1 0,893. T_edge datar di 0,50–0,85, jadi pada data ini nilainya praktis tidak teruji (lihat kelemahan).

## Hasil

| Set | Varian | F1 keluarga | F0.5 | Akurasi induk | Akurasi tertua | Kategori diff | Rewrite terdeteksi |
|---|---|---|---|---|---|---|---|
| tuning | 22 | 1,000 | 1,000 | 15/17 (0,882) | 3/3 | 15/15 | 2/2 |
| holdout (terkontaminasi) | 21 | 0,948 | 0,979 | 13/16 (0,812) | 2/3 | 13/13 | 1/1 |
| **holdout2 (bersih)** | 14 | **0,909** | **0,962** | **9/11 (0,818)** | **2/2** | **10/10** | **1/1** |

Presisi kategori diff sama dengan akurasinya di ketiga set: tidak ada mutasi berlebih pada tepi sebenarnya. Tidak ada saran gabung yang muncul di ketiga set.

## Kasus gagal

**Tuning**
- `T1e` (rewrite bahasa Jawa): induk benar `T1b`, prediksi akar `T1a` dengan confidence `low`.
- `T2e` (rewrite bahasa Sunda): induk benar `T2d`, prediksi akar `T2a` dengan confidence `low`.

**Holdout (terkontaminasi)**
- Keluarga H2 terpecah: rewrite Jawa `H2e` menjadi keluarga sendiri.
- `H1e` (lembaga diganti seluruhnya): induk benar `H1b`, prediksi akar `H1a` (`low`). Kemiripannya di bawah T_edge 0,85.
- `H3f` (singkatan chat, tanggal hanya "Agustus 2026"): menjadi akar keluarga sendiri, sehingga tertua H3 salah.

**Holdout2 (bersih)**
- Keluarga B1 terpecah: rewrite Sunda `B1f` menjadi keluarga sendiri. Tanggalnya "Juni 2026" (paling awal di B1), jadi bila bergabung pun ia akan keliru menjadi akar.
- `B2e` (singkatan chat): induk benar `B2d`, prediksi akar `B2a` dengan confidence `low`.

## Analisis

1. **Rewrite bahasa daerah adalah titik lemah utama.** MiniLM menilai teks santai/bahasa daerah mirip karena *gaya*-nya, bukan isinya. Contoh: rewrite Jawa tentang badai lebih mirip (0,73) dengan pesan jam malam bergaya chat daripada dengan keluarganya sendiri (0,49). Single-linkage awalnya merantai tiga keluarga holdout menjadi satu. Centroid linkage memutus rantai itu, tetapi rewrite kini cenderung menjadi keluarga sendiri. Mitigasi berikutnya: model embedding yang lebih kuat lintas bahasa daerah, atau saran gabung untuk kurator berdasarkan kemiripan kandidat di bawah ambang.
2. **Embedding nyaris buta terhadap angka dan nama.** Induk dan kakek sering seri, dan aturan "pilih yang lebih awal" lalu memilih kakek. Pemutus seri dengan kemiripan token (`lexical_similarity`) menghilangkan kegagalan "kakek" di set tuning (`T1g`, `T2c`, `T3e`). Akurasi induk tuning naik dari 0,706 ke 0,882, tetapi kenaikan ini gabungan beberapa perubahan sekaligus dan tidak diukur terpisah.
3. **Tanggal tidak presisi bisa merebut posisi akar.** Tanggal dibandingkan dari awal periodenya (toleransi `date_precision`). Varian "Agustus 2026" otomatis lebih awal dari 10 Agustus. Ini sesuai definisi "tertua yang dilaporkan", tetapi UI wajib menampilkan presisi dan jumlah laporan di sebelah label tertua; endpoint persetujuan sudah mengembalikannya.
4. **Diff** 38/38 di semua set pada tepi sebenarnya, setelah dua perbaikan bug yang ditemukan oleh holdout pertama: nominal `25.000.000` terbaca sebagai tanggal, dan "tanggal 20 → 25 Juli" tidak dikenali tanpa konteks. Daftar kata kunci di `phylogeny/keywords.yaml` jelas belum lengkap; perubahan pada nama lembaga tanpa kata pembuka (mis. "Korlantas") akan jatuh ke `other`.

## Kejujuran tentang angka

- Set tuning dipakai untuk menyetel aturan **dan** ambang, jadi angkanya optimis.
- Holdout pertama dijalankan sekali, lalu kegagalannya memicu: perbaikan regex tanggal, konteks tanggal, centroid linkage, ekspansi singkatan, pemutus seri leksikal, dan kriteria F0.5. Karena itu ia dilaporkan sebagai **terkontaminasi**.
- Holdout2 ditulis sesudah semua itu dan dijalankan **sekali** tanpa penyetelan lanjutan. Ini angka yang paling jujur, tetapi hanya 14 varian dari 2 keluarga. Interval ketidakpastiannya lebar; anggap sebagai pemeriksaan arah, bukan jaminan kualitas.
- Semua teks ditulis oleh pihak yang sama yang merancang aturannya. Pesan berantai nyata lebih beragam.
