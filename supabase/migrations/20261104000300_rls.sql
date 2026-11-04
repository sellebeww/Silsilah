-- RLS dan hak akses. services/nlp memakai service_role yang melewati RLS.

-- security definer agar policy di contributors tidak memicu rekursi RLS.
create function public.has_role(variadic roles text[])
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.contributors c
    where c.id = (select auth.uid()) and c.role = any (roles)
  )
$$;

alter table public.contributors enable row level security;
alter table public.families enable row level security;
alter table public.variants enable row level security;
alter table public.mutations enable row level security;
alter table public.trusted_publishers enable row level security;
alter table public.factcheck_links enable row level security;
alter table public.takedown_requests enable row level security;

-- Default deny: Supabase memberi anon/authenticated hak penuh pada tabel public; dicabut lalu diberi seperlunya.
revoke all on public.contributors, public.families, public.variants, public.mutations,
  public.trusted_publishers, public.factcheck_links, public.takedown_requests
  from anon, authenticated;

grant select on public.families, public.variants, public.mutations, public.factcheck_links to anon, authenticated;
grant insert, update, delete on public.families, public.mutations, public.factcheck_links to authenticated;
grant select, insert, update, delete on public.trusted_publishers to authenticated;
grant select on public.contributors, public.takedown_requests to authenticated;
-- Klien hanya mengisi isi laporan; status, penempatan, dan penanda tertua tidak bisa diisi dari luar.
grant insert (body_anonymized, body_hash, embedding, language_hint, first_seen_reported_at, date_precision)
  on public.variants to authenticated;
grant update (family_id, parent_id, body_anonymized, edge_similarity, is_oldest_reported, moderation_status)
  on public.variants to authenticated;
grant delete on public.variants to authenticated;
grant update (role) on public.contributors to authenticated;
grant insert (variant_id, reason) on public.takedown_requests to authenticated;
grant update (status), delete on public.takedown_requests to authenticated;

revoke execute on function public.handle_new_user() from public, anon, authenticated;

-- contributors
create policy contributors_read_self_or_admin on public.contributors
  for select to authenticated
  using (id = (select auth.uid()) or (select public.has_role('admin')));

create policy contributors_admin_update on public.contributors
  for update to authenticated
  using ((select public.has_role('admin')))
  with check ((select public.has_role('admin')));

-- families
create policy families_read on public.families
  for select to anon, authenticated
  using (status = 'published' or (select public.has_role('curator', 'admin')));

create policy families_staff_write on public.families
  for all to authenticated
  using ((select public.has_role('curator', 'admin')))
  with check ((select public.has_role('curator', 'admin')));

-- variants
create policy variants_read on public.variants
  for select to anon, authenticated
  using (
    (moderation_status = 'approved'
      and exists (select 1 from public.families f where f.id = family_id and f.status = 'published'))
    or (select public.has_role('curator', 'admin'))
  );

-- Laporan bisa dikirim lewat JWT kontributor; karena tanpa pemilik, kontributor tak bisa ubah/hapus varian apa pun.
create policy variants_contributor_insert on public.variants
  for insert to authenticated
  with check (moderation_status = 'pending' and (select public.has_role('contributor', 'curator', 'admin')));

create policy variants_staff_update on public.variants
  for update to authenticated
  using ((select public.has_role('curator', 'admin')))
  with check ((select public.has_role('curator', 'admin')));

create policy variants_staff_delete on public.variants
  for delete to authenticated
  using ((select public.has_role('curator', 'admin')));

-- mutations: induk juga harus terlihat, karena before_text adalah isi varian induk.
create policy mutations_read on public.mutations
  for select to anon, authenticated
  using (
    exists (select 1 from public.variants v where v.id = variant_id)
    and exists (select 1 from public.variants v where v.id = parent_variant_id)
  );

create policy mutations_staff_write on public.mutations
  for all to authenticated
  using ((select public.has_role('curator', 'admin')))
  with check ((select public.has_role('curator', 'admin')));

-- trusted_publishers
create policy trusted_publishers_staff on public.trusted_publishers
  for all to authenticated
  using ((select public.has_role('curator', 'admin')))
  with check ((select public.has_role('curator', 'admin')));

-- factcheck_links: subquery ke families ikut tersaring RLS families.
create policy factcheck_links_read on public.factcheck_links
  for select to anon, authenticated
  using (exists (select 1 from public.families f where f.id = family_id));

create policy factcheck_links_staff_write on public.factcheck_links
  for all to authenticated
  using ((select public.has_role('curator', 'admin')))
  with check ((select public.has_role('curator', 'admin')));

-- takedown_requests
create policy takedown_requests_insert on public.takedown_requests
  for insert to authenticated
  with check (
    status = 'open' and variant_id is not null
    and (select public.has_role('contributor', 'curator', 'admin'))
  );

create policy takedown_requests_staff on public.takedown_requests
  for all to authenticated
  using ((select public.has_role('curator', 'admin')))
  with check ((select public.has_role('curator', 'admin')));
