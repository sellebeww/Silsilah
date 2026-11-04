-- S4: penempatan di pohon. services/nlp menghitung ulang seluruh pohon keluarga dan menulisnya atomik.
alter table public.variants
  add column edge_confidence text check (edge_confidence in ('high', 'low')),
  -- kandidat induk yang seri: UI menampilkan "arah turunan tidak pasti"
  add column alt_parent_ids uuid[] not null default '{}',
  -- keluarga lain yang juga mirip; tidak pernah digabung otomatis, menunggu keputusan kurator
  add column merge_suggestion uuid[] not null default '{}',
  add column mutation_summary text check (char_length(mutation_summary) <= 500);

-- Satu rencana = satu keluarga: setujui varian, tulis ulang induk/penanda tertua semua anggota, ganti mutasi.
create function public.apply_family_plan(p_plan jsonb)
returns void
language plpgsql
set search_path = ''
as $$
declare
  fam uuid := (p_plan ->> 'family_id')::uuid;
  vid uuid := (p_plan ->> 'variant_id')::uuid;
  n jsonb;
begin
  insert into public.families (id, title) values (fam, 'Belum berjudul') on conflict (id) do nothing;

  update public.variants
  set family_id = fam,
      moderation_status = 'approved',
      merge_suggestion = array(select jsonb_array_elements_text(p_plan -> 'merge_suggestion'))::uuid[]
  where id = vid and moderation_status <> 'rejected' and (family_id is null or family_id = fam);
  if not found then
    raise exception 'varian tidak bisa ditempatkan di keluarga ini' using errcode = 'P0001';
  end if;

  -- dikosongkan dulu: indeks unik "satu tertua per keluarga" tidak boleh bentrok saat ditulis ulang
  update public.variants set is_oldest_reported = false where family_id = fam and is_oldest_reported;
  for n in select * from jsonb_array_elements(p_plan -> 'nodes') loop
    update public.variants
    set parent_id = (n ->> 'parent_id')::uuid,
        edge_similarity = (n ->> 'edge_similarity')::double precision,
        edge_confidence = n ->> 'edge_confidence',
        alt_parent_ids = array(select jsonb_array_elements_text(n -> 'alt_parent_ids'))::uuid[],
        is_oldest_reported = (n ->> 'is_oldest')::boolean,
        mutation_summary = n ->> 'mutation_summary'
    where id = (n ->> 'id')::uuid and family_id = fam;
  end loop;

  delete from public.mutations m using public.variants v where m.variant_id = v.id and v.family_id = fam;
  insert into public.mutations (variant_id, parent_variant_id, category, before_text, after_text, position_hint)
  select (x ->> 'variant_id')::uuid, (x ->> 'parent_variant_id')::uuid, x ->> 'category',
         x ->> 'before_text', x ->> 'after_text', (x ->> 'position_hint')::integer
  from jsonb_array_elements(p_plan -> 'mutations') x;
end;
$$;

revoke execute on function public.apply_family_plan(jsonb) from public, anon, authenticated;
grant execute on function public.apply_family_plan(jsonb) to service_role;
