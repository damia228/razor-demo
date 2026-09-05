from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import csv
import hmac
import io
import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

app = Flask(__name__)

APP_ENV = os.getenv("APP_ENV", "development").lower()
IS_PRODUCTION = APP_ENV == "production"

app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-before-deploy")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=32 * 1024,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "bookings.db")))

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SERVICES = {
    "Стрижка": {"price": 6000, "duration": 60},
    "Стрижка + борода": {"price": 9000, "duration": 60},
    "Борода": {"price": 4000, "duration": 60},
}

MASTERS = {
    "Арман": {"rating": "4.9", "experience": "5 лет", "speciality": "Классика • Fade • Styling"},
    "Тимур": {"rating": "5.0", "experience": "7 лет", "speciality": "Fade • Crop • Modern"},
    "Данияр": {"rating": "4.8", "experience": "4 года", "speciality": "Борода • Классика • Fade"},
}

WORKING_HOURS = [
    "10:00", "11:00", "12:00", "13:00", "14:00", "15:00",
    "16:00", "17:00", "18:00", "19:00", "20:00"
]

STATUS_LABELS = {
    "new": "Новая",
    "confirmed": "Подтверждена",
    "completed": "Завершена",
    "cancelled": "Отменена",
}

PHONE_RE = re.compile(r"^[+0-9()\-\s]{7,24}$")


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_code TEXT UNIQUE,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                service TEXT NOT NULL,
                price INTEGER NOT NULL DEFAULT 0,
                master TEXT NOT NULL,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                client_note TEXT NOT NULL DEFAULT '',
                admin_note TEXT NOT NULL DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(bookings)").fetchall()}
        migrations = {
            "reference_code": "TEXT",
            "price": "INTEGER NOT NULL DEFAULT 0",
            "status": "TEXT NOT NULL DEFAULT 'new'",
            "client_note": "TEXT NOT NULL DEFAULT ''",
            "admin_note": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        }
        for name, definition in migrations.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE bookings ADD COLUMN {name} {definition}")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS booking_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
            )
        """)

        rows = conn.execute("SELECT id FROM bookings WHERE reference_code IS NULL OR reference_code = ''").fetchall()
        for row in rows:
            conn.execute(
                "UPDATE bookings SET reference_code = ? WHERE id = ?",
                (generate_reference(conn), row["id"]),
            )

        # Old demo databases may contain duplicate cancelled slots. A partial unique index
        # blocks only active bookings and still lets cancelled history remain intact.
        try:
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS unique_active_slot
                ON bookings(master, booking_date, booking_time)
                WHERE status != 'cancelled'
            """)
        except sqlite3.IntegrityError:
            pass

        conn.commit()


def generate_reference(conn=None):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    owns_conn = conn is None
    db = conn or get_db()
    try:
        while True:
            code = "RZ-" + "".join(secrets.choice(alphabet) for _ in range(6))
            exists = db.execute("SELECT 1 FROM bookings WHERE reference_code = ?", (code,)).fetchone()
            if not exists:
                return code
    finally:
        if owns_conn:
            db.close()


def log_event(conn, booking_id, event_type, old_value=None, new_value=None):
    conn.execute(
        "INSERT INTO booking_events (booking_id, event_type, old_value, new_value) VALUES (?, ?, ?, ?)",
        (booking_id, event_type, old_value, new_value),
    )


def admin_logged_in():
    return session.get("admin_authenticated") is True


def require_admin_json():
    if not admin_logged_in():
        return jsonify({"ok": False, "error": "Требуется вход администратора"}), 401
    return None


def parse_booking_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def normalize_phone(value):
    return re.sub(r"\D", "", value or "")


def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=8,
        )
        return response.ok
    except requests.RequestException:
        return False


def validate_runtime_config():
    if IS_PRODUCTION:
        if app.secret_key == "change-me-before-deploy":
            raise RuntimeError("FLASK_SECRET_KEY must be set in production")
        if not ADMIN_PASSWORD:
            raise RuntimeError("ADMIN_PASSWORD must be set in production")


validate_runtime_config()

init_db()


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "razor"}), 200


@app.route("/")
def index():
    return render_template("index.html", services=SERVICES, masters=MASTERS)


@app.route("/my-booking")
def my_booking_page():
    return render_template("my_booking.html")


