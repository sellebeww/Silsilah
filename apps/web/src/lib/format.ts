import type { MutationCategory, DatePrecision } from "./types";

const MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];

/** Tanggal sesuai presisinya; perkiraan diberi keterangan agar tidak tampak lebih pasti dari aslinya. */
export function formatDate(iso: string, precision: DatePrecision): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (precision === "year") return `${y} (perkiraan tahun)`;
  if (precision === "month") return `${MONTHS[m - 1]} ${y} (perkiraan bulan)`;
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

// Teks gelap pada latar terang; rasio kontras diuji di format.test.ts (WCAG AA >= 4,5).
export const CATEGORY_STYLE: Record<MutationCategory, { label: string; bg: string; fg: string }> = {
  number: { label: "Angka", bg: "#fde68a", fg: "#422006" },
  institution: { label: "Institusi", bg: "#bfdbfe", fg: "#172554" },
  call_to_action: { label: "Ajakan", bg: "#fbcfe8", fg: "#500724" },
  date: { label: "Tanggal", bg: "#bbf7d0", fg: "#052e16" },
  place: { label: "Tempat", bg: "#ddd6fe", fg: "#2e1065" },
  url: { label: "Tautan", bg: "#fed7aa", fg: "#431407" },
  other: { label: "Lainnya", bg: "#e5e7eb", fg: "#111827" },
};

function luminance(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = c.map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

export function formatDateShort(iso: string, precision: DatePrecision): string {
  const [y, m, d] = iso.split("-").map(Number);
  const mon = MONTHS[m - 1].slice(0, 3);
  if (precision === "year") return `~${y}`;
  if (precision === "month") return `~${mon} ${y}`;
  return `${d} ${mon} ${y}`;
}
