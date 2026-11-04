-- S6: nama penerbit resmi ditampilkan di halaman keluarga, jadi daftar penerbit (domain + nama, bukan data
-- pribadi) dibuat terbaca publik. Menulis tetap hanya kurator/admin (policy trusted_publishers_staff).
grant select on public.trusted_publishers to anon;

create policy trusted_publishers_read on public.trusted_publishers
  for select to anon, authenticated
  using (true);
