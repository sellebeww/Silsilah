"use client";
import { useCallback, useEffect, useState } from "react";
import { AuthGate, type Auth } from "@/components/AuthGate";
import { formatDate } from "@/lib/format";
import { matchPublisher } from "@/lib/publishers";
import { NLP_URL, supabase } from "@/lib/supabase-browser";
import type { DatePrecision } from "@/lib/types";

interface Pending { id: string; body_anonymized: string; first_seen_reported_at: string; date_precision: DatePrecision; report_count: number }
interface Fam { id: string; title: string; status: "pending" | "published" | "hidden"; factcheck_links: { id: string; url: string; title: string; publisher: string }[] }
interface Suggest { id: string; family_id: string; merge_suggestion: string[] }

function Dashboard({ auth }: { auth: Auth }) {
  const [pending, setPending] = useState<Pending[]>([]);
  const [fams, setFams] = useState<Fam[]>([]);
  const [suggest, setSuggest] = useState<Suggest[]>([]);
  const [domains, setDomains] = useState<string[]>([]);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const db = supabase();
    const [p, f, s, d] = await Promise.all([
      db.from("variants").select("id,body_anonymized,first_seen_reported_at,date_precision,report_count").eq("moderation_status", "pending").order("submitted_at"),
      db.from("families").select("id,title,status,factcheck_links(id,url,title,publisher)").order("created_at", { ascending: false }),
      db.from("variants").select("id,family_id,merge_suggestion").neq("merge_suggestion", "{}"),
      db.from("trusted_publishers").select("domain"),
    ]);
    if (p.error || f.error || s.error || d.error) return setMsg("Gagal memuat data kurasi.");
    setPending(p.data as Pending[]);
    setFams(f.data as Fam[]);
    setSuggest(s.data as Suggest[]);
    setDomains(d.data.map((r) => r.domain));
  }, []);
  // Pengambilan data awal: setState terjadi setelah await, bukan sinkron; aturan lint terlalu konservatif di sini.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, [load]);

  const title = (id: string) => fams.find((f) => f.id === id)?.title ?? id;
  const run = async (fn: () => PromiseLike<{ error: unknown }>, ok: string) => {
    const { error } = await fn();
    setMsg(error ? "Aksi gagal." : ok);
    await load();
  };

  async function approve(id: string) {
    const res = await fetch(`${NLP_URL}/moderation/variants/${id}/approve`, { method: "POST", headers: { Authorization: `Bearer ${auth.token}` } });
    const j = await res.json().catch(() => ({}));
    setMsg(res.ok ? (j.new_family ? "Disetujui: keluarga baru dibuat (status pending, beri judul lalu publikasikan)." : "Disetujui dan ditempatkan di pohon.") : (typeof j.detail === "string" ? j.detail : "Persetujuan gagal."));
    await load();
  }

  async function addLink(e: React.FormEvent<HTMLFormElement>, family_id: string) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const url = String(f.get("url")).trim();
    const publisher = matchPublisher(url, domains);
    if (!publisher) return setMsg("Tautan ditolak: harus https dan dari domain sumber resmi (trusted_publishers).");
    await run(() => supabase().from("factcheck_links").insert({ family_id, url, publisher, title: String(f.get("judul")), verdict_label: String(f.get("vonis")) || null }), "Tautan ditambahkan.");
    form.reset();
  }

  return (
    <>
      {msg && <p role="status" className="note">{msg}</p>}
      <h2>Antrean pending ({pending.length})</h2>
      {pending.length === 0 && <p>Tidak ada antrean.</p>}
      <ul className="cards">
        {pending.map((v) => (
          <li key={v.id}>
            <p>{v.body_anonymized}</p>
            <p>{formatDate(v.first_seen_reported_at, v.date_precision)} · {v.report_count} laporan</p>
            <button type="button" onClick={() => void approve(v.id)}>Setujui</button>{" "}
            <button type="button" onClick={() => void run(() => supabase().from("variants").update({ moderation_status: "rejected" }).eq("id", v.id), "Ditolak.")}>Tolak</button>
          </li>
        ))}
      </ul>

      {suggest.length > 0 && (
        <>
          <h2>Saran gabung keluarga</h2>
          <p className="note">Tidak pernah digabung otomatis; keputusan ada pada kurator.</p>
          <ul>
            {suggest.map((s) => (
              <li key={s.id}>&ldquo;{title(s.family_id)}&rdquo; mirip dengan {s.merge_suggestion.map((id) => `“${title(id)}”`).join(", ")}</li>
            ))}
          </ul>
        </>
      )}

      <h2>Keluarga</h2>
      {fams.map((f) => (
        <section key={f.id} className="card" aria-label={f.title}>
          <form
            className="form inline"
            onSubmit={(e) => {
              e.preventDefault();
              const d = new FormData(e.currentTarget);
              void run(() => supabase().from("families").update({ title: String(d.get("judul")), status: String(d.get("status")) }).eq("id", f.id), "Keluarga disimpan.");
            }}
          >
            <label htmlFor={`j-${f.id}`}>Judul netral</label>
            <input id={`j-${f.id}`} name="judul" defaultValue={f.title} minLength={3} maxLength={200} required />
            <label htmlFor={`s-${f.id}`}>Status</label>
            <select id={`s-${f.id}`} name="status" defaultValue={f.status}>
              <option value="pending">pending</option>
              <option value="published">published</option>
              <option value="hidden">hidden</option>
            </select>
            <button type="submit">Simpan</button>
          </form>
          <h3>Tautan pemeriksaan fakta</h3>
          <ul>
            {f.factcheck_links.map((l) => (
              <li key={l.id}>
                {l.title} ({l.publisher}){" "}
                <button type="button" onClick={() => void run(() => supabase().from("factcheck_links").delete().eq("id", l.id), "Tautan dihapus.")}>Hapus</button>
              </li>
            ))}
          </ul>
          <form className="form inline" onSubmit={(e) => void addLink(e, f.id)}>
            <label htmlFor={`u-${f.id}`}>URL (sumber resmi saja)</label>
            <input id={`u-${f.id}`} name="url" type="url" required />
            <label htmlFor={`t-${f.id}`}>Judul artikel</label>
            <input id={`t-${f.id}`} name="judul" required minLength={3} maxLength={300} />
            <label htmlFor={`v-${f.id}`}>Vonis (opsional)</label>
            <input id={`v-${f.id}`} name="vonis" maxLength={100} />
            <button type="submit">Tambah tautan</button>
          </form>
        </section>
      ))}
      <p className="note">Sumber resmi yang diizinkan: {domains.join(", ") || "—"}</p>
    </>
  );
}

export default function Page() {
  return (
    <>
      <h1>Kurasi</h1>
      <AuthGate need="curator">{(auth) => <Dashboard auth={auth} />}</AuthGate>
    </>
  );
}
