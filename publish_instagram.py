import os,time,requests,json,sys
from pathlib import Path

INSTAGRAM_API="https://graph.instagram.com/v24.0"
FACEBOOK_API="https://graph.facebook.com/v24.0"

def credentials():
    """Choose the Meta endpoint matching the actual user token, without logging secrets."""
    ig=(os.environ.get("IG_USER_ID") or "").strip()
    token=(os.environ.get("IG_ACCESS_TOKEN") or "").strip()
    if token.startswith("IG_ACCESS_TOKEN="):
        token=token.split("=",1)[1].strip()
    token=token.strip('"\'' )
    if token.lower().startswith("bearer "):
        token=token[7:].strip()
    if not ig.isdigit():
        raise RuntimeError("IG_USER_ID must be a numeric Instagram professional account ID.")
    if not token or any(c.isspace() for c in token):
        raise RuntimeError("IG_ACCESS_TOKEN is missing or contains whitespace; enter only the complete Meta access token in GitHub Secrets.")
    if token.startswith("EAA"):
        # Facebook Login (including Page tokens) uses graph.facebook.com.
        api=FACEBOOK_API
    elif token.startswith("IG"):
        # Instagram Login uses graph.instagram.com.
        api=INSTAGRAM_API
    else:
        raise RuntimeError("IG_ACCESS_TOKEN has an unrecognized token format; expected an Instagram (IG...) or Facebook (EAA...) user access token.")
    return ig,token,api


def check_credentials():
    """Read-only token/account validation; never creates or publishes a Reel."""
    ig,token,api=credentials()
    r=requests.get(f"{api}/{ig}",params={"fields":"id","access_token":token},timeout=30)
    fail(r,"Validate Instagram access")
    if str(r.json().get("id")) != ig:
        raise RuntimeError("IG_USER_ID does not match the Instagram account accessible through IG_ACCESS_TOKEN.")
    print("Instagram token and target account verified (read-only; publication permission not tested).")

def fail(r,label):
    if r.ok: return
    try: detail=r.json()
    except Exception: detail=r.text
    error=detail.get("error",{}) if isinstance(detail,dict) else {}
    if error.get("code")==190:
        raise RuntimeError(f"{label} failed: Meta rejected IG_ACCESS_TOKEN (OAuth 190). Check the token value, expiration, and matching Instagram/Facebook Login type.")
    raise RuntimeError(f"{label} failed (HTTP {r.status_code}): {json.dumps(detail,ensure_ascii=False)}")

def publish_reel(video_url,caption):
    ig,token,api=credentials()
    base=f"{api}/{ig}"
    r=requests.post(base+"/media",data={"media_type":"REELS","video_url":video_url,"caption":caption,"share_to_feed":"true","access_token":token},timeout=60)
    fail(r,"Create Reel container")
    cid=r.json()["id"]; print("Container created:",cid)
    for _ in range(30):
        s=requests.get(f"{api}/{cid}",params={"fields":"status_code,status","access_token":token},timeout=30)
        fail(s,"Check Reel status")
        data=s.json(); print("Meta status:",data.get("status_code"))
        if data.get("status_code")=="FINISHED": break
        if data.get("status_code") in ("ERROR","EXPIRED"): raise RuntimeError(json.dumps(data,ensure_ascii=False))
        time.sleep(10)
    else: raise RuntimeError("Timed out waiting for Meta to process the Reel")
    # Meta occasionally returns transient HTTP 5xx / code 2 even after the container is FINISHED.
    # Retry publishing the SAME container with exponential backoff instead of creating a duplicate Reel.
    for attempt in range(1,6):
        r=requests.post(base+"/media_publish",data={"creation_id":cid,"access_token":token},timeout=60)
        if r.ok:
            published=r.json()
            media_id=published.get("id")
            if not media_id:
                raise RuntimeError("Meta publish response has no media ID; publication is unconfirmed")
            receipt={"city":os.environ.get("CITY","taipei"),"container_id":cid,"media_id":str(media_id),"status":"published","run_id":os.environ.get("GITHUB_RUN_ID")}
            out=Path("output"); out.mkdir(exist_ok=True)
            temporary=out/"publish-result.json.tmp"
            temporary.write_text(json.dumps(receipt,ensure_ascii=False),encoding="utf-8")
            temporary.replace(out/"publish-result.json")
            print("Published:",published)
            return receipt
        try:
            detail=r.json()
        except Exception:
            detail={"raw":r.text}
        err=detail.get("error",{}) if isinstance(detail,dict) else {}
        transient=(r.status_code >= 500 or err.get("is_transient") is True or err.get("code")==2)
        if transient and attempt < 5:
            wait=10*(2**(attempt-1))
            print(f"Transient Meta publish error; retry {attempt}/5 in {wait}s:",json.dumps(detail,ensure_ascii=False))
            time.sleep(wait)
            continue
        fail(r,"Publish Reel")

if __name__=="__main__":
    if sys.argv[1:]==["--check-config"]:
        check_credentials()
        sys.exit(0)
    if len(sys.argv)>1:
        raise SystemExit("Usage: publish_instagram.py [--check-config]")
    # Never accept a stale receipt from a prior local invocation.
    Path("output/publish-result.json").unlink(missing_ok=True)
    url=os.environ.get("REEL_PUBLIC_URL")
    if not url: raise SystemExit("REEL_PUBLIC_URL missing")
    publish_reel(url,open("output/caption.txt",encoding="utf-8").read())
