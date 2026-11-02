# ТЗ: бэкенд интернет-магазина Voltra (Django + DRF)

> Этот файл — задание для Claude Code. Фронтенд уже готов и лежит в репозитории
> https://github.com/AmirSaidov/e-commerce (папка `frontend/`, отчёт — `docs/frontend-report.md`).
> Твоя задача — написать **только бэкенд**, который полностью совпадает с контрактом, который ждёт фронт.
> **Фронтенд не изменяется ни в каком виде** (см. раздел 0).

## 0. Главное правило: фронтенд НЕ ТРОГАЕМ

**Запрещено** изменять что-либо во фронтенде: ни файлы, ни конфиги, ни `.env`, ни тесты, ни зависимости, ни документацию, ни коммиты/PR/пуши в его репозиторий. Фронтенд — готовый чужой продукт. Всё, что тебе нужно от него, — читать.

- Фронт нельзя «слегка поправить», чтобы он подошёл к бэкенду. **Подстраивается всегда бэкенд.**
- Если контракт кажется неудобным или странным — реализуй его как есть. Если контракт невозможно выполнить — выбери ближайший совместимый вариант на стороне бэка и запиши в `docs/decisions.md`.
- Репозиторий фронта клонируй **вне** папки бэкенда (например, `../frontend-readonly/`), только для чтения. Не делай `git add`, `commit`, `push` в нём. В репозиторий бэкенда фронт не копируй (кроме картинок для seed, см. раздел 7).
- Любые изменения, которые «нужны на фронте», не делай, а перечисли в конце отчёта списком для человека.

## 1. Как работать

1. Склонируй `https://github.com/AmirSaidov/e-commerce` в соседнюю папку (**только чтение**, см. раздел 0). **Источник правды по контракту** — код фронта:
   - `frontend/src/lib/types*` (или аналог) — TypeScript-типы ответов API (`ProductListItem`, `ProductDetail`, `ProductVariant`, `Order`, `ServerCart`, `Review`, `User`, `Address`, `Category`, `Brand`);
   - `frontend/src/lib/api*` — какие URL и параметры фронт реально вызывает;
   - `frontend/src/lib/config.ts` — правила доставки и `SITE_NAME`;
   - `frontend/src/lib/mock/catalog.json` — демо-каталог для seed;
   - `docs/frontend-report.md` — описание контракта.
2. Если этот файл и код фронта расходятся — прав код фронта, бэкенд подстраивается; расхождение выпиши мне в конце отдельным списком.
3. Работай этапами (см. раздел 11). После каждого этапа: тесты зелёные, коммит с понятным сообщением.
4. Не придумывай лишних фич: Docker, Redis, Celery, Google OAuth, сравнение товаров, админ-дашборд — **не нужны**.
5. Если что-то неясно и это влияет на контракт — выбери разумный вариант, запиши его в `docs/decisions.md` и иди дальше.

## 1. Стек

- Python 3.12, Django 5.x, Django REST Framework
- `djangorestframework-simplejwt` (с `token_blacklist`)
- `django-filter`, `django-cors-headers`
- PostgreSQL (локально можно SQLite через `DATABASE_URL`, но full-text поиск и `select_for_update` должны работать на Postgres)
- `dj-database-url`, `python-decouple` или `django-environ` для настроек из `.env`
- `Pillow`, `whitenoise`, `gunicorn`
- `stripe` (Checkout Session + webhook)
- Тесты: `pytest`, `pytest-django`, `factory_boy`
- Линтер: `ruff`
- Без Docker, без Redis/Celery. Письма отправляются синхронно из view.

Структура проекта:

```
backend/
  config/            # settings (base/local/prod или один с env), urls, wsgi
  apps/
    users/           # User, Address, auth-эндпоинты
    catalog/         # Category, Brand, Product, ProductImage, ProductVariant, Review
    wishlist/
    cart/            # Cart, CartItem, PromoCode
    orders/          # Order, OrderItem
    payments/        # Stripe
  manage.py
  requirements.txt
  .env.example
  README.md
```

## 2. Общие правила API

