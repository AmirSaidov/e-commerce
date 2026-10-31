// Единая точка доступа к данным. NEXT_PUBLIC_API_MODE=api — запросы в Django REST Framework,
// mock — встроенные демо-данные. Компоненты используют только `api` и не знают, какой режим включён.
import { API_MODE } from "@/lib/config";
import * as mockBackend from "@/lib/mock/backend";
import * as mockCatalog from "@/lib/mock/catalog";
import { ApiError, refreshAccessToken, request, setAccessToken } from "./http";
import type {
  Address,
  AddressInput,
  Brand,
  CartLineInput,
  Category,
  CheckoutSession,
  CreateOrderPayload,
  Order,
  Paginated,
  ProductDetail,
  ProductListItem,
  ProductQuery,
  PromoCheck,
  Review,
  ServerCart,
  TokenPair,
  User,
} from "./types";

export { ApiError };
export type * from "./types";

/** Каталог кэшируется Next.js и обновляется раз в минуту (ISR). */
const CATALOG_REVALIDATE = 60;

const realApi = {
  catalog: {
    categories: () => request<Category[]>("/categories/", { revalidate: CATALOG_REVALIDATE }),
    brands: () => request<Brand[]>("/brands/", { revalidate: CATALOG_REVALIDATE }),
    products: (query: ProductQuery = {}) =>
      request<Paginated<ProductListItem>>("/products/", {
        query: { ...query },
        revalidate: CATALOG_REVALIDATE,
      }),
    product: async (slug: string): Promise<ProductDetail | null> => {
      try {
        return await request<ProductDetail>(`/products/${slug}/`, {
          revalidate: CATALOG_REVALIDATE,
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    related: (slug: string) =>
      request<ProductListItem[]>(`/products/${slug}/related/`, { revalidate: CATALOG_REVALIDATE }),
    search: (q: string, signal?: AbortSignal) =>
      request<ProductListItem[]>("/products/search/", { query: { q }, signal }),
  },
  reviews: {
    list: (slug: string, page = 1) =>
      request<Paginated<Review>>(`/products/${slug}/reviews/`, { query: { page } }),
    create: (slug: string, data: { rating: number; text: string; images: File[] }) => {
      const form = new FormData();
      form.set("rating", String(data.rating));
      form.set("text", data.text);
      data.images.forEach((file) => form.append("images", file));
      return request<Review>(`/products/${slug}/reviews/`, {
        method: "POST",
        body: form,
        auth: true,
      });
    },
  },
  auth: {
    register: (data: { email: string; password: string; first_name: string; last_name: string }) =>
      request<User>("/auth/register/", { method: "POST", body: data }),
    login: async (email: string, password: string) => {
      const tokens = await request<TokenPair>("/auth/login/", {
        method: "POST",
        body: { email, password },
      });
      setAccessToken(tokens.access);
      return tokens;
    },
    /** Восстанавливает сессию по refresh-cookie. */
    restore: () => refreshAccessToken(),
    logout: async () => {
      try {
        await request<void>("/auth/logout/", { method: "POST", auth: true });
      } finally {
        setAccessToken(null);
      }
    },
    verifyEmail: (uid: string, token: string) =>
      request<void>("/auth/verify-email/", { method: "POST", body: { uid, token } }),
    requestPasswordReset: (email: string) =>
      request<void>("/auth/password-reset/", { method: "POST", body: { email } }),
    confirmPasswordReset: (uid: string, token: string, password: string) =>
      request<void>("/auth/password-reset/confirm/", {
        method: "POST",
        body: { uid, token, password },
      }),
  },
  users: {
    me: () => request<User>("/users/me/", { auth: true }),
    update: (data: Partial<Pick<User, "first_name" | "last_name" | "phone">>) =>
      request<User>("/users/me/", { method: "PATCH", body: data, auth: true }),
    changePassword: (old_password: string, new_password: string) =>
      request<void>("/users/me/password/", {
        method: "POST",
        body: { old_password, new_password },
        auth: true,
      }),
  },
  addresses: {
    list: () => request<Address[]>("/users/me/addresses/", { auth: true }),
    save: (data: AddressInput, id?: number) =>
      id
        ? request<Address>(`/users/me/addresses/${id}/`, {
            method: "PATCH",
            body: data,
            auth: true,
          })
        : request<Address>("/users/me/addresses/", { method: "POST", body: data, auth: true }),
    remove: (id: number) =>
      request<void>(`/users/me/addresses/${id}/`, { method: "DELETE", auth: true }),
  },
  wishlist: {
    list: () => request<ProductListItem[]>("/wishlist/", { auth: true }),
    add: (productId: number) =>
      request<void>("/wishlist/", { method: "POST", body: { product_id: productId }, auth: true }),
    remove: (productId: number) =>
      request<void>(`/wishlist/${productId}/`, { method: "DELETE", auth: true }),
  },
  cart: {
    /** После входа: сливает гостевую корзину с серверной и возвращает итог. */
    merge: (items: CartLineInput[]) =>
      request<ServerCart>("/cart/merge/", { method: "POST", body: { items }, auth: true }),
    replace: (items: CartLineInput[]) =>
      request<void>("/cart/", { method: "PUT", body: { items }, auth: true }),
    checkPromo: (code: string, subtotal: number) =>
      request<PromoCheck>("/cart/apply-promo/", { method: "POST", body: { code, subtotal } }),
  },
  orders: {
    list: () => request<Paginated<Order>>("/orders/", { query: { page_size: 50 }, auth: true }),
    get: (number: string) => request<Order>(`/orders/${number}/`, { auth: true }),
    create: (payload: CreateOrderPayload) =>
      request<Order>("/orders/", { method: "POST", body: payload, auth: true }),
    cancel: (number: string) =>
      request<Order>(`/orders/${number}/cancel/`, { method: "POST", auth: true }),
  },
  payments: {
    checkoutSession: (orderNumber: string) =>
      request<CheckoutSession>("/payments/checkout-session/", {
        method: "POST",
        body: { order_number: orderNumber },
        auth: true,
      }),
  },
};

export type Api = typeof realApi;

const mockApi: Api = {
  catalog: {
    categories: async () => mockCatalog.mockCategories(),
    brands: async () => mockCatalog.mockBrands(),
    products: async (query) => mockCatalog.mockProducts(query),
    product: async (slug) => mockCatalog.mockProduct(slug),
    related: async (slug) => mockCatalog.mockRelated(slug),
    search: async (q) => mockCatalog.mockSearch(q),
  },
  reviews: {
    list: (slug, page = 1) => mockBackend.listReviews(slug, page),
    create: (slug, data) => mockBackend.createReview(slug, data),
  },
  auth: {
    register: (data) => mockBackend.register(data),
    login: async (email, password) => {
      const tokens = await mockBackend.login(email, password);
      setAccessToken(tokens.access);
      return tokens;
    },
    restore: async () => {
      const tokens = await mockBackend.refresh();
      setAccessToken(tokens?.access ?? null);
      return tokens !== null;
    },
    logout: async () => {
      await mockBackend.logout();
      setAccessToken(null);
    },
    verifyEmail: () => mockBackend.verifyEmail(),
    requestPasswordReset: (email) => mockBackend.requestPasswordReset(email),
    confirmPasswordReset: () => mockBackend.confirmPasswordReset(),
  },
  users: {
    me: () => mockBackend.me(),
    update: (data) => mockBackend.updateMe(data),
    changePassword: (oldPassword, newPassword) =>
      mockBackend.changePassword(oldPassword, newPassword),
  },
  addresses: {
    list: () => mockBackend.listAddresses(),
    save: (data, id) => mockBackend.saveAddress(data, id),
    remove: (id) => mockBackend.deleteAddress(id),
  },
  wishlist: {
    list: () => mockBackend.listWishlist(),
    add: (productId) => mockBackend.addToWishlist(productId),
    remove: (productId) => mockBackend.removeFromWishlist(productId),
  },
  cart: {
    merge: (items) => mockBackend.mergeCart(items),
    replace: (items) => mockBackend.replaceCart(items),
    checkPromo: (code, subtotal) => mockBackend.checkPromo(code, subtotal),
  },
  orders: {
    list: () => mockBackend.listOrders(),
    get: (number) => mockBackend.getOrder(number),
    create: (payload) => mockBackend.createOrder(payload),
    cancel: (number) => mockBackend.cancelOrder(number),
  },
  payments: {
    checkoutSession: (orderNumber) => mockBackend.createCheckoutSession(orderNumber),
  },
};

export const api: Api = API_MODE === "mock" ? mockApi : realApi;
