import { expect, test } from "@playwright/test";

// Главный сценарий из ТЗ: найти товар → купить → увидеть заказ в кабинете.
test("покупка: поиск → корзина → промокод → вход → оформление → заказ в кабинете", async ({
  page,
}) => {
  await page.goto("/");

  const search = page.getByRole("combobox", { name: "Поиск товаров" }).locator("visible=true");
  await search.fill("airpods");
  await page.getByRole("option", { name: /Apple AirPods Pro 2/ }).click();
  await expect(page).toHaveURL(/\/product\/apple-airpods-pro-2$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Apple AirPods Pro 2");

  await page.getByRole("button", { name: "В корзину", exact: true }).click();
  await expect(page.getByText("Добавлено в корзину")).toBeVisible();

  await page.goto("/cart");
  await expect(page.getByRole("link", { name: "Apple AirPods Pro 2" })).toBeVisible();
  await page.getByLabel("Промокод").fill("SUMMER25");
  await page.getByRole("button", { name: "Применить" }).click();
  await expect(page.getByText("Срок действия промокода истёк.")).toBeVisible();
  await page.getByLabel("Промокод").fill("WELCOME10");
  await page.getByRole("button", { name: "Применить" }).click();
  await expect(page.getByText("Промокод WELCOME10")).toBeVisible();
  // 129 990 − 10% = 116 991
  await expect(page.getByText(/116\s991\s₸/)).toBeVisible();

  await page.getByRole("link", { name: "Перейти к оформлению" }).click();
  await expect(page).toHaveURL(/\/login\?next=%2Fcheckout/);
  await page.getByRole("button", { name: "Подставить" }).click();
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).toHaveURL(/\/checkout$/);

  await page.getByRole("button", { name: "Продолжить" }).click();
  await page.getByText("Самовывоз", { exact: true }).click();
  await page.getByRole("button", { name: "Продолжить" }).click();
  await page.getByText("Картой онлайн").click();
  await page.getByRole("button", { name: "Перейти к оплате" }).click();

  await expect(page).toHaveURL(/\/checkout\/success\?order=VT-\d+/);
  await expect(page.getByRole("heading", { name: "Спасибо, заказ оформлен!" })).toBeVisible();
  const number = new URL(page.url()).searchParams.get("order")!;

  // корзина очистилась
  const cartButton = page.getByRole("button", { name: /^Корзина, товаров: \d+$/ });
  await expect(cartButton).toHaveAccessibleName("Корзина, товаров: 0");

  await page.getByRole("link", { name: "Открыть заказ" }).click();
  await expect(page.getByRole("heading", { name: `Заказ ${number}` })).toBeVisible();
  await expect(page.getByText("Оплачен", { exact: true }).first()).toBeVisible();
});

test("каталог: фильтры живут в URL и сужают выдачу", async ({ page, isMobile }) => {
  await page.goto("/catalog/audio");
  await expect(page.getByText("8 товаров", { exact: true })).toBeVisible();

  if (isMobile) await page.getByRole("button", { name: "Фильтры" }).click();
  await page.getByLabel("Со скидкой").locator("visible=true").check();
  await expect(page).toHaveURL(/on_sale=1/);
  await expect(page.getByText("3 товара", { exact: true })).toBeVisible();
  if (isMobile) await page.getByRole("button", { name: /^Показать/ }).click();

  await page.getByLabel("Сортировка").selectOption("price");
  await expect(page).toHaveURL(/ordering=price/);
  const firstCard = page.getByRole("article").first();
  await expect(firstCard).toContainText("JBL Tune 770NC");

  await page.getByRole("button", { name: "Убрать фильтр: Со скидкой" }).click();
  await expect(page).not.toHaveURL(/on_sale/);
  await expect(page.getByText("8 товаров", { exact: true })).toBeVisible();
});

test("приватные страницы и 404", async ({ page }) => {
  await page.goto("/account/orders");
  await expect(page).toHaveURL(/\/login\?next=%2Faccount%2Forders/);

  const response = await page.goto("/product/does-not-exist");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "Такой страницы нет" })).toBeVisible();
});
