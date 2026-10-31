import type { ProductOrdering, ProductQuery } from "@/lib/api/types";

export type SearchParams = Record<string, string | string[] | undefined>;

export const ORDERING_OPTIONS: { value: ProductOrdering; label: string }[] = [
  { value: "-popularity", label: "Популярные" },
  { value: "price", label: "Сначала дешевле" },
  { value: "-price", label: "Сначала дороже" },
  { value: "-created_at", label: "Новинки" },
  { value: "-rating", label: "По рейтингу" },
];

const ORDERING_VALUES = new Set<string>(ORDERING_OPTIONS.map((o) => o.value));

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function positiveNumber(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? n : undefined;
}

/** Параметры URL каталога → запрос к API. Имена совпадают с query-параметрами бэкенда. */
export function parseProductQuery(sp: SearchParams): ProductQuery {
  const ordering = first(sp.ordering);
  const brand = first(sp.brand);
  return {
    brand: brand ? brand.split(",").filter(Boolean) : undefined,
    price_min: positiveNumber(first(sp.price_min)),
    price_max: positiveNumber(first(sp.price_max)),
    rating_min: positiveNumber(first(sp.rating_min)),
    in_stock: first(sp.in_stock) === "1" || undefined,
    on_sale: first(sp.on_sale) === "1" || undefined,
    ordering: ordering && ORDERING_VALUES.has(ordering) ? (ordering as ProductOrdering) : undefined,
    search: first(sp.q)?.trim() || undefined,
    page: Math.max(1, Math.floor(positiveNumber(first(sp.page)) ?? 1)),
  };
}

export function toSearchString(sp: SearchParams, overrides: Record<string, string | null>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(sp)) {
    const v = first(value);
    if (v) params.set(key, v);
  }
  for (const [key, value] of Object.entries(overrides)) {
    if (value === null) params.delete(key);
    else params.set(key, value);
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
