// Имитация пользовательской части бэкенда в localStorage: авторизация, адреса, заказы, избранное.
// Вызывается только в браузере. Ошибки бросаются в том же формате, что и у DRF ({detail, code, fields}).
import { ApiError } from "@/lib/api/http";
import type {
  Address,
  AddressInput,
  CartLineInput,
  CheckoutSession,
  CreateOrderPayload,
  Order,
  OrderItem,
  Paginated,
  ProductListItem,
  PromoCheck,
  Review,
  ServerCart,
  ServerCartItem,
  TokenPair,
  User,
} from "@/lib/api/types";
import { calcDeliveryPrice, calcPromoDiscount } from "@/lib/utils";
import { mockProductById, mockReviews, mockVariant, toListItem } from "./catalog";

interface StoredUser extends User {
  password: string;
}

interface StoredReview extends Review {
  user_id: number;
  slug: string;
}

interface Db {
  users: StoredUser[];
  addresses: Record<number, Address[]>;
  orders: Record<number, Order[]>;
  wishlist: Record<number, number[]>;
  carts: Record<number, CartLineInput[]>;
  reviews: StoredReview[];
  session: number | null;
  seq: number;
}

const KEY = "voltra-mock-db-v1";

export const DEMO_USER = { email: "demo@voltra.kz", password: "demo12345" };

const PROMO_CODES: Record<string, { type: "percent" | "fixed"; value: number; expired?: boolean }> =
  {
    WELCOME10: { type: "percent", value: 10 },
    VOLTRA5000: { type: "fixed", value: 5000 },
    SUMMER25: { type: "percent", value: 25, expired: true },
  };

function seed(): Db {
  const demoOrderItems: OrderItem[] = [
    { variantId: 1701, quantity: 1 },
    { variantId: 2101, quantity: 1 },
  ].map(({ variantId, quantity }, i) => {
    const { product, variant } = mockVariant(variantId)!;
    return {
      id: i + 1,
      variant_id: variant.id,
      product_name: product.name,
      product_slug: product.slug,
      variant_name: variant.name,
      image: product.image,
      price: variant.price,
      quantity,
    };
  });
  const subtotal = demoOrderItems.reduce((s, it) => s + Number(it.price) * it.quantity, 0);
  return {
    users: [
      {
        id: 1,
        email: DEMO_USER.email,
        password: DEMO_USER.password,
        first_name: "Демо",
        last_name: "Покупатель",
        phone: "+7 700 000 00 00",
        avatar: null,
        is_email_verified: true,
      },
    ],
    addresses: {
      1: [
        {
          id: 1,
          city: "Алматы",
          street: "пр. Абая",
          building: "150",
          apartment: "12",
          postal_code: "050000",
          is_default: true,
        },
      ],
    },
    orders: {
      1: [
        {
          number: "VT-100245",
          status: "delivered",
          created_at: "2026-10-12T10:24:00.000Z",
          items: demoOrderItems,
          address: {
            city: "Алматы",
            street: "пр. Абая",
            building: "150",
            apartment: "12",
            postal_code: "050000",
          },
          delivery_method: "courier",
          payment_method: "card",
          subtotal: subtotal.toFixed(2),
          discount: "0.00",
          delivery_price: "0.00",
          total: subtotal.toFixed(2),
          promo_code: null,
        },
      ],
    },
    wishlist: { 1: [1, 16] },
    carts: {},
    reviews: [],
    session: null,
    seq: 100,
  };
}

function load(): Db {
  if (typeof window === "undefined") return seed();
  try {
    const stored = window.localStorage.getItem(KEY);
    if (stored) return JSON.parse(stored) as Db;
  } catch {
    // повреждённые данные — начинаем заново
  }
  const db = seed();
  save(db);
  return db;
}

function save(db: Db) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(db));
  } catch {
    // приватный режим или переполнение — работаем без сохранения
  }
}

function mutate<T>(fn: (db: Db) => T): T {
  const db = load();
  const result = fn(db);
  save(db);
  return result;
}

