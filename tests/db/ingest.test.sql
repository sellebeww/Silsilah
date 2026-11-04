-- Tes fungsi ingest S3 (pgTAP). Jalankan: supabase test db tests/db
begin;
create extension if not exists pgtap with schema extensions;
select plan(9);

truncate public.families, public.variants cascade;

select is(
  (select is_duplicate from public.insert_pending_variant(
     'Teks uji tersamar', repeat('a', 64), array_fill(0.1::real, array[384])::extensions.vector, null,
     '2026-03-10', 'day')),
  false, 'varian baru tersimpan'
);
select is(
  (select moderation_status from public.variants where body_hash = repeat('a', 64)), 'pending',
  'varian baru berstatus pending'
);
select is(
  (select submitted_at from public.variants where body_hash = repeat('a', 64)),
  (now() at time zone 'Asia/Jakarta')::date, 'submitted_at diisi server (WIB)'
);

select results_eq(
  $$ select report_count, is_duplicate from public.insert_pending_variant(
       'Teks uji tersamar', repeat('a', 64), null, null, '2026-03-12', 'day') $$,
  $$ values (2, true) $$, 'hash sama: report_count naik, tidak ada baris baru'
);
select is((select count(*)::int from public.variants), 1, 'tetap satu baris');
select is(
  (select first_seen_reported_at from public.variants where body_hash = repeat('a', 64)), '2026-03-10'::date,
  'tanggal lebih baru tidak menggeser tanggal pertama'
);

select is(
  (select report_count from public.register_duplicate_report(repeat('a', 64), '2026-02-01', 'month')), 3,
  'register_duplicate_report menaikkan report_count'
);
select results_eq(
  $$ select first_seen_reported_at, date_precision from public.variants where body_hash = repeat('a', 64) $$,
  $$ values ('2026-02-01'::date, 'month') $$, 'tanggal lebih awal memperbarui tanggal dan presisinya'
);

set local role authenticated;
select throws_ok(
  $$ select * from public.register_duplicate_report(repeat('a', 64), '2026-01-01', 'day') $$,
  '42501', null, 'klien tidak bisa memanggil fungsi ingest'
);
reset role;

select * from finish();
rollback;
