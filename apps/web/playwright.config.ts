import { defineConfig } from "@playwright/test";

// Supabase palsu (data sintetis) agar e2e tidak butuh Docker.
const MOCK = "http://localhost:54399";

export default defineConfig({
  testDir: "e2e",
  webServer: [
    { command: "node e2e/mock-supabase.mjs", url: `${MOCK}/health`, reuseExistingServer: false },
    {
      command: "npm run dev -- --port 3100",
      url: "http://localhost:3100",
      reuseExistingServer: false,
      env: { NEXT_PUBLIC_SUPABASE_URL: MOCK, NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon-test", NEXT_PUBLIC_NLP_URL: "http://localhost:8000" },
    },
  ],
  use: { baseURL: "http://localhost:3100" },
});
