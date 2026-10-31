"use client";

import { Heart, LogOut, MapPin, Package, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";

const LINKS = [
  { href: "/account", label: "Профиль", icon: UserRound },
  { href: "/account/orders", label: "Заказы", icon: Package },
  { href: "/account/addresses", label: "Адреса", icon: MapPin },
  { href: "/account/wishlist", label: "Избранное", icon: Heart },
];

export function AccountNav() {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);
  const item =
    "flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors [&_svg]:size-4";

  return (
    <nav
      aria-label="Личный кабинет"
      className="no-scrollbar -mx-4 overflow-x-auto px-4 lg:mx-0 lg:px-0"
    >
      <ul className="flex gap-1 lg:flex-col">
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active = href === "/account" ? pathname === href : pathname.startsWith(href);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  item,
                  active
                    ? "bg-primary-soft text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon /> {label}
              </Link>
            </li>
          );
        })}
        <li className="lg:mt-4 lg:border-t lg:pt-4">
          <button
            type="button"
            onClick={async () => {
              await logout();
              router.push("/");
            }}
            className={cn(
              item,
              "text-muted-foreground hover:bg-muted hover:text-destructive w-full",
            )}
          >
            <LogOut /> Выйти
          </button>
        </li>
      </ul>
    </nav>
  );
}
