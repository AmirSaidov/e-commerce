// Типы ответов API. Повторяют модели из ТЗ (раздел 5) и то, как их отдаёт DRF:
// DecimalField сериализуется строкой, даты — ISO 8601.

export type Money = string;

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiErrorBody {
  detail?: string;
  code?: string;
  fields?: Record<string, string[]>;
}

// ---------- Каталог ----------

export interface Category {
  id: number;
  name: string;
  slug: string;
  parent: number | null;
  image: string | null;
  children: Category[];
}

export interface Brand {
  id: number;
  name: string;
  slug: string;
  logo: string | null;
}

export interface CategoryRef {
  id: number;
  name: string;
  slug: string;
}

export interface BrandRef {
  id: number;
  name: string;
  slug: string;
}

export interface ProductImage {
  id: number;
  image: string;
  alt: string;
  order: number;
}

export interface ProductVariant {
  id: number;
  sku: string;
  name: string;
  price: Money;
  old_price: Money | null;
  stock: number;
}

export interface ProductListItem {
  id: number;
  name: string;
  slug: string;
  category: CategoryRef;
  brand: BrandRef;
  image: string | null;
  /** Цена самого дешёвого варианта в наличии (или самого дешёвого вообще). */
  price: Money;
  old_price: Money | null;
  rating: number;
  reviews_count: number;
  in_stock: boolean;
  variants_count: number;
  /** Вариант для кнопки «В корзину» прямо из каталога. */
  default_variant: ProductVariant;
  created_at: string;
}

export interface ProductDetail extends ProductListItem {
  description: string;
  specs: Record<string, string>;
  images: ProductImage[];
  variants: ProductVariant[];
}

export type ProductOrdering = "-popularity" | "price" | "-price" | "-created_at" | "-rating";

export interface ProductQuery {
  category?: string;
  brand?: string[];
  price_min?: number;
  price_max?: number;
  rating_min?: number;
  in_stock?: boolean;
  on_sale?: boolean;
  ordering?: ProductOrdering;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface Review {
  id: number;
  author: string;
  rating: number;
  text: string;
  images: string[];
  created_at: string;
}

// ---------- Пользователь ----------

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  avatar: string | null;
  is_email_verified: boolean;
}

export interface Address {
  id: number;
  city: string;
  street: string;
  building: string;
  apartment: string;
  postal_code: string;
  is_default: boolean;
}

export type AddressInput = Omit<Address, "id">;

export interface TokenPair {
  access: string;
}

// ---------- Корзина, заказы, оплата ----------

export interface ServerCartItem {
  id: number;
  variant: ProductVariant;
  product: Pick<ProductListItem, "id" | "name" | "slug" | "image">;
  quantity: number;
}

export interface ServerCart {
  id: number;
  items: ServerCartItem[];
}

export interface CartLineInput {
  variant_id: number;
  quantity: number;
}

export type PromoType = "percent" | "fixed";

export interface PromoCheck {
  code: string;
  type: PromoType;
  value: Money;
  /** Скидка для переданного subtotal. */
  discount: Money;
}

export type OrderStatus = "created" | "paid" | "assembling" | "shipped" | "delivered" | "cancelled";
export type DeliveryMethod = "courier" | "pickup";
export type PaymentMethod = "card" | "cash";

export interface OrderItem {
  id: number;
  variant_id: number;
  product_name: string;
  product_slug: string;
  variant_name: string;
  image: string | null;
  price: Money;
  quantity: number;
}

export interface Order {
  number: string;
  status: OrderStatus;
  created_at: string;
  items: OrderItem[];
  address: Omit<Address, "id" | "is_default"> | null;
  delivery_method: DeliveryMethod;
  payment_method: PaymentMethod;
  subtotal: Money;
  discount: Money;
  delivery_price: Money;
  total: Money;
  promo_code: string | null;
}

export interface CreateOrderPayload {
  address_id?: number;
  delivery_method: DeliveryMethod;
  payment_method: PaymentMethod;
  promo_code?: string;
  items: CartLineInput[];
}

export interface CheckoutSession {
  url: string;
}