const delay = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms));

function fail(
  status: number,
  detail: string,
  code: string,
  fields?: Record<string, string[]>,
): never {
  throw new ApiError(status, { detail, code, fields });
}

function currentUser(db: Db): StoredUser {
  const user = db.users.find((u) => u.id === db.session);
  if (!user) fail(401, "Требуется авторизация.", "not_authenticated");
  return user;
}

function publicUser({ password: _p, ...user }: StoredUser): User {
  return user;
}

// ---------- Авторизация ----------

export async function register(data: {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}): Promise<User> {
  await delay();
  return mutate((db) => {
    const email = data.email.trim().toLowerCase();
    if (db.users.some((u) => u.email === email)) {
      fail(400, "Проверьте поля формы.", "validation_error", {
        email: ["Пользователь с таким email уже зарегистрирован."],
      });
    }
    const user: StoredUser = {
      id: ++db.seq,
      email,
      password: data.password,
      first_name: data.first_name,
      last_name: data.last_name,
      phone: "",
      avatar: null,
      // В демо письмо не отправляется, поэтому сразу считаем email подтверждённым.
      is_email_verified: true,
    };
    db.users.push(user);
    return publicUser(user);
  });
}

export async function login(email: string, password: string): Promise<TokenPair> {
  await delay();
  return mutate((db) => {
    const user = db.users.find((u) => u.email === email.trim().toLowerCase());
    if (!user || user.password !== password) {
      fail(401, "Неверный email или пароль.", "invalid_credentials");
    }
    db.session = user.id;
    return { access: `mock-access-${user.id}` };
  });
}

export async function refresh(): Promise<TokenPair | null> {
  const db = load();
  return db.session ? { access: `mock-access-${db.session}` } : null;
}

export async function logout(): Promise<void> {
  mutate((db) => {
    db.session = null;
  });
}

export async function requestPasswordReset(_email: string): Promise<void> {
  await delay();
}

export async function confirmPasswordReset(): Promise<void> {
  await delay();
  fail(400, "В демо-режиме ссылки из писем не работают.", "mock_mode");
}

export async function verifyEmail(): Promise<void> {
  await delay();
}

// ---------- Профиль и адреса ----------

export async function me(): Promise<User> {
  await delay(100);
  return publicUser(currentUser(load()));
}

export async function updateMe(data: Partial<Pick<User, "first_name" | "last_name" | "phone">>) {
  await delay();
  return mutate((db) => {
    const user = currentUser(db);
    Object.assign(user, data);
    return publicUser(user);
  });
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await delay();
  mutate((db) => {
    const user = currentUser(db);
    if (user.password !== oldPassword) {
      fail(400, "Проверьте поля формы.", "validation_error", {
        old_password: ["Текущий пароль указан неверно."],
      });
    }
    user.password = newPassword;
  });
}

export async function listAddresses(): Promise<Address[]> {
  await delay(150);
  const db = load();
  return db.addresses[currentUser(db).id] ?? [];
}

export async function saveAddress(input: AddressInput, id?: number): Promise<Address> {
  await delay();
  return mutate((db) => {
    const userId = currentUser(db).id;
    const list = (db.addresses[userId] ??= []);
    if (input.is_default || list.length === 0) list.forEach((a) => (a.is_default = false));
    const isDefault = input.is_default || list.length === 0;
    if (id) {
      const existing = list.find((a) => a.id === id);
      if (!existing) fail(404, "Адрес не найден.", "not_found");
      Object.assign(existing, input, { is_default: isDefault || existing.is_default });
      return existing;
    }
    const address: Address = { ...input, id: ++db.seq, is_default: isDefault };
    list.push(address);
    return address;
  });
}

export async function deleteAddress(id: number): Promise<void> {
  await delay();
  mutate((db) => {
    const userId = currentUser(db).id;
    const list = (db.addresses[userId] ?? []).filter((a) => a.id !== id);
    if (list.length && !list.some((a) => a.is_default)) list[0].is_default = true;
    db.addresses[userId] = list;
  });
}

