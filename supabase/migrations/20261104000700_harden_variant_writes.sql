-- Varian hanya ditulis services/nlp (service_role, lewat RPC) setelah anonimisasi.
-- Klien tidak boleh insert varian, dan kurator tidak boleh mengubah isi teks (jalur itu melewati anonimizer).
drop policy variants_contributor_insert on public.variants;
revoke insert on public.variants from authenticated;
revoke update (body_anonymized) on public.variants from authenticated;
