import { Star } from "lucide-react";
import Image from "next/image";
import { cn, discountPercent, formatPrice, pluralize } from "@/lib/utils";
import type { Money } from "@/lib/api/types";
import { Badge } from "@/components/ui/misc";

interface PriceProps {
  price: Money | number;
  oldPrice?: Money | number | null;
  size?: "sm" | "md" | "lg";
  from?: boolean;
  className?: string;
}

export function Price({ price, oldPrice, size = "md", from = false, className }: PriceProps) {
  const percent = oldPrice ? discountPercent(String(price), String(oldPrice)) : null;
  return (
    <div className={cn("flex flex-wrap items-baseline gap-x-2 gap-y-1", className)}>
      <span
        className={cn(
          "font-bold tracking-tight tabular-nums",
          size === "sm" && "text-base",
          size === "md" && "text-lg",
          size === "lg" && "text-3xl",
          percent && "text-destructive",
        )}
      >
        {from && <span className="mr-1 text-[0.7em] font-medium">от</span>}
        {formatPrice(price)}
      </span>
      {percent && (
        <>
          <span className="text-muted-foreground text-sm tabular-nums line-through">
            {formatPrice(oldPrice!)}
          </span>
          {size === "lg" && <Badge variant="sale">−{percent}%</Badge>}
        </>
      )}
    </div>
  );
}

export function Rating({
  value,
  count,
  className,
}: {
  value: number;
  count?: number;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-1 text-sm", className)}>
      <Star className="fill-warning text-warning size-4" aria-hidden />
      <span className="font-medium tabular-nums">{value.toFixed(1)}</span>
      {count !== undefined && (
        <span className="text-muted-foreground">
          · {count} {pluralize(count, ["отзыв", "отзыва", "отзывов"])}
        </span>
      )}
      <span className="sr-only">Рейтинг {value} из 5</span>
    </span>
  );
}

export function Stars({ value, size = "sm" }: { value: number; size?: "sm" | "md" }) {
  return (
    <span className="inline-flex" aria-label={`Оценка ${value} из 5`} role="img">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          aria-hidden
          className={cn(
            size === "sm" ? "size-3.5" : "size-5",
            n <= Math.round(value) ? "fill-warning text-warning" : "fill-muted text-muted",
          )}
        />
      ))}
    </span>
  );
}

interface ProductImageProps {
  src: string | null;
  alt: string;
  sizes: string;
  priority?: boolean;
  className?: string;
}

export function ProductImage({ src, alt, sizes, priority, className }: ProductImageProps) {
  return (
    <div className={cn("bg-muted relative aspect-square overflow-hidden", className)}>
      {src ? (
        <Image
          src={src}
          alt={alt}
          fill
          sizes={sizes}
          priority={priority}
          className="object-cover"
        />
      ) : (
        <div className="text-muted-foreground flex size-full items-center justify-center text-xs">
          Нет фото
        </div>
      )}
    </div>
  );
}
