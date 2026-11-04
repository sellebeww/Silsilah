import { hierarchy, tree, type HierarchyPointNode } from "d3-hierarchy";
import type { Variant } from "./types";

export interface TreeNode {
  variant: Variant;
  children: TreeNode[];
}

/** Susun variants (daftar datar) jadi pohon. Induk yang tidak terlihat publik -> digantung ke varian tertua yang dilaporkan. */
export function buildTree(variants: Variant[]): TreeNode | null {
  if (variants.length === 0) return null;
  const nodes = new Map(variants.map((v) => [v.id, { variant: v, children: [] as TreeNode[] }]));
  const root = variants.find((v) => v.is_oldest_reported) ?? variants.find((v) => !v.parent_id) ?? variants[0];
  for (const v of variants) {
    if (v.id === root.id) continue;
    const parent = (v.parent_id && nodes.get(v.parent_id)) || nodes.get(root.id)!;
    parent.children.push(nodes.get(v.id)!);
  }
  return nodes.get(root.id)!;
}

export const NODE_W = 150;
export const NODE_H = 56;
const GAP_X = 24;
const GAP_Y = 48;

export function layoutTree(root: TreeNode): HierarchyPointNode<TreeNode> {
  const h = hierarchy(root, (n) => n.children);
  return tree<TreeNode>().nodeSize([NODE_W + GAP_X, NODE_H + GAP_Y])(h);
}
