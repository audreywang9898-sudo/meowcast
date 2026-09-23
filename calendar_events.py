import json
from pathlib import Path

CALENDAR_PATH = Path("calendar.json")


def load_calendar(path=CALENDAR_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data.get("events", {}), dict):
            raise ValueError("calendar.json: events must be an object")
        return data
    except FileNotFoundError:
        print("Calendar fallback: calendar.json not found")
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Calendar fallback: {exc}")
    return {"events": {}}


def event_for_date(date_text, calendar=None):
    calendar = calendar or load_calendar()
    event = calendar.get("events", {}).get(date_text)
    return event if isinstance(event, dict) else None
