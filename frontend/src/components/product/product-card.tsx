import Link from "next/link";
import { Badge, Skeleton } from "@/components/ui/misc";
import type { ProductListItem } from "@/lib/api/types";
import { cn, discountPercent } from "@/lib/utils";
import { AddToCartButton, WishlistButton } from "./actions";
import { Price, ProductImage, Rating } from "./price";

const NEW_DAYS = 45;

export function ProductCard({
  product,
  priority,
}: {
  product: ProductListItem;
  priority?: boolean;
}) {
  const percent = discountPercent(product.price, product.old_price);
  const isNew = Date.now() - Date.parse(product.created_at) < NEW_DAYS * 864e5;

  return (
    <article className="group bg-card relative flex flex-col overflow-hidden rounded-2xl border transition-shadow hover:shadow-lg hover:shadow-black/5">
      <Link
        href={`/product/${product.slug}`}
        className="relative block"
        aria-label={product.name}
        tabIndex={-1}
      >
        <ProductImage
          src={product.image}
          alt={product.name}
          priority={priority}
          sizes="(min-width: 1280px) 300px, (min-width: 768px) 33vw, 50vw"
          className={cn(
            "transition-transform duration-500 group-hover:scale-[1.03]",
            !product.in_stock && "opacity-60",
          )}
        />
      </Link>
      <div className="pointer-events-none absolute top-3 left-3 flex flex-col items-start gap-1">
        {percent && <Badge variant="sale">−{percent}%</Badge>}
        {isNew && <Badge variant="soft">Новинка</Badge>}
      </div>
      <WishlistButton productId={product.id} className="absolute top-2 right-2" />

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="text-muted-foreground flex items-center justify-between gap-2 text-xs">
          <span>{product.brand.name}</span>
          {product.reviews_count > 0 && <Rating value={product.rating} className="text-xs" />}
        </div>
        <h3 className="line-clamp-2 text-sm leading-snug font-medium">
          <Link href={`/product/${product.slug}`} className="hover:text-primary">
            {product.name}
          </Link>
        </h3>
        <div className="mt-auto flex min-h-10 items-end justify-between gap-2 pt-2">
          <Price
            price={product.price}
            oldPrice={product.old_price}
            from={product.variants_count > 1}
            size="sm"
          />
          {product.variants_count > 1 || !product.in_stock ? null : (
            <AddToCartButton
              product={product}
              variant={product.default_variant}
              size="sm"
              compact
            />
          )}
        </div>
        {!product.in_stock && <p className="text-muted-foreground text-xs">Нет в наличии</p>}
      </div>
    </article>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className="bg-card overflow-hidden rounded-2xl border">
      <Skeleton className="aspect-square rounded-none" />
      <div className="space-y-3 p-4">
        <Skeleton className="h-3 w-1/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-6 w-1/2" />
      </div>
    </div>
  );
}

export function ProductGrid({ products }: { products: ProductListItem[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 xl:grid-cols-4">
      {products.map((p, i) => (
        <ProductCard key={p.id} product={p} priority={i < 4} />
      ))}
    </div>
  );
}
