# Voltra API

Бэкенд интернет-магазина электроники **Voltra** на Django 5.2 и Django REST Framework.
Он отдаёт API для готового фронтенда на Next.js — [AmirSaidov/e-commerce](https://github.com/AmirSaidov/e-commerce).
Контракт API задаёт фронт: типы `frontend/src/lib/api/types.ts` и мок-бэкенд `frontend/src/lib/mock/`.
Бэкенд подстраивается под них, фронт не меняется.

Что умеет:
- регистрация с подтверждением email, вход по JWT (refresh-токен в httpOnly-cookie), сброс пароля;
- каталог: дерево категорий, бренды, фильтры, сортировка, поиск, похожие товары;
- отзывы с фото;
- профиль, адреса, избранное;
- серверная корзина и промокоды;
- заказы с расчётом доставки;
- оплата через Stripe Checkout (необязательно).

- Стек: Python 3.12, Django 5.2, DRF, SimpleJWT, django-filter, drf-spectacular; PostgreSQL в проде, SQLite локально.
- Документация API: **`/api/docs/`** (Swagger UI), схема OpenAPI: `/api/schema/`.
- Решения и расхождения с ТЗ: [docs/decisions.md](docs/decisions.md). ТЗ: [docs/tz.md](docs/tz.md).

## Локальный запуск (Windows, SQLite)

Нужны Python 3.12 и git. Команды для PowerShell из корня репозитория:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.example .env
# в .env впишите SECRET_KEY — любую длинную случайную строку:
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50))"

.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed
.\.venv\Scripts\python.exe manage.py runserver
```

API: http://localhost:8000/api/v1/ · документация: http://localhost:8000/api/docs/ ·
админка: http://localhost:8000/admin/ (создать администратора — `manage.py createsuperuser`).

В режиме разработки письма (подтверждение email, сброс пароля) печатаются в консоль `runserver`.
Ссылку из письма можно открыть на фронте.

### Демо-данные: `seed`

`python manage.py seed` берёт каталог фронта — `frontend/src/lib/mock/catalog.json` и картинки
`frontend/public/mock/` — из клона фронта рядом с папкой бэкенда (`../frontend-readonly`).
Если клона нет, используйте `--github`: данные скачаются из репозитория фронта.

```powershell
git clone https://github.com/AmirSaidov/e-commerce ..\frontend-readonly   # один раз, только для чтения
.\.venv\Scripts\python.exe manage.py seed                    # из клона
.\.venv\Scripts\python.exe manage.py seed --github           # из GitHub, без клона
.\.venv\Scripts\python.exe manage.py seed --catalog C:\path\catalog.json --images C:\path\public\mock
```

Создаётся:
- 13 категорий, 21 бренд, 36 товаров (53 варианта, 108 фото);
- 190 отзывов: рейтинги совпадают с демо-режимом фронта;
- промокоды `WELCOME10` (−10 %), `VOLTRA5000` (−5 000 ₸), `SUMMER25` (истёкший);
- **демо-аккаунт `demo@voltra.kz` / `demo12345`** (email подтверждён).

Команда идемпотентна: повторный запуск не создаёт дублей. Он возвращает каталог, остатки и демо-аккаунт к исходным значениям.

### Тесты и линтер

```powershell
.\.venv\Scripts\python.exe -m pytest        # 317 тестов; 7 — только на PostgreSQL (на SQLite пропускаются)
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
```

Тесты на PostgreSQL: задайте `DATABASE_URL=postgres://…` (пользователю нужно право создавать базы) и
запустите `pytest`. Что именно проверяется только там — в конце [docs/decisions.md](docs/decisions.md).

## Подключение фронтенда

Во фронте (в его `.env.local` или в переменных Vercel) задаются:

```
NEXT_PUBLIC_API_MODE=api
NEXT_PUBLIC_API_URL=http://localhost:8000          # прод: https://<ваш-сервис>.onrender.com
NEXT_PUBLIC_MEDIA_URL=https://pub-xxxx.r2.dev       # только если медиа на своём домене (см. ниже)
```

На бэке адрес фронта указывается в `FRONTEND_URL` и `CORS_ALLOWED_ORIGINS`. По `FRONTEND_URL` строятся
ссылки в письмах и адреса возврата из Stripe.

- Фронт шлёт запросы с `credentials: "include"`, refresh-токен лежит в cookie `refresh_token` (`Path=/api/v1/auth/`).
  Локально (localhost:3000 ↔ localhost:8000) cookie `SameSite=Lax`. В проде фронт и API на разных доменах,
  поэтому `SameSite=None; Secure`, и нужен HTTPS.
