import { CreditCard, RotateCcw, ShieldCheck, Truck } from "lucide-react";
import Link from "next/link";
import type { Category } from "@/lib/api/types";
import { SITE_NAME } from "@/lib/config";
import { Logo } from "./header";

const BENEFITS = [
  { icon: Truck, title: "Бесплатная доставка", text: "по городу от 100 000 ₸" },
  { icon: ShieldCheck, title: "Официальная гарантия", text: "только оригинальная техника" },
  { icon: RotateCcw, title: "Возврат 14 дней", text: "без лишних вопросов" },
  { icon: CreditCard, title: "Удобная оплата", text: "картой онлайн или при получении" },
];

export function Benefits() {
  return (
    <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {BENEFITS.map(({ icon: Icon, title, text }) => (
        <li key={title} className="bg-card flex items-start gap-3 rounded-2xl border p-4">
          <span className="bg-primary-soft text-primary flex size-10 shrink-0 items-center justify-center rounded-xl">
            <Icon className="size-5" />
          </span>
          <div>
            <p className="text-sm font-semibold">{title}</p>
            <p className="text-muted-foreground text-xs">{text}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function Footer({ categories }: { categories: Category[] }) {
  return (
    <footer className="bg-muted/40 mt-20 border-t">
      <div className="container-page grid gap-10 py-12 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-3">
          <Logo />
          <p className="text-muted-foreground max-w-xs text-sm">
            Магазин электроники и гаджетов: смартфоны, ноутбуки, аудио и всё для игр.
          </p>
        </div>
        <nav aria-label="Каталог">
          <h2 className="mb-3 text-sm font-semibold">Каталог</h2>
          <ul className="text-muted-foreground space-y-2 text-sm">
            {categories.map((c) => (
              <li key={c.id}>
                <Link href={`/catalog/${c.slug}`} className="hover:text-foreground">
                  {c.name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <nav aria-label="Покупателям">
          <h2 className="mb-3 text-sm font-semibold">Покупателям</h2>
          <ul className="text-muted-foreground space-y-2 text-sm">
            <li>
              <Link href="/account" className="hover:text-foreground">
                Личный кабинет
              </Link>
            </li>
            <li>
              <Link href="/account/orders" className="hover:text-foreground">
                Мои заказы
              </Link>
            </li>
            <li>
              <Link href="/cart" className="hover:text-foreground">
                Корзина
              </Link>
            </li>
            <li>
              <Link href="/catalog?on_sale=1" className="hover:text-foreground">
                Скидки
              </Link>
            </li>
          </ul>
        </nav>
        <div>
          <h2 className="mb-3 text-sm font-semibold">О проекте</h2>
          <p className="text-muted-foreground text-sm">
            Учебный портфолио-проект: Next.js + Django REST Framework. Оплата работает в тестовом
            режиме, реальные заказы не принимаются.
          </p>
        </div>
      </div>
      <div className="border-t">
        <div className="container-page text-muted-foreground flex flex-col gap-2 py-5 text-xs sm:flex-row sm:justify-between">
          <p>
            © {new Date().getFullYear()} {SITE_NAME}. Демо-магазин.
          </p>
          <p>Айбек — backend · Амир — frontend</p>
        </div>
      </div>
    </footer>
  );
}
