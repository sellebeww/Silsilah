import Link from "next/link";
import { listFamilies, type SortKey } from "@/lib/data";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function Home({ searchParams }: { searchParams: Promise<{ q?: string; urut?: string }> }) {
  const { q = "", urut } = await searchParams;
  const sort: SortKey = urut === "laporan" ? "laporan" : "terbaru";
  const families = await listFamilies(q, sort);
  return (
    <>
      <h1>Hoaks punya keluarga. Temukan leluhurnya.</h1>
      <p>
        Silsilah menempatkan laporan pesan berantai di pohon varian dan menunjuk <strong>varian tertua yang dilaporkan</strong>. Itu
        bukan asal-usul pasti: pesan serupa mungkin sudah beredar lebih dulu dan belum pernah dilaporkan.
      </p>
      <form method="get" role="search" className="search">
        <label htmlFor="q">Cari keluarga pesan</label>
        <input id="q" name="q" type="search" defaultValue={q} maxLength={100} />
        <label htmlFor="urut">Urutkan</label>
        <select id="urut" name="urut" defaultValue={sort}>
          <option value="terbaru">Terbaru</option>
          <option value="laporan">Laporan terbanyak</option>
        </select>
        <button type="submit">Cari</button>
      </form>
      {families.length === 0 ? (
        <p>Tidak ada keluarga yang cocok.</p>
      ) : (
        <ul className="cards">
          {families.map((f) => (
            <li key={f.id}>
              <h2><Link href={`/keluarga/${f.id}`}>{f.title}</Link></h2>
              <p>
                {f.variant_count} varian · {f.report_total} laporan
                {f.oldest && <> · tertua yang dilaporkan: {formatDate(f.oldest.first_seen_reported_at, f.oldest.date_precision)}</>}
              </p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
