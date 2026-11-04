"use client";
import { useState } from "react";
import { AuthGate } from "@/components/AuthGate";
import { UUID_RE } from "@/lib/uuid";
import { supabase } from "@/lib/supabase-browser";

function TakedownForm() {
  const [status, setStatus] = useState<"" | "ok" | "gagal" | "tidak-valid">("");
  const initial = typeof window === "undefined" ? "" : (new URLSearchParams(window.location.search).get("varian") ?? "");

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const variant_id = String(f.get("varian")).trim();
    if (!UUID_RE.test(variant_id)) return setStatus("tidak-valid");
    // tanpa .select(): kontributor boleh menulis tetapi tidak membaca antrean takedown
    const { error } = await supabase().from("takedown_requests").insert({ variant_id, reason: String(f.get("alasan")) });
    setStatus(error ? "gagal" : "ok");
    if (!error) e.currentTarget.reset();
  }

  return (
    <form onSubmit={submit} className="form">
      <label htmlFor="varian">ID varian (ada di tautan &ldquo;Ajukan penghapusan&rdquo; pada panel varian)</label>
      <input id="varian" name="varian" required defaultValue={initial} pattern="[0-9a-fA-F-]{36}" />
      <label htmlFor="alasan">Alasan (10–2000 karakter; jangan menulis data pribadi)</label>
      <textarea id="alasan" name="alasan" required minLength={10} maxLength={2000} rows={5} />
      <button type="submit">Kirim permintaan</button>
      {status === "ok" && <p role="status">Permintaan diterima dan akan ditinjau kurator.</p>}
      {status === "tidak-valid" && <p role="alert" className="error">ID varian tidak valid.</p>}
      {status === "gagal" && <p role="alert" className="error">Permintaan gagal. Pastikan alasan tidak memuat nomor, email, atau NIK.</p>}
    </form>
  );
}

export default function Page() {
  return (
    <>
      <h1>Permintaan penghapusan</h1>
      <p className="note">Identitas pemohon tidak disimpan. Kurator meninjau setiap permintaan.</p>
      <AuthGate>{() => <TakedownForm />}</AuthGate>
    </>
  );
}
