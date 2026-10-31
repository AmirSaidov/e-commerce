// Демо-каталог: повторяет то, что вернёт DRF, чтобы фронт работал без бэкенда.
// Модуль чистый (без window), поэтому его можно вызывать из серверных компонентов.
import { PAGE_SIZE } from "@/lib/config";
import type {
  Brand,
  Category,
  Paginated,
  ProductDetail,
  ProductListItem,
  ProductQuery,
  ProductVariant,
  Review,
} from "@/lib/api/types";
import raw from "./catalog.json";

interface RawVariant {
  name: string;
  delta: number;
  stock: number;
}

const categoriesFlat: Category[] = raw.categories.map((c, i) => ({
  id: i + 1,
  name: c.name,
  slug: c.slug,
  parent: null,
  image: `/mock/categories/${c.slug}.svg`,
  children: [],
}));
const categoryBySlug = new Map(categoriesFlat.map((c) => [c.slug, c]));
raw.categories.forEach((c, i) => {
  if (c.parent) {
    const parent = categoryBySlug.get(c.parent)!;
    categoriesFlat[i].parent = parent.id;
    parent.children.push(categoriesFlat[i]);
  }
});
const categoryTree = categoriesFlat.filter((c) => c.parent === null);

const brands: Brand[] = raw.brands.map((b, i) => ({ id: i + 1, ...b, logo: null }));
const brandBySlug = new Map(brands.map((b) => [b.slug, b]));

const REVIEW_TEXTS = [
  "Пользуюсь уже месяц — полностью доволен. Доставили на следующий день, всё упаковано аккуратно.",
  "Отличное качество сборки, работает быстро. За свои деньги лучше варианта не нашёл.",
  "Хороший товар, но хотелось бы чуть больше времени автономной работы. В остальном всё супер.",
  "Брал в подарок — очень понравилось. Магазину спасибо за быструю доставку и консультацию.",
  "Сравнивал с конкурентами, остановился на этом и не пожалел. Рекомендую.",
  "Всё как в описании. Настроил за пять минут, пользоваться удобно.",
  "Качество отличное, но коробка пришла слегка помятой. Сам товар в идеальном состоянии.",
  "Второй раз покупаю здесь — цены ниже, чем в других магазинах, и всё оригинальное.",
];
const AUTHORS = [
  "Айгерим С.",
  "Данияр К.",
  "Мария П.",
  "Тимур А.",
  "Алина Ж.",
  "Ерлан Б.",
  "Ольга В.",
  "Нурлан М.",
];

const reviewsBySlug = new Map<string, Review[]>();

const products: ProductDetail[] = raw.products.map((p, i) => {
  const id = i + 1;
  const category = categoryBySlug.get(p.category)!;
  const brand = brandBySlug.get(p.brand)!;
  const variants: ProductVariant[] = (p.variants as RawVariant[]).map((v, j) => ({
    id: id * 100 + j + 1,
    sku: `${p.slug.toUpperCase().replace(/-/g, "").slice(0, 10)}-${j + 1}`,
    name: v.name,
    price: (p.price + v.delta).toFixed(2),
    old_price: p.old_price ? (p.old_price + v.delta).toFixed(2) : null,
    stock: v.stock,
  }));
  const byPrice = [...variants].sort((a, b) => Number(a.price) - Number(b.price));
  const defaultVariant = byPrice.find((v) => v.stock > 0) ?? byPrice[0];

  // Отзывы подбираем так, чтобы средняя оценка совпадала с рейтингом из JSON.
  const count = Math.max(2, Math.round(p.popularity / 12));
  const fives = Math.min(count, Math.round((p.rating - 4) * count));
  const reviews: Review[] = Array.from({ length: count }, (_, k) => ({
    id: id * 1000 + k + 1,
    author: AUTHORS[(i + k) % AUTHORS.length],
    rating: k < fives ? 5 : 4,
    text: REVIEW_TEXTS[(i * 3 + k) % REVIEW_TEXTS.length],
    images: [],
    created_at: new Date(Date.parse(p.created) + (k + 1) * 6 * 864e5).toISOString(),
  })).reverse();
  reviewsBySlug.set(p.slug, reviews);
  const rating = Math.round((reviews.reduce((s, r) => s + r.rating, 0) / count) * 10) / 10;

  return {
    id,
    name: p.name,
    slug: p.slug,
    category: { id: category.id, name: category.name, slug: category.slug },
    brand: { id: brand.id, name: brand.name, slug: brand.slug },
    image: `/mock/products/${p.slug}-1.svg`,
    price: defaultVariant.price,
    old_price: defaultVariant.old_price,
    rating,
    reviews_count: count,
    in_stock: variants.some((v) => v.stock > 0),
    variants_count: variants.length,
    default_variant: defaultVariant,
    created_at: new Date(p.created).toISOString(),
    description: p.description,
    specs: Object.fromEntries(
      Object.entries(p.specs).filter(
        (entry): entry is [string, string] => typeof entry[1] === "string",
      ),
    ),
    images: [1, 2, 3].map((n) => ({
      id: id * 10 + n,
      image: `/mock/products/${p.slug}-${n}.svg`,
      alt: `${p.name} — фото ${n}`,
      order: n,
    })),
    variants,
  };
});
const popularity = new Map(raw.products.map((p) => [p.slug, p.popularity]));
const productBySlug = new Map(products.map((p) => [p.slug, p]));

