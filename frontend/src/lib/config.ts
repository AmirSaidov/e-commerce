export const API_MODE: "mock" | "api" = process.env.NEXT_PUBLIC_API_MODE === "api" ? "api" : "mock";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(
  /\/$/,
  "",
);

export const SITE_NAME = "Voltra";

export const CURRENCY = "KZT";

export const PAGE_SIZE = 20;

// Стоимость доставки должна совпадать с расчётом на бэкенде (orders/services.py).
export const DELIVERY = {
  courier: { label: "Курьером", price: 1500, freeFrom: 100_000, eta: "1–2 дня" },
  pickup: { label: "Самовывоз", price: 0, freeFrom: 0, eta: "сегодня, после 18:00" },
} as const;
