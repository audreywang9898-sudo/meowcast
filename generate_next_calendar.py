import calendar
import json
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from lunar_python import Lunar, Solar

ROOT = Path(__file__).resolve().parent
CALENDAR_PATH = ROOT / "calendar.json"\nNEXT_CALENDAR_PATH = ROOT / "calendar_next.json"

SOLAR_TERMS = {
    "小寒":"xiaohan","大寒":"dahan","立春":"lichun","雨水":"yushui","惊蛰":"jingzhe","驚蟄":"jingzhe",
    "春分":"chunfen","清明":"qingming","谷雨":"guyu","穀雨":"guyu","立夏":"lixia","小满":"xiaoman","小滿":"xiaoman",
    "芒种":"mangzhong","芒種":"mangzhong","夏至":"xiazhi","小暑":"xiaoshu","大暑":"dashu","立秋":"liqiu",
    "处暑":"chushu","處暑":"chushu","白露":"bailu","秋分":"autumn_equinox","寒露":"hanlu","霜降":"shuangjiang",
    "立冬":"lidong","小雪":"xiaoxue","大雪":"daxue","冬至":"dongzhi"
}
LUNAR = {
    "lunar_new_year": (1,1), "lantern_festival": (1,15), "dragon_boat": (5,5),
    "qixi": (7,7), "ghost_festival": (7,15), "mid_autumn": (8,15), "double_ninth": (9,9)
}
FIXED = {
    "new_year": (1,1), "valentines_day": (2,14), "peace_memorial_day": (2,28),
    "womens_day": (3,8), "white_day": (3,14), "april_fools": (4,1), "childrens_day": (4,4),
    "earth_day": (4,22), "labour_day": (5,1), "fathers_day": (8,8), "teachers_day": (9,28),
    "national_day": (10,10), "taiwan_retrocession_day": (10,25), "halloween": (10,31),
    "christmas_eve": (12,24), "christmas": (12,25), "new_years_eve": (12,31)
}

def nth_weekday(year, month, weekday, n):
    d=date(year,month,1)
    d += timedelta(days=(weekday-d.weekday())%7 + 7*(n-1))
    return d

def last_lunar_day(year):
    # Lunar New Year's Eve is the solar day before lunar 1/1.
    new_year = Lunar.fromYmd(year,1,1).getSolar()
    d=date(new_year.getYear(),new_year.getMonth(),new_year.getDay())-timedelta(days=1)
    return d

def solar_terms(year):
    out={}
    d=date(year,1,1)
    while d.year==year:
        lunar=Solar.fromYmd(d.year,d.month,d.day).getLunar()
        name=lunar.getJieQi()
        if name in SOLAR_TERMS:
            out[SOLAR_TERMS[name]]=d
        d += timedelta(days=1)
    return out

def main():
    old=json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    source_year=old["year"]
    target=source_year+1
    templates={v["key"]:v for v in old["events"].values()}
    dates={}

    for key,(m,day) in FIXED.items():
        dates[key]=date(target,m,day)

    for key,(m,day) in LUNAR.items():
        s=Lunar.fromYmd(target,m,day).getSolar()
        dates[key]=date(s.getYear(),s.getMonth(),s.getDay())

    dates["lunar_new_year_eve"]=last_lunar_day(target)
    dates["mothers_day"]=nth_weekday(target,5,6,2)
    dates["thanksgiving"]=nth_weekday(target,11,3,4)
    dates.update(solar_terms(target))

    # Easter (if present as a secondary observance) uses Gregorian computus.
    easter=date(target,*calendar.monthrange(target,3)[:1],1) if False else None

    events={}
    for key,dt in sorted(dates.items(), key=lambda kv: kv[1]):
        if key not in templates:
            continue
        event=deepcopy(templates[key])
        # Secondary observances tied to a different movable date are not blindly copied.
        event.pop("also",None)
        events[dt.isoformat()]=event

    # Preserve Easter as secondary only when it shares a primary event date.
    # Python's standard-library-friendly Anonymous Gregorian algorithm.
    y=target
    a=y%19; b=y//100; c=y%100; d=b//4; e=b%4; f=(b+8)//25; g=(b-f+1)//3
    h=(19*a+b-d-g+15)%30; i=c//4; k=c%4; l=(32+2*e+2*i-h-k)%7
    m=(a+11*h+22*l)//451
    em=(h+l-7*m+114)//31; ed=(h+l-7*m+114)%31+1
    easter_date=date(y,em,ed).isoformat()
    if easter_date in events:
        events[easter_date].setdefault("also",[]).append({
            "type":"festival","key":"easter","name_en":"Easter","name_zh":"復活節"
        })

    # Constitution Day remains a secondary observance on Christmas.
    christmas=f"{target}-12-25"
    if christmas in events:
        events[christmas].setdefault("also",[]).append({
            "type":"holiday","key":"constitution_day","name_en":"Constitution Day","name_zh":"行憲紀念日"
        })

    new={
        "version": old.get("version",2),
        "timezone":"Asia/Taipei",
        "year":target,
        "description":f"Taipei Meowcast {target} calendar, generated automatically on Dec 1 from stable event templates plus lunar and solar-term calculations.",
        "events":events
    }
    CALENDAR_PATH.write_text(json.dumps(new,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Generated {target} calendar with {len(events)} primary events")

if __name__=="__main__":
    main()
