import { ArrowRight } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { ProductCard } from "@/components/product/product-card";
import type { Brand, Category, ProductListItem } from "@/lib/api/types";

export function SectionHeader({
  title,
  href,
  linkLabel = "Смотреть все",
}: {
  title: string;
  href?: string;
  linkLabel?: string;
}) {
  return (
    <div className="mb-5 flex items-end justify-between gap-4">
      <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
      {href && (
        <Link
          href={href}
          className="text-primary inline-flex items-center gap-1 text-sm font-medium hover:underline"
        >
          {linkLabel} <ArrowRight className="size-4" />
        </Link>
      )}
    </div>
  );
}

export function ProductRail({
  title,
  href,
  products,
}: {
  title: string;
  href?: string;
  products: ProductListItem[];
}) {
  if (!products.length) return null;
  return (
    <section>
      <SectionHeader title={title} href={href} />
      <div className="no-scrollbar -mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-2 sm:gap-4 md:mx-0 md:grid md:grid-cols-3 md:overflow-visible md:px-0 xl:grid-cols-4">
        {products.map((p) => (
          <div key={p.id} className="w-[46%] shrink-0 snap-start sm:w-[32%] md:w-auto">
            <ProductCard product={p} />
          </div>
        ))}
      </div>
    </section>
  );
}

export function CategoryTiles({ categories }: { categories: Category[] }) {
  return (
    <section>
      <SectionHeader title="Категории" href="/catalog" linkLabel="Весь каталог" />
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {categories.map((c) => (
          <li key={c.id}>
            <Link
              href={`/catalog/${c.slug}`}
              className="group bg-card flex flex-col overflow-hidden rounded-2xl border transition-shadow hover:shadow-lg hover:shadow-black/5"
            >
              <div className="bg-muted relative aspect-[4/3] overflow-hidden">
                {c.image && (
                  <Image
                    src={c.image}
                    alt=""
                    fill
                    sizes="(min-width: 1024px) 200px, 50vw"
                    className="object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                )}
              </div>
              <div className="flex items-center justify-between p-3">
                <span className="text-sm font-semibold">{c.name}</span>
                <ArrowRight className="text-muted-foreground size-4 transition-transform group-hover:translate-x-0.5" />
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function BrandStrip({ brands }: { brands: Brand[] }) {
  return (
    <section>
      <SectionHeader title="Бренды" />
      <ul className="flex flex-wrap gap-2">
        {brands.map((b) => (
          <li key={b.id}>
            <Link
              href={`/catalog?brand=${b.slug}`}
              className="bg-card hover:border-primary hover:text-primary inline-flex h-11 items-center rounded-full border px-5 text-sm font-semibold tracking-tight transition-colors"
            >
              {b.name}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
