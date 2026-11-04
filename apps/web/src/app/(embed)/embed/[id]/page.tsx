import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { EmbedResizer } from "@/components/EmbedResizer";
import { MiniTree } from "@/components/MiniTree";
import { getFamily } from "@/lib/data";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ id: string }> };

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const MAX_SNIPPET = 280;

export const metadata: Metadata = { title: "Pohon mutasi pesan berantai" };

export default async function EmbedPage({ params }: Props) {
  const f = await getFamily((await params).id);
  if (!f) notFound();
  const oldest = f.variants.find((v) => v.is_oldest_reported);
  const total = f.variants.reduce((n, v) => n + v.report_count, 0);
  const snippet = oldest && (oldest.body_anonymized.length > MAX_SNIPPET ? `${oldest.body_anonymized.slice(0, MAX_SNIPPET).trimEnd()}…` : oldest.body_anonymized);
  return (
    <article className="embed" aria-labelledby="judul">
      <h1 id="judul">{f.title}</h1>
      <MiniTree variants={f.variants} />
      <p className="legend">
        {f.variants.length} varian · {total} laporan · garis putus-putus = arah turunan tidak pasti
      </p>
      {oldest ? (
        <>
          <p>
            <span className="badge">Tertua yang dilaporkan</span> {formatDate(oldest.first_seen_reported_at, oldest.date_precision)}
          </p>
          <blockquote className="text">{snippet}</blockquote>
          <p className="note">Varian paling awal yang sampai ke Silsilah, bukan asal-usul pasti.</p>
        </>
      ) : (
        <p>Belum ada varian yang dipublikasikan.</p>
      )}
      <p>
        <a href={`${SITE}/keluarga/${f.id}`} target="_blank" rel="noopener">Lihat lengkap di Silsilah</a>
      </p>
      <EmbedResizer />
    </article>
  );
}
