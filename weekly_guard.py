"""Read-only Sunday weekly publication evidence audit."""
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

today = datetime.now(ZoneInfo("Asia/Taipei")).date()
if today.weekday() != 6:
    print("Not Sunday; no audit")
    sys.exit(0)
week = (today + timedelta(days=1)).isoformat()
checks = [
    ("Taipei IG", f"weekly/taipei/{week}/state.json", "media_id"),
    ("Melbourne IG", f"weekly/melbourne/{week}/state.json", "media_id"),
    ("Taipei FB", f"facebook/weekly/taipei/{week}/state.json", "post_id"),
]
failed = False
for label, path, identifier in checks:
    response = requests.get(
        f"https://api.github.com/repos/audreywang9898-sudo/meowcast-media/contents/{path}",
        timeout=20)
    if response.status_code == 404:
        print(f"::error::{label}: no weekly publication evidence at {path}")
        failed = True
        continue
    response.raise_for_status()
    import base64
    state = json.loads(base64.b64decode(response.json()["content"]))
    valid = state.get("status") == "published" and bool(state.get(identifier)) and state.get("issue_date") == today.isoformat()
    print(f"{label}: {'confirmed' if valid else 'unconfirmed'}")
    if not valid:
        failed = True
if failed:
    sys.exit(1)
