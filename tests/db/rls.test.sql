-- Tes RLS dan skema S1 (pgTAP). Jalankan: supabase test db tests/db
-- Fixture sintetis, dibuat sebagai pemilik tabel lalu di-rollback.
-- JWT diset di dua kunci: auth.uid() versi lama membaca claim.sub, versi GoTrue membaca claims.
begin;
create extension if not exists pgtap with schema extensions;
select plan(22);

-- Kosongkan data seed agar hitungan pasti; ikut di-rollback.
truncate public.families, public.variants, public.mutations, public.factcheck_links,
  public.trusted_publishers, public.takedown_requests cascade;

insert into auth.users (id) values
  ('00000000-0000-0000-0000-0000000000c1'),  -- kontributor
  ('00000000-0000-0000-0000-0000000000c2');  -- kurator
update public.contributors set role = 'curator' where id = '00000000-0000-0000-0000-0000000000c2';

insert into public.families (id, title, status) values
  ('00000000-0000-0000-0000-0000000000f1', 'Keluarga uji terbit', 'published'),
  ('00000000-0000-0000-0000-0000000000f2', 'Keluarga uji tertunda', 'pending');

insert into public.variants (id, family_id, parent_id, body_anonymized, body_hash, embedding,
                             first_seen_reported_at, moderation_status) values
  ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000f1', null,
   'Varian uji disetujui', repeat('a', 64), array_fill(0.1::real, array[384])::extensions.vector, '2026-01-01', 'approved'),
  ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-0000000000f1', '00000000-0000-0000-0000-0000000000a1',
   'Varian uji tertunda', repeat('b', 64), array_fill(0.1::real, array[384])::extensions.vector, '2026-01-02', 'pending'),
  ('00000000-0000-0000-0000-0000000000a3', '00000000-0000-0000-0000-0000000000f2', null,
   'Varian uji di keluarga tertunda', repeat('c', 64), array_fill(0.1::real, array[384])::extensions.vector, '2026-01-03', 'approved'),
  ('00000000-0000-0000-0000-0000000000a4', null, null,
   'Laporan kontributor uji', repeat('d', 64), null, '2026-02-01', 'pending');

insert into public.mutations (variant_id, parent_variant_id, category, before_text, after_text) values
  ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-0000000000a1', 'number', '3', '5');

insert into public.trusted_publishers (domain, name) values ('cekfakta.example', 'Contoh');
insert into public.factcheck_links (family_id, url, publisher, title) values
  ('00000000-0000-0000-0000-0000000000f1', 'https://cekfakta.example/a', 'cekfakta.example', 'Uji terbit'),
  ('00000000-0000-0000-0000-0000000000f2', 'https://cekfakta.example/b', 'cekfakta.example', 'Uji tertunda');

-- Skema
select is_empty(
  $$ select table_name || '.' || column_name from information_schema.columns
     where table_schema = 'public'
       and (data_type = 'bytea'
            or column_name ~* '(raw|original|mentah|image|gambar|photo|phone|telepon|email|nik|ip_addr|sender|pengirim|location|lokasi)') $$,
  'tidak ada kolom teks mentah, gambar, atau identitas'
);
select is_empty(
  $$ select relname from pg_class
     where relnamespace = 'public'::regnamespace and relkind = 'r' and not relrowsecurity $$,
  'RLS aktif di semua tabel public'
);
select set_eq(
  $$ select id from public.match_variants(array_fill(0.1::real, array[384])::extensions.vector, 0.5, 10) $$,
  $$ values ('00000000-0000-0000-0000-0000000000a1'::uuid), ('00000000-0000-0000-0000-0000000000a3'::uuid) $$,
  'match_variants hanya mengembalikan varian approved'
);

-- Constraint privasi
select throws_ok(
  $$ insert into public.variants (body_anonymized, body_hash, first_seen_reported_at)
     values ('Hubungi 0812-3456-7890 sekarang', repeat('e', 64), '2026-01-01') $$,
  '23514', null, 'nomor telepon di body ditolak'
);
select throws_ok(
  $$ insert into public.factcheck_links (family_id, url, publisher, title)
     values ('00000000-0000-0000-0000-0000000000f1', 'https://jahat.example@cekfakta.example/x', 'cekfakta.example', 'Uji') $$,
  '23514', null, 'URL dengan userinfo ditolak'
);
select throws_ok(
  $$ insert into public.factcheck_links (family_id, url, publisher, title)
     values ('00000000-0000-0000-0000-0000000000f1', 'http://cekfakta.example/x', 'cekfakta.example', 'Uji') $$,
  '23514', null, 'URL non-https ditolak'
);

