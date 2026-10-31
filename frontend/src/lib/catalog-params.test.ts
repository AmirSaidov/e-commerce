import { describe, expect, it } from "vitest";
import { parseProductQuery, toSearchString } from "./catalog-params";

describe("parseProductQuery", () => {
  it("переводит параметры URL в запрос к API", () => {
    expect(
      parseProductQuery({
        brand: "apple,samsung",
        price_min: "1000",
        price_max: "50000",
        rating_min: "4.5",
        in_stock: "1",
        on_sale: "1",
        ordering: "-price",
        q: "  iphone ",
        page: "2",
      }),
    ).toEqual({
      brand: ["apple", "samsung"],
      price_min: 1000,
      price_max: 50000,
      rating_min: 4.5,
      in_stock: true,
      on_sale: true,
      ordering: "-price",
      search: "iphone",
      page: 2,
    });
  });

  it("отбрасывает мусор: неизвестную сортировку, отрицательные числа, кривую страницу", () => {
    const query = parseProductQuery({ ordering: "DROP TABLE", price_min: "-5", page: "abc" });
    expect(query.ordering).toBeUndefined();
    expect(query.price_min).toBeUndefined();
    expect(query.page).toBe(1);
  });
});

describe("toSearchString", () => {
  it("сохраняет текущие параметры и применяет изменения", () => {
    expect(toSearchString({ brand: "apple", page: "3" }, { page: null, ordering: "price" })).toBe(
      "?brand=apple&ordering=price",
    );
  });

  it("возвращает пустую строку без параметров", () => {
    expect(toSearchString({ page: "2" }, { page: null })).toBe("");
  });
});
