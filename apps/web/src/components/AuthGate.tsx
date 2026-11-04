"use client";
import { useEffect, useState, type ReactNode } from "react";
import { supabase } from "@/lib/supabase-browser";

export interface Auth {
  token: string;
  role: "contributor" | "curator" | "admin";
}

/** Magic link Supabase Auth. Email hanya dipakai Supabase untuk masuk; laporan tidak dikaitkan ke akun. */
export function AuthGate({ children, need }: { children: (a: Auth) => ReactNode; need?: "curator" }) {
  const [state, setState] = useState<"loading" | "out" | Auth>("loading");
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    const load = async (token: string | null, uid: string | null) => {
      if (!token || !uid) return setState("out");
      const { data } = await supabase().from("contributors").select("role").eq("id", uid);
      setState({ token, role: (data?.[0]?.role ?? "contributor") as Auth["role"] });
    };
    const { data } = supabase().auth.onAuthStateChange((_e, s) => void load(s?.access_token ?? null, s?.user.id ?? null));
    return () => data.subscription.unsubscribe();
  }, []);

  async function login(e: React.FormEvent) {
    e.preventDefault();
    const { error } = await supabase().auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.href } });
    setMsg(error ? "Gagal mengirim tautan masuk. Coba lagi." : "Tautan masuk sudah dikirim. Periksa email Anda.");
  }

  if (state === "loading") return <p role="status">Memeriksa sesi…</p>;
  if (state === "out")
    return (
      <form onSubmit={login} className="form">
        <p>Masuk dulu dengan tautan ajaib (magic link) yang dikirim ke email. Email hanya dipakai untuk masuk, tidak dikaitkan dengan isi laporan.</p>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <button type="submit">Kirim tautan masuk</button>
        {msg && <p role="status">{msg}</p>}
      </form>
    );
  if (need === "curator" && state.role === "contributor") return <p role="alert">Halaman ini hanya untuk kurator.</p>;
  return (
    <>
      <p>
        <button type="button" className="link" onClick={() => void supabase().auth.signOut()}>Keluar</button>
      </p>
      {children(state)}
    </>
  );
}
