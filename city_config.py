import json
import os
from pathlib import Path

DEFAULT_CITY = "taipei"


def get_city_id():
    return os.environ.get("CITY", DEFAULT_CITY).strip().lower() or DEFAULT_CITY


def load_city_config(city_id=None):
    city_id=(city_id or get_city_id()).strip().lower()
    path=Path("cities") / f"{city_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown city config: {path}")
    with path.open(encoding="utf-8") as f:
        cfg=json.load(f)
    cfg.setdefault("id", city_id)
    cfg.setdefault("display_name", city_id.title())
    cfg.setdefault("cat_name", f"{cfg['display_name']} Cat")
    cfg.setdefault("timezone", "UTC")
    cfg.setdefault("language", "english")
    cfg.setdefault("asset_prefix", f"asset/{city_id}")
    cfg.setdefault("media_state_prefix", f"latest/{city_id}")
    cfg.setdefault("holiday_mode", False)
    cfg.setdefault("morning_window", [7,17])
    cfg.setdefault("evening_window", [17,23])
    return cfg
