# Фронтенд готов: отчёт для бэкенда

Амир → Айбек, 31 октября 2026.

Фронтенд по ТЗ готов и работает на демо-данных. К твоему API он переключается одной переменной: `NEXT_PUBLIC_API_MODE=api`. Ниже — что сделано, какой контракт фронт ждёт от DRF и что к нему добавилось по сравнению с таблицей в ТЗ (раздел 5.2).

## 1. Что сделано

| Раздел ТЗ | Страницы | Статус |
| --- | --- | --- |
| 3.1 Авторизация | `/login`, `/register`, `/verify-email`, `/password-reset`, `/password-reset/confirm` | готово, OAuth Google — нет |
| 3.2 Каталог | `/catalog`, `/catalog/[category]`, `/product/[slug]` | готово |
| 3.3 Поиск | подсказки в шапке (debounce 300 мс), `/search?q=` | готово |
| 3.4 Корзина, избранное | `/cart`, мини-корзина, `/account/wishlist` | готово, сравнение товаров — нет |
| 3.5 Заказ и оплата | `/checkout` (адрес → доставка → оплата), `/checkout/success` | готово |
| 3.6 Кабинет | `/account`, `/account/orders`, `/account/orders/[number]`, `/account/addresses` | готово, загрузки аватара нет |
| 3.7 Отзывы | блок на карточке товара, форма с фото до 5 шт. | готово |
| 4 Дизайн | светлая и тёмная темы, mobile-first, 404 и страница ошибки | готово, макетов в Figma нет — дизайн-система сразу в коде |
| 6 SEO | SSR + ISR 60 с, `generateMetadata`, Open Graph, JSON-LD, `sitemap.xml`, `robots.txt` | готово |
| 6 Тесты | 35 юнит-тестов (Vitest), 3 e2e-сценария × desktop/mobile (Playwright) | все зелёные |
| 6 CI | `.github/workflows/frontend.yml`: lint, типы, тесты, сборка, e2e | готово |

Как посмотреть: `cd frontend && cp .env.example .env.local && npm i && npm run dev`, демо-вход `demo@voltra.kz` / `demo12345`.

## 2. Общие правила API

- Префикс `/api/v1/`, все URL со слешем на конце.
- Деньги — `DecimalField`, приходят строкой: `"599990.00"`. Валюта — тенге (KZT).
- Даты — ISO 8601.
- Пагинация — `PageNumberPagination`: `{count, next, previous, results}`, по умолчанию 20, фронт иногда передаёт `page_size` (до 100).
- Ошибки — `{"detail": "...", "code": "...", "fields": {"email": ["..."]}}`. `detail` фронт показывает пользователю как есть, поэтому текст нужен на русском. `fields` фронт раскладывает по полям форм.
- Картинки — абсолютные URL (`request.build_absolute_uri` или URL хранилища): фронт и бэк на разных доменах.

## 3. Авторизация и CORS

| Метод | Путь | Тело | Ответ |
| --- | --- | --- | --- |
| POST | `/auth/register/` | `{email, password, first_name, last_name}` | 201 `User`, письмо со ссылкой |
| POST | `/auth/login/` | `{email, password}` | `{access}` + cookie с refresh |
| POST | `/auth/refresh/` | — (refresh из cookie) | `{access}` |
| POST | `/auth/logout/` | — | 204, cookie удалить, refresh в blacklist |
| POST | `/auth/verify-email/` | `{uid, token}` | 204 |
| POST | `/auth/password-reset/` | `{email}` | 204 всегда, даже если email не найден |
| POST | `/auth/password-reset/confirm/` | `{uid, token, password}` | 204 — **новый эндпоинт** |

- Access-токен фронт держит в памяти и шлёт в `Authorization: Bearer`. Refresh — только в httpOnly-cookie, в JSON его не возвращать.
- Cookie: `HttpOnly; Secure; SameSite=None; Path=/api/v1/auth/`. `SameSite=None` нужен, потому что фронт на Vercel, а бэк на другом домене.
- `CORS_ALLOWED_ORIGINS = [FRONTEND_URL]`, `CORS_ALLOW_CREDENTIALS = True` — фронт шлёт все запросы с `credentials: "include"`.
- Ссылки в письмах ведут на фронт: `{FRONTEND_URL}/verify-email?uid=…&token=…` и `{FRONTEND_URL}/password-reset/confirm?uid=…&token=…`.
- Пароль на фронте проверяется так: минимум 8 символов, не только цифры. Стандартные `AUTH_PASSWORD_VALIDATORS` строже, их ошибки придут в `fields.password` и покажутся под полем.

