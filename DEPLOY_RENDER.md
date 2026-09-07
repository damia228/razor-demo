# RAZOR Engine V2.1 — Render deployment

## Что изменилось в V2.1

Настройки из `/admin/settings` больше не обязаны жить в `business_config.json`.

- Локально, если `SETTINGS_DATABASE_URL` пустой, настройки сохраняются в SQLite рядом с записями.
- На production можно задать PostgreSQL URL через `SETTINGS_DATABASE_URL`.
- При первом запуске движок автоматически импортирует текущий `business_config.json` в хранилище.
- После этого изменения из конструктора читаются из БД и переживают restart/redeploy при использовании постоянной PostgreSQL БД.
- `/healthz` показывает только тип хранилища и его состояние, без секрета подключения.

## Обновление существующего razor-demo

1. Распакуй V2.1 и замени содержимое GitHub-репозитория RAZOR этими файлами.
2. Настоящий `.env` в GitHub не загружай.
3. В Render открой `razor-demo` → Environment.
4. Оставь существующие `APP_ENV=production`, `FLASK_SECRET_KEY`, `ADMIN_PASSWORD`.
5. Добавь `SETTINGS_DATABASE_URL` со строкой подключения к постоянной PostgreSQL БД.
6. Сохрани переменные и запусти redeploy последнего commit.
7. После deploy открой `/healthz`. В `settings_storage.backend` должно быть `postgres`.
8. Войди в `/admin/settings`, поменяй тестовое поле, сохрани.
9. Выполни Manual Deploy / restart и убедись, что изменение осталось.

## Важно про записи клиентов

V2.1 делает постоянными именно настройки конструктора через PostgreSQL. Сами клиентские записи пока используют `DATABASE_PATH` / SQLite.
На Render с временной файловой системой это всё ещё DEMO-режим: записи могут исчезнуть после redeploy/restart.

Следующий production-шаг для платящего бизнеса — перенести таблицы `bookings` и `booking_events` в PostgreSQL тоже.

## Локальный запуск

Создай `.env` рядом с `app.py`:

```env
APP_ENV=development
ADMIN_PASSWORD=CHANGE_THIS_LOCAL_PASSWORD
FLASK_SECRET_KEY=razor-local-secret
DATABASE_PATH=bookings.db
SETTINGS_DATABASE_URL=
```

Затем:

```bat
pip install -r requirements.txt
python app.py
```

Локально PostgreSQL не нужен.
