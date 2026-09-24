import json
from pathlib import Path

CALENDAR_DIR = Path("calendar")


def calendar_path_for_year(year):
    return CALENDAR_DIR / f"{year}.json"


def load_calendar(year):
    path = calendar_path_for_year(year)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("year") != year:
            raise ValueError(f"{path}: year mismatch")
        if not isinstance(data.get("events", {}), dict):
            raise ValueError(f"{path}: events must be an object")
        return data
    except FileNotFoundError:
        print(f"Calendar fallback: {path} not found")
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Calendar fallback: {exc}")
    return {"year": year, "events": {}}


def event_for_date(date_text, calendar=None):
    if calendar is not None:
        event = calendar.get("events", {}).get(date_text)
        return event if isinstance(event, dict) else None

    year = int(date_text[:4])
    data = load_calendar(year)
    event = data.get("events", {}).get(date_text)
    return event if isinstance(event, dict) else None
