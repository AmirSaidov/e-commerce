import { describe, expect, it } from "vitest";
import { calcDeliveryPrice, discountPercent, formatPrice, pluralize, toNumber } from "./utils";

const normalize = (s: string) => s.replace(/\s/g, " ");

describe("formatPrice", () => {
  it("форматирует строку DecimalField из DRF в тенге без копеек", () => {
    expect(normalize(formatPrice("599990.00"))).toBe("599 990 ₸");
  });

  it("принимает число", () => {
    expect(normalize(formatPrice(1500))).toBe("1 500 ₸");
  });
});

describe("toNumber", () => {
  it("превращает Money в число и null в 0", () => {
    expect(toNumber("12.50")).toBe(12.5);
    expect(toNumber(null)).toBe(0);
  });
});

describe("discountPercent", () => {
  it("считает процент скидки", () => {
    expect(discountPercent("180000.00", "200000.00")).toBe(10);
  });

  it("возвращает null без старой цены или если она не выше текущей", () => {
    expect(discountPercent("100.00", null)).toBeNull();
    expect(discountPercent("100.00", "90.00")).toBeNull();
  });
});

describe("calcDeliveryPrice", () => {
  it("курьер платный до порога и бесплатный от 100 000 ₸", () => {
    expect(calcDeliveryPrice("courier", 99_999)).toBe(1500);
    expect(calcDeliveryPrice("courier", 100_000)).toBe(0);
  });

  it("самовывоз всегда бесплатный", () => {
    expect(calcDeliveryPrice("pickup", 10)).toBe(0);
  });
});

describe("pluralize", () => {
  const forms: [string, string, string] = ["товар", "товара", "товаров"];
  it.each([
    [1, "товар"],
    [2, "товара"],
    [5, "товаров"],
    [11, "товаров"],
    [21, "товар"],
    [104, "товара"],
  ])("%i → %s", (n, expected) => {
    expect(pluralize(n, forms)).toBe(expected);
  });
});
