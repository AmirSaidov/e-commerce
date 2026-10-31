import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { CURRENCY, DELIVERY } from "@/lib/config";
import type { DeliveryMethod, Money, PromoType } from "@/lib/api/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// narrowSymbol: без него ru-RU выводит «KZT» вместо «₸», и разные движки могут разойтись (ошибка гидрации).
const priceFormatter = new Intl.NumberFormat("ru-RU", {
  style: "currency",
  currency: CURRENCY,
  currencyDisplay: "narrowSymbol",
  maximumFractionDigits: 0,
});

export function toNumber(value: Money | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  return typeof value === "number" ? value : Number.parseFloat(value);
}

export function formatPrice(value: Money | number): string {
  return priceFormatter.format(toNumber(value));
}

export function discountPercent(price: Money, oldPrice: Money | null): number | null {
  const now = toNumber(price);
  const before = toNumber(oldPrice);
  if (!before || before <= now) return null;
  return Math.round((1 - now / before) * 100);
}

export function calcPromoDiscount(subtotal: number, type: PromoType, value: number): number {
  const raw = type === "percent" ? (subtotal * value) / 100 : value;
  return Math.min(Math.round(raw), subtotal);
}

export function calcDeliveryPrice(method: DeliveryMethod, subtotalAfterDiscount: number): number {
  const rule = DELIVERY[method];
  if (rule.freeFrom && subtotalAfterDiscount >= rule.freeFrom) return 0;
  return rule.price;
}

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(iso));
}

export function pluralize(count: number, forms: [string, string, string]): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return forms[0];
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return forms[1];
  return forms[2];
}
