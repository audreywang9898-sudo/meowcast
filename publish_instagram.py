import os,time,requests

def publish_reel(video_url,caption):
    ig=os.environ.get("IG_USER_ID"); token=os.environ.get("IG_ACCESS_TOKEN")
    if not ig or not token:
        print("IG publishing skipped: add IG_USER_ID and IG_ACCESS_TOKEN as GitHub Actions secrets.")
        return
    base=f"https://graph.facebook.com/v24.0/{ig}"
    r=requests.post(base+"/media",data={"media_type":"REELS","video_url":video_url,"caption":caption,"share_to_feed":"true","access_token":token},timeout=60); r.raise_for_status(); cid=r.json()["id"]
    for _ in range(30):
        s=requests.get(f"https://graph.facebook.com/v24.0/{cid}",params={"fields":"status_code","access_token":token},timeout=30).json()
        if s.get("status_code")=="FINISHED": break
        if s.get("status_code")=="ERROR": raise RuntimeError(s)
        time.sleep(10)
    r=requests.post(base+"/media_publish",data={"creation_id":cid,"access_token":token},timeout=60); r.raise_for_status(); print(r.json())

if __name__=="__main__":
    url=os.environ.get("REEL_PUBLIC_URL")
    if not url: raise SystemExit("REEL_PUBLIC_URL missing")
    publish_reel(url,open("output/caption.txt",encoding="utf-8").read())
