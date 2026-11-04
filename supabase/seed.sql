-- Data SINTETIS untuk pengembangan. Semua lembaga, tempat, dan penyakit di sini fiktif.
-- body_hash = sha256 teks apa adanya; S3 akan menghitung ulang dengan normalisasi sebenarnya.
-- embedding sengaja null; diisi saat re-embed di S3.

insert into public.trusted_publishers (domain, name) values
  ('turnbackhoax.id', 'TurnBackHoax (MAFINDO)'),
  ('cekfakta.example', 'Pemeriksa Fakta Contoh (sintetis)');

insert into public.families (id, title, status) values
  ('f000000a-0000-0000-0000-000000000000', 'Klaim bantuan tunai dari lembaga fiktif', 'published'),
  ('f000000b-0000-0000-0000-000000000000', 'Klaim air garam hangat mencegah flu', 'published'),
  ('f000000c-0000-0000-0000-000000000000', 'Klaim penutupan ATM serentak', 'pending');

insert into public.variants (
  id, family_id, parent_id, body_anonymized, body_hash, language_hint,
  first_seen_reported_at, date_precision, submitted_at, edge_similarity,
  is_oldest_reported, report_count, moderation_status
)
select v.id::uuid, v.family_id::uuid, v.parent_id::uuid, v.body,
       encode(sha256(convert_to(v.body, 'UTF8')), 'hex'), 'id',
       v.first_seen::date, v.prec, v.submitted::date, v.sim::double precision,
       v.oldest, v.reports, v.status
from (values
  -- Keluarga A: bantuan tunai (published)
  ('aaaaaaaa-0000-0000-0000-000000000001', 'f000000a-0000-0000-0000-000000000000', null,
   'INFO PENTING!! Lembaga Rekaan Sejahtera membagikan bantuan tunai Rp 500.000 untuk setiap keluarga di Kota Lamunan. Daftar sebelum hari Jumat lewat [TAUTAN]. Sebarkan ke 5 grup supaya semua kebagian.',
   '2026-01-05', 'day', '2026-01-06', null, true, 3, 'approved'),
  ('aaaaaaaa-0000-0000-0000-000000000002', 'f000000a-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000001',
   'INFO PENTING!! Lembaga Rekaan Sejahtera membagikan bantuan tunai Rp 1.000.000 untuk setiap keluarga di Kota Lamunan. Daftar sebelum hari Jumat lewat [TAUTAN]. Sebarkan ke 5 grup supaya semua kebagian.',
   '2026-02-01', 'month', '2026-02-10', 0.96, false, 7, 'approved'),
  ('aaaaaaaa-0000-0000-0000-000000000003', 'f000000a-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000002',
   'INFO PENTING!! Kementerian Urusan Awan membagikan bantuan tunai Rp 1.000.000 untuk setiap keluarga di Kota Lamunan. Daftar sebelum hari Jumat lewat [TAUTAN]. Sebarkan ke 10 grup supaya semua kebagian.',
   '2026-02-14', 'day', '2026-02-15', 0.91, false, 4, 'approved'),
  ('aaaaaaaa-0000-0000-0000-000000000004', 'f000000a-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000003',
   'INFO PENTING!! Kementerian Urusan Awan membagikan bantuan tunai Rp 2.500.000 untuk setiap keluarga di Kota Lamunan. Daftar sebelum 31 Maret lewat [TAUTAN]. Sebarkan ke 10 grup supaya semua kebagian.',
   '2026-03-01', 'month', '2026-03-20', 0.89, false, 2, 'approved'),
  ('aaaaaaaa-0000-0000-0000-000000000005', 'f000000a-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000002',
   'INFO PENTING!! Lembaga Rekaan Sejahtera membagikan bantuan tunai Rp 1.000.000 untuk setiap keluarga di seluruh Provinsi Andaikata. Daftar sebelum hari Jumat lewat [TAUTAN]. Sebarkan ke 5 grup supaya semua kebagian.',
   '2026-03-10', 'day', '2026-03-11', 0.93, false, 1, 'pending'),
  -- Keluarga B: klaim kesehatan (published)
  ('bbbbbbbb-0000-0000-0000-000000000001', 'f000000b-0000-0000-0000-000000000000', null,
   'Pesan dari dokter RS Rekaan Medika: minum air garam hangat 3 kali sehari bisa mencegah flu Lamunan. Teruskan ke keluarga tercinta.',
   '2025-01-01', 'year', '2025-12-02', null, true, 5, 'approved'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'f000000b-0000-0000-0000-000000000000', 'bbbbbbbb-0000-0000-0000-000000000001',
   'Pesan dari dokter RS Rekaan Medika: minum air garam hangat 5 kali sehari bisa mencegah flu Lamunan. Teruskan ke keluarga tercinta.',
   '2025-11-20', 'day', '2025-12-05', 0.95, false, 3, 'approved'),
  ('bbbbbbbb-0000-0000-0000-000000000003', 'f000000b-0000-0000-0000-000000000000', 'bbbbbbbb-0000-0000-0000-000000000002',
   'Pesan dari profesor Universitas Andaikata: minum air garam hangat 5 kali sehari bisa mencegah flu Lamunan. Wajib teruskan ke 20 orang, jangan berhenti di kamu!',
   '2026-01-08', 'day', '2026-01-09', 0.84, false, 6, 'approved'),
  ('bbbbbbbb-0000-0000-0000-000000000004', 'f000000b-0000-0000-0000-000000000000', 'bbbbbbbb-0000-0000-0000-000000000001',
   'Pesan dari dokter RS Rekaan Medika: minum air garam hangat 3 kali sehari bisa mencegah flu Lamunan. Info lengkap di [TAUTAN]. Teruskan ke keluarga tercinta.',
   '2026-02-02', 'day', '2026-02-03', 0.92, false, 1, 'rejected'),
  -- Keluarga C: penutupan ATM (keluarga masih pending, tidak terlihat publik)
  ('cccccccc-0000-0000-0000-000000000001', 'f000000c-0000-0000-0000-000000000000', null,
   'Semua ATM Bank Contoh Makmur di Kota Lamunan tutup mulai tanggal 12 Mei karena gangguan sistem. Tarik uang tunai sekarang juga sebelum terlambat!',
   '2026-04-28', 'day', '2026-04-29', null, true, 2, 'approved'),
  ('cccccccc-0000-0000-0000-000000000002', 'f000000c-0000-0000-0000-000000000000', 'cccccccc-0000-0000-0000-000000000001',
   'Semua ATM Bank Contoh Makmur di Kota Lamunan tutup mulai tanggal 15 Mei karena gangguan sistem. Tarik uang tunai sekarang juga sebelum terlambat!',
   '2026-05-02', 'day', '2026-05-02', 0.97, false, 1, 'pending'),
  ('cccccccc-0000-0000-0000-000000000003', 'f000000c-0000-0000-0000-000000000000', 'cccccccc-0000-0000-0000-000000000002',
   'Semua ATM bank di Kota Lamunan tutup mulai tanggal 15 Mei karena gangguan sistem. Tarik uang tunai sekarang juga sebelum terlambat!',
   '2026-05-05', 'day', '2026-05-06', 0.88, false, 1, 'pending'),
  ('cccccccc-0000-0000-0000-000000000004', 'f000000c-0000-0000-0000-000000000000', 'cccccccc-0000-0000-0000-000000000003',
   'Semua ATM bank di Pulau Rekaan tutup mulai tanggal 15 Mei karena gangguan sistem. Tarik semua tabungan hari ini dan bagikan pesan ini!',
   '2026-05-01', 'month', '2026-05-09', 0.86, false, 1, 'pending')
) as v(id, family_id, parent_id, body, first_seen, prec, submitted, sim, oldest, reports, status);

