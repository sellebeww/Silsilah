"use client";
import { useState } from "react";

export function embedSnippets(origin: string, id: string) {
  return {
    script: `<div data-silsilah-id="${id}"></div>\n<script async src="${origin}/embed.js"></script>`,
    iframe: `<iframe src="${origin}/embed/${id}" title="Pohon mutasi pesan berantai (Silsilah)" width="100%" height="460" style="max-width:640px;border:1px solid #9ca3af;border-radius:8px" loading="lazy" referrerpolicy="no-referrer" sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"></iframe>`,
  };
}

function Snippet({ id, label, code }: { id: string; label: string; code: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
    } catch {
      setCopied(false); // izin clipboard ditolak: pengguna masih bisa menyalin dari kotak teks
    }
  }
  return (
    <div className="form">
      <label htmlFor={id}>{label}</label>
      <textarea id={id} readOnly rows={4} value={code} onFocus={(e) => e.currentTarget.select()} />
      <button type="button" onClick={copy}>Salin kode</button>
      <p role="status">{copied ? "Kode disalin." : ""}</p>
    </div>
  );
}

export function EmbedBuilder({ families, origin }: { families: { id: string; title: string }[]; origin: string }) {
  const [id, setId] = useState(families[0]?.id ?? "");
  if (!id) return <p>Belum ada keluarga yang dipublikasikan.</p>;
  const s = embedSnippets(origin, id);
  return (
    <>
      <div className="form">
        <label htmlFor="keluarga">Pilih keluarga pesan</label>
        <select id="keluarga" value={id} onChange={(e) => setId(e.target.value)}>
          {families.map((f) => (
            <option key={f.id} value={f.id}>{f.title}</option>
          ))}
        </select>
      </div>
      <Snippet id="kode-skrip" label="Kode skrip (disarankan; tinggi menyesuaikan otomatis)" code={s.script} />
      <Snippet id="kode-iframe" label="Kode iframe (bila situs melarang skrip pihak ketiga)" code={s.iframe} />
      <h2>Pratinjau</h2>
      <iframe key={id} src={`/embed/${id}`} title="Pratinjau widget" className="embed-preview" />
    </>
  );
}
