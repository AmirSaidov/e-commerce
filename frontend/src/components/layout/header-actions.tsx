"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  Heart,
  LogOut,
  Moon,
  Package,
  ShoppingBag,
  ShoppingCart,
  Sun,
  User,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useState } from "react";
import { CartLineItem } from "@/components/cart/cart-line";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/misc";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { useHydrated } from "@/hooks/use-hydrated";
import { formatPrice } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { cartTotals, useCartStore } from "@/stores/cart";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const hydrated = useHydrated();
  const isDark = hydrated && resolvedTheme === "dark";
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Включить светлую тему" : "Включить тёмную тему"}
    >
      {isDark ? <Sun /> : <Moon />}
    </Button>
  );
}

export function UserMenu() {
  const router = useRouter();
  const { status, user, logout } = useAuthStore();

  if (status !== "authenticated" || !user) {
    return (
      <Button asChild variant="ghost" size="icon" aria-label="Войти">
        <Link href="/login">
          <User />
        </Link>
      </Button>
    );
  }

  const item =
    "flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm outline-none data-[highlighted]:bg-muted [&_svg]:size-4 [&_svg]:text-muted-foreground";

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <Button variant="ghost" size="icon" aria-label="Меню профиля">
          <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-full text-xs font-semibold">
            {(user.first_name[0] ?? user.email[0]).toUpperCase()}
          </span>
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="animate-fade-in bg-card z-50 w-56 rounded-xl border p-1 shadow-xl"
        >
          <div className="px-2 py-2">
            <p className="truncate text-sm font-medium">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-muted-foreground truncate text-xs">{user.email}</p>
          </div>
          <DropdownMenu.Separator className="bg-border my-1 h-px" />
          <DropdownMenu.Item className={item} onSelect={() => router.push("/account")}>
            <UserRound /> Профиль
          </DropdownMenu.Item>
          <DropdownMenu.Item className={item} onSelect={() => router.push("/account/orders")}>
            <Package /> Мои заказы
          </DropdownMenu.Item>
          <DropdownMenu.Item className={item} onSelect={() => router.push("/account/wishlist")}>
            <Heart /> Избранное
          </DropdownMenu.Item>
          <DropdownMenu.Separator className="bg-border my-1 h-px" />
          <DropdownMenu.Item
            className={item}
            onSelect={async () => {
              await logout();
              router.push("/");
            }}
          >
            <LogOut /> Выйти
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

export function MiniCart() {
  const [open, setOpen] = useState(false);
  const hydrated = useHydrated();
  const lines = useCartStore((s) => s.lines);
  const promo = useCartStore((s) => s.promo);
  const { count, subtotal, discount, total } = cartTotals(lines, promo);
  const shownCount = hydrated ? count : 0;
  const close = () => setOpen(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => setOpen(true)}
        aria-label={`Корзина, товаров: ${shownCount}`}
      >
        <ShoppingCart />
        {shownCount > 0 && (
          <span className="bg-primary text-primary-foreground absolute -top-0.5 -right-0.5 flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] font-semibold tabular-nums">
            {shownCount > 99 ? "99+" : shownCount}
          </span>
        )}
      </Button>
      <SheetContent title="Корзина" description={count ? `Товаров: ${count}` : undefined}>
        {lines.length === 0 ? (
          <div className="flex flex-1 items-center p-5">
            <div className="w-full">
              <EmptyState
                icon={<ShoppingBag />}
                title="Корзина пуста"
                description="Загляните в каталог — там много интересного."
                action={
                  <Button asChild onClick={close}>
                    <Link href="/catalog">В каталог</Link>
                  </Button>
                }
              />
            </div>
          </div>
        ) : (
          <>
            <ul className="flex-1 divide-y overflow-y-auto px-5">
              {lines.map((line) => (
                <CartLineItem key={line.variantId} line={line} compact onNavigate={close} />
              ))}
            </ul>
            <div className="space-y-3 border-t p-5">
              {discount > 0 && (
                <div className="text-success flex justify-between text-sm">
                  <span>Промокод {promo?.code}</span>
                  <span className="tabular-nums">−{formatPrice(discount)}</span>
                </div>
              )}
              <div className="flex items-baseline justify-between">
                <span className="text-muted-foreground">Итого</span>
                <span className="text-xl font-bold tabular-nums">
                  {formatPrice(discount ? total : subtotal)}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Button asChild variant="outline" onClick={close}>
                  <Link href="/cart">В корзину</Link>
                </Button>
                <Button asChild onClick={close}>
                  <Link href="/checkout">Оформить</Link>
                </Button>
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
