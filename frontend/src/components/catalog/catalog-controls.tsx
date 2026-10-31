"use client";

import { SlidersHorizontal, X } from "lucide-react";
import {
  type ReadonlyURLSearchParams,
  usePathname,
  useRouter,
  useSearchParams,
} from "next/navigation";
import { useOptimistic, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Input, NativeSelect } from "@/components/ui/input";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import type { Brand } from "@/lib/api/types";
import { ORDERING_OPTIONS } from "@/lib/catalog-params";
import { cn, formatPrice, pluralize } from "@/lib/utils";

const RATINGS = [
  { value: "4.5", label: "4,5 и выше" },
  { value: "4", label: "4 и выше" },
];

function useFilterUrl() {
  const router = useRouter();
  const pathname = usePathname();
  const urlParams = useSearchParams();
  // Галочки и сортировка переключаются сразу, не дожидаясь ответа сервера.
  const [searchParams, setOptimisticParams] = useOptimistic<
    URLSearchParams | ReadonlyURLSearchParams
  >(urlParams);
  const [pending, startTransition] = useTransition();

  const update = (changes: Record<string, string | null>) => {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") params.delete(key);
      else params.set(key, value);
    }
    params.delete("page");
    const qs = params.toString();
    startTransition(() => {
      setOptimisticParams(params);
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    });
  };

  return { searchParams, update, pending };
}

function Checkbox({
  checked,
  onChange,
  children,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 rounded-md py-1 text-sm">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="size-4 rounded accent-[var(--primary)]"
      />
      {children}
    </label>
  );
}

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="border-b py-4 last:border-0">
      <legend className="mb-2 text-sm font-semibold">{title}</legend>
      {children}
    </fieldset>
  );
}

function PriceFilter() {
  const { searchParams, update } = useFilterUrl();
  const [min, setMin] = useState(searchParams.get("price_min") ?? "");
  const [max, setMax] = useState(searchParams.get("price_max") ?? "");
  return (
    <form
      className="space-y-2"
      onSubmit={(e) => {
        e.preventDefault();
        update({ price_min: min || null, price_max: max || null });
      }}
    >
      <div className="flex items-center gap-2">
        <Input
          type="number"
          inputMode="numeric"
          min={0}
          placeholder="от"
          value={min}
          onChange={(e) => setMin(e.target.value)}
          aria-label="Цена от, ₸"
        />
        <span className="text-muted-foreground">—</span>
        <Input
          type="number"
          inputMode="numeric"
          min={0}
          placeholder="до"
          value={max}
          onChange={(e) => setMax(e.target.value)}
          aria-label="Цена до, ₸"
        />
      </div>
      <Button type="submit" variant="secondary" size="sm" className="w-full">
        Применить
      </Button>
    </form>
  );
}

function FiltersPanel({ brands }: { brands: Brand[] }) {
  const { searchParams, update } = useFilterUrl();
  const selectedBrands = (searchParams.get("brand") ?? "").split(",").filter(Boolean);
  const toggleBrand = (slug: string, on: boolean) => {
    const next = on ? [...selectedBrands, slug] : selectedBrands.filter((b) => b !== slug);
    update({ brand: next.join(",") || null });
  };

  return (
    <div>
      <FilterGroup title="Цена, ₸">
        <PriceFilter key={`${searchParams.get("price_min")}-${searchParams.get("price_max")}`} />
      </FilterGroup>
      <FilterGroup title="Наличие и акции">
        <Checkbox
          checked={searchParams.get("in_stock") === "1"}
          onChange={(on) => update({ in_stock: on ? "1" : null })}
        >
          Только в наличии
        </Checkbox>
        <Checkbox
          checked={searchParams.get("on_sale") === "1"}
          onChange={(on) => update({ on_sale: on ? "1" : null })}
        >
          Со скидкой
        </Checkbox>
      </FilterGroup>
      <FilterGroup title="Рейтинг">
        {RATINGS.map((r) => (
          <Checkbox
            key={r.value}
            checked={searchParams.get("rating_min") === r.value}
            onChange={(on) => update({ rating_min: on ? r.value : null })}
          >
            {r.label}
          </Checkbox>
        ))}
      </FilterGroup>
      <FilterGroup title="Бренд">
        <div className="max-h-64 space-y-0.5 overflow-y-auto pr-1">
          {brands.map((b) => (
            <Checkbox
              key={b.id}
              checked={selectedBrands.includes(b.slug)}
              onChange={(on) => toggleBrand(b.slug, on)}
            >
              {b.name}
            </Checkbox>
          ))}
        </div>
      </FilterGroup>
    </div>
  );
}

