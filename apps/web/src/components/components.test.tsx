import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import fixture from "@/test/fixture.json";
import type { FamilyDetail } from "@/lib/types";
import { DiffView } from "./DiffView";
import { FamilyTree } from "./FamilyTree";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
afterEach(cleanup);

const family = { ...fixture.families[0], variants: fixture.variants, mutations: fixture.mutations, factcheck_links: fixture.factcheck_links } as unknown as FamilyDetail;

describe("DiffView", () => {
  it("menandai kata yang hilang di induk dan yang baru di anak", () => {
    render(<DiffView parent="bantuan Rp 500.000 untuk keluarga" child="bantuan Rp 1.000.000 untuk keluarga" />);
    expect(screen.getByTestId("diff-parent").querySelector("del")).toHaveTextContent("500.000");
    expect(screen.getByTestId("diff-child").querySelector("ins")).toHaveTextContent("1.000.000");
  });
});

describe("FamilyTree", () => {
  it("merender satu node per varian dan satu lencana tertua", () => {
    render(<FamilyTree family={family} />);
    expect(screen.getAllByRole("treeitem")).toHaveLength(4);
    expect(screen.getAllByRole("treeitem").filter((n) => /tertua yang dilaporkan/.test(n.getAttribute("aria-label")!))).toHaveLength(1);
  });
  it("edge low digambar putus-putus dengan tooltip", () => {
    const { container } = render(<FamilyTree family={family} />);
    expect(container.querySelectorAll("path[stroke-dasharray]")).toHaveLength(1);
    expect(container.querySelector("title")).toHaveTextContent("Arah turunan tidak pasti");
  });
  it("memilih node membuka panel dengan mutasi berlabel dan diff", () => {
    render(<FamilyTree family={family} />);
    fireEvent.click(screen.getAllByRole("treeitem")[1]);
    expect(screen.getByTestId("panel")).toHaveTextContent("Angka");
    expect(screen.getByTestId("diff-child").querySelector("ins")).toBeInTheDocument();
  });
  it("panah bawah pindah ke anak", () => {
    render(<FamilyTree family={family} />);
    const root = screen.getAllByRole("treeitem").find((n) => n.getAttribute("aria-selected") === "true")!;
    fireEvent.keyDown(root, { key: "ArrowDown" });
    expect(screen.getByTestId("panel")).toHaveTextContent("Pertama kali diterima");
    expect(screen.getAllByRole("treeitem").find((n) => n.getAttribute("aria-selected") === "true")).not.toBe(root);
  });
});
