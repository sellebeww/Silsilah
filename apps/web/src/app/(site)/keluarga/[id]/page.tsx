import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FamilyTree } from "@/components/FamilyTree";
import { getFamily } from "@/lib/data";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const f = await getFamily((await params).id);
  if (!f) return { title: "Tidak ditemukan", robots: { index: false } };
  const oldest = f.variants.find((v) => v.is_oldest_reported);
  const description =
    `Pohon mutasi pesan berantai: ${f.variants.length} varian.` +
    (oldest ? ` Varian tertua yang dilaporkan: ${formatDate(oldest.first_seen_reported_at, oldest.date_precision)}.` : "");
  return {
    title: f.title,
    description,
    alternates: { canonical: `/keluarga/${f.id}` },
    openGraph: { title: f.title, description, type: "article", url: `/keluarga/${f.id}`, locale: "id_ID" },
    twitter: { card: "summary", title: f.title, description },
  };
}

export default async function FamilyPage({ params }: Props) {
  const f = await getFamily((await params).id);
  if (!f) notFound();
  return (
    <>
      <h1>{f.title}</h1>
      <p className="note">
        Penanda &ldquo;Tertua yang dilaporkan&rdquo; berarti varian paling awal yang masuk ke sistem ini, bukan asal-usul atau pembuat pertama.
      </p>
      {f.factcheck_links.length > 0 && (
        <section aria-labelledby="fc">
          <h2 id="fc">Hasil pemeriksaan fakta resmi</h2>
          <ul>
            {f.factcheck_links.map((l) => (
              <li key={l.id}>
                <strong>{l.publisher_name}</strong>
                {l.verdict_label && <> · <span className="badge">{l.verdict_label}</span></>}
                <br />
                <a href={l.url} rel="noopener noreferrer nofollow" target="_blank">{l.title}</a>
              </li>
            ))}
          </ul>
        </section>
      )}
      <FamilyTree family={f} />
    </>
  );
}
