import { buildTree, layoutTree, NODE_W } from "@/lib/tree";
import type { Variant } from "@/lib/types";

const R = 22;
const PAD = 12;

/** Pohon mini non-interaktif untuk widget. Komponen server: tanpa JS di klien. */
export function MiniTree({ variants }: { variants: Variant[] }) {
  const root = buildTree(variants);
  if (!root) return null;
  const nodes = layoutTree(root).descendants();
  const xs = nodes.map((n) => n.x);
  const minX = Math.min(...xs) - NODE_W / 2;
  const w = Math.max(...xs) + NODE_W / 2 - minX;
  const h = Math.max(...nodes.map((n) => n.y)) + 2 * R + 2 * PAD;
  return (
    <svg
      viewBox={`${minX} ${-PAD} ${w} ${h}`}
      className="mini-tree"
      role="img"
      aria-label={`Pohon mutasi: ${variants.length} varian. Lingkaran kuning di puncak adalah varian tertua yang dilaporkan.`}
    >
      {nodes.filter((n) => n.parent).map((n) => {
        const p = n.parent!;
        const low = n.data.variant.edge_confidence === "low";
        return (
          <path
            key={`e-${n.data.variant.id}`}
            d={`M${p.x},${p.y + R} C${p.x},${(p.y + n.y) / 2} ${n.x},${(p.y + n.y) / 2} ${n.x},${n.y - R}`}
            fill="none"
            stroke="#374151"
            strokeWidth={3}
            strokeDasharray={low ? "8 6" : undefined}
          />
        );
      })}
      {nodes.map((n) => (
        <circle
          key={n.data.variant.id}
          cx={n.x}
          cy={n.y}
          r={R}
          fill={n.data.variant.is_oldest_reported ? "#fef3c7" : "#ffffff"}
          stroke={n.data.variant.is_oldest_reported ? "#92400e" : "#374151"}
          strokeWidth={n.data.variant.is_oldest_reported ? 5 : 3}
        />
      ))}
    </svg>
  );
}
