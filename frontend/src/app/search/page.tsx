import type { Metadata } from "next";
import { CatalogView } from "@/components/catalog/catalog-view";
import { parseProductQuery, type SearchParams } from "@/lib/catalog-params";

interface Props {
  searchParams: Promise<SearchParams>;
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const { q } = await searchParams;
  return {
    title: q ? `Поиск: ${q}` : "Поиск",
    robots: { index: false, follow: true },
  };
}

export default async function SearchPage({ searchParams }: Props) {
  const sp = await searchParams;
  const query = parseProductQuery(sp);
  return (
    <CatalogView
      title={query.search ? `Результаты по запросу «${query.search}»` : "Поиск"}
      crumbs={[{ label: "Поиск" }]}
      basePath="/search"
      query={query}
      searchParams={sp}
    />
  );
}
