import type { MetadataRoute } from "next";
import { api } from "@/lib/api";
import type { Category } from "@/lib/api/types";
import { SITE_URL } from "@/lib/config";

export const revalidate = 3600;

function flatten(tree: Category[]): Category[] {
  return tree.flatMap((c) => [c, ...flatten(c.children)]);
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const pages: MetadataRoute.Sitemap = [
    { url: SITE_URL, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/catalog`, changeFrequency: "daily", priority: 0.9 },
  ];
  try {
    const [categories, first] = await Promise.all([
      api.catalog.categories(),
      api.catalog.products({ page_size: 100 }),
    ]);
    // Для больших каталогов стоит перейти на generateSitemaps с разбивкой по 50 000 ссылок.
    const rest = await Promise.all(
      Array.from({ length: Math.ceil(first.count / 100) - 1 }, (_, i) =>
        api.catalog.products({ page_size: 100, page: i + 2 }),
      ),
    );
    const products = [first, ...rest].flatMap((p) => p.results);
    pages.push(
      ...flatten(categories).map((c) => ({
        url: `${SITE_URL}/catalog/${c.slug}`,
        changeFrequency: "weekly" as const,
        priority: 0.8,
      })),
      ...products.map((p) => ({
        url: `${SITE_URL}/product/${p.slug}`,
        lastModified: p.created_at,
        changeFrequency: "weekly" as const,
        priority: 0.7,
      })),
    );
  } catch {
    // без бэкенда отдаём хотя бы статические страницы
  }
  return pages;
}
