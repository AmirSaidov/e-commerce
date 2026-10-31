"use client";

import { Heart, Minus, Plus, ShoppingCart } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useHydrated } from "@/hooks/use-hydrated";
import type { ProductListItem, ProductVariant } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { lineFromProduct, useCartStore } from "@/stores/cart";
import { useWishlistStore } from "@/stores/wishlist";

interface QuantityStepperProps {
  value: number;
  max: number;
  onChange: (value: number) => void;
  size?: "sm" | "md";
  label: string;
}

export function QuantityStepper({
  value,
  max,
  onChange,
  size = "md",
  label,
}: QuantityStepperProps) {
  const btn = size === "sm" ? "icon-sm" : "icon";
  return (
    <div
      className="bg-card inline-flex items-center rounded-lg border"
      role="group"
      aria-label={label}
    >
      <Button
        variant="ghost"
        size={btn}
        onClick={() => onChange(value - 1)}
        aria-label="Уменьшить количество"
      >
        <Minus />
      </Button>
      <span
        className={cn("min-w-8 text-center text-sm font-medium tabular-nums")}
        aria-live="polite"
      >
        {value}
      </span>
      <Button
        variant="ghost"
        size={btn}
        onClick={() => onChange(value + 1)}
        disabled={value >= max}
        aria-label="Увеличить количество"
      >
        <Plus />
      </Button>
    </div>
  );
}

interface AddToCartProps {
  product: Pick<ProductListItem, "id" | "slug" | "name" | "image">;
  variant: ProductVariant;
  size?: "sm" | "default" | "lg";
  className?: string;
  compact?: boolean;
}

export function AddToCartButton({
  product,
  variant,
  size = "default",
  className,
  compact,
}: AddToCartProps) {
  const hydrated = useHydrated();
  const line = useCartStore((s) => s.lines.find((l) => l.variantId === variant.id));
  const add = useCartStore((s) => s.add);
  const setQuantity = useCartStore((s) => s.setQuantity);

  if (variant.stock <= 0) {
    return (
      <Button size={size} variant="secondary" disabled className={className}>
        Нет в наличии
      </Button>
    );
  }

  if (hydrated && line) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <QuantityStepper
          value={line.quantity}
          max={line.stock}
          size={size === "sm" ? "sm" : "md"}
          onChange={(q) => setQuantity(variant.id, q)}
          label={`Количество «${product.name}» в корзине`}
        />
        {!compact && (
          <Button asChild variant="outline" size={size}>
            <Link href="/cart">В корзине</Link>
          </Button>
        )}
      </div>
    );
  }

  return (
    <Button
      size={size}
      className={className}
      onClick={() => {
        add(lineFromProduct(product, variant));
        toast.success("Добавлено в корзину", { description: `${product.name}, ${variant.name}` });
      }}
    >
      <ShoppingCart />
      {compact ? <span className="sr-only">В корзину: {product.name}</span> : "В корзину"}
    </Button>
  );
}

export function WishlistButton({
  productId,
  className,
  variant = "floating",
}: {
  productId: number;
  className?: string;
  variant?: "floating" | "outline";
}) {
  const router = useRouter();
  const status = useAuthStore((s) => s.status);
  const active = useWishlistStore((s) => s.ids.includes(productId));
  const toggle = useWishlistStore((s) => s.toggle);

  const onClick = async () => {
    if (status !== "authenticated") {
      toast("Войдите, чтобы сохранять товары", {
        action: { label: "Войти", onClick: () => router.push("/login") },
      });
      return;
    }
    try {
      const added = await toggle(productId);
      toast.success(added ? "Добавлено в избранное" : "Удалено из избранного");
    } catch {
      toast.error("Не удалось обновить избранное");
    }
  };

  return (
    <Button
      type="button"
      variant={variant === "outline" ? "outline" : "ghost"}
      size="icon"
      onClick={onClick}
      aria-pressed={active}
      aria-label={active ? "Убрать из избранного" : "Добавить в избранное"}
      className={cn(
        variant === "floating" && "bg-card/80 hover:bg-card rounded-full shadow-sm backdrop-blur",
        className,
      )}
    >
      <Heart className={cn(active && "fill-destructive text-destructive")} />
    </Button>
  );
}