@app.route("/admin")
def admin():
    if not admin_logged_in():
        return redirect(url_for("admin_login"))
    return render_template("admin.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if admin_logged_in():
        return redirect(url_for("admin"))

    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if not ADMIN_PASSWORD:
            error = "ADMIN_PASSWORD не настроен."
        elif hmac.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session["admin_authenticated"] = True
            session.permanent = True
            return redirect(url_for("admin"))
        else:
            error = "Неверный пароль."

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/api/slots")
def slots():
    master = (request.args.get("master") or "").strip()
    booking_date = (request.args.get("date") or "").strip()
    chosen_date = parse_booking_date(booking_date)

    if master not in MASTERS or not chosen_date:
        return jsonify({"ok": False, "error": "Выберите мастера и корректную дату"}), 400

    today = date.today()
    if chosen_date < today:
        return jsonify({"ok": False, "error": "Нельзя записаться на прошедшую дату"}), 400
    if chosen_date > today + timedelta(days=60):
        return jsonify({"ok": False, "error": "Запись доступна максимум на 60 дней вперёд"}), 400

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT booking_time FROM bookings
            WHERE master = ? AND booking_date = ? AND status != 'cancelled'
            """,
            (master, booking_date),
        ).fetchall()

    busy = {row["booking_time"] for row in rows}
    available = [t for t in WORKING_HOURS if t not in busy]

    # Hide already elapsed hours if booking for today.
    if chosen_date == today:
        now_hm = datetime.now().strftime("%H:%M")
        available = [t for t in available if t > now_hm]

    return jsonify({"ok": True, "available": available, "busy": sorted(busy)})


@app.route("/api/lead", methods=["POST"])
def lead():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    service = (data.get("service") or "").strip()
    master = (data.get("master") or "").strip()
    booking_date = (data.get("date") or "").strip()
    booking_time = (data.get("bookingTime") or "").strip()
    client_note = (data.get("clientNote") or "").strip()[:500]
    chosen_date = parse_booking_date(booking_date)

    if not all([name, phone, service, master, booking_date, booking_time]):
        return jsonify({"ok": False, "error": "Заполните обязательные поля"}), 400
    if len(name) < 2 or len(name) > 60:
        return jsonify({"ok": False, "error": "Проверьте имя"}), 400
    if not PHONE_RE.match(phone):
        return jsonify({"ok": False, "error": "Проверьте номер телефона"}), 400
    if service not in SERVICES:
        return jsonify({"ok": False, "error": "Неизвестная услуга"}), 400
    if master not in MASTERS:
        return jsonify({"ok": False, "error": "Неизвестный мастер"}), 400
    if booking_time not in WORKING_HOURS:
        return jsonify({"ok": False, "error": "Недоступное время"}), 400
    if not chosen_date or chosen_date < date.today():
        return jsonify({"ok": False, "error": "Проверьте дату записи"}), 400
    if chosen_date > date.today() + timedelta(days=60):
        return jsonify({"ok": False, "error": "Запись доступна максимум на 60 дней вперёд"}), 400

    price = SERVICES[service]["price"]

    try:
        with get_db() as conn:
            conflict = conn.execute(
                """
                SELECT id FROM bookings
                WHERE master = ? AND booking_date = ? AND booking_time = ? AND status != 'cancelled'
                """,
                (master, booking_date, booking_time),
            ).fetchone()
            if conflict:
                return jsonify({"ok": False, "error": "Это время уже занято. Выберите другой слот."}), 409

            reference_code = generate_reference(conn)
            cursor = conn.execute(
                """
                INSERT INTO bookings
                (reference_code, name, phone, service, price, master, booking_date, booking_time, status, client_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
                """,
                (reference_code, name, phone, service, price, master, booking_date, booking_time, client_note),
            )
            booking_id = cursor.lastrowid
            log_event(conn, booking_id, "created", None, "new")
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "error": "Это время уже занято. Выберите другой слот."}), 409

    telegram_sent = send_telegram(
        "💈 Новая запись RAZOR\n\n"
        f"Код: {reference_code}\n"
        f"Имя: {name}\nТелефон: {phone}\n"
        f"Услуга: {service} — {price:,} ₸\n".replace(",", " ")
        + f"Мастер: {master}\nДата: {booking_date}\nВремя: {booking_time}"
        + (f"\nКомментарий: {client_note}" if client_note else "")
    )

    return jsonify({
        "ok": True,
        "reference": reference_code,
        "telegram_sent": telegram_sent,
        "booking": {
            "service": service,
            "master": master,
            "date": booking_date,
            "time": booking_time,
            "price": price,
        }
    })


@app.route("/api/my-booking", methods=["POST"])
def find_my_booking():
    data = request.get_json(silent=True) or {}
    reference = (data.get("reference") or "").strip().upper()
    phone = normalize_phone(data.get("phone"))

    if not reference or len(phone) < 7:
        return jsonify({"ok": False, "error": "Введите код записи и телефон"}), 400

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT reference_code, name, phone, service, price, master,
                   booking_date, booking_time, status, client_note
            FROM bookings WHERE reference_code = ?
            """,
            (reference,),
        ).fetchone()

    if not row or normalize_phone(row["phone"]) != phone:
        return jsonify({"ok": False, "error": "Запись не найдена. Проверьте код и телефон."}), 404

    result = dict(row)
    result["status_label"] = STATUS_LABELS.get(result["status"], result["status"])
    result["can_cancel"] = result["status"] in {"new", "confirmed"}
    return jsonify({"ok": True, "booking": result})


@app.route("/api/my-booking/cancel", methods=["POST"])
def cancel_my_booking():
    data = request.get_json(silent=True) or {}
    reference = (data.get("reference") or "").strip().upper()
    phone = normalize_phone(data.get("phone"))

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, phone, status FROM bookings WHERE reference_code = ?",
            (reference,),
        ).fetchone()

        if not row or normalize_phone(row["phone"]) != phone:
            return jsonify({"ok": False, "error": "Запись не найдена"}), 404
        if row["status"] not in {"new", "confirmed"}:
            return jsonify({"ok": False, "error": "Эту запись уже нельзя отменить"}), 409

        old = row["status"]
        conn.execute(
            "UPDATE bookings SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["id"],),
        )
        log_event(conn, row["id"], "status", old, "cancelled")
        conn.commit()

    return jsonify({"ok": True})


