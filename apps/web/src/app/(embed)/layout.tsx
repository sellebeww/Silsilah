import type { Metadata } from "next";
import "../globals.css";

// Tanpa header/footer; halaman ini dimuat di iframe situs lain.
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function EmbedLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body className="embed-body">{children}</body>
    </html>
  );
}