- Префикс `/api/v1/`, **все URL со слешем на конце**.
- Деньги — `DecimalField(max_digits=12, decimal_places=2)`, в JSON приходят **строкой**: `"599990.00"`. Валюта — тенге (KZT).
- Даты — ISO 8601.
- Пагинация — `PageNumberPagination`: `{count, next, previous, results}`, размер по умолчанию 20, `page_size` из query до 100.
- Формат ошибок (свой `EXCEPTION_HANDLER`):
  ```json
  {"detail": "Текст на русском", "code": "machine_code", "fields": {"email": ["..."]}}
  ```
  `detail` фронт показывает пользователю как есть → **тексты только на русском**. Ошибки валидации сериализаторов раскладывай в `fields`. `LANGUAGE_CODE = "ru"`.
- Картинки — **абсолютные URL** (`request.build_absolute_uri` или URL хранилища): фронт и бэк на разных доменах.
- Часовой пояс: `Asia/Almaty`, `USE_TZ = True`.

## 3. Авторизация и CORS

Кастомная модель `User`: вход по `email` (без username), поля `email (unique)`, `first_name`, `last_name`, `phone`, `is_email_verified`. Создай её **до первой миграции**.

| Метод | Путь | Тело | Ответ |
|---|---|---|---|
| POST | `/auth/register/` | `{email, password, first_name, last_name}` | `201` User, отправить письмо со ссылкой подтверждения |
| POST | `/auth/login/` | `{email, password}` | `{access}` + httpOnly-cookie с refresh |
| POST | `/auth/refresh/` | — (refresh берётся из cookie) | `{access}` |
| POST | `/auth/logout/` | — | `204`, cookie удалить, refresh в blacklist |
| POST | `/auth/verify-email/` | `{uid, token}` | `204` |
| POST | `/auth/password-reset/` | `{email}` | `204` **всегда**, даже если email не найден |
| POST | `/auth/password-reset/confirm/` | `{uid, token, password}` | `204` |

Правила:
- Refresh-токен **никогда не возвращается в JSON** — только в cookie: `HttpOnly; Secure; SameSite=None; Path=/api/v1/auth/`. SameSite=None нужен, потому что фронт на Vercel, а бэк на другом домене. В локальной разработке (`DEBUG`) допускается `Secure=False`, `SameSite=Lax`.
- Access-токен фронт держит в памяти и шлёт как `Authorization: Bearer`.
- Включить ротацию refresh + blacklist после ротации.
- `uid`/`token` для подтверждения email и сброса пароля — стандартные `urlsafe_base64_encode(pk)` + `default_token_generator`.
- Ссылки в письмах ведут на фронт: `{FRONTEND_URL}/verify-email?uid=…&token=…` и `{FRONTEND_URL}/password-reset/confirm?uid=…&token=…`.
- Вход без подтверждённого email — `403` с `code: "email_not_verified"` (сделай это переключаемым настройкой `EMAIL_VERIFICATION_REQUIRED`, по умолчанию `True`). Демо-пользователь из seed уже подтверждён.
- CORS: `CORS_ALLOWED_ORIGINS = [FRONTEND_URL]`, `CORS_ALLOW_CREDENTIALS = True`. Фронт шлёт все запросы с `credentials: "include"`.
- Пароль: стандартные `AUTH_PASSWORD_VALIDATORS`, их ошибки должны попадать в `fields.password` (на русском).
- Email-бэкенд: в dev — console, в prod — SMTP из env.

## 4. Каталог

### Модели

- `Category`: `name`, `slug (unique)`, `parent (FK self, null)`, `image`, `order`. Эндпоинт отдаёт дерево.
- `Brand`: `name`, `slug (unique)`, `logo`.
- `Product`: `name`, `slug (unique)`, `description`, `specs (JSONField: «название» → «значение»)`, `category`, `brand`, `rating` (денормализованное среднее, считается при сохранении отзывов), `reviews_count`, `popularity` (число проданных, увеличивается при оплате заказа), `is_active`, `created_at`.
- `ProductImage`: `product`, `image`, `alt`, `order`.
- `ProductVariant`: `product`, `sku (unique)`, `name` / атрибуты (цвет, память — смотри тип `ProductVariant` на фронте), `price`, `old_price (null)`, `stock (PositiveInteger)`.
- `Review`: `product`, `user`, `rating (1–5)`, `text`, `created_at`; уникальность `(product, user)`. `ReviewImage`: `review`, `image` (до 5 на отзыв).

### Эндпоинты

