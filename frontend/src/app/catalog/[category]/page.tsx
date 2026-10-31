import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CatalogView } from "@/components/catalog/catalog-view";
import { api } from "@/lib/api";
import { parseProductQuery, type SearchParams } from "@/lib/catalog-params";
import { findCategoryPath } from "@/lib/category-tree";

interface Props {
  params: Promise<{ category: string }>;
  searchParams: Promise<SearchParams>;
}

async function loadPath(slug: string) {
  const tree = await api.catalog.categories();
  return findCategoryPath(tree, slug);
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params;
  const path = await loadPath(category);
  if (!path) return { title: "Категория не найдена" };
  const current = path.at(-1)!;
  return {
    title: `${current.name} — купить с доставкой`,
    description: `${current.name}: актуальные модели, честные цены, официальная гарантия и быстрая доставка.`,
    alternates: { canonical: `/catalog/${current.slug}` },
    openGraph: { title: current.name, images: current.image ? [current.image] : undefined },
  };
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const [{ category }, sp] = await Promise.all([params, searchParams]);
  const path = await loadPath(category);
  if (!path) notFound();

  const current = path.at(-1)!;
  const parent = path.at(-2);
  // У листовой категории показываем соседей, чтобы можно было переключаться между ними.
  const subcategories = current.children.length ? current.children : (parent?.children ?? []);

  return (
    <CatalogView
      title={current.name}
      crumbs={[
        { label: "Каталог", href: "/catalog" },
        ...path.map((c) => ({ label: c.name, href: `/catalog/${c.slug}` })),
      ]}
      basePath={`/catalog/${current.slug}`}
      query={{ ...parseProductQuery(sp), category: current.slug }}
      searchParams={sp}
      subcategories={subcategories}
      activeCategory={current.slug}
    />
  );
}
