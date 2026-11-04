import { expect, test } from "@playwright/test";

test("baca pohon: beranda -> keluarga -> pilih node -> panel + diff", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("bukan asal-usul pasti", { exact: false })).toBeVisible();
  await page.getByRole("link", { name: "Klaim bantuan tunai dari lembaga fiktif" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toContainText("bantuan tunai");
  await expect(page.getByRole("treeitem")).toHaveCount(4);
  await expect(page.getByRole("treeitem", { name: /tertua yang dilaporkan/ })).toHaveCount(1);

  // navigasi keyboard: panah bawah ke anak pertama, lalu panel menampilkan mutasi dan diff
  await page.getByRole("treeitem", { name: /tertua yang dilaporkan/ }).focus();
  await page.keyboard.press("ArrowDown");
  const panel = page.getByTestId("panel");
  await expect(panel).toContainText("Angka");
  await expect(panel.getByTestId("diff-child").locator("ins")).toContainText("1.000.000");
  await expect(panel.getByTestId("diff-parent").locator("del")).toContainText("500.000");
});

test("edge low berputus-putus", async ({ page }) => {
  await page.goto("/keluarga/f000000a-0000-0000-0000-000000000000");
  await expect(page.locator("svg path[stroke-dasharray]").first()).toBeVisible();
  await expect(page.locator("svg title", { hasText: "Arah turunan tidak pasti" })).toHaveCount(1);
});

const FAM = "f000000a-0000-0000-0000-000000000000";

test("fact-check resmi: hanya penerbit terdaftar, rel aman", async ({ page }) => {
  await page.goto(`/keluarga/${FAM}`);
  await expect(page.getByRole("heading", { name: "Hasil pemeriksaan fakta resmi" })).toBeVisible();
  const links = page.locator("#fc a");
  await expect(links).toHaveCount(1); // tautan jahat.example di fixture tidak ditampilkan
  await expect(links.first()).toHaveAttribute("rel", "noopener noreferrer nofollow");
  await expect(page.locator("#fc")).toContainText("Pemeriksa Fakta Contoh");
  await expect(page.locator("#fc")).toContainText("Hoaks");
});

test("widget embed: ringkas tanpa header/footer, boleh dibingkai; halaman lain tidak", async ({ page, request }) => {
  const res = await page.goto(`/embed/${FAM}`);
  expect(res!.headers()["content-security-policy"]).toContain("frame-ancestors *");
  await expect(page.locator("header, footer")).toHaveCount(0);
  await expect(page.getByText("Tertua yang dilaporkan")).toBeVisible();
  await expect(page.getByRole("img", { name: /Pohon mutasi/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Lihat lengkap/ })).toHaveAttribute("href", new RegExp(`/keluarga/${FAM}$`));
  const full = await request.get(`/keluarga/${FAM}`);
  expect(full.headers()["x-frame-options"]).toBe("DENY");
  expect(full.headers()["content-security-policy"]).toContain("frame-ancestors 'none'");
});

test("halaman /embed memberi kode salin-tempel", async ({ page }) => {
  await page.goto("/embed");
  await expect(page.getByLabel(/Kode skrip/)).toHaveValue(new RegExp(`data-silsilah-id="${FAM}"`));
  await expect(page.getByLabel(/Kode iframe/)).toHaveValue(/sandbox=/);
});

test("embed.js menyisipkan iframe widget", async ({ page }) => {
  await page.route("http://host.test/", (r) =>
    r.fulfill({ contentType: "text/html", body: `<div data-silsilah-id="${FAM}"></div><script async src="http://localhost:3100/embed.js"></script>` }),
  );
  await page.goto("http://host.test/");
  await expect(page.locator("iframe")).toHaveAttribute("src", `http://localhost:3100/embed/${FAM}`);
  await expect(page.frameLocator("iframe").getByText("Tertua yang dilaporkan")).toBeVisible();
});
