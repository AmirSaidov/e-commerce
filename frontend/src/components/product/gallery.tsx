"use client";

import Image from "next/image";
import { useState } from "react";
import type { ProductImage } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export function ProductGallery({ images, name }: { images: ProductImage[]; name: string }) {
  const [active, setActive] = useState(0);
  const current = images[active];

  if (!current) {
    return <div className="bg-muted aspect-square rounded-3xl" />;
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowRight") setActive((i) => (i + 1) % images.length);
    if (e.key === "ArrowLeft") setActive((i) => (i - 1 + images.length) % images.length);
  };

  return (
    <div className="flex flex-col-reverse gap-3 md:flex-row">
      {images.length > 1 && (
        <div
          className="no-scrollbar flex gap-2 overflow-x-auto md:flex-col"
          role="tablist"
          aria-label="Фото товара"
          onKeyDown={onKeyDown}
        >
          {images.map((img, i) => (
            <button
              key={img.id}
              type="button"
              role="tab"
              aria-selected={i === active}
              aria-label={`Фото ${i + 1}`}
              tabIndex={i === active ? 0 : -1}
              onClick={() => setActive(i)}
              className={cn(
                "bg-muted relative size-16 shrink-0 overflow-hidden rounded-xl border-2 transition-colors sm:size-20",
                i === active ? "border-primary" : "border-transparent opacity-70 hover:opacity-100",
              )}
            >
              <Image src={img.image} alt="" fill sizes="80px" className="object-cover" />
            </button>
          ))}
        </div>
      )}
      <div className="bg-muted relative aspect-square flex-1 overflow-hidden rounded-3xl">
        <Image
          key={current.id}
          src={current.image}
          alt={current.alt || name}
          fill
          priority
          sizes="(min-width: 1024px) 560px, 100vw"
          className="animate-fade-in object-cover"
        />
      </div>
    </div>
  );
}
