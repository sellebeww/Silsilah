import { NextResponse } from "next/server";
import { getFamily } from "@/lib/data";

export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const f = await getFamily((await params).id);
    return f ? NextResponse.json(f) : NextResponse.json({ error: "Tidak ditemukan" }, { status: 404 });
  } catch {
    return NextResponse.json({ error: "Gagal memuat keluarga" }, { status: 503 });
  }
}
