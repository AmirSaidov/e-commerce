# Voltra — фронтенд

Next.js 15 (App Router) + TypeScript + Tailwind CSS 4. Интернет-магазин электроники: каталог с фильтрами, поиск, корзина, оформление заказа с оплатой Stripe, личный кабинет.

## Быстрый старт

```bash
cd frontend
cp .env.example .env.local   # по умолчанию NEXT_PUBLIC_API_MODE=mock
npm install
npm run dev                  # http://localhost:3000
```

В режиме `mock` бэкенд не нужен: каталог берётся из `src/lib/mock/catalog.json`, а пользователи, заказы и адреса хранятся в `localStorage`.

Демо-аккаунт: `demo@voltra.kz` / `demo12345`. На странице входа есть кнопка «Подставить».

Демо-промокоды: `WELCOME10` (−10%), `VOLTRA5000` (−5 000 ₸), `SUMMER25` (истёк, для проверки ошибки).

## Подключение к Django

```env
NEXT_PUBLIC_API_MODE=api
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Все запросы идут через `src/lib/api/index.ts` на `${NEXT_PUBLIC_API_URL}/api/v1/...`. Контракт описан в `src/lib/api/types.ts` и в `docs/frontend-report.md` в корне репозитория.

## Скрипты

| Команда | Что делает |
| --- | --- |
| `npm run dev` | dev-сервер с Turbopack |
| `npm run build` / `npm start` | прод-сборка и запуск |
| `npm run lint` / `npm run typecheck` | ESLint и TypeScript |
| `npm test` | юнит-тесты (Vitest) |
| `npm run test:e2e` | e2e-тесты (Playwright), нужен `npm run build` перед запуском |
| `npm run mock:images` | перегенерировать демо-картинки в `public/mock/` |

Локально e2e можно гонять в установленном Edge или Chrome, без скачивания браузеров: `PW_CHANNEL=msedge npm run test:e2e`.

## Структура

```
src/
  app/                 страницы (App Router)
  components/
    ui/                базовые компоненты: кнопки, поля, шторка, диалог
    layout/            шапка, подвал, поиск, мини-корзина
    product/ catalog/ cart/ account/ auth/ home/
  lib/
    api/               HTTP-клиент, типы API, единая точка доступа `api`
    mock/              демо-данные и имитация бэкенда
    config.ts          режим API, адреса, доставка
  stores/              Zustand: корзина, авторизация, избранное
e2e/                   Playwright-сценарии
```

## Ключевые решения

- **Каталог и карточки товаров рендерятся на сервере** (Server Components + ISR, 60 с). Фильтры хранятся в URL, поэтому любую выдачу можно отправить ссылкой, и она индексируется.
- **Корзина живёт в Zustand + localStorage.** После входа гостевая корзина сливается с серверной (`POST /cart/merge/`), дальше изменения дублируются на сервер (`PUT /cart/`).
- **JWT:** access-токен хранится только в памяти, refresh — в httpOnly-cookie от бэкенда. На 401 клиент один раз обновляет токен и повторяет запрос.
- **Оплата:** статус заказа меняет вебхук Stripe, а не редирект. Страница успеха опрашивает заказ, пока тот не станет `paid`.
- **SEO:** `generateMetadata` с Open Graph, JSON-LD (Product, BreadcrumbList), `sitemap.xml`, `robots.txt`, корректный 404.
- **Доступность:** навигация с клавиатуры, видимый фокус, aria-атрибуты у поиска-комбобокса, галереи и слайдера, учёт `prefers-reduced-motion`.

## Деплой

Vercel: импортировать репозиторий, Root Directory — `frontend`, в Environment Variables задать `NEXT_PUBLIC_API_MODE`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL` (и `NEXT_PUBLIC_MEDIA_URL`, если медиа не на хосте API). Пока бэкенда нет, достаточно `NEXT_PUBLIC_API_MODE=mock` — сайт работает на демо-данных.
