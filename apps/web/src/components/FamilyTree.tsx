"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { buildTree, layoutTree, NODE_H, NODE_W } from "@/lib/tree";
import { formatDate, formatDateShort } from "@/lib/format";
import type { FamilyDetail } from "@/lib/types";
import { VariantPanel } from "./VariantPanel";

const PAD = 16;

export function FamilyTree({ family }: { family: FamilyDetail }) {
  const root = useMemo(() => buildTree(family.variants), [family.variants]);
  const layout = useMemo(() => (root ? layoutTree(root) : null), [root]);
  const [selected, setSelected] = useState(root?.variant.id ?? "");
  const [zoom, setZoom] = useState(1);
  const refs = useRef(new Map<string, SVGGElement>());
  const moved = useRef(false);

  useEffect(() => {
    if (moved.current) refs.current.get(selected)?.focus();
  }, [selected]);

  if (!layout || !root) return <p>Belum ada varian yang dipublikasikan.</p>;

  const nodes = layout.descendants();
  const xs = nodes.map((n) => n.x);
  const minX = Math.min(...xs) - NODE_W / 2 - PAD;
  const w = Math.max(...xs) + NODE_W / 2 + PAD - minX;
  const h = Math.max(...nodes.map((n) => n.y)) + NODE_H + 2 * PAD;
  const byId = new Map(nodes.map((n) => [n.data.variant.id, n]));
  const order = new Map([...family.variants].sort((a, b) => a.first_seen_reported_at.localeCompare(b.first_seen_reported_at)).map((v, i) => [v.id, i + 1]));
  const current = byId.get(selected) ?? layout;
  const variant = current.data.variant;
  const parent = current.parent?.data.variant ?? null;

  function onKey(e: React.KeyboardEvent, id: string) {
    const n = byId.get(id)!;
    const sibs = n.parent?.children ?? [n];
    const i = sibs.indexOf(n);
    const next =
      e.key === "ArrowUp" ? n.parent : e.key === "ArrowDown" ? n.children?.[0] : e.key === "ArrowLeft" ? sibs[i - 1] : e.key === "ArrowRight" ? sibs[i + 1] : undefined;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      moved.current = true;
      setSelected(id);
    } else if (next) {
      e.preventDefault();
      moved.current = true;
      setSelected(next.data.variant.id);
    }
  }

  return (
    <div className="tree-layout">
      <div>
        <div className="toolbar" role="group" aria-label="Zoom pohon">
          <button type="button" onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))} aria-label="Perkecil pohon">−</button>
          <button type="button" onClick={() => setZoom(1)}>Atur ulang</button>
          <button type="button" onClick={() => setZoom((z) => Math.min(2, z + 0.25))} aria-label="Perbesar pohon">+</button>
          <span className="legend">
            <svg width="40" height="10" aria-hidden="true"><line x1="0" y1="5" x2="40" y2="5" stroke="#374151" strokeWidth="2" strokeDasharray="6 4" /></svg>{" "}
            = arah turunan tidak pasti
          </span>
        </div>
        <div className="tree-scroll" role="region" aria-label="Pohon mutasi (dapat digulir)">
          <svg
            viewBox={`${minX} ${-PAD} ${w} ${h}`}
            width={w * zoom}
            height={h * zoom}
            role="tree"
            aria-label={`Pohon mutasi: ${family.variants.length} varian. Gunakan tombol panah untuk berpindah, Enter untuk memilih.`}
          >
            {nodes.filter((n) => n.parent).map((n) => {
              const p = n.parent!;
              const low = n.data.variant.edge_confidence === "low";
              const y1 = p.y + NODE_H;
              const mid = (y1 + n.y) / 2;
              const d = `M${p.x},${y1} C${p.x},${mid} ${n.x},${mid} ${n.x},${n.y}`;
              return (
                <g key={`e-${n.data.variant.id}`}>
                  <path d={d} fill="none" stroke="#374151" strokeWidth={2} strokeDasharray={low ? "6 4" : undefined} />
                  {low && (
                    <>
                      <path d={d} fill="none" stroke="transparent" strokeWidth={14} />
                      <title>Arah turunan tidak pasti</title>
                    </>
                  )}
                </g>
              );
            })}
            {nodes.map((n) => {
              const v = n.data.variant;
              const sel = v.id === current.data.variant.id;
              return (
                <g
                  key={v.id}
                  ref={(el) => {
                    if (el) refs.current.set(v.id, el);
                    else refs.current.delete(v.id);
                  }}
                  role="treeitem"
                  aria-selected={sel}
                  aria-level={n.depth + 1}
                  tabIndex={sel ? 0 : -1}
                  aria-label={`Varian ${order.get(v.id)}${v.is_oldest_reported ? ", tertua yang dilaporkan" : ""}, ${formatDate(v.first_seen_reported_at, v.date_precision)}, ${v.report_count} laporan`}
                  transform={`translate(${n.x - NODE_W / 2},${n.y})`}
                  className="node"
                  onClick={() => setSelected(v.id)}
                  onKeyDown={(e) => onKey(e, v.id)}
                >
                  <rect width={NODE_W} height={NODE_H} rx={8} fill={v.is_oldest_reported ? "#fef3c7" : "#ffffff"} stroke={sel ? "#1d4ed8" : "#374151"} strokeWidth={sel ? 3 : 1.5} />
                  <text x={8} y={18} fontSize={11} fontWeight={700} fill="#111827">{v.is_oldest_reported ? "Tertua yang dilaporkan" : `Varian ${order.get(v.id)}`}</text>
                  <text x={8} y={34} fontSize={12} fill="#111827">{formatDateShort(v.first_seen_reported_at, v.date_precision)}</text>
                  <text x={8} y={49} fontSize={11} fill="#374151">{v.report_count} laporan</text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>
      <VariantPanel
        key={variant.id}
        variant={variant}
        parent={parent}
        mutations={family.mutations.filter((m) => m.variant_id === variant.id)}
      />
    </div>
  );
}
