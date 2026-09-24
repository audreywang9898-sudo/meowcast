import json
from pathlib import Path

CALENDAR_PATH = Path("calendar.json")
NEXT_CALENDAR_PATH = Path("calendar_next.json")


def load_calendar(path=CALENDAR_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data.get("events", {}), dict):
            raise ValueError(f"{path}: events must be an object")
        return data
    except FileNotFoundError:
        print(f"Calendar fallback: {path} not found")
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Calendar fallback: {exc}")
    return {"events": {}}


def event_for_date(date_text, calendar=None):
    if calendar is not None:
        event = calendar.get("events", {}).get(date_text)
        return event if isinstance(event, dict) else None

    year = int(date_text[:4])
    current = load_calendar(CALENDAR_PATH)
    if current.get("year") == year:
        event = current.get("events", {}).get(date_text)
        return event if isinstance(event, dict) else None

    upcoming = load_calendar(NEXT_CALENDAR_PATH)
    if upcoming.get("year") == year:
        event = upcoming.get("events", {}).get(date_text)
        return event if isinstance(event, dict) else None

    return None