export function toListItem(p: ProductDetail): ProductListItem {
  const { description: _d, specs: _s, images: _i, variants: _v, ...item } = p;
  return item;
}

function descendantSlugs(slug: string): Set<string> {
  const result = new Set<string>();
  const walk = (c: Category) => {
    result.add(c.slug);
    c.children.forEach(walk);
  };
  const root = categoryBySlug.get(slug);
  if (root) walk(root);
  return result;
}

function matchesSearch(p: ProductDetail, search: string): boolean {
  const haystack = `${p.name} ${p.brand.name} ${p.category.name} ${p.description}`.toLowerCase();
  return search
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word));
}

export function mockCategories(): Category[] {
  return categoryTree;
}

export function mockAllCategories(): Category[] {
  return categoriesFlat;
}

export function mockBrands(): Brand[] {
  return brands;
}

export function mockProducts(query: ProductQuery = {}): Paginated<ProductListItem> {
  let list = products;
  if (query.category) {
    const slugs = descendantSlugs(query.category);
    list = list.filter((p) => slugs.has(p.category.slug));
  }
  if (query.brand?.length) list = list.filter((p) => query.brand!.includes(p.brand.slug));
  if (query.price_min !== undefined) list = list.filter((p) => Number(p.price) >= query.price_min!);
  if (query.price_max !== undefined) list = list.filter((p) => Number(p.price) <= query.price_max!);
  if (query.rating_min !== undefined) list = list.filter((p) => p.rating >= query.rating_min!);
  if (query.in_stock) list = list.filter((p) => p.in_stock);
  if (query.on_sale) list = list.filter((p) => p.old_price !== null);
  if (query.search) list = list.filter((p) => matchesSearch(p, query.search!));

  const ordering = query.ordering ?? "-popularity";
  const sorted = [...list].sort((a, b) => {
    switch (ordering) {
      case "price":
        return Number(a.price) - Number(b.price);
      case "-price":
        return Number(b.price) - Number(a.price);
      case "-created_at":
        return b.created_at.localeCompare(a.created_at);
      case "-rating":
        return b.rating - a.rating;
      default:
        return (popularity.get(b.slug) ?? 0) - (popularity.get(a.slug) ?? 0);
    }
  });

  const pageSize = query.page_size ?? PAGE_SIZE;
  const page = Math.max(1, query.page ?? 1);
  const results = sorted.slice((page - 1) * pageSize, page * pageSize).map(toListItem);
  const hasNext = page * pageSize < sorted.length;
  return {
    count: sorted.length,
    next: hasNext ? `?page=${page + 1}` : null,
    previous: page > 1 ? `?page=${page - 1}` : null,
    results,
  };
}

export function mockProduct(slug: string): ProductDetail | null {
  return productBySlug.get(slug) ?? null;
}

export function mockProductById(id: number): ProductDetail | null {
  return products.find((p) => p.id === id) ?? null;
}

export function mockVariant(
  variantId: number,
): { product: ProductDetail; variant: ProductVariant } | null {
  const product = mockProductById(Math.floor(variantId / 100));
  const variant = product?.variants.find((v) => v.id === variantId);
  return product && variant ? { product, variant } : null;
}

export function mockRelated(slug: string): ProductListItem[] {
  const product = productBySlug.get(slug);
  if (!product) return [];
  const sameCategory = products.filter(
    (p) => p.slug !== slug && p.category.slug === product.category.slug,
  );
  const parentId = categoryBySlug.get(product.category.slug)?.parent;
  const siblings = products.filter(
    (p) =>
      p.slug !== slug &&
      !sameCategory.includes(p) &&
      parentId !== null &&
      categoryBySlug.get(p.category.slug)?.parent === parentId,
  );
  return [...sameCategory, ...siblings].slice(0, 8).map(toListItem);
}

export function mockSearch(q: string): ProductListItem[] {
  if (!q.trim()) return [];
  return mockProducts({ search: q, page_size: 6 }).results;
}

export function mockReviews(slug: string, page = 1, pageSize = 5): Paginated<Review> {
  const all = reviewsBySlug.get(slug) ?? [];
  const results = all.slice((page - 1) * pageSize, page * pageSize);
  return {
    count: all.length,
    next: page * pageSize < all.length ? `?page=${page + 1}` : null,
    previous: page > 1 ? `?page=${page - 1}` : null,
    results,
  };
}
