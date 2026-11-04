import { diffWords } from "diff";

/** Dua kolom: induk (bagian yang hilang dicoret) dan anak (bagian baru digarisbawahi). Tidak hanya warna: ada coretan/garis bawah. */
export function DiffView({ parent, child }: { parent: string; child: string }) {
  const parts = diffWords(parent, child);
  return (
    <div className="diff" role="group" aria-label="Perbandingan dengan varian induk">
      <div>
        <h4>Induk</h4>
        <p data-testid="diff-parent">
          {parts.filter((p) => !p.added).map((p, i) => (p.removed ? <del key={i}>{p.value}</del> : <span key={i}>{p.value}</span>))}
        </p>
      </div>
      <div>
        <h4>Varian ini</h4>
        <p data-testid="diff-child">
          {parts.filter((p) => !p.removed).map((p, i) => (p.added ? <ins key={i}>{p.value}</ins> : <span key={i}>{p.value}</span>))}
        </p>
      </div>
    </div>
  );
}
