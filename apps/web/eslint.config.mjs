import next from "eslint-config-next";

const config = [...next, { ignores: [".next/**", "e2e/mock-supabase.mjs"] }];

export default config;
