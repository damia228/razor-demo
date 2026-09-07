# RAZOR PRO — premium demo

Запуск:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Сайт: http://127.0.0.1:5000
Моя запись: http://127.0.0.1:5000/my-booking
Админка: http://127.0.0.1:5000/admin

Пароль администратора задаётся только через переменную окружения `ADMIN_PASSWORD`. Реальный пароль в репозиторий не добавляй.

## Что добавлено

- полностью переработанный премиальный UI;
- динамические доступные слоты;
- уникальный код записи;
- самостоятельная проверка и отмена записи клиентом;
- статусы new / confirmed / completed / cancelled;
- комментарий клиента и заметка администратора;
- история изменений записи;
- KPI админки: сегодня, новые заявки, выручка месяца, топ-мастер;
- CSV-экспорт;
- защита админки и закрытые admin API;
- валидация имени, телефона, даты и слота на сервере;
- ограничение бронирования 60 днями;
- прошедшие часы сегодня скрываются;
- Telegram остаётся опциональным;
- 404-страница и адаптивный mobile UI.

## Перед реальным запуском

Эта сборка — качественный MVP/демо, но перед продажей реальному бизнесу стоит вынести БД в PostgreSQL, добавить HTTPS-хостинг, резервное копирование, юридический текст согласия/политику конфиденциальности под конкретного клиента и настроить его реальные услуги, адрес, график, фото и контакты.


# Render Free deployment

This build is prepared for Render Web Service / Blueprint deployment.

## Included
- Gunicorn production server
- `render.yaml` Blueprint
- `/healthz` health check
- secure production session cookies
- generated Flask secret on Render
- admin password stored only as a Render secret
- one Gunicorn worker for SQLite safety
- configurable `DATABASE_PATH`
- `.python-version` for Python 3.13

## Deploy
1. Create a new GitHub repository and upload all files from this project root.
2. Do NOT upload a real `.env` file. This archive intentionally contains no `.env`.
3. In Render choose **New → Blueprint** and connect the repository. Render reads `render.yaml`.
4. Render asks for secret environment values. Set `ADMIN_PASSWORD`. Telegram values are optional and may be left empty.
5. Deploy. The public URL will look like `https://razor-demo.onrender.com`.
6. Test `/healthz`, the client booking flow, `/my-booking`, and `/admin`.

## Important limitation of Render Free
The local filesystem is ephemeral. The SQLite database works for a live demo, but data can disappear after a restart, redeploy, or free-service spin-down. Do not use this SQLite setup for a paying client's production data. For a real client, migrate bookings to a persistent database before launch.

## Product polish update

This build adds production-oriented booking and admin workflow improvements:
- field-level booking validation and clearer confirmation state;
- Kazakhstan-friendly phone formatting on the client form;
- server-side slot revalidation before insert;
- working hours generated from 10:00–21:00 with 60-minute slots;
- 30-minute minimum same-day booking notice;
- booking calculations pinned to Asia/Almaty timezone;
- double-booking protection via active-slot unique index and conflict checks;
- safe booking status transitions;
- admin quick views for upcoming, today, new, next 7 days and all bookings;
- upcoming bookings sorted chronologically for daily operations.

---

## RAZOR Engine V2 — Админ-конструктор

В версии V2 появился полноценный раздел `/admin/settings`.

Через него владелец бизнеса может без редактирования JSON:

- изменить название, тип бизнеса, город, страну и описание;
- поменять акцентные цвета и изображения;
- настроить рабочие часы, шаг слотов, окно записи и часовой пояс;
- редактировать основные тексты сайта;
- добавлять и удалять услуги с ценой и длительностью;
- добавлять и удалять сотрудников с рейтингом, опытом, специализацией и фото;
- менять терминологию: мастер, врач, специалист, визит и т.д.

Сохранение выполняется через защищённый API администратора. Конфигурация валидируется, сохраняется атомарно в `business_config.json`, после чего runtime движка сразу подхватывает новые настройки без ручного перезапуска кода.

## Engine V2.1 — persistent settings

В V2.1 конструктор `/admin/settings` использует слой хранения настроек:

- SQLite локально;
- PostgreSQL при наличии `SETTINGS_DATABASE_URL`.

Текущий `business_config.json` автоматически импортируется при первом запуске и остаётся seed/backup-конфигом.
