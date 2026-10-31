"use client";

import { Heart, Menu, Zap } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import type { Category } from "@/lib/api/types";
import { SITE_NAME } from "@/lib/config";
import { cn } from "@/lib/utils";
import { MiniCart, ThemeToggle, UserMenu } from "./header-actions";
import { SearchBar } from "./search-bar";

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn("flex items-center gap-2 font-bold tracking-tight", className)}>
      <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-lg">
        <Zap className="size-4 fill-current" />
      </span>
      <span className="text-lg">{SITE_NAME}</span>
    </Link>
  );
}

function MobileNav({ categories }: { categories: Category[] }) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={() => setOpen(true)}
        aria-label="Открыть меню"
      >
        <Menu />
      </Button>
      <SheetContent side="left" title="Каталог" className="max-w-xs">
        <nav className="flex-1 overflow-y-auto p-3" aria-label="Категории">
          <Link
            href="/catalog"
            onClick={close}
            className="hover:bg-muted block rounded-lg px-3 py-2 font-medium"
          >
            Все товары
          </Link>
          {categories.map((c) => (
            <div key={c.id} className="mt-1">
              <Link
                href={`/catalog/${c.slug}`}
                onClick={close}
                className="hover:bg-muted block rounded-lg px-3 py-2 font-medium"
              >
                {c.name}
              </Link>
              {c.children.map((child) => (
                <Link
                  key={child.id}
                  href={`/catalog/${child.slug}`}
                  onClick={close}
                  className="text-muted-foreground hover:bg-muted hover:text-foreground block rounded-lg py-1.5 pr-3 pl-6 text-sm"
                >
                  {child.name}
                </Link>
              ))}
            </div>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  );
}

export function Header({ categories }: { categories: Category[] }) {
  const pathname = usePathname();
  return (
    <header className="bg-background/80 sticky top-0 z-40 border-b backdrop-blur-xl">
      <div className="container-page flex h-16 items-center gap-2 sm:gap-4">
        <MobileNav categories={categories} />
        <Logo className="mr-2" />
        <Suspense fallback={<div className="hidden h-10 flex-1 md:block" />}>
          <SearchBar className="mx-auto hidden max-w-xl flex-1 md:block" />
        </Suspense>
        <div className="ml-auto flex items-center gap-0.5 md:ml-0">
          <ThemeToggle />
          <Button
            asChild
            variant="ghost"
            size="icon"
            aria-label="Избранное"
            className="hidden sm:inline-flex"
          >
            <Link href="/account/wishlist">
              <Heart />
            </Link>
          </Button>
          <UserMenu />
          <MiniCart />
        </div>
      </div>
      <div className="container-page pb-3 md:hidden">
        <Suspense fallback={<div className="h-10" />}>
          <SearchBar />
        </Suspense>
      </div>
      <nav aria-label="Категории" className="hidden border-t lg:block">
        <ul className="container-page no-scrollbar flex h-11 items-center gap-1 overflow-x-auto text-sm">
          <li>
            <Link
              href="/catalog"
              className={cn(
                "hover:bg-muted rounded-md px-3 py-1.5 font-medium transition-colors",
                pathname === "/catalog" && "bg-muted",
              )}
            >
              Все товары
            </Link>
          </li>
          {categories.map((c) => (
            <li key={c.id}>
              <Link
                href={`/catalog/${c.slug}`}
                className={cn(
                  "text-muted-foreground hover:bg-muted hover:text-foreground rounded-md px-3 py-1.5 transition-colors",
                  pathname.startsWith(`/catalog/${c.slug}`) && "bg-muted text-foreground",
                )}
              >
                {c.name}
              </Link>
            </li>
          ))}
          <li className="ml-auto">
            <Link
              href="/catalog?on_sale=1"
              className="text-destructive hover:bg-muted rounded-md px-3 py-1.5 font-medium transition-colors"
            >
              Скидки
            </Link>
          </li>
        </ul>
      </nav>
    </header>
  );
}
