import type { Category } from "@/lib/api/types";

/** Ищет категорию в дереве и возвращает путь от корня (для хлебных крошек). */
export function findCategoryPath(tree: Category[], slug: string): Category[] | null {
  for (const node of tree) {
    if (node.slug === slug) return [node];
    const sub = findCategoryPath(node.children, slug);
    if (sub) return [node, ...sub];
  }
  return null;
}