// ---------- Избранное ----------

export async function listWishlist(): Promise<ProductListItem[]> {
  await delay(150);
  const db = load();
  const ids = db.wishlist[currentUser(db).id] ?? [];
  return ids
    .map((id) => mockProductById(id))
    .filter((p) => p !== null)
    .map(toListItem);
}

export async function addToWishlist(productId: number): Promise<void> {
  mutate((db) => {
    const list = (db.wishlist[currentUser(db).id] ??= []);
    if (!list.includes(productId)) list.unshift(productId);
  });
}

export async function removeFromWishlist(productId: number): Promise<void> {
  mutate((db) => {
    const userId = currentUser(db).id;
    db.wishlist[userId] = (db.wishlist[userId] ?? []).filter((id) => id !== productId);
  });
}

// ---------- Корзина и промокоды ----------

export async function mergeCart(items: CartLineInput[]): Promise<ServerCart> {
  await delay(150);
  return mutate((db) => {
    const userId = currentUser(db).id;
    const merged = new Map((db.carts[userId] ?? []).map((i) => [i.variant_id, i.quantity]));
    for (const item of items) {
      merged.set(item.variant_id, Math.max(merged.get(item.variant_id) ?? 0, item.quantity));
    }
    db.carts[userId] = [...merged].map(([variant_id, quantity]) => ({ variant_id, quantity }));
    const cartItems: ServerCartItem[] = db.carts[userId].flatMap((line, i) => {
      const found = mockVariant(line.variant_id);
      if (!found) return [];
      const { product, variant } = found;
      return [
        {
          id: i + 1,
          variant,
          product: { id: product.id, name: product.name, slug: product.slug, image: product.image },
          quantity: Math.min(line.quantity, variant.stock),
        },
      ];
    });
    return { id: userId, items: cartItems };
  });
}

export async function replaceCart(items: CartLineInput[]): Promise<void> {
  mutate((db) => {
    db.carts[currentUser(db).id] = items;
  });
}

export async function checkPromo(code: string, subtotal: number): Promise<PromoCheck> {
  await delay();
  const promo = PROMO_CODES[code.trim().toUpperCase()];
  if (!promo) fail(400, "Такого промокода нет.", "promo_not_found");
  if (promo.expired) fail(400, "Срок действия промокода истёк.", "promo_expired");
  return {
    code: code.trim().toUpperCase(),
    type: promo.type,
    value: promo.value.toFixed(2),
    discount: calcPromoDiscount(subtotal, promo.type, promo.value).toFixed(2),
  };
}

// ---------- Заказы и оплата ----------

export async function createOrder(payload: CreateOrderPayload): Promise<Order> {
  await delay(500);
  return mutate((db) => {
    const user = currentUser(db);
    if (!payload.items.length) fail(400, "Корзина пуста.", "cart_empty");

    const items: OrderItem[] = payload.items.map((line, i) => {
      const found = mockVariant(line.variant_id);
      if (!found) fail(400, "Товар больше не продаётся.", "variant_not_found");
      const { product, variant } = found;
      if (variant.stock < line.quantity) {
        fail(400, `«${product.name}» осталось только ${variant.stock} шт.`, "out_of_stock");
      }
      return {
        id: i + 1,
        variant_id: variant.id,
        product_name: product.name,
        product_slug: product.slug,
        variant_name: variant.name,
        image: product.image,
        price: variant.price,
        quantity: line.quantity,
      };
    });

    const subtotal = items.reduce((s, it) => s + Number(it.price) * it.quantity, 0);
    let discount = 0;
    if (payload.promo_code) {
      const promo = PROMO_CODES[payload.promo_code];
      if (promo && !promo.expired) discount = calcPromoDiscount(subtotal, promo.type, promo.value);
    }
    const deliveryPrice = calcDeliveryPrice(payload.delivery_method, subtotal - discount);

    let address: Order["address"] = null;
    if (payload.delivery_method === "courier") {
      const found = (db.addresses[user.id] ?? []).find((a) => a.id === payload.address_id);
      if (!found) fail(400, "Укажите адрес доставки.", "address_required");
      const { id: _id, is_default: _d, ...rest } = found;
      address = rest;
    }

    const order: Order = {
      number: `VT-${100000 + ++db.seq}`,
      status: "created",
      created_at: new Date().toISOString(),
      items,
      address,
      delivery_method: payload.delivery_method,
      payment_method: payload.payment_method,
      subtotal: subtotal.toFixed(2),
      discount: discount.toFixed(2),
      delivery_price: deliveryPrice.toFixed(2),
      total: (subtotal - discount + deliveryPrice).toFixed(2),
      promo_code: discount ? payload.promo_code! : null,
    };
    (db.orders[user.id] ??= []).unshift(order);
    db.carts[user.id] = [];
    return order;
  });
}