- Картинки приходят абсолютными URL. `next.config` фронта уже разрешает `localhost:8000`, `*.r2.dev` и
  `res.cloudinary.com`. Для другого домена медиа нужен `NEXT_PUBLIC_MEDIA_URL`.

## Переменные окружения

Полный список с комментариями — в [.env.example](.env.example). Основные:

| Переменная | Локально | Прод | Зачем |
|---|---|---|---|
| `SECRET_KEY` | любая строка | генерирует Render | подпись JWT и токенов в письмах |
| `DEBUG` | `True` | `False` | при `False` — строгие cookie, лимиты, статика через whitenoise |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | адрес Render добавляется сам | домены API |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | из базы Render | БД |
| `FRONTEND_URL` | `http://localhost:3000` | `https://voltra.vercel.app` | ссылки в письмах и Stripe |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | адрес фронта | CORS с credentials |
| `CSRF_TRUSTED_ORIGINS` | — | по умолчанию CORS + домен Render | админка за HTTPS |
| `EMAIL_URL` | `consolemail://` | `smtp+tls://user:pass@host:587` | отправка писем |
| `EMAIL_VERIFICATION_REQUIRED` | `True` | `True` | вход только с подтверждённым email |
| `FREE_SHIPPING_FROM`, `COURIER_PRICE` | `100000`, `1500` | так же | доставка, как на фронте |
| `MEDIA_STORAGE` | `local` | `s3` | где хранить фото |
| `S3_*` | — | ключи R2 | см. «Медиа» |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | пусто | по желанию | онлайн-оплата |

## Онлайн-оплата (Stripe) — необязательна

**Без ключей Stripe приложение работает целиком.** Не работает только оплата картой онлайн:
- заказ с `payment_method=card` получает `400 payment_method_unavailable` «Оплата картой онлайн сейчас
  недоступна. Выберите оплату при получении.»;
- заказы «при получении» оформляются как обычно.

Онлайн-оплата включается, когда заданы оба ключа:

1. `STRIPE_SECRET_KEY` — ключ из Dashboard → Developers → API keys (`sk_test_…` для тестов).
2. `STRIPE_WEBHOOK_SECRET` — секрет endpoint вебхука `https://<api>/api/v1/payments/webhook/`
   с событиями `checkout.session.completed` и `checkout.session.async_payment_succeeded`.
   Локально: `stripe listen --forward-to localhost:8000/api/v1/payments/webhook/` — команда напечатает `whsec_…`.

Статус «оплачен» ставит только вебхук. Валюта — KZT (суммы в тиынах), переопределяется через `STRIPE_CURRENCY`.
Что проверить на настоящем Stripe, перечислено в конце [docs/decisions.md](docs/decisions.md).

## Деплой на Render

В репозитории есть [render.yaml](render.yaml) (Blueprint): веб-сервис и PostgreSQL на бесплатном плане.

1. Render → **New → Blueprint** → выберите этот репозиторий.
2. Render спросит значения переменных с `sync: false`: `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, `EMAIL_URL`,
   ключи R2 (`S3_*`) и, по желанию, Stripe. `SECRET_KEY` и `DATABASE_URL` Render заполнит сам.
3. Что происходит при деплое:
   - **сборка:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`;
   - **старт:** `migrate` → `seed --github --if-empty` → `gunicorn`;
   - **health-check:** `/api/v1/health/`.
4. **Seed одной командой.** При первом деплое каталог, промокоды и демо-аккаунт создаются сами:
   `seed --github --if-empty` скачивает данные фронта из GitHub примерно за 10 с, а при следующих
   стартах ничего не делает. Заполнить или сбросить данные вручную можно из Shell сервиса или
   локально с прод-переменными:
   ```bash
   python manage.py seed --github
   ```
5. Во фронте на Vercel задайте `NEXT_PUBLIC_API_URL=https://<сервис>.onrender.com`.

Railway — то же самое: в Start Command поставьте ту же цепочку `migrate && seed --github --if-empty && gunicorn …`.
Переменные те же. `RENDER_EXTERNAL_HOSTNAME` там нет, поэтому домен нужно указать в `ALLOWED_HOSTS` вручную.

### Медиа без постоянного диска

У бесплатного Render нет постоянного диска: всё, что записано в `media/`, пропадает при перезапуске.
Поэтому в проде фото (товаров, категорий, отзывов) хранятся в **Cloudflare R2**: это S3-совместимое
хранилище, 10 ГБ бесплатно, домен `*.r2.dev` уже разрешён в `next.config` фронта.

