import type { Metadata } from "next";
import { EmbedBuilder } from "@/components/EmbedBuilder";
import { listFamilies } from "@/lib/data";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Sematkan di situs Anda", description: "Kode salin-tempel untuk menampilkan pohon mutasi satu keluarga pesan di artikel pemeriksaan fakta." };

export default async function Page() {
  const families = await listFamilies();
  return (
    <>
      <h1>Sematkan pohon mutasi</h1>
      <p>
        Untuk pemeriksa fakta dan redaksi: tampilkan pohon mini, varian tertua yang dilaporkan, dan tautan ke halaman lengkap di artikel
        Anda. Widget tidak memasang pelacak dan tidak menyimpan apa pun tentang pembaca.
      </p>
      <EmbedBuilder families={families.map((f) => ({ id: f.id, title: f.title }))} origin={process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"} />
    </>
  );
}