export async function listOrders(): Promise<Paginated<Order>> {
  await delay(200);
  const db = load();
  const results = db.orders[currentUser(db).id] ?? [];
  return { count: results.length, next: null, previous: null, results };
}

export async function getOrder(number: string): Promise<Order> {
  await delay(150);
  const db = load();
  const order = (db.orders[currentUser(db).id] ?? []).find((o) => o.number === number);
  if (!order) fail(404, "Заказ не найден.", "not_found");
  return order;
}

export async function cancelOrder(number: string): Promise<Order> {
  await delay();
  return mutate((db) => {
    const order = (db.orders[currentUser(db).id] ?? []).find((o) => o.number === number);
    if (!order) fail(404, "Заказ не найден.", "not_found");
    if (order.status !== "created" && order.status !== "paid") {
      fail(400, "Этот заказ уже нельзя отменить.", "order_not_cancellable");
    }
    order.status = "cancelled";
    return order;
  });
}

// Вместо Stripe Checkout: помечаем заказ оплаченным (как это сделал бы вебхук) и сразу ведём на успех.
export async function createCheckoutSession(orderNumber: string): Promise<CheckoutSession> {
  await delay(600);
  mutate((db) => {
    const order = (db.orders[currentUser(db).id] ?? []).find((o) => o.number === orderNumber);
    if (order && order.status === "created") order.status = "paid";
  });
  return { url: `/checkout/success?order=${orderNumber}` };
}

// ---------- Отзывы ----------

export async function listReviews(slug: string, page: number): Promise<Paginated<Review>> {
  await delay(150);
  const own = load()
    .reviews.filter((r) => r.slug === slug)
    .map(({ user_id: _u, slug: _s, ...r }) => r);
  const base = mockReviews(slug, 1, 1000).results;
  const all = [...own, ...base];
  const size = 5;
  return {
    count: all.length,
    next: page * size < all.length ? `?page=${page + 1}` : null,
    previous: page > 1 ? `?page=${page - 1}` : null,
    results: all.slice((page - 1) * size, page * size),
  };
}

export async function createReview(
  slug: string,
  data: { rating: number; text: string; images: File[] },
): Promise<Review> {
  await delay(400);
  return mutate((db) => {
    const user = currentUser(db);
    const bought = (db.orders[user.id] ?? []).some(
      (o) => o.status === "delivered" && o.items.some((it) => it.product_slug === slug),
    );
    if (!bought) {
      fail(403, "Отзыв можно оставить только на полученный товар.", "review_not_purchased");
    }
    if (db.reviews.some((r) => r.slug === slug && r.user_id === user.id)) {
      fail(400, "Вы уже оставили отзыв на этот товар.", "review_exists");
    }
    const review: StoredReview = {
      id: ++db.seq,
      user_id: user.id,
      slug,
      author: `${user.first_name} ${user.last_name.charAt(0)}.`.trim(),
      rating: data.rating,
      text: data.text,
      // Фото в демо не сохраняем: localStorage для этого не подходит.
      images: [],
      created_at: new Date().toISOString(),
    };
    db.reviews.unshift(review);
    const { user_id: _u, slug: _s, ...result } = review;
    return result;
  });
}
