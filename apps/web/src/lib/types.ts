export type DatePrecision = "day" | "month" | "year";
export type MutationCategory = "number" | "institution" | "call_to_action" | "date" | "place" | "url" | "other";

export interface Variant {
  id: string;
  parent_id: string | null;
  body_anonymized: string;
  first_seen_reported_at: string;
  date_precision: DatePrecision;
  report_count: number;
  is_oldest_reported: boolean;
  edge_similarity: number | null;
  edge_confidence: "high" | "low" | null;
  alt_parent_ids: string[];
  mutation_summary: string | null;
}

export interface Mutation {
  id: string;
  variant_id: string;
  parent_variant_id: string;
  category: MutationCategory;
  before_text: string | null;
  after_text: string | null;
}

export interface FactcheckLink {
  id: string;
  url: string;
  publisher: string;
  title: string;
  verdict_label: string | null;
  /** Nama penerbit dari trusted_publishers (bukan dari input pengguna). */
  publisher_name: string;
}

export interface FamilySummary {
  id: string;
  title: string;
  created_at: string;
  variant_count: number;
  report_total: number;
  oldest: { first_seen_reported_at: string; date_precision: DatePrecision } | null;
}

export interface FamilyDetail {
  id: string;
  title: string;
  variants: Variant[];
  mutations: Mutation[];
  factcheck_links: FactcheckLink[];
}
