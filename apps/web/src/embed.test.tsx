import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it } from "vitest";
import { EmbedBuilder, embedSnippets } from "@/components/EmbedBuilder";
import { MiniTree } from "@/components/MiniTree";
import fixture from "@/test/fixture.json";
import type { Variant } from "@/lib/types";
import config from "../next.config";

afterEach(cleanup);
const ID = "f000000a-0000-0000-0000-000000000000";

describe("MiniTree", () => {
  it("satu lingkaran per varian, satu yang tertua, edge ragu putus-putus", () => {
    const { container } = render(<MiniTree variants={fixture.variants as unknown as Variant[]} />);
    expect(container.querySelectorAll("circle")).toHaveLength(4);
    expect(container.querySelectorAll('circle[fill="#fef3c7"]')).toHaveLength(1);
    expect(container.querySelectorAll("path[stroke-dasharray]")).toHaveLength(1);
    expect(screen.getByRole("img")).toHaveAccessibleName(/varian tertua yang dilaporkan/);
  });
});

describe("EmbedBuilder", () => {
  it("kode salin-tempel memuat ID, origin, dan iframe tersandbox", () => {
    const s = embedSnippets("https://silsilah.example", ID);
    expect(s.script).toContain(`data-silsilah-id="${ID}"`);
    expect(s.script).toContain('src="https://silsilah.example/embed.js"');
    expect(s.iframe).toContain(`https://silsilah.example/embed/${ID}`);
    expect(s.iframe).toContain("sandbox=");
    render(<EmbedBuilder families={[{ id: ID, title: "Uji" }]} origin="https://silsilah.example" />);
    expect(screen.getAllByRole("button", { name: "Salin kode" })).toHaveLength(2);
  });
});

describe("embed.js", () => {
  function run(attrs: Record<string, string>) {
    document.body.innerHTML = "";
    const node = document.createElement("div");
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    document.body.append(node);
    const script = document.createElement("script");
    script.src = "https://silsilah.example/embed.js";
    Object.defineProperty(document, "currentScript", { value: script, configurable: true });
    new Function(readFileSync("public/embed.js", "utf8"))();
    return node;
  }
  it("menyisipkan iframe tersandbox dan menyesuaikan tinggi hanya dari jendela iframe itu", () => {
    const node = run({ "data-silsilah-id": ID });
    const f = node.querySelector("iframe")!;
    expect(f.src).toBe(`https://silsilah.example/embed/${ID}`);
    expect(f.getAttribute("sandbox")).not.toContain("allow-same-origin");
    window.dispatchEvent(new MessageEvent("message", { data: { type: "silsilah:height", height: 700 }, source: window }));
    expect(f.style.height).toBe("460px"); // pengirim bukan iframe ini
    window.dispatchEvent(new MessageEvent("message", { data: { type: "silsilah:height", height: 700 }, source: f.contentWindow }));
    expect(f.style.height).toBe("700px");
  });
  it("menolak ID yang bukan UUID", () => {
    expect(run({ "data-silsilah-id": '"><script>x</script>' }).querySelector("iframe")).toBeNull();
  });
});

describe("header keamanan", () => {
  it("widget boleh dibingkai, halaman lain tidak", async () => {
    const rules = await config.headers!();
    const get = (src: string, key: string) => rules.find((r) => r.source === src)!.headers.find((h) => h.key === key)?.value;
    expect(get("/embed/:id", "Content-Security-Policy")).toContain("frame-ancestors *");
    expect(get("/embed/:id", "X-Frame-Options")).toBeUndefined();
    const other = rules.find((r) => r.source !== "/embed/:id")!;
    expect(other.headers.find((h) => h.key === "X-Frame-Options")?.value).toBe("DENY");
    expect(other.headers.find((h) => h.key === "Content-Security-Policy")?.value).toContain("frame-ancestors 'none'");
    expect(other.headers.map((h) => h.key)).toEqual(expect.arrayContaining(["Strict-Transport-Security", "Referrer-Policy"]));
    expect(new RegExp(`^${other.source}$`).test("/embed/abc")).toBe(false);
  });
});
