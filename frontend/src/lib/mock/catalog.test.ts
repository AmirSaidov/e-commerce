import { describe, expect, it } from "vitest";
import { mockCategories, mockProduct, mockProducts, mockRelated } from "./catalog";

// Эти тесты фиксируют поведение, которого фронт ждёт от GET /api/v1/products/.

describe("mockProducts", () => {
  it("фильтр по родительской категории включает товары подкатегорий", () => {
    const { results } = mockProducts({ category: "audio", page_size: 100 });
    const categories = new Set(results.map((p) => p.category.slug));
    expect(categories).toEqual(new Set(["headphones", "speakers"]));
  });

  it("фильтрует по нескольким брендам и сортирует по цене", () => {
    const { results } = mockProducts({ brand: ["sony", "jbl"], ordering: "price", page_size: 100 });
    expect(results.every((p) => ["sony", "jbl"].includes(p.brand.slug))).toBe(true);
    const prices = results.map((p) => Number(p.price));
    expect(prices).toEqual([...prices].sort((a, b) => a - b));
  });

  it("on_sale возвращает только товары со старой ценой", () => {
    const { results } = mockProducts({ on_sale: true, page_size: 100 });
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((p) => p.old_price !== null)).toBe(true);
  });

  it("поиск ищет по всем словам запроса", () => {
    const { results } = mockProducts({ search: "galaxy watch" });
    expect(results.map((p) => p.slug)).toEqual(["samsung-galaxy-watch-7"]);
  });

  it("пагинирует как PageNumberPagination", () => {
    const first = mockProducts({ page_size: 20 });
    const second = mockProducts({ page_size: 20, page: 2 });
    expect(first.count).toBe(36);
    expect(first.results).toHaveLength(20);
    expect(first.next).toBe("?page=2");
    expect(second.results).toHaveLength(16);
    expect(second.next).toBeNull();
  });
});

describe("mockProduct", () => {
  it("default_variant — самый дешёвый вариант в наличии", () => {
    const ps5 = mockProduct("sony-playstation-5-slim")!;
    expect(ps5.default_variant.name).toBe("Digital Edition");
    expect(ps5.price).toBe(ps5.default_variant.price);
  });

  it("товар без остатков помечен как отсутствующий", () => {
    expect(mockProduct("huawei-matebook-14")!.in_stock).toBe(false);
  });
});

describe("категории и похожие товары", () => {
  it("дерево категорий содержит только корни с вложенными детьми", () => {
    const tree = mockCategories();
    expect(tree.every((c) => c.parent === null)).toBe(true);
    expect(tree.find((c) => c.slug === "computers")!.children.map((c) => c.slug)).toEqual([
      "laptops",
      "tablets",
      "monitors",
    ]);
  });

  it("похожие товары не включают сам товар", () => {
    const related = mockRelated("sony-wh-1000xm5");
    expect(related.length).toBeGreaterThan(0);
    expect(related.some((p) => p.slug === "sony-wh-1000xm5")).toBe(false);
  });
});
