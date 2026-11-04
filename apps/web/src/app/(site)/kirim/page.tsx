"use client";
import { useState } from "react";
import { AuthGate, type Auth } from "@/components/AuthGate";
import { NLP_URL } from "@/lib/supabase-browser";

interface Result { is_duplicate: boolean; report_count: number; body_anonymized: string; entities_found: { type: string; count: number }[] }

function SubmitForm({ auth }: { auth: Auth }) {
  const [mode, setMode] = useState<"teks" | "gambar">("teks");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const today = new Date().toLocaleDateString("sv-SE");

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const meta = { first_seen_date: String(f.get("tanggal")), date_precision: String(f.get("presisi")) };
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const headers: Record<string, string> = { Authorization: `Bearer ${auth.token}` };
      let res: Response;
      if (mode === "teks") {
        res = await fetch(`${NLP_URL}/submit/text`, {
          method: "POST",
          headers: { ...headers, "Content-Type": "application/json" },
          body: JSON.stringify({ text: String(f.get("teks")), ...meta }),
        });
      } else {
        const body = new FormData();
        body.set("image", f.get("gambar") as File);
        body.set("first_seen_date", meta.first_seen_date);
        body.set("date_precision", meta.date_precision);
        res = await fetch(`${NLP_URL}/submit/image`, { method: "POST", headers, body });
      }
      if (res.ok) return setResult(await res.json());
      const j = await res.json().catch(() => ({}));
      const d = j.detail;
      setError(typeof d === "string" ? d : res.status === 422 ? "Isian tidak valid. Periksa teks (20–5000 karakter) dan tanggal." : "Pengiriman gagal.");
    } catch {
      setError("Layanan tidak dapat dihubungi.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form onSubmit={submit} className="form">
        <fieldset>
          <legend>Jenis kiriman</legend>
          <label><input type="radio" checked={mode === "teks"} onChange={() => setMode("teks")} /> Teks</label>{" "}
          <label><input type="radio" checked={mode === "gambar"} onChange={() => setMode("gambar")} /> Gambar (tangkapan layar)</label>
        </fieldset>
        {mode === "teks" ? (
          <>
            <label htmlFor="teks">Isi pesan</label>
            <textarea id="teks" name="teks" required minLength={20} maxLength={5000} rows={8} />
          </>
        ) : (
          <>
            <label htmlFor="gambar">Gambar (JPEG, PNG, atau WebP, maks. 5 MB)</label>
            <input id="gambar" name="gambar" type="file" required accept="image/jpeg,image/png,image/webp" />
          </>
        )}
        <label htmlFor="tanggal">Kapan pertama kali Anda menerima pesan ini?</label>
        <input id="tanggal" name="tanggal" type="date" required max={today} />
        <label htmlFor="presisi">Seberapa pasti tanggalnya?</label>
        <select id="presisi" name="presisi" defaultValue="day">
          <option value="day">Tanggal pasti</option>
          <option value="month">Perkiraan bulan</option>
          <option value="year">Perkiraan tahun</option>
        </select>
        <button type="submit" disabled={busy}>{busy ? "Mengirim…" : "Kirim"}</button>
      </form>
      {error && <p role="alert" className="error">{error}</p>}
      {result && (
        <div role="status" className="note">
          <p>{result.is_duplicate ? `Pesan ini sudah pernah dilaporkan (${result.report_count} laporan).` : "Terima kasih. Pesan menunggu tinjauan kurator."}</p>
          <p>Versi yang disimpan (setelah penyamaran):</p>
          <blockquote>{result.body_anonymized}</blockquote>
        </div>
      )}
    </>
  );
}

export default function Page() {
  return (
    <>
      <h1>Kirim pesan berantai</h1>
      <aside className="note" aria-label="Privasi">
        <strong>Privasi.</strong> Nomor telepon, nama, email, dan NIK disamarkan sebelum disimpan. Gambar asli tidak disimpan: hanya
        teksnya dibaca di memori lalu gambar dibuang. Kami tidak menyimpan akun, nomor pengirim, grup, lokasi, atau IP. Bila penyamaran
        gagal, kiriman ditolak.
      </aside>
      <AuthGate>{(auth) => <SubmitForm auth={auth} />}</AuthGate>
    </>
  );
}
