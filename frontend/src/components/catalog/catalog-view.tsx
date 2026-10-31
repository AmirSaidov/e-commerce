import { ChevronLeft, ChevronRight, SearchX } from "lucide-react";
import Link from "next/link";
import { ProductGrid } from "@/components/product/product-card";
import { Breadcrumbs, type Crumb } from "@/components/ui/breadcrumbs";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/misc";
import { api } from "@/lib/api";
import type { Category, ProductQuery } from "@/lib/api/types";
import { type SearchParams, toSearchString } from "@/lib/catalog-params";
import { PAGE_SIZE } from "@/lib/config";
import { cn } from "@/lib/utils";
import { CatalogControls } from "./catalog-controls";

interface CatalogViewProps {
  title: string;
  description?: string;
  crumbs: Crumb[];
  basePath: string;
  query: ProductQuery;
  searchParams: SearchParams;
  subcategories?: Category[];
  activeCategory?: string;
}

export async function CatalogView({
  title,
  description,
  crumbs,
  basePath,
  query,
  searchParams,
  subcategories = [],
  activeCategory,
}: CatalogViewProps) {
  const [page, brands] = await Promise.all([api.catalog.products(query), api.catalog.brands()]);
  const totalPages = Math.max(1, Math.ceil(page.count / PAGE_SIZE));
  const current = query.page ?? 1;
  const resetHref = query.search ? `${basePath}?q=${encodeURIComponent(query.search)}` : basePath;

  const subnav = subcategories.length ? (
    <nav aria-label="Подкатегории" className="border-b pb-4">
      <p className="mb-2 text-sm font-semibold">Категории</p>
      <ul className="space-y-0.5 text-sm">
        {subcategories.map((c) => (
          <li key={c.id}>
            <Link
              href={`/catalog/${c.slug}`}
              className={cn(
                "text-muted-foreground hover:bg-muted hover:text-foreground block rounded-md px-2 py-1.5",
                c.slug === activeCategory && "bg-muted text-foreground font-medium",
              )}
            >
              {c.name}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  ) : null;

  return (
    <div className="container-page py-6 sm:py-8">
      <Breadcrumbs items={crumbs} />
      <header className="mt-3 mb-6">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground mt-1">{description}</p>}
      </header>

      <CatalogControls brands={brands} total={page.count} sidebarTop={subnav}>
        {page.results.length ? (
          <>
            <ProductGrid products={page.results} />
            {totalPages > 1 && (
              <Pagination
                current={current}
                total={totalPages}
                basePath={basePath}
                searchParams={searchParams}
              />
            )}
          </>
        ) : (
          <EmptyState
            icon={<SearchX />}
            title="Ничего не нашлось"
            description="Попробуйте изменить фильтры или поискать по-другому."
            action={
              <Button asChild variant="outline">
                <Link href={resetHref}>Сбросить фильтры</Link>
              </Button>
            }
          />
        )}
      </CatalogControls>
    </div>
  );
}

function Pagination({
  current,
  total,
  basePath,
  searchParams,
}: {
  current: number;
  total: number;
  basePath: string;
  searchParams: SearchParams;
}) {
  const href = (page: number) =>
    `${basePath}${toSearchString(searchParams, { page: page === 1 ? null : String(page) })}`;
  const pages = Array.from({ length: total }, (_, i) => i + 1).filter(
    (p) => p === 1 || p === total || Math.abs(p - current) <= 1,
  );

  return (
    <nav aria-label="Страницы" className="mt-10 flex items-center justify-center gap-1">
      <Button asChild variant="ghost" size="icon" aria-label="Предыдущая страница">
        {current > 1 ? (
          <Link href={href(current - 1)}>
            <ChevronLeft />
          </Link>
        ) : (
          <span aria-disabled className="pointer-events-none opacity-40">
            <ChevronLeft />
          </span>
        )}
      </Button>
      {pages.map((p, i) => (
        <span key={p} className="flex items-center">
          {i > 0 && p - pages[i - 1] > 1 && <span className="text-muted-foreground px-2">…</span>}
          <Button asChild variant={p === current ? "default" : "ghost"} size="icon">
            <Link href={href(p)} aria-current={p === current ? "page" : undefined}>
              {p}
            </Link>
          </Button>
        </span>
      ))}
      <Button asChild variant="ghost" size="icon" aria-label="Следующая страница">
        {current < total ? (
          <Link href={href(current + 1)}>
            <ChevronRight />
          </Link>
        ) : (
          <span aria-disabled className="pointer-events-none opacity-40">
            <ChevronRight />
          </span>
        )}
      </Button>
    </nav>
  );
}
