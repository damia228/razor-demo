import json
import os
from pathlib import Path

from settings_store import (
    get_settings_updated_at,
    load_settings_value,
    save_settings_value,
    storage_description,
)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.getenv("BUSINESS_CONFIG_PATH", str(BASE_DIR / "business_config.json")))


def _require(obj, key, expected=None):
    if key not in obj:
        raise RuntimeError(f"business config: missing '{key}'")
    value = obj[key]
    if expected and not isinstance(value, expected):
        raise RuntimeError(f"business config: '{key}' has invalid type")
    return value


def validate_business_config(config):
    if not isinstance(config, dict):
        raise RuntimeError("business config: root must be an object")

    brand = _require(config, "brand", dict)
    schedule = _require(config, "schedule", dict)
    commerce = _require(config, "commerce", dict)
    services = _require(config, "services", list)
    staff = _require(config, "staff", list)

    if not services:
        raise RuntimeError("business config: at least one service is required")
    if not staff:
        raise RuntimeError("business config: at least one staff member is required")

    service_names = [str(item.get("name", "")).strip() for item in services]
    staff_names = [str(item.get("name", "")).strip() for item in staff]
    if any(not name for name in service_names) or len(service_names) != len(set(service_names)):
        raise RuntimeError("business config: service names must be non-empty and unique")
    if any(not name for name in staff_names) or len(staff_names) != len(set(staff_names)):
        raise RuntimeError("business config: staff names must be non-empty and unique")

    for item in services:
        if int(item.get("price", -1)) < 0 or int(item.get("duration", 0)) <= 0:
            raise RuntimeError("business config: every service needs non-negative price and positive duration")

    for key in ("open", "close", "timezone"):
        _require(schedule, key)
    for key in ("name", "type", "city"):
        _require(brand, key)
    _require(commerce, "currency")

    return config


def _load_seed_file():
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Business config seed not found: {CONFIG_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {CONFIG_PATH}: {exc}") from exc
    return validate_business_config(config)


def load_business_config():
    stored = load_settings_value()
    if stored:
        try:
            return validate_business_config(json.loads(stored))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Stored business config contains invalid JSON") from exc

    # First run / migration from V2: seed persistent storage with current JSON.
    seed = _load_seed_file()
    save_settings_value(json.dumps(seed, ensure_ascii=False))
    return seed


def save_business_config(config):
    validated = validate_business_config(config)
    save_settings_value(json.dumps(validated, ensure_ascii=False))
    return validated


def business_config_storage_info():
    info = storage_description()
    info["updated_at"] = get_settings_updated_at()
    return info
