"use client";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | undefined;

/** Satu klien per tab; sesi (magic link) disimpan supabase-js di localStorage. Hanya anon key. */
export function supabase(): SupabaseClient {
  client ??= createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);
  return client;
}

export const NLP_URL = process.env.NEXT_PUBLIC_NLP_URL ?? "http://localhost:8000";
