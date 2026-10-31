"use client";

import { useQuery } from "@tanstack/react-query";
import { Heart } from "lucide-react";
import Link from "next/link";
import { ProductCard, ProductCardSkeleton } from "@/components/product/product-card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { useWishlistStore } from "@/stores/wishlist";

export default function WishlistPage() {
  const ids = useWishlistStore((s) => s.ids);
  const { data, isPending } = useQuery({ queryKey: ["wishlist"], queryFn: api.wishlist.list });
  // Снятое сердечко сразу убирает товар из списка, не дожидаясь перезапроса.
  const products = data?.filter((p) => ids.includes(p.id)) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Избранное</h1>
      {isPending ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <ProductCardSkeleton key={i} />
          ))}
        </div>
      ) : products.length === 0 ? (
        <EmptyState
          icon={<Heart />}
          title="В избранном пусто"
          description="Нажмите на сердечко у товара, чтобы сохранить его здесь."
          action={
            <Button asChild>
              <Link href="/catalog">В каталог</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </div>
  );
}
