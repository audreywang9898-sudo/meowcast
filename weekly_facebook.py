"""Publish Taipei weekly two-photo Facebook Page post, independently of Instagram."""
import argparse
import base64
import json
import os
import re
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

REPO = "audreywang9898-sudo/meowcast-media"
API = "https://graph.facebook.com/v24.0"

def git(root, *args, check=True):
    return subprocess.run(["git", "-C", str(root), *args], check=check,
                          capture_output=True, text=True)

def save(root, path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    git(root, "add", str(path.relative_to(root)))
    if git(root, "diff", "--cached", "--quiet", check=False).returncode == 0:
        return
    git(root, "commit", "-m", "Persist Taipei weekly Facebook publication state")
    for _ in range(4):
        if git(root, "push", "origin", "HEAD:main", check=False).returncode == 0:
            return
        if git(root, "pull", "--rebase", "origin", "main", check=False).returncode != 0:
            git(root, "rebase", "--abort", check=False)
            raise RuntimeError("Facebook state conflict; stopped to avoid duplicate publication")
    raise RuntimeError("Cannot persist Facebook state; do not republish")

def request(method, path, token, **params):
    params["access_token"] = token
    try:
        response = requests.request(method, API + "/" + path, data=params if method == "POST" else None,
                                    params=params if method == "GET" else None, timeout=60)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError("Facebook API result uncertain; inspect Page before retrying") from None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--issue-date", required=True)
    a = p.parse_args()
    issue = date.fromisoformat(a.issue_date)
    today = datetime.now(ZoneInfo("Asia/Taipei")).date()
    if issue.weekday() != 6 or issue != today:
        raise RuntimeError("Weekly Facebook production only permits today's Sunday issue")
    token = os.environ["TAIPEI_FB_PAGE_ACCESS_TOKEN"]
    page = os.environ["TAIPEI_FB_PAGE_ID"]
    media_token = os.environ["MEDIA_REPO_TOKEN"]
    if not re.fullmatch(r"[0-9]+", page):
        raise RuntimeError("Invalid Facebook Page ID")
    auth = base64.b64encode(("x-access-token:" + media_token).encode()).decode()
    env = os.environ.copy()
    env.update({"GIT_CONFIG_COUNT":"1","GIT_CONFIG_KEY_0":"http.https://github.com/.extraheader",
                "GIT_CONFIG_VALUE_0":"AUTHORIZATION: basic " + auth,"GIT_TERMINAL_PROMPT":"0"})
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "media"
        subprocess.run(["git", "clone", "--quiet", "--depth", "20",
                        "https://github.com/" + REPO + ".git", str(root)], env=env, check=True)
        # git commands inherit credential configuration for authenticated push/pull.
        os.environ.update({k:v for k,v in env.items() if k.startswith("GIT_CONFIG_") or k=="GIT_TERMINAL_PROMPT"})
        git(root, "config", "user.name", "meowcast-bot")
        git(root, "config", "user.email", "actions@users.noreply.github.com")
        week_start = issue.fromordinal(issue.toordinal() + 1).isoformat()
        source_path = root / "weekly" / "taipei" / week_start / "state.json"
        if not source_path.exists():
            raise RuntimeError("Taipei Instagram weekly evidence missing; Facebook not published")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        if (source.get("status") != "published" or not source.get("media_id")
                or source.get("issue_date") != a.issue_date or source.get("city") != "taipei"
                or len(source.get("image_urls", [])) != 2 or not source.get("caption")):
            raise RuntimeError("Taipei Instagram weekly evidence incomplete; Facebook not published")
        state_path = root / "facebook" / "weekly" / "taipei" / week_start / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else None
        if state:
            if state.get("source_media_id") != source["media_id"] or state.get("page_id") != page:
                raise RuntimeError("Weekly Facebook state/source mismatch")
            if state.get("status") == "published" and state.get("post_id"):
                print("Already published Facebook weekly post:", state["post_id"])
                return
            if state.get("status") == "publishing":
                raise RuntimeError("Facebook publish outcome uncertain; check Page and reconcile manually, no repost")
            if state.get("status") != "prepared":
                raise RuntimeError("Unknown Facebook weekly state")
        else:
            state = {"status":"prepared","issue_date":a.issue_date,"week_start":week_start,
                     "page_id":page,"source_media_id":source["media_id"],
                     "source_run_id":source.get("run_id"),"photo_ids":[]}
            save(root, state_path, state)
        # Each photo is created unpublished; IDs are persisted before proceeding.
        for url in source["image_urls"][len(state["photo_ids"]):]:
            result = request("POST", page + "/photos", token, url=url, published="false")
            if not str(result.get("id","")).isdigit():
                raise RuntimeError("Unpublished photo ID missing; stop")
            state["photo_ids"].append(str(result["id"]))
            save(root, state_path, state)
        attached = {f"attached_media[{i}]":json.dumps({"media_fbid":pid})
                    for i,pid in enumerate(state["photo_ids"])}
        # Persist intent BEFORE posting. An ambiguous API response must never auto-repost.
        state["status"] = "publishing"
        save(root, state_path, state)
        result = request("POST", page + "/feed", token, message=source["caption"], **attached)
        if not result.get("id"):
            raise RuntimeError("Facebook post ID missing; do not retry automatically")
        state.update(status="published", post_id=str(result["id"]),
                     published_at=datetime.now(ZoneInfo("Asia/Taipei")).isoformat())
        save(root, state_path, state)
        print("Published Taipei weekly Facebook post:", state["post_id"])

if __name__ == "__main__":
    main()