1. Cloudflare → R2 → создать бакет, например `voltra-media`. В настройках бакета включите **Public access → r2.dev subdomain**.
2. R2 → Manage API tokens → токен с правом *Object Read & Write* на этот бакет.
3. Переменные сервиса:
   ```
   MEDIA_STORAGE=s3
   S3_BUCKET=voltra-media
   S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
   S3_ACCESS_KEY_ID=…
   S3_SECRET_ACCESS_KEY=…
   S3_PUBLIC_DOMAIN=pub-xxxxxxxx.r2.dev
   ```
4. API будет отдавать картинки как `https://pub-xxxxxxxx.r2.dev/products/…svg`. `seed` загрузит фото каталога в R2.

Без R2 (`MEDIA_STORAGE=local`) Django сам отдаёт `/media/`, но фото пропадут при первом же перезапуске
сервиса. Этот вариант годится только для проверки. Подробнее — в [docs/decisions.md](docs/decisions.md), раздел «Этап 9».

## Эндпоинты

Префикс `/api/v1/`, все URL со слешем на конце. Ошибки всегда в формате
`{"detail": "текст на русском", "code": "machine_code", "fields": {"поле": ["…"]}}`.
Подробные схемы запросов и ответов — в **`/api/docs/`**.

| Метод | Путь | Доступ | Что делает |
|---|---|---|---|
| POST | `/auth/register/` | все | регистрация, письмо с подтверждением → `201 User` |
| POST | `/auth/login/` | все | `{access}` + refresh в httpOnly-cookie |
| POST | `/auth/refresh/` | cookie | новый `{access}`, refresh ротируется |
| POST | `/auth/logout/` | cookie | `204`, refresh в blacklist, cookie удаляется |
| POST | `/auth/verify-email/` | все | `{uid, token}` → `204` |
| POST | `/auth/password-reset/` | все | `{email}` → `204` всегда |
| POST | `/auth/password-reset/confirm/` | все | `{uid, token, password}` → `204` |
| GET | `/categories/` | все | дерево категорий |
| GET | `/brands/` | все | бренды без пагинации |
| GET | `/products/` | все | список: `category`, `brand=a,b`, `price_min/max`, `rating_min`, `in_stock`, `on_sale`, `search`, `ordering`, `page`, `page_size` |
| GET | `/products/search/?q=` | все | до 6 подсказок |
| GET | `/products/{slug}/` | все | карточка товара |
| GET | `/products/{slug}/related/` | все | до 8 похожих |
| GET | `/products/{slug}/reviews/` | все | отзывы, по 5 |
| POST | `/products/{slug}/reviews/` | JWT | multipart `rating`, `text`, `images` (до 5) |
| GET, PATCH | `/users/me/` | JWT | профиль |
| POST | `/users/me/password/` | JWT | смена пароля |
| GET, POST | `/users/me/addresses/` | JWT | адреса |
| PATCH, DELETE | `/users/me/addresses/{id}/` | JWT | изменить или удалить адрес |
| GET, POST | `/wishlist/` | JWT | избранное, добавить `{product_id}` |
| DELETE | `/wishlist/{product_id}/` | JWT | убрать из избранного |
| POST | `/cart/merge/` | JWT | слить гостевую корзину → `ServerCart` |
| PUT | `/cart/` | JWT | заменить корзину |
| POST | `/cart/apply-promo/` | все | проверить промокод `{code, subtotal}` |
| GET, POST | `/orders/` | JWT | список (новые сверху), создать заказ |
| GET | `/orders/{number}/` | JWT | заказ |
| POST | `/orders/{number}/cancel/` | JWT | отменить (из `created` и `paid`) |
| POST | `/payments/checkout-session/` | JWT | `{order_number}` → `{url}` Stripe |
| POST | `/payments/webhook/` | подпись Stripe | вебхук оплаты |
| GET | `/health/` | все | `{"status": "ok"}` для health-check |

## Структура

```
config/            настройки (один модуль, всё из .env), urls, wsgi
apps/core/         формат ошибок, пагинация, медиа-URL, лимиты частоты, служебные view
apps/users/        User (вход по email), адреса, авторизация и профиль
apps/catalog/      категории, бренды, товары, варианты, отзывы, команда seed
apps/wishlist/     избранное
apps/cart/         корзина, промокоды
apps/orders/       заказы
apps/payments/     Stripe Checkout и вебхук
docs/              ТЗ и принятые решения
```
