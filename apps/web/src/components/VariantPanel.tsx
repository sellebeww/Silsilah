import Link from "next/link";
import { CATEGORY_STYLE, formatDate } from "@/lib/format";
import type { Mutation, Variant } from "@/lib/types";
import { DiffView } from "./DiffView";

export function VariantPanel({ variant, parent, mutations }: { variant: Variant; parent: Variant | null; mutations: Mutation[] }) {
  return (
    <section aria-label="Detail varian" className="panel" data-testid="panel">
      <h3>
        {variant.is_oldest_reported ? <span className="badge">Tertua yang dilaporkan</span> : "Varian"}
      </h3>
      {variant.is_oldest_reported && (
        <p className="note">Varian tertua yang sampai ke sistem ini, bukan asal-usul pasti. Pesan serupa mungkin sudah beredar lebih dulu.</p>
      )}
      <p className="text">{variant.body_anonymized}</p>
      <dl>
        <dt>Pertama kali diterima</dt>
        <dd>{formatDate(variant.first_seen_reported_at, variant.date_precision)}</dd>
        <dt>Jumlah laporan</dt>
        <dd>{variant.report_count}</dd>
      </dl>
      {parent && variant.edge_confidence === "low" && (
        <p className="note warn">Arah turunan tidak pasti: induk ini dipilih dengan kemiripan rendah atau ada kandidat lain.</p>
      )}
      {variant.mutation_summary && <p>{variant.mutation_summary}</p>}
      {mutations.length > 0 && (
        <>
          <h4>Mutasi dari induk</h4>
          <ul className="mutations">
            {mutations.map((m) => {
              const s = CATEGORY_STYLE[m.category];
              return (
                <li key={m.id}>
                  <span className="chip" style={{ background: s.bg, color: s.fg }}>{s.label}</span>{" "}
                  {m.before_text && <del>{m.before_text}</del>} {m.before_text && m.after_text && "→"} {m.after_text && <ins>{m.after_text}</ins>}
                </li>
              );
            })}
          </ul>
        </>
      )}
      {parent && <DiffView parent={parent.body_anonymized} child={variant.body_anonymized} />}
      <p>
        <Link href={`/hapus?varian=${variant.id}`}>Ajukan penghapusan varian ini</Link>
      </p>
    </section>
  );
}
