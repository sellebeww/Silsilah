-- S1: skema inti Silsilah. Tidak ada kolom untuk teks mentah, gambar, atau identitas penyebar.

create extension if not exists vector with schema extensions;

-- Jaring pengaman terakhir; anonimisasi tetap tugas services/nlp, DB hanya menolak pola PII yang jelas.
create function public.has_obvious_pii(t text)
returns boolean
language sql
immutable
parallel safe
set search_path = ''
as $$
  select t ~* '[[:alnum:]._%+-]+@[[:alnum:]-]+(\.[[:alnum:]-]+)*\.[[:alpha:]]{2,}'
      or t ~ '(^|[^0-9.])(\+?62|0)[ .-]?8[0-9]([ .-]?[0-9]){6,11}'
      or t ~ '(^|[^0-9])[0-9]{16}([^0-9]|$)'
$$;

-- Host diambil ketat (menolak "https://x@host") agar allowlist tidak bisa diakali; '' bila tidak cocok.
create function public.url_host(url text)
returns text
language sql
immutable
parallel safe
set search_path = ''
as $$
  select coalesce(lower(substring(url from '^https://([A-Za-z0-9.-]+)(?::[0-9]{1,5})?(?:[/?#]|$)')), '')
$$;

create table public.contributors (
  id uuid primary key references auth.users (id) on delete cascade,
  role text not null default 'contributor' check (role in ('contributor', 'curator', 'admin')),
  created_at timestamptz not null default now()
);

create table public.families (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(title) between 3 and 200 and not public.has_obvious_pii(title)),
  status text not null default 'pending' check (status in ('pending', 'published', 'hidden')),
  created_at timestamptz not null default now()
);

-- Sengaja tanpa submitted_by: akun kontributor tidak dikaitkan dengan laporannya (prinsip 3).
create table public.variants (
  id uuid primary key default gen_random_uuid(),
  -- null = belum ditempatkan di pohon (penempatan di S4)
  family_id uuid references public.families (id) on delete cascade,
  parent_id uuid references public.variants (id) on delete set null,
  body_anonymized text not null check (char_length(body_anonymized) between 1 and 10000),
  body_hash text not null unique check (body_hash ~ '^[0-9a-f]{64}$'),
  -- 384 = EMBEDDING_DIM default; ganti model = migrasi baru + re-embed
  embedding extensions.vector(384),
  language_hint text check (language_hint ~ '^[a-z]{2,3}(-[a-z]{2,3})*$'),
  first_seen_reported_at date not null,
  date_precision text not null default 'day' check (date_precision in ('day', 'month', 'year')),
  -- tanggal saja, bukan jam, agar tidak bisa dicocokkan dengan aktivitas kontributor
  submitted_at date not null default current_date,
  edge_similarity double precision check (edge_similarity between -1 and 1),
  is_oldest_reported boolean not null default false,
  report_count integer not null default 1 check (report_count >= 1),
  moderation_status text not null default 'pending'
    check (moderation_status in ('pending', 'approved', 'rejected')),
  constraint variants_not_own_parent check (parent_id <> id),
  constraint variants_body_no_obvious_pii check (not public.has_obvious_pii(body_anonymized)),
  constraint variants_seen_before_submitted check (first_seen_reported_at <= submitted_at),
  -- tanggal perkiraan disimpan di awal periode supaya tidak tampak lebih presisi dari aslinya
  constraint variants_date_matches_precision check (
    date_precision = 'day'
    or (date_precision = 'month' and extract(day from first_seen_reported_at) = 1)
    or (date_precision = 'year' and extract(day from first_seen_reported_at) = 1
        and extract(month from first_seen_reported_at) = 1)
  ),
  constraint variants_approved_needs_family check (moderation_status <> 'approved' or family_id is not null)
);

create table public.mutations (
  id uuid primary key default gen_random_uuid(),
  variant_id uuid not null references public.variants (id) on delete cascade,
  -- salinan variants.parent_id saat diff dihitung; S4 wajib menghitung ulang mutasi bila re-parent
  parent_variant_id uuid not null references public.variants (id) on delete cascade,
  category text not null
    check (category in ('number', 'institution', 'call_to_action', 'date', 'place', 'url', 'other')),
  before_text text check (char_length(before_text) <= 2000),
  after_text text check (char_length(after_text) <= 2000),
  position_hint integer check (position_hint >= 0),
  constraint mutations_has_change check (before_text is not null or after_text is not null),
  constraint mutations_distinct_variants check (variant_id <> parent_variant_id),
  constraint mutations_no_obvious_pii
    check (not public.has_obvious_pii(coalesce(before_text, '') || ' ' || coalesce(after_text, '')))
);

create table public.trusted_publishers (
  domain text primary key check (domain ~ '^[a-z0-9-]+(\.[a-z0-9-]+)+$'),
  name text not null check (char_length(name) between 2 and 200)
);

create table public.factcheck_links (
  id uuid primary key default gen_random_uuid(),
  family_id uuid not null references public.families (id) on delete cascade,
  url text not null check (char_length(url) <= 2000),
  publisher text not null references public.trusted_publishers (domain),
  title text not null check (char_length(title) between 3 and 300),
  verdict_label text check (char_length(verdict_label) <= 100),
  added_by uuid default auth.uid() references public.contributors (id) on delete set null,
  created_at timestamptz not null default now(),
  unique (family_id, url),
  -- https wajib dan host harus domain penerbit tepercaya atau subdomainnya
  constraint factcheck_links_url_trusted check (
    public.url_host(url) = publisher or public.url_host(url) like '%.' || publisher
  )
);

-- Identitas pemohon sengaja tidak disimpan.
create table public.takedown_requests (
  id uuid primary key default gen_random_uuid(),
  -- set null: catatan keputusan tetap ada setelah varian dihapus permanen
  variant_id uuid references public.variants (id) on delete set null,
  reason text not null check (char_length(reason) between 10 and 2000 and not public.has_obvious_pii(reason)),
  status text not null default 'open' check (status in ('open', 'accepted', 'rejected')),
  created_at timestamptz not null default now()
);

create index variants_embedding_hnsw on public.variants using hnsw (embedding extensions.vector_cosine_ops);
create index variants_family_id_idx on public.variants (family_id);
create index variants_parent_id_idx on public.variants (parent_id);
create index variants_first_seen_idx on public.variants (first_seen_reported_at);
-- paling banyak satu "tertua yang dilaporkan" per keluarga
create unique index variants_one_oldest_per_family on public.variants (family_id) where is_oldest_reported;
create index mutations_variant_id_idx on public.mutations (variant_id);
create index mutations_parent_variant_id_idx on public.mutations (parent_variant_id);
create index factcheck_links_family_id_idx on public.factcheck_links (family_id);
create index takedown_requests_variant_id_idx on public.takedown_requests (variant_id);

-- Setiap akun Auth baru otomatis menjadi kontributor; peran lain hanya diberi admin.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.contributors (id) values (new.id);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
