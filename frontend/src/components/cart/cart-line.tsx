"use client";

import { Trash2 } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { QuantityStepper } from "@/components/product/actions";
import { Button } from "@/components/ui/button";
import { cn, formatPrice } from "@/lib/utils";
import { type CartLine, useCartStore } from "@/stores/cart";

export function CartLineItem({
  line,
  compact = false,
  onNavigate,
}: {
  line: CartLine;
  compact?: boolean;
  onNavigate?: () => void;
}) {
  const setQuantity = useCartStore((s) => s.setQuantity);
  const remove = useCartStore((s) => s.remove);
  const href = `/product/${line.slug}`;

  return (
    <li className="flex gap-3 py-4 sm:gap-4">
      <Link
        href={href}
        onClick={onNavigate}
        tabIndex={-1}
        aria-hidden
        className={cn(
          "bg-muted relative shrink-0 overflow-hidden rounded-xl",
          compact ? "size-20" : "size-24 sm:size-28",
        )}
      >
        {line.image && (
          <Image src={line.image} alt={line.name} fill sizes="112px" className="object-cover" />
        )}
      </Link>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <Link
              href={href}
              onClick={onNavigate}
              className="hover:text-primary line-clamp-2 text-sm font-medium"
            >
              {line.name}
            </Link>
            <p className="text-muted-foreground text-xs">{line.variantName}</p>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => remove(line.variantId)}
            aria-label={`Удалить «${line.name}» из корзины`}
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 />
          </Button>
        </div>
        <div className="mt-auto flex flex-wrap items-end justify-between gap-2">
          <QuantityStepper
            value={line.quantity}
            max={line.stock}
            size="sm"
            onChange={(q) => setQuantity(line.variantId, q)}
            label={`Количество «${line.name}»`}
          />
          <div className="text-right">
            <p className="font-semibold tabular-nums">{formatPrice(line.price * line.quantity)}</p>
            {line.quantity > 1 && (
              <p className="text-muted-foreground text-xs tabular-nums">
                {formatPrice(line.price)} / шт.
              </p>
            )}
          </div>
        </div>
        {line.quantity >= line.stock && (
          <p className="text-warning text-xs">Это весь остаток на складе</p>
        )}
      </div>
    </li>
  );
}