| Метод | Путь | Ответ |
|---|---|---|
| GET | `/categories/` | дерево `Category[]`, у каждой `children` |
| GET | `/brands/` | `Brand[]` без пагинации |
| GET | `/products/` | `Paginated<ProductListItem>` |
| GET | `/products/{slug}/` | `ProductDetail` |
| GET | `/products/{slug}/related/` | `ProductListItem[]`, до 8 (та же категория, исключая сам товар) |
| GET | `/products/search/?q=` | `ProductListItem[]`, до 6 — подсказки в шапке (фронт вызывает с debounce 300 мс) |
| GET | `/products/{slug}/reviews/?page=` | `Paginated<Review>`, по 5 |
| POST | `/products/{slug}/reviews/` | multipart: `rating`, `text`, `images` (до 5 файлов) → `Review` |

> Внимание: маршрут `/products/search/` должен стоять **раньше** `/products/{slug}/`, иначе `search` будет принят за slug.

### Фильтры `/products/`

| Параметр | Пример | Смысл |
|---|---|---|
| `category` | `audio` | slug; **включает все подкатегории** |
| `brand` | `apple,samsung` | несколько slug через запятую (`BaseInFilter`) |
| `price_min`, `price_max` | `10000` | по цене `default_variant` |
| `rating_min` | `4.5` | минимальный рейтинг |
| `in_stock`, `on_sale` | `true` | `on_sale` — у default-варианта есть `old_price` |
| `search` | `galaxy watch` | все слова должны встретиться (Postgres full-text или `icontains` по каждому слову) |
| `ordering` | `-popularity`, `price`, `-price`, `-created_at`, `-rating` | по умолчанию `-popularity` |
| `page`, `page_size` | `2`, `20` | пагинация |

Сортировка по цене — по цене `default_variant` (аннотация через `Subquery`/`Min`). Избегай N+1: `select_related`, `prefetch_related`, аннотации.

### `ProductListItem`

`id, name, slug, image` (URL главного фото), `category` и `brand` — вложенные `{id, name, slug}`, `rating`, `reviews_count`, `price`, `old_price`, `in_stock`, `variants_count`, `default_variant` — **целиком `ProductVariant`**.

`default_variant` — самый дешёвый вариант **в наличии** (`stock > 0`); если таких нет — просто самый дешёвый. `price`/`old_price` — цены этого варианта. `in_stock` — есть ли хоть один вариант с `stock > 0`.

### `ProductDetail`

Всё то же + `description`, `specs`, `images[]` (`{id, image, alt, order}`), `variants[]`.

### `Review`

`{id, author, rating, text, images: string[], created_at}`, где `author` — «Имя Ф.» (имя + первая буква фамилии с точкой).

Ошибки создания отзыва:
- `403`, `code: review_not_purchased` — товар не куплен (нужен заказ в статусе `delivered` с этим товаром);
- `400`, `code: review_exists` — отзыв уже есть.

После создания отзыва пересчитать `Product.rating` и `reviews_count`.

### Необязательно (если останется время)

`GET /products/facets/?category=` → бренды с количеством и диапазон цен.

## 5. Пользователь, адреса, избранное

| Метод | Путь | Заметки |
|---|---|---|
| GET, PATCH | `/users/me/` | PATCH: `first_name`, `last_name`, `phone` |
| POST | `/users/me/password/` | `{old_password, new_password}` → `204`; неверный старый → `fields.old_password` |
| GET, POST | `/users/me/addresses/` | список **без пагинации** |
| PATCH, DELETE | `/users/me/addresses/{id}/` | — |
| GET | `/wishlist/` | `ProductListItem[]` |
| POST | `/wishlist/` | `{product_id}` |
| DELETE | `/wishlist/{product_id}/` | **по id товара**, а не записи; идемпотентно |

Адрес: поля смотри в типе `Address` на фронте (город, улица, дом, квартира, получатель, телефон и т.п.), плюс `is_default`. При `is_default=true` остальные адреса пользователя сбрасываются. Первый адрес пользователя автоматически становится основным. Пользователь видит и меняет только свои адреса.

## 6. Корзина, промокоды, заказы

| Метод | Путь | Тело → ответ |
|---|---|---|
| POST | `/cart/merge/` | `{items: [{variant_id, quantity}]}` → `ServerCart`. Вызывается сразу после входа; при совпадении варианта берётся **максимум** количества |
| PUT | `/cart/` | `{items: [...]}` → `204`, **полностью заменяет** корзину. Фронт шлёт с debounce 800 мс после каждого изменения |
| POST | `/cart/apply-promo/` | `{code, subtotal}` → `{code, type, value, discount}`. **Доступен гостям**, ничего не сохраняет, только проверяет |
| GET | `/orders/?page_size=50` | `Paginated<Order>`, новые сверху |
| GET | `/orders/{number}/` | `Order` |
| POST | `/orders/` | `{items, delivery_method, payment_method, address_id?, promo_code?}` → `Order` |
| POST | `/orders/{number}/cancel/` | → `Order`; только из `created` и `paid`, иначе `400 order_not_cancellable` |
| POST | `/payments/checkout-session/` | `{order_number}` → `{url}` |
| POST | `/payments/webhook/` | Stripe |