function ActiveFilters({ brands }: { brands: Brand[] }) {
  const { searchParams, update } = useFilterUrl();
  const chips: { label: string; clear: Record<string, string | null> }[] = [];
  const selectedBrands = (searchParams.get("brand") ?? "").split(",").filter(Boolean);
  for (const slug of selectedBrands) {
    const name = brands.find((b) => b.slug === slug)?.name ?? slug;
    chips.push({
      label: name,
      clear: { brand: selectedBrands.filter((b) => b !== slug).join(",") || null },
    });
  }
  const min = searchParams.get("price_min");
  const max = searchParams.get("price_max");
  if (min || max) {
    const label = [min && `от ${formatPrice(min)}`, max && `до ${formatPrice(max)}`]
      .filter(Boolean)
      .join(" ");
    chips.push({ label, clear: { price_min: null, price_max: null } });
  }
  if (searchParams.get("in_stock") === "1")
    chips.push({ label: "В наличии", clear: { in_stock: null } });
  if (searchParams.get("on_sale") === "1")
    chips.push({ label: "Со скидкой", clear: { on_sale: null } });
  const rating = searchParams.get("rating_min");
  if (rating)
    chips.push({ label: `Рейтинг от ${rating.replace(".", ",")}`, clear: { rating_min: null } });

  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      {chips.map((chip) => (
        <button
          key={chip.label}
          type="button"
          onClick={() => update(chip.clear)}
          className="bg-primary-soft text-primary hover:bg-primary-soft/70 inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium"
          aria-label={`Убрать фильтр: ${chip.label}`}
        >
          {chip.label} <X className="size-3" />
        </button>
      ))}
      <button
        type="button"
        onClick={() =>
          update({
            brand: null,
            price_min: null,
            price_max: null,
            in_stock: null,
            on_sale: null,
            rating_min: null,
          })
        }
        className="text-muted-foreground hover:text-foreground text-xs font-medium"
      >
        Сбросить всё
      </button>
    </div>
  );
}

interface CatalogControlsProps {
  brands: Brand[];
  total: number;
  sidebarTop?: React.ReactNode;
  children: React.ReactNode;
}

export function CatalogControls({ brands, total, sidebarTop, children }: CatalogControlsProps) {
  const { searchParams, update, pending } = useFilterUrl();
  const [open, setOpen] = useState(false);

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_1fr] lg:gap-8">
      <aside className="hidden lg:block" aria-label="Фильтры">
        {sidebarTop}
        <FiltersPanel brands={brands} />
      </aside>

      <div className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-muted-foreground text-sm" aria-live="polite">
            {total} {pluralize(total, ["товар", "товара", "товаров"])}
          </p>
          <div className="flex items-center gap-2">
            <Sheet open={open} onOpenChange={setOpen}>
              <Button variant="outline" className="lg:hidden" onClick={() => setOpen(true)}>
                <SlidersHorizontal /> Фильтры
              </Button>
              <SheetContent side="left" title="Фильтры" className="max-w-sm">
                <div className="flex-1 overflow-y-auto px-5">
                  {sidebarTop}
                  <FiltersPanel brands={brands} />
                </div>
                <div className="border-t p-4">
                  <Button className="w-full" onClick={() => setOpen(false)} loading={pending}>
                    Показать {total} {pluralize(total, ["товар", "товара", "товаров"])}
                  </Button>
                </div>
              </SheetContent>
            </Sheet>
            <label className="sr-only" htmlFor="ordering">
              Сортировка
            </label>
            <NativeSelect
              id="ordering"
              value={searchParams.get("ordering") ?? "-popularity"}
              onChange={(e) =>
                update({ ordering: e.target.value === "-popularity" ? null : e.target.value })
              }
              className="w-auto"
            >
              {ORDERING_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </NativeSelect>
          </div>
        </div>
        <ActiveFilters brands={brands} />
        <div className={cn("transition-opacity", pending && "pointer-events-none opacity-50")}>
          {children}
        </div>
      </div>
    </div>
  );
}