@app.route("/api/bookings")
def bookings():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, reference_code, name, phone, service, price, master,
                   booking_date, booking_time, status, client_note, admin_note,
                   created_at, updated_at
            FROM bookings
            ORDER BY booking_date DESC, booking_time DESC
            """
        ).fetchall()

    return jsonify({"ok": True, "bookings": [dict(row) for row in rows]})


@app.route("/api/admin/stats")
def admin_stats():
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()

    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM bookings").fetchone()["c"]
        new_count = conn.execute("SELECT COUNT(*) c FROM bookings WHERE status = 'new'").fetchone()["c"]
        today_count = conn.execute(
            "SELECT COUNT(*) c FROM bookings WHERE booking_date = ? AND status != 'cancelled'", (today,)
        ).fetchone()["c"]
        completed_month = conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(price),0) revenue FROM bookings WHERE status = 'completed' AND booking_date >= ?",
            (month_start,),
        ).fetchone()
        masters = conn.execute(
            """
            SELECT master, COUNT(*) c FROM bookings
            WHERE status != 'cancelled'
            GROUP BY master ORDER BY c DESC
            """
        ).fetchall()

    return jsonify({
        "ok": True,
        "stats": {
            "total": total,
            "new": new_count,
            "today": today_count,
            "completed_month": completed_month["c"],
            "revenue_month": completed_month["revenue"],
            "top_master": masters[0]["master"] if masters else "—",
        }
    })


@app.route("/api/bookings/<int:booking_id>/status", methods=["PATCH"])
def update_booking_status(booking_id):
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip()
    if new_status not in STATUS_LABELS:
        return jsonify({"ok": False, "error": "Недопустимый статус"}), 400

    with get_db() as conn:
        booking = conn.execute(
            "SELECT id, master, booking_date, booking_time, status FROM bookings WHERE id = ?",
            (booking_id,),
        ).fetchone()
        if not booking:
            return jsonify({"ok": False, "error": "Запись не найдена"}), 404

        if booking["status"] == "cancelled" and new_status != "cancelled":
            conflict = conn.execute(
                """
                SELECT id FROM bookings
                WHERE master = ? AND booking_date = ? AND booking_time = ?
                  AND status != 'cancelled' AND id != ?
                """,
                (booking["master"], booking["booking_date"], booking["booking_time"], booking_id),
            ).fetchone()
            if conflict:
                return jsonify({"ok": False, "error": "Этот слот уже занят другой записью"}), 409

        old_status = booking["status"]
        conn.execute(
            "UPDATE bookings SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, booking_id),
        )
        log_event(conn, booking_id, "status", old_status, new_status)
        conn.commit()

    return jsonify({"ok": True, "status": new_status, "status_label": STATUS_LABELS[new_status]})


@app.route("/api/bookings/<int:booking_id>/note", methods=["PATCH"])
def update_admin_note(booking_id):
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    note = (data.get("note") or "").strip()[:1000]

    with get_db() as conn:
        row = conn.execute("SELECT admin_note FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Запись не найдена"}), 404
        conn.execute(
            "UPDATE bookings SET admin_note = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (note, booking_id),
        )
        log_event(conn, booking_id, "admin_note", row["admin_note"], note)
        conn.commit()

    return jsonify({"ok": True})


@app.route("/api/bookings/<int:booking_id>/history")
def booking_history(booking_id):
    auth_error = require_admin_json()
    if auth_error:
        return auth_error

    with get_db() as conn:
        rows = conn.execute(
            "SELECT event_type, old_value, new_value, created_at FROM booking_events WHERE booking_id = ? ORDER BY id DESC",
            (booking_id,),
        ).fetchall()
    return jsonify({"ok": True, "events": [dict(r) for r in rows]})


@app.route("/admin/export.csv")
def export_csv():
    if not admin_logged_in():
        return redirect(url_for("admin_login"))

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT reference_code, name, phone, service, price, master,
                   booking_date, booking_time, status, client_note, admin_note, created_at
            FROM bookings ORDER BY booking_date, booking_time
            """
        ).fetchall()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["Код", "Имя", "Телефон", "Услуга", "Цена", "Мастер", "Дата", "Время", "Статус", "Комментарий клиента", "Заметка админа", "Создано"])
    for row in rows:
        writer.writerow([
            row["reference_code"], row["name"], row["phone"], row["service"], row["price"],
            row["master"], row["booking_date"], row["booking_time"], STATUS_LABELS.get(row["status"], row["status"]),
            row["client_note"], row["admin_note"], row["created_at"],
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=razor-bookings-{date.today().isoformat()}.csv"},
    )


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "Ресурс не найден"}), 404
    return render_template("404.html"), 404


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=not IS_PRODUCTION,
    )
