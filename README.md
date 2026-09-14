# RAZOR V3.5 — Lead Engine / FORMA

Полноценная lead-first версия RAZOR для бизнеса с дорогой индивидуальной услугой. Демо-ниша — мебель на заказ.

## Что уже работает
- продающий сайт FORMA;
- структурированная заявка: имя, телефон, услуга, размеры, бюджет, пожелания, источник;
- `POST /api/lead` сохраняет лид в БД;
- PostgreSQL на Render через `DATABASE_URL` **или** прежний `SETTINGS_DATABASE_URL`;
- SQLite локально без дополнительной настройки;
- CRM на `/admin`;
- воронка: Новый → Связались → Расчёт → Сделка / Отказ;
- поиск и фильтрация лидов;
- карточка лида, заметки, сумма сделки;
- базовая аналитика: заявки за 14 дней, категории, конверсия, сумма воронки;
- `/healthz` для Render;
- пароль CRM через `ADMIN_PASSWORD`.

## Локальный запуск
```powershell
python -m pip install -r requirements.txt
$env:ADMIN_PASSWORD="your-password"
$env:SECRET_KEY="change-me"
python app.py
```

Сайт: `http://127.0.0.1:5000`
CRM: `http://127.0.0.1:5000/admin`

При локальном запуске без `ADMIN_PASSWORD` CRM доступна с localhost для удобства разработки. На публичном сервере без `ADMIN_PASSWORD` CRM блокируется.

## Render
Для существующего сервиса достаточно заменить файлы проекта и убедиться, что заданы:
- `ADMIN_PASSWORD` — пароль для `/admin`;
- `SECRET_KEY` — длинная случайная строка;
- `SETTINGS_DATABASE_URL` можно оставить как есть, если он уже указывает на вашу PostgreSQL. Код его поддерживает.

Build command:
`pip install -r requirements.txt`

Start command:
`gunicorn app:app`

## API заявки
`POST /api/lead`
```json
{
  "name": "Дамир",
  "phone": "+7 777 000 00 00",
  "service": "Кухня",
  "width": "3.2 м",
  "budget": "600 000–1 000 000 ₸",
  "details": "Тёплый дуб, встроенная техника",
  "source": "instagram / cpc / september"
}
```
