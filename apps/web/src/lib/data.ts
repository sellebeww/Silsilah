import { createClient } from "@supabase/supabase-js";
import { UUID_RE } from "./uuid";
import type { FamilyDetail, FamilySummary } from "./types";

// Hanya anon key: RLS membatasi ke keluarga published dan varian approved.
function db() {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    auth: { persistSession: false },
  });
}

export type SortKey = "terbaru" | "laporan";

const escapeLike = (s: string) => s.replace(/[\\%_]/g, "\\$&");

export async function listFamilies(q = "", sort: SortKey = "terbaru"): Promise<FamilySummary[]> {
  let query = db()
    .from("families")
    .select("id,title,created_at,variants(report_count,is_oldest_reported,first_seen_reported_at,date_precision)")
    .order("created_at", { ascending: false })
    .limit(100);
  const term = q.trim().slice(0, 100);
  if (term) query = query.ilike("title", `%${escapeLike(term)}%`);
  const { data, error } = await query;
  if (error) throw new Error("Gagal memuat daftar keluarga");
  const rows = (data ?? []).map((f) => {
    const oldest = f.variants.find((v) => v.is_oldest_reported) ?? null;
    return {
      id: f.id,
      title: f.title,
      created_at: f.created_at,
      variant_count: f.variants.length,
      report_total: f.variants.reduce((n, v) => n + v.report_count, 0),
      oldest: oldest && { first_seen_reported_at: oldest.first_seen_reported_at, date_precision: oldest.date_precision },
    } as FamilySummary;
  });
  return sort === "laporan" ? rows.sort((a, b) => b.report_total - a.report_total) : rows;
}

export async function getFamily(id: string): Promise<FamilyDetail | null> {
  if (!UUID_RE.test(id)) return null;
  const c = db();
  const [fam, vars, links] = await Promise.all([
    c.from("families").select("id,title").eq("id", id),
    c
      .from("variants")
      .select(
        "id,parent_id,body_anonymized,first_seen_reported_at,date_precision,report_count,is_oldest_reported,edge_similarity,edge_confidence,alt_parent_ids,mutation_summary",
      )
      .eq("family_id", id)
      .order("first_seen_reported_at"),
    c.from("factcheck_links").select("id,url,publisher,title,verdict_label").eq("family_id", id),
  ]);
  if (fam.error || vars.error || links.error) throw new Error("Gagal memuat keluarga");
  if (!fam.data?.length) return null;
  const ids = vars.data.map((v) => v.id);
  const muts = ids.length
    ? await c.from("mutations").select("id,variant_id,parent_variant_id,category,before_text,after_text").in("variant_id", ids)
    : { data: [], error: null };
  if (muts.error) throw new Error("Gagal memuat mutasi");
  return {
    ...fam.data[0],
    variants: vars.data as FamilyDetail["variants"],
    mutations: muts.data as FamilyDetail["mutations"],
    factcheck_links: links.data,
  };
}
