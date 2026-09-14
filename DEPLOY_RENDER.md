# Обновление текущего Render-сервиса

1. Скопируйте содержимое этой папки в ваш `razor-demo-clean` с заменой файлов.
2. В Render → Environment добавьте:
   - `ADMIN_PASSWORD` — пароль CRM;
   - `SECRET_KEY` — длинная случайная строка.
3. Существующий `SETTINGS_DATABASE_URL` **не удаляйте** — RAZOR V3.5 умеет использовать его как PostgreSQL.
4. Проверьте команды Render:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app`
5. После deploy:
   - `/healthz` → `ok: true`;
   - `/` → FORMA;
   - `/admin` → вход в RAZOR CRM.

## Git-команды после локальной проверки
```powershell
git add .
git commit -m "RAZOR V3.5 Lead Engine CRM"
git pull --rebase origin main
git push
```

Если `git pull --rebase` покажет `CONFLICT`, не делайте force push — сначала разрешите конфликт.
