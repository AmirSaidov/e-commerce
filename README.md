# Voltra — интернет-магазин электроники

Портфолио-проект: полноценный e-commerce от каталога до оплаты.

| Часть | Стек | Кто |
| --- | --- | --- |
| [`frontend/`](frontend/) | Next.js 15, TypeScript, Tailwind CSS 4, TanStack Query, Zustand, React Hook Form + Zod | Амир |
| `backend/` | Django 5, Django REST Framework, PostgreSQL, Stripe | Айбек |

## Статус

- [x] Фронтенд: все страницы из ТЗ, работает на демо-данных (`NEXT_PUBLIC_API_MODE=mock`)
- [ ] Бэкенд: API по контракту из [`docs/frontend-report.md`](docs/frontend-report.md)
- [ ] Деплой (фронт — Vercel, бэк — Render/Railway) и демо-ссылка

## Запуск фронтенда

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Откройте http://localhost:3000. Демо-аккаунт: `demo@voltra.kz` / `demo12345`.

Подробности — в [`frontend/README.md`](frontend/README.md).

## Ветки и коммиты

`main` — прод, `develop` — разработка, `feature/*` — задачи. Коммиты по Conventional Commits (`feat:`, `fix:`). В `main` попадаем только через PR с ревью и зелёным CI.
