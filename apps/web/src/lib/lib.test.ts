import { describe, expect, it } from "vitest";
import { CATEGORY_STYLE, contrast, formatDate } from "./format";
import { matchPublisher, trustedLinks } from "./publishers";
import { buildTree } from "./tree";
import fixture from "@/test/fixture.json";
import type { Variant } from "./types";

describe("format", () => {
  it("tanggal mengikuti presisi", () => {
    expect(formatDate("2026-01-05", "day")).toBe("5 Januari 2026");
    expect(formatDate("2026-02-01", "month")).toContain("perkiraan bulan");
    expect(formatDate("2025-01-01", "year")).toContain("perkiraan tahun");
  });
  it("warna kategori memenuhi WCAG AA (>= 4,5)", () => {
    for (const s of Object.values(CATEGORY_STYLE)) expect(contrast(s.bg, s.fg)).toBeGreaterThanOrEqual(4.5);
  });
});

describe("matchPublisher", () => {
  const d = ["turnbackhoax.id"];
  it("menerima domain dan subdomain https", () => {
    expect(matchPublisher("https://turnbackhoax.id/a", d)).toBe("turnbackhoax.id");
    expect(matchPublisher("https://www.turnbackhoax.id/a", d)).toBe("turnbackhoax.id");
  });
  it("menolak http, userinfo, dan domain tiruan", () => {
    expect(matchPublisher("http://turnbackhoax.id/a", d)).toBeNull();
    expect(matchPublisher("https://turnbackhoax.id@evil.com/", d)).toBeNull();
    expect(matchPublisher("https://eviturnbackhoax.id/", d)).toBeNull();
    expect(matchPublisher("bukan url", d)).toBeNull();
  });
});

describe("buildTree", () => {
  const vs = fixture.variants as unknown as Variant[];
  it("akar = tertua yang dilaporkan, anak sesuai parent_id", () => {
    const root = buildTree(vs)!;
    expect(root.variant.is_oldest_reported).toBe(true);
    expect(root.children.map((c) => c.variant.id).sort()).toEqual([vs[1].id, vs[3].id].sort());
  });
  it("induk yang tidak terlihat digantung ke akar", () => {
    const orphan = { ...vs[2], parent_id: "00000000-0000-0000-0000-000000000000" };
    const root = buildTree([vs[0], orphan])!;
    expect(root.children[0].variant.id).toBe(orphan.id);
  });
  it("kosong -> null", () => expect(buildTree([])).toBeNull());
});

describe("trustedLinks", () => {
  const pubs = [{ domain: "turnbackhoax.id", name: "TurnBackHoax (MAFINDO)" }];
  const link = (url: string, publisher = "turnbackhoax.id") => ({ id: url, url, publisher, title: "t", verdict_label: null });
  it("menyertakan nama penerbit dari daftar resmi", () => {
    const [l] = trustedLinks([link("https://turnbackhoax.id/a")], pubs);
    expect(l.publisher_name).toBe("TurnBackHoax (MAFINDO)");
  });
  it("membuang penerbit tak terdaftar, domain tak cocok, dan non-https", () => {
    const out = trustedLinks(
      [link("https://jahat.example/a", "jahat.example"), link("https://jahat.example/a"), link("http://turnbackhoax.id/a"), link("javascript:alert(1)")],
      pubs,
    );
    expect(out).toEqual([]);
  });
});
