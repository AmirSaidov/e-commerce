import { Benefits } from "@/components/layout/footer";
import { Hero } from "@/components/home/hero";
import { BrandStrip, CategoryTiles, ProductRail } from "@/components/home/sections";
import { api } from "@/lib/api";

export const revalidate = 60;

export default async function HomePage() {
  const [categories, brands, hits, sale, fresh] = await Promise.all([
    api.catalog.categories(),
    api.catalog.brands(),
    api.catalog.products({ ordering: "-popularity", page_size: 8 }),
    api.catalog.products({ on_sale: true, ordering: "-popularity", page_size: 8 }),
    api.catalog.products({ ordering: "-created_at", page_size: 8 }),
  ]);

  return (
    <div className="container-page space-y-14 py-6 sm:py-8">
      <Hero />
      <Benefits />
      <CategoryTiles categories={categories} />
      <ProductRail
        title="Хиты продаж"
        href="/catalog?ordering=-popularity"
        products={hits.results}
      />
      <ProductRail title="Скидки" href="/catalog?on_sale=1" products={sale.results} />
      <ProductRail title="Новинки" href="/catalog?ordering=-created_at" products={fresh.results} />
      <BrandStrip brands={brands} />
    </div>
  );
}
