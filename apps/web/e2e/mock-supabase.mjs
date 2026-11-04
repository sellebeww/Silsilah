// PostgREST palsu untuk e2e: melayani fixture sintetis, tanpa Docker. Hanya GET, filter eq/in/ilike.
import { createServer } from "node:http";
import { readFileSync } from "node:fs";

const data = JSON.parse(readFileSync(new URL("../src/test/fixture.json", import.meta.url), "utf8"));
const NON_FILTER = new Set(["select", "order", "limit"]);

function matches(row, key, val) {
  const [op, ...rest] = val.split(".");
  const arg = rest.join(".");
  if (op === "eq") return String(row[key]) === arg;
  if (op === "in") return arg.slice(1, -1).split(",").includes(String(row[key]));
  if (op === "ilike") return String(row[key]).toLowerCase().includes(arg.replaceAll("*", "").replaceAll("%", "").toLowerCase());
  return true;
}

createServer((req, res) => {
  const u = new URL(req.url, "http://x");
  res.setHeader("content-type", "application/json");
  if (u.pathname === "/health") return res.end("{}");
  const table = u.pathname.replace("/rest/v1/", "");
  if (!(table in data)) return res.writeHead(404).end("[]");
  let rows = data[table].filter((r) => [...u.searchParams].every(([k, v]) => NON_FILTER.has(k) || matches(r, k, v)));
  if (table === "families" && (u.searchParams.get("select") ?? "").includes("variants(")) {
    rows = rows.map((f) => ({ ...f, variants: data.variants.filter((v) => v.family_id === f.id) }));
  }
  res.end(JSON.stringify(rows));
}).listen(54399);