-- anon
set local role anon;
select set_config('request.jwt.claims', '{"role":"anon"}', true);

select results_eq(
  'select id from public.families',
  $$ values ('00000000-0000-0000-0000-0000000000f1'::uuid) $$,
  'anon hanya melihat keluarga published'
);
select results_eq(
  'select id from public.variants',
  $$ values ('00000000-0000-0000-0000-0000000000a1'::uuid) $$,
  'anon hanya melihat varian approved di keluarga published'
);
select is_empty(
  $$ select 1 from public.variants where moderation_status = 'pending' $$,
  'anon tidak bisa membaca varian pending'
);
select is_empty('select 1 from public.mutations', 'anon tidak melihat mutasi yang melibatkan varian pending');
select is((select count(*)::int from public.factcheck_links), 1, 'anon hanya melihat tautan fact-check keluarga published');
select throws_ok(
  $$ insert into public.variants (body_anonymized, body_hash, first_seen_reported_at)
     values ('Laporan anon', repeat('f', 64), '2026-01-01') $$,
  '42501', null, 'anon tidak bisa insert varian'
);
select is((select count(*)::int from public.trusted_publishers), 1, 'anon boleh membaca daftar penerbit resmi (untuk nama penerbit)');
select throws_ok(
  $$ insert into public.trusted_publishers (domain, name) values ('jahat.example', 'Penerbit palsu') $$,
  '42501', null, 'anon tidak bisa menambah penerbit'
);
select throws_ok(
  $$ select * from public.match_variants(array_fill(0.1::real, array[384])::extensions.vector, 0.5, 10) $$,
  '42501', null, 'anon tidak bisa memanggil match_variants'
);
reset role;

-- kontributor
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true),
  set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-0000000000c1', true);

select throws_ok(
  $$ insert into public.variants (body_anonymized, body_hash, first_seen_reported_at)
     values ('Laporan kontributor uji', repeat('8', 64), '2026-02-01') $$,
  '42501', null, 'kontributor tidak bisa insert langsung (wajib lewat services/nlp)'
);
select throws_ok(
  $$ insert into public.variants (body_anonymized, body_hash, first_seen_reported_at, moderation_status)
     values ('Laporan langsung disetujui', repeat('9', 64), '2026-02-01', 'approved') $$,
  '42501', null, 'kontributor tidak bisa mengirim varian berstatus approved'
);
select is_empty(
  $$ select 1 from public.variants where moderation_status = 'pending' $$,
  'kontributor tidak bisa membaca varian pending'
);
update public.variants set moderation_status = 'approved', family_id = '00000000-0000-0000-0000-0000000000f1'
  where body_hash = repeat('d', 64);
update public.variants set moderation_status = 'rejected' where id = '00000000-0000-0000-0000-0000000000a1';
update public.contributors set role = 'admin' where id = '00000000-0000-0000-0000-0000000000c1';
reset role;

select is(
  (select moderation_status from public.variants where body_hash = repeat('d', 64)), 'pending',
  'kontributor tidak bisa menyetujui varian sendiri'
);
select is(
  (select moderation_status from public.variants where id = '00000000-0000-0000-0000-0000000000a1'), 'approved',
  'kontributor tidak bisa mengubah varian orang lain'
);
select is(
  (select role from public.contributors where id = '00000000-0000-0000-0000-0000000000c1'), 'contributor',
  'kontributor tidak bisa menaikkan perannya sendiri'
);

-- kurator
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true),
  set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-0000000000c2', true);
update public.variants set moderation_status = 'approved' where id = '00000000-0000-0000-0000-0000000000a2';
reset role;

select is(
  (select moderation_status from public.variants where id = '00000000-0000-0000-0000-0000000000a2'), 'approved',
  'kurator bisa menyetujui varian'
);

select * from finish();
rollback;
