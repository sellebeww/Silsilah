import { NextResponse } from "next/server";
import { listFamilies, type SortKey } from "@/lib/data";

export async function GET(req: Request) {
  const p = new URL(req.url).searchParams;
  const sort: SortKey = p.get("urut") === "laporan" ? "laporan" : "terbaru";
  try {
    return NextResponse.json(await listFamilies(p.get("q") ?? "", sort));
  } catch {
    return NextResponse.json({ error: "Gagal memuat daftar keluarga" }, { status: 503 });
  }
}