`ServerCart`: `{id, items: [{id, variant: ProductVariant, product: {id, name, slug, image}, quantity}]}`.

Промокоды (`PromoCode`: `code`, `type` = `percent`/`fixed`, `value`, `expires_at`, `is_active`, опционально `min_subtotal`, `usage_limit`). Ошибки — `400` с понятным `detail` («Промокод не найден», «Срок действия промокода истёк»). Seed: `WELCOME10` (−10%), `VOLTRA5000` (−5 000 ₸), `SUMMER25` (истёкший).

### `POST /orders/` — самое важное

- Состав заказа приходит в `items`, **а не из серверной корзины** (чтобы не было гонки между синхронизацией корзины и оформлением).
- **Цены берёшь из БД**, не от клиента.
- Остаток списывай в `transaction.atomic()` через `select_for_update()` по вариантам.
- При нехватке остатка — `400` с понятным `detail`, например `«AirPods Pro 2» осталось только 2 шт.` — фронт покажет его в тосте.
- `address_id` обязателен для `delivery_method=courier`, для `pickup` может не прийти. Адрес должен принадлежать пользователю.
- Доставка считается **как на фронте** (`frontend/src/lib/config.ts`): курьер 1 500 ₸, бесплатно от 100 000 ₸ **после скидки**; самовывоз 0 ₸. Значения вынеси в настройки.
- Промокод применяется на бэке повторно (не доверяй клиенту).
- После успешного создания — очистить серверную корзину.
- `Order.address` — **снимок** адреса (без `id` и `is_default`). Номер — строка вида `VT-100245` (последовательный, уникальный).
- `OrderItem` хранит снимок: название товара, название варианта, sku, цену, количество, картинку.
- Статусы: `created → paid → assembling → shipped → delivered`, плюс `cancelled`. При отмене возвращай остатки на склад.
- Заказы видит только владелец.

### Stripe Checkout

- `POST /payments/checkout-session/` создаёт Stripe Checkout Session по позициям заказа (валюта KZT; если Stripe не поддерживает — вынеси валюту в настройку и опиши в `docs/decisions.md`).
- `success_url = {FRONTEND_URL}/checkout/success?order={number}`
- `cancel_url = {FRONTEND_URL}/account/orders/{number}` (там кнопка «Оплатить заказ», она снова вызывает `checkout-session`).
- Статус `paid` ставит **только вебхук** (`checkout.session.completed`), с проверкой подписи `STRIPE_WEBHOOK_SECRET`. Вебхук идемпотентный. При переходе в `paid` увеличь `Product.popularity` на количество.
- Страница успеха фронта опрашивает `GET /orders/{number}/` каждые 2 с около 30 секунд.
- `payment_method` в заказе: смотри допустимые значения в типах фронта (например `card` / `cash`); для оплаты при получении `checkout-session` не нужен.

## 7. Seed и демо-данные

Management-команда `python manage.py seed`:

- читает `frontend/src/lib/mock/catalog.json` (путь через аргумент `--catalog`, по умолчанию — путь к клону репозитория): 13 категорий, 21 бренд, 36 товаров с вариантами, характеристиками и описаниями. **Слаги должны совпадать с файлом**, потому что баннеры на главной ссылаются на них;
- картинки: `frontend/public/mock/products/{slug}-{1..3}.svg` — **скопируй** (не перемещай) в `MEDIA_ROOT` бэкенда и привяжи к `ProductImage`; оригиналы во фронте остаются нетронутыми;
- демо-пользователь `demo@voltra.kz` / `demo12345` (email подтверждён);
- промокоды `WELCOME10`, `VOLTRA5000`, `SUMMER25`;
- команда идемпотентна (повторный запуск не плодит дубли).

## 8. Настройки и `.env.example`

