"""Validate 2027 H2 calendar wiring and asset readiness without publishing."""
import json
from pathlib import Path
from calendar_events import event_for_slot, load_calendar

ROOT=Path(__file__).resolve().parent
BASE=ROOT/"asset"/"taipei"
MANIFEST=BASE/"2027-h2"/"artwork-manifest.json"


def main():
    cal=load_calendar(2027)
    assert cal["coverage"]["end"]=="2027-12-31"
    entries=json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(entries["images"])==8
    assert len({x["asset"] for x in entries["images"]})==8
    missing=[]
    for image in entries["images"]:
        date, asset=image["date"],image["asset"]
        ev=cal["events"][date]
        assert any(x.get("asset")==asset for x in [ev,*ev.get("also",[])]), (date,asset)
        path=BASE/asset
        if not path.exists():
            missing.append(asset)
            continue
        from PIL import Image
        with Image.open(path) as png:
            png.verify()
        with Image.open(path) as png:
            assert png.size==(1080,1920),(asset,png.size)
    expected={
        ("2027-02-04","morning"):"lunar_new_year_holiday_start",
        ("2027-02-04","evening"):"lichun",
        ("2027-08-08","morning"):"fathers_day",
        ("2027-08-08","evening"):"qixi",
        ("2027-10-08","morning"):"hanlu",
        ("2027-10-08","evening"):"double_ninth",
        ("2027-09-15","morning"):"mid_autumn",
    }
    for (day,slot),key in expected.items():
        result=event_for_slot(day,slot,cal)
        assert result and result["key"]==key,(day,slot,key,result)
    assert event_for_slot("2027-08-07","morning",cal) is None
    assert event_for_slot("2027-08-08","evening",cal)["key"]!="liqiu"
    for reused in entries["reuse"]:
        assert (BASE/reused["asset"]).is_file(), reused
    print(f"PASS: {len(cal['events'])} calendar dates, {len(entries['images'])} new assets registered, "+
          f"{len(entries['reuse'])} reused assets present; morning/evening routes verified.")
    if missing:
        print("PENDING: New image generation (not a code test failure):")
        for file in missing:
            print(" -",file)
    else:
        print("PASS: all 8 images exist, decode, and are 1080x1920.")


if __name__=="__main__":
    main()
