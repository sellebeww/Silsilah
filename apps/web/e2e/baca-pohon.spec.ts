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
