"use client";

import { ShoppingBag } from "lucide-react";
import Link from "next/link";
import { CartLineItem } from "@/components/cart/cart-line";
import { PromoForm } from "@/components/cart/promo-form";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { useHydrated } from "@/hooks/use-hydrated";
import { DELIVERY } from "@/lib/config";
import { formatPrice, pluralize } from "@/lib/utils";
import { cartTotals, useCartStore } from "@/stores/cart";

export default function CartPage() {
  const hydrated = useHydrated();
  const lines = useCartStore((s) => s.lines);
  const promo = useCartStore((s) => s.promo);
  const clear = useCartStore((s) => s.clear);
  const { count, subtotal, savings, discount, total } = cartTotals(lines, promo);
  const toFreeDelivery = DELIVERY.courier.freeFrom - total;

  return (
    <div className="container-page py-6 sm:py-8">
      <Breadcrumbs items={[{ label: "Корзина" }]} />
      <h1 className="mt-3 mb-6 text-3xl font-bold tracking-tight">
        Корзина
        {hydrated && count > 0 && (
          <span className="text-muted-foreground ml-2 text-lg font-medium">
            {count} {pluralize(count, ["товар", "товара", "товаров"])}
          </span>
        )}
      </h1>

      {!hydrated ? (
        <Skeleton className="h-64" />
      ) : lines.length === 0 ? (
        <EmptyState
          icon={<ShoppingBag />}
          title="В корзине пока пусто"
          description="Добавьте товары из каталога — они появятся здесь."
          action={
            <Button asChild>
              <Link href="/catalog">Перейти в каталог</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid items-start gap-8 lg:grid-cols-[1fr_360px]">
          <div className="bg-card rounded-2xl border px-4 sm:px-6">
            <ul className="divide-y">
              {lines.map((line) => (
                <CartLineItem key={line.variantId} line={line} />
              ))}
            </ul>
            <div className="border-t py-3 text-right">
              <Button variant="link" size="sm" onClick={clear} className="text-muted-foreground">
                Очистить корзину
              </Button>
            </div>
          </div>

          <aside className="bg-card space-y-4 rounded-2xl border p-5 lg:sticky lg:top-32">
            <h2 className="text-lg font-semibold">Ваш заказ</h2>
            <PromoForm subtotal={subtotal} />
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Товары ({count})</dt>
                <dd className="tabular-nums">{formatPrice(subtotal + savings)}</dd>
              </div>
              {savings > 0 && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Скидка магазина</dt>
                  <dd className="text-destructive tabular-nums">−{formatPrice(savings)}</dd>
                </div>
              )}
              {discount > 0 && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Промокод {promo?.code}</dt>
                  <dd className="text-success tabular-nums">−{formatPrice(discount)}</dd>
                </div>
              )}
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Доставка</dt>
                <dd>рассчитаем на следующем шаге</dd>
              </div>
            </dl>
            <div className="flex items-baseline justify-between border-t pt-4">
              <span className="font-semibold">Итого</span>
              <span className="text-2xl font-bold tabular-nums">{formatPrice(total)}</span>
            </div>
            {toFreeDelivery > 0 && (
              <p className="bg-primary-soft text-primary rounded-lg px-3 py-2 text-xs">
                Добавьте товаров ещё на {formatPrice(toFreeDelivery)} — и доставка курьером будет
                бесплатной
              </p>
            )}
            <Button asChild size="lg" className="w-full">
              <Link href="/checkout">Перейти к оформлению</Link>
            </Button>
          </aside>
        </div>
      )}
    </div>
  );
}
