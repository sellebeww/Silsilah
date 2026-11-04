import type { Metadata } from "next";
import Link from "next/link";
import "../globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: { default: "Silsilah", template: "%s · Silsilah" },
  description: "Hoaks punya keluarga. Temukan leluhurnya: varian tertua yang dilaporkan dari pesan berantai.",
  openGraph: { siteName: "Silsilah", locale: "id_ID", type: "website" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>
        <a href="#isi" className="skip">Langsung ke isi</a>
        <header>
          <Link href="/" className="brand">Silsilah</Link>
          <nav aria-label="Utama">
            <Link href="/">Keluarga</Link>
            <Link href="/kirim">Kirim pesan</Link>
            <Link href="/kurasi">Kurasi</Link>
            <Link href="/embed">Sematkan</Link>
            <Link href="/hapus">Minta hapus</Link>
          </nav>
        </header>
        <main id="isi">{children}</main>
        <footer>
          <p>Yang dilacak adalah isi pesan, bukan orang. Tanpa pelacak dan analitik pihak ketiga.</p>
        </footer>
      </body>
    </html>
  );
}
