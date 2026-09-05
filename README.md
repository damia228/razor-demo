# RAZOR PRO — premium demo

Запуск:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Сайт: http://127.0.0.1:5000
Моя запись: http://127.0.0.1:5000/my-booking
Админка: http://127.0.0.1:5000/admin

Пароль администратора этой локальной сборки:

`RazorAdmin2026!`

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
