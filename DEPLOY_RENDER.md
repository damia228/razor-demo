# RAZOR PRO — деплой на Render Free

## Что уже подготовлено

- Flask запускается через Gunicorn.
- Есть `render.yaml` для Blueprint.
- Есть `/healthz` для проверки здоровья сервиса.
- Python фиксируется через `.python-version`.
- `FLASK_SECRET_KEY` Render генерирует автоматически.
- `ADMIN_PASSWORD` вводится как секрет в Render и не хранится в GitHub.
- Настроены secure-cookie для production.
- Gunicorn запускается с одним worker, чтобы SQLite-демо не ловило лишние конфликты.
- `.env` специально НЕ включён в архив.

## 1. Создай GitHub-репозиторий

Создай новый пустой репозиторий, например:

`razor-demo`

Загрузи в корень репозитория ВСЁ содержимое этой папки. В корне должны лежать:

- `app.py`
- `requirements.txt`
- `render.yaml`
- `.python-version`
- `.env.example`
- папки `templates` и `static`

Не создавай и не загружай настоящий `.env`.

## 2. Создай Blueprint на Render

1. Открой Render Dashboard.
2. Нажми `New` → `Blueprint`.
3. Подключи GitHub.
4. Выбери репозиторий `razor-demo`.
5. Render автоматически прочитает `render.yaml`.
6. При создании введи значение `ADMIN_PASSWORD`.
7. Запусти создание Blueprint.

## 3. Дождись deploy

Build command уже задан:

`pip install -r requirements.txt`

Start command уже задан:

`gunicorn app:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`

После успешного deploy Render выдаст адрес примерно:

`https://razor-demo.onrender.com`

## 4. Что проверить

Открой по очереди:

- `/healthz` — должен вернуть JSON `ok: true`.
- `/` — главная RAZOR.
- `/my-booking` — управление клиентской записью.
- `/admin` — должен перекинуть на вход.

Сделай тестовую запись и проверь её в админке.

## 5. Telegram — позже

Telegram для деплоя не обязателен. Если захочешь включить уведомления:

Render → твой Web Service → Environment → Add Environment Variable

Добавь:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

После сохранения Render перезапустит приложение.

## ВАЖНО: SQLite на Render Free

Эта сборка годится для публичного продающего DEMO.

Render Free использует временную файловую систему. `bookings.db` создаётся и работает, но данные могут исчезнуть после:

- spin-down / пробуждения сервиса;
- рестарта;
- redeploy.

Поэтому текущий вариант НЕ предназначен для хранения реальных клиентских записей платящего бизнеса.

Когда появится первый заказчик, следующий технический шаг — вынести данные в постоянную БД и только после этого запускать систему как production-сервис.

## Особенность Free-сервиса

После 15 минут без входящего трафика Render Free может усыпить Web Service. Первый посетитель после этого может увидеть загрузку примерно до минуты, пока сервер просыпается.

Для демо на старте это допустимо и не требует оплаты.
