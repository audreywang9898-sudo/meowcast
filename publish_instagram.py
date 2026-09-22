import os,time,requests,json

API="https://graph.instagram.com/v24.0"

def fail(r,label):
    if r.ok: return
    try: detail=r.json()
    except Exception: detail=r.text
    raise RuntimeError(f"{label} failed (HTTP {r.status_code}): {json.dumps(detail,ensure_ascii=False)}")

def publish_reel(video_url,caption):
    ig=os.environ.get("IG_USER_ID"); token=os.environ.get("IG_ACCESS_TOKEN")
    if not ig or not token:
        print("IG publishing skipped: missing GitHub secrets.")
        return
    base=f"{API}/{ig}"
    r=requests.post(base+"/media",data={"media_type":"REELS","video_url":video_url,"caption":caption,"share_to_feed":"true","access_token":token},timeout=60)
    fail(r,"Create Reel container")
    cid=r.json()["id"]; print("Container created:",cid)
    for _ in range(30):
        s=requests.get(f"{API}/{cid}",params={"fields":"status_code,status","access_token":token},timeout=30)
        fail(s,"Check Reel status")
        data=s.json(); print("Meta status:",data.get("status_code"))
        if data.get("status_code")=="FINISHED": break
        if data.get("status_code") in ("ERROR","EXPIRED"): raise RuntimeError(json.dumps(data,ensure_ascii=False))
        time.sleep(10)
    else: raise RuntimeError("Timed out waiting for Meta to process the Reel")
    r=requests.post(base+"/media_publish",data={"creation_id":cid,"access_token":token},timeout=60)
    fail(r,"Publish Reel")
    print("Published:",r.json())

if __name__=="__main__":
    url=os.environ.get("REEL_PUBLIC_URL")
    if not url: raise SystemExit("REEL_PUBLIC_URL missing")
    publish_reel(url,open("output/caption.txt",encoding="utf-8").read())
