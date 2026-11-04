-- S3: jalur ingest lewat services/nlp. Semua kiriman wajib dianonimkan dulu (prinsip 1),
-- jadi insert varian langsung dari klien ditutup; services/nlp memanggil fungsi di bawah dengan service_role.
drop policy variants_contributor_insert on public.variants;
revoke insert on public.variants from authenticated;

-- Laporan ulang teks yang sama persis: naikkan report_count, majukan tanggal bila kontributor melihatnya lebih awal.
create function public.register_duplicate_report(p_body_hash text, p_first_seen date, p_date_precision text)
returns table (id uuid, report_count integer)
language sql
set search_path = ''
as $$
  update public.variants v
  set report_count = v.report_count + 1,
      first_seen_reported_at = least(v.first_seen_reported_at, p_first_seen),
      -- presisi ikut tanggal yang dipakai; perbandingan antar presisi berbeda sengaja sederhana (tanggal awal periode)
      date_precision = case when p_first_seen < v.first_seen_reported_at then p_date_precision else v.date_precision end
  where v.body_hash = p_body_hash
  returning v.id, v.report_count
$$;

-- Simpan varian baru berstatus pending; bila hash sudah ada (balapan dua kiriman), jatuh ke jalur duplikat.
create function public.insert_pending_variant(
  p_body text,
  p_body_hash text,
  p_embedding extensions.vector(384),
  p_language_hint text,
  p_first_seen date,
  p_date_precision text
)
returns table (id uuid, report_count integer, is_duplicate boolean)
language plpgsql
set search_path = ''
as $$
begin
  return query
  insert into public.variants as v (
    body_anonymized, body_hash, embedding, language_hint, first_seen_reported_at, date_precision, submitted_at
  )
  -- tanggal WIB, sama dengan validasi "tidak di masa depan" di services/nlp
  values (p_body, p_body_hash, p_embedding, p_language_hint, p_first_seen, p_date_precision,
          (now() at time zone 'Asia/Jakarta')::date)
  on conflict (body_hash) do nothing
  returning v.id, v.report_count, false;

  if not found then
    return query
    select d.id, d.report_count, true from public.register_duplicate_report(p_body_hash, p_first_seen, p_date_precision) d;
  end if;
end;
$$;

revoke execute on function public.register_duplicate_report(text, date, text) from public, anon, authenticated;
revoke execute on function public.insert_pending_variant(text, text, extensions.vector, text, date, text)
  from public, anon, authenticated;
grant execute on function public.register_duplicate_report(text, date, text) to service_role;
grant execute on function public.insert_pending_variant(text, text, extensions.vector, text, date, text)
  to service_role;