```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://user:pass@localhost:5432/voltra
FRONTEND_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000
EMAIL_URL=consolemail://
DEFAULT_FROM_EMAIL=Voltra <no-reply@voltra.kz>
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
EMAIL_VERIFICATION_REQUIRED=True
FREE_SHIPPING_FROM=100000
COURIER_PRICE=1500
MEDIA_URL=/media/
```

## 9. Деплой

- Локально: `python manage.py runserver` на `localhost:8000`; фронт — `npm run dev` на `localhost:3000` с `NEXT_PUBLIC_API_MODE=api`.
- Прод: бэк на Render или Railway вместе с их PostgreSQL, фронт на Vercel (его деплой — не твоя задача). Подготовь `Procfile`/`render.yaml`, `gunicorn`, `whitenoise`, `collectstatic`, миграции при деплое.
- API должен быть доступен из интернета (серверные компоненты Next ходят в него с сервера Vercel).
- В prod: `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, `SESSION/CSRF cookies secure`.
- Медиа: если Render/Railway без постоянного диска — используй Cloudinary или R2 через `django-storages`. Фронт при этом не меняем: для `next/image` разрешённый хост медиа задаёт владелец фронта сам (`NEXT_PUBLIC_MEDIA_URL`), поэтому в отчёте просто напиши итоговый адрес медиа-хоста, а настройку фронта не трогай.

## 10. Тесты и качество

- `pytest` покрывает минимум: регистрация/логин/refresh/logout (cookie, blacklist), сброс пароля, фильтры и сортировки каталога (включая подкатегории и `brand=a,b`), `default_variant`/`in_stock`/`variants_count`, избранное, слияние корзины (максимум), `apply-promo` (гость, истёкший, неверный), создание заказа (цены из БД, нехватка остатка, доставка и порог бесплатной), отмена, вебхук (подпись, идемпотентность), отзывы (`review_not_purchased`, `review_exists`).
- Проверка формата ошибок: всегда `detail`, `code`, `fields` на русском.
- `ruff check` без ошибок.
- Отдельный тест на отсутствие N+1 для списка товаров (`django_assert_max_num_queries`).
- OpenAPI-схема через `drf-spectacular` на `/api/schema/` (удобно сверять с фронтом).

## 11. Порядок работы (этапы)

1. Каркас проекта, настройки, кастомный `User`, формат ошибок, CORS.
2. Авторизация: все 7 эндпоинтов + письма + cookie + тесты.
3. Каталог: модели, `categories`, `brands`, `products` с фильтрами/сортировкой, `related`, `search`, детальная страница + seed из `catalog.json`.
4. Пользователь: `/users/me/`, смена пароля, адреса, избранное.
5. Корзина и промокоды: `merge`, `PUT /cart/`, `apply-promo`.
6. Заказы: создание, список, детали, отмена, расчёт доставки.
7. Stripe: `checkout-session` + вебхук.
8. Отзывы с фото.
9. README (запуск, переменные, seed, деплой), `docs/decisions.md`, чек-лист ниже.

## 12. Чек-лист приёмки

- [ ] CORS с credentials; cookie refresh с `SameSite=None; Secure` (в prod)
- [ ] Новые эндпоинты есть: `/products/{slug}/related/`, `/auth/password-reset/confirm/`, `/users/me/password/`, `PUT /cart/`
- [ ] `/cart/apply-promo/` принимает `{code, subtotal}` и открыт гостям
- [ ] В списке товаров есть `default_variant`, `variants_count`, `in_stock`; `ordering=-popularity` работает
- [ ] Фильтр `category` включает подкатегории; `brand` принимает список через запятую
- [ ] `POST /orders/` принимает `items`, цены из БД, доставка считается как на фронте
- [ ] Stripe: `success_url`/`cancel_url` на фронт, `paid` — только по вебхуку
- [ ] Ошибки в формате `{detail, code, fields}` на русском
- [ ] `seed` создаёт каталог, демо-пользователя и промокоды
- [ ] Пройден e2e-сценарий покупки с фронтом на `NEXT_PUBLIC_API_MODE=api`

## 13. Что не нужно делать

Любые изменения фронтенда (см. раздел 0), Google OAuth, сравнение товаров, английская версия, админ-дашборд, загрузка аватара, Docker, Redis, Celery.

## 14. Финальный отчёт от тебя

В конце напиши коротко: что сделано, как запустить, какие решения принял сам (`docs/decisions.md`), где контракт фронта и ТЗ разошлись, и отдельным списком — что, по-твоему, стоило бы поменять на фронте (**ты это не делаешь**, решает владелец фронта).
