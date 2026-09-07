import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_DATABASE_URL = (os.getenv("SETTINGS_DATABASE_URL") or "").strip()
SETTINGS_DATABASE_PATH = Path(
    os.getenv(
        "SETTINGS_DATABASE_PATH",
        os.getenv("DATABASE_PATH", str(BASE_DIR / "bookings.db")),
    )
)
SETTINGS_KEY = "business_config"


def backend_name():
    return "postgres" if SETTINGS_DATABASE_URL else "sqlite"


def storage_description():
    if SETTINGS_DATABASE_URL:
        return {
            "backend": "postgres",
            "persistent": True,
            "location": "SETTINGS_DATABASE_URL",
        }
    return {
        "backend": "sqlite",
        "persistent": False if os.getenv("APP_ENV", "development").lower() == "production" else True,
        "location": str(SETTINGS_DATABASE_PATH),
    }


def _postgres_connect():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "SETTINGS_DATABASE_URL задан, но psycopg не установлен. "
            "Выполните pip install -r requirements.txt."
        ) from exc
    return psycopg.connect(SETTINGS_DATABASE_URL)


def _ensure_sqlite_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def _ensure_postgres_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    conn.commit()


def load_settings_value(key=SETTINGS_KEY):
    if SETTINGS_DATABASE_URL:
        with _postgres_connect() as conn:
            _ensure_postgres_table(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM app_settings WHERE key = %s", (key,))
                row = cur.fetchone()
                return row[0] if row else None

    SETTINGS_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SETTINGS_DATABASE_PATH, timeout=10) as conn:
        _ensure_sqlite_table(conn)
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        conn.commit()
        return row[0] if row else None


def save_settings_value(value, key=SETTINGS_KEY):
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)

    if SETTINGS_DATABASE_URL:
        with _postgres_connect() as conn:
            _ensure_postgres_table(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_settings(key, value, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT(key) DO UPDATE
                    SET value = EXCLUDED.value, updated_at = NOW()
                    """,
                    (key, value),
                )
            conn.commit()
        return

    SETTINGS_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(SETTINGS_DATABASE_PATH, timeout=10) as conn:
        _ensure_sqlite_table(conn)
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE
            SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
        conn.commit()


def get_settings_updated_at(key=SETTINGS_KEY):
    if SETTINGS_DATABASE_URL:
        with _postgres_connect() as conn:
            _ensure_postgres_table(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT updated_at FROM app_settings WHERE key = %s", (key,))
                row = cur.fetchone()
                return row[0].isoformat() if row and row[0] else None

    SETTINGS_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SETTINGS_DATABASE_PATH, timeout=10) as conn:
        _ensure_sqlite_table(conn)
        row = conn.execute("SELECT updated_at FROM app_settings WHERE key = ?", (key,)).fetchone()
        conn.commit()
        return row[0] if row else None
