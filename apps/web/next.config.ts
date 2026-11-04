import type { NextConfig } from "next";

const dev = process.env.NODE_ENV !== "production";
const origin = (u: string | undefined) => {
  try {
    return u ? new URL(u).origin : "";
  } catch {
    return "";
  }
};

// Browser hanya boleh bicara dengan situs ini, Supabase (auth), dan layanan NLP (kirim pesan).
const connect = ["'self'", origin(process.env.NEXT_PUBLIC_SUPABASE_URL), origin(process.env.NEXT_PUBLIC_NLP_URL), ...(dev ? ["ws:"] : [])]
  .filter(Boolean)
  .join(" ");

// shortcut: 'unsafe-inline' pada script-src karena Next menyisipkan skrip hidrasi inline; ganti ke CSP
// berbasis nonce lewat proxy.ts bila ada konten pengguna yang dirender sebagai HTML (saat ini tidak ada).
const csp = (frameAncestors: string, extra: string[] = []) =>
  [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    `connect-src ${connect}`,
    "object-src 'none'",
    "base-uri 'self'",
    `frame-ancestors ${frameAncestors}`,
    ...extra,
  ].join("; ");

const common = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), interest-cohort=()" },
];

const config: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [
      {
        // semua halaman kecuali widget: tidak boleh dibingkai situs lain
        source: "/((?!embed/).*)",
        headers: [
          ...common,
          { key: "Content-Security-Policy", value: csp("'none'", ["form-action 'self'", "frame-src 'self'"]) },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
      {
        // widget: sengaja boleh dibingkai di situs mana pun, tetapi tanpa form dan tanpa iframe turunan
        source: "/embed/:id",
        headers: [...common, { key: "Content-Security-Policy", value: csp("*", ["form-action 'none'", "frame-src 'none'"]) }],
      },
    ];
  },
};

export default config;
