#!/usr/bin/env python3
"""External scheduler watchdog for Taipei and Melbourne Meowcast.

Runs outside GitHub Actions (e.g. Render Cron). It never publishes directly.
It verifies public publication evidence and, only when a local slot is overdue,
uses GitHub's official workflow_dispatch API to wake the existing publisher.
"""
import json, os, sys
from datetime import datetime, time, timezone
from urllib import request, error
from zoneinfo import ZoneInfo

OWNER="audreywang9898-sudo"
REPO="meowcast"
MEDIA_BASE="https://raw.githubusercontent.com/audreywang9898-sudo/meowcast-media/main"
TOKEN=os.environ.get("MEOWCAST_GITHUB_TOKEN","").strip()
DRY_RUN=os.environ.get("WATCHDOG_DRY_RUN","false").lower()=="true"

CITIES={
 "taipei":{
   "tz":"Asia/Taipei","workflow":"daily.yml","prefix":"latest",
   "slots":{
     "0700":{"not_before":time(7,20),"not_after":time(8,30),"inputs":{"period":"morning","republish":False}},
     "1630":{"not_before":time(16,55),"not_after":time(18,30),"inputs":{"period":"evening","republish":False}},
   }},
 "melbourne":{
   "tz":"Australia/Melbourne","workflow":"melbourne.yml","prefix":"latest/melbourne",
   "slots":{
     "0700":{"not_before":time(7,20),"not_after":time(8,30),"inputs":{"period":"morning","publish":True,"republish":False}},
     "1630":{"not_before":time(16,55),"not_after":time(18,30),"inputs":{"period":"evening","publish":True,"republish":False}},
   }},
}

# Keep Matala opt-in until its dedicated account and artwork are verified.
if os.environ.get("MATALA_PRODUCTION_ENABLED", "false").lower() == "true":
    CITIES["matala"] = {
        "tz": "Europe/Athens", "workflow": "matala.yml", "prefix": "latest/matala",
        "slots": {
            "0700": {"not_before": time(7,20), "not_after": time(8,30),
                     "inputs": {"period": "morning", "publish": True, "republish": False}},
            "1630": {"not_before": time(16,55), "not_after": time(18,30),
                     "inputs": {"period": "evening", "publish": True, "republish": False}},
        },
    }

def get_json(url, headers=None):
    req=request.Request(url,headers=headers or {})
    try:
        with request.urlopen(req,timeout=20) as r:
            return json.loads(r.read().decode())
    except error.HTTPError as e:
        if e.code==404:return None
        raise

def evidence_ok(city,cfg,slot,local_date):
    url=f"{MEDIA_BASE}/{cfg['prefix']}/published-evidence-{slot}.json?watchdog={int(datetime.now(timezone.utc).timestamp())}"
    e=get_json(url)
    if not e:return False,"missing"
    required=("media_id","container_id","status","date","slot","run_id","published_at")
    if any(not e.get(k) for k in required):return False,"incomplete"
    if e["status"]!="published" or e["date"]!=local_date or str(e["slot"])!=slot:
        return False,f"stale:{e.get('date')}/{e.get('slot')}/{e.get('status')}"
    try:
        published=datetime.fromisoformat(e["published_at"].replace("Z","+00:00")).astimezone(ZoneInfo(cfg["tz"]))
        cutoff=time(6,45) if slot=="0700" else time(16,20)
        if published.date().isoformat()!=local_date or published.time()<cutoff:
            return False,"outside-slot-window"
    except Exception:
        return False,"bad-published_at"
    return True,f"published:{e['media_id']}"

def github_headers():
    if not TOKEN: raise RuntimeError("MEOWCAST_GITHUB_TOKEN is required")
    return {"Authorization":f"Bearer {TOKEN}","Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version":"2022-11-28","User-Agent":"meowcast-external-watchdog"}

def active_run(workflow):
    url=f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{workflow}/runs?per_page=20"
    data=get_json(url,github_headers()) or {}
    for r in data.get("workflow_runs",[]):
        if r.get("status") in ("queued","in_progress","waiting","pending","requested"):
            return r.get("html_url") or str(r.get("id"))
    return None

def dispatch(workflow,inputs):
    url=f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{workflow}/dispatches"
    body=json.dumps({"ref":"main","inputs":inputs}).encode()
    req=request.Request(url,data=body,method="POST",headers={**github_headers(),"Content-Type":"application/json"})
    with request.urlopen(req,timeout=20) as r:
        if r.status not in (200,201,204): raise RuntimeError(f"dispatch HTTP {r.status}")

def main():
    actions=0
    for city,cfg in CITIES.items():
        now=datetime.now(ZoneInfo(cfg["tz"]))
        local_date=now.date().isoformat()
        for slot,s in cfg["slots"].items():
            if not (s["not_before"] <= now.time().replace(tzinfo=None) <= s["not_after"]):
                continue
            ok,why=evidence_ok(city,cfg,slot,local_date)
            if ok:
                print(f"OK {city} {local_date} {slot} {why}")
                continue
            active=active_run(cfg["workflow"]) if TOKEN else None
            if active:
                print(f"WAIT {city} {local_date} {slot}: evidence={why}; active={active}")
                continue
            if DRY_RUN:
                print(f"DRY_RUN {city} {local_date} {slot}: would dispatch; evidence={why}")
                continue
            dispatch(cfg["workflow"],s["inputs"])
            actions+=1
            print(f"DISPATCHED {city} {local_date} {slot}: evidence={why}")
    print(f"watchdog complete; dispatches={actions}")

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"WATCHDOG ERROR: {exc}",file=sys.stderr)
        raise