## 4. Каталог

| Метод | Путь | Ответ |
| --- | --- | --- |
| GET | `/categories/` | дерево: `Category[]`, у каждой `children` |
| GET | `/brands/` | `Brand[]` без пагинации |
| GET | `/products/` | `Paginated<ProductListItem>` |
| GET | `/products/{slug}/` | `ProductDetail` |
| GET | `/products/{slug}/related/` | `ProductListItem[]`, до 8 — **новый эндпоинт** |
| GET | `/products/search/?q=` | `ProductListItem[]`, до 6 — подсказки в шапке |
| GET | `/products/{slug}/reviews/?page=` | `Paginated<Review>`, по 5 |
| POST | `/products/{slug}/reviews/` | multipart: `rating`, `text`, `images` (до 5 файлов) → `Review` |

Параметры `/products/`:

| Параметр | Пример | Смысл |
| --- | --- | --- |
| `category` | `audio` | slug; включает **все подкатегории** |
| `brand` | `apple,samsung` | несколько slug через запятую (`BaseInFilter`) |
| `price_min`, `price_max` | `10000` | по цене `default_variant` |
| `rating_min` | `4.5` | |
| `in_stock`, `on_sale` | `true` | `on_sale` — есть `old_price` |
| `search` | `galaxy watch` | все слова должны встретиться (full-text) |
| `ordering` | `-popularity`, `price`, `-price`, `-created_at`, `-rating` | по умолчанию `-popularity` — **нужно поле или аннотация popularity** (например, число проданных) |
| `page`, `page_size` | | |

Поля товара в списке (`ProductListItem`) — в ТЗ их не было, фронту они нужны:

- `default_variant` — целиком `ProductVariant`: самый дешёвый вариант в наличии, если таких нет — просто самый дешёвый. Нужен для кнопки «В корзину» прямо из каталога.
- `price`, `old_price` — цены этого варианта.
- `variants_count` — если больше 1, в карточке пишется «от» и нет быстрой покупки.
- `in_stock` — есть ли хоть один вариант с `stock > 0`.
- `category` и `brand` — вложенные `{id, name, slug}`, `image` — URL главного фото.

`ProductDetail` = всё то же + `description`, `specs` (объект «название → значение»), `images[]` (`{id, image, alt, order}`), `variants[]`.

`Review`: `{id, author, rating, text, images: string[], created_at}`, где `author` — «Имя Ф.». Ошибки: 403 `review_not_purchased` — товар не куплен (нужен доставленный заказ), 400 `review_exists` — отзыв уже есть.

## 5. Пользователь, адреса, избранное

| Метод | Путь | Заметки |
| --- | --- | --- |
| GET, PATCH | `/users/me/` | PATCH: `first_name`, `last_name`, `phone` |
| POST | `/users/me/password/` | `{old_password, new_password}` → 204 — **новый эндпоинт**; неверный старый пароль → `fields.old_password` |
| GET, POST | `/users/me/addresses/` | список без пагинации |
| PATCH, DELETE | `/users/me/addresses/{id}/` | |
| GET | `/wishlist/` | `ProductListItem[]` |
| POST | `/wishlist/` | `{product_id}` |
| DELETE | `/wishlist/{product_id}/` | по id **товара**, а не записи |

У адреса `is_default`: при `true` остальные адреса пользователя сбрасываются. Первый адрес автоматически становится основным.

## 6. Корзина, промокоды, заказы

| Метод | Путь | Тело → ответ |
| --- | --- | --- |
| POST | `/cart/merge/` | `{items: [{variant_id, quantity}]}` → `ServerCart`. Вызывается сразу после входа; при совпадении варианта берём максимум количества |
| PUT | `/cart/` | `{items: [...]}` → 204, полностью заменяет корзину — **новый эндпоинт**. Фронт шлёт его с debounce 800 мс после каждого изменения |
| POST | `/cart/apply-promo/` | `{code, subtotal}` → `{code, type, value, discount}` — **изменён**: доступен и гостям, ничего не сохраняет, только проверяет |
| GET | `/orders/?page_size=50` | `Paginated<Order>`, новые сверху |
| GET | `/orders/{number}/` | `Order` |
| POST | `/orders/` | `{items, delivery_method, payment_method, address_id?, promo_code?}` → `Order` |
| POST | `/orders/{number}/cancel/` | → `Order`; только из `created` и `paid`, иначе 400 `order_not_cancellable` |
| POST | `/payments/checkout-session/` | `{order_number}` → `{url}` |
| POST | `/payments/webhook/` | Stripe |

