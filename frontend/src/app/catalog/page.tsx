import type { Metadata } from "next";
import { CatalogView } from "@/components/catalog/catalog-view";
import { api } from "@/lib/api";
import { parseProductQuery, type SearchParams } from "@/lib/catalog-params";

interface Props {
  searchParams: Promise<SearchParams>;
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const sp = await searchParams;
  const onSale = sp.on_sale === "1";
  return {
    title: onSale ? "Скидки на электронику" : "Каталог электроники",
    description:
      "Смартфоны, ноутбуки, аудио, умные часы и техника для игр с доставкой и гарантией.",
    alternates: { canonical: onSale ? "/catalog?on_sale=1" : "/catalog" },
  };
}

export default async function CatalogPage({ searchParams }: Props) {
  const sp = await searchParams;
  const categories = await api.catalog.categories();
  const onSale = sp.on_sale === "1";
  return (
    <CatalogView
      title={onSale ? "Скидки" : "Каталог"}
      description={onSale ? "Товары со сниженной ценой" : undefined}
      crumbs={[{ label: "Каталог" }]}
      basePath="/catalog"
      query={parseProductQuery(sp)}
      searchParams={sp}
      subcategories={categories}
    />
  );
}
