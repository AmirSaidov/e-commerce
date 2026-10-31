"use client";

import { Check, PackageCheck, Store, Truck } from "lucide-react";
import { useState } from "react";
import type { ProductDetail } from "@/lib/api/types";
import { DELIVERY } from "@/lib/config";
import { cn, formatPrice, toNumber } from "@/lib/utils";
import { AddToCartButton, WishlistButton } from "./actions";
import { Price } from "./price";

function StockLabel({ stock }: { stock: number }) {
  if (stock <= 0) return <span className="text-muted-foreground text-sm">Нет в наличии</span>;
  if (stock <= 3)
    return <span className="text-warning text-sm font-medium">Осталось {stock} шт.</span>;
  return (
    <span className="text-success inline-flex items-center gap-1 text-sm font-medium">
      <Check className="size-4" /> В наличии
    </span>
  );
}

export function PurchasePanel({ product }: { product: ProductDetail }) {
  const [variantId, setVariantId] = useState(product.default_variant.id);
  const variant = product.variants.find((v) => v.id === variantId) ?? product.default_variant;
  const freeCourier = toNumber(variant.price) >= DELIVERY.courier.freeFrom;

  return (
    <div className="space-y-6">
      {product.variants.length > 1 && (
        <fieldset>
          <legend className="mb-2 text-sm font-medium">
            Вариант: <span className="text-muted-foreground">{variant.name}</span>
          </legend>
          <div className="flex flex-wrap gap-2">
            {product.variants.map((v) => (
              <label
                key={v.id}
                className={cn(
                  "has-[:focus-visible]:ring-ring/30 cursor-pointer rounded-xl border-2 px-4 py-2 text-sm font-medium transition-colors has-[:focus-visible]:ring-3",
                  v.id === variant.id ? "border-primary bg-primary-soft" : "hover:border-input",
                  v.stock <= 0 && "text-muted-foreground line-through decoration-1",
                )}
              >
                <input
                  type="radio"
                  name="variant"
                  value={v.id}
                  checked={v.id === variant.id}
                  onChange={() => setVariantId(v.id)}
                  className="sr-only"
                />
                {v.name}
                {v.price !== product.default_variant.price && (
                  <span className="text-muted-foreground ml-1.5 text-xs font-normal">
                    {formatPrice(v.price)}
                  </span>
                )}
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <div className="bg-card space-y-3 rounded-2xl border p-5">
        <div className="flex items-start justify-between gap-3">
          <Price price={variant.price} oldPrice={variant.old_price} size="lg" />
          <StockLabel stock={variant.stock} />
        </div>
        <div className="flex gap-2">
          <AddToCartButton product={product} variant={variant} size="lg" className="flex-1" />
          <WishlistButton productId={product.id} variant="outline" className="size-12" />
        </div>
        <p className="text-muted-foreground text-xs">Артикул: {variant.sku}</p>
      </div>

      <ul className="space-y-3 text-sm">
        <li className="flex gap-3">
          <Truck className="text-muted-foreground mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-medium">
              Курьером — {freeCourier ? "бесплатно" : formatPrice(DELIVERY.courier.price)}
            </p>
            <p className="text-muted-foreground">
              {DELIVERY.courier.eta}
              {!freeCourier && `, бесплатно от ${formatPrice(DELIVERY.courier.freeFrom)}`}
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <Store className="text-muted-foreground mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-medium">Самовывоз — бесплатно</p>
            <p className="text-muted-foreground">{DELIVERY.pickup.eta}</p>
          </div>
        </li>
        <li className="flex gap-3">
          <PackageCheck className="text-muted-foreground mt-0.5 size-5 shrink-0" />
          <p className="font-medium">Официальная гарантия производителя</p>
        </li>
      </ul>
    </div>
  );
}
