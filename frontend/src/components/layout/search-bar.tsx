"use client";

import { useQuery } from "@tanstack/react-query";
import { LoaderCircle, Search } from "lucide-react";
import Image from "next/image";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { useDebouncedValue } from "@/hooks/use-debounce";
import { api } from "@/lib/api";
import { cn, formatPrice } from "@/lib/utils";

export function SearchBar({ className }: { className?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const initial = pathname === "/search" ? (searchParams.get("q") ?? "") : "";
  const [value, setValue] = useState(initial);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const query = useDebouncedValue(value.trim(), 300);

  const { data = [], isFetching } = useQuery({
    queryKey: ["search-suggest", query],
    queryFn: ({ signal }) => api.catalog.search(query, signal),
    enabled: query.length >= 2,
    staleTime: 60_000,
  });
  const suggestions = query.length >= 2 ? data : [];

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!wrapperRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const go = (href: string) => {
    setOpen(false);
    setActive(-1);
    router.push(href);
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (active >= 0 && suggestions[active]) return go(`/product/${suggestions[active].slug}`);
    if (value.trim()) go(`/search?q=${encodeURIComponent(value.trim())}`);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!suggestions.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const showList = open && query.length >= 2;

  return (
    <div ref={wrapperRef} className={cn("relative", className)}>
      <form role="search" onSubmit={onSubmit}>
        <label htmlFor={`${listId}-input`} className="sr-only">
          Поиск товаров
        </label>
        <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
        <input
          id={`${listId}-input`}
          type="search"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Искать смартфоны, наушники, ноутбуки…"
          autoComplete="off"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          className="border-input bg-muted/60 placeholder:text-muted-foreground focus:border-ring focus:bg-card focus:ring-ring/20 h-10 w-full rounded-full border pr-10 pl-9 text-sm transition-colors focus:ring-3 focus:outline-none [&::-webkit-search-cancel-button]:hidden"
        />
        {isFetching && (
          <LoaderCircle className="text-muted-foreground absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin" />
        )}
      </form>

      {showList && (
        <div
          id={listId}
          role="listbox"
          className="bg-card absolute inset-x-0 top-12 z-50 overflow-hidden rounded-xl border shadow-xl"
        >
          {suggestions.length === 0 && !isFetching ? (
            <p className="text-muted-foreground px-4 py-6 text-center text-sm">
              Ничего не нашли по запросу «{query}»
            </p>
          ) : (
            <ul className="py-1">
              {suggestions.map((p, i) => (
                <li
                  key={p.id}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={i === active}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => go(`/product/${p.slug}`)}
                  onMouseEnter={() => setActive(i)}
                  className={cn(
                    "flex cursor-pointer items-center gap-3 px-3 py-2",
                    i === active && "bg-muted",
                  )}
                >
                  <div className="bg-muted relative size-10 shrink-0 overflow-hidden rounded-lg">
                    {p.image && (
                      <Image src={p.image} alt="" fill sizes="40px" className="object-cover" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{p.name}</p>
                    <p className="text-muted-foreground text-xs">{p.category.name}</p>
                  </div>
                  <span className="text-sm font-semibold tabular-nums">{formatPrice(p.price)}</span>
                </li>
              ))}
            </ul>
          )}
          {suggestions.length > 0 && (
            <button
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => go(`/search?q=${encodeURIComponent(query)}`)}
              className="text-primary hover:bg-muted w-full border-t px-4 py-2.5 text-left text-sm font-medium"
            >
              Все результаты по запросу «{query}»
            </button>
          )}
        </div>
      )}
    </div>
  );
}