-- position_hint = offset karakter after_text di teks anak
insert into public.mutations (variant_id, parent_variant_id, category, before_text, after_text, position_hint)
select v.id, v.parent_id, m.category, m.before_text, m.after_text,
       nullif(strpos(v.body_anonymized, m.after_text), 0) - 1
from (values
  ('aaaaaaaa-0000-0000-0000-000000000002', 'number', 'Rp 500.000', 'Rp 1.000.000'),
  ('aaaaaaaa-0000-0000-0000-000000000003', 'institution', 'Lembaga Rekaan Sejahtera', 'Kementerian Urusan Awan'),
  ('aaaaaaaa-0000-0000-0000-000000000003', 'call_to_action', 'Sebarkan ke 5 grup', 'Sebarkan ke 10 grup'),
  ('aaaaaaaa-0000-0000-0000-000000000004', 'number', 'Rp 1.000.000', 'Rp 2.500.000'),
  ('aaaaaaaa-0000-0000-0000-000000000004', 'date', 'sebelum hari Jumat', 'sebelum 31 Maret'),
  ('aaaaaaaa-0000-0000-0000-000000000005', 'place', 'Kota Lamunan', 'seluruh Provinsi Andaikata'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'number', '3 kali', '5 kali'),
  ('bbbbbbbb-0000-0000-0000-000000000003', 'institution', 'dokter RS Rekaan Medika', 'profesor Universitas Andaikata'),
  ('bbbbbbbb-0000-0000-0000-000000000003', 'call_to_action', 'Teruskan ke keluarga tercinta.', 'Wajib teruskan ke 20 orang, jangan berhenti di kamu!'),
  ('bbbbbbbb-0000-0000-0000-000000000004', 'url', null, 'Info lengkap di [TAUTAN].'),
  ('cccccccc-0000-0000-0000-000000000002', 'date', '12 Mei', '15 Mei'),
  ('cccccccc-0000-0000-0000-000000000003', 'institution', 'Bank Contoh Makmur', 'bank'),
  ('cccccccc-0000-0000-0000-000000000004', 'place', 'Kota Lamunan', 'Pulau Rekaan'),
  ('cccccccc-0000-0000-0000-000000000004', 'call_to_action', 'Tarik uang tunai sekarang juga sebelum terlambat!', 'Tarik semua tabungan hari ini dan bagikan pesan ini!')
) as m(variant_id, category, before_text, after_text)
join public.variants v on v.id = m.variant_id::uuid;

insert into public.factcheck_links (family_id, url, publisher, title, verdict_label) values
  ('f000000a-0000-0000-0000-000000000000', 'https://cekfakta.example/artikel/bantuan-tunai-lembaga-rekaan',
   'cekfakta.example', '[SINTETIS] Lembaga Rekaan Sejahtera tidak pernah membagikan bantuan tunai', 'Hoaks'),
  ('f000000b-0000-0000-0000-000000000000', 'https://cekfakta.example/artikel/air-garam-flu-lamunan',
   'cekfakta.example', '[SINTETIS] Air garam hangat tidak mencegah flu', 'Disinformasi kesehatan');
