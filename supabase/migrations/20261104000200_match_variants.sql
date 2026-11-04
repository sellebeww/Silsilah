-- Pencarian kNN kosinus untuk penempatan di pohon. Hanya varian approved.
create function public.match_variants(
  query_embedding extensions.vector(384),
  match_threshold double precision,
  match_count integer
)
returns table (id uuid, family_id uuid, parent_id uuid, similarity double precision)
language sql
stable
set search_path = ''
as $$
  -- shortcut: HNSW memfilter setelah scan, jadi hasil bisa < match_count bila banyak non-approved; aktifkan hnsw.iterative_scan bila terjadi
  select v.id, v.family_id, v.parent_id, 1 - (v.embedding operator(extensions.<=>) query_embedding)
  from public.variants v
  where v.moderation_status = 'approved'
    and v.embedding is not null
    and 1 - (v.embedding operator(extensions.<=>) query_embedding) >= match_threshold
  order by v.embedding operator(extensions.<=>) query_embedding
  limit least(greatest(match_count, 0), 100)
$$;

-- Hanya services/nlp (service role) yang memanggil; mencegah klien menyisir isi lewat embedding.
revoke execute on function public.match_variants(extensions.vector, double precision, integer)
  from public, anon, authenticated;
grant execute on function public.match_variants(extensions.vector, double precision, integer) to service_role;
