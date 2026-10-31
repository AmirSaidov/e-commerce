import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cache } from "react";
import { ProductRail } from "@/components/home/sections";
import { ProductGallery } from "@/components/product/gallery";
import { Rating } from "@/components/product/price";
import { PurchasePanel } from "@/components/product/purchase-panel";
import { Reviews } from "@/components/product/reviews";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { api } from "@/lib/api";
import { findCategoryPath } from "@/lib/category-tree";
import { CURRENCY, SITE_URL } from "@/lib/config";
import { toNumber } from "@/lib/utils";

export const revalidate = 60;

interface Props {
  params: Promise<{ slug: string }>;
}

const getProduct = cache((slug: string) => api.catalog.product(slug));

export async function generateStaticParams() {
  try {
    const { results } = await api.catalog.products({ ordering: "-popularity", page_size: 50 });
    return results.map((p) => ({ slug: p.slug }));
  } catch {
    // бэкенд недоступен во время сборки — страницы соберутся по первому запросу
    return [];
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) return { title: "Товар не найден" };
  const description = product.description.slice(0, 160);
  return {
    title: product.name,
    description,
    alternates: { canonical: `/product/${product.slug}` },
    openGraph: {
      type: "website",
      title: product.name,
      description,
      images: product.images.map((i) => ({ url: i.image, alt: i.alt })),
    },
  };
}

export default async function ProductPage({ params }: Props) {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) notFound();

  const [categories, related] = await Promise.all([
    api.catalog.categories(),
    api.catalog.related(slug).catch(() => []),
  ]);
  const path = findCategoryPath(categories, product.category.slug) ?? [];

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    description: product.description,
    sku: product.default_variant.sku,
    image: product.images.map((i) =>
      i.image.startsWith("http") ? i.image : `${SITE_URL}${i.image}`,
    ),
    brand: { "@type": "Brand", name: product.brand.name },
    ...(product.reviews_count > 0 && {
      aggregateRating: {
        "@type": "AggregateRating",
        ratingValue: product.rating,
        reviewCount: product.reviews_count,
      },
    }),
    offers: {
      "@type": "AggregateOffer",
      priceCurrency: CURRENCY,
      lowPrice: Math.min(...product.variants.map((v) => toNumber(v.price))),
      highPrice: Math.max(...product.variants.map((v) => toNumber(v.price))),
      offerCount: product.variants.length,
      availability: product.in_stock
        ? "https://schema.org/InStock"
        : "https://schema.org/OutOfStock",
    },
  };

  return (
    <div className="container-page space-y-14 py-6 sm:py-8">
      <div className="space-y-5">
        <Breadcrumbs
          items={[
            { label: "Каталог", href: "/catalog" },
            ...path.map((c) => ({ label: c.name, href: `/catalog/${c.slug}` })),
            { label: product.name },
          ]}
        />
        <div className="grid gap-8 lg:grid-cols-[1.15fr_1fr] lg:gap-12">
          <ProductGallery images={product.images} name={product.name} />
          <div className="space-y-6">
            <div className="space-y-2">
              <Link
                href={`/catalog?brand=${product.brand.slug}`}
                className="text-primary text-sm font-medium hover:underline"
              >
                {product.brand.name}
              </Link>
              <h1 className="text-2xl font-bold tracking-tight text-balance sm:text-3xl">
                {product.name}
              </h1>
              {product.reviews_count > 0 && (
                <a href="#reviews" className="inline-block hover:opacity-80">
                  <Rating value={product.rating} count={product.reviews_count} />
                </a>
              )}
            </div>
            <PurchasePanel product={product} />
          </div>
        </div>
      </div>

      <div className="grid gap-10 lg:grid-cols-[1.15fr_1fr] lg:gap-12">
        <section aria-labelledby="about-title" className="space-y-4">
          <h2 id="about-title" className="text-2xl font-bold tracking-tight">
            О товаре
          </h2>
          <p className="text-muted-foreground leading-relaxed">{product.description}</p>
        </section>
        <section aria-labelledby="specs-title" className="space-y-4">
          <h2 id="specs-title" className="text-2xl font-bold tracking-tight">
            Характеристики
          </h2>
          <dl className="bg-card divide-y rounded-2xl border">
            {Object.entries(product.specs).map(([key, value]) => (
              <div key={key} className="grid grid-cols-2 gap-4 px-5 py-3 text-sm">
                <dt className="text-muted-foreground">{key}</dt>
                <dd className="font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>

      <Reviews slug={product.slug} rating={product.rating} count={product.reviews_count} />
      <ProductRail title="Похожие товары" products={related} />

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />
    </div>
  );
}
