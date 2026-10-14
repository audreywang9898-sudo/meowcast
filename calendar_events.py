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


def event_for_slot(date_text, period="morning", calendar=None):
    """Select primary morning or explicitly scheduled secondary evening event.

    Compatibility: a single asset-bearing legacy 'also' without a slot is
    treated as an evening event (2027-02-04 Beginning of Spring).
    Standby and unassigned secondary entries never pre-empt evening weather.
    """
    event = event_for_date(date_text, calendar=calendar)
    if not event:
        return None
    if period != "evening":
        return event
    extras = [e for e in event.get("also", []) if isinstance(e, dict) and e.get("asset")]
    explicit = [e for e in extras if e.get("slot") == "evening"]
    legacy = [e for e in extras if "slot" not in e]
    selected = explicit[0] if len(explicit) == 1 else (
        legacy[0] if not explicit and len(extras) == 1 and len(legacy) == 1 else None
    )
    return {**selected, "_use_evening_artwork": True} if selected else None