`ServerCart`: `{id, items: [{id, variant: ProductVariant, product: {id, name, slug, image}, quantity}]}`.

Важно про `POST /orders/`:

- Состав заказа приходит в `items`, а не из серверной корзины: так нет гонки между debounce-синхронизацией и оформлением. Цены бери из БД, а не от клиента; остаток списывай через `select_for_update`.
- При нехватке остатка — 400 с понятным `detail`, например «„AirPods Pro 2“ осталось только 2 шт.» — фронт покажет его в тосте.
- `address_id` обязателен для `courier`, для `pickup` может не прийти.
- Доставка должна считаться так же, как на фронте (`frontend/src/lib/config.ts`): курьер 1 500 ₸, бесплатно от 100 000 ₸ **после скидки**; самовывоз 0 ₸.
- После успешного заказа можно очистить серверную корзину.
- `Order.address` — снимок адреса без `id` и `is_default`. Номер — строка вида `VT-100245`.
- Статусы: `created → paid → assembling → shipped → delivered`, плюс `cancelled`.

Stripe Checkout:

- `success_url = {FRONTEND_URL}/checkout/success?order={number}`
- `cancel_url = {FRONTEND_URL}/account/orders/{number}` — там есть кнопка «Оплатить заказ», она снова вызывает `checkout-session`.
- Статус `paid` ставит **только вебхук**. Страница успеха опрашивает `GET /orders/{number}/` каждые 2 с примерно 30 секунд.

## 7. Деплой и Docker

- `frontend/Dockerfile` собирает standalone-образ. `NEXT_PUBLIC_*` передаются как `--build-arg`, потому что вшиваются в бандл при сборке. Docker у меня не установлен, поэтому образ я не проверял.
- Сервис для `docker-compose.yml`:

```yaml
frontend:
  build:
    context: ./frontend
    args:
      NEXT_PUBLIC_API_MODE: api
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_SITE_URL: http://localhost:3000
  ports: ["3000:3000"]
  depends_on: [backend]
```

- Серверные компоненты Next ходят в API со своей стороны. Внутри одной compose-сети браузеру нужен `localhost:8000`, а контейнеру — `backend:8000`. Сейчас адрес один на оба случая, поэтому для compose проще открыть бэк наружу на 8000. Если понадобится, разделю на два адреса.
- Если медиа лежат не на хосте API (Cloudinary, R2), задай `NEXT_PUBLIC_MEDIA_URL`: `next/image` пускает только разрешённые хосты.

## 8. Демо-данные

Каталог фронта — `frontend/src/lib/mock/catalog.json`: 13 категорий, 21 бренд, 36 товаров с вариантами, характеристиками и описаниями. Если команда `seed` будет брать данные оттуда, слаги совпадут с баннерами на главной. Картинки к ним — в `frontend/public/mock/products/{slug}-{1..3}.svg`. Демо-аккаунт: `demo@voltra.kz` / `demo12345`. Промокоды: `WELCOME10` (−10%), `VOLTRA5000` (−5 000 ₸), `SUMMER25` (истёкший).

## 9. Не сделано и открытые вопросы

- На фронте нет: входа через Google, сравнения товаров, английской версии, дашборда для админа, загрузки аватара. Всё это было «дополнительно» или идёт следующим шагом.
- Lighthouse пока не мерил. Сделаю на задеплоенной версии, на dev-сервере цифры нерелевантны.
- Фильтр брендов показывает все бренды, а не только те, что есть в текущей категории. Если отдашь фасеты (`/products/facets/?category=` → бренды с количеством и диапазон цен), фильтр станет точнее.
- Название магазина «Voltra» — временное, меняется в одном месте: `SITE_NAME` в `frontend/src/lib/config.ts`.

## 10. Чек-лист для интеграции

- [ ] CORS с credentials и cookie refresh с `SameSite=None; Secure`
- [ ] Новые эндпоинты: `/products/{slug}/related/`, `/auth/password-reset/confirm/`, `/users/me/password/`, `PUT /cart/`
- [ ] `/cart/apply-promo/` принимает `{code, subtotal}` и открыт гостям
- [ ] В списке товаров есть `default_variant`, `variants_count`, `in_stock`, а `ordering=-popularity` работает
- [ ] Фильтр `category` включает подкатегории, `brand` принимает список через запятую
- [ ] `POST /orders/` принимает `items`, доставка считается как на фронте
- [ ] Stripe: `success_url` и `cancel_url` на фронт, `paid` только по вебхуку
- [ ] Пройти e2e-сценарий покупки на `NEXT_PUBLIC_API_MODE=api`
