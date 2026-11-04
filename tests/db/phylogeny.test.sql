-- Tes apply_family_plan S4 (pgTAP). Jalankan: supabase test db tests/db
begin;
create extension if not exists pgtap with schema extensions;
select plan(9);

truncate public.families, public.variants cascade;
insert into public.variants (id, body_anonymized, body_hash, first_seen_reported_at, moderation_status) values
  ('00000000-0000-0000-0000-0000000000b1', 'Varian uji satu 5 hari', repeat('1', 64), '2026-02-06', 'pending'),
  ('00000000-0000-0000-0000-0000000000b2', 'Varian uji dua 3 hari', repeat('2', 64), '2026-02-03', 'pending'),
  ('00000000-0000-0000-0000-0000000000b3', 'Varian uji ditolak', repeat('3', 64), '2026-02-01', 'rejected');

-- b1 disetujui sendirian: keluarga baru, b1 akar
select lives_ok($$ select public.apply_family_plan('{
  "family_id": "00000000-0000-0000-0000-0000000000f9", "variant_id": "00000000-0000-0000-0000-0000000000b1",
  "merge_suggestion": [],
  "nodes": [{"id": "00000000-0000-0000-0000-0000000000b1", "parent_id": null, "edge_similarity": null,
             "edge_confidence": null, "alt_parent_ids": [], "is_oldest": true, "mutation_summary": null}],
  "mutations": []}'::jsonb) $$, 'varian pertama membuat keluarga baru');
select is((select status from public.families where id = '00000000-0000-0000-0000-0000000000f9'), 'pending',
  'keluarga baru berstatus pending (judul menunggu kurator)');
select is((select moderation_status from public.variants where id = '00000000-0000-0000-0000-0000000000b1'),
  'approved', 'varian disetujui');

-- b2 lebih tua dilaporkan belakangan: rebalance, b2 jadi akar, b1 anaknya
select lives_ok($$ select public.apply_family_plan('{
  "family_id": "00000000-0000-0000-0000-0000000000f9", "variant_id": "00000000-0000-0000-0000-0000000000b2",
  "merge_suggestion": ["00000000-0000-0000-0000-0000000000f8"],
  "nodes": [
    {"id": "00000000-0000-0000-0000-0000000000b2", "parent_id": null, "edge_similarity": null,
     "edge_confidence": null, "alt_parent_ids": [], "is_oldest": true, "mutation_summary": null},
    {"id": "00000000-0000-0000-0000-0000000000b1", "parent_id": "00000000-0000-0000-0000-0000000000b2",
     "edge_similarity": 0.97, "edge_confidence": "high", "alt_parent_ids": [], "is_oldest": false,
     "mutation_summary": "angka diganti 3 -> 5"}],
  "mutations": [{"variant_id": "00000000-0000-0000-0000-0000000000b1",
                 "parent_variant_id": "00000000-0000-0000-0000-0000000000b2", "category": "number",
                 "before_text": "3", "after_text": "5", "position_hint": 16}]}'::jsonb) $$,
  'rebalance memindahkan penanda tertua tanpa bentrok indeks unik');
select results_eq(
  $$ select id, is_oldest_reported, parent_id from public.variants
     where family_id = '00000000-0000-0000-0000-0000000000f9' order by id $$,
  $$ values ('00000000-0000-0000-0000-0000000000b1'::uuid, false, '00000000-0000-0000-0000-0000000000b2'::uuid),
            ('00000000-0000-0000-0000-0000000000b2'::uuid, true, null::uuid) $$,
  'akar dan induk ditulis ulang'
);
select is((select merge_suggestion from public.variants where id = '00000000-0000-0000-0000-0000000000b2'),
  array['00000000-0000-0000-0000-0000000000f8']::uuid[], 'saran gabung disimpan, keluarga tidak digabung');

-- menjalankan rencana yang sama lagi tidak menggandakan mutasi
select public.apply_family_plan(p) from (select '{
  "family_id": "00000000-0000-0000-0000-0000000000f9", "variant_id": "00000000-0000-0000-0000-0000000000b1",
  "merge_suggestion": [], "nodes": [], "mutations": [{"variant_id": "00000000-0000-0000-0000-0000000000b1",
  "parent_variant_id": "00000000-0000-0000-0000-0000000000b2", "category": "number", "before_text": "3",
  "after_text": "5", "position_hint": 16}]}'::jsonb p) x;
select is((select count(*)::int from public.mutations), 1, 'mutasi diganti, bukan ditambah (idempoten)');

select throws_ok($$ select public.apply_family_plan('{
  "family_id": "00000000-0000-0000-0000-0000000000f9", "variant_id": "00000000-0000-0000-0000-0000000000b3",
  "merge_suggestion": [], "nodes": [], "mutations": []}'::jsonb) $$,
  'P0001', null, 'varian ditolak tidak bisa ditempatkan');

set local role authenticated;
select throws_ok($$ select public.apply_family_plan('{}'::jsonb) $$, '42501', null,
  'klien tidak bisa memanggil apply_family_plan');
reset role;

select * from finish();
rollback;
