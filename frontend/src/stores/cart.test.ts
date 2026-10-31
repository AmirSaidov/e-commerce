import { beforeEach, describe, expect, it } from "vitest";
import { type CartLine, cartTotals, useCartStore } from "./cart";

const phone: Omit<CartLine, "quantity"> = {
  variantId: 101,
  productId: 1,
  slug: "phone",
  name: "Телефон",
  variantName: "128 ГБ",
  image: null,
  price: 100_000,
  oldPrice: 120_000,
  stock: 3,
};
const case_: Omit<CartLine, "quantity"> = {
  ...phone,
  variantId: 202,
  productId: 2,
  slug: "case",
  price: 5_000,
  oldPrice: null,
  stock: 10,
};

describe("cart store", () => {
  beforeEach(() => useCartStore.getState().clear());

  it("добавляет товар и увеличивает количество при повторном добавлении", () => {
    const { add } = useCartStore.getState();
    expect(add(phone)).toBe(true);
    expect(add(phone)).toBe(true);
    expect(useCartStore.getState().lines).toHaveLength(1);
    expect(useCartStore.getState().lines[0].quantity).toBe(2);
  });

  it("не даёт положить больше, чем есть на складе", () => {
    const { add } = useCartStore.getState();
    expect(add(phone, 5)).toBe(false);
    expect(useCartStore.getState().lines[0].quantity).toBe(3);
  });

  it("не добавляет товар, которого нет в наличии", () => {
    expect(useCartStore.getState().add({ ...phone, stock: 0 })).toBe(false);
    expect(useCartStore.getState().lines).toHaveLength(0);
  });

  it("удаляет позицию, если количество стало нулём", () => {
    const { add, setQuantity } = useCartStore.getState();
    add(phone);
    setQuantity(phone.variantId, 0);
    expect(useCartStore.getState().lines).toHaveLength(0);
  });

  it("ограничивает setQuantity остатком", () => {
    const { add, setQuantity } = useCartStore.getState();
    add(phone);
    setQuantity(phone.variantId, 99);
    expect(useCartStore.getState().lines[0].quantity).toBe(3);
  });

  it("clear сбрасывает и товары, и промокод", () => {
    const { add, applyPromo, clear } = useCartStore.getState();
    add(phone);
    applyPromo({ code: "WELCOME10", type: "percent", value: 10 });
    clear();
    expect(useCartStore.getState()).toMatchObject({ lines: [], promo: null });
  });
});

describe("cartTotals", () => {
  const lines: CartLine[] = [
    { ...phone, quantity: 2 },
    { ...case_, quantity: 1 },
  ];

  it("считает количество, сумму и экономию по старым ценам", () => {
    expect(cartTotals(lines, null)).toEqual({
      count: 3,
      subtotal: 205_000,
      savings: 40_000,
      discount: 0,
      total: 205_000,
    });
  });

  it("применяет процентный промокод", () => {
    const totals = cartTotals(lines, { code: "WELCOME10", type: "percent", value: 10 });
    expect(totals.discount).toBe(20_500);
    expect(totals.total).toBe(184_500);
  });

  it("фиксированная скидка не больше суммы корзины", () => {
    const totals = cartTotals([{ ...case_, quantity: 1 }], {
      code: "BIG",
      type: "fixed",
      value: 10_000,
    });
    expect(totals.discount).toBe(5_000);
    expect(totals.total).toBe(0);
  });
});
