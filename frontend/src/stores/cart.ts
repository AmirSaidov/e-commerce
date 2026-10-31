import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { ProductListItem, ProductVariant, PromoType, ServerCart } from "@/lib/api/types";
import { calcPromoDiscount, toNumber } from "@/lib/utils";

export interface CartLine {
  variantId: number;
  productId: number;
  slug: string;
  name: string;
  variantName: string;
  image: string | null;
  price: number;
  oldPrice: number | null;
  stock: number;
  quantity: number;
}

export interface AppliedPromo {
  code: string;
  type: PromoType;
  value: number;
}

export function lineFromProduct(
  product: Pick<ProductListItem, "id" | "slug" | "name" | "image">,
  variant: ProductVariant,
): Omit<CartLine, "quantity"> {
  return {
    variantId: variant.id,
    productId: product.id,
    slug: product.slug,
    name: product.name,
    variantName: variant.name,
    image: product.image,
    price: toNumber(variant.price),
    oldPrice: variant.old_price ? toNumber(variant.old_price) : null,
    stock: variant.stock,
  };
}

export function linesFromServer(cart: ServerCart): CartLine[] {
  return cart.items.map((item) => ({
    ...lineFromProduct(item.product, item.variant),
    quantity: item.quantity,
  }));
}

export function cartTotals(lines: CartLine[], promo: AppliedPromo | null) {
  const count = lines.reduce((sum, l) => sum + l.quantity, 0);
  const subtotal = lines.reduce((sum, l) => sum + l.price * l.quantity, 0);
  const savings = lines.reduce(
    (sum, l) => sum + (l.oldPrice ? (l.oldPrice - l.price) * l.quantity : 0),
    0,
  );
  const discount = promo ? calcPromoDiscount(subtotal, promo.type, promo.value) : 0;
  return { count, subtotal, savings, discount, total: subtotal - discount };
}

interface CartState {
  lines: CartLine[];
  promo: AppliedPromo | null;
  /** Добавляет товар; возвращает false, если упёрлись в остаток на складе. */
  add: (line: Omit<CartLine, "quantity">, quantity?: number) => boolean;
  setQuantity: (variantId: number, quantity: number) => void;
  remove: (variantId: number) => void;
  clear: () => void;
  replace: (lines: CartLine[]) => void;
  applyPromo: (promo: AppliedPromo) => void;
  removePromo: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      lines: [],
      promo: null,
      add: (line, quantity = 1) => {
        const existing = get().lines.find((l) => l.variantId === line.variantId);
        const wanted = (existing?.quantity ?? 0) + quantity;
        const allowed = Math.min(wanted, line.stock);
        if (allowed <= 0) return false;
        set((state) => ({
          lines: existing
            ? state.lines.map((l) =>
                l.variantId === line.variantId ? { ...l, ...line, quantity: allowed } : l,
              )
            : [...state.lines, { ...line, quantity: allowed }],
        }));
        return allowed === wanted;
      },
      setQuantity: (variantId, quantity) =>
        set((state) => ({
          lines:
            quantity <= 0
              ? state.lines.filter((l) => l.variantId !== variantId)
              : state.lines.map((l) =>
                  l.variantId === variantId ? { ...l, quantity: Math.min(quantity, l.stock) } : l,
                ),
        })),
      remove: (variantId) =>
        set((state) => ({ lines: state.lines.filter((l) => l.variantId !== variantId) })),
      clear: () => set({ lines: [], promo: null }),
      replace: (lines) => set({ lines }),
      applyPromo: (promo) => set({ promo }),
      removePromo: () => set({ promo: null }),
    }),
    {
      name: "voltra-cart",
      storage: createJSONStorage(() => localStorage),
      version: 1,
    },
  ),
);
